"""
APIs específicas para cardex D0-D28
"""

from flask import jsonify
from flask_login import login_required
# USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
from app.estoque.services.estoque_simples import ServicoEstoqueSimples as ServicoEstoqueTempoReal
from app.carteira.utils.workspace_utils import (
    converter_projecao_para_cardex,
    calcular_estatisticas_cardex,
    gerar_alertas_reais
)
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/produto/<cod_produto>/cardex')
@login_required
def cardex_produto_real(cod_produto):
    """
    API unificada para cardex D0-D28 usando SaldoEstoque
    Usado por: modal-cardex.js
    """
    try:
        # Obter projeção completa usando Sistema de Estoque em Tempo Real
        projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)

        if not projecao_completa:
            return jsonify({
                'success': False,
                'error': f'Produto {cod_produto} não encontrado ou sem movimentações'
            }), 404

        # Preparar dados do cardex com mapeamento correto de campos
        cardex_list = []
        estoque_atual = float(projecao_completa.get('estoque_atual', 0))
        maior_estoque = {'dia': 0, 'valor': estoque_atual}
        menor_estoque = {'dia': 0, 'valor': estoque_atual}
        total_producao = 0
        total_saidas = 0
        alertas = []
        
        # Log para debug
        logger.info(f"Cardex API: Processando projeção para {cod_produto}")
        logger.info(f"Estoque atual: {estoque_atual}")
        
        # Processar cada dia da projeção
        for i, dia_proj in enumerate(projecao_completa.get('projecao', [])):
            # Debug: verificar dados recebidos
            if i < 3:  # Logar apenas primeiros 3 dias
                logger.info(f"Dia {i}: {dia_proj}")
            
            # Mapear campos do backend para o frontend
            # IMPORTANTE: Garantir que valores existam, mesmo quando negativos
            estoque_inicial = float(dia_proj.get('estoque_inicial', 0))  # Usar 'estoque_inicial' do projecao
            saidas = float(dia_proj.get('saidas', 0))  # 'saidas' COM 's' no projecao
            producao = float(dia_proj.get('producao', 0))  # 'producao' direto do projecao
            
            # Calcular saldo corretamente
            if 'saldo' in dia_proj:
                saldo = float(dia_proj.get('saldo', 0))
            else:
                saldo = estoque_inicial - saidas
            
            estoque_final = float(dia_proj.get('estoque_final', 0))  # 'estoque_final' no projecao
            
            # Debug temporário para verificar o valor
            if i < 3:
                logger.info(f"   estoque_final obtido: {estoque_final} (original: {dia_proj.get('estoque_final')})")
            
            # Se os valores principais estão zerados mas temos estoque negativo, ajustar
            if i == 0 and estoque_inicial == 0 and estoque_atual < 0:
                estoque_inicial = estoque_atual
                saldo = estoque_inicial - saidas
                if estoque_final == 0:
                    estoque_final = saldo + producao
            
            # Atualizar estatísticas
            dia_num = dia_proj.get('dia', i)  # Usar índice se 'dia' não existir
            if estoque_final > maior_estoque['valor']:
                maior_estoque = {'dia': dia_num, 'valor': estoque_final}
            if estoque_final < menor_estoque['valor']:
                menor_estoque = {'dia': dia_num, 'valor': estoque_final}
            
            total_producao += producao
            total_saidas += saidas
            
            # Adicionar alertas se necessário
            if estoque_final <= 0 and len(alertas) < 5:
                alertas.append({
                    'tipo': 'danger',
                    'dia': dia_num,
                    'titulo': 'Ruptura de Estoque',
                    'descricao': f'Estoque zerado em D+{dia_num}',
                    'sugestao': 'Programar produção urgente'
                })
            elif estoque_final < 10 and len(alertas) < 5:
                alertas.append({
                    'tipo': 'warning',
                    'dia': dia_num,
                    'titulo': 'Estoque Crítico',
                    'descricao': f'Estoque muito baixo em D+{dia_num}: {estoque_final:.0f} unidades',
                    'sugestao': 'Considerar produção adicional'
                })
            
            # Adicionar ao cardex com campos esperados pelo frontend
            cardex_list.append({
                'dia': dia_num,
                'data': dia_proj.get('data'),
                'estoque_inicial': estoque_inicial,
                'saidas': saidas,  # Com 's' para o frontend
                'saldo': saldo,  # Saldo após saídas, antes da produção
                'producao': producao,  # Mapeado de 'entrada'
                'estoque_final': estoque_final
            })

        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'estoque_atual': estoque_atual,
            'maior_estoque': maior_estoque,
            'menor_estoque': menor_estoque,
            'total_producao': total_producao,  # Total calculado
            'total_saidas': total_saidas,  # Total calculado
            'cardex': cardex_list,
            'alertas': alertas
        })

    except Exception as e:
        logger.error(f"Erro ao buscar cardex do produto {cod_produto}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/produto/<cod_produto>/cardex-detalhado', methods=['GET'])
@login_required
def obter_cardex_detalhado_produto(cod_produto):
    """
    API unificada para cardex detalhado com detalhes de todas as saídas
    Usado por: modal-cardex-expandido.js
    """
    try:
        from app.separacao.models import Separacao
        from app import db
        
        # Obter projeção completa de 28 dias
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
        
        if not projecao or not isinstance(projecao, dict):
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado ou sem dados de estoque'
            }), 404
        
        # Buscar todos os pedidos com sincronizado_nf=False
        pedidos = db.session.query(
            Separacao.num_pedido,
            Separacao.expedicao,
            Separacao.qtd_saldo,
            Separacao.raz_social_red,
            Separacao.nome_cidade,
            Separacao.cod_uf,
            Separacao.separacao_lote_id,
            Separacao.status
        ).filter(
            Separacao.cod_produto == cod_produto,
            Separacao.qtd_saldo > 0,
            Separacao.sincronizado_nf == False
        ).all()
        
        # Agrupar pedidos por data
        pedidos_por_data = {}
        pedidos_sem_data = []
        
        logger.info(f"Cardex Detalhado: {len(pedidos)} pedidos encontrados para {cod_produto}")
        
        for pedido in pedidos:
            if pedido.expedicao:
                data_key = pedido.expedicao.isoformat()
                if data_key not in pedidos_por_data:
                    pedidos_por_data[data_key] = []
                
                pedidos_por_data[data_key].append({
                    'num_pedido': pedido.num_pedido,
                    'qtd': float(pedido.qtd_saldo),
                    'cliente': pedido.raz_social_red or 'Cliente não informado',
                    'cidade': pedido.nome_cidade or 'Cidade não informada',
                    'uf': pedido.cod_uf or 'UF',
                    'tem_separacao': bool(pedido.separacao_lote_id)
                })
            else:
                pedidos_sem_data.append({
                    'num_pedido': pedido.num_pedido,
                    'qtd': float(pedido.qtd_saldo),
                    'cliente': pedido.raz_social_red or 'Cliente não informado',
                    'cidade': pedido.nome_cidade or 'Cidade não informada',
                    'uf': pedido.cod_uf or 'UF',
                    'tem_separacao': bool(pedido.separacao_lote_id)
                })
        
        # Adicionar pedidos sem data em uma categoria especial
        if pedidos_sem_data:
            pedidos_por_data['sem_data'] = pedidos_sem_data
        
        # Formatar projecao_resumo com os campos corretos para o frontend
        projecao_resumo = []
        for dia in projecao.get('projecao', []):
            if isinstance(dia, dict):
                # Mapear campos para o frontend (modal-cardex-expandido.js linha 283-285)
                projecao_resumo.append({
                    'dia': dia.get('dia', 0),
                    'data': dia.get('data', ''),
                    'saldo_inicial': dia.get('saldo_inicial', 0),  # Mapeia para estoqueInicial
                    'saida': dia.get('saida', 0),  # Total de saídas do dia
                    'saldo': dia.get('saldo', 0),  # Saldo após saídas
                    'entrada': dia.get('entrada', 0),  # Mapeia para producao
                    'saldo_final': dia.get('saldo_final', 0)  # Mapeia para estoqueFinal
                })
        
        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'estoque_atual': float(projecao.get('estoque_atual', 0)),
            'projecao_resumo': projecao_resumo,
            'pedidos_por_data': pedidos_por_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter cardex detalhado do produto {cod_produto}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500