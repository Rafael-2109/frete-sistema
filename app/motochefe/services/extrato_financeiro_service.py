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
    # 🆕 FILTRO: Exclui movimentações FILHAS (movimentacao_origem_id IS NULL)
    # Mostra apenas PAI (lotes) e recebimentos individuais
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
        CONCAT('/motochefe/recebimentos/', mf.id, '/detalhes') AS rota_detalhes,
        CAST(mf.id AS TEXT) AS id_original
    FROM movimentacao_financeira mf
    WHERE mf.tipo = 'RECEBIMENTO'
      AND mf.movimentacao_origem_id IS NULL
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

        # 2. PAGAMENTOS - USAR MOVIMENTACAOFINANCEIRA PAI E INDIVIDUAIS
        # 🆕 Mostra lotes (movimentacao_origem_id IS NULL) E pagamentos individuais
        # Categorias:
        #   - Lotes: 'Lote Custo Moto', 'Lote Comissão', 'Lote Montagem', 'Lote Despesa'
        #   - Individuais: 'Custo Moto', 'Comissão', 'Montagem', 'Despesa', 'Frete'
        sql_pagamentos_lote = """
        SELECT
            'PAGAMENTO' AS tipo,
            mf.categoria AS categoria,
            mf.data_movimentacao AS data_movimentacao,
            mf.descricao AS descricao,
            -mf.valor AS valor,
            COALESCE(
                mf.destino_identificacao,
                (SELECT empresa FROM empresa_venda_moto WHERE id = mf.empresa_destino_id),
                'Fornecedor'
            ) AS cliente_fornecedor,
            NULL AS numero_pedido,
            mf.numero_nf AS numero_nf,
            mf.numero_chassi AS numero_chassi,
            NULL AS numero_embarque,
            CONCAT('/motochefe/pagamentos/', mf.id, '/detalhes') AS rota_detalhes,
            CAST(mf.id AS TEXT) AS id_original
        FROM movimentacao_financeira mf
        WHERE mf.tipo = 'PAGAMENTO'
          AND mf.movimentacao_origem_id IS NULL
          AND mf.categoria IN ('Lote Custo Moto', 'Lote Comissão', 'Lote Montagem', 'Lote Despesa',
                               'Custo Moto', 'Comissão', 'Montagem', 'Despesa', 'Frete')
        """

        filtros_pagamentos = []
        if data_inicial and data_final:
            filtros_pagamentos.append(f"AND mf.data_movimentacao BETWEEN '{data_inicial}' AND '{data_final}'")

        sql_pagamentos_lote += " " + " ".join(filtros_pagamentos)
        sql_parts.append(sql_pagamentos_lote)


        # 3. FRETES (Pagamento a Transportadoras - ainda individual, não em lote)
        # ⚠️ Frete ainda usa tabela embarque_moto diretamente
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
