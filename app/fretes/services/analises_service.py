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
