"""
API para gerar separação de pedidos completos na carteira agrupada
"""

from flask import jsonify, request
from flask_login import login_required
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.utils.data_brasil import agora_brasil
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
    gerar_novo_lote_id
)
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/gerar-separacao-completa', methods=['POST'])
@login_required
def gerar_separacao_completa_pedido(num_pedido):
    """
    API para gerar separação de TODOS os produtos do pedido
    
    Usado pelo botão "Gerar Separação" na carteira agrupada
    Aplica mesma data de expedição, agendamento e protocolo para todos os produtos
    
    Payload esperado:
    {
        "expedicao": "2025-01-25",
        "agendamento": "2025-01-26", // opcional
        "protocolo": "PROT123" // opcional
    }
    """
    try:
        data = request.get_json()
        expedicao = data.get('expedicao')
        agendamento = data.get('agendamento')
        protocolo = data.get('protocolo')

        if not expedicao:
            return jsonify({
                'success': False,
                'error': 'Data de expedição é obrigatória'
            }), 400

        # Buscar todos os produtos do pedido
        produtos_pedido = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()

        if not produtos_pedido:
            return jsonify({
                'success': False,
                'error': f'Nenhum produto encontrado para o pedido {num_pedido}'
            }), 404

        # Converter datas
        try:
            expedicao_obj = datetime.strptime(expedicao, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de data de expedição inválido'
            }), 400

        agendamento_obj = None
        if agendamento:
            try:
                agendamento_obj = datetime.strptime(agendamento, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Gerar ID único para o lote
        lote_id = gerar_novo_lote_id()

        # Criar separações para todos os produtos
        separacoes_criadas = []
        valor_total_separacao = 0
        peso_total_separacao = 0
        pallet_total_separacao = 0

        # Tipo de envio é sempre 'total' pois está separando todos os produtos
        tipo_envio = 'total'

        for item in produtos_pedido:
            quantidade = float(item.qtd_saldo_produto_pedido or 0)
            
            if quantidade <= 0:
                continue

            # Calcular valores proporcionais
            preco_unitario = float(item.preco_produto_pedido or 0)
            valor_separacao = quantidade * preco_unitario
            
            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(item.cod_produto, quantidade)
            
            # Buscar rota e sub-rota
            rota_calculada = buscar_rota_por_uf(item.cod_uf or 'SP')
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item.cod_uf or '', 
                item.nome_cidade or ''
            )

            # Criar separação
            separacao = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                data_pedido=item.data_pedido,
                cnpj_cpf=item.cnpj_cpf,
                raz_social_red=item.raz_social_red,
                nome_cidade=item.nome_cidade,
                cod_uf=item.cod_uf,
                cod_produto=item.cod_produto,
                nome_produto=item.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=item.observ_ped_1,
                roteirizacao=None,
                expedicao=expedicao_obj,
                agendamento=agendamento_obj,
                protocolo=protocolo,
                tipo_envio=tipo_envio,
                criado_em=agora_brasil()
            )
            
            db.session.add(separacao)
            separacoes_criadas.append(separacao)
            
            # Acumular totais
            valor_total_separacao += valor_separacao
            peso_total_separacao += peso_calculado
            pallet_total_separacao += pallet_calculado

        if not separacoes_criadas:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação foi criada. Verifique se há produtos com quantidade válida.'
            }), 400

        # Atualizar pedido na tabela pedidos
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        if pedido:
            pedido.separacao_lote_id = lote_id
            pedido.expedicao = expedicao_obj
            pedido.agendamento = agendamento_obj
            pedido.protocolo = protocolo

        # Commit das mudanças
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Separação completa gerada com sucesso! {len(separacoes_criadas)} produtos separados.',
            'lote_id': lote_id,
            'tipo_envio': tipo_envio,
            'separacoes_criadas': len(separacoes_criadas),
            'totais': {
                'valor': valor_total_separacao,
                'peso': peso_total_separacao,
                'pallet': pallet_total_separacao
            },
            'datas': {
                'expedicao': expedicao,
                'agendamento': agendamento,
                'protocolo': protocolo
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separação completa do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500