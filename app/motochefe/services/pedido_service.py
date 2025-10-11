"""
Service Orquestrador para Pedidos - Sistema MotoCHEFE
Gerencia emissão completa de pedidos com títulos financeiros e títulos a pagar
"""
from app import db
from app.motochefe.models.vendas import PedidoVendaMoto, PedidoVendaMotoItem
from app.motochefe.models.produto import Moto
from app.motochefe.services.titulo_service import gerar_titulos_com_fifo_parcelas
from app.motochefe.services.titulo_a_pagar_service import (
    criar_titulo_a_pagar_movimentacao,
    criar_titulo_a_pagar_montagem
)
from decimal import Decimal


def criar_pedido_completo(dados_pedido, itens_json):
    """
    Cria pedido com alocação FIFO + títulos financeiros com parcelas + títulos a pagar

    Args:
        dados_pedido: dict com dados do pedido {
            'numero_pedido': str,
            'cliente_id': int,
            'vendedor_id': int,
            'equipe_vendas_id': int (opcional),
            'data_pedido': date,
            'data_expedicao': date,
            'valor_total_pedido': Decimal,
            'valor_frete_cliente': Decimal,
            'forma_pagamento': str,
            'condicao_pagamento': str,
            'prazo_dias': int (se sem parcelamento),
            'numero_parcelas': int,
            'parcelas': [  # Se com parcelamento
                {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
                {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
            ],
            'transportadora_id': int,
            'tipo_frete': str,
            'observacoes': str,
            'criado_por': str
        }
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
    # 🆕 Novos pedidos são criados com ativo=False e status='PENDENTE'
    # Aguardam aprovação na tela "Confirmação de Pedidos"
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
        prazo_dias=dados_pedido.get('prazo_dias', 0),
        numero_parcelas=dados_pedido.get('numero_parcelas', 1),
        transportadora_id=dados_pedido.get('transportadora_id'),
        tipo_frete=dados_pedido.get('tipo_frete'),
        observacoes=dados_pedido.get('observacoes'),
        criado_por=dados_pedido.get('criado_por', 'SISTEMA'),
        # 🆕 NOVOS CAMPOS
        ativo=False,            # Não aparece na lista até aprovação
        status='PENDENTE'       # Aguardando aprovação
    )

    db.session.add(pedido)
    db.session.flush()

    # 2. PROCESSAR ITENS - ALOCAR MOTOS (FIFO)
    itens_criados = []
    titulos_a_pagar_criados = []

    for item_data in itens_json:
        modelo_id = item_data['modelo_id']
        cor = item_data['cor']
        quantidade = int(item_data['quantidade'])
        preco_venda = Decimal(str(item_data['preco_venda']))
        montagem = item_data.get('montagem', False)
        valor_montagem = Decimal(str(item_data.get('valor_montagem', 0)))
        fornecedor_montagem = item_data.get('fornecedor_montagem')

        # Alocar motos disponíveis (FIFO por data_entrada)
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

        # Criar itens do pedido
        for moto in motos_disponiveis:
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

    # 3. GERAR TÍTULOS COM FIFO ENTRE PARCELAS
    parcelas_config = dados_pedido.get('parcelas', [])
    titulos_financeiros_criados = gerar_titulos_com_fifo_parcelas(
        pedido,
        itens_criados,
        parcelas_config
    )

    # 4. CRIAR TÍTULOS A PAGAR (PENDENTES)
    for titulo in titulos_financeiros_criados:
        if titulo.tipo_titulo == 'MOVIMENTACAO':
            titulo_pagar = criar_titulo_a_pagar_movimentacao(titulo)
            if titulo_pagar:
                titulos_a_pagar_criados.append(titulo_pagar)

        elif titulo.tipo_titulo == 'MONTAGEM':
            # Buscar item correspondente
            item = next((i for i in itens_criados if i.numero_chassi == titulo.numero_chassi), None)
            if item and item.montagem_contratada:
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
    Fatura pedido: atualiza NF, calcula vencimentos baseado em prazo_dias, muda status

    Args:
        pedido: PedidoVendaMoto
        empresa_id: int
        numero_nf: str
        data_nf: date (ou data_expedicao do pedido)

    Returns:
        dict com resultado
    """
    from datetime import timedelta

    # 🆕 VALIDAÇÕES DE STATUS
    if pedido.faturado:
        raise Exception('Pedido já foi faturado')

    if pedido.status != 'APROVADO':
        raise Exception(f'Apenas pedidos aprovados podem ser faturados. Status atual: {pedido.status}')

    if not pedido.ativo:
        raise Exception('Pedido inativo não pode ser faturado')

    # Atualizar pedido
    pedido.faturado = True
    pedido.numero_nf = numero_nf
    pedido.data_nf = data_nf
    pedido.empresa_venda_id = empresa_id

    # Atualizar motos
    for item in pedido.itens:
        item.moto.status = 'VENDIDA'

    # Atualizar títulos: calcular data_vencimento
    # NOTA: Títulos já são criados com status='ABERTO' desde a criação do pedido
    # Aqui apenas calculamos data_vencimento = data_expedicao (ou data_nf) + prazo_dias
    titulos_atualizados = []
    data_base = pedido.data_expedicao or data_nf

    for titulo in pedido.titulos:
        if titulo.prazo_dias is not None:
            titulo.data_vencimento = data_base + timedelta(days=titulo.prazo_dias)
        # Linha abaixo é redundante mas mantida por segurança (já criado como ABERTO)
        titulo.status = 'ABERTO'
        titulos_atualizados.append(titulo)

    db.session.flush()

    return {
        'pedido': pedido,
        'titulos_atualizados': titulos_atualizados,
        'total_titulos': len(titulos_atualizados)
    }
