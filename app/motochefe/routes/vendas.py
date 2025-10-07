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

            # 1. PREPARAR DADOS DO PEDIDO
            dados_pedido = {
                'numero_pedido': numero_pedido,
                'cliente_id': int(request.form.get('cliente_id')),
                'vendedor_id': int(request.form.get('vendedor_id')),
                'equipe_vendas_id': int(request.form.get('equipe_vendas_id')) if request.form.get('equipe_vendas_id') else None,
                'data_pedido': request.form.get('data_pedido') or date.today(),
                'data_expedicao': request.form.get('data_expedicao') or None,
                'valor_total_pedido': Decimal(request.form.get('valor_total_pedido', 0)),
                'valor_frete_cliente': Decimal(request.form.get('valor_frete_cliente', 0)),
                'forma_pagamento': request.form.get('forma_pagamento'),
                'condicao_pagamento': request.form.get('condicao_pagamento'),
                'transportadora_id': int(request.form.get('transportadora_id')) if request.form.get('transportadora_id') else None,
                'tipo_frete': request.form.get('tipo_frete'),
                'observacoes': request.form.get('observacoes'),
                'criado_por': current_user.nome
            }

            # 2. PROCESSAR ITENS (JSON do form)
            itens_json = request.form.get('itens_json')
            if not itens_json:
                raise Exception('Nenhum item adicionado ao pedido')

            itens = json.loads(itens_json)

            # 3. CRIAR PEDIDO COMPLETO (novo sistema)
            # Cria: Pedido + Itens + Reserva Motos + 4 Títulos por Moto + Títulos a Pagar
            resultado = criar_pedido_completo(dados_pedido, itens)

            db.session.commit()

            # 4. Mensagem de sucesso detalhada
            pedido = resultado['pedido']
            total_titulos = len(resultado['titulos_financeiros'])
            total_titulos_pagar = len(resultado['titulos_a_pagar'])

            flash(
                f'Pedido "{pedido.numero_pedido}" criado com sucesso! '
                f'{total_titulos} títulos a receber e {total_titulos_pagar} títulos a pagar gerados.',
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
        # Atualiza: Pedido + Motos + Títulos (RASCUNHO → ABERTO)
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

    return render_template('motochefe/vendas/comissoes/listar.html',
                         comissoes=paginacao.items,
                         paginacao=paginacao,
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
