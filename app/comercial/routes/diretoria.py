"""
Rotas para visão da diretoria - acesso completo
"""
from flask import render_template, jsonify, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.comercial import comercial_bp
from app.comercial.services.cliente_service import ClienteService
from app.comercial.services.pedido_service import PedidoService
from app.comercial.services.documento_service import DocumentoService
from app.comercial.services.produto_documento_service import ProdutoDocumentoService
from app.comercial.services.permissao_service import PermissaoService
from app.comercial.services.agregacao_service import AgregacaoComercialService
from app.comercial.decorators import comercial_required, admin_comercial_required, get_permissoes_cached
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import distinct, text, func
import typing as t
from typing import Optional
from app import db
import logging
import pandas as pd
from io import BytesIO
from datetime import datetime, date

logger = logging.getLogger(__name__)


def _coletar_clientes_data(
    filtro_posicao: str,
    equipe_filtro: Optional[str],
    vendedor_filtro: Optional[str],
    filtros_avancados: t.Dict[str, str]
) -> t.List[t.Dict[str, object]]:
    """Monta a lista de clientes respeitando filtros e permissões."""

    filtros_avancados_ativos = any(value.strip() for value in filtros_avancados.values())

    is_vendedor = current_user.is_authenticated and current_user.perfil == 'vendedor'
    # OTIMIZAÇÃO: Usa cache de permissões para evitar múltiplas queries
    permissoes = get_permissoes_cached() if is_vendedor else {
        'equipes': [],
        'vendedores': []
    }

    clientes_cnpjs: t.List[str] = []

    if filtros_avancados_ativos:
        sql = text("""
            WITH pedidos_filtrados AS (
                SELECT
                    cnpj_cpf,
                    num_pedido,
                    pedido_cliente,
                    raz_social,
                    raz_social_red,
                    estado,
                    municipio,
                    vendedor,
                    equipe_vendas,
                    qtd_saldo_produto_pedido,
                    preco_produto_pedido,
                    (qtd_saldo_produto_pedido * preco_produto_pedido) as valor_item
                FROM carteira_principal
                WHERE
                    -- TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
                    (:posicao = 'todos' OR qtd_saldo_produto_pedido > 0.02)

                    AND (:is_vendedor = false OR
                         ((:equipe_filtro IS NOT NULL AND equipe_vendas = :equipe_filtro) OR
                          (:vendedor_filtro IS NOT NULL AND vendedor = :vendedor_filtro) OR
                          (:equipe_filtro IS NULL AND :vendedor_filtro IS NULL AND
                           (equipe_vendas = ANY(:equipes_permitidas) OR
                            vendedor = ANY(:vendedores_permitidos)))))

                    AND (:equipe_filtro IS NULL OR equipe_vendas = :equipe_filtro)
                    AND (:vendedor_filtro IS NULL OR vendedor = :vendedor_filtro)

                    AND (:pedido = '' OR
                         lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')) OR
                         lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')))

                    AND (:num_pedido = '' OR
                         lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :num_pedido || '%')))

                    AND (:pedido_cliente = '' OR
                         lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido_cliente || '%')))
            ),
            clientes_agrupados AS (
                SELECT
                    cnpj_cpf,
                    SUM(valor_item) as valor_em_aberto
                FROM pedidos_filtrados
                WHERE
                    (:cnpj_cpf = '' OR cnpj_cpf LIKE '%' || :cnpj_cpf || '%')

                    AND (:cliente = '' OR
                         lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')) OR
                         lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')))

                    AND (:raz_social = '' OR
                         lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :raz_social || '%')))

                    AND (:raz_social_red = '' OR
                         lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :raz_social_red || '%')))

                    AND (:uf = '' OR estado = :uf)
                GROUP BY cnpj_cpf
                HAVING SUM(valor_item) > 0 OR :posicao = 'todos'
            )
            SELECT cnpj_cpf
            FROM clientes_agrupados
        """)

        is_vendedor_param = is_vendedor
        equipes_permitidas = permissoes.get('equipes', []) if is_vendedor else []
        vendedores_permitidos = permissoes.get('vendedores', []) if is_vendedor else []

        params = {
            'posicao': filtro_posicao,
            'is_vendedor': is_vendedor_param,
            'equipe_filtro': equipe_filtro,
            'vendedor_filtro': vendedor_filtro,
            'equipes_permitidas': equipes_permitidas or [''],
            'vendedores_permitidos': vendedores_permitidos or [''],
            'cnpj_cpf': filtros_avancados['cnpj_cpf'],
            'cliente': filtros_avancados['cliente'],
            'pedido': filtros_avancados['pedido'],
            'raz_social': filtros_avancados['raz_social'],
            'raz_social_red': filtros_avancados['raz_social_red'],
            'uf': filtros_avancados['uf'],
            'num_pedido': filtros_avancados['num_pedido'],
            'pedido_cliente': filtros_avancados['pedido_cliente']
        }

        resultado = db.session.execute(sql, params).fetchall()
        clientes_cnpjs = [row.cnpj_cpf for row in resultado if row.cnpj_cpf]

        # Se há filtro de pedido_cliente, buscar também via FaturamentoProduto
        # Estratégia: CarteiraPrincipal.pedido_cliente → num_pedido → FaturamentoProduto.cnpj_cliente
        if filtros_avancados['pedido_cliente'].strip():
            # Passo 1: Buscar num_pedidos que têm o pedido_cliente filtrado
            # Usar text() para evitar problemas com f_unaccent em literais
            sql_pedido_cliente = text("""
                SELECT DISTINCT num_pedido
                FROM carteira_principal
                WHERE pedido_cliente IS NOT NULL
                  AND lower(f_unaccent(pedido_cliente)) LIKE lower(f_unaccent(:pattern))
            """)

            num_pedidos_com_filtro = db.session.execute(
                sql_pedido_cliente,
                {'pattern': f"%{filtros_avancados['pedido_cliente']}%"}
            ).fetchall()

            num_pedidos_lista = [row[0] for row in num_pedidos_com_filtro if row[0]]

            # Passo 2: Buscar CNPJs que faturaram esses num_pedidos
            if num_pedidos_lista:
                cnpjs_via_faturamento = db.session.query(
                    distinct(FaturamentoProduto.cnpj_cliente)
                ).filter(
                    FaturamentoProduto.origem.in_(num_pedidos_lista),
                    FaturamentoProduto.status_nf != 'Cancelado',
                    FaturamentoProduto.cnpj_cliente.isnot(None)
                ).all()

                for cnpj_row in cnpjs_via_faturamento:
                    if cnpj_row[0] and cnpj_row[0] not in clientes_cnpjs:
                        clientes_cnpjs.append(cnpj_row[0])

        # Se há filtro de pedido (via campo "Pedido:"), buscar também CNPJs via FaturamentoProduto
        if filtros_avancados['pedido'].strip():
            # Passo 1: Buscar num_pedidos que batem com o filtro (via pedido_cliente também)
            sql_busca_pedidos = text("""
                SELECT DISTINCT num_pedido
                FROM carteira_principal
                WHERE (lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent(:pattern))
                   OR lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent(:pattern)))
            """)

            num_pedidos_encontrados = db.session.execute(
                sql_busca_pedidos,
                {'pattern': f"%{filtros_avancados['pedido']}%"}
            ).fetchall()

            num_pedidos_lista = [row[0] for row in num_pedidos_encontrados if row[0]]

            # Passo 2: Buscar CNPJs que faturaram esses pedidos
            if num_pedidos_lista:
                if filtro_posicao == 'em_aberto':
                    # Para "Em Aberto": apenas faturamento não entregue
                    sql_cnpjs_faturados = text("""
                        SELECT DISTINCT fp.cnpj_cliente
                        FROM faturamento_produto fp
                        LEFT JOIN entregas_monitoradas em ON fp.numero_nf = em.numero_nf
                        WHERE fp.status_nf != 'Cancelado'
                          AND fp.cnpj_cliente IS NOT NULL
                          AND fp.origem = ANY(:pedidos_lista)
                          AND (em.status_finalizacao != 'Entregue' OR em.status_finalizacao IS NULL)
                    """)
                else:
                    # Para "Todos": qualquer faturamento
                    sql_cnpjs_faturados = text("""
                        SELECT DISTINCT fp.cnpj_cliente
                        FROM faturamento_produto fp
                        WHERE fp.status_nf != 'Cancelado'
                          AND fp.cnpj_cliente IS NOT NULL
                          AND fp.origem = ANY(:pedidos_lista)
                    """)

                cnpjs_faturados = db.session.execute(
                    sql_cnpjs_faturados,
                    {'pedidos_lista': num_pedidos_lista}
                ).fetchall()

                for cnpj_row in cnpjs_faturados:
                    if cnpj_row[0] and cnpj_row[0] not in clientes_cnpjs:
                        clientes_cnpjs.append(cnpj_row[0])

    else:
        if vendedor_filtro:
            clientes_cnpjs = ClienteService.obter_clientes_por_vendedor(
                vendedor_filtro
            )
        elif equipe_filtro:
            clientes_cnpjs = ClienteService.obter_clientes_por_equipe(equipe_filtro)
        else:
            if is_vendedor:
                clientes_cnpj_set: set[str] = set()

                for equipe in permissoes['equipes']:
                    clientes_cnpj_set.update(ClienteService.obter_clientes_por_equipe(equipe))

                for vendedor in permissoes['vendedores']:
                    clientes_cnpj_set.update(ClienteService.obter_clientes_por_vendedor(vendedor))

                clientes_cnpjs = sorted(clientes_cnpj_set)
            else:
                clientes_cnpjs = ClienteService.obter_todos_clientes_distintos()

    # Remover duplicados preservando ordem
    clientes_cnpjs = list(dict.fromkeys(clientes_cnpjs))

    vendedor_filtro_norm = vendedor_filtro.strip() if isinstance(vendedor_filtro, str) else None
    equipe_filtro_norm = equipe_filtro.strip() if isinstance(equipe_filtro, str) else None

    clientes_data: t.List[t.Dict[str, object]] = []
    for cnpj in clientes_cnpjs:
        pedidos_posicao = ClienteService.obter_pedidos_cliente(cnpj, filtro_posicao)
        pedidos_todos = ClienteService.obter_pedidos_cliente(cnpj, 'todos')

        pedido_filtro_norm = (filtros_avancados['pedido'] or '').strip().lower()
        num_pedido_filtro_norm = (filtros_avancados['num_pedido'] or '').strip().lower()
        pedido_cliente_filtro_norm = (filtros_avancados['pedido_cliente'] or '').strip().lower()
        filtros_pedido_ativos = any([pedido_filtro_norm, num_pedido_filtro_norm, pedido_cliente_filtro_norm])

        pedido_cliente_map: dict[str, str] = {}
        base_para_map = pedidos_todos or pedidos_posicao
        if base_para_map:
            pedidos_para_busca = [str(p) for p in base_para_map if str(p).strip()]
            if pedidos_para_busca:
                # Buscar pedido_cliente na CarteiraPrincipal
                rows_carteira = db.session.query(
                    CarteiraPrincipal.num_pedido,
                    func.max(CarteiraPrincipal.pedido_cliente)
                ).filter(
                    CarteiraPrincipal.cnpj_cpf == cnpj,
                    CarteiraPrincipal.num_pedido.in_(pedidos_para_busca)
                ).group_by(
                    CarteiraPrincipal.num_pedido
                ).all()
                pedido_cliente_map = {row[0]: (row[1] or '') for row in rows_carteira}

                # Buscar pedido_cliente via FaturamentoProduto (JOIN com CarteiraPrincipal)
                # Para pedidos que foram faturados mas podem não estar mais na carteira
                rows_faturados = db.session.query(
                    FaturamentoProduto.origem.label('num_pedido'),
                    func.max(CarteiraPrincipal.pedido_cliente).label('pedido_cliente')
                ).join(
                    CarteiraPrincipal,
                    FaturamentoProduto.origem == CarteiraPrincipal.num_pedido
                ).filter(
                    FaturamentoProduto.cnpj_cliente == cnpj,
                    FaturamentoProduto.origem.in_(pedidos_para_busca),
                    FaturamentoProduto.status_nf != 'Cancelado',
                    CarteiraPrincipal.pedido_cliente.isnot(None)
                ).group_by(
                    FaturamentoProduto.origem
                ).all()

                # Mesclar resultados (prioridade para carteira, depois faturamento)
                for row in rows_faturados:
                    if row.num_pedido and row.pedido_cliente:
                        if row.num_pedido not in pedido_cliente_map or not pedido_cliente_map[row.num_pedido]:
                            pedido_cliente_map[row.num_pedido] = row.pedido_cliente

        if filtros_pedido_ativos:
            # Usar a lista correta baseado no filtro de posição
            # Se filtro é "Em Aberto", usar apenas pedidos em aberto
            # Se filtro é "Todos", usar todos os pedidos
            if filtro_posicao == 'em_aberto':
                base_lista = pedidos_posicao
            else:
                base_lista = pedidos_todos

            def _match_pedido(numero: str) -> bool:
                alvo = str(numero or '').lower()
                pedido_cli = (pedido_cliente_map.get(str(numero), '') or '').lower()
                # Campo "Pedido:" busca em num_pedido OU pedido_cliente
                return ((pedido_filtro_norm and (pedido_filtro_norm in alvo or pedido_filtro_norm in pedido_cli)) or
                        (num_pedido_filtro_norm and num_pedido_filtro_norm in alvo) or
                        (pedido_cliente_filtro_norm and pedido_cliente_filtro_norm in pedido_cli)) # type: ignore

            pedidos_considerados = [p for p in base_lista if _match_pedido(p)]
            if not pedidos_considerados:
                continue
        else:
            pedidos_considerados = pedidos_posicao

        pedidos_considerados = [p for p in pedidos_considerados if str(p).strip()]
        pedidos_set = {str(p) for p in pedidos_considerados}

        dados_cliente = ClienteService.obter_dados_cliente(
            cnpj,
            filtro_posicao,
            pedidos_set if filtros_pedido_ativos else None
        )

        valor_em_aberto = float(dados_cliente['valor_em_aberto']) if dados_cliente['valor_em_aberto'] else 0.0
        valor_total = float(dados_cliente['valor_total']) if dados_cliente['valor_total'] else 0.0
        valor_principal = valor_em_aberto if filtro_posicao == 'em_aberto' else valor_total

        if filtro_posicao == 'em_aberto' and valor_principal <= 0:
            continue

        vendedor_cliente = (dados_cliente['vendedor'] or '').strip() if dados_cliente['vendedor'] else ''
        equipe_cliente = (dados_cliente['equipe_vendas'] or '').strip() if dados_cliente['equipe_vendas'] else ''

        if vendedor_filtro_norm and vendedor_cliente != vendedor_filtro_norm:
            continue
        if equipe_filtro_norm and equipe_cliente != equipe_filtro_norm:
            continue

        clientes_data.append({
            'cnpj_cpf': dados_cliente['cnpj_cpf'],
            'raz_social': dados_cliente['raz_social'],
            'raz_social_red': dados_cliente['raz_social_red'],
            'estado': dados_cliente['estado'],
            'municipio': dados_cliente['municipio'],
            'vendedor': dados_cliente['vendedor'],
            'equipe_vendas': dados_cliente['equipe_vendas'],
            'forma_agendamento': dados_cliente['forma_agendamento'],
            'total_pedidos': dados_cliente['total_pedidos'],
            'valor_em_aberto': valor_em_aberto,
            'valor_total': valor_total,
            'valor_principal': valor_principal,
            'pedidos': dados_cliente['pedidos']
        })

    clientes_data.sort(key=lambda x: x['valor_principal'], reverse=True)
    return clientes_data


@comercial_bp.route('/')
@comercial_bp.route('/dashboard')
@login_required
@comercial_required
def dashboard_diretoria():
    """
    Dashboard principal da diretoria com badges de equipes
    OTIMIZADO: Usa AgregacaoComercialService para reduzir de 500+ queries para 1
    """
    # Se for vendedor e não tiver permissões, mostrar mensagem
    if current_user.perfil == 'vendedor':
        if not PermissaoService.usuario_tem_permissoes(current_user.id):
            flash('Você ainda não possui permissões configuradas. Solicite ao administrador.', 'warning')
            return render_template('comercial/dashboard_diretoria.html', equipes=[])

    # Obter filtro de equipes baseado em permissões (para vendedores)
    equipes_filtro = None
    if current_user.perfil == 'vendedor':
        # OTIMIZAÇÃO: Usa cache de permissões para evitar múltiplas queries
        permissoes = get_permissoes_cached()

        # Se tem permissões específicas de equipes, usar como filtro
        if permissoes['equipes']:
            equipes_filtro = permissoes['equipes']
        elif permissoes['vendedores']:
            # Se só tem permissão de vendedores, buscar as equipes desses vendedores
            equipes_dos_vendedores = db.session.query(
                distinct(CarteiraPrincipal.equipe_vendas)
            ).filter(
                CarteiraPrincipal.vendedor.in_(permissoes['vendedores']),
                CarteiraPrincipal.equipe_vendas.isnot(None)
            ).all()
            equipes_filtro = [e[0] for e in equipes_dos_vendedores if e[0]]

    # OTIMIZAÇÃO: Usar query única com CTE ao invés de N+1 queries
    equipes_data = AgregacaoComercialService.obter_dashboard_completo_otimizado(equipes_filtro)

    return render_template('comercial/dashboard_diretoria.html',
                         equipes=equipes_data)


@comercial_bp.route('/equipe/<string:equipe_nome>')
@login_required
@comercial_required
def vendedores_equipe(equipe_nome):
    """
    Visualização de vendedores de uma equipe específica
    OTIMIZADO: Usa AgregacaoComercialService para reduzir de 600+ queries para 1
    """
    # Se for vendedor, verificar se tem acesso à equipe
    vendedores_filtro = None
    if current_user.perfil == 'vendedor':
        # OTIMIZAÇÃO: Usa cache de permissões para evitar múltiplas queries
        permissoes = get_permissoes_cached()

        # Verificar se tem acesso direto à equipe
        tem_acesso = equipe_nome in permissoes['equipes']

        # Se não tem acesso direto, verificar se tem acesso a algum vendedor da equipe
        if not tem_acesso:
            # Buscar vendedores da equipe que o usuário tem permissão
            vendedores_equipe_lista = db.session.query(
                distinct(CarteiraPrincipal.vendedor)
            ).filter(
                CarteiraPrincipal.equipe_vendas == equipe_nome,
                CarteiraPrincipal.vendedor.isnot(None)
            ).all()

            vendedores_permitidos = []
            for v in vendedores_equipe_lista:
                if v[0] in permissoes['vendedores']:
                    vendedores_permitidos.append(v[0])
                    tem_acesso = True

            if tem_acesso:
                vendedores_filtro = vendedores_permitidos

        if not tem_acesso:
            flash('Você não tem permissão para acessar esta equipe.', 'danger')
            return redirect(url_for('comercial.dashboard_diretoria'))

    # OTIMIZAÇÃO: Usar query única com CTE ao invés de N+1 queries
    vendedores_data = AgregacaoComercialService.obter_vendedores_equipe_otimizado(
        equipe_nome,
        vendedores_filtro
    )

    return render_template('comercial/vendedores_equipe.html',
                         equipe_nome=equipe_nome,
                         vendedores=vendedores_data)


@comercial_bp.route('/clientes')
@login_required
@comercial_required
def lista_clientes():
    """
    Lista de clientes agrupados com filtros avançados
    Suporta busca sem acento e filtros múltiplos
    """
    # Obter parâmetros de filtro
    filtro_posicao = request.args.get('posicao', 'em_aberto')  # em_aberto ou todos
    equipe_filtro = request.args.get('equipe', None)
    vendedor_filtro = request.args.get('vendedor', None)

    # Novos filtros unificados
    cnpj_cpf_filtro = request.args.get('cnpj_cpf', '').strip()
    cliente_filtro = request.args.get('cliente', '').strip()  # Busca em razão social OU nome fantasia
    pedido_filtro = request.args.get('pedido', '').strip()    # Busca em num_pedido OU pedido_cliente
    uf_filtro = request.args.get('uf', '').strip()

    # Manter compatibilidade com filtros antigos (caso venham de outros lugares)
    raz_social_filtro = request.args.get('raz_social', '').strip()
    raz_social_red_filtro = request.args.get('raz_social_red', '').strip()
    num_pedido_filtro = request.args.get('num_pedido', '').strip()
    pedido_cliente_filtro = request.args.get('pedido_cliente', '').strip()

    # Se for vendedor, aplicar restrições de permissões
    if current_user.perfil == 'vendedor':
        # OTIMIZAÇÃO: Usa cache de permissões para evitar múltiplas queries
        permissoes = get_permissoes_cached()

        # Se não tem permissões, mostrar página vazia
        if not permissoes['equipes'] and not permissoes['vendedores']:
            flash('Você não possui permissões configuradas.', 'warning')
            return render_template('comercial/lista_clientes.html',
                                 clientes=[],
                                 filtro_posicao=filtro_posicao,
                                 equipe_filtro=equipe_filtro,
                                 vendedor_filtro=vendedor_filtro)

        # Validar filtros contra permissões
        if equipe_filtro and equipe_filtro not in permissoes['equipes']:
            # Verificar se tem acesso a algum vendedor da equipe
            tem_acesso = False
            vendedores_equipe = db.session.query(
                distinct(CarteiraPrincipal.vendedor)
            ).filter(
                CarteiraPrincipal.equipe_vendas == equipe_filtro,
                CarteiraPrincipal.vendedor.isnot(None)
            ).all()

            for v in vendedores_equipe:
                if v[0] in permissoes['vendedores']:
                    tem_acesso = True
                    break

            if not tem_acesso:
                flash('Você não tem permissão para acessar esta equipe.', 'danger')
                return redirect(url_for('comercial.dashboard_diretoria'))

        if vendedor_filtro and vendedor_filtro not in permissoes['vendedores']:
            # Verificar se tem acesso à equipe do vendedor
            vendedor_equipe = db.session.query(CarteiraPrincipal.equipe_vendas).filter(
                CarteiraPrincipal.vendedor == vendedor_filtro
            ).first()

            if not vendedor_equipe or vendedor_equipe[0] not in permissoes['equipes']:
                flash('Você não tem permissão para acessar este vendedor.', 'danger')
                return redirect(url_for('comercial.dashboard_diretoria'))

    filtros_avancados = {
        'cnpj_cpf': cnpj_cpf_filtro,
        'cliente': cliente_filtro,
        'pedido': pedido_filtro,
        'uf': uf_filtro,
        'raz_social': raz_social_filtro,
        'raz_social_red': raz_social_red_filtro,
        'num_pedido': num_pedido_filtro,
        'pedido_cliente': pedido_cliente_filtro
    }

    clientes_data = _coletar_clientes_data(
        filtro_posicao=filtro_posicao,
        equipe_filtro=equipe_filtro,
        vendedor_filtro=vendedor_filtro,
        filtros_avancados=filtros_avancados
    )

    # Buscar UFs disponíveis para o dropdown
    ufs_disponiveis = []
    if clientes_data:
        # Extrair UFs únicas dos clientes já filtrados
        ufs_set = {c['estado'] for c in clientes_data if c['estado']}
        ufs_disponiveis = sorted(list(ufs_set))
    else:
        # Se não há clientes, buscar UFs disponíveis no banco
        # TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
        ufs = db.session.query(distinct(CarteiraPrincipal.estado)).filter(
            CarteiraPrincipal.estado.isnot(None),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02 if filtro_posicao == 'em_aberto' else True
        ).all()
        ufs_disponiveis = sorted([uf[0] for uf in ufs if uf[0]])

    # Calcular totais
    total_clientes = len(clientes_data)
    valor_total = sum(c['valor_principal'] for c in clientes_data)

    return render_template('comercial/lista_clientes.html',
                         clientes=clientes_data,
                         filtro_posicao=filtro_posicao,
                         equipe_filtro=equipe_filtro,
                         vendedor_filtro=vendedor_filtro,
                         ufs_disponiveis=ufs_disponiveis,
                         total_clientes=total_clientes,
                         valor_total=valor_total)


@comercial_bp.route('/clientes/exportar_excel')
@login_required
@comercial_required
def exportar_clientes_excel():
    """
    Exporta dados detalhados dos clientes para Excel
    Uma linha por produto, com todos os dados do cliente/pedido/documento repetidos
    """
    filtro_posicao = request.args.get('posicao', 'em_aberto')
    equipe_filtro = request.args.get('equipe', None)
    vendedor_filtro = request.args.get('vendedor', None)
    cnpj_cpf_filtro = request.args.get('cnpj_cpf', '').strip()
    cliente_filtro = request.args.get('cliente', '').strip()
    pedido_filtro = request.args.get('pedido', '').strip()
    uf_filtro = request.args.get('uf', '').strip()
    raz_social_filtro = request.args.get('raz_social', '').strip()
    raz_social_red_filtro = request.args.get('raz_social_red', '').strip()
    num_pedido_filtro = request.args.get('num_pedido', '').strip()
    pedido_cliente_filtro = request.args.get('pedido_cliente', '').strip()

    if current_user.perfil == 'vendedor':
        # OTIMIZAÇÃO: Usa cache de permissões para evitar múltiplas queries
        permissoes = get_permissoes_cached()

        if not permissoes['equipes'] and not permissoes['vendedores']:
            flash('Você não possui permissões para exportar dados.', 'warning')
            return redirect(url_for('comercial.lista_clientes', posicao=filtro_posicao))

        if equipe_filtro and equipe_filtro not in permissoes['equipes']:
            flash('Você não tem permissão para acessar esta equipe.', 'danger')
            return redirect(url_for('comercial.lista_clientes', posicao=filtro_posicao))

        if vendedor_filtro and vendedor_filtro not in permissoes['vendedores']:
            flash('Você não tem permissão para acessar este vendedor.', 'danger')
            return redirect(url_for('comercial.lista_clientes', posicao=filtro_posicao))

    filtros_avancados = {
        'cnpj_cpf': cnpj_cpf_filtro,
        'cliente': cliente_filtro,
        'pedido': pedido_filtro,
        'uf': uf_filtro,
        'raz_social': raz_social_filtro,
        'raz_social_red': raz_social_red_filtro,
        'num_pedido': num_pedido_filtro,
        'pedido_cliente': pedido_cliente_filtro
    }

    clientes_data = _coletar_clientes_data(
        filtro_posicao=filtro_posicao,
        equipe_filtro=equipe_filtro,
        vendedor_filtro=vendedor_filtro,
        filtros_avancados=filtros_avancados
    )

    if not clientes_data:
        flash('Nenhum cliente encontrado para exportação.', 'warning')
        return redirect(url_for('comercial.lista_clientes', posicao=filtro_posicao))

    def preparar_data_excel(valor):
        """
        Prepara valor de data para Excel preservando tipo datetime/date.
        Retorna None para vazios, datetime/date objects para datas válidas, string caso contrário.
        """
        if not valor or valor in ('-', ''):
            return None
        if isinstance(valor, str):
            valor_limpo = valor.replace('Previsão:', '').replace('previsão:', '').strip()
            if not valor_limpo:
                return None
            # Tentar converter string para datetime
            formatos = ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d']
            for fmt in formatos:
                try:
                    return datetime.strptime(valor_limpo, fmt)
                except ValueError:
                    continue
            return valor_limpo
        # Já é datetime/date - preservar
        if isinstance(valor, (datetime, date)):
            return valor
        return valor

    linhas: t.List[t.Dict[str, object]] = []

    for cliente in clientes_data:
        cnpj = cliente['cnpj_cpf']
        pedidos_cliente = cliente.get('pedidos') or ClienteService.obter_pedidos_cliente(cnpj, filtro_posicao)

        for num_pedido in pedidos_cliente:
            pedido_info = PedidoService._processar_pedido(num_pedido, cnpj, None, None)

            carteira_info = db.session.query(
                func.min(CarteiraPrincipal.data_pedido).label('data_pedido'),
                func.min(CarteiraPrincipal.expedicao).label('expedicao'),
                func.min(CarteiraPrincipal.agendamento).label('agendamento'),
                func.max(CarteiraPrincipal.protocolo).label('protocolo')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido == num_pedido
            ).first()

            agendamento_confirmado_carteira = db.session.query(CarteiraPrincipal.id).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.agendamento_confirmado.is_(True)
            ).first() is not None

            documentos = DocumentoService.obter_documentos_pedido(num_pedido=num_pedido, cnpj_cliente=cnpj)
            docs = documentos.get('documentos', [])

            saldo_carteira_float = float(pedido_info.get('saldo_carteira') or 0)
            if not docs and saldo_carteira_float > 0:
                docs = [{
                    'tipo': 'Saldo',
                    'valor': saldo_carteira_float,
                    'numero_nf': '-',
                    'data_faturamento': None,
                    'data_embarque': carteira_info.expedicao if carteira_info else None,
                    'data_agendamento': carteira_info.agendamento if carteira_info else None,
                    'protocolo_agendamento': carteira_info.protocolo if carteira_info and carteira_info.protocolo else '',
                    'status_agendamento': 'aguardando',
                    'data_entrega_prevista': None,
                    'data_entrega_realizada': None,
                    'cnpj_transportadora': '',
                    'nome_transportadora': '',
                    'status_finalizacao': ''
                }]

            for doc in docs:
                if filtro_posicao == 'em_aberto' and doc.get('tipo') == 'NF':
                    status_finalizacao = (doc.get('status_finalizacao') or '').lower()
                    entrega_realizada = doc.get('data_entrega_realizada')
                    if status_finalizacao == 'entregue':
                        continue
                    if entrega_realizada and entrega_realizada not in ('', '-', None):
                        continue

                tipo_documento = 'NF' if doc.get('tipo') == 'NF' else ('Separacao' if doc.get('tipo') == 'Separação' else 'Saldo')
                if tipo_documento == 'NF':
                    identificador = doc.get('numero_nf')
                elif tipo_documento == 'Separacao':
                    identificador = doc.get('separacao_lote_id')
                else:
                    identificador = num_pedido

                if not identificador:
                    identificador = num_pedido

                produtos_result = ProdutoDocumentoService.obter_produtos_documento(
                    tipo_documento=tipo_documento,
                    identificador=identificador,
                    num_pedido=num_pedido if tipo_documento == 'Saldo' else None
                )

                produtos_lista = produtos_result.get('produtos') or [{
                    'codigo': '-',
                    'produto': '-',
                    'quantidade': 0,
                    'preco': 0,
                    'valor': float(doc.get('valor') or 0),
                    'peso': 0,
                    'pallet': 0
                }]

                data_pedido = pedido_info.get('data_pedido') or (carteira_info.data_pedido if carteira_info else None)
                data_expedicao = doc.get('data_embarque') or (carteira_info.expedicao if carteira_info else None)
                data_agendamento = doc.get('data_agendamento') or (carteira_info.agendamento if carteira_info else None)
                protocolo_agendamento = doc.get('protocolo_agendamento') or (carteira_info.protocolo if carteira_info and carteira_info.protocolo else '')

                agendamento_confirmado_doc = (doc.get('status_agendamento') or '').lower() == 'confirmado'
                agendamento_confirmado = agendamento_confirmado_doc or agendamento_confirmado_carteira

                status_entrega = doc.get('status_finalizacao') or doc.get('status_agendamento')
                if not status_entrega:
                    status_entrega = 'Em Aberto' if doc.get('tipo') != 'NF' else ''

                valor_documento = float(doc.get('valor', 0) or 0)

                for produto in produtos_lista:
                    quantidade_produto = float(produto.get('quantidade', 0) or 0)
                    if abs(quantidade_produto) < 0.01:
                        continue
                    linhas.append({
                        'Equipe Vendas': cliente.get('equipe_vendas') or '',
                        'Vendedor': cliente.get('vendedor') or '',
                        'CNPJ Cliente': cliente['cnpj_cpf'],
                        'Razão Social': cliente.get('raz_social') or '',
                        'Nome Fantasia': cliente.get('raz_social_red') or '',
                        'Município': cliente.get('municipio') or '',
                        'UF': cliente.get('estado') or '',
                        'Número Pedido': num_pedido,
                        'Pedido Cliente': pedido_info.get('pedido_cliente') if pedido_info.get('pedido_cliente') != '-' else '',
                        'Tipo Registro': 'Faturamento' if doc.get('tipo') == 'NF' else doc.get('tipo'),
                        'Identificador Documento': identificador or '',
                        'Data Pedido': preparar_data_excel(data_pedido),
                        'Data Faturamento': preparar_data_excel(doc.get('data_faturamento')),
                        'Data Expedição': preparar_data_excel(data_expedicao),
                        'Data Agendamento': preparar_data_excel(data_agendamento),
                        'Protocolo Agendamento': protocolo_agendamento,
                        'Agendamento Confirmado': 'Sim' if agendamento_confirmado else 'Não',
                        'Status Entrega': status_entrega,
                        'Data Entrega Prevista': preparar_data_excel(doc.get('data_entrega_prevista')),
                        'Data Entrega Realizada': preparar_data_excel(doc.get('data_entrega_realizada')),
                        'CNPJ Transportadora': doc.get('cnpj_transportadora') or '',
                        'Nome Transportadora': doc.get('nome_transportadora') or doc.get('transportadora') or '',
                        'Incoterm': pedido_info.get('incoterm') if pedido_info.get('incoterm') != '-' else '',
                        'Método Entrega': pedido_info.get('metodo_entrega_pedido') if pedido_info.get('metodo_entrega_pedido') != '-' else '',
                        'Status Pedido': pedido_info.get('status'),
                        'Valor Pedido': float(pedido_info.get('valor_total_pedido') or 0),
                        'Valor Faturado Pedido': float(pedido_info.get('valor_total_faturado') or 0),
                        'Saldo Carteira Pedido': float(pedido_info.get('saldo_carteira') or 0),
                        'Valor Documento': valor_documento,
                        'Código Produto': produto.get('codigo', ''),
                        'Produto': produto.get('produto', ''),
                        'Quantidade': quantidade_produto,
                        'Preço Unitário': float(produto.get('preco', 0) or 0),
                        'Valor Produto': float(produto.get('valor', 0) or 0),
                        'Peso Total': float(produto.get('peso', 0) or 0),
                        'Pallets': float(produto.get('pallet', 0) or 0),
                        'Forma Agendamento Cliente': cliente.get('forma_agendamento') or ''
                    })

    df = pd.DataFrame(linhas)

    colunas_ordenadas = [
        'Equipe Vendas', 'Vendedor', 'CNPJ Cliente', 'Razão Social', 'Nome Fantasia', 'Município', 'UF',
        'Número Pedido', 'Pedido Cliente', 'Tipo Registro', 'Identificador Documento', 'Data Pedido',
        'Data Faturamento', 'Data Expedição', 'Data Agendamento', 'Protocolo Agendamento',
        'Agendamento Confirmado', 'Status Entrega', 'Data Entrega Prevista', 'Data Entrega Realizada',
        'CNPJ Transportadora', 'Nome Transportadora', 'Incoterm', 'Método Entrega', 'Status Pedido',
        'Valor Pedido', 'Valor Faturado Pedido', 'Saldo Carteira Pedido', 'Valor Documento',
        'Código Produto', 'Produto', 'Quantidade', 'Preço Unitário', 'Valor Produto', 'Peso Total',
        'Pallets', 'Forma Agendamento Cliente'
    ]

    if not df.empty:
        df = df[colunas_ordenadas]
    else:
        df = pd.DataFrame(columns=colunas_ordenadas)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Clientes Detalhado', index=False)

        worksheet = writer.sheets['Clientes Detalhado']

        # Aplicar formatação de data para colunas específicas
        colunas_data = ['Data Pedido', 'Data Faturamento', 'Data Expedição', 'Data Agendamento',
                        'Data Entrega Prevista', 'Data Entrega Realizada']

        for col_idx, col_name in enumerate(df.columns, start=1):
            column_letter = worksheet.cell(row=1, column=col_idx).column_letter

            # Aplicar formato de data brasileiro
            if col_name in colunas_data:
                for row in range(2, len(df) + 2):  # Começar da linha 2 (pula header)
                    cell = worksheet.cell(row=row, column=col_idx)
                    if cell.value and isinstance(cell.value, (datetime, date)):
                        # Formato brasileiro: dd/mm/yyyy ou dd/mm/yyyy hh:mm
                        if isinstance(cell.value, datetime) and cell.value.hour + cell.value.minute + cell.value.second > 0:
                            cell.number_format = 'DD/MM/YYYY HH:MM'
                        else:
                            cell.number_format = 'DD/MM/YYYY'

            # Ajustar largura da coluna
            max_length = 0
            for cell in worksheet[column_letter]:
                try:
                    if cell.value:
                        if isinstance(cell.value, (datetime, date)):
                            max_length = max(max_length, 10)  # Tamanho padrão para datas
                        else:
                            max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    filename = f"clientes_detalhado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@comercial_bp.route('/api/cliente/<path:cnpj>/detalhes')
@login_required
def detalhes_cliente_api(cnpj):
    """
    API para obter detalhes de um cliente específico
    Usa <path:cnpj> para aceitar CNPJs com barra
    """
    filtro_posicao = request.args.get('posicao', 'em_aberto')

    dados = ClienteService.obter_dados_cliente(cnpj, filtro_posicao)

    # Converter Decimal para float para JSON
    dados['valor_em_aberto'] = float(dados['valor_em_aberto'])
    dados['valor_total'] = float(dados['valor_total'])

    return jsonify(dados)



@comercial_bp.route('/api/cliente/<path:cnpj>/pedidos')
@login_required
def pedidos_cliente_api(cnpj):
    """
    API para obter lista detalhada de pedidos de um cliente com paginação
    Usa <path:cnpj> para aceitar CNPJs com barra
    """
    try:
        filtro_posicao = request.args.get('posicao', 'em_aberto')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if per_page > 100:
            per_page = 100

        pedido_param = (request.args.get('pedido') or '').strip().lower()
        num_pedido_param = (request.args.get('num_pedido') or '').strip().lower()
        pedido_cliente_param = (request.args.get('pedido_cliente') or '').strip().lower()
        filtros_pedido_ativos = any([pedido_param, num_pedido_param, pedido_cliente_param])

        pedidos_posicao = ClienteService.obter_pedidos_cliente(cnpj, filtro_posicao)
        pedidos_todos = ClienteService.obter_pedidos_cliente(cnpj, 'todos')

        if filtros_pedido_ativos:
            # Respeitar filtro de posição
            if filtro_posicao == 'em_aberto':
                base_lista = pedidos_posicao
            else:
                base_lista = pedidos_todos

            pedido_cliente_map: dict[str, str] = {}
            if base_lista:
                pedidos_para_busca = [str(p) for p in base_lista if str(p).strip()]
                if pedidos_para_busca:
                    # Buscar pedido_cliente na CarteiraPrincipal
                    rows_carteira = db.session.query(
                        CarteiraPrincipal.num_pedido,
                        func.max(CarteiraPrincipal.pedido_cliente)
                    ).filter(
                        CarteiraPrincipal.cnpj_cpf == cnpj,
                        CarteiraPrincipal.num_pedido.in_(pedidos_para_busca)
                    ).group_by(
                        CarteiraPrincipal.num_pedido
                    ).all()
                    pedido_cliente_map = {row[0]: (row[1] or '') for row in rows_carteira}

                    # Buscar pedido_cliente via FaturamentoProduto (JOIN com CarteiraPrincipal)
                    rows_faturados = db.session.query(
                        FaturamentoProduto.origem.label('num_pedido'),
                        func.max(CarteiraPrincipal.pedido_cliente).label('pedido_cliente')
                    ).join(
                        CarteiraPrincipal,
                        FaturamentoProduto.origem == CarteiraPrincipal.num_pedido
                    ).filter(
                        FaturamentoProduto.cnpj_cliente == cnpj,
                        FaturamentoProduto.origem.in_(pedidos_para_busca),
                        FaturamentoProduto.status_nf != 'Cancelado',
                        CarteiraPrincipal.pedido_cliente.isnot(None)
                    ).group_by(
                        FaturamentoProduto.origem
                    ).all()

                    # Mesclar resultados (prioridade para carteira, depois faturamento)
                    for row in rows_faturados:
                        if row.num_pedido and row.pedido_cliente:
                            if row.num_pedido not in pedido_cliente_map or not pedido_cliente_map[row.num_pedido]:
                                pedido_cliente_map[row.num_pedido] = row.pedido_cliente

            def _match_pedido(numero: str) -> bool:
                alvo = str(numero or '').lower()
                pedido_cli = (pedido_cliente_map.get(str(numero), '') or '').lower()
                # Campo "pedido" busca em num_pedido OU pedido_cliente
                return ((pedido_param and (pedido_param in alvo or pedido_param in pedido_cli)) or
                        (num_pedido_param and num_pedido_param in alvo) or
                        (pedido_cliente_param and pedido_cliente_param in pedido_cli)) # type: ignore

            pedidos_filtrados = [p for p in (pedidos_todos or pedidos_posicao) if _match_pedido(p)]

            total = len(pedidos_filtrados)
            if total == 0:
                return jsonify({
                    'pedidos': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': 0
                })

            total_pages = (total + per_page - 1) // per_page
            if page > total_pages:
                page = total_pages or 1

            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            pedidos_pagina = pedidos_filtrados[start_idx:end_idx]

            pedidos_detalhados = []
            for num_pedido in pedidos_pagina:
                detalhe = PedidoService._processar_pedido(str(num_pedido), cnpj, None, None)
                if detalhe:
                    pedidos_detalhados.append(detalhe)

            for pedido in pedidos_detalhados:
                pedido['valor_total_pedido'] = float(pedido['valor_total_pedido'])
                pedido['valor_total_faturado'] = float(pedido['valor_total_faturado'])
                pedido['valor_entregue'] = float(pedido['valor_entregue'])
                pedido['saldo_carteira'] = float(pedido['saldo_carteira'])
                if pedido['data_pedido']:
                    pedido['data_pedido'] = pedido['data_pedido'].strftime('%d/%m/%Y')

            return jsonify({
                'pedidos': pedidos_detalhados,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages
            })

        resultado = PedidoService.obter_detalhes_pedidos_cliente(
            cnpj=cnpj,
            filtro_posicao=filtro_posicao,
            page=page,
            per_page=per_page
        )

        for pedido in resultado['pedidos']:
            pedido['valor_total_pedido'] = float(pedido['valor_total_pedido'])
            pedido['valor_total_faturado'] = float(pedido['valor_total_faturado'])
            pedido['valor_entregue'] = float(pedido['valor_entregue'])
            pedido['saldo_carteira'] = float(pedido['saldo_carteira'])
            if pedido['data_pedido']:
                pedido['data_pedido'] = pedido['data_pedido'].strftime('%d/%m/%Y')

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro na API de pedidos do cliente {cnpj}: {e}")
        return jsonify({
            'error': 'Erro ao buscar pedidos',
            'pedidos': [],
            'total': 0,
            'page': 1,
            'per_page': 20,
            'total_pages': 0
        }), 500


@comercial_bp.route('/api/pedido/<string:num_pedido>/documentos')
@login_required
def documentos_pedido_api(num_pedido):
    """
    API para obter todos os documentos de um pedido (NFs, Separações e Saldo).

    Args:
        num_pedido: Número do pedido

    Query params:
        cnpj: CNPJ do cliente (obrigatório)
    """
    try:
        cnpj = request.args.get('cnpj')
        if not cnpj:
            return jsonify({'error': 'CNPJ do cliente é obrigatório'}), 400

        # Obter documentos do pedido
        resultado = DocumentoService.obter_documentos_pedido(
            num_pedido=num_pedido,
            cnpj_cliente=cnpj
        )

        # Formatar datas para JSON
        for doc in resultado['documentos']:
            # Converter valores que possam ser Decimal para float
            if 'valor' in doc and doc['valor'] != '-':
                doc['valor'] = float(doc['valor'])

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro na API de documentos do pedido {num_pedido}: {e}")
        return jsonify({
            'error': 'Erro ao buscar documentos',
            'cliente_precisa_agendamento': False,
            'documentos': [],
            'totais': {
                'valor_total_pedido': 0,
                'valor_total_faturado': 0,
                'valor_total_separacoes': 0,
                'saldo': 0
            }
        }), 500


@comercial_bp.route('/api/documento/<string:tipo>/<path:identificador>/produtos')
@login_required
def produtos_documento_api(tipo, identificador):
    """
    API para obter produtos de um documento específico (NF, Separação ou Saldo).

    Args:
        tipo: Tipo do documento ('NF', 'Separacao', 'Saldo')
        identificador: ID único do documento

    Query params:
        num_pedido: Número do pedido (opcional, usado principalmente para Saldo)
    """
    try:
        num_pedido = request.args.get('num_pedido')

        # Obter produtos do documento
        resultado = ProdutoDocumentoService.obter_produtos_documento(
            tipo_documento=tipo,
            identificador=identificador,
            num_pedido=num_pedido
        )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro na API de produtos do documento {tipo} {identificador}: {e}")
        return jsonify({
            'error': 'Erro ao buscar produtos',
            'produtos': [],
            'totais': {
                'quantidade': 0,
                'valor': 0,
                'peso': 0,
                'pallet': 0
            }
        }), 500


# ============================================================================
# ROTAS DE ADMINISTRAÇÃO DE PERMISSÕES
# ============================================================================

@comercial_bp.route('/admin/permissoes')
@login_required
@admin_comercial_required
def admin_permissoes():
    """
    Página principal de administração de permissões.
    Lista todos os usuários vendedores.
    """
    from app.auth.models import Usuario

    # Buscar todos os usuários vendedores
    vendedores = db.session.query(Usuario).filter_by(
        perfil='vendedor',
        status='ativo'
    ).order_by(Usuario.nome).all()

    # Para cada vendedor, contar permissões
    vendedores_data = []
    for vendedor in vendedores:
        permissoes = PermissaoService.obter_permissoes_usuario(vendedor.id)
        vendedores_data.append({
            'id': vendedor.id,
            'nome': vendedor.nome,
            'email': vendedor.email,
            'total_equipes': len(permissoes['equipes']),
            'total_vendedores': len(permissoes['vendedores']),
            'total_permissoes': len(permissoes['equipes']) + len(permissoes['vendedores'])
        })

    return render_template('comercial/admin/lista_vendedores.html',
                         vendedores=vendedores_data)


@comercial_bp.route('/admin/permissoes/<int:usuario_id>')
@login_required
@admin_comercial_required
def admin_editar_permissoes(usuario_id):
    """
    Página de edição de permissões de um usuário específico.
    Interface com dois painéis separados por tipo.
    """
    from app.auth.models import Usuario

    # Buscar usuário
    usuario = db.session.query(Usuario).get_or_404(usuario_id)

    # Verificar se é vendedor
    if usuario.perfil != 'vendedor':
        flash('Apenas vendedores podem ter permissões configuradas.', 'warning')
        return redirect(url_for('comercial.admin_permissoes'))

    # Obter todas as equipes e vendedores disponíveis
    todas_equipes = PermissaoService.obter_equipes_disponiveis()
    todos_vendedores = PermissaoService.obter_vendedores_disponiveis()

    # Obter permissões atuais do usuário
    permissoes_atuais = PermissaoService.obter_permissoes_usuario(usuario_id)

    # Separar em disponíveis e permitidos
    equipes_disponiveis = [e for e in todas_equipes if e not in permissoes_atuais['equipes']]
    equipes_permitidas = permissoes_atuais['equipes']

    vendedores_disponiveis = [v for v in todos_vendedores if v not in permissoes_atuais['vendedores']]
    vendedores_permitidos = permissoes_atuais['vendedores']

    # Obter logs recentes
    logs = PermissaoService.obter_logs_usuario(usuario_id, limite=20)

    return render_template('comercial/admin/editar_permissoes.html',
                         usuario=usuario,
                         equipes_disponiveis=equipes_disponiveis,
                         equipes_permitidas=equipes_permitidas,
                         vendedores_disponiveis=vendedores_disponiveis,
                         vendedores_permitidos=vendedores_permitidos,
                         logs=logs)


@comercial_bp.route('/admin/permissoes/<int:usuario_id>/adicionar', methods=['POST'])
@login_required
@admin_comercial_required
def admin_adicionar_permissao(usuario_id):
    """
    API para adicionar permissão a um usuário.
    """
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        valor = data.get('valor')

        if not tipo or not valor:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        # Adicionar permissão
        sucesso = PermissaoService.adicionar_permissao(
            usuario_id=usuario_id,
            tipo=tipo,
            valor=valor,
            admin_email=current_user.email
        )

        if sucesso:
            return jsonify({'success': True, 'message': 'Permissão adicionada com sucesso'})
        else:
            return jsonify({'success': False, 'message': 'Permissão já existe'}), 400

    except Exception as e:
        logger.error(f"Erro ao adicionar permissão: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@comercial_bp.route('/admin/permissoes/<int:usuario_id>/remover', methods=['POST'])
@login_required
@admin_comercial_required
def admin_remover_permissao(usuario_id):
    """
    API para remover permissão de um usuário.
    """
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        valor = data.get('valor')

        if not tipo or not valor:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        # Remover permissão
        sucesso = PermissaoService.remover_permissao(
            usuario_id=usuario_id,
            tipo=tipo,
            valor=valor
        )

        if sucesso:
            return jsonify({'success': True, 'message': 'Permissão removida com sucesso'})
        else:
            return jsonify({'success': False, 'message': 'Permissão não encontrada'}), 400

    except Exception as e:
        logger.error(f"Erro ao remover permissão: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@comercial_bp.route('/admin/permissoes/<int:usuario_id>/limpar', methods=['POST'])
@login_required
@admin_comercial_required
def admin_limpar_permissoes(usuario_id):
    """
    API para limpar todas as permissões de um usuário.
    """
    try:
        # Limpar todas as permissões
        quantidade = PermissaoService.limpar_permissoes_usuario(usuario_id)

        return jsonify({
            'success': True,
            'message': f'{quantidade} permissões removidas com sucesso'
        })

    except Exception as e:
        logger.error(f"Erro ao limpar permissões: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
