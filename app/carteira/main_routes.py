from flask import Blueprint, render_template, flash
from flask_login import login_required
from app import db
from app.carteira.models import (
    CarteiraPrincipal, ControleCruzadoSeparacao,
    SaldoStandby
)
from sqlalchemy import func, inspect
from datetime import date, timedelta
import logging
from app.permissions.permissions import check_permission

logger = logging.getLogger(__name__)

# Blueprint da carteira (seguindo padrao dos outros modulos)
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')


@carteira_bp.route('/')
@login_required
@check_permission('carteira')
def index():
    """Dashboard principal da carteira de pedidos com KPIs e visao geral"""
    try:
        # VERIFICAR SE TABELAS EXISTEM (FALLBACK PARA DEPLOY)
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            estatisticas = {
                'total_pedidos': 0,
                'total_produtos': 0,
                'total_itens': 0,
                'valor_total': 0
            }

            return render_template('carteira/dashboard.html',
                                 estatisticas=estatisticas,
                                 status_breakdown=[],
                                 alertas_inconsistencias=0,
                                 alertas_vinculacao=0,
                                 alertas_pendentes_count=0,
                                 expedicoes_proximas=[],
                                 top_vendedores=[],
                                 standby_stats=[],
                                 total_standby_pedidos=0,
                                 total_standby_valor=0,
                                 sistema_inicializado=False)

        # ESTATISTICAS PRINCIPAIS
        # Filtrar apenas itens com saldo > 0 para consistencia com workspace
        total_pedidos = db.session.query(CarteiraPrincipal.num_pedido).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).distinct().count()

        total_produtos = db.session.query(CarteiraPrincipal.cod_produto).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).distinct().count()

        total_itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()

        # VALORES TOTAIS
        valor_total_carteira = db.session.query(func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
        )).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar() or 0

        # STATUS BREAKDOWN
        status_breakdown = db.session.query(
            CarteiraPrincipal.status_pedido,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(CarteiraPrincipal.status_pedido).all()

        # CONTROLES CRUZADOS PENDENTES (com fallback)
        controles_pendentes = 0
        inconsistencias_abertas = 0
        if inspector.has_table('controle_cruzado_separacao'):
            controles_pendentes = ControleCruzadoSeparacao.query.filter_by(resolvida=False).count()

        # PEDIDOS COM EXPEDICAO PROXIMA (7 dias)
        # Campo expedicao foi REMOVIDO de CarteiraPrincipal - usar data_pedido
        data_limite = date.today() + timedelta(days=7)
        expedicoes_proximas = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.data_pedido <= data_limite,
            CarteiraPrincipal.data_pedido >= date.today() - timedelta(days=30),
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()

        # BREAKDOWN POR VENDEDOR (ordenado por valor total decrescente)
        vendedores_breakdown = db.session.query(
            CarteiraPrincipal.vendedor,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(CarteiraPrincipal.vendedor).order_by(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).desc()
        ).limit(10).all()

        # ESTATISTICAS DE STANDBY
        standby_stats = []
        total_standby_pedidos = 0
        total_standby_valor = 0

        if inspector.has_table('saldo_standby'):
            standby_stats = db.session.query(
                SaldoStandby.status_standby,
                func.count(func.distinct(SaldoStandby.num_pedido)).label('qtd_pedidos'),
                func.sum(SaldoStandby.valor_saldo).label('valor_total')
            ).filter(
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).group_by(
                SaldoStandby.status_standby
            ).all()

            total_geral = db.session.query(
                func.count(func.distinct(SaldoStandby.num_pedido)).label('total_pedidos'),
                func.sum(SaldoStandby.valor_saldo).label('valor_total')
            ).filter(
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).first()

            if total_geral:
                total_standby_pedidos = total_geral.total_pedidos or 0
                total_standby_valor = float(total_geral.valor_total) if total_geral.valor_total else 0

        # CONTAGEM DE ALERTAS PENDENTES
        try:
            from app.carteira.models_alertas import AlertaSeparacaoCotada
            alertas_pendentes_count = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).count()
        except Exception as e:
            logger.error(f"Erro ao buscar alertas pendentes: {e}")
            alertas_pendentes_count = 0

        # ORGANIZAR DADOS PARA O TEMPLATE
        estatisticas = {
            'total_pedidos': total_pedidos,
            'total_produtos': total_produtos,
            'total_itens': total_itens,
            'valor_total': valor_total_carteira
        }

        return render_template('carteira/dashboard.html',
                             estatisticas=estatisticas,
                             status_breakdown=status_breakdown,
                             alertas_inconsistencias=inconsistencias_abertas,
                             alertas_vinculacao=controles_pendentes,
                             alertas_pendentes_count=alertas_pendentes_count,
                             expedicoes_proximas=[],
                             top_vendedores=vendedores_breakdown[:5] if vendedores_breakdown else [],
                             standby_stats=standby_stats,
                             total_standby_pedidos=total_standby_pedidos,
                             total_standby_valor=total_standby_valor,
                             sistema_inicializado=True)

    except Exception as e:
        logger.error(f"Erro no dashboard da carteira: {str(e)}")
        flash('Erro ao carregar dashboard da carteira', 'error')

        estatisticas = {
            'total_pedidos': 0,
            'total_produtos': 0,
            'total_itens': 0,
            'valor_total': 0
        }

        return render_template('carteira/dashboard.html',
                             estatisticas=estatisticas,
                             status_breakdown=[],
                             alertas_inconsistencias=0,
                             alertas_vinculacao=0,
                             alertas_pendentes_count=0,
                             expedicoes_proximas=[],
                             top_vendedores=[],
                             standby_stats=[],
                             total_standby_pedidos=0,
                             total_standby_valor=0,
                             sistema_inicializado=False)
