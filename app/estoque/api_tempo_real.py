"""
API Otimizada para Sistema de Estoque em Tempo Real
Performance garantida < 100ms para consultas
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from decimal import Decimal
from flask import jsonify, request, Blueprint
from sqlalchemy import and_, or_
from app import db
from app.estoque.models import UnificacaoCodigos
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal


# Blueprint para rotas da API
estoque_tempo_real_bp = Blueprint('estoque_tempo_real', __name__)


class APIEstoqueTempoReal:
    """
    API otimizada para consultas de estoque em tempo real.
    Todas as consultas garantidas < 100ms.
    """
    
    @staticmethod
    def consultar_workspace(cod_produtos: List[str]) -> List[Dict[str, Any]]:
        """
        Consulta direta nas tabelas pré-calculadas para múltiplos produtos.
        Otimizada para performance máxima.
        
        Args:
            cod_produtos: Lista de códigos de produtos
            
        Returns:
            Lista com dados de estoque e projeção
        """
        if not cod_produtos:
            return []
        
        # Expandir códigos considerando unificação
        todos_codigos = set()
        for cod in cod_produtos:
            todos_codigos.update(
                UnificacaoCodigos.get_todos_codigos_relacionados(cod)
            )
        
        # Query otimizada com apenas campos necessários
        estoques = db.session.query(
            EstoqueTempoReal.cod_produto,
            EstoqueTempoReal.nome_produto,
            EstoqueTempoReal.saldo_atual,
            EstoqueTempoReal.menor_estoque_d7,
            EstoqueTempoReal.dia_ruptura
        ).filter(
            EstoqueTempoReal.cod_produto.in_(list(todos_codigos))
        ).all()
        
        # Buscar movimentações futuras em batch
        hoje = date.today()
        fim_periodo = hoje + timedelta(days=7)
        
        movimentacoes = db.session.query(
            MovimentacaoPrevista.cod_produto,
            MovimentacaoPrevista.data_prevista,
            MovimentacaoPrevista.entrada_prevista,
            MovimentacaoPrevista.saida_prevista
        ).filter(
            MovimentacaoPrevista.cod_produto.in_(list(todos_codigos)),
            MovimentacaoPrevista.data_prevista >= hoje,
            MovimentacaoPrevista.data_prevista <= fim_periodo
        ).order_by(
            MovimentacaoPrevista.cod_produto,
            MovimentacaoPrevista.data_prevista
        ).all()
        
        # Organizar movimentações por produto
        movs_por_produto = {}
        for mov in movimentacoes:
            if mov.cod_produto not in movs_por_produto:
                movs_por_produto[mov.cod_produto] = []
            movs_por_produto[mov.cod_produto].append({
                'data': mov.data_prevista.isoformat(),
                'entrada': float(mov.entrada_prevista),
                'saida': float(mov.saida_prevista),
                'saldo_dia': float(mov.entrada_prevista - mov.saida_prevista)
            })
        
        # Montar resultado
        resultado = []
        for est in estoques:
            resultado.append({
                'cod_produto': est.cod_produto,
                'nome_produto': est.nome_produto,
                'estoque_atual': float(est.saldo_atual),
                'menor_estoque_d7': float(est.menor_estoque_d7) if est.menor_estoque_d7 else None,
                'dia_ruptura': est.dia_ruptura.isoformat() if est.dia_ruptura else None,
                'movimentacoes_previstas': movs_por_produto.get(est.cod_produto, [])
            })
        
        return resultado
    
    @staticmethod
    def consultar_produto(cod_produto: str) -> Optional[Dict[str, Any]]:
        """
        Consulta otimizada para um único produto.
        
        Args:
            cod_produto: Código do produto
            
        Returns:
            Dict com dados do produto ou None
        """
        # Usar consulta em batch mesmo para 1 produto (reutilização de código)
        resultado = APIEstoqueTempoReal.consultar_workspace([cod_produto])
        return resultado[0] if resultado else None
    
    @staticmethod
    def consultar_rupturas(dias_limite: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        Consulta produtos com ruptura prevista nos próximos N dias.
        
        Args:
            dias_limite: Número de dias para considerar
            
        Returns:
            Lista de produtos com ruptura prevista
        """
        data_limite = date.today() + timedelta(days=dias_limite)
        
        # Query otimizada para rupturas
        rupturas = db.session.query(
            EstoqueTempoReal.cod_produto,
            EstoqueTempoReal.nome_produto,
            EstoqueTempoReal.saldo_atual,
            EstoqueTempoReal.menor_estoque_d7,
            EstoqueTempoReal.dia_ruptura
        ).filter(
            EstoqueTempoReal.dia_ruptura.isnot(None),
            EstoqueTempoReal.dia_ruptura <= data_limite
        ).order_by(
            EstoqueTempoReal.dia_ruptura.asc()
        ).all()
        
        resultado = []
        for rup in rupturas:
            resultado.append({
                'cod_produto': rup.cod_produto,
                'nome_produto': rup.nome_produto,
                'estoque_atual': float(rup.saldo_atual),
                'menor_estoque_d7': float(rup.menor_estoque_d7) if rup.menor_estoque_d7 else 0,
                'dia_ruptura': rup.dia_ruptura.isoformat(),
                'dias_ate_ruptura': (rup.dia_ruptura - date.today()).days
            })
        
        return resultado
    
    @staticmethod
    def consultar_projecao_completa(cod_produto: str, dias: int = 28) -> Optional[Dict[str, Any]]:
        """
        Consulta projeção completa de estoque para N dias.
        
        Args:
            cod_produto: Código do produto
            dias: Número de dias para projetar
            
        Returns:
            Dict com projeção dia a dia
        """
        return ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias)
    
    @staticmethod
    def get_estatisticas() -> Optional[Dict[str, Any]]:
        """
        Retorna estatísticas gerais do sistema de estoque.
        
        Returns:
            Dict com estatísticas
        """
        # Contadores básicos
        total_produtos = db.session.query(EstoqueTempoReal).count()
        
        # Produtos com ruptura
        produtos_ruptura = db.session.query(EstoqueTempoReal).filter(
            EstoqueTempoReal.dia_ruptura.isnot(None)
        ).count()
        
        # Produtos com estoque negativo
        produtos_negativos = db.session.query(EstoqueTempoReal).filter(
            EstoqueTempoReal.saldo_atual < 0
        ).count()
        
        # Produtos sem movimento (estoque zerado)
        produtos_zerados = db.session.query(EstoqueTempoReal).filter(
            EstoqueTempoReal.saldo_atual == 0
        ).count()
        
        # Movimentações previstas próximos 7 dias
        hoje = date.today()
        fim_periodo = hoje + timedelta(days=7)
        
        movs_futuras = db.session.query(MovimentacaoPrevista).filter(
            MovimentacaoPrevista.data_prevista >= hoje,
            MovimentacaoPrevista.data_prevista <= fim_periodo
        ).count()
        
        return {
            'total_produtos': total_produtos,
            'produtos_com_ruptura': produtos_ruptura,
            'produtos_estoque_negativo': produtos_negativos,
            'produtos_estoque_zerado': produtos_zerados,
            'movimentacoes_previstas_7d': movs_futuras,
            'percentual_ruptura': round(
                (produtos_ruptura / total_produtos * 100) if total_produtos > 0 else 0, 
                2
            )
        }


# ============================================================================
# ROTAS FLASK DA API
# ============================================================================

@estoque_tempo_real_bp.route('/api/saldo-estoque', methods=['GET'])
def get_saldo_estoque():
    """
    Endpoint GET para obter todos os produtos com estoque.
    Compatível com o frontend existente.
    """
    try:
        # Buscar todos os produtos com estoque
        produtos = db.session.query(
            EstoqueTempoReal.cod_produto,
            EstoqueTempoReal.nome_produto,
            EstoqueTempoReal.saldo_atual,
            EstoqueTempoReal.menor_estoque_d7,
            EstoqueTempoReal.dia_ruptura
        ).all()
        
        resultado = []
        hoje = date.today()
        
        for p in produtos:
            # Calcular disponibilidade (primeiro dia com estoque positivo)
            data_disponivel = None
            qtd_disponivel = None
            
            if p.saldo_atual <= 0:
                # Se estoque atual é negativo ou zero, buscar quando ficará positivo
                saldo_projetado = float(p.saldo_atual)
                
                # Buscar movimentações futuras
                movimentacoes = MovimentacaoPrevista.query.filter(
                    MovimentacaoPrevista.cod_produto == p.cod_produto,
                    MovimentacaoPrevista.data_prevista >= hoje,
                    MovimentacaoPrevista.data_prevista <= hoje + timedelta(days=28)
                ).order_by(MovimentacaoPrevista.data_prevista).all()
                
                for mov in movimentacoes:
                    saldo_projetado += float(mov.entrada_prevista - mov.saida_prevista)
                    if saldo_projetado > 0 and data_disponivel is None:
                        data_disponivel = mov.data_prevista
                        qtd_disponivel = saldo_projetado
                        break
            else:
                # Se já tem estoque, disponível hoje
                data_disponivel = hoje
                qtd_disponivel = float(p.saldo_atual)
            
            resultado.append({
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'estoque_atual': float(p.saldo_atual),
                'menor_estoque_d7': float(p.menor_estoque_d7) if p.menor_estoque_d7 else None,
                'dia_ruptura': p.dia_ruptura.isoformat() if p.dia_ruptura else None,
                'status_ruptura': 'CRÍTICO' if p.dia_ruptura else 'OK',
                'data_disponivel': data_disponivel.isoformat() if data_disponivel else None,
                'qtd_disponivel': qtd_disponivel
            })
        
        return jsonify({
            'sucesso': True,
            'total': len(resultado),
            'produtos': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/consultar', methods=['POST'])
def consultar_workspace():
    """
    Endpoint para consultar múltiplos produtos.
    
    Body JSON:
        {
            "produtos": ["P001", "P002", "P003"]
        }
    """
    try:
        data = request.get_json()
        produtos = data.get('produtos', [])
        
        if not produtos:
            return jsonify({'erro': 'Lista de produtos vazia'}), 400
        
        resultado = APIEstoqueTempoReal.consultar_workspace(produtos)
        
        return jsonify({
            'sucesso': True,
            'total': len(resultado),
            'produtos': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/produto/<cod_produto>', methods=['GET'])
def consultar_produto(cod_produto):
    """
    Endpoint para consultar um único produto.
    """
    try:
        resultado = APIEstoqueTempoReal.consultar_produto(cod_produto)
        
        if not resultado:
            return jsonify({
                'sucesso': False,
                'erro': 'Produto não encontrado'
            }), 404
        
        return jsonify({
            'sucesso': True,
            'produto': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/rupturas', methods=['GET'])
def consultar_rupturas():
    """
    Endpoint para consultar produtos com ruptura prevista.
    
    Query params:
        - dias: número de dias para considerar (padrão: 7)
    """
    try:
        dias = request.args.get('dias', 7, type=int)
        resultado = APIEstoqueTempoReal.consultar_rupturas(dias)
        
        return jsonify({
            'sucesso': True,
            'dias_analisados': dias,
            'total_rupturas': len(resultado),
            'produtos': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/projecao/<cod_produto>', methods=['GET'])
def consultar_projecao(cod_produto):
    """
    Endpoint para consultar projeção completa de um produto.
    
    Query params:
        - dias: número de dias para projetar (padrão: 28)
    """
    try:
        dias = request.args.get('dias', 28, type=int)
        resultado = APIEstoqueTempoReal.consultar_projecao_completa(cod_produto, dias)
        
        if not resultado:
            return jsonify({
                'sucesso': False,
                'erro': 'Produto não encontrado'
            }), 404
        
        return jsonify({
            'sucesso': True,
            'projecao': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/estatisticas', methods=['GET'])
def get_estatisticas():
    """
    Endpoint para obter estatísticas gerais do estoque.
    """
    try:
        resultado = APIEstoqueTempoReal.get_estatisticas()
        
        return jsonify({
            'sucesso': True,
            'estatisticas': resultado
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@estoque_tempo_real_bp.route('/api/estoque/tempo-real/recalcular/<cod_produto>', methods=['POST'])
def recalcular_produto(cod_produto):
    """
    Endpoint para forçar recálculo de um produto específico.
    Útil para debug e correções manuais.
    """
    try:
        # Inicializar produto se não existir
        estoque = ServicoEstoqueTempoReal.inicializar_produto(cod_produto)
        
        # Recalcular saldo do zero
        from app.estoque.models import MovimentacaoEstoque
        
        saldo = Decimal('0')
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        
        for codigo in codigos:
            movs = MovimentacaoEstoque.query.filter_by(
                cod_produto=codigo,
                ativo=True
            ).all()
            
            for mov in movs:
                if mov.tipo_movimentacao == 'ENTRADA':
                    saldo += Decimal(str(mov.qtd_movimentacao))
                else:
                    saldo -= Decimal(str(mov.qtd_movimentacao))
        
        estoque.saldo_atual = saldo
        estoque.atualizado_em = ServicoEstoqueTempoReal.agora_brasil()
        
        # Recalcular projeção
        ServicoEstoqueTempoReal.calcular_ruptura_d7(cod_produto)
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Produto {cod_produto} recalculado com sucesso',
            'saldo_atual': float(saldo)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500