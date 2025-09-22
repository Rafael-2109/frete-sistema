"""
Rotas para visão da diretoria - acesso completo
"""
from flask import render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.comercial import comercial_bp
from app.comercial.services.cliente_service import ClienteService
from app.comercial.services.pedido_service import PedidoService
from app.comercial.services.documento_service import DocumentoService
from app.comercial.services.produto_documento_service import ProdutoDocumentoService
from app.comercial.services.permissao_service import PermissaoService
from app.comercial.decorators import comercial_required, admin_comercial_required
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import distinct
from app import db
import logging

logger = logging.getLogger(__name__)


@comercial_bp.route('/')
@comercial_bp.route('/dashboard')
@login_required
@comercial_required
def dashboard_diretoria():
    """
    Dashboard principal da diretoria com badges de equipes
    """
    # Se for vendedor e não tiver permissões, mostrar mensagem
    if current_user.perfil == 'vendedor':
        if not PermissaoService.usuario_tem_permissoes(current_user.id):
            flash('Você ainda não possui permissões configuradas. Solicite ao administrador.', 'warning')
            return render_template('comercial/dashboard_diretoria.html', equipes=[])

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

    # Se for vendedor, filtrar equipes permitidas
    if current_user.perfil == 'vendedor':
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Filtrar equipes baseado nas permissões
        equipes_permitidas = []
        for equipe in equipes:
            # Verificar se tem permissão direta para a equipe
            if equipe in permissoes['equipes']:
                equipes_permitidas.append(equipe)
            else:
                # Verificar se tem permissão para algum vendedor da equipe
                vendedores_equipe = db.session.query(
                    distinct(CarteiraPrincipal.vendedor)
                ).filter(
                    CarteiraPrincipal.equipe_vendas == equipe,
                    CarteiraPrincipal.vendedor.isnot(None)
                ).all()

                for v in vendedores_equipe:
                    if v[0] in permissoes['vendedores']:
                        equipes_permitidas.append(equipe)
                        break

        equipes = equipes_permitidas

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
@comercial_required
def vendedores_equipe(equipe_nome):
    """
    Visualização de vendedores de uma equipe específica
    """
    # Se for vendedor, verificar se tem acesso à equipe
    if current_user.perfil == 'vendedor':
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

        # Verificar se tem acesso direto à equipe
        tem_acesso = equipe_nome in permissoes['equipes']

        # Se não tem acesso direto, verificar se tem acesso a algum vendedor da equipe
        if not tem_acesso:
            # Buscar vendedores da equipe
            vendedores_equipe = db.session.query(
                distinct(CarteiraPrincipal.vendedor)
            ).filter(
                CarteiraPrincipal.equipe_vendas == equipe_nome,
                CarteiraPrincipal.vendedor.isnot(None)
            ).all()

            for v in vendedores_equipe:
                if v[0] in permissoes['vendedores']:
                    tem_acesso = True
                    break

        if not tem_acesso:
            flash('Você não tem permissão para acessar esta equipe.', 'danger')
            return redirect(url_for('comercial.dashboard_diretoria'))

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

    # Se for vendedor, filtrar apenas vendedores permitidos
    if current_user.perfil == 'vendedor':
        # Se tem acesso à equipe inteira, mostrar todos
        if equipe_nome not in permissoes['equipes']:
            # Filtrar apenas vendedores permitidos
            vendedores = [v for v in vendedores if v in permissoes['vendedores']]

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
        permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

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

    # Se há filtros avançados, usar query otimizada
    if any([cnpj_cpf_filtro, cliente_filtro, pedido_filtro, uf_filtro,
            raz_social_filtro, raz_social_red_filtro, num_pedido_filtro, pedido_cliente_filtro]):
        # Usar query SQL otimizada com busca sem acento
        from sqlalchemy import text

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
                    -- Filtro de posição
                    (:posicao = 'todos' OR qtd_saldo_produto_pedido > 0)

                    -- Filtros de permissão (para vendedores)
                    AND (:is_vendedor = false OR
                         ((:equipe_filtro IS NOT NULL AND equipe_vendas = :equipe_filtro) OR
                          (:vendedor_filtro IS NOT NULL AND vendedor = :vendedor_filtro) OR
                          (:equipe_filtro IS NULL AND :vendedor_filtro IS NULL AND
                           (equipe_vendas = ANY(:equipes_permitidas) OR
                            vendedor = ANY(:vendedores_permitidos)))))

                    -- Filtros de equipe/vendedor específicos
                    AND (:equipe_filtro IS NULL OR equipe_vendas = :equipe_filtro)
                    AND (:vendedor_filtro IS NULL OR vendedor = :vendedor_filtro)

                    -- Filtro unificado de pedido (busca em num_pedido OU pedido_cliente)
                    AND (:pedido = '' OR
                         lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')) OR
                         lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')))

                    -- Filtros individuais de pedido (para compatibilidade)
                    AND (:num_pedido = '' OR
                         lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :num_pedido || '%')))

                    AND (:pedido_cliente = '' OR
                         lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido_cliente || '%')))
            ),
            clientes_agrupados AS (
                SELECT
                    cnpj_cpf,
                    MAX(raz_social) as raz_social,
                    MAX(raz_social_red) as raz_social_red,
                    MAX(estado) as estado,
                    MAX(municipio) as municipio,
                    MAX(vendedor) as vendedor,
                    MAX(equipe_vendas) as equipe_vendas,
                    COUNT(DISTINCT num_pedido) as total_pedidos,
                    SUM(valor_item) as valor_em_aberto
                FROM pedidos_filtrados
                WHERE
                    -- Filtros de cliente
                    (:cnpj_cpf = '' OR cnpj_cpf LIKE '%' || :cnpj_cpf || '%')

                    -- Filtro unificado de cliente (busca em razão social OU nome fantasia)
                    AND (:cliente = '' OR
                         lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')) OR
                         lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')))

                    -- Filtros individuais de cliente (para compatibilidade)
                    AND (:raz_social = '' OR
                         lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :raz_social || '%')))

                    AND (:raz_social_red = '' OR
                         lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :raz_social_red || '%')))

                    AND (:uf = '' OR estado = :uf)
                GROUP BY cnpj_cpf
                HAVING SUM(valor_item) > 0 OR :posicao = 'todos'
            )
            SELECT * FROM clientes_agrupados
            ORDER BY valor_em_aberto DESC NULLS LAST
        """)

        # Preparar parâmetros
        is_vendedor = current_user.perfil == 'vendedor'
        equipes_permitidas = []
        vendedores_permitidos = []

        if is_vendedor:
            permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)
            equipes_permitidas = permissoes.get('equipes', [])
            vendedores_permitidos = permissoes.get('vendedores', [])

        params = {
            'posicao': filtro_posicao,
            'is_vendedor': is_vendedor,
            'equipe_filtro': equipe_filtro,
            'vendedor_filtro': vendedor_filtro,
            'equipes_permitidas': equipes_permitidas or [''],
            'vendedores_permitidos': vendedores_permitidos or [''],
            'cnpj_cpf': cnpj_cpf_filtro,
            'cliente': cliente_filtro,  # Campo unificado cliente
            'pedido': pedido_filtro,    # Campo unificado pedido
            'raz_social': raz_social_filtro,
            'raz_social_red': raz_social_red_filtro,
            'uf': uf_filtro,
            'num_pedido': num_pedido_filtro,
            'pedido_cliente': pedido_cliente_filtro
        }

        # Executar query
        result = db.session.execute(sql, params).fetchall()

        clientes_data = []
        for row in result:
            clientes_data.append({
                'cnpj_cpf': row.cnpj_cpf,
                'raz_social': row.raz_social,
                'raz_social_red': row.raz_social_red,
                'estado': row.estado,
                'municipio': row.municipio,
                'vendedor': row.vendedor,
                'equipe_vendas': row.equipe_vendas,
                'forma_agendamento': 'Portal',  # Default
                'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0,
                'total_pedidos': int(row.total_pedidos) if row.total_pedidos else 0
            })

    else:
        # Usar lógica original se não há filtros avançados
        if vendedor_filtro:
            clientes_cnpj = ClienteService.obter_clientes_por_vendedor(vendedor_filtro)
        elif equipe_filtro:
            clientes_cnpj = ClienteService.obter_clientes_por_equipe(equipe_filtro)
        else:
            # Se não tem filtro específico e é vendedor, aplicar todos os filtros de permissão
            if current_user.perfil == 'vendedor':
                permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)

                # Buscar clientes de todas as equipes e vendedores permitidos
                clientes_cnpj_set = set()

                # Adicionar clientes das equipes permitidas
                for equipe in permissoes['equipes']:
                    clientes_equipe = ClienteService.obter_clientes_por_equipe(equipe)
                    clientes_cnpj_set.update(clientes_equipe)

                # Adicionar clientes dos vendedores permitidos
                for vendedor in permissoes['vendedores']:
                    clientes_vendedor = ClienteService.obter_clientes_por_vendedor(vendedor)
                    clientes_cnpj_set.update(clientes_vendedor)

                clientes_cnpj = list(clientes_cnpj_set)
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

    # Buscar UFs disponíveis para o dropdown
    ufs_disponiveis = []
    if clientes_data:
        # Extrair UFs únicas dos clientes já filtrados
        ufs_set = {c['estado'] for c in clientes_data if c['estado']}
        ufs_disponiveis = sorted(list(ufs_set))
    else:
        # Se não há clientes, buscar UFs disponíveis no banco
        ufs = db.session.query(distinct(CarteiraPrincipal.estado)).filter(
            CarteiraPrincipal.estado.isnot(None),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0 if filtro_posicao == 'em_aberto' else True
        ).all()
        ufs_disponiveis = sorted([uf[0] for uf in ufs if uf[0]])

    # Calcular totais
    total_clientes = len(clientes_data)
    valor_total = sum(c['valor_em_aberto'] for c in clientes_data)

    return render_template('comercial/lista_clientes.html',
                         clientes=clientes_data,
                         filtro_posicao=filtro_posicao,
                         equipe_filtro=equipe_filtro,
                         vendedor_filtro=vendedor_filtro,
                         ufs_disponiveis=ufs_disponiveis,
                         total_clientes=total_clientes,
                         valor_total=valor_total)


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

        # Limitar per_page para evitar sobrecarga
        if per_page > 100:
            per_page = 100

        # Obter dados paginados dos pedidos
        resultado = PedidoService.obter_detalhes_pedidos_cliente(
            cnpj=cnpj,
            filtro_posicao=filtro_posicao,
            page=page,
            per_page=per_page
        )

        # Converter Decimals para float para JSON
        for pedido in resultado['pedidos']:
            pedido['valor_total_pedido'] = float(pedido['valor_total_pedido'])
            pedido['valor_total_faturado'] = float(pedido['valor_total_faturado'])
            pedido['valor_entregue'] = float(pedido['valor_entregue'])
            pedido['saldo_carteira'] = float(pedido['saldo_carteira'])

            # Formatar data para string
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