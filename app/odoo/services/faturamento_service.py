"""
Serviço de Faturamento - Integração Odoo Correta
===============================================

Este serviço implementa a integração correta com o Odoo usando múltiplas consultas
ao invés de campos com "/" que não funcionam.

Baseado no mapeamento_faturamento.csv e usando FaturamentoMapper hardcoded.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import sessionmaker

from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.faturamento_mapper import FaturamentoMapper
from app import db

logger = logging.getLogger(__name__)

class FaturamentoService:
    """
    Serviço para integração de faturamento com Odoo
    Usa FaturamentoMapper hardcoded com sistema de múltiplas queries
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mapper = FaturamentoMapper()
        self.connection = get_odoo_connection()
    
    def importar_faturamento_odoo(self, filtros: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Importa dados de faturamento do Odoo usando a abordagem CORRETA
        
        Args:
            filtros: Filtros para aplicar na consulta
            
        Returns:
            Resultado da importação
        """
        try:
            self.logger.info("Iniciando importação de faturamento do Odoo")
            
            # Conectar ao Odoo
            if not self.connection:
                raise Exception("Não foi possível conectar ao Odoo")
            
            # Aplicar filtros para faturamento
            filtros_faturamento = {
                'modelo': 'faturamento'
            }
            
            # Adicionar filtros opcionais
            if filtros:
                if filtros.get('data_inicio'):
                    filtros_faturamento['data_inicio'] = filtros['data_inicio']
                if filtros.get('data_fim'):
                    filtros_faturamento['data_fim'] = filtros['data_fim']
            
            # Buscar dados brutos do Odoo - account.move.line (linhas de fatura)
            logger.info("Buscando dados de faturamento do Odoo...")
            
            # Filtro para linhas de fatura ativas
            domain = [('move_id.state', '=', 'posted')]  # Faturas postadas
            
            # Campos básicos para buscar de account.move.line
            campos_basicos = [
                'id', 'move_id', 'partner_id', 'product_id', 
                'quantity', 'price_unit', 'price_total', 'date'
            ]
            
            dados_odoo_brutos = self.connection.search_read(
                'account.move.line', domain, campos_basicos, limit=100
            )
            
            if dados_odoo_brutos:
                logger.info(f"✅ SUCESSO: {len(dados_odoo_brutos)} registros de faturamento encontrados")
                
                # Processar dados usando mapeamento completo com múltiplas queries
                dados_processados = self._processar_dados_faturamento_com_multiplas_queries(dados_odoo_brutos)
                
                return {
                    'sucesso': True,
                    'dados': dados_processados,
                    'total_registros': len(dados_processados),
                    'mensagem': f'✅ {len(dados_processados)} registros de faturamento processados'
                }
            else:
                logger.warning("Nenhum dado de faturamento encontrado")
                return {
                    'sucesso': True,
                    'dados': [],
                    'total_registros': 0,
                    'mensagem': 'Nenhum faturamento encontrado'
                }
            
        except Exception as e:
            logger.error(f"❌ ERRO na importação: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': [],
                'mensagem': 'Erro ao importar faturamento'
            }
    
    def _processar_dados_faturamento_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
        """
        Processa dados de faturamento usando o sistema completo de múltiplas queries
        Resolve campos complexos que precisam de consultas relacionadas
        """
        try:
            logger.info("Processando faturamento com sistema de múltiplas queries...")
            
            # Usar o mapeamento completo que suporta múltiplas queries
            dados_mapeados = self.mapper.mapear_para_faturamento_completo(dados_odoo_brutos, self.connection)
            
            # Mostrar estatísticas do mapeamento
            stats = self.mapper.obter_estatisticas_mapeamento()
            logger.info(f"📊 Estatísticas do mapeamento de faturamento:")
            logger.info(f"   Total de campos: {stats['total_campos']}")
            logger.info(f"   Campos simples: {stats['campos_simples']} ({stats['percentual_simples']:.1f}%)")
            logger.info(f"   Campos complexos: {stats['campos_complexos']} ({stats['percentual_complexos']:.1f}%)")
            logger.info(f"   Campos calculados: {stats['campos_calculados']} ({stats['percentual_calculados']:.1f}%)")
            
            # Contar campos resolvidos vs não resolvidos
            campos_resolvidos = 0
            campos_nulos = 0
            
            for item in dados_mapeados:
                for campo, valor in item.items():
                    if valor is not None and valor != '':
                        campos_resolvidos += 1
                    else:
                        campos_nulos += 1
            
            taxa_resolucao = (campos_resolvidos / (campos_resolvidos + campos_nulos) * 100) if (campos_resolvidos + campos_nulos) > 0 else 0
            
            logger.info(f"🎯 Taxa de resolução de campos: {taxa_resolucao:.1f}%")
            logger.info(f"   Campos resolvidos: {campos_resolvidos}")
            logger.info(f"   Campos nulos: {campos_nulos}")
            
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento com múltiplas queries: {e}")
            return []
    
    def _mapear_status(self, status_odoo: Optional[str]) -> str:
        """
        Mapeia status do Odoo para status do sistema
        """
        if not status_odoo:
            return 'ATIVO'
        
        status_map = {
            'draft': 'RASCUNHO',
            'sent': 'ENVIADO',
            'sale': 'ATIVO',
            'done': 'ATIVO',
            'cancel': 'CANCELADO'
        }
        
        return status_map.get(status_odoo.lower(), 'ATIVO')
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data para datetime
        """
        if not date_str:
            return None
        
        try:
            # Formato do Odoo: 2025-07-14 20:19:52
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return dt  # Retorna datetime para compatibilidade
        except ValueError:
            try:
                # Formato de data apenas: 2025-07-14
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt  # Retorna datetime para compatibilidade
            except ValueError:
                self.logger.warning(f"Formato de data inválido: {date_str}")
                return None
    
    def _consolidar_faturamento(self, dados_faturamento: List[Dict]) -> Dict[str, Any]:
        """
        Consolida dados de faturamento para RelatorioFaturamentoImportado
        """
        try:
            self.logger.info("Consolidando dados para RelatorioFaturamentoImportado")
            
            total_consolidado = 0
            total_relatorio_importado = 0
            
            # Agrupar por NF para consolidação
            nfs_consolidadas = {}
            
            for dado in dados_faturamento:
                numero_nf = dado.get('numero_nf')
                if not numero_nf:
                    continue
                    
                nf_key = f"{numero_nf}_{dado.get('cnpj_cliente', '')}"
                
                if nf_key not in nfs_consolidadas:
                    nfs_consolidadas[nf_key] = {
                        'numero_nf': numero_nf,
                        'nome_cliente': dado.get('nome_cliente'),
                        'cnpj_cliente': dado.get('cnpj_cliente'),
                        'data_fatura': dado.get('data_fatura'),
                        'valor_total': 0,
                        'origem': dado.get('origem'),
                        'incoterm': dado.get('incoterm'),
                        'vendedor': dado.get('vendedor'),
                        'municipio': dado.get('municipio'),
                        'status': dado.get('status'),
                        'itens': []
                    }
                
                # Adicionar valor do item ao total
                valor_item = dado.get('valor_total_item_nf') or 0
                nfs_consolidadas[nf_key]['valor_total'] += valor_item
                
                # Adicionar item
                nfs_consolidadas[nf_key]['itens'].append({
                    'codigo_produto': dado.get('codigo_produto'),
                    'nome_produto': dado.get('nome_produto'),
                    'quantidade': dado.get('quantidade'),
                    'valor_total': valor_item
                })
                
                total_consolidado += 1
            
            # Salvar dados consolidados
            for nf_key, dados_nf in nfs_consolidadas.items():
                try:
                    # Verificar se já existe
                    existe = db.session.query(RelatorioFaturamentoImportado).filter_by(
                        numero_nf=dados_nf['numero_nf'],
                        cnpj_cliente=dados_nf['cnpj_cliente']
                    ).first()
                    
                    if not existe:
                        relatorio = RelatorioFaturamentoImportado()
                        relatorio.numero_nf = dados_nf['numero_nf']
                        relatorio.nome_cliente = dados_nf['nome_cliente']
                        relatorio.cnpj_cliente = dados_nf['cnpj_cliente']
                        data_fatura = self._parse_date(dados_nf['data_fatura'])
                        relatorio.data_fatura = data_fatura.date() if data_fatura else None
                        relatorio.valor_total = dados_nf['valor_total']
                        relatorio.origem = dados_nf['origem']
                        relatorio.incoterm = dados_nf['incoterm']
                        relatorio.vendedor = dados_nf['vendedor']
                        relatorio.municipio = dados_nf['municipio']
                        relatorio.status_faturamento = dados_nf['status']
                        relatorio.data_importacao = datetime.now()
                        relatorio.origem_importacao = 'odoo_integracao'
                        
                        db.session.add(relatorio)
                        total_relatorio_importado += 1
                    else:
                        # Atualizar registro existente
                        existe.valor_total = dados_nf['valor_total']
                        existe.status_faturamento = dados_nf['status']
                        existe.data_importacao = datetime.now()
                        existe.origem_importacao = 'odoo_integracao'
                
                except Exception as e:
                    self.logger.error(f"Erro ao consolidar NF {nf_key}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            self.logger.info(f"Consolidação concluída: {total_consolidado} itens processados, {total_relatorio_importado} relatórios criados")
            
            return {
                'total_consolidado': total_consolidado,
                'total_relatorio_importado': total_relatorio_importado
            }
            
        except Exception as e:
            self.logger.error(f"Erro na consolidação: {e}")
            db.session.rollback()
            return {
                'total_consolidado': 0,
                'total_relatorio_importado': 0
            }
    
    def buscar_faturamento_por_filtro(self, filtro: str) -> List[Dict]:
        """
        Busca dados de faturamento com filtros específicos
        """
        try:
            self.logger.info(f"Buscando faturamento com filtro: {filtro}")
            
            # Conectar ao Odoo
            connection = get_odoo_connection()
            if not connection:
                return []
            
            # Definir filtros baseados no parâmetro
            filtros = {}
            
            if filtro.lower() == 'faturamento_pendente':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'to invoice'
                }
            elif filtro.lower() == 'faturamento_parcial':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'partial'
                }
            elif filtro.lower() == 'faturamento_completo':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'invoiced'
                }
            else:
                # Filtro personalizado
                filtros = {'state': 'sale'}
            
            # Buscar dados
            dados_odoo = self.mapper.buscar_dados_completos(connection, filtros)
            
            # Mapear para faturamento
            dados_faturamento = self.mapper.mapear_para_faturamento(dados_odoo)
            
            return dados_faturamento
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar faturamento por filtro: {e}")
            return []
    
    def sincronizar_faturamento_completo(self) -> Dict[str, Any]:
        """
        Sincroniza faturamento completo do Odoo
        """
        try:
            self.logger.info("Iniciando sincronização completa de faturamento")
            
            # Buscar dados do mês atual
            resultado = self.importar_faturamento_odoo()
            
            if resultado['sucesso']:
                # Buscar dados históricos (últimos 3 meses)
                for mes_offset in range(1, 4):
                    data_inicio = datetime.now().replace(day=1)
                    if mes_offset == 1:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 1)
                    elif mes_offset == 2:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 2)
                    elif mes_offset == 3:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 3)
                    
                    filtros_historico = {
                        'state': 'sale',
                        'data_inicio': data_inicio.strftime('%Y-%m-%d')
                    }
                    
                    resultado_historico = self.importar_faturamento_odoo(filtros_historico)
                    
                    if resultado_historico['sucesso']:
                        resultado['total_registros'] += resultado_historico['total_registros']
                        # resultado['total_processado'] += resultado_historico['total_processado'] # This line was removed from the new_code
                
                resultado['mensagem'] = 'Sincronização completa realizada com sucesso'
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Erro na sincronização completa: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': [],
                'mensagem': 'Erro na sincronização'
            } 