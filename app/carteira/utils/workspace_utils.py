"""
Utilitários específicos para o workspace de montagem
"""

from datetime import datetime, timedelta
from app import db
from app.carteira.models import CarteiraPrincipal
from app.estoque.models import SaldoEstoque
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


def calcular_estoque_na_data(projecao_29_dias, data_target):
    """
    Calcula estoque disponível em uma data específica
    """
    try:
        if not data_target or not projecao_29_dias:
            return 0

        # Encontrar o dia correspondente na projeção
        for dia_info in projecao_29_dias:
            if dia_info['data'] == data_target:
                return dia_info['estoque_final']

        # Se não encontrou a data exata, retornar 0
        return 0

    except Exception as e:
        logger.error(f"Erro ao calcular estoque na data {data_target}: {e}")
        return 0


def calcular_data_disponibilidade_real(projecao_29_dias, qtd_necessaria):
    """
    Calcula quando o produto estará disponível baseado na projeção real
    """
    try:
        if not projecao_29_dias:
            return datetime.now().date().isoformat()

        # Verificar cada dia da projeção
        for dia_info in projecao_29_dias:
            if dia_info['estoque_final'] >= qtd_necessaria:
                return dia_info['data'].isoformat()

        # Se não encontrou disponibilidade em 28 dias
        return 'Sem previsão'

    except Exception as e:
        logger.error(f"Erro ao calcular data disponibilidade: {e}")
        return datetime.now().date().isoformat()


def contar_clientes_programados(cod_produto):
    """
    Conta quantos clientes têm este produto programado
    """
    try:
        # Contar pedidos distintos para este produto
        count = db.session.query(
            func.count(func.distinct(CarteiraPrincipal.cnpj_cpf))
        ).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True
        ).scalar()

        return count or 0

    except Exception:
        return 0


def gerar_alertas_reais(resumo_estoque, cardex_dados):
    """
    Gera alertas baseados na análise real do estoque
    """
    alertas = []
    
    try:
        # Usar status de ruptura do SaldoEstoque
        if resumo_estoque['status_ruptura'] == 'CRÍTICO':
            # Encontrar primeiro dia com ruptura
            dias_ruptura = [i for i, dia in enumerate(cardex_dados) if dia['estoque_final'] <= 0]
            if dias_ruptura:
                primeiro_dia_ruptura = dias_ruptura[0]
                alertas.append({
                    'tipo': 'danger',
                    'dia': primeiro_dia_ruptura,
                    'titulo': 'Ruptura de Estoque Prevista',
                    'descricao': f'Estoque zerado em D+{primeiro_dia_ruptura}',
                    'sugestao': 'Antecipar produção ou reduzir compromissos de venda'
                })

        elif resumo_estoque['status_ruptura'] == 'ATENÇÃO':
            # Encontrar primeiro dia crítico
            dias_criticos = [i for i, dia in enumerate(cardex_dados) if 0 < dia['estoque_final'] <= 20]
            if dias_criticos:
                primeiro_dia_critico = dias_criticos[0]
                estoque_critico = cardex_dados[primeiro_dia_critico]['estoque_final']
                alertas.append({
                    'tipo': 'warning',
                    'dia': primeiro_dia_critico,
                    'titulo': 'Estoque Baixo',
                    'descricao': f'Estoque de apenas {estoque_critico:.0f} unidades em D+{primeiro_dia_critico}',
                    'sugestao': 'Monitorar vendas e avaliar aumento de produção'
                })

        # Verificar excesso de estoque
        estoques_altos = [i for i, dia in enumerate(cardex_dados) if dia['estoque_final'] > 1000]
        if estoques_altos:
            dia_maior_estoque = max(estoques_altos, key=lambda i: cardex_dados[i]['estoque_final'])
            maior_estoque = cardex_dados[dia_maior_estoque]['estoque_final']
            alertas.append({
                'tipo': 'info',
                'dia': dia_maior_estoque,
                'titulo': 'Alto Volume de Estoque',
                'descricao': f'Pico de {maior_estoque:.0f} unidades em D+{dia_maior_estoque}',
                'sugestao': 'Avaliar oportunidades de vendas ou ajustar produção'
            })

        return alertas

    except Exception as e:
        logger.error(f"Erro ao gerar alertas: {e}")
        return []


def processar_dados_workspace_produto(produto, resumo_estoque):
    """
    Processa dados de um produto para o workspace
    """
    try:
        if resumo_estoque:
            # Calcular estoque na data de expedição
            estoque_data_expedicao = calcular_estoque_na_data(
                resumo_estoque['projecao_29_dias'],
                produto.expedicao
            )
            
            # Calcular quando estará disponível
            data_disponibilidade = calcular_data_disponibilidade_real(
                resumo_estoque['projecao_29_dias'],
                produto.qtd_pedido
            )
        else:
            # Fallback se não conseguir calcular
            estoque_data_expedicao = float(produto.estoque_hoje or 0)
            data_disponibilidade = datetime.now().date().isoformat()

        # Contar clientes programados
        clientes_programados = contar_clientes_programados(produto.cod_produto)

        return {
            'cod_produto': produto.cod_produto,
            'nome_produto': produto.nome_produto or '',
            'qtd_pedido': float(produto.qtd_pedido or 0),
            'estoque_hoje': float(resumo_estoque['estoque_inicial'] if resumo_estoque else produto.estoque_hoje or 0),
            'menor_estoque_7d': float(resumo_estoque['previsao_ruptura'] if resumo_estoque else 0),
            'estoque_data_expedicao': float(estoque_data_expedicao),
            'data_disponibilidade': data_disponibilidade,
            'producao_data_expedicao': 0,  # Será calculado no cardex
            'preco_unitario': float(produto.preco_unitario or 0),
            'peso_unitario': float(produto.peso_unitario or 0),
            'palletizacao': float(produto.palletizacao or 1),
            'clientes_programados_count': clientes_programados
        }

    except Exception as e:
        logger.error(f"Erro ao processar dados do produto {produto.cod_produto}: {e}")
        return None


def converter_projecao_para_cardex(resumo_estoque):
    """
    Converte projeção do SaldoEstoque para formato do cardex
    """
    try:
        cardex_dados = []
        for dia_info in resumo_estoque['projecao_29_dias']:
            cardex_dados.append({
                'data': dia_info['data'].isoformat(),
                'estoque_inicial': float(dia_info['estoque_inicial']),
                'saidas': float(dia_info['saida_prevista']),
                'saldo': float(dia_info['estoque_inicial'] - dia_info['saida_prevista']),
                'producao': float(dia_info['producao_programada']),
                'estoque_final': float(dia_info['estoque_final'])
            })

        return cardex_dados

    except Exception as e:
        logger.error(f"Erro ao converter projeção para cardex: {e}")
        return []


def calcular_estatisticas_cardex(cardex_dados):
    """
    Calcula estatísticas do cardex
    """
    try:
        if not cardex_dados:
            return {}

        # Calcular estatísticas
        estoques_finais = [dia['estoque_final'] for dia in cardex_dados]
        menor_estoque = min(estoques_finais)
        maior_estoque = max(estoques_finais)
        total_producao = sum(dia['producao'] for dia in cardex_dados)
        total_saidas = sum(dia['saidas'] for dia in cardex_dados)

        # Identificar dias críticos
        menor_estoque_dia = estoques_finais.index(menor_estoque)
        maior_estoque_dia = estoques_finais.index(maior_estoque)

        return {
            'menor_estoque': {
                'valor': menor_estoque,
                'dia': menor_estoque_dia
            },
            'maior_estoque': {
                'valor': maior_estoque,
                'dia': maior_estoque_dia
            },
            'total_producao': total_producao,
            'total_saidas': total_saidas
        }

    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas do cardex: {e}")
        return {}