from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem
from sqlalchemy import func

app = create_app()
with app.app_context():
    # Verificar todos os alertas não reimpresos
    alertas = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).all()
    print(f'Total de alertas não reimpresos: {len(alertas)}')
    print('\nDetalhes dos alertas:')
    
    # Agrupar por lote
    lotes = {}
    for alerta in alertas:
        if alerta.separacao_lote_id not in lotes:
            lotes[alerta.separacao_lote_id] = {
                'alertas': [],
                'pedido': None,
                'embarque_item': None
            }
        lotes[alerta.separacao_lote_id]['alertas'].append(alerta)
    
    # Para cada lote, verificar status
    for lote_id, info in lotes.items():
        print(f'\n📦 Lote: {lote_id}')
        print(f'   Alertas: {len(info["alertas"])} produtos alterados')
        
        # Verificar Pedido
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido:
            print(f'   Pedido: {pedido.num_pedido} - Status: {pedido.status}')
            info['pedido'] = pedido
        else:
            print(f'   ❌ Pedido não encontrado')
        
        # Verificar EmbarqueItem
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=lote_id,
            status='ativo'
        ).first()
        if embarque_item:
            print(f'   ✅ EmbarqueItem ATIVO - Embarque #{embarque_item.embarque_id}')
            info['embarque_item'] = embarque_item
        else:
            # Verificar se existe com outro status
            embarque_cancelado = EmbarqueItem.query.filter_by(
                separacao_lote_id=lote_id,
                status='cancelado'
            ).first()
            if embarque_cancelado:
                print(f'   ⚠️ EmbarqueItem CANCELADO - Embarque #{embarque_cancelado.embarque_id}')
            else:
                print(f'   ❌ EmbarqueItem não encontrado')
    
    # Resumo
    print('\n📊 RESUMO:')
    cotados_com_embarque = sum(1 for info in lotes.values() if info['pedido'] and info['pedido'].status == 'COTADO' and info['embarque_item'])
    cotados_sem_embarque = sum(1 for info in lotes.values() if info['pedido'] and info['pedido'].status == 'COTADO' and not info['embarque_item'])
    outros_status = sum(1 for info in lotes.values() if info['pedido'] and info['pedido'].status != 'COTADO')
    sem_pedido = sum(1 for info in lotes.values() if not info['pedido'])
    
    print(f'   COTADOS com embarque ativo: {cotados_com_embarque}')
    print(f'   COTADOS sem embarque ativo: {cotados_sem_embarque}')
    print(f'   Outros status: {outros_status}')
    print(f'   Sem pedido: {sem_pedido}')