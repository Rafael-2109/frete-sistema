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

logger = logging.getLogger(__name__)

class ExcelGenerator:
    """Gerador de relatórios Excel baseado em comandos do Claude"""
    
    def __init__(self):
        self.output_dir = os.path.join(current_app.static_folder, 'reports')
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Garante que o diretório de relatórios existe"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
        except Exception as e:
            logger.error(f"Erro ao criar diretório de relatórios: {e}")
    
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
            file_url = url_for('static', filename=f'reports/{filename}')
            
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
            
            file_url = url_for('static', filename=f'reports/{filename}')
            
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
        """Gera Excel com entregas PENDENTES (não realizadas, incluindo agendamentos)"""
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
            
            hoje = date.today()
            
            # Query para entregas PENDENTES (não entregues)
            query = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.entregue == False,
                # Incluir também entregas sem data prevista (sem agendamento)
                # EntregaMonitorada.data_entrega_prevista.isnot(None)
            )
            
            # Aplicar filtros adicionais se fornecidos
            if filtros:
                if filtros.get('uf'):
                    query = query.filter(EntregaMonitorada.uf == filtros['uf'])
                if filtros.get('cliente'):
                    query = query.filter(EntregaMonitorada.cliente.ilike(f"%{filtros['cliente']}%"))
                if filtros.get('vendedor'):
                    query = query.filter(EntregaMonitorada.vendedor.ilike(f"%{filtros['vendedor']}%"))
            
            entregas = query.order_by(EntregaMonitorada.data_embarque.desc()).all()
            
            if not entregas:
                return self._gerar_excel_vazio("Nenhuma entrega pendente encontrada")
            
            # Preparar dados para Excel
            dados = []
            for entrega in entregas:
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
                    'Data Criacao': entrega.criado_em.strftime('%d/%m/%Y %H:%M') if entrega.criado_em else ''
                })
            
            # Criar DataFrame
            df = pd.DataFrame(dados)
            
            # Gerar arquivo Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'entregas_pendentes_{timestamp}.xlsx'
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
            file_url = url_for('static', filename=f'reports/{filename}')
            
            # Estatísticas para retorno
            total_pendentes = len(dados)
            atrasadas = len([d for d in dados if d['Categoria'] == 'ATRASADA'])
            sem_agendamento = len([d for d in dados if d['Categoria'] == 'SEM_AGENDAMENTO'])
            no_prazo = len([d for d in dados if d['Categoria'] == 'NO_PRAZO'])
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url,
                'total_registros': total_pendentes,
                'valor_total': sum(d['Valor NF'] for d in dados),
                'estatisticas': {
                    'total_pendentes': total_pendentes,
                    'atrasadas': atrasadas,
                    'sem_agendamento': sem_agendamento,
                    'no_prazo': no_prazo,
                    'com_agendamento': total_pendentes - sem_agendamento
                },
                'message': f'Relatório de entregas pendentes gerado com {total_pendentes} registros'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de entregas pendentes: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao gerar relatório Excel de entregas pendentes'
            }
    
    def _criar_resumo_entregas_atrasadas(self, df):
        """Cria resumo das entregas atrasadas"""
        if df.empty:
            return [{'Métrica': 'Nenhum dado', 'Valor': 0}]
        
        resumo = [
            {'Métrica': 'Total de Entregas Atrasadas', 'Valor': len(df)},
            {'Métrica': 'Valor Total (R$)', 'Valor': f"R$ {df['Valor NF'].sum():,.2f}"},
            {'Métrica': 'Maior Atraso (dias)', 'Valor': df['Dias Atraso'].max()},
            {'Métrica': 'Atraso Médio (dias)', 'Valor': f"{df['Dias Atraso'].mean():.1f}"},
            {'Métrica': 'Clientes Afetados', 'Valor': df['Cliente'].nunique()},
            {'Métrica': 'UFs Afetadas', 'Valor': df['UF'].nunique()},
            {'Métrica': 'Com Pendência Financeira', 'Valor': len(df[df['Pendencia Financeira'] == 'Sim'])}
        ]
        
        return resumo
    
    def _criar_acoes_recomendadas(self, df):
        """Cria lista de ações recomendadas"""
        if df.empty:
            return [{'Prioridade': 'N/A', 'Ação': 'Nenhuma ação necessária', 'Cliente': ''}]
        
        acoes = []
        
        # Entregas com mais de 5 dias de atraso
        criticas = df[df['Dias Atraso'] > 5]
        for _, row in criticas.iterrows():
            acoes.append({
                'Prioridade': 'CRÍTICA',
                'Ação': f'Contato urgente - {row["Dias Atraso"]} dias atraso',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}"
            })
        
        # Entregas com pendência financeira
        financeiras = df[df['Pendencia Financeira'] == 'Sim']
        for _, row in financeiras.iterrows():
            acoes.append({
                'Prioridade': 'FINANCEIRA',
                'Ação': 'Resolver pendência financeira',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}"
            })
        
        # Entregas sem transportadora
        sem_transp = df[df['Transportadora'] == 'Não definida']
        for _, row in sem_transp.iterrows():
            acoes.append({
                'Prioridade': 'OPERACIONAL',
                'Ação': 'Definir transportadora',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}"
            })
        
        if not acoes:
            acoes.append({
                'Prioridade': 'BAIXA',
                'Ação': 'Monitoramento de rotina',
                'Cliente': 'Todos',
                'NF': 'N/A',
                'Valor': 'N/A'
            })
        
        return acoes
    
    def _criar_resumo_cliente(self, df, cliente):
        """Cria resumo executivo do cliente"""
        if df.empty:
            return [{'Métrica': 'Nenhum dado', 'Valor': 0}]
        
        entregues = df[df['Status'] == 'Entregue']
        no_prazo = df[df['Status Prazo'] == 'No prazo']
        
        resumo = [
            {'Métrica': 'Cliente', 'Valor': cliente},
            {'Métrica': 'Total de Entregas', 'Valor': len(df)},
            {'Métrica': 'Entregas Realizadas', 'Valor': len(entregues)},
            {'Métrica': 'Taxa de Entrega (%)', 'Valor': f"{len(entregues)/len(df)*100:.1f}%"},
            {'Métrica': 'Entregas no Prazo', 'Valor': len(no_prazo)},
            {'Métrica': 'Taxa Pontualidade (%)', 'Valor': f"{len(no_prazo)/len(df)*100:.1f}%"},
            {'Métrica': 'Valor Total (R$)', 'Valor': f"R$ {df['Valor NF'].sum():,.2f}"},
            {'Métrica': 'Lead Time Médio (dias)', 'Valor': f"{df['Lead Time'].mean():.1f}"},
            {'Métrica': 'UFs Atendidas', 'Valor': df['UF'].nunique()}
        ]
        
        return resumo
    
    def _criar_analise_performance(self, df):
        """Cria análise de performance"""
        if df.empty:
            return [{'Indicador': 'Sem dados', 'Resultado': 'N/A', 'Meta': 'N/A', 'Status': 'N/A'}]
        
        entregues = len(df[df['Status'] == 'Entregue'])
        no_prazo = len(df[df['Status Prazo'] == 'No prazo'])
        total = len(df)
        
        performance = [
            {
                'Indicador': 'Taxa de Entrega',
                'Resultado': f"{entregues/total*100:.1f}%",
                'Meta': '95%',
                'Status': '✅ OK' if entregues/total >= 0.95 else '⚠️ Atenção'
            },
            {
                'Indicador': 'Pontualidade',
                'Resultado': f"{no_prazo/total*100:.1f}%",
                'Meta': '85%',
                'Status': '✅ OK' if no_prazo/total >= 0.85 else '⚠️ Atenção'
            },
            {
                'Indicador': 'Lead Time Médio',
                'Resultado': f"{df['Lead Time'].mean():.1f} dias",
                'Meta': '≤ 5 dias',
                'Status': '✅ OK' if df['Lead Time'].mean() <= 5 else '⚠️ Atenção'
            }
        ]
        
        return performance
    
    def _buscar_agendamentos_cliente(self, cliente, data_limite):
        """Busca agendamentos do cliente"""
        try:
            from app import db
            from app.monitoramento.models import AgendamentoEntrega, EntregaMonitorada
            
            agendamentos = db.session.query(AgendamentoEntrega).join(
                EntregaMonitorada,
                AgendamentoEntrega.entrega_id == EntregaMonitorada.id
            ).filter(
                EntregaMonitorada.cliente.ilike(f'%{cliente}%'),
                AgendamentoEntrega.criado_em >= data_limite
            ).all()
            
            dados = []
            for ag in agendamentos:
                dados.append({
                    'NF': ag.entrega.numero_nf,
                    'Data Agendada': ag.data_agendada.strftime('%d/%m/%Y') if ag.data_agendada else '',
                    'Hora Agendada': ag.hora_agendada.strftime('%H:%M') if ag.hora_agendada else '',
                    'Forma': ag.forma_agendamento or '',
                    'Contato': ag.contato_agendamento or '',
                    'Protocolo': ag.protocolo_agendamento or '',
                    'Status': ag.status or 'Pendente',
                    'Criado em': ag.criado_em.strftime('%d/%m/%Y %H:%M') if ag.criado_em else ''
                })
            
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao buscar agendamentos: {e}")
            return []
    
    def _gerar_excel_vazio(self, mensagem):
        """Gera Excel vazio com mensagem informativa"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sem_dados_{timestamp}.xlsx'
        filepath = os.path.join(self.output_dir, filename)
        
        df = pd.DataFrame([{'Resultado': mensagem}])
        df.to_excel(filepath, index=False)
        
        file_url = url_for('static', filename=f'reports/{filename}')
        
        return {
            'success': True,
            'filename': filename,
            'file_url': file_url,
            'total_registros': 0,
            'message': mensagem
        }
    
    def _criar_resumo_entregas_pendentes(self, df):
        """Cria resumo das entregas pendentes"""
        if df.empty:
            return [{'Métrica': 'Nenhum dado', 'Valor': 0}]
        
        # Contar por categoria
        atrasadas = len(df[df['Categoria'] == 'ATRASADA'])
        vence_hoje = len(df[df['Categoria'] == 'VENCE_HOJE'])
        proximas = len(df[df['Categoria'] == 'PROXIMA'])
        no_prazo = len(df[df['Categoria'] == 'NO_PRAZO'])
        sem_agendamento = len(df[df['Categoria'] == 'SEM_AGENDAMENTO'])
        
        resumo = [
            {'Métrica': 'Total de Entregas Pendentes', 'Valor': len(df)},
            {'Métrica': 'Valor Total (R$)', 'Valor': f"R$ {df['Valor NF'].sum():,.2f}"},
            {'Métrica': '🔴 ATRASADAS', 'Valor': atrasadas},
            {'Métrica': '⚠️ VENCEM HOJE', 'Valor': vence_hoje},
            {'Métrica': '🟡 PRÓXIMAS (1-2 dias)', 'Valor': proximas},
            {'Métrica': '🟢 NO PRAZO (3+ dias)', 'Valor': no_prazo},
            {'Métrica': '⚪ SEM AGENDAMENTO', 'Valor': sem_agendamento},
            {'Métrica': 'Clientes Envolvidos', 'Valor': df['Cliente'].nunique()},
            {'Métrica': 'UFs Envolvidas', 'Valor': df['UF'].nunique()},
            {'Métrica': 'Com Pendência Financeira', 'Valor': len(df[df['Pendencia Financeira'] == 'Sim'])},
            {'Métrica': 'Com Agendamento Confirmado', 'Valor': len(df[df['Status Agendamento'] == 'Confirmado'])}
        ]
        
        return resumo
    
    def _criar_analise_categorias(self, df):
        """Cria análise detalhada por categoria de status"""
        if df.empty:
            return [{'Categoria': 'Sem dados', 'Quantidade': 0, 'Valor Total': 0, 'Percentual': '0%'}]
        
        categorias = []
        total_valor = df['Valor NF'].sum()
        total_registros = len(df)
        
        for categoria in ['ATRASADA', 'VENCE_HOJE', 'PROXIMA', 'NO_PRAZO', 'SEM_AGENDAMENTO']:
            dados_categoria = df[df['Categoria'] == categoria]
            quantidade = len(dados_categoria)
            valor_categoria = dados_categoria['Valor NF'].sum()
            percentual = (quantidade / total_registros * 100) if total_registros > 0 else 0
            
            nome_categoria = {
                'ATRASADA': '🔴 Atrasadas',
                'VENCE_HOJE': '⚠️ Vencem Hoje',
                'PROXIMA': '🟡 Próximas (1-2 dias)',
                'NO_PRAZO': '🟢 No Prazo (3+ dias)',
                'SEM_AGENDAMENTO': '⚪ Sem Agendamento'
            }.get(categoria, categoria)
            
            if quantidade > 0:
                categorias.append({
                    'Categoria': nome_categoria,
                    'Quantidade': quantidade,
                    'Valor Total': f"R$ {valor_categoria:,.2f}",
                    'Percentual': f"{percentual:.1f}%",
                    'Valor Médio': f"R$ {valor_categoria/quantidade:,.2f}" if quantidade > 0 else "R$ 0,00"
                })
        
        return categorias
    
    def _criar_resumo_agendamentos(self, df):
        """Cria resumo dos status de agendamentos"""
        if df.empty:
            return [{'Status Agendamento': 'Sem dados', 'Quantidade': 0}]
        
        resumo = []
        agendamentos_count = df['Status Agendamento'].value_counts()
        
        for status, quantidade in agendamentos_count.items():
            emoji = {
                'Confirmado': '✅',
                'Aguardando aprovação': '⏳',
                'Sem agendamento': '❌',
                'Reagendado': '🔄'
            }.get(status, '📋')
            
            resumo.append({
                'Status Agendamento': f"{emoji} {status}",
                'Quantidade': quantidade,
                'Percentual': f"{quantidade/len(df)*100:.1f}%"
            })
        
        return resumo
    
    def _criar_acoes_entregas_pendentes(self, df):
        """Cria lista de ações prioritárias para entregas pendentes"""
        if df.empty:
            return [{'Prioridade': 'N/A', 'Ação': 'Nenhuma ação necessária', 'Cliente': ''}]
        
        acoes = []
        
        # 1. CRÍTICAS - Entregas atrasadas
        atrasadas = df[df['Categoria'] == 'ATRASADA']
        for _, row in atrasadas.iterrows():
            acoes.append({
                'Prioridade': '🔴 CRÍTICA',
                'Ação': f'URGENTE: Contato imediato - {abs(row["Dias até Prazo"])} dias atrasado',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}",
                'Status Agendamento': row['Status Agendamento']
            })
        
        # 2. URGENTES - Vencem hoje
        vence_hoje = df[df['Categoria'] == 'VENCE_HOJE']
        for _, row in vence_hoje.iterrows():
            acoes.append({
                'Prioridade': '⚠️ URGENTE',
                'Ação': 'Entrega programada para HOJE - Confirmar status',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}",
                'Status Agendamento': row['Status Agendamento']
            })
        
        # 3. ATENÇÃO - Próximas (1-2 dias)
        proximas = df[df['Categoria'] == 'PROXIMA']
        for _, row in proximas.iterrows():
            acoes.append({
                'Prioridade': '🟡 ATENÇÃO',
                'Ação': f'Monitorar - Entrega em {row["Dias até Prazo"]} dias',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}",
                'Status Agendamento': row['Status Agendamento']
            })
        
        # 4. OPERACIONAL - Sem agendamento
        sem_agendamento = df[df['Categoria'] == 'SEM_AGENDAMENTO']
        for _, row in sem_agendamento.iterrows():
            acoes.append({
                'Prioridade': '⚪ OPERACIONAL',
                'Ação': 'Realizar agendamento da entrega',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}",
                'Status Agendamento': row['Status Agendamento']
            })
        
        # 5. FINANCEIRAS - Pendências financeiras
        pendencias_fin = df[df['Pendencia Financeira'] == 'Sim']
        for _, row in pendencias_fin.iterrows():
            acoes.append({
                'Prioridade': '💰 FINANCEIRA',
                'Ação': 'Resolver pendência financeira',
                'Cliente': row['Cliente'],
                'NF': row['NF'],
                'Valor': f"R$ {row['Valor NF']:,.2f}",
                'Status Agendamento': row['Status Agendamento']
            })
        
        # Ordenar por prioridade
        ordem_prioridade = {
            '🔴 CRÍTICA': 1,
            '⚠️ URGENTE': 2,
            '🟡 ATENÇÃO': 3,
            '💰 FINANCEIRA': 4,
            '⚪ OPERACIONAL': 5
        }
        
        acoes.sort(key=lambda x: ordem_prioridade.get(x['Prioridade'], 999))
        
        if not acoes:
            acoes.append({
                'Prioridade': '🟢 OK',
                'Ação': 'Todas as entregas estão no prazo',
                'Cliente': 'N/A',
                'NF': 'N/A',
                'Valor': 'N/A',
                'Status Agendamento': 'N/A'
            })
        
        return acoes

# Instância global
excel_generator = ExcelGenerator()

def get_excel_generator():
    """Retorna instância do gerador Excel"""
    return excel_generator 