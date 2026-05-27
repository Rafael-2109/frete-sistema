"""CadastroFiscalAuditService — pre-flight de auditoria de cadastro fiscal
para faturamento/inventario no Odoo (delegado pela Skill 8 faturando-odoo).

Perfil V1: 'inventario' (uso pela Skill 8 + script 09 + scripts ad-hoc).
Roadmap perfis: 'venda-cliente' (V2), 'compras-importacao' (V3+).

Gotchas cobertos V1 (perfil inventario):
- G017 (NCM ausente)        — BLOQUEIO ('strict') ou WARN ('warn'). NCM=False
                              gera cstat=225 SEFAZ.
- G018 (weight=0)            — WARN. Fallback no picking F5b->F5c, nao bloqueia
                              mais (fix v2 inventario 2026-05).
- G035 (barcode invalido)    — BLOQUEIO ou AUTO-FIX se `auto_corrigir_barcode=True`
                              + `dry_run=False`. cstat=225 SEFAZ.
- G038 (l10n_br_origem       — BLOQUEIO. l10n_br_origem in (False, None, '')
   ausente) — NOVO v22+        produz modal Odoo "Aviso: Produtos sem Origem" que
                              bloqueia transmissao SEFAZ. Playwright nao trata o
                              modal, gerando loop silencioso 15× sem efeito.
                              Descoberto em retry pipeline INVENTARIO_2026_05
                              (produto 104000046 CORANTE VERMELHO, 2026-05-27).
                              SEM AUTO-FIX — operador deve setar manualmente
                              (0=Nacional, 1=Estr. importacao, 2=Estr. mercado
                              interno, ...).
- G014 (lote vencido)        — WARN. Resolvido on-the-fly em ETAPA B do
                              faturamento (transfere para lote novo via Skill 2).
- D-OPS-2 (duplicacao        — BLOQUEIO. Pre-flight checa AjusteEstoqueInventario
   pipeline ativa)             com mesmo cod+company em fase F5a..F5e.
- D-OPS-3 (tracking='none')  — INFO. Apos fix Skill 2 v14b (D-OPS-5) aceita
                              quants sem lote; antes era WARN. Mantido como
                              INFO para visibilidade.

Service READ-only por default; WRITE so' com `auto_corrigir_barcode=True` +
`dry_run=False` (limpa product.barcode dos produtos com G035).

Spec: consolidacao das validacoes que vivem em
`scripts/inventario_2026_05/09_executar_onda1_bulk.py` (`validar_cadastro_fiscal`
+ pre-checks D-OPS no codigo morto) + `app/odoo/utils/gtin_validator.py`.
Capinado em 2026-05-25 v14b (sessao do orquestrador-Odoo).
"""
import logging
import time
from typing import Any, Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.gtin_validator import find_invalid_barcodes
from app.utils.timezone import agora_utc

logger = logging.getLogger(__name__)

# Fases de pipeline da Skill 8 (faturando-odoo). Ajuste pendente eh' qualquer
# ajuste com status APROVADO/PROPOSTO ou EXECUTADO em fase F5a..F5e (ainda
# nao FINALIZADO). Re-criar picking sobre cods nesse estado e' D-OPS-2.
FASES_PIPELINE_ATIVA = (
    'F5a_PICKING_CRIADO',
    'F5b_VALIDADO',
    'F5c_LIBERADO',
    'F5d_INVOICE_CRIADA',
    'F5e_SEFAZ_OK',
)

# Statuses de AjusteEstoqueInventario que representam vida (nao reprocessado/cancelado).
STATUS_ATIVOS = ('APROVADO', 'PROPOSTO', 'EXECUTADO')


class CadastroFiscalAuditService:
    """Pre-flight de cadastro fiscal + duplicacao pipeline (perfil inventario V1)."""

    def __init__(self, odoo=None, db_session=None):
        """
        Args:
            odoo: conexao OdooConnection (default = get_odoo_connection()).
            db_session: SQLAlchemy session para verificar AjusteEstoqueInventario
                (default = None; D-OPS-2 SO' funciona se passado).
        """
        self.odoo = odoo or get_odoo_connection()
        self.db_session = db_session

    # ============================================================
    # Resolvedores de entrada (3 formas mutuamente exclusivas)
    # ============================================================

    def _resolver_produtos(
        self,
        *,
        produto_ids: Optional[List[int]] = None,
        cods_produto: Optional[List[str]] = None,
        ciclo: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Resolve produtos a auditar via 1 das 3 formas: ids, cods, ciclo.

        Returns:
            Lista de dicts {id, default_code, ciclo?, company_id?}.
            ciclo/company_id presentes apenas quando entrada via `ciclo`.

        Raises:
            ValueError: nenhuma forma fornecida OU mais de uma OU ciclo
                fornecido sem db_session.
        """
        formas = [produto_ids, cods_produto, ciclo]
        nao_none = sum(1 for f in formas if f)
        if nao_none == 0:
            raise ValueError(
                'Forneca uma forma: produto_ids OU cods_produto OU ciclo.'
            )
        if nao_none > 1:
            raise ValueError(
                'Formas mutuamente exclusivas — forneca apenas uma.'
            )

        if ciclo:
            if self.db_session is None:
                raise ValueError(
                    'auditar por ciclo exige db_session; passe no construtor '
                    '(CadastroFiscalAuditService(odoo, db_session=db.session)).'
                )
            from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
            ajustes = self.db_session.query(AjusteEstoqueInventario).filter(
                AjusteEstoqueInventario.ciclo == ciclo,
                AjusteEstoqueInventario.status.in_(STATUS_ATIVOS),
            ).all()
            if not ajustes:
                return []
            cods = sorted({a.cod_produto for a in ajustes})
            ciclo_company_map = {a.cod_produto: a.company_id for a in ajustes}
            prods = self.odoo.search_read(
                'product.product', [['default_code', 'in', cods]],
                ['id', 'default_code'],
            )
            out = []
            for p in prods:
                cod = p.get('default_code')
                out.append({
                    'id': p['id'],
                    'default_code': cod,
                    'ciclo': ciclo,
                    'company_id': ciclo_company_map.get(cod),
                })
            # Cods sem product correspondente — reportar como faltando
            cods_resolvidos = {p.get('default_code') for p in prods}
            for cod in cods:
                if cod not in cods_resolvidos:
                    out.append({
                        'id': None,
                        'default_code': cod,
                        'ciclo': ciclo,
                        'company_id': ciclo_company_map.get(cod),
                        '_erro_resolucao': f'cod {cod!r} sem product.product correspondente',
                    })
            return out

        if cods_produto:
            prods = self.odoo.search_read(
                'product.product', [['default_code', 'in', list(cods_produto)]],
                ['id', 'default_code'],
            )
            cods_resolvidos = {p.get('default_code') for p in prods}
            out = [{'id': p['id'], 'default_code': p.get('default_code')} for p in prods]
            for cod in cods_produto:
                if cod not in cods_resolvidos:
                    out.append({
                        'id': None,
                        'default_code': cod,
                        '_erro_resolucao': f'cod {cod!r} sem product.product',
                    })
            return out

        # produto_ids
        prods = self.odoo.read('product.product', list(produto_ids), ['default_code'])
        return [{'id': p['id'], 'default_code': p.get('default_code')} for p in prods]

    # ============================================================
    # Checks individuais (perfil inventario V1)
    # ============================================================

    def _check_ncm_weight_tracking(
        self, produto_ids: List[int],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """G017 (NCM), G018 (weight=0), G038 (l10n_br_origem ausente — v22+),
        G007 (standard_price=0 — NOVO v24+ pre-flight),
        l10n_br_tipo_produto ausente (NOVO v24+ — BLOQUEIO SEFAZ),
        D-OPS-3 (tracking='none').

        Returns:
            {
                'ncm_faltando': [{id, default_code, name}],
                'weight_zero': [{id, default_code, name}],
                'origem_ausente': [{id, default_code, name, gotcha: 'G038'}],
                'standard_price_zero': [{id, default_code, name, gotcha: 'G007',
                                          standard_price: float}],  # NOVO v24+
                'tipo_produto_ausente': [{id, default_code, name,
                                           gotcha: 'l10n_br_tipo_produto',
                                           l10n_br_tipo_produto: value}],  # NOVO v24+
                'tracking_none': [{id, default_code, name}],
            }
        """
        if not produto_ids:
            return {
                'ncm_faltando': [], 'weight_zero': [],
                'origem_ausente': [], 'standard_price_zero': [],
                'tipo_produto_ausente': [], 'tracking_none': [],
            }
        prods = self.odoo.read(
            'product.product', produto_ids,
            ['default_code', 'name', 'l10n_br_ncm_id', 'weight', 'tracking',
             'l10n_br_origem', 'standard_price', 'l10n_br_tipo_produto'],
        )
        ncm_faltando: List[Dict] = []
        weight_zero: List[Dict] = []
        origem_ausente: List[Dict] = []
        standard_price_zero: List[Dict] = []
        tipo_produto_ausente: List[Dict] = []
        tracking_none: List[Dict] = []
        for p in prods:
            base = {'id': p['id'], 'default_code': p.get('default_code'),
                    'name': (p.get('name') or '')[:60]}
            if not p.get('l10n_br_ncm_id'):
                ncm_faltando.append({**base, 'gotcha': 'G017'})
            if float(p.get('weight') or 0) <= 0:
                weight_zero.append({**base, 'gotcha': 'G018', 'weight': float(p.get('weight') or 0)})
            # G038 v22+: l10n_br_origem ausente bloqueia transmissao SEFAZ
            # via modal "Aviso: Produtos sem Origem" (Playwright nao trata).
            # False/None/'' = ausente. '0' (Nacional), '1'..'8' = OK.
            origem_val = p.get('l10n_br_origem')
            if not origem_val:
                origem_ausente.append({**base, 'gotcha': 'G038',
                                        'l10n_br_origem': origem_val})
            # G007 v24+ pre-flight: standard_price=0 nao bloqueia SEFAZ direto
            # (runtime corrigir_price_zero_em_invoice fallback 0.01), mas
            # ajustes com std_price=0 ficam com vUnCom=0.01 esquisito — WARN
            # para que operador cadastre custo medio real ANTES do bulk.
            std_price = float(p.get('standard_price') or 0)
            if std_price <= 0:
                standard_price_zero.append({**base, 'gotcha': 'G007',
                                             'standard_price': std_price})
            # l10n_br_tipo_produto v24+ pre-flight: campo SEFAZ obrigatorio
            # para muitas operacoes (servicos, industrializacao, etc.).
            # Vazio/False = BLOQUEIO. Valores validos sao strings ('01'-'09')
            # mapeados conforme Tabela CIEL IT.
            tipo_prod_val = p.get('l10n_br_tipo_produto')
            if not tipo_prod_val:
                tipo_produto_ausente.append({**base,
                    'gotcha': 'l10n_br_tipo_produto',
                    'l10n_br_tipo_produto': tipo_prod_val})
            if (p.get('tracking') or 'none') == 'none':
                tracking_none.append({**base, 'gotcha': 'D-OPS-3', 'tracking': 'none'})
        return {
            'ncm_faltando': ncm_faltando,
            'weight_zero': weight_zero,
            'origem_ausente': origem_ausente,
            'standard_price_zero': standard_price_zero,
            'tipo_produto_ausente': tipo_produto_ausente,
            'tracking_none': tracking_none,
        }

    def _check_barcode_invalido(
        self, produto_ids: List[int],
        auto_corrigir: bool, dry_run: bool,
    ) -> Dict[str, Any]:
        """G035 — barcode invalido GTIN. Auto-fix opcional.

        Returns:
            {
                'barcode_invalido': [{id, default_code, barcode}],
                'acao_aplicada': Optional[{tipo: 'clear_barcode', count: N}],
            }
        """
        if not produto_ids:
            return {'barcode_invalido': [], 'acao_aplicada': None}
        invalidos = find_invalid_barcodes(self.odoo, product_ids=produto_ids)
        acao = None
        if auto_corrigir and not dry_run and invalidos:
            # Reusa lista ja encontrada (1 round-trip a menos vs
            # clear_invalid_barcodes que faria find novamente).
            ids = [p['id'] for p in invalidos]
            self.odoo.write('product.product', ids, {'barcode': False})
            acao = {'tipo': 'clear_barcode', 'count': len(ids), 'ids': ids}
            invalidos = []  # apos limpeza, lista zerada
        return {
            'barcode_invalido': [
                {'id': p['id'], 'default_code': p.get('default_code'),
                 'barcode': p.get('barcode'), 'gotcha': 'G035'}
                for p in invalidos
            ],
            'acao_aplicada': acao,
        }

    def _check_lote_vencido(
        self, produto_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """G014 — produtos com lotes ja vencidos com saldo livre.

        Heuristica: para cada produto, busca stock.lot com expiration_date < HOJE
        E que tenha pelo menos 1 quant com quantity > 0. NAO bloqueia (ETAPA B
        do faturamento resolve on-the-fly via Skill 2), apenas reporta.

        Returns:
            [{id, default_code, lotes_vencidos: [{lot_id, name, expiration_date, qty_total}]}]
        """
        if not produto_ids:
            return []
        # agora_utc (UTC tz-aware) -> string formatada Odoo (sem tz).
        # Convencao projeto: SEMPRE usar app.utils.timezone.agora_utc para
        # comparacoes com datetime do Odoo (vide REGRAS_TIMEZONE.md).
        hoje_str = agora_utc().strftime('%Y-%m-%d %H:%M:%S')
        out: List[Dict[str, Any]] = []
        # 1 query bulk para lotes
        lots = self.odoo.search_read('stock.lot', [
            ['product_id', 'in', produto_ids],
            ['expiration_date', '<', hoje_str],
        ], ['id', 'product_id', 'name', 'expiration_date'])
        if not lots:
            return []
        # Agrupar por produto + verificar saldo > 0 em locs REAIS (exclui
        # Indisponivel/MIGRACAO — saldo fantasma a baixar gradualmente, vide
        # memoria [[estoque-fantasma-migracao-indisponivel]]). Sem essa
        # exclusao, lote vencido com saldo SO em Indisp gerava falso WARN
        # G014 (CR-HIGH-2 v14b).
        from app.odoo.constants.locations import LOCAIS_INDISPONIVEL
        locs_indisp = list({v for v in LOCAIS_INDISPONIVEL.values() if v})
        lot_ids = [l['id'] for l in lots]
        quants_por_lot: Dict[int, float] = {}
        if lot_ids:
            quant_domain = [
                ['lot_id', 'in', lot_ids],
                ['quantity', '>', 0],
            ]
            if locs_indisp:
                quant_domain.append(['location_id', 'not in', locs_indisp])
            quants = self.odoo.search_read('stock.quant', quant_domain,
                                           ['lot_id', 'quantity'])
            for q in quants:
                lot_id = q['lot_id'][0] if q.get('lot_id') else None
                if lot_id:
                    quants_por_lot[lot_id] = quants_por_lot.get(lot_id, 0) + float(q['quantity'])
        # Agrupar lotes vencidos COM saldo por produto
        prod_lotes: Dict[int, List[Dict]] = {}
        prod_codes_cache: Dict[int, str] = {}
        for l in lots:
            qty = quants_por_lot.get(l['id'], 0)
            if qty <= 0:
                continue  # sem saldo, irrelevante
            pid = l['product_id'][0] if l.get('product_id') else None
            if not pid:
                continue
            prod_lotes.setdefault(pid, []).append({
                'lot_id': l['id'],
                'name': l.get('name'),
                'expiration_date': l.get('expiration_date'),
                'qty_total': qty,
            })
        # Resolver default_code dos produtos com lotes vencidos relevantes
        if prod_lotes:
            prods = self.odoo.read('product.product', list(prod_lotes.keys()),
                                   ['default_code', 'name'])
            for p in prods:
                prod_codes_cache[p['id']] = p.get('default_code') or '?'
            for pid, lotes in prod_lotes.items():
                out.append({
                    'id': pid,
                    'default_code': prod_codes_cache.get(pid, '?'),
                    'lotes_vencidos': lotes,
                    'gotcha': 'G014',
                })
        return out

    def _check_duplicacao_pipeline(
        self,
        produtos: List[Dict[str, Any]],
        ciclo: Optional[str],
    ) -> List[Dict[str, Any]]:
        """D-OPS-2 — cod_produto + company_id em pipeline ativo (F5a..F5e).

        Sem db_session, retorna [] (caller pode skip via flag).

        Returns:
            [{cod_produto, company_id, ciclo, fase_pipeline, status, ajuste_id}]
        """
        if self.db_session is None:
            return []
        if not produtos:
            return []
        # Considerar cods + (opcionalmente) ciclo. Cods sem company_id via
        # input ids/cods sao IGNORADOS aqui (nao da pra checar duplicacao
        # sem company).
        cods_com_company = [
            (p['default_code'], p['company_id']) for p in produtos
            if p.get('default_code') and p.get('company_id')
        ]
        if not cods_com_company:
            return []
        # Tratamento de variantes: separa cods por company para 1 query por
        # (cod, company) — D_OPS-2 e' especifico do par.
        from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
        from sqlalchemy import and_, or_
        conds = [
            and_(
                AjusteEstoqueInventario.cod_produto == cod,
                AjusteEstoqueInventario.company_id == company,
            )
            for cod, company in cods_com_company
        ]
        if not conds:
            return []
        ativos = self.db_session.query(AjusteEstoqueInventario).filter(
            or_(*conds),
            AjusteEstoqueInventario.fase_pipeline.in_(FASES_PIPELINE_ATIVA),
            AjusteEstoqueInventario.status.in_(STATUS_ATIVOS),
        ).all()
        # Filtrar ajustes do PROPRIO ciclo da auditoria (sao o input — nao
        # contam como duplicacao). Comparar pelo `id` evita falsos positivos.
        # Se ciclo dado, todos os ativos do mesmo ciclo+cod+company sao'
        # esperados (nao duplicacao). Reportar APENAS ativos de OUTRO ciclo
        # OU ciclos diferentes do passado.
        out = []
        for aj in ativos:
            # Se foi resolvido via ciclo igual ao do input, nao reportar como
            # duplicacao (eh' o proprio).
            if ciclo and aj.ciclo == ciclo:
                continue
            out.append({
                'ajuste_id': aj.id,
                'cod_produto': aj.cod_produto,
                'company_id': aj.company_id,
                'ciclo': aj.ciclo,
                'status': aj.status,
                'fase_pipeline': aj.fase_pipeline,
                'gotcha': 'D-OPS-2',
            })
        return out

    # ============================================================
    # Auditoria perfil inventario (entry-point)
    # ============================================================

    def auditar_perfil_inventario(
        self,
        *,
        produto_ids: Optional[List[int]] = None,
        cods_produto: Optional[List[str]] = None,
        ciclo: Optional[str] = None,
        auto_corrigir_barcode: bool = False,
        verificar_duplicacao_pipeline: bool = True,
        verificar_lote_vencido: bool = True,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Auditoria pre-flight perfil 'inventario'.

        Args:
            produto_ids OU cods_produto OU ciclo (mutuamente exclusivos).
            auto_corrigir_barcode: SE True + dry_run=False, limpa G035
                automaticamente via gtin_validator.clear_invalid_barcodes.
            verificar_duplicacao_pipeline: SE True (default), checa D-OPS-2
                em AjusteEstoqueInventario (so' funciona com db_session).
            verificar_lote_vencido: SE True (default), checa G014 (lotes
                vencidos com saldo). NAO bloqueia, apenas reporta.
            dry_run: SE True (default), service e' READ-only.

        Returns:
            {
                'status_global': 'PRE_FLIGHT_OK' | 'PRE_FLIGHT_WARN' | 'PRE_FLIGHT_BLOQUEADO',
                'pode_faturar': bool,
                'auditados': int,
                'erros_resolucao': [...],     # cods nao encontrados em product.product
                'bloqueios': {
                    'ncm_faltando': [...],         # G017 — BLOQUEIO
                    'barcode_invalido': [...],     # G035 — BLOQUEIO (a menos auto_corrigir)
                    'origem_ausente': [...],       # G038 — BLOQUEIO (v22+)
                    'tipo_produto_ausente': [...], # l10n_br_tipo_produto — BLOQUEIO (NOVO v24+)
                    'duplicacao_pipeline': [...],  # D-OPS-2 — BLOQUEIO
                },
                'warnings': {
                    'weight_zero': [...],          # G018 — apenas WARN
                    'standard_price_zero': [...],  # G007 — apenas WARN (NOVO v24+)
                    'lote_vencido': [...],         # G014 — apenas WARN
                    'tracking_none': [...],        # D-OPS-3 — apenas INFO
                },
                'acoes_aplicadas': [...],         # se auto_corrigir
                'tempo_ms': int,
                'erro': Optional[str],
            }
        """
        inicio = time.time()
        try:
            produtos = self._resolver_produtos(
                produto_ids=produto_ids,
                cods_produto=cods_produto,
                ciclo=ciclo,
            )
        except ValueError as exc:
            return {
                'status_global': 'PRE_FLIGHT_BLOQUEADO',
                'pode_faturar': False,
                'auditados': 0,
                'erros_resolucao': [],
                'bloqueios': {'ncm_faltando': [], 'barcode_invalido': [],
                              'origem_ausente': [], 'tipo_produto_ausente': [],
                              'duplicacao_pipeline': []},
                'warnings': {'weight_zero': [], 'standard_price_zero': [],
                             'lote_vencido': [], 'tracking_none': []},
                'acoes_aplicadas': [],
                'tempo_ms': int((time.time() - inicio) * 1000),
                'erro': str(exc),
            }

        erros_resolucao = [p for p in produtos if p.get('_erro_resolucao')]
        produtos_validos = [p for p in produtos if p.get('id')]
        produto_ids_validos = [p['id'] for p in produtos_validos]

        # Checks individuais
        ncm_w_trk = self._check_ncm_weight_tracking(produto_ids_validos)
        bc_res = self._check_barcode_invalido(
            produto_ids_validos, auto_corrigir_barcode, dry_run,
        )
        lote_venc = self._check_lote_vencido(produto_ids_validos) if verificar_lote_vencido else []
        dup_pipe = self._check_duplicacao_pipeline(
            produtos_validos, ciclo,
        ) if verificar_duplicacao_pipeline else []

        bloqueios = {
            'ncm_faltando': ncm_w_trk['ncm_faltando'],
            'barcode_invalido': bc_res['barcode_invalido'],
            'origem_ausente': ncm_w_trk['origem_ausente'],  # G038 v22+
            'tipo_produto_ausente': ncm_w_trk['tipo_produto_ausente'],  # NOVO v24+
            'duplicacao_pipeline': dup_pipe,
        }
        warnings = {
            'weight_zero': ncm_w_trk['weight_zero'],
            'standard_price_zero': ncm_w_trk['standard_price_zero'],  # NOVO v24+
            'lote_vencido': lote_venc,
            'tracking_none': ncm_w_trk['tracking_none'],
        }
        acoes_aplicadas = [bc_res['acao_aplicada']] if bc_res['acao_aplicada'] else []

        tem_bloqueio = any(len(v) > 0 for v in bloqueios.values()) or bool(erros_resolucao)
        tem_warning = any(len(v) > 0 for v in warnings.values())

        if tem_bloqueio:
            status_global = 'PRE_FLIGHT_BLOQUEADO'
            pode_faturar = False
        elif tem_warning:
            status_global = 'PRE_FLIGHT_WARN'
            pode_faturar = True  # warnings nao bloqueiam
        else:
            status_global = 'PRE_FLIGHT_OK'
            pode_faturar = True

        return {
            'status_global': status_global,
            'pode_faturar': pode_faturar,
            'auditados': len(produto_ids_validos),
            'erros_resolucao': erros_resolucao,
            'bloqueios': bloqueios,
            'warnings': warnings,
            'acoes_aplicadas': acoes_aplicadas,
            'tempo_ms': int((time.time() - inicio) * 1000),
            'erro': None,
        }
