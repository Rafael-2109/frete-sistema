"""
Utilitários específicos para o workspace de montagem
"""

from app.utils.timezone import agora_brasil
from app import db
from app.carteira.models import CarteiraPrincipal
# NOTA: SaldoEstoque mantido apenas para compatibilidade de fallback
# O sistema principal usa ServicoProjecaoEstoque (híbrido)
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
            # Comparar datas considerando diferentes formatos
            dia_data = dia_info.get('data')
            if dia_data:
                # Converter para string se necessário
                if hasattr(dia_data, 'isoformat'):
                    dia_data = dia_data.isoformat()
                if hasattr(data_target, 'isoformat'):
                    data_target_str = data_target.isoformat()
                else:
                    data_target_str = str(data_target)
                    
                if str(dia_data) == data_target_str:
                    # Compatibilidade com novo formato (saldo_final) e antigo (estoque_final)
                    return float(dia_info.get('saldo_final', dia_info.get('estoque_final', 0)))

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
            return agora_brasil().date().isoformat()

        # Verificar cada dia da projeção
        for dia_info in projecao_29_dias:
            # Compatibilidade com novo formato (saldo_final) e antigo (estoque_final)
            estoque_final = dia_info.get('saldo_final', dia_info.get('estoque_final', 0))
            if estoque_final >= qtd_necessaria:
                dia_data = dia_info.get('data')
                if hasattr(dia_data, 'isoformat'):
                    return dia_data.isoformat()
                else:
                    return str(dia_data)

        # Se não encontrou disponibilidade em 28 dias
        return 'Sem previsão'

    except Exception as e:
        logger.error(f"Erro ao calcular data disponibilidade: {e}")
        return agora_brasil().date().isoformat()


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


def obter_producao_hoje(cod_produto, resumo_estoque):
    """
    Obtém quantidade programada para produzir hoje
    """
    try:
        if resumo_estoque:
            # Verificar se tem projecao_29_dias ou projecao
            projecao = resumo_estoque.get('projecao_29_dias') or resumo_estoque.get('projecao', [])
            # Verificar se há dados na projeção
            if projecao and len(projecao) > 0:
                # Primeiro dia da projeção é D0 (hoje)
                hoje_dados = projecao[0]
                # O campo pode ser producao_programada ou entrada
                return float(hoje_dados.get('producao_programada', hoje_dados.get('entrada', 0)))
            else:
                return 0
        
        # Fallback: calcular diretamente do SaldoEstoque
        hoje = agora_brasil().date()
        producao = SaldoEstoque.calcular_producao_periodo(cod_produto, hoje, hoje)
        return float(producao)
        
    except Exception as e:
        logger.error(f"Erro ao obter produção hoje para {cod_produto}: {e}")
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
        estoques_altos = [i for i, dia in enumerate(cardex_dados) if dia['estoque_final'] > 5000]
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


def calcular_disponibilidade_para_pedido(projecao, qtd_pedido):
    """
    Calcula quando o produto terá saldo suficiente para atender o pedido.
    SALDO = Est. Inicial - Saída (antes de somar a Produção/Entrada)
    Retorna a data e quantidade quando o SALDO for maior que a quantidade do pedido.
    """
    try:
        if not projecao or not qtd_pedido:
            return None, None
        
        for dia_info in projecao:
            # Calcular SALDO = Est. Inicial - Saída
            # No cardex: Est.Inicial -> Saída -> SALDO -> Produção -> Est.Final
            est_inicial = dia_info.get('saldo_inicial', 0)  # Est. Inicial do dia
            saida = dia_info.get('saida', 0)  # Saída do dia
            
            # SALDO = Est. Inicial - Saída (antes de somar a entrada/produção)
            saldo = est_inicial - saida
            
            # Verificar se o saldo é maior que a quantidade do pedido
            if saldo > qtd_pedido:
                data = dia_info.get('data')
                return data, saldo
        
        return None, None
    except Exception as e:
        logger.error(f"Erro ao calcular disponibilidade para pedido: {e}")
        return None, None

def processar_dados_workspace_produto(produto, resumo_estoque):
    """
    Processa dados de um produto para o workspace
    Aceita tanto resultado de query com alias quanto objeto CarteiraPrincipal
    """
    try:
        # Determinar o campo correto para quantidade
        # Se tem qtd_pedido (alias da query), usa ele
        # Senão, usa qtd_saldo_produto_pedido (campo real do CarteiraPrincipal)
        qtd_pedido = getattr(produto, 'qtd_pedido', None)
        if qtd_pedido is None:
            qtd_pedido = getattr(produto, 'qtd_saldo_produto_pedido', 0)
        qtd_pedido = float(qtd_pedido or 0)
        
        # Determinar estoque_hoje (pode vir como alias ou campo real)
        estoque_hoje = getattr(produto, 'estoque_hoje', None)
        if estoque_hoje is None:
            estoque_hoje = getattr(produto, 'estoque', 0)
        
        if resumo_estoque:
            # Verificar se tem projecao_29_dias ou projecao
            projecao = resumo_estoque.get('projecao_29_dias') or resumo_estoque.get('projecao', [])
            
            # Calcular estoque na data de expedição
            estoque_data_expedicao = calcular_estoque_na_data(
                projecao,
                produto.expedicao
            )
            
            # Calcular quando estará disponível com saldo maior que o pedido
            data_disponibilidade, qtd_disponivel = calcular_disponibilidade_para_pedido(
                projecao,
                qtd_pedido
            )
            
            # Se não encontrou, usar lógica antiga como fallback
            if not data_disponibilidade:
                data_disponibilidade = calcular_data_disponibilidade_real(
                    projecao,
                    qtd_pedido
                )
                qtd_disponivel = resumo_estoque.get('qtd_disponivel', 0)
        else:
            # Fallback se não conseguir calcular
            estoque_data_expedicao = float(estoque_hoje or 0)
            data_disponibilidade = agora_brasil().date().isoformat()
            qtd_disponivel = 0

        # Contar clientes programados
        clientes_programados = contar_clientes_programados(produto.cod_produto)
        
        # Obter produção de hoje
        producao_hoje = obter_producao_hoje(produto.cod_produto, resumo_estoque)

        return {
            'cod_produto': produto.cod_produto,
            'nome_produto': produto.nome_produto or '',
            'qtd_pedido': qtd_pedido,
            'estoque_hoje': float(resumo_estoque.get('estoque_atual', resumo_estoque.get('estoque_inicial', 0)) if resumo_estoque else estoque_hoje or 0),
            'menor_estoque_7d': float(resumo_estoque.get('menor_estoque_d7', resumo_estoque.get('menor_estoque_7d', 0)) if resumo_estoque else 0),
            'estoque_data_expedicao': float(estoque_data_expedicao),
            'data_disponibilidade': data_disponibilidade,
            'qtd_disponivel': float(qtd_disponivel) if qtd_disponivel else 0,
            'producao_hoje': float(producao_hoje),
            'producao_data_expedicao': 0,  # Será calculado no cardex
            'preco_unitario': float(getattr(produto, 'preco_unitario', getattr(produto, 'preco_produto_pedido', 0)) or 0),
            'peso_unitario': float(getattr(produto, 'peso_unitario', getattr(produto, 'peso_bruto', 0)) or 0),
            'palletizacao': float(getattr(produto, 'palletizacao', 1) or 1),
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
        
        # Verificar se há projeção disponível
        if not resumo_estoque:
            return []
            
        # Verificar se tem projecao_29_dias ou projecao
        projecao = resumo_estoque.get('projecao_29_dias') or resumo_estoque.get('projecao', [])
        if not projecao:
            return []
            
        for dia_info in projecao:
            # Verificar se dia_info tem estrutura esperada
            if isinstance(dia_info, dict):
                # Compatibilidade com novo formato (saldo_inicial, entrada, saida, saldo_final)
                # e formato antigo (estoque_inicial, saida_prevista, producao_programada, estoque_final)
                estoque_inicial = float(dia_info.get('saldo_inicial', dia_info.get('estoque_inicial', 0)))
                saidas = float(dia_info.get('saida', dia_info.get('saida_prevista', 0)))
                producao = float(dia_info.get('entrada', dia_info.get('producao_programada', 0)))
                estoque_final = float(dia_info.get('saldo_final', dia_info.get('estoque_final', 0)))
                
                cardex_dados.append({
                    'data': dia_info.get('data', '').isoformat() if hasattr(dia_info.get('data'), 'isoformat') else str(dia_info.get('data', '')),
                    'estoque_inicial': estoque_inicial,
                    'saidas': saidas,
                    'saldo': estoque_inicial - saidas,
                    'producao': producao,
                    'estoque_final': estoque_final
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