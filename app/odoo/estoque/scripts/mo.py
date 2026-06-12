# etapa: C2
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""StockMOService — operacoes de escrita em mrp.production (Manufacturing Orders).

Primitivas REUTILIZAVEIS para CANCELAR e CONCLUIR MO no Odoo.

V1 (2026-05-24): unico atomo demanda-driven (skills nascem de casos reais):
- cancelar_mo(mo_id, motivo='', forcar_consumo=False, dry_run=False)
  - Wrapper sobre action_cancel + re-le state pos (G019-like pattern)
  - Guard G-MO-01: consumo_total > 0 -> bloqueia (FALHA_FURO_CONTABIL)
  - Idempotencia: state pre='cancel' -> NOOP (validado AO VIVO 2026-05-24)
- cancelar_mos_em_massa(criterio, max_n=0, dry_run=False)
  - Composicao sobre cancelar_mo. Filtra MOs por criterio (create_date range,
    states, empresas, consumo zero|qualquer), mede consumo em batch (perf),
    delega cancelar_mo individual.

V7 (2026-06-12): atomo concluir_mo (demanda real: MO LF/MO/03556 sessao
2026-06-10 + piloto industrializacao FB-LF 2026-06-01):
- concluir_mo(mo_id, nome_lote=None, motivo='', dry_run=False)
  - Produzir Tudo + Validar: action_assign -> lot_producing/qty_producing ->
    picked=True nos raws (G-MO-05) -> button_mark_done (+ wizard consumo) ->
    G019-like -> POS-CHECK anti-producao-fantasma. Single-only (sem batch —
    escrita CONTABIL irreversivel). Sequencia minerada de
    docs/industrializacao-fb-lf/scripts/e2e_mo_lf_criar.py (validada PROD).

Atomos PREVISTOS sem demanda (NAO implementar — feedback-skills-demanda-driven):
- criar_mo: sem demanda real isolada (pipeline cria via Odoo)
- alterar_mo: caso real existe mas e fluxo cross-skill (Skill 2 transfer +
  write em stock.move). Ver memoria local Claude Code [[mo_componente_local_consumo]].

Gotchas-invariante codificados:
- G-MO-01: consumo_total > 0 = FURO CONTABIL -> bloqueia cancelamento.
  Operador deve usar mrp.unbuild via fluxo cross-skill se precisar reverter
  consumo. Ver memoria local Claude Code [[reaproveitar-semiacabado-orfao-mo-cancelada]] §3.
- G-MO-02: manual_consumption=True nao reserva via action_assign. NAO
  relevante para cancelar (action_cancel ignora reservas/picked). RELEVANTE
  para concluir: raw sem move.line e CANCELADO pelo button_mark_done ->
  G-MO-06 bloqueia (FALHA_COMPONENTE_SEM_RESERVA).
- G-MO-03: componente em local errado (Indisponivel/Estoque vs location_src
  declarado). Nao relevante para cancelar. RELEVANTE para concluir: e a outra
  causa de raw sem move.line pos-action_assign (mesmo bloqueio G-MO-06).
- G-MO-04: picked=True em to_close/done — herdado de Skill 2.4 G026.
  action_cancel e seguro com picked (nao mexe em quants existentes).
- G-MO-05 (ex-G-ENT-10 do piloto, validado PROD 2026-06-01): action_assign
  cria move.line com picked=False; o wizard mrp.consumption.warning dispara
  button_mark_done(skip_consumption=True) que, com picked=False, interpreta
  "nada apontado" e CANCELA os raws -> producao fantasma (SVL value=0, sem
  account.move; caso real MOs 20235/36/38/39). Fix codificado: picked=True
  em MLs + moves ANTES do mark_done + POS-CHECK pos-done (raw cancelado ->
  FALHA_PRODUCAO_FANTASMA). Ground-truth MO boa: LF/MO/03510.
- G-MO-06: raw move sem stock.move.line pos-action_assign (causas: G-MO-02
  manual_consumption OU G-MO-03 saldo fora do location_src) -> concluir
  cancelaria o raw silenciosamente (consumo parcial). Default seguro:
  BLOQUEAR listando os raws (FALHA_COMPONENTE_SEM_RESERVA).

Helpers:
- medir_consumo_mo(mo_ids): retorna dict {mo_id: {done, reservado, total}}.
  Soma stock.move.quantity por raw_material_production_id particionado por state:
    done       = state='done'                              (consumo CONTABIL real)
    reservado  = state IN (assigned, waiting, partially_available, confirmed)
                                                           (apenas reserva fantasma)
    total      = done + reservado                          (compat legacy)
  Tolerancia > 0.0001 (mesma de cancelar_mos.py e 14_cancelar_mos_antigas_fb.py).
- medir_consumo_mo_legacy(mo_ids): retorna {mo_id: float total} (compat ate
  callers migrarem; nao usar em codigo novo).

Status canonicos (output['status']):
- EXECUTADO — state pos='cancel' (action_cancel teve efeito)
- NOOP — state pre='cancel' (idempotente, action_cancel chamado mesmo assim)
- FALHA_FURO_CONTABIL_REAL — consumo done > 0 e forcar_consumo=False (default).
                              Renomeado em 2026-05-27 v6 (era FALHA_FURO_CONTABIL).
                              Alias FALHA_FURO_CONTABIL mantido em compatibilidade.
- FALHA_STATE_NAO_CANCELAVEL — state pre='done' (nao tem como reverter sem unbuild)
- FALHA_STATE_INESPERADO — state pos != 'cancel' (chamado mas nao cancelou)
- FALHA — excecao generica
- DRY_RUN_OK | DRY_RUN_NOOP | DRY_RUN_FALHA_FURO_CONTABIL_REAL |
  DRY_RUN_FALHA_STATE_NAO_CANCELAVEL
- DRY_RUN_OK_RESERVA_FANTASMA — consumo done = 0 mas reservado > 0 (NOVO 2026-05-27 v6).
                                 Passa o guard (action_cancel apenas libera reservas).
- OK_RESERVA_FANTASMA — espelho confirmado de DRY_RUN_OK_RESERVA_FANTASMA

Status canonicos do concluir_mo (V7 2026-06-12):
- EXECUTADO — state pos='done' + POS-CHECK G-MO-05 limpo (raws consumidos)
- NOOP | DRY_RUN_NOOP — state pre='done' (idempotente, nenhum RPC de escrita)
- DRY_RUN_OK — plano valido (pode carregar `warnings` informativos)
- FALHA_STATE_NAO_CONCLUIVEL | DRY_RUN_FALHA_STATE_NAO_CONCLUIVEL —
  state pre IN (cancel, draft); draft orienta action_confirm previo
- FALHA_COMPONENTE_SEM_RESERVA — G-MO-06: raw sem move.line pos-action_assign
- FALHA_LOTE_PRODUZIDO_AUSENTE | DRY_RUN_FALHA_LOTE_PRODUZIDO_AUSENTE —
  tracking lot/serial sem lot_producing_id nem nome_lote informado
  (nunca inventar nome de lote)
- FALHA_PRODUCAO_FANTASMA — POS-CHECK G-MO-05: raw cancelado pos-mark_done
- FALHA_STATE_INESPERADO — mark_done executado mas state pos != 'done'
- FALHA — excecao generica

Spec: consolidacao de scripts cancelar_mos.py + 14_cancelar_mos_antigas_fb.py
(inventario 2026-05). Validado AO VIVO 2026-05-24 (10.000 MOs FB / 17 CD /
3367 LF, idempotencia action_cancel em state=cancel = True sem erro).
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Tolerancia para considerar consumo > 0 (mesma dos scripts-fonte).
TOL_CONSUMO = 0.0001

# States em que cancelar MO faz sentido (pre).
STATES_CANCELAVEIS = ('draft', 'confirmed', 'progress', 'to_close')

# States bloqueados (nao da pra reverter sem unbuild).
STATES_NAO_CANCELAVEIS = ('done',)

# States em que concluir MO faz sentido (pre). draft exige action_confirm
# previo (decisao 2026-06-12: falhar pedindo confirmacao, nao auto-confirmar).
STATES_CONCLUIVEIS = ('confirmed', 'progress', 'to_close')

# Particao de stock.move.state para classificar consumo (G-MO-01 v6, 2026-05-27).
# DONE = baixa contabil efetivada (action_cancel = furo); RESERVADO = apenas
# reserva (action_cancel libera sem furo).
_STATES_CONSUMO_DONE = ('done',)
_STATES_CONSUMO_RESERVADO = ('assigned', 'waiting', 'partially_available', 'confirmed')

# Campos minimos para diagnostico/auditoria.
_CAMPOS_MO = [
    'id', 'name', 'state', 'company_id', 'product_id', 'product_qty',
    'qty_produced', 'create_date', 'date_start',
]


class StockMOService:
    """Gerencia mrp.production no Odoo de forma reutilizavel (cancelar only V1)."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    # ============================================================
    # Helpers de leitura
    # ============================================================

    def _ler_mo(self, mo_id: int) -> Optional[Dict[str, Any]]:
        """Le 1 MO com campos minimos. Retorna None se nao existe."""
        res = self.odoo.search_read(
            'mrp.production', [['id', '=', mo_id]], _CAMPOS_MO,
        )
        return res[0] if res else None

    @staticmethod
    def _chunks(lst, n=200):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def medir_consumo_mo(self, mo_ids: List[int]) -> Dict[int, Dict[str, float]]:
        """Soma stock.move.quantity dos componentes por MO, particionado por state.

        Pattern refinado em 2026-05-27 v6 a partir da descoberta de que MOs
        com `quantity > 0` em state `assigned`/`waiting` sao apenas RESERVAS
        marcadas (picked=True), NAO consumo contabil. Sem essa particao, o
        guard G-MO-01 classificava 29 MOs zumbi como FURO (todas eram falso
        positivo — auditoria 2026-05-27).

        Returns:
            {mo_id: {'done': float, 'reservado': float, 'total': float}}.
            done       = sum(quantity WHERE state='done')                  furo real
            reservado  = sum(quantity WHERE state IN reservado-states)     so reserva
            total      = done + reservado                                  legacy
            MOs sem moves retornam {'done': 0.0, 'reservado': 0.0, 'total': 0.0}.
        """
        if not mo_ids:
            return {}
        done: Dict[int, float] = defaultdict(float)
        reservado: Dict[int, float] = defaultdict(float)
        for ch in self._chunks(mo_ids):
            mvs = self.odoo.search_read(
                'stock.move',
                [['raw_material_production_id', 'in', list(ch)],
                 ['state', '!=', 'cancel']],
                ['raw_material_production_id', 'state', 'quantity'],
            )
            for m in mvs:
                rid = m.get('raw_material_production_id')
                if not rid:
                    continue
                st = m.get('state')
                qty = float(m.get('quantity') or 0)
                if st in _STATES_CONSUMO_DONE:
                    done[rid[0]] += qty
                elif st in _STATES_CONSUMO_RESERVADO:
                    reservado[rid[0]] += qty
        return {
            mid: {
                'done': float(done.get(mid, 0.0)),
                'reservado': float(reservado.get(mid, 0.0)),
                'total': float(done.get(mid, 0.0)) + float(reservado.get(mid, 0.0)),
            }
            for mid in mo_ids
        }

    def medir_consumo_mo_legacy(self, mo_ids: List[int]) -> Dict[int, float]:
        """Compat: retorna apenas o `total` (= done + reservado) por MO.

        Para callers que ainda dependem do formato float legacy. NAO usar em
        codigo novo — preferir `medir_consumo_mo` (dict particionado).
        """
        return {mid: d['total'] for mid, d in self.medir_consumo_mo(mo_ids).items()}

    # ============================================================
    # Operacao atomica: cancelar 1 MO
    # ============================================================

    def cancelar_mo(
        self,
        mo_id: int,
        *,
        motivo: str = '',
        forcar_consumo: bool = False,
        consumo_total: Optional[Union[Dict[str, float], float]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Cancela 1 mrp.production via action_cancel com guards G-MO-*.

        Guard G-MO-01 refinado em 2026-05-27 v6:
        - done > TOL  -> FALHA_FURO_CONTABIL_REAL  (consumo contabil efetivado)
        - done = 0 e reservado > TOL -> OK_RESERVA_FANTASMA (action_cancel
                                         libera reservas sem furo)
        - done = 0 e reservado = 0 -> OK (limpo)

        Args:
            mo_id: mrp.production.id alvo.
            motivo: registrado apenas para log/auditoria (Odoo nao tem
                campo nativo para motivo de cancelamento).
            forcar_consumo: se True, IGNORA o guard G-MO-01 ate em furo real.
                NAO RECOMENDADO — use mrp.unbuild via cross-skill se precisar
                reverter consumo. Mantido para casos extremos auditados.
            consumo_total: dict {done, reservado, total} ja calculado
                (opcional). Quando informado, evita re-query (uso em
                cancelar_mos_em_massa). Quando None, mede via medir_consumo_mo
                (custa 1 RPC extra). Aceita float (compat legacy) — tratado
                como `total` (sem particao; degrada para guard antigo).
            dry_run: nao chama action_cancel; retorna plano validado.

        Returns:
            dict com chaves:
                status: EXECUTADO | NOOP | OK_RESERVA_FANTASMA |
                        FALHA_FURO_CONTABIL_REAL | FALHA_STATE_NAO_CANCELAVEL |
                        FALHA_STATE_INESPERADO | FALHA | DRY_RUN_* (espelhos)
                mo_id, name, state_antes, state_apos,
                consumo: {done, reservado, total} (G-MO-01 v6),
                consumo_total: float total (compat legacy),
                forcar_consumo (se aplicavel), motivo, tempo_ms, acao,
                erro (se houver).

        Raises:
            (nenhuma — condicoes de dado retornam status, nao raise).
        """
        inicio = time.time()
        r: Dict[str, Any] = {
            'mo_id': mo_id,
            'motivo': motivo,
            'forcar_consumo': forcar_consumo,
            'dry_run': dry_run,
            'acao': 'none',
        }

        # --- 1. Ler MO ---
        mo = self._ler_mo(mo_id)
        if not mo:
            r['status'] = 'FALHA'
            r['erro'] = f'MO {mo_id} nao existe no Odoo'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        state_antes = mo['state']
        r['name'] = mo.get('name')
        r['state_antes'] = state_antes
        r['company_id'] = mo['company_id'][0] if mo.get('company_id') else None
        r['product_id'] = mo['product_id'][0] if mo.get('product_id') else None
        r['qty_produced'] = mo.get('qty_produced')

        # --- 2. Idempotencia: ja cancelado? ---
        if state_antes == 'cancel':
            r['status'] = 'DRY_RUN_NOOP' if dry_run else 'NOOP'
            r['state_apos'] = 'cancel'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 3. State nao-cancelavel (done) ---
        if state_antes in STATES_NAO_CANCELAVEIS:
            r['status'] = ('DRY_RUN_FALHA_STATE_NAO_CANCELAVEL'
                           if dry_run else 'FALHA_STATE_NAO_CANCELAVEL')
            r['erro'] = (
                f"State '{state_antes}' nao e cancelavel via action_cancel. "
                f"Para reverter consumo, use mrp.unbuild via fluxo cross-skill "
                f"(ver memoria local Claude Code 'reaproveitar-semiacabado-orfao-mo-cancelada')."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 4. Guard G-MO-01 (v6): particao done vs reservado ---
        # Compat: aceita dict (novo) OU float (legacy — tratado como total puro).
        if consumo_total is None:
            consumo = self.medir_consumo_mo([mo_id]).get(
                mo_id, {'done': 0.0, 'reservado': 0.0, 'total': 0.0}
            )
        elif isinstance(consumo_total, dict):
            consumo = consumo_total
        else:  # float legacy — tratamos como 'total' sem particao (degrada para guard antigo)
            v = float(consumo_total)
            consumo = {'done': v, 'reservado': 0.0, 'total': v}
        r['consumo'] = {
            'done': round(consumo['done'], 3),
            'reservado': round(consumo['reservado'], 3),
            'total': round(consumo['total'], 3),
        }
        r['consumo_total'] = r['consumo']['total']  # compat

        done = consumo['done']
        reservado = consumo['reservado']

        # G-MO-01 REAL: done > TOL = consumo contabil efetivado -> furo
        if done > TOL_CONSUMO and not forcar_consumo:
            r['status'] = ('DRY_RUN_FALHA_FURO_CONTABIL_REAL'
                           if dry_run else 'FALHA_FURO_CONTABIL_REAL')
            r['erro'] = (
                f"G-MO-01: consumo done={done:.3f} > {TOL_CONSUMO} em "
                f"mrp.production {mo_id} ({mo.get('name')}). Cancelar com "
                f"consumo contabil efetivado (state='done') cria furo "
                f"(componentes consumidos sem produto finalizado). Use "
                f"mrp.unbuild via fluxo cross-skill (ver memoria "
                f"'reaproveitar-semiacabado-orfao-mo-cancelada' — memoria local Claude Code). Se "
                f"realmente precisar, passe forcar_consumo=True (NAO "
                f"recomendado, auditavel)."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 5. Dry-run: parou aqui ---
        # Diferencia limpo (reservado=0) de reserva fantasma (reservado>0).
        reserva_fantasma = reservado > TOL_CONSUMO
        if dry_run:
            r['status'] = ('DRY_RUN_OK_RESERVA_FANTASMA'
                           if reserva_fantasma else 'DRY_RUN_OK')
            r['state_apos_esperado'] = 'cancel'
            if reserva_fantasma:
                r['warning_reserva_fantasma'] = (
                    f'reservado={reservado:.3f} un (G-MO-01 v6). action_cancel '
                    f'libera reservas sem furo contabil (done={done:.3f}).'
                )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 6. Executar action_cancel ---
        try:
            self.odoo.execute_kw('mrp.production', 'action_cancel', [[mo_id]])
        except Exception as exc:
            r['status'] = 'FALHA'
            r['erro'] = str(exc)[:500]
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 7. G019-like: re-le state pos action_cancel ---
        mo_atualizada = self._ler_mo(mo_id)
        if mo_atualizada is None:
            # MO desapareceu apos action_cancel (config customizada com cascade
            # delete?). Conservador: tratar como sucesso — action_cancel nao
            # raised, registro nao mais existe = efeito equivalente a cancel.
            r['status'] = 'EXECUTADO'
            r['state_apos'] = 'cancel_deleted'
            r['acao'] = 'cancelled_and_deleted'
            logger.warning(
                f'MO {mo_id} ({mo.get("name")}) desapareceu apos action_cancel '
                f'(cascade delete? state pre={state_antes!r}). '
                f'Tratado como EXECUTADO.'
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        state_apos = mo_atualizada['state']
        r['state_apos'] = state_apos

        if state_apos == 'cancel':
            r['status'] = 'OK_RESERVA_FANTASMA' if reserva_fantasma else 'EXECUTADO'
            r['acao'] = 'cancelled'
            logger.info(
                f'MO {mo_id} ({mo.get("name")}) cancelada '
                f'(state {state_antes}->cancel'
                + (f', reserva_fantasma={reservado:.3f} un' if reserva_fantasma else '')
                + ')'
                + (f' motivo: {motivo}' if motivo else '')
            )
        else:
            r['status'] = 'FALHA_STATE_INESPERADO'
            r['erro'] = (
                f"action_cancel executado mas state pos='{state_apos}' "
                f"(esperado 'cancel'). Pode haver bloqueio (ex.: MO referenciada "
                f"por outra em producao, lock pessimista, regra customizada)."
            )

        r['tempo_ms'] = int((time.time() - inicio) * 1000)
        return r

    # ============================================================
    # Operacao atomica: concluir 1 MO (V7 — Produzir Tudo + Validar)
    # ============================================================

    _CAMPOS_MO_CONCLUIR = _CAMPOS_MO + ['qty_producing', 'lot_producing_id']

    @staticmethod
    def _ctx_company(company_id: Optional[int]) -> Dict[str, Any]:
        """Context multi-company derivado da PROPRIA MO (licao D-V30-1 GOTCHA 1:
        action_* com company do USUARIO opera na empresa errada)."""
        if not company_id:
            return {}
        return {'allowed_company_ids': [company_id], 'company_id': company_id}

    def _ler_raws_concluir(self, mo_id: int) -> List[Dict[str, Any]]:
        """Raws operaveis (state not in done/cancel) com count de move.lines."""
        raws = self.odoo.search_read(
            'stock.move',
            [['raw_material_production_id', '=', mo_id],
             ['state', 'not in', ['done', 'cancel']]],
            ['id', 'product_id', 'product_uom_qty', 'state', 'move_line_ids'],
        )
        for rm in raws:
            rm['_mls'] = list(rm.get('move_line_ids') or [])
        return raws

    def _resolver_lot_producing(
        self, nome_lote: str, product_id: int, company_id: Optional[int],
        ctx: Dict[str, Any], *, criar: bool = True,
    ) -> Optional[int]:
        """Busca stock.lot por (name, product_id, company_id); cria se ausente.

        Operador 'in' no name (gotcha stock_lot_search_bug: '=' retorna vazio
        intermitente) + filtro company_id (gotcha lote multi-empresa: mesmo
        nome existe em FB e LF).
        """
        domain: List[Any] = [
            ['name', 'in', [nome_lote]], ['product_id', '=', product_id],
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        ex = self.odoo.execute_kw(
            'stock.lot', 'search_read', [domain],
            {'fields': ['id'], 'context': ctx},
        )
        if ex:
            return ex[0]['id']
        if not criar:
            return None
        vals = {'name': nome_lote, 'product_id': product_id}
        if company_id:
            vals['company_id'] = company_id
        return self.odoo.execute_kw('stock.lot', 'create', [vals], {'context': ctx})

    def concluir_mo(
        self,
        mo_id: int,
        *,
        nome_lote: Optional[str] = None,
        motivo: str = '',
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Conclui 1 mrp.production (Produzir Tudo + Validar) via button_mark_done.

        Sequencia minerada do piloto industrializacao FB-LF (validada PROD
        2026-06-01 — docs/industrializacao-fb-lf/scripts/e2e_mo_lf_criar.py):
          1. action_assign (reservar componentes; idempotente)
          2. G-MO-06: raw sem move.line pos-assign -> BLOQUEIA (sem isso o
             mark_done cancela o raw = consumo parcial silencioso)
          3. lot_producing_id (se tracking lot/serial) + qty_producing =
             product_qty (Produzir Tudo — producao parcial fora do V7)
          4. G-MO-05: picked=True nas move.lines E nos moves dos raws
          5. button_mark_done (context skip_backorder) + wizard
             mrp.consumption.warning se aparecer
          6. G019-like: re-le state (esperado 'done')
          7. POS-CHECK G-MO-05: raw cancelado pos-done -> FALHA_PRODUCAO_FANTASMA

        IRREVERSIVEL: gera consumo contabil (SVL + account.move). MO done nao
        e cancelavel; reverter exige mrp.unbuild (cross-skill) com efeitos
        colaterais. Por isso single-only (sem batch).

        Args:
            mo_id: mrp.production.id alvo.
            nome_lote: nome do lote produzido (obrigatorio quando o produto
                tem tracking lot/serial E a MO ainda nao tem lot_producing_id;
                nunca inventado — decisao 2026-06-12).
            motivo: registrado para log/auditoria.
            dry_run: nao escreve; retorna plano com estado atual dos raws.

        Returns:
            dict com status (ver docstring do modulo, secao V7), mo_id, name,
            state_antes/state_apos, plano (dry-run), raws_apontados,
            raws_sem_ml, lote, tempo_ms, erro (se houver).

        Raises:
            (nenhuma — condicoes de dado retornam status, nao raise).
        """
        from app.odoo.utils.connection import is_cannot_marshal_none

        inicio = time.time()
        r: Dict[str, Any] = {
            'mo_id': mo_id,
            'motivo': motivo,
            'dry_run': dry_run,
            'acao': 'none',
        }

        # --- 1. Ler MO (campos de concluir) ---
        mos = self.odoo.search_read(
            'mrp.production', [['id', '=', mo_id]], list(self._CAMPOS_MO_CONCLUIR),
        )
        if not mos:
            r['status'] = 'FALHA'
            r['erro'] = f'MO {mo_id} nao existe no Odoo'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r
        mo = mos[0]

        state_antes = mo['state']
        company_id = mo['company_id'][0] if mo.get('company_id') else None
        product_id = mo['product_id'][0] if mo.get('product_id') else None
        r['name'] = mo.get('name')
        r['state_antes'] = state_antes
        r['company_id'] = company_id
        r['product_id'] = product_id
        r['product_qty'] = mo.get('product_qty')

        # --- 2. Idempotencia: ja concluida? ---
        if state_antes == 'done':
            r['status'] = 'DRY_RUN_NOOP' if dry_run else 'NOOP'
            r['state_apos'] = 'done'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 3. State nao-concluivel (cancel/draft) ---
        if state_antes not in STATES_CONCLUIVEIS:
            r['status'] = ('DRY_RUN_FALHA_STATE_NAO_CONCLUIVEL'
                           if dry_run else 'FALHA_STATE_NAO_CONCLUIVEL')
            if state_antes == 'draft':
                r['erro'] = (
                    f"State 'draft' exige action_confirm previo (confirme a MO "
                    f"no Odoo ou via fluxo proprio antes de concluir)."
                )
            else:
                r['erro'] = (
                    f"State '{state_antes}' nao e concluivel via "
                    f"button_mark_done (concluiveis: {STATES_CONCLUIVEIS})."
                )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        ctx = self._ctx_company(company_id)

        # --- 4. Premissas de plano (reads — validas em dry-run E write) ---
        tracking = 'none'
        if product_id:
            prods = self.odoo.execute_kw(
                'product.product', 'search_read',
                [[['id', '=', product_id]]],
                {'fields': ['tracking'], 'context': ctx},
            )
            tracking = prods[0].get('tracking') or 'none' if prods else 'none'
        r['tracking'] = tracking

        lot_atual = mo.get('lot_producing_id')
        lot_atual_id = lot_atual[0] if lot_atual else None
        precisa_lote = tracking in ('lot', 'serial')
        if precisa_lote and not lot_atual_id and not nome_lote:
            r['status'] = ('DRY_RUN_FALHA_LOTE_PRODUZIDO_AUSENTE'
                           if dry_run else 'FALHA_LOTE_PRODUZIDO_AUSENTE')
            r['erro'] = (
                f"Produto {product_id} tem tracking='{tracking}' e a MO nao tem "
                f"lot_producing_id. Informe nome_lote (--lote) — nunca inventado."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        raws = self._ler_raws_concluir(mo_id)
        raws_sem_ml_atual = [
            {'move_id': rm['id'],
             'produto': rm['product_id'][1] if rm.get('product_id') else '?',
             'qty': rm.get('product_uom_qty')}
            for rm in raws if not rm['_mls']
        ]

        # --- 5. Dry-run: plano com estado atual ---
        if dry_run:
            r['status'] = 'DRY_RUN_OK'
            r['state_apos_esperado'] = 'done'
            r['plano'] = {
                'passos': [
                    'action_assign', 'lot_producing/qty_producing',
                    'picked=True raws (G-MO-05)',
                    'button_mark_done (+wizard consumo)',
                    'G019-like state', 'POS-CHECK G-MO-05',
                ],
                'qty_producing': mo.get('product_qty'),
                'lote': (lot_atual[1] if lot_atual else nome_lote) if precisa_lote else None,
                'lote_sera_criado': bool(
                    precisa_lote and not lot_atual_id and nome_lote
                    and self._resolver_lot_producing(
                        nome_lote, product_id, company_id, ctx, criar=False,
                    ) is None
                ),
                'raws_total': len(raws),
                'raws_sem_ml_atual': raws_sem_ml_atual,
            }
            warnings = []
            if raws_sem_ml_atual:
                warnings.append(
                    f'{len(raws_sem_ml_atual)} raw(s) sem move.line no estado '
                    f'ATUAL — action_assign sera executado no real; se '
                    f'persistirem sem reserva, G-MO-06 bloqueia '
                    f'(manual_consumption ou saldo fora do location_src).'
                )
            if state_antes == 'progress':
                warnings.append(
                    "MO em 'progress': pode haver apontamento do operador no "
                    "chao de fabrica — concluir por fora conflita com o real."
                )
            if warnings:
                r['warnings'] = warnings
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 6. WRITE: action_assign (idempotente) ---
        try:
            self.odoo.execute_kw(
                'mrp.production', 'action_assign', [[mo_id]], {'context': ctx},
            )
        except Exception as exc:
            r['status'] = 'FALHA'
            r['erro'] = f'action_assign: {str(exc)[:400]}'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 7. G-MO-06: raw sem move.line pos-assign -> bloqueia ---
        raws = self._ler_raws_concluir(mo_id)
        raws_sem_ml = [
            {'move_id': rm['id'],
             'produto': rm['product_id'][1] if rm.get('product_id') else '?',
             'qty': rm.get('product_uom_qty')}
            for rm in raws if not rm['_mls']
        ]
        if raws_sem_ml:
            r['status'] = 'FALHA_COMPONENTE_SEM_RESERVA'
            r['raws_sem_ml'] = raws_sem_ml
            r['erro'] = (
                f"G-MO-06: {len(raws_sem_ml)} raw(s) sem move.line apos "
                f"action_assign — concluir os cancelaria silenciosamente "
                f"(consumo parcial). Causas tipicas: manual_consumption "
                f"(G-MO-02) ou saldo fora do location_src (G-MO-03; ver "
                f"memoria mo_componente_local_consumo — transferencia interna "
                f"resolve). Trate os componentes e rode novamente."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 8. Lote produzido + qty_producing (Produzir Tudo) ---
        try:
            vals_mo: Dict[str, Any] = {'qty_producing': mo.get('product_qty')}
            if precisa_lote:
                lot_id = lot_atual_id or self._resolver_lot_producing(
                    nome_lote, product_id, company_id, ctx,  # type: ignore[arg-type]
                )
                vals_mo['lot_producing_id'] = lot_id
                r['lote'] = {'id': lot_id, 'nome': lot_atual[1] if lot_atual else nome_lote}
            self.odoo.execute_kw(
                'mrp.production', 'write', [[mo_id], vals_mo], {'context': ctx},
            )
        except Exception as exc:
            r['status'] = 'FALHA'
            r['erro'] = f'lot/qty_producing: {str(exc)[:400]}'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 9. G-MO-05: picked=True em MLs + moves ANTES do mark_done ---
        raws_apontados = []
        try:
            for rm in raws:
                if rm['_mls']:
                    self.odoo.execute_kw(
                        'stock.move.line', 'write',
                        [rm['_mls'], {'picked': True}], {'context': ctx},
                    )
                    self.odoo.execute_kw(
                        'stock.move', 'write',
                        [[rm['id']], {'picked': True}], {'context': ctx},
                    )
                    raws_apontados.append(rm['id'])
        except Exception as exc:
            r['status'] = 'FALHA'
            r['erro'] = f'picked=True (G-MO-05): {str(exc)[:400]}'
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r
        r['raws_apontados'] = raws_apontados

        # --- 10. button_mark_done (+ wizard consumo) ---
        try:
            res = self.odoo.execute_kw(
                'mrp.production', 'button_mark_done', [[mo_id]],
                {'context': dict(ctx, skip_backorder=True)},
            )
            if isinstance(res, dict) and res.get('res_model') == 'mrp.consumption.warning':
                wiz = self.odoo.execute_kw(
                    'mrp.consumption.warning', 'create',
                    [{'mrp_production_ids': [(6, 0, [mo_id])]}], {'context': ctx},
                )
                self.odoo.execute_kw(
                    'mrp.consumption.warning', 'action_confirm', [[wiz]],
                    {'context': ctx},
                )
                r['wizard_consumo_confirmado'] = True
        except Exception as exc:
            # Unico artefato tolerado: retorno None do XML-RPC (helper T1.5).
            if not is_cannot_marshal_none(exc):
                r['status'] = 'FALHA'
                r['erro'] = f'button_mark_done: {str(exc)[:400]}'
                r['tempo_ms'] = int((time.time() - inicio) * 1000)
                return r

        # --- 11. G019-like: re-le state pos mark_done ---
        mo_pos = self._ler_mo(mo_id)
        state_apos = mo_pos['state'] if mo_pos else None
        r['state_apos'] = state_apos
        if state_apos != 'done':
            r['status'] = 'FALHA_STATE_INESPERADO'
            r['erro'] = (
                f"button_mark_done executado mas state pos='{state_apos}' "
                f"(esperado 'done'). Investigar no Odoo (wizard pendente, "
                f"regra customizada, qty_producing zerada)."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 12. POS-CHECK G-MO-05: raws consumiram de verdade? ---
        raws_pos = self.odoo.search_read(
            'stock.move',
            [['raw_material_production_id', '=', mo_id]],
            ['id', 'product_id', 'state', 'quantity'],
        )
        cancelados = [
            {'move_id': m['id'],
             'produto': m['product_id'][1] if m.get('product_id') else '?',
             'qty': m.get('quantity')}
            for m in raws_pos if m.get('state') == 'cancel'
        ]
        n_consumido = sum(
            1 for m in raws_pos
            if m.get('state') == 'done' and float(m.get('quantity') or 0) > TOL_CONSUMO
        )
        r['raws_consumidos'] = n_consumido
        if cancelados:
            r['status'] = 'FALHA_PRODUCAO_FANTASMA'
            r['raws_cancelados'] = cancelados
            r['erro'] = (
                f"POS-CHECK G-MO-05: {len(cancelados)} raw(s) CANCELADOS apos "
                f"mark_done — MO done SEM consumir (producao fantasma, SVL "
                f"value=0). NAO prosseguir; cirurgia manual necessaria "
                f"(MO ja esta done e nao e cancelavel)."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        r['status'] = 'EXECUTADO'
        r['acao'] = 'concluida'
        logger.info(
            f'MO {mo_id} ({mo.get("name")}) concluida '
            f'(state {state_antes}->done, {n_consumido} raws consumidos)'
            + (f' motivo: {motivo}' if motivo else '')
        )
        r['tempo_ms'] = int((time.time() - inicio) * 1000)
        return r

    # ============================================================
    # Composicao: cancelar MOs em massa por criterio
    # ============================================================

    def cancelar_mos_em_massa(
        self,
        *,
        # --- criterio de filtragem ---
        create_de: Optional[str] = None,  # 'YYYY-MM-DD' inclusivo
        create_ate: Optional[str] = None,  # 'YYYY-MM-DD' exclusivo
        states: Optional[List[str]] = None,  # default: cancelaveis
        empresas: Optional[List[int]] = None,  # default: [1,4,5] (FB,CD,LF)
        consumo: str = 'zero',  # 'zero' (default seguro) | 'qualquer'
        # --- limites / behavior ---
        max_n: int = 0,  # 0 = sem limite (cuidado)
        forcar_consumo: bool = False,  # default: bloqueia G-MO-01
        motivo: str = '',
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Cancela MOs em massa por criterio.

        Pattern de cancelar_mos.py: search_read com filtros, medir_consumo
        em batch (perf), filtrar por consumo zero (se modo), delegar
        cancelar_mo por MO. Resumo agregado.

        Args:
            create_de: 'YYYY-MM-DD' inclusivo (default sem filtro).
            create_ate: 'YYYY-MM-DD' exclusivo (default sem filtro).
            states: lista de states aceitos (default STATES_CANCELAVEIS).
            empresas: lista de company_id (default [1,4,5]).
            consumo: 'zero' (filtra MOs com consumo<=TOL_CONSUMO; SEGURO) ou
                'qualquer' (inclui MOs com consumo>0, requer forcar_consumo=True
                no service para nao falhar).
            max_n: limite N MOs (canary). 0 = sem limite.
            forcar_consumo: passa adiante para cancelar_mo (NAO RECOMENDADO).
            motivo: registrado em cada cancelar_mo individual.
            dry_run: nao chama action_cancel.

        Returns:
            dict:
                criterio: dict com args recebidos
                total_candidatas: N MOs apos filtro de consumo
                total_filtradas_por_consumo: N MOs excluidas (consumo>0 em modo zero)
                contagem_status: {status: N}
                resultados: [<dict de cada cancelar_mo>]
                tempo_total_ms: int
        """
        inicio = time.time()
        if states is None:
            states = list(STATES_CANCELAVEIS)
        if empresas is None:
            empresas = [1, 4, 5]

        # --- 0. Warning antecipado: consumo='qualquer' sem forcar_consumo ---
        if consumo == 'qualquer' and not forcar_consumo:
            logger.warning(
                "cancelar_mos_em_massa: consumo='qualquer' sem forcar_consumo=True. "
                "MOs com consumo > TOL_CONSUMO serao todas FALHA_FURO_CONTABIL "
                "(G-MO-01). Para realmente cancelar com consumo>0, passe "
                "forcar_consumo=True (NAO recomendado — use mrp.unbuild via "
                "fluxo cross-skill em vez disso)."
            )

        # --- 1. Buscar MOs candidatas ---
        domain: List = [
            ['state', 'in', states],
            ['company_id', 'in', empresas],
        ]
        if create_de:
            domain.append(['create_date', '>=', create_de])
        if create_ate:
            domain.append(['create_date', '<', create_ate])

        # H1 code-review fix: order server-side (FIFO por create_date)
        # evita Python sort de N candidatas em memoria; ainda assim
        # NAO usar limit=max_n aqui — max_n trim ocorre POS-filtro de
        # consumo (ver passo 3), nao pre-filtro (senao limitaria MOs
        # com consumo>0 antes do filtro zero e perderia candidatas reais).
        mos = self.odoo.search_read(
            'mrp.production', domain,
            ['id', 'name', 'state', 'create_date', 'company_id'],
            order='create_date asc',
        )
        logger.info(
            f'cancelar_mos_em_massa: {len(mos)} MOs pre-filtro de consumo '
            f'(criterio: states={states} empresas={empresas} '
            f'create_de={create_de} create_ate={create_ate})'
        )

        # --- 2. Medir consumo em batch (perf) ---
        # Dict {mo_id: {done, reservado, total}} desde 2026-05-27 v6.
        mo_ids = [m['id'] for m in mos]
        consumo_map = self.medir_consumo_mo(mo_ids)

        def _vazio():
            return {'done': 0.0, 'reservado': 0.0, 'total': 0.0}

        # --- 3. Filtrar por consumo (default 'zero') ---
        # 'zero' agora filtra apenas furo REAL (done > TOL). Reserva fantasma
        # (reservado > 0 mas done = 0) PASSA — action_cancel libera sem furo.
        filtradas_por_consumo = 0
        if consumo == 'zero':
            candidatas = [
                m for m in mos
                if consumo_map.get(m['id'], _vazio())['done'] <= TOL_CONSUMO
            ]
            filtradas_por_consumo = len(mos) - len(candidatas)
            if filtradas_por_consumo:
                logger.info(
                    f'cancelar_mos_em_massa: {filtradas_por_consumo} MOs excluidas '
                    f'por consumo done > {TOL_CONSUMO} (furo contabil real preservado)'
                )
        elif consumo == 'qualquer':
            candidatas = mos
        else:
            raise ValueError(f"consumo deve ser 'zero' ou 'qualquer' (recebeu {consumo!r})")

        # Ordenar por create_date (FIFO — mais antigas primeiro).
        candidatas.sort(key=lambda m: m.get('create_date') or '')
        if max_n > 0:
            candidatas = candidatas[:max_n]

        logger.info(f'cancelar_mos_em_massa: processando {len(candidatas)} MOs '
                    f'(dry_run={dry_run})')

        # --- 4. Delegar cancelar_mo para cada uma ---
        resultados: List[Dict[str, Any]] = []
        for i, mo in enumerate(candidatas, 1):
            r = self.cancelar_mo(
                mo['id'],
                motivo=motivo,
                forcar_consumo=forcar_consumo,
                consumo_total=consumo_map.get(mo['id'], _vazio()),
                dry_run=dry_run,
            )
            resultados.append(r)
            if i <= 3 or i == len(candidatas) or i % 50 == 0:
                logger.info(
                    f'[{i:4}/{len(candidatas)}] {r["status"]} '
                    f'{r.get("name", "?")} (state_antes={r.get("state_antes")})'
                )

        # --- 5. Resumo ---
        contagem: Dict[str, int] = defaultdict(int)
        for r in resultados:
            contagem[r['status']] += 1

        return {
            'criterio': {
                'create_de': create_de, 'create_ate': create_ate,
                'states': states, 'empresas': empresas, 'consumo': consumo,
                'max_n': max_n, 'forcar_consumo': forcar_consumo,
                'motivo': motivo, 'dry_run': dry_run,
            },
            'total_pre_filtro': len(mos),
            'total_candidatas': len(candidatas),
            'total_filtradas_por_consumo': filtradas_por_consumo,
            'contagem_status': dict(contagem),
            'resultados': resultados,
            'tempo_total_ms': int((time.time() - inicio) * 1000),
        }

    # ============================================================
    # Modos READ (CLAUDE.md §6.b — listar + detalhar do objeto)
    # ============================================================

    def listar_mos(
        self,
        *,
        create_de: Optional[str] = None,
        create_ate: Optional[str] = None,
        states: Optional[List[str]] = None,
        empresas: Optional[List[int]] = None,
        max_n: int = 0,
    ) -> Dict[str, Any]:
        """READ: lista MOs candidatas + classificacao por consumo (V6).

        Mesmos filtros de cancelar_mos_em_massa, mas SEM action_cancel. Cada
        item ganha rotulo `classificacao`:
            SEGURO            = done=0 e reservado=0
            RESERVA_FANTASMA  = done=0 e reservado>0 (action_cancel libera)
            FURO_REAL         = done>0 (exige mrp.unbuild)

        Returns:
            {
              criterio: dict,
              total: int,
              classificacao: {SEGURO|RESERVA_FANTASMA|FURO_REAL: N},
              itens: [{id, name, state, company_id, create_date,
                       classificacao, consumo:{done,reservado,total}}],
              tempo_ms: int,
            }
        """
        inicio = time.time()
        if states is None:
            states = list(STATES_CANCELAVEIS)
        if empresas is None:
            empresas = [1, 4, 5]

        domain: List = [
            ['state', 'in', states],
            ['company_id', 'in', empresas],
        ]
        if create_de:
            domain.append(['create_date', '>=', create_de])
        if create_ate:
            domain.append(['create_date', '<', create_ate])

        mos = self.odoo.search_read(
            'mrp.production', domain,
            ['id', 'name', 'state', 'create_date', 'company_id'],
            order='create_date asc',
        )
        if max_n > 0:
            mos = mos[:max_n]

        # Medir consumo em batch
        mo_ids = [m['id'] for m in mos]
        consumo_map = self.medir_consumo_mo(mo_ids)

        # Classificar e montar itens
        classificacao_count: Dict[str, int] = defaultdict(int)
        itens: List[Dict[str, Any]] = []
        for m in mos:
            c = consumo_map.get(m['id'], {'done': 0.0, 'reservado': 0.0, 'total': 0.0})
            if c['done'] > TOL_CONSUMO:
                cls = 'FURO_REAL'
            elif c['reservado'] > TOL_CONSUMO:
                cls = 'RESERVA_FANTASMA'
            else:
                cls = 'SEGURO'
            classificacao_count[cls] += 1
            itens.append({
                'id': m['id'],
                'name': m['name'],
                'state': m['state'],
                'company_id': m['company_id'][0] if m.get('company_id') else None,
                'company_name': m['company_id'][1] if m.get('company_id') else None,
                'create_date': m.get('create_date'),
                'classificacao': cls,
                'consumo': {
                    'done': round(c['done'], 3),
                    'reservado': round(c['reservado'], 3),
                    'total': round(c['total'], 3),
                },
            })

        return {
            'criterio': {
                'create_de': create_de, 'create_ate': create_ate,
                'states': states, 'empresas': empresas, 'max_n': max_n,
            },
            'total': len(itens),
            'classificacao': dict(classificacao_count),
            'itens': itens,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    # ============================================================
    # Audit pre/pos (opt-in — costoso, +1-2s/MO)
    # ============================================================

    _AUDIT_FIELDS_MOVE = (
        'id', 'state', 'product_id', 'product_uom_qty', 'quantity', 'picked',
        'location_id', 'move_line_ids',
    )

    def _snapshot_mo(self, mo_id: int) -> Optional[Dict[str, Any]]:
        """Snapshot minimo de MO + raws + finished + MLs + quants origem.

        Para audit pre/pos action_cancel. Retorna None se MO nao existe.
        """
        mos = self.odoo.search_read(
            'mrp.production', [['id', '=', mo_id]],
            ['id', 'name', 'state', 'reservation_state',
             'qty_produced', 'move_raw_ids', 'move_finished_ids'],
        )
        if not mos:
            return None
        mo = mos[0]

        all_move_ids = list(mo['move_raw_ids']) + list(mo['move_finished_ids'])
        moves = self.odoo.search_read(
            'stock.move', [['id', 'in', all_move_ids]],
            list(self._AUDIT_FIELDS_MOVE),
        ) if all_move_ids else []
        # Conta MLs por move (sem ler MLs detalhadas — economiza RPC).
        mls_count = sum(len(m.get('move_line_ids') or []) for m in moves)

        # Quants nas origens dos raws (para detectar liberacao de reservas).
        quant_keys = set()
        for m in moves:
            if m.get('product_id') and m.get('location_id'):
                rid = m.get('raw_material_production_id') if hasattr(m, 'get') else None
                # raw_material_production_id NAO esta em _AUDIT_FIELDS_MOVE;
                # presenca de raws_ids no MO ja delimitou.
                _ = rid
                quant_keys.add((m['product_id'][0], m['location_id'][0]))
        quants: List[Dict[str, Any]] = []
        for (pid, loc_id) in quant_keys:
            quants.extend(self.odoo.search_read(
                'stock.quant',
                [['product_id', '=', pid], ['location_id', '=', loc_id]],
                ['product_id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'],
            ))

        return {
            'mo': mo,
            'moves_raw': [m for m in moves if m['id'] in mo['move_raw_ids']],
            'moves_finished': [m for m in moves if m['id'] in mo['move_finished_ids']],
            'mls_count': mls_count,
            'quants_origem': quants,
        }

    @staticmethod
    def _diff_snapshots(pre: Dict[str, Any], pos: Dict[str, Any]) -> Dict[str, Any]:
        """Diff sucinto pre/pos para o JSON de auditoria."""
        d = {
            'mo_state': {
                'pre': pre['mo']['state'],
                'pos': pos['mo']['state'],
            },
            'reservation_state': {
                'pre': pre['mo'].get('reservation_state'),
                'pos': pos['mo'].get('reservation_state'),
            },
            'mls_count': {'pre': pre['mls_count'], 'pos': pos['mls_count']},
            'raws_states': {
                'pre': sorted([(m['id'], m['state'], m.get('quantity', 0)) for m in pre['moves_raw']]),
                'pos': sorted([(m['id'], m['state'], m.get('quantity', 0)) for m in pos['moves_raw']]),
            },
            'finished_states': {
                'pre': sorted([(m['id'], m['state']) for m in pre['moves_finished']]),
                'pos': sorted([(m['id'], m['state']) for m in pos['moves_finished']]),
            },
            'quants_reserved_delta': [],
        }
        pre_q = {
            (q['product_id'][0] if q.get('product_id') else None,
             q['lot_id'][0] if q.get('lot_id') else None): float(q.get('reserved_quantity') or 0)
            for q in pre['quants_origem']
        }
        pos_q = {
            (q['product_id'][0] if q.get('product_id') else None,
             q['lot_id'][0] if q.get('lot_id') else None): float(q.get('reserved_quantity') or 0)
            for q in pos['quants_origem']
        }
        for k, v_pre in pre_q.items():
            v_pos = float(pos_q.get(k, 0))
            if abs(v_pre - v_pos) > 0.0001:
                d['quants_reserved_delta'].append({
                    'product_id': k[0], 'lot_id': k[1],
                    'reserved_pre': v_pre, 'reserved_pos': v_pos,
                    'delta': v_pos - v_pre,
                })
        return d

    def cancelar_mo_com_audit(
        self,
        mo_id: int,
        *,
        motivo: str = '',
        forcar_consumo: bool = False,
        consumo_total: Optional[Union[Dict[str, float], float]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """cancelar_mo + snapshots pre/pos + diff (opt-in costoso).

        Wrapper que captura estado completo antes e depois do action_cancel,
        para auditoria. Em dry-run, captura so o snapshot pre. Custo: +1-2s
        por MO (queries adicionais). Use para single mode ou batches pequenos.
        """
        snap_pre = self._snapshot_mo(mo_id)
        out = self.cancelar_mo(
            mo_id, motivo=motivo, forcar_consumo=forcar_consumo,
            consumo_total=consumo_total, dry_run=dry_run,
        )
        out['audit'] = {'pre': snap_pre}
        if not dry_run and snap_pre is not None and out.get('status') in (
            'EXECUTADO', 'OK_RESERVA_FANTASMA', 'NOOP'
        ):
            snap_pos = self._snapshot_mo(mo_id)
            out['audit']['pos'] = snap_pos
            if snap_pos is not None:
                out['audit']['diff'] = self._diff_snapshots(snap_pre, snap_pos)
        return out

    def concluir_mo_com_audit(
        self,
        mo_id: int,
        *,
        nome_lote: Optional[str] = None,
        motivo: str = '',
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """concluir_mo + snapshots pre/pos + diff (opt-in costoso, +1-2s).

        Espelha cancelar_mo_com_audit. Em dry-run, captura so o snapshot pre.
        """
        snap_pre = self._snapshot_mo(mo_id)
        out = self.concluir_mo(
            mo_id, nome_lote=nome_lote, motivo=motivo, dry_run=dry_run,
        )
        out['audit'] = {'pre': snap_pre}
        if not dry_run and snap_pre is not None and out.get('status') in (
            'EXECUTADO', 'NOOP',
        ):
            snap_pos = self._snapshot_mo(mo_id)
            out['audit']['pos'] = snap_pos
            if snap_pos is not None:
                out['audit']['diff'] = self._diff_snapshots(snap_pre, snap_pos)
        return out

    def detalhar_mo(self, mo_id: int) -> Dict[str, Any]:
        """READ: detalhamento completo de 1 MO (raws + finished + MLs + consumo).

        Sem WRITE — para investigacao individual antes/depois de operar.

        Returns:
            {id, name, state, company, product, product_qty, qty_produced,
             reservation_state, classificacao, consumo:{done,reservado,total},
             details:{
                raws:[{id, product, state, planejado, quantity, picked, MLs}],
                finished:[{id, product, state, planejado, quantity, picked}],
                date_start, date_deadline, date_finished, origin, bom_id,
             },
             tempo_ms}
            Se MO inexistente: {'erro': '...'}
        """
        inicio = time.time()
        mos = self.odoo.search_read(
            'mrp.production', [['id', '=', mo_id]],
            ['id', 'name', 'state', 'company_id', 'product_id', 'product_qty',
             'qty_produced', 'reservation_state', 'date_start', 'date_deadline',
             'date_finished', 'origin', 'bom_id',
             'move_raw_ids', 'move_finished_ids'],
        )
        if not mos:
            return {'erro': f'MO {mo_id} nao existe', 'tempo_ms': int((time.time() - inicio) * 1000)}
        mo = mos[0]

        # Consumo + classificacao
        c = self.medir_consumo_mo([mo_id]).get(
            mo_id, {'done': 0.0, 'reservado': 0.0, 'total': 0.0}
        )
        if c['done'] > TOL_CONSUMO:
            cls = 'FURO_REAL'
        elif c['reservado'] > TOL_CONSUMO:
            cls = 'RESERVA_FANTASMA'
        else:
            cls = 'SEGURO'

        # Moves (raws + finished)
        all_move_ids = list(mo['move_raw_ids']) + list(mo['move_finished_ids'])
        moves = self.odoo.search_read(
            'stock.move', [['id', 'in', all_move_ids]],
            ['id', 'state', 'product_id', 'product_uom_qty', 'quantity',
             'picked', 'location_id', 'location_dest_id', 'move_line_ids',
             'raw_material_production_id'],
        ) if all_move_ids else []
        move_by_id = {m['id']: m for m in moves}

        # Move lines (batch)
        all_ml_ids: List[int] = []
        for m in moves:
            all_ml_ids.extend(m.get('move_line_ids') or [])
        mls = self.odoo.search_read(
            'stock.move.line', [['id', 'in', all_ml_ids]],
            ['id', 'state', 'quantity', 'picked', 'location_id', 'lot_id', 'move_id'],
        ) if all_ml_ids else []
        mls_by_move: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for ml in mls:
            mv = ml.get('move_id')
            if mv:
                mls_by_move[mv[0]].append({
                    'id': ml['id'],
                    'state': ml['state'],
                    'quantity': ml.get('quantity', 0),
                    'picked': ml.get('picked'),
                    'location': ml['location_id'][1] if ml.get('location_id') else None,
                    'lot': ml['lot_id'][1] if ml.get('lot_id') else None,
                })

        def _fmt_move(m: Dict[str, Any]) -> Dict[str, Any]:
            return {
                'id': m['id'],
                'product_id': m['product_id'][0] if m.get('product_id') else None,
                'product_name': m['product_id'][1] if m.get('product_id') else None,
                'state': m['state'],
                'planejado': m.get('product_uom_qty', 0),
                'quantity': m.get('quantity', 0),
                'picked': m.get('picked'),
                'location': m['location_id'][1] if m.get('location_id') else None,
                'location_dest': m['location_dest_id'][1] if m.get('location_dest_id') else None,
                'move_lines': mls_by_move.get(m['id'], []),
            }

        raws = [_fmt_move(move_by_id[i]) for i in mo['move_raw_ids'] if i in move_by_id]
        finished = [_fmt_move(move_by_id[i]) for i in mo['move_finished_ids'] if i in move_by_id]

        return {
            'id': mo['id'],
            'name': mo['name'],
            'state': mo['state'],
            'company_id': mo['company_id'][0] if mo.get('company_id') else None,
            'company_name': mo['company_id'][1] if mo.get('company_id') else None,
            'product_id': mo['product_id'][0] if mo.get('product_id') else None,
            'product_name': mo['product_id'][1] if mo.get('product_id') else None,
            'product_qty': mo.get('product_qty'),
            'qty_produced': mo.get('qty_produced'),
            'reservation_state': mo.get('reservation_state'),
            'classificacao': cls,
            'consumo': {
                'done': round(c['done'], 3),
                'reservado': round(c['reservado'], 3),
                'total': round(c['total'], 3),
            },
            'details': {
                'date_start': mo.get('date_start'),
                'date_deadline': mo.get('date_deadline'),
                'date_finished': mo.get('date_finished'),
                'origin': mo.get('origin'),
                'bom_id': mo['bom_id'][1] if mo.get('bom_id') else None,
                'raws': raws,
                'finished': finished,
            },
            'tempo_ms': int((time.time() - inicio) * 1000),
        }
