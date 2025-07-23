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
from app.utils.timezone import agora_brasil
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
    gerar_novo_lote_id
)
import logging

from . import carteira_bp
from app.carteira.models import PreSeparacaoItem

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/verificar-lote', methods=['GET'])
@login_required
def verificar_lote_pedido(num_pedido):
    """
    API para verificar se existe pré-separação para o pedido
    
    Retorna:
    {
        "lote_completo_com_expedicao": true/false,
        "lote_parcial_existe": true/false,
        "lote_id": "LOTE-ID" (se existir lote completo)
    }
    """
    try:
        # Buscar pré-separações do pedido
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'lote_completo_com_expedicao': False,
                'lote_parcial_existe': False,
                'lote_id': None
            })
        
        # Agrupar por lote_id e verificar tipo_envio
        lotes_info = {}
        for item in pre_separacoes:
            lote_id = getattr(item, 'lote_id', None) or 'sem_lote'
            if lote_id not in lotes_info:
                lotes_info[lote_id] = {
                    'tipo_envio': getattr(item, 'tipo_envio', 'total'),
                    'data_expedicao': getattr(item, 'data_expedicao_editada', None),
                    'itens': []
                }
            lotes_info[lote_id]['itens'].append(item)
        
        # Verificar se existe lote completo com expedição
        for lote_id, info in lotes_info.items():
            if (info['tipo_envio'] == 'total' and 
                info['data_expedicao'] is not None):
                return jsonify({
                    'lote_completo_com_expedicao': True,
                    'lote_parcial_existe': False,
                    'lote_id': lote_id
                })
        
        # Verificar se existe lote parcial
        tem_parcial = any(info['tipo_envio'] == 'parcial' for info in lotes_info.values())
        
        return jsonify({
            'lote_completo_com_expedicao': False,
            'lote_parcial_existe': tem_parcial,
            'lote_id': None
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar lote do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


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


@carteira_bp.route('/api/lote/<lote_id>/transformar-separacao', methods=['POST'])
@login_required
def transformar_lote_em_separacao(lote_id):
    """
    API para transformar pré-separação em separação definitiva
    Usado pelo botão "Transformar em Separação" no workspace
    """
    try:
        # Verificar se é um lote de pré-separação (formato: PRE-YYYY-MM-DD)
        if lote_id.startswith('PRE-'):
            # Extrair data de expedição do lote_id
            data_expedicao_str = lote_id.replace('PRE-', '')
            try:
                data_expedicao_obj = datetime.strptime(data_expedicao_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de lote inválido'
                }), 400

            # Buscar pré-separações do lote
            pre_separacoes = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.data_expedicao_editada == data_expedicao_obj,
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
            ).all()

            if not pre_separacoes:
                return jsonify({
                    'success': False,
                    'error': 'Nenhuma pré-separação encontrada para este lote'
                }), 404

            # Verificar se é lote completo (todos os produtos do pedido)
            num_pedido = pre_separacoes[0].num_pedido
            
            # Buscar produtos totais do pedido
            produtos_totais = db.session.query(CarteiraPrincipal).filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.ativo == True
            ).all()

            # Verificar se tipo_envio é 'total' para pelo menos uma pré-separação
            tem_envio_total = any(ps.tipo_envio == 'total' for ps in pre_separacoes)
            
            if not tem_envio_total:
                return jsonify({
                    'success': False,
                    'error': 'Este lote contém apenas envios parciais. Use o botão "Criar Separação Completa" para produtos completos.'
                }), 400

            # Gerar novo lote_id para separação
            novo_lote_id = gerar_novo_lote_id()

            # Criar separações
            separacoes_criadas = []
            valor_total = 0
            peso_total = 0
            pallet_total = 0

            for pre_sep in pre_separacoes:
                quantidade = float(pre_sep.qtd_selecionada_usuario)
                
                # Buscar dados completos do item na carteira
                item_carteira = db.session.query(CarteiraPrincipal).filter(
                    CarteiraPrincipal.num_pedido == pre_sep.num_pedido,
                    CarteiraPrincipal.cod_produto == pre_sep.cod_produto,
                    CarteiraPrincipal.ativo == True
                ).first()

                if not item_carteira:
                    continue

                # Calcular valores
                preco_unitario = float(item_carteira.preco_produto_pedido or 0)
                valor_separacao = quantidade * preco_unitario
                
                # Calcular peso e pallet
                peso_calculado, pallet_calculado = calcular_peso_pallet_produto(
                    pre_sep.cod_produto, quantidade
                )
                
                # Buscar rota e sub-rota
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')
                sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                    item_carteira.cod_uf or '', 
                    item_carteira.nome_cidade or ''
                )

                # Criar separação
                separacao = Separacao(
                    separacao_lote_id=novo_lote_id,
                    num_pedido=pre_sep.num_pedido,
                    data_pedido=item_carteira.data_pedido,
                    cnpj_cpf=item_carteira.cnpj_cpf,
                    raz_social_red=item_carteira.raz_social_red,
                    nome_cidade=item_carteira.nome_cidade,
                    cod_uf=item_carteira.cod_uf,
                    cod_produto=pre_sep.cod_produto,
                    nome_produto=pre_sep.nome_produto,
                    qtd_saldo=quantidade,
                    valor_saldo=valor_separacao,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    rota=rota_calculada,
                    sub_rota=sub_rota_calculada,
                    observ_ped_1=item_carteira.observ_ped_1,
                    roteirizacao=None,
                    expedicao=pre_sep.data_expedicao_editada,
                    agendamento=pre_sep.data_agendamento_editada,
                    protocolo=pre_sep.protocolo_editado,
                    tipo_envio=pre_sep.tipo_envio,
                    criado_em=agora_brasil()
                )
                
                db.session.add(separacao)
                separacoes_criadas.append(separacao)
                
                # Acumular totais
                valor_total += valor_separacao
                peso_total += peso_calculado
                pallet_total += pallet_calculado

                # Marcar pré-separação como processada
                pre_sep.status = 'ENVIADO_SEPARACAO'

            if not separacoes_criadas:
                return jsonify({
                    'success': False,
                    'error': 'Nenhuma separação foi criada'
                }), 400

            # Atualizar pedido na tabela pedidos
            pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
            if pedido:
                pedido.separacao_lote_id = novo_lote_id
                pedido.expedicao = data_expedicao_obj
                if pre_separacoes[0].data_agendamento_editada:
                    pedido.agendamento = pre_separacoes[0].data_agendamento_editada
                if pre_separacoes[0].protocolo_editado:
                    pedido.protocolo = pre_separacoes[0].protocolo_editado

            # Commit das mudanças
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Lote transformado em separação com sucesso! {len(separacoes_criadas)} produtos processados.',
                'lote_id': novo_lote_id,
                'separacoes_criadas': len(separacoes_criadas),
                'pre_separacoes_processadas': len(pre_separacoes),
                'totais': {
                    'valor': valor_total,
                    'peso': peso_total,
                    'pallet': pallet_total
                }
            })

        else:
            return jsonify({
                'success': False,
                'error': 'Lote não é uma pré-separação válida'
            }), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao transformar lote {lote_id} em separação: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500