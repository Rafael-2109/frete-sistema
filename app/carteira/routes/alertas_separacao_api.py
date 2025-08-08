"""
API para Alertas de Separações Cotadas Alteradas
==================================================

Endpoints para gerenciar alertas e reimpressões de separações.
"""

from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('alertas_separacao', __name__, url_prefix='/api/alertas-separacao')


@bp.route('/pendentes', methods=['GET'])
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


@bp.route('/reimprimir/<separacao_lote_id>', methods=['POST'])
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
            usuario=current_user.nome if current_user else 'Sistema'
        )
        
        logger.info(f"✅ {qtd_marcados} alertas marcados como reimpresos para {num_pedido}/{separacao_lote_id}")
        
        # Retornar URL para impressão
        url_impressao = url_for('separacao.imprimir_separacao', 
                               separacao_lote_id=separacao_lote_id,
                               _external=True)
        
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


@bp.route('/card-html', methods=['GET'])
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
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Pedido</th>
                                                <th>Cliente</th>
                                                <th>Produto</th>
                                                <th>Alteração</th>
                                                <th>Qtd Anterior</th>
                                                <th>Qtd Nova</th>
                                                <th>Ação</th>
                                            </tr>
                                        </thead>
                                        <tbody>
            '''
            
            for num_pedido, pedido_info in embarque_info['pedidos'].items():
                for item in pedido_info['itens']:
                    tipo_badge = 'danger' if item['tipo_alteracao'] == 'REMOCAO' else 'warning'
                    html += f'''
                                            <tr>
                                                <td>{num_pedido}</td>
                                                <td>{pedido_info.get('cliente', 'N/A')}</td>
                                                <td>{item['cod_produto']}<br><small>{item.get('nome_produto', '')}</small></td>
                                                <td><span class="badge bg-{tipo_badge}">{item['tipo_alteracao']}</span></td>
                                                <td>{item['qtd_anterior']:.2f}</td>
                                                <td>{item['qtd_nova']:.2f}</td>
                                                <td>
                                                    <button class="btn btn-sm btn-primary" 
                                                            onclick="reimprimirSeparacao('{pedido_info['separacao_lote_id']}', '{num_pedido}')">
                                                        <i class="fas fa-print"></i> Reimprimir
                                                    </button>
                                                </td>
                                            </tr>
                    '''
            
            html += '''
                                        </tbody>
                                    </table>
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
        
        <script>
        function reimprimirSeparacao(separacaoLoteId, numPedido) {
            if (!confirm(`Confirma a reimpressão da separação do pedido ${numPedido}?`)) {
                return;
            }
            
            fetch(`/api/alertas-separacao/reimprimir/${separacaoLoteId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Abrir URL de impressão em nova aba
                    window.open(data.url_impressao, '_blank');
                    
                    // Recarregar a página após 2 segundos
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                    
                    alert(`Separação marcada como reimpressa. ${data.alertas_marcados} alertas processados.`);
                } else {
                    alert('Erro ao reimprimir: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao processar reimpressão');
            });
        }
        </script>
        '''
        
        return html
        
    except Exception as e:
        logger.error(f"Erro ao gerar HTML de alertas: {e}")
        return '', 500