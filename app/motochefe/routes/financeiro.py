"""
Rotas Financeiras - MotoChefe
Contas a Pagar e Contas a Receber - Visão Consolidada
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    Moto, PedidoVendaMotoItem, EmbarqueMoto, 
    ComissaoVendedor, DespesaMensal, TituloFinanceiro
)


# ===== CONTAS A PAGAR - VISÃO CONSOLIDADA =====

@motochefe_bp.route('/contas-a-pagar')
@login_required
@requer_motochefe
def listar_contas_a_pagar():
    """
    Tela consolidada de contas a pagar com paginação
    Mostra: Motos, Fretes, Comissões, Montagens, Despesas
    """
    page = request.args.get('page', 1, type=int)
    per_page = 100

    # 1. MOTOS - Custo de Aquisição Pendente
    motos_pendentes = Moto.query.filter(
        Moto.status_pagamento_custo != 'PAGO',
        Moto.ativo == True
    ).order_by(Moto.nf_entrada, Moto.data_entrada).all()

    # Agrupar por NF
    motos_por_nf = {}
    for moto in motos_pendentes:
        if moto.nf_entrada not in motos_por_nf:
            motos_por_nf[moto.nf_entrada] = {
                'nf': moto.nf_entrada,
                'fornecedor': moto.fornecedor,
                'data_nf': moto.data_nf_entrada,
                'motos': [],
                'total_custo': Decimal('0'),
                'total_pago': Decimal('0')
            }

        motos_por_nf[moto.nf_entrada]['motos'].append(moto)
        motos_por_nf[moto.nf_entrada]['total_custo'] += moto.custo_aquisicao
        motos_por_nf[moto.nf_entrada]['total_pago'] += (moto.custo_pago or Decimal('0'))

    motos_agrupados = list(motos_por_nf.values())
    total_motos = sum(g['total_custo'] - g['total_pago'] for g in motos_agrupados)

    # 2. FRETES - Pendentes por Transportadora
    embarques_pendentes = EmbarqueMoto.query.filter(
        EmbarqueMoto.status_pagamento_frete != 'PAGO',
        EmbarqueMoto.ativo == True
    ).all()

    # Agrupar por transportadora
    fretes_por_transp = {}
    for emb in embarques_pendentes:
        transp_nome = emb.transportadora.transportadora if emb.transportadora else 'Sem Transportadora'
        if transp_nome not in fretes_por_transp:
            fretes_por_transp[transp_nome] = {
                'transportadora': transp_nome,
                'embarques': [],
                'total': Decimal('0')
            }

        fretes_por_transp[transp_nome]['embarques'].append(emb)
        fretes_por_transp[transp_nome]['total'] += emb.valor_frete_contratado

    fretes_agrupados = list(fretes_por_transp.values())
    total_fretes = sum(g['total'] for g in fretes_agrupados)

    # 3. COMISSÕES - Pendentes por Vendedor
    comissoes_pendentes = ComissaoVendedor.query.filter(
        ComissaoVendedor.status != 'PAGO'
    ).all()

    # Agrupar por vendedor
    comissoes_por_vend = {}
    for com in comissoes_pendentes:
        vend_nome = com.vendedor.vendedor if com.vendedor else 'Sem Vendedor'
        if vend_nome not in comissoes_por_vend:
            comissoes_por_vend[vend_nome] = {
                'vendedor': vend_nome,
                'comissoes': [],
                'total': Decimal('0')
            }

        comissoes_por_vend[vend_nome]['comissoes'].append(com)
        comissoes_por_vend[vend_nome]['total'] += com.valor_rateado

    comissoes_agrupadas = list(comissoes_por_vend.values())
    total_comissoes = sum(g['total'] for g in comissoes_agrupadas)

    # 4. MONTAGENS - Pendentes por Fornecedor
    montagens_pendentes = PedidoVendaMotoItem.query.filter(
        PedidoVendaMotoItem.montagem_contratada == True,
        PedidoVendaMotoItem.montagem_paga == False,
        PedidoVendaMotoItem.ativo == True
    ).all()

    # Agrupar por fornecedor
    montagens_por_forn = {}
    for mont in montagens_pendentes:
        forn_nome = mont.fornecedor_montagem or 'Sem Fornecedor'
        if forn_nome not in montagens_por_forn:
            montagens_por_forn[forn_nome] = {
                'fornecedor': forn_nome,
                'montagens': [],
                'total': Decimal('0')
            }

        montagens_por_forn[forn_nome]['montagens'].append(mont)
        montagens_por_forn[forn_nome]['total'] += mont.valor_montagem

    montagens_agrupadas = list(montagens_por_forn.values())
    total_montagens = sum(g['total'] for g in montagens_agrupadas)

    # 5. DESPESAS - Pendentes por Tipo
    despesas_pendentes = DespesaMensal.query.filter(
        DespesaMensal.status != 'PAGO',
        DespesaMensal.ativo == True
    ).all()

    # Agrupar por tipo
    despesas_por_tipo = {}
    for desp in despesas_pendentes:
        tipo = desp.tipo_despesa
        if tipo not in despesas_por_tipo:
            despesas_por_tipo[tipo] = {
                'tipo': tipo,
                'despesas': [],
                'total': Decimal('0')
            }

        despesas_por_tipo[tipo]['despesas'].append(desp)
        despesas_por_tipo[tipo]['total'] += (desp.valor - (desp.valor_pago or Decimal('0')))

    despesas_agrupadas = list(despesas_por_tipo.values())
    total_despesas = sum(g['total'] for g in despesas_agrupadas)

    # 6. TÍTULOS A PAGAR - Movimentação e Montagem (Pendentes e Abertos)
    from app.motochefe.models.financeiro import TituloAPagar

    titulos_a_pagar = TituloAPagar.query.filter(
        TituloAPagar.status.in_(['PENDENTE', 'ABERTO', 'PARCIAL'])
    ).order_by(TituloAPagar.data_criacao.desc()).all()

    # Agrupar por tipo
    titulos_por_tipo = {}
    for titulo in titulos_a_pagar:
        tipo = titulo.tipo  # MOVIMENTACAO ou MONTAGEM
        if tipo not in titulos_por_tipo:
            titulos_por_tipo[tipo] = {
                'tipo': tipo,
                'titulos': [],
                'total': Decimal('0')
            }

        titulos_por_tipo[tipo]['titulos'].append(titulo)
        titulos_por_tipo[tipo]['total'] += titulo.valor_saldo

    titulos_agrupados = list(titulos_por_tipo.values())
    total_titulos_a_pagar = sum(g['total'] for g in titulos_agrupados)

    # TOTAIS GERAIS
    total_geral = total_motos + total_fretes + total_comissoes + total_montagens + total_despesas + total_titulos_a_pagar

    # Consolidar TODOS os itens em uma lista única para paginação
    # Cada item terá um 'tipo' para identificação no template
    todos_itens = []

    for item in motos_agrupados:
        todos_itens.append({'tipo': 'MOTO', 'dados': item})

    for item in fretes_agrupados:
        todos_itens.append({'tipo': 'FRETE', 'dados': item})

    for item in comissoes_agrupadas:
        todos_itens.append({'tipo': 'COMISSAO', 'dados': item})

    for item in montagens_agrupadas:
        todos_itens.append({'tipo': 'MONTAGEM', 'dados': item})

    for item in despesas_agrupadas:
        todos_itens.append({'tipo': 'DESPESA', 'dados': item})

    for item in titulos_agrupados:
        todos_itens.append({'tipo': 'TITULO_A_PAGAR', 'dados': item})

    # Paginação manual
    total_items = len(todos_itens)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    itens_paginados = todos_itens[start_idx:end_idx]

    # Criar objeto paginacao manual
    class PaginacaoManual:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

    paginacao = PaginacaoManual(itens_paginados, page, per_page, total_items)

    # Vencidos (hoje)
    hoje = date.today()

    return render_template('motochefe/financeiro/contas_a_pagar.html',
                         itens=paginacao.items,
                         paginacao=paginacao,
                         total_motos=total_motos,
                         total_fretes=total_fretes,
                         total_comissoes=total_comissoes,
                         total_montagens=total_montagens,
                         total_despesas=total_despesas,
                         total_titulos_a_pagar=total_titulos_a_pagar,
                         total_geral=total_geral,
                         hoje=hoje)


@motochefe_bp.route('/contas-a-pagar/pagar-lote', methods=['POST'])
@login_required
@requer_motochefe
def pagar_lote():
    """
    Pagamento em lote
    Recebe JSON com array de itens: {tipo, id}
    """
    try:
        import json
        itens_json = request.form.get('itens_pagamento')
        data_pagamento = request.form.get('data_pagamento')

        if not itens_json:
            flash('Nenhum item selecionado para pagamento', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_pagar'))

        itens = json.loads(itens_json)
        data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else date.today()

        contador = 0

        for item in itens:
            tipo = item['tipo']
            item_id = int(item['id'])
            valor_pago = Decimal(item.get('valor', '0'))

            if tipo == 'moto':
                moto = Moto.query.get(item_id)  # PK é chassi (string), precisamos ajustar
                # Usar chassi como chave
                moto = Moto.query.filter_by(numero_chassi=item['id']).first()
                if moto:
                    moto.custo_pago = valor_pago
                    moto.data_pagamento_custo = data_pag
                    moto.status_pagamento_custo = 'PAGO' if valor_pago >= moto.custo_aquisicao else 'PARCIAL'
                    contador += 1

            elif tipo == 'frete':
                from app.motochefe.services.movimentacao_service import registrar_pagamento_frete_embarque
                from app.motochefe.services.empresa_service import atualizar_saldo
                from app.motochefe.models.cadastro import EmpresaVendaMoto

                embarque = EmbarqueMoto.query.get(item_id)
                empresa_pagadora_id = request.form.get('empresa_pagadora_id')

                if not empresa_pagadora_id:
                    raise Exception('Selecione a empresa pagadora para o frete')

                empresa_pagadora = EmpresaVendaMoto.query.get(empresa_pagadora_id)

                if embarque and empresa_pagadora:
                    # 1. REGISTRAR MOVIMENTAÇÃO
                    movimentacao = registrar_pagamento_frete_embarque(
                        embarque,
                        valor_pago,
                        empresa_pagadora,
                        current_user.nome
                    )

                    # 2. ATUALIZAR SALDO DA EMPRESA
                    atualizar_saldo(empresa_pagadora.id, valor_pago, 'SUBTRAIR')

                    # 3. ATUALIZAR EMBARQUE
                    embarque.valor_frete_pago = valor_pago
                    embarque.data_pagamento_frete = data_pag
                    embarque.empresa_pagadora_id = empresa_pagadora.id
                    embarque.status_pagamento_frete = 'PAGO'

                    contador += 1

            elif tipo == 'comissao':
                comissao = ComissaoVendedor.query.get(item_id)
                if comissao:
                    comissao.data_pagamento = data_pag
                    comissao.status = 'PAGO'
                    contador += 1

            elif tipo == 'montagem':
                montagem = PedidoVendaMotoItem.query.get(item_id)
                if montagem:
                    montagem.montagem_paga = True
                    montagem.data_pagamento_montagem = data_pag
                    contador += 1

            elif tipo == 'despesa':
                despesa = DespesaMensal.query.get(item_id)
                if despesa:
                    despesa.valor_pago = valor_pago
                    despesa.data_pagamento = data_pag
                    despesa.status = 'PAGO'
                    contador += 1

        db.session.commit()
        flash(f'{contador} pagamentos realizados com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar pagamentos: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_contas_a_pagar'))


# ===== CONTAS A RECEBER - VISÃO CONSOLIDADA =====

@motochefe_bp.route('/contas-a-receber')
@login_required
@requer_motochefe
def listar_contas_a_receber():
    """
    Tela consolidada de contas a receber (novo sistema com accordion)
    Mostra: Pedidos > Parcelas > Motos > Títulos
    """
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    from app.motochefe.services.titulo_service import obter_todos_titulos_agrupados

    # Buscar títulos agrupados por Pedido > Parcela > Moto
    pedidos_agrupados = obter_todos_titulos_agrupados()

    # Calcular totais
    hoje = date.today()
    total_vencidos = Decimal('0')
    total_hoje = Decimal('0')
    total_a_vencer = Decimal('0')

    for pedido_id, dados_pedido in pedidos_agrupados.items():
        for parcela_num, dados_parcela in dados_pedido['parcelas'].items():
            for chassi, titulos in dados_parcela['motos'].items():
                for titulo in titulos:
                    if titulo.data_vencimento:
                        if titulo.data_vencimento < hoje:
                            total_vencidos += titulo.valor_saldo
                        elif titulo.data_vencimento == hoje:
                            total_hoje += titulo.valor_saldo
                        else:
                            total_a_vencer += titulo.valor_saldo

    total_geral = total_vencidos + total_hoje + total_a_vencer

    # Buscar empresas ativas para o select
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(
        EmpresaVendaMoto.tipo_conta,
        EmpresaVendaMoto.empresa
    ).all()

    return render_template('motochefe/financeiro/contas_a_receber.html',
                         pedidos_agrupados=pedidos_agrupados,
                         total_vencidos=total_vencidos,
                         total_hoje=total_hoje,
                         total_a_vencer=total_a_vencer,
                         total_geral=total_geral,
                         empresas=empresas,
                         hoje=hoje)


@motochefe_bp.route('/contas-a-receber/receber-lote', methods=['POST'])
@login_required
@requer_motochefe
def receber_lote():
    """
    Recebimento em lote de títulos (novo sistema)
    Cria MovimentacaoFinanceira, atualiza saldo, dispara triggers
    """
    from app.motochefe.services.titulo_service import receber_titulo
    from app.motochefe.models.cadastro import EmpresaVendaMoto

    try:
        import json
        itens_json = request.form.get('itens_recebimento')
        empresa_recebedora_id = request.form.get('empresa_recebedora_id')

        if not itens_json:
            flash('Nenhum título selecionado', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_receber'))

        if not empresa_recebedora_id:
            flash('Selecione a empresa recebedora', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_receber'))

        itens = json.loads(itens_json)
        empresa = EmpresaVendaMoto.query.get_or_404(int(empresa_recebedora_id))

        contador = 0
        total_recebido = Decimal('0')

        for item in itens:
            titulo_id = int(item['id'])
            valor_recebido = Decimal(item.get('valor', '0'))

            titulo = TituloFinanceiro.query.get(titulo_id)
            if titulo and valor_recebido > 0:
                # USAR NOVO SISTEMA DE RECEBIMENTO
                # Cria MovimentacaoFinanceira, atualiza saldo, dispara triggers:
                # - Libera TituloAPagar
                # - Baixa automática de motos (se empresa.baixa_compra_auto=True)
                # - Gera comissão por moto (se título de VENDA)
                resultado = receber_titulo(
                    titulo=titulo,
                    valor_recebido=valor_recebido,
                    empresa_recebedora=empresa,
                    usuario=current_user.nome
                )

                contador += 1
                total_recebido += valor_recebido

        db.session.commit()

        if contador > 0:
            flash(
                f'{contador} título(s) recebido(s) com sucesso! Total: R$ {total_recebido:,.2f}',
                'success'
            )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar recebimentos: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_contas_a_receber'))


@motochefe_bp.route('/contas-a-receber/receber-pedido/<int:pedido_id>', methods=['POST'])
@login_required
@requer_motochefe
def receber_pedido_contas(pedido_id):
    """
    Recebe pagamento de um pedido inteiro na tela de Contas a Receber
    Usa mesma lógica da listagem de pedidos
    """
    from app.motochefe.services.titulo_service import receber_por_pedido
    from app.motochefe.models.vendas import PedidoVendaMoto
    from app.motochefe.models.cadastro import EmpresaVendaMoto

    try:
        empresa_id = request.form.get('empresa_recebedora_id')
        valor_recebido = request.form.get('valor_recebido')

        if not all([empresa_id, valor_recebido]):
            raise Exception('Empresa recebedora e valor são obrigatórios')

        valor = Decimal(valor_recebido)
        if valor <= 0:
            raise Exception('Valor deve ser maior que zero')

        pedido = PedidoVendaMoto.query.get_or_404(pedido_id)
        empresa = EmpresaVendaMoto.query.get_or_404(int(empresa_id))

        resultado = receber_por_pedido(
            pedido_id=pedido.id,
            valor_recebido=valor,
            empresa_recebedora=empresa,
            usuario=current_user.nome
        )

        db.session.commit()

        total_titulos = len(resultado['titulos_recebidos'])
        total_aplicado = resultado['total_aplicado']

        flash(
            f'Recebimento do pedido {pedido.numero_pedido} registrado! '
            f'{total_titulos} título(s) atualizado(s). Valor: R$ {total_aplicado:,.2f}',
            'success'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar recebimento: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_contas_a_receber'))


@motochefe_bp.route('/contas-a-receber/receber-moto/<int:pedido_id>/<string:chassi>', methods=['POST'])
@login_required
@requer_motochefe
def receber_moto_contas(pedido_id, chassi):
    """
    Recebe pagamento de uma moto específica na tela de Contas a Receber
    """
    from app.motochefe.services.titulo_service import receber_por_moto
    from app.motochefe.models.vendas import PedidoVendaMoto
    from app.motochefe.models.cadastro import EmpresaVendaMoto

    try:
        empresa_id = request.form.get('empresa_recebedora_id')
        valor_recebido = request.form.get('valor_recebido')

        if not all([empresa_id, valor_recebido]):
            raise Exception('Empresa recebedora e valor são obrigatórios')

        valor = Decimal(valor_recebido)
        if valor <= 0:
            raise Exception('Valor deve ser maior que zero')

        pedido = PedidoVendaMoto.query.get_or_404(pedido_id)
        empresa = EmpresaVendaMoto.query.get_or_404(int(empresa_id))

        resultado = receber_por_moto(
            pedido_id=pedido.id,
            numero_chassi=chassi,
            valor_recebido=valor,
            empresa_recebedora=empresa,
            usuario=current_user.nome
        )

        db.session.commit()

        total_titulos = len(resultado['titulos_recebidos'])
        total_aplicado = resultado['total_aplicado']

        flash(
            f'Recebimento da moto {chassi} registrado! '
            f'{total_titulos} título(s) atualizado(s). Valor: R$ {total_aplicado:,.2f}',
            'success'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar recebimento: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_contas_a_receber'))
