"""
Service para sincronização de extratos com baixas do Odoo/CNAB.

Este service é responsável por:
1. Identificar extratos pendentes que já foram pagos via CNAB ou Odoo
2. Atualizar status dos extratos automaticamente
3. Pode ser executado no scheduler ou manualmente

Uso:
    service = SincronizacaoExtratosService()
    resultado = service.sincronizar_extratos_pendentes(janela_minutos=120)

Scheduler:
    Recomendado executar após SincronizacaoBaixasService (cada 60-120 min)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.models import (
    ExtratoItem,
    ExtratoLote,
    ContasAReceber,
    CnabRetornoItem
)
from app.financeiro.parcela_utils import parcela_to_int

logger = logging.getLogger(__name__)


class SincronizacaoExtratosService:
    """
    Sincroniza extratos pendentes quando há baixas CNAB/manual no Odoo.

    O fluxo de sincronização:
    1. Busca ExtratoItem com status PENDENTE ou MATCH_ENCONTRADO
    2. Para cada item com título vinculado, verifica se título já foi pago
    3. Se pago: atualiza ExtratoItem.status para refletir a baixa
    4. Registra estatísticas de sincronização
    """

    def __init__(self):
        self.stats = {
            'total_verificados': 0,
            'atualizados_por_titulo': 0,
            'atualizados_por_cnab': 0,
            'sem_alteracao': 0,
            'erros': 0
        }

    def sincronizar_extratos_pendentes(
        self,
        janela_minutos: int = 120,
        limite: int = 500
    ) -> Dict[str, Any]:
        """
        Sincroniza extratos pendentes com baixas já realizadas.

        Args:
            janela_minutos: Janela de tempo para buscar extratos (default 120min)
            limite: Limite de registros por execução

        Returns:
            Dict com estatísticas da sincronização
        """
        logger.info(f"[SYNC_EXTRATOS] Iniciando sincronização (janela={janela_minutos}min)")

        self.stats = {
            'total_verificados': 0,
            'atualizados_por_titulo': 0,
            'atualizados_por_cnab': 0,
            'sem_alteracao': 0,
            'erros': 0,
            'inicio': agora_utc_naive().isoformat()
        }

        try:
            # 1. Buscar extratos pendentes
            data_limite = agora_utc_naive() - timedelta(minutes=janela_minutos)

            extratos_pendentes = ExtratoItem.query.filter(
                ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
                ExtratoItem.titulo_receber_id.isnot(None),  # Tem título vinculado
                ExtratoItem.criado_em >= data_limite
            ).limit(limite).all()

            logger.info(f"[SYNC_EXTRATOS] {len(extratos_pendentes)} extratos pendentes encontrados")

            # 2. Processar cada extrato
            for extrato in extratos_pendentes:
                self.stats['total_verificados'] += 1
                try:
                    atualizado = self._verificar_e_atualizar(extrato)
                    if atualizado:
                        if atualizado == 'titulo':
                            self.stats['atualizados_por_titulo'] += 1
                        elif atualizado == 'cnab':
                            self.stats['atualizados_por_cnab'] += 1
                    else:
                        self.stats['sem_alteracao'] += 1
                except Exception as e:
                    logger.error(f"[SYNC_EXTRATOS] Erro no extrato {extrato.id}: {e}")
                    self.stats['erros'] += 1

            # 3. Commit das alterações
            db.session.commit()

            self.stats['fim'] = agora_utc_naive().isoformat()
            logger.info(f"[SYNC_EXTRATOS] Concluído: {self.stats}")

            return {
                'success': True,
                'stats': self.stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC_EXTRATOS] Erro geral: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }

    def _verificar_e_atualizar(self, extrato: ExtratoItem) -> Optional[str]:
        """
        Verifica se o extrato deve ser atualizado e atualiza se necessário.

        Args:
            extrato: ExtratoItem a verificar

        Returns:
            'titulo' se atualizado por título pago
            'cnab' se atualizado por CNAB processado
            None se não atualizado
        """
        # Verificar se título vinculado foi pago
        if extrato.titulo_receber_id:
            titulo = ContasAReceber.query.get(extrato.titulo_receber_id)

            if titulo and titulo.parcela_paga:
                # Título foi pago - atualizar extrato

                # Verificar se foi via CNAB
                cnab_item = CnabRetornoItem.query.filter(
                    CnabRetornoItem.conta_a_receber_id == titulo.id,
                    CnabRetornoItem.processado == True
                ).first()

                if cnab_item:
                    # Pago via CNAB
                    extrato.status = 'CONCILIADO'
                    extrato.status_match = 'MATCH_ENCONTRADO'
                    extrato.match_criterio = f'SYNC_AUTO_CNAB_LOTE_{cnab_item.lote_id}'
                    extrato.mensagem = (
                        f"Baixa via CNAB detectada (Lote #{cnab_item.lote_id}, "
                        f"Ocorrência {cnab_item.codigo_ocorrencia})"
                    )

                    # Vincular CNAB ao extrato se ainda não estiver
                    if not cnab_item.extrato_item_id:
                        cnab_item.extrato_item_id = extrato.id
                        cnab_item.status_match_extrato = 'SYNC_AUTOMATICO'

                    return 'cnab'
                else:
                    # Pago de outra forma (Odoo direto, manual)
                    extrato.status = 'CONCILIADO'
                    extrato.status_match = 'MATCH_ENCONTRADO'
                    extrato.match_criterio = 'SYNC_AUTO_TITULO_PAGO'
                    extrato.mensagem = (
                        f"Título já pago (detectado via sincronização automática). "
                        f"Status Odoo: {titulo.status_pagamento_odoo or 'N/D'}"
                    )
                    return 'titulo'

        return None

    def _normalizar_cnpj(self, cnpj: str) -> str:
        """Remove formatação do CNPJ, retornando apenas dígitos."""
        if not cnpj:
            return ''
        return ''.join(filter(str.isdigit, str(cnpj)))

    def _buscar_titulo_para_extrato(self, extrato: ExtratoItem) -> Optional[ContasAReceber]:
        """
        Busca título correspondente para um extrato sem vínculo.

        Critérios de busca (em ordem de prioridade):
        1. CNPJ exato + Valor exato (tolerância ±R$0.02)
        2. CNPJ raiz (8 dígitos) + Valor exato
        3. Apenas Valor exato (menos confiável)

        Args:
            extrato: ExtratoItem sem título vinculado

        Returns:
            ContasAReceber encontrado ou None
        """
        # Obter valor do extrato
        valor_extrato = float(extrato.valor or 0)
        if valor_extrato <= 0:
            return None

        tolerancia = 0.02  # R$ 0,02

        # Query base: títulos pendentes com valor aproximado
        query_base = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,  # Apenas não pagos
            ContasAReceber.valor_titulo.between(valor_extrato - tolerancia, valor_extrato + tolerancia)
        )

        # PRIORIDADE 1: CNPJ exato + Valor
        cnpj_extrato = self._normalizar_cnpj(extrato.cnpj_pagador)
        if cnpj_extrato and len(cnpj_extrato) >= 11:  # CPF ou CNPJ
            titulo = query_base.filter(
                db.func.regexp_replace(ContasAReceber.cnpj, '[^0-9]', '', 'g') == cnpj_extrato
            ).first()

            if titulo:
                return titulo

            # PRIORIDADE 2: CNPJ raiz (grupo empresarial) + Valor
            if len(cnpj_extrato) >= 8:
                raiz_cnpj = cnpj_extrato[:8]
                titulo = query_base.filter(
                    db.func.left(
                        db.func.regexp_replace(ContasAReceber.cnpj, '[^0-9]', '', 'g'),
                        8
                    ) == raiz_cnpj
                ).first()

                if titulo:
                    return titulo

        # PRIORIDADE 3: Apenas valor (se data também coincidir)
        # Menos confiável, só usa se tiver data de transação
        if extrato.data_transacao:
            titulo = query_base.filter(
                ContasAReceber.vencimento == extrato.data_transacao
            ).first()

            if titulo:
                return titulo

        return None

    def _vincular_extrato_ao_titulo(
        self,
        extrato: ExtratoItem,
        titulo: ContasAReceber,
        criterio: str = 'REVALIDACAO_AUTO'
    ) -> None:
        """
        Vincula um extrato a um título encontrado.

        Args:
            extrato: ExtratoItem a vincular
            titulo: ContasAReceber encontrado
            criterio: Critério usado para o match
        """
        extrato.titulo_receber_id = titulo.id
        extrato.titulo_nf = titulo.titulo_nf
        extrato.titulo_parcela = titulo.parcela_int
        extrato.titulo_valor = titulo.valor_titulo
        extrato.titulo_cliente = titulo.raz_social_red or titulo.raz_social
        extrato.titulo_cnpj = titulo.cnpj
        extrato.status_match = 'MATCH_ENCONTRADO'
        extrato.match_criterio = criterio
        extrato.match_score = 85  # Score automático (não é 100 pois não foi revisado)
        extrato.mensagem = f"Título vinculado automaticamente via revalidação"

    def sincronizar_extratos_por_cnab(self, lote_id: int) -> Dict[str, Any]:
        """
        Sincroniza extratos especificamente para itens de um lote CNAB.

        Útil após processar um lote CNAB para garantir que os extratos
        correspondentes sejam atualizados.

        Args:
            lote_id: ID do lote CNAB

        Returns:
            Dict com estatísticas
        """
        logger.info(f"[SYNC_EXTRATOS] Sincronizando extratos para lote CNAB #{lote_id}")

        stats = {
            'total': 0,
            'atualizados': 0,
            'ja_vinculados': 0,
            'sem_extrato': 0
        }

        try:
            # Buscar itens do lote que foram processados
            cnab_itens = CnabRetornoItem.query.filter(
                CnabRetornoItem.lote_id == lote_id,
                CnabRetornoItem.processado == True,
                CnabRetornoItem.conta_a_receber_id.isnot(None)
            ).all()

            for item in cnab_itens:
                stats['total'] += 1

                # Verificar se já tem extrato vinculado
                if item.extrato_item_id:
                    stats['ja_vinculados'] += 1
                    continue

                # Buscar extrato correspondente ao título
                extrato = ExtratoItem.query.filter(
                    ExtratoItem.titulo_receber_id == item.conta_a_receber_id,
                    ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO'])
                ).first()

                if extrato:
                    # Vincular CNAB ao extrato
                    item.extrato_item_id = extrato.id
                    item.status_match_extrato = 'SYNC_POS_PROCESSAMENTO'

                    # Atualizar extrato
                    extrato.status = 'CONCILIADO'
                    extrato.status_match = 'MATCH_ENCONTRADO'
                    extrato.match_criterio = f'VIA_CNAB_LOTE_{lote_id}'
                    extrato.mensagem = f"Vinculado automaticamente ao CNAB Lote #{lote_id}"

                    stats['atualizados'] += 1
                else:
                    stats['sem_extrato'] += 1

            db.session.commit()

            logger.info(f"[SYNC_EXTRATOS] Lote #{lote_id}: {stats}")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC_EXTRATOS] Erro ao sincronizar lote #{lote_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    def revalidar_todos_extratos_pendentes(self) -> Dict[str, Any]:
        """
        Revalida TODOS os extratos pendentes (sem limite de janela).

        Este método faz DUAS coisas:
        1. Para extratos COM título vinculado: verifica se título foi pago
        2. Para extratos SEM título vinculado: BUSCA título correspondente

        ⚠️ CUIDADO: Pode ser lento em bases grandes.
        Use apenas em situações de manutenção ou primeira execução.

        Returns:
            Dict com estatísticas
        """
        logger.warning("[SYNC_EXTRATOS] Iniciando revalidação COMPLETA de extratos pendentes")

        stats = {
            'total_verificados': 0,
            'com_titulo_verificados': 0,
            'sem_titulo_verificados': 0,
            'titulos_encontrados': 0,
            'titulos_pagos_detectados': 0,
            'atualizados_por_titulo': 0,
            'atualizados_por_cnab': 0,
            'sem_alteracao': 0,
            'erros': 0,
            'inicio': agora_utc_naive().isoformat()
        }

        try:
            # =====================================================
            # PARTE 1: Extratos COM título vinculado
            # Verificar se os títulos foram pagos
            # =====================================================
            logger.info("[SYNC_EXTRATOS] Parte 1: Verificando extratos COM título vinculado...")

            extratos_com_titulo = ExtratoItem.query.filter(
                ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
                ExtratoItem.titulo_receber_id.isnot(None)
            ).all()

            stats['com_titulo_verificados'] = len(extratos_com_titulo)
            logger.info(f"[SYNC_EXTRATOS] {len(extratos_com_titulo)} extratos COM título para verificar")

            for extrato in extratos_com_titulo:
                stats['total_verificados'] += 1
                try:
                    resultado = self._verificar_e_atualizar(extrato)
                    if resultado == 'titulo':
                        stats['atualizados_por_titulo'] += 1
                        stats['titulos_pagos_detectados'] += 1
                    elif resultado == 'cnab':
                        stats['atualizados_por_cnab'] += 1
                        stats['titulos_pagos_detectados'] += 1
                    else:
                        stats['sem_alteracao'] += 1
                except Exception as e:
                    logger.error(f"[SYNC_EXTRATOS] Erro extrato {extrato.id}: {e}")
                    stats['erros'] += 1

            # Commit intermediário
            db.session.commit()
            logger.info(f"[SYNC_EXTRATOS] Parte 1 concluída: {stats['titulos_pagos_detectados']} títulos pagos detectados")

            # =====================================================
            # PARTE 2: Extratos SEM título vinculado
            # Buscar títulos correspondentes
            # =====================================================
            logger.info("[SYNC_EXTRATOS] Parte 2: Buscando títulos para extratos SEM vínculo...")

            extratos_sem_titulo = ExtratoItem.query.filter(
                ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
                ExtratoItem.titulo_receber_id.is_(None)
            ).limit(10000).all()

            stats['sem_titulo_verificados'] = len(extratos_sem_titulo)
            logger.info(f"[SYNC_EXTRATOS] {len(extratos_sem_titulo)} extratos SEM título para processar")

            processados = 0
            for extrato in extratos_sem_titulo:
                stats['total_verificados'] += 1
                processados += 1

                try:
                    # Tentar encontrar título correspondente
                    titulo = self._buscar_titulo_para_extrato(extrato)

                    if titulo:
                        # Título encontrado - vincular
                        self._vincular_extrato_ao_titulo(
                            extrato,
                            titulo,
                            criterio='REVALIDACAO_AUTO_CNPJ_VALOR'
                        )
                        stats['titulos_encontrados'] += 1

                        # Verificar se título já está pago
                        if titulo.parcela_paga:
                            extrato.status = 'CONCILIADO'
                            extrato.mensagem = (
                                f"Título encontrado e já pago. "
                                f"NF: {titulo.titulo_nf}/{titulo.parcela}"
                            )
                            stats['titulos_pagos_detectados'] += 1
                    else:
                        stats['sem_alteracao'] += 1

                    # Log de progresso a cada 500 registros
                    if processados % 500 == 0:
                        db.session.commit()
                        logger.info(f"[SYNC_EXTRATOS] Progresso: {processados}/{len(extratos_sem_titulo)} processados")

                except Exception as e:
                    logger.error(f"[SYNC_EXTRATOS] Erro extrato {extrato.id}: {e}")
                    stats['erros'] += 1

            # Commit final
            db.session.commit()

            stats['fim'] = agora_utc_naive().isoformat()
            logger.info(f"[SYNC_EXTRATOS] Revalidação COMPLETA concluída: {stats}")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC_EXTRATOS] Erro geral na revalidação: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    def sincronizar_via_odoo(
        self,
        janela_minutos: int = 120,
        limite: int = 500
    ) -> Dict[str, Any]:
        """
        Sincronização incremental consultando diretamente o Odoo.

        Este método busca linhas de extrato (account.bank.statement.line) que foram
        modificadas na janela de tempo (via write_date) e verifica se:
        1. Foram conciliadas no Odoo (is_reconciled=True)
        2. Existem no nosso sistema como ExtratoItem pendente

        Benefício: Detecta conciliações feitas DIRETAMENTE no Odoo, não apenas
        via CNAB ou via nosso sistema.

        Args:
            janela_minutos: Janela de tempo para buscar modificações no Odoo
            limite: Limite de registros a processar

        Returns:
            Dict com estatísticas da sincronização
        """
        logger.info(f"[SYNC_EXTRATOS_ODOO] Iniciando sincronização via Odoo (janela={janela_minutos}min)")

        stats = {
            'linhas_odoo_verificadas': 0,
            'extratos_atualizados': 0,
            'extratos_nao_encontrados': 0,
            'ja_conciliados': 0,
            'erros': 0,
            'inicio': agora_utc_naive().isoformat()
        }

        try:
            # Obter conexão Odoo
            from app.odoo.utils.connection import get_odoo_connection
            conn = get_odoo_connection()
            if not conn.authenticate():
                raise Exception("Falha na autenticação com Odoo")

            # Calcular data de corte para write_date
            # Odoo armazena write_date em UTC
            data_corte = agora_utc_naive() - timedelta(minutes=janela_minutos)
            data_corte_str = data_corte.strftime('%Y-%m-%d %H:%M:%S')

            logger.info(f"[SYNC_EXTRATOS_ODOO] Buscando linhas modificadas desde {data_corte_str}")

            # Buscar linhas de extrato CONCILIADAS que foram modificadas recentemente
            # Essas são as linhas que foram reconciliadas no Odoo
            linhas_conciliadas = conn.search_read(
                'account.bank.statement.line',
                [
                    ['write_date', '>=', data_corte_str],
                    ['is_reconciled', '=', True],  # Conciliadas no Odoo
                    ['amount', '>', 0]  # Apenas recebimentos (entradas)
                ],
                fields=['id', 'date', 'amount', 'payment_ref', 'is_reconciled', 'write_date'],
                limit=limite
            )

            stats['linhas_odoo_verificadas'] = len(linhas_conciliadas)
            logger.info(f"[SYNC_EXTRATOS_ODOO] {len(linhas_conciliadas)} linhas conciliadas encontradas no Odoo")

            # Para cada linha conciliada no Odoo, verificar se temos ExtratoItem correspondente
            for linha in linhas_conciliadas:
                try:
                    statement_line_id = linha['id']

                    # Buscar ExtratoItem correspondente
                    extrato = ExtratoItem.query.filter_by(
                        statement_line_id=statement_line_id
                    ).first()

                    if not extrato:
                        stats['extratos_nao_encontrados'] += 1
                        continue

                    # Verificar se já está conciliado no nosso sistema
                    if extrato.status == 'CONCILIADO':
                        stats['ja_conciliados'] += 1
                        continue

                    # Atualizar status para CONCILIADO
                    extrato.status = 'CONCILIADO'
                    extrato.status_match = 'MATCH_ENCONTRADO'
                    extrato.match_criterio = 'SYNC_ODOO_WRITE_DATE'
                    extrato.mensagem = (
                        f"Conciliado no Odoo (detectado via write_date). "
                        f"Última modificação: {linha.get('write_date')}"
                    )
                    extrato.processado_em = agora_utc_naive()

                    stats['extratos_atualizados'] += 1

                    # Commit a cada 50 registros
                    if stats['extratos_atualizados'] % 50 == 0:
                        db.session.commit()
                        logger.info(f"[SYNC_EXTRATOS_ODOO] Progresso: {stats['extratos_atualizados']} atualizados")

                except Exception as e:
                    logger.error(f"[SYNC_EXTRATOS_ODOO] Erro na linha {linha.get('id')}: {e}")
                    stats['erros'] += 1

            # Commit final
            db.session.commit()

            stats['fim'] = agora_utc_naive().isoformat()
            logger.info(f"[SYNC_EXTRATOS_ODOO] Concluído: {stats}")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC_EXTRATOS_ODOO] Erro geral: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    def sincronizar_completo(
        self,
        janela_minutos: int = 120,
        limite: int = 500
    ) -> Dict[str, Any]:
        """
        Executa sincronização COMPLETA combinando todas as estratégias:

        1. Sincroniza via títulos pagos (ContasAReceber.parcela_paga)
        2. Sincroniza via CNAB processados
        3. Sincroniza via Odoo write_date (linhas conciliadas diretamente no Odoo)

        Ideal para executar no scheduler após SincronizacaoBaixasService.

        Args:
            janela_minutos: Janela de tempo para todas as buscas
            limite: Limite de registros por método

        Returns:
            Dict com estatísticas combinadas
        """
        logger.info(f"[SYNC_EXTRATOS] Iniciando sincronização COMPLETA (janela={janela_minutos}min)")

        resultado_final = {
            'success': True,
            'metodo_titulos': None,
            'metodo_odoo': None,
            'stats_combinadas': {
                'total_atualizados': 0,
                'erros_totais': 0
            }
        }

        # 1. Sincronizar via títulos pagos (método original)
        try:
            resultado_titulos = self.sincronizar_extratos_pendentes(
                janela_minutos=janela_minutos,
                limite=limite
            )
            resultado_final['metodo_titulos'] = resultado_titulos
            if resultado_titulos.get('success'):
                stats_t = resultado_titulos.get('stats', {})
                resultado_final['stats_combinadas']['total_atualizados'] += (
                    stats_t.get('atualizados_por_titulo', 0) +
                    stats_t.get('atualizados_por_cnab', 0)
                )
                resultado_final['stats_combinadas']['erros_totais'] += stats_t.get('erros', 0)
        except Exception as e:
            logger.error(f"[SYNC_EXTRATOS] Erro no método títulos: {e}")
            resultado_final['metodo_titulos'] = {'success': False, 'error': str(e)}
            resultado_final['stats_combinadas']['erros_totais'] += 1

        # 2. Sincronizar via Odoo write_date
        try:
            resultado_odoo = self.sincronizar_via_odoo(
                janela_minutos=janela_minutos,
                limite=limite
            )
            resultado_final['metodo_odoo'] = resultado_odoo
            if resultado_odoo.get('success'):
                stats_o = resultado_odoo.get('stats', {})
                resultado_final['stats_combinadas']['total_atualizados'] += stats_o.get('extratos_atualizados', 0)
                resultado_final['stats_combinadas']['erros_totais'] += stats_o.get('erros', 0)
        except Exception as e:
            logger.error(f"[SYNC_EXTRATOS] Erro no método Odoo: {e}")
            resultado_final['metodo_odoo'] = {'success': False, 'error': str(e)}
            resultado_final['stats_combinadas']['erros_totais'] += 1

        # Determinar sucesso geral
        resultado_final['success'] = (
            resultado_final['metodo_titulos'].get('success', False) or
            resultado_final['metodo_odoo'].get('success', False)
        )

        logger.info(f"[SYNC_EXTRATOS] Sincronização COMPLETA finalizada: {resultado_final['stats_combinadas']}")

        return resultado_final

    def revalidar_todos_extratos_via_odoo(self, batch_size: int = 500) -> Dict[str, Any]:
        """
        Revalida TODOS os extratos do sistema consultando o Odoo diretamente.

        Diferente do método `sincronizar_via_odoo()` que usa janela de tempo (write_date),
        este método busca TODOS os extratos pendentes no sistema e verifica no Odoo
        se a linha correspondente (statement_line_id) já foi conciliada.

        Ideal para:
        - Primeira sincronização do sistema
        - Reprocessamento após problemas de sincronização
        - Manutenção periódica para garantir consistência

        ⚠️ CUIDADO: Pode ser lento em bases grandes. Use com moderação.

        Args:
            batch_size: Quantidade de extratos a processar por lote Odoo (default 500)

        Returns:
            Dict com estatísticas da sincronização
        """
        logger.warning("[SYNC_EXTRATOS_ODOO_FULL] Iniciando revalidação COMPLETA de extratos via Odoo")

        stats = {
            'total_extratos_sistema': 0,
            'total_verificados': 0,
            'conciliados_no_odoo': 0,
            'nao_conciliados_no_odoo': 0,
            'statement_line_nao_encontrado': 0,
            'sem_statement_line_id': 0,
            'ja_conciliados_sistema': 0,
            'atualizados': 0,
            'erros': 0,
            'inicio': agora_utc_naive().isoformat()
        }

        try:
            # Obter conexão Odoo
            from app.odoo.utils.connection import get_odoo_connection
            conn = get_odoo_connection()
            if not conn.authenticate():
                raise Exception("Falha na autenticação com Odoo")

            # Contar extratos pendentes SEM statement_line_id (para informar)
            extratos_sem_stmt = ExtratoItem.query.filter(
                ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
                ExtratoItem.statement_line_id.is_(None)
            ).count()

            stats['sem_statement_line_id'] = extratos_sem_stmt
            if extratos_sem_stmt > 0:
                logger.warning(
                    f"[SYNC_EXTRATOS_ODOO_FULL] ⚠️  {extratos_sem_stmt} extratos pendentes SEM statement_line_id "
                    "(não podem ser verificados no Odoo - verifique importação)"
                )

            # Buscar TODOS os extratos pendentes que têm statement_line_id
            extratos_pendentes = ExtratoItem.query.filter(
                ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
                ExtratoItem.statement_line_id.isnot(None)
            ).all()

            stats['total_extratos_sistema'] = len(extratos_pendentes)
            logger.info(f"[SYNC_EXTRATOS_ODOO_FULL] {len(extratos_pendentes)} extratos pendentes com statement_line_id")

            if not extratos_pendentes:
                logger.info("[SYNC_EXTRATOS_ODOO_FULL] Nenhum extrato pendente para verificar")
                return {
                    'success': True,
                    'stats': stats,
                    'message': 'Nenhum extrato pendente para verificar'
                }

            # Coletar todos os statement_line_ids
            stmt_line_ids = [e.statement_line_id for e in extratos_pendentes if e.statement_line_id]

            # Criar mapeamento extrato_id -> extrato para acesso rápido
            extrato_por_stmt_id = {e.statement_line_id: e for e in extratos_pendentes}

            # Processar em lotes para não sobrecarregar o Odoo
            total_ids = len(stmt_line_ids)
            processados = 0

            for i in range(0, total_ids, batch_size):
                batch_ids = stmt_line_ids[i:i + batch_size]
                logger.info(f"[SYNC_EXTRATOS_ODOO_FULL] Processando lote {i//batch_size + 1}: IDs {i+1} a {min(i+batch_size, total_ids)}")

                try:
                    # Buscar status de conciliação no Odoo
                    linhas_odoo = conn.search_read(
                        'account.bank.statement.line',
                        [['id', 'in', batch_ids]],
                        fields=['id', 'is_reconciled', 'date', 'amount', 'payment_ref']
                    )

                    # Criar mapeamento por ID
                    odoo_por_id = {linha['id']: linha for linha in linhas_odoo}

                    # Atualizar extratos baseado no status do Odoo
                    for stmt_id in batch_ids:
                        stats['total_verificados'] += 1
                        extrato = extrato_por_stmt_id.get(stmt_id)

                        if not extrato:
                            continue

                        linha_odoo = odoo_por_id.get(stmt_id)

                        if not linha_odoo:
                            # Linha não encontrada no Odoo (pode ter sido deletada)
                            stats['statement_line_nao_encontrado'] += 1
                            continue

                        if linha_odoo.get('is_reconciled'):
                            # Conciliado no Odoo - atualizar nosso sistema
                            stats['conciliados_no_odoo'] += 1

                            if extrato.status != 'CONCILIADO':
                                extrato.status = 'CONCILIADO'
                                extrato.status_match = 'MATCH_ENCONTRADO'
                                extrato.match_criterio = 'SYNC_ODOO_FULL_REVALIDACAO'
                                extrato.mensagem = (
                                    f"Conciliado no Odoo (revalidação completa). "
                                    f"Ref: {linha_odoo.get('payment_ref', 'N/D')[:50] if linha_odoo.get('payment_ref') else 'N/D'}"
                                )
                                extrato.processado_em = agora_utc_naive()
                                stats['atualizados'] += 1
                            else:
                                stats['ja_conciliados_sistema'] += 1
                        else:
                            # Não conciliado no Odoo
                            stats['nao_conciliados_no_odoo'] += 1

                    processados += len(batch_ids)

                    # Commit por lote
                    db.session.commit()
                    logger.info(f"[SYNC_EXTRATOS_ODOO_FULL] Progresso: {processados}/{total_ids} ({100*processados//total_ids}%)")

                except Exception as e:
                    logger.error(f"[SYNC_EXTRATOS_ODOO_FULL] Erro no lote {i//batch_size + 1}: {e}")
                    stats['erros'] += len(batch_ids)
                    db.session.rollback()

            # Commit final
            db.session.commit()

            stats['fim'] = agora_utc_naive().isoformat()
            logger.info(f"[SYNC_EXTRATOS_ODOO_FULL] Revalidação concluída: {stats}")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC_EXTRATOS_ODOO_FULL] Erro geral: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    # =========================================================================
    # MÉTODOS DE IMPORTAÇÃO AUTOMÁTICA E VINCULAÇÃO CNAB↔EXTRATO
    # =========================================================================

    def importar_extratos_automatico(
        self,
        journals: List[str] = None,
        dias_retroativos: int = 7,
        limite: int = 500
    ) -> Dict[str, Any]:
        """
        Importa extratos novos do Odoo para o sistema local automaticamente.

        Este método é usado pelo scheduler para importar novos extratos que
        existem no Odoo mas ainda não foram importados no sistema local.

        Fluxo:
        1. Para cada journal configurado, busca statement lines não conciliadas
        2. Filtra as que já existem localmente (via statement_line_id)
        3. Importa as novas via ExtratoService.importar_extrato()

        Args:
            journals: Lista de códigos de journal (GRA1, SIC, BRAD, etc.)
                      Se None, usa ['GRA1'] como padrão
            dias_retroativos: Quantos dias para trás buscar (default: 7)
            limite: Limite de registros por journal (default: 500)

        Returns:
            Dict com estatísticas de importação
        """
        import os
        from datetime import date

        if journals is None:
            # Configurável via variável de ambiente
            journals_env = os.environ.get('JOURNALS_EXTRATO', 'GRA1')
            journals = [j.strip() for j in journals_env.split(',')]

        stats = {
            'inicio': agora_utc_naive().isoformat(),
            'journals_processados': 0,
            'total_importados': 0,
            'total_ja_existentes': 0,
            'total_erros': 0,
            'detalhes_por_journal': {}
        }

        logger.info(f"[IMPORT_EXTRATOS_AUTO] Iniciando importação automática: journals={journals}, dias={dias_retroativos}")

        try:
            from app.financeiro.services.extrato_service import ExtratoService

            data_inicio = date.today() - timedelta(days=dias_retroativos)
            data_fim = date.today()

            for journal_code in journals:
                for tipo in ['entrada', 'saida']:
                    chave_detalhe = f"{journal_code}_{tipo}"
                    try:
                        tipo_label = 'recebimentos' if tipo == 'entrada' else 'pagamentos'
                        logger.info(f"[IMPORT_EXTRATOS_AUTO] Processando journal: {journal_code} ({tipo_label})")

                        extrato_service = ExtratoService()

                        # Importar extrato usando o service existente
                        lote = extrato_service.importar_extrato(
                            journal_code=journal_code,
                            data_inicio=data_inicio,
                            data_fim=data_fim,
                            limit=limite,
                            criado_por='SCHEDULER_AUTO',
                            tipo_transacao=tipo,
                        )

                        stats['journals_processados'] += 1
                        stats['total_importados'] += extrato_service.estatisticas.get('importados', 0)
                        stats['detalhes_por_journal'][chave_detalhe] = {
                            'lote_id': lote.id if lote else None,
                            'tipo_transacao': tipo,
                            'importados': extrato_service.estatisticas.get('importados', 0),
                            'com_cnpj': extrato_service.estatisticas.get('com_cnpj', 0),
                            'sem_cnpj': extrato_service.estatisticas.get('sem_cnpj', 0),
                            'erros': extrato_service.estatisticas.get('erros', 0)
                        }

                        logger.info(
                            f"[IMPORT_EXTRATOS_AUTO] Journal {journal_code} ({tipo_label}): "
                            f"{extrato_service.estatisticas.get('importados', 0)} importados"
                        )

                    except Exception as e:
                        logger.error(f"[IMPORT_EXTRATOS_AUTO] Erro no journal {journal_code} ({tipo}): {e}")
                        stats['total_erros'] += 1
                        stats['detalhes_por_journal'][chave_detalhe] = {
                            'tipo_transacao': tipo,
                            'erro': str(e)
                        }

            db.session.commit()

            stats['fim'] = agora_utc_naive().isoformat()
            logger.info(f"[IMPORT_EXTRATOS_AUTO] Importação concluída: {stats['total_importados']} extratos importados")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[IMPORT_EXTRATOS_AUTO] Erro geral: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    def vincular_cnab_extratos_pendentes(self) -> Dict[str, Any]:
        """
        Busca CNABs processados sem extrato vinculado e tenta fazer match
        com extratos existentes. Atualiza status do extrato se CNAB já baixou título.

        Este método resolve o problema de ordem de importação:
        - Quando CNAB é importado ANTES do extrato
        - O match não acontece no momento do CNAB
        - Quando extrato é importado depois, este método vincula retroativamente

        Critérios de match (mesmos do _buscar_extrato_correspondente do CNAB):
        1. Data ocorrência (CNAB) = Data transação (Extrato)
        2. Valor pago ≈ Valor (tolerância ±R$0.02)
        3. CNPJ pagador (opcional, aumenta score)

        Returns:
            Dict com estatísticas:
            {
                'cnabs_verificados': N,
                'matches_encontrados': N,
                'extratos_atualizados': N,
                'odoo_reconciliados': N,
                'erros': N
            }
        """
        stats = {
            'inicio': agora_utc_naive().isoformat(),
            'cnabs_verificados': 0,
            'matches_encontrados': 0,
            'extratos_atualizados': 0,
            'odoo_reconciliados': 0,
            'erros': 0
        }

        logger.info("[VINCULAR_CNAB_EXTRATO] Iniciando vinculação retroativa CNAB↔Extrato")

        try:
            # Buscar CNABs processados sem extrato vinculado (liquidações)
            cnabs_sem_extrato = CnabRetornoItem.query.filter(
                CnabRetornoItem.processado == True,
                CnabRetornoItem.extrato_item_id.is_(None),
                CnabRetornoItem.codigo_ocorrencia.in_(['06', '10', '17']),  # Liquidações
                CnabRetornoItem.conta_a_receber_id.isnot(None)  # Tem título vinculado
            ).all()

            logger.info(f"[VINCULAR_CNAB_EXTRATO] {len(cnabs_sem_extrato)} CNABs sem extrato encontrados")

            for cnab in cnabs_sem_extrato:
                stats['cnabs_verificados'] += 1

                try:
                    # Buscar extrato correspondente
                    extrato = self._buscar_extrato_para_cnab(cnab)

                    if extrato:
                        stats['matches_encontrados'] += 1

                        # Vincular CNAB ao extrato
                        cnab.extrato_item_id = extrato.id
                        cnab.status_match_extrato = 'VINCULADO_POSTERIOR'

                        # Atualizar extrato se ainda não estiver conciliado
                        if extrato.status not in ['CONCILIADO']:
                            extrato.status = 'CONCILIADO'
                            extrato.status_match = 'VIA_CNAB_RETROATIVO'
                            extrato.aprovado = True
                            extrato.aprovado_por = 'VINCULAR_CNAB_AUTO'
                            extrato.aprovado_em = agora_utc_naive()
                            extrato.processado_em = agora_utc_naive()
                            extrato.mensagem = f"Conciliado retroativamente via CNAB item {cnab.id}"

                            # Vincular título se não tiver
                            if not extrato.titulo_receber_id and cnab.conta_a_receber_id:
                                titulo = cnab.conta_a_receber
                                extrato.titulo_receber_id = cnab.conta_a_receber_id
                                if titulo:
                                    extrato.titulo_nf = titulo.titulo_nf
                                    extrato.titulo_parcela = titulo.parcela_int
                                    extrato.titulo_valor = float(titulo.valor_titulo) if titulo.valor_titulo else None
                                    extrato.titulo_cliente = titulo.raz_social_red or titulo.raz_social
                                    extrato.titulo_cnpj = titulo.cnpj

                            stats['extratos_atualizados'] += 1

                            # Tentar reconciliar no Odoo se tiver statement_line_id
                            if extrato.statement_line_id:
                                try:
                                    from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService
                                    conciliador = ExtratoConciliacaoService()
                                    odoo_result = conciliador.conciliar_item(extrato.id, usuario='VINCULAR_CNAB_AUTO')
                                    if odoo_result.get('success'):
                                        stats['odoo_reconciliados'] += 1
                                except Exception as odoo_err:
                                    logger.warning(f"[VINCULAR_CNAB_EXTRATO] Erro Odoo para extrato {extrato.id}: {odoo_err}")

                except Exception as e:
                    logger.error(f"[VINCULAR_CNAB_EXTRATO] Erro no CNAB {cnab.id}: {e}")
                    stats['erros'] += 1

            db.session.commit()

            stats['fim'] = agora_utc_naive().isoformat()
            logger.info(
                f"[VINCULAR_CNAB_EXTRATO] Concluído: "
                f"{stats['matches_encontrados']} matches, "
                f"{stats['extratos_atualizados']} extratos atualizados, "
                f"{stats['odoo_reconciliados']} reconciliados no Odoo"
            )

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[VINCULAR_CNAB_EXTRATO] Erro geral: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': stats
            }

    def _buscar_extrato_para_cnab(self, cnab: CnabRetornoItem) -> Optional[ExtratoItem]:
        """
        Busca extrato correspondente a um item CNAB.

        Critérios de match:
        1. Data ocorrência = Data transação
        2. Valor pago ≈ Valor (tolerância ±R$0.02)
        3. CNPJ pagador (opcional)
        4. Status não conciliado

        Args:
            cnab: CnabRetornoItem para buscar correspondência

        Returns:
            ExtratoItem encontrado ou None
        """
        if not cnab.data_ocorrencia:
            return None

        valor_cnab = float(cnab.valor_pago or 0)
        tolerancia = 0.02

        # Query base
        query = db.session.query(ExtratoItem).join(ExtratoLote).filter(
            ExtratoItem.data_transacao == cnab.data_ocorrencia,
            ExtratoItem.valor.between(valor_cnab - tolerancia, valor_cnab + tolerancia),
            ExtratoItem.status.in_(['PENDENTE', 'MATCH_ENCONTRADO', 'APROVADO']),
            ExtratoLote.tipo_transacao == 'entrada'  # Apenas recebimentos
        )

        # Normalizar CNPJ
        cnpj_cnab = ''.join(filter(str.isdigit, str(cnab.cnpj_pagador or '')))

        if cnpj_cnab and len(cnpj_cnab) >= 8:
            # Tentar match por CNPJ exato
            extrato = query.filter(
                db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g') == cnpj_cnab
            ).first()

            if extrato:
                return extrato

            # Tentar match por raiz do CNPJ (8 primeiros dígitos)
            raiz_cnpj = cnpj_cnab[:8]
            extrato = query.filter(
                db.func.left(
                    db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g'),
                    8
                ) == raiz_cnpj
            ).first()

            if extrato:
                return extrato

        # Match apenas por data + valor
        return query.first()
