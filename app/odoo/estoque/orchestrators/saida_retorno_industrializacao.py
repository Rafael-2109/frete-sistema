# etapa: C3-orchestrator
# doc-dono: docs/industrializacao-fb-lf/SOT_OPERACOES.md §6.3 + app/odoo/estoque/CLAUDE.md §3.1
"""LADO NOSSO (READ) da automação da SAÍDA do retorno de industrialização LF→FB.

A **execução** das 2 NFs de saída (NF-1 serviço 5124 via `stock.invoice.onshipping` +
NF-2 insumos 5902 montada-direto op 2864 + recompute + remap fp 111 + R3) é **server-side**
e vive na **server action persistente** (categoria infra-Odoo, `app/odoo/estoque/provisioning/`)
— porque o recompute fiscal `onchange_l10n_br_calcular_imposto` **só persiste dentro de uma SA**
(`s48`/`s49`; ver `PROTECAO §N34`). Este orchestrator NÃO monta NF.

Papel deste módulo (DECISÃO SOT §6.3 — Opção B): o `DescobertaIndustrializacaoService`
vira **spec executável + ORÁCULO de validação**. Aqui compomos os átomos READ (descoberta +
`resolver_chave_remessa`) para:
  - `planejar(nf1_id)`  — pré-computa o spec do ciclo (componentes/total via rateio, remessa, PA);
  - `validar(nf1_id, nf2_id)` — confronta a NF-2 que a SA produziu CONTRA o spec (oráculo);
  - `medir(nf1_id, nf2_id)`   — baixa da PASSIVA `5101020001` (LF) medida pelo CICLO (não saldo global).

Constituição (`app/odoo/estoque/CLAUDE.md §3.1`): orchestrator C3 só COMPÕE átomos; READ-only
aqui (zero escrita — a escrita é da SA). NÃO usa `RecebimentoLfOdooService` (NÃO MEXER).
"""
import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService
from app.odoo.estoque.scripts.descoberta_industrializacao import DescobertaIndustrializacaoService

logger = logging.getLogger(__name__)

# ── CONSTANTS (saída LF→FB — provados no piloto pelo s37/s40/s54) ──────────────────
# 🔴 TODO FOCO 3 (consolidar em L0 `app/odoo/constants/` + IDS_FIXOS.md): account.account
#    é COMPANY-SPECIFIC — VERIFICAR CADA id contra o Odoo vivo antes de promover (Zero
#    Invenção). Hoje espelham os IDs já verificados no piloto (s37 constants).
COMPANY_FB = 1
COMPANY_LF = 5
PARTNER_FB = 1                       # FB como destinatário (partner) da NF-2 de saída

J847 = 847                           # NF-1 serviço (venda-industrializacao) — gatilho do ciclo
RETIND = 1083                        # NF-2 insumos (LF sale, no_payment PASSIVA 26667)
OP_5902 = 2864                       # operação da linha 5902 (header + linhas operacao_manual)
FP_RETIND = 111                      # fiscal_position do retorno (De-Para conta → 1150100012)

CFOP_NF2 = '5902'                    # esperado nas linhas da NF-2 (saída intraestadual)
CST_NF2 = '50'                       # ICMS CST suspensão (sem tributo — tax_ids=[])
COD_CONTA_NF2 = '1150100012'         # conta destino das linhas 5902 (transitória faturamento)

# Conta da baixa da PASSIVA 5101020001 no lado LF (medição por ciclo — s40 saldo_passiva)
ACC_PASSIVA_LF = (26667, '5101020001')


def _total_esperado_por_linha(spec: Dict[str, Any]) -> float:
    """Total esperado da NF-2 = Σ do `price_subtotal` arredondado POR LINHA (replica como a
    NF-e soma), NÃO o float arredondado só no fim. Usado por `validar` (estrutura) e `medir`
    (baixa PASSIVA): a baixa = total da NF = soma por-linha. Comparar contra o float acusaria
    falsa divergência de arredondamento (N linhas → ~R$0,0n) sem ser erro de cálculo.
    Fallback p/ `total_ic` quando o spec não traz `componentes` (qty + price_unit)."""
    componentes = spec.get('componentes') or []
    if componentes:
        return round(sum(round((c.get('qty') or 0) * (c.get('price_unit') or 0), 2)
                         for c in componentes), 2)
    return round(spec.get('total_ic') or 0, 2)


class SaidaRetornoIndustrializacaoExecutor:
    """Orchestrator C3 READ do lado nosso da SAÍDA. Services-átomos injetáveis (test-friendly)."""

    def __init__(
        self,
        odoo,
        *,
        escrit_svc: Optional[EscrituracaoLfService] = None,
        descoberta_svc: Optional[DescobertaIndustrializacaoService] = None,
    ):
        self.odoo = odoo
        self.escrit = escrit_svc or EscrituracaoLfService(odoo=odoo)
        self.descoberta = descoberta_svc or DescobertaIndustrializacaoService(odoo)

    # ── PLAN (READ) — pré-computa o spec do ciclo (= oráculo da SA) ───────────────
    def planejar(self, *, nf1_servico_id: int, ciclo: Optional[str] = None) -> Dict[str, Any]:
        """READ — monta o `spec` do ciclo a partir da NF-1 de serviço de SAÍDA da LF.

        Pré-computa o que a SA produz server-side, para o orchestrator/monitor VALIDAR
        a saída da SA contra a nossa Descoberta (DECISÃO SOT §6.3 — Descoberta = oráculo):
          - descoberta da fonte da NF-2 (componentes, total Ic via rateio, remessa, PA);
          - metadados da NF-1 (journal, cstat, invoice_date);
          - chave da remessa (R3) via `referencia_ids` da NF-1 (best-effort: só existe
            DEPOIS que a SA gravou o R3 — pré-SA retorna VAZIO, o que é esperado).
        ZERO escrita.
        """
        desc = self.descoberta.descobrir_fonte_nf2(nf1_servico_id)
        pa = desc.get('pa') or {}
        ciclo = ciclo or f"RET-IND-{pa.get('product_id')}-{nf1_servico_id}"

        nf1 = self.odoo.read('account.move', [nf1_servico_id],
                             ['journal_id', 'l10n_br_cstat_nf', 'invoice_date', 'state'])
        nf1 = nf1[0] if nf1 else {}
        journal = nf1.get('journal_id')
        journal_id = (journal[0] if isinstance(journal, list) else journal) if journal else None

        # chave da remessa (R3) — referencia_ids da NF-1 (best-effort: pode estar vazio pré-SA)
        rem = self.escrit.resolver_chave_remessa(nf_saida_id=nf1_servico_id, company_id=COMPANY_LF)
        chave_remessa = rem.get('chave')

        return {
            'nf1_servico_id': nf1_servico_id,
            'ciclo': ciclo,
            'journal_id_nf1': journal_id,
            'journal_ok': journal_id == J847,
            'cstat_nf1': nf1.get('l10n_br_cstat_nf'),
            'invoice_date': nf1.get('invoice_date'),
            'state_nf1': nf1.get('state'),
            'pa_product_id': pa.get('product_id'),
            'pa_lote_id': pa.get('lote'),
            'pa_qtd_faturada': pa.get('qtd_faturada'),
            'produzido_total': desc.get('produzido_total'),
            'componentes': desc.get('componentes') or [],
            'n_componentes': len(desc.get('componentes') or []),
            'total_ic': desc.get('total'),
            'remessa': desc.get('remessa'),
            'chave_remessa': chave_remessa,
        }

    # ── VALIDAR (READ) — confronta a NF-2 da SA contra o spec (oráculo) ───────────
    def validar(self, spec: Dict[str, Any], *, nf2_id: int) -> Dict[str, Any]:
        """READ — confronta a NF-2 (produzida server-side pela SA) CONTRA o spec da
        Descoberta. Cada divergência é fiscal-crítica (CFOP/CST/conta/total errados =
        NF errada na SEFAZ). NÃO escreve.

        Checks: journal RETIND · nº linhas == nº componentes · CFOP {5902} · CST {50} ·
        conta da linha == 1150100012 · total ≈ spec.total_ic · R3 (invoice_origin + refNFe).
        """
        divergencias: List[str] = []
        nf2 = self.odoo.read(
            'account.move', [nf2_id],
            ['journal_id', 'invoice_origin', 'referencia_ids', 'state', 'amount_untaxed'])
        if not nf2:
            return {'ok': False, 'divergencias': ['nf2_inexistente'], 'nf2_id': nf2_id}
        nf2 = nf2[0]

        jid = nf2.get('journal_id')
        jid = (jid[0] if isinstance(jid, list) else jid) if jid else None
        if jid != RETIND:
            divergencias.append(f'journal={jid} (esperado RETIND {RETIND})')

        linhas = self._sr(
            'account.move.line',
            [('move_id', '=', nf2_id), ('display_type', '=', 'product')],
            ['l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'account_id', 'price_subtotal'])
        n = len(linhas)
        n_esperado = spec.get('n_componentes') or 0
        if n_esperado and n != n_esperado:
            divergencias.append(f'n_linhas={n} (esperado {n_esperado} componentes)')

        cfops = {str(l.get('l10n_br_cfop_codigo')) for l in linhas if l.get('l10n_br_cfop_codigo')}
        if cfops and cfops != {CFOP_NF2}:
            divergencias.append(f'CFOP={sorted(cfops)} (esperado {{{CFOP_NF2}}})')
        csts = {str(l.get('l10n_br_icms_cst')) for l in linhas if l.get('l10n_br_icms_cst')}
        if csts and csts != {CST_NF2}:
            divergencias.append(f'CST={sorted(csts)} (esperado {{{CST_NF2}}})')

        contas = set()
        for l in linhas:
            acc = l.get('account_id')
            contas.add(acc[1] if isinstance(acc, list) and len(acc) > 1 else acc)
        contas_cod = {str(c).split(' ')[0].strip() for c in contas if c}
        if contas_cod and not all(c == COD_CONTA_NF2 for c in contas_cod):
            divergencias.append(f'conta_linha={sorted(contas_cod)} (esperado {COD_CONTA_NF2})')

        total_nf2 = round(nf2.get('amount_untaxed') or 0, 2)
        # Total esperado = Σ por-linha (replica a NF-e); float só p/ transparência. Ver
        # _total_esperado_por_linha — não afrouxa a tolerância de 0,01 (pega erro real).
        total_spec_float = round(spec.get('total_ic') or 0, 2)
        total_spec = _total_esperado_por_linha(spec)
        if total_spec and abs(total_nf2 - total_spec) > 0.01:
            divergencias.append(
                f'total={total_nf2} (esperado ≈ {total_spec} por-linha; float={total_spec_float})')

        if not nf2.get('invoice_origin'):
            divergencias.append('R3 invoice_origin ausente')
        if not (nf2.get('referencia_ids') or []):
            divergencias.append('R3 referencia_ids (refNFe) ausente')

        return {
            'ok': not divergencias,
            'divergencias': divergencias,
            'nf2_id': nf2_id,
            'n_linhas': n,
            'cfops': sorted(cfops),
            'csts': sorted(csts),
            'total_nf2': total_nf2,
            'total_spec': total_spec,
            'total_spec_float': total_spec_float,
            'state': nf2.get('state'),
        }

    # ── MEDIR (READ) — baixa da PASSIVA pelo CICLO ────────────────────────────────
    def medir(self, spec: Dict[str, Any], *, nf2_id: Optional[int] = None) -> Dict[str, Any]:
        """READ — baixa da PASSIVA `5101020001` (LF, conta 26667) medida pelos LANÇAMENTOS
        DOS MOVES DO CICLO (NÃO saldo global — a conta é compartilhada pela empresa inteira,
        oscila com o tráfego concorrente). Coleta os `account.move` do ciclo por
        `invoice_origin` (+ id explícito da NF-2) e soma o débito na conta 26667.

        Alvo: a NF-2 (insumos) DEBITA a conta 26667 = total dos insumos (baixa a PASSIVA
        criada na entrada da remessa). `s40` mediu Δ+279,23 no piloto (lote inteiro).
        """
        ciclo = spec['ciclo']
        acc_id, acc_cod = ACC_PASSIVA_LF
        move_ids, detalhe = self._coletar_moves_ciclo(ciclo=ciclo, extra_ids=[nf2_id] if nf2_id else [])
        baixa = self._debito_moves_conta(move_ids, acc_id)
        # Alvo = total por-linha (= total da NF = baixa da PASSIVA). Float só p/ transparência.
        alvo = _total_esperado_por_linha(spec)
        return {
            'ciclo': ciclo,
            'conta_passiva': acc_cod,
            'baixa_passiva': baixa,
            'alvo': alvo,
            'alvo_float': round(spec.get('total_ic') or 0, 2),
            'ok': bool(alvo) and abs(baixa - alvo) <= 0.01,
            'moves_incluidos': detalhe,
            'nota': ('baixa = D na conta 26667 das NFs do ciclo (= total insumos). Em fatura '
                     'PARCIAL (rateio) a baixa é do PA faturado; lote inteiro fecha a PASSIVA.'),
        }

    # ── helpers de resolução (READ) ───────────────────────────────────────────────
    def _coletar_moves_ciclo(self, *, ciclo: str, extra_ids: Optional[List[int]] = None):
        """READ — coleta os account.move do ciclo por `invoice_origin` (+ ids explícitos).
        Query DIRECIONADA (por origin) — nunca varre a conta inteira (timeout)."""
        move_ids = set(i for i in (extra_ids or []) if i)
        detalhe: List[Dict[str, Any]] = []
        for e in self._sr('account.move',
                          [('invoice_origin', '=', ciclo), ('company_id', '=', COMPANY_LF)],
                          ['id', 'name']):
            move_ids.add(e['id'])
            detalhe.append({'tipo': 'saida', 'id': e['id'], 'name': e.get('name')})
        return move_ids, detalhe

    def _debito_moves_conta(self, move_ids, account_id: int) -> float:
        """READ — soma do débito das linhas (moves do ciclo ∩ conta). Baixa de PASSIVA = D."""
        if not move_ids:
            return 0.0
        ml = self._sr('account.move.line',
                      [('move_id', 'in', list(move_ids)), ('account_id', '=', account_id)],
                      ['debit'])
        return round(sum((l.get('debit') or 0) for l in ml), 2)

    def _sr(self, model: str, domain: list, fields: list) -> list:
        """search_read defensivo (retorna [] se não-lista — robusto a mock/erro)."""
        try:
            rows = self.odoo.search_read(model, domain, fields)
            return rows if isinstance(rows, list) else []
        except Exception as e:
            logger.warning(f'_sr {model} falhou: {str(e)[:120]}')
            return []


# ── CLI (READ-only — a escrita é da server action; ver provisioning/) ──────────────
_MODOS = ('plan', 'validar', 'medir')


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Lado NOSSO (READ) da SAÍDA de retorno de industrialização (oráculo/validar/medir). '
                    'A execução é server-side (server action — ver app/odoo/estoque/provisioning/).')
    ap.add_argument('modo', choices=_MODOS, help='etapa READ a executar')
    ap.add_argument('--nf1-servico', type=int, required=True, help='account.move da NF-1 serviço de SAÍDA da LF')
    ap.add_argument('--ciclo', type=str, default=None, help="invoice_origin comum (ex.: 'RET-IND-4870112-PILOTO')")
    ap.add_argument('--nf2-id', type=int, default=None, help='account.move da NF-2 insumos (validar/medir)')
    args = ap.parse_args(argv)

    from app.odoo.utils.connection import get_odoo_connection
    import json
    odoo = get_odoo_connection()
    assert odoo.authenticate(), 'falha autenticacao Odoo'
    ex = SaidaRetornoIndustrializacaoExecutor(odoo)
    spec = ex.planejar(nf1_servico_id=args.nf1_servico, ciclo=args.ciclo)

    if args.modo == 'plan':
        out = spec
    elif args.modo == 'validar':
        assert args.nf2_id, '--nf2-id obrigatório para validar'
        out = ex.validar(spec, nf2_id=args.nf2_id)
    elif args.modo == 'medir':
        out = ex.medir(spec, nf2_id=args.nf2_id)
    else:
        out = {'erro': f'modo desconhecido: {args.modo}'}

    print(json.dumps({'modo': args.modo, 'resultado': out}, default=str, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
