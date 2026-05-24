"""StockMOService — operacoes de escrita em mrp.production (Manufacturing Orders).

Primitiva REUTILIZAVEL para CANCELAR MO no Odoo (mrp.production.action_cancel).

V1 (2026-05-24): unico atomo demanda-driven (skills nascem de casos reais):
- cancelar_mo(mo_id, motivo='', forcar_consumo=False, dry_run=False)
  - Wrapper sobre action_cancel + re-le state pos (G019-like pattern)
  - Guard G-MO-01: consumo_total > 0 -> bloqueia (FALHA_FURO_CONTABIL)
  - Idempotencia: state pre='cancel' -> NOOP (validado AO VIVO 2026-05-24)
- cancelar_mos_em_massa(criterio, max_n=0, dry_run=False)
  - Composicao sobre cancelar_mo. Filtra MOs por criterio (create_date range,
    states, empresas, consumo zero|qualquer), mede consumo em batch (perf),
    delega cancelar_mo individual.

Atomos PREVISTOS sem demanda (NAO implementar — feedback-skills-demanda-driven):
- criar_mo: sem demanda real isolada (pipeline cria via Odoo)
- alterar_mo: caso real existe mas e fluxo cross-skill (Skill 2 transfer +
  write em stock.move). Ver memoria [[mo_componente_local_consumo]].

Gotchas-invariante codificados:
- G-MO-01: consumo_total > 0 = FURO CONTABIL -> bloqueia cancelamento.
  Operador deve usar mrp.unbuild via fluxo cross-skill se precisar reverter
  consumo. Ver [[reaproveitar-semiacabado-orfao-mo-cancelada]] §3.
- G-MO-02: manual_consumption=True nao reserva via action_assign. NAO
  relevante para cancelar (action_cancel ignora reservas/picked). Relevante
  para criar/alterar (nao cobertos em V1).
- G-MO-03: componente em local errado (Indisponivel/Estoque vs location_src
  declarado). Nao relevante para cancelar (nao toca componentes).
- G-MO-04: picked=True em to_close/done — herdado de Skill 2.4 G026.
  action_cancel e seguro com picked (nao mexe em quants existentes).

Helpers:
- medir_consumo_mo(mo_ids): soma stock.move.quantity (state != 'cancel') por
  raw_material_production_id. Tolerancia > 0.0001 (mesma de cancelar_mos.py
  e 14_cancelar_mos_antigas_fb.py).

Status canonicos (output['status']):
- EXECUTADO — state pos='cancel' (action_cancel teve efeito)
- NOOP — state pre='cancel' (idempotente, action_cancel chamado mesmo assim)
- FALHA_FURO_CONTABIL — consumo_total > 0 e forcar_consumo=False (default)
- FALHA_STATE_NAO_CANCELAVEL — state pre='done' (nao tem como reverter sem unbuild)
- FALHA_STATE_INESPERADO — state pos != 'cancel' (chamado mas nao cancelou)
- FALHA — excecao generica
- DRY_RUN_OK | DRY_RUN_NOOP | DRY_RUN_FALHA_FURO_CONTABIL | DRY_RUN_FALHA_STATE_NAO_CANCELAVEL

Spec: consolidacao de scripts cancelar_mos.py + 14_cancelar_mos_antigas_fb.py
(inventario 2026-05). Validado AO VIVO 2026-05-24 (10.000 MOs FB / 17 CD /
3367 LF, idempotencia action_cancel em state=cancel = True sem erro).
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Tolerancia para considerar consumo > 0 (mesma dos scripts-fonte).
TOL_CONSUMO = 0.0001

# States em que cancelar MO faz sentido (pre).
STATES_CANCELAVEIS = ('draft', 'confirmed', 'progress', 'to_close')

# States bloqueados (nao da pra reverter sem unbuild).
STATES_NAO_CANCELAVEIS = ('done',)

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

    def medir_consumo_mo(self, mo_ids: List[int]) -> Dict[int, float]:
        """Soma stock.move.quantity (state != cancel) dos componentes por MO.

        Pattern de cancelar_mos.py e 14_cancelar_mos_antigas_fb.py. Util para:
        - Guard G-MO-01: filtrar MOs com consumo=0 antes de cancelar em massa.
        - Auditoria: relatar consumo de cada MO no log.

        Returns:
            {mo_id: consumo_total (float)}. MOs sem moves retornam 0.0.
        """
        if not mo_ids:
            return {}
        consumo: Dict[int, float] = defaultdict(float)
        for ch in self._chunks(mo_ids):
            mvs = self.odoo.search_read(
                'stock.move',
                [['raw_material_production_id', 'in', list(ch)],
                 ['state', '!=', 'cancel']],
                ['raw_material_production_id', 'quantity'],
            )
            for m in mvs:
                rid = m.get('raw_material_production_id')
                if rid:
                    consumo[rid[0]] += float(m.get('quantity') or 0)
        # Garante chave para TODAS as mo_ids (mesmo sem moves = 0.0).
        return {mid: float(consumo.get(mid, 0.0)) for mid in mo_ids}

    # ============================================================
    # Operacao atomica: cancelar 1 MO
    # ============================================================

    def cancelar_mo(
        self,
        mo_id: int,
        *,
        motivo: str = '',
        forcar_consumo: bool = False,
        consumo_total: Optional[float] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Cancela 1 mrp.production via action_cancel com guards G-MO-*.

        Args:
            mo_id: mrp.production.id alvo.
            motivo: registrado apenas para log/auditoria (Odoo nao tem
                campo nativo para motivo de cancelamento).
            forcar_consumo: se True, IGNORA o guard G-MO-01 (consumo>0).
                NAO RECOMENDADO — use mrp.unbuild via cross-skill se precisar
                reverter consumo. Mantido para casos extremos auditados.
            consumo_total: consumo_total ja calculado (opcional). Quando
                informado, evita re-query (uso em cancelar_mos_em_massa).
                Quando None, mede via medir_consumo_mo (custa 1 RPC extra).
            dry_run: nao chama action_cancel; retorna plano validado.

        Returns:
            dict com chaves:
                status: EXECUTADO | NOOP | FALHA_FURO_CONTABIL |
                        FALHA_STATE_NAO_CANCELAVEL | FALHA_STATE_INESPERADO |
                        FALHA | DRY_RUN_* (espelhos com DRY_RUN_ prefix)
                mo_id, name, state_antes, state_apos, consumo_total,
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
                f"(ver memoria 'reaproveitar-semiacabado-orfao-mo-cancelada')."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 4. Guard G-MO-01: consumo > 0 = FURO CONTABIL ---
        if consumo_total is None:
            consumo_total = self.medir_consumo_mo([mo_id]).get(mo_id, 0.0)
        r['consumo_total'] = round(consumo_total, 3)

        if consumo_total > TOL_CONSUMO and not forcar_consumo:
            r['status'] = ('DRY_RUN_FALHA_FURO_CONTABIL'
                           if dry_run else 'FALHA_FURO_CONTABIL')
            r['erro'] = (
                f"G-MO-01: consumo_total={consumo_total:.3f} > {TOL_CONSUMO} "
                f"em mrp.production {mo_id} ({mo.get('name')}). "
                f"Cancelar com consumo > 0 cria furo contabil (componentes "
                f"consumidos sem produto finalizado). Use mrp.unbuild via "
                f"fluxo cross-skill (ver memoria "
                f"'reaproveitar-semiacabado-orfao-mo-cancelada'). "
                f"Se realmente precisar, passe forcar_consumo=True (NAO "
                f"recomendado, auditavel)."
            )
            r['tempo_ms'] = int((time.time() - inicio) * 1000)
            return r

        # --- 5. Dry-run: parou aqui ---
        if dry_run:
            r['status'] = 'DRY_RUN_OK'
            r['state_apos_esperado'] = 'cancel'
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
            r['status'] = 'EXECUTADO'
            r['acao'] = 'cancelled'
            logger.info(
                f'MO {mo_id} ({mo.get("name")}) cancelada '
                f'(state {state_antes}->cancel)'
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
        mo_ids = [m['id'] for m in mos]
        consumo_map = self.medir_consumo_mo(mo_ids)

        # --- 3. Filtrar por consumo (default 'zero') ---
        filtradas_por_consumo = 0
        if consumo == 'zero':
            candidatas = [m for m in mos if consumo_map.get(m['id'], 0) <= TOL_CONSUMO]
            filtradas_por_consumo = len(mos) - len(candidatas)
            if filtradas_por_consumo:
                logger.info(
                    f'cancelar_mos_em_massa: {filtradas_por_consumo} MOs excluidas '
                    f'por consumo>{TOL_CONSUMO} (preservadas)'
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
                consumo_total=consumo_map.get(mo['id'], 0.0),
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
