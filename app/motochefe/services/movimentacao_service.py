"""
Service para Movimentações Financeiras - Sistema MotoCHEFE
Registra TODAS as movimentações (recebimentos e pagamentos)
"""
from app import db
from app.motochefe.models.financeiro import MovimentacaoFinanceira
from datetime import date


def registrar_recebimento_titulo(titulo, valor_recebido, empresa_recebedora, usuario=None):
    """
    Registra recebimento de título financeiro

    Args:
        titulo: TituloFinanceiro
        valor_recebido: Decimal
        empresa_recebedora: EmpresaVendaMoto
        usuario: str (nome do usuário)

    Returns:
        MovimentacaoFinanceira criada
    """
    movimentacao = MovimentacaoFinanceira(
        tipo='RECEBIMENTO',
        categoria=f'Título {titulo.tipo_titulo}',
        valor=valor_recebido,
        data_movimentacao=date.today(),

        # Origem (Cliente)
        empresa_origem_id=None,
        origem_tipo='Cliente',
        origem_identificacao=titulo.pedido.cliente.cliente if titulo.pedido.cliente else 'Cliente',

        # Destino (Empresa)
        empresa_destino_id=empresa_recebedora.id,

        # Relacionamentos
        titulo_financeiro_id=titulo.id,
        pedido_id=titulo.pedido_id,
        numero_chassi=titulo.numero_chassi,
        numero_nf=titulo.pedido.numero_nf if titulo.pedido.faturado else None,

        # Descrição
        descricao=f'Recebimento Título #{titulo.id} - {titulo.tipo_titulo} - Moto {titulo.numero_chassi}',

        # Auditoria
        criado_por=usuario
    )

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def registrar_pagamento_titulo_a_pagar(titulo_pagar, valor_pago, empresa_pagadora, usuario=None):
    """
    Registra pagamento de título a pagar (Movimentação ou Montagem)

    Args:
        titulo_pagar: TituloAPagar
        valor_pago: Decimal
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        MovimentacaoFinanceira criada
    """
    if titulo_pagar.tipo == 'MOVIMENTACAO':
        # Pagamento para MargemSogima (outra empresa)
        movimentacao = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Movimentação',
            valor=valor_pago,
            data_movimentacao=date.today(),

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=titulo_pagar.empresa_destino_id,  # MargemSogima

            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,

            descricao=f'Pagamento Movimentação - Título #{titulo_pagar.id} - {titulo_pagar.beneficiario}',
            criado_por=usuario
        )

    elif titulo_pagar.tipo == 'MONTAGEM':
        # Pagamento para Equipe Montagem (não é empresa)
        movimentacao = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Montagem',
            valor=valor_pago,
            data_movimentacao=date.today(),

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=None,
            destino_tipo='Equipe Montagem',
            destino_identificacao=titulo_pagar.fornecedor_montagem,

            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,

            descricao=f'Pagamento Montagem - {titulo_pagar.fornecedor_montagem} - Título #{titulo_pagar.id}',
            criado_por=usuario
        )

    else:
        raise Exception(f'Tipo de título a pagar inválido: {titulo_pagar.tipo}')

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def registrar_pagamento_custo_moto(moto, valor_pago, empresa_pagadora, usuario=None, eh_baixa_auto=False, mov_origem_id=None):
    """
    Registra pagamento de custo de moto

    Args:
        moto: Moto
        valor_pago: Decimal
        empresa_pagadora: EmpresaVendaMoto
        usuario: str
        eh_baixa_auto: bool (se foi baixa automática)
        mov_origem_id: int (ID da movimentação que originou)

    Returns:
        MovimentacaoFinanceira criada
    """
    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Custo Moto',
        valor=valor_pago,
        data_movimentacao=date.today(),

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Fornecedor',
        destino_identificacao=moto.fornecedor,

        numero_chassi=moto.numero_chassi,
        numero_nf=moto.nf_entrada,

        descricao=f'{"[BAIXA AUTO] " if eh_baixa_auto else ""}Pagamento Custo Moto {moto.numero_chassi} - {moto.fornecedor}',

        eh_baixa_automatica=eh_baixa_auto,
        movimentacao_origem_id=mov_origem_id,

        criado_por=usuario or 'SISTEMA' if eh_baixa_auto else None
    )

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def registrar_pagamento_comissao(comissao, empresa_pagadora, usuario=None):
    """
    Registra pagamento de comissão

    Args:
        comissao: ComissaoVendedor
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        MovimentacaoFinanceira criada
    """
    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Comissão',
        valor=comissao.valor_rateado,
        data_movimentacao=date.today(),

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Vendedor',
        destino_identificacao=comissao.vendedor.vendedor if comissao.vendedor else 'Vendedor',

        comissao_vendedor_id=comissao.id,
        pedido_id=comissao.pedido_id,
        numero_chassi=comissao.numero_chassi,

        descricao=f'Pagamento Comissão - {comissao.vendedor.vendedor} - Pedido {comissao.pedido.numero_pedido}',
        criado_por=usuario
    )

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def obter_extrato(data_inicial, data_final, empresa_id=None):
    """
    Retorna extrato financeiro

    Args:
        data_inicial: date
        data_final: date
        empresa_id: int (opcional, filtra por empresa)

    Returns:
        Lista de MovimentacaoFinanceira ordenada por data DESC
    """
    query = MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.data_movimentacao.between(data_inicial, data_final)
    )

    if empresa_id:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                MovimentacaoFinanceira.empresa_origem_id == empresa_id,
                MovimentacaoFinanceira.empresa_destino_id == empresa_id
            )
        )

    return query.order_by(
        MovimentacaoFinanceira.data_movimentacao.desc(),
        MovimentacaoFinanceira.id.desc()
    ).all()


def registrar_pagamento_despesa_mensal(despesa, valor_pago, empresa_pagadora, usuario=None):
    """
    Registra pagamento de despesa mensal (permite pagamento parcial)

    Args:
        despesa: DespesaMensal
        valor_pago: Decimal - Valor efetivamente pago (pode ser parcial)
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        MovimentacaoFinanceira criada
    """
    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Despesa',
        valor=valor_pago,  # ✅ CORRIGIDO: Usar valor_pago em vez de despesa.valor
        data_movimentacao=despesa.data_pagamento or date.today(),

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Despesa',
        destino_identificacao=f'{despesa.tipo_despesa} - {despesa.mes_competencia}/{despesa.ano_competencia}',

        despesa_mensal_id=despesa.id,

        descricao=f'Pagamento Despesa - {despesa.tipo_despesa} - {despesa.descricao or ""}',
        criado_por=usuario
    )

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def registrar_pagamento_frete_embarque(embarque, valor_pago, empresa_pagadora, usuario=None):
    """
    Registra pagamento de frete de embarque

    Args:
        embarque: EmbarqueMoto
        valor_pago: Decimal
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        MovimentacaoFinanceira criada
    """
    # ✅ Buscar primeiro pedido do embarque para rastreabilidade
    primeiro_ep = embarque.pedidos_rel.first()
    pedido_id = primeiro_ep.pedido_id if primeiro_ep else None
    numero_chassi = None

    # Se o pedido tem itens, pegar primeiro chassi para referência
    if primeiro_ep and primeiro_ep.pedido:
        primeiro_item = primeiro_ep.pedido.itens.first() if hasattr(primeiro_ep.pedido, 'itens') else None
        if primeiro_item:
            numero_chassi = primeiro_item.numero_chassi

    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Frete Embarque',
        valor=valor_pago,
        data_movimentacao=embarque.data_pagamento_frete or date.today(),

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Transportadora',
        destino_identificacao=embarque.transportadora.transportadora if embarque.transportadora else 'Sem Transportadora',

        pedido_id=pedido_id,  # ✅ ASSOCIAR ao primeiro pedido do embarque
        numero_chassi=numero_chassi,  # ✅ Opcional: primeiro chassi para referência
        embarque_moto_id=embarque.id,

        descricao=f'Pagamento Frete Embarque #{embarque.numero_embarque} - {embarque.transportadora.transportadora if embarque.transportadora else "Sem Transp"}',
        criado_por=usuario
    )

    db.session.add(movimentacao)
    db.session.flush()

    return movimentacao


def calcular_saldo_periodo(movimentacoes):
    """
    Calcula saldo acumulado período

    Args:
        movimentacoes: Lista de MovimentacaoFinanceira

    Returns:
        dict com totais
    """
    from decimal import Decimal

    total_recebimentos = sum(
        (m.valor for m in movimentacoes if m.tipo == 'RECEBIMENTO'),
        Decimal('0')
    )

    total_pagamentos = sum(
        (m.valor for m in movimentacoes if m.tipo == 'PAGAMENTO'),
        Decimal('0')
    )

    saldo = total_recebimentos - total_pagamentos

    return {
        'recebimentos': total_recebimentos,
        'pagamentos': total_pagamentos,
        'saldo': saldo
    }
