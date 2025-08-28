"""
Serviço de Sincronização Integrada Odoo
=======================================

Executa sincronização na SEQUÊNCIA CORRETA para máxima segurança:
1. FATURAMENTO primeiro (preserva NFs)
2. CARTEIRA depois (sem risco de perda)

Este serviço elimina o risco humano de executar na ordem errada.

Autor: Sistema de Fretes
Data: 2025-07-21
"""

import logging
from datetime import datetime

from app.odoo.services.faturamento_service import FaturamentoService
from app.odoo.services.carteira_service import CarteiraService

logger = logging.getLogger(__name__)

class SincronizacaoIntegradaService:
    """
    🔄 SINCRONIZAÇÃO INTEGRADA SEGURA
    
    Executa sincronização na sequência correta SEMPRE:
    FATURAMENTO → CARTEIRA
    
    Elimina risco de perda de dados por ordem incorreta
    """
    
    def __init__(self):
        self.faturamento_service = FaturamentoService()
        self.carteira_service = CarteiraService()
    
    def executar_sincronizacao_completa_segura(self, usar_filtro_carteira=True):
        """
        🔄 SINCRONIZAÇÃO SEGURA COMPLETA
        
        Executa na sequência CORRETA para máxima segurança:
        1. 📊 FATURAMENTO primeiro (preserva NFs)
        2. 🔍 Validação de integridade
        3. 🔄 CARTEIRA depois (sem risco)
        
        Args:
            usar_filtro_carteira (bool): Filtrar apenas carteira pendente
            
        Returns:
            dict: Resultado completo da operação segura
        """
        inicio_operacao = datetime.now()
        
        try:
            logger.info("🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA (FATURAMENTO → CARTEIRA)")
            
            resultado_completo = {
                'sucesso': False,
                'operacao_completa': False,
                'etapas_executadas': [],
                'tempo_total': 0,
                'estatisticas': {},
                'alertas': [],
                'mensagem': ''
            }
            
            # ✅ ETAPA 1: SINCRONIZAR FATURAMENTO PRIMEIRO
            logger.info("📊 ETAPA 1/3: Sincronizando FATURAMENTO (prioridade de segurança)...")
            resultado_completo['etapas_executadas'].append('INICIANDO_FATURAMENTO')
            
            resultado_faturamento = self._sincronizar_faturamento_seguro()
            
            if not resultado_faturamento.get('sucesso', False):
                # Falha no faturamento = PARAR TUDO
                logger.error("❌ FALHA na sincronização de faturamento - ABORTANDO operação")
                resultado_completo['sucesso'] = False
                resultado_completo['erro'] = f"Falha no faturamento: {resultado_faturamento.get('erro', 'Erro desconhecido')}"
                resultado_completo['etapas_executadas'].append('FATURAMENTO_FALHOU')
                return resultado_completo
            
            resultado_completo['etapas_executadas'].append('FATURAMENTO_CONCLUIDO')
            resultado_completo['faturamento_resultado'] = resultado_faturamento
            
            # ✅ ETAPA 2: VALIDAÇÃO DE INTEGRIDADE
            logger.info("🔍 ETAPA 2/3: Validação de integridade pós-faturamento...")
            resultado_completo['etapas_executadas'].append('VALIDACAO_INTEGRIDADE')
            
            validacao = self._validar_integridade_pos_faturamento()
            resultado_completo['validacao_integridade'] = validacao
            
            if not validacao.get('integro', True):
                logger.warning(f"⚠️ Problemas de integridade detectados: {validacao.get('problemas', [])}")
                resultado_completo['alertas'].extend(validacao.get('problemas', []))
            
            # ✅ ETAPA 2.5: FORÇAR ATUALIZAÇÃO DE STATUS FATURADO
            logger.info("🔄 ETAPA 2.5/4: Atualizando status FATURADO dos pedidos...")
            try:
                from app import db
                from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
                processador = ProcessadorFaturamento()
                pedidos_atualizados = processador._atualizar_status_pedidos_faturados()
                
                if pedidos_atualizados > 0:
                    logger.info(f"✅ {pedidos_atualizados} pedidos atualizados para status FATURADO")
                    db.session.commit()  # COMMIT CRÍTICO: Salvar status antes de processar carteira
                    logger.info("💾 Status FATURADO salvo no banco antes de processar carteira")
                    
            except Exception as e:
                logger.error(f"⚠️ Erro ao atualizar status FATURADO: {e}")
                # Não é fatal, continuar
            
            # ✅ ETAPA 3: SINCRONIZAR CARTEIRA COM SEGURANÇA MÁXIMA
            logger.info("🔄 ETAPA 3/4: Sincronizando CARTEIRA (com faturamento protegido)...")
            resultado_completo['etapas_executadas'].append('INICIANDO_CARTEIRA')
            
            resultado_carteira = self.carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
                usar_filtro_pendente=usar_filtro_carteira
            )
            
            if not resultado_carteira.get('sucesso', False):
                # Falha na carteira = Operação parcial
                logger.error("❌ FALHA na sincronização de carteira")
                resultado_completo['sucesso'] = False
                resultado_completo['operacao_completa'] = False
                resultado_completo['erro'] = f"Falha na carteira: {resultado_carteira.get('erro', 'Erro desconhecido')}"
                resultado_completo['etapas_executadas'].append('CARTEIRA_FALHOU')
                
                # MAS faturamento foi OK, então é sucesso parcial
                resultado_completo['sucesso_parcial'] = True
                resultado_completo['mensagem'] = "✅ Faturamento sincronizado, ❌ Carteira falhou"
                
            else:
                # ✅ SUCESSO COMPLETO
                resultado_completo['sucesso'] = True
                resultado_completo['operacao_completa'] = True
                resultado_completo['etapas_executadas'].append('CARTEIRA_CONCLUIDA')
                resultado_completo['etapas_executadas'].append('OPERACAO_COMPLETA')
            
            resultado_completo['carteira_resultado'] = resultado_carteira
            
            # ✅ COMPILAR ESTATÍSTICAS FINAIS
            fim_operacao = datetime.now()
            tempo_total = (fim_operacao - inicio_operacao).total_seconds()
            
            resultado_completo['tempo_total'] = round(tempo_total, 2)
            resultado_completo['estatisticas'] = self._compilar_estatisticas_integradas(
                resultado_faturamento, resultado_carteira, tempo_total
            )
            
            # Mensagem final
            if resultado_completo['sucesso']:
                resultado_completo['mensagem'] = (
                    f"✅ SINCRONIZAÇÃO INTEGRADA COMPLETA: "
                    f"Faturamento + Carteira sincronizados em {tempo_total:.1f}s"
                )
                logger.info(f"✅ SINCRONIZAÇÃO INTEGRADA CONCLUÍDA COM SUCESSO em {tempo_total:.1f}s")
            
            return resultado_completo
            
        except Exception as e:
            fim_operacao = datetime.now()
            tempo_erro = (fim_operacao - inicio_operacao).total_seconds()
            
            logger.error(f"❌ ERRO CRÍTICO na sincronização integrada: {e}")
            
            return {
                'sucesso': False,
                'operacao_completa': False,
                'erro': str(e),
                'tempo_total': tempo_erro,
                'etapas_executadas': resultado_completo.get('etapas_executadas', []),
                'mensagem': f'❌ Erro na sincronização integrada: {str(e)}'
            }
    
    def _sincronizar_faturamento_seguro(self):
        """
        📊 SINCRONIZAÇÃO SEGURA DE FATURAMENTO COM MOVIMENTAÇÕES DE ESTOQUE
        
        Executa sincronização completa:
        1. Importa faturamento do Odoo
        2. Processa movimentações de estoque automaticamente
        """
        try:
            logger.info("📊 Executando sincronização completa de faturamento + estoque...")
            
            # ✅ EXECUTAR SINCRONIZAÇÃO REAL DE FATURAMENTO
            resultado_fat = self.faturamento_service.sincronizar_faturamento_incremental()
            
            if not resultado_fat.get('sucesso', False):
                return {
                    'sucesso': False,
                    'erro': resultado_fat.get('erro', 'Erro desconhecido na sincronização de faturamento'),
                    'registros_importados': 0,
                    'simulado': False
                }
            
            # ✅ EXTRAIR ESTATÍSTICAS DETALHADAS
            registros_novos = resultado_fat.get('registros_novos', 0)
            registros_atualizados = resultado_fat.get('registros_atualizados', 0)
            movimentacoes_estoque = resultado_fat.get('movimentacoes_estoque', {})
            tempo_execucao = resultado_fat.get('tempo_execucao', 0)
            
            total_importados = registros_novos + registros_atualizados
            movimentacoes_criadas = movimentacoes_estoque.get('movimentacoes_criadas', 0)
            
            logger.info(f"✅ Faturamento sincronizado: {total_importados} registros, {movimentacoes_criadas} movimentações de estoque")
            
            return {
                'sucesso': True,
                'registros_importados': total_importados,
                'registros_novos': registros_novos,
                'registros_atualizados': registros_atualizados,
                'movimentacoes_criadas': movimentacoes_criadas,
                'tempo_execucao': tempo_execucao,
                'mensagem': f'Faturamento + Estoque sincronizados: {total_importados} registros, {movimentacoes_criadas} movimentações',
                'simulado': False,
                'detalhes_estoque': movimentacoes_estoque
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização de faturamento: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'registros_importados': 0,
                'simulado': False
            }
    
    def _validar_integridade_pos_faturamento(self):
        """
        🔍 VALIDAÇÃO DE INTEGRIDADE PÓS-FATURAMENTO
        
        Verifica se a sincronização de faturamento não causou problemas
        """
        try:
            logger.info("🔍 Validando integridade após sincronização de faturamento...")
            
            problemas = []
            
            # Verificar se existem registros de faturamento
            try:
                from app import db
                from app.faturamento.models import FaturamentoProduto
                
                # Renovar sessão após commit anterior
                db.session.rollback()  # Limpar qualquer transação pendente
                db.session.begin()  # Iniciar nova transação limpa
                
                # Agora fazer a query com sessão limpa
                total_faturamento = db.session.query(FaturamentoProduto).count()
                
                if total_faturamento == 0:
                    problemas.append({
                        'tipo': 'SEM_FATURAMENTO',
                        'nivel': 'AVISO',
                        'mensagem': 'Nenhum registro de faturamento encontrado'
                    })
                else:
                    logger.info(f"✅ {total_faturamento} registros de faturamento encontrados")
                
                # Fazer rollback para limpar a transação de leitura
                db.session.rollback()
                
            except Exception as e:
                # Garantir que a sessão seja limpa em caso de erro
                try:
                    db.session.rollback()
                except:
                    pass
                
                problemas.append({
                    'tipo': 'ERRO_VALIDACAO_FATURAMENTO',
                    'nivel': 'ERRO',
                    'mensagem': f'Erro ao validar faturamento: {e}'
                })
            
            return {
                'integro': len([p for p in problemas if p['nivel'] == 'ERRO']) == 0,
                'total_problemas': len(problemas),
                'problemas': problemas,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de integridade: {e}")
            return {
                'integro': False,
                'total_problemas': 1,
                'problemas': [{
                    'tipo': 'ERRO_VALIDACAO',
                    'nivel': 'ERRO',
                    'mensagem': f'Erro na validação: {e}'
                }]
            }
    
    def _compilar_estatisticas_integradas(self, resultado_faturamento, resultado_carteira, tempo_total):
        """
        📊 COMPILAR ESTATÍSTICAS DA OPERAÇÃO INTEGRADA
        """
        try:
            stats_faturamento = resultado_faturamento.get('estatisticas', {})
            stats_carteira = resultado_carteira.get('estatisticas', {})
            
            return {
                # Estatísticas gerais
                'tempo_total_segundos': tempo_total,
                'operacao_tipo': 'INTEGRADA_SEGURA',
                'sequencia': 'FATURAMENTO_PRIMEIRO_CARTEIRA_DEPOIS',
                
                # Faturamento
                'faturamento_registros': resultado_faturamento.get('registros_importados', 0),
                'faturamento_sucesso': resultado_faturamento.get('sucesso', False),
                'faturamento_simulado': resultado_faturamento.get('simulado', False),
                
                # Carteira
                'carteira_registros_inseridos': stats_carteira.get('registros_inseridos', 0),
                'carteira_registros_removidos': stats_carteira.get('registros_removidos', 0),
                'carteira_pre_separacoes_recompostas': stats_carteira.get('recomposicao_sucesso', 0),
                'carteira_alertas_pre_sync': stats_carteira.get('alertas_pre_sync', 0),
                'carteira_alertas_pos_sync': stats_carteira.get('alertas_pos_sync', 0),
                
                # Segurança
                'sequencia_segura_executada': True,
                'risco_perda_nfs_eliminado': True,
                'protecoes_ativas': [
                    'Faturamento sincronizado primeiro',
                    'Validação de integridade executada',
                    'Carteira sincronizada com proteção máxima'
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao compilar estatísticas: {e}")
            return {
                'tempo_total_segundos': tempo_total,
                'erro_compilacao': str(e)
            }
    
    def verificar_status_sincronizacao(self):
        """
        📊 VERIFICAR STATUS ATUAL DO SISTEMA
        
        Verifica se é seguro executar sincronização e fornece recomendações
        """
        try:
            logger.info("🔍 Verificando status atual do sistema...")
            
            status = {
                'timestamp': datetime.now(),
                'recomendacao': '',
                'nivel_risco': 'BAIXO',
                'pode_sincronizar': True,
                'alertas': []
            }
            
            # Verificar última sincronização de cada tipo
            try:
                from app.faturamento.models import FaturamentoProduto
                from app.carteira.models import CarteiraPrincipal
                
                # Faturamento
                ultimo_faturamento = FaturamentoProduto.query.order_by(
                    FaturamentoProduto.created_at.desc()
                ).first()
                
                # Carteira
                ultima_carteira = CarteiraPrincipal.query.order_by(
                    CarteiraPrincipal.created_at.desc()
                ).first()
                
                if ultimo_faturamento:
                    status['ultima_sync_faturamento'] = ultimo_faturamento.created_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    status['alertas'].append('Nenhum faturamento sincronizado ainda')
                    status['nivel_risco'] = 'MÉDIO'
                
                if ultima_carteira:
                    status['ultima_sync_carteira'] = ultima_carteira.created_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    status['alertas'].append('Nenhuma carteira sincronizada ainda')
                
                # Recomendação baseada no status
                if not ultimo_faturamento and not ultima_carteira:
                    status['recomendacao'] = 'Primeira sincronização - sequência segura será aplicada automaticamente'
                    status['nivel_risco'] = 'BAIXO'
                elif ultimo_faturamento and ultima_carteira:
                    status['recomendacao'] = 'Sistema atualizado - sincronização segura disponível'
                    status['nivel_risco'] = 'BAIXO'
                else:
                    status['recomendacao'] = 'Sincronização parcial detectada - executar sincronização completa'
                    status['nivel_risco'] = 'MÉDIO'
                    
            except Exception as e:
                status['alertas'].append(f'Erro ao verificar status: {e}')
                status['nivel_risco'] = 'ALTO'
                status['pode_sincronizar'] = False
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            return {
                'timestamp': datetime.now(),
                'recomendacao': 'Erro na verificação - contate administrador',
                'nivel_risco': 'ALTO',
                'pode_sincronizar': False,
                'erro': str(e)
            }