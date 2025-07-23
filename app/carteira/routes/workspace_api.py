"""
APIs reais para o workspace de montagem de carga
"""

from flask import jsonify, request
from flask_login import login_required
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.estoque.models import SaldoEstoque
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.utils.data_brasil import agora_brasil
from app.carteira.utils.separacao_utils import (
    determinar_tipo_envio, 
    calcular_peso_pallet_produto, 
    buscar_rota_por_uf, 
    buscar_sub_rota_por_uf_cidade
)
from app.carteira.utils.workspace_utils import (
    processar_dados_workspace_produto
)
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/workspace')
@login_required
def workspace_pedido_real(num_pedido):
    """
    API real para dados do workspace de montagem
    Retorna produtos do pedido com dados completos de estoque
    """
    try:
        # Buscar produtos do pedido na carteira
        produtos_carteira = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido.label('qtd_pedido'),
            CarteiraPrincipal.preco_produto_pedido.label('preco_unitario'),
            CarteiraPrincipal.expedicao,
            # Dados de palletização
            CadastroPalletizacao.peso_bruto.label('peso_unitario'),
            CadastroPalletizacao.palletizacao,
            # Dados básicos (estoque será calculado via SaldoEstoque)
            CarteiraPrincipal.estoque.label('estoque_hoje')
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()

        if not produtos_carteira:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado ou sem itens ativos'
            }), 404

        # Processar produtos e calcular dados complementares
        produtos_processados = []
        valor_total = 0

        for produto in produtos_carteira:
            # Obter resumo completo do produto usando SaldoEstoque
            resumo_estoque = SaldoEstoque.obter_resumo_produto(
                produto.cod_produto, 
                produto.nome_produto
            )

            # Processar dados do produto usando função utilitária
            produto_data = processar_dados_workspace_produto(produto, resumo_estoque)
            
            if produto_data:
                produtos_processados.append(produto_data)
                valor_total += produto_data['qtd_pedido'] * produto_data['preco_unitario']

        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'valor_total': valor_total,
            'produtos': produtos_processados,
            'total_produtos': len(produtos_processados)
        })

    except Exception as e:
        logger.error(f"Erro ao buscar workspace do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500




@carteira_bp.route('/api/workspace/gerar-separacao', methods=['POST'])
@login_required
def gerar_separacao_workspace():
    """
    API para gerar separação a partir dos lotes criados no workspace
    
    Payload esperado:
    {
        "num_pedido": "PED001",
        "lotes": [
            {
                "lote_id": "LOTE-20250123-001-143025",
                "produtos": [
                    {
                        "cod_produto": "PROD001",
                        "quantidade": 100
                    }
                ],
                "expedicao": "2025-01-25",
                "agendamento": "2025-01-26",
                "protocolo": "PROT123"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        num_pedido = data.get('num_pedido')
        lotes = data.get('lotes', [])
        
        if not num_pedido:
            return jsonify({
                'success': False,
                'error': 'Número do pedido é obrigatório'
            }), 400
            
        if not lotes:
            return jsonify({
                'success': False,
                'error': 'Nenhum lote fornecido para separação'
            }), 400

        # Validar que todos os lotes têm data de expedição
        for lote in lotes:
            if not lote.get('expedicao'):
                return jsonify({
                    'success': False,
                    'error': 'Todos os lotes devem ter Data de Expedição preenchida'
                }), 400

        separacoes_criadas = []
        lotes_processados = []

        # Processar cada lote
        for lote in lotes:
            lote_id = lote.get('lote_id')
            produtos_lote = lote.get('produtos', [])
            expedicao = lote.get('expedicao')
            agendamento = lote.get('agendamento')
            protocolo = lote.get('protocolo')

            if not produtos_lote:
                continue

            # Buscar informações dos produtos na carteira
            produtos_carteira = {}
            for produto in produtos_lote:
                cod_produto = produto.get('cod_produto')
                item_carteira = db.session.query(CarteiraPrincipal).filter(
                    CarteiraPrincipal.num_pedido == num_pedido,
                    CarteiraPrincipal.cod_produto == cod_produto,
                    CarteiraPrincipal.ativo == True
                ).first()
                
                if item_carteira:
                    produtos_carteira[cod_produto] = item_carteira

            # Determinar tipo de envio (total ou parcial)
            tipo_envio = determinar_tipo_envio(num_pedido, produtos_lote, produtos_carteira)

            # Converter datas
            try:
                expedicao_obj = datetime.strptime(expedicao, '%Y-%m-%d').date() if expedicao else None
            except ValueError:
                expedicao_obj = None
                
            try:
                agendamento_obj = datetime.strptime(agendamento, '%Y-%m-%d').date() if agendamento else None
            except ValueError:
                agendamento_obj = None

            # Criar separações para cada produto do lote
            separacoes_lote = []
            for produto in produtos_lote:
                cod_produto = produto.get('cod_produto')
                quantidade = float(produto.get('quantidade', 0))
                
                if quantidade <= 0:
                    continue
                    
                item_carteira = produtos_carteira.get(cod_produto)
                if not item_carteira:
                    continue

                # Calcular valores proporcionais
                preco_unitario = float(item_carteira.preco_produto_pedido or 0)
                valor_separacao = quantidade * preco_unitario
                
                # Calcular peso e pallet
                peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade)
                
                # Buscar rota e sub-rota
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')
                sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                    item_carteira.cod_uf or '', 
                    item_carteira.nome_cidade or ''
                )

                # Criar separação
                separacao = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido,
                    data_pedido=item_carteira.data_pedido,
                    cnpj_cpf=item_carteira.cnpj_cpf,
                    raz_social_red=item_carteira.raz_social_red,
                    nome_cidade=item_carteira.nome_cidade,
                    cod_uf=item_carteira.cod_uf,
                    cod_produto=cod_produto,
                    nome_produto=item_carteira.nome_produto,
                    qtd_saldo=quantidade,
                    valor_saldo=valor_separacao,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    rota=rota_calculada,
                    sub_rota=sub_rota_calculada,
                    observ_ped_1=item_carteira.observ_ped_1,
                    roteirizacao=None,
                    expedicao=expedicao_obj,
                    agendamento=agendamento_obj,
                    protocolo=protocolo,
                    tipo_envio=tipo_envio,
                    criado_em=agora_brasil()
                )
                
                db.session.add(separacao)
                separacoes_lote.append(separacao)
                separacoes_criadas.append(separacao)

            if separacoes_lote:
                # Calcular totais do lote
                total_valor = sum(s.valor_saldo for s in separacoes_lote)
                total_peso = sum(s.peso for s in separacoes_lote)
                total_pallet = sum(s.pallet for s in separacoes_lote)
                
                lotes_processados.append({
                    'lote_id': lote_id,
                    'tipo_envio': tipo_envio,
                    'total_produtos': len(separacoes_lote),
                    'total_valor': total_valor,
                    'total_peso': total_peso,
                    'total_pallet': total_pallet,
                    'expedicao': expedicao,
                    'agendamento': agendamento,
                    'protocolo': protocolo
                })

        if not separacoes_criadas:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação foi criada. Verifique os produtos informados.'
            }), 400

        # Atualizar pedido na tabela pedidos
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        if pedido:
            # Usar o lote_id do primeiro lote processado
            if lotes_processados:
                pedido.separacao_lote_id = lotes_processados[0]['lote_id']
                pedido.expedicao = datetime.strptime(lotes_processados[0]['expedicao'], '%Y-%m-%d').date()
                if lotes_processados[0]['agendamento']:
                    pedido.agendamento = datetime.strptime(lotes_processados[0]['agendamento'], '%Y-%m-%d').date()
                pedido.protocolo = lotes_processados[0]['protocolo']

        # Commit das mudanças
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Separação gerada com sucesso! {len(separacoes_criadas)} itens criados em {len(lotes_processados)} lote(s).',
            'separacoes_criadas': len(separacoes_criadas),
            'lotes_processados': lotes_processados
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separação do workspace: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


# Função movida para app.carteira.utils.separacao_utils