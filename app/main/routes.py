from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app, request, jsonify, send_file
from flask_login import current_user, login_required
import os
from app.utils.api_helper import APIDataHelper
import tempfile
from datetime import datetime, timedelta, date
from app.utils.timezone import agora_utc_naive

from app import db
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import Embarque, EmbarqueItem
from app.fretes.models import Frete
from app.transportadoras.models import Transportadora
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from app.manufatura.models import PedidoCompras
from app.producao.models import ProgramacaoProducao
from app.separacao.models import Separacao
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload
main_bp = Blueprint('main', __name__)

def _ultimo_dia_util(ref_date):
    """Retorna o ultimo dia util antes de ref_date (pula sabado/domingo)."""
    d = ref_date - timedelta(days=1)
    while d.weekday() >= 5:  # 5=sabado, 6=domingo
        d -= timedelta(days=1)
    return d


@main_bp.route('/dashboard')
@main_bp.route('/main/dashboard')
@login_required
def dashboard():
    """Dashboard principal — dados carregados via AJAX pelos endpoints /api/dashboard/*"""
    if current_user.perfil == 'vendedor':
        return redirect(url_for('comercial.dashboard_diretoria'))
    return render_template('main/dashboard.html', usuario=current_user)

@main_bp.route('/relatorio_gerencial')
@login_required
def relatorio_gerencial():
    """Relatório gerencial usando dados da API"""
    try:
        periodo = int(request.args.get('periodo', 30))
        
        # Obtém dados via API Helper
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        embarques_data = APIDataHelper.get_embarques_data(limite=20)
        fretes_data = APIDataHelper.get_fretes_pendentes_data(limite=15)
        
        dados_relatorio = {
            'periodo': periodo,
            'estatisticas': stats_data.get('data', {}) if stats_data.get('success') else {},
            'embarques_recentes': embarques_data.get('data', []) if embarques_data.get('success') else [],
            'fretes_pendentes': fretes_data.get('data', []) if fretes_data.get('success') else [],
            'data_geracao': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return render_template('main/relatorio_gerencial.html', **dados_relatorio)
        
    except Exception as e:
        return f"Erro ao gerar relatório: {str(e)}", 500

@main_bp.route('/relatorio_gerencial/excel')
@login_required  
def relatorio_gerencial_excel():
    """Exporta relatório gerencial em Excel usando dados da API"""
    import pandas as pd  # Lazy import

    try:
        periodo = int(request.args.get('periodo', 30))
        
        # Obtém dados via API Helper
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        embarques_data = APIDataHelper.get_embarques_data(limite=50)
        fretes_data = APIDataHelper.get_fretes_pendentes_data(limite=100)
        
        # Prepara dados para Excel
        dados_excel = {
            'Estatísticas': [],
            'Embarques': [],
            'Fretes_Pendentes': []
        }
        
        # Aba de estatísticas
        if stats_data.get('success'):
            stats = stats_data['data']
            dados_excel['Estatísticas'] = [
                {'Métrica': 'Total de Embarques', 'Valor': stats['embarques']['total']},
                {'Métrica': 'Embarques Ativos', 'Valor': stats['embarques']['ativos']},
                {'Métrica': 'Total de Fretes', 'Valor': stats['fretes']['total']},
                {'Métrica': 'Fretes Aprovados', 'Valor': stats['fretes']['aprovados']},
                {'Métrica': '% Aprovação', 'Valor': f"{stats['fretes']['percentual_aprovacao']}%"},
                {'Métrica': 'Total Entregas', 'Valor': stats['entregas']['total_monitoradas']},
                {'Métrica': 'Entregas Concluídas', 'Valor': stats['entregas']['entregues']},
                {'Métrica': 'Pendências Financeiras', 'Valor': stats['entregas']['pendencias_financeiras']},
                {'Métrica': '% Entregas', 'Valor': f"{stats['entregas']['percentual_entrega']}%"}
            ]
        
        # Aba de embarques
        if embarques_data.get('success'):
            for embarque in embarques_data['data']:
                dados_excel['Embarques'].append({
                    'ID': embarque['id'],
                    'Número': embarque['numero'],
                    'Status': embarque['status'],
                    'Data_Embarque': embarque['data_embarque'] or 'N/A',
                    'Transportadora': embarque['transportadora'] or 'N/A',
                    'Total_Fretes': embarque['total_fretes']
                })
        
        # Aba de fretes pendentes
        if fretes_data.get('success'):
            for frete in fretes_data['data']:
                dados_excel['Fretes_Pendentes'].append({
                    'ID': frete['id'],
                    'Embarque': frete['embarque_numero'] or 'N/A',
                    'Transportadora': frete['transportadora'] or 'N/A',
                    'Cliente': frete['cliente'],
                    'Destino': frete['destino'],
                    'Valor_Cotado': frete['valor_cotado'] or 0,
                    'Tem_CTe': 'Sim' if frete['tem_cte'] else 'Não'
                })
        
        # Cria arquivo Excel temporário
        arquivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        
        with pd.ExcelWriter(arquivo_temp.name, engine='xlsxwriter') as writer:
            # Cria cada aba
            for aba_nome, dados in dados_excel.items():
                if dados:
                    df = pd.DataFrame(dados)
                    df.to_excel(writer, sheet_name=aba_nome, index=False)
            
            # Aba de resumo
            resumo_data = [{
                'Relatório': 'Relatório Gerencial',
                'Período': f'Últimos {periodo} dias',
                'Data_Geração': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S'),
                'Usuário': current_user.nome,
                'Total_Abas': len([d for d in dados_excel.values() if d])
            }]
            
            df_resumo = pd.DataFrame(resumo_data)
            df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        arquivo_temp.close()
        
        # Nome do arquivo para download
        nome_arquivo = f"relatorio_gerencial_{periodo}dias_{agora_utc_naive().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            arquivo_temp.name,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return f"Erro ao gerar Excel: {str(e)}", 500

@main_bp.route('/api/dashboard/estatisticas')
@login_required
def api_dashboard_estatisticas():
    """Endpoint interno para estatísticas do dashboard"""
    try:
        periodo = int(request.args.get('periodo', 30))
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        return jsonify(stats_data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/dashboard/alertas')
@login_required
def api_dashboard_alertas():
    """Endpoint interno para alertas do dashboard"""
    try:
        alertas_data = APIDataHelper.get_alertas_sistema()
        return jsonify(alertas_data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/consulta_rapida/<cliente_nome>')
@login_required
def consulta_rapida_cliente(cliente_nome):
    """Página de consulta rápida usando dados da API"""
    try:
        uf = request.args.get('uf', '')
        limite = int(request.args.get('limite', 10))
        
        # Usa API Helper para obter dados do cliente
        dados_cliente = APIDataHelper.get_cliente_data(
            cliente_nome=cliente_nome, 
            uf_filtro=uf if uf else None, 
            limite=limite
        )
        
        if dados_cliente.get('success'):
            return render_template('main/consulta_cliente.html', 
                                 dados=dados_cliente,
                                 cliente_nome=cliente_nome,
                                 uf_filtro=uf)
        else:
            return render_template('main/consulta_cliente.html', 
                                 erro=dados_cliente.get('error'),
                                 cliente_nome=cliente_nome,
                                 uf_filtro=uf)
        
    except Exception as e:
        return f"Erro na consulta: {str(e)}", 500

@main_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

@main_bp.route('/favicon.ico')
def favicon():
    """Rota para o favicon.ico para evitar erros 404"""
    try:
        # Tenta servir favicon.ico da pasta static se existir
        static_dir = os.path.join(current_app.root_path, 'static')
        if os.path.exists(os.path.join(static_dir, 'favicon.ico')):
            return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        pass
    
    # Se não encontrar, retorna resposta vazia
    from flask import Response
    return Response('', status=204, mimetype='image/vnd.microsoft.icon')

@main_bp.route('/api/estatisticas-internas', methods=['GET'])
@login_required
def api_estatisticas_internas():
    """Estatísticas do sistema para dashboard interno (com autenticação de sessão)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando coleta de estatísticas internas")
        
        # Contar embarques
        logger.info("📊 Contando embarques...")
        total_embarques = Embarque.query.count()
        logger.info(f"📦 Total embarques: {total_embarques}")
        
        embarques_ativos = Embarque.query.filter(Embarque.status == 'ativo').count()
        logger.info(f"🟢 Embarques ativos: {embarques_ativos}")
        
        # Embarques pendentes (ativos sem data de embarque)
        embarques_pendentes = Embarque.query.filter(
            Embarque.status == 'ativo',
            Embarque.data_embarque == None
        ).count()
        logger.info(f"⏳ Embarques pendentes: {embarques_pendentes}")
        
        # Contar fretes
        logger.info("🚛 Contando fretes...")
        total_fretes = Frete.query.count()
        logger.info(f"📋 Total fretes: {total_fretes}")
        
        # Campo correto é 'status', não 'status_aprovacao'
        fretes_pendentes = Frete.query.filter(Frete.status == 'pendente').count()
        logger.info(f"⏳ Fretes pendentes: {fretes_pendentes}")
        
        fretes_aprovados = Frete.query.filter(Frete.status == 'aprovado').count()
        logger.info(f"✅ Fretes aprovados: {fretes_aprovados}")
        
        # Contar entregas monitoradas
        logger.info("📦 Contando entregas...")
        total_entregas = EntregaMonitorada.query.count()
        logger.info(f"📊 Total entregas: {total_entregas}")
        
        entregas_entregues = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao == 'Entregue'
        ).count()
        logger.info(f"✅ Entregas entregues: {entregas_entregues}")
        
        # Entregas pendentes (não entregues)
        entregas_pendentes = EntregaMonitorada.query.filter(
            EntregaMonitorada.entregue == False
        ).count()
        logger.info(f"📦 Entregas pendentes: {entregas_pendentes}")
        
        pendencias_financeiras = EntregaMonitorada.query.filter(
            EntregaMonitorada.pendencia_financeira == True
        ).count()
        logger.info(f"💰 Pendências financeiras: {pendencias_financeiras}")
        
        # Contar pedidos abertos
        logger.info("📋 Contando pedidos...")
        pedidos_abertos = Pedido.query.filter(
            Pedido.status == 'aberto'
        ).count()
        logger.info(f"📂 Pedidos abertos: {pedidos_abertos}")
        
        logger.info("🧮 Montando resultado...")
        resultado = {
            'embarques': {
                'total': total_embarques,
                'ativos': embarques_ativos,
                'pendentes': embarques_pendentes,
                'cancelados': total_embarques - embarques_ativos
            },
            'fretes': {
                'total': total_fretes,
                'pendentes_aprovacao': fretes_pendentes,
                'aprovados': fretes_aprovados,
                'percentual_aprovacao': round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0
            },
            'entregas': {
                'total_monitoradas': total_entregas,
                'entregues': entregas_entregues,
                'pendentes': entregas_pendentes,
                'pendencias_financeiras': pendencias_financeiras,
                'percentual_entrega': round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0
            },
            'pedidos': {
                'abertos': pedidos_abertos
            }
        }
        
        logger.info("✅ Estatísticas coletadas com sucesso")
        
        return jsonify({
            'success': True,
            'data': resultado,
            'usuario': current_user.nome,
            'timestamp': agora_utc_naive().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Erro ao coletar estatísticas: {str(e)}")
        logger.error(f"📍 Tipo do erro: {type(e)}")
        import traceback
        logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': str(type(e))
        }), 500

@main_bp.route('/api/embarques-internos', methods=['GET'])
@login_required
def api_embarques_internos():
    """Lista embarques para dashboard interno (com autenticação de sessão)"""
    try:
        limite = int(request.args.get('limite', 8))
        
        embarques = Embarque.query.filter(
            Embarque.status == 'ativo'
        ).order_by(Embarque.id.desc()).limit(limite).all()
        
        resultado = []
        for embarque in embarques:
            modalidade = None
            if embarque.itens and len(embarque.itens) > 0:
                modalidade = embarque.itens[0].modalidade
            resultado.append({
                'id': embarque.id,
                'numero': embarque.numero,
                'status': embarque.status,
                'data_prevista_embarque': embarque.data_prevista_embarque.isoformat() if embarque.data_prevista_embarque else None,
                'tipo_carga': embarque.tipo_carga,
                'modalidade': modalidade,
                'transportadora': embarque.transportadora.razao_social if embarque.transportadora else None,
                'total_fretes': len(embarque.fretes) if embarque.fretes else 0,
                'valor_total': embarque.valor_total,
                'pallet_total': embarque.pallet_total,
                'peso_total': embarque.peso_total
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.nome,
            'timestamp': agora_utc_naive().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
       }), 500

# ==========================================
# DASHBOARD APIs (novos — alimentam dashboard principal)
# ==========================================

@main_bp.route('/api/dashboard/kpis')
@login_required
def api_dashboard_kpis():
    """6 KPIs do dashboard com variacao percentual vs periodo anterior."""
    try:
        hoje = date.today()
        inicio_7d = hoje - timedelta(days=7)
        inicio_14d = hoje - timedelta(days=14)

        # --- 1. Faturamento 7d ---
        fat_filtro = [
            FaturamentoProduto.status_nf == 'Lançado',
            FaturamentoProduto.revertida == False,  # noqa: E712
        ]
        fat_atual = db.session.query(
            func.coalesce(func.sum(FaturamentoProduto.valor_produto_faturado), 0)
        ).filter(*fat_filtro, FaturamentoProduto.data_fatura >= inicio_7d).scalar()

        fat_anterior = db.session.query(
            func.coalesce(func.sum(FaturamentoProduto.valor_produto_faturado), 0)
        ).filter(
            *fat_filtro,
            FaturamentoProduto.data_fatura >= inicio_14d,
            FaturamentoProduto.data_fatura < inicio_7d
        ).scalar()

        # --- 2. Embarcado 7d ---
        emb_atual = db.session.query(
            func.coalesce(func.sum(Embarque.valor_total), 0)
        ).filter(
            Embarque.status == 'ativo',
            Embarque.data_embarque >= inicio_7d
        ).scalar()

        emb_anterior = db.session.query(
            func.coalesce(func.sum(Embarque.valor_total), 0)
        ).filter(
            Embarque.status == 'ativo',
            Embarque.data_embarque >= inicio_14d,
            Embarque.data_embarque < inicio_7d
        ).scalar()

        # --- 3. Carteira Ativa (valor total) ---
        # Filtro ativo=True necessario para excluir registros inativos
        carteira_valor = db.session.query(
            func.coalesce(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido),
                0
            )
        ).filter(
            CarteiraPrincipal.status_pedido == 'Pedido de venda',
            CarteiraPrincipal.ativo == True,  # noqa: E712
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar()

        # Standby (pedidos pausados — deduzir da carteira ativa)
        carteira_standby = db.session.query(
            func.coalesce(func.sum(SaldoStandby.valor_saldo), 0)
        ).filter(
            SaldoStandby.status_standby == 'ATIVO'
        ).scalar()

        # Cotacao (pedidos em status Cotacao)
        carteira_cotacao = db.session.query(
            func.coalesce(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido),
                0
            )
        ).filter(
            CarteiraPrincipal.status_pedido == 'Cotação',
            CarteiraPrincipal.ativo == True,  # noqa: E712
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar()

        # --- 4. Entregas Pendentes (apenas atrasadas ou sem data prevista) ---
        from sqlalchemy import or_
        entregas_pendentes = EntregaMonitorada.query.filter(
            EntregaMonitorada.entregue == False,  # noqa: E712
            or_(
                EntregaMonitorada.data_entrega_prevista < hoje,
                EntregaMonitorada.data_entrega_prevista == None  # noqa: E711
            )
        ).count()

        # --- 5. Producao Programada Hoje ---
        prod_atual = db.session.query(
            func.coalesce(func.sum(ProgramacaoProducao.qtd_programada), 0)
        ).filter(
            ProgramacaoProducao.data_programacao == hoje
        ).scalar()

        ontem_util = _ultimo_dia_util(hoje)
        prod_anterior = db.session.query(
            func.coalesce(func.sum(ProgramacaoProducao.qtd_programada), 0)
        ).filter(
            ProgramacaoProducao.data_programacao == ontem_util
        ).scalar()

        # --- 6. Compras Recebidas 7d (valor) ---
        compras_valor = db.session.query(
            func.coalesce(
                func.sum(PedidoCompras.qtd_recebida * PedidoCompras.preco_produto_pedido),
                0
            )
        ).filter(
            PedidoCompras.qtd_recebida > 0,
            PedidoCompras.atualizado_em >= inicio_7d
        ).scalar()

        compras_valor_ant = db.session.query(
            func.coalesce(
                func.sum(PedidoCompras.qtd_recebida * PedidoCompras.preco_produto_pedido),
                0
            )
        ).filter(
            PedidoCompras.qtd_recebida > 0,
            PedidoCompras.atualizado_em >= inicio_14d,
            PedidoCompras.atualizado_em < inicio_7d
        ).scalar()

        def variacao(atual, anterior):
            if not anterior or float(anterior) == 0:
                return None
            return round((float(atual) - float(anterior)) / float(anterior) * 100, 1)

        return jsonify({
            'success': True,
            'data': {
                'faturamento_7d': {
                    'valor': float(fat_atual),
                    'variacao_pct': variacao(fat_atual, fat_anterior)
                },
                'embarcado_7d': {
                    'valor': float(emb_atual),
                    'variacao_pct': variacao(emb_atual, emb_anterior)
                },
                'carteira_ativa': {
                    'valor': float(carteira_valor) - float(carteira_standby),
                    'standby': float(carteira_standby),
                    'cotacao': float(carteira_cotacao),
                    'variacao_pct': None
                },
                'entregas_pendentes': {
                    'valor': entregas_pendentes,
                    'variacao_pct': None
                },
                'producao_ultimo_dia': {
                    'valor': float(prod_atual),
                    'data_ref': hoje.isoformat(),
                    'variacao_pct': variacao(prod_atual, prod_anterior)
                },
                'compras_recebidas': {
                    'valor': float(compras_valor),
                    'variacao_pct': variacao(compras_valor, compras_valor_ant)
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/faturamento-diario')
@login_required
def api_dashboard_faturamento_diario():
    """Faturamento por dia nos ultimos 7 dias (para bar chart). Inclui hoje."""
    try:
        hoje = date.today()
        inicio = hoje - timedelta(days=6)  # 6 dias atras + hoje = 7 barras

        resultados = db.session.query(
            FaturamentoProduto.data_fatura,
            func.sum(FaturamentoProduto.valor_produto_faturado)
        ).filter(
            FaturamentoProduto.data_fatura >= inicio,
            FaturamentoProduto.status_nf == 'Lançado',
            FaturamentoProduto.revertida == False  # noqa: E712
        ).group_by(
            FaturamentoProduto.data_fatura
        ).order_by(
            FaturamentoProduto.data_fatura
        ).all()

        # Mapear resultados por data
        dados_por_dia = {r[0]: float(r[1]) for r in resultados}

        # Preencher todos os 7 dias (incluindo zeros)
        labels = []
        values = []
        for i in range(7):
            d = inicio + timedelta(days=i)
            labels.append(d.strftime('%d/%m'))
            values.append(dados_por_dia.get(d, 0))

        return jsonify({
            'success': True,
            'data': {'labels': labels, 'values': values}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/top-produtos')
@login_required
def api_dashboard_top_produtos():
    """Top 5 produtos por quantidade faturada nos ultimos 7 dias."""
    try:
        hoje = date.today()
        inicio_7d = hoje - timedelta(days=7)

        resultados = db.session.query(
            FaturamentoProduto.cod_produto,
            FaturamentoProduto.nome_produto,
            func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_total')
        ).filter(
            FaturamentoProduto.data_fatura >= inicio_7d,
            FaturamentoProduto.status_nf == 'Lançado',
            FaturamentoProduto.revertida == False  # noqa: E712
        ).group_by(
            FaturamentoProduto.cod_produto,
            FaturamentoProduto.nome_produto
        ).order_by(
            func.sum(FaturamentoProduto.qtd_produto_faturado).desc()
        ).limit(5).all()

        return jsonify({
            'success': True,
            'data': [{
                'cod_produto': r.cod_produto,
                'nome_produto': r.nome_produto,
                'qtd_total': float(r.qtd_total)
            } for r in resultados]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/ultimas-compras')
@login_required
def api_dashboard_ultimas_compras():
    """Ultimas compras recebidas com produtos (painel rotativo)."""
    try:
        compras = PedidoCompras.query.filter(
            PedidoCompras.qtd_recebida > 0
        ).order_by(
            PedidoCompras.atualizado_em.desc()
        ).limit(10).all()

        return jsonify({
            'success': True,
            'data': [{
                'num_pedido': c.num_pedido,
                'fornecedor': c.raz_social or 'N/A',
                'cod_produto': c.cod_produto,
                'nome_produto': c.nome_produto or 'N/A',
                'qtd_pedida': float(c.qtd_produto_pedido) if c.qtd_produto_pedido else 0,
                'qtd_recebida': float(c.qtd_recebida) if c.qtd_recebida else 0,
                'preco': float(c.preco_produto_pedido) if c.preco_produto_pedido else 0,
                'data_entrega': c.data_pedido_entrega.strftime('%d/%m/%Y') if c.data_pedido_entrega else '-'
            } for c in compras]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/producao-ultimo-dia')
@login_required
def api_dashboard_producao_ultimo_dia():
    """Producao programada para hoje (painel rotativo)."""
    try:
        hoje = date.today()

        producao = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.data_programacao == hoje
        ).order_by(
            ProgramacaoProducao.linha_producao,
            ProgramacaoProducao.cod_produto
        ).all()

        return jsonify({
            'success': True,
            'data_referencia': hoje.strftime('%d/%m/%Y'),
            'data': [{
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_programada': float(p.qtd_programada) if p.qtd_programada else 0,
                'linha_producao': p.linha_producao or '-',
                'cliente': p.cliente_produto or '-'
            } for p in producao]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/embarques-recentes')
@login_required
def api_dashboard_embarques_recentes():
    """Embarques ativos — tipo=embarcados (com data) ou tipo=pendentes (sem data)."""
    try:
        tipo = request.args.get('tipo', 'embarcados')

        query = Embarque.query.options(
            joinedload(Embarque.transportadora)
        ).filter(Embarque.status == 'ativo')

        if tipo == 'pendentes':
            query = query.filter(Embarque.data_embarque == None)  # noqa: E711
        else:
            query = query.filter(Embarque.data_embarque != None)  # noqa: E711

        embarques = query.order_by(Embarque.id.desc()).limit(10).all()

        return jsonify({
            'success': True,
            'tipo': tipo,
            'data': [{
                'id': e.id,
                'numero': e.numero,
                'status': e.status,
                'transportadora': e.transportadora.razao_social if e.transportadora else 'N/A',
                'data_embarque': e.data_embarque.strftime('%d/%m/%Y') if e.data_embarque else '-',
                'tipo_carga': e.tipo_carga or '-',
                'valor_total': float(e.valor_total) if e.valor_total else 0,
                'peso_total': float(e.peso_total) if e.peso_total else 0,
                'pallet_total': float(e.pallet_total) if e.pallet_total else 0,
                'total_fretes': len(e.fretes) if e.fretes else 0
            } for e in embarques]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/dashboard/separacoes-programadas')
@login_required
def api_dashboard_separacoes_programadas():
    """Separacoes futuras agrupadas por pedido (painel rotativo)."""
    try:
        hoje = date.today()

        # Agrupar por pedido: total itens, valor, peso
        resultados = db.session.query(
            Separacao.num_pedido,
            func.min(Separacao.raz_social_red).label('cliente'),
            func.min(Separacao.nome_cidade).label('cidade'),
            func.min(Separacao.cod_uf).label('uf'),
            func.min(Separacao.expedicao).label('expedicao'),
            func.min(Separacao.rota).label('rota'),
            func.count(Separacao.id).label('total_itens'),
            func.coalesce(func.sum(Separacao.valor_saldo), 0).label('valor_total'),
            func.coalesce(func.sum(Separacao.peso), 0).label('peso_total')
        ).filter(
            Separacao.expedicao >= hoje,
            Separacao.sincronizado_nf == False  # noqa: E712
        ).group_by(
            Separacao.num_pedido
        ).order_by(
            func.min(Separacao.expedicao).asc(),
            func.min(Separacao.raz_social_red).asc()
        ).limit(15).all()

        return jsonify({
            'success': True,
            'data': [{
                'num_pedido': r.num_pedido,
                'cliente': r.cliente or 'N/A',
                'cidade': f"{r.cidade}/{r.uf}" if r.cidade else (r.uf or '-'),
                'total_itens': r.total_itens,
                'valor_total': float(r.valor_total),
                'peso_total': float(r.peso_total),
                'expedicao': r.expedicao.strftime('%d/%m/%Y') if r.expedicao else '-',
                'rota': r.rota or '-'
            } for r in resultados]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================================
# INTEGRAÇÃO ODOO
# ==========================================

@main_bp.route('/odoo-integration')
@login_required
def odoo_integration():
    """Página de integração com Odoo"""
    return render_template('main/odoo_integration.html')

@main_bp.route('/api/odoo/test', methods=['GET'])
@login_required
def test_odoo_connection():
    """Testar conexão com Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        integration = get_odoo_integration()
        result = integration.test_connection()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao testar conexão Odoo: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro ao conectar com Odoo: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-customers', methods=['POST'])
@login_required
def sync_customers():
    """Sincronizar clientes do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        limit = request.json.get('limit', 10) if request.json else 10
        
        integration = get_odoo_integration()
        result = integration.sync_customers_to_system(limit=limit)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar clientes: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-products', methods=['POST'])
@login_required
def sync_products():
    """Sincronizar produtos do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        limit = request.json.get('limit', 10) if request.json else 10
        
        integration = get_odoo_integration()
        result = integration.sync_products_to_system(limit=limit)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar produtos: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-orders', methods=['POST'])
@login_required
def sync_orders():
    """Sincronizar pedidos do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        data = request.json if request.json else {}
        limit = data.get('limit', 10)
        days_back = data.get('days_back', 7)
        
        integration = get_odoo_integration()
        result = integration.sync_orders_to_system(limit=limit, days_back=days_back)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar pedidos: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500
