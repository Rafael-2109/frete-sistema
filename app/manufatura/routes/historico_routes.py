"""
Rotas de Gestao do Historico de Pedidos
========================================

Funcionalidades:
- Visualizacao do historico combinado (Odoo + Carteira Ativa)
- Exportacao para Excel
- Sincronizacao com Odoo por periodo
"""
from flask import render_template, jsonify, request, send_file
from flask_login import login_required
from app import db
from app.carteira.models import CarteiraPrincipal
from app.manufatura.models import HistoricoPedidos, GrupoEmpresarial
from app.manufatura.services.demanda_service import extrair_prefixo_cnpj
from sqlalchemy import select, union_all, literal, and_, func
import pandas as pd
from io import BytesIO
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _limpar_cnpj_input(cnpj_str):
    """Remove formatacao do CNPJ digitado pelo usuario."""
    return re.sub(r'[^\d]', '', cnpj_str)


def _cnpj_limpo_col(column):
    """Expressao SQL que remove pontos, tracos e barras de uma coluna CNPJ."""
    return func.replace(func.replace(func.replace(column, '.', ''), '-', ''), '/', '')


def _read_filters():
    """Le todos os filtros de request.args, retornando None para vazios."""
    return {
        'data_inicio': request.args.get('data_inicio') or None,
        'data_fim': request.args.get('data_fim') or None,
        'grupo': request.args.get('grupo') or None,
        'cod_produto': request.args.get('cod_produto') or None,
        'num_pedido': request.args.get('num_pedido') or None,
        'cliente': request.args.get('cliente') or None,
        'cnpj': request.args.get('cnpj') or None,
        'nome_produto': request.args.get('nome_produto') or None,
    }


def _build_combined_query(filters):
    """
    Constroi UNION ALL de historico_pedidos + carteira_principal.

    Retorna subquery com colunas:
        num_pedido, data_pedido, cnpj_cliente, raz_social_red, nome_grupo,
        nome_cidade, cod_uf, cod_produto, nome_produto, qtd_produto_pedido,
        valor_produto_pedido
    """
    data_inicio = filters.get('data_inicio')
    data_fim = filters.get('data_fim')
    grupo = filters.get('grupo')
    cod_produto = filters.get('cod_produto')
    num_pedido = filters.get('num_pedido')
    cliente = filters.get('cliente')
    cnpj = filters.get('cnpj')
    nome_produto = filters.get('nome_produto')

    cnpj_limpo = _limpar_cnpj_input(cnpj) if cnpj else None

    # ------------------------------------------------------------------
    # Query 1: HistoricoPedidos (exclui registros duplicados na carteira)
    # ------------------------------------------------------------------
    exists_in_carteira = (
        select(CarteiraPrincipal.id)
        .where(and_(
            CarteiraPrincipal.num_pedido == HistoricoPedidos.num_pedido,
            CarteiraPrincipal.cod_produto == HistoricoPedidos.cod_produto,
            CarteiraPrincipal.ativo == True,
        ))
        .correlate(HistoricoPedidos)
        .exists()
    )

    q_hist = (
        select(
            HistoricoPedidos.num_pedido.label('num_pedido'),
            HistoricoPedidos.data_pedido.label('data_pedido'),
            HistoricoPedidos.cnpj_cliente.label('cnpj_cliente'),
            HistoricoPedidos.raz_social_red.label('raz_social_red'),
            HistoricoPedidos.nome_grupo.label('nome_grupo'),
            HistoricoPedidos.nome_cidade.label('nome_cidade'),
            HistoricoPedidos.cod_uf.label('cod_uf'),
            HistoricoPedidos.cod_produto.label('cod_produto'),
            HistoricoPedidos.nome_produto.label('nome_produto'),
            HistoricoPedidos.qtd_produto_pedido.label('qtd_produto_pedido'),
            HistoricoPedidos.valor_produto_pedido.label('valor_produto_pedido'),
        )
        .where(~exists_in_carteira)
    )

    if data_inicio:
        q_hist = q_hist.where(HistoricoPedidos.data_pedido >= data_inicio)
    if data_fim:
        q_hist = q_hist.where(HistoricoPedidos.data_pedido <= data_fim)
    if grupo:
        q_hist = q_hist.where(HistoricoPedidos.nome_grupo == grupo)
    if cod_produto:
        q_hist = q_hist.where(HistoricoPedidos.cod_produto.ilike(f'%{cod_produto}%'))
    if num_pedido:
        q_hist = q_hist.where(HistoricoPedidos.num_pedido.ilike(f'%{num_pedido}%'))
    if cliente:
        q_hist = q_hist.where(HistoricoPedidos.raz_social_red.ilike(f'%{cliente}%'))
    if cnpj_limpo:
        q_hist = q_hist.where(
            _cnpj_limpo_col(HistoricoPedidos.cnpj_cliente).ilike(f'%{cnpj_limpo}%')
        )
    if nome_produto:
        q_hist = q_hist.where(HistoricoPedidos.nome_produto.ilike(f'%{nome_produto}%'))

    # ------------------------------------------------------------------
    # Query 2: CarteiraPrincipal (pedidos ativos)
    # ------------------------------------------------------------------
    valor_calculado = func.coalesce(
        CarteiraPrincipal.qtd_produto_pedido * CarteiraPrincipal.preco_produto_pedido,
        literal(0),
    ).label('valor_produto_pedido')

    q_cart = (
        select(
            CarteiraPrincipal.num_pedido.label('num_pedido'),
            CarteiraPrincipal.data_pedido.label('data_pedido'),
            CarteiraPrincipal.cnpj_cpf.label('cnpj_cliente'),
            CarteiraPrincipal.raz_social_red.label('raz_social_red'),
            func.coalesce(GrupoEmpresarial.nome_grupo, literal('GERAL')).label('nome_grupo'),
            CarteiraPrincipal.nome_cidade.label('nome_cidade'),
            CarteiraPrincipal.cod_uf.label('cod_uf'),
            CarteiraPrincipal.cod_produto.label('cod_produto'),
            CarteiraPrincipal.nome_produto.label('nome_produto'),
            CarteiraPrincipal.qtd_produto_pedido.label('qtd_produto_pedido'),
            valor_calculado,
        )
        .outerjoin(
            GrupoEmpresarial,
            and_(
                extrair_prefixo_cnpj(CarteiraPrincipal.cnpj_cpf) == GrupoEmpresarial.prefixo_cnpj,
                GrupoEmpresarial.ativo == True,
            ),
        )
        .where(CarteiraPrincipal.ativo == True)
    )

    if data_inicio:
        q_cart = q_cart.where(CarteiraPrincipal.data_pedido >= data_inicio)
    if data_fim:
        q_cart = q_cart.where(CarteiraPrincipal.data_pedido <= data_fim)
    if grupo:
        if grupo == 'GERAL':
            q_cart = q_cart.where(GrupoEmpresarial.nome_grupo.is_(None))
        else:
            q_cart = q_cart.where(GrupoEmpresarial.nome_grupo == grupo)
    if cod_produto:
        q_cart = q_cart.where(CarteiraPrincipal.cod_produto.ilike(f'%{cod_produto}%'))
    if num_pedido:
        q_cart = q_cart.where(CarteiraPrincipal.num_pedido.ilike(f'%{num_pedido}%'))
    if cliente:
        q_cart = q_cart.where(CarteiraPrincipal.raz_social_red.ilike(f'%{cliente}%'))
    if cnpj_limpo:
        q_cart = q_cart.where(
            _cnpj_limpo_col(CarteiraPrincipal.cnpj_cpf).ilike(f'%{cnpj_limpo}%')
        )
    if nome_produto:
        q_cart = q_cart.where(CarteiraPrincipal.nome_produto.ilike(f'%{nome_produto}%'))

    # ------------------------------------------------------------------
    # UNION ALL
    # ------------------------------------------------------------------
    combined = union_all(q_hist, q_cart).subquery('combined')
    return combined


# ---------------------------------------------------------------------------
# Registro de rotas
# ---------------------------------------------------------------------------

def register_historico_routes(bp):

    @bp.route('/historico-pedidos')  # type: ignore
    @login_required
    def historico_pedidos():  # type: ignore
        """Tela de gestao do historico de pedidos"""
        return render_template('manufatura/historico_pedidos.html')

    @bp.route('/api/historico-pedidos/listar')  # type: ignore
    @login_required
    def listar_historico():  # type: ignore
        """Lista historico combinado (Odoo + Carteira) com filtros e paginacao"""
        try:
            filters = _read_filters()
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))

            combined = _build_combined_query(filters)

            # Total de registros
            total = db.session.execute(
                select(func.count()).select_from(combined)
            ).scalar()

            # Dados paginados
            rows = db.session.execute(
                select(combined)
                .order_by(combined.c.data_pedido.desc(), combined.c.num_pedido)
                .limit(per_page)
                .offset((page - 1) * per_page)
            ).mappings().all()

            registros = []
            for r in rows:
                registros.append({
                    'num_pedido': r['num_pedido'],
                    'data_pedido': r['data_pedido'].strftime('%d/%m/%Y') if r['data_pedido'] else None,
                    'cnpj_cliente': r['cnpj_cliente'],
                    'raz_social_red': r['raz_social_red'],
                    'nome_grupo': r['nome_grupo'],
                    'cod_produto': r['cod_produto'],
                    'nome_produto': r['nome_produto'],
                    'qtd_produto_pedido': float(r['qtd_produto_pedido'] or 0),
                    'valor_produto_pedido': float(r['valor_produto_pedido'] or 0),
                    'nome_cidade': r['nome_cidade'],
                    'cod_uf': r['cod_uf'],
                })

            total_pages = max(1, (total + per_page - 1) // per_page)

            return jsonify({
                'sucesso': True,
                'registros': registros,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
            })

        except Exception as e:
            logger.error(f"Erro ao listar historico: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/estatisticas')  # type: ignore
    @login_required
    def estatisticas_historico():  # type: ignore
        """Retorna estatisticas do historico combinado"""
        try:
            filters = _read_filters()
            combined = _build_combined_query(filters)

            row = db.session.execute(
                select(
                    func.count().label('total_registros'),
                    func.count(func.distinct(combined.c.num_pedido)).label('total_pedidos'),
                    func.count(func.distinct(combined.c.cod_produto)).label('total_produtos'),
                    func.coalesce(func.sum(combined.c.valor_produto_pedido), 0).label('valor_total'),
                    func.min(combined.c.data_pedido).label('data_mais_antiga'),
                    func.max(combined.c.data_pedido).label('data_mais_recente'),
                ).select_from(combined)
            ).mappings().first()

            return jsonify({
                'total_registros': row['total_registros'],
                'total_pedidos': row['total_pedidos'],
                'total_produtos': row['total_produtos'],
                'valor_total': float(row['valor_total']),
                'data_mais_antiga': (
                    row['data_mais_antiga'].strftime('%d/%m/%Y')
                    if row['data_mais_antiga'] else None
                ),
                'data_mais_recente': (
                    row['data_mais_recente'].strftime('%d/%m/%Y')
                    if row['data_mais_recente'] else None
                ),
            })

        except Exception as e:
            logger.error(f"Erro ao buscar estatisticas: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/exportar-excel')  # type: ignore
    @login_required
    def exportar_historico_excel():  # type: ignore
        """Exporta historico combinado para Excel"""
        try:
            filters = _read_filters()

            logger.info(
                f"[EXPORTAR] Periodo: {filters.get('data_inicio')} ate "
                f"{filters.get('data_fim')}, Grupo: {filters.get('grupo')}"
            )

            combined = _build_combined_query(filters)

            rows = db.session.execute(
                select(combined)
                .order_by(combined.c.data_pedido.desc(), combined.c.num_pedido)
            ).mappings().all()

            if not rows:
                return jsonify({'erro': 'Nenhum registro encontrado para exportar'}), 404

            logger.info(f"[EXPORTAR] Total de registros: {len(rows)}")

            dados = []
            for r in rows:
                dados.append({
                    'Numero Pedido': r['num_pedido'],
                    'Data Pedido': r['data_pedido'].strftime('%d/%m/%Y') if r['data_pedido'] else '',
                    'CNPJ Cliente': r['cnpj_cliente'],
                    'Razao Social': r['raz_social_red'],
                    'Grupo': r['nome_grupo'],
                    'Cidade': r['nome_cidade'],
                    'UF': r['cod_uf'],
                    'Codigo Produto': r['cod_produto'],
                    'Nome Produto': r['nome_produto'],
                    'Quantidade': float(r['qtd_produto_pedido'] or 0),
                    'Valor Total': float(r['valor_produto_pedido'] or 0),
                })

            df = pd.DataFrame(dados)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Historico Pedidos')

                worksheet = writer.sheets['Historico Pedidos']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col),
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

            output.seek(0)

            grupo_nome = filters.get('grupo') or 'TODOS'
            periodo = f"{filters.get('data_inicio') or 'inicio'}_{filters.get('data_fim') or 'fim'}"
            nome_arquivo = f'historico_pedidos_{periodo}_{grupo_nome}.xlsx'

            logger.info(f"[EXPORTAR] Arquivo gerado: {nome_arquivo}")

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo,
            )

        except Exception as e:
            logger.error(f"[EXPORTAR] Erro: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/historico-pedidos/sincronizar-odoo', methods=['POST'])  # type: ignore
    @login_required
    def sincronizar_odoo():  # type: ignore
        """Sincroniza historico com Odoo (UPSERT)"""
        try:
            dados = request.json
            data_inicio = dados.get('data_inicio')
            data_fim = dados.get('data_fim')

            if not data_fim:
                return jsonify({'erro': 'Data fim e obrigatoria'}), 400

            logger.info(f"[SYNC] Iniciando sincronizacao: {data_inicio} ate {data_fim}")

            from importar_historico_odoo import importar_historico_odoo

            sucesso = importar_historico_odoo(
                data_inicio=data_inicio,
                data_fim=data_fim,
                lote=50,
            )

            if sucesso:
                query = HistoricoPedidos.query.filter(
                    HistoricoPedidos.data_pedido <= data_fim
                )
                if data_inicio:
                    query = query.filter(HistoricoPedidos.data_pedido >= data_inicio)

                total_registros = query.count()

                return jsonify({
                    'sucesso': True,
                    'mensagem': 'Sincronizacao concluida com sucesso!',
                    'total_registros': total_registros,
                })
            else:
                return jsonify({'erro': 'Falha na sincronizacao'}), 500

        except Exception as e:
            logger.error(f"[SYNC] Erro: {e}", exc_info=True)
            return jsonify({'erro': str(e)}), 500
