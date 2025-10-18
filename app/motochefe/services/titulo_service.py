"""
Service para Títulos Financeiros - Sistema MotoCHEFE
Gerencia geração de títulos com FIFO, pagamentos parciais e splitting
"""
from app import db
from app.motochefe.models.financeiro import TituloFinanceiro
from datetime import date
from decimal import Decimal
import json


def gerar_titulos_com_fifo_parcelas(pedido, itens_pedido, parcelas_config, tipos_permitidos=None):
    """
    Gera títulos aplicando FIFO entre parcelas
    Títulos podem ser divididos entre parcelas conforme necessário

    IMPORTANTE: Títulos são criados com status='ABERTO' desde a criação do pedido.
    A data_vencimento é calculada posteriormente no faturamento (data_expedicao + prazo_dias).

    Args:
        pedido: PedidoVendaMoto
        itens_pedido: list de PedidoVendaMotoItem
        parcelas_config: [
            {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
            {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
        ]
        tipos_permitidos: list (opcional) - Se fornecido, gera APENAS esses tipos
            Ex: ['VENDA', 'FRETE'] para modo histórico
            Se None, gera TODOS os tipos (MOVIMENTACAO, MONTAGEM, FRETE, VENDA)

    Returns:
        list de TituloFinanceiro criados

    Exemplo:
        3 motos × 4 títulos = 12 títulos
        Parcela 1: R$ 7.800 (prazo 28 dias)
        Parcela 2: R$ 7.800 (prazo 35 dias)

        Algoritmo FIFO consome títulos sequencialmente:
        - P1 consome até R$ 7.800
        - Se último título exceder, SPLIT em 2 títulos
        - P2 recebe restante do split + próximos títulos
    """
    from app.motochefe.services.titulo_service import calcular_valores_titulos_moto

    # 1. GERAR LISTA DE TÍTULOS (sem parcela ainda)
    titulos_pendentes = []
    total_motos = len(itens_pedido)

    for item in itens_pedido:
        equipe = pedido.equipe if pedido.equipe else pedido.vendedor.equipe
        valores = calcular_valores_titulos_moto(item, equipe, pedido, total_motos)

        # Ordem: MOVIMENTACAO, MONTAGEM, FRETE, VENDA
        tipos_titulo = [
            ('MOVIMENTACAO', 1, valores['movimentacao']),
            ('MONTAGEM', 2, valores['montagem']),
            ('FRETE', 3, valores['frete']),
            ('VENDA', 4, valores['venda'])
        ]

        for tipo, ordem, valor in tipos_titulo:
            # ⚠️ FILTRO POR TIPO (modo histórico)
            if tipos_permitidos and tipo not in tipos_permitidos:
                continue

            # Pular montagem se não contratada
            if tipo == 'MONTAGEM' and not item.montagem_contratada:
                continue

            # ✅ CORRIGIDO: MOVIMENTACAO sempre cria (mesmo R$ 0), mas será ocultado na exibição
            # Outros tipos pulam se valor zerado
            if tipo != 'MOVIMENTACAO' and valor <= 0:
                continue

            titulos_pendentes.append({
                'tipo': tipo,
                'ordem': ordem,
                'valor': Decimal(str(valor)),
                'chassi': item.numero_chassi,
                'custo_real': valores.get('movimentacao_custo') if tipo == 'MOVIMENTACAO' else None
            })

    # 2. APLICAR FIFO - Distribuir títulos entre parcelas
    titulos_criados = []
    total_parcelas = len(parcelas_config) if parcelas_config else 1

    if not parcelas_config:
        # Sem parcelamento: todos títulos na parcela 1, prazo do pedido
        for t_data in titulos_pendentes:
            titulo = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=t_data['chassi'],
                tipo_titulo=t_data['tipo'],
                ordem_pagamento=t_data['ordem'],
                numero_parcela=1,
                total_parcelas=1,
                valor_parcela=Decimal('0'),  # 0 quando não há parcelamento
                prazo_dias=pedido.prazo_dias,
                valor_original=t_data['valor'],
                valor_saldo=t_data['valor'],
                valor_pago_total=0,
                data_emissao=date.today(),
                status='ABERTO',
                criado_por='SISTEMA'
            )
            db.session.add(titulo)
            db.session.flush()
            titulos_criados.append(titulo)
    else:
        # COM parcelamento: aplicar FIFO
        valor_restante_parcela = Decimal(str(parcelas_config[0]['valor']))
        parcela_atual = parcelas_config[0]
        idx_parcela = 0

        for t_data in titulos_pendentes:
            valor_titulo = t_data['valor']

            if valor_titulo <= valor_restante_parcela:
                # Cabe inteiro na parcela atual
                titulo = TituloFinanceiro(
                    pedido_id=pedido.id,
                    numero_chassi=t_data['chassi'],
                    tipo_titulo=t_data['tipo'],
                    ordem_pagamento=t_data['ordem'],
                    numero_parcela=parcela_atual['numero'],
                    total_parcelas=total_parcelas,
                    valor_parcela=Decimal(str(parcela_atual['valor'])),
                    prazo_dias=parcela_atual['prazo_dias'],
                    valor_original=valor_titulo,
                    valor_saldo=valor_titulo,
                    valor_pago_total=0,
                    data_emissao=date.today(),
                    status='ABERTO',
                    criado_por='SISTEMA'
                )
                db.session.add(titulo)
                db.session.flush()
                titulos_criados.append(titulo)

                valor_restante_parcela -= valor_titulo

            else:
                # SPLIT: Título excede parcela atual
                # Parte 1: Preenche parcela atual
                parcela_p1_valor = Decimal(str(parcela_atual['valor']))
                titulo_p1 = TituloFinanceiro(
                    pedido_id=pedido.id,
                    numero_chassi=t_data['chassi'],
                    tipo_titulo=t_data['tipo'],
                    ordem_pagamento=t_data['ordem'],
                    numero_parcela=parcela_atual['numero'],
                    total_parcelas=total_parcelas,
                    valor_parcela=parcela_p1_valor,
                    prazo_dias=parcela_atual['prazo_dias'],
                    valor_original=valor_restante_parcela,
                    valor_saldo=valor_restante_parcela,
                    valor_pago_total=0,
                    data_emissao=date.today(),
                    status='ABERTO',
                    criado_por='SISTEMA'
                )
                db.session.add(titulo_p1)
                db.session.flush()
                titulos_criados.append(titulo_p1)

                # Próxima parcela
                idx_parcela += 1
                if idx_parcela >= len(parcelas_config):
                    raise Exception(
                        f'Valor das parcelas ({sum(p["valor"] for p in parcelas_config)}) '
                        f'é insuficiente para cobrir total dos títulos'
                    )

                parcela_atual = parcelas_config[idx_parcela]

                # Parte 2: Restante vai para próxima parcela
                valor_p2 = valor_titulo - valor_restante_parcela
                parcela_p2_valor = Decimal(str(parcela_atual['valor']))
                titulo_p2 = TituloFinanceiro(
                    pedido_id=pedido.id,
                    numero_chassi=t_data['chassi'],
                    tipo_titulo=t_data['tipo'],
                    ordem_pagamento=t_data['ordem'],
                    numero_parcela=parcela_atual['numero'],
                    total_parcelas=total_parcelas,
                    valor_parcela=parcela_p2_valor,
                    prazo_dias=parcela_atual['prazo_dias'],
                    valor_original=valor_p2,
                    valor_saldo=valor_p2,
                    valor_pago_total=0,
                    data_emissao=date.today(),
                    status='ABERTO',
                    criado_por='SISTEMA'
                )
                db.session.add(titulo_p2)
                db.session.flush()
                titulos_criados.append(titulo_p2)

                valor_restante_parcela = parcela_p2_valor - valor_p2

    return titulos_criados


def calcular_valores_titulos_moto(item_pedido, equipe, pedido=None, total_motos=1):
    """
    Calcula valores dos 4 títulos para uma moto

    Args:
        item_pedido: PedidoVendaMotoItem
        equipe: EquipeVendasMoto
        pedido: PedidoVendaMoto (opcional, para rateio de frete)
        total_motos: int (total de motos no pedido, para rateio)

    Returns:
        dict com valores
    """
    # MOVIMENTAÇÃO - Lógica CORRIGIDA:
    # - incluir_custo_movimentacao=True: Cliente PAGA R$ 50 → cria TituloFinanceiro R$ 50
    # - incluir_custo_movimentacao=False: Cliente paga R$ 0 → cria TituloFinanceiro R$ 0
    # - MAS: Empresa SEMPRE paga MargemSogima R$ 50 → SEMPRE cria TituloAPagar R$ 50
    valor_movimentacao_cliente = equipe.custo_movimentacao if equipe.incluir_custo_movimentacao else Decimal('0')
    valor_movimentacao_custo = equipe.custo_movimentacao  # SEMPRE tem custo para empresa

    # MONTAGEM: Valor cobrado do cliente (custo real será usado no título a pagar)
    valor_montagem = item_pedido.valor_montagem if item_pedido.montagem_contratada else Decimal('0')

    # FRETE: Rateio do frete do pedido entre motos
    valor_frete = Decimal('0')
    if pedido and pedido.valor_frete_cliente and total_motos > 0:
        valor_frete = Decimal(str(pedido.valor_frete_cliente)) / total_motos
        # Arredondar para 2 casas decimais
        valor_frete = valor_frete.quantize(Decimal('0.01'))

    # VENDA: Preço de venda
    valor_venda = item_pedido.preco_venda

    return {
        'movimentacao': valor_movimentacao_cliente,  # O que cliente paga (pode ser R$ 0)
        'movimentacao_custo': valor_movimentacao_custo,  # O que empresa paga (sempre > 0)
        'montagem': valor_montagem,
        'frete': valor_frete,
        'venda': valor_venda
    }


def processar_pagamento_fifo(pedido, valor_pago, empresa_recebedora, usuario=None):
    """
    Processa pagamento aplicando FIFO nos títulos
    Pode gerar splitting e renumeração automática

    Args:
        pedido: PedidoVendaMoto
        valor_pago: Decimal
        empresa_recebedora: EmpresaVendaMoto
        usuario: str

    Returns:
        dict com resultado detalhado
    """
    from app.motochefe.services.movimentacao_service import registrar_recebimento_titulo
    from app.motochefe.services.empresa_service import atualizar_saldo
    from app.motochefe.services.titulo_a_pagar_service import liberar_titulo_a_pagar
    from app.motochefe.services.baixa_automatica_service import processar_baixa_automatica_motos

    # Buscar títulos ABERTOS ordenados por FIFO
    titulos_abertos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido.id,
        status='ABERTO'
    ).order_by(
        TituloFinanceiro.numero_parcela,
        TituloFinanceiro.numero_chassi,
        TituloFinanceiro.ordem_pagamento
    ).all()

    if not titulos_abertos:
        raise Exception('Nenhum título em aberto para receber pagamento')

    valor_restante = Decimal(str(valor_pago))
    titulos_pagos = []
    titulo_splitado = None
    ultimo_titulo_parcial = None

    # Aplicar FIFO
    for titulo in titulos_abertos:
        if valor_restante <= 0:
            break

        if valor_restante >= titulo.valor_saldo:
            # Paga título completo
            valor_recebido = titulo.valor_saldo

            # Registrar movimentação
            mov = registrar_recebimento_titulo(titulo, valor_recebido, empresa_recebedora, usuario)

            # Atualizar título
            titulo.valor_pago_total += valor_recebido
            titulo.valor_saldo = Decimal('0')
            titulo.status = 'PAGO'
            titulo.empresa_recebedora_id = empresa_recebedora.id
            titulo.data_ultimo_pagamento = date.today()
            titulo.atualizado_por = usuario

            titulos_pagos.append(titulo)
            valor_restante -= valor_recebido

            # Triggers para título totalmente pago
            liberar_titulo_a_pagar(titulo.id)

            if empresa_recebedora.baixa_compra_auto:
                processar_baixa_automatica_motos(empresa_recebedora, valor_recebido, mov.id, usuario)

            if titulo.tipo_titulo == 'VENDA':
                from app.motochefe.services.comissao_service import gerar_comissao_moto
                from app.motochefe.services.titulo_a_pagar_service import quitar_titulo_movimentacao_ao_pagar_moto

                gerar_comissao_moto(titulo)
                # Liberar TituloAPagar de movimentação se cliente não pagou movimentação
                quitar_titulo_movimentacao_ao_pagar_moto(titulo.numero_chassi, titulo.pedido_id, usuario)

        else:
            # Pagamento parcial: SPLIT do título
            valor_recebido = valor_restante

            # Criar título PAGO (mantém numero_parcela original)
            titulo_pago = TituloFinanceiro(
                pedido_id=titulo.pedido_id,
                numero_chassi=titulo.numero_chassi,
                tipo_titulo=titulo.tipo_titulo,
                ordem_pagamento=titulo.ordem_pagamento,
                numero_parcela=titulo.numero_parcela,
                total_parcelas=titulo.total_parcelas,
                valor_parcela=titulo.valor_parcela,
                prazo_dias=titulo.prazo_dias,
                data_vencimento=titulo.data_vencimento,
                valor_original=valor_recebido,
                valor_saldo=Decimal('0'),
                valor_pago_total=valor_recebido,
                data_emissao=titulo.data_emissao,
                empresa_recebedora_id=empresa_recebedora.id,
                data_ultimo_pagamento=date.today(),
                status='PAGO',
                titulo_pai_id=titulo.id,
                eh_titulo_dividido=True,
                criado_por=usuario or 'SISTEMA'
            )
            db.session.add(titulo_pago)
            db.session.flush()

            # Registrar movimentação no título PAGO
            registrar_recebimento_titulo(titulo_pago, valor_recebido, empresa_recebedora, usuario)

            # Criar título RESTANTE (mantém numero_parcela original)
            valor_restante_titulo = titulo.valor_saldo - valor_recebido
            titulo_restante = TituloFinanceiro(
                pedido_id=titulo.pedido_id,
                numero_chassi=titulo.numero_chassi,
                tipo_titulo=titulo.tipo_titulo,
                ordem_pagamento=titulo.ordem_pagamento,
                numero_parcela=titulo.numero_parcela,
                total_parcelas=titulo.total_parcelas,
                valor_parcela=titulo.valor_parcela,
                prazo_dias=titulo.prazo_dias,
                data_vencimento=titulo.data_vencimento,
                valor_original=valor_restante_titulo,
                valor_saldo=valor_restante_titulo,
                valor_pago_total=Decimal('0'),
                data_emissao=titulo.data_emissao,
                status='ABERTO',
                titulo_pai_id=titulo.id,
                eh_titulo_dividido=True,
                criado_por=usuario or 'SISTEMA'
            )
            db.session.add(titulo_restante)
            db.session.flush()

            # Inativar título original
            titulo.status = 'CANCELADO'
            titulo.historico_divisao = json.dumps({
                'data_split': str(date.today()),
                'valor_pago': float(valor_recebido),
                'valor_restante': float(valor_restante_titulo),
                'titulo_pago_id': titulo_pago.id,
                'titulo_restante_id': titulo_restante.id,
                'usuario': usuario
            })

            titulos_pagos.append(titulo_pago)
            titulo_splitado = titulo
            ultimo_titulo_parcial = titulo_restante
            valor_restante = Decimal('0')

            # RENUMERAR: Todos títulos não pagos (exceto o restante do split) +1
            renumerar_parcelas_nao_pagas(pedido.id, titulo.numero_parcela, [titulo_restante.id])

    # Atualizar saldo empresa
    atualizar_saldo(empresa_recebedora.id, valor_pago, 'SOMAR')

    db.session.flush()

    return {
        'titulos_pagos': titulos_pagos,
        'titulo_splitado': titulo_splitado,
        'titulo_restante': ultimo_titulo_parcial,
        'valor_processado': valor_pago,
        'renumeracao_executada': titulo_splitado is not None
    }


def renumerar_parcelas_nao_pagas(pedido_id, a_partir_de_parcela, exceto_ids=None):
    """
    Renumera todos os títulos ABERTOS somando +1 no numero_parcela
    Mantém prazo_dias e data_vencimento inalterados

    Args:
        pedido_id: int
        a_partir_de_parcela: int (renumera >= esta parcela)
        exceto_ids: list de IDs para não renumerar

    Returns:
        int (quantidade de títulos renumerados)
    """
    query = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        status='ABERTO'
    ).filter(
        TituloFinanceiro.numero_parcela >= a_partir_de_parcela
    )

    if exceto_ids:
        query = query.filter(~TituloFinanceiro.id.in_(exceto_ids))

    titulos_abertos = query.all()

    for titulo in titulos_abertos:
        # Soma +1 MANTENDO prazo_dias e data_vencimento
        titulo.numero_parcela += 1

    db.session.flush()

    return len(titulos_abertos)


def receber_titulo(titulo, valor_recebido, empresa_recebedora, usuario=None):
    """
    Processa recebimento de título INDIVIDUAL (mantido por compatibilidade)
    ATENÇÃO: Usar processar_pagamento_fifo() para fluxo completo com splitting

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
            from app.motochefe.services.titulo_a_pagar_service import quitar_titulo_movimentacao_ao_pagar_moto

            comissao = gerar_comissao_moto(titulo)
            resultado['comissao_gerada'] = comissao

            # Liberar TituloAPagar de movimentação se cliente não pagou movimentação
            quitar_titulo_movimentacao_ao_pagar_moto(titulo.numero_chassi, titulo.pedido_id, usuario)

    else:
        # PAGAMENTO PARCIAL - continua ABERTO
        titulo.status = 'ABERTO'

    db.session.flush()

    return resultado


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
    ).filter(
        TituloFinanceiro.status != 'CANCELADO'  # Não mostrar títulos cancelados (pais de split)
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


def obter_todos_titulos_agrupados():
    """
    Retorna TODOS os títulos (em aberto) agrupados por Pedido > Parcela > Moto > Tipo
    Para exibir em accordion consolidado

    ✅ FILTRO: Exclui títulos com valor_original = 0 (empresa absorveu custo, nada a receber)

    Returns:
        dict estruturado: {pedido_id: {pedido, parcelas: {numero: {motos: {chassi: [titulos]}}}}}
    """

    # Buscar todos títulos em aberto COM VALOR > 0
    titulos = TituloFinanceiro.query.filter(
        TituloFinanceiro.status == 'ABERTO',
        TituloFinanceiro.valor_original > 0  # ✅ Apenas títulos com valor a receber
    ).order_by(
        TituloFinanceiro.pedido_id,
        TituloFinanceiro.numero_parcela,
        TituloFinanceiro.numero_chassi,
        TituloFinanceiro.ordem_pagamento
    ).all()

    # Agrupar
    agrupado = {}

    for titulo in titulos:
        pedido_id = titulo.pedido_id

        if pedido_id not in agrupado:
            agrupado[pedido_id] = {
                'pedido': titulo.pedido,
                'parcelas': {}
            }

        parcela = titulo.numero_parcela

        if parcela not in agrupado[pedido_id]['parcelas']:
            agrupado[pedido_id]['parcelas'][parcela] = {
                'motos': {}
            }

        chassi = titulo.numero_chassi

        if chassi not in agrupado[pedido_id]['parcelas'][parcela]['motos']:
            agrupado[pedido_id]['parcelas'][parcela]['motos'][chassi] = []

        agrupado[pedido_id]['parcelas'][parcela]['motos'][chassi].append(titulo)

    return agrupado


def receber_por_pedido(pedido_id, valor_recebido, empresa_recebedora, usuario):
    """
    Recebe pagamento por pedido - USA SISTEMA DE LOTE
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS
    """
    from app.motochefe.models.financeiro import TituloFinanceiro
    from app.motochefe.services.lote_pagamento_service import processar_recebimento_lote_titulos
    from decimal import Decimal

    # Buscar títulos do pedido, ordenados
    titulos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        status='ABERTO'
    ).filter(
        TituloFinanceiro.valor_saldo > 0
    ).order_by(
        TituloFinanceiro.numero_chassi.asc(),
        TituloFinanceiro.numero_parcela.asc(),
        TituloFinanceiro.ordem_pagamento.asc()
    ).all()

    if not titulos:
        raise Exception('Nenhum título em aberto encontrado para este pedido')

    # Distribuir valor entre títulos (FIFO)
    valor_restante = Decimal(str(valor_recebido))
    titulo_ids = []
    valores_recebidos = {}

    for titulo in titulos:
        if valor_restante <= 0:
            break

        saldo_titulo = titulo.valor_saldo
        valor_aplicar = min(valor_restante, saldo_titulo)

        titulo_ids.append(titulo.id)
        valores_recebidos[titulo.id] = valor_aplicar
        valor_restante -= valor_aplicar

    # Processar lote (cria PAI + FILHOS)
    resultado = processar_recebimento_lote_titulos(
        titulo_ids=titulo_ids,
        valores_recebidos=valores_recebidos,
        empresa_recebedora=empresa_recebedora,
        data_recebimento=date.today(),
        usuario=usuario
    )

    return {
        'titulos_recebidos': [t.id for t in resultado['titulos_recebidos']],
        'total_aplicado': resultado['valor_total'],
        'saldo_restante': valor_restante
    }


def receber_por_moto(pedido_id, numero_chassi, valor_recebido, empresa_recebedora, usuario):
    """
    Recebe pagamento de uma moto - USA SISTEMA DE LOTE
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS
    """
    from app.motochefe.models.financeiro import TituloFinanceiro
    from app.motochefe.services.lote_pagamento_service import processar_recebimento_lote_titulos
    from decimal import Decimal

    # Buscar títulos da moto, ordenados
    titulos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido_id,
        numero_chassi=numero_chassi,
        status='ABERTO'
    ).filter(
        TituloFinanceiro.valor_saldo > 0
    ).order_by(
        TituloFinanceiro.numero_parcela.asc(),
        TituloFinanceiro.ordem_pagamento.asc()
    ).all()

    if not titulos:
        raise Exception(f'Nenhum título em aberto para a moto {numero_chassi}')

    # Distribuir valor entre títulos (FIFO)
    valor_restante = Decimal(str(valor_recebido))
    titulo_ids = []
    valores_recebidos = {}

    for titulo in titulos:
        if valor_restante <= 0:
            break

        saldo_titulo = titulo.valor_saldo
        valor_aplicar = min(valor_restante, saldo_titulo)

        titulo_ids.append(titulo.id)
        valores_recebidos[titulo.id] = valor_aplicar
        valor_restante -= valor_aplicar

    # Processar lote (cria PAI + FILHOS)
    resultado = processar_recebimento_lote_titulos(
        titulo_ids=titulo_ids,
        valores_recebidos=valores_recebidos,
        empresa_recebedora=empresa_recebedora,
        data_recebimento=date.today(),
        usuario=usuario
    )

    return {
        'titulos_recebidos': [t.id for t in resultado['titulos_recebidos']],
        'total_aplicado': resultado['valor_total'],
        'saldo_restante': valor_restante
    }
