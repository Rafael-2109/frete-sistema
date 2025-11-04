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
    RequisicaoCompraAlocacao
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


@pedidos_compras_bp.route('/api/listar')
def api_listar_pedidos():
    """
    API: Lista pedidos de compra com filtros
    """
    # Filtros
    cod_produto = request.args.get('cod_produto')
    fornecedor = request.args.get('fornecedor')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    limit = request.args.get('limit', 500, type=int)

    # Query base
    query = PedidoCompras.query.filter_by(importado_odoo=True)

    # Aplicar filtros
    if cod_produto:
        query = query.filter(PedidoCompras.cod_produto.like(f'%{cod_produto}%'))

    if fornecedor:
        query = query.filter(PedidoCompras.raz_social.like(f'%{fornecedor}%'))

    if data_inicio:
        query = query.filter(PedidoCompras.data_pedido_previsao >= data_inicio)

    if data_fim:
        query = query.filter(PedidoCompras.data_pedido_previsao <= data_fim)

    # Executar
    pedidos = query.order_by(desc(PedidoCompras.data_pedido_previsao)).limit(limit).all()

    # Serializar com alocações
    resultado = []
    for pedido in pedidos:
        # Buscar alocações
        alocacoes = RequisicaoCompraAlocacao.query.filter_by(
            pedido_compra_id=pedido.id
        ).all()

        resultado.append({
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'cod_produto': pedido.cod_produto,
            'nome_produto': pedido.nome_produto,
            'qtd_pedido': float(pedido.qtd_produto_pedido),
            'preco_unitario': float(pedido.preco_produto_pedido) if pedido.preco_produto_pedido else 0,
            'fornecedor': pedido.raz_social,
            'cnpj_fornecedor': pedido.cnpj_fornecedor,
            'data_criacao': pedido.data_pedido_criacao.isoformat() if pedido.data_pedido_criacao else None,
            'data_previsao': pedido.data_pedido_previsao.isoformat() if pedido.data_pedido_previsao else None,
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

    return jsonify({
        'sucesso': True,
        'total': len(resultado),
        'pedidos': resultado
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
