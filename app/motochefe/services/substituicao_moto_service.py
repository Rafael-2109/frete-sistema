"""
Service de Substituição de Motos em Pedidos
Gerencia substituição de motos em pedidos com ajuste automático de títulos
"""
from decimal import Decimal
from datetime import datetime
from app import db
from app.motochefe.models import (
    PedidoVendaMoto, PedidoVendaMotoItem, Moto, TituloFinanceiro,
    ModeloMoto
)


def substituir_moto_pedido(
    pedido_id: int,
    chassi_antigo: str,
    chassi_novo: str,
    preco_novo: Decimal,
    motivo: str,
    observacao: str,
    usuario: str
) -> dict:
    """
    Substitui uma moto em um pedido

    Args:
        pedido_id: ID do pedido
        chassi_antigo: Chassi da moto a ser substituída
        chassi_novo: Chassi da moto nova
        preco_novo: Preço da nova moto (editável pelo usuário)
        motivo: Motivo da substituição ('AVARIA' ou 'OUTROS')
        observacao: Observação sobre a substituição
        usuario: Nome do usuário que fez a substituição

    Returns:
        dict com informações da substituição

    Raises:
        Exception: Se houver qualquer erro na substituição
    """

    # 1. BUSCAR PEDIDO E VALIDAR
    pedido = db.session.get(PedidoVendaMoto,pedido_id) if pedido_id else None
    if not pedido:
        raise Exception(f'Pedido {pedido_id} não encontrado')

    # 2. BUSCAR ITEM DO PEDIDO COM MOTO ANTIGA
    item_antigo = db.session.query(PedidoVendaMotoItem).filter_by(
        pedido_id=pedido_id,
        numero_chassi=chassi_antigo,
        ativo=True
    ).first()

    if not item_antigo:
        raise Exception(f'Moto {chassi_antigo} não encontrada neste pedido')

    # 3. BUSCAR MOTOS
    moto_antiga = db.session.get(Moto,chassi_antigo) if chassi_antigo else None
    moto_nova = db.session.get(Moto,chassi_novo) if chassi_novo else None

    if not moto_antiga or not moto_nova:
        raise Exception('Moto antiga ou nova não encontrada')

    if not moto_nova.disponivel_para_venda:
        raise Exception(f'Moto {chassi_novo} não está disponível para venda')

    # 4. CALCULAR DIFERENÇA DE PREÇO
    preco_antigo = item_antigo.preco_venda
    # preco_novo já vem como parâmetro (editável pelo usuário)
    diferenca = preco_novo - preco_antigo

    # 5. REGISTRAR OBSERVAÇÃO NA MOTO ANTIGA
    if motivo == 'AVARIA':
        moto_antiga.status = 'AVARIADO'
        moto_antiga.observacao = f"Avaria detectada - Substituída em pedido {pedido.numero_pedido}\n{observacao}"
    else:
        # Motivo 'OUTROS'
        if moto_antiga.observacao:
            moto_antiga.observacao += f"\n\nSubstituída em pedido {pedido.numero_pedido} (Motivo: {motivo})\n{observacao}"
        else:
            moto_antiga.observacao = f"Substituída em pedido {pedido.numero_pedido} (Motivo: {motivo})\n{observacao}"

    moto_antiga.atualizado_por = usuario

    # 6. LIBERAR MOTO ANTIGA (se não foi marcada como avariada)
    if motivo != 'AVARIA':
        moto_antiga.reservado = False
        moto_antiga.status = 'DISPONIVEL'
    else:
        moto_antiga.reservado = False  # Libera reserva mesmo marcando como avariada

    # 7. RESERVAR MOTO NOVA
    moto_nova.reservado = True
    moto_nova.status = 'RESERVADA'
    moto_nova.atualizado_por = usuario

    # 8. REMOVER ITEM ANTIGO DO PEDIDO E CRIAR NOVO
    db.session.delete(item_antigo)  # Remove fisicamente do pedido
    db.session.flush()  # Garante que foi removido antes de criar novo

    # Criar novo item
    novo_item = PedidoVendaMotoItem(
        pedido_id=pedido_id,
        numero_chassi=chassi_novo,
        preco_venda=preco_novo,
        montagem_contratada=item_antigo.montagem_contratada,
        valor_montagem=item_antigo.valor_montagem,
        fornecedor_montagem=item_antigo.fornecedor_montagem,
        montagem_paga=item_antigo.montagem_paga,
        data_pagamento_montagem=item_antigo.data_pagamento_montagem,
        criado_por=usuario
    )
    db.session.add(novo_item)
    db.session.flush()

    # 9. AJUSTAR VALOR TOTAL DO PEDIDO
    pedido.valor_total_pedido += diferenca
    pedido.atualizado_por = usuario

    # 10. AJUSTAR TÍTULO FINANCEIRO DE VENDA DA MOTO
    # Buscar título de venda da moto antiga (que não esteja cancelado)
    titulo_venda = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        numero_chassi=chassi_antigo,
        tipo_titulo='VENDA'
    ).filter(
        TituloFinanceiro.status != 'CANCELADO'
    ).first()

    resultado_ajuste_titulo = None

    if titulo_venda:
        valor_original_titulo = titulo_venda.valor_original
        valor_saldo_titulo = titulo_venda.valor_saldo
        valor_pago = valor_original_titulo - valor_saldo_titulo

        # Calcular novo valor do título
        novo_valor_titulo = preco_novo

        # Ajustar título
        titulo_venda.valor_original = novo_valor_titulo
        titulo_venda.numero_chassi = chassi_novo  # Atualizar chassi

        # Lógica de ajuste do saldo baseada no valor pago
        if valor_pago > 0:
            # Já houve pagamento
            novo_saldo = novo_valor_titulo - valor_pago

            if novo_saldo < 0:
                # Valor pago excede novo valor (moto nova mais barata)
                # Tratar excedente como novo pagamento (crédito)
                titulo_venda.valor_saldo = Decimal('0.00')
                titulo_venda.status = 'PAGO'
                resultado_ajuste_titulo = {
                    'tipo': 'CREDITO',
                    'valor_credito': abs(novo_saldo),
                    'mensagem': f'Moto nova mais barata. Crédito de R$ {abs(novo_saldo):.2f} gerado'
                }
            else:
                # Valor pago menor que novo valor (moto nova mais cara)
                titulo_venda.valor_saldo = novo_saldo
                titulo_venda.status = 'ABERTO'
                resultado_ajuste_titulo = {
                    'tipo': 'DEBITO',
                    'valor_debito': novo_saldo,
                    'mensagem': f'Saldo restante atualizado para R$ {novo_saldo:.2f}'
                }
        else:
            # Ainda não houve pagamento
            titulo_venda.valor_saldo = novo_valor_titulo
            resultado_ajuste_titulo = {
                'tipo': 'AJUSTE_SIMPLES',
                'mensagem': f'Valor do título atualizado de R$ {valor_original_titulo:.2f} para R$ {novo_valor_titulo:.2f}'
            }

        titulo_venda.atualizado_por = usuario

    # 11. COMMIT
    db.session.commit()

    return {
        'sucesso': True,
        'pedido': pedido,
        'item_antigo': item_antigo,
        'item_novo': novo_item,
        'moto_antiga': moto_antiga,
        'moto_nova': moto_nova,
        'preco_antigo': float(preco_antigo),
        'preco_novo': float(preco_novo),
        'diferenca': float(diferenca),
        'resultado_ajuste_titulo': resultado_ajuste_titulo
    }


def buscar_motos_disponiveis_agrupadas(modelo_id_referencia: int, cor_referencia: str):
    """
    Busca motos disponíveis agrupadas com priorização:
    1. Mesmo modelo_id + mesma cor
    2. Mesmo modelo_id + cores diferentes
    3. Mesma cor + modelos diferentes
    4. Resto (modelo e cor diferentes)

    Args:
        modelo_id_referencia: ID do modelo da moto original
        cor_referencia: Cor da moto original

    Returns:
        dict com motos agrupadas por prioridade
    """

    # Buscar todas as motos disponíveis
    motos_disponiveis = Moto.query.filter_by(
        status='DISPONIVEL',
        reservado=False,
        ativo=True
    ).order_by(Moto.data_entrada.asc()).all()  # FIFO

    # Agrupar por prioridade
    grupos = {
        'mesmo_modelo_mesma_cor': [],
        'mesmo_modelo': [],
        'mesma_cor': [],
        'outros': []
    }

    for moto in motos_disponiveis:
        mesmo_modelo = moto.modelo_id == modelo_id_referencia
        mesma_cor = moto.cor.upper() == cor_referencia.upper()

        if mesmo_modelo and mesma_cor:
            grupos['mesmo_modelo_mesma_cor'].append(moto)
        elif mesmo_modelo:
            grupos['mesmo_modelo'].append(moto)
        elif mesma_cor:
            grupos['mesma_cor'].append(moto)
        else:
            grupos['outros'].append(moto)

    return grupos
