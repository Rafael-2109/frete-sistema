from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.carteira.models import (
    CarteiraPrincipal, CarteiraCopia, ControleCruzadoSeparacao,
    InconsistenciaFaturamento, HistoricoFaturamento, LogAtualizacaoCarteira
)
from app.estoque.models import SaldoEstoque
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from app.utils.auth_decorators import require_admin, require_operacional
from app.utils.timezone import agora_brasil
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
import pandas as pd
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# 📦 Blueprint da carteira (seguindo padrão dos outros módulos)
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')

@carteira_bp.route('/')
@login_required
def index():
    """Dashboard principal da carteira de pedidos com KPIs e visão geral"""
    try:
        # 📊 VERIFICAR SE TABELAS EXISTEM (FALLBACK PARA DEPLOY)
        if not db.engine.has_table('carteira_principal'):
            return render_template('carteira/dashboard.html',
                                 total_pedidos=0,
                                 total_produtos=0,
                                 total_itens=0,
                                 valor_total_carteira=0,
                                 status_breakdown=[],
                                 controles_pendentes=0,
                                 inconsistencias_abertas=0,
                                 expedicoes_proximas=0,
                                 vendedores_breakdown=[])
        
        # 📊 ESTATÍSTICAS PRINCIPAIS
        total_pedidos = db.session.query(CarteiraPrincipal.num_pedido).distinct().count()
        total_produtos = db.session.query(CarteiraPrincipal.cod_produto).distinct().count()
        total_itens = CarteiraPrincipal.query.filter_by(ativo=True).count()
        
        # 💰 VALORES TOTAIS
        valor_total_carteira = db.session.query(func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido
        )).scalar() or 0
        
        # 🎯 STATUS BREAKDOWN
        status_breakdown = db.session.query(
            CarteiraPrincipal.status_pedido,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter_by(ativo=True).group_by(CarteiraPrincipal.status_pedido).all()
        
        # 🔄 CONTROLES CRUZADOS PENDENTES (com fallback)
        controles_pendentes = 0
        inconsistencias_abertas = 0
        if db.engine.has_table('controle_cruzado_separacao'):
            controles_pendentes = ControleCruzadoSeparacao.query.filter_by(resolvida=False).count()
        if db.engine.has_table('inconsistencia_faturamento'):
            inconsistencias_abertas = InconsistenciaFaturamento.query.filter_by(resolvida=False).count()
        
        # 📈 PEDIDOS COM EXPEDIÇÃO PRÓXIMA (7 dias)
        data_limite = date.today() + timedelta(days=7)
        expedicoes_proximas = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.expedicao <= data_limite,
            CarteiraPrincipal.expedicao >= date.today(),
            CarteiraPrincipal.ativo == True
        ).count()
        
        # 👥 BREAKDOWN POR VENDEDOR
        vendedores_breakdown = db.session.query(
            CarteiraPrincipal.vendedor,
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor')
        ).filter_by(ativo=True).group_by(CarteiraPrincipal.vendedor).limit(10).all()
        
        return render_template('carteira/dashboard.html',
                             total_pedidos=total_pedidos,
                             total_produtos=total_produtos,
                             total_itens=total_itens,
                             valor_total_carteira=valor_total_carteira,
                             status_breakdown=status_breakdown,
                             controles_pendentes=controles_pendentes,
                             inconsistencias_abertas=inconsistencias_abertas,
                             expedicoes_proximas=expedicoes_proximas,
                             vendedores_breakdown=vendedores_breakdown)
        
    except Exception as e:
        logger.error(f"Erro no dashboard da carteira: {str(e)}")
        flash('Erro ao carregar dashboard da carteira', 'error')
        return render_template('carteira/dashboard.html',
                             total_pedidos=0,
                             total_produtos=0,
                             total_itens=0,
                             valor_total_carteira=0,
                             status_breakdown=[],
                             controles_pendentes=0,
                             inconsistencias_abertas=0,
                             expedicoes_proximas=0,
                             vendedores_breakdown=[])

@carteira_bp.route('/principal')
@login_required
def listar_principal():
    """Lista a carteira principal com filtros e paginação"""
    try:
        if not db.engine.has_table('carteira_principal'):
            flash('Sistema de carteira ainda não foi inicializado', 'warning')
            return render_template('carteira/listar_principal.html', itens=None)
            
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # 🔍 FILTROS
        num_pedido = request.args.get('num_pedido', '').strip()
        cod_produto = request.args.get('cod_produto', '').strip()
        vendedor = request.args.get('vendedor', '').strip()
        status = request.args.get('status', '').strip()
        cliente = request.args.get('cliente', '').strip()
        
        # 📊 QUERY BASE
        query = CarteiraPrincipal.query.filter_by(ativo=True)
        
        # 🔎 APLICAR FILTROS
        if num_pedido:
            query = query.filter(CarteiraPrincipal.num_pedido.ilike(f'%{num_pedido}%'))
        if cod_produto:
            query = query.filter(CarteiraPrincipal.cod_produto.ilike(f'%{cod_produto}%'))
        if vendedor:
            query = query.filter(CarteiraPrincipal.vendedor.ilike(f'%{vendedor}%'))
        if status:
            query = query.filter(CarteiraPrincipal.status_pedido.ilike(f'%{status}%'))
        if cliente:
            query = query.filter(or_(
                CarteiraPrincipal.raz_social.ilike(f'%{cliente}%'),
                CarteiraPrincipal.raz_social_red.ilike(f'%{cliente}%')
            ))
        
        # 📈 ORDENAÇÃO E PAGINAÇÃO
        itens = query.order_by(
            CarteiraPrincipal.expedicao.asc().nullslast(),
            CarteiraPrincipal.num_pedido.asc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('carteira/listar_principal.html',
                             itens=itens,
                             num_pedido=num_pedido,
                             cod_produto=cod_produto,
                             vendedor=vendedor,
                             status=status,
                             cliente=cliente)
        
    except Exception as e:
        logger.error(f"Erro ao listar carteira principal: {str(e)}")
        flash('Erro ao carregar carteira principal', 'error')
        return redirect(url_for('carteira.index'))

@carteira_bp.route('/importar', methods=['GET', 'POST'])
@require_operacional
def importar_carteira():
    """Importa nova carteira principal com atualização inteligente"""
    if request.method == 'GET':
        return render_template('carteira/importar.html')
    
    try:
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        if not arquivo.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            flash('Arquivo deve ser Excel (.xlsx, .xls) ou CSV', 'error')
            return redirect(request.url)
        
        # 📖 LER ARQUIVO
        try:
            if arquivo.filename.lower().endswith('.csv'):
                df = pd.read_csv(arquivo.stream, encoding='utf-8')
            else:
                df = pd.read_excel(arquivo.stream)
        except Exception as e:
            flash(f'Erro ao ler arquivo: {str(e)}', 'error')
            return redirect(request.url)
        
        # ✅ VALIDAR COLUNAS OBRIGATÓRIAS
        colunas_obrigatorias = ['num_pedido', 'cod_produto', 'nome_produto', 'qtd_produto_pedido', 'cnpj_cpf']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltantes:
            flash(f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}', 'error')
            return redirect(request.url)
        
        # 🔄 PROCESSAR IMPORTAÇÃO
        resultado = _processar_importacao_carteira(df, current_user.nome)
        
        flash(f"""
        Importação concluída com sucesso!
        ✅ {resultado['criados']} itens criados
        🔄 {resultado['atualizados']} itens atualizados  
        ❌ {resultado['erros']} erros
        """, 'success')
        
        return redirect(url_for('carteira.listar_principal'))
        
    except Exception as e:
        logger.error(f"Erro na importação da carteira: {str(e)}")
        flash(f'Erro na importação: {str(e)}', 'error')
        return redirect(request.url)

@carteira_bp.route('/inconsistencias')
@require_operacional  
def listar_inconsistencias():
    """Lista e gerencia inconsistências de faturamento"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 25
        
        # 🔍 FILTROS
        tipo = request.args.get('tipo', '').strip()
        resolvida = request.args.get('resolvida', '')
        
        # 📊 QUERY
        query = InconsistenciaFaturamento.query
        
        if tipo:
            query = query.filter(InconsistenciaFaturamento.tipo == tipo)
        if resolvida:
            query = query.filter(InconsistenciaFaturamento.resolvida == (resolvida == 'true'))
        
        inconsistencias = query.order_by(
            InconsistenciaFaturamento.detectada_em.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 📈 ESTATÍSTICAS
        total_abertas = InconsistenciaFaturamento.query.filter_by(resolvida=False).count()
        tipos_count = db.session.query(
            InconsistenciaFaturamento.tipo,
            func.count(InconsistenciaFaturamento.id).label('count')
        ).filter_by(resolvida=False).group_by(InconsistenciaFaturamento.tipo).all()
        
        return render_template('carteira/inconsistencias.html',
                             inconsistencias=inconsistencias,
                             total_abertas=total_abertas,
                             tipos_count=tipos_count,
                             tipo=tipo,
                             resolvida=resolvida)
        
    except Exception as e:
        logger.error(f"Erro ao listar inconsistências: {str(e)}")
        flash('Erro ao carregar inconsistências', 'error')
        return redirect(url_for('carteira.index'))

@carteira_bp.route('/resolver-inconsistencia/<int:id>', methods=['POST'])
@require_operacional
def resolver_inconsistencia(id):
    """Resolve uma inconsistência específica"""
    try:
        inconsistencia = InconsistenciaFaturamento.query.get_or_404(id)
        
        acao = request.form.get('acao')
        observacao = request.form.get('observacao', '').strip()
        
        if not acao:
            flash('Ação é obrigatória', 'error')
            return redirect(url_for('carteira.listar_inconsistencias'))
        
        # 🔧 APLICAR RESOLUÇÃO
        inconsistencia.resolvida = True
        inconsistencia.acao_tomada = acao
        inconsistencia.observacao_resolucao = observacao
        inconsistencia.resolvida_em = agora_brasil()
        inconsistencia.resolvida_por = current_user.nome
        
        db.session.commit()
        
        flash('Inconsistência resolvida com sucesso', 'success')
        return redirect(url_for('carteira.listar_inconsistencias'))
        
    except Exception as e:
        logger.error(f"Erro ao resolver inconsistência {id}: {str(e)}")
        db.session.rollback()
        flash('Erro ao resolver inconsistência', 'error')
        return redirect(url_for('carteira.listar_inconsistencias'))

@carteira_bp.route('/gerar-separacao', methods=['GET', 'POST'])
@require_operacional
def gerar_separacao():
    """Interface para gerar separação (recorte) da carteira"""
    if request.method == 'GET':
        return render_template('carteira/gerar_separacao.html')
    
    try:
        # 📋 RECEBER DADOS DO FORMULÁRIO
        itens_selecionados = request.form.getlist('itens_selecionados')
        observacao = request.form.get('observacao', '').strip()
        
        if not itens_selecionados:
            flash('Selecione pelo menos um item para gerar separação', 'error')
            return redirect(request.url)
        
        # 🔄 PROCESSAR GERAÇÃO
        resultado = _processar_geracao_separacao(itens_selecionados, current_user.nome, observacao)
        
        flash(f"""
        Separação gerada com sucesso!
        🆔 Lote: {resultado['lote_id']}
        📦 {resultado['itens_processados']} itens processados
        """, 'success')
        
        return redirect(url_for('separacao.listar'))
        
    except Exception as e:
        logger.error(f"Erro ao gerar separação: {str(e)}")
        flash(f'Erro ao gerar separação: {str(e)}', 'error')
        return redirect(request.url)

@carteira_bp.route('/api/item/<int:id>')
@login_required
def api_item_detalhes(id):
    """API para detalhes de um item da carteira"""
    try:
        item = CarteiraPrincipal.query.get_or_404(id)
        return jsonify(item.to_dict())
    except Exception as e:
        logger.error(f"Erro na API item {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@carteira_bp.route('/api/processar-faturamento', methods=['POST'])
@require_operacional
def api_processar_faturamento():
    """API para processar baixa automática do faturamento"""
    try:
        data = request.get_json()
        numero_nf = data.get('numero_nf')
        
        if not numero_nf:
            return jsonify({'error': 'Número da NF é obrigatório'}), 400
        
        # 🔄 PROCESSAR BAIXA DO FATURAMENTO
        resultado = _processar_baixa_faturamento(numero_nf, current_user.nome)
        
        return jsonify({
            'success': True,
            'itens_processados': resultado['itens_processados'],
            'inconsistencias_detectadas': resultado['inconsistencias'],
            'message': 'Faturamento processado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar faturamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

@carteira_bp.route('/baixar-modelo')
@login_required
def baixar_modelo():
    """Download do modelo Excel para importação da carteira"""
    try:
        # 📝 CRIAR MODELO COM EXEMPLOS REAIS
        modelo_data = {
            'num_pedido': ['PED001', 'PED001', 'PED002'],
            'cod_produto': ['PROD001', 'PROD002', 'PROD001'],
            'nome_produto': ['Produto Exemplo A', 'Produto Exemplo B', 'Produto Exemplo A'],
            'qtd_produto_pedido': [100, 50, 200],
            'qtd_saldo_produto_pedido': [100, 50, 200],
            'preco_produto_pedido': [15.50, 23.75, 15.50],
            'cnpj_cpf': ['12.345.678/0001-90', '12.345.678/0001-90', '98.765.432/0001-10'],
            'raz_social': ['Cliente Exemplo LTDA', 'Cliente Exemplo LTDA', 'Outro Cliente S.A.'],
            'raz_social_red': ['Cliente Exemplo', 'Cliente Exemplo', 'Outro Cliente'],
            'vendedor': ['João Silva', 'João Silva', 'Maria Santos'],
            'status_pedido': ['Pedido de venda', 'Pedido de venda', 'Cotação'],
            'municipio': ['São Paulo', 'São Paulo', 'Rio de Janeiro'],
            'estado': ['SP', 'SP', 'RJ'],
            'expedicao': ['15/03/2025', '20/03/2025', '25/03/2025'],
            'data_entrega': ['18/03/2025', '23/03/2025', '28/03/2025']
        }
        
        df = pd.DataFrame(modelo_data)
        
        # 📁 SALVAR TEMPORARIAMENTE
        temp_path = os.path.join('app', 'static', 'modelos', 'modelo_carteira_pedidos.xlsx')
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        df.to_excel(temp_path, index=False, sheet_name='Carteira')
        
        return send_file(temp_path, as_attachment=True, 
                        download_name='modelo_carteira_pedidos.xlsx')
        
    except Exception as e:
        logger.error(f"Erro ao gerar modelo: {str(e)}")
        flash('Erro ao gerar modelo', 'error')
        return redirect(url_for('carteira.index'))

# ========================================
# 🔧 FUNÇÕES AUXILIARES PRIVADAS
# ========================================

def _processar_importacao_carteira(df, usuario):
    """Processa importação com atualização inteligente"""
    criados = 0
    atualizados = 0
    erros = 0
    
    for _, row in df.iterrows():
        try:
            # 🔍 BUSCAR ITEM EXISTENTE
            item_existente = CarteiraPrincipal.query.filter_by(
                num_pedido=str(row['num_pedido']),
                cod_produto=str(row['cod_produto'])
            ).first()
            
            if item_existente:
                # 🔄 ATUALIZAR PRESERVANDO DADOS OPERACIONAIS
                _atualizar_item_preservando_operacional(item_existente, row, usuario)
                atualizados += 1
            else:
                # ✅ CRIAR NOVO ITEM
                _criar_novo_item_carteira(row, usuario)
                criados += 1
                
        except Exception as e:
            logger.error(f"Erro ao processar linha: {str(e)}")
            erros += 1
    
    db.session.commit()
    return {'criados': criados, 'atualizados': atualizados, 'erros': erros}

def _atualizar_item_preservando_operacional(item, row, usuario):
    """Atualiza item preservando dados operacionais (expedição, agendamento, etc)"""
    
    # 🛡️ PRESERVAR DADOS OPERACIONAIS
    expedicao_original = item.expedicao
    agendamento_original = item.agendamento
    protocolo_original = item.protocolo
    roteirizacao_original = item.roteirizacao
    lote_separacao_original = item.lote_separacao_id
    
    # 🔄 ATUALIZAR DADOS MESTRES
    item.pedido_cliente = row.get('pedido_cliente')
    item.data_pedido = pd.to_datetime(row.get('data_pedido')).date() if pd.notna(row.get('data_pedido')) else None
    item.cnpj_cpf = str(row['cnpj_cpf'])
    item.raz_social = row.get('raz_social')
    item.raz_social_red = row.get('raz_social_red')
    item.municipio = row.get('municipio')
    item.estado = row.get('estado')
    item.vendedor = row.get('vendedor')
    item.nome_produto = str(row['nome_produto'])
    item.qtd_produto_pedido = float(row['qtd_produto_pedido'])
    item.qtd_saldo_produto_pedido = float(row['qtd_saldo_produto_pedido'])
    item.preco_produto_pedido = float(row['preco_produto_pedido']) if pd.notna(row.get('preco_produto_pedido')) else None
    item.status_pedido = row.get('status_pedido')
    
    # 🛡️ RESTAURAR DADOS OPERACIONAIS
    item.expedicao = expedicao_original
    item.agendamento = agendamento_original  
    item.protocolo = protocolo_original
    item.roteirizacao = roteirizacao_original
    item.lote_separacao_id = lote_separacao_original
    
    item.updated_by = usuario
    item.updated_at = agora_brasil()

def _criar_novo_item_carteira(row, usuario):
    """Cria novo item na carteira"""
    
    item = CarteiraPrincipal(
        num_pedido=str(row['num_pedido']),
        cod_produto=str(row['cod_produto']),
        nome_produto=str(row['nome_produto']),
        qtd_produto_pedido=float(row['qtd_produto_pedido']),
        qtd_saldo_produto_pedido=float(row['qtd_saldo_produto_pedido']),
        preco_produto_pedido=float(row['preco_produto_pedido']) if pd.notna(row.get('preco_produto_pedido')) else None,
        cnpj_cpf=str(row['cnpj_cpf']),
        raz_social=row.get('raz_social'),
        raz_social_red=row.get('raz_social_red'),
        municipio=row.get('municipio'),
        estado=row.get('estado'),
        vendedor=row.get('vendedor'),
        status_pedido=row.get('status_pedido'),
        created_by=usuario,
        updated_by=usuario
    )
    
    db.session.add(item)

def _processar_baixa_faturamento(numero_nf, usuario):
    """Processa baixa automática do faturamento na carteira cópia"""
    # TODO: Implementar lógica de baixa automática
    # Esta função será chamada quando uma NF for criada/importada
    return {'itens_processados': 0, 'inconsistencias': 0}

def _processar_geracao_separacao(itens_selecionados, usuario, observacao):
    """Processa geração de separação baseada na carteira"""
    # TODO: Implementar lógica de geração de separação
    # Esta função criará lote_separacao_id e baixará da carteira
    return {'lote_id': 1, 'itens_processados': len(itens_selecionados)} 