"""
Rotas Financeiras - MotoChefe
Contas a Pagar e Contas a Receber - Visão Consolidada
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import and_, or_, func

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import (
    Moto, PedidoVendaMotoItem, EmbarqueMoto, EmbarquePedido,
    ComissaoVendedor, DespesaMensal, TituloFinanceiro,
    TransportadoraMoto
)


# ===== CONTAS A PAGAR - VISÃO CONSOLIDADA =====

@motochefe_bp.route('/contas-a-pagar')
@login_required
@requer_motochefe
def listar_contas_a_pagar():
    """
    Tela consolidada de contas a pagar
    Mostra: Motos, Fretes, Comissões, Montagens, Despesas
    """

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

    # TOTAIS GERAIS
    total_geral = total_motos + total_fretes + total_comissoes + total_montagens + total_despesas

    # Vencidos (hoje)
    hoje = date.today()

    return render_template('motochefe/financeiro/contas_a_pagar.html',
                         motos_agrupados=motos_agrupados,
                         fretes_agrupados=fretes_agrupados,
                         comissoes_agrupadas=comissoes_agrupadas,
                         montagens_agrupadas=montagens_agrupadas,
                         despesas_agrupadas=despesas_agrupadas,
                         total_motos=total_motos,
                         total_fretes=total_fretes,
                         total_comissoes=total_comissoes,
                         total_montagens=total_montagens,
                         total_despesas=total_despesas,
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
                embarque = EmbarqueMoto.query.get(item_id)
                if embarque:
                    embarque.valor_frete_pago = valor_pago
                    embarque.data_pagamento_frete = data_pag
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
    Tela consolidada de contas a receber (novo sistema)
    Mostra: Títulos Financeiros por moto + tipo
    """
    from app.motochefe.models.cadastro import EmpresaVendaMoto

    # Títulos em aberto (novo sistema usa valor_saldo)
    titulos_abertos = TituloFinanceiro.query.filter(
        TituloFinanceiro.status != 'PAGO'
    ).order_by(TituloFinanceiro.data_vencimento).all()

    # Agrupar por status (vencido, hoje, a vencer)
    hoje = date.today()

    vencidos = [t for t in titulos_abertos if t.data_vencimento and t.data_vencimento < hoje]
    vencendo_hoje = [t for t in titulos_abertos if t.data_vencimento == hoje]
    a_vencer = [t for t in titulos_abertos if t.data_vencimento and t.data_vencimento > hoje]
    sem_vencimento = [t for t in titulos_abertos if not t.data_vencimento]

    # Totais (novo sistema usa valor_saldo diretamente)
    total_vencidos = sum(t.valor_saldo for t in vencidos)
    total_hoje = sum(t.valor_saldo for t in vencendo_hoje)
    total_a_vencer = sum(t.valor_saldo for t in a_vencer)
    total_geral = total_vencidos + total_hoje + total_a_vencer

    # Buscar empresas ativas para o select
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(
        EmpresaVendaMoto.tipo_conta,
        EmpresaVendaMoto.empresa
    ).all()

    return render_template('motochefe/financeiro/contas_a_receber.html',
                         vencidos=vencidos,
                         vencendo_hoje=vencendo_hoje,
                         a_vencer=a_vencer,
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
