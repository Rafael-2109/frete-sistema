"""
Routes para Pedidos de Compra
"""
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import desc
from datetime import datetime, timedelta
import logging

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompraAlocacao,
    HistoricoPedidoCompras
)
from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

pedidos_compras_bp = Blueprint(
    'pedidos_compras',
    __name__,
    url_prefix='/manufatura/pedidos-compras'
)


@pedidos_compras_bp.route('/')
def index():
    """Tela principal de pedidos de compra"""
    return render_template('manufatura/pedidos_compras/index.html')


@pedidos_compras_bp.route('/api/autocomplete-produtos')
def api_autocomplete_produtos():
    """
    API: Autocomplete de produtos para filtro
    Busca por código OU nome do produto
    """
    termo = request.args.get('termo', '').strip()

    if len(termo) < 2:
        return jsonify([])

    # Buscar produtos (código ou nome) - DISTINCT para evitar duplicatas
    query = db.session.query(
        PedidoCompras.cod_produto,
        PedidoCompras.nome_produto
    ).filter(
        PedidoCompras.importado_odoo == True
    ).filter(
        db.or_(
            PedidoCompras.cod_produto.ilike(f'%{termo}%'),
            PedidoCompras.nome_produto.ilike(f'%{termo}%')
        )
    ).distinct().limit(50)

    resultados = query.all()

    produtos = [
        {
            'cod_produto': r.cod_produto,
            'nome_produto': r.nome_produto
        }
        for r in resultados
    ]

    return jsonify(produtos)


@pedidos_compras_bp.route('/api/listar')
def api_listar_pedidos():
    """
    API: Lista pedidos de compra AGRUPADOS por num_pedido

    Filtros independentes:
    - data_criacao_inicio/fim: Filtra por data_pedido_criacao
    - data_previsao_inicio/fim: Filtra por data_pedido_previsao
    - cod_produto: Filtra por código do produto
    - fornecedor: Filtra por razão social

    Retorna cards agrupados com:
    - Cabeçalho: dados do pedido (num_pedido, fornecedor, datas, status)
    - Linhas: produtos do pedido

    ✅ OTIMIZADO: Paginação SQL + Eager Loading (sem N+1)
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    import math

    # Filtros independentes
    cod_produto = request.args.get('cod_produto')
    fornecedor = request.args.get('fornecedor')
    tipo_pedido = request.args.get('tipo_pedido')
    status_odoo = request.args.get('status_odoo')

    # Filtro de data de criação
    data_criacao_inicio = request.args.get('data_criacao_inicio')
    data_criacao_fim = request.args.get('data_criacao_fim')

    # Filtro de data de previsão
    data_previsao_inicio = request.args.get('data_previsao_inicio')
    data_previsao_fim = request.args.get('data_previsao_fim')

    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # ========== ETAPA 1: Contar e buscar num_pedidos únicos (paginação SQL) ==========

    # Query base para filtros
    query_base = PedidoCompras.query.filter_by(importado_odoo=True)

    # Aplicar filtros
    if cod_produto:
        query_base = query_base.filter(PedidoCompras.cod_produto.ilike(f'%{cod_produto}%'))

    if fornecedor:
        query_base = query_base.filter(PedidoCompras.raz_social.ilike(f'%{fornecedor}%'))

    if tipo_pedido:
        query_base = query_base.filter(PedidoCompras.tipo_pedido == tipo_pedido)

    if status_odoo:
        query_base = query_base.filter(PedidoCompras.status_odoo == status_odoo)

    if data_criacao_inicio:
        query_base = query_base.filter(PedidoCompras.data_pedido_criacao >= data_criacao_inicio)

    if data_criacao_fim:
        query_base = query_base.filter(PedidoCompras.data_pedido_criacao <= data_criacao_fim)

    if data_previsao_inicio:
        query_base = query_base.filter(PedidoCompras.data_pedido_previsao >= data_previsao_inicio)

    if data_previsao_fim:
        query_base = query_base.filter(PedidoCompras.data_pedido_previsao <= data_previsao_fim)

    # Subquery: num_pedidos únicos com data mais recente (para paginação)
    subquery_pedidos = db.session.query(
        PedidoCompras.num_pedido,
        func.max(PedidoCompras.data_pedido_criacao).label('max_data')
    ).filter_by(importado_odoo=True)

    # Reaplicar filtros na subquery
    if cod_produto:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.cod_produto.ilike(f'%{cod_produto}%'))
    if fornecedor:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.raz_social.ilike(f'%{fornecedor}%'))
    if tipo_pedido:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.tipo_pedido == tipo_pedido)
    if status_odoo:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.status_odoo == status_odoo)
    if data_criacao_inicio:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.data_pedido_criacao >= data_criacao_inicio)
    if data_criacao_fim:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.data_pedido_criacao <= data_criacao_fim)
    if data_previsao_inicio:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.data_pedido_previsao >= data_previsao_inicio)
    if data_previsao_fim:
        subquery_pedidos = subquery_pedidos.filter(PedidoCompras.data_pedido_previsao <= data_previsao_fim)

    subquery_pedidos = subquery_pedidos.group_by(PedidoCompras.num_pedido).subquery()

    # Contar total de pedidos únicos
    total_pedidos = db.session.query(func.count()).select_from(subquery_pedidos).scalar() or 0
    total_pages = math.ceil(total_pedidos / per_page) if total_pedidos > 0 else 1

    # Buscar num_pedidos da página atual (paginação SQL)
    pedidos_pagina = db.session.query(
        subquery_pedidos.c.num_pedido
    ).order_by(
        desc(subquery_pedidos.c.max_data)
    ).offset((page - 1) * per_page).limit(per_page).all()

    num_pedidos_pagina = [p.num_pedido for p in pedidos_pagina]

    if not num_pedidos_pagina:
        return jsonify({
            'sucesso': True,
            'total_pedidos': 0,
            'total_linhas': 0,
            'pedidos': [],
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total_pages': 1,
                'has_prev': False,
                'has_next': False
            }
        })

    # ========== ETAPA 2: Buscar linhas dos pedidos da página (com eager loading) ==========

    # ✅ Eager loading: carrega alocações junto (evita N+1)
    linhas = PedidoCompras.query.options(
        joinedload(PedidoCompras.alocacoes).joinedload(RequisicaoCompraAlocacao.requisicao)
    ).filter(
        PedidoCompras.num_pedido.in_(num_pedidos_pagina),
        PedidoCompras.importado_odoo == True
    ).order_by(
        desc(PedidoCompras.data_pedido_criacao),
        PedidoCompras.num_pedido,
        PedidoCompras.cod_produto
    ).all()

    total_linhas = len(linhas)

    # ========== ETAPA 3: Agrupar por num_pedido ==========

    pedidos_agrupados = {}

    for linha in linhas:
        num_pedido = linha.num_pedido

        if num_pedido not in pedidos_agrupados:
            pedidos_agrupados[num_pedido] = {
                'id': linha.id,
                'num_pedido': num_pedido,
                'company_id': linha.company_id,
                'fornecedor': linha.raz_social,
                'cnpj_fornecedor': linha.cnpj_fornecedor,
                'data_criacao': linha.data_pedido_criacao.isoformat() if linha.data_pedido_criacao else None,
                'data_previsao': linha.data_pedido_previsao.isoformat() if linha.data_pedido_previsao else None,
                'status_odoo': linha.status_odoo,
                'tipo_pedido': linha.tipo_pedido,
                'nf_pdf_path': linha.nf_pdf_path,
                'nf_xml_path': linha.nf_xml_path,
                'nf_numero': linha.nf_numero,
                'nf_serie': linha.nf_serie,
                'nf_chave_acesso': linha.nf_chave_acesso,
                'nf_data_emissao': linha.nf_data_emissao.isoformat() if linha.nf_data_emissao else None,
                'nf_valor_total': float(linha.nf_valor_total) if linha.nf_valor_total else None,
                'linhas': []
            }

        # ✅ Alocações já carregadas via eager loading (sem query extra)
        pedidos_agrupados[num_pedido]['linhas'].append({
            'id': linha.id,
            'cod_produto': linha.cod_produto,
            'nome_produto': linha.nome_produto,
            'qtd_produto_pedido': float(linha.qtd_produto_pedido),
            'qtd_recebida': float(linha.qtd_recebida) if linha.qtd_recebida else 0,
            'preco_produto_pedido': float(linha.preco_produto_pedido) if linha.preco_produto_pedido else 0,
            'valor_total_linha': float(linha.qtd_produto_pedido * linha.preco_produto_pedido) if linha.preco_produto_pedido else 0,
            'requisicoes_atendidas': [
                {
                    'num_requisicao': aloc.requisicao.num_requisicao if aloc.requisicao else None,
                    'qtd_alocada': float(aloc.qtd_alocada),
                    'qtd_aberta': float(aloc.qtd_aberta),
                    'percentual': aloc.percentual_alocado(),
                    'status': aloc.purchase_state
                }
                for aloc in linha.alocacoes
            ]
        })

    # Manter ordem da paginação
    pedidos_ordenados = [pedidos_agrupados[np] for np in num_pedidos_pagina if np in pedidos_agrupados]

    return jsonify({
        'sucesso': True,
        'total_pedidos': total_pedidos,
        'total_linhas': total_linhas,
        'pedidos': pedidos_ordenados,
        'paginacao': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    })


@pedidos_compras_bp.route('/api/detalhes/<int:pedido_id>')
def api_detalhes_pedido(pedido_id):
    """
    API: Detalhes de um pedido específico
    """
    pedido = PedidoCompras.query.get_or_404(pedido_id)

    # Buscar todas as alocações
    alocacoes = RequisicaoCompraAlocacao.query.filter_by(
        pedido_compra_id=pedido.id
    ).all()

    return jsonify({
        'sucesso': True,
        'pedido': {
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'company_id': pedido.company_id,  # ✅ NOVO: Empresa compradora
            'cod_produto': pedido.cod_produto,
            'nome_produto': pedido.nome_produto,
            'qtd_pedido': float(pedido.qtd_produto_pedido),
            'preco_unitario': float(pedido.preco_produto_pedido) if pedido.preco_produto_pedido else 0,
            'valor_total': float(pedido.qtd_produto_pedido * pedido.preco_produto_pedido) if pedido.preco_produto_pedido else 0,
            'fornecedor': pedido.raz_social,
            'cnpj_fornecedor': pedido.cnpj_fornecedor,
            'data_criacao': pedido.data_pedido_criacao.isoformat() if pedido.data_pedido_criacao else None,
            'data_previsao': pedido.data_pedido_previsao.isoformat() if pedido.data_pedido_previsao else None,
            'data_entrega': pedido.data_pedido_entrega.isoformat() if pedido.data_pedido_entrega else None,
            'lead_time': pedido.lead_time_pedido,
            'requisicoes': [
                {
                    'id': aloc.requisicao.id if aloc.requisicao else None,
                    'num_requisicao': aloc.requisicao.num_requisicao if aloc.requisicao else None,
                    'qtd_alocada': float(aloc.qtd_alocada),
                    'qtd_requisitada': float(aloc.qtd_requisitada),
                    'qtd_aberta': float(aloc.qtd_aberta),
                    'percentual': aloc.percentual_alocado(),
                    'status': aloc.purchase_state,
                    'data_necessidade': aloc.requisicao.data_necessidade.isoformat() if aloc.requisicao and aloc.requisicao.data_necessidade else None
                }
                for aloc in alocacoes
            ]
        }
    })


@pedidos_compras_bp.route('/api/historico/<int:pedido_compra_id>')
def api_historico_pedido(pedido_compra_id):
    """
    API: Retorna TODOS os snapshots de histórico de uma linha de pedido

    Retorna lista ordenada por data (mais recente primeiro) com:
    - Operação (CRIAR/EDITAR)
    - Data da alteração
    - Quem alterou (Odoo/usuário)
    - Snapshot completo de TODOS os campos
    """
    # Verificar se pedido existe
    pedido = PedidoCompras.query.get_or_404(pedido_compra_id)

    # Buscar TODOS os snapshots ordenados por data (mais recente primeiro)
    snapshots = HistoricoPedidoCompras.query.filter_by(
        pedido_compra_id=pedido_compra_id
    ).order_by(desc(HistoricoPedidoCompras.alterado_em)).all()

    # Serializar snapshots
    historico = []
    for snapshot in snapshots:
        historico.append({
            'id': snapshot.id,
            'operacao': snapshot.operacao,
            'alterado_em': snapshot.alterado_em.isoformat() if snapshot.alterado_em else None,
            'alterado_por': snapshot.alterado_por,
            'write_date_odoo': snapshot.write_date_odoo.isoformat() if snapshot.write_date_odoo else None,

            # Snapshot completo
            'dados': {
                'num_pedido': snapshot.num_pedido,
                'company_id': snapshot.company_id,  # ✅ NOVO: Empresa compradora
                'num_requisicao': snapshot.num_requisicao,
                'cnpj_fornecedor': snapshot.cnpj_fornecedor,
                'raz_social': snapshot.raz_social,
                'numero_nf': snapshot.numero_nf,
                'data_pedido_criacao': snapshot.data_pedido_criacao.isoformat() if snapshot.data_pedido_criacao else None,
                'usuario_pedido_criacao': snapshot.usuario_pedido_criacao,
                'lead_time_pedido': snapshot.lead_time_pedido,
                'lead_time_previsto': snapshot.lead_time_previsto,
                'data_pedido_previsao': snapshot.data_pedido_previsao.isoformat() if snapshot.data_pedido_previsao else None,
                'data_pedido_entrega': snapshot.data_pedido_entrega.isoformat() if snapshot.data_pedido_entrega else None,
                'cod_produto': snapshot.cod_produto,
                'nome_produto': snapshot.nome_produto,
                'qtd_produto_pedido': float(snapshot.qtd_produto_pedido) if snapshot.qtd_produto_pedido else 0,
                'qtd_recebida': float(snapshot.qtd_recebida) if snapshot.qtd_recebida else 0,
                'preco_produto_pedido': float(snapshot.preco_produto_pedido) if snapshot.preco_produto_pedido else 0,
                'icms_produto_pedido': float(snapshot.icms_produto_pedido) if snapshot.icms_produto_pedido else 0,
                'pis_produto_pedido': float(snapshot.pis_produto_pedido) if snapshot.pis_produto_pedido else 0,
                'cofins_produto_pedido': float(snapshot.cofins_produto_pedido) if snapshot.cofins_produto_pedido else 0,
                'confirmacao_pedido': snapshot.confirmacao_pedido,
                'confirmado_por': snapshot.confirmado_por,
                'confirmado_em': snapshot.confirmado_em.isoformat() if snapshot.confirmado_em else None,
                'status_odoo': snapshot.status_odoo,
                'tipo_pedido': snapshot.tipo_pedido,
                'importado_odoo': snapshot.importado_odoo,
                'odoo_id': snapshot.odoo_id,
                'criado_em': snapshot.criado_em.isoformat() if snapshot.criado_em else None,
                'atualizado_em': snapshot.atualizado_em.isoformat() if snapshot.atualizado_em else None,
            }
        })

    # Calcular diferenças entre snapshots consecutivos
    diferencas = []
    for i in range(len(historico) - 1):
        snapshot_atual = historico[i]
        snapshot_anterior = historico[i + 1]

        campos_alterados = []
        for campo, valor_atual in snapshot_atual['dados'].items():
            valor_anterior = snapshot_anterior['dados'].get(campo)

            if valor_atual != valor_anterior:
                campos_alterados.append({
                    'campo': campo,
                    'valor_anterior': valor_anterior,
                    'valor_atual': valor_atual
                })

        diferencas.append({
            'snapshot_id': snapshot_atual['id'],
            'campos_alterados': campos_alterados
        })

    return jsonify({
        'sucesso': True,
        'pedido': {
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'cod_produto': pedido.cod_produto,
            'nome_produto': pedido.nome_produto
        },
        'total_snapshots': len(historico),
        'historico': historico,
        'diferencas': diferencas
    })


@pedidos_compras_bp.route('/sincronizar-manual')
@login_required
def tela_sincronizacao_manual():
    """
    Tela para sincronização manual de pedidos e alocações com filtro de datas
    """
    # Sugerir últimos 7 dias como padrão
    data_fim_padrao = agora_utc_naive()
    data_inicio_padrao = data_fim_padrao - timedelta(days=7)

    return render_template(
        'manufatura/pedidos_compras/sincronizar_manual.html',
        data_inicio_padrao=data_inicio_padrao.strftime('%Y-%m-%d'),
        data_fim_padrao=data_fim_padrao.strftime('%Y-%m-%d')
    )


@pedidos_compras_bp.route('/sincronizar-manual', methods=['POST'])
@login_required
def executar_sincronizacao_manual():
    """
    Executa sincronização manual de PEDIDOS E ALOCAÇÕES com período específico
    """
    try:
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')

        if not data_inicio or not data_fim:
            flash('Datas de início e fim são obrigatórias', 'warning')
            return redirect(url_for('pedidos_compras.tela_sincronizacao_manual'))

        # Converter para datetime
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')

        # Validar período
        if data_inicio_dt > data_fim_dt:
            flash('Data inicial não pode ser maior que data final', 'warning')
            return redirect(url_for('pedidos_compras.tela_sincronizacao_manual'))

        diferenca_dias = (data_fim_dt - data_inicio_dt).days
        if diferenca_dias > 90:
            flash('Período máximo de sincronização: 90 dias', 'warning')
            return redirect(url_for('pedidos_compras.tela_sincronizacao_manual'))

        # Calcular janela em minutos
        minutos_janela = diferenca_dias * 24 * 60

        logger.info(f"[PEDIDOS] Sincronização manual: {data_inicio} a {data_fim} ({diferenca_dias} dias)")

        # 1️⃣ Executar sincronização de PEDIDOS
        pedido_service = PedidoComprasServiceOtimizado()
        resultado_pedidos = pedido_service.sincronizar_pedidos_incremental(
            minutos_janela=minutos_janela,
            primeira_execucao=False  # ✅ SEMPRE aplicar filtro de data
        )

        # 2️⃣ Executar sincronização de ALOCAÇÕES
        alocacao_service = AlocacaoComprasServiceOtimizado()
        resultado_alocacoes = alocacao_service.sincronizar_alocacoes_incremental(
            minutos_janela=minutos_janela,
            primeira_execucao=False  # ✅ SEMPRE aplicar filtro de data
        )

        # Verificar resultados
        sucesso_pedidos = resultado_pedidos.get('sucesso')
        sucesso_alocacoes = resultado_alocacoes.get('sucesso')

        if sucesso_pedidos and sucesso_alocacoes:
            db.session.commit()

            mensagem = (
                f"✅ Sincronização concluída! "
                f"Pedidos: {resultado_pedidos.get('pedidos_novos', 0)} novos, "
                f"{resultado_pedidos.get('pedidos_atualizados', 0)} atualizados | "
                f"Alocações: {resultado_alocacoes.get('alocacoes_novas', 0)} novas, "
                f"{resultado_alocacoes.get('alocacoes_atualizadas', 0)} atualizadas"
            )
            flash(mensagem, 'success')
        elif sucesso_pedidos:
            db.session.commit()
            flash(f'⚠️ Pedidos OK, mas Alocações falharam: {resultado_alocacoes.get("erro")}', 'warning')
        elif sucesso_alocacoes:
            db.session.commit()
            flash(f'⚠️ Alocações OK, mas Pedidos falharam: {resultado_pedidos.get("erro")}', 'warning')
        else:
            flash(
                f'❌ Ambos falharam - Pedidos: {resultado_pedidos.get("erro")} | '
                f'Alocações: {resultado_alocacoes.get("erro")}',
                'danger'
            )

        return redirect(url_for('pedidos_compras.index'))

    except Exception as e:
        logger.error(f"[PEDIDOS] Erro na sincronização manual: {e}")
        flash(f'❌ Erro ao executar sincronização: {str(e)}', 'danger')
        return redirect(url_for('pedidos_compras.tela_sincronizacao_manual'))


@pedidos_compras_bp.route('/nf/<tipo>/<int:pedido_id>')
@login_required
def visualizar_nf(tipo, pedido_id):
    """
    Visualizar PDF ou XML da NF de um pedido de compra

    Args:
        tipo: 'pdf' ou 'xml'
        pedido_id: ID do pedido de compra
    """
    try:
        # Buscar pedido
        pedido = PedidoCompras.query.get_or_404(pedido_id)

        # Verificar tipo solicitado
        if tipo == 'pdf':
            file_path = pedido.nf_pdf_path
        elif tipo == 'xml':
            file_path = pedido.nf_xml_path
        else:
            flash('Tipo de arquivo inválido', 'danger')
            return redirect(url_for('pedidos_compras.index'))

        if not file_path:
            flash(f'❌ {tipo.upper()} da NF não disponível para este pedido', 'warning')
            return redirect(url_for('pedidos_compras.index'))

        # Obter FileStorage e gerar URL
        file_storage = get_file_storage()
        file_url = file_storage.get_file_url(file_path)

        if not file_url:
            flash(f'❌ Arquivo {tipo.upper()} não encontrado no storage', 'warning')
            return redirect(url_for('pedidos_compras.index'))

        # Redirecionar para a URL do arquivo (S3 assinada ou estática local)
        return redirect(file_url)

    except Exception as e:
        logger.error(f"Erro ao visualizar {tipo} da NF: {e}")
        flash(f'❌ Erro ao abrir {tipo.upper()}: {str(e)}', 'danger')
        return redirect(url_for('pedidos_compras.index'))


# ============================================================================
# ENDPOINT TEMPORÁRIO - Correção de company_id
# REMOVER APÓS EXECUÇÃO EM PRODUÇÃO
# ============================================================================

@pedidos_compras_bp.route('/api/corrigir-company-id', methods=['POST'])
@login_required
def corrigir_company_id():
    """
    [TEMPORÁRIO] Corrige company_id dos pedidos buscando no Odoo

    Parâmetros (JSON):
        - dry_run: bool (default: True) - Se True, apenas simula
        - batch_size: int (default: 100) - Quantidade por batch
        - tabela: str (default: 'pedidos') - 'pedidos', 'requisicoes' ou 'alocacoes'
    """
    from app.odoo.utils.connection import get_odoo_connection

    try:
        data = request.get_json() or {}
        dry_run = data.get('dry_run', True)
        batch_size = min(data.get('batch_size', 100), 500)  # Max 500
        tabela = data.get('tabela', 'pedidos')

        logger.info(f"[CORRIGIR] Iniciando correção de company_id - tabela={tabela}, dry_run={dry_run}, batch={batch_size}")

        connection = get_odoo_connection()
        uid = connection.authenticate()

        if not uid:
            return jsonify({'erro': 'Falha na autenticação com Odoo'}), 500

        if tabela == 'pedidos':
            resultado = _corrigir_pedidos(connection, batch_size, dry_run)
        elif tabela == 'requisicoes':
            resultado = _corrigir_requisicoes(connection, batch_size, dry_run)
        elif tabela == 'alocacoes':
            resultado = _corrigir_alocacoes(connection, batch_size, dry_run)
        else:
            return jsonify({'erro': f'Tabela inválida: {tabela}'}), 400

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"[CORRIGIR] Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


def _corrigir_pedidos(connection, batch_size: int, dry_run: bool):
    """Corrige company_id nos pedidos, tratando duplicatas"""
    from app.manufatura.models import PedidoCompras, RequisicaoCompraAlocacao

    # Buscar pedidos sem company_id
    pedidos = PedidoCompras.query.filter(
        PedidoCompras.importado_odoo == True,
        PedidoCompras.company_id.is_(None),
        PedidoCompras.odoo_id.isnot(None)
    ).limit(batch_size).all()

    total = len(pedidos)
    if total == 0:
        return {'tabela': 'pedidos', 'total': 0, 'corrigidos': 0, 'deletados': 0, 'dry_run': dry_run}

    # Coletar line_ids
    line_ids = [int(p.odoo_id) for p in pedidos if p.odoo_id and p.odoo_id.isdigit()]

    if not line_ids:
        return {'tabela': 'pedidos', 'total': total, 'corrigidos': 0, 'deletados': 0, 'erro': 'Sem IDs válidos'}

    # Buscar linhas no Odoo
    linhas = connection.read('purchase.order.line', line_ids, fields=['id', 'order_id'])

    # Mapear line_id -> order_id
    line_to_order = {}
    order_ids = set()
    for linha in linhas:
        if linha.get('order_id'):
            line_to_order[str(linha['id'])] = linha['order_id'][0]
            order_ids.add(linha['order_id'][0])

    # Buscar pedidos no Odoo
    orders = connection.read('purchase.order', list(order_ids), fields=['id', 'company_id'])

    # Mapear order_id -> company_name
    order_to_company = {}
    for o in orders:
        if o.get('company_id'):
            company_name = o['company_id'][1] if len(o['company_id']) > 1 else None
            order_to_company[o['id']] = company_name

    # Atualizar pedidos (tratando duplicatas)
    corrigidos = 0
    deletados = 0

    for pedido in pedidos:
        if pedido.odoo_id and pedido.odoo_id in line_to_order:
            order_id = line_to_order[pedido.odoo_id]
            company_name = order_to_company.get(order_id)

            if company_name:
                if not dry_run:
                    # Verificar se já existe pedido com essa combinação
                    existente = PedidoCompras.query.filter(
                        PedidoCompras.num_pedido == pedido.num_pedido,
                        PedidoCompras.cod_produto == pedido.cod_produto,
                        PedidoCompras.company_id == company_name,
                        PedidoCompras.id != pedido.id
                    ).first()

                    if existente:
                        # Já existe - transferir alocações e deletar duplicado
                        RequisicaoCompraAlocacao.query.filter_by(
                            pedido_compra_id=pedido.id
                        ).update({'pedido_compra_id': existente.id})
                        # HistoricoPedidoCompras será deletado automaticamente (CASCADE)
                        db.session.delete(pedido)
                        deletados += 1
                    else:
                        # Não existe - atualizar company_id
                        pedido.company_id = company_name
                        corrigidos += 1
                else:
                    # Dry run - apenas contar
                    existente = PedidoCompras.query.filter(
                        PedidoCompras.num_pedido == pedido.num_pedido,
                        PedidoCompras.cod_produto == pedido.cod_produto,
                        PedidoCompras.company_id == company_name,
                        PedidoCompras.id != pedido.id
                    ).first()
                    if existente:
                        deletados += 1
                    else:
                        corrigidos += 1

    if not dry_run:
        db.session.commit()

    return {
        'tabela': 'pedidos',
        'total': total,
        'corrigidos': corrigidos,
        'deletados': deletados,
        'dry_run': dry_run,
        'restantes': PedidoCompras.query.filter(
            PedidoCompras.importado_odoo == True,
            PedidoCompras.company_id.is_(None)
        ).count() if not dry_run else None
    }


def _corrigir_requisicoes(connection, batch_size: int, dry_run: bool):
    """Corrige company_id nas requisições, tratando duplicatas"""
    from app.manufatura.models import RequisicaoCompras, RequisicaoCompraAlocacao

    # Buscar requisições sem company_id
    requisicoes = RequisicaoCompras.query.filter(
        RequisicaoCompras.importado_odoo == True,
        RequisicaoCompras.company_id.is_(None),
        RequisicaoCompras.requisicao_odoo_id.isnot(None)
    ).limit(batch_size).all()

    total = len(requisicoes)
    if total == 0:
        return {'tabela': 'requisicoes', 'total': 0, 'corrigidos': 0, 'deletados': 0, 'dry_run': dry_run}

    # Coletar request_ids únicos
    request_ids = list(set([
        int(r.requisicao_odoo_id) for r in requisicoes
        if r.requisicao_odoo_id and r.requisicao_odoo_id.isdigit()
    ]))

    if not request_ids:
        return {'tabela': 'requisicoes', 'total': total, 'corrigidos': 0, 'deletados': 0, 'erro': 'Sem IDs válidos'}

    # Buscar requisições no Odoo
    requests = connection.read('purchase.request', request_ids, fields=['id', 'company_id'])

    # Mapear request_id -> company_name
    request_to_company = {}
    for r in requests:
        if r.get('company_id'):
            company_name = r['company_id'][1] if len(r['company_id']) > 1 else None
            request_to_company[str(r['id'])] = company_name

    # Atualizar requisições (tratando duplicatas)
    corrigidos = 0
    deletados = 0

    for requisicao in requisicoes:
        if requisicao.requisicao_odoo_id:
            company_name = request_to_company.get(requisicao.requisicao_odoo_id)

            if company_name:
                if not dry_run:
                    # Verificar se já existe requisição com essa combinação
                    existente = RequisicaoCompras.query.filter(
                        RequisicaoCompras.num_requisicao == requisicao.num_requisicao,
                        RequisicaoCompras.cod_produto == requisicao.cod_produto,
                        RequisicaoCompras.company_id == company_name,
                        RequisicaoCompras.id != requisicao.id
                    ).first()

                    if existente:
                        # Já existe - transferir alocações e deletar duplicado
                        RequisicaoCompraAlocacao.query.filter_by(
                            requisicao_compra_id=requisicao.id
                        ).update({'requisicao_compra_id': existente.id})
                        db.session.delete(requisicao)
                        deletados += 1
                    else:
                        # Não existe - atualizar company_id
                        requisicao.company_id = company_name
                        corrigidos += 1
                else:
                    # Dry run - apenas contar
                    existente = RequisicaoCompras.query.filter(
                        RequisicaoCompras.num_requisicao == requisicao.num_requisicao,
                        RequisicaoCompras.cod_produto == requisicao.cod_produto,
                        RequisicaoCompras.company_id == company_name,
                        RequisicaoCompras.id != requisicao.id
                    ).first()
                    if existente:
                        deletados += 1
                    else:
                        corrigidos += 1

    if not dry_run:
        db.session.commit()

    return {
        'tabela': 'requisicoes',
        'total': total,
        'corrigidos': corrigidos,
        'deletados': deletados,
        'dry_run': dry_run,
        'restantes': RequisicaoCompras.query.filter(
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.company_id.is_(None)
        ).count() if not dry_run else None
    }


def _corrigir_alocacoes(connection, batch_size: int, dry_run: bool):
    """Corrige company_id nas alocações"""
    from app.manufatura.models import RequisicaoCompraAlocacao

    # Buscar alocações sem company_id
    alocacoes = RequisicaoCompraAlocacao.query.filter(
        RequisicaoCompraAlocacao.importado_odoo == True,
        RequisicaoCompraAlocacao.company_id.is_(None),
        RequisicaoCompraAlocacao.odoo_allocation_id.isnot(None)
    ).limit(batch_size).all()

    total = len(alocacoes)
    if total == 0:
        return {'tabela': 'alocacoes', 'total': 0, 'corrigidos': 0, 'deletados': 0, 'dry_run': dry_run}

    # Coletar allocation_ids
    allocation_ids = [
        int(a.odoo_allocation_id) for a in alocacoes
        if a.odoo_allocation_id and a.odoo_allocation_id.isdigit()
    ]

    if not allocation_ids:
        return {'tabela': 'alocacoes', 'total': total, 'corrigidos': 0, 'erro': 'Sem IDs válidos'}

    # Buscar alocações no Odoo
    allocations = connection.read('purchase.request.allocation', allocation_ids, fields=['id', 'company_id'])

    # Mapear allocation_id -> company_name
    allocation_to_company = {}
    for a in allocations:
        if a.get('company_id'):
            company_name = a['company_id'][1] if len(a['company_id']) > 1 else None
            allocation_to_company[str(a['id'])] = company_name

    # Atualizar alocações
    corrigidos = 0
    for alocacao in alocacoes:
        if alocacao.odoo_allocation_id:
            company_name = allocation_to_company.get(alocacao.odoo_allocation_id)

            if company_name:
                if not dry_run:
                    alocacao.company_id = company_name
                corrigidos += 1

    if not dry_run:
        db.session.commit()

    return {
        'tabela': 'alocacoes',
        'total': total,
        'corrigidos': corrigidos,
        'deletados': 0,
        'dry_run': dry_run,
        'restantes': RequisicaoCompraAlocacao.query.filter(
            RequisicaoCompraAlocacao.importado_odoo == True,
            RequisicaoCompraAlocacao.company_id.is_(None)
        ).count() if not dry_run else None
    }


@pedidos_compras_bp.route('/api/status-company-id')
@login_required
def status_company_id():
    """
    [TEMPORÁRIO] Retorna status de preenchimento do company_id
    """
    from app.manufatura.models import RequisicaoCompras, RequisicaoCompraAlocacao

    try:
        # Pedidos
        pedidos_total = PedidoCompras.query.filter(PedidoCompras.importado_odoo == True).count()
        pedidos_sem = PedidoCompras.query.filter(
            PedidoCompras.importado_odoo == True,
            PedidoCompras.company_id.is_(None)
        ).count()

        # Requisições
        requisicoes_total = RequisicaoCompras.query.filter(RequisicaoCompras.importado_odoo == True).count()
        requisicoes_sem = RequisicaoCompras.query.filter(
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.company_id.is_(None)
        ).count()

        # Alocações
        alocacoes_total = RequisicaoCompraAlocacao.query.filter(RequisicaoCompraAlocacao.importado_odoo == True).count()
        alocacoes_sem = RequisicaoCompraAlocacao.query.filter(
            RequisicaoCompraAlocacao.importado_odoo == True,
            RequisicaoCompraAlocacao.company_id.is_(None)
        ).count()

        return jsonify({
            'pedidos': {
                'total': pedidos_total,
                'sem_empresa': pedidos_sem,
                'percentual_ok': round((pedidos_total - pedidos_sem) / pedidos_total * 100, 1) if pedidos_total > 0 else 100
            },
            'requisicoes': {
                'total': requisicoes_total,
                'sem_empresa': requisicoes_sem,
                'percentual_ok': round((requisicoes_total - requisicoes_sem) / requisicoes_total * 100, 1) if requisicoes_total > 0 else 100
            },
            'alocacoes': {
                'total': alocacoes_total,
                'sem_empresa': alocacoes_sem,
                'percentual_ok': round((alocacoes_total - alocacoes_sem) / alocacoes_total * 100, 1) if alocacoes_total > 0 else 100
            }
        })

    except Exception as e:
        logger.error(f"[STATUS] Erro: {e}")
        return jsonify({'erro': str(e)}), 500
