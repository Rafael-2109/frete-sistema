"""
Service para Baixa Automática de Motos - Sistema MotoCHEFE
Paga motos pendentes via FIFO quando empresa.baixa_compra_auto = True
"""
from app import db
from app.motochefe.models.produto import Moto
from app.motochefe.services.movimentacao_service import registrar_pagamento_custo_moto
from app.motochefe.services.empresa_service import atualizar_saldo
from datetime import date
from decimal import Decimal


def processar_baixa_automatica_motos(empresa, valor_disponivel, movimentacao_recebimento_id=None, usuario=None):
    """
    Paga motos pendentes via FIFO
    Executado quando empresa.baixa_compra_auto = True

    Args:
        empresa: EmpresaVendaMoto
        valor_disponivel: Decimal (valor do recebimento)
        movimentacao_recebimento_id: int (ID da movimentação que originou)
        usuario: str

    Returns:
        dict com resultado:
        {
            'motos_pagas': list,
            'valor_utilizado': Decimal,
            'valor_sobra': Decimal,
            'total_motos': int
        }
    """
    if not empresa.baixa_compra_auto:
        return {
            'motos_pagas': [],
            'valor_utilizado': Decimal('0'),
            'valor_sobra': valor_disponivel,
            'total_motos': 0
        }

    # 1. BUSCAR MOTOS PENDENTES (FIFO por data_entrada)
    motos_pendentes = Moto.query.filter(
        Moto.status_pagamento_custo != 'PAGO',
        Moto.ativo == True
    ).order_by(Moto.data_entrada.asc()).all()

    if not motos_pendentes:
        return {
            'motos_pagas': [],
            'valor_utilizado': Decimal('0'),
            'valor_sobra': valor_disponivel,
            'total_motos': 0
        }

    # 2. DISTRIBUIR VALOR ENTRE MOTOS
    motos_pagas = []
    valor_restante = valor_disponivel

    for moto in motos_pendentes:
        if valor_restante <= 0:
            break

        # Calcular saldo devedor da moto
        saldo_devedor = moto.custo_aquisicao - (moto.custo_pago or Decimal('0'))

        if saldo_devedor <= 0:
            continue  # Moto já paga

        # Calcular quanto pagar desta moto
        valor_pagar_moto = min(valor_restante, saldo_devedor)

        # 3. REGISTRAR PAGAMENTO
        movimentacao = registrar_pagamento_custo_moto(
            moto=moto,
            valor_pago=valor_pagar_moto,
            empresa_pagadora=empresa,
            usuario=usuario or 'SISTEMA',
            eh_baixa_auto=True,
            mov_origem_id=movimentacao_recebimento_id
        )

        # 4. ATUALIZAR MOTO
        moto.custo_pago = (moto.custo_pago or Decimal('0')) + valor_pagar_moto

        if moto.custo_pago >= moto.custo_aquisicao:
            moto.status_pagamento_custo = 'PAGO'
            moto.data_pagamento_custo = date.today()
        else:
            moto.status_pagamento_custo = 'PARCIAL'

        # 5. ATUALIZAR SALDO DA EMPRESA
        atualizar_saldo(empresa.id, valor_pagar_moto, 'SUBTRAIR')

        # 6. REDUZIR VALOR DISPONÍVEL
        valor_restante -= valor_pagar_moto

        motos_pagas.append({
            'moto': moto,
            'valor_pago': valor_pagar_moto,
            'saldo_apos': moto.custo_aquisicao - moto.custo_pago,
            'movimentacao_id': movimentacao.id
        })

    db.session.flush()

    valor_utilizado = valor_disponivel - valor_restante

    return {
        'motos_pagas': motos_pagas,
        'valor_utilizado': valor_utilizado,
        'valor_sobra': valor_restante,
        'total_motos': len(motos_pagas)
    }


def verificar_motos_pendentes():
    """
    Retorna motos com pagamento pendente ou parcial

    Returns:
        dict com estatísticas
    """
    from sqlalchemy import func

    pendentes = Moto.query.filter(
        Moto.status_pagamento_custo == 'PENDENTE',
        Moto.ativo == True
    ).count()

    parciais = Moto.query.filter(
        Moto.status_pagamento_custo == 'PARCIAL',
        Moto.ativo == True
    ).count()

    total_devedor = db.session.query(
        func.sum(Moto.custo_aquisicao - func.coalesce(Moto.custo_pago, 0))
    ).filter(
        Moto.status_pagamento_custo != 'PAGO',
        Moto.ativo == True
    ).scalar() or Decimal('0')

    return {
        'motos_pendentes': pendentes,
        'motos_parciais': parciais,
        'total_motos': pendentes + parciais,
        'total_devedor': total_devedor
    }


def simular_baixa_automatica(empresa, valor_disponivel):
    """
    Simula baixa automática SEM executar
    Útil para preview

    Args:
        empresa: EmpresaVendaMoto
        valor_disponivel: Decimal

    Returns:
        dict com simulação
    """
    if not empresa.baixa_compra_auto:
        return {'erro': 'Empresa não tem baixa automática ativada'}

    # Buscar motos FIFO
    motos_pendentes = Moto.query.filter(
        Moto.status_pagamento_custo != 'PAGO',
        Moto.ativo == True
    ).order_by(Moto.data_entrada.asc()).all()

    simulacao = []
    valor_restante = valor_disponivel

    for moto in motos_pendentes:
        if valor_restante <= 0:
            break

        saldo_devedor = moto.custo_aquisicao - (moto.custo_pago or Decimal('0'))

        if saldo_devedor <= 0:
            continue

        valor_pagar = min(valor_restante, saldo_devedor)
        valor_restante -= valor_pagar

        simulacao.append({
            'chassi': moto.numero_chassi,
            'fornecedor': moto.fornecedor,
            'custo_total': moto.custo_aquisicao,
            'ja_pago': moto.custo_pago or Decimal('0'),
            'devedor': saldo_devedor,
            'valor_a_pagar': valor_pagar,
            'ficara_devendo': saldo_devedor - valor_pagar
        })

    return {
        'motos_a_pagar': simulacao,
        'total_motos': len(simulacao),
        'valor_utilizado': valor_disponivel - valor_restante,
        'valor_sobra': valor_restante
    }
