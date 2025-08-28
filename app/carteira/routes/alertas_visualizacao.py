"""
Rotas para visualização de alertas de separação
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem, Embarque
from datetime import datetime
from sqlalchemy import func

alertas_visualizacao_bp = Blueprint('alertas_visualizacao', __name__, url_prefix='/carteira/alertas')

@alertas_visualizacao_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard de visualização de alertas"""
    
    # Filtros
    filtro_status = request.args.get('status', 'todos')
    filtro_tipo = request.args.get('tipo', 'todos')
    
    # Query base
    query = AlertaSeparacaoCotada.query
    
    # Aplicar filtros
    if filtro_status == 'pendentes':
        query = query.filter_by(reimpresso=False)
    elif filtro_status == 'reimpresos':
        query = query.filter_by(reimpresso=True)
    
    if filtro_tipo != 'todos':
        query = query.filter_by(tipo_alteracao=filtro_tipo)
    
    # Buscar alertas
    alertas = query.order_by(AlertaSeparacaoCotada.data_alerta.desc()).limit(100).all()
    
    # Enriquecer com dados de pedido e embarque
    alertas_enriquecidos = []
    for alerta in alertas:
        pedido = Pedido.query.filter_by(separacao_lote_id=alerta.separacao_lote_id).first()
        
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=alerta.separacao_lote_id,
            status='ativo'
        ).first()
        
        if not embarque_item:
            embarque_item = EmbarqueItem.query.filter_by(
                pedido=alerta.num_pedido,
                status='ativo'
            ).first()
        
        embarque = None
        if embarque_item:
            embarque = Embarque.query.get(embarque_item.embarque_id)
        
        alertas_enriquecidos.append({
            'alerta': alerta,
            'pedido': pedido,
            'embarque': embarque,
            'is_orfao': not pedido or not embarque_item
        })
    
    # Estatísticas
    stats = {
        'total': AlertaSeparacaoCotada.query.count(),
        'pendentes': AlertaSeparacaoCotada.query.filter_by(reimpresso=False).count(),
        'reimpresos': AlertaSeparacaoCotada.query.filter_by(reimpresso=True).count()
    }
    
    # Tipos de alteração
    tipos = db.session.query(
        AlertaSeparacaoCotada.tipo_alteracao,
        func.count(AlertaSeparacaoCotada.id).label('total')
    ).group_by(AlertaSeparacaoCotada.tipo_alteracao).all()
    
    return render_template(
        'carteira/alertas_dashboard.html',
        alertas=alertas_enriquecidos,
        stats=stats,
        tipos=tipos,
        filtro_status=filtro_status,
        filtro_tipo=filtro_tipo
    )

@alertas_visualizacao_bp.route('/marcar-reimpresso/<int:alerta_id>', methods=['POST'])
@login_required
def marcar_reimpresso(alerta_id):
    """Marca um alerta como reimpresso"""
    
    alerta = AlertaSeparacaoCotada.query.get_or_404(alerta_id)
    
    alerta.reimpresso = True
    alerta.data_reimpressao = datetime.utcnow()
    alerta.usuario_reimpressao = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
    
    db.session.commit()
    
    flash(f'Alerta {alerta_id} marcado como reimpresso', 'success')
    return redirect(url_for('carteira.alertas_visualizacao.dashboard'))

@alertas_visualizacao_bp.route('/limpar-orfaos', methods=['POST'])
@login_required
def limpar_orfaos():
    """Limpa alertas órfãos (sem pedido ou embarque)"""
    
    # Buscar alertas órfãos
    alertas = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).all()
    contador = 0
    
    for alerta in alertas:
        pedido = Pedido.query.filter_by(separacao_lote_id=alerta.separacao_lote_id).first()
        
        if not pedido:
            alerta.reimpresso = True
            alerta.observacoes = "Marcado como reimpresso - Órfão sem pedido"
            contador += 1
            continue
        
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=alerta.separacao_lote_id,
            status='ativo'
        ).first()
        
        if not embarque_item:
            embarque_item = EmbarqueItem.query.filter_by(
                pedido=alerta.num_pedido,
                status='ativo'
            ).first()
        
        if not embarque_item:
            alerta.reimpresso = True
            alerta.observacoes = "Marcado como reimpresso - Órfão sem embarque ativo"
            contador += 1
    
    db.session.commit()
    
    flash(f'{contador} alertas órfãos foram marcados como reimpresos', 'success')
    return redirect(url_for('carteira.alertas_visualizacao.dashboard'))