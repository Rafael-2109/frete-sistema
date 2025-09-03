"""
Service para o Dashboard do módulo de Manufatura
"""
from app import db
from app.manufatura.models import (
    OrdemProducao, RequisicaoCompras, PlanoMestreProducao,
    PrevisaoDemanda
)
from datetime import datetime, timedelta
from sqlalchemy import func


class DashboardService:
    
    def obter_metricas(self):
        """Obtém métricas principais para o dashboard"""
        try:
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            
            # Ordens de produção
            total_ordens = OrdemProducao.query.count()
            ordens_abertas = OrdemProducao.query.filter(
                OrdemProducao.status.in_(['Planejada', 'Liberada', 'Em Produção'])
            ).count()
            
            # Requisições de compras
            necessidades_pendentes = RequisicaoCompras.query.filter_by(
                necessidade=True,
                status='Pendente'
            ).count()
            
            requisicoes_mes = RequisicaoCompras.query.filter(
                db.extract('month', RequisicaoCompras.data_requisicao_criacao) == mes_atual,
                db.extract('year', RequisicaoCompras.data_requisicao_criacao) == ano_atual
            ).count()
            
            # Previsão vs Realizado
            previsao_mes = db.session.query(
                func.sum(PrevisaoDemanda.qtd_demanda_prevista)
            ).filter_by(
                data_mes=mes_atual,
                data_ano=ano_atual
            ).scalar() or 0
            
            realizado_mes = db.session.query(
                func.sum(PrevisaoDemanda.qtd_demanda_realizada)
            ).filter_by(
                data_mes=mes_atual,
                data_ano=ano_atual
            ).scalar() or 0
            
            # Taxa de cumprimento
            taxa_cumprimento = (realizado_mes / previsao_mes * 100) if previsao_mes > 0 else 0
            
            # Plano Mestre - Métricas adicionais
            planos_mes = PlanoMestreProducao.query.filter_by(
                data_mes=mes_atual,
                data_ano=ano_atual
            ).all()
            
            total_reposicao_sugerida = sum(float(p.qtd_reposicao_sugerida or 0) for p in planos_mes)
            produtos_abaixo_seguranca = sum(1 for p in planos_mes 
                                           if (p.qtd_estoque or 0) < (p.qtd_estoque_seguranca or 0))
            
            return {
                'ordens': {
                    'total': total_ordens,
                    'abertas': ordens_abertas,
                    'concluidas_mes': OrdemProducao.query.filter(
                        OrdemProducao.status == 'Concluída',
                        db.extract('month', OrdemProducao.data_fim_real) == mes_atual,
                        db.extract('year', OrdemProducao.data_fim_real) == ano_atual
                    ).count()
                },
                'compras': {
                    'necessidades_pendentes': necessidades_pendentes,
                    'requisicoes_mes': requisicoes_mes
                },
                'previsao': {
                    'previsto_mes': float(previsao_mes),
                    'realizado_mes': float(realizado_mes),
                    'taxa_cumprimento': round(taxa_cumprimento, 1)
                },
                'plano_mestre': {
                    'total_reposicao_sugerida': round(total_reposicao_sugerida, 2),
                    'produtos_abaixo_seguranca': produtos_abaixo_seguranca,
                    'planos_aprovados': sum(1 for p in planos_mes if p.status_geracao == 'aprovado')
                }
            }
            
        except Exception as e:
            raise Exception(f"Erro ao obter métricas: {str(e)}")
    
    def obter_ordens_abertas(self):
        """Obtém lista de ordens de produção abertas"""
        try:
            ordens = OrdemProducao.query.filter(
                OrdemProducao.status.in_(['Planejada', 'Liberada', 'Em Produção'])
            ).order_by(OrdemProducao.data_inicio_prevista).limit(10).all()
            
            return [{
                'numero_ordem': o.numero_ordem,
                'cod_produto': o.cod_produto,
                'nome_produto': o.nome_produto,
                'status': o.status,
                'qtd_planejada': float(o.qtd_planejada or 0),
                'qtd_produzida': float(o.qtd_produzida or 0),
                'progresso': round((o.qtd_produzida / o.qtd_planejada * 100) if o.qtd_planejada > 0 else 0, 1),
                'data_inicio': o.data_inicio_prevista.strftime('%d/%m/%Y') if o.data_inicio_prevista else None,
                'linha_producao': o.linha_producao
            } for o in ordens]
            
        except Exception as e:
            raise Exception(f"Erro ao obter ordens abertas: {str(e)}")
    
    def obter_necessidades_compras(self):
        """Obtém lista de necessidades de compras urgentes"""
        try:
            data_limite = datetime.now().date() + timedelta(days=15)
            
            necessidades = RequisicaoCompras.query.filter(
                RequisicaoCompras.necessidade == True,
                RequisicaoCompras.status == 'Pendente',
                RequisicaoCompras.data_necessidade <= data_limite
            ).order_by(RequisicaoCompras.data_necessidade).limit(10).all()
            
            return [{
                'cod_produto': n.cod_produto,
                'nome_produto': n.nome_produto,
                'qtd_necessaria': float(n.qtd_produto_requisicao or 0),
                'data_necessidade': n.data_necessidade.strftime('%d/%m/%Y') if n.data_necessidade else None,
                'dias_restantes': (n.data_necessidade - datetime.now().date()).days if n.data_necessidade else None,
                'urgente': (n.data_necessidade - datetime.now().date()).days <= 7 if n.data_necessidade else False
            } for n in necessidades]
            
        except Exception as e:
            raise Exception(f"Erro ao obter necessidades de compras: {str(e)}")
    
    def obter_plano_mestre_resumo(self, mes=None, ano=None):
        """Obtém resumo do plano mestre de produção"""
        try:
            if not mes:
                mes = datetime.now().month
            if not ano:
                ano = datetime.now().year
            
            planos = PlanoMestreProducao.query.filter_by(
                data_mes=mes,
                data_ano=ano
            ).order_by(PlanoMestreProducao.qtd_reposicao_sugerida.desc()).limit(20).all()
            
            return [{
                'id': p.separacao_lote_id,
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_demanda_prevista': float(p.qtd_demanda_prevista or 0),
                'qtd_estoque': float(p.qtd_estoque or 0),
                'qtd_estoque_seguranca': float(p.qtd_estoque_seguranca or 0),
                'qtd_producao_programada': float(p.qtd_producao_programada or 0),
                'qtd_reposicao_sugerida': float(p.qtd_reposicao_sugerida or 0),
                'status_geracao': p.status_geracao,
                'critico': (p.qtd_estoque or 0) < (p.qtd_estoque_seguranca or 0)
            } for p in planos]
            
        except Exception as e:
            raise Exception(f"Erro ao obter resumo do plano mestre: {str(e)}")