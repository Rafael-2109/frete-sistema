"""
Camada de Compatibilidade para Migração Gradual
================================================
Este módulo fornece uma camada de compatibilidade para migrar gradualmente
de SaldoEstoque para ServicoEstoqueSimples.

Data: 02/09/2025
"""

from datetime import date, timedelta
from typing import Dict, Any, Optional
import logging

from app import db
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.producao.models import ProgramacaoProducao

logger = logging.getLogger(__name__)


class SaldoEstoqueCompativel:
    """
    Classe de compatibilidade que replica a interface de SaldoEstoque
    mas usa ServicoEstoqueSimples internamente.
    
    Isso permite migração gradual sem quebrar o código existente.
    """
    
    @staticmethod
    def calcular_estoque_inicial(cod_produto: str) -> float:
        """
        Calcula estoque inicial (D0) - compatível com SaldoEstoque.calcular_estoque_inicial
        """
        try:
            # Usar o novo serviço
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
            return float(estoque_atual) if estoque_atual else 0.0
        except Exception as e:
            logger.error(f"Erro ao calcular estoque inicial: {e}")
            return 0.0
    
    @staticmethod
    def calcular_producao_periodo(cod_produto: str, data_inicio: date, data_fim: date) -> float:
        """
        Calcula produção programada para um período - compatível com SaldoEstoque
        """
        try:
            # Query direta similar ao ServicoEstoqueSimples
            producao = db.session.query(
                db.func.sum(ProgramacaoProducao.qtd_programada)
            ).filter(
                ProgramacaoProducao.cod_produto == cod_produto,
                ProgramacaoProducao.data_programacao >= data_inicio,
                ProgramacaoProducao.data_programacao <= data_fim
            ).scalar()
            
            return float(producao) if producao else 0.0
        except Exception as e:
            logger.error(f"Erro ao calcular produção do período: {e}")
            return 0.0
    
    @staticmethod
    def obter_resumo_produto(cod_produto: str, nome_produto: str = None) -> Optional[Dict[str, Any]]:
        """
        Obtém resumo completo de um produto - compatível com SaldoEstoque
        """
        try:
            # Usar o novo serviço para obter projeção
            projecao = ServicoEstoqueSimples.get_projecao_completa(cod_produto, dias=28)
            
            if not projecao:
                return None
            
            # Formatar no mesmo formato que SaldoEstoque retornava
            return {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto or cod_produto,
                'estoque_atual': projecao.get('estoque_atual', 0),
                'estoque_d0': projecao.get('estoque_atual', 0),
                'menor_estoque_d7': projecao.get('menor_estoque_d7', 0),
                'dia_ruptura': projecao.get('dia_ruptura'),
                'projecao_29_dias': projecao.get('projecao', []),
                'projecao': projecao.get('projecao', [])  # Compatibilidade
            }
        except Exception as e:
            logger.error(f"Erro ao obter resumo do produto: {e}")
            return None
    
    @staticmethod
    def calcular_projecao_completa(cod_produto: str) -> list:
        """
        Calcula projeção completa - compatível com SaldoEstoque
        """
        try:
            projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=28)
            return projecao.get('projecao', [])
        except Exception as e:
            logger.error(f"Erro ao calcular projeção completa: {e}")
            return []
    
    @staticmethod
    def calcular_previsao_ruptura(projecao: list) -> Optional[date]:
        """
        Calcula previsão de ruptura baseada na projeção
        """
        try:
            for dia in projecao:
                if dia.get('saldo_final', 0) < 0:
                    return dia.get('data')
            return None
        except Exception as e:
            logger.error(f"Erro ao calcular previsão de ruptura: {e}")
            return None
    
    @staticmethod
    def _calcular_qtd_total_carteira(cod_produto: str) -> float:
        """
        Calcula quantidade total na carteira (para compatibilidade)
        """
        try:
            # Usar ServicoEstoqueSimples para calcular saídas previstas
            saidas = ServicoEstoqueSimples.calcular_saidas_previstas(
                cod_produto, 
                date.today(), 
                date.today() + timedelta(days=90)
            )
            
            total = sum(dia.get('saida_prevista', 0) for dia in saidas.values())
            return float(total)
        except Exception as e:
            logger.error(f"Erro ao calcular qtd total carteira: {e}")
            return 0.0
    
    @staticmethod
    def _calcular_saidas_completas(cod_produto: str, data_calculo: date) -> float:
        """
        Calcula saídas completas para uma data (compatibilidade)
        """
        try:
            saidas = ServicoEstoqueSimples.calcular_saidas_previstas(
                cod_produto,
                data_calculo,
                data_calculo
            )
            
            if data_calculo.isoformat() in saidas:
                return float(saidas[data_calculo.isoformat()].get('saida_prevista', 0))
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao calcular saídas completas: {e}")
            return 0.0
    
    @staticmethod
    def obter_produtos_com_estoque():
        """
        Obtém lista de produtos com estoque (compatibilidade)
        """
        try:
            from app.estoque.models import MovimentacaoEstoque
            
            # Query similar ao ServicoEstoqueSimples
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto,
                db.func.sum(MovimentacaoEstoque.qtd_movimentacao).label('saldo')
            ).filter(
                MovimentacaoEstoque.ativo == True  # Apenas registros ativos
            ).group_by(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).having(
                db.func.sum(MovimentacaoEstoque.qtd_movimentacao) != 0
            ).all()
            
            # Converter para lista de dicionários (compatibilidade com routes.py)
            produtos_dict = []
            for produto in produtos:
                produtos_dict.append({
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'saldo': float(produto.saldo) if produto.saldo else 0
                })
            
            return produtos_dict
        except Exception as e:
            logger.error(f"Erro ao obter produtos com estoque: {e}")
            return []
    
    @staticmethod
    def processar_ajuste_estoque(cod_produto: str, qtd_ajuste: float, motivo: str = None, 
                                 usuario: str = 'Sistema'):
        """
        Processa ajuste de estoque (compatibilidade)
        """
        try:
            from app.estoque.models import MovimentacaoEstoque
            from app.utils.timezone import agora_brasil
            
            # Determinar tipo de ajuste baseado no valor
            tipo_ajuste = 'AJUSTE'
            
            # Buscar nome do produto se existir
            produto_existente = MovimentacaoEstoque.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            nome_produto = produto_existente.nome_produto if produto_existente else cod_produto
            
            # Criar movimentação de ajuste
            mov = MovimentacaoEstoque(
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                qtd_movimentacao=qtd_ajuste,  # Já vem com sinal correto
                tipo_movimentacao=tipo_ajuste,
                local_movimentacao='AJUSTE',
                data_movimentacao=date.today(),
                observacao=motivo or f"Ajuste manual",
                tipo_origem='MANUAL',
                criado_por=usuario
            )
            
            db.session.add(mov)
            db.session.commit()
            
            logger.info(f"Ajuste de estoque processado: {cod_produto} - {qtd_ajuste} ({tipo_ajuste})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar ajuste de estoque: {e}")
            db.session.rollback()
            return False


# Alias para facilitar migração gradual
SaldoEstoque = SaldoEstoqueCompativel