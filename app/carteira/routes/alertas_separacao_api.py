"""
API para Alertas de Separações Cotadas Alteradas
==================================================

Endpoints para gerenciar alertas e reimpressões de separações.
"""

from flask import Blueprint, jsonify, request, url_for
from flask_login import login_required, current_user
from app.carteira.models_alertas import AlertaSeparacaoCotada
import logging

logger = logging.getLogger(__name__)

alertas_separacao_api = Blueprint('alertas_separacao', __name__, url_prefix='/api/alertas-separacao')


@alertas_separacao_api.route('/pendentes', methods=['GET'])
@login_required
def buscar_alertas_pendentes():
    """
    Retorna alertas pendentes agrupados por embarque
    """
    try:
        alertas = AlertaSeparacaoCotada.buscar_alertas_pendentes()
        total_alertas = AlertaSeparacaoCotada.contar_alertas_pendentes()
        
        return jsonify({
            'success': True,
            'total_alertas': total_alertas,
            'alertas_por_embarque': alertas
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alertas_separacao_api.route('/reimprimir/<separacao_lote_id>', methods=['POST'])
@login_required
def reimprimir_separacao(separacao_lote_id):
    """
    Marca separação como reimpressa e redireciona para impressão
    """
    try:
        num_pedido = request.json.get('num_pedido')
        
        if not num_pedido:
            return jsonify({
                'success': False,
                'error': 'Número do pedido é obrigatório'
            }), 400
        
        # Marcar alertas como reimpresos
        qtd_marcados = AlertaSeparacaoCotada.marcar_como_reimpresso(
            num_pedido=num_pedido,
            separacao_lote_id=separacao_lote_id,
            usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        )
        
        logger.info(f"✅ {qtd_marcados} alertas marcados como reimpresos para {num_pedido}/{separacao_lote_id}")
        
        # Retornar URL para impressão - buscar embarque_id primeiro
        from app.embarques.models import EmbarqueItem
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=separacao_lote_id,
            status='ativo'
        ).first()
        
        if embarque_item:
            url_impressao = url_for('embarques.imprimir_separacao', 
                                   embarque_id=embarque_item.embarque_id,
                                   separacao_lote_id=separacao_lote_id,
                                   _external=True)
        else:
            # Fallback caso não encontre o embarque
            url_impressao = '#'
        
        return jsonify({
            'success': True,
            'alertas_marcados': qtd_marcados,
            'url_impressao': url_impressao
        })
        
    except Exception as e:
        logger.error(f"Erro ao reimprimir separação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alertas_separacao_api.route('/card-html', methods=['GET'])
@login_required
def get_card_alertas_html():
    """
    Retorna HTML do card de alertas para inserir no topo da página
    """
    try:
        alertas = AlertaSeparacaoCotada.buscar_alertas_pendentes()
        total_alertas = AlertaSeparacaoCotada.contar_alertas_pendentes()
        
        if total_alertas == 0:
            return '', 204  # No content
        
        # Gerar HTML do card
        html = f'''
        <div class="alert alert-warning alert-dismissible fade show" role="alert" id="alertaSeparacoesCotadas">
            <div class="d-flex align-items-start">
                <div class="flex-grow-1">
                    <h5 class="alert-heading mb-3">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        {total_alertas} Separações COTADAS Alteradas - Reimpressão Necessária
                    </h5>
                    
                    <div class="accordion" id="accordionAlertas">
        '''
        
        for idx, (embarque_num, embarque_info) in enumerate(alertas.items()):
            html += f'''
                        <div class="accordion-item mb-2">
                            <h6 class="accordion-header" id="heading{idx}">
                                <button class="accordion-button collapsed" type="button" 
                                        data-bs-toggle="collapse" data-bs-target="#collapse{idx}">
                                    <strong>Embarque #{embarque_num}</strong>
                                    <span class="ms-3 badge bg-danger">
                                        {len(embarque_info["pedidos"])} pedidos alterados
                                    </span>
                                </button>
                            </h6>
                            <div id="collapse{idx}" class="accordion-collapse collapse" 
                                 data-bs-parent="#accordionAlertas">
                                <div class="accordion-body">
            '''
            
            # Agrupar por pedido para ter um único botão por pedido
            for num_pedido, pedido_info in embarque_info['pedidos'].items():
                html += f'''
                                    <div class="mb-3 border rounded p-2">
                                        <div class="d-flex justify-content-between align-items-start mb-2">
                                            <div>
                                                <strong>Pedido: {num_pedido}</strong><br>
                                                <small class="text-muted">Cliente: {pedido_info.get('cliente', 'N/A')}</small>
                                            </div>
                                            <button class="btn btn-sm btn-primary" 
                                                    onclick="reimprimirSeparacao('{pedido_info['separacao_lote_id']}', '{num_pedido}')">
                                                <i class="fas fa-print"></i> Reimprimir Separação
                                            </button>
                                        </div>
                                        <table class="table table-sm mb-0">
                                            <thead>
                                                <tr>
                                                    <th>Produto</th>
                                                    <th>Alteração</th>
                                                    <th>Qtd Anterior</th>
                                                    <th>Qtd Nova</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                '''
                
                for item in pedido_info['itens']:
                    tipo_badge = 'danger' if item['tipo_alteracao'] == 'REMOCAO' else 'warning'
                    html += f'''
                                                <tr>
                                                    <td>{item['cod_produto']}<br><small class="text-muted">{item.get('nome_produto', '')}</small></td>
                                                    <td><span class="badge bg-{tipo_badge}">{item['tipo_alteracao']}</span></td>
                                                    <td>{item['qtd_anterior']:.2f}</td>
                                                    <td>{item['qtd_nova']:.2f}</td>
                                                </tr>
                    '''
                
                html += '''
                                            </tbody>
                                        </table>
                                    </div>
                '''
            
            html += '''
                                </div>
                            </div>
                        </div>
            '''
        
        html += '''
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        </div>
        '''
        
        return html
        
    except Exception as e:
        logger.error(f"Erro ao gerar HTML de alertas: {e}")
        return '', 500