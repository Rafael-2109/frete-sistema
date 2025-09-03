"""
APIs centralizadas para agendamento da carteira
Consolidação de todas as funcionalidades de agendamento
"""

from flask import jsonify, request
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.pedidos.models import Pedido
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/agendamento-info')
@login_required
def obter_info_agendamento(num_pedido):
    """
    API para obter informações completas de agendamento de um pedido
    Usado pelos modais de agendamento
    """
    try:
        # Buscar dados agregados do pedido
        pedido_info = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.raz_social_red.label('cliente'),
            CarteiraPrincipal.nome_cidade.label('cidade'),
            CarteiraPrincipal.cod_uf.label('uf'),
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.hora_agendamento,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento_confirmado,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.hora_agendamento,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento_confirmado
        ).first()

        if not pedido_info:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado'
            }), 404

        # Buscar itens do pedido
        itens = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido.label('quantidade'),
            (CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            CarteiraPrincipal.expedicao
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()

        itens_formatados = []
        for item in itens:
            itens_formatados.append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto or '',
                'quantidade': float(item.quantidade or 0),
                'valor_total': float(item.valor_total or 0),
                'expedicao': item.expedicao.isoformat() if item.expedicao else None
            })

        return jsonify({
            'success': True,
            'cliente': pedido_info.cliente or '',
            'cidade': pedido_info.cidade or '',
            'uf': pedido_info.uf or '',
            'vendedor': pedido_info.vendedor or '',
            'equipe_vendas': pedido_info.equipe_vendas or '',
            'valor_total': float(pedido_info.valor_total or 0),
            'total_itens': pedido_info.total_itens or 0,
            'expedicao': pedido_info.expedicao.isoformat() if pedido_info.expedicao else None,
            'agendamento': pedido_info.agendamento.isoformat() if pedido_info.agendamento else None,
            'hora_agendamento': pedido_info.hora_agendamento.strftime('%H:%M') if pedido_info.hora_agendamento else None,
            'protocolo': pedido_info.protocolo or '',
            'agendamento_confirmado': bool(pedido_info.agendamento_confirmado),
            'itens': itens_formatados
        })

    except Exception as e:
        logger.error(f"Erro ao buscar agendamento do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/salvar-agendamento', methods=['POST'])
@login_required
def salvar_agendamento(num_pedido):
    """
    API para salvar/atualizar agendamento de um pedido
    Atualiza todos os itens do pedido na carteira e na tabela pedidos
    """
    try:
        data = request.get_json()
        data_expedicao = data.get('data_expedicao')
        data_agendamento = data.get('data_agendamento')
        protocolo = data.get('protocolo')
        confirmado = data.get('confirmado', False)

        if not data_expedicao:
            return jsonify({
                'success': False,
                'error': 'Data de expedição é obrigatória'
            }), 400

        # Converter datas
        try:
            data_exp_obj = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de data de expedição inválido'
            }), 400

        data_agend_obj = None
        if data_agendamento:
            try:
                data_agend_obj = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de data de agendamento inválido'
                }), 400

        # Atualizar todos os itens do pedido na carteira
        itens_atualizados = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).update({
            'expedicao': data_exp_obj,
            'agendamento': data_agend_obj,
            'protocolo': protocolo,
            'agendamento_confirmado': confirmado
        })

        if itens_atualizados == 0:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404

        # Atualizar também na tabela Pedido se existir
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        separacoes_atualizadas = 0
        pre_separacoes_atualizadas = 0
        
        if pedido:
            pedido.expedicao = data_exp_obj
            pedido.agendamento = data_agend_obj
            pedido.protocolo = protocolo
            
            # IMPORTANTE: Se o pedido tem separacao_lote_id, atualizar também as Separações deste lote
            if pedido.separacao_lote_id:
                from app.separacao.models import Separacao
                from app.carteira.models import PreSeparacaoItem
                
                logger.info(f"Atualizando Separações do lote {pedido.separacao_lote_id} com novas datas")
                
                # Atualizar Separações do lote específico
                separacoes_atualizadas = db.session.query(Separacao).filter(
                    Separacao.separacao_lote_id == pedido.separacao_lote_id
                ).update({
                    'expedicao': data_exp_obj,
                    'agendamento': data_agend_obj,
                    'protocolo': protocolo
                })
                
                # Atualizar PreSeparacaoItem que estão vinculadas a este lote
                # (status ENVIADO_SEPARACAO significa que já foram convertidas em separação)
                pre_separacoes_atualizadas = db.session.query(PreSeparacaoItem).filter(
                    PreSeparacaoItem.separacao_lote_id == pedido.separacao_lote_id,
                    PreSeparacaoItem.status == 'ENVIADO_SEPARACAO'
                ).update({
                    'data_expedicao_editada': data_exp_obj,
                    'data_agendamento_editada': data_agend_obj,
                    'protocolo_editado': protocolo
                })
                
                if separacoes_atualizadas > 0:
                    logger.info(f"✅ {separacoes_atualizadas} separações atualizadas com novas datas")
                if pre_separacoes_atualizadas > 0:
                    logger.info(f"✅ {pre_separacoes_atualizadas} pré-separações (ENVIADO_SEPARACAO) atualizadas")
        
        # Também atualizar PreSeparacaoItem que ainda não foram enviadas para separação
        # mas que são do mesmo pedido (mantém consistência)
        from app.carteira.models import PreSeparacaoItem
        pre_sep_pendentes = db.session.query(PreSeparacaoItem).filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).update({
            'data_expedicao_editada': data_exp_obj,
            'data_agendamento_editada': data_agend_obj,
            'protocolo_editado': protocolo
        })
        
        if pre_sep_pendentes > 0:
            logger.info(f"✅ {pre_sep_pendentes} pré-separações pendentes atualizadas")

        db.session.commit()

        # Preparar mensagem de retorno detalhada
        mensagem_detalhes = [f'{itens_atualizados} itens da carteira']
        if separacoes_atualizadas > 0:
            mensagem_detalhes.append(f'{separacoes_atualizadas} separações')
        if pre_separacoes_atualizadas > 0:
            mensagem_detalhes.append(f'{pre_separacoes_atualizadas} pré-separações enviadas')
        if pre_sep_pendentes > 0:
            mensagem_detalhes.append(f'{pre_sep_pendentes} pré-separações pendentes')
        
        mensagem_final = f'Expedição e agendamento salvos com sucesso! Atualizados: {", ".join(mensagem_detalhes)}.'

        return jsonify({
            'success': True,
            'message': mensagem_final,
            'data_expedicao': data_expedicao,
            'data_agendamento': data_agendamento,
            'confirmado': confirmado,
            'detalhes': {
                'carteira': itens_atualizados,
                'separacoes': separacoes_atualizadas,
                'pre_separacoes_enviadas': pre_separacoes_atualizadas,
                'pre_separacoes_pendentes': pre_sep_pendentes
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar agendamento do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento(num_pedido):
    """
    API para confirmar um agendamento existente
    Apenas marca como confirmado sem alterar dados
    """
    try:
        # Verificar se pedido tem agendamento
        pedido_info = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.agendamento.isnot(None)
        ).first()

        if not pedido_info:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não possui agendamento para confirmar'
            }), 404

        # Atualizar confirmação
        itens_atualizados = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).update({
            'agendamento_confirmado': True
        })

        # IMPORTANTE: Também confirmar nas Separações se o pedido tem lote de separação
        # Buscar o pedido para obter o separacao_lote_id
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        separacoes_confirmadas = 0
        
        if pedido and pedido.separacao_lote_id:
            from app.separacao.models import Separacao
            
            logger.info(f"Confirmando agendamento nas Separações do lote {pedido.separacao_lote_id}")
            
            # Atualizar agendamento_confirmado nas Separações do lote
            separacoes_confirmadas = db.session.query(Separacao).filter(
                Separacao.separacao_lote_id == pedido.separacao_lote_id
            ).update({
                'agendamento_confirmado': True
            })
            
            if separacoes_confirmadas > 0:
                logger.info(f"✅ {separacoes_confirmadas} separações do lote {pedido.separacao_lote_id} confirmadas")

        db.session.commit()

        # Preparar mensagem detalhada
        mensagem_detalhes = [f'{itens_atualizados} itens da carteira']
        if separacoes_confirmadas > 0:
            mensagem_detalhes.append(f'{separacoes_confirmadas} separações verificadas')
        
        mensagem_final = f'Agendamento confirmado com sucesso! Confirmados: {", ".join(mensagem_detalhes)}.'

        return jsonify({
            'success': True,
            'message': mensagem_final,
            'detalhes': {
                'carteira': itens_atualizados,
                'separacoes_verificadas': separacoes_confirmadas
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar agendamento do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500


@carteira_bp.route('/api/pedido/<num_pedido>/cancelar-agendamento', methods=['POST'])
@login_required
def cancelar_agendamento(num_pedido):
    """
    API para cancelar/limpar agendamento de um pedido
    """
    try:
        # Limpar dados de agendamento
        itens_atualizados = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).update({
            'agendamento': None,
            'hora_agendamento': None,
            'protocolo': None,
            'agendamento_confirmado': False
        })

        if itens_atualizados == 0:
            return jsonify({
                'success': False,
                'error': f'Nenhum item encontrado para o pedido {num_pedido}'
            }), 404

        # Limpar também na tabela Pedido
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        separacoes_limpas = 0
        pre_separacoes_limpas = 0
        
        if pedido:
            pedido.agendamento = None
            pedido.protocolo = None
            
            # IMPORTANTE: Limpar também nas Separações e PreSeparacaoItem se houver lote
            if pedido.separacao_lote_id:
                from app.separacao.models import Separacao
                from app.carteira.models import PreSeparacaoItem
                
                logger.info(f"Cancelando agendamento nas Separações do lote {pedido.separacao_lote_id}")
                
                # Limpar agendamento nas Separações do lote
                separacoes_limpas = db.session.query(Separacao).filter(
                    Separacao.separacao_lote_id == pedido.separacao_lote_id
                ).update({
                    'agendamento': None,
                    'protocolo': None,
                    'agendamento_confirmado': False
                })
                
                # Limpar agendamento nas PreSeparacaoItem enviadas para separação
                pre_separacoes_limpas = db.session.query(PreSeparacaoItem).filter(
                    PreSeparacaoItem.separacao_lote_id == pedido.separacao_lote_id,
                    PreSeparacaoItem.status == 'ENVIADO_SEPARACAO'
                ).update({
                    'data_agendamento_editada': None,
                    'protocolo_editado': None
                })
                
                if separacoes_limpas > 0:
                    logger.info(f"✅ {separacoes_limpas} separações tiveram agendamento cancelado")
                if pre_separacoes_limpas > 0:
                    logger.info(f"✅ {pre_separacoes_limpas} pré-separações tiveram agendamento cancelado")
        
        # Limpar também PreSeparacaoItem pendentes do mesmo pedido
        pre_sep_pendentes = db.session.query(PreSeparacaoItem).filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).update({
            'data_agendamento_editada': None,
            'protocolo_editado': None
        })
        
        if pre_sep_pendentes > 0:
            logger.info(f"✅ {pre_sep_pendentes} pré-separações pendentes tiveram agendamento cancelado")

        db.session.commit()

        # Preparar mensagem detalhada
        mensagem_detalhes = [f'{itens_atualizados} itens da carteira']
        if separacoes_limpas > 0:
            mensagem_detalhes.append(f'{separacoes_limpas} separações')
        if pre_separacoes_limpas > 0:
            mensagem_detalhes.append(f'{pre_separacoes_limpas} pré-separações enviadas')
        if pre_sep_pendentes > 0:
            mensagem_detalhes.append(f'{pre_sep_pendentes} pré-separações pendentes')
        
        mensagem_final = f'Agendamento cancelado com sucesso! Limpos: {", ".join(mensagem_detalhes)}.'

        return jsonify({
            'success': True,
            'message': mensagem_final,
            'detalhes': {
                'carteira': itens_atualizados,
                'separacoes': separacoes_limpas,
                'pre_separacoes_enviadas': pre_separacoes_limpas,
                'pre_separacoes_pendentes': pre_sep_pendentes
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao cancelar agendamento do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500