"""
Service para Comissões - Sistema MotoCHEFE
Gerencia geração de comissões POR MOTO (não mais por pedido)
"""
from app import db
from app.motochefe.models.financeiro import ComissaoVendedor, TituloFinanceiro
from app.motochefe.models.cadastro import VendedorMoto
from app.motochefe.models.vendas import PedidoVendaMotoItem
from decimal import Decimal


def gerar_comissao_moto(titulo_venda):
    """
    Gera comissão para UMA moto específica
    Chamado quando título de VENDA é totalmente pago

    Args:
        titulo_venda: TituloFinanceiro (tipo VENDA, status PAGO)

    Returns:
        list de ComissaoVendedor criadas (uma por vendedor se rateada)
    """
    if titulo_venda.tipo_titulo != 'VENDA':
        raise Exception(f'Título não é de venda: {titulo_venda.tipo_titulo}')

    if titulo_venda.status != 'PAGO':
        raise Exception(f'Título não está pago: {titulo_venda.status}')

    # Verificar se já existe comissão para esta moto
    comissao_existente = db.session.query(ComissaoVendedor).filter_by(
        pedido_id=titulo_venda.pedido_id,
        numero_chassi=titulo_venda.numero_chassi
    ).first()

    if comissao_existente:
        return []  # Já gerou comissão

    pedido = titulo_venda.pedido
    equipe = pedido.vendedor.equipe

    if not equipe:
        raise Exception('Equipe de vendas não encontrada')

    # Buscar item da moto
    item = db.session.query(PedidoVendaMotoItem).filter_by(
        pedido_id=pedido.id,
        numero_chassi=titulo_venda.numero_chassi
    ).first()

    if not item:
        raise Exception(f'Item da moto {titulo_venda.numero_chassi} não encontrado')

    # CALCULAR COMISSÃO
    if equipe.tipo_comissao == 'FIXA_EXCEDENTE':
        comissao_fixa = equipe.valor_comissao_fixa or Decimal('0')
        excedente = item.excedente_tabela  # Propriedade do item
        valor_total_comissao = comissao_fixa + excedente

    elif equipe.tipo_comissao == 'PERCENTUAL':
        # Percentual sobre soma dos 4 títulos da moto (conforme confirmado)
        valor_base = calcular_valor_total_titulos_moto(titulo_venda.pedido_id, titulo_venda.numero_chassi)
        percentual = equipe.percentual_comissao or Decimal('0')
        valor_total_comissao = (valor_base * percentual) / Decimal('100')
        comissao_fixa = Decimal('0')
        excedente = Decimal('0')

    else:
        raise Exception(f'Tipo de comissão desconhecido: {equipe.tipo_comissao}')

    # RATEAR OU NÃO
    if equipe.comissao_rateada:
        # Dividir entre TODOS vendedores da equipe
        vendedores_equipe = VendedorMoto.query.filter_by(
            equipe_vendas_id=equipe.id,
            ativo=True
        ).all()
        qtd_vendedores = len(vendedores_equipe)
        valor_por_vendedor = valor_total_comissao / qtd_vendedores if qtd_vendedores > 0 else Decimal('0')
    else:
        # Apenas vendedor do pedido
        vendedores_equipe = [pedido.vendedor]
        qtd_vendedores = 1
        valor_por_vendedor = valor_total_comissao

    # CRIAR COMISSÕES
    comissoes_criadas = []

    for vendedor in vendedores_equipe:
        comissao = ComissaoVendedor(
            pedido_id=pedido.id,
            numero_chassi=titulo_venda.numero_chassi,
            vendedor_id=vendedor.id,

            valor_comissao_fixa=comissao_fixa / qtd_vendedores if equipe.comissao_rateada else comissao_fixa,
            valor_excedente=excedente / qtd_vendedores if equipe.comissao_rateada else excedente,
            valor_total_comissao=valor_total_comissao,
            qtd_vendedores_equipe=qtd_vendedores,
            valor_rateado=valor_por_vendedor,

            status='PENDENTE'
        )

        db.session.add(comissao)
        db.session.flush()

        comissoes_criadas.append(comissao)

    return comissoes_criadas


def calcular_valor_total_titulos_moto(pedido_id, numero_chassi):
    """
    Calcula valor total dos 4 títulos de uma moto
    Para cálculo de comissão percentual

    Args:
        pedido_id: int
        numero_chassi: str

    Returns:
        Decimal (soma dos 4 títulos)
    """
    from sqlalchemy import func

    total = db.session.query(
        func.sum(TituloFinanceiro.valor_original)
    ).filter_by(
        pedido_id=pedido_id,
        numero_chassi=numero_chassi
    ).scalar() or Decimal('0')

    return total


def pagar_comissao(comissao, empresa_pagadora, usuario=None):
    """
    Efetua pagamento de comissão

    Args:
        comissao: ComissaoVendedor
        empresa_pagadora: EmpresaVendaMoto
        usuario: str

    Returns:
        dict com resultado
    """
    from app.motochefe.services.movimentacao_service import registrar_pagamento_comissao
    from app.motochefe.services.empresa_service import atualizar_saldo
    from datetime import date

    if comissao.status == 'PAGO':
        raise Exception('Comissão já foi paga')

    # 1. Registrar movimentação
    movimentacao = registrar_pagamento_comissao(
        comissao,
        empresa_pagadora,
        usuario
    )

    # 2. Atualizar saldo da empresa
    atualizar_saldo(empresa_pagadora.id, comissao.valor_rateado, 'SUBTRAIR')

    # 3. Atualizar comissão
    comissao.data_pagamento = date.today()
    comissao.status = 'PAGO'
    comissao.atualizado_por = usuario

    db.session.flush()

    return {
        'success': True,
        'comissao': comissao,
        'movimentacao': movimentacao
    }


def listar_comissoes_pendentes(vendedor_id=None):
    """
    Lista comissões pendentes

    Args:
        vendedor_id: int (opcional)

    Returns:
        list de ComissaoVendedor
    """
    query = ComissaoVendedor.query.filter_by(status='PENDENTE')

    if vendedor_id:
        query = query.filter_by(vendedor_id=vendedor_id)

    return query.order_by(ComissaoVendedor.criado_em.desc()).all()
