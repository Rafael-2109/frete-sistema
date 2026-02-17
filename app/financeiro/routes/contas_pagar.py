# -*- coding: utf-8 -*-
"""
Rotas de Contas a Pagar
=======================

Hub, Listagem, Sincronização e APIs básicas.

Rotas:
- /contas-pagar/ - Hub central
- /contas-pagar/listar - Listagem com filtros
- /contas-pagar/sincronizar-odoo - Sincronização manual
- /contas-pagar/api/status - Status da sincronização

Autor: Sistema de Fretes
Data: 2025-12-13
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, or_

from app import db
from app.financeiro.routes import financeiro_bp
from app.financeiro.models import ContasAPagar


# =============================================================================
# HUB CENTRAL
# =============================================================================

@financeiro_bp.route('/contas-pagar/')
@login_required
def contas_pagar_hub():
    """
    Hub Central de Contas a Pagar.
    Página inicial com resumo e links para funcionalidades.
    """
    # Estatísticas rápidas
    hoje = date.today()

    # Total em aberto
    total_aberto = db.session.query(func.sum(ContasAPagar.valor_residual)).filter(
        ContasAPagar.parcela_paga == False
    ).scalar() or 0

    # Vencidos
    total_vencido = db.session.query(func.sum(ContasAPagar.valor_residual)).filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento < hoje
    ).scalar() or 0

    qtd_vencido = ContasAPagar.query.filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento < hoje
    ).count()

    # Vence hoje
    total_hoje = db.session.query(func.sum(ContasAPagar.valor_residual)).filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento == hoje
    ).scalar() or 0

    qtd_hoje = ContasAPagar.query.filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento == hoje
    ).count()

    # Vence semana (próximos 7 dias)
    semana = hoje + timedelta(days=7)
    total_semana = db.session.query(func.sum(ContasAPagar.valor_residual)).filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento > hoje,
        ContasAPagar.vencimento <= semana
    ).scalar() or 0

    qtd_semana = ContasAPagar.query.filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.vencimento > hoje,
        ContasAPagar.vencimento <= semana
    ).count()

    # Última sincronização
    ultima_sync = db.session.query(func.max(ContasAPagar.ultima_sincronizacao)).scalar()

    # Total de registros
    total_registros = ContasAPagar.query.count()

    return render_template(
        'financeiro/contas_pagar_hub.html',
        total_aberto=total_aberto,
        total_vencido=total_vencido,
        qtd_vencido=qtd_vencido,
        total_hoje=total_hoje,
        qtd_hoje=qtd_hoje,
        total_semana=total_semana,
        qtd_semana=qtd_semana,
        ultima_sync=ultima_sync,
        total_registros=total_registros,
        hoje=hoje
    )


# =============================================================================
# LISTAGEM
# =============================================================================

@financeiro_bp.route('/contas-pagar/listar')
@login_required
def listar_contas_pagar():
    """
    Listagem de Contas a Pagar com paginação e filtros.
    """
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = 100

    # Parâmetros de ordenação
    sort = request.args.get('sort', 'vencimento')
    direction = request.args.get('direction', 'asc')

    # Parâmetros de filtro
    empresa = request.args.get('empresa', '', type=str)
    titulo_nf = request.args.get('titulo_nf', '', type=str)
    cnpj = request.args.get('cnpj', '', type=str)
    fornecedor = request.args.get('fornecedor', '', type=str)
    status = request.args.get('status', '', type=str)
    venc_de = request.args.get('venc_de', '', type=str)
    venc_ate = request.args.get('venc_ate', '', type=str)

    # Query base
    query = ContasAPagar.query

    # Aplicar filtros
    if empresa:
        query = query.filter(ContasAPagar.empresa == int(empresa))

    if titulo_nf:
        query = query.filter(ContasAPagar.titulo_nf.ilike(f'%{titulo_nf}%'))

    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '').replace(' ', '')
        query = query.filter(
            or_(
                ContasAPagar.cnpj.ilike(f'%{cnpj}%'),
                func.regexp_replace(ContasAPagar.cnpj, r'[^0-9]', '', 'g').ilike(f'%{cnpj_limpo}%')
            )
        )

    if fornecedor:
        query = query.filter(or_(
            ContasAPagar.raz_social.ilike(f'%{fornecedor}%'),
            ContasAPagar.raz_social_red.ilike(f'%{fornecedor}%')
        ))

    if status:
        hoje = date.today()

        if status == 'aberto':
            query = query.filter(
                ContasAPagar.parcela_paga == False,
                or_(ContasAPagar.vencimento >= hoje, ContasAPagar.vencimento.is_(None))
            )
        elif status == 'pago':
            query = query.filter(ContasAPagar.parcela_paga == True)
        elif status == 'vencido':
            query = query.filter(
                ContasAPagar.parcela_paga == False,
                ContasAPagar.vencimento < hoje
            )
        elif status == 'vence_hoje':
            query = query.filter(
                ContasAPagar.parcela_paga == False,
                ContasAPagar.vencimento == hoje
            )
        elif status == 'vence_semana':
            semana = hoje + timedelta(days=7)
            query = query.filter(
                ContasAPagar.parcela_paga == False,
                ContasAPagar.vencimento > hoje,
                ContasAPagar.vencimento <= semana
            )

    if venc_de:
        try:
            data_de = datetime.strptime(venc_de, '%Y-%m-%d').date()
            query = query.filter(ContasAPagar.vencimento >= data_de)
        except ValueError:
            pass

    if venc_ate:
        try:
            data_ate = datetime.strptime(venc_ate, '%Y-%m-%d').date()
            query = query.filter(ContasAPagar.vencimento <= data_ate)
        except ValueError:
            pass

    # Aplicar ordenação
    sort_column = getattr(ContasAPagar, sort, ContasAPagar.vencimento)
    if direction == 'desc':
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    # Paginar
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)
    contas = paginacao.items

    # Calcular totais da página
    valor_total = sum(c.valor_residual or 0 for c in contas)
    hoje = date.today()
    vencidos = sum(1 for c in contas if c.vencimento and c.vencimento < hoje and not c.parcela_paga)
    pagos = sum(1 for c in contas if c.parcela_paga)

    return render_template(
        'financeiro/listar_contas_pagar.html',
        contas=contas,
        paginacao=paginacao,
        sort=sort,
        direction=direction,
        hoje=hoje,
        valor_total=valor_total,
        vencidos=vencidos,
        pagos=pagos
    )


# =============================================================================
# SINCRONIZAÇÃO
# =============================================================================

@financeiro_bp.route('/contas-pagar/sincronizar-odoo', methods=['POST'])
@login_required
def sincronizar_contas_pagar_odoo():
    """
    Sincronização manual de Contas a Pagar com Odoo.

    Parâmetros (JSON body ou form data):
        data_inicio: Data inicial (YYYY-MM-DD) - opcional
        data_fim: Data final (YYYY-MM-DD) - opcional
        dias: Quantidade de dias retroativos - alternativa
        apenas_em_aberto: Se True, apenas títulos em aberto
    """
    try:
        from app.financeiro.services.sincronizacao_contas_pagar_service import SincronizacaoContasAPagarService

        # Obter parâmetros
        data = request.get_json(silent=True) or {}

        data_inicio_str = data.get('data_inicio') or request.form.get('data_inicio')
        data_fim_str = data.get('data_fim') or request.form.get('data_fim')
        dias = data.get('dias') or request.form.get('dias')
        apenas_em_aberto = data.get('apenas_em_aberto', True)

        # Converter datas
        data_inicio = None
        data_fim = None

        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de data_inicio inválido: {data_inicio_str}'
                }), 400

        if data_fim_str:
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de data_fim inválido: {data_fim_str}'
                }), 400

        if dias and not data_inicio:
            try:
                dias = int(dias)
                data_inicio = date.today() - timedelta(days=dias)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Parâmetro dias inválido: {dias}'
                }), 400

        # Criar serviço e executar
        service = SincronizacaoContasAPagarService()

        if data_inicio or data_fim:
            resultado = service.sincronizar(
                data_inicio=data_inicio,
                data_fim=data_fim,
                apenas_em_aberto=apenas_em_aberto
            )
        else:
            resultado = service.sincronizar_manual(dias=90)

        if resultado.get('sucesso'):
            return jsonify({
                'success': True,
                'message': 'Sincronização concluída com sucesso!',
                'periodo': resultado.get('periodo', 'Últimos 90 dias'),
                'novos': resultado.get('novos', 0),
                'atualizados': resultado.get('atualizados', 0),
                'ignorados': resultado.get('ignorados', 0),
                'erros': resultado.get('erros', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('erro', 'Erro desconhecido na sincronização')
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# APIs
# =============================================================================

@financeiro_bp.route('/contas-pagar/api/status')
@login_required
def status_contas_pagar():
    """
    Retorna estatísticas da tabela contas_a_pagar
    """
    try:
        total = ContasAPagar.query.count()

        por_empresa = db.session.query(
            ContasAPagar.empresa,
            func.count(ContasAPagar.id),
            func.sum(ContasAPagar.valor_residual)
        ).filter(ContasAPagar.parcela_paga == False).group_by(ContasAPagar.empresa).all()

        ultima_sync = db.session.query(
            func.max(ContasAPagar.ultima_sincronizacao)
        ).scalar()

        empresas = {
            1: 'NACOM GOYA - FB',
            2: 'NACOM GOYA - SC',
            3: 'NACOM GOYA - CD'
        }

        return jsonify({
            'success': True,
            'total': total,
            'por_empresa': [
                {
                    'empresa': empresas.get(e, f'Empresa {e}'),
                    'total': t,
                    'valor': round(v or 0, 2)
                }
                for e, t, v in por_empresa
            ],
            'ultima_sincronizacao': ultima_sync.isoformat() if ultima_sync else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/contas-pagar/api/<int:conta_id>')
@login_required
def detalhe_conta_pagar(conta_id):
    """
    Retorna detalhes de uma conta a pagar
    """
    try:
        conta = ContasAPagar.query.get_or_404(conta_id)
        return jsonify({
            'success': True,
            'data': conta.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# BUSCA SEMANTICA DE ENTIDADES (compartilhado pagar/receber)
# =============================================================================

@financeiro_bp.route('/api/busca-semantica', methods=['GET'])
@login_required
def busca_semantica_entidades():
    """
    Busca semantica de fornecedores/clientes via embeddings.

    Recebe termo parcial/abreviado e retorna matches por similaridade
    usando FinancialEntityEmbedding (Voyage AI + pgvector).

    Query params:
        q: Termo de busca (min 2 chars)
        tipo: 'supplier', 'customer', ou 'all' (default: 'all')
        limit: Maximo de resultados (default: 8, max: 20)

    Returns:
        JSON: { success, resultados: [{ cnpj_raiz, cnpj_completo, nome, entity_type, similarity }] }
    """
    try:
        q = request.args.get('q', '').strip()
        tipo = request.args.get('tipo', 'all')
        limit = min(request.args.get('limit', 8, type=int), 20)

        if not q or len(q) < 2:
            return jsonify({'success': True, 'resultados': []})

        if tipo not in ('supplier', 'customer', 'all'):
            tipo = 'all'

        # Tentar busca semantica
        try:
            from app.embeddings.config import FINANCIAL_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
            if not EMBEDDINGS_ENABLED or not FINANCIAL_SEMANTIC_SEARCH:
                return jsonify({
                    'success': True,
                    'resultados': [],
                    'metodo': 'desabilitado'
                })

            from app.embeddings.service import EmbeddingService
            svc = EmbeddingService()
            results = svc.search_entities(
                query=q,
                entity_type=tipo,
                limit=limit,
                min_similarity=0.60,
            )

            resultados = []
            for r in results:
                resultados.append({
                    'cnpj_raiz': r.get('cnpj_raiz', ''),
                    'cnpj_completo': r.get('cnpj_completo', ''),
                    'nome': r.get('nome', ''),
                    'entity_type': r.get('entity_type', ''),
                    'similarity': round(r.get('similarity', 0), 3),
                })

            return jsonify({
                'success': True,
                'resultados': resultados,
                'metodo': 'semantico',
                'total': len(resultados),
            })

        except Exception:
            # Fallback: retornar vazio (busca ILIKE normal continua funcionando no form)
            return jsonify({
                'success': True,
                'resultados': [],
                'metodo': 'fallback'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
