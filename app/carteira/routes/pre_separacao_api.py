"""
APIs para gerenciamento de pré-separações
Sistema de persistência para drag & drop do workspace
"""

from flask import jsonify, request, current_app
from flask_login import login_required
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.utils.timezone import agora_brasil
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    gerar_separacao_workspace_interno,
    gerar_novo_lote_id
)
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pre-separacao/salvar', methods=['POST'])
@login_required
def salvar_pre_separacao():
    """
    API para salvar pré-separação no drag & drop
    Cada drag & drop cria/atualiza um PreSeparacaoItem
    """
    try:
        data = request.get_json()
        num_pedido = data.get('num_pedido')
        cod_produto = data.get('cod_produto')
        separacao_lote_id = data.get('lote_id')  # Pode vir como 'lote_id' do frontend
        qtd_selecionada = data.get('qtd_selecionada_usuario')
        data_expedicao = data.get('data_expedicao_editada')

        # Se não foi fornecido separacao_lote_id, gerar um novo
        if not separacao_lote_id:
            separacao_lote_id = gerar_novo_lote_id()

        if not all([num_pedido, cod_produto, qtd_selecionada, data_expedicao]):
            return jsonify({
                'success': False,
                'error': 'Dados obrigatórios: num_pedido, cod_produto, qtd_selecionada_usuario, data_expedicao_editada'
            }), 400

        # Buscar item da carteira para dados base
        item_carteira = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True
        ).first()

        if not item_carteira:
            return jsonify({
                'success': False,
                'error': f'Item não encontrado: {num_pedido} - {cod_produto}'
            }), 404

        # Converter data
        try:
            data_expedicao_obj = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de data inválido'
            }), 400

        # Verificar se já existe pré-separação para este produto no mesmo lote
        pre_separacao_existente = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.cod_produto == cod_produto,
            PreSeparacaoItem.separacao_lote_id == separacao_lote_id,  # Verificar pelo lote específico
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).first()

        if pre_separacao_existente:
            # Somar quantidade à existente
            nova_quantidade = float(pre_separacao_existente.qtd_selecionada_usuario) + float(qtd_selecionada)
            
            # Verificar se não excede o saldo disponível
            if nova_quantidade > float(item_carteira.qtd_saldo_produto_pedido):
                return jsonify({
                    'success': False,
                    'error': f'Quantidade total ({nova_quantidade}) excede o saldo disponível ({item_carteira.qtd_saldo_produto_pedido})'
                }), 400
            
            # Atualizar quantidade existente (somar)
            pre_separacao_existente.qtd_selecionada_usuario = nova_quantidade
            pre_separacao_existente.qtd_restante_calculada = (
                float(item_carteira.qtd_saldo_produto_pedido) - nova_quantidade
            )
            # Recalcular valor total
            pre_separacao_existente.valor_original_item = float(item_carteira.preco_produto_pedido or 0) * nova_quantidade
            pre_separacao = pre_separacao_existente
            acao = 'atualizada (quantidade somada)'
        else:
            # Criar nova pré-separação
            pre_separacao = PreSeparacaoItem(
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                cnpj_cliente=item_carteira.cnpj_cpf,
                nome_produto=item_carteira.nome_produto,
                qtd_original_carteira=float(item_carteira.qtd_saldo_produto_pedido),
                qtd_selecionada_usuario=float(qtd_selecionada),
                qtd_restante_calculada=float(item_carteira.qtd_saldo_produto_pedido) - float(qtd_selecionada),
                valor_original_item=float(item_carteira.preco_produto_pedido or 0) * float(qtd_selecionada),
                data_expedicao_editada=data_expedicao_obj,
                data_agendamento_editada=None,
                protocolo_editado=data.get('protocolo_editado'),
                observacoes_usuario=data.get('observacoes_usuario'),
                separacao_lote_id=separacao_lote_id,  # Adicionar o lote_id
                status='CRIADO',
                tipo_envio='parcial' if float(qtd_selecionada) < float(item_carteira.qtd_saldo_produto_pedido) else 'total',
                data_criacao=agora_brasil(),
                criado_por='workspace_drag_drop'
            )
            db.session.add(pre_separacao)
            acao = 'criada'

        db.session.commit()

        # Calcular peso e pallet para resposta usando a quantidade total final
        quantidade_final = float(pre_separacao.qtd_selecionada_usuario)
        peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade_final)

        return jsonify({
            'success': True,
            'message': f'Pré-separação {acao} com sucesso',
            'pre_separacao_id': pre_separacao.id,
            'lote_id': separacao_lote_id,
            'dados': {
                'cod_produto': cod_produto,
                'quantidade': quantidade_final,
                'valor': float(pre_separacao.valor_original_item or 0),
                'peso': peso_calculado,
                'pallet': pallet_calculado,
                'status': 'CRIADO',
                'tipo': 'pre_separacao'
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar pré-separação: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/pre-separacoes')
@login_required
def listar_pre_separacoes(num_pedido):
    """
    API para listar pré-separações existentes de um pedido
    Usado para carregar o workspace com dados já salvos
    """
    try:
        pre_separacoes = db.session.query(PreSeparacaoItem).filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()

        # Agrupar por separacao_lote_id
        lotes = {}
        for pre_sep in pre_separacoes:
            lote_key = pre_sep.separacao_lote_id
            
            if lote_key not in lotes:
                lotes[lote_key] = {
                    'lote_id': lote_key,
                    'data_expedicao': pre_sep.data_expedicao_editada.isoformat() if pre_sep.data_expedicao_editada else None,
                    'status': 'pre_separacao',
                    'produtos': [],
                    'totais': {'valor': 0, 'peso': 0, 'pallet': 0}
                }

            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(
                pre_sep.cod_produto, 
                float(pre_sep.qtd_selecionada_usuario)
            )

            produto_data = {
                'pre_separacao_id': pre_sep.id,
                'cod_produto': pre_sep.cod_produto,
                'nome_produto': pre_sep.nome_produto,
                'quantidade': float(pre_sep.qtd_selecionada_usuario),
                'valor': float(pre_sep.valor_original_item or 0),
                'peso': peso_calculado,
                'pallet': pallet_calculado
            }

            lotes[lote_key]['produtos'].append(produto_data)
            lotes[lote_key]['totais']['valor'] += produto_data['valor']
            lotes[lote_key]['totais']['peso'] += produto_data['peso']
            lotes[lote_key]['totais']['pallet'] += produto_data['pallet']

        return jsonify({
            'success': True,
            'num_pedido': num_pedido,
            'lotes': list(lotes.values()),
            'total_lotes': len(lotes)
        })

    except Exception as e:
        logger.error(f"Erro ao listar pré-separações do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pre-separacao/<int:pre_separacao_id>/remover', methods=['DELETE'])
@login_required
def remover_pre_separacao(pre_separacao_id):
    """
    API para remover pré-separação (quando remove produto do lote)
    """
    try:
        pre_separacao = PreSeparacaoItem.query.get(pre_separacao_id)
        
        if not pre_separacao:
            return jsonify({
                'success': False,
                'error': 'Pré-separação não encontrada'
            }), 404

        # Dados para resposta antes de deletar
        dados_removidos = {
            'cod_produto': pre_separacao.cod_produto,
            'quantidade': float(pre_separacao.qtd_selecionada_usuario),
            'valor': float(pre_separacao.valor_original_item or 0)
        }

        db.session.delete(pre_separacao)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pré-separação removida com sucesso',
            'dados_removidos': dados_removidos
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao remover pré-separação {pre_separacao_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pre-separacao/<lote_id>/atualizar-datas', methods=['POST'])
@login_required
def atualizar_datas_pre_separacao(lote_id):
    """
    Atualiza datas de expedição, agendamento e protocolo de uma pré-separação
    """
    try:
        data = request.get_json()
        data_expedicao = data.get('expedicao')
        data_agendamento = data.get('agendamento')
        protocolo = data.get('protocolo')
        
        if not data_expedicao:
            return jsonify({
                'success': False,
                'error': 'Data de expedição é obrigatória'
            }), 400
            
        # Buscar todas as pré-separações do lote
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'success': False,
                'error': 'Pré-separação não encontrada ou já processada'
            }), 404
            
        # Converter datas
        from datetime import datetime
        data_expedicao_obj = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        data_agendamento_obj = None
        if data_agendamento:
            data_agendamento_obj = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
            
        # Atualizar todas as pré-separações do lote
        for pre_sep in pre_separacoes:
            pre_sep.data_expedicao_editada = data_expedicao_obj
            pre_sep.data_agendamento_editada = data_agendamento_obj
            pre_sep.protocolo_editado = protocolo
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(pre_separacoes)} itens atualizados com sucesso',
            'itens_atualizados': len(pre_separacoes)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar datas da pré-separação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🗑️ ROTA REMOVIDA - REDUNDANTE
# Funcionalidade movida para /api/lote/<lote_id>/transformar-separacao em separacao_api.py
# Esta rota estava duplicando a lógica de transformação de pré-separação em separação
# Agora toda transformação de pré-separação é feita via separacao-manager.js → Caso 2