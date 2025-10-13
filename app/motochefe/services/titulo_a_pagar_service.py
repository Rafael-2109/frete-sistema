"""
Service para Títulos A Pagar - Sistema MotoCHEFE
Gerencia criação e liberação de títulos a pagar (Movimentação e Montagem)
"""
from app import db
from app.motochefe.models.financeiro import TituloAPagar
from app.motochefe.models.operacional import CustosOperacionais
from app.motochefe.services.empresa_service import garantir_margem_sogima
from datetime import date
from decimal import Decimal


def criar_titulo_a_pagar_movimentacao(titulo_financeiro, custo_real_movimentacao):
    """
    Cria título a pagar para Movimentação → MargemSogima

    ✅ LÓGICA CORRIGIDA:
    - titulo_financeiro.valor_original = o que CLIENTE paga (R$ 0 ou R$ 50)
    - custo_real_movimentacao = o que EMPRESA paga MargemSogima (SEMPRE R$ 50)

    Args:
        titulo_financeiro: TituloFinanceiro (tipo MOVIMENTACAO)
        custo_real_movimentacao: Decimal - Custo REAL que empresa paga (sempre > 0)

    Returns:
        TituloAPagar criado
    """
    if titulo_financeiro.tipo_titulo != 'MOVIMENTACAO':
        raise Exception(f'Título não é de movimentação: {titulo_financeiro.tipo_titulo}')

    # Garantir que MargemSogima existe
    margem_sogima = garantir_margem_sogima()

    titulo_pagar = TituloAPagar(
        tipo='MOVIMENTACAO',
        titulo_financeiro_id=titulo_financeiro.id,
        pedido_id=titulo_financeiro.pedido_id,
        numero_chassi=titulo_financeiro.numero_chassi,

        empresa_destino_id=margem_sogima.id,
        fornecedor_montagem=None,

        # ✅ CORRIGIDO: Usa custo REAL, não valor que cliente paga
        valor_original=custo_real_movimentacao,
        valor_saldo=custo_real_movimentacao,
        valor_pago=0,

        data_criacao=date.today(),
        status='PENDENTE',  # Bloqueado até cliente pagar totalmente

        criado_por='SISTEMA'
    )

    db.session.add(titulo_pagar)
    db.session.flush()

    return titulo_pagar


def criar_titulo_a_pagar_montagem(titulo_financeiro, item_pedido):
    """
    Cria título a pagar para Montagem → Equipe Montagem
    Usa CUSTO REAL de CustosOperacionais (não o valor cobrado)

    Args:
        titulo_financeiro: TituloFinanceiro (tipo MONTAGEM)
        item_pedido: PedidoVendaMotoItem

    Returns:
        TituloAPagar criado ou None (se não tem montagem)
    """
    if titulo_financeiro.tipo_titulo != 'MONTAGEM':
        raise Exception(f'Título não é de montagem: {titulo_financeiro.tipo_titulo}')

    if not item_pedido.montagem_contratada:
        return None  # Sem montagem, não cria título

    # Buscar custo REAL da montagem
    custos = CustosOperacionais.get_custos_vigentes()

    if not custos:
        raise Exception('Custos operacionais vigentes não encontrados')

    valor_custo_real = custos.custo_montagem

    titulo_pagar = TituloAPagar(
        tipo='MONTAGEM',
        titulo_financeiro_id=titulo_financeiro.id,
        pedido_id=titulo_financeiro.pedido_id,
        numero_chassi=titulo_financeiro.numero_chassi,

        empresa_destino_id=None,
        fornecedor_montagem=item_pedido.fornecedor_montagem or 'Equipe Montagem',

        valor_original=valor_custo_real,  # CUSTO REAL
        valor_saldo=valor_custo_real,
        valor_pago=0,

        data_criacao=date.today(),
        status='PENDENTE',  # Bloqueado até cliente pagar totalmente

        criado_por='SISTEMA'
    )

    db.session.add(titulo_pagar)
    db.session.flush()

    return titulo_pagar


def liberar_titulo_a_pagar(titulo_financeiro_id):
    """
    Libera título a pagar quando cliente pagou título origem totalmente
    Muda status de PENDENTE → ABERTO

    Args:
        titulo_financeiro_id: int

    Returns:
        TituloAPagar atualizado ou None
    """
    titulo_pagar = TituloAPagar.query.filter_by(
        titulo_financeiro_id=titulo_financeiro_id,
        status='PENDENTE'
    ).first()

    if not titulo_pagar:
        return None  # Já foi liberado ou não existe

    titulo_pagar.status = 'ABERTO'
    titulo_pagar.data_liberacao = date.today()

    db.session.flush()

    return titulo_pagar


def quitar_titulo_movimentacao_ao_pagar_moto(numero_chassi, pedido_id, usuario=None):
    """
    Quita automaticamente TituloAPagar de MOVIMENTACAO quando cliente quitar a moto (VENDA)
    Usado quando incluir_custo_movimentacao=False (TituloFinanceiro MOVIMENTACAO tem valor=0)

    Args:
        numero_chassi: str
        pedido_id: int
        usuario: str

    Returns:
        TituloAPagar quitado ou None
    """
    from app.motochefe.models.financeiro import TituloFinanceiro

    # Buscar TituloFinanceiro MOVIMENTACAO desta moto
    titulo_mov = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        numero_chassi=numero_chassi,
        tipo_titulo='MOVIMENTACAO'
    ).first()

    if not titulo_mov:
        return None

    # ✅ Validação EXPLÍCITA: Só quita se valor_original = 0 (empresa absorveu custo)
    if titulo_mov.valor_original != Decimal('0'):
        return None

    # ✅ Marcar TituloFinanceiro MOVIMENTACAO como PAGO automaticamente
    if titulo_mov.status != 'PAGO':
        titulo_mov.status = 'PAGO'
        titulo_mov.valor_pago_total = Decimal('0')
        titulo_mov.valor_saldo = Decimal('0')
        titulo_mov.data_ultimo_pagamento = date.today()
        titulo_mov.atualizado_por = usuario

    # Buscar TituloAPagar correspondente
    titulo_pagar = TituloAPagar.query.filter_by(
        pedido_id=pedido_id,
        numero_chassi=numero_chassi,
        tipo='MOVIMENTACAO'
    ).filter(
        TituloAPagar.status.in_(['PENDENTE', 'ABERTO'])
    ).first()

    if not titulo_pagar:
        return None

    # Liberar TituloAPagar (mudar de PENDENTE para ABERTO)
    if titulo_pagar.status == 'PENDENTE':
        titulo_pagar.status = 'ABERTO'
        titulo_pagar.data_liberacao = date.today()
        titulo_pagar.atualizado_por = usuario

    db.session.flush()

    return titulo_pagar


def pagar_titulo_a_pagar(titulo_pagar, valor_pago, empresa_pagadora, usuario=None):
    """
    Efetua pagamento de título a pagar

    Args:
        titulo_pagar: TituloAPagar
        valor_pago: Decimal
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        dict com resultado
    """
    from app.motochefe.services.movimentacao_service import registrar_pagamento_titulo_a_pagar
    from app.motochefe.services.empresa_service import atualizar_saldo

    # Validar status
    if not titulo_pagar.pode_pagar:
        raise Exception(f'Título não pode ser pago. Status: {titulo_pagar.status}')

    # Validar valor
    if valor_pago > titulo_pagar.valor_saldo:
        raise Exception(f'Valor pago (R$ {valor_pago}) excede saldo devedor (R$ {titulo_pagar.valor_saldo})')

    # 1. Registrar movimentação
    movimentacao = registrar_pagamento_titulo_a_pagar(
        titulo_pagar,
        valor_pago,
        empresa_pagadora,
        usuario
    )

    # 2. Atualizar saldos
    # Origem: sempre subtrai
    atualizar_saldo(empresa_pagadora.id, valor_pago, 'SUBTRAIR')

    # Destino: só soma se for MOVIMENTACAO (para MargemSogima)
    if titulo_pagar.tipo == 'MOVIMENTACAO' and titulo_pagar.empresa_destino_id:
        atualizar_saldo(titulo_pagar.empresa_destino_id, valor_pago, 'SOMAR')

    # 3. Atualizar título a pagar
    titulo_pagar.valor_pago += valor_pago
    titulo_pagar.valor_saldo -= valor_pago
    titulo_pagar.atualizado_por = usuario

    if titulo_pagar.valor_saldo <= 0:
        titulo_pagar.status = 'PAGO'
        titulo_pagar.data_pagamento = date.today()

        # ✅ SINCRONIZAÇÃO: Atualizar PedidoVendaMotoItem.montagem_paga
        if titulo_pagar.tipo == 'MONTAGEM':
            from app.motochefe.models.vendas import PedidoVendaMotoItem
            item = PedidoVendaMotoItem.query.filter_by(
                pedido_id=titulo_pagar.pedido_id,
                numero_chassi=titulo_pagar.numero_chassi
            ).first()
            if item:
                item.montagem_paga = True
                item.data_pagamento_montagem = date.today()
    else:
        titulo_pagar.status = 'PARCIAL'

    db.session.flush()

    return {
        'success': True,
        'titulo_pagar': titulo_pagar,
        'movimentacao': movimentacao,
        'saldo_restante': titulo_pagar.valor_saldo
    }


def listar_titulos_a_pagar(status=None, tipo=None, pedido_id=None):
    """
    Lista títulos a pagar com filtros

    Args:
        status: str (PENDENTE, ABERTO, PAGO, PARCIAL)
        tipo: str (MOVIMENTACAO, MONTAGEM)
        pedido_id: int

    Returns:
        Lista de TituloAPagar
    """
    query = TituloAPagar.query

    if status:
        query = query.filter_by(status=status)

    if tipo:
        query = query.filter_by(tipo=tipo)

    if pedido_id:
        query = query.filter_by(pedido_id=pedido_id)

    return query.order_by(
        TituloAPagar.data_criacao.desc(),
        TituloAPagar.id.desc()
    ).all()
