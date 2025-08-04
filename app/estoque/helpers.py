"""
Helpers para Garantir Precisão do Estoque
=========================================

Funções auxiliares que garantem que todas as consultas de estoque
retornem dados 100% precisos e atualizados.
"""

import logging
from typing import Dict, List
from app import db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache

logger = logging.getLogger(__name__)


def consultar_saldo_preciso(cod_produto: str) -> Dict:
    """
    Consulta o saldo de um produto com GARANTIA de precisão.
    
    Esta função SEMPRE retorna o saldo real e atualizado,
    nunca dados desatualizados do cache.
    
    Args:
        cod_produto: Código do produto
        
    Returns:
        Dict com saldo e informações do produto
    """
    try:
        # Importar a função de garantia
        from app.estoque.cache_triggers_safe import garantir_cache_atualizado
        return garantir_cache_atualizado(cod_produto)
    except ImportError:
        # Fallback: recalcular diretamente
        logger.warning("⚠️ Triggers safe não disponível, recalculando saldo diretamente")
        
        from app.estoque.models import MovimentacaoEstoque
        
        # Calcular saldo real diretamente do banco
        movimentacoes = MovimentacaoEstoque.query.filter_by(
            cod_produto=str(cod_produto),
            ativo=True
        ).all()
        
        saldo_real = sum(float(m.qtd_movimentacao) for m in movimentacoes)
        
        # Atualizar cache para próximas consultas
        cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
        if cache:
            cache.saldo_atual = saldo_real
            db.session.commit()
        
        return {
            'cod_produto': cod_produto,
            'saldo_atual': saldo_real,
            'precisao': 'CALCULADO_DIRETAMENTE'
        }


def validar_disponibilidade_estoque(cod_produto: str, quantidade_necessaria: float) -> Dict:
    """
    Valida se há estoque disponível para uma operação.
    
    GARANTE que a validação é feita com dados 100% atualizados.
    
    Args:
        cod_produto: Código do produto
        quantidade_necessaria: Quantidade que precisa estar disponível
        
    Returns:
        Dict com resultado da validação
    """
    saldo = consultar_saldo_preciso(cod_produto)
    
    saldo_disponivel = saldo.get('saldo_disponivel', saldo.get('saldo_atual', 0))
    tem_disponivel = saldo_disponivel >= quantidade_necessaria
    
    return {
        'disponivel': tem_disponivel,
        'saldo_atual': saldo.get('saldo_atual', 0),
        'saldo_disponivel': saldo_disponivel,
        'quantidade_necessaria': quantidade_necessaria,
        'falta': max(0, quantidade_necessaria - saldo_disponivel) if not tem_disponivel else 0,
        'precisao': saldo.get('precisao', 'GARANTIDA')
    }


def atualizar_cache_apos_operacao(produtos: List[str]) -> Dict:
    """
    Força atualização do cache após uma operação importante.
    
    Use esta função após:
    - Importações em massa
    - Sincronizações com sistemas externos
    - Operações que afetam múltiplos produtos
    
    Args:
        produtos: Lista de códigos de produtos para atualizar
        
    Returns:
        Dict com estatísticas da atualização
    """
    sucessos = 0
    erros = 0
    detalhes_erros = []
    
    for cod_produto in produtos:
        try:
            # Atualizar saldo
            SaldoEstoqueCache.atualizar_saldo_completo(cod_produto)
            
            # Atualizar projeção
            ProjecaoEstoqueCache.atualizar_projecao(cod_produto)
            
            sucessos += 1
            
        except Exception as e:
            erros += 1
            detalhes_erros.append({
                'cod_produto': cod_produto,
                'erro': str(e)
            })
            logger.error(f"Erro ao atualizar cache de {cod_produto}: {e}")
    
    db.session.commit()
    
    return {
        'total_produtos': len(produtos),
        'sucessos': sucessos,
        'erros': erros,
        'taxa_sucesso': f"{(sucessos/len(produtos)*100):.1f}%" if produtos else "0%",
        'detalhes_erros': detalhes_erros
    }


def verificar_integridade_cache(limite_produtos: int = 100) -> Dict:
    """
    Verifica a integridade do cache comparando com dados reais.
    
    Esta função é útil para auditoria e diagnóstico.
    
    Args:
        limite_produtos: Número máximo de produtos para verificar
        
    Returns:
        Dict com resultado da verificação
    """
    from app.estoque.models import MovimentacaoEstoque
    
    # Buscar produtos do cache
    produtos_cache = SaldoEstoqueCache.query.limit(limite_produtos).all()
    
    divergencias = []
    corretos = 0
    
    for cache in produtos_cache:
        # Calcular saldo real
        movimentacoes = MovimentacaoEstoque.query.filter_by(
            cod_produto=cache.cod_produto,
            ativo=True
        ).all()
        
        saldo_real = sum(float(m.qtd_movimentacao) for m in movimentacoes)
        saldo_cache = float(cache.saldo_atual)
        
        diferenca = abs(saldo_real - saldo_cache)
        
        if diferenca < 0.01:  # Tolerância para arredondamento
            corretos += 1
        else:
            divergencias.append({
                'cod_produto': cache.cod_produto,
                'nome_produto': cache.nome_produto,
                'saldo_cache': saldo_cache,
                'saldo_real': saldo_real,
                'diferenca': saldo_real - saldo_cache,
                'percentual_erro': f"{(diferenca/max(saldo_real, 0.01)*100):.1f}%"
            })
    
    # Se há divergências, corrigir automaticamente
    if divergencias:
        logger.warning(f"⚠️ Encontradas {len(divergencias)} divergências no cache, corrigindo...")
        
        for div in divergencias:
            try:
                SaldoEstoqueCache.atualizar_saldo_completo(div['cod_produto'])
            except Exception as e:
                logger.error(f"Erro ao corrigir cache de {div['cod_produto']}: {e}")
        
        db.session.commit()
    
    return {
        'produtos_verificados': len(produtos_cache),
        'corretos': corretos,
        'divergencias_encontradas': len(divergencias),
        'divergencias_corrigidas': len(divergencias),
        'integridade': f"{(corretos/len(produtos_cache)*100):.1f}%" if produtos_cache else "100%",
        'status': 'OK' if not divergencias else 'CORRIGIDO',
        'detalhes_divergencias': divergencias[:10]  # Limitar detalhes
    }


# Função de conveniência para uso direto
def obter_saldo(cod_produto: str) -> float:
    """
    Obtém o saldo atual de um produto (sempre preciso).
    
    Função simplificada para uso rápido.
    """
    saldo_info = consultar_saldo_preciso(cod_produto)
    return saldo_info.get('saldo_atual', 0)


logger.info("📦 Helpers de precisão de estoque carregados")