"""
Helper para reutilizar funções da API internamente no sistema
Permite usar os mesmos dados JSON em diferentes partes do sistema
"""

import json
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from app import db
from app.embarques.models import Embarque
from app.pedidos.models import Pedido
from app.fretes.models import Frete
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import RelatorioFaturamentoImportado
from app.transportadoras.models import Transportadora
from app.portaria.models import ControlePortaria

class APIDataHelper:
    """Classe para acessar dados da API internamente"""
    
    @staticmethod
    def get_embarques_data(status='ativo', limite=10):
        """Retorna dados de embarques (mesma lógica da API)"""
        try:
            query = Embarque.query
            if status:
                query = query.filter(Embarque.status == status)
            
            embarques = query.order_by(Embarque.id.desc()).limit(limite).all()
            
            resultado = []
            for embarque in embarques:
                resultado.append({
                    'id': embarque.id,
                    'numero': embarque.numero,
                    'status': embarque.status,
                    'data_embarque': embarque.data_embarque.isoformat() if embarque.data_embarque else None,
                    'transportadora': embarque.transportadora.razao_social if embarque.transportadora else None,
                    'total_fretes': len(embarque.fretes) if embarque.fretes else 0
                })
            
            return {
                'success': True,
                'data': resultado,
                'total': len(resultado),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_estatisticas_data(periodo_dias=30):
        """Retorna estatísticas do sistema (mesma lógica da API)"""
        try:
            data_inicio = datetime.now() - timedelta(days=periodo_dias)
            
            # Estatísticas básicas
            total_embarques = Embarque.query.count()
            embarques_ativos = Embarque.query.filter(Embarque.status == 'ativo').count()
            
            total_fretes = Frete.query.count()
            fretes_pendentes = Frete.query.filter(Frete.status_aprovacao == 'pendente').count()
            fretes_aprovados = Frete.query.filter(Frete.status_aprovacao == 'aprovado').count()
            
            total_entregas = EntregaMonitorada.query.count()
            entregas_entregues = EntregaMonitorada.query.filter(
                EntregaMonitorada.status_finalizacao == 'Entregue'
            ).count()
            
            pendencias_financeiras = EntregaMonitorada.query.filter(
                EntregaMonitorada.pendencia_financeira == True
            ).count()
            
            total_transportadoras = Transportadora.query.count()
            transportadoras_ativas = Transportadora.query.filter(
                Transportadora.ativa == True
            ).count()
            
            resultado = {
                'periodo_analisado': f'Últimos {periodo_dias} dias',
                'embarques': {
                    'total': total_embarques,
                    'ativos': embarques_ativos,
                    'cancelados': total_embarques - embarques_ativos
                },
                'fretes': {
                    'total': total_fretes,
                    'pendentes_aprovacao': fretes_pendentes,
                    'aprovados': fretes_aprovados,
                    'percentual_aprovacao': round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0
                },
                'entregas': {
                    'total_monitoradas': total_entregas,
                    'entregues': entregas_entregues,
                    'pendencias_financeiras': pendencias_financeiras,
                    'percentual_entrega': round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0
                },
                'transportadoras': {
                    'total': total_transportadoras,
                    'ativas': transportadoras_ativas
                }
            }
            
            return {
                'success': True,
                'data': resultado,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_cliente_data(cliente_nome, uf_filtro=None, limite=5):
        """Retorna dados detalhados de cliente (mesma lógica da API)"""
        try:
            # Buscar pedidos do cliente
            query = Pedido.query.filter(
                Pedido.raz_social_red.ilike(f"%{cliente_nome}%")
            )
            
            if uf_filtro:
                query = query.filter(Pedido.cod_uf == uf_filtro.upper())
            
            pedidos = query.order_by(desc(Pedido.data_pedido)).limit(limite).all()
            
            if not pedidos:
                return {
                    'success': False,
                    'error': f'Nenhum pedido encontrado para {cliente_nome}' + (f' em {uf_filtro}' if uf_filtro else '')
                }
            
            resultado = []
            
            for pedido in pedidos:
                item_pedido = {
                    'pedido': {
                        'numero': pedido.num_pedido,
                        'data': pedido.data_pedido.strftime('%d/%m/%Y') if pedido.data_pedido else '',
                        'cliente': pedido.raz_social_red,
                        'destino': f"{pedido.nome_cidade}/{pedido.cod_uf}",
                        'valor': pedido.valor_saldo_total,
                        'status': pedido.status_calculado,
                        'nf': pedido.nf or ''
                    },
                    'faturamento': None,
                    'monitoramento': None
                }
                
                # Buscar faturamento se tem NF
                if pedido.nf and pedido.nf.strip():
                    faturamento = RelatorioFaturamentoImportado.query.filter_by(
                        numero_nf=pedido.nf
                    ).first()
                    
                    if faturamento:
                        saldo_carteira = 0
                        if pedido.valor_saldo_total and faturamento.valor_total:
                            saldo_carteira = pedido.valor_saldo_total - faturamento.valor_total
                        
                        item_pedido['faturamento'] = {
                            'data_fatura': faturamento.data_fatura.strftime('%d/%m/%Y') if faturamento.data_fatura else '',
                            'valor_nf': faturamento.valor_total,
                            'saldo_carteira': saldo_carteira,
                            'status_faturamento': 'Parcial' if saldo_carteira > 0 else 'Completo'
                        }
                    
                    # Buscar monitoramento
                    entrega = EntregaMonitorada.query.filter_by(
                        numero_nf=pedido.nf
                    ).first()
                    
                    if entrega:
                        item_pedido['monitoramento'] = {
                            'status_entrega': entrega.status_finalizacao or 'Em andamento',
                            'transportadora': entrega.transportadora,
                            'pendencia_financeira': entrega.pendencia_financeira,
                            'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else None
                        }
                
                resultado.append(item_pedido)
            
            # Resumo
            total_valor = sum(p.valor_saldo_total for p in pedidos if p.valor_saldo_total)
            pedidos_faturados = sum(1 for p in pedidos if p.nf and p.nf.strip())
            
            return {
                'success': True,
                'cliente': cliente_nome.upper(),
                'uf': uf_filtro or 'Todas',
                'resumo': {
                    'total_pedidos': len(pedidos),
                    'valor_total': total_valor,
                    'pedidos_faturados': pedidos_faturados,
                    'percentual_faturado': round((pedidos_faturados/len(pedidos)*100), 1) if pedidos else 0
                },
                'data': resultado,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_fretes_pendentes_data(limite=10):
        """Retorna fretes pendentes de aprovação"""
        try:
            fretes = Frete.query.filter(
                Frete.status_aprovacao == 'pendente'
            ).order_by(Frete.id.desc()).limit(limite).all()
            
            resultado = []
            for frete in fretes:
                resultado.append({
                    'id': frete.id,
                    'embarque_numero': frete.embarque.numero if frete.embarque else None,
                    'transportadora': frete.transportadora.razao_social if frete.transportadora else None,
                    'valor_cotado': float(frete.valor_cotado) if frete.valor_cotado else None,
                    'status_aprovacao': frete.status_aprovacao,
                    'tem_cte': bool(frete.numero_cte),
                    'cliente': frete.nome_cliente,
                    'destino': f"{frete.cidade_destino}/{frete.uf_destino}"
                })
            
            return {
                'success': True,
                'data': resultado,
                'total': len(resultado),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_alertas_sistema():
        """Retorna alertas e notificações do sistema"""
        try:
            alertas = []
            
            # Verifica fretes pendentes há mais de 2 dias
            fretes_antigos = Frete.query.filter(
                Frete.status_aprovacao == 'pendente',
                Frete.data_criacao < datetime.now() - timedelta(days=2)
            ).count()
            
            if fretes_antigos > 0:
                alertas.append({
                    'tipo': 'warning',
                    'titulo': 'Fretes Pendentes',
                    'mensagem': f'{fretes_antigos} fretes pendentes há mais de 2 dias',
                    'icone': 'fas fa-clock',
                    'url': '/fretes/listar?status_aprovacao=pendente'
                })
            
            # Verifica pendências financeiras
            pendencias = EntregaMonitorada.query.filter(
                EntregaMonitorada.pendencia_financeira == True
            ).count()
            
            if pendencias > 10:
                alertas.append({
                    'tipo': 'danger',
                    'titulo': 'Pendências Financeiras',
                    'mensagem': f'{pendencias} entregas com pendências financeiras',
                    'icone': 'fas fa-exclamation-triangle',
                    'url': '/monitoramento/listar_entregas?pendencia_financeira=true'
                })
            
            # Verifica embarques sem data de embarque há mais de 1 dia
            embarques_sem_data = Embarque.query.filter(
                Embarque.status == 'ativo',
                Embarque.data_embarque.is_(None),
                Embarque.criado_em < datetime.now() - timedelta(days=1)
            ).count()
            
            if embarques_sem_data > 0:
                alertas.append({
                    'tipo': 'info',
                    'titulo': 'Embarques sem Data',
                    'mensagem': f'{embarques_sem_data} embarques ativos sem data de embarque',
                    'icone': 'fas fa-calendar-alt',
                    'url': '/embarques/listar_embarques?status=ativo'
                })
            
            return {
                'success': True,
                'data': alertas,
                'total': len(alertas),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def format_money(value):
        """Helper para formatar valores monetários"""
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    @staticmethod
    def format_percentage(value, total):
        """Helper para formatar percentuais"""
        if total == 0:
            return "0%"
        return f"{(value/total*100):.1f}%"

# Funções de conveniência para usar nos templates
def get_dashboard_stats():
    """Função de conveniência para usar em templates"""
    return APIDataHelper.get_estatisticas_data()

def get_recent_embarques(limite=5):
    """Função de conveniência para embarques recentes"""
    return APIDataHelper.get_embarques_data(limite=limite)

def get_system_alerts():
    """Função de conveniência para alertas do sistema"""
    return APIDataHelper.get_alertas_sistema() 