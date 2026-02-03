"""
Rotas para Análise de Produção
Permite visualizar produções realizadas e ajustar consumos de componentes
Inclui agrupamento por Ordem de Produção (OP) + Produto
"""
from flask import render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from types import SimpleNamespace
import logging

from app import db
from app.estoque.models import MovimentacaoEstoque
from app.manufatura.services.bom_service import ServicoBOM
from app.manufatura.services.analise_producao_export_service import AnaliseProducaoExportService
from app.producao.models import CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from sqlalchemy import func, literal_column

logger = logging.getLogger(__name__)


def register_analise_producao_routes(bp):
    """Registra rotas de Análise de Produção"""

    @bp.route('/analise-producao')  # type: ignore
    @login_required
    def analise_producao():
        """
        Tela principal de Análise de Produção com agrupamento por OP+Produto.
        - Produções COM ordem_producao: agrupadas por (ordem_producao, cod_produto)
        - Produções SEM ordem_producao: aparecem individualmente
        """
        # Parâmetros de filtro
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        cod_produto = request.args.get('cod_produto', '')
        nome_produto_filtro = request.args.get('nome_produto', '')
        ordem_producao_filtro = request.args.get('ordem_producao', '')
        local_filtro = request.args.get('local_movimentacao', '')
        page = request.args.get('page', 1, type=int)
        per_page = 50

        # ===== PARTE 1: Produções COM ordem_producao (agrupadas) =====
        query_agrupada = db.session.query(
            MovimentacaoEstoque.ordem_producao,
            MovimentacaoEstoque.cod_produto,
            func.max(MovimentacaoEstoque.nome_produto).label('nome_produto'),
            func.sum(MovimentacaoEstoque.qtd_movimentacao).label('qtd_total'),
            func.count(MovimentacaoEstoque.id).label('qtd_producoes'),
            func.max(MovimentacaoEstoque.data_movimentacao).label('ultima_data'),
            func.max(MovimentacaoEstoque.local_movimentacao).label('local_movimentacao'),
            func.string_agg(
                MovimentacaoEstoque.id.cast(db.String),
                literal_column("','")
            ).label('ids_producoes')
        ).filter(
            MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
            MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
            MovimentacaoEstoque.ativo == True,
            MovimentacaoEstoque.ordem_producao != None,  # noqa: E711
            MovimentacaoEstoque.ordem_producao != ''
        )

        # ===== PARTE 2: Produções SEM ordem_producao (individuais) =====
        query_individual = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
            MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
            MovimentacaoEstoque.ativo == True,
            db.or_(
                MovimentacaoEstoque.ordem_producao == None,  # noqa: E711
                MovimentacaoEstoque.ordem_producao == ''
            )
        )

        # ===== Aplicar filtros a AMBAS as queries =====
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query_agrupada = query_agrupada.filter(MovimentacaoEstoque.data_movimentacao >= dt_inicio)
                query_individual = query_individual.filter(MovimentacaoEstoque.data_movimentacao >= dt_inicio)
            except ValueError:
                pass

        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query_agrupada = query_agrupada.filter(MovimentacaoEstoque.data_movimentacao <= dt_fim)
                query_individual = query_individual.filter(MovimentacaoEstoque.data_movimentacao <= dt_fim)
            except ValueError:
                pass

        if cod_produto:
            query_agrupada = query_agrupada.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
            query_individual = query_individual.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))

        if nome_produto_filtro:
            query_agrupada = query_agrupada.filter(MovimentacaoEstoque.nome_produto.ilike(f'%{nome_produto_filtro}%'))
            query_individual = query_individual.filter(MovimentacaoEstoque.nome_produto.ilike(f'%{nome_produto_filtro}%'))

        if ordem_producao_filtro:
            query_agrupada = query_agrupada.filter(MovimentacaoEstoque.ordem_producao.ilike(f'%{ordem_producao_filtro}%'))
            # Individuais não têm OP, então se filtrar por OP, individuais = vazio
            query_individual = query_individual.filter(db.literal(False))

        if local_filtro:
            query_agrupada = query_agrupada.filter(MovimentacaoEstoque.local_movimentacao.ilike(f'%{local_filtro}%'))
            query_individual = query_individual.filter(MovimentacaoEstoque.local_movimentacao.ilike(f'%{local_filtro}%'))

        # ===== Executar queries =====
        query_agrupada = query_agrupada.group_by(
            MovimentacaoEstoque.ordem_producao,
            MovimentacaoEstoque.cod_produto
        ).order_by(func.max(MovimentacaoEstoque.data_movimentacao).desc())

        resultados_agrupados = query_agrupada.all()

        query_individual = query_individual.order_by(
            MovimentacaoEstoque.data_movimentacao.desc(),
            MovimentacaoEstoque.id.desc()
        )
        resultados_individuais = query_individual.all()

        # ===== Montar lista unificada =====
        itens = []

        # Agrupados
        for row in resultados_agrupados:
            itens.append({
                'tipo_item': 'grupo',
                'ordem_producao': row.ordem_producao,
                'cod_produto': row.cod_produto,
                'nome_produto': row.nome_produto,
                'qtd_total': float(row.qtd_total or 0),
                'qtd_producoes': row.qtd_producoes,
                'ultima_data': row.ultima_data,
                'local_movimentacao': row.local_movimentacao,
                'ids_producoes': row.ids_producoes,
            })

        # Individuais (sem OP)
        for prod in resultados_individuais:
            itens.append({
                'tipo_item': 'individual',
                'id': prod.id,
                'ordem_producao': '',
                'cod_produto': prod.cod_produto,
                'nome_produto': prod.nome_produto,
                'qtd_total': float(prod.qtd_movimentacao or 0),
                'qtd_producoes': 1,
                'ultima_data': prod.data_movimentacao,
                'local_movimentacao': prod.local_movimentacao,
                'operacao_producao_id': prod.operacao_producao_id,
                'tipo_origem_producao': prod.tipo_origem_producao,
            })

        # Ordenar tudo por data desc
        itens.sort(key=lambda x: x.get('ultima_data') or datetime.min, reverse=True)

        # Paginação manual
        total = len(itens)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)
        start = (page - 1) * per_page
        end = start + per_page
        itens_pagina = itens[start:end]

        # Objeto de paginação (SimpleNamespace para acesso por atributo no Jinja2)
        paginacao = SimpleNamespace(
            items=itens_pagina,
            total=total,
            page=page,
            pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
            prev_num=page - 1,
            next_num=page + 1,
        )

        return render_template(
            'manufatura/analise_producao/index.html',
            producoes=paginacao,
            filtros={
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'cod_produto': cod_produto,
                'nome_produto': nome_produto_filtro,
                'ordem_producao': ordem_producao_filtro,
                'local_movimentacao': local_filtro,
            }
        )

    # ===== HELPER: Aplicar filtros comuns =====
    def _aplicar_filtros_producao(query, data_inicio, data_fim, cod_produto, nome_produto, ordem_producao, local_mov):
        """Aplica filtros comuns a queries de produção"""
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(MovimentacaoEstoque.data_movimentacao >= dt_inicio)
            except ValueError:
                pass
        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(MovimentacaoEstoque.data_movimentacao <= dt_fim)
            except ValueError:
                pass
        if cod_produto:
            query = query.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
        if nome_produto:
            query = query.filter(MovimentacaoEstoque.nome_produto.ilike(f'%{nome_produto}%'))
        if ordem_producao:
            query = query.filter(MovimentacaoEstoque.ordem_producao.ilike(f'%{ordem_producao}%'))
        if local_mov:
            query = query.filter(MovimentacaoEstoque.local_movimentacao.ilike(f'%{local_mov}%'))
        return query

    @bp.route('/analise-producao/exportar')  # type: ignore
    @login_required
    def exportar_analise_producao():
        """
        Exporta Análise de Produção para Excel.
        Suporta agrupamento por Ordem ou Dia, com/sem Lista de Materiais (BOM).

        Query params:
            - agrupamento: 'ordem' (default) ou 'dia'
            - com_bom: 'true' ou 'false' (default 'false')
            - data_inicio, data_fim, cod_produto, nome_produto, ordem_producao, local_movimentacao
        """
        try:
            # Parâmetros de exportação
            agrupamento = request.args.get('agrupamento', 'ordem')
            com_bom = request.args.get('com_bom', 'false').lower() == 'true'

            # Parâmetros de filtro
            data_inicio = request.args.get('data_inicio', '')
            data_fim = request.args.get('data_fim', '')
            cod_produto = request.args.get('cod_produto', '')
            nome_produto_filtro = request.args.get('nome_produto', '')
            ordem_producao_filtro = request.args.get('ordem_producao', '')
            local_filtro = request.args.get('local_movimentacao', '')

            itens = []

            if agrupamento == 'dia':
                # ===== AGRUPAMENTO POR DIA + ORDEM + PRODUTO =====
                # Cada combinação (data, ordem_producao, cod_produto) gera 1 linha
                query_dia = db.session.query(
                    MovimentacaoEstoque.data_movimentacao,
                    MovimentacaoEstoque.ordem_producao,
                    MovimentacaoEstoque.cod_produto,
                    func.max(MovimentacaoEstoque.nome_produto).label('nome_produto'),
                    func.sum(MovimentacaoEstoque.qtd_movimentacao).label('qtd_total'),
                    func.count(MovimentacaoEstoque.id).label('qtd_producoes'),
                    func.max(MovimentacaoEstoque.local_movimentacao).label('local_movimentacao'),
                    func.string_agg(
                        MovimentacaoEstoque.operacao_producao_id.cast(db.String),
                        literal_column("','")
                    ).label('operacao_ids')
                ).filter(
                    MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                    MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                    MovimentacaoEstoque.ativo == True  # noqa: E712
                )

                query_dia = _aplicar_filtros_producao(
                    query_dia, data_inicio, data_fim, cod_produto,
                    nome_produto_filtro, ordem_producao_filtro, local_filtro
                )

                query_dia = query_dia.group_by(
                    MovimentacaoEstoque.data_movimentacao,
                    MovimentacaoEstoque.ordem_producao,
                    MovimentacaoEstoque.cod_produto
                ).order_by(
                    MovimentacaoEstoque.data_movimentacao.desc(),
                    MovimentacaoEstoque.ordem_producao
                )

                resultados = query_dia.all()

                for row in resultados:
                    itens.append({
                        'data_movimentacao': row.data_movimentacao,
                        'ordem_producao': row.ordem_producao or '',
                        'cod_produto': row.cod_produto,
                        'nome_produto': row.nome_produto,
                        'qtd_total': float(row.qtd_total or 0),
                        'qtd_producoes': row.qtd_producoes,
                        'local_movimentacao': row.local_movimentacao,
                        'operacao_ids': row.operacao_ids or '',
                    })

            else:
                # ===== AGRUPAMENTO POR ORDEM =====
                # Produções COM ordem_producao (agrupadas)
                query_agrupada = db.session.query(
                    MovimentacaoEstoque.ordem_producao,
                    MovimentacaoEstoque.cod_produto,
                    func.max(MovimentacaoEstoque.nome_produto).label('nome_produto'),
                    func.sum(MovimentacaoEstoque.qtd_movimentacao).label('qtd_total'),
                    func.count(MovimentacaoEstoque.id).label('qtd_producoes'),
                    func.max(MovimentacaoEstoque.data_movimentacao).label('ultima_data'),
                    func.max(MovimentacaoEstoque.local_movimentacao).label('local_movimentacao'),
                    func.string_agg(
                        MovimentacaoEstoque.operacao_producao_id.cast(db.String),
                        literal_column("','")
                    ).label('operacao_ids')
                ).filter(
                    MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                    MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                    MovimentacaoEstoque.ativo == True,  # noqa: E712
                    MovimentacaoEstoque.ordem_producao != None,  # noqa: E711
                    MovimentacaoEstoque.ordem_producao != ''
                )

                query_agrupada = _aplicar_filtros_producao(
                    query_agrupada, data_inicio, data_fim, cod_produto,
                    nome_produto_filtro, ordem_producao_filtro, local_filtro
                )

                query_agrupada = query_agrupada.group_by(
                    MovimentacaoEstoque.ordem_producao,
                    MovimentacaoEstoque.cod_produto
                ).order_by(func.max(MovimentacaoEstoque.data_movimentacao).desc())

                for row in query_agrupada.all():
                    itens.append({
                        'ordem_producao': row.ordem_producao,
                        'cod_produto': row.cod_produto,
                        'nome_produto': row.nome_produto,
                        'qtd_total': float(row.qtd_total or 0),
                        'qtd_producoes': row.qtd_producoes,
                        'ultima_data': row.ultima_data,
                        'local_movimentacao': row.local_movimentacao,
                        'operacao_ids': row.operacao_ids or '',
                    })

                # Produções SEM ordem_producao (individuais)
                if not ordem_producao_filtro:
                    query_individual = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                        MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                        MovimentacaoEstoque.ativo == True,  # noqa: E712
                        db.or_(
                            MovimentacaoEstoque.ordem_producao == None,  # noqa: E711
                            MovimentacaoEstoque.ordem_producao == ''
                        )
                    )

                    query_individual = _aplicar_filtros_producao(
                        query_individual, data_inicio, data_fim, cod_produto,
                        nome_produto_filtro, '', local_filtro
                    )

                    for prod in query_individual.order_by(MovimentacaoEstoque.data_movimentacao.desc()).all():
                        itens.append({
                            'ordem_producao': '',
                            'cod_produto': prod.cod_produto,
                            'nome_produto': prod.nome_produto,
                            'qtd_total': float(prod.qtd_movimentacao or 0),
                            'qtd_producoes': 1,
                            'ultima_data': prod.data_movimentacao,
                            'local_movimentacao': prod.local_movimentacao,
                            'operacao_ids': prod.operacao_producao_id or '',
                        })

            # Validar se tem dados
            if not itens:
                return jsonify({
                    'success': False,
                    'message': 'Nenhum registro encontrado para exportar com os filtros aplicados'
                }), 404

            filtros = {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'cod_produto': cod_produto,
                'nome_produto': nome_produto_filtro,
                'ordem_producao': ordem_producao_filtro,
                'local_movimentacao': local_filtro,
            }

            # Gerar Excel
            excel_bytes = AnaliseProducaoExportService.exportar(
                itens=itens,
                agrupamento=agrupamento,
                com_bom=com_bom,
                filtros=filtros
            )

            # Retornar como download
            sufixo_bom = '_com_bom' if com_bom else ''
            filename = f'analise_producao_{agrupamento}{sufixo_bom}_{date.today().strftime("%Y%m%d")}.xlsx'
            response = make_response(excel_bytes)
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

        except Exception as e:
            logger.error(f"Erro ao exportar análise de produção: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro ao gerar exportação: {str(e)}'
            }), 500

    @bp.route('/analise-producao/grupo-detalhe')  # type: ignore
    @login_required
    def grupo_detalhe_producao():
        """
        Retorna as produções individuais de um grupo (OP + Produto)
        para expansão na tabela principal.
        """
        try:
            ordem_producao = request.args.get('ordem_producao', '')
            cod_produto = request.args.get('cod_produto', '')

            if not ordem_producao or not cod_produto:
                return jsonify({'success': False, 'message': 'Parâmetros obrigatórios: ordem_producao, cod_produto'}), 400

            producoes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                MovimentacaoEstoque.ativo == True,
                MovimentacaoEstoque.ordem_producao == ordem_producao,
                MovimentacaoEstoque.cod_produto == cod_produto
            ).order_by(
                MovimentacaoEstoque.data_movimentacao.desc()
            ).all()

            resultado = []
            for prod in producoes:
                resultado.append({
                    'id': prod.id,
                    'data_movimentacao': prod.data_movimentacao.strftime('%d/%m/%Y') if prod.data_movimentacao else '-',
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'qtd_movimentacao': float(prod.qtd_movimentacao or 0),
                    'local_movimentacao': prod.local_movimentacao or '-',
                    'operacao_producao_id': prod.operacao_producao_id or '',
                })

            return jsonify({'success': True, 'producoes': resultado})

        except Exception as e:
            logger.error(f"Erro ao buscar detalhe do grupo: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/analise-producao/componentes-grupo')  # type: ignore
    @login_required
    def componentes_grupo_producao():
        """
        Retorna a explosão de BOM para um GRUPO de produções (mesma OP + Produto).
        Soma as quantidades de todas as produções do grupo.
        """
        try:
            ordem_producao = request.args.get('ordem_producao', '')
            cod_produto = request.args.get('cod_produto', '')

            if not ordem_producao or not cod_produto:
                return jsonify({'success': False, 'message': 'Parâmetros obrigatórios: ordem_producao, cod_produto'}), 400

            # Buscar todas as produções do grupo
            producoes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                MovimentacaoEstoque.ativo == True,
                MovimentacaoEstoque.ordem_producao == ordem_producao,
                MovimentacaoEstoque.cod_produto == cod_produto
            ).all()

            if not producoes:
                return jsonify({'success': False, 'message': 'Nenhuma produção encontrada para este grupo'}), 404

            # Somar quantidade total produzida
            qtd_total = sum(float(p.qtd_movimentacao or 0) for p in producoes)

            # Coletar todos os operacao_producao_ids do grupo
            operacao_ids = [p.operacao_producao_id for p in producoes if p.operacao_producao_id]
            producao_ids = [p.id for p in producoes]

            # Explodir BOM com quantidade TOTAL
            bom_explodido = ServicoBOM.explodir_bom(cod_produto, qtd_total)

            # Buscar consumos de TODAS as operações do grupo
            consumos_existentes = {}
            if operacao_ids:
                consumos = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.operacao_producao_id.in_(operacao_ids),
                    MovimentacaoEstoque.tipo_movimentacao == 'CONSUMO',
                    MovimentacaoEstoque.ativo == True
                ).all()

                for c in consumos:
                    if c.cod_produto not in consumos_existentes:
                        consumos_existentes[c.cod_produto] = 0
                    consumos_existentes[c.cod_produto] += abs(float(c.qtd_movimentacao or 0))

            # Buscar ajustes de TODAS as operações do grupo
            ajustes_existentes = {}
            if operacao_ids:
                ajustes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.operacao_producao_id.in_(operacao_ids),
                    MovimentacaoEstoque.tipo_movimentacao == 'AJUSTE',
                    MovimentacaoEstoque.ativo == True
                ).all()

                for a in ajustes:
                    if a.cod_produto not in ajustes_existentes:
                        ajustes_existentes[a.cod_produto] = 0
                    ajustes_existentes[a.cod_produto] += float(a.qtd_movimentacao or 0)

            # Achatar BOM (mesma lógica da rota individual)
            def achatar_bom(componente_info, nivel=1, resultados=None):
                if resultados is None:
                    resultados = []

                for comp in componente_info.get('componentes', []):
                    cod = comp['cod_produto']
                    estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod)
                    consumo_previsto = comp['qtd_necessaria']
                    consumo_registrado = consumos_existentes.get(cod, 0)
                    ajuste_estoque = ajustes_existentes.get(cod, 0)
                    ajuste_registrado = -ajuste_estoque
                    consumo_real = consumo_registrado + ajuste_registrado

                    resultados.append({
                        'cod_produto': cod,
                        'nome_produto': comp['nome_produto'],
                        'tipo': comp['tipo'],
                        'nivel': nivel,
                        'qtd_necessaria': round(consumo_previsto, 3),
                        'consumo_previsto': round(consumo_previsto, 3),
                        'consumo_registrado': round(consumo_registrado, 3),
                        'ajuste_registrado': round(ajuste_registrado, 3),
                        'consumo_real': round(consumo_real, 3),
                        'estoque_atual': round(estoque_atual, 3),
                        'tem_estrutura': comp.get('tem_estrutura', False),
                        'produto_produzido': comp.get('produto_produzido', False)
                    })

                    if comp.get('tem_estrutura') and comp.get('componentes'):
                        achatar_bom(comp, nivel + 1, resultados)

                return resultados

            componentes_lista = achatar_bom(bom_explodido)

            return jsonify({
                'success': True,
                'producao': {
                    'id': f'GRUPO-{ordem_producao}-{cod_produto}',
                    'cod_produto': cod_produto,
                    'nome_produto': producoes[0].nome_produto,
                    'qtd_produzida': qtd_total,
                    'data_movimentacao': producoes[0].data_movimentacao.strftime('%d/%m/%Y') if producoes[0].data_movimentacao else '',
                    'operacao_producao_id': ', '.join(operacao_ids[:3]) + ('...' if len(operacao_ids) > 3 else ''),
                    'local_movimentacao': producoes[0].local_movimentacao,
                    'observacao': f'Grupo: {len(producoes)} produções agrupadas',
                    'ordem_producao': ordem_producao,
                    'qtd_producoes': len(producoes),
                    'producao_ids': producao_ids,
                },
                'componentes': componentes_lista,
                'estrutura_bom': bom_explodido
            })

        except Exception as e:
            logger.error(f"Erro ao obter componentes do grupo: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/analise-producao/<int:producao_id>/componentes')  # type: ignore
    @login_required
    def obter_componentes_producao(producao_id):
        """
        Retorna a explosão de BOM para uma produção específica
        Inclui componentes recursivamente (intermediários)
        """
        try:
            # Buscar a movimentação de produção
            producao = MovimentacaoEstoque.query.get_or_404(producao_id)

            if producao.tipo_movimentacao not in ['PRODUÇÃO', 'PRODUCAO']:
                return jsonify({
                    'success': False,
                    'message': 'Movimentação não é uma produção'
                }), 400

            cod_produto = producao.cod_produto
            qtd_produzida = float(producao.qtd_movimentacao or 0)

            # Explodir BOM
            bom_explodido = ServicoBOM.explodir_bom(cod_produto, qtd_produzida)

            # Buscar consumos já registrados para esta produção
            consumos_existentes = {}
            if producao.operacao_producao_id:
                consumos = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.operacao_producao_id == producao.operacao_producao_id,
                    MovimentacaoEstoque.tipo_movimentacao == 'CONSUMO',
                    MovimentacaoEstoque.ativo == True
                ).all()

                for c in consumos:
                    if c.cod_produto not in consumos_existentes:
                        consumos_existentes[c.cod_produto] = 0
                    consumos_existentes[c.cod_produto] += abs(float(c.qtd_movimentacao or 0))

            # Buscar ajustes já feitos
            ajustes_existentes = {}
            if producao.operacao_producao_id:
                ajustes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.operacao_producao_id == producao.operacao_producao_id,
                    MovimentacaoEstoque.tipo_movimentacao == 'AJUSTE',
                    MovimentacaoEstoque.ativo == True
                ).all()

                for a in ajustes:
                    if a.cod_produto not in ajustes_existentes:
                        ajustes_existentes[a.cod_produto] = 0
                    ajustes_existentes[a.cod_produto] += float(a.qtd_movimentacao or 0)

            # Função para achatar a estrutura BOM em lista
            def achatar_bom(componente_info, nivel=1, resultados=None):
                if resultados is None:
                    resultados = []

                for comp in componente_info.get('componentes', []):
                    cod = comp['cod_produto']

                    # Estoque atual
                    estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod)

                    # Consumo previsto (da BOM)
                    consumo_previsto = comp['qtd_necessaria']

                    # Consumo já registrado
                    consumo_registrado = consumos_existentes.get(cod, 0)

                    # Ajuste já registrado (no estoque: + = devolveu, - = consumiu mais)
                    # Para calcular consumo real, invertemos: se devolveu (+), consumiu menos
                    ajuste_estoque = ajustes_existentes.get(cod, 0)
                    ajuste_registrado = -ajuste_estoque  # Inverte para visão de consumo

                    # Consumo real = consumo registrado + ajuste (na visão de consumo)
                    consumo_real = consumo_registrado + ajuste_registrado

                    resultados.append({
                        'cod_produto': cod,
                        'nome_produto': comp['nome_produto'],
                        'tipo': comp['tipo'],  # INTERMEDIARIO ou COMPONENTE
                        'nivel': nivel,
                        'qtd_necessaria': round(consumo_previsto, 3),
                        'consumo_previsto': round(consumo_previsto, 3),
                        'consumo_registrado': round(consumo_registrado, 3),
                        'ajuste_registrado': round(ajuste_registrado, 3),
                        'consumo_real': round(consumo_real, 3),
                        'estoque_atual': round(estoque_atual, 3),
                        'tem_estrutura': comp.get('tem_estrutura', False),
                        'produto_produzido': comp.get('produto_produzido', False)
                    })

                    # Recursão para intermediários
                    if comp.get('tem_estrutura') and comp.get('componentes'):
                        achatar_bom(comp, nivel + 1, resultados)

                return resultados

            # Achatar estrutura
            componentes_lista = achatar_bom(bom_explodido)

            return jsonify({
                'success': True,
                'producao': {
                    'id': producao.id,
                    'cod_produto': producao.cod_produto,
                    'nome_produto': producao.nome_produto,
                    'qtd_produzida': qtd_produzida,
                    'data_movimentacao': producao.data_movimentacao.strftime('%d/%m/%Y') if producao.data_movimentacao else '',
                    'operacao_producao_id': producao.operacao_producao_id,
                    'local_movimentacao': producao.local_movimentacao,
                    'observacao': producao.observacao
                },
                'componentes': componentes_lista,
                'estrutura_bom': bom_explodido
            })

        except Exception as e:
            logger.error(f"Erro ao obter componentes da produção {producao_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @bp.route('/analise-producao/<int:producao_id>/ajustar', methods=['POST'])  # type: ignore
    @login_required
    def ajustar_consumo_producao(producao_id):
        """
        Salva ajustes de consumo para uma produção
        Cria movimentações do tipo AJUSTE para cada componente ajustado
        Propaga ordem_producao da produção original
        """
        try:
            # Buscar a produção
            producao = MovimentacaoEstoque.query.get_or_404(producao_id)

            if producao.tipo_movimentacao not in ['PRODUÇÃO', 'PRODUCAO']:
                return jsonify({
                    'success': False,
                    'message': 'Movimentação não é uma produção'
                }), 400

            dados = request.get_json()
            ajustes = dados.get('ajustes', [])

            if not ajustes:
                return jsonify({
                    'success': False,
                    'message': 'Nenhum ajuste informado'
                }), 400

            # Garantir que a produção tenha operacao_producao_id
            operacao_id = producao.operacao_producao_id
            if not operacao_id:
                # Gerar ID de operação se não existir
                from app.estoque.services.consumo_producao_service import ServicoConsumoProducao
                operacao_id = ServicoConsumoProducao.gerar_operacao_id()
                producao.operacao_producao_id = operacao_id
                db.session.add(producao)

            ajustes_criados = []
            erros = []

            for ajuste in ajustes:
                cod_produto = ajuste.get('cod_produto')
                qtd_ajuste = ajuste.get('qtd_ajuste', 0)

                if not cod_produto:
                    continue

                try:
                    qtd_ajuste = float(qtd_ajuste)
                except (ValueError, TypeError):
                    erros.append(f'{cod_produto}: quantidade inválida')
                    continue

                if qtd_ajuste == 0:
                    continue

                # Buscar dados do produto
                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=str(cod_produto),
                    ativo=True
                ).first()

                nome_produto = cadastro.nome_produto if cadastro else f'Produto {cod_produto}'

                # Criar movimentação de AJUSTE
                # qtd_ajuste vem com semântica de CONSUMO:
                #   > 0 = consumiu mais que o previsto
                #   < 0 = consumiu menos que o previsto
                # Para ESTOQUE, invertemos:
                #   Consumiu mais → estoque diminui → qtd_movimentacao negativo
                #   Consumiu menos → estoque aumenta → qtd_movimentacao positivo
                qtd_movimentacao_estoque = -qtd_ajuste
                nova_mov = MovimentacaoEstoque(
                    cod_produto=str(cod_produto),
                    nome_produto=nome_produto,
                    tipo_movimentacao='AJUSTE',
                    qtd_movimentacao=qtd_movimentacao_estoque,
                    data_movimentacao=producao.data_movimentacao,
                    local_movimentacao=producao.local_movimentacao,
                    observacao=f'Ajuste de consumo ({"+" if qtd_ajuste > 0 else ""}{qtd_ajuste:.3f}) ref. produção {producao.id} - {producao.cod_produto}',
                    operacao_producao_id=operacao_id,
                    tipo_origem_producao='AJUSTE_MANUAL',
                    cod_produto_raiz=producao.cod_produto,
                    producao_pai_id=producao.id,
                    ordem_producao=producao.ordem_producao,  # Propagar OP da produção
                    criado_por=current_user.nome if current_user else 'Sistema',
                    tipo_origem='MANUAL'
                )

                db.session.add(nova_mov)
                ajustes_criados.append({
                    'cod_produto': cod_produto,
                    'qtd_ajuste_consumo': qtd_ajuste,  # Visão de consumo
                    'qtd_movimentacao_estoque': qtd_movimentacao_estoque  # Efeito no estoque
                })

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'{len(ajustes_criados)} ajuste(s) registrado(s)',
                'ajustes': ajustes_criados,
                'erros': erros if erros else None
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao ajustar consumo da produção {producao_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @bp.route('/analise-producao/grupo/ajustar', methods=['POST'])  # type: ignore
    @login_required
    def ajustar_consumo_grupo():
        """
        Salva ajustes de consumo para um GRUPO de produções (mesma OP + Produto).
        Cria movimentações de AJUSTE vinculadas à PRIMEIRA produção do grupo.
        """
        try:
            dados = request.get_json()
            ordem_producao = dados.get('ordem_producao', '')
            cod_produto_grupo = dados.get('cod_produto', '')
            ajustes = dados.get('ajustes', [])

            if not ordem_producao or not cod_produto_grupo:
                return jsonify({'success': False, 'message': 'Parâmetros obrigatórios: ordem_producao, cod_produto'}), 400

            if not ajustes:
                return jsonify({'success': False, 'message': 'Nenhum ajuste informado'}), 400

            # Buscar a primeira produção do grupo (para usar como referência)
            producao_ref = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'PRODUCAO']),
                MovimentacaoEstoque.tipo_origem_producao == 'RAIZ',
                MovimentacaoEstoque.ativo == True,
                MovimentacaoEstoque.ordem_producao == ordem_producao,
                MovimentacaoEstoque.cod_produto == cod_produto_grupo
            ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).first()

            if not producao_ref:
                return jsonify({'success': False, 'message': 'Nenhuma produção encontrada para este grupo'}), 404

            # Garantir que tenha operacao_producao_id
            operacao_id = producao_ref.operacao_producao_id
            if not operacao_id:
                from app.estoque.services.consumo_producao_service import ServicoConsumoProducao
                operacao_id = ServicoConsumoProducao.gerar_operacao_id()
                producao_ref.operacao_producao_id = operacao_id
                db.session.add(producao_ref)

            ajustes_criados = []
            erros = []

            for ajuste in ajustes:
                cod_produto = ajuste.get('cod_produto')
                qtd_ajuste = ajuste.get('qtd_ajuste', 0)

                if not cod_produto:
                    continue

                try:
                    qtd_ajuste = float(qtd_ajuste)
                except (ValueError, TypeError):
                    erros.append(f'{cod_produto}: quantidade inválida')
                    continue

                if qtd_ajuste == 0:
                    continue

                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=str(cod_produto),
                    ativo=True
                ).first()

                nome_produto = cadastro.nome_produto if cadastro else f'Produto {cod_produto}'

                qtd_movimentacao_estoque = -qtd_ajuste
                nova_mov = MovimentacaoEstoque(
                    cod_produto=str(cod_produto),
                    nome_produto=nome_produto,
                    tipo_movimentacao='AJUSTE',
                    qtd_movimentacao=qtd_movimentacao_estoque,
                    data_movimentacao=producao_ref.data_movimentacao,
                    local_movimentacao=producao_ref.local_movimentacao,
                    observacao=f'Ajuste de consumo grupo OP={ordem_producao} ({"+" if qtd_ajuste > 0 else ""}{qtd_ajuste:.3f}) ref. {cod_produto_grupo}',
                    operacao_producao_id=operacao_id,
                    tipo_origem_producao='AJUSTE_MANUAL',
                    cod_produto_raiz=cod_produto_grupo,
                    producao_pai_id=producao_ref.id,
                    ordem_producao=ordem_producao,
                    criado_por=current_user.nome if current_user else 'Sistema',
                    tipo_origem='MANUAL'
                )

                db.session.add(nova_mov)
                ajustes_criados.append({
                    'cod_produto': cod_produto,
                    'qtd_ajuste_consumo': qtd_ajuste,
                    'qtd_movimentacao_estoque': qtd_movimentacao_estoque
                })

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'{len(ajustes_criados)} ajuste(s) registrado(s) para o grupo',
                'ajustes': ajustes_criados,
                'erros': erros if erros else None
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao ajustar consumo do grupo: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/analise-producao/<int:producao_id>/consumos-vinculados')  # type: ignore
    @login_required
    def consumos_vinculados_producao(producao_id):
        """
        Retorna todas as movimentações vinculadas a uma produção
        (CONSUMO, AJUSTE, PRODUCAO_AUTO, etc.)
        """
        try:
            producao = MovimentacaoEstoque.query.get_or_404(producao_id)

            if not producao.operacao_producao_id:
                return jsonify({
                    'success': True,
                    'movimentacoes': [],
                    'message': 'Produção sem operação vinculada'
                })

            # Buscar todas as movimentações da mesma operação
            movimentacoes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.operacao_producao_id == producao.operacao_producao_id,
                MovimentacaoEstoque.ativo == True
            ).order_by(MovimentacaoEstoque.id).all()

            resultado = []
            for mov in movimentacoes:
                resultado.append({
                    'id': mov.id,
                    'cod_produto': mov.cod_produto,
                    'nome_produto': mov.nome_produto,
                    'tipo_movimentacao': mov.tipo_movimentacao,
                    'tipo_origem_producao': mov.tipo_origem_producao,
                    'qtd_movimentacao': float(mov.qtd_movimentacao or 0),
                    'data_movimentacao': mov.data_movimentacao.strftime('%d/%m/%Y') if mov.data_movimentacao else '',
                    'observacao': mov.observacao
                })

            return jsonify({
                'success': True,
                'operacao_id': producao.operacao_producao_id,
                'movimentacoes': resultado
            })

        except Exception as e:
            logger.error(f"Erro ao buscar consumos vinculados da produção {producao_id}: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
