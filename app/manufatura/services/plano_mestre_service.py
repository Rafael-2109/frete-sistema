"""
Service para Plano Mestre de Produção
"""
from app import db
from app.manufatura.models import (
    PlanoMestreProducao, PrevisaoDemanda, RecursosProducao,
    OrdemProducao
)
from app.estoque.models import MovimentacaoEstoque
from datetime import datetime
from sqlalchemy import func, extract, and_
from decimal import Decimal


class PlanoMestreService:
    
    def gerar_plano_mestre(self, mes, ano, usuario='Sistema'):
        """Gera plano mestre baseado na previsão de demanda"""
        
        # Buscar previsões aprovadas
        previsoes = PrevisaoDemanda.query.filter_by(
            data_mes=mes,
            data_ano=ano
        ).all()
        
        planos_criados = []
        
        for previsao in previsoes:
            # Verificar se já existe plano
            plano_existe = PlanoMestreProducao.query.filter_by(
                data_mes=mes,
                data_ano=ano,
                cod_produto=previsao.cod_produto
            ).first()
            
            if not plano_existe:
                # Calcular estoque atual
                estoque_atual = self._calcular_estoque_produto(previsao.cod_produto)
                
                # Calcular produção já programada
                producao_programada = self._calcular_producao_programada(
                    previsao.cod_produto, mes, ano
                )
                
                # Calcular produção realizada
                producao_realizada = self._calcular_producao_realizada(
                    previsao.cod_produto, mes, ano
                )
                
                # Buscar parâmetros de produção
                recursos = RecursosProducao.query.filter_by(
                    cod_produto=previsao.cod_produto
                ).first()
                
                # Criar plano
                plano = PlanoMestreProducao(
                    data_mes=mes,
                    data_ano=ano,
                    cod_produto=previsao.cod_produto,
                    nome_produto=previsao.nome_produto,
                    qtd_demanda_prevista=previsao.qtd_demanda_prevista,
                    disparo_producao=previsao.disparo_producao,
                    qtd_producao_programada=producao_programada,
                    qtd_producao_realizada=producao_realizada,
                    qtd_estoque=estoque_atual,
                    qtd_estoque_seguranca=0,  # Definir manualmente
                    qtd_lote_ideal=recursos.qtd_lote_ideal if recursos else None,
                    qtd_lote_minimo=recursos.qtd_lote_minimo if recursos else None,
                    status_geracao='rascunho',
                    criado_por=usuario
                )
                
                # Calcular reposição sugerida
                plano.qtd_reposicao_sugerida = self._calcular_reposicao_sugerida(plano)
                
                db.session.add(plano)
                planos_criados.append(plano)
        
        if planos_criados:
            db.session.commit()
        
        return planos_criados
    
    def _calcular_estoque_produto(self, cod_produto):
        """Calcula estoque atual do produto"""
        
        resultado = db.session.query(
            func.sum(
                func.case(
                    [
                        (MovimentacaoEstoque.tipo_movimentacao.in_([
                            'ENTRADA_COMPRA', 'PRODUCAO', 'AJUSTE_POSITIVO'
                        ]), MovimentacaoEstoque.qtd_movimentacao),
                        (MovimentacaoEstoque.tipo_movimentacao.in_([
                            'SAIDA_VENDA', 'CONSUMO_BOM', 'AJUSTE_NEGATIVO'
                        ]), -MovimentacaoEstoque.qtd_movimentacao)
                    ],
                    else_=0
                )
            )
        ).filter(
            MovimentacaoEstoque.cod_produto == cod_produto
        ).scalar()
        
        return Decimal(str(resultado or 0))
    
    def _calcular_producao_programada(self, cod_produto, mes, ano):
        """Calcula produção já programada para o período"""
        
        resultado = db.session.query(
            func.sum(OrdemProducao.qtd_planejada)
        ).filter(
            OrdemProducao.cod_produto == cod_produto,
            OrdemProducao.status.in_(['Planejada', 'Liberada', 'Em Produção']),
            extract('month', OrdemProducao.data_fim_prevista) == mes,
            extract('year', OrdemProducao.data_fim_prevista) == ano
        ).scalar()
        
        return Decimal(str(resultado or 0))
    
    def _calcular_producao_realizada(self, cod_produto, mes, ano):
        """Calcula produção realizada no período"""
        
        resultado = db.session.query(
            func.sum(MovimentacaoEstoque.qtd_movimentacao)
        ).filter(
            MovimentacaoEstoque.cod_produto == cod_produto,
            MovimentacaoEstoque.tipo_movimentacao == 'PRODUCAO',
            extract('month', MovimentacaoEstoque.data_movimentacao) == mes,
            extract('year', MovimentacaoEstoque.data_movimentacao) == ano
        ).scalar()
        
        return Decimal(str(resultado or 0))
    
    def _calcular_reposicao_sugerida(self, plano):
        """Calcula quantidade de reposição sugerida"""
        
        necessidade = (
            (plano.qtd_demanda_prevista or 0) +
            (plano.qtd_estoque_seguranca or 0) -
            (plano.qtd_estoque or 0) -
            (plano.qtd_producao_programada or 0) -
            (plano.qtd_producao_realizada or 0)
        )
        
        return max(Decimal('0'), necessidade)
    
    def aprovar_plano(self, plano_id, usuario='Sistema'):
        """Aprova plano mestre para execução"""
        
        plano = PlanoMestreProducao.query.get_or_404(plano_id)
        
        if plano.status_geracao == 'aprovado':
            raise ValueError("Plano já está aprovado")
        
        plano.status_geracao = 'aprovado'
        plano.criado_por = usuario
        
        # Se tem reposição sugerida e é MTS, pode gerar ordem automaticamente
        if plano.qtd_reposicao_sugerida > 0 and plano.disparo_producao == 'MTS':
            self._gerar_ordem_producao_mts(plano)
        
        db.session.commit()
        return plano
    
    def _gerar_ordem_producao_mts(self, plano):
        """Gera ordem de produção MTS a partir do plano"""
        
        from app.manufatura.services.ordem_producao_service import OrdemProducaoService
        
        service = OrdemProducaoService()
        
        # Calcular quantidade respeitando lote mínimo
        qtd_producao = plano.qtd_reposicao_sugerida
        if plano.qtd_lote_minimo and qtd_producao < plano.qtd_lote_minimo:
            qtd_producao = plano.qtd_lote_minimo
        
        # Arredondar para lote ideal se próximo
        if plano.qtd_lote_ideal:
            num_lotes = qtd_producao / plano.qtd_lote_ideal
            if num_lotes > int(num_lotes) and (num_lotes - int(num_lotes)) > 0.7:
                qtd_producao = plano.qtd_lote_ideal * (int(num_lotes) + 1)
        
        # Criar ordem
        ordem_data = {
            'origem_ordem': 'PMP',
            'cod_produto': plano.cod_produto,
            'nome_produto': plano.nome_produto,
            'qtd_planejada': qtd_producao,
            'data_inicio_prevista': datetime.now().date(),
            'data_fim_prevista': datetime(plano.data_ano, plano.data_mes, 28).date()
        }
        
        return service.criar_ordem(ordem_data)
    
    def obter_resumo_plano(self, mes, ano):
        """Obtém resumo do plano mestre"""
        
        planos = PlanoMestreProducao.query.filter_by(
            data_mes=mes,
            data_ano=ano
        ).all()
        
        resumo = {
            'total_produtos': len(planos),
            'total_demanda': sum(p.qtd_demanda_prevista or 0 for p in planos),
            'total_estoque': sum(p.qtd_estoque or 0 for p in planos),
            'total_reposicao': sum(p.qtd_reposicao_sugerida or 0 for p in planos),
            'produtos_criticos': [],
            'status': {
                'rascunho': sum(1 for p in planos if p.status_geracao == 'rascunho'),
                'aprovado': sum(1 for p in planos if p.status_geracao == 'aprovado'),
                'executando': sum(1 for p in planos if p.status_geracao == 'executando'),
                'concluido': sum(1 for p in planos if p.status_geracao == 'concluido')
            }
        }
        
        # Identificar produtos críticos (estoque < segurança)
        for plano in planos:
            if plano.qtd_estoque < plano.qtd_estoque_seguranca:
                resumo['produtos_criticos'].append({
                    'cod_produto': plano.cod_produto,
                    'nome_produto': plano.nome_produto,
                    'estoque': float(plano.qtd_estoque or 0),
                    'seguranca': float(plano.qtd_estoque_seguranca or 0),
                    'deficit': float(plano.qtd_estoque_seguranca - plano.qtd_estoque)
                })
        
        return resumo