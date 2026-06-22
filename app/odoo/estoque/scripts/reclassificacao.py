# etapa: C2
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""reclassificacao.py — SERVICE da skill WRITE `reclassificando-amls-odoo`.

ReclassificacaoService: executor WRITE de reclassificacao contabil em lote de
account.move.line no Odoo (conta_origem -> conta_destino), preservando a chave
fiscal. Irma WRITE da READ `auditando-reclassificacao-odoo` (que so mede/valida/
monitora).

PRINCIPIO FUNDADOR (app/odoo/estoque/CLAUDE.md §1): atomo versatil + auto-seguro,
2 modos (dry-run default -> confirmar). Objeto Odoo principal: account.move.line
(1 objeto — §1.1). Os guards (SEFAZ, ciclo button_draft->write->action_post,
invariante pos-post, contador real) vivem DENTRO do service como invariante.

REUSO (salvaguarda — NAO reimplementar):
- `_dominio_saldo`: dominio de busca da skill READ
  (.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py
   account_id origem, company_id, journal_id, date range, debit>0, parent_state=posted).
- `validar_lote`: CONTADOR REAL pos-write (processadas/pendentes/divergentes/
  ausentes/duplicados/moves_draft + integro). NUNCA reimplementar contagem.
- guard SEFAZ: pattern provado em app/odoo/estoque/scripts/_invoice_helpers.py:237-310
  + :400-438 (ler l10n_br_situacao_nf antes de button_draft; in (autorizado,
  excecao_autorizado, enviado) -> NAO incluir).

Metodos PUROS testaveis (FakeOdoo): coletar_amls, agrupar_por_move, planejar,
executar, validar_pos_write. Conexao real (CLI) via
app.odoo.utils.connection.get_odoo_connection — mas os metodos recebem a conexao
INJETADA (testes usam FakeOdoo).

Constantes reais recorrentes (defaults, overridaveis):
  company_id=4 (CD)  journal_id=845
Receita-exemplo do D8: 26784 -> 26844 company 4 journal 845.
"""
from __future__ import annotations

import sys
from pathlib import Path

MODEL_LINE = 'account.move.line'
MODEL_MOVE = 'account.move'

# Situacoes SEFAZ que PROIBEM button_draft (invalidaria/abandonaria a chave
# fiscal). Espelha o guard provado em _invoice_helpers.py.
SITUACOES_SEFAZ_BLOQUEADAS = ('autorizado', 'excecao_autorizado', 'enviado')

DEFAULT_COMPANY_ID = 4   # CD
DEFAULT_JOURNAL_ID = 845


# ---------------------------------------------------------------------------
# Import do dominio + contador real da skill READ irma (salvaguarda).
# Carregado via importlib para nao depender de package path da skill.
# ---------------------------------------------------------------------------
def _carregar_skill_read():
    import importlib.util

    here = Path(__file__).resolve()
    # app/odoo/estoque/scripts/reclassificacao.py -> repo root = parents[4]
    repo_root = here.parents[4]
    read_script = (
        repo_root
        / '.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py'
    )
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    spec = importlib.util.spec_from_file_location('auditar_reclassificacao', read_script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_READ = _carregar_skill_read()
# Salvaguardas reusadas (NUNCA reimplementar):
_dominio_saldo = _READ._dominio_saldo
validar_lote = _READ.validar_lote
monitorar_andamento = _READ.monitorar_andamento  # exposto p/ acompanhar execucao


class ReclassificacaoService:
    """Executor WRITE de reclassificacao de account.move.line em lote."""

    def __init__(self, odoo):
        self.odoo = odoo

    # -------------------------------------------------------------------
    # Helpers puros
    # -------------------------------------------------------------------
    @staticmethod
    def _acc_id(row):
        """Extrai id da conta (account_id vem como [id, nome] ou False).

        Reusa a semantica de _acc_id da skill READ.
        """
        acc = row.get('account_id')
        if isinstance(acc, (list, tuple)) and acc:
            return acc[0]
        return acc or None

    @staticmethod
    def _move_id(row):
        """Extrai id do move (move_id vem como [id, nome] ou False)."""
        mv = row.get('move_id')
        if isinstance(mv, (list, tuple)) and mv:
            return mv[0]
        return mv or None

    # -------------------------------------------------------------------
    # coletar_amls — reusa o dominio da skill READ
    # -------------------------------------------------------------------
    def coletar_amls(self, conta_origem, data_inicio, data_fim,
                     company_id=DEFAULT_COMPANY_ID, journal_id=DEFAULT_JOURNAL_ID):
        """Coleta as account.move.line da conta_origem no periodo (debit>0,
        parent_state=posted) usando o MESMO dominio da skill READ.

        Retorna lista de rows com id/account_id/move_id/debit.
        """
        dom = _dominio_saldo(conta_origem, data_inicio, data_fim,
                             company_id, journal_id, state='posted')
        return self.odoo.search_read(
            MODEL_LINE, dom, ['account_id', 'move_id', 'debit'])

    # -------------------------------------------------------------------
    # agrupar_por_move
    # -------------------------------------------------------------------
    def agrupar_por_move(self, rows):
        """Agrupa as linhas por move_id. Cada item: {lid, move_id, debit}.

        Mantem a ordem de 1a ocorrencia de cada move (deterministico).
        """
        grupos: dict = {}
        for r in rows:
            mid = self._move_id(r)
            if mid is None:
                continue
            grupos.setdefault(mid, []).append({
                'lid': r['id'],
                'move_id': mid,
                'debit': r.get('debit', 0.0),
            })
        return grupos

    # -------------------------------------------------------------------
    # planejar — monta plano + aplica GUARD SEFAZ
    # -------------------------------------------------------------------
    def planejar(self, conta_origem, conta_destino, data_inicio, data_fim,
                 company_id=DEFAULT_COMPANY_ID, journal_id=DEFAULT_JOURNAL_ID):
        """Monta o plano de reclassificacao agrupado por move.

        GUARD SEFAZ: le l10n_br_situacao_nf de cada move; os que estao em
        SITUACOES_SEFAZ_BLOQUEADAS NAO entram em `grupos` (vao para
        `skip_sefaz` com status SKIP_GUARD_SITUACAO_NF). button_draft neles
        invalidaria/abandonaria a chave fiscal.

        Retorna:
          {modo, conta_origem, conta_destino, company_id, journal_id, periodo,
           grupos: {move_id: [{lid, move_id, debit}, ...]} (efetivaveis),
           skip_sefaz: [{move_id, status, situacao_nf}],
           n_moves, n_linhas, total_debito}
        """
        rows = self.coletar_amls(conta_origem, data_inicio, data_fim,
                                 company_id, journal_id)
        grupos_brutos = self.agrupar_por_move(rows)

        # GUARD SEFAZ — ler situacao_nf de todos os moves de uma vez
        move_ids = list(grupos_brutos.keys())
        situacoes: dict = {}
        if move_ids:
            mrows = self.odoo.read(
                MODEL_MOVE, move_ids, ['l10n_br_situacao_nf', 'state'])
            situacoes = {m['id']: m for m in mrows}

        grupos: dict = {}
        skip_sefaz = []
        for mid, linhas in grupos_brutos.items():
            sit = (situacoes.get(mid) or {}).get('l10n_br_situacao_nf')
            if sit in SITUACOES_SEFAZ_BLOQUEADAS:
                skip_sefaz.append({
                    'move_id': mid,
                    'status': 'SKIP_GUARD_SITUACAO_NF',
                    'situacao_nf': sit,
                    'n_linhas': len(linhas),
                })
                continue
            grupos[mid] = linhas

        n_linhas = sum(len(v) for v in grupos.values())
        total_debito = round(
            sum(l['debit'] for v in grupos.values() for l in v), 2)
        return {
            'modo': 'plano',
            'conta_origem': conta_origem,
            'conta_destino': conta_destino,
            'company_id': company_id,
            'journal_id': journal_id,
            'periodo': {'inicio': data_inicio, 'fim': data_fim},
            'grupos': grupos,
            'skip_sefaz': skip_sefaz,
            'n_moves': len(grupos),
            'n_linhas': n_linhas,
            'total_debito': total_debito,
        }

    # -------------------------------------------------------------------
    # executar — dry-run (default) ou WRITE por move
    # -------------------------------------------------------------------
    def executar(self, plano, confirmar: bool = False):
        """Efetiva a reclassificacao (ou preview se confirmar=False).

        WRITE por move (batch): para cada move com state=posted aplica o ciclo
        OBRIGATORIO button_draft -> write account_id=destino (SO as linhas da
        conta_origem do move) -> action_post.

        INVARIANTE pos action_post: re-le state; se != posted, retorna
        FALHA_POST_NAO_POSTED e PARA o batch (nao deixa rascunho no razao).

        Retorna:
          confirmar=False -> {status: DRY_RUN_OK, moves_a_processar, linhas_a_escrever}
          confirmar=True  -> {status: EXECUTADO | FALHA_POST_NAO_POSTED |
                              FALHA_ODOO, moves_processados, linhas_escritas,
                              moves_falha?, erro?}
        """
        grupos = plano['grupos']
        conta_destino = plano['conta_destino']

        if not confirmar:
            return {
                'status': 'DRY_RUN_OK',
                'moves_a_processar': len(grupos),
                'linhas_a_escrever': sum(len(v) for v in grupos.values()),
                'total_debito': plano['total_debito'],
            }

        moves_processados = 0
        linhas_escritas = 0
        for mid, linhas in grupos.items():
            lids = [l['lid'] for l in linhas]
            try:
                # 1) button_draft (rebaixa o move para rascunho)
                self.odoo.execute_kw(MODEL_MOVE, 'button_draft', [[mid]])
                # 2) write account_id=destino SO nas linhas da conta_origem
                self.odoo.write(MODEL_LINE, lids, {'account_id': conta_destino})
                linhas_escritas += len(lids)
                # 3) action_post (re-posta o move)
                self.odoo.execute_kw(MODEL_MOVE, 'action_post', [[mid]])
            except Exception as exc:  # noqa: BLE001 — qualquer falha PARA o batch
                return {
                    'status': 'FALHA_ODOO',
                    'moves_processados': moves_processados,
                    'linhas_escritas': linhas_escritas,
                    'move_falha': mid,
                    'erro': str(exc)[:500],
                }
            # INVARIANTE pos-post: re-ler state
            estado = self.odoo.read(MODEL_MOVE, [mid], ['state'])
            state = (estado[0].get('state') if estado else None)
            if state != 'posted':
                return {
                    'status': 'FALHA_POST_NAO_POSTED',
                    'moves_processados': moves_processados,
                    'linhas_escritas': linhas_escritas,
                    'move_falha': mid,
                    'state_apos_post': state,
                    'erro': (f'move {mid} ficou state={state!r} apos action_post '
                             f'— batch PARADO para nao deixar rascunho no razao'),
                }
            moves_processados += 1

        return {
            'status': 'EXECUTADO',
            'moves_processados': moves_processados,
            'linhas_escritas': linhas_escritas,
            'total_debito': plano['total_debito'],
        }

    # -------------------------------------------------------------------
    # validar_pos_write — CONTADOR REAL da skill READ (salvaguarda)
    # -------------------------------------------------------------------
    def validar_pos_write(self, plano, conta_destino, conta_origem):
        """Valida o resultado via `validar_lote` da skill READ (CONTADOR REAL).

        Monta os `registros` no formato que a skill READ consome
        ({line: move_id, lid, debit}) a partir do plano efetivado, delega a
        validar_lote e adiciona `total_esperado`. NAO reimplementa contagem.

        integro==True exige: sem duplicados/ausentes/divergentes. O caller
        (CLI) exige adicionalmente processadas==total_esperado + moves_draft==0
        para declarar EXECUTADO (senao EXECUTADO_PARCIAL).
        """
        registros = []
        for mid, linhas in plano['grupos'].items():
            for l in linhas:
                registros.append({
                    'line': mid,
                    'lid': l['lid'],
                    'debit': l['debit'],
                })
        res = validar_lote(self.odoo, registros, conta_destino, conta_origem)
        res['total_esperado'] = len(registros)
        return res


# ---------------------------------------------------------------------------
# Conexao real (so usada pelo CLI; testes injetam FakeOdoo)
# ---------------------------------------------------------------------------
def get_service(odoo=None) -> ReclassificacaoService:
    """Fronteira de I/O — instancia o service com a conexao oficial do Odoo.

    Import lazy de get_odoo_connection para nao acoplar os helpers ao app.
    """
    if odoo is None:
        from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            raise RuntimeError('Falha na autenticacao com Odoo')
    return ReclassificacaoService(odoo)
