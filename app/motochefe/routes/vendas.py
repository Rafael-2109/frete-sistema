"""
Rotas de Vendas - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date, timedelta

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    PedidoVendaMoto, PedidoVendaMotoItem, TituloFinanceiro,
    ClienteMoto, VendedorMoto, EquipeVendasMoto,
    TransportadoraMoto, EmpresaVendaMoto, ModeloMoto, Moto,
    CustosOperacionais, ComissaoVendedor
)

# ===== EMPRESA VENDA (FATURAMENTO) =====

@motochefe_bp.route('/empresas')
@login_required
@requer_motochefe
def listar_empresas():
    """Lista empresas de faturamento"""
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()
    return render_template('motochefe/cadastros/empresas/listar.html', empresas=empresas)

@motochefe_bp.route('/empresas/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_empresa():
    """Adiciona nova empresa"""
    if request.method == 'POST':
        cnpj = request.form.get('cnpj_empresa')
        empresa = request.form.get('empresa')

        if not cnpj or not empresa:
            flash('CNPJ e Nome são obrigatórios', 'danger')
            return redirect(url_for('motochefe.adicionar_empresa'))

        # Verificar duplicidade
        existe = EmpresaVendaMoto.query.filter_by(cnpj_empresa=cnpj).first()
        if existe:
            flash('CNPJ já cadastrado', 'warning')
            return redirect(url_for('motochefe.listar_empresas'))

        empresa_obj = EmpresaVendaMoto(
            cnpj_empresa=cnpj,
            empresa=empresa,
            chave_pix=request.form.get('chave_pix'),
            banco=request.form.get('banco'),
            cod_banco=request.form.get('cod_banco'),
            agencia=request.form.get('agencia'),
            conta=request.form.get('conta'),
            criado_por=current_user.nome
        )
        db.session.add(empresa_obj)
        db.session.commit()

        flash(f'Empresa "{empresa}" cadastrada com sucesso!', 'success')

        # Se veio de modal via AJAX, retorna JSON
        if request.form.get('from_modal'):
            return jsonify({'success': True, 'id': empresa_obj.id, 'nome': empresa_obj.empresa})

        return redirect(url_for('motochefe.listar_empresas'))

    return render_template('motochefe/cadastros/empresas/form.html', empresa=None)

@motochefe_bp.route('/empresas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_empresa(id):
    """Edita empresa existente"""
    empresa = EmpresaVendaMoto.query.get_or_404(id)

    if request.method == 'POST':
        empresa.cnpj_empresa = request.form.get('cnpj_empresa')
        empresa.empresa = request.form.get('empresa')
        empresa.chave_pix = request.form.get('chave_pix')
        empresa.banco = request.form.get('banco')
        empresa.cod_banco = request.form.get('cod_banco')
        empresa.agencia = request.form.get('agencia')
        empresa.conta = request.form.get('conta')
        empresa.atualizado_por = current_user.nome

        db.session.commit()
        flash('Empresa atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_empresas'))

    return render_template('motochefe/cadastros/empresas/form.html', empresa=empresa)

@motochefe_bp.route('/empresas/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_empresa(id):
    """Remove (desativa) empresa"""
    empresa = EmpresaVendaMoto.query.get_or_404(id)
    empresa.ativo = False
    empresa.atualizado_por = current_user.nome
    db.session.commit()

    flash('Empresa removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_empresas'))


# ===== PEDIDO VENDA =====

@motochefe_bp.route('/pedidos')
@login_required
@requer_motochefe
def listar_pedidos():
    """Lista pedidos de venda"""
    # Filtros
    faturado = request.args.get('faturado')
    enviado = request.args.get('enviado')

    query = PedidoVendaMoto.query.filter_by(ativo=True)

    if faturado == '1':
        query = query.filter_by(faturado=True)
    elif faturado == '0':
        query = query.filter_by(faturado=False)

    if enviado == '1':
        query = query.filter_by(enviado=True)
    elif enviado == '0':
        query = query.filter_by(enviado=False)

    pedidos = query.order_by(PedidoVendaMoto.data_pedido.desc()).all()

    # Buscar empresas para modal de faturamento
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()

    return render_template('motochefe/vendas/pedidos/listar.html',
                         pedidos=pedidos,
                         empresas=empresas)


@motochefe_bp.route('/pedidos/<int:id>/detalhes')
@login_required
@requer_motochefe
def detalhes_pedido(id):
    """Exibe detalhes completos do pedido com itens e montagens"""
    pedido = PedidoVendaMoto.query.get_or_404(id)
    return render_template('motochefe/vendas/pedidos/detalhes.html', pedido=pedido)


@motochefe_bp.route('/pedidos/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_pedido():
    """Adiciona novo pedido com parcelamento e alocação FIFO"""
    if request.method == 'POST':
        try:
            # 1. CRIAR PEDIDO
            pedido = PedidoVendaMoto(
                numero_pedido=request.form.get('numero_pedido'),
                cliente_id=int(request.form.get('cliente_id')),
                vendedor_id=int(request.form.get('vendedor_id')),
                equipe_vendas_id=int(request.form.get('equipe_vendas_id')) if request.form.get('equipe_vendas_id') else None,
                data_pedido=request.form.get('data_pedido') or date.today(),
                data_expedicao=request.form.get('data_expedicao') or None,
                valor_total_pedido=Decimal(request.form.get('valor_total_pedido', 0)),
                valor_frete_cliente=Decimal(request.form.get('valor_frete_cliente', 0)),
                forma_pagamento=request.form.get('forma_pagamento'),
                condicao_pagamento=request.form.get('condicao_pagamento'),
                transportadora_id=int(request.form.get('transportadora_id')) if request.form.get('transportadora_id') else None,
                tipo_frete=request.form.get('tipo_frete'),
                responsavel_movimentacao=request.form.get('responsavel_movimentacao'),
                observacoes=request.form.get('observacoes'),
                criado_por=current_user.nome
            )
            db.session.add(pedido)
            db.session.flush()  # Pega ID sem commit

            # 2. PROCESSAR ITENS (JSON do form)
            import json
            itens_json = request.form.get('itens_json')
            if not itens_json:
                raise Exception('Nenhum item adicionado ao pedido')

            itens = json.loads(itens_json)

            for item_data in itens:
                modelo_id = item_data['modelo_id']
                cor = item_data['cor']
                quantidade = int(item_data['quantidade'])
                preco_venda = Decimal(item_data['preco_venda'])
                montagem = item_data.get('montagem', False)
                valor_montagem = Decimal(item_data.get('valor_montagem', 0))

                # 3. ALOCAR CHASSI VIA FIFO
                motos_disponiveis = Moto.query.filter_by(
                    modelo_id=modelo_id,
                    cor=cor,
                    status='DISPONIVEL',
                    reservado=False,
                    ativo=True
                ).order_by(Moto.data_entrada.asc()).limit(quantidade).all()

                if len(motos_disponiveis) < quantidade:
                    raise Exception(f'Estoque insuficiente para modelo ID {modelo_id} cor {cor}. Disponível: {len(motos_disponiveis)}, Solicitado: {quantidade}')

                # 4. CRIAR ITENS E RESERVAR MOTOS
                for moto in motos_disponiveis:
                    item = PedidoVendaMotoItem(
                        pedido_id=pedido.id,
                        numero_chassi=moto.numero_chassi,
                        preco_venda=preco_venda,
                        montagem_contratada=montagem,
                        valor_montagem=valor_montagem if montagem else 0,
                        criado_por=current_user.nome
                    )
                    db.session.add(item)

                    # ATUALIZAR STATUS DA MOTO
                    moto.status = 'RESERVADA'
                    moto.reservado = True

            # 5. CRIAR TÍTULOS FINANCEIROS (JSON das parcelas)
            parcelas_json = request.form.get('parcelas_json')
            if parcelas_json:
                parcelas = json.loads(parcelas_json)

                for parcela_data in parcelas:
                    titulo = TituloFinanceiro(
                        pedido_id=pedido.id,
                        numero_parcela=parcela_data['numero'],
                        total_parcelas=len(parcelas),
                        valor_parcela=Decimal(parcela_data['valor']),
                        prazo_dias=int(parcela_data['prazo_dias']),
                        data_vencimento=None,  # Calculado no faturamento
                        status='RASCUNHO'  # Muda para ABERTO no faturamento
                    )
                    db.session.add(titulo)

            db.session.commit()
            flash(f'Pedido "{pedido.numero_pedido}" criado com sucesso!', 'success')
            return redirect(url_for('motochefe.listar_pedidos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar pedido: {str(e)}', 'danger')
            return redirect(url_for('motochefe.adicionar_pedido'))

    # GET - Carregar dados para o form
    clientes = ClienteMoto.query.filter_by(ativo=True).order_by(ClienteMoto.cliente).all()
    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).order_by(EquipeVendasMoto.equipe_vendas).all()
    transportadoras = TransportadoraMoto.query.filter_by(ativo=True).order_by(TransportadoraMoto.transportadora).all()
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()

    return render_template('motochefe/vendas/pedidos/form.html',
                         pedido=None,
                         clientes=clientes,
                         vendedores=vendedores,
                         equipes=equipes,
                         transportadoras=transportadoras,
                         modelos=modelos)


@motochefe_bp.route('/pedidos/api/estoque-modelo')
@login_required
@requer_motochefe
def api_estoque_modelo():
    """API: Retorna estoque disponível por modelo/cor"""
    modelo_id = request.args.get('modelo_id', type=int)

    if not modelo_id:
        return jsonify([])

    # Agrupa por cor e conta quantidade disponível
    from sqlalchemy import func
    estoque = db.session.query(
        Moto.cor,
        func.count(Moto.numero_chassi).label('quantidade')
    ).filter(
        Moto.modelo_id == modelo_id,
        Moto.status == 'DISPONIVEL',
        Moto.reservado == False,
        Moto.ativo == True
    ).group_by(Moto.cor).all()

    return jsonify([{
        'cor': e.cor,
        'quantidade': e.quantidade
    } for e in estoque])


@motochefe_bp.route('/pedidos/<int:id>/faturar', methods=['POST'])
@login_required
@requer_motochefe
def faturar_pedido(id):
    """Fatura pedido: preenche NF, calcula vencimentos, atualiza motos"""
    pedido = PedidoVendaMoto.query.get_or_404(id)

    if pedido.faturado:
        flash('Pedido já foi faturado', 'warning')
        return redirect(url_for('motochefe.listar_pedidos'))

    try:
        empresa_id = request.form.get('empresa_venda_id')
        numero_nf = request.form.get('numero_nf')
        data_nf = request.form.get('data_nf')

        if not all([empresa_id, numero_nf, data_nf]):
            raise Exception('Empresa, Número NF e Data NF são obrigatórios')

        # Converter data
        data_nf_obj = datetime.strptime(data_nf, '%Y-%m-%d').date()

        # ATUALIZAR PEDIDO
        pedido.faturado = True
        pedido.numero_nf = numero_nf
        pedido.data_nf = data_nf_obj
        pedido.empresa_venda_id = int(empresa_id)
        pedido.atualizado_por = current_user.nome

        # ATUALIZAR MOTOS (status VENDIDA)
        for item in pedido.itens:
            moto = item.moto
            moto.status = 'VENDIDA'

        # ATUALIZAR TÍTULOS (calcular vencimentos)
        for titulo in pedido.titulos:
            if titulo.prazo_dias:
                titulo.data_vencimento = data_nf_obj + timedelta(days=titulo.prazo_dias)
            titulo.status = 'ABERTO'  # Muda de RASCUNHO para ABERTO

        db.session.commit()
        flash(f'Pedido faturado com sucesso! NF: {numero_nf}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao faturar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_pedidos'))


# ===== TÍTULO FINANCEIRO =====

@motochefe_bp.route('/titulos')
@login_required
@requer_motochefe
def listar_titulos():
    """Lista títulos financeiros"""
    status = request.args.get('status')

    query = TituloFinanceiro.query

    if status:
        query = query.filter_by(status=status)

    titulos = query.join(PedidoVendaMoto).filter(
        PedidoVendaMoto.faturado == True  # Só mostra títulos de pedidos faturados
    ).order_by(TituloFinanceiro.data_vencimento.asc()).all()

    return render_template('motochefe/vendas/titulos/listar.html', titulos=titulos)


@motochefe_bp.route('/titulos/<int:id>/detalhes')
@login_required
@requer_motochefe
def detalhes_titulo(id):
    """Exibe detalhes completos do título financeiro"""
    titulo = TituloFinanceiro.query.get_or_404(id)
    return render_template('motochefe/vendas/titulos/detalhes.html', titulo=titulo)


@motochefe_bp.route('/titulos/<int:id>/pagar', methods=['POST'])
@login_required
@requer_motochefe
def pagar_titulo(id):
    """Marca título como pago e verifica se gera comissão"""
    titulo = TituloFinanceiro.query.get_or_404(id)

    if titulo.status == 'PAGO':
        flash('Título já foi pago', 'warning')
        return redirect(url_for('motochefe.listar_titulos'))

    try:
        valor_recebido = request.form.get('valor_recebido')
        data_recebimento = request.form.get('data_recebimento') or date.today()

        titulo.valor_recebido = Decimal(valor_recebido)
        titulo.data_recebimento = datetime.strptime(data_recebimento, '%Y-%m-%d').date() if isinstance(data_recebimento, str) else data_recebimento
        titulo.status = 'PAGO'

        # VERIFICAR SE TODOS OS TÍTULOS DO PEDIDO FORAM PAGOS
        pedido = titulo.pedido
        todos_pagos = all(t.status == 'PAGO' for t in pedido.titulos)

        if todos_pagos:
            # GERAR COMISSÃO
            gerar_comissao_pedido(pedido)
            flash(f'Título pago! Pedido totalmente quitado - Comissões geradas.', 'success')
        else:
            flash('Título pago com sucesso!', 'success')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar título: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_titulos'))


def gerar_comissao_pedido(pedido):
    """Gera comissão para todos vendedores da equipe quando pedido quitado"""
    # 1. Buscar valores de comissão
    custos = CustosOperacionais.get_custos_vigentes()
    if not custos:
        raise Exception('Custos operacionais não configurados')

    comissao_fixa = custos.valor_comissao_fixa

    # 2. Calcular excedente (soma de todos itens)
    excedente = sum(item.excedente_tabela for item in pedido.itens)

    # 3. Total da comissão
    valor_total = comissao_fixa + excedente

    # 4. Buscar TODOS vendedores da equipe
    if not pedido.equipe_vendas_id:
        # Se não tem equipe, comissão só para o vendedor
        vendedores_equipe = [pedido.vendedor]
    else:
        vendedores_equipe = VendedorMoto.query.filter_by(
            equipe_vendas_id=pedido.equipe_vendas_id,
            ativo=True
        ).all()

    qtd_vendedores = len(vendedores_equipe)
    valor_por_vendedor = valor_total / qtd_vendedores

    # 5. Criar 1 REGISTRO PARA CADA VENDEDOR
    for vendedor in vendedores_equipe:
        comissao = ComissaoVendedor(
            pedido_id=pedido.id,
            vendedor_id=vendedor.id,
            valor_comissao_fixa=comissao_fixa / qtd_vendedores,
            valor_excedente=excedente / qtd_vendedores,
            valor_total_comissao=valor_por_vendedor,
            qtd_vendedores_equipe=qtd_vendedores,
            valor_rateado=valor_por_vendedor,
            status='PENDENTE'
        )
        db.session.add(comissao)


# ===== COMISSÃO VENDEDOR =====

@motochefe_bp.route('/comissoes')
@login_required
@requer_motochefe
def listar_comissoes():
    """Lista comissões por vendedor"""
    vendedor_id = request.args.get('vendedor_id', type=int)
    status = request.args.get('status')

    query = ComissaoVendedor.query

    if vendedor_id:
        query = query.filter_by(vendedor_id=vendedor_id)
    if status:
        query = query.filter_by(status=status)

    comissoes = query.order_by(ComissaoVendedor.criado_em.desc()).all()

    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()

    return render_template('motochefe/vendas/comissoes/listar.html',
                         comissoes=comissoes,
                         vendedores=vendedores)


@motochefe_bp.route('/comissoes/<int:id>/detalhes')
@login_required
@requer_motochefe
def detalhes_comissao(id):
    """Exibe detalhes completos da comissão"""
    comissao = ComissaoVendedor.query.get_or_404(id)
    return render_template('motochefe/vendas/comissoes/detalhes.html', comissao=comissao)


@motochefe_bp.route('/comissoes/<int:id>/pagar', methods=['POST'])
@login_required
@requer_motochefe
def pagar_comissao(id):
    """Marca comissão como paga"""
    comissao = ComissaoVendedor.query.get_or_404(id)

    if comissao.status == 'PAGO':
        flash('Comissão já foi paga', 'warning')
        return redirect(url_for('motochefe.listar_comissoes'))

    try:
        data_pagamento = request.form.get('data_pagamento') or date.today()

        comissao.data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if isinstance(data_pagamento, str) else data_pagamento
        comissao.status = 'PAGO'
        comissao.atualizado_por = current_user.nome

        db.session.commit()
        flash('Comissão paga com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar comissão: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_comissoes'))
