"""
Rotas de agendamento integradas com Separação e De-Para
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app import db
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('portal_agendamento', __name__, url_prefix='/portal/atacadao/agendamento')

@bp.route('/status')
@login_required
def status():
    """
    Página para visualizar e gerenciar status de agendamentos
    """
    return render_template('portal/atacadao/agendamento/status.html')

@bp.route('/preparar/<separacao_lote_id>')
@login_required
def preparar_agendamento(separacao_lote_id):
    """
    Prepara dados de agendamento baseado na Separação
    Converte códigos usando De-Para
    """
    try:
        # Buscar itens da separação
        itens_separacao = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()
        
        if not itens_separacao:
            return jsonify({
                'success': False,
                'message': f'Nenhum item encontrado para o lote {separacao_lote_id}'
            }), 404
        
        # Preparar dados para o formulário
        produtos_formulario = []
        produtos_sem_depara = []
        
        for item in itens_separacao:
            # Buscar conversão De-Para
            depara = ProdutoDeParaAtacadao.query.filter_by(
                codigo_nosso=item.cod_produto,
                ativo=True
            ).first()
            
            if depara:
                # Calcular quantidade convertida
                qtd_convertida = float(item.qtd_saldo or 0) * float(depara.fator_conversao)
                
                # Buscar palletização
                palletizacao = CadastroPalletizacao.query.filter_by(
                    cod_produto=item.cod_produto
                ).first()
                
                pallets = 0
                if palletizacao and palletizacao.palletizacao:
                    pallets = qtd_convertida / float(palletizacao.palletizacao)
                
                produtos_formulario.append({
                    'codigo_atacadao': depara.codigo_atacadao,
                    'descricao_atacadao': depara.descricao_atacadao,
                    'codigo_nosso': item.cod_produto,
                    'descricao_nosso': depara.descricao_nosso,
                    'quantidade': qtd_convertida,
                    'pallets': round(pallets, 2),
                    'fator_conversao': float(depara.fator_conversao)
                })
            else:
                # Produto sem De-Para cadastrado
                produtos_sem_depara.append({
                    'codigo': item.cod_produto,
                    'quantidade': float(item.qtd_saldo or 0)
                })
        
        # Pegar data de agendamento do primeiro item
        data_agendamento = None
        if itens_separacao:
            data_agendamento = itens_separacao[0].agendamento
        
        return jsonify({
            'success': True,
            'lote_id': separacao_lote_id,
            'data_agendamento': data_agendamento.strftime('%d/%m/%Y') if data_agendamento else None,
            'produtos': produtos_formulario,
            'produtos_sem_depara': produtos_sem_depara,
            'total_itens': len(itens_separacao),
            'total_convertidos': len(produtos_formulario)
        })
        
    except Exception as e:
        logger.error(f"Erro ao preparar agendamento: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/gravar_protocolo', methods=['POST'])
@login_required
def gravar_protocolo():
    """
    Grava o protocolo de agendamento na Separação
    Marca agendamento_confirmado como False (aguardando confirmação)
    """
    try:
        data = request.get_json()
        separacao_lote_id = data.get('lote_id')
        protocolo = data.get('protocolo')
        
        if not separacao_lote_id or not protocolo:
            return jsonify({
                'success': False,
                'message': 'Lote ID e protocolo são obrigatórios'
            }), 400
        
        # Atualizar todos os itens da separação
        itens_atualizados = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update({
            'protocolo': protocolo,
            'agendamento_confirmado': False,  # Aguardando confirmação
        })
        
        db.session.commit()
        
        logger.info(f"Protocolo {protocolo} gravado para lote {separacao_lote_id} - {itens_atualizados} itens")
        
        return jsonify({
            'success': True,
            'message': f'Protocolo {protocolo} gravado com sucesso',
            'itens_atualizados': itens_atualizados
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gravar protocolo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/confirmar_agendamento', methods=['POST'])
@login_required
def confirmar_agendamento():
    """
    Confirma o agendamento após verificação manual
    Marca agendamento_confirmado como True
    """
    try:
        data = request.get_json()
        separacao_lote_id = data.get('lote_id')
        
        if not separacao_lote_id:
            return jsonify({
                'success': False,
                'message': 'Lote ID é obrigatório'
            }), 400
        
        # Verificar se tem protocolo
        item_exemplo = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()
        
        if not item_exemplo or not item_exemplo.protocolo:
            return jsonify({
                'success': False,
                'message': 'Protocolo não encontrado. Realize o agendamento primeiro.'
            }), 400
        
        # Confirmar agendamento
        itens_confirmados = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update({
            'agendamento_confirmado': True,
        })
        
        db.session.commit()
        
        logger.info(f"Agendamento confirmado para lote {separacao_lote_id} - {itens_confirmados} itens")
        
        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado com sucesso',
            'protocolo': item_exemplo.protocolo,
            'itens_confirmados': itens_confirmados
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar agendamento: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/verificar_depara/<separacao_lote_id>')
@login_required
def verificar_depara(separacao_lote_id):
    """
    Verifica quais produtos da separação têm De-Para cadastrado
    """
    try:
        # Buscar itens únicos da separação
        itens = db.session.query(
            Separacao.cod_produto
        ).filter_by(
            separacao_lote_id=separacao_lote_id
        ).distinct().all()
        
        produtos_com_depara = []
        produtos_sem_depara = []
        
        for item in itens:
            codigo = item.cod_produto
            
            # Verificar se tem De-Para
            depara = ProdutoDeParaAtacadao.query.filter_by(
                codigo_nosso=codigo,
                ativo=True
            ).first()
            
            if depara:
                produtos_com_depara.append({
                    'codigo_nosso': codigo,
                    'codigo_atacadao': depara.codigo_atacadao,
                    'descricao_atacadao': depara.descricao_atacadao
                })
            else:
                # Buscar descrição do produto
                produto = CadastroPalletizacao.query.filter_by(
                    cod_produto=codigo
                ).first()
                
                produtos_sem_depara.append({
                    'codigo': codigo,
                    'descricao': produto.nome_produto if produto else 'Produto não encontrado'
                })
        
        return jsonify({
            'success': True,
            'lote_id': separacao_lote_id,
            'total_produtos': len(itens),
            'com_depara': len(produtos_com_depara),
            'sem_depara': len(produtos_sem_depara),
            'produtos_com_depara': produtos_com_depara,
            'produtos_sem_depara': produtos_sem_depara
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar De-Para: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500