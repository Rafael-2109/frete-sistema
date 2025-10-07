"""
Service para Títulos Financeiros - Sistema MotoCHEFE
Gerencia geração de títulos por moto e pagamentos parciais
"""
from app import db
from app.motochefe.models.financeiro import TituloFinanceiro
from app.motochefe.models.cadastro import EquipeVendasMoto
from datetime import date
from decimal import Decimal


def gerar_titulos_por_moto(pedido, item_pedido, valores):
    """
    Gera 4 títulos para uma moto (Movimentação, Montagem, Frete, Venda)

    Args:
        pedido: PedidoVendaMoto
        item_pedido: PedidoVendaMotoItem
        valores: dict {
            'movimentacao': Decimal,
            'montagem': Decimal,
            'frete': Decimal,
            'venda': Decimal
        }

    Returns:
        list de TituloFinanceiro criados
    """
    titulos_criados = []

    # Ordem de pagamento definida
    tipos_titulo = [
        ('MOVIMENTACAO', 1, valores['movimentacao']),
        ('MONTAGEM', 2, valores['montagem']),
        ('FRETE', 3, valores['frete']),
        ('VENDA', 4, valores['venda'])
    ]

    for tipo, ordem, valor in tipos_titulo:
        # Pular montagem se não contratada
        if tipo == 'MONTAGEM' and not item_pedido.montagem_contratada:
            continue

        # Pular se valor zerado
        if valor <= 0:
            continue

        titulo = TituloFinanceiro(
            pedido_id=pedido.id,
            numero_chassi=item_pedido.numero_chassi,
            tipo_titulo=tipo,
            ordem_pagamento=ordem,
            numero_parcela=1,
            valor_original=valor,
            valor_saldo=valor,
            valor_pago_total=0,
            data_emissao=date.today(),
            empresa_recebedora_id=None,  # Definido no pagamento
            status='RASCUNHO',  # Muda para ABERTO no faturamento
            criado_por='SISTEMA'
        )

        db.session.add(titulo)
        db.session.flush()

        titulos_criados.append(titulo)

    return titulos_criados


def calcular_valores_titulos_moto(item_pedido, equipe):
    """
    Calcula valores dos 4 títulos para uma moto

    Args:
        item_pedido: PedidoVendaMotoItem
        equipe: EquipeVendasMoto

    Returns:
        dict com valores
    """
    # MOVIMENTAÇÃO: Conforme configuração da equipe
    valor_movimentacao = equipe.custo_movimentacao if equipe.incluir_custo_movimentacao else Decimal('0')

    # MONTAGEM: Valor cobrado do cliente (custo real será usado no título a pagar)
    valor_montagem = item_pedido.valor_montagem if item_pedido.montagem_contratada else Decimal('0')

    # FRETE: Conforme pedido (rateado por moto)
    # TODO: Implementar rateio de frete por moto
    valor_frete = Decimal('0')  # Simplificado por enquanto

    # VENDA: Preço de venda
    valor_venda = item_pedido.preco_venda

    return {
        'movimentacao': valor_movimentacao,
        'montagem': valor_montagem,
        'frete': valor_frete,
        'venda': valor_venda
    }


def receber_titulo(titulo, valor_recebido, empresa_recebedora, usuario=None):
    """
    Processa recebimento de título (total ou parcial)

    Args:
        titulo: TituloFinanceiro
        valor_recebido: Decimal
        empresa_recebedora: EmpresaVendaMoto
        usuario: str

    Returns:
        dict com resultado
    """
    from app.motochefe.services.movimentacao_service import registrar_recebimento_titulo
    from app.motochefe.services.empresa_service import atualizar_saldo
    from app.motochefe.services.titulo_a_pagar_service import liberar_titulo_a_pagar
    from app.motochefe.services.baixa_automatica_service import processar_baixa_automatica_motos

    # Validar valor
    if valor_recebido > titulo.valor_saldo:
        raise Exception(f'Valor recebido (R$ {valor_recebido}) excede saldo devedor (R$ {titulo.valor_saldo})')

    # 1. REGISTRAR MOVIMENTAÇÃO
    movimentacao = registrar_recebimento_titulo(
        titulo,
        valor_recebido,
        empresa_recebedora,
        usuario
    )

    # 2. ATUALIZAR SALDO DA EMPRESA
    atualizar_saldo(empresa_recebedora.id, valor_recebido, 'SOMAR')

    # 3. ATUALIZAR TÍTULO
    titulo.valor_pago_total += valor_recebido
    titulo.valor_saldo -= valor_recebido
    titulo.empresa_recebedora_id = empresa_recebedora.id
    titulo.data_ultimo_pagamento = date.today()
    titulo.atualizado_por = usuario

    resultado = {
        'titulo': titulo,
        'movimentacao': movimentacao,
        'totalmente_pago': False,
        'titulo_a_pagar_liberado': None,
        'baixa_automatica': None,
        'comissao_gerada': None
    }

    # 4. VERIFICAR SE TOTALMENTE PAGO
    if titulo.valor_saldo <= 0:
        titulo.status = 'PAGO'
        resultado['totalmente_pago'] = True

        # TRIGGER 1: Liberar Título A Pagar
        titulo_pagar = liberar_titulo_a_pagar(titulo.id)
        if titulo_pagar:
            resultado['titulo_a_pagar_liberado'] = titulo_pagar

        # TRIGGER 2: Baixa Automática
        if empresa_recebedora.baixa_compra_auto:
            resultado_baixa = processar_baixa_automatica_motos(
                empresa_recebedora,
                valor_recebido,
                movimentacao.id,
                usuario
            )
            resultado['baixa_automatica'] = resultado_baixa

        # TRIGGER 3: Comissão (se título de VENDA)
        if titulo.tipo_titulo == 'VENDA':
            from app.motochefe.services.comissao_service import gerar_comissao_moto
            comissao = gerar_comissao_moto(titulo)
            resultado['comissao_gerada'] = comissao

    else:
        # PAGAMENTO PARCIAL - continua ABERTO
        titulo.status = 'ABERTO'

    db.session.flush()

    return resultado


def renumerar_parcelas_pedido(pedido_id, parcela_atual):
    """
    Renumera todos os títulos ABERTOS da parcela atual para parcela+1

    Args:
        pedido_id: int
        parcela_atual: int

    Returns:
        int (quantidade de títulos renumerados)
    """
    titulos_abertos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        numero_parcela=parcela_atual,
        status='ABERTO'
    ).all()

    for titulo in titulos_abertos:
        titulo.numero_parcela = parcela_atual + 1

    db.session.flush()

    return len(titulos_abertos)


def obter_titulos_por_pedido_agrupados(pedido_id):
    """
    Retorna títulos agrupados por parcela > moto > tipo
    Para exibir em accordion

    Args:
        pedido_id: int

    Returns:
        dict estruturado para accordion
    """
    titulos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id
    ).order_by(
        TituloFinanceiro.numero_parcela,
        TituloFinanceiro.numero_chassi,
        TituloFinanceiro.ordem_pagamento
    ).all()

    # Agrupar
    agrupado = {}

    for titulo in titulos:
        parcela = titulo.numero_parcela

        if parcela not in agrupado:
            agrupado[parcela] = {}

        chassi = titulo.numero_chassi

        if chassi not in agrupado[parcela]:
            agrupado[parcela][chassi] = []

        agrupado[parcela][chassi].append(titulo)

    return agrupado
