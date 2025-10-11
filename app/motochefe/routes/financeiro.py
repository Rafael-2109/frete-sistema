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
    ComissaoVendedor, DespesaMensal, CustosOperacionais, MovimentacaoFinanceira
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
    total_motos = sum((g['total_custo'] - g['total_pago'] for g in motos_agrupados), Decimal("0"))

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
    total_fretes = sum((g['total'] for g in fretes_agrupados), Decimal("0"))

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
    total_comissoes = sum((g['total'] for g in comissoes_agrupadas), Decimal("0"))

    # 4. MONTAGENS - Pendentes por Fornecedor
    montagens_pendentes = PedidoVendaMotoItem.query.filter(
        PedidoVendaMotoItem.montagem_contratada == True,
        PedidoVendaMotoItem.montagem_paga == False,
        PedidoVendaMotoItem.ativo == True
    ).all()

    # Buscar custo REAL da montagem de CustosOperacionais
    custos_vigentes = CustosOperacionais.get_custos_vigentes()
    custo_montagem_real = custos_vigentes.custo_montagem if custos_vigentes else Decimal('0')

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
        # ✅ CORRIGIDO: Usar custo real de CustosOperacionais, não valor cobrado do cliente
        montagens_por_forn[forn_nome]['total'] += custo_montagem_real

    montagens_agrupadas = list(montagens_por_forn.values())
    total_montagens = sum((g['total'] for g in montagens_agrupadas), Decimal("0"))

    # 🆕 PASSAR custo_montagem_real para o template
    # Para ser usado na exibição dos detalhes de cada montagem
    custo_montagem_para_template = custo_montagem_real

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
    total_despesas = sum((g['total'] for g in despesas_agrupadas), Decimal("0"))

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
    total_titulos_a_pagar = sum((g['total'] for g in titulos_agrupados), Decimal("0"))

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

    # Buscar empresas ativas para o select de empresa pagadora
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(
        EmpresaVendaMoto.tipo_conta,
        EmpresaVendaMoto.empresa
    ).all()

    return render_template('motochefe/financeiro/contas_a_pagar.html',
                         itens=paginacao.items,
                         paginacao=paginacao,
                         motos_agrupados=motos_agrupados,
                         fretes_agrupados=fretes_agrupados,
                         comissoes_agrupadas=comissoes_agrupadas,
                         montagens_agrupadas=montagens_agrupadas,
                         despesas_agrupadas=despesas_agrupadas,
                         titulos_agrupados=titulos_agrupados,
                         total_motos=total_motos,
                         total_fretes=total_fretes,
                         total_comissoes=total_comissoes,
                         total_montagens=total_montagens,
                         total_despesas=total_despesas,
                         total_titulos_a_pagar=total_titulos_a_pagar,
                         total_geral=total_geral,
                         empresas=empresas,
                         hoje=hoje,
                         custo_montagem_real=custo_montagem_para_template)


@motochefe_bp.route('/contas-a-pagar/pagar-lote', methods=['POST'])
@login_required
@requer_motochefe
def pagar_lote():
    """
    Pagamento em lote - REFATORADO
    Usa novo sistema com MovimentacaoFinanceira PAI + FILHOS
    Agrupa itens por tipo e cria um lote para cada tipo
    """
    try:
        import json
        from app.motochefe.models.cadastro import EmpresaVendaMoto
        from app.motochefe.services.lote_pagamento_service import (
            processar_pagamento_lote_motos,
            processar_pagamento_lote_comissoes,
            processar_pagamento_lote_montagens,
            processar_pagamento_lote_despesas
        )
        from app.motochefe.services.movimentacao_service import registrar_pagamento_frete_embarque
        from app.motochefe.services.empresa_service import atualizar_saldo

        itens_json = request.form.get('itens_pagamento')
        data_pagamento = request.form.get('data_pagamento')
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')

        if not itens_json:
            flash('Nenhum item selecionado para pagamento', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_pagar'))

        if not empresa_pagadora_id:
            flash('Selecione a empresa pagadora', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_pagar'))

        itens = json.loads(itens_json)
        data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else date.today()
        empresa_pagadora = EmpresaVendaMoto.query.get_or_404(int(empresa_pagadora_id))

        # Agrupar itens por tipo
        itens_por_tipo = {
            'moto': [],
            'comissao': [],
            'montagem': [],
            'despesa': [],
            'frete': []
        }

        for item in itens:
            tipo = item['tipo']
            if tipo in itens_por_tipo:
                itens_por_tipo[tipo].append(item)

        total_lotes = 0
        total_itens = 0
        valor_total_geral = Decimal('0')

        # Processar MOTOS em lote
        if itens_por_tipo['moto']:
            chassi_list = [item['id'] for item in itens_por_tipo['moto']]
            resultado = processar_pagamento_lote_motos(
                chassi_list=chassi_list,
                empresa_pagadora=empresa_pagadora,
                data_pagamento=data_pag,
                usuario=current_user.nome
            )
            total_lotes += 1
            total_itens += len(resultado['motos_atualizadas'])
            valor_total_geral += resultado['valor_total']

        # Processar COMISSÕES em lote
        if itens_por_tipo['comissao']:
            comissao_ids = [int(item['id']) for item in itens_por_tipo['comissao']]
            resultado = processar_pagamento_lote_comissoes(
                comissao_ids=comissao_ids,
                empresa_pagadora=empresa_pagadora,
                data_pagamento=data_pag,
                usuario=current_user.nome
            )
            total_lotes += 1
            total_itens += len(resultado['comissoes_atualizadas'])
            valor_total_geral += resultado['valor_total']

        # Processar MONTAGENS em lote
        if itens_por_tipo['montagem']:
            item_ids = [int(item['id']) for item in itens_por_tipo['montagem']]
            resultado = processar_pagamento_lote_montagens(
                item_ids=item_ids,
                empresa_pagadora=empresa_pagadora,
                data_pagamento=data_pag,
                usuario=current_user.nome
            )
            total_lotes += 1
            total_itens += len(resultado['itens_atualizados'])
            valor_total_geral += resultado['valor_total']

        # Processar DESPESAS em lote
        if itens_por_tipo['despesa']:
            despesa_ids = [int(item['id']) for item in itens_por_tipo['despesa']]
            resultado = processar_pagamento_lote_despesas(
                despesa_ids=despesa_ids,
                empresa_pagadora=empresa_pagadora,
                data_pagamento=data_pag,
                usuario=current_user.nome
            )
            total_lotes += 1
            total_itens += len(resultado['despesas_atualizadas'])
            valor_total_geral += resultado['valor_total']

        # Processar FRETES individualmente (não agrupa em lote por enquanto)
        if itens_por_tipo['frete']:
            for item in itens_por_tipo['frete']:
                embarque = EmbarqueMoto.query.get(int(item['id']))
                valor_pago = Decimal(item.get('valor', '0'))

                if embarque:
                    # Registrar movimentação
                    registrar_pagamento_frete_embarque(
                        embarque,
                        valor_pago,
                        empresa_pagadora,
                        current_user.nome
                    )
                    # Atualizar saldo
                    atualizar_saldo(empresa_pagadora.id, valor_pago, 'SUBTRAIR')
                    # Atualizar embarque
                    embarque.valor_frete_pago = valor_pago
                    embarque.data_pagamento_frete = data_pag
                    embarque.empresa_pagadora_id = empresa_pagadora.id
                    embarque.status_pagamento_frete = 'PAGO'

                    total_itens += 1
                    valor_total_geral += valor_pago

        db.session.commit()

        flash(
            f'Pagamento realizado com sucesso! '
            f'{total_lotes} lote(s) criado(s), {total_itens} item(ns) processado(s). '
            f'Total: R$ {valor_total_geral:,.2f}',
            'success'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar pagamentos: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_contas_a_pagar'))


@motochefe_bp.route('/contas-a-pagar/pagar-grupo', methods=['POST'])
@login_required
@requer_motochefe
def pagar_grupo():
    """
    Pagamento de um grupo com valor editável
    Paga sequencialmente (quita item por item até acabar o valor)
    """
    try:
        from app.motochefe.models.cadastro import EmpresaVendaMoto
        from app.motochefe.services.lote_pagamento_service import (
            processar_pagamento_lote_motos,
            processar_pagamento_lote_comissoes,
            processar_pagamento_lote_montagens,
            processar_pagamento_lote_despesas
        )
        from app.motochefe.services.movimentacao_service import registrar_pagamento_frete_embarque
        from app.motochefe.services.empresa_service import atualizar_saldo

        itens_ids_str = request.form.get('itens_ids')
        tipo_grupo = request.form.get('tipo_grupo')
        data_pagamento = request.form.get('data_pagamento')
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')
        valor_pagar = request.form.get('valor_pagar', '0')

        if not itens_ids_str or not empresa_pagadora_id or not tipo_grupo:
            flash('Dados inválidos para pagamento', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_pagar'))

        # Converter IDs de string para lista
        itens_ids = itens_ids_str.split(',')
        data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else date.today()
        empresa_pagadora = EmpresaVendaMoto.query.get_or_404(int(empresa_pagadora_id))
        valor_disponivel = Decimal(valor_pagar)

        if valor_disponivel <= 0:
            flash('Valor deve ser maior que zero', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_pagar'))

        total_pago = Decimal('0')
        total_itens = 0

        # PROCESSAR MOTOS COM PAGAMENTO PARCIAL (USA FUNÇÃO DE LOTE)
        if tipo_grupo == 'moto':
            resultado = processar_pagamento_lote_motos(
                chassi_list=itens_ids,
                empresa_pagadora=empresa_pagadora,
                data_pagamento=data_pag,
                usuario=current_user.nome,
                valor_limite=valor_disponivel
            )
            total_pago = resultado['valor_total']
            total_itens = len(resultado['motos_atualizadas'])

        # PROCESSAR FRETES COM PAGAMENTO PARCIAL (LÓGICA INLINE - SEM FUNÇÃO AINDA)
        elif tipo_grupo == 'frete':

            embarques_para_pagar = []
            for emb_id in itens_ids:
                if valor_disponivel <= 0:
                    break

                embarque = EmbarqueMoto.query.get(int(emb_id))
                if embarque:
                    valor_saldo_frete = embarque.valor_frete_contratado - (embarque.valor_frete_pago or Decimal('0'))
                    if valor_saldo_frete <= 0:
                        continue

                    valor_pagar_frete = min(valor_disponivel, valor_saldo_frete)
                    if valor_pagar_frete > 0:
                        embarques_para_pagar.append({'embarque': embarque, 'valor': valor_pagar_frete})
                        valor_disponivel -= valor_pagar_frete
                        total_pago += valor_pagar_frete

            if embarques_para_pagar:
                transportadora = embarques_para_pagar[0]['embarque'].transportadora.transportadora if embarques_para_pagar[0]['embarque'].transportadora else 'Sem Transportadora'
                if len(embarques_para_pagar) > 1:
                    transportadora = f'{transportadora} ({len(embarques_para_pagar)} embarques)'

                movimentacao_pai = MovimentacaoFinanceira(
                    tipo='PAGAMENTO',
                    categoria='Lote Frete',
                    valor=total_pago,
                    data_movimentacao=data_pag,
                    empresa_origem_id=empresa_pagadora.id,
                    empresa_destino_id=None,
                    destino_tipo='Transportadora',
                    destino_identificacao=transportadora,
                    descricao=f'Pagamento Lote {len(embarques_para_pagar)} frete(s)',
                    observacoes=f'Valor informado: R$ {valor_pagar}',
                    criado_por=current_user.nome
                )
                db.session.add(movimentacao_pai)
                db.session.flush()

                for item in embarques_para_pagar:
                    embarque = item['embarque']
                    valor_pagar_frete = item['valor']

                    movimentacao_filha = MovimentacaoFinanceira(
                        tipo='PAGAMENTO',
                        categoria='Frete',
                        valor=valor_pagar_frete,
                        data_movimentacao=data_pag,
                        empresa_origem_id=empresa_pagadora.id,
                        empresa_destino_id=None,
                        destino_tipo='Transportadora',
                        destino_identificacao=embarque.transportadora.transportadora if embarque.transportadora else 'Sem Transportadora',
                        descricao=f'Frete Embarque #{embarque.id}',
                        movimentacao_origem_id=movimentacao_pai.id,
                        eh_baixa_automatica=False,
                        criado_por=current_user.nome
                    )
                    db.session.add(movimentacao_filha)

                    embarque.valor_frete_pago = (embarque.valor_frete_pago or Decimal('0')) + valor_pagar_frete
                    embarque.data_pagamento_frete = data_pag
                    embarque.empresa_pagadora_id = empresa_pagadora.id

                    if embarque.valor_frete_pago >= embarque.valor_frete_contratado:
                        embarque.status_pagamento_frete = 'PAGO'
                    else:
                        embarque.status_pagamento_frete = 'PARCIAL'

                    total_itens += 1

                atualizar_saldo(empresa_pagadora.id, total_pago, 'SUBTRAIR')

        # PROCESSAR COMISSÕES SEQUENCIALMENTE
        elif tipo_grupo == 'comissao':
            comissao_selecionadas = []
            for com_id in itens_ids:
                if valor_disponivel <= 0:
                    break

                comissao = ComissaoVendedor.query.get(int(com_id))
                if comissao:
                    valor_item = comissao.valor_rateado
                    if valor_disponivel >= valor_item:
                        comissao_selecionadas.append(int(com_id))
                        valor_disponivel -= valor_item
                        total_pago += valor_item

            if comissao_selecionadas:
                resultado = processar_pagamento_lote_comissoes(
                    comissao_ids=comissao_selecionadas,
                    empresa_pagadora=empresa_pagadora,
                    data_pagamento=data_pag,
                    usuario=current_user.nome
                )
                total_itens += len(resultado['comissoes_atualizadas'])

        # PROCESSAR MONTAGENS SEQUENCIALMENTE
        elif tipo_grupo == 'montagem':
            # Buscar custo REAL da montagem
            custos_vigentes = CustosOperacionais.get_custos_vigentes()
            custo_montagem_real = custos_vigentes.custo_montagem if custos_vigentes else Decimal('0')

            montagem_selecionadas = []
            for mont_id in itens_ids:
                if valor_disponivel <= 0:
                    break

                if valor_disponivel >= custo_montagem_real:
                    montagem_selecionadas.append(int(mont_id))
                    valor_disponivel -= custo_montagem_real
                    total_pago += custo_montagem_real

            if montagem_selecionadas:
                resultado = processar_pagamento_lote_montagens(
                    item_ids=montagem_selecionadas,
                    empresa_pagadora=empresa_pagadora,
                    data_pagamento=data_pag,
                    usuario=current_user.nome
                )
                total_itens += len(resultado['itens_atualizados'])

        # PROCESSAR DESPESAS SEQUENCIALMENTE
        elif tipo_grupo == 'despesa':
            despesa_selecionadas = []
            for desp_id in itens_ids:
                if valor_disponivel <= 0:
                    break

                despesa = DespesaMensal.query.get(int(desp_id))
                if despesa:
                    valor_item = despesa.valor - (despesa.valor_pago or Decimal('0'))
                    if valor_disponivel >= valor_item:
                        despesa_selecionadas.append(int(desp_id))
                        valor_disponivel -= valor_item
                        total_pago += valor_item

            if despesa_selecionadas:
                resultado = processar_pagamento_lote_despesas(
                    despesa_ids=despesa_selecionadas,
                    empresa_pagadora=empresa_pagadora,
                    data_pagamento=data_pag,
                    usuario=current_user.nome
                )
                total_itens += len(resultado['despesas_atualizadas'])

        db.session.commit()

        flash(
            f'Pagamento realizado com sucesso! '
            f'{total_itens} item(ns) quitado(s). Total pago: R$ {total_pago:,.2f}',
            'success'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar pagamento: {str(e)}', 'danger')

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
    Recebimento em lote de títulos - REFATORADO
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS
    """
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    from app.motochefe.services.lote_pagamento_service import processar_recebimento_lote_titulos

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

        # Montar dicionário de valores por título
        titulo_ids = []
        valores_recebidos = {}

        for item in itens:
            titulo_id = int(item['id'])
            valor = Decimal(item.get('valor', '0'))

            if valor > 0:
                titulo_ids.append(titulo_id)
                valores_recebidos[titulo_id] = valor

        if not titulo_ids:
            flash('Nenhum título com valor válido', 'warning')
            return redirect(url_for('motochefe.listar_contas_a_receber'))

        # PROCESSAR LOTE (cria PAI + FILHOS)
        resultado = processar_recebimento_lote_titulos(
            titulo_ids=titulo_ids,
            valores_recebidos=valores_recebidos,
            empresa_recebedora=empresa,
            data_recebimento=date.today(),
            usuario=current_user.nome
        )

        db.session.commit()

        flash(
            f'Recebimento registrado com sucesso! '
            f'{len(resultado["titulos_recebidos"])} título(s) atualizado(s). '
            f'Total: R$ {resultado["valor_total"]:,.2f}',
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


# ===== DETALHES DE PAGAMENTOS E RECEBIMENTOS =====

@motochefe_bp.route('/pagamentos/<int:movimentacao_id>/detalhes')
@login_required
@requer_motochefe
def detalhes_pagamento(movimentacao_id):
    """
    Tela de detalhes de um pagamento em lote
    Mostra MovimentacaoFinanceira PAI + breakdown dos FILHOS
    """
    from app.motochefe.services.lote_pagamento_service import obter_detalhes_lote_pagamento

    try:
        detalhes = obter_detalhes_lote_pagamento(movimentacao_id)

        # ✅ TAREFA 4: Agrupar itens por pedido para accordion
        itens_relacionados = detalhes['itens_relacionados']
        itens_por_pedido = {}
        itens_sem_pedido = []

        for item in itens_relacionados:
            # Tentar obter pedido_id do item ou do objeto relacionado
            pedido_id = None
            numero_pedido = None

            if hasattr(item.get('movimentacao'), 'pedido_id'):
                pedido_id = item.get('movimentacao').pedido_id
            elif hasattr(item.get('item_objeto'), 'pedido_id'):
                pedido_id = item.get('item_objeto').pedido_id
            elif hasattr(item.get('item_objeto'), 'pedido'):
                pedido_obj = item.get('item_objeto').pedido
                if pedido_obj:
                    pedido_id = pedido_obj.id
                    numero_pedido = pedido_obj.numero_pedido

            # Separar itens COM pedido vs SEM pedido
            if pedido_id:
                if pedido_id not in itens_por_pedido:
                    itens_por_pedido[pedido_id] = {
                        'numero_pedido': numero_pedido or f'Pedido #{pedido_id}',
                        'itens': []
                    }
                itens_por_pedido[pedido_id]['itens'].append(item)
            else:
                itens_sem_pedido.append(item)

        return render_template('motochefe/financeiro/detalhes_pagamento.html',
                             movimentacao_pai=detalhes['movimentacao_pai'],
                             movimentacoes_filhas=detalhes['movimentacoes_filhas'],
                             itens_relacionados=detalhes['itens_relacionados'],
                             itens_por_pedido=itens_por_pedido,
                             itens_sem_pedido=itens_sem_pedido,
                             todos_titulos_pedido=detalhes.get('todos_titulos_pedido', []),
                             titulos_com_movimentacao=detalhes.get('titulos_com_movimentacao', set()),
                             total_saldo_anterior=detalhes.get('total_saldo_anterior', 0),
                             total_saldo_apos=detalhes.get('total_saldo_apos', 0),
                             eh_pagamento_individual=detalhes.get('eh_pagamento_individual', False))

    except Exception as e:
        flash(f'Erro ao carregar detalhes do pagamento: {str(e)}', 'danger')
        return redirect(url_for('motochefe.extrato_financeiro'))


@motochefe_bp.route('/recebimentos/<int:movimentacao_id>/detalhes')
@login_required
@requer_motochefe
def detalhes_recebimento(movimentacao_id):
    """
    Tela de detalhes de um recebimento em lote
    Usa a mesma função genérica de pagamentos
    """
    from app.motochefe.services.lote_pagamento_service import obter_detalhes_lote_pagamento

    try:
        detalhes = obter_detalhes_lote_pagamento(movimentacao_id)

        # ✅ Agrupar itens por pedido (igual em detalhes_pagamento)
        itens_relacionados = detalhes['itens_relacionados']
        itens_por_pedido = {}
        itens_sem_pedido = []

        for item in itens_relacionados:
            pedido_id = None
            numero_pedido = None

            if hasattr(item.get('movimentacao'), 'pedido_id'):
                pedido_id = item.get('movimentacao').pedido_id
            elif hasattr(item.get('item_objeto'), 'pedido_id'):
                pedido_id = item.get('item_objeto').pedido_id
            elif hasattr(item.get('item_objeto'), 'pedido'):
                pedido_obj = item.get('item_objeto').pedido
                if pedido_obj:
                    pedido_id = pedido_obj.id
                    numero_pedido = pedido_obj.numero_pedido

            if pedido_id:
                if pedido_id not in itens_por_pedido:
                    itens_por_pedido[pedido_id] = {
                        'numero_pedido': numero_pedido or f'Pedido #{pedido_id}',
                        'itens': []
                    }
                itens_por_pedido[pedido_id]['itens'].append(item)
            else:
                itens_sem_pedido.append(item)

        return render_template('motochefe/financeiro/detalhes_pagamento.html',
                             movimentacao_pai=detalhes['movimentacao_pai'],
                             movimentacoes_filhas=detalhes['movimentacoes_filhas'],
                             itens_relacionados=detalhes['itens_relacionados'],
                             itens_por_pedido=itens_por_pedido,
                             itens_sem_pedido=itens_sem_pedido,
                             todos_titulos_pedido=detalhes.get('todos_titulos_pedido', []),
                             titulos_com_movimentacao=detalhes.get('titulos_com_movimentacao', set()),
                             total_saldo_anterior=detalhes.get('total_saldo_anterior', 0),
                             total_saldo_apos=detalhes.get('total_saldo_apos', 0),
                             eh_pagamento_individual=detalhes.get('eh_pagamento_individual', False))

    except Exception as e:
        flash(f'Erro ao carregar detalhes do recebimento: {str(e)}', 'danger')
        return redirect(url_for('motochefe.extrato_financeiro'))
