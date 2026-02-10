"""
Service de Sincronizacao: Pickings de Recebimento (Odoo -> Local)
=================================================================

Segue o padrao de PedidoComprasServiceOtimizado:
1. Buscar do Odoo com filtro write_date/create_date >= (now - janela)
2. Batch load (moves, move_lines, products, quality_checks)
3. JOIN em memoria + cache
4. Upsert nas 4 tabelas normalizadas

Scheduler: APScheduler a cada 30 minutos
Janela: 90 minutos (configuravel via JANELA_PICKINGS)
Filtro: picking_type_code=incoming, purchase_id != False

Estrategia de busca por state:
- Pickings assigned/waiting/confirmed: SEMPRE sincronizados (sem filtro de data).
  Sao os que importam para Fase 4 (Recebimento Fisico) e podem
  ficar semanas sem write_date recente.
  - assigned: PO vinculado ao DFe, itens pre-preenchidos (pronto para receber)
  - confirmed: Picking criado, aguardando disponibilidade de estoque
  - waiting: Aguardando outra operacao (ex: transferencia entre armazens)
- Pickings done/cancel: sincronizados dentro da janela de tempo
  (filtro create_date/write_date) para limitar volume.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app import db
from app.utils.timezone import agora_utc_naive
from app.recebimento.models import (
    PickingRecebimento,
    PickingRecebimentoProduto,
    PickingRecebimentoMoveLine,
    PickingRecebimentoQualityCheck,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# States de pickings "em aberto" (pendentes de recebimento fisico)
# - assigned: PO vinculado ao DFe, itens pre-preenchidos (pronto para receber)
# - confirmed: Picking criado, aguardando disponibilidade de estoque
# - waiting: Aguardando outra operacao (ex: transferencia entre armazens)
STATES_PENDENTES = ['assigned', 'waiting', 'confirmed']


class PickingRecebimentoSyncService:
    """
    Sincroniza pickings de recebimento do Odoo para tabelas locais.
    Padrao: mesmo de PedidoComprasServiceOtimizado.
    """

    # Companies conhecidas
    COMPANIES = [1, 3, 4, 5]

    def __init__(self):
        self.connection = get_odoo_connection()

    def sincronizar_pickings_incremental(
        self,
        minutos_janela: int = 90,
        primeira_execucao: bool = False
    ) -> Dict[str, Any]:
        """
        Sincroniza pickings de recebimento do Odoo para tabelas locais.

        Args:
            minutos_janela: Janela de tempo para buscar alteracoes (padrao: 90 min)
            primeira_execucao: Se True, busca TODOS os assigned

        Returns:
            Dict com resultado da sincronizacao
        """
        inicio = datetime.now()
        logger.info("=" * 60)
        logger.info(f"📦 SYNC PICKINGS RECEBIMENTO - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Janela: {minutos_janela} minutos | Primeira: {primeira_execucao}")
        logger.info("=" * 60)

        try:
            # Autenticar
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticacao com Odoo")

            # PASSO 1: Buscar pickings atualizados
            pickings_odoo = self._buscar_pickings_odoo(minutos_janela, primeira_execucao)

            if not pickings_odoo:
                logger.info("✅ Nenhum picking novo ou alterado encontrado")
                return {
                    'sucesso': True,
                    'novos': 0,
                    'atualizados': 0,
                    'tempo_execucao': (datetime.now() - inicio).total_seconds()
                }

            logger.info(f"   Encontrados {len(pickings_odoo)} pickings para processar")

            # PASSO 2: Batch load de dados relacionados
            picking_ids = [p['id'] for p in pickings_odoo]

            moves = self._buscar_moves_batch(picking_ids)
            move_lines = self._buscar_move_lines_batch(picking_ids)
            quality_checks = self._buscar_quality_checks_batch(picking_ids)

            # PASSO 3: Batch load de produtos (tracking + use_expiration_date)
            product_ids = set()
            for m in moves:
                if m.get('product_id'):
                    product_ids.add(m['product_id'][0])
            produtos_cache = self._buscar_produtos_batch(list(product_ids))

            # PASSO 3.1: Batch load de CNPJs dos parceiros
            partner_ids = set()
            for p in pickings_odoo:
                if p.get('partner_id'):
                    partner_ids.add(p['partner_id'][0])
            cnpjs_cache = self._buscar_cnpjs_parceiros(list(partner_ids))

            # PASSO 4: Processar e upsert
            resultado = self._processar_pickings(
                pickings_odoo, moves, move_lines,
                quality_checks, produtos_cache, cnpjs_cache
            )

            # PASSO 5: Commit
            db.session.commit()

            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.info("=" * 60)
            logger.info(f"✅ SYNC PICKINGS CONCLUIDA EM {tempo_total:.2f}s")
            logger.info(f"   Novos: {resultado['novos']} | Atualizados: {resultado['atualizados']}")
            logger.info("=" * 60)

            return {
                'sucesso': True,
                **resultado,
                'tempo_execucao': tempo_total
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro na sincronizacao de pickings: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

    def sincronizar_por_periodo(self, data_de: str, data_ate: str) -> Dict[str, Any]:
        """
        Sincroniza pickings de recebimento com datas absolutas (De/Até).

        Args:
            data_de: Data inicial no formato YYYY-MM-DD
            data_ate: Data final no formato YYYY-MM-DD

        Returns:
            Dict com resultado da sincronizacao
        """
        inicio = datetime.now()
        logger.info("=" * 60)
        logger.info(f"📦 SYNC PICKINGS POR PERIODO - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Periodo: {data_de} a {data_ate}")
        logger.info("=" * 60)

        try:
            # Autenticar
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticacao com Odoo")

            # PASSO 1: Buscar pickings por periodo absoluto
            pickings_odoo = self._buscar_pickings_por_periodo(data_de, data_ate)

            if not pickings_odoo:
                logger.info("✅ Nenhum picking encontrado no periodo")
                return {
                    'sucesso': True,
                    'novos': 0,
                    'atualizados': 0,
                    'tempo_execucao': (datetime.now() - inicio).total_seconds()
                }

            logger.info(f"   Encontrados {len(pickings_odoo)} pickings para processar")

            # PASSO 2: Batch load de dados relacionados
            picking_ids = [p['id'] for p in pickings_odoo]

            moves = self._buscar_moves_batch(picking_ids)
            move_lines = self._buscar_move_lines_batch(picking_ids)
            quality_checks = self._buscar_quality_checks_batch(picking_ids)

            # PASSO 3: Batch load de produtos (tracking + use_expiration_date)
            product_ids = set()
            for m in moves:
                if m.get('product_id'):
                    product_ids.add(m['product_id'][0])
            produtos_cache = self._buscar_produtos_batch(list(product_ids))

            # PASSO 3.1: Batch load de CNPJs dos parceiros
            partner_ids = set()
            for p in pickings_odoo:
                if p.get('partner_id'):
                    partner_ids.add(p['partner_id'][0])
            cnpjs_cache = self._buscar_cnpjs_parceiros(list(partner_ids))

            # PASSO 4: Processar e upsert
            resultado = self._processar_pickings(
                pickings_odoo, moves, move_lines,
                quality_checks, produtos_cache, cnpjs_cache
            )

            # PASSO 5: Commit
            db.session.commit()

            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.info("=" * 60)
            logger.info(f"✅ SYNC POR PERIODO CONCLUIDA EM {tempo_total:.2f}s")
            logger.info(f"   Novos: {resultado['novos']} | Atualizados: {resultado['atualizados']}")
            logger.info("=" * 60)

            return {
                'sucesso': True,
                **resultado,
                'tempo_execucao': tempo_total
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro na sincronizacao por periodo: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

    def refresh_picking(self, odoo_picking_id: int) -> Dict[str, Any]:
        """
        Busca dados frescos de UM picking no Odoo e atualiza cache local.
        Usado ao abrir um picking para recebimento (real-time refresh).

        Args:
            odoo_picking_id: ID do picking no Odoo

        Returns:
            Dict com resultado
        """
        logger.info(f"🔄 Refresh picking {odoo_picking_id} do Odoo...")

        try:
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticacao com Odoo")

            # Buscar o picking especifico
            pickings_odoo = self.connection.execute_kw(
                'stock.picking', 'search_read',
                [[['id', '=', odoo_picking_id]]],
                {
                    'fields': [
                        'id', 'name', 'state', 'picking_type_code',
                        'partner_id', 'origin', 'purchase_id',
                        'company_id', 'scheduled_date',
                        'create_date', 'write_date',
                        'location_id', 'location_dest_id',
                        'move_ids', 'move_line_ids',
                    ],
                    'limit': 1,
                }
            )

            if not pickings_odoo:
                logger.warning(f"Picking {odoo_picking_id} nao encontrado no Odoo")
                return {'sucesso': False, 'erro': 'Picking nao encontrado'}

            # Batch load para este picking
            picking_ids = [odoo_picking_id]
            moves = self._buscar_moves_batch(picking_ids)
            move_lines = self._buscar_move_lines_batch(picking_ids)
            quality_checks = self._buscar_quality_checks_batch(picking_ids)

            product_ids = set()
            for m in moves:
                if m.get('product_id'):
                    product_ids.add(m['product_id'][0])
            produtos_cache = self._buscar_produtos_batch(list(product_ids))

            # Buscar CNPJ do parceiro
            partner_ids = set()
            for p in pickings_odoo:
                if p.get('partner_id'):
                    partner_ids.add(p['partner_id'][0])
            cnpjs_cache = self._buscar_cnpjs_parceiros(list(partner_ids))

            # Processar (upsert)
            resultado = self._processar_pickings(
                pickings_odoo, moves, move_lines,
                quality_checks, produtos_cache, cnpjs_cache
            )

            db.session.commit()
            logger.info(f"✅ Refresh picking {odoo_picking_id} concluido")
            return {'sucesso': True, **resultado}

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao fazer refresh do picking {odoo_picking_id}: {e}")
            raise

    # =========================================================================
    # METODOS PRIVADOS: BUSCA ODOO
    # =========================================================================

    def _buscar_pickings_por_periodo(self, data_de: str, data_ate: str) -> List[Dict]:
        """
        Busca pickings de recebimento por periodo absoluto (De/Até).

        Estrategia por state:
        - assigned: TODOS (sem filtro de data) — sao os pendentes de recebimento
        - done/cancel: apenas os criados/alterados dentro do periodo
        """
        logger.info(f"🔍 Buscando pickings de recebimento no Odoo (periodo: {data_de} a {data_ate})...")

        # Adicionar hora para incluir o dia inteiro
        data_de_dt = f"{data_de} 00:00:00"
        data_ate_dt = f"{data_ate} 23:59:59"

        # Domain em 2 partes:
        # - Grupo 1 (OR): TODOS os pendentes assigned/waiting/confirmed (sem filtro data)
        # - Grupo 2 (OR): done/cancel com filtro create_date/write_date
        domain = [
            ['picking_type_code', '=', 'incoming'],
            ['purchase_id', '!=', False],
            '|',
            # Grupo 1: TODOS os pendentes (sem filtro data)
            ['state', 'in', STATES_PENDENTES],
            # Grupo 2: done/cancel com filtro data
            '&',
            ['state', 'in', ['done', 'cancel']],
            '|',
            '&',
            ['create_date', '>=', data_de_dt],
            ['create_date', '<=', data_ate_dt],
            '&',
            ['write_date', '>=', data_de_dt],
            ['write_date', '<=', data_ate_dt],
        ]

        logger.info(f"   Filtro: {STATES_PENDENTES}=TODOS | done/cancel entre {data_de_dt} e {data_ate_dt}")

        campos = [
            'id', 'name', 'state', 'picking_type_code',
            'partner_id', 'origin', 'purchase_id',
            'company_id', 'scheduled_date',
            'create_date', 'write_date',
            'location_id', 'location_dest_id',
            'move_ids', 'move_line_ids',
        ]

        pickings = self.connection.execute_kw(
            'stock.picking', 'search_read',
            [domain],
            {
                'fields': campos,
                'order': 'write_date desc',
                'limit': 500,
            }
        )

        logger.info(f"   Encontrados {len(pickings)} pickings no periodo")
        return pickings

    def _buscar_pickings_odoo(self, minutos_janela: int, primeira_execucao: bool) -> List[Dict]:
        """Busca pickings de recebimento atualizados no Odoo."""
        logger.info("🔍 Buscando pickings de recebimento no Odoo...")

        if primeira_execucao:
            # Primeira execucao: busca TODOS os pendentes (sem filtro data)
            domain = [
                ['picking_type_code', '=', 'incoming'],
                ['purchase_id', '!=', False],
                ['state', 'in', STATES_PENDENTES],
            ]
            logger.info(f"   Primeira execucao: buscando TODOS os pickings {STATES_PENDENTES}")
        else:
            # Incremental: pendentes SEMPRE + done/cancel com janela de tempo
            data_limite = (datetime.now() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')

            # Domain em 2 partes:
            # - Grupo 1 (OR): TODOS os pendentes assigned/waiting/confirmed (sem filtro data)
            # - Grupo 2 (OR): done/cancel com filtro create_date/write_date
            domain = [
                ['picking_type_code', '=', 'incoming'],
                ['purchase_id', '!=', False],
                '|',
                # Grupo 1: TODOS os pendentes (sem filtro data)
                ['state', 'in', STATES_PENDENTES],
                # Grupo 2: done/cancel com filtro data
                '&',
                ['state', 'in', ['done', 'cancel']],
                '|',
                ['create_date', '>=', data_limite],
                ['write_date', '>=', data_limite],
            ]
            logger.info(f"   Filtro: {STATES_PENDENTES}=TODOS | done/cancel >= {data_limite}")

        campos = [
            'id', 'name', 'state', 'picking_type_code',
            'partner_id', 'origin', 'purchase_id',
            'company_id', 'scheduled_date',
            'create_date', 'write_date',
            'location_id', 'location_dest_id',
            'move_ids', 'move_line_ids',
        ]

        pickings = self.connection.execute_kw(
            'stock.picking', 'search_read',
            [domain],
            {
                'fields': campos,
                'order': 'write_date desc',
                'limit': 500,
            }
        )

        logger.info(f"   Encontrados {len(pickings)} pickings no Odoo")
        return pickings

    def _buscar_moves_batch(self, picking_ids: List[int]) -> List[Dict]:
        """Busca TODOS os stock.move dos pickings em 1 query."""
        if not picking_ids:
            return []

        campos = [
            'id', 'picking_id', 'product_id',
            'product_uom_qty', 'quantity',
            'product_uom', 'state', 'move_line_ids',
        ]

        moves = self.connection.execute_kw(
            'stock.move', 'search_read',
            [[['picking_id', 'in', picking_ids]]],
            {'fields': campos}
        )

        logger.info(f"   Batch: {len(moves)} moves carregados")
        return moves

    def _buscar_move_lines_batch(self, picking_ids: List[int]) -> List[Dict]:
        """Busca TODAS as stock.move.line dos pickings em 1 query."""
        if not picking_ids:
            return []

        campos = [
            'id', 'picking_id', 'product_id', 'move_id',
            'lot_id', 'lot_name', 'quantity', 'qty_done',
            'product_uom_id', 'location_id', 'location_dest_id',
        ]

        move_lines = self.connection.execute_kw(
            'stock.move.line', 'search_read',
            [[['picking_id', 'in', picking_ids]]],
            {'fields': campos}
        )

        logger.info(f"   Batch: {len(move_lines)} move_lines carregadas")
        return move_lines

    def _buscar_quality_checks_batch(self, picking_ids: List[int]) -> List[Dict]:
        """Busca TODOS os quality.check dos pickings em 1 query."""
        if not picking_ids:
            return []

        campos = [
            'id', 'picking_id', 'product_id', 'point_id',
            'quality_state', 'test_type_id', 'test_type',
            'measure', 'norm_unit', 'tolerance_min', 'tolerance_max',
            'title', 'name',
        ]

        try:
            checks = self.connection.execute_kw(
                'quality.check', 'search_read',
                [[['picking_id', 'in', picking_ids]]],
                {'fields': campos}
            )
            logger.info(f"   Batch: {len(checks)} quality_checks carregados")
            return checks
        except Exception as e:
            # quality.check pode nao existir se modulo nao instalado
            if 'quality.check' in str(e):
                logger.warning("   Modulo quality.check nao disponivel no Odoo")
                return []
            raise

    def _buscar_produtos_batch(self, product_ids: List[int]) -> Dict[int, Dict]:
        """Busca tracking e use_expiration_date dos produtos em 1 query."""
        if not product_ids:
            return {}

        campos = ['id', 'name', 'tracking', 'use_expiration_date']

        produtos = self.connection.execute_kw(
            'product.product', 'search_read',
            [[['id', 'in', product_ids]]],
            {'fields': campos}
        )

        cache = {}
        for p in produtos:
            cache[p['id']] = {
                'name': p.get('name', ''),
                'tracking': p.get('tracking', 'none'),
                'use_expiration_date': p.get('use_expiration_date', False),
            }

        logger.info(f"   Batch: {len(cache)} produtos carregados (tracking)")
        return cache

    def _buscar_cnpjs_parceiros(self, partner_ids: List[int]) -> Dict[int, str]:
        """
        Busca CNPJ dos parceiros em batch.

        Campo Odoo: res.partner.l10n_br_cnpj

        Args:
            partner_ids: Lista de IDs de parceiros

        Returns:
            Dict mapeando partner_id -> CNPJ (apenas dígitos)
        """
        if not partner_ids:
            return {}

        parceiros = self.connection.execute_kw(
            'res.partner', 'search_read',
            [[['id', 'in', list(partner_ids)]]],
            {'fields': ['id', 'l10n_br_cnpj']}
        )

        # Limpar CNPJ (apenas dígitos)
        resultado = {}
        for p in parceiros:
            cnpj_raw = p.get('l10n_br_cnpj') or ''
            cnpj_limpo = ''.join(c for c in cnpj_raw if c.isdigit())
            resultado[p['id']] = cnpj_limpo

        logger.info(f"   Batch: {len(resultado)} CNPJs de parceiros carregados")
        return resultado

    # =========================================================================
    # METODOS PRIVADOS: PROCESSAMENTO + UPSERT
    # =========================================================================

    def _processar_pickings(
        self,
        pickings_odoo: List[Dict],
        moves: List[Dict],
        move_lines: List[Dict],
        quality_checks: List[Dict],
        produtos_cache: Dict[int, Dict],
        cnpjs_cache: Dict[int, str] = None
    ) -> Dict[str, int]:
        """
        Processa pickings e faz upsert nas 4 tabelas.

        Args:
            pickings_odoo: Lista de pickings do Odoo
            moves: Lista de stock.move
            move_lines: Lista de stock.move.line
            quality_checks: Lista de quality.check
            produtos_cache: Cache de produtos {id: {name, tracking, use_expiration_date}}
            cnpjs_cache: Cache de CNPJs dos parceiros {partner_id: cnpj}

        Returns:
            Dict com contadores de novos/atualizados.
        """
        if cnpjs_cache is None:
            cnpjs_cache = {}
        # Indexar moves por picking_id
        moves_por_picking = {}
        for m in moves:
            pid = m['picking_id'][0] if m.get('picking_id') else None
            if pid:
                if pid not in moves_por_picking:
                    moves_por_picking[pid] = []
                moves_por_picking[pid].append(m)

        # Indexar move_lines por picking_id e move_id
        lines_por_picking = {}
        for ml in move_lines:
            pid = ml['picking_id'][0] if ml.get('picking_id') else None
            if pid:
                if pid not in lines_por_picking:
                    lines_por_picking[pid] = []
                lines_por_picking[pid].append(ml)

        # Indexar quality_checks por picking_id
        checks_por_picking = {}
        for qc in quality_checks:
            pid = qc['picking_id'][0] if qc.get('picking_id') else None
            if pid:
                if pid not in checks_por_picking:
                    checks_por_picking[pid] = []
                checks_por_picking[pid].append(qc)

        # Cache de pickings existentes no banco
        existing_pickings = {}
        odoo_ids = [p['id'] for p in pickings_odoo]
        if odoo_ids:
            existentes = PickingRecebimento.query.filter(
                PickingRecebimento.odoo_picking_id.in_(odoo_ids)
            ).all()
            for e in existentes:
                existing_pickings[e.odoo_picking_id] = e

        novos = 0
        atualizados = 0

        for p in pickings_odoo:
            odoo_id = p['id']
            picking_local = existing_pickings.get(odoo_id)

            # Obter partner_id para buscar CNPJ
            partner_id = p['partner_id'][0] if p.get('partner_id') else None

            # Dados do picking
            picking_data = {
                'odoo_picking_id': odoo_id,
                'odoo_picking_name': p.get('name', ''),
                'state': p.get('state', ''),
                'picking_type_code': p.get('picking_type_code', ''),
                'odoo_partner_id': partner_id,
                'odoo_partner_name': p['partner_id'][1] if p.get('partner_id') else None,
                'odoo_partner_cnpj': cnpjs_cache.get(partner_id, '') if partner_id else '',
                'origin': (p.get('origin') or '')[:500],
                'odoo_purchase_order_id': p['purchase_id'][0] if p.get('purchase_id') else None,
                'odoo_purchase_order_name': p['purchase_id'][1] if p.get('purchase_id') else None,
                'company_id': p['company_id'][0] if p.get('company_id') else 1,
                'scheduled_date': self._parse_datetime(p.get('scheduled_date')),
                'create_date': self._parse_datetime(p.get('create_date')),
                'write_date': self._parse_datetime(p.get('write_date')),
                'location_id': p['location_id'][0] if p.get('location_id') else None,
                'location_dest_id': p['location_dest_id'][0] if p.get('location_dest_id') else None,
                'sincronizado_em': agora_utc_naive(),
                'atualizado_em': agora_utc_naive(),
            }

            if picking_local:
                # UPDATE
                for key, val in picking_data.items():
                    setattr(picking_local, key, val)
                atualizados += 1
            else:
                # INSERT
                picking_local = PickingRecebimento(**picking_data)
                db.session.add(picking_local)
                db.session.flush()  # Obter ID
                novos += 1

            # Processar filhos (delete + re-insert para simplificar)
            self._upsert_produtos_e_lines(
                picking_local,
                moves_por_picking.get(odoo_id, []),
                lines_por_picking.get(odoo_id, []),
                produtos_cache
            )
            self._upsert_quality_checks(picking_local, checks_por_picking.get(odoo_id, []))

        return {'novos': novos, 'atualizados': atualizados}

    def _upsert_produtos_e_lines(
        self,
        picking_local: PickingRecebimento,
        moves_picking: List[Dict],
        lines_picking: List[Dict],
        produtos_cache: Dict[int, Dict]
    ):
        """
        Atualiza produtos e move_lines do picking (delete + re-insert).

        Args:
            picking_local: Registro local do picking
            moves_picking: Lista de stock.move deste picking (do Odoo)
            lines_picking: Lista de stock.move.line deste picking (do Odoo)
            produtos_cache: Cache de product.product {id: {name, tracking, use_expiration_date}}
        """
        # Deletar existentes (move_lines primeiro por FK)
        PickingRecebimentoMoveLine.query.filter_by(
            picking_recebimento_id=picking_local.id
        ).delete()
        PickingRecebimentoProduto.query.filter_by(
            picking_recebimento_id=picking_local.id
        ).delete()
        db.session.flush()

        # Indexar move_lines do Odoo por move_id
        lines_por_move = {}
        for ml in lines_picking:
            move_id = ml['move_id'][0] if ml.get('move_id') else None
            if move_id:
                if move_id not in lines_por_move:
                    lines_por_move[move_id] = []
                lines_por_move[move_id].append(ml)

        for move in moves_picking:
            product_id = move['product_id'][0] if move.get('product_id') else None
            product_info = produtos_cache.get(product_id, {})

            produto = PickingRecebimentoProduto(
                picking_recebimento_id=picking_local.id,
                odoo_move_id=move['id'],
                odoo_product_id=product_id or 0,
                odoo_product_name=move['product_id'][1] if move.get('product_id') else '',
                product_uom_qty=move.get('product_uom_qty', 0),
                product_uom=move['product_uom'][1] if move.get('product_uom') else 'UN',
                tracking=product_info.get('tracking', 'none'),
                use_expiration_date=product_info.get('use_expiration_date', False),
            )
            db.session.add(produto)
            db.session.flush()  # Obter produto.id para FK

            # Inserir move_lines deste move
            move_lines_do_move = lines_por_move.get(move['id'], [])
            for ml in move_lines_do_move:
                move_line = PickingRecebimentoMoveLine(
                    picking_recebimento_id=picking_local.id,
                    produto_id=produto.id,
                    odoo_move_line_id=ml['id'],
                    odoo_move_id=move['id'],
                    lot_id=ml['lot_id'][0] if ml.get('lot_id') else None,
                    lot_name=ml['lot_id'][1] if ml.get('lot_id') else (ml.get('lot_name') or None),
                    quantity=ml.get('quantity', 0),
                    reserved_uom_qty=ml.get('qty_done', 0),
                    location_id=ml['location_id'][0] if ml.get('location_id') else None,
                    location_dest_id=ml['location_dest_id'][0] if ml.get('location_dest_id') else None,
                )
                db.session.add(move_line)

    def _upsert_quality_checks(
        self,
        picking_local: PickingRecebimento,
        checks_picking: List[Dict]
    ):
        """Atualiza quality checks do picking (delete + re-insert)."""
        PickingRecebimentoQualityCheck.query.filter_by(
            picking_recebimento_id=picking_local.id
        ).delete()
        db.session.flush()

        for qc in checks_picking:
            check = PickingRecebimentoQualityCheck(
                picking_recebimento_id=picking_local.id,
                odoo_check_id=qc['id'],
                odoo_point_id=qc['point_id'][0] if qc.get('point_id') else None,
                odoo_product_id=qc['product_id'][0] if qc.get('product_id') else None,
                odoo_product_name=qc['product_id'][1] if qc.get('product_id') else None,
                quality_state=qc.get('quality_state', 'none'),
                test_type=qc.get('test_type', 'passfail'),
                title=qc.get('title') or qc.get('name', ''),
                norm_unit=qc.get('norm_unit', ''),
                tolerance_min=qc.get('tolerance_min', 0),
                tolerance_max=qc.get('tolerance_max', 0),
            )
            db.session.add(check)

    def _parse_datetime(self, value) -> datetime:
        """Converte string datetime do Odoo para datetime Python."""
        if not value:
            return None # type: ignore
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            try:
                return datetime.strptime(str(value)[:19], '%Y-%m-%dT%H:%M:%S')
            except (ValueError, TypeError):
                return None # type: ignore
