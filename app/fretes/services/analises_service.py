"""
Service para análises de fretes
Fornece dados agregados por UF, Cidade, Sub-rota, Transportadora, Cliente e Mês
"""
from sqlalchemy import func, case, extract
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.localidades.models import CadastroSubRota
from app.transportadoras.models import Transportadora
from datetime import datetime, timedelta


def calcular_metricas(valor_frete, valor_despesa, valor_nf, peso):
    """
    Calcula as métricas de análise

    Args:
        valor_frete: Valor considerado do frete
        valor_despesa: Total de despesas extras
        valor_nf: Valor total das NFs
        peso: Peso total em KG

    Returns:
        dict com percentual_valor e valor_por_kg
    """
    valor_frete = valor_frete or 0
    valor_despesa = valor_despesa or 0
    valor_nf = valor_nf or 0
    peso = peso or 0

    total_custo = valor_frete + valor_despesa

    # Percentual do custo sobre o valor da NF
    percentual_valor = (total_custo / valor_nf * 100) if valor_nf > 0 else 0

    # Custo por KG
    valor_por_kg = (total_custo / peso) if peso > 0 else 0

    return {
        'percentual_valor': round(percentual_valor, 2),
        'valor_por_kg': round(valor_por_kg, 2),
        'total_custo': round(total_custo, 2),
        'valor_frete': round(valor_frete, 2),
        'valor_despesa': round(valor_despesa, 2),
        'valor_nf': round(valor_nf, 2),
        'peso': round(peso, 2)
    }


def calcular_frete_liquido_agregado(valor_frete_bruto, icms_total, pis_cofins_total):
    """
    Calcula o frete líquido a partir dos valores agregados

    Fórmula correta:
    Frete Líquido = (Valor Bruto - ICMS) - PIS/COFINS
    Ou: Frete Líquido = (Valor Bruto - ICMS) * (1 - 0.0925)

    Nota: PIS/COFINS já foi calculado sobre a base (valor_bruto - ICMS),
    então basta subtrair ambos.

    Args:
        valor_frete_bruto: Soma total de Frete.valor_considerado
        icms_total: Soma total de ICMS descontado
        pis_cofins_total: Soma total de PIS/COFINS descontado (já calculado sobre base líquida de ICMS)

    Returns:
        float: Frete líquido total
    """
    # Base após ICMS
    base_apos_icms = valor_frete_bruto - icms_total

    # Frete Líquido = Base - PIS/COFINS
    frete_liquido = base_apos_icms - pis_cofins_total

    return round(frete_liquido, 2)


def analise_por_uf(data_inicio=None, data_fim=None, transportadora_id=None, status=None):
    """
    Análise agregada por UF

    Returns:
        list: Lista de dicts com dados agregados por UF
    """
    # Subquery para somar despesas extras por frete
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        Frete.uf_destino.label('uf'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        # Adicionar 1 dia para incluir todo o dia final
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por UF
    query = query.group_by(Frete.uf_destino).order_by(Frete.uf_destino)

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'uf': row.uf,
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_cidade(data_inicio=None, data_fim=None, transportadora_id=None, uf=None, status=None):
    """
    Análise agregada por Cidade + UF

    Returns:
        list: Lista de dicts com dados agregados por Cidade/UF
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        Frete.uf_destino.label('uf'),
        Frete.cidade_destino.label('cidade'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por Cidade e UF
    query = query.group_by(Frete.uf_destino, Frete.cidade_destino).order_by(
        Frete.uf_destino, Frete.cidade_destino
    )

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'uf': row.uf,
            'cidade': row.cidade,
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_subrota(data_inicio=None, data_fim=None, transportadora_id=None, uf=None, status=None):
    """
    Análise agregada por UF + Sub-rota

    Returns:
        list: Lista de dicts com dados agregados por UF/Sub-rota
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal com LEFT JOIN em CadastroSubRota
    query = db.session.query(
        Frete.uf_destino.label('uf'),
        CadastroSubRota.sub_rota.label('sub_rota'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).outerjoin(
        CadastroSubRota,
        db.and_(
            Frete.uf_destino == CadastroSubRota.cod_uf,
            Frete.cidade_destino == CadastroSubRota.nome_cidade,
            CadastroSubRota.ativa == True
        )
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por UF e Sub-rota
    query = query.group_by(Frete.uf_destino, CadastroSubRota.sub_rota).order_by(
        Frete.uf_destino, CadastroSubRota.sub_rota
    )

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'uf': row.uf,
            'sub_rota': row.sub_rota or 'SEM SUB-ROTA',
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_transportadora(data_inicio=None, data_fim=None, uf=None, status=None):
    """
    Análise agregada por Transportadora

    Returns:
        list: Lista de dicts com dados agregados por Transportadora
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        Transportadora.id.label('transportadora_id'),
        Transportadora.razao_social.label('transportadora'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).join(
        Transportadora,
        Frete.transportadora_id == Transportadora.id
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por Transportadora
    query = query.group_by(Transportadora.id, Transportadora.razao_social).order_by(
        Transportadora.razao_social
    )

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'transportadora_id': row.transportadora_id,
            'transportadora': row.transportadora,
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_cliente(data_inicio=None, data_fim=None, transportadora_id=None, uf=None, status=None):
    """
    Análise agregada por Cliente

    Returns:
        list: Lista de dicts com dados agregados por Cliente
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        Frete.cnpj_cliente.label('cnpj_cliente'),
        Frete.nome_cliente.label('cliente'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por Cliente
    query = query.group_by(Frete.cnpj_cliente, Frete.nome_cliente).order_by(
        Frete.nome_cliente
    )

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'cnpj_cliente': row.cnpj_cliente,
            'cliente': row.cliente,
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_mes(data_inicio=None, data_fim=None, transportadora_id=None, uf=None, status=None):
    """
    Análise agregada por Mês/Ano

    Returns:
        list: Lista de dicts com dados agregados por Mês
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        extract('year', Frete.criado_em).label('ano'),
        extract('month', Frete.criado_em).label('mes'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por Ano e Mês
    query = query.group_by('ano', 'mes').order_by('ano', 'mes')

    resultados = query.all()

    # Processar resultados
    dados = []
    meses = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        mes_nome = meses.get(int(row.mes), str(row.mes))

        dados.append({
            'ano': int(row.ano),
            'mes': int(row.mes),
            'mes_nome': mes_nome,
            'periodo': f"{mes_nome}/{int(row.ano)}",
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_por_modalidade(data_inicio=None, data_fim=None, transportadora_id=None, uf=None, status=None):
    """
    Análise agregada por Modalidade (Veículo)

    Returns:
        list: Lista de dicts com dados agregados por Modalidade
    """
    # Subquery para despesas
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Query principal
    query = db.session.query(
        Frete.modalidade.label('modalidade'),
        func.count(Frete.id).label('qtd_fretes'),
        func.sum(Frete.valor_considerado).label('total_frete'),
        func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
        func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
        func.sum(Frete.peso_total).label('total_peso')
    ).outerjoin(
        subq_despesas,
        Frete.id == subq_despesas.c.frete_id
    ).filter(
        Frete.status != 'CANCELADO'  # ✅ Excluir fretes cancelados
    )

    # Aplicar filtros
    if data_inicio:
        query = query.filter(Frete.criado_em >= data_inicio)
    if data_fim:
        data_fim_inclusivo = data_fim + timedelta(days=1)
        query = query.filter(Frete.criado_em < data_fim_inclusivo)
    if transportadora_id:
        query = query.filter(Frete.transportadora_id == transportadora_id)
    if uf:
        query = query.filter(Frete.uf_destino == uf)
    if status:
        query = query.filter(Frete.status == status)

    # Agrupar por Modalidade
    query = query.group_by(Frete.modalidade).order_by(Frete.modalidade)

    resultados = query.all()

    # Processar resultados
    dados = []
    for row in resultados:
        metricas = calcular_metricas(
            valor_frete=row.total_frete,
            valor_despesa=row.total_despesa,
            valor_nf=row.total_valor_nf,
            peso=row.total_peso
        )

        dados.append({
            'modalidade': row.modalidade or 'NÃO INFORMADO',
            'qtd_fretes': row.qtd_fretes,
            **metricas
        })

    return dados


def analise_dinamica(filtros=None, group_by='uf', incluir_transportadora=True, incluir_freteiro=True):
    """
    Análise dinâmica que aceita array de filtros e agrupa por qualquer dimensão

    Args:
        filtros: [{'type': 'uf', 'value': 'SP'}, {'type': 'mes', 'value': '02/2025'}]
        group_by: 'uf' | 'transportadora' | 'modalidade' | 'mes' | 'subrota' | 'cliente'
        incluir_transportadora: Se True, inclui transportadoras (freteiro=False)
        incluir_freteiro: Se True, inclui freteiros (freteiro=True)

    Returns:
        list: Dados agregados pela dimensão escolhida com frete líquido calculado
    """
    # Subquery para despesas extras
    subq_despesas = db.session.query(
        DespesaExtra.frete_id,
        func.sum(DespesaExtra.valor_despesa).label('total_despesas')
    ).group_by(DespesaExtra.frete_id).subquery()

    # Definir campos de agrupamento baseado no group_by
    if group_by == 'uf':
        group_field = Frete.uf_destino
        label_field = 'uf'
        needs_join = None
    elif group_by == 'transportadora':
        group_field = Transportadora.razao_social
        label_field = 'transportadora'
        needs_join = 'transportadora'
    elif group_by == 'modalidade':
        group_field = Frete.modalidade
        label_field = 'modalidade'
        needs_join = None
    elif group_by == 'mes':
        # Para mês, precisamos agrupar por ano e mês
        label_field = 'periodo'
        needs_join = None
    elif group_by == 'subrota':
        group_field = CadastroSubRota.sub_rota
        label_field = 'sub_rota'
        needs_join = 'subrota'
    elif group_by == 'cliente':
        group_field = Frete.nome_cliente
        label_field = 'cliente'
        needs_join = None
    else:
        # Default para UF
        group_field = Frete.uf_destino
        label_field = 'uf'
        needs_join = None

    # Calcular ICMS: Se (freteiro=False OU freteiro IS NULL) E optante=False
    # ICMS = (tabela_icms_proprio OR tabela_icms_destino) / 100 * valor_considerado
    # Campos estão como PERCENTUAL (ex: 12), precisa dividir por 100
    # IMPORTANTE: freteiro NULL é tratado como transportadora (não freteiro)
    icms_calc = case(
        (
            db.and_(
                db.or_(
                    Transportadora.freteiro == False,
                    Transportadora.freteiro.is_(None)
                ),
                db.or_(
                    Transportadora.optante == False,
                    Transportadora.optante.is_(None)
                )
            ),
            (func.coalesce(Frete.tabela_icms_proprio, Frete.tabela_icms_destino, 0) / 100.0) * Frete.valor_considerado
        ),
        else_=0
    )

    # Calcular Base para PIS/COFINS: valor_considerado - ICMS
    # PIS/COFINS = (valor_considerado - ICMS) * 0.0925
    # Aplica em todos que NÃO são freteiros (freteiro=False OU freteiro IS NULL)
    pis_cofins_calc = case(
        (
            db.or_(
                Transportadora.freteiro == False,
                Transportadora.freteiro.is_(None)
            ),
            (Frete.valor_considerado - icms_calc) * 0.0925
        ),
        else_=0
    )

    # Construir query base
    if group_by == 'mes':
        # Query especial para mês
        query = db.session.query(
            extract('year', Frete.criado_em).label('ano'),
            extract('month', Frete.criado_em).label('mes'),
            func.count(Frete.id).label('qtd_fretes'),
            func.sum(Frete.valor_considerado).label('total_frete'),
            func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
            func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
            func.sum(Frete.peso_total).label('total_peso'),
            func.sum(icms_calc).label('total_icms'),
            func.sum(pis_cofins_calc).label('total_pis_cofins')
        )
    else:
        query = db.session.query(
            group_field.label('dimensao'),
            func.count(Frete.id).label('qtd_fretes'),
            func.sum(Frete.valor_considerado).label('total_frete'),
            func.sum(func.coalesce(subq_despesas.c.total_despesas, 0)).label('total_despesa'),
            func.sum(Frete.valor_total_nfs).label('total_valor_nf'),
            func.sum(Frete.peso_total).label('total_peso'),
            func.sum(icms_calc).label('total_icms'),
            func.sum(pis_cofins_calc).label('total_pis_cofins')
        )

    # Aplicar joins necessários
    query = query.outerjoin(subq_despesas, Frete.id == subq_despesas.c.frete_id)

    # SEMPRE fazer JOIN com Transportadora (necessário para cálculos de ICMS/PIS/COFINS)
    query = query.join(Transportadora, Frete.transportadora_id == Transportadora.id)

    # ✅ Excluir fretes cancelados
    query = query.filter(Frete.status != 'CANCELADO')

    # Join adicional para subrota se necessário
    if needs_join == 'subrota':
        query = query.outerjoin(
            CadastroSubRota,
            db.and_(
                Frete.uf_destino == CadastroSubRota.cod_uf,
                Frete.cidade_destino == CadastroSubRota.nome_cidade,
                CadastroSubRota.ativa == True
            )
        )

    # Aplicar filtro dos checkboxes (Transportadora/Freteiro)
    # IMPORTANTE: NULL em freteiro é tratado como transportadora
    if not incluir_transportadora and not incluir_freteiro:
        # Se nenhum checkbox marcado, retornar vazio
        query = query.filter(db.false())
    elif incluir_transportadora and not incluir_freteiro:
        # Apenas transportadoras (freteiro=False OU freteiro IS NULL)
        query = query.filter(
            db.or_(
                Transportadora.freteiro == False,
                Transportadora.freteiro.is_(None)
            )
        )
    elif not incluir_transportadora and incluir_freteiro:
        # Apenas freteiros (freteiro=True)
        query = query.filter(Transportadora.freteiro == True)
    # else: ambos marcados, não aplicar filtro (traz tudo)

    # Aplicar filtros dinamicamente
    if filtros:
        for filtro in filtros:
            filter_type = filtro['type']
            filter_value = filtro['value']

            if filter_type == 'uf':
                query = query.filter(Frete.uf_destino == filter_value)
            elif filter_type == 'transportadora':
                # Filtrar pela razão social da transportadora
                # JOIN já foi feito anteriormente (linha ~666), não precisa adicionar novamente
                query = query.filter(Transportadora.razao_social == filter_value)
            elif filter_type == 'modalidade':
                query = query.filter(Frete.modalidade == filter_value)
            elif filter_type == 'mes':
                # Formato esperado: "02/2025" ou "Fev/2025"
                if '/' in filter_value:
                    parts = filter_value.split('/')
                    mes_parte = parts[0]
                    ano_parte = parts[1]

                    # Converter nome do mês para número se necessário
                    meses_map = {
                        'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4, 'Mai': 5, 'Jun': 6,
                        'Jul': 7, 'Ago': 8, 'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12
                    }

                    try:
                        # Tentar converter diretamente
                        mes_num = int(mes_parte)
                    except ValueError:
                        # Se falhar, tentar pelo mapa de nomes
                        mes_num = meses_map.get(mes_parte, 1)

                    ano_num = int(ano_parte)

                    query = query.filter(
                        extract('month', Frete.criado_em) == mes_num,
                        extract('year', Frete.criado_em) == ano_num
                    )
            elif filter_type == 'subrota':
                query = query.filter(CadastroSubRota.sub_rota == filter_value)
                # Garantir que o join existe
                if needs_join != 'subrota':
                    query = query.outerjoin(
                        CadastroSubRota,
                        db.and_(
                            Frete.uf_destino == CadastroSubRota.cod_uf,
                            Frete.cidade_destino == CadastroSubRota.nome_cidade,
                            CadastroSubRota.ativa == True
                        )
                    )
            elif filter_type == 'cliente':
                query = query.filter(Frete.nome_cliente == filter_value)

    # Agrupar e ordenar
    if group_by == 'mes':
        query = query.group_by('ano', 'mes').order_by('ano', 'mes')
    else:
        query = query.group_by('dimensao').order_by('dimensao')

    # Executar query
    resultados = query.all()

    # Processar resultados
    dados = []

    if group_by == 'mes':
        meses = {
            1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
        }

        for row in resultados:
            # Calcular frete líquido
            frete_liquido = calcular_frete_liquido_agregado(
                valor_frete_bruto=row.total_frete,
                icms_total=row.total_icms,
                pis_cofins_total=row.total_pis_cofins
            )

            # Calcular métricas usando frete líquido
            metricas = calcular_metricas(
                valor_frete=frete_liquido,  # Usar frete líquido
                valor_despesa=row.total_despesa,
                valor_nf=row.total_valor_nf,
                peso=row.total_peso
            )

            mes_nome = meses.get(int(row.mes), str(row.mes))
            periodo = f"{mes_nome}/{int(row.ano)}"

            dados.append({
                'label': periodo,
                'ano': int(row.ano),
                'mes': int(row.mes),
                'mes_nome': mes_nome,
                'periodo': periodo,
                'qtd_fretes': row.qtd_fretes,
                'valor_frete_bruto': round(row.total_frete, 2),  # Incluir frete bruto
                'total_icms': round(row.total_icms, 2),
                'total_pis_cofins': round(row.total_pis_cofins, 2),
                **metricas
            })
    else:
        for row in resultados:
            # Calcular frete líquido
            frete_liquido = calcular_frete_liquido_agregado(
                valor_frete_bruto=row.total_frete,
                icms_total=row.total_icms,
                pis_cofins_total=row.total_pis_cofins
            )

            # Calcular métricas usando frete líquido
            metricas = calcular_metricas(
                valor_frete=frete_liquido,  # Usar frete líquido
                valor_despesa=row.total_despesa,
                valor_nf=row.total_valor_nf,
                peso=row.total_peso
            )

            # Tratar valores None
            label = str(row.dimensao) if row.dimensao else 'NÃO INFORMADO'

            # Tratamento especial para sub-rota
            if group_by == 'subrota' and not row.dimensao:
                label = 'SEM SUB-ROTA'

            dados.append({
                'label': label,
                'qtd_fretes': row.qtd_fretes,
                'valor_frete_bruto': round(row.total_frete, 2),  # Incluir frete bruto
                'total_icms': round(row.total_icms, 2),
                'total_pis_cofins': round(row.total_pis_cofins, 2),
                **metricas
            })

    return dados
