# -*- coding: utf-8 -*-
"""
Serviço de Conciliação - Extrato Bancário no Odoo
=================================================

Executa a conciliação de linhas de extrato com títulos no Odoo.

Processo:
1. Buscar linha de crédito do extrato (conta transitória)
2. Buscar título no Odoo pelo ID
3. Capturar snapshot ANTES
4. Executar reconcile([credit_line_id, titulo_id])
5. Capturar snapshot DEPOIS
6. Atualizar item com resultado

Diferença da baixa manual:
- Manual: Cria account.payment -> action_post -> reconcile
- Extrato: Linha já existe -> apenas reconcile

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber

logger = logging.getLogger(__name__)


# Campos para snapshot
CAMPOS_SNAPSHOT_TITULO = [
    'id', 'name', 'debit', 'credit', 'balance',
    'amount_residual', 'amount_residual_currency',
    'reconciled', 'matched_credit_ids', 'matched_debit_ids',
    'full_reconcile_id', 'matching_number',
    'date_maturity', 'partner_id', 'move_id', 'company_id'
]


class ExtratoConciliacaoService:
    """
    Serviço para conciliar linhas de extrato com títulos no Odoo.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self.estatisticas = {
            'processados': 0,
            'conciliados': 0,
            'erros': 0
        }

    @property
    def connection(self):
        """Retorna a conexão Odoo, criando se necessário."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        return self._connection

    def conciliar_lote(self, lote_id: int) -> Dict:
        """
        Concilia todos os itens aprovados de um lote.

        Args:
            lote_id: ID do lote

        Returns:
            Dict com estatísticas
        """
        lote = ExtratoLote.query.get(lote_id)
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        logger.info(f"=" * 60)
        logger.info(f"CONCILIANDO LOTE {lote_id} - {lote.nome}")
        logger.info(f"=" * 60)

        # Buscar itens aprovados
        itens = ExtratoItem.query.filter_by(
            lote_id=lote_id,
            aprovado=True,
            status='APROVADO'
        ).all()

        logger.info(f"Itens a conciliar: {len(itens)}")

        for item in itens:
            try:
                self.conciliar_item(item)
                self.estatisticas['conciliados'] += 1
            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status = 'ERRO'
                item.mensagem = str(e)
                self.estatisticas['erros'] += 1

            self.estatisticas['processados'] += 1
            db.session.commit()

        logger.info(f"Conciliação concluída: {self.estatisticas}")

        return self.estatisticas

    def conciliar_item(self, item: ExtratoItem) -> Dict:
        """
        Concilia um item individual no Odoo.

        Args:
            item: ExtratoItem a conciliar

        Returns:
            Dict com resultado
        """
        logger.info(f"Conciliando item {item.id}: NF {item.titulo_nf} P{item.titulo_parcela}")

        if not item.titulo_id:
            raise ValueError("Item não possui título vinculado")

        if not item.credit_line_id:
            # Buscar linha de crédito se não tiver
            item.credit_line_id = self._buscar_linha_credito(item.move_id)
            if not item.credit_line_id:
                raise ValueError(f"Linha de crédito não encontrada para move_id {item.move_id}")

        # Buscar título no Odoo
        titulo = ContasAReceber.query.get(item.titulo_id)
        if not titulo:
            raise ValueError(f"Título {item.titulo_id} não encontrado no sistema")

        # Buscar ID do título no Odoo (account.move.line)
        titulo_odoo = self._buscar_titulo_odoo(titulo.titulo_nf, titulo.parcela, titulo.empresa)
        if not titulo_odoo:
            raise ValueError(f"Título NF {titulo.titulo_nf} P{titulo.parcela} não encontrado no Odoo")

        titulo_odoo_id = titulo_odoo['id']

        # Salvar saldo antes
        item.titulo_saldo_antes = titulo_odoo.get('amount_residual', 0)

        # Capturar snapshot ANTES
        snapshot_antes = self._capturar_snapshot(titulo_odoo_id)
        item.set_snapshot_antes(snapshot_antes)

        # Executar reconciliação
        logger.info(f"  Reconciliando: credit_line={item.credit_line_id} com titulo={titulo_odoo_id}")
        self._executar_reconcile(item.credit_line_id, titulo_odoo_id)

        # Capturar snapshot DEPOIS
        snapshot_depois = self._capturar_snapshot(titulo_odoo_id)
        item.set_snapshot_depois(snapshot_depois)

        # Buscar saldo depois
        titulo_atualizado = self._buscar_titulo_por_id(titulo_odoo_id)
        item.titulo_saldo_depois = titulo_atualizado.get('amount_residual', 0) if titulo_atualizado else None

        # Buscar partial_reconcile criado
        item.partial_reconcile_id = self._buscar_partial_reconcile(titulo_odoo_id)

        # Verificar full_reconcile (se titulo foi quitado)
        if titulo_atualizado and titulo_atualizado.get('full_reconcile_id'):
            full_rec = titulo_atualizado.get('full_reconcile_id')
            if isinstance(full_rec, (list, tuple)) and len(full_rec) > 0:
                item.full_reconcile_id = full_rec[0]

        # Atualizar status
        item.status = 'CONCILIADO'
        item.processado_em = datetime.utcnow()
        item.mensagem = f"Conciliado: Saldo {item.titulo_saldo_antes} -> {item.titulo_saldo_depois}"

        logger.info(f"  OK - Saldo: {item.titulo_saldo_antes} -> {item.titulo_saldo_depois}")

        return {
            'item_id': item.id,
            'titulo_id': titulo_odoo_id,
            'saldo_antes': item.titulo_saldo_antes,
            'saldo_depois': item.titulo_saldo_depois,
            'partial_reconcile_id': item.partial_reconcile_id
        }

    def _buscar_linha_credito(self, move_id: int) -> Optional[int]:
        """
        Busca a linha de crédito (contrapartida) do extrato.
        """
        if not move_id:
            return None

        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['credit', '>', 0]
            ],
            fields=['id'],
            limit=1
        )
        return linhas[0]['id'] if linhas else None

    def _buscar_titulo_odoo(self, nf: str, parcela: str, empresa: int) -> Optional[Dict]:
        """
        Busca o título no Odoo pelo número da NF e parcela.
        """
        # Mapeamento empresa local -> company_id Odoo
        EMPRESA_MAP = {1: 1, 2: 3, 3: 4}  # FB=1, SC=3, CD=4
        company_id = EMPRESA_MAP.get(empresa, empresa)

        # Tentar converter parcela para int
        try:
            parcela_int = int(parcela)
        except:
            parcela_int = None

        # Buscar por x_studio_nf_e e parcela
        domain = [
            ['x_studio_nf_e', '=', str(nf)],
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted'],
            ['reconciled', '=', False]
        ]

        if parcela_int:
            domain.append(['l10n_br_cobranca_parcela', '=', parcela_int])

        titulos = self.connection.search_read(
            'account.move.line',
            domain,
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            # Preferir empresa correta
            for t in titulos:
                comp = t.get('company_id')
                if comp and isinstance(comp, (list, tuple)):
                    if comp[0] == company_id:
                        return t
            return titulos[0]

        return None

    def _buscar_titulo_por_id(self, titulo_id: int) -> Optional[Dict]:
        """Busca título por ID."""
        titulos = self.connection.search_read(
            'account.move.line',
            [['id', '=', titulo_id]],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=1
        )
        return titulos[0] if titulos else None

    def _capturar_snapshot(self, titulo_id: int) -> Dict:
        """Captura snapshot do título."""
        titulo = self._buscar_titulo_por_id(titulo_id)
        return {'titulo': titulo} if titulo else {}

    def _executar_reconcile(self, credit_line_id: int, titulo_id: int) -> None:
        """
        Executa a reconciliação no Odoo.

        Nota: reconcile() retorna None, causando erro de serialização XML-RPC.
        Isso é esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.move.line',
                'reconcile',
                [[credit_line_id, titulo_id]]
            )
        except Exception as e:
            # Ignorar erro de serialização - operação foi executada
            if "cannot marshal None" not in str(e):
                raise

    def _buscar_partial_reconcile(self, titulo_id: int) -> Optional[int]:
        """Busca o último partial_reconcile criado para o título."""
        titulo = self._buscar_titulo_por_id(titulo_id)
        if not titulo:
            return None

        matched_ids = titulo.get('matched_credit_ids', [])
        if matched_ids:
            return matched_ids[-1]

        return None
