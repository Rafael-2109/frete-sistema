#!/usr/bin/env python3
"""
📊 GERADOR DE EXCEL VIA CLAUDE
Módulo para gerar arquivos Excel reais baseados em comandos do Claude
"""

import pandas as pd
import os
from datetime import datetime, date, timedelta
from flask import current_app, url_for
from io import BytesIO
import logging
from sqlalchemy import or_

logger = logging.getLogger(__name__)

class ExcelGenerator:
    """Gerador de relatórios Excel baseado em comandos do Claude"""
    
    def __init__(self):
        self.output_dir = None  # Será inicializado quando necessário
    
    def _safe_url_for(self, filename):
        """Gera URL de forma segura, mesmo fora de contexto de request"""
        try:
            return url_for('claude_ai.download_excel', filename=filename)
        except RuntimeError:
            # Fallback para quando não está em contexto de request
            return f'/claude-ai/download/{filename}'
    
    def _ensure_output_dir(self):
        """Garante que o diretório de relatórios existe"""
        try:
            if self.output_dir is None:
                # Inicializar diretório apenas quando necessário (dentro do contexto da aplicação)
                from flask import current_app
                self.output_dir = os.path.join(current_app.static_folder, 'reports')
            
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"📁 Diretório de relatórios criado: {self.output_dir}")
        except Exception as e:
            logger.error(f"Erro ao criar diretório de relatórios: {e}")
            # Fallback para diretório temporário se falhar
            import tempfile
            self.output_dir = tempfile.gettempdir()
    
    def gerar_relatorio_entregas_atrasadas(self, filtros=None):
        """Gera Excel com entregas atrasadas e agendamento pendente"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            
            hoje = date.today()
            
            # Query para entregas atrasadas
            query = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.data_entrega_prevista < hoje,
                EntregaMonitorada.entregue == False
            )
            
            # Aplicar filtros adicionais se fornecidos
            if filtros:
                if filtros.get('uf'):
                    query = query.filter(EntregaMonitorada.uf == filtros['uf'])
                if filtros.get('cliente'):
                    query = query.filter(EntregaMonitorada.cliente.ilike(f"%{filtros['cliente']}%"))
            
            entregas = query.order_by(EntregaMonitorada.data_entrega_prevista).all()
            
            if not entregas:
                return self._gerar_excel_vazio("Nenhuma entrega atrasada encontrada")
            
            # Preparar dados para Excel
            dados = []
            for entrega in entregas:
                dias_atraso = (hoje - entrega.data_entrega_prevista).days if entrega.data_entrega_prevista else 0
                
                dados.append({
                    'NF': entrega.numero_nf,
                    'Cliente': entrega.cliente,
                    'Município': entrega.municipio or '',
                    'UF': entrega.uf or '',
                    'Transportadora': entrega.transportadora or 'Não definida',
                    'Data Embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else '',
                    'Data Prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else '',
                    'Dias Atraso': dias_atraso,
                    'Valor NF': float(entrega.valor_nf or 0),
                    'Vendedor': entrega.vendedor or '',
                    'Status Finalizacao': entrega.status_finalizacao or 'Pendente',
                    'Pendencia Financeira': 'Sim' if entrega.pendencia_financeira else 'Não',
                    'Data Criacao': entrega.criado_em.strftime('%d/%m/%Y %H:%M') if entrega.criado_em else ''
                })
            
            # Criar DataFrame
            df = pd.DataFrame(dados)
            
            # Gerar arquivo Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'entregas_atrasadas_{timestamp}.xlsx'
            self._ensure_output_dir()  # Garantir que diretório existe
            filepath = os.path.join(self.output_dir, filename)
            
            # Criar Excel com formatação
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Aba principal com dados
                df.to_excel(writer, sheet_name='Entregas Atrasadas', index=False)
                
                # Aba de resumo
                resumo_dados = self._criar_resumo_entregas_atrasadas(df)
                resumo_df = pd.DataFrame(resumo_dados)
                resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
                
                # Aba de ações recomendadas
                acoes_dados = self._criar_acoes_recomendadas(df)
                acoes_df = pd.DataFrame(acoes_dados)
                acoes_df.to_excel(writer, sheet_name='Ações Recomendadas', index=False)
            
            # Retornar informações do arquivo
            file_url = self._safe_url_for(filename)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url,
                'total_registros': len(dados),
                'valor_total': sum(d['Valor NF'] for d in dados),
                'maior_atraso': max(d['Dias Atraso'] for d in dados) if dados else 0,
                'message': f'Relatório gerado com {len(dados)} entregas atrasadas'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de entregas atrasadas: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao gerar relatório Excel'
            }
    
    def gerar_relatorio_cliente_especifico(self, cliente, periodo_dias=30):
        """Gera Excel completo para um cliente específico"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from app.pedidos.models import Pedido
            from app.fretes.models import Frete
            
            data_limite = datetime.now() - timedelta(days=periodo_dias)
            
            # Buscar dados do cliente
            entregas = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.cliente.ilike(f'%{cliente}%'),
                EntregaMonitorada.criado_em >= data_limite
            ).all()
            
            if not entregas:
                return self._gerar_excel_vazio(f"Nenhum dado encontrado para o cliente {cliente}")
            
            # Preparar dados principais
            dados_entregas = []
            hoje = date.today()
            
            for entrega in entregas:
                dias_atraso = 0
                status_prazo = 'No prazo'
                
                if entrega.data_entrega_prevista:
                    if entrega.data_hora_entrega_realizada:
                        # Entrega realizada
                        if entrega.data_hora_entrega_realizada.date() > entrega.data_entrega_prevista:
                            dias_atraso = (entrega.data_hora_entrega_realizada.date() - entrega.data_entrega_prevista).days
                            status_prazo = f'Atrasado {dias_atraso} dias'
                    elif entrega.data_entrega_prevista < hoje:
                        # Ainda não entregue e prazo vencido
                        dias_atraso = (hoje - entrega.data_entrega_prevista).days
                        status_prazo = f'Atrasado {dias_atraso} dias'
                
                dados_entregas.append({
                    'NF': entrega.numero_nf,
                    'Data Embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else '',
                    'Data Prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else 'Sem agendamento',
                    'Data Realizada': entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y %H:%M') if entrega.data_hora_entrega_realizada else '',
                    'Status': entrega.status_finalizacao or 'Pendente',
                    'Status Prazo': status_prazo,
                    'Dias Atraso': dias_atraso,
                    'Valor NF': float(entrega.valor_nf or 0),
                    'Município': entrega.municipio or '',
                    'UF': entrega.uf or '',
                    'Transportadora': entrega.transportadora or '',
                    'Vendedor': entrega.vendedor or '',
                    'Lead Time': entrega.lead_time or 0,
                    'Pendencia Financeira': 'Sim' if entrega.pendencia_financeira else 'Não'
                })
            
            # Criar arquivo Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'relatorio_{cliente.replace(" ", "_")}_{timestamp}.xlsx'
            self._ensure_output_dir()  # Garantir que diretório existe
            filepath = os.path.join(self.output_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Aba: Entregas
                df_entregas = pd.DataFrame(dados_entregas)
                df_entregas.to_excel(writer, sheet_name='Entregas', index=False)
                
                # Aba: Resumo Executivo
                resumo = self._criar_resumo_cliente(df_entregas, cliente)
                pd.DataFrame(resumo).to_excel(writer, sheet_name='Resumo Executivo', index=False)
                
                # Aba: Análise de Performance
                performance = self._criar_analise_performance(df_entregas)
                pd.DataFrame(performance).to_excel(writer, sheet_name='Performance', index=False)
                
                # Aba: Agendamentos (se houver)
                agendamentos = self._buscar_agendamentos_cliente(cliente, data_limite)
                if agendamentos:
                    pd.DataFrame(agendamentos).to_excel(writer, sheet_name='Agendamentos', index=False)
            
            file_url = self._safe_url_for(filename)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url,
                'total_registros': len(dados_entregas),
                'cliente': cliente,
                'periodo_dias': periodo_dias,
                'message': f'Relatório completo do {cliente} gerado com {len(dados_entregas)} registros'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório do cliente {cliente}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Erro ao gerar relatório do cliente {cliente}'
            }
    
    def gerar_relatorio_entregas_pendentes(self, filtros=None):
        """Gera Excel com entregas PENDENTES (não realizadas + pedidos com agendamento não faturados)"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from app.pedidos.models import Pedido
            
            hoje = date.today()
            
            # 🎯 DEFINIÇÃO EXPANDIDA DE ENTREGAS PENDENTES:
            # 1. EntregaMonitorada com entregue = False
            # 2. Pedidos com agendamento mas não faturados
            
            # Query 1: Entregas monitoradas pendentes (não finalizadas)
            query_entregas = db.session.query(EntregaMonitorada).filter(
                or_(
                    EntregaMonitorada.status_finalizacao.is_(None),
                    EntregaMonitorada.status_finalizacao == '',
                    EntregaMonitorada.status_finalizacao == 'Pendente'
                )
            )
            
            # Query 2: Pedidos com agendamento mas não faturados
            query_pedidos = db.session.query(Pedido).filter(
                Pedido.agendamento.isnot(None),  # Tem agendamento
                Pedido.nf.is_(None)  # Não foi faturado (sem NF)
            )
            
            # Aplicar filtros às entregas monitoradas
            if filtros:
                if filtros.get('uf'):
                    query_entregas = query_entregas.filter(EntregaMonitorada.uf == filtros['uf'])
                    query_pedidos = query_pedidos.filter(Pedido.uf_normalizada == filtros['uf'])
                if filtros.get('cliente'):
                    query_entregas = query_entregas.filter(EntregaMonitorada.cliente.ilike(f"%{filtros['cliente']}%"))
                    query_pedidos = query_pedidos.filter(Pedido.raz_social_red.ilike(f"%{filtros['cliente']}%"))
                if filtros.get('vendedor'):
                    query_entregas = query_entregas.filter(EntregaMonitorada.vendedor.ilike(f"%{filtros['vendedor']}%"))
                    # Para pedidos, o vendedor não está direto no modelo, então pular filtro
            
            # Executar as queries
            entregas_monitoradas = query_entregas.order_by(EntregaMonitorada.data_embarque.desc()).all()
            pedidos_agendados = query_pedidos.order_by(Pedido.agendamento.desc()).all()
            
            if not entregas_monitoradas and not pedidos_agendados:
                return self._gerar_excel_vazio("Nenhuma entrega pendente encontrada")
            
            # Preparar dados para Excel - UNIFICAR ambos os tipos
            dados = []
            
            # 1. Processar entregas monitoradas
            for entrega in entregas_monitoradas:
                # Calcular status da entrega
                status_prazo = 'Sem agendamento'
                dias_diferenca = 0
                categoria = 'SEM_AGENDAMENTO'
                
                if entrega.data_entrega_prevista:
                    dias_diferenca = (entrega.data_entrega_prevista - hoje).days
                    if dias_diferenca < 0:
                        status_prazo = f'ATRASADA ({abs(dias_diferenca)} dias)'
                        categoria = 'ATRASADA'
                    elif dias_diferenca == 0:
                        status_prazo = 'VENCE HOJE'
                        categoria = 'VENCE_HOJE'
                    elif dias_diferenca <= 2:
                        status_prazo = f'Próxima ({dias_diferenca} dias)'
                        categoria = 'PROXIMA'
                    else:
                        status_prazo = f'No prazo ({dias_diferenca} dias)'
                        categoria = 'NO_PRAZO'
                
                # Buscar agendamentos desta entrega
                agendamentos = db.session.query(AgendamentoEntrega).filter(
                    AgendamentoEntrega.entrega_id == entrega.id
                ).order_by(AgendamentoEntrega.criado_em.desc()).all()
                
                # Dados do último agendamento
                ultimo_agendamento = agendamentos[0] if agendamentos else None
                protocolo_agendamento = ''
                forma_agendamento = ''
                contato_agendamento = ''
                status_agendamento = 'Sem agendamento'
                
                if ultimo_agendamento:
                    protocolo_agendamento = ultimo_agendamento.protocolo_agendamento or ''
                    forma_agendamento = ultimo_agendamento.forma_agendamento or ''
                    contato_agendamento = ultimo_agendamento.contato_agendamento or ''
                    status_agendamento = ultimo_agendamento.status or 'Aguardando aprovação'
                
                dados.append({
                    'Tipo': 'Entrega Monitorada',
                    'NF': entrega.numero_nf,
                    'Cliente': entrega.cliente,
                    'Município': entrega.municipio or '',
                    'UF': entrega.uf or '',
                    'Transportadora': entrega.transportadora or 'Não definida',
                    'Vendedor': entrega.vendedor or '',
                    'Data Embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else '',
                    'Data Prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else 'Sem agendamento',
                    'Status Prazo': status_prazo,
                    'Categoria': categoria,
                    'Dias até Prazo': dias_diferenca,
                    'Valor NF': float(entrega.valor_nf or 0),
                    'Status Finalizacao': entrega.status_finalizacao or 'Pendente',
                    'Pendencia Financeira': 'Sim' if entrega.pendencia_financeira else 'Não',
                    # Dados de agendamento
                    'Forma Agendamento': forma_agendamento,
                    'Contato Agendamento': contato_agendamento,
                    'Protocolo Agendamento': protocolo_agendamento,
                    'Status Agendamento': status_agendamento,
                    'Total Agendamentos': len(agendamentos),
                    'Data Criacao': entrega.criado_em.strftime('%d/%m/%Y %H:%M') if entrega.criado_em else '',
                    # Campos específicos de pedidos (vazios para entregas)
                    'Num Pedido': '',
                    'Data Expedicao': '',
                    'Peso Total (kg)': 0,
                    'Valor Pedido': 0
                })
            
            # 2. Processar pedidos com agendamento não faturados
            for pedido in pedidos_agendados:
                # Calcular status do pedido com agendamento
                dias_diferenca = 0
                categoria = 'PEDIDO_AGENDADO'
                status_prazo = 'Pedido com agendamento'
                
                if pedido.agendamento:
                    dias_diferenca = (pedido.agendamento - hoje).days
                    if dias_diferenca < 0:
                        status_prazo = f'AGENDAMENTO ATRASADO ({abs(dias_diferenca)} dias)'
                        categoria = 'AGENDAMENTO_ATRASADO'
                    elif dias_diferenca == 0:
                        status_prazo = 'AGENDADO PARA HOJE'
                        categoria = 'AGENDADO_HOJE'
                    elif dias_diferenca <= 2:
                        status_prazo = f'Agendado próximo ({dias_diferenca} dias)'
                        categoria = 'AGENDADO_PROXIMO'
                    else:
                        status_prazo = f'Agendado futuro ({dias_diferenca} dias)'
                        categoria = 'AGENDADO_FUTURO'
                
                dados.append({
                    'Tipo': 'Pedido Agendado',
                    'NF': 'PENDENTE FATURAMENTO',
                    'Cliente': pedido.raz_social_red or '',
                    'Município': pedido.cidade_normalizada or pedido.nome_cidade or '',
                    'UF': pedido.uf_normalizada or pedido.cod_uf or '',
                    'Transportadora': pedido.transportadora or 'Não definida',
                    'Vendedor': '',  # Pedidos não têm vendedor direto
                    'Data Embarque': pedido.data_embarque.strftime('%d/%m/%Y') if pedido.data_embarque else '',
                    'Data Prevista': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                    'Status Prazo': status_prazo,
                    'Categoria': categoria,
                    'Dias até Prazo': dias_diferenca,
                    'Valor NF': 0,  # Pedido ainda não faturado
                    'Status Finalizacao': pedido.status_calculado or 'Pendente',
                    'Pendencia Financeira': 'Não',  # Pedidos não têm pendência financeira
                    # Dados de agendamento do pedido
                    'Forma Agendamento': 'Agendamento Pedido',
                    'Contato Agendamento': '',
                    'Protocolo Agendamento': pedido.protocolo or '',
                    'Status Agendamento': 'Agendado no Pedido',
                    'Total Agendamentos': 1,
                    'Data Criacao': pedido.criado_em.strftime('%d/%m/%Y %H:%M') if pedido.criado_em else '',
                    # Campos específicos de pedidos
                    'Num Pedido': pedido.num_pedido or '',
                    'Data Expedicao': pedido.expedicao.strftime('%d/%m/%Y') if pedido.expedicao else '',
                    'Peso Total (kg)': float(pedido.peso_total or 0),
                    'Valor Pedido': float(pedido.valor_saldo_total or 0)
                })
            
            # Criar DataFrame
            df = pd.DataFrame(dados)
            
            # Gerar arquivo Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'entregas_pendentes_{timestamp}.xlsx'
            self._ensure_output_dir()  # Garantir que diretório existe
            filepath = os.path.join(self.output_dir, filename)
            
            # Criar Excel com formatação
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Aba principal com dados
                df.to_excel(writer, sheet_name='Entregas Pendentes', index=False)
                
                # Aba de resumo
                resumo_dados = self._criar_resumo_entregas_pendentes(df)
                resumo_df = pd.DataFrame(resumo_dados)
                resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
                
                # Aba de análise por categoria
                categoria_dados = self._criar_analise_categorias(df)
                categoria_df = pd.DataFrame(categoria_dados)
                categoria_df.to_excel(writer, sheet_name='Análise por Status', index=False)
                
                # Aba de agendamentos
                agendamentos_dados = self._criar_resumo_agendamentos(df)
                agendamentos_df = pd.DataFrame(agendamentos_dados)
                agendamentos_df.to_excel(writer, sheet_name='Status Agendamentos', index=False)
                
                # Aba de ações prioritárias
                acoes_dados = self._criar_acoes_entregas_pendentes(df)
                acoes_df = pd.DataFrame(acoes_dados)
                acoes_df.to_excel(writer, sheet_name='Ações Prioritárias', index=False)
            
            # Retornar informações do arquivo
            file_url = self._safe_url_for(filename)
            
            # Estatísticas EXPANDIDAS para retorno
            total_pendentes = len(dados)
            entregas_monitoradas_count = len([d for d in dados if d['Tipo'] == 'Entrega Monitorada'])
            pedidos_agendados_count = len([d for d in dados if d['Tipo'] == 'Pedido Agendado'])
            
            # Estatísticas por categoria
            atrasadas = len([d for d in dados if d['Categoria'] == 'ATRASADA'])
            vence_hoje = len([d for d in dados if d['Categoria'] == 'VENCE_HOJE'])
            sem_agendamento = len([d for d in dados if d['Categoria'] == 'SEM_AGENDAMENTO'])
            no_prazo = len([d for d in dados if d['Categoria'] == 'NO_PRAZO'])
            
            # Estatísticas específicas de pedidos
            agendamentos_atrasados = len([d for d in dados if d['Categoria'] == 'AGENDAMENTO_ATRASADO'])
            agendado_hoje = len([d for d in dados if d['Categoria'] == 'AGENDADO_HOJE'])
            agendado_proximo = len([d for d in dados if d['Categoria'] == 'AGENDADO_PROXIMO'])
            
            # Calcular valores totais
            valor_total_entregas = sum(d['Valor NF'] for d in dados if d['Tipo'] == 'Entrega Monitorada')
            valor_total_pedidos = sum(d['Valor Pedido'] for d in dados if d['Tipo'] == 'Pedido Agendado')
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url,
                'total_registros': total_pendentes,
                'valor_total': valor_total_entregas + valor_total_pedidos,
                'estatisticas': {
                    'total_pendentes': total_pendentes,
                    'entregas_monitoradas': entregas_monitoradas_count,
                    'pedidos_agendados': pedidos_agendados_count,
                    # Estatísticas de entregas
                    'atrasadas': atrasadas,
                    'vence_hoje': vence_hoje,
                    'sem_agendamento': sem_agendamento,
                    'no_prazo': no_prazo,
                    # Estatísticas de pedidos
                    'agendamentos_atrasados': agendamentos_atrasados,
                    'agendado_hoje': agendado_hoje,
                    'agendado_proximo': agendado_proximo,
                    # Valores
                    'valor_entregas': valor_total_entregas,
                    'valor_pedidos': valor_total_pedidos
                },
                'message': f'Relatório EXPANDIDO de entregas pendentes gerado: {entregas_monitoradas_count} entregas monitoradas + {pedidos_agendados_count} pedidos agendados = {total_pendentes} registros totais'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de entregas pendentes: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao gerar relatório Excel de entregas pendentes'
            }
    
    def gerar_relatorio_entregas_finalizadas(self, filtros=None, periodo_dias=30):
        """📊 Gera relatório Excel de entregas FINALIZADAS/CONCLUÍDAS com performance"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            from datetime import datetime, timedelta
            import pandas as pd
            
            logger.info("✅ Gerando relatório de entregas FINALIZADAS")
            
            # Data limite baseada no período
            data_limite = datetime.now() - timedelta(days=periodo_dias)
            
            # Query principal - APENAS entregas FINALIZADAS/ENTREGUES
            query = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.criado_em >= data_limite,
                EntregaMonitorada.entregue == True,  # SOMENTE entregues
                EntregaMonitorada.status_finalizacao.in_(['ENTREGUE', 'FINALIZADA'])  # Status finalizado
            )
            
            # Aplicar filtros
            if filtros:
                if filtros.get('cliente'):
                    query = query.filter(EntregaMonitorada.cliente.ilike(f"%{filtros['cliente']}%"))
                    logger.info(f"✅ Filtro cliente aplicado: {filtros['cliente']}")
                    
                if filtros.get('uf'):
                    query = query.filter(EntregaMonitorada.uf == filtros['uf'])
                    
                if filtros.get('vendedor'):
                    query = query.filter(EntregaMonitorada.vendedor.ilike(f"%{filtros['vendedor']}%"))
            
            # Buscar entregas finalizadas
            entregas = query.order_by(EntregaMonitorada.data_hora_entrega_realizada.desc()).all()
            
            logger.info(f"✅ Total entregas finalizadas encontradas: {len(entregas)}")
            
            if not entregas:
                filtro_info = ""
                if filtros and filtros.get('cliente'):
                    filtro_info = f" para o cliente {filtros['cliente']}"
                return self._gerar_excel_vazio(f'Nenhuma entrega finalizada encontrada nos últimos {periodo_dias} dias{filtro_info}')
            
            # Processar dados das entregas finalizadas
            dados = []
            hoje = datetime.now().date()
            
            for entrega in entregas:
                # Calcular performance de prazo
                if entrega.data_entrega_prevista and entrega.data_hora_entrega_realizada:
                    prazo_previsto = entrega.data_entrega_prevista
                    entrega_realizada = entrega.data_hora_entrega_realizada.date() if hasattr(entrega.data_hora_entrega_realizada, 'date') else entrega.data_hora_entrega_realizada
                    
                    dias_diferenca = (entrega_realizada - prazo_previsto).days
                    
                    if dias_diferenca <= 0:
                        performance_prazo = 'NO PRAZO'
                        performance_categoria = 'SUCESSO'
                    elif dias_diferenca <= 2:
                        performance_prazo = f'ATRASO LEVE ({dias_diferenca} dias)'
                        performance_categoria = 'LEVE'
                    else:
                        performance_prazo = f'ATRASO SIGNIFICATIVO ({dias_diferenca} dias)'
                        performance_categoria = 'SIGNIFICATIVO'
                        
                    # Calcular lead time real
                    if entrega.data_embarque and entrega.data_hora_entrega_realizada:
                        embarque_date = entrega.data_embarque.date() if hasattr(entrega.data_embarque, 'date') else entrega.data_embarque
                        lead_time_real = (entrega_realizada - embarque_date).days
                    else:
                        lead_time_real = 0
                else:
                    performance_prazo = 'SEM PRAZO DEFINIDO'
                    performance_categoria = 'SEM_DADOS'
                    lead_time_real = 0
                    dias_diferenca = 0
                
                # Buscar agendamentos desta entrega
                agendamentos = db.session.query(AgendamentoEntrega).filter(
                    AgendamentoEntrega.entrega_id == entrega.id
                ).order_by(AgendamentoEntrega.criado_em.desc()).all()
                
                # Dados do último agendamento
                ultimo_agendamento = agendamentos[0] if agendamentos else None
                protocolo_agendamento = ultimo_agendamento.protocolo_agendamento if ultimo_agendamento else ''
                forma_agendamento = ultimo_agendamento.forma_agendamento if ultimo_agendamento else ''
                status_agendamento = ultimo_agendamento.status if ultimo_agendamento else 'Sem agendamento'
                
                dados.append({
                    'NF': entrega.numero_nf,
                    'Cliente': entrega.cliente,
                    'Município': entrega.municipio or '',
                    'UF': entrega.uf or '',
                    'Transportadora': entrega.transportadora or 'Não definida',
                    'Vendedor': entrega.vendedor or '',
                    'Data Embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else '',
                    'Data Prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else '',
                    'Data Realizada': entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y') if entrega.data_hora_entrega_realizada else '',
                    'Performance Prazo': performance_prazo,
                    'Categoria Performance': performance_categoria,
                    'Dias Diferença': dias_diferenca,
                    'Lead Time Real (dias)': lead_time_real,
                    'Valor NF': float(entrega.valor_nf or 0),
                    'Status Finalizacao': entrega.status_finalizacao or 'Entregue',
                    'Pendencia Financeira': 'Sim' if entrega.pendencia_financeira else 'Não',
                    # Dados de agendamento
                    'Forma Agendamento': forma_agendamento,
                    'Protocolo Agendamento': protocolo_agendamento,
                    'Status Agendamento': status_agendamento,
                    'Total Agendamentos': len(agendamentos),
                    'Data Criacao': entrega.criado_em.strftime('%d/%m/%Y %H:%M') if entrega.criado_em else '',
                    'Observacoes': entrega.observacao_operacional or ''
                })
            
            # Criar DataFrame
            df = pd.DataFrame(dados)
            
            # Gerar arquivo Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'entregas_finalizadas_{timestamp}.xlsx'
            if filtros and filtros.get('cliente'):
                cliente_safe = filtros['cliente'].replace(' ', '_').lower()
                filename = f'entregas_finalizadas_{cliente_safe}_{timestamp}.xlsx'
                
            self._ensure_output_dir()
            filepath = os.path.join(self.output_dir, filename)
            
            # Criar Excel com formatação
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Aba principal com dados
                df.to_excel(writer, sheet_name='Entregas Finalizadas', index=False)
                
                # Aba de resumo executivo
                resumo_dados = self._criar_resumo_entregas_finalizadas(df)
                resumo_df = pd.DataFrame(resumo_dados)
                resumo_df.to_excel(writer, sheet_name='Resumo Executivo', index=False)
                
                # Aba de análise de performance
                performance_dados = self._criar_analise_performance_finalizadas(df)
                performance_df = pd.DataFrame(performance_dados)
                performance_df.to_excel(writer, sheet_name='Análise Performance', index=False)
                
                # Aba de agendamentos realizados
                agendamentos_dados = self._criar_resumo_agendamentos_finalizados(df)
                agendamentos_df = pd.DataFrame(agendamentos_dados)
                agendamentos_df.to_excel(writer, sheet_name='Agendamentos', index=False)
                
                # Aba de estatísticas por transportadora
                transp_dados = self._criar_analise_por_transportadora(df)
                transp_df = pd.DataFrame(transp_dados)
                transp_df.to_excel(writer, sheet_name='Por Transportadora', index=False)
            
            # Retornar informações do arquivo
            file_url = self._safe_url_for(filename)
            
            # Calcular estatísticas de performance
            total_finalizadas = len(dados)
            no_prazo = len([d for d in dados if d['Categoria Performance'] == 'SUCESSO'])
            atraso_leve = len([d for d in dados if d['Categoria Performance'] == 'LEVE'])
            atraso_significativo = len([d for d in dados if d['Categoria Performance'] == 'SIGNIFICATIVO'])
            
            # Calcular médias
            lead_time_medio = sum(d['Lead Time Real (dias)'] for d in dados if d['Lead Time Real (dias)'] > 0) / len([d for d in dados if d['Lead Time Real (dias)'] > 0]) if any(d['Lead Time Real (dias)'] > 0 for d in dados) else 0
            valor_total = sum(d['Valor NF'] for d in dados)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url,
                'total_registros': total_finalizadas,
                'valor_total': valor_total,
                'periodo_dias': periodo_dias,
                'cliente': filtros.get('cliente') if filtros else None,
                'estatisticas': {
                    'total_finalizadas': total_finalizadas,
                    'no_prazo': no_prazo,
                    'atraso_leve': atraso_leve,
                    'atraso_significativo': atraso_significativo,
                    'percentual_pontualidade': round((no_prazo / total_finalizadas * 100), 1) if total_finalizadas > 0 else 0,
                    'lead_time_medio': round(lead_time_medio, 1),
                    'valor_total': valor_total,
                    'ticket_medio': round(valor_total / total_finalizadas, 2) if total_finalizadas > 0 else 0
                },
                'message': f'Relatório de entregas finalizadas gerado: {total_finalizadas} entregas nos últimos {periodo_dias} dias'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de entregas finalizadas: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao gerar relatório Excel de entregas finalizadas'
            }
    
    def _criar_resumo_entregas_finalizadas(self, df):
        """Cria resumo executivo das entregas finalizadas"""
        if df.empty:
            return [{'Métrica': 'Nenhum dado', 'Valor': 0}]
        
        # Contar por categoria de performance
        no_prazo = len(df[df['Categoria Performance'] == 'SUCESSO'])
        atraso_leve = len(df[df['Categoria Performance'] == 'LEVE'])
        atraso_significativo = len(df[df['Categoria Performance'] == 'SIGNIFICATIVO'])
        
        # Calcular médias
        lead_time_medio = df[df['Lead Time Real (dias)'] > 0]['Lead Time Real (dias)'].mean()
        valor_total = df['Valor NF'].sum()
        
        resumo = [
            # TOTAIS GERAIS
            {'Métrica': '📊 TOTAL DE ENTREGAS FINALIZADAS', 'Valor': len(df)},
            {'Métrica': '💰 Valor Total Entregue', 'Valor': f"R$ {valor_total:,.2f}"},
            {'Métrica': '📈 Ticket Médio', 'Valor': f"R$ {valor_total/len(df):,.2f}"},
            {'Métrica': '', 'Valor': ''},  # Linha vazia
            
            # PERFORMANCE DE PRAZOS
            {'Métrica': '🎯 PERFORMANCE DE PRAZOS', 'Valor': ''},
            {'Métrica': '└─ ✅ Entregas no Prazo', 'Valor': no_prazo},
            {'Métrica': '└─ 🟡 Atraso Leve (1-2 dias)', 'Valor': atraso_leve},
            {'Métrica': '└─ 🔴 Atraso Significativo (3+ dias)', 'Valor': atraso_significativo},
            {'Métrica': '└─ 📊 Taxa de Pontualidade', 'Valor': f"{no_prazo/len(df)*100:.1f}%"},
            {'Métrica': '', 'Valor': ''},  # Linha vazia
            
            # LEAD TIME
            {'Métrica': '⚡ LEAD TIME REALIZADO', 'Valor': ''},
            {'Métrica': '└─ Lead Time Médio', 'Valor': f"{lead_time_medio:.1f} dias" if not pd.isna(lead_time_medio) else "N/A"},
            {'Métrica': '└─ Menor Lead Time', 'Valor': f"{df[df['Lead Time Real (dias)'] > 0]['Lead Time Real (dias)'].min():.0f} dias" if len(df[df['Lead Time Real (dias)'] > 0]) > 0 else "N/A"},
            {'Métrica': '└─ Maior Lead Time', 'Valor': f"{df[df['Lead Time Real (dias)'] > 0]['Lead Time Real (dias)'].max():.0f} dias" if len(df[df['Lead Time Real (dias)'] > 0]) > 0 else "N/A"},
        ]
        
        return resumo
    
    def _criar_analise_performance_finalizadas(self, df):
        """Cria análise detalhada de performance das entregas finalizadas"""
        if df.empty:
            return [{'Categoria': 'Sem dados', 'Quantidade': 0, 'Percentual': '0%', 'Valor Total': 'R$ 0,00'}]
        
        categorias = []
        total_registros = len(df)
        
        # Análise por categoria de performance
        for categoria in ['SUCESSO', 'LEVE', 'SIGNIFICATIVO', 'SEM_DADOS']:
            dados_categoria = df[df['Categoria Performance'] == categoria]
            quantidade = len(dados_categoria)
            
            if quantidade > 0:
                valor_categoria = dados_categoria['Valor NF'].sum()
                percentual = (quantidade / total_registros * 100)
                
                nome_categoria = {
                    'SUCESSO': '✅ No Prazo',
                    'LEVE': '🟡 Atraso Leve (1-2 dias)',
                    'SIGNIFICATIVO': '🔴 Atraso Significativo (3+ dias)',
                    'SEM_DADOS': '⚪ Sem Dados de Prazo'
                }.get(categoria, categoria)
                
                categorias.append({
                    'Categoria': nome_categoria,
                    'Quantidade': quantidade,
                    'Percentual': f"{percentual:.1f}%",
                    'Valor Total': f"R$ {valor_categoria:,.2f}",
                    'Valor Médio': f"R$ {valor_categoria/quantidade:,.2f}"
                })
        
        return categorias
    
    def _criar_resumo_agendamentos_finalizados(self, df):
        """Cria resumo dos agendamentos das entregas finalizadas"""
        if df.empty:
            return [{'Status Agendamento': 'Sem dados', 'Quantidade': 0}]
        
        resumo = []
        agendamentos_count = df['Status Agendamento'].value_counts()
        
        for status, quantidade in agendamentos_count.items():
            emoji = {
                'Confirmado': '✅',
                'Aguardando aprovação': '⏳',
                'Sem agendamento': '❌',
                'Reagendado': '🔄',
                'Agendado no Pedido': '📋'
            }.get(status, '📋')
            
            resumo.append({
                'Status Agendamento': f"{emoji} {status}",
                'Quantidade': quantidade,
                'Percentual': f"{quantidade/len(df)*100:.1f}%"
            })
        
        return resumo
    
    def _criar_analise_por_transportadora(self, df):
        """Cria análise de performance por transportadora"""
        if df.empty:
            return [{'Transportadora': 'Sem dados', 'Entregas': 0}]
        
        analise = []
        
        # Agrupar por transportadora
        for transportadora in df['Transportadora'].unique():
            dados_transp = df[df['Transportadora'] == transportadora]
            
            if len(dados_transp) > 0:
                total_entregas = len(dados_transp)
                no_prazo = len(dados_transp[dados_transp['Categoria Performance'] == 'SUCESSO'])
                valor_total = dados_transp['Valor NF'].sum()
                lead_time_medio = dados_transp[dados_transp['Lead Time Real (dias)'] > 0]['Lead Time Real (dias)'].mean()
                
                analise.append({
                    'Transportadora': transportadora,
                    'Total Entregas': total_entregas,
                    'Entregas no Prazo': no_prazo,
                    'Taxa Pontualidade': f"{no_prazo/total_entregas*100:.1f}%",
                    'Valor Total': f"R$ {valor_total:,.2f}",
                    'Valor Médio': f"R$ {valor_total/total_entregas:,.2f}",
                    'Lead Time Médio': f"{lead_time_medio:.1f} dias" if not pd.isna(lead_time_medio) else "N/A"
                })
        
        # Ordenar por quantidade de entregas
        analise.sort(key=lambda x: x['Total Entregas'], reverse=True)
        
        return analise

# Instância global
excel_generator = ExcelGenerator()

def get_excel_generator():
    """Retorna instância do gerador Excel"""
    return excel_generator 