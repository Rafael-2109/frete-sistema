"""
Service Orquestrador para Pedidos - Sistema MotoCHEFE
Gerencia emissão completa de pedidos com títulos financeiros e títulos a pagar
"""
from app import db
from app.motochefe.models.vendas import PedidoVendaMoto, PedidoVendaMotoItem
from app.motochefe.models.produto import Moto
from app.motochefe.services.titulo_service import gerar_titulos_por_moto, calcular_valores_titulos_moto
from app.motochefe.services.titulo_a_pagar_service import (
    criar_titulo_a_pagar_movimentacao,
    criar_titulo_a_pagar_montagem
)
from decimal import Decimal


def criar_pedido_completo(dados_pedido, itens_json):
    """
    Cria pedido com alocação FIFO + títulos financeiros + títulos a pagar

    Args:
        dados_pedido: dict com dados do pedido
        itens_json: list de dicts com itens [
            {
                'modelo_id': int,
                'cor': str,
                'quantidade': int,
                'preco_venda': Decimal,
                'montagem': bool,
                'valor_montagem': Decimal,
                'fornecedor_montagem': str
            }
        ]

    Returns:
        dict {
            'pedido': PedidoVendaMoto,
            'itens': list de PedidoVendaMotoItem,
            'titulos_financeiros': list de TituloFinanceiro,
            'titulos_a_pagar': list de TituloAPagar
        }
    """
    # 1. CRIAR PEDIDO
    pedido = PedidoVendaMoto(
        numero_pedido=dados_pedido['numero_pedido'],
        cliente_id=dados_pedido['cliente_id'],
        vendedor_id=dados_pedido['vendedor_id'],
        equipe_vendas_id=dados_pedido.get('equipe_vendas_id'),
        data_pedido=dados_pedido.get('data_pedido'),
        data_expedicao=dados_pedido.get('data_expedicao'),
        valor_total_pedido=dados_pedido['valor_total_pedido'],
        valor_frete_cliente=dados_pedido.get('valor_frete_cliente', 0),
        forma_pagamento=dados_pedido.get('forma_pagamento'),
        condicao_pagamento=dados_pedido.get('condicao_pagamento'),
        transportadora_id=dados_pedido.get('transportadora_id'),
        tipo_frete=dados_pedido.get('tipo_frete'),
        observacoes=dados_pedido.get('observacoes'),
        criado_por=dados_pedido.get('criado_por', 'SISTEMA')
    )

    db.session.add(pedido)
    db.session.flush()

    # 2. PROCESSAR ITENS
    itens_criados = []
    titulos_financeiros_criados = []
    titulos_a_pagar_criados = []

    for item_data in itens_json:
        modelo_id = item_data['modelo_id']
        cor = item_data['cor']
        quantidade = int(item_data['quantidade'])
        preco_venda = Decimal(str(item_data['preco_venda']))
        montagem = item_data.get('montagem', False)
        valor_montagem = Decimal(str(item_data.get('valor_montagem', 0)))
        fornecedor_montagem = item_data.get('fornecedor_montagem')

        # 3. ALOCAR MOTOS (FIFO)
        motos_disponiveis = Moto.query.filter_by(
            modelo_id=modelo_id,
            cor=cor,
            status='DISPONIVEL',
            reservado=False,
            ativo=True
        ).order_by(Moto.data_entrada.asc()).limit(quantidade).all()

        if len(motos_disponiveis) < quantidade:
            raise Exception(
                f'Estoque insuficiente para modelo ID {modelo_id} cor {cor}. '
                f'Disponível: {len(motos_disponiveis)}, Solicitado: {quantidade}'
            )

        # 4. CRIAR ITENS E TÍTULOS POR MOTO
        for moto in motos_disponiveis:
            # Criar item
            item = PedidoVendaMotoItem(
                pedido_id=pedido.id,
                numero_chassi=moto.numero_chassi,
                preco_venda=preco_venda,
                montagem_contratada=montagem,
                valor_montagem=valor_montagem if montagem else 0,
                fornecedor_montagem=fornecedor_montagem if montagem else None,
                criado_por=dados_pedido.get('criado_por', 'SISTEMA')
            )
            db.session.add(item)
            db.session.flush()

            itens_criados.append(item)

            # Reservar moto
            moto.status = 'RESERVADA'
            moto.reservado = True

            # Calcular valores dos títulos
            equipe = pedido.vendedor.equipe
            valores = calcular_valores_titulos_moto(item, equipe)

            # Gerar 4 títulos financeiros (Movimentação, Montagem, Frete, Venda)
            titulos = gerar_titulos_por_moto(pedido, item, valores)
            titulos_financeiros_criados.extend(titulos)

            # Criar títulos a pagar (PENDENTES)
            for titulo in titulos:
                if titulo.tipo_titulo == 'MOVIMENTACAO':
                    titulo_pagar = criar_titulo_a_pagar_movimentacao(titulo)
                    if titulo_pagar:
                        titulos_a_pagar_criados.append(titulo_pagar)

                elif titulo.tipo_titulo == 'MONTAGEM' and item.montagem_contratada:
                    titulo_pagar = criar_titulo_a_pagar_montagem(titulo, item)
                    if titulo_pagar:
                        titulos_a_pagar_criados.append(titulo_pagar)

    db.session.flush()

    return {
        'pedido': pedido,
        'itens': itens_criados,
        'titulos_financeiros': titulos_financeiros_criados,
        'titulos_a_pagar': titulos_a_pagar_criados
    }


def faturar_pedido_completo(pedido, empresa_id, numero_nf, data_nf):
    """
    Fatura pedido: atualiza NF, calcula vencimentos, muda status

    Args:
        pedido: PedidoVendaMoto
        empresa_id: int
        numero_nf: str
        data_nf: date

    Returns:
        dict com resultado
    """
    from datetime import timedelta

    if pedido.faturado:
        raise Exception('Pedido já foi faturado')

    # Atualizar pedido
    pedido.faturado = True
    pedido.numero_nf = numero_nf
    pedido.data_nf = data_nf
    pedido.empresa_venda_id = empresa_id

    # Atualizar motos
    for item in pedido.itens:
        item.moto.status = 'VENDIDA'

    # Atualizar títulos (RASCUNHO → ABERTO)
    titulos_atualizados = []
    for titulo in pedido.titulos:
        if titulo.prazo_dias:
            titulo.data_vencimento = data_nf + timedelta(days=titulo.prazo_dias)
        titulo.status = 'ABERTO'
        titulos_atualizados.append(titulo)

    db.session.flush()

    return {
        'pedido': pedido,
        'titulos_atualizados': titulos_atualizados,
        'total_titulos': len(titulos_atualizados)
    }
