"""
Service para Pagamento em Lote - Sistema MotoCHEFE
Cria MovimentacaoFinanceira PAI + FILHOS, atualiza saldo, registra empresa pagadora
"""
from app import db
from app.motochefe.models.financeiro import MovimentacaoFinanceira
from app.motochefe.models.produto import Moto
from app.motochefe.models.vendas import PedidoVendaMotoItem
from app.motochefe.models.financeiro import ComissaoVendedor
from app.motochefe.models.operacional import DespesaMensal
from datetime import date
from decimal import Decimal


def processar_pagamento_lote_motos(chassi_list, empresa_pagadora, data_pagamento=None, usuario=None, valor_limite=None):
    """
    Processa pagamento em lote de custos de motos
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS (um para cada chassi)

    ✨ SUPORTA PAGAMENTO PARCIAL quando valor_limite é informado

    Args:
        chassi_list: list[str] - Lista de números de chassi
        empresa_pagadora: EmpresaVendaMoto - Empresa que está pagando
        data_pagamento: date - Data do pagamento (default: hoje)
        usuario: str - Nome do usuário
        valor_limite: Decimal - Valor máximo a pagar (opcional, se None paga tudo)

    Returns:
        dict {
            'movimentacao_pai': MovimentacaoFinanceira,
            'movimentacoes_filhas': list[MovimentacaoFinanceira],
            'motos_atualizadas': list[Moto],
            'valor_total': Decimal
        }
    """
    from app.motochefe.services.empresa_service import atualizar_saldo

    data_pag = data_pagamento or date.today()
    motos_para_pagar = []
    movimentacoes_filhas = []
    valor_total_pago = Decimal('0')
    valor_disponivel = Decimal(str(valor_limite)) if valor_limite else None

    # 1. BUSCAR MOTOS E CALCULAR VALORES
    for chassi in chassi_list:
        # Se tem limite e já acabou o valor, para
        if valor_disponivel is not None and valor_disponivel <= 0:
            break

        moto = Moto.query.filter_by(numero_chassi=chassi).first()
        if not moto:
            raise Exception(f'Moto com chassi {chassi} não encontrada')

        valor_saldo_moto = moto.custo_aquisicao - (moto.custo_pago or Decimal('0'))

        # Se já está paga, pular
        if valor_saldo_moto <= 0:
            continue

        # Calcular quanto pagar nesta moto
        if valor_disponivel is not None:
            # COM LIMITE: Pagar o MENOR entre disponível e saldo
            valor_pagar_moto = min(valor_disponivel, valor_saldo_moto)
            valor_disponivel -= valor_pagar_moto
        else:
            # SEM LIMITE: Pagar o saldo completo
            valor_pagar_moto = valor_saldo_moto

        motos_para_pagar.append({
            'moto': moto,
            'valor_pagar': valor_pagar_moto,
            'saldo_anterior': moto.custo_pago or Decimal('0')
        })
        valor_total_pago += valor_pagar_moto

    if not motos_para_pagar:
        raise Exception('Nenhuma moto disponível para pagamento')

    # 2. CRIAR MOVIMENTAÇÃO PAI
    nf_entrada = motos_para_pagar[0]['moto'].nf_entrada if len(motos_para_pagar) == 1 else 'Múltiplas NFs'
    fornecedor = motos_para_pagar[0]['moto'].fornecedor if len(motos_para_pagar) == 1 else f'{len(motos_para_pagar)} fornecedor(es)'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Lote Custo Moto',
        valor=valor_total_pago,
        data_movimentacao=data_pag,

        # Origem (Empresa)
        empresa_origem_id=empresa_pagadora.id,

        # Destino (Fornecedor - não é empresa)
        empresa_destino_id=None,
        destino_tipo='Fornecedor',
        destino_identificacao=fornecedor,

        # Informações
        numero_nf=nf_entrada if len(motos_para_pagar) == 1 else None,
        descricao=f'Pagamento Lote {len(motos_para_pagar)} moto(s) - NF {nf_entrada}',
        observacoes=f'Lote com {len(motos_para_pagar)} moto(s): {", ".join([m["moto"].numero_chassi for m in motos_para_pagar])}',

        # Auditoria
        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR MOTOS
    motos_atualizadas = []
    for item in motos_para_pagar:
        moto = item['moto']
        valor_pagar = item['valor_pagar']

        # Criar movimentação FILHA
        movimentacao_filha = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Custo Moto',
            valor=valor_pagar,  # Usar valor calculado (pode ser parcial)
            data_movimentacao=data_pag,

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=None,
            destino_tipo='Fornecedor',
            destino_identificacao=moto.fornecedor,

            numero_chassi=moto.numero_chassi,
            numero_nf=moto.nf_entrada,
            descricao=f'Custo Moto {moto.numero_chassi} - {moto.fornecedor}',

            # Relacionamento com PAI
            movimentacao_origem_id=movimentacao_pai.id,
            eh_baixa_automatica=False,

            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        # Atualizar MOTO
        moto.custo_pago = (moto.custo_pago or Decimal('0')) + valor_pagar
        moto.data_pagamento_custo = data_pag
        moto.empresa_pagadora_id = empresa_pagadora.id
        moto.lote_pagamento_id = movimentacao_pai.id
        moto.atualizado_por = usuario

        # Atualizar STATUS
        if moto.custo_pago >= moto.custo_aquisicao:
            moto.status_pagamento_custo = 'PAGO'
        else:
            moto.status_pagamento_custo = 'PARCIAL'

        motos_atualizadas.append(moto)

    # 4. ATUALIZAR SALDO DA EMPRESA
    atualizar_saldo(empresa_pagadora.id, valor_total_pago, 'SUBTRAIR')

    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'motos_atualizadas': motos_atualizadas,
        'valor_total': valor_total_pago
    }


def processar_pagamento_lote_comissoes(comissao_ids, empresa_pagadora, data_pagamento=None, usuario=None):
    """
    Processa pagamento em lote de comissões
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS

    Args:
        comissao_ids: list[int] - Lista de IDs de ComissaoVendedor
        empresa_pagadora: EmpresaVendaMoto
        data_pagamento: date
        usuario: str

    Returns:
        dict similar a processar_pagamento_lote_motos
    """
    from app.motochefe.services.empresa_service import atualizar_saldo

    data_pag = data_pagamento or date.today()
    comissoes = []
    movimentacoes_filhas = []
    valor_total = Decimal('0')

    # 1. BUSCAR COMISSÕES E VALIDAR
    for com_id in comissao_ids:
        comissao = db.session.get(ComissaoVendedor,com_id) if com_id else None
        if not comissao:
            raise Exception(f'Comissão ID {com_id} não encontrada')

        if comissao.status == 'PAGO':
            raise Exception(f'Comissão ID {com_id} já está paga')

        comissoes.append(comissao)
        valor_total += comissao.valor_rateado

    # 2. CRIAR MOVIMENTAÇÃO PAI
    # Agrupar por vendedor (pode ter múltiplos vendedores)
    vendedores_set = set([c.vendedor.vendedor for c in comissoes if c.vendedor])
    vendedores_str = ', '.join(sorted(vendedores_set)) if vendedores_set else 'Vendedores'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Lote Comissão',
        valor=valor_total,
        data_movimentacao=data_pag,

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Vendedor',
        destino_identificacao=vendedores_str if len(vendedores_set) <= 3 else f'{len(vendedores_set)} vendedor(es)',

        descricao=f'Pagamento Lote {len(comissoes)} comissão(ões) - {vendedores_str}',
        observacoes=f'Lote com {len(comissoes)} comissão(ões)',

        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR COMISSÕES
    for comissao in comissoes:
        movimentacao_filha = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Comissão',
            valor=comissao.valor_rateado,
            data_movimentacao=data_pag,

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=None,
            destino_tipo='Vendedor',
            destino_identificacao=comissao.vendedor.vendedor if comissao.vendedor else 'Vendedor',

            pedido_id=comissao.pedido_id,
            numero_chassi=comissao.numero_chassi,
            comissao_vendedor_id=comissao.id,

            descricao=f'Comissão Pedido {comissao.pedido.numero_pedido} - {comissao.vendedor.vendedor if comissao.vendedor else "Vendedor"}',

            movimentacao_origem_id=movimentacao_pai.id,
            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        # Atualizar COMISSÃO
        comissao.data_pagamento = data_pag
        comissao.status = 'PAGO'
        comissao.empresa_pagadora_id = empresa_pagadora.id
        comissao.lote_pagamento_id = movimentacao_pai.id
        comissao.atualizado_por = usuario

    # 4. ATUALIZAR SALDO
    atualizar_saldo(empresa_pagadora.id, valor_total, 'SUBTRAIR')

    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'comissoes_atualizadas': comissoes,
        'valor_total': valor_total
    }


def processar_pagamento_lote_montagens(titulo_ids, empresa_pagadora, data_pagamento=None, usuario=None, valor_limite=None):
    """
    ✅ REFATORADO: Processa pagamento em lote de montagens com suporte a pagamento PARCIAL
    Comportamento IDÊNTICO a processar_pagamento_lote_motos
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS

    Args:
        titulo_ids: list[int] - Lista de IDs de TituloAPagar (MONTAGEM)
        empresa_pagadora: EmpresaVendaMoto
        data_pagamento: date
        usuario: str
        valor_limite: Decimal (opcional) - Valor máximo a pagar (pagamento parcial sequencial)

    Returns:
        dict {
            'movimentacao_pai': MovimentacaoFinanceira,
            'movimentacoes_filhas': list[MovimentacaoFinanceira],
            'titulos_atualizados': list[TituloAPagar],
            'valor_total': Decimal
        }
    """
    from app.motochefe.services.empresa_service import atualizar_saldo
    from app.motochefe.models.financeiro import TituloAPagar

    data_pag = data_pagamento or date.today()
    titulos_para_pagar = []
    movimentacoes_filhas = []
    valor_total_pago = Decimal('0')
    valor_disponivel = Decimal(str(valor_limite)) if valor_limite else None

    # 1. BUSCAR TÍTULOS E CALCULAR VALORES (COM PAGAMENTO PARCIAL)
    for titulo_id in titulo_ids:
        # Se tem limite e já acabou o valor, parar
        if valor_disponivel is not None and valor_disponivel <= 0:
            break

        titulo_pagar = db.session.get(TituloAPagar,titulo_id) if titulo_id else None
        if not titulo_pagar:
            continue  # Pular título não encontrado

        if titulo_pagar.tipo != 'MONTAGEM':
            continue  # Pular títulos que não são de montagem

        if titulo_pagar.status not in ['ABERTO', 'PARCIAL']:
            continue  # Pular títulos não liberados ou já pagos

        valor_saldo_titulo = titulo_pagar.valor_saldo

        # Se já está totalmente pago, pular
        if valor_saldo_titulo <= 0:
            continue

        # ✅ PAGAMENTO PARCIAL: Calcular quanto pagar neste título
        if valor_disponivel is not None:
            # COM LIMITE: Pagar o MENOR entre disponível e saldo
            valor_pagar_titulo = min(valor_disponivel, valor_saldo_titulo)
            valor_disponivel -= valor_pagar_titulo
        else:
            # SEM LIMITE: Pagar o saldo completo
            valor_pagar_titulo = valor_saldo_titulo

        titulos_para_pagar.append({
            'titulo': titulo_pagar,
            'valor_pagar': valor_pagar_titulo,
            'saldo_anterior': titulo_pagar.valor_pago
        })
        valor_total_pago += valor_pagar_titulo

    if not titulos_para_pagar:
        raise Exception('Nenhum título disponível para pagamento')

    # 2. CRIAR MOVIMENTAÇÃO PAI
    fornecedores_set = set([t['titulo'].fornecedor_montagem for t in titulos_para_pagar if t['titulo'].fornecedor_montagem])
    fornecedores_str = ', '.join(sorted(fornecedores_set)) if fornecedores_set else 'Equipe Montagem'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Lote Montagem',
        valor=valor_total_pago,
        data_movimentacao=data_pag,

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Equipe Montagem',
        destino_identificacao=fornecedores_str if len(fornecedores_set) <= 3 else f'{len(fornecedores_set)} fornecedor(es)',

        descricao=f'Pagamento Lote {len(titulos_para_pagar)} montagem(ns) - {fornecedores_str}',
        observacoes=f'Lote com {len(titulos_para_pagar)} montagem(ns). Valor limite: R$ {valor_limite or "sem limite"}',

        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR TÍTULOS
    titulos_atualizados = []
    for item in titulos_para_pagar:
        titulo_pagar = item['titulo']
        valor_pagar = item['valor_pagar']

        # Criar movimentação FILHA
        movimentacao_filha = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Montagem',
            valor=valor_pagar,  # ✅ USAR VALOR CALCULADO (pode ser parcial)
            data_movimentacao=data_pag,

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=None,
            destino_tipo='Equipe Montagem',
            destino_identificacao=titulo_pagar.fornecedor_montagem or 'Equipe Montagem',

            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,

            descricao=f'Montagem Moto {titulo_pagar.numero_chassi} - Pedido {titulo_pagar.pedido.numero_pedido if titulo_pagar.pedido else titulo_pagar.pedido_id}',

            # Relacionamento com PAI
            movimentacao_origem_id=movimentacao_pai.id,
            eh_baixa_automatica=False,

            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        # ✅ ATUALIZAR TITULO A PAGAR (suporte a pagamento PARCIAL)
        titulo_pagar.valor_pago += valor_pagar
        titulo_pagar.valor_saldo -= valor_pagar
        titulo_pagar.atualizado_por = usuario

        # ✅ ATUALIZAR STATUS
        if titulo_pagar.valor_saldo <= 0:
            titulo_pagar.status = 'PAGO'
            titulo_pagar.data_pagamento = data_pag

            # ✅ SINCRONIZAÇÃO: Atualizar PedidoVendaMotoItem.montagem_paga
            item_pedido = db.session.query(PedidoVendaMotoItem).filter_by(
                pedido_id=titulo_pagar.pedido_id,
                numero_chassi=titulo_pagar.numero_chassi
            ).first()
            if item_pedido:
                item_pedido.montagem_paga = True
                item_pedido.data_pagamento_montagem = data_pag
                item_pedido.empresa_pagadora_montagem_id = empresa_pagadora.id
                item_pedido.lote_pagamento_montagem_id = movimentacao_pai.id
        else:
            titulo_pagar.status = 'PARCIAL'

        titulos_atualizados.append(titulo_pagar)

    # 4. ATUALIZAR SALDO DA EMPRESA
    atualizar_saldo(empresa_pagadora.id, valor_total_pago, 'SUBTRAIR')

    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'titulos_atualizados': titulos_atualizados,
        'valor_total': valor_total_pago
    }


def processar_pagamento_lote_despesas(despesa_ids, empresa_pagadora, data_pagamento=None, usuario=None):
    """
    Processa pagamento em lote de despesas mensais
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS

    Args:
        despesa_ids: list[int] - Lista de IDs de DespesaMensal
        empresa_pagadora: EmpresaVendaMoto
        data_pagamento: date
        usuario: str

    Returns:
        dict similar a processar_pagamento_lote_motos
    """
    from app.motochefe.services.empresa_service import atualizar_saldo

    data_pag = data_pagamento or date.today()
    despesas = []
    movimentacoes_filhas = []
    valor_total = Decimal('0')

    # 1. BUSCAR DESPESAS E VALIDAR
    for desp_id in despesa_ids:
        despesa = db.session.get(DespesaMensal,desp_id) if desp_id else None
        if not despesa:
            raise Exception(f'Despesa ID {desp_id} não encontrada')

        if despesa.status == 'PAGO':
            raise Exception(f'Despesa ID {desp_id} já está paga')

        despesas.append(despesa)
        valor_total += (despesa.valor - (despesa.valor_pago or Decimal('0')))

    # 2. CRIAR MOVIMENTAÇÃO PAI
    tipos_set = set([d.tipo_despesa for d in despesas])
    tipos_str = ', '.join(sorted(tipos_set)) if len(tipos_set) <= 3 else f'{len(tipos_set)} tipo(s)'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Lote Despesa',
        valor=valor_total,
        data_movimentacao=data_pag,

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=None,
        destino_tipo='Despesa',
        destino_identificacao=tipos_str,

        descricao=f'Pagamento Lote {len(despesas)} despesa(s) - {tipos_str}',
        observacoes=f'Lote com {len(despesas)} despesa(s)',

        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR DESPESAS
    for despesa in despesas:
        valor_pagar = despesa.valor - (despesa.valor_pago or Decimal('0'))

        movimentacao_filha = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Despesa',
            valor=valor_pagar,
            data_movimentacao=data_pag,

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=None,
            destino_tipo='Despesa',
            destino_identificacao=despesa.tipo_despesa,

            despesa_mensal_id=despesa.id,

            descricao=f'Despesa {despesa.tipo_despesa} - {despesa.mes_competencia:02d}/{despesa.ano_competencia} - {despesa.descricao or ""}',

            movimentacao_origem_id=movimentacao_pai.id,
            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        # Atualizar DESPESA
        despesa.valor_pago = despesa.valor
        despesa.data_pagamento = data_pag
        despesa.status = 'PAGO'
        despesa.empresa_pagadora_id = empresa_pagadora.id
        despesa.atualizado_por = usuario

    # 4. ATUALIZAR SALDO
    atualizar_saldo(empresa_pagadora.id, valor_total, 'SUBTRAIR')

    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'despesas_atualizadas': despesas,
        'valor_total': valor_total
    }


def processar_pagamento_lote_movimentacoes(titulo_ids, empresa_pagadora, data_pagamento=None, usuario=None, valor_limite=None):
    """
    Processa pagamento em lote de movimentações (TituloAPagar de MargemSogima)
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS

    ✨ SUPORTA PAGAMENTO PARCIAL quando valor_limite é informado

    Args:
        titulo_ids: list[int] - Lista de IDs de TituloAPagar
        empresa_pagadora: EmpresaVendaMoto
        data_pagamento: date
        usuario: str
        valor_limite: Decimal - Valor máximo a pagar (opcional)

    Returns:
        dict {
            'movimentacao_pai': MovimentacaoFinanceira,
            'movimentacoes_filhas': list[MovimentacaoFinanceira],
            'titulos_atualizados': list[TituloAPagar],
            'valor_total': Decimal
        }
    """
    from app.motochefe.models.financeiro import TituloAPagar, MovimentacaoFinanceira
    from app.motochefe.services.empresa_service import atualizar_saldo

    data_pag = data_pagamento or date.today()
    titulos_para_pagar = []
    movimentacoes_filhas = []
    valor_total_pago = Decimal('0')
    valor_disponivel = Decimal(str(valor_limite)) if valor_limite else None

    # 1. BUSCAR TÍTULOS E CALCULAR VALORES
    for titulo_id in titulo_ids:
        # Se tem limite e já acabou o valor, para
        if valor_disponivel is not None and valor_disponivel <= 0:
            break

        titulo_pagar = db.session.get(TituloAPagar,titulo_id) if titulo_id else None
        if not titulo_pagar:
            continue

        # Validar status
        if titulo_pagar.status not in ['ABERTO', 'PARCIAL']:
            continue

        valor_saldo_titulo = titulo_pagar.valor_saldo

        # Se já está pago, pular
        if valor_saldo_titulo <= 0:
            continue

        # Calcular quanto pagar neste título
        if valor_disponivel is not None:
            # COM LIMITE: Pagar o MENOR entre disponível e saldo
            valor_pagar_titulo = min(valor_disponivel, valor_saldo_titulo)
            valor_disponivel -= valor_pagar_titulo
        else:
            # SEM LIMITE: Pagar o saldo completo
            valor_pagar_titulo = valor_saldo_titulo

        titulos_para_pagar.append({
            'titulo': titulo_pagar,
            'valor_pagar': valor_pagar_titulo,
            'saldo_anterior': titulo_pagar.valor_pago
        })
        valor_total_pago += valor_pagar_titulo

    if not titulos_para_pagar:
        raise Exception('Nenhum título de movimentação disponível para pagamento')

    # 2. CRIAR MOVIMENTAÇÃO PAI
    empresa_destino = titulos_para_pagar[0]['titulo'].empresa_destino
    empresa_destino_nome = empresa_destino.empresa if empresa_destino else 'MargemSogima'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Lote Movimentação',
        valor=valor_total_pago,
        data_movimentacao=data_pag,

        empresa_origem_id=empresa_pagadora.id,
        empresa_destino_id=titulos_para_pagar[0]['titulo'].empresa_destino_id,

        descricao=f'Pagamento Lote {len(titulos_para_pagar)} movimentação(ões) - {empresa_destino_nome}',
        observacoes=f'Lote com {len(titulos_para_pagar)} movimentação(ões)',

        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR TÍTULOS
    titulos_atualizados = []
    for item in titulos_para_pagar:
        titulo_pagar = item['titulo']
        valor_pagar = item['valor_pagar']

        # Criar movimentação FILHA
        movimentacao_filha = MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            categoria='Movimentação',
            valor=valor_pagar,
            data_movimentacao=data_pag,

            empresa_origem_id=empresa_pagadora.id,
            empresa_destino_id=titulo_pagar.empresa_destino_id,

            pedido_id=titulo_pagar.pedido_id,
            numero_chassi=titulo_pagar.numero_chassi,

            descricao=f'Movimentação Pedido {titulo_pagar.pedido.numero_pedido if titulo_pagar.pedido else "-"} - Chassi {titulo_pagar.numero_chassi}',

            movimentacao_origem_id=movimentacao_pai.id,
            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        # Atualizar TÍTULO A PAGAR
        titulo_pagar.valor_pago += valor_pagar
        titulo_pagar.valor_saldo -= valor_pagar
        titulo_pagar.atualizado_por = usuario

        # Atualizar STATUS
        if titulo_pagar.valor_saldo <= 0:
            titulo_pagar.status = 'PAGO'
            titulo_pagar.data_pagamento = data_pag
        else:
            titulo_pagar.status = 'PARCIAL'

        titulos_atualizados.append(titulo_pagar)

    # 4. ATUALIZAR SALDOS
    # Origem: sempre subtrai
    atualizar_saldo(empresa_pagadora.id, valor_total_pago, 'SUBTRAIR')

    # Destino: soma para MargemSogima (se for empresa)
    if titulos_para_pagar[0]['titulo'].empresa_destino_id:
        atualizar_saldo(titulos_para_pagar[0]['titulo'].empresa_destino_id, valor_total_pago, 'SOMAR')

    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'titulos_atualizados': titulos_atualizados,
        'valor_total': valor_total_pago
    }


def obter_detalhes_lote_pagamento(movimentacao_pai_id):
    """
    Retorna detalhes de um lote de pagamento/recebimento (MovimentacaoFinanceira PAI + FILHOS)
    Para recebimentos, busca TODOS os títulos do pedido para dar panorama geral

    Args:
        movimentacao_pai_id: int - ID da MovimentacaoFinanceira PAI

    Returns:
        dict {
            'movimentacao_pai': MovimentacaoFinanceira,
            'movimentacoes_filhas': list[MovimentacaoFinanceira],
            'itens_relacionados': list[dict] com detalhes de cada item,
            'todos_titulos_pedido': list[TituloFinanceiro] (apenas para recebimentos)
        }
    """
    from app.motochefe.models.financeiro import TituloFinanceiro

    movimentacao_pai = MovimentacaoFinanceira.query.get_or_404(movimentacao_pai_id)

    # Buscar movimentações filhas
    movimentacoes_filhas = MovimentacaoFinanceira.query.filter_by(
        movimentacao_origem_id=movimentacao_pai_id
    ).order_by(MovimentacaoFinanceira.id).all()

    # 🆕 DETECTAR SE É PAGAMENTO INDIVIDUAL (sem filhos)
    eh_pagamento_individual = len(movimentacoes_filhas) == 0

    # Se for recebimento e tiver pedido_id, buscar TODOS os títulos do pedido
    todos_titulos_pedido = []
    if movimentacao_pai.tipo == 'RECEBIMENTO' and movimentacao_pai.pedido_id:
        todos_titulos_pedido = TituloFinanceiro.query.filter_by(
            pedido_id=movimentacao_pai.pedido_id
        ).order_by(
            TituloFinanceiro.numero_chassi,
            TituloFinanceiro.numero_parcela,
            TituloFinanceiro.ordem_pagamento
        ).all()

    # Montar lista de itens relacionados com detalhes
    itens_relacionados = []
    # IDs dos títulos que tiveram movimentação (para marcar no template)
    titulos_com_movimentacao = set()

    # 🆕 SE FOR INDIVIDUAL, processar a própria movimentacao_pai
    if eh_pagamento_individual:
        movimentacoes_a_processar = [movimentacao_pai]
    else:
        movimentacoes_a_processar = movimentacoes_filhas

    for mov_filha in movimentacoes_a_processar:
        item_detalhe = {
            'movimentacao': mov_filha,
            'tipo_item': None,
            'item_objeto': None,
            'descricao_completa': mov_filha.descricao
        }

        # Identificar tipo de item baseado na categoria
        if mov_filha.categoria == 'Custo Moto' and mov_filha.numero_chassi:
            moto = Moto.query.filter_by(numero_chassi=mov_filha.numero_chassi).first()
            item_detalhe['tipo_item'] = 'MOTO'
            item_detalhe['item_objeto'] = moto

            if moto:
                # Calcular saldo ANTES e DEPOIS baseado no estado atual da moto
                # Saldo atual da moto
                saldo_atual = moto.custo_aquisicao - (moto.custo_pago or Decimal('0'))

                # Saldo ANTES = saldo atual + valor que foi pago nesta movimentação
                saldo_anterior = saldo_atual + mov_filha.valor

                # Saldo DEPOIS = saldo atual
                saldo_apos = saldo_atual

                item_detalhe['saldo_anterior'] = saldo_anterior
                item_detalhe['valor_pagamento'] = mov_filha.valor
                item_detalhe['saldo_apos'] = saldo_apos
            else:
                # Fallback se moto não encontrada
                item_detalhe['saldo_anterior'] = mov_filha.valor
                item_detalhe['valor_pagamento'] = mov_filha.valor
                item_detalhe['saldo_apos'] = Decimal('0')

        elif mov_filha.categoria == 'Comissão' and mov_filha.comissao_vendedor_id:
            comissao = db.session.get(ComissaoVendedor,mov_filha.comissao_vendedor_id) if mov_filha.comissao_vendedor_id else None
            item_detalhe['tipo_item'] = 'COMISSAO'
            item_detalhe['item_objeto'] = comissao

            # Para Comissão: saldo anterior = valor devido, após = 0 (quitado)
            item_detalhe['saldo_anterior'] = mov_filha.valor
            item_detalhe['valor_pagamento'] = mov_filha.valor
            item_detalhe['saldo_apos'] = Decimal('0')

        elif mov_filha.categoria == 'Montagem' and mov_filha.numero_chassi:
            item = db.session.query(PedidoVendaMotoItem).filter_by(numero_chassi=mov_filha.numero_chassi).first()
            item_detalhe['tipo_item'] = 'MONTAGEM'
            item_detalhe['item_objeto'] = item

            # Para Montagem: saldo anterior = valor devido, após = 0 (quitado)
            item_detalhe['saldo_anterior'] = mov_filha.valor
            item_detalhe['valor_pagamento'] = mov_filha.valor
            item_detalhe['saldo_apos'] = Decimal('0')

        elif mov_filha.categoria == 'Despesa' and mov_filha.despesa_mensal_id:
            despesa = db.session.get(DespesaMensal,mov_filha.despesa_mensal_id) if mov_filha.despesa_mensal_id else None
            item_detalhe['tipo_item'] = 'DESPESA'
            item_detalhe['item_objeto'] = despesa

            # Para Despesa: saldo anterior = valor devido, após = 0 (quitado)
            item_detalhe['saldo_anterior'] = mov_filha.valor
            item_detalhe['valor_pagamento'] = mov_filha.valor
            item_detalhe['saldo_apos'] = Decimal('0')

        elif mov_filha.categoria == 'Movimentação' and mov_filha.pedido_id and mov_filha.numero_chassi:
            from app.motochefe.models.financeiro import TituloAPagar

            # Buscar TituloAPagar de MOVIMENTACAO correspondente
            titulo_pagar = db.session.query(TituloAPagar).filter_by(
                pedido_id=mov_filha.pedido_id,
                numero_chassi=mov_filha.numero_chassi,
                tipo='MOVIMENTACAO'
            ).first()

            item_detalhe['tipo_item'] = 'MOVIMENTACAO'
            item_detalhe['item_objeto'] = titulo_pagar

            if titulo_pagar:
                # Calcular saldo HISTORICAMENTE
                # Buscar todas as movimentações POSTERIORES a esta para recalcular o saldo no momento
                movimentacoes_posteriores = db.session.query(MovimentacaoFinanceira).filter(
                    MovimentacaoFinanceira.pedido_id == mov_filha.pedido_id,
                    MovimentacaoFinanceira.numero_chassi == mov_filha.numero_chassi,
                    MovimentacaoFinanceira.categoria == 'Movimentação',
                    MovimentacaoFinanceira.id > mov_filha.id,
                    MovimentacaoFinanceira.tipo == 'PAGAMENTO'
                ).all()

                # Saldo atual + soma de todos os pagamentos posteriores = saldo ANTES deste pagamento
                valor_pagamentos_posteriores = sum(m.valor for m in movimentacoes_posteriores)
                saldo_anterior = titulo_pagar.valor_saldo + valor_pagamentos_posteriores + mov_filha.valor
                saldo_apos = saldo_anterior - mov_filha.valor

                item_detalhe['saldo_anterior'] = saldo_anterior
                item_detalhe['valor_pagamento'] = mov_filha.valor
                item_detalhe['saldo_apos'] = saldo_apos
            else:
                # Fallback se título não encontrado
                item_detalhe['saldo_anterior'] = mov_filha.valor
                item_detalhe['valor_pagamento'] = mov_filha.valor
                item_detalhe['saldo_apos'] = Decimal('0')

        elif mov_filha.categoria and 'Título' in mov_filha.categoria and mov_filha.titulo_financeiro_id:
            from app.motochefe.models.financeiro import TituloFinanceiro
            titulo = db.session.get(TituloFinanceiro,mov_filha.titulo_financeiro_id) if mov_filha.titulo_financeiro_id else None
            item_detalhe['tipo_item'] = 'TITULO'
            item_detalhe['item_objeto'] = titulo

            # Calcular saldo HISTORICAMENTE
            # Buscar todas as movimentações POSTERIORES a esta para recalcular o saldo no momento
            movimentacoes_posteriores = db.session.query(MovimentacaoFinanceira).filter(
                MovimentacaoFinanceira.titulo_financeiro_id == titulo.id,
                MovimentacaoFinanceira.id > mov_filha.id,
                MovimentacaoFinanceira.tipo == 'RECEBIMENTO'
            ).all()

            # Saldo atual + soma de todos os recebimentos posteriores = saldo ANTES deste pagamento
            valor_recebimentos_posteriores = sum(m.valor for m in movimentacoes_posteriores)
            saldo_anterior = titulo.valor_saldo + valor_recebimentos_posteriores + mov_filha.valor
            saldo_apos = saldo_anterior - mov_filha.valor

            item_detalhe['saldo_anterior'] = saldo_anterior
            item_detalhe['valor_pagamento'] = mov_filha.valor
            item_detalhe['saldo_apos'] = saldo_apos

            # Marcar este título como tendo movimentação
            titulos_com_movimentacao.add(titulo.id)

        itens_relacionados.append(item_detalhe)

    # Calcular totais de saldo anterior e saldo após (TODOS os tipos)
    total_saldo_anterior = Decimal('0')
    total_saldo_apos = Decimal('0')

    for item in itens_relacionados:
        # Somar para TODOS os itens que têm saldo (não apenas títulos)
        if 'saldo_anterior' in item:
            total_saldo_anterior += Decimal(str(item.get('saldo_anterior', 0)))
        if 'saldo_apos' in item:
            total_saldo_apos += Decimal(str(item.get('saldo_apos', 0)))

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'itens_relacionados': itens_relacionados,
        'todos_titulos_pedido': todos_titulos_pedido,
        'titulos_com_movimentacao': titulos_com_movimentacao,
        'total_saldo_anterior': total_saldo_anterior,
        'total_saldo_apos': total_saldo_apos,
        'eh_pagamento_individual': eh_pagamento_individual
    }


def processar_recebimento_lote_titulos(titulo_ids, valores_recebidos, empresa_recebedora, data_recebimento=None, usuario=None):
    """
    Processa recebimento em lote de títulos
    Cria 1 MovimentacaoFinanceira PAI + N FILHOS (um para cada título)

    Args:
        titulo_ids: list[int] - Lista de IDs de TituloFinanceiro
        valores_recebidos: dict - {titulo_id: valor_recebido}
        empresa_recebedora: EmpresaVendaMoto
        data_recebimento: date
        usuario: str

    Returns:
        dict {
            'movimentacao_pai': MovimentacaoFinanceira,
            'movimentacoes_filhas': list[MovimentacaoFinanceira],
            'titulos_recebidos': list[TituloFinanceiro],
            'valor_total': Decimal
        }
    """
    from app.motochefe.models.financeiro import TituloFinanceiro
    from app.motochefe.services.empresa_service import atualizar_saldo
    from app.motochefe.services.titulo_a_pagar_service import liberar_titulo_a_pagar
    from app.motochefe.services.baixa_automatica_service import processar_baixa_automatica_motos

    data_rec = data_recebimento or date.today()
    titulos = []
    movimentacoes_filhas = []
    valor_total = Decimal('0')
    cliente_nome = None
    pedido_num = None

    # 1. BUSCAR TÍTULOS E VALIDAR
    for titulo_id in titulo_ids:
        titulo = db.session.get(TituloFinanceiro,titulo_id) if titulo_id else None
        if not titulo:
            raise Exception(f'Título ID {titulo_id} não encontrado')

        valor_receber = Decimal(str(valores_recebidos.get(titulo_id, 0)))
        if valor_receber <= 0:
            continue

        if valor_receber > titulo.valor_saldo:
            raise Exception(f'Valor recebido (R$ {valor_receber}) excede saldo do título (R$ {titulo.valor_saldo})')

        titulos.append({'titulo': titulo, 'valor': valor_receber})
        valor_total += valor_receber

        # Capturar cliente e pedido do primeiro título
        if not cliente_nome and titulo.pedido and titulo.pedido.cliente:
            cliente_nome = titulo.pedido.cliente.cliente
            pedido_num = titulo.pedido.numero_pedido

    if not titulos:
        raise Exception('Nenhum título com valor válido para receber')

    # 2. CRIAR MOVIMENTAÇÃO PAI
    descricao_pai = f'Recebimento Lote {len(titulos)} título(s)'
    if pedido_num:
        descricao_pai += f' - Pedido {pedido_num}'

    movimentacao_pai = MovimentacaoFinanceira(
        tipo='RECEBIMENTO',
        categoria='Lote Recebimento',
        valor=valor_total,
        data_movimentacao=data_rec,
        empresa_origem_id=None,
        origem_tipo='Cliente',
        origem_identificacao=cliente_nome or 'Cliente',
        empresa_destino_id=empresa_recebedora.id,
        pedido_id=titulos[0]['titulo'].pedido_id if titulos else None,
        descricao=descricao_pai,
        observacoes=f'Lote com {len(titulos)} título(s) recebido(s)',
        criado_por=usuario
    )
    db.session.add(movimentacao_pai)
    db.session.flush()

    # 3. CRIAR MOVIMENTAÇÕES FILHAS + ATUALIZAR TÍTULOS
    for item in titulos:
        titulo = item['titulo']
        valor = item['valor']

        movimentacao_filha = MovimentacaoFinanceira(
            tipo='RECEBIMENTO',
            categoria=f'Título {titulo.tipo_titulo}',
            valor=valor,
            data_movimentacao=data_rec,
            empresa_origem_id=None,
            origem_tipo='Cliente',
            origem_identificacao=cliente_nome or 'Cliente',
            empresa_destino_id=empresa_recebedora.id,
            titulo_financeiro_id=titulo.id,
            pedido_id=titulo.pedido_id,
            numero_chassi=titulo.numero_chassi,
            descricao=f'Recebimento Título #{titulo.id} - {titulo.tipo_titulo} - Moto {titulo.numero_chassi}',
            movimentacao_origem_id=movimentacao_pai.id,
            criado_por=usuario
        )
        db.session.add(movimentacao_filha)
        movimentacoes_filhas.append(movimentacao_filha)

        titulo.valor_pago_total += valor
        titulo.valor_saldo -= valor
        titulo.empresa_recebedora_id = empresa_recebedora.id
        titulo.data_ultimo_pagamento = data_rec
        titulo.atualizado_por = usuario

        if titulo.valor_saldo <= 0:
            titulo.status = 'PAGO'
            liberar_titulo_a_pagar(titulo.id)
            
            if empresa_recebedora.baixa_compra_auto:
                processar_baixa_automatica_motos(empresa_recebedora, valor, movimentacao_filha.id, usuario)

            if titulo.tipo_titulo == 'VENDA':
                from app.motochefe.services.comissao_service import gerar_comissao_moto
                from app.motochefe.services.titulo_a_pagar_service import quitar_titulo_movimentacao_ao_pagar_moto

                gerar_comissao_moto(titulo)
                # ✅ Liberar/Quitar TituloAPagar de movimentação se incluir_custo_movimentacao=False
                quitar_titulo_movimentacao_ao_pagar_moto(titulo.numero_chassi, titulo.pedido_id, usuario)

    # 4. ATUALIZAR SALDO
    atualizar_saldo(empresa_recebedora.id, valor_total, 'SOMAR')
    db.session.flush()

    return {
        'movimentacao_pai': movimentacao_pai,
        'movimentacoes_filhas': movimentacoes_filhas,
        'titulos_recebidos': [item['titulo'] for item in titulos],
        'valor_total': valor_total
    }
