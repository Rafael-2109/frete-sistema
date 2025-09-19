"""
Rotas para visão da diretoria - acesso completo
"""
from flask import render_template, jsonify, request
from flask_login import login_required
from app.comercial import comercial_bp
from app.comercial.services.cliente_service import ClienteService
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import distinct
from app import db


@comercial_bp.route('/')
@comercial_bp.route('/dashboard')
@login_required
def dashboard_diretoria():
    """
    Dashboard principal da diretoria com badges de equipes
    """
    # Buscar todas as equipes distintas
    equipes_carteira = db.session.query(
        distinct(CarteiraPrincipal.equipe_vendas)
    ).filter(
        CarteiraPrincipal.equipe_vendas.isnot(None),
        CarteiraPrincipal.equipe_vendas != ''
    ).all()

    equipes_faturamento = db.session.query(
        distinct(FaturamentoProduto.equipe_vendas)
    ).filter(
        FaturamentoProduto.equipe_vendas.isnot(None),
        FaturamentoProduto.equipe_vendas != ''
    ).all()

    # Unir e fazer distinct
    equipes_set = set()
    for e in equipes_carteira:
        if e[0]:
            equipes_set.add(e[0])

    for e in equipes_faturamento:
        if e[0]:
            equipes_set.add(e[0])

    equipes = sorted(list(equipes_set))

    # Para cada equipe, contar clientes e calcular valores
    equipes_data = []
    for equipe in equipes:
        clientes_cnpj = ClienteService.obter_clientes_por_equipe(equipe)

        # Calcular valor total em aberto da equipe
        valor_total_equipe = 0
        for cnpj in clientes_cnpj:
            valor_cliente = ClienteService.calcular_valor_em_aberto(cnpj, 'em_aberto')
            valor_total_equipe += valor_cliente

        equipes_data.append({
            'nome': equipe,
            'total_clientes': len(clientes_cnpj),
            'valor_em_aberto': float(valor_total_equipe)
        })

    return render_template('comercial/dashboard_diretoria.html',
                         equipes=equipes_data)


@comercial_bp.route('/equipe/<string:equipe_nome>')
@login_required
def vendedores_equipe(equipe_nome):
    """
    Visualização de vendedores de uma equipe específica
    """
    # Buscar vendedores da equipe
    vendedores_carteira = db.session.query(
        distinct(CarteiraPrincipal.vendedor)
    ).filter(
        CarteiraPrincipal.equipe_vendas == equipe_nome,
        CarteiraPrincipal.vendedor.isnot(None),
        CarteiraPrincipal.vendedor != ''
    ).all()

    vendedores_faturamento = db.session.query(
        distinct(FaturamentoProduto.vendedor)
    ).filter(
        FaturamentoProduto.equipe_vendas == equipe_nome,
        FaturamentoProduto.vendedor.isnot(None),
        FaturamentoProduto.vendedor != ''
    ).all()

    # Unir e fazer distinct
    vendedores_set = set()
    for v in vendedores_carteira:
        if v[0]:
            vendedores_set.add(v[0])

    for v in vendedores_faturamento:
        if v[0]:
            vendedores_set.add(v[0])

    vendedores = sorted(list(vendedores_set))

    # Para cada vendedor, contar clientes e calcular valores
    vendedores_data = []
    for vendedor in vendedores:
        clientes_cnpj = ClienteService.obter_clientes_por_vendedor(vendedor)

        # Calcular valor total em aberto do vendedor
        valor_total_vendedor = 0
        for cnpj in clientes_cnpj:
            valor_cliente = ClienteService.calcular_valor_em_aberto(cnpj, 'em_aberto')
            valor_total_vendedor += valor_cliente

        vendedores_data.append({
            'nome': vendedor,
            'total_clientes': len(clientes_cnpj),
            'valor_em_aberto': float(valor_total_vendedor)
        })

    return render_template('comercial/vendedores_equipe.html',
                         equipe_nome=equipe_nome,
                         vendedores=vendedores_data)


@comercial_bp.route('/clientes')
@login_required
def lista_clientes():
    """
    Lista de clientes agrupados com filtros
    """
    # Obter parâmetros de filtro
    filtro_posicao = request.args.get('posicao', 'em_aberto')  # em_aberto ou todos
    equipe_filtro = request.args.get('equipe', None)
    vendedor_filtro = request.args.get('vendedor', None)

    # Buscar clientes conforme filtros
    if vendedor_filtro:
        clientes_cnpj = ClienteService.obter_clientes_por_vendedor(vendedor_filtro)
    elif equipe_filtro:
        clientes_cnpj = ClienteService.obter_clientes_por_equipe(equipe_filtro)
    else:
        clientes_cnpj = ClienteService.obter_todos_clientes_distintos()

    # Buscar dados de cada cliente
    clientes_data = []
    for cnpj in clientes_cnpj:
        dados_cliente = ClienteService.obter_dados_cliente(cnpj, filtro_posicao)

        # Adicionar ao resultado
        clientes_data.append({
            'cnpj_cpf': dados_cliente['cnpj_cpf'],
            'raz_social': dados_cliente['raz_social'],
            'raz_social_red': dados_cliente['raz_social_red'],
            'estado': dados_cliente['estado'],
            'municipio': dados_cliente['municipio'],
            'vendedor': dados_cliente['vendedor'],
            'equipe_vendas': dados_cliente['equipe_vendas'],
            'forma_agendamento': dados_cliente['forma_agendamento'],
            'valor_em_aberto': float(dados_cliente['valor_em_aberto']),
            'total_pedidos': dados_cliente['total_pedidos']
        })

    # Ordenar por valor em aberto (maior para menor)
    clientes_data.sort(key=lambda x: x['valor_em_aberto'], reverse=True)

    return render_template('comercial/lista_clientes.html',
                         clientes=clientes_data,
                         filtro_posicao=filtro_posicao,
                         equipe_filtro=equipe_filtro,
                         vendedor_filtro=vendedor_filtro)


@comercial_bp.route('/api/cliente/<string:cnpj>/detalhes')
@login_required
def detalhes_cliente_api(cnpj):
    """
    API para obter detalhes de um cliente específico
    """
    filtro_posicao = request.args.get('posicao', 'em_aberto')

    dados = ClienteService.obter_dados_cliente(cnpj, filtro_posicao)

    # Converter Decimal para float para JSON
    dados['valor_em_aberto'] = float(dados['valor_em_aberto'])

    return jsonify(dados)