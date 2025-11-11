"""
Routes para Pedidos de Compra
"""
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import desc
from datetime import date, datetime, timedelta
import logging

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompraAlocacao,
    HistoricoPedidoCompras
)
from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado

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
    """
    # Filtros independentes
    cod_produto = request.args.get('cod_produto')
    fornecedor = request.args.get('fornecedor')

    # Filtro de data de criação
    data_criacao_inicio = request.args.get('data_criacao_inicio')
    data_criacao_fim = request.args.get('data_criacao_fim')

    # Filtro de data de previsão
    data_previsao_inicio = request.args.get('data_previsao_inicio')
    data_previsao_fim = request.args.get('data_previsao_fim')

    limit = request.args.get('limit', 500, type=int)

    # Query base
    query = PedidoCompras.query.filter_by(importado_odoo=True)

    # Aplicar filtros independentes
    if cod_produto:
        query = query.filter(PedidoCompras.cod_produto.like(f'%{cod_produto}%'))

    if fornecedor:
        query = query.filter(PedidoCompras.raz_social.like(f'%{fornecedor}%'))

    # Filtro de data de CRIAÇÃO
    if data_criacao_inicio:
        query = query.filter(PedidoCompras.data_pedido_criacao >= data_criacao_inicio)

    if data_criacao_fim:
        query = query.filter(PedidoCompras.data_pedido_criacao <= data_criacao_fim)

    # Filtro de data de PREVISÃO
    if data_previsao_inicio:
        query = query.filter(PedidoCompras.data_pedido_previsao >= data_previsao_inicio)

    if data_previsao_fim:
        query = query.filter(PedidoCompras.data_pedido_previsao <= data_previsao_fim)

    # ✅ ORDENAÇÃO: Por data_pedido_criacao DESC (mais recentes primeiro)
    query_ordenada = query.order_by(
        desc(PedidoCompras.data_pedido_criacao),
        PedidoCompras.num_pedido,
        PedidoCompras.cod_produto
    )

    # ✅ BUSCAR TODAS as linhas que atendem aos filtros
    todas_linhas = query_ordenada.all()

    # ✅ AGRUPAR por num_pedido ANTES de paginar
    pedidos_agrupados = {}
    total_linhas = len(todas_linhas)

    for linha in todas_linhas:
        num_pedido = linha.num_pedido

        # Criar card do pedido se não existir
        if num_pedido not in pedidos_agrupados:
            pedidos_agrupados[num_pedido] = {
                # Cabeçalho do card (dados do pedido)
                'num_pedido': num_pedido,
                'company_id': linha.company_id,  # ✅ NOVO: Empresa compradora
                'fornecedor': linha.raz_social,
                'cnpj_fornecedor': linha.cnpj_fornecedor,
                'data_criacao': linha.data_pedido_criacao.isoformat() if linha.data_pedido_criacao else None,
                'data_previsao': linha.data_pedido_previsao.isoformat() if linha.data_pedido_previsao else None,
                'status_odoo': linha.status_odoo,
                'tipo_pedido': linha.tipo_pedido,

                # Linhas de produtos
                'linhas': []
            }

        # Buscar alocações da linha
        alocacoes = RequisicaoCompraAlocacao.query.filter_by(
            pedido_compra_id=linha.id
        ).all()

        # Adicionar linha de produto
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
                for aloc in alocacoes
            ]
        })

    # ✅ CONVERTER para lista (mantém ordem de criação DESC)
    todos_pedidos = list(pedidos_agrupados.values())
    total_pedidos = len(todos_pedidos)

    # ✅ APLICAR PAGINAÇÃO: 20 PEDIDOS por página (não linhas!)
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 20 PEDIDOS por página

    import math
    total_pages = math.ceil(total_pedidos / per_page) if total_pedidos > 0 else 1

    # Calcular slice para paginação
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    pedidos_paginados = todos_pedidos[start_idx:end_idx]

    return jsonify({
        'sucesso': True,
        'total_pedidos': total_pedidos,
        'total_linhas': total_linhas,
        'pedidos': pedidos_paginados,
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
    data_fim_padrao = datetime.now()
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
