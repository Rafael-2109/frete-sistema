# -*- coding: utf-8 -*-
"""
Serviço de Sincronização de Baixas/Reconciliações do Odoo
=========================================================

Este serviço sincroniza as baixas (account.partial.reconcile) do Odoo
para a tabela ContasAReceberReconciliacao.

IMPORTANTE: Este serviço NÃO importa as tabelas deprecated:
- ContasAReceberPagamento (REMOVED)
- ContasAReceberDocumento (REMOVED)
- ContasAReceberLinhaCredito (REMOVED)

Apenas a tabela ContasAReceberReconciliacao é atualizada.

Uso no Scheduler:
    from app.financeiro.services.sincronizacao_baixas_service import SincronizacaoBaixasService
    service = SincronizacaoBaixasService()
    estatisticas = service.sincronizar_baixas(janela_minutos=120)

Data: 2025-11-28
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.models import ContasAReceber, ContasAReceberReconciliacao
from app.financeiro.parcela_utils import parcela_to_odoo
from app.financeiro.services.vinculacao_abatimentos_service import VinculacaoAbatimentosService

logger = logging.getLogger(__name__)


class SincronizacaoBaixasService:
    """
    Serviço para sincronização incremental de baixas do Odoo.

    Estratégia:
    1. Buscar títulos não pagos OU com baixas recentes (janela de tempo)
    2. Para cada título, buscar matched_credit_ids no Odoo
    3. Importar/atualizar apenas ContasAReceberReconciliacao
    4. Classificar tipo de baixa automaticamente
    5. Tentar vincular automaticamente com abatimentos do sistema
    """

    def __init__(self, connection=None):
        """
        Inicializa o serviço.

        Args:
            connection: Conexão Odoo (opcional, será criada se não fornecida)
        """
        self._connection = connection
        self.estatisticas = {
            'titulos_processados': 0,
            'titulos_com_baixas': 0,
            'reconciliacoes_criadas': 0,
            'reconciliacoes_atualizadas': 0,
            'vinculacoes_automaticas': 0,
            'erros': 0,
            'inicio': None,
            'fim': None,
            'duracao_segundos': 0
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

    def sincronizar_baixas(
        self,
        janela_minutos: int = 120,
        limite_titulos: int = None,
        empresa: int = None,
        apenas_nao_pagos: bool = False,
        vincular_automatico: bool = True
    ) -> Dict:
        """
        Sincroniza baixas do Odoo de forma incremental.

        Args:
            janela_minutos: Janela de tempo para buscar títulos (default: 120)
            limite_titulos: Limite de títulos a processar (para testes)
            empresa: Filtrar por empresa (1=FB, 2=SC, 3=CD)
            apenas_nao_pagos: Processar apenas títulos não pagos
            vincular_automatico: Tentar vincular abatimentos automaticamente

        Returns:
            Dict com estatísticas da sincronização
        """
        self.estatisticas['inicio'] = agora_utc_naive()
        logger.info(f"=" * 60)
        logger.info(f"SINCRONIZAÇÃO DE BAIXAS - INÍCIO")
        logger.info(f"Janela: {janela_minutos} minutos")
        logger.info(f"=" * 60)

        try:
            # Buscar títulos que precisam de sincronização
            titulos = self._buscar_titulos_para_sincronizar(
                janela_minutos=janela_minutos,
                limite=limite_titulos,
                empresa=empresa,
                apenas_nao_pagos=apenas_nao_pagos
            )

            logger.info(f"📊 {len(titulos)} títulos para processar")

            # Processar cada título
            for i, titulo in enumerate(titulos, 1):
                try:
                    if i % 50 == 0:
                        logger.info(f"   Progresso: {i}/{len(titulos)}")

                    qtd_importadas = self._processar_titulo(titulo)
                    self.estatisticas['titulos_processados'] += 1

                    if qtd_importadas > 0:
                        self.estatisticas['titulos_com_baixas'] += 1

                        # Vincular automaticamente
                        if vincular_automatico:
                            stats_vinc = VinculacaoAbatimentosService.vincular_todos_pendentes(
                                conta_id=titulo.id
                            )
                            self.estatisticas['vinculacoes_automaticas'] += stats_vinc.get('vinculados', 0)

                    # Commit a cada 10 títulos
                    if i % 10 == 0:
                        db.session.commit()

                except Exception as e:
                    logger.error(f"❌ Erro no título {titulo.titulo_nf}: {e}")
                    self.estatisticas['erros'] += 1
                    db.session.rollback()

            # Commit final
            db.session.commit()

        except Exception as e:
            logger.error(f"❌ Erro geral na sincronização: {e}")
            self.estatisticas['erros'] += 1
            db.session.rollback()

        # Finalizar estatísticas
        self.estatisticas['fim'] = agora_utc_naive()
        self.estatisticas['duracao_segundos'] = (
            self.estatisticas['fim'] - self.estatisticas['inicio']
        ).total_seconds()

        self._log_resumo()
        return self.estatisticas

    def _buscar_titulos_para_sincronizar(
        self,
        janela_minutos: int,
        limite: int = None,
        empresa: int = None,
        apenas_nao_pagos: bool = False
    ) -> List[ContasAReceber]:
        """
        Busca títulos que precisam ter baixas sincronizadas.

        Critérios:
        1. Títulos não pagos (parcela_paga=False)
        2. Títulos sincronizados recentemente (última janela de tempo)
        3. Títulos com vencimento nos últimos 30 dias ou próximos 15 dias
        """
        data_corte = agora_utc_naive() - timedelta(minutes=janela_minutos)
        data_venc_inicio = agora_utc_naive().date() - timedelta(days=30)
        data_venc_fim = agora_utc_naive().date() + timedelta(days=15)

        query = ContasAReceber.query

        if apenas_nao_pagos:
            query = query.filter(ContasAReceber.parcela_paga == False)
        else:
            # Títulos não pagos OU atualizados recentemente
            query = query.filter(
                db.or_(
                    ContasAReceber.parcela_paga == False,
                    ContasAReceber.ultima_sincronizacao >= data_corte
                )
            )

        # Filtrar por vencimento relevante
        query = query.filter(
            ContasAReceber.vencimento.between(data_venc_inicio, data_venc_fim)
        )

        if empresa:
            query = query.filter(ContasAReceber.empresa == empresa)

        query = query.order_by(ContasAReceber.vencimento.asc())

        if limite:
            query = query.limit(limite)

        return query.all()

    def _processar_titulo(self, titulo: ContasAReceber) -> int:
        """
        Processa um título, buscando suas baixas no Odoo.

        Returns:
            Número de reconciliações importadas/atualizadas
        """
        # Buscar linha do título no Odoo
        titulo_odoo = self._buscar_titulo_odoo(titulo)

        if not titulo_odoo:
            return 0

        # FIX: Atualizar parcela_paga se Odoo indica título pago
        # _buscar_titulo_odoo já retorna l10n_br_paga e balance
        paga_odoo = bool(titulo_odoo.get('l10n_br_paga'))
        balance = float(titulo_odoo.get('balance', 0) or 0)

        if (paga_odoo or balance <= 0) and not titulo.parcela_paga:
            titulo.parcela_paga = True
            if not titulo.metodo_baixa:
                titulo.metodo_baixa = 'ODOO_DIRETO'
            logger.info(f"  Titulo {titulo.titulo_nf}-{titulo.parcela}: marcado pago via sync baixas")

        matched_credit_ids = titulo_odoo.get('matched_credit_ids', [])

        if not matched_credit_ids:
            return 0

        # Buscar detalhes das reconciliações
        reconciliacoes = self._buscar_reconciliacoes(matched_credit_ids)

        count = 0
        for rec in reconciliacoes:
            try:
                criada = self._salvar_reconciliacao(titulo, rec, titulo_odoo)
                if criada:
                    self.estatisticas['reconciliacoes_criadas'] += 1
                else:
                    self.estatisticas['reconciliacoes_atualizadas'] += 1
                count += 1
            except Exception as e:
                logger.error(f"   Erro na reconciliação {rec.get('id')}: {e}")

        return count

    def _buscar_titulo_odoo(self, titulo: ContasAReceber) -> Optional[Dict]:
        """Busca a linha do título no Odoo (account.move.line)."""
        empresa_map = {1: 'FB', 2: 'SC', 3: 'CD'}
        empresa_sufixo = empresa_map.get(titulo.empresa, '')

        # Gotcha ORM Odoo: integer 0 é armazenado como False no PostgreSQL.
        # Busca com '=' 0 não encontra — precisa usar 'in' [0, False].
        parcela_odoo = parcela_to_odoo(titulo.parcela)
        if parcela_odoo:
            filtro_parcela = ['l10n_br_cobranca_parcela', '=', parcela_odoo]
        else:
            filtro_parcela = ['l10n_br_cobranca_parcela', 'in', [0, False]]

        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['x_studio_nf_e', '=', titulo.titulo_nf],
                filtro_parcela,
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ],
            fields=[
                'id', 'name', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'balance', 'amount_residual', 'debit', 'credit',
                'matched_credit_ids', 'matched_debit_ids',
                'full_reconcile_id', 'reconciled', 'l10n_br_paga',
                'company_id', 'partner_id', 'move_id'
            ],
            limit=10
        )

        if not linhas:
            return None

        # Se tiver mais de uma, filtrar pela empresa
        if len(linhas) > 1 and empresa_sufixo:
            for linha in linhas:
                company = linha.get('company_id')
                if company and isinstance(company, (list, tuple)):
                    if empresa_sufixo in company[1]:
                        return linha
            return linhas[0]

        return linhas[0]

    def _buscar_reconciliacoes(self, matched_credit_ids: List[int]) -> List[Dict]:
        """Busca detalhes das reconciliações no Odoo."""
        if not matched_credit_ids:
            return []

        return self.connection.search_read(
            'account.partial.reconcile',
            [['id', 'in', matched_credit_ids]],
            fields=[
                'id', 'amount', 'debit_move_id', 'credit_move_id',
                'max_date', 'company_id',
                'create_date', 'write_date'
            ],
            limit=100
        )

    def _salvar_reconciliacao(
        self,
        titulo: ContasAReceber,
        rec: Dict,
        titulo_odoo: Dict
    ) -> bool:
        """
        Salva ou atualiza uma reconciliação.

        Returns:
            True se foi criada, False se foi atualizada
        """
        odoo_id = rec.get('id')

        # Verificar se já existe
        existente = ContasAReceberReconciliacao.query.filter_by(odoo_id=odoo_id).first()
        criada = existente is None

        if existente:
            reconciliacao = existente
        else:
            reconciliacao = ContasAReceberReconciliacao()
            reconciliacao.odoo_id = odoo_id
            reconciliacao.conta_a_receber_id = titulo.id
            db.session.add(reconciliacao)

        # Preencher campos básicos
        reconciliacao.amount = rec.get('amount')
        reconciliacao.debit_move_id = self._extrair_id(rec.get('debit_move_id'))
        reconciliacao.credit_move_id = self._extrair_id(rec.get('credit_move_id'))
        reconciliacao.max_date = self._parse_date(rec.get('max_date'))
        reconciliacao.company_id = self._extrair_id(rec.get('company_id'))

        # Auditoria Odoo
        reconciliacao.odoo_create_date = self._parse_datetime(rec.get('create_date'))
        reconciliacao.odoo_write_date = self._parse_datetime(rec.get('write_date'))

        # Buscar detalhes da linha de crédito para classificar tipo
        credit_move_id = reconciliacao.credit_move_id
        if credit_move_id:
            linha_info = self._buscar_info_linha_credito(credit_move_id)
            if linha_info:
                reconciliacao.credit_move_name = linha_info.get('name')
                reconciliacao.credit_move_ref = linha_info.get('ref')
                reconciliacao.tipo_baixa_odoo = linha_info.get('move_type')
                reconciliacao.journal_code = linha_info.get('journal_code')

                # Classificar tipo de baixa
                reconciliacao.tipo_baixa = self._classificar_tipo_baixa(
                    move_type=linha_info.get('move_type'),
                    payment_id=linha_info.get('payment_id'),
                    journal_code=linha_info.get('journal_code'),
                    ref=linha_info.get('ref')
                )

        reconciliacao.ultima_sincronizacao = agora_utc_naive()

        return criada

    def _buscar_info_linha_credito(self, odoo_id: int) -> Optional[Dict]:
        """Busca informações básicas da linha de crédito no Odoo."""
        linhas = self.connection.search_read(
            'account.move.line',
            [['id', '=', odoo_id]],
            fields=[
                'id', 'name', 'ref', 'move_type', 'payment_id', 'journal_id'
            ],
            limit=1
        )

        if not linhas:
            return None

        linha = linhas[0]

        # Buscar código do diário
        journal_id = self._extrair_id(linha.get('journal_id'))
        journal_code = None
        if journal_id:
            journals = self.connection.search_read(
                'account.journal',
                [['id', '=', journal_id]],
                fields=['code'],
                limit=1
            )
            if journals:
                journal_code = journals[0].get('code')

        return {
            'name': linha.get('name'),
            'ref': linha.get('ref'),
            'move_type': linha.get('move_type'),
            'payment_id': self._extrair_id(linha.get('payment_id')),
            'journal_code': journal_code
        }

    def _classificar_tipo_baixa(
        self,
        move_type: str,
        payment_id: Optional[int],
        journal_code: Optional[str],
        ref: Optional[str]
    ) -> str:
        """
        Classifica o tipo de baixa baseado nos dados do Odoo.

        Usa a mesma lógica do VinculacaoAbatimentosService.
        """
        return VinculacaoAbatimentosService.classificar_tipo_baixa_odoo(
            move_type=move_type,
            payment_id=payment_id,
            journal_code=journal_code,
            ref=ref
        )

    def _extrair_id(self, valor) -> Optional[int]:
        """Extrai ID de um campo many2one do Odoo."""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 0:
            return valor[0]
        if isinstance(valor, int):
            return valor
        return None

    def _parse_date(self, valor) -> Optional[datetime]:
        """Converte string de data do Odoo para date."""
        if not valor or valor is False:
            return None
        try:
            if isinstance(valor, str):
                return datetime.strptime(valor, '%Y-%m-%d').date() # type: ignore
            return valor
        except Exception:
            return None

    def _parse_datetime(self, valor) -> Optional[datetime]:
        """Converte string de datetime do Odoo para datetime."""
        if not valor or valor is False:
            return None
        try:
            if isinstance(valor, str):
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.strptime(valor, fmt)
                    except ValueError:
                        continue
            return valor # type: ignore
        except Exception:
            return None

    def _log_resumo(self):
        """Loga o resumo da sincronização."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"SINCRONIZAÇÃO DE BAIXAS - RESUMO")
        logger.info(f"{'=' * 60}")
        logger.info(f"Títulos processados:       {self.estatisticas['titulos_processados']}")
        logger.info(f"Títulos com baixas:        {self.estatisticas['titulos_com_baixas']}")
        logger.info(f"Reconciliações criadas:    {self.estatisticas['reconciliacoes_criadas']}")
        logger.info(f"Reconciliações atualizadas: {self.estatisticas['reconciliacoes_atualizadas']}")
        logger.info(f"Vinculações automáticas:   {self.estatisticas['vinculacoes_automaticas']}")
        logger.info(f"Erros:                     {self.estatisticas['erros']}")
        logger.info(f"Duração:                   {self.estatisticas['duracao_segundos']:.1f}s")
        logger.info(f"{'=' * 60}")


# Função auxiliar para uso no scheduler
def sincronizar_baixas_odoo(janela_minutos: int = 120) -> Dict:
    """
    Função simplificada para uso no scheduler.

    Args:
        janela_minutos: Janela de tempo para buscar títulos

    Returns:
        Dict com estatísticas
    """
    service = SincronizacaoBaixasService()
    return service.sincronizar_baixas(janela_minutos=janela_minutos)
