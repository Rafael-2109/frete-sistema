"""
Service para Extrato Financeiro - Sistema MotoCHEFE
Consolida TODAS as movimentações financeiras (recebimentos e pagamentos) realizadas
"""
from sqlalchemy import text
from decimal import Decimal
from app import db


def obter_movimentacoes_financeiras(data_inicial=None, data_final=None,
                                     cliente_id=None, fornecedor=None, vendedor_id=None, #type: ignore
                                     transportadora_id=None, tipo_movimentacao=None): #type: ignore
    """
    Retorna TODAS as movimentações financeiras consolidadas

    Parâmetros:
        data_inicial: Data início do filtro (obrigatório se tipo_movimentacao não especificado)
        data_final: Data fim do filtro (obrigatório se tipo_movimentacao não especificado)
        cliente_id: ID do cliente (filtra recebimentos)
        fornecedor: Nome do fornecedor (filtra pagamentos de motos)
        vendedor_id: ID do vendedor (filtra comissões)
        transportadora_id: ID da transportadora (filtra fretes)
        tipo_movimentacao: 'RECEBIMENTO' ou 'PAGAMENTO' (None = todos)

    Retorna:
        Lista de dicts com estrutura:
        {
            'id': int,
            'tipo': str ('RECEBIMENTO' ou 'PAGAMENTO'),
            'categoria': str ('Título', 'Custo Moto', 'Montagem', 'Comissão', 'Frete', 'Despesa'),
            'data_movimentacao': date,
            'descricao': str (detalhada com entidade),
            'valor': Decimal (positivo para recebimento, negativo para pagamento),
            'cliente_fornecedor': str (nome da entidade relacionada),
            'numero_pedido': str ou None,
            'numero_nf': str ou None,
            'numero_chassi': str ou None,
            'numero_embarque': str ou None,
            'rota_detalhes': str (URL para detalhes),
            'id_original': int ou str (ID do registro original)
        }
    """

    # SQL RAW para UNION ALL de todas as movimentações
    # Estrutura: tipo, categoria, data, descrição, valor, entidade, pedido, nf, chassi, embarque, rota, id_original

    sql_parts = []

    # ==================== RECEBIMENTOS ====================

    # 1. MOVIMENTAÇÕES FINANCEIRAS DE RECEBIMENTO (da tabela movimentacao_financeira)
    sql_recebimento = """
    SELECT
        'RECEBIMENTO' AS tipo,
        mf.categoria AS categoria,
        mf.data_movimentacao AS data_movimentacao,
        CONCAT(
            mf.categoria, ' - ', mf.descricao,
            CASE WHEN mf.origem_identificacao IS NOT NULL
                 THEN CONCAT(' - ', mf.origem_identificacao)
                 ELSE '' END
        ) AS descricao,
        mf.valor AS valor,
        COALESCE(mf.origem_identificacao, 'Cliente') AS cliente_fornecedor,
        CASE WHEN mf.pedido_id IS NOT NULL
             THEN (SELECT numero_pedido FROM pedido_venda_moto WHERE id = mf.pedido_id)
             ELSE NULL END AS numero_pedido,
        NULL AS numero_nf,
        mf.numero_chassi AS numero_chassi,
        NULL AS numero_embarque,
        CASE WHEN mf.titulo_financeiro_id IS NOT NULL
             THEN CONCAT('/motochefe/titulos/', mf.titulo_financeiro_id, '/detalhes')
             ELSE NULL END AS rota_detalhes,
        CAST(mf.id AS TEXT) AS id_original
    FROM movimentacao_financeira mf
    WHERE mf.tipo = 'RECEBIMENTO'
    """

    # Filtros para recebimentos
    filtros_recebimento = []
    if data_inicial and data_final:
        filtros_recebimento.append(f"AND mf.data_movimentacao BETWEEN '{data_inicial}' AND '{data_final}'")
    if cliente_id:
        # Filtrar por cliente através do pedido relacionado
        filtros_recebimento.append(f"AND mf.pedido_id IN (SELECT id FROM pedido_venda_moto WHERE cliente_id = {cliente_id})")
    if tipo_movimentacao == 'PAGAMENTO':
        sql_parts.append("SELECT NULL LIMIT 0")  # Não incluir recebimentos
    else:
        sql_recebimento += " " + " ".join(filtros_recebimento)
        sql_parts.append(sql_recebimento)


    # ==================== PAGAMENTOS ====================

    if tipo_movimentacao != 'RECEBIMENTO':

        # 2. CUSTO DE MOTOS (Pagamento a Fornecedores)
        sql_moto = """
        SELECT
            'PAGAMENTO' AS tipo,
            'Custo Moto' AS categoria,
            m.data_pagamento_custo AS data_movimentacao,
            CONCAT(
                'Custo Moto Chassi ', m.numero_chassi,
                ' - NF ', m.nf_entrada,
                ' - Fornecedor: ', m.fornecedor
            ) AS descricao,
            -m.custo_pago AS valor,
            m.fornecedor AS cliente_fornecedor,
            NULL AS numero_pedido,
            m.nf_entrada AS numero_nf,
            m.numero_chassi AS numero_chassi,
            NULL AS numero_embarque,
            CONCAT('/motochefe/motos/', m.numero_chassi, '/editar') AS rota_detalhes,
            m.numero_chassi AS id_original
        FROM moto m
        WHERE m.status_pagamento_custo = 'PAGO'
          AND m.data_pagamento_custo IS NOT NULL
          AND m.ativo = TRUE
        """

        filtros_moto = []
        if data_inicial and data_final:
            filtros_moto.append(f"AND m.data_pagamento_custo BETWEEN '{data_inicial}' AND '{data_final}'")
        if fornecedor:
            filtros_moto.append(f"AND m.fornecedor ILIKE '%{fornecedor}%'")

        sql_moto += " " + " ".join(filtros_moto)
        sql_parts.append(sql_moto)


        # 3. MONTAGEM (Pagamento a Fornecedores de Montagem)
        sql_montagem = """
        SELECT
            'PAGAMENTO' AS tipo,
            'Montagem' AS categoria,
            pvmi.data_pagamento_montagem AS data_movimentacao,
            CONCAT(
                'Montagem Moto Chassi ', pvmi.numero_chassi,
                ' - Pedido ', pvm.numero_pedido,
                ' - Fornecedor: ', pvmi.fornecedor_montagem
            ) AS descricao,
            -pvmi.valor_montagem AS valor,
            pvmi.fornecedor_montagem AS cliente_fornecedor,
            pvm.numero_pedido AS numero_pedido,
            pvm.numero_nf AS numero_nf,
            pvmi.numero_chassi AS numero_chassi,
            NULL AS numero_embarque,
            CONCAT('/motochefe/pedidos/', pvm.id, '/detalhes') AS rota_detalhes,
            CAST(pvmi.id AS TEXT) AS id_original
        FROM pedido_venda_moto_item pvmi
        JOIN pedido_venda_moto pvm ON pvmi.pedido_id = pvm.id
        WHERE pvmi.montagem_paga = TRUE
          AND pvmi.data_pagamento_montagem IS NOT NULL
          AND pvmi.ativo = TRUE
        """

        filtros_montagem = []
        if data_inicial and data_final:
            filtros_montagem.append(f"AND pvmi.data_pagamento_montagem BETWEEN '{data_inicial}' AND '{data_final}'")
        if fornecedor:
            filtros_montagem.append(f"AND pvmi.fornecedor_montagem ILIKE '%{fornecedor}%'")

        sql_montagem += " " + " ".join(filtros_montagem)
        sql_parts.append(sql_montagem)


        # 4. COMISSÕES (Pagamento a Vendedores)
        sql_comissao = """
        SELECT
            'PAGAMENTO' AS tipo,
            'Comissão' AS categoria,
            cv.data_pagamento AS data_movimentacao,
            CONCAT(
                'Comissão Pedido ', pvm.numero_pedido,
                ' - Vendedor: ', vm.vendedor
            ) AS descricao,
            -cv.valor_rateado AS valor,
            vm.vendedor AS cliente_fornecedor,
            pvm.numero_pedido AS numero_pedido,
            pvm.numero_nf AS numero_nf,
            NULL AS numero_chassi,
            NULL AS numero_embarque,
            CONCAT('/motochefe/comissoes/', cv.id, '/detalhes') AS rota_detalhes,
            CAST(cv.id AS TEXT) AS id_original
        FROM comissao_vendedor cv
        JOIN pedido_venda_moto pvm ON cv.pedido_id = pvm.id
        JOIN vendedor_moto vm ON cv.vendedor_id = vm.id
        WHERE cv.status = 'PAGO'
          AND cv.data_pagamento IS NOT NULL
        """

        filtros_comissao = []
        if data_inicial and data_final:
            filtros_comissao.append(f"AND cv.data_pagamento BETWEEN '{data_inicial}' AND '{data_final}'")
        if vendedor_id:
            filtros_comissao.append(f"AND cv.vendedor_id = {vendedor_id}")

        sql_comissao += " " + " ".join(filtros_comissao)
        sql_parts.append(sql_comissao)


        # 5. FRETES (Pagamento a Transportadoras)
        sql_frete = """
        SELECT
            'PAGAMENTO' AS tipo,
            'Frete' AS categoria,
            em.data_pagamento_frete AS data_movimentacao,
            CONCAT(
                'Frete Embarque ', em.numero_embarque,
                ' - Transportadora: ', tm.transportadora
            ) AS descricao,
            -em.valor_frete_pago AS valor,
            tm.transportadora AS cliente_fornecedor,
            NULL AS numero_pedido,
            NULL AS numero_nf,
            NULL AS numero_chassi,
            em.numero_embarque AS numero_embarque,
            CONCAT('/motochefe/embarques/', em.id, '/editar') AS rota_detalhes,
            CAST(em.id AS TEXT) AS id_original
        FROM embarque_moto em
        JOIN transportadora_moto tm ON em.transportadora_id = tm.id
        WHERE em.status_pagamento_frete = 'PAGO'
          AND em.data_pagamento_frete IS NOT NULL
          AND em.ativo = TRUE
        """

        filtros_frete = []
        if data_inicial and data_final:
            filtros_frete.append(f"AND em.data_pagamento_frete BETWEEN '{data_inicial}' AND '{data_final}'")
        if transportadora_id:
            filtros_frete.append(f"AND em.transportadora_id = {transportadora_id}")

        sql_frete += " " + " ".join(filtros_frete)
        sql_parts.append(sql_frete)


        # 6. DESPESAS OPERACIONAIS (Pagamentos Diversos)
        sql_despesa = """
        SELECT
            'PAGAMENTO' AS tipo,
            'Despesa' AS categoria,
            dm.data_pagamento AS data_movimentacao,
            CONCAT(
                'Despesa: ', dm.tipo_despesa,
                CASE WHEN dm.descricao IS NOT NULL
                     THEN CONCAT(' - ', dm.descricao)
                     ELSE '' END,
                ' - Competência: ', LPAD(CAST(dm.mes_competencia AS TEXT), 2, '0'), '/', dm.ano_competencia
            ) AS descricao,
            -dm.valor_pago AS valor,
            dm.tipo_despesa AS cliente_fornecedor,
            NULL AS numero_pedido,
            NULL AS numero_nf,
            NULL AS numero_chassi,
            NULL AS numero_embarque,
            CONCAT('/motochefe/despesas/', dm.id, '/editar') AS rota_detalhes,
            CAST(dm.id AS TEXT) AS id_original
        FROM despesa_mensal dm
        WHERE dm.status = 'PAGO'
          AND dm.data_pagamento IS NOT NULL
          AND dm.ativo = TRUE
        """

        filtros_despesa = []
        if data_inicial and data_final:
            filtros_despesa.append(f"AND dm.data_pagamento BETWEEN '{data_inicial}' AND '{data_final}'")

        sql_despesa += " " + " ".join(filtros_despesa)
        sql_parts.append(sql_despesa)


    # ==================== EXECUTAR UNION ====================

    if not sql_parts:
        return []

    sql_final = " UNION ALL ".join(sql_parts)
    sql_final += " ORDER BY data_movimentacao DESC, id_original DESC"

    resultado = db.session.execute(text(sql_final))

    # Converter para lista de dicts
    movimentacoes = []
    for row in resultado:
        movimentacoes.append({
            'tipo': row[0],
            'categoria': row[1],
            'data_movimentacao': row[2],
            'descricao': row[3],
            'valor': Decimal(str(row[4])) if row[4] else Decimal('0'),
            'cliente_fornecedor': row[5],
            'numero_pedido': row[6],
            'numero_nf': row[7],
            'numero_chassi': row[8],
            'numero_embarque': row[9],
            'rota_detalhes': row[10],
            'id_original': row[11]
        })

    return movimentacoes


def calcular_saldo_acumulado(movimentacoes):
    """
    Calcula o saldo acumulado progressivo para cada movimentação
    Recebimentos somam (+), Pagamentos subtraem (-)
    """
    saldo = Decimal('0')

    # Inverter ordem para calcular do mais antigo para o mais recente
    movimentacoes_ordenadas = sorted(movimentacoes, key=lambda x: (x['data_movimentacao'], x['id_original']))

    for mov in movimentacoes_ordenadas:
        saldo += mov['valor']  # Valor já vem com sinal correto
        mov['saldo_acumulado'] = saldo

    # Retornar na ordem original (mais recente primeiro)
    return sorted(movimentacoes_ordenadas, key=lambda x: (x['data_movimentacao'], x['id_original']), reverse=True)
