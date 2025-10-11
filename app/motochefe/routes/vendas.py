"""
Rotas de Vendas - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    PedidoVendaMoto, TituloFinanceiro,
    ClienteMoto, VendedorMoto, EquipeVendasMoto,
    TransportadoraMoto, EmpresaVendaMoto, ModeloMoto, Moto,
    ComissaoVendedor, PedidoVendaAuditoria
)

# ===== EMPRESA VENDA (FATURAMENTO) =====

@motochefe_bp.route('/empresas')
@login_required
@requer_motochefe
def listar_empresas():
    """Lista empresas de faturamento com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = EmpresaVendaMoto.query.filter_by(ativo=True)\
        .order_by(EmpresaVendaMoto.empresa)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/cadastros/empresas/listar.html',
                         empresas=paginacao.items,
                         paginacao=paginacao)

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
    """Lista pedidos de venda com paginação"""
    # Filtros
    faturado = request.args.get('faturado')
    enviado = request.args.get('enviado')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    query = PedidoVendaMoto.query.filter_by(ativo=True)

    if faturado == '1':
        query = query.filter_by(faturado=True)
    elif faturado == '0':
        query = query.filter_by(faturado=False)

    if enviado == '1':
        query = query.filter_by(enviado=True)
    elif enviado == '0':
        query = query.filter_by(enviado=False)

    paginacao = query.order_by(PedidoVendaMoto.data_pedido.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    # Buscar empresas para modal de faturamento
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()

    return render_template('motochefe/vendas/pedidos/listar.html',
                         pedidos=paginacao.items,
                         paginacao=paginacao,
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
    """Adiciona novo pedido com títulos por moto e alocação FIFO"""
    if request.method == 'POST':
        try:
            # VALIDAR número de pedido único
            from app.motochefe.services.numero_pedido_service import validar_numero_pedido_unico
            from app.motochefe.services.pedido_service import criar_pedido_completo
            import json

            numero_pedido = request.form.get('numero_pedido')
            valido, mensagem = validar_numero_pedido_unico(numero_pedido)
            if not valido:
                flash(mensagem, 'danger')
                return redirect(url_for('motochefe.adicionar_pedido'))

            # 1. PROCESSAR ITENS (JSON do form)
            itens_json = request.form.get('itens_json')
            if not itens_json:
                raise Exception('Nenhum item adicionado ao pedido')

            itens = json.loads(itens_json)

            # 2. PROCESSAR PARCELAS (JSON do form)
            parcelas_json = request.form.get('parcelas_json')
            parcelas = []
            prazo_dias = 0
            numero_parcelas = 1

            if parcelas_json:
                parcelas = json.loads(parcelas_json)
                numero_parcelas = len(parcelas) if parcelas else 1

                # VALIDAR: Soma das parcelas deve ser igual ao total
                if parcelas:
                    valor_total_pedido = Decimal(request.form.get('valor_total_pedido', 0))
                    soma_parcelas = sum(Decimal(str(p['valor'])) for p in parcelas)
                    diferenca = abs(valor_total_pedido - soma_parcelas)

                    if diferenca > Decimal('0.02'):  # Tolerância de R$ 0.02
                        raise Exception(
                            f'Soma das parcelas (R$ {soma_parcelas}) difere do total do pedido '
                            f'(R$ {valor_total_pedido}). Diferença: R$ {diferenca}'
                        )
            else:
                # Sem parcelamento: usar prazo simples
                prazo_dias_form = request.form.get('prazo_dias', '0')
                # Garantir que seja 0 se vier vazio, None ou string vazia
                prazo_dias = int(prazo_dias_form) if prazo_dias_form and prazo_dias_form.strip() else 0

            # 3. PREPARAR DADOS DO PEDIDO
            # Validar data_expedicao obrigatória
            data_expedicao = request.form.get('data_expedicao')
            if not data_expedicao:
                raise Exception('Data de Expedição é obrigatória')

            dados_pedido = {
                'numero_pedido': numero_pedido,
                'cliente_id': int(request.form.get('cliente_id')),
                'vendedor_id': int(request.form.get('vendedor_id')),
                'equipe_vendas_id': int(request.form.get('equipe_vendas_id')) if request.form.get('equipe_vendas_id') else None,
                'data_pedido': request.form.get('data_pedido') or date.today(),
                'data_expedicao': data_expedicao,
                'valor_total_pedido': Decimal(request.form.get('valor_total_pedido', 0)),
                'valor_frete_cliente': Decimal(request.form.get('valor_frete_cliente', 0)),
                'forma_pagamento': request.form.get('forma_pagamento'),
                'condicao_pagamento': request.form.get('condicao_pagamento'),
                'prazo_dias': prazo_dias,  # ✅ Usado se sem parcelamento
                'numero_parcelas': numero_parcelas,  # ✅ Quantidade de parcelas
                'parcelas': parcelas,  # ✅ Array de parcelas (se houver)
                'transportadora_id': int(request.form.get('transportadora_id')) if request.form.get('transportadora_id') else None,
                'tipo_frete': request.form.get('tipo_frete'),
                'observacoes': request.form.get('observacoes'),
                'criado_por': current_user.nome
            }

            # 4. CRIAR PEDIDO COMPLETO (novo sistema FIFO)
            # Cria: Pedido + Itens + Reserva Motos + Títulos com FIFO entre parcelas + Títulos a Pagar
            resultado = criar_pedido_completo(dados_pedido, itens)
            pedido = resultado['pedido']

            # 🆕 5. CRIAR REGISTRO DE AUDITORIA
            # Pedido foi criado com ativo=False e status='PENDENTE'
            # Registra ação de INSERÇÃO aguardando confirmação
            auditoria = PedidoVendaAuditoria(
                pedido_id=pedido.id,
                acao='INSERCAO',
                observacao=f'Novo pedido criado via sistema',
                solicitado_por=current_user.nome,
                solicitado_em=datetime.now()
            )
            db.session.add(auditoria)

            db.session.commit()

            # 6. Mensagem de sucesso detalhada
            total_titulos = len(resultado['titulos_financeiros'])
            total_titulos_pagar = len(resultado['titulos_a_pagar'])

            flash(
                f'Pedido "{pedido.numero_pedido}" criado com sucesso! '
                f'{total_titulos} títulos a receber e {total_titulos_pagar} títulos a pagar gerados. '
                f'Aguardando aprovação na tela "Confirmação de Pedidos".',
                'success'
            )
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

    # ✅ TAREFA 1: Data de hoje para campo de data do pedido
    today = date.today().strftime('%Y-%m-%d')

    return render_template('motochefe/vendas/pedidos/form.html',
                         pedido=None,
                         clientes=clientes,
                         vendedores=vendedores,
                         equipes=equipes,
                         transportadoras=transportadoras,
                         modelos=modelos,
                         today=today)


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


@motochefe_bp.route('/pedidos/api/proximo-numero')
@login_required
@requer_motochefe
def api_proximo_numero_pedido():
    """API: Gera próximo número de pedido no formato MC ####"""
    from app.motochefe.services.numero_pedido_service import gerar_proximo_numero_pedido

    numero = gerar_proximo_numero_pedido()
    return jsonify({'numero': numero})


@motochefe_bp.route('/pedidos/<int:id>/faturar', methods=['POST'])
@login_required
@requer_motochefe
def faturar_pedido(id):
    """Fatura pedido: preenche NF, calcula vencimentos, atualiza motos e títulos"""
    from app.motochefe.services.pedido_service import faturar_pedido_completo

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

        # Registrar usuário
        pedido.atualizado_por = current_user.nome

        # FATURAR PEDIDO (novo sistema)
        # Atualiza: Pedido + Motos + Calcula data_vencimento dos títulos
        resultado = faturar_pedido_completo(
            pedido=pedido,
            empresa_id=int(empresa_id),
            numero_nf=numero_nf,
            data_nf=data_nf_obj
        )

        db.session.commit()

        total_titulos = resultado['total_titulos']
        flash(
            f'Pedido faturado com sucesso! NF: {numero_nf} - {total_titulos} títulos liberados para recebimento.',
            'success'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao faturar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_pedidos'))


@motochefe_bp.route('/pedidos/<int:id>/editar-nf', methods=['POST'])
@login_required
@requer_motochefe
def editar_nf_pedido(id):
    """Edita número e data da NF de um pedido já faturado"""
    pedido = PedidoVendaMoto.query.get_or_404(id)

    if not pedido.faturado:
        flash('Pedido ainda não foi faturado', 'warning')
        return redirect(url_for('motochefe.listar_pedidos'))

    try:
        numero_nf = request.form.get('numero_nf')
        data_nf = request.form.get('data_nf')

        if not all([numero_nf, data_nf]):
            raise Exception('Número NF e Data NF são obrigatórios')

        # Validar se novo número de NF já existe (exceto se for o mesmo)
        if numero_nf != pedido.numero_nf:
            nf_existente = PedidoVendaMoto.query.filter_by(numero_nf=numero_nf, ativo=True).first()
            if nf_existente:
                raise Exception(f'Número de NF "{numero_nf}" já está em uso no pedido {nf_existente.numero_pedido}')

        # Atualizar NF
        pedido.numero_nf = numero_nf
        pedido.data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
        pedido.atualizado_por = current_user.nome

        db.session.commit()

        flash(f'NF do pedido {pedido.numero_pedido} atualizada com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao editar NF: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_pedidos'))


@motochefe_bp.route('/pedidos/<int:id>/receber', methods=['POST'])
@login_required
@requer_motochefe
def receber_pedido(id):
    """
    Recebe pagamento por pedido inteiro
    Distribui valor automaticamente pelos títulos na ordem correta
    Pode receber antes ou depois do faturamento
    """
    from app.motochefe.services.titulo_service import receber_por_pedido

    pedido = PedidoVendaMoto.query.get_or_404(id)

    try:
        empresa_id = request.form.get('empresa_recebedora_id')
        valor_recebido = request.form.get('valor_recebido')

        if not all([empresa_id, valor_recebido]):
            raise Exception('Empresa recebedora e valor são obrigatórios')

        valor = Decimal(valor_recebido)
        if valor <= 0:
            raise Exception('Valor deve ser maior que zero')

        empresa = EmpresaVendaMoto.query.get_or_404(int(empresa_id))

        # RECEBER POR PEDIDO (novo sistema)
        # Distribui valor automaticamente pelos títulos na ordem:
        # 1º Movimentação → 2º Montagem → 3º Frete → 4º Venda
        resultado = receber_por_pedido(
            pedido_id=pedido.id,
            valor_recebido=valor,
            empresa_recebedora=empresa,
            usuario=current_user.nome
        )

        db.session.commit()

        total_titulos = len(resultado['titulos_recebidos'])
        total_aplicado = resultado['total_aplicado']
        saldo_restante = resultado['saldo_restante']

        mensagem = (
            f'Recebimento registrado com sucesso! '
            f'{total_titulos} título(s) atualizado(s). '
            f'Valor aplicado: R$ {total_aplicado:,.2f}'
        )

        if saldo_restante > 0:
            mensagem += f' | Saldo não aplicado: R$ {saldo_restante:,.2f} (todos os títulos foram pagos)'

        flash(mensagem, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar recebimento: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_pedidos'))


# ===== TÍTULO FINANCEIRO =====

@motochefe_bp.route('/titulos')
@login_required
@requer_motochefe
def listar_titulos():
    """
    DEPRECATED: Redireciona para contas a receber (novo sistema)
    Antiga lista de títulos foi substituída por visão consolidada com empresa recebedora
    """
    return redirect(url_for('motochefe.listar_contas_a_receber'))


@motochefe_bp.route('/titulos/<int:id>/detalhes')
@login_required
@requer_motochefe
def detalhes_titulo(id):
    """Exibe detalhes completos do título financeiro"""
    titulo = TituloFinanceiro.query.get_or_404(id)
    return render_template('motochefe/vendas/titulos/detalhes.html', titulo=titulo)


# FUNÇÃO REMOVIDA: pagar_titulo()
# Substituída pelo novo sistema de recebimento em titulo_service.receber_titulo()
# O recebimento agora é feito via routes/financeiro.py com MovimentacaoFinanceira


# FUNÇÃO REMOVIDA: gerar_comissao_pedido()
# Substituída por comissao_service.gerar_comissao_moto() (sistema por moto)
# A comissão agora é gerada automaticamente pelo trigger em titulo_service.receber_titulo()


# ===== COMISSÃO VENDEDOR =====

@motochefe_bp.route('/comissoes')
@login_required
@requer_motochefe
def listar_comissoes():
    """Lista comissões por vendedor com paginação"""
    vendedor_id = request.args.get('vendedor_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    query = ComissaoVendedor.query

    if vendedor_id:
        query = query.filter_by(vendedor_id=vendedor_id)
    if status:
        query = query.filter_by(status=status)

    paginacao = query.order_by(ComissaoVendedor.criado_em.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()

    # Buscar empresas para pagamento
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(
        EmpresaVendaMoto.tipo_conta,
        EmpresaVendaMoto.empresa
    ).all()

    return render_template('motochefe/vendas/comissoes/listar.html',
                         comissoes=paginacao.items,
                         paginacao=paginacao,
                         vendedores=vendedores,
                         empresas=empresas)


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
    """
    Registra pagamento de comissão com MovimentacaoFinanceira
    Similar ao pagamento de despesa
    """
    comissao = ComissaoVendedor.query.get_or_404(id)

    if comissao.status == 'PAGO':
        flash('Comissão já foi paga', 'warning')
        return redirect(url_for('motochefe.listar_comissoes'))

    try:
        from app.motochefe.models.cadastro import EmpresaVendaMoto
        from app.motochefe.models.financeiro import MovimentacaoFinanceira
        from app.motochefe.services.empresa_service import atualizar_saldo

        data_pagamento = request.form.get('data_pagamento')
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')

        if not empresa_pagadora_id:
            raise Exception('Selecione a empresa pagadora')

        empresa_pagadora = EmpresaVendaMoto.query.get(empresa_pagadora_id)
        if not empresa_pagadora:
            raise Exception('Empresa pagadora não encontrada')

        data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if isinstance(data_pagamento, str) else (data_pagamento or date.today())

        # 1. CRIAR MOVIMENTAÇÃO FINANCEIRA
        movimentacao = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Comissão',
            valor=comissao.valor_rateado,
            data_movimentacao=data_pag,
            empresa_origem_id=empresa_pagadora.id,
            origem_tipo='Empresa',
            origem_identificacao=empresa_pagadora.empresa,
            empresa_destino_id=None,
            destino_tipo='Vendedor',
            destino_identificacao=comissao.vendedor.vendedor if comissao.vendedor else 'Vendedor',
            comissao_vendedor_id=comissao.id,
            pedido_id=comissao.pedido_id,
            numero_chassi=comissao.numero_chassi,
            descricao=f'Pagamento Comissão Vendedor {comissao.vendedor.vendedor if comissao.vendedor else "-"} - Pedido {comissao.pedido.numero_pedido if comissao.pedido else "-"} - Chassi {comissao.numero_chassi}',
            criado_por=current_user.nome
        )
        db.session.add(movimentacao)

        # 2. ATUALIZAR SALDO DA EMPRESA
        atualizar_saldo(empresa_pagadora.id, comissao.valor_rateado, 'SUBTRAIR')

        # 3. ATUALIZAR COMISSÃO
        comissao.data_pagamento = data_pag
        comissao.empresa_pagadora_id = empresa_pagadora.id
        comissao.status = 'PAGO'
        comissao.atualizado_por = current_user.nome

        db.session.commit()
        flash('Comissão paga com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar comissão: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_comissoes'))


@motochefe_bp.route('/comissoes/pagar-lote', methods=['POST'])
@login_required
@requer_motochefe
def pagar_comissoes_lote():
    """
    Pagamento em lote de comissões
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS (um para cada comissão)
    Similar ao pagamento de títulos em lote
    """
    try:
        import json
        from app.motochefe.models.cadastro import EmpresaVendaMoto
        from app.motochefe.models.financeiro import MovimentacaoFinanceira
        from app.motochefe.services.empresa_service import atualizar_saldo

        # Receber dados do form
        comissoes_json = request.form.get('comissoes_selecionadas')
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')
        data_pagamento = request.form.get('data_pagamento')

        if not comissoes_json:
            raise Exception('Nenhuma comissão selecionada')

        if not empresa_pagadora_id:
            raise Exception('Selecione a empresa pagadora')

        # Parse IDs
        comissao_ids = json.loads(comissoes_json)
        if not comissao_ids:
            raise Exception('Lista de comissões vazia')

        # Buscar empresa
        empresa_pagadora = EmpresaVendaMoto.query.get(empresa_pagadora_id)
        if not empresa_pagadora:
            raise Exception('Empresa pagadora não encontrada')

        data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if isinstance(data_pagamento, str) else (data_pagamento or date.today())

        # Buscar comissões
        comissoes = ComissaoVendedor.query.filter(ComissaoVendedor.id.in_(comissao_ids)).all()

        if not comissoes:
            raise Exception('Comissões não encontradas')

        # Calcular total
        valor_total = sum((c.valor_rateado for c in comissoes), Decimal("0"))

        # 1. CRIAR MOVIMENTAÇÃO PAI
        descricao_pai = f'Pagamento Lote {len(comissoes)} comissão(ões)'

        movimentacao_pai = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Lote Comissão',
            valor=valor_total,
            data_movimentacao=data_pag,
            empresa_origem_id=empresa_pagadora.id,
            origem_tipo='Empresa',
            origem_identificacao=empresa_pagadora.empresa,
            empresa_destino_id=None,
            destino_tipo='Vendedores',
            destino_identificacao='Comissões',
            descricao=descricao_pai,
            observacoes=f'Lote com {len(comissoes)} comissão(ões)',
            criado_por=current_user.nome
        )
        db.session.add(movimentacao_pai)
        db.session.flush()

        # 2. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR COMISSÕES
        for comissao in comissoes:
            # Validar se já foi paga
            if comissao.status == 'PAGO':
                raise Exception(f'Comissão ID {comissao.id} já foi paga')

            # Movimentação filha
            movimentacao_filha = MovimentacaoFinanceira(
                tipo='PAGAMENTO',
                categoria='Comissão',
                valor=comissao.valor_rateado,
                data_movimentacao=data_pag,
                empresa_origem_id=empresa_pagadora.id,
                origem_tipo='Empresa',
                origem_identificacao=empresa_pagadora.empresa,
                empresa_destino_id=None,
                destino_tipo='Vendedor',
                destino_identificacao=comissao.vendedor.vendedor if comissao.vendedor else 'Vendedor',
                comissao_vendedor_id=comissao.id,
                pedido_id=comissao.pedido_id,
                numero_chassi=comissao.numero_chassi,
                descricao=f'Comissão Vendedor {comissao.vendedor.vendedor if comissao.vendedor else "-"} - Pedido {comissao.pedido.numero_pedido if comissao.pedido else "-"}',
                movimentacao_origem_id=movimentacao_pai.id,
                criado_por=current_user.nome
            )
            db.session.add(movimentacao_filha)

            # Atualizar comissão
            comissao.data_pagamento = data_pag
            comissao.empresa_pagadora_id = empresa_pagadora.id
            comissao.lote_pagamento_id = movimentacao_pai.id
            comissao.status = 'PAGO'
            comissao.atualizado_por = current_user.nome

        # 3. ATUALIZAR SALDO DA EMPRESA
        atualizar_saldo(empresa_pagadora.id, valor_total, 'SUBTRAIR')

        db.session.commit()
        flash(f'{len(comissoes)} comissão(ões) paga(s) com sucesso! Total: R$ {valor_total:.2f}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar comissões em lote: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_comissoes'))


# ===== APIs DE CASCATA =====

@motochefe_bp.route('/api/vendedores-por-equipe')
@login_required
@requer_motochefe
def api_vendedores_por_equipe():
    """API: Retorna vendedores de uma equipe"""
    equipe_id = request.args.get('equipe_id', type=int)

    if not equipe_id:
        return jsonify([])

    vendedores = VendedorMoto.query.filter_by(
        equipe_vendas_id=equipe_id,
        ativo=True
    ).order_by(VendedorMoto.vendedor).all()

    return jsonify([{
        'id': v.id,
        'vendedor': v.vendedor
    } for v in vendedores])


@motochefe_bp.route('/api/clientes-por-vendedor')
@login_required
@requer_motochefe
def api_clientes_por_vendedor():
    """API: Retorna clientes de um vendedor"""
    vendedor_id = request.args.get('vendedor_id', type=int)

    if not vendedor_id:
        return jsonify([])

    clientes = ClienteMoto.query.filter_by(
        vendedor_id=vendedor_id,
        ativo=True
    ).order_by(ClienteMoto.cliente).all()

    return jsonify([{
        'id': c.id,
        'cliente': c.cliente,
        'cnpj': c.cnpj_cliente,
        'crossdocking': c.crossdocking
    } for c in clientes])


@motochefe_bp.route('/api/cores-disponiveis')
@login_required
@requer_motochefe
def api_cores_disponiveis():
    """API: Retorna cores disponíveis de um modelo com quantidade"""
    modelo_id = request.args.get('modelo_id', type=int)

    if not modelo_id:
        return jsonify([])

    from sqlalchemy import func

    cores = db.session.query(
        Moto.cor,
        func.count(Moto.numero_chassi).label('quantidade')
    ).filter(
        Moto.modelo_id == modelo_id,
        Moto.status == 'DISPONIVEL',
        Moto.reservado == False,
        Moto.ativo == True
    ).group_by(Moto.cor).all()

    return jsonify([{
        'cor': c.cor,
        'quantidade': c.quantidade,
        'label': f'{c.cor} ({c.quantidade} un)'
    } for c in cores])


# ===== SUBSTITUIÇÃO DE MOTOS =====

@motochefe_bp.route('/pedidos/<int:pedido_id>/motos-disponiveis/<string:chassi_atual>')
@login_required
@requer_motochefe
def api_motos_disponiveis_substituicao(pedido_id, chassi_atual):
    """API: Retorna motos disponíveis agrupadas por prioridade para substituição"""
    from app.motochefe.services.substituicao_moto_service import buscar_motos_disponiveis_agrupadas

    # Buscar moto atual
    moto_atual = Moto.query.get_or_404(chassi_atual)

    # Buscar motos agrupadas
    grupos = buscar_motos_disponiveis_agrupadas(
        modelo_id_referencia=moto_atual.modelo_id,
        cor_referencia=moto_atual.cor
    )

    # Converter para JSON
    resultado = {}
    for chave, motos in grupos.items():
        resultado[chave] = [{
            'chassi': m.numero_chassi,
            'motor': m.numero_motor,
            'modelo': m.modelo.nome_modelo,
            'modelo_id': m.modelo_id,
            'potencia': m.modelo.potencia_motor,
            'cor': m.cor,
            'preco_tabela': float(m.modelo.preco_tabela),
            'ano': m.ano_fabricacao,
            'data_entrada': m.data_entrada.strftime('%d/%m/%Y') if m.data_entrada else None
        } for m in motos]

    return jsonify(resultado)


@motochefe_bp.route('/pedidos/<int:pedido_id>/substituir-moto', methods=['POST'])
@login_required
@requer_motochefe
def substituir_moto(pedido_id):
    """Substitui uma moto em um pedido"""
    from app.motochefe.services.substituicao_moto_service import substituir_moto_pedido

    try:
        from decimal import Decimal

        chassi_antigo = request.form.get('chassi_antigo')
        chassi_novo = request.form.get('chassi_novo')
        preco_novo_str = request.form.get('preco_novo')
        motivo = request.form.get('motivo')  # 'AVARIA' ou 'OUTROS'
        observacao = request.form.get('observacao', '')

        if not all([chassi_antigo, chassi_novo, preco_novo_str, motivo]):
            raise Exception('Dados incompletos para substituição')

        # Converter preço para Decimal
        try:
            preco_novo = Decimal(str(preco_novo_str))
        except Exception as e:
            raise Exception(f'Preço da moto nova inválido: {e}')

        # Executar substituição
        resultado = substituir_moto_pedido(
            pedido_id=pedido_id,
            chassi_antigo=chassi_antigo,
            chassi_novo=chassi_novo,
            preco_novo=preco_novo,
            motivo=motivo,
            observacao=observacao,
            usuario=current_user.nome
        )

        # Montar mensagem de sucesso
        mensagem = f'Moto substituída com sucesso! '
        mensagem += f'Chassi antigo: {chassi_antigo} → Chassi novo: {chassi_novo}'

        if resultado['resultado_ajuste_titulo']:
            mensagem += f" | {resultado['resultado_ajuste_titulo']['mensagem']}"

        flash(mensagem, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao substituir moto: {str(e)}', 'danger')

    return redirect(url_for('motochefe.detalhes_pedido', id=pedido_id))


# ===== CONFIRMAÇÃO DE PEDIDOS (APROVAÇÃO/REJEIÇÃO) =====

@motochefe_bp.route('/confirmacao-pedidos')
@login_required
@requer_motochefe
def confirmacao_pedidos():
    """
    Lista todas as ações pendentes de confirmação
    - INSERÇÃO: Novos pedidos aguardando aprovação
    - CANCELAMENTO: Pedidos solicitados para cancelamento
    """
    # Buscar todas as auditorias pendentes
    pendentes = PedidoVendaAuditoria.query\
        .filter_by(confirmado=False, rejeitado=False)\
        .join(PedidoVendaMoto)\
        .order_by(PedidoVendaAuditoria.solicitado_em.desc())\
        .all()

    return render_template('motochefe/vendas/pedidos/confirmacao_pedidos.html',
                         pendentes=pendentes)


@motochefe_bp.route('/pedidos/<int:id>/solicitar-cancelamento', methods=['POST'])
@login_required
@requer_motochefe
def solicitar_cancelamento_pedido(id):
    """
    Solicita cancelamento de um pedido
    IMEDIATAMENTE altera: ativo=False, status='CANCELADO'
    Gestor pode aprovar (confirma) ou rejeitar (reverte)
    """
    pedido = PedidoVendaMoto.query.get_or_404(id)

    try:
        observacao = request.form.get('observacao', '').strip()

        if not observacao:
            raise Exception('Motivo do cancelamento é obrigatório')

        # Validações
        if pedido.status == 'CANCELADO':
            raise Exception('Pedido já está cancelado')

        if pedido.faturado:
            raise Exception('Pedido faturado não pode ser cancelado. Entre em contato com financeiro.')

        # 🆕 CANCELAMENTO IMEDIATO
        # Altera AGORA para não aparecer na lista
        pedido.ativo = False
        pedido.status = 'CANCELADO'
        pedido.atualizado_por = current_user.nome

        # Criar registro de auditoria PENDENTE
        auditoria = PedidoVendaAuditoria(
            pedido_id=pedido.id,
            acao='CANCELAMENTO',
            observacao=observacao,
            solicitado_por=current_user.nome,
            solicitado_em=datetime.now()
        )
        db.session.add(auditoria)

        db.session.commit()

        flash(
            f'Cancelamento do pedido "{pedido.numero_pedido}" solicitado com sucesso! '
            f'Aguardando confirmação na tela "Confirmação de Pedidos".',
            'warning'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao solicitar cancelamento: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_pedidos'))


@motochefe_bp.route('/pedidos/auditoria/<int:auditoria_id>/aprovar', methods=['POST'])
@login_required
@requer_motochefe
def aprovar_acao_pedido(auditoria_id):
    """
    Aprova uma ação pendente (INSERÇÃO ou CANCELAMENTO)

    INSERÇÃO: ativo=False → ativo=True, status='PENDENTE' → status='APROVADO'
    CANCELAMENTO: mantém ativo=False, status='CANCELADO' (já aplicado)
    """
    auditoria = PedidoVendaAuditoria.query.get_or_404(auditoria_id)

    try:
        # Validações
        if auditoria.confirmado:
            raise Exception('Ação já foi aprovada')

        if auditoria.rejeitado:
            raise Exception('Ação já foi rejeitada')

        pedido = auditoria.pedido

        # Processar aprovação conforme tipo de ação
        if auditoria.acao == 'INSERCAO':
            # APROVAR INSERÇÃO: Ativar pedido
            pedido.ativo = True
            pedido.status = 'APROVADO'
            pedido.atualizado_por = current_user.nome

            mensagem = f'Pedido "{pedido.numero_pedido}" aprovado com sucesso! Agora aparece na lista de pedidos.'

        elif auditoria.acao == 'CANCELAMENTO':
            # APROVAR CANCELAMENTO: Pedido já está ativo=False, status='CANCELADO'
            # Apenas confirma a auditoria
            mensagem = f'Cancelamento do pedido "{pedido.numero_pedido}" aprovado com sucesso!'

        else:
            raise Exception(f'Ação desconhecida: {auditoria.acao}')

        # Confirmar auditoria
        auditoria.confirmado = True
        auditoria.confirmado_por = current_user.nome
        auditoria.confirmado_em = datetime.now()

        db.session.commit()

        flash(mensagem, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar ação: {str(e)}', 'danger')

    return redirect(url_for('motochefe.confirmacao_pedidos'))


@motochefe_bp.route('/pedidos/auditoria/<int:auditoria_id>/rejeitar', methods=['POST'])
@login_required
@requer_motochefe
def rejeitar_acao_pedido(auditoria_id):
    """
    Rejeita uma ação pendente (INSERÇÃO ou CANCELAMENTO)

    INSERÇÃO: mantém ativo=False, status='PENDENTE' → status='REJEITADO'
    CANCELAMENTO: REVERTE para ativo=True, status='APROVADO' (volta ao normal)
    """
    auditoria = PedidoVendaAuditoria.query.get_or_404(auditoria_id)

    try:
        motivo_rejeicao = request.form.get('motivo_rejeicao', '').strip()

        if not motivo_rejeicao:
            raise Exception('Motivo da rejeição é obrigatório')

        # Validações
        if auditoria.confirmado:
            raise Exception('Ação já foi aprovada')

        if auditoria.rejeitado:
            raise Exception('Ação já foi rejeitada')

        pedido = auditoria.pedido

        # Processar rejeição conforme tipo de ação
        if auditoria.acao == 'INSERCAO':
            # REJEITAR INSERÇÃO: Mantém inativo e muda status para REJEITADO
            pedido.status = 'REJEITADO'
            pedido.atualizado_por = current_user.nome

            mensagem = f'Pedido "{pedido.numero_pedido}" rejeitado. Permanece inativo no sistema.'

        elif auditoria.acao == 'CANCELAMENTO':
            # REJEITAR CANCELAMENTO: REVERTE para estado ativo
            pedido.ativo = True
            pedido.status = 'APROVADO'
            pedido.atualizado_por = current_user.nome

            mensagem = f'Cancelamento do pedido "{pedido.numero_pedido}" rejeitado. Pedido voltou ao normal!'

        else:
            raise Exception(f'Ação desconhecida: {auditoria.acao}')

        # Registrar rejeição
        auditoria.rejeitado = True
        auditoria.motivo_rejeicao = motivo_rejeicao
        auditoria.confirmado_por = current_user.nome
        auditoria.confirmado_em = datetime.now()

        db.session.commit()

        flash(mensagem, 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar ação: {str(e)}', 'danger')

    return redirect(url_for('motochefe.confirmacao_pedidos'))


@motochefe_bp.route('/confirmacao-pedidos/historico')
@login_required
@requer_motochefe
def historico_confirmacoes():
    """
    Lista histórico completo de confirmações/rejeições
    Mostra todas as auditorias processadas (confirmadas ou rejeitadas)
    com campos completos de auditoria
    """
    from sqlalchemy import desc, or_

    # Filtros
    acao_filtro = request.args.get('acao', '')
    status_filtro = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Query base: apenas auditorias processadas (confirmadas ou rejeitadas)
    query = PedidoVendaAuditoria.query.filter(
        or_(
            PedidoVendaAuditoria.confirmado == True,
            PedidoVendaAuditoria.rejeitado == True
        )
    ).join(PedidoVendaMoto)

    # Aplicar filtros
    if acao_filtro:
        query = query.filter(PedidoVendaAuditoria.acao == acao_filtro)

    if status_filtro == 'APROVADO':
        query = query.filter(PedidoVendaAuditoria.confirmado == True)
    elif status_filtro == 'REJEITADO':
        query = query.filter(PedidoVendaAuditoria.rejeitado == True)

    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(PedidoVendaAuditoria.confirmado_em >= data_inicio_dt)
        except ValueError:
            pass

    if data_fim:
        try:
            from datetime import timedelta
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(PedidoVendaAuditoria.confirmado_em < data_fim_dt)
        except ValueError:
            pass

    # Ordenar por data de confirmação (mais recentes primeiro)
    query = query.order_by(desc(PedidoVendaAuditoria.confirmado_em))

    # Paginar
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/vendas/pedidos/historico_confirmacoes.html',
                         historico=paginacao.items,
                         paginacao=paginacao,
                         acao_filtro=acao_filtro,
                         status_filtro=status_filtro,
                         data_inicio=data_inicio,
                         data_fim=data_fim)


# ===== IMPRESSÃO DE PEDIDOS =====

@motochefe_bp.route('/pedidos/<int:id>/imprimir')
@login_required
@requer_motochefe
def imprimir_pedido(id):
    """
    Exibe pedido formatado para impressão A4
    Marca pedido como impresso no primeiro acesso
    """
    pedido = PedidoVendaMoto.query.get_or_404(id)

    # Marcar como impresso na primeira impressão
    if not pedido.impresso:
        pedido.impresso = True
        pedido.impresso_por = current_user.nome
        pedido.impresso_em = datetime.now()
        db.session.commit()

    return render_template('motochefe/vendas/pedidos/imprimir.html', pedido=pedido)
