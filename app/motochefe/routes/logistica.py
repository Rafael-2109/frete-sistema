"""
Rotas de Logística - MotoChefe
Embarques: Agrupamento de pedidos para entrega com rateio de frete
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    EmbarqueMoto, EmbarquePedido, PedidoVendaMoto,
    TransportadoraMoto
)


def gerar_numero_embarque():
    """
    Gera número sequencial de embarque no formato EMB-001, EMB-002, etc.
    """
    # Buscar último embarque criado
    ultimo = EmbarqueMoto.query.order_by(EmbarqueMoto.id.desc()).first()

    if not ultimo or not ultimo.numero_embarque:
        return 'EMB-001'

    # Extrair número do formato EMB-XXX
    try:
        numero_str = ultimo.numero_embarque.replace('EMB-', '')
        numero = int(numero_str)
        proximo = numero + 1
        return f'EMB-{proximo:03d}'
    except (ValueError, AttributeError):
        return 'EMB-001'


# ===== CRUD EMBARQUES =====

@motochefe_bp.route('/embarques')
@login_required
@requer_motochefe
def listar_embarques():
    """Lista todos os embarques com paginação"""
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    query = EmbarqueMoto.query.filter_by(ativo=True)

    if status:
        query = query.filter_by(status=status)

    paginacao = query.order_by(EmbarqueMoto.data_embarque.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/logistica/embarques/listar.html',
                         embarques=paginacao.items,
                         paginacao=paginacao)


@motochefe_bp.route('/embarques/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_embarque():
    """Cria novo embarque vazio"""
    if request.method == 'POST':
        try:
            # Gerar número automático
            numero = gerar_numero_embarque()

            embarque = EmbarqueMoto(
                numero_embarque=numero,
                transportadora_id=int(request.form.get('transportadora_id')),
                data_embarque=datetime.strptime(request.form.get('data_embarque'), '%Y-%m-%d').date() if request.form.get('data_embarque') else date.today(),
                data_entrega_prevista=datetime.strptime(request.form.get('data_entrega_prevista'), '%Y-%m-%d').date() if request.form.get('data_entrega_prevista') else None,
                valor_frete_contratado=Decimal(request.form.get('valor_frete_contratado')),
                tipo_veiculo=request.form.get('tipo_veiculo'),
                status=request.form.get('status', 'PLANEJADO'),
                observacoes=request.form.get('observacoes'),
                criado_por=current_user.nome
            )

            db.session.add(embarque)
            db.session.commit()

            flash(f'Embarque {numero} criado com sucesso!', 'success')
            return redirect(url_for('motochefe.editar_embarque', id=embarque.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar embarque: {str(e)}', 'danger')
            return redirect(url_for('motochefe.adicionar_embarque'))

    # GET - Carregar transportadoras
    transportadoras = TransportadoraMoto.query.filter_by(ativo=True).order_by(TransportadoraMoto.transportadora).all()

    return render_template('motochefe/logistica/embarques/form.html',
                         embarque=None,
                         transportadoras=transportadoras)


@motochefe_bp.route('/embarques/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_embarque(id):
    """Edita embarque e gerencia pedidos"""
    embarque = EmbarqueMoto.query.get_or_404(id)

    if request.method == 'POST':
        try:
            import json

            # ✅ VALIDAÇÃO 1: Embarque DEVE ter pelo menos 1 pedido
            if embarque.pedidos_rel.count() == 0:
                raise Exception('Embarque deve ter pelo menos 1 pedido associado antes de salvar')

            embarque.transportadora_id = int(request.form.get('transportadora_id'))
            embarque.data_embarque = datetime.strptime(request.form.get('data_embarque'), '%Y-%m-%d').date()
            embarque.data_entrega_prevista = datetime.strptime(request.form.get('data_entrega_prevista'), '%Y-%m-%d').date() if request.form.get('data_entrega_prevista') else None
            embarque.valor_frete_contratado = Decimal(request.form.get('valor_frete_contratado'))
            embarque.tipo_veiculo = request.form.get('tipo_veiculo')
            embarque.observacoes = request.form.get('observacoes')

            # ✅ AUDITORIA 2: Registrar mudança de status
            novo_status = request.form.get('status')
            if novo_status != embarque.status:
                # Carregar histórico existente
                historico = []
                if embarque.historico_status:
                    try:
                        historico = json.loads(embarque.historico_status)
                    except:
                        historico = []

                # Adicionar nova entrada
                historico.append({
                    'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'de': embarque.status,
                    'para': novo_status,
                    'usuario': current_user.nome
                })

                embarque.historico_status = json.dumps(historico, ensure_ascii=False)
                embarque.status = novo_status

            embarque.atualizado_por = current_user.nome

            # ✅ VALIDAÇÃO 3: Recalcular saldo
            embarque.valor_frete_saldo = embarque.valor_frete_contratado - (embarque.valor_frete_pago or Decimal('0'))

            db.session.commit()
            flash('Embarque atualizado com sucesso!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'danger')

        return redirect(url_for('motochefe.editar_embarque', id=id))

    # GET - Carregar dados
    transportadoras = TransportadoraMoto.query.filter_by(ativo=True).order_by(TransportadoraMoto.transportadora).all()

    # Buscar TODOS os pedidos (conforme solicitado)
    todos_pedidos = PedidoVendaMoto.query.filter_by(ativo=True).order_by(PedidoVendaMoto.data_pedido.desc()).all()

    return render_template('motochefe/logistica/embarques/form.html',
                         embarque=embarque,
                         transportadoras=transportadoras,
                         todos_pedidos=todos_pedidos)


@motochefe_bp.route('/embarques/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_embarque(id):
    """Remove (desativa) embarque"""
    embarque = EmbarqueMoto.query.get_or_404(id)

    # Reverter todos os pedidos enviados
    for ep in embarque.pedidos_rel.all():
        if ep.enviado:
            ep.pedido.enviado = False

    embarque.ativo = False
    embarque.atualizado_por = current_user.nome
    db.session.commit()

    flash('Embarque removido com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_embarques'))


# ===== GERENCIAMENTO DE PEDIDOS NO EMBARQUE =====

@motochefe_bp.route('/embarques/<int:id>/adicionar-pedido', methods=['POST'])
@login_required
@requer_motochefe
def adicionar_pedido_embarque(id):
    """Adiciona pedido ao embarque"""
    embarque = EmbarqueMoto.query.get_or_404(id)

    try:
        pedido_id = int(request.form.get('pedido_id'))
        pedido = PedidoVendaMoto.query.get_or_404(pedido_id)

        # Verificar se já existe (PERMITIDO ter duplicata conforme solicitado)
        # Apenas verificar se é exatamente o mesmo embarque + pedido
        existe = EmbarquePedido.query.filter_by(
            embarque_id=embarque.id,
            pedido_id=pedido_id
        ).first()

        if existe:
            flash('Este pedido já está neste embarque', 'warning')
            return redirect(url_for('motochefe.editar_embarque', id=id))

        # Criar relação
        ep = EmbarquePedido(
            embarque_id=embarque.id,
            pedido_id=pedido.id,
            qtd_motos_pedido=pedido.quantidade_motos,
            enviado=False  # Inicia como False
        )

        db.session.add(ep)
        db.session.commit()

        flash(f'Pedido {pedido.numero_pedido} adicionado ao embarque!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar pedido: {str(e)}', 'danger')

    return redirect(url_for('motochefe.editar_embarque', id=id))


@motochefe_bp.route('/embarques/<int:id>/remover-pedido/<int:ep_id>', methods=['POST'])
@login_required
@requer_motochefe
def remover_pedido_embarque(id, ep_id):
    """Remove pedido do embarque e REVERTE status enviado"""
    ep = EmbarquePedido.query.get_or_404(ep_id)

    # OPÇÃO 1: Reverter PedidoVendaMoto.enviado se estava True
    if ep.enviado:
        ep.pedido.enviado = False

    db.session.delete(ep)
    db.session.commit()

    flash('Pedido removido do embarque e status revertido!', 'success')
    return redirect(url_for('motochefe.editar_embarque', id=id))


@motochefe_bp.route('/embarques/<int:id>/marcar-enviado/<int:ep_id>', methods=['POST'])
@login_required
@requer_motochefe
def marcar_pedido_enviado(id, ep_id):
    """
    Marca/desmarca pedido como enviado
    TRIGGER: Ao marcar enviado=True:
      - Calcula rateio
      - Marca PedidoVendaMoto.enviado = True
    """
    ep = EmbarquePedido.query.get_or_404(ep_id)

    # Obter novo valor (toggle)
    novo_valor = request.form.get('enviado') == '1'

    try:
        if novo_valor:
            # MARCAR ENVIADO
            ep.enviado = True

            # TRIGGER 1: Calcular rateio
            ep.calcular_rateio()

            # TRIGGER 2: Marcar pedido como enviado
            ep.pedido.enviado = True

            flash(f'Pedido marcado como enviado! Rateio calculado: R$ {ep.valor_frete_rateado:.2f}', 'success')

        else:
            # DESMARCAR ENVIADO (OPÇÃO 1: Reverter)
            ep.enviado = False
            ep.valor_frete_rateado = 0

            # REVERTER pedido
            ep.pedido.enviado = False

            flash('Pedido desmarcado e status revertido!', 'info')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {str(e)}', 'danger')

    return redirect(url_for('motochefe.editar_embarque', id=id))


# ===== PAGAMENTO DE FRETE =====

@motochefe_bp.route('/embarques/<int:id>/pagar-frete', methods=['POST'])
@login_required
@requer_motochefe
def pagar_frete_embarque(id):
    """Registra pagamento do frete (modal) - REFATORADO"""
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    from app.motochefe.services.movimentacao_service import registrar_pagamento_frete_embarque
    from app.motochefe.services.empresa_service import atualizar_saldo

    embarque = EmbarqueMoto.query.get_or_404(id)

    try:
        # ✅ VALIDAÇÃO 1: Embarque DEVE ter pedidos
        if embarque.pedidos_rel.count() == 0:
            raise Exception('Embarque sem pedidos não pode ter frete pago')

        valor_pago = Decimal(request.form.get('valor_frete_pago'))
        data_pag = datetime.strptime(request.form.get('data_pagamento_frete'), '%Y-%m-%d').date()
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')

        if not empresa_pagadora_id:
            raise Exception('Selecione a empresa pagadora')

        empresa_pagadora = EmpresaVendaMoto.query.get_or_404(int(empresa_pagadora_id))

        # ✅ VALIDAÇÃO 2: Determinar status baseado no valor pago
        valor_ja_pago = embarque.valor_frete_pago or Decimal('0')
        valor_total_pago = valor_ja_pago + valor_pago

        if valor_total_pago < embarque.valor_frete_contratado:
            # Pagamento PARCIAL
            novo_status = 'PARCIAL'
            saldo_restante = embarque.valor_frete_contratado - valor_total_pago
            msg_extra = f' | Saldo devedor: R$ {saldo_restante:,.2f}'
        elif valor_total_pago == embarque.valor_frete_contratado:
            # Pagamento TOTAL
            novo_status = 'PAGO'
            saldo_restante = Decimal('0')
            msg_extra = ' | Frete quitado!'
        else:
            # Pagamento MAIOR que contratado
            novo_status = 'PAGO'
            saldo_restante = Decimal('0')
            msg_extra = f' | ATENÇÃO: Pago a mais! Contratado: R$ {embarque.valor_frete_contratado:,.2f}'

        # Atualizar embarque
        embarque.valor_frete_pago = valor_total_pago
        embarque.valor_frete_saldo = saldo_restante
        embarque.data_pagamento_frete = data_pag
        embarque.status_pagamento_frete = novo_status
        embarque.empresa_pagadora_id = empresa_pagadora.id
        embarque.atualizado_por = current_user.nome

        # ✅ CRIAR MOVIMENTAÇÃO FINANCEIRA com pedido_id
        # Buscar primeiro pedido do embarque
        primeiro_ep = embarque.pedidos_rel.first()
        if not primeiro_ep:
            raise Exception('Erro: Embarque sem pedidos associados')

        # Registrar movimentação
        registrar_pagamento_frete_embarque(
            embarque=embarque,
            valor_pago=valor_pago,
            empresa_pagadora=empresa_pagadora,
            usuario=current_user.nome
        )

        # Atualizar saldo da empresa
        atualizar_saldo(empresa_pagadora.id, valor_pago, 'SUBTRAIR')

        db.session.commit()
        flash(f'Frete pago: R$ {valor_pago:,.2f}{msg_extra}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar frete: {str(e)}', 'danger')

    return redirect(url_for('motochefe.editar_embarque', id=id))
