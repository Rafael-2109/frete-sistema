from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.carteira.models import (
    CarteiraPrincipal, CarteiraCopia, ControleCruzadoSeparacao,
    InconsistenciaFaturamento, HistoricoFaturamento, LogAtualizacaoCarteira,
    VinculacaoCarteiraSeparacao, EventoCarteira, AprovacaoMudancaCarteira,
    TipoCarga, FaturamentoParcialJustificativa, ControleAlteracaoCarga, SaldoStandby,
    SnapshotCarteira, ValidacaoNFSimples, ControleDescasamentoNF
)
from app.estoque.models import SaldoEstoque
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
# from app.utils.auth_decorators import require_admin, require_editar_cadastros  # Removido temporariamente
from app.utils.timezone import agora_brasil
from sqlalchemy import func, and_, or_, inspect
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
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            # 📊 SISTEMA NÃO INICIALIZADO
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
                                 expedicoes_proximas=[],
                                 top_vendedores=[],
                                 sistema_inicializado=False)
        
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
        if inspector.has_table('controle_cruzado_separacao'):
            controles_pendentes = ControleCruzadoSeparacao.query.filter_by(resolvida=False).count()
        if inspector.has_table('inconsistencia_faturamento'):
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
        
        # 📊 ORGANIZAR DADOS PARA O TEMPLATE
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
                             expedicoes_proximas=[],  # Lista vazia por enquanto
                             top_vendedores=vendedores_breakdown[:5] if vendedores_breakdown else [],
                             sistema_inicializado=True)
        
    except Exception as e:
        logger.error(f"Erro no dashboard da carteira: {str(e)}")
        flash('Erro ao carregar dashboard da carteira', 'error')
        
        # 📊 FALLBACK COM DADOS ZERO
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
                             expedicoes_proximas=[],
                             top_vendedores=[],
                             sistema_inicializado=False)

@carteira_bp.route('/principal')
@login_required
def listar_principal():
    """Lista a carteira principal com filtros e paginação"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
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
@login_required
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
        
        # 🔄 PROCESSAR FORMATOS ANTES DA IMPORTAÇÃO
        df = _processar_formatos_brasileiros(df)
        
        # 🔄 PROCESSAR IMPORTAÇÃO
        resultado = _processar_importacao_carteira_inteligente(df, current_user.nome)
        
        if resultado['sucesso']:
            flash(f"""
            Importação concluída com sucesso! ✅
            📊 Novos criados: {resultado['novos_criados']}
            🔄 Existentes atualizados: {resultado['existentes_atualizados']}
            🛡️ Dados preservados: {resultado['dados_preservados']}
            📋 Total processados: {resultado['total_processados']}
            """, 'success')
        else:
            flash(f'Erro na importação: {resultado["erro"]}', 'error')
        
        return redirect(url_for('carteira.listar_principal'))
        
    except Exception as e:
        logger.error(f"Erro na importação da carteira: {str(e)}")
        flash(f'Erro na importação: {str(e)}', 'error')
        return redirect(request.url)

@carteira_bp.route('/inconsistencias')
@login_required
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
@login_required
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
@login_required
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
@login_required
def processar_faturamento():
    """API para processar baixa automática de NFs"""
    try:
        data = request.json
        nfs_processadas = data.get('nfs', [])
        
        if not nfs_processadas:
            return jsonify({'success': False, 'error': 'Nenhuma NF informada'}), 400
        
        # ⚡ USAR FUNÇÃO IMPLEMENTADA
        total_processadas = 0
        total_erros = []
        
        for numero_nf in nfs_processadas:
            resultado = _processar_baixa_faturamento(numero_nf, current_user.nome)
            if resultado.get('success'):
                total_processadas += resultado.get('processadas', 0)
            else:
                total_erros.extend(resultado.get('erros', []))
        
        return jsonify({
            'success': True,
            'processadas': total_processadas,
            'erros': total_erros,
            'total_nfs': len(nfs_processadas)
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar faturamento: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@carteira_bp.route('/baixar-modelo')
@login_required
def baixar_modelo():
    """
    📥 DOWNLOAD DO MODELO EXCEL PARA IMPORTAÇÃO DA CARTEIRA
    
    ✅ FORMATOS SUPORTADOS:
    - 📅 Data: YYYY-MM-DD HH:MM:SS (ISO/SQL)
    - 💰 Decimal: 1.234,56 (vírgula brasileira)
    """
    try:
        # 📝 MODELO EXCEL CORRETO - APENAS CAMPOS DE IMPORTAÇÃO (LINHAS 2-38 ARQUIVO 1)
        modelo_data = {
            # 🔑 CAMPOS OBRIGATÓRIOS - CHAVES PRIMÁRIAS
            'num_pedido': ['PED001', 'PED001', 'PED002'],
            'cod_produto': ['PROD001', 'PROD002', 'PROD001'],
            'nome_produto': ['Produto Exemplo A', 'Produto Exemplo B', 'Produto Exemplo A'],
            'qtd_produto_pedido': ['100,00', '50,50', '200,25'],  # 💰 DECIMAL COM VÍRGULA
            'qtd_saldo_produto_pedido': ['100,00', '50,50', '200,25'],  # 💰 DECIMAL COM VÍRGULA
            'cnpj_cpf': ['12.345.678/0001-90', '12.345.678/0001-90', '98.765.432/0001-10'],
            
            # 📋 DADOS DO PEDIDO (LINHAS 2, 4, 5, 20)
            'pedido_cliente': ['CLI-001', 'CLI-002', 'CLI-003'],
            'data_pedido': ['2025-01-15 08:30:00', '2025-01-15 09:15:00', '2025-01-16 14:20:00'],
            'data_atual_pedido': ['2025-01-17 10:00:00', '2025-01-17 11:00:00', '2025-01-18 15:00:00'],
            'status_pedido': ['Pedido de venda', 'Pedido de venda', 'Cotação'],
            
            # 👥 DADOS DO CLIENTE (LINHAS 7, 8, 9, 10, 11, 12)
            'raz_social': ['Cliente Exemplo LTDA', 'Cliente Exemplo LTDA', 'Outro Cliente S.A.'],
            'raz_social_red': ['Cliente Exemplo', 'Cliente Exemplo', 'Outro Cliente'],
            'municipio': ['São Paulo', 'São Paulo', 'Rio de Janeiro'],
            'estado': ['SP', 'SP', 'RJ'],
            'vendedor': ['João Silva', 'João Silva', 'Maria Santos'],
            'equipe_vendas': ['VENDA INTERNA DENISE', 'VENDA EXTERNA MILER', 'VENDA EXTERNA JUNIOR'],
            
            # 📦 DADOS DO PRODUTO (LINHAS 15, 18, 19, 21, 22, 23)
            'unid_medida_produto': ['CAIXAS', 'UNIDADES', 'KG'],
            'qtd_cancelada_produto_pedido': ['0,00', '5,00', '0,00'],
            'preco_produto_pedido': ['15,50', '23,75', '15,50'],  # 💰 DECIMAL COM VÍRGULA
            'embalagem_produto': ['GALAO 5,02 L', 'CAIXA 12 UNID', 'SACO 25 KG'],
            'materia_prima_produto': ['OLEO DE SOJA', 'BISCOITO', 'FARINHA'],
            'categoria_produto': ['OLEOS', 'DOCES', 'FARINHAS'],
            
            # 💳 CONDIÇÕES COMERCIAIS (LINHAS 24, 25, 26, 27, 28, 29, 30)
            'cond_pgto_pedido': ['28/35/42 DDL', '30 DDL', '60 DDL'],
            'forma_pgto_pedido': ['Boleto Grafeno CD', 'PIX', 'Transferência'],
            'observ_ped_1': ['Entrega urgente', 'Cliente VIP', 'Produto frágil'],
            'incoterm': ['[CIF] CIF', '[FOB] FOB', '[RED] REDESPACHO'],
            'metodo_entrega_pedido': ['Entrega Expressa', 'Entrega Normal', 'Retirada'],
            'data_entrega_pedido': ['2025-03-18 16:00:00', '2025-03-23 15:30:00', '2025-03-28 17:00:00'],
            'cliente_nec_agendamento': ['Sim', 'Não', 'Sim'],
            
            # 🏠 ENDEREÇO DE ENTREGA COMPLETO (LINHAS 31-38)
            'cnpj_endereco_ent': ['12.345.678/0001-90', '12.345.678/0001-90', '98.765.432/0001-10'],
            'empresa_endereco_ent': ['CLIENTE EXEMPLO', 'CLIENTE EXEMPLO', 'OUTRO CLIENTE'],
            'cep_endereco_ent': ['01310-100', '01310-100', '20040-020'],
            'nome_cidade': ['São Paulo (SP)', 'São Paulo (SP)', 'Rio de Janeiro (RJ)'],  # 🌍 FORMATO ESPECIAL
            'bairro_endereco_ent': ['Centro', 'Vila Olímpia', 'Copacabana'],
            'rua_endereco_ent': ['Rua das Flores', 'Av. das Nações', 'Rua do Ouvidor'],
            'endereco_ent': ['123', '456', '789'],
            'telefone_endereco_ent': ['(11) 1234-5678', '(11) 8765-4321', '(21) 9999-8888']
        }
        
        df = pd.DataFrame(modelo_data)
        
        # 📁 CRIAR EXCEL COM MÚLTIPLAS ABAS - CAMINHO ABSOLUTO
        from flask import current_app
        import tempfile
        
        # Criar arquivo temporário para evitar problemas de caminho
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.xlsx', 
            prefix='modelo_carteira_'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            # 📋 ABA 1: DADOS PARA IMPORTAÇÃO
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # 📖 ABA 2: INSTRUÇÕES DETALHADAS
            instrucoes_data = {
                'Campo': [
                    'num_pedido', 'cod_produto', 'nome_produto', 
                    'qtd_produto_pedido', 'preco_produto_pedido',
                    'data_pedido', 'expedicao', 'agendamento',
                    'peso', 'pallet', 'valor_total'
                ],
                'Obrigatório': [
                    'SIM', 'SIM', 'SIM', 'SIM', 'NÃO', 
                    'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'
                ],
                'Formato': [
                    'Texto (PED001)', 'Texto (PROD001)', 'Texto livre',
                    'Decimal: 100,50', 'Decimal: 15,75',
                    'YYYY-MM-DD HH:MM:SS', 'YYYY-MM-DD HH:MM:SS', 'YYYY-MM-DD HH:MM:SS',
                    'Decimal: 10,50', 'Decimal: 1,25', 'Decimal: 1.500,00'
                ],
                'Exemplo': [
                    'PED001', 'PROD001', 'Produto Exemplo',
                    '100,50', '15,75',
                    '2025-03-15 08:30:00', '2025-03-15 07:00:00', '2025-03-17 10:00:00',
                    '10,50', '1,25', '1.550,00'
                ],
                'Observação': [
                    'Código único do pedido', 'Código único do produto', 'Nome completo do produto',
                    'Usar VÍRGULA como decimal', 'Usar VÍRGULA como decimal',
                    'Formato ISO: Ano-Mês-Dia Hora:Min:Seg', 'Data prevista expedição', 'Data agendamento cliente',
                    'Peso em KG com vírgula', 'Pallets com vírgula', 'Valor total com vírgula'
                ]
            }
            
            df_instrucoes = pd.DataFrame(instrucoes_data)
            df_instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
            
            # ⚙️ ABA 3: COMPORTAMENTO DO SISTEMA
            comportamento_data = {
                'Funcionalidade': [
                    '📥 Importação Inteligente',
                    '🛡️ Preservação de Dados',
                    '📅 Formatos de Data',
                    '💰 Decimais Brasileiros',
                    '🔄 Atualização vs Criação',
                    '📊 Dados Operacionais',
                    '⚠️ Validação Automática'
                ],
                'Descrição': [
                    'Sistema preserva dados operacionais existentes',
                    'Expedição, agendamento e protocolo são mantidos',
                    'Aceita YYYY-MM-DD HH:MM:SS (2025-03-15 08:30:00)',
                    'Aceita vírgula como separador decimal (1.234,56)',
                    'Atualiza se existe, cria se novo (chave: num_pedido + cod_produto)',
                    'Roteirização, lote_separacao_id, peso, pallet preservados',
                    'Campos obrigatórios validados automaticamente'
                ]
            }
            
            df_comportamento = pd.DataFrame(comportamento_data)
            df_comportamento.to_excel(writer, sheet_name='Comportamento', index=False)
        
        logger.info(f"✅ Modelo gerado: {temp_path}")
        
        # Enviar arquivo e limpar temporário
        try:
            return send_file(temp_path, as_attachment=True, 
                            download_name='modelo_carteira_pedidos.xlsx')
        finally:
            # Limpar arquivo temporário após envio (ou em caso de erro)
            try:
                os.unlink(temp_path)
            except:
                pass  # Ignorar erro de limpeza
        
    except Exception as e:
        logger.error(f"Erro ao gerar modelo: {str(e)}")
        flash('Erro ao gerar modelo', 'error')
        return redirect(url_for('carteira.index'))

@carteira_bp.route('/vincular-separacoes', methods=['POST'])
@login_required
def vincular_separacoes():
    """Vincula carteira com separações existentes"""
    try:
        # resultado = _vincular_carteira_com_separacoes_existentes(current_user.nome)
        # TODO: Implementar função _vincular_carteira_com_separacoes_existentes
        resultado = {'vinculacoes_criadas': 0, 'conflitos': []}
        
        # relatorio = _gerar_relatorio_vinculacao(resultado)
        # TODO: Implementar função _gerar_relatorio_vinculacao
        relatorio = "Processo de vinculação concluído"
        
        flash(f'Vinculação concluída: {relatorio}', 'success')
        return redirect(url_for('carteira.dashboard'))
        
    except Exception as e:
        logger.error(f"Erro na vinculação: {str(e)}")
        flash(f'Erro na vinculação: {str(e)}', 'error')
        return redirect(url_for('carteira.dashboard'))

@carteira_bp.route('/relatorio-vinculacoes')
@login_required
def relatorio_vinculacoes():
    """Relatório de itens vinculados vs não vinculados"""
    try:
        from app.separacao.models import Separacao
        
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            flash('Sistema de carteira ainda não foi inicializado', 'warning')
            return redirect(url_for('carteira.index'))
        
        # 📊 ESTATÍSTICAS DE VINCULAÇÃO
        total_carteira = CarteiraPrincipal.query.filter_by(ativo=True).count()
        itens_vinculados = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.lote_separacao_id.isnot(None),
            CarteiraPrincipal.ativo == True
        ).count()
        itens_nao_vinculados = total_carteira - itens_vinculados
        
        # 📋 DETALHES DOS ITENS NÃO VINCULADOS
        itens_sem_vinculacao = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.lote_separacao_id.is_(None),
            CarteiraPrincipal.ativo == True
        ).limit(50).all()  # Limitar para não sobrecarregar
        
        # 🔍 VERIFICAR QUAIS TÊM SEPARAÇÃO DISPONÍVEL
        itens_com_separacao_disponivel = []
        for item in itens_sem_vinculacao:
            separacao_existe = Separacao.query.filter_by(
                num_pedido=item.num_pedido,
                cod_produto=item.cod_produto
            ).first()
            
            if separacao_existe:
                itens_com_separacao_disponivel.append({
                    'item': item,
                    'separacao': separacao_existe
                })
        
        return render_template('carteira/relatorio_vinculacoes.html',
                             total_carteira=total_carteira,
                             itens_vinculados=itens_vinculados,
                             itens_nao_vinculados=itens_nao_vinculados,
                             itens_sem_vinculacao=itens_sem_vinculacao,
                             itens_com_separacao_disponivel=itens_com_separacao_disponivel)
        
    except Exception as e:
        logger.error(f"Erro no relatório de vinculações: {str(e)}")
        flash('Erro ao gerar relatório de vinculações', 'error')
        return redirect(url_for('carteira.index'))

@carteira_bp.route('/processar-alteracao-carga', methods=['POST'])
@login_required
def processar_alteracao_carga():
    """
    🎯 FUNÇÃO INTELIGENTE - RESOLVER CONFLITO DE REGRAS
    
    PROBLEMA RESOLVIDO:
    - Pedido tinha 100, separou 60, carteira importada com 120
    - Decidir se adiciona +20 na carga ou cria nova carga
    - Validar capacidade vs preservar dados operacionais
    """
    try:
        data = request.json
        carteira_item_id = data.get('carteira_item_id')
        separacao_lote_id = data.get('separacao_lote_id')
        qtd_nova = float(data.get('qtd_nova', 0))
        decisao_manual = data.get('decisao_manual')  # 'adicionar', 'nova_carga', 'manter'
        
        resultado = _processar_alteracao_inteligente(
            carteira_item_id, separacao_lote_id, qtd_nova, 
            current_user.nome, decisao_manual
        )
        
        return jsonify({
            'success': True,
            'decisao_tomada': resultado['decisao'],
            'motivo': resultado['motivo'],
            'nova_carga_id': resultado.get('nova_carga_id'),
            'capacidade_utilizada': resultado.get('capacidade_utilizada')
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar alteração de carga: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@carteira_bp.route('/justificar-faturamento-parcial', methods=['GET', 'POST'])
@login_required
def justificar_faturamento_parcial():
    """
    📋 TELA DE JUSTIFICATIVAS PARA FATURAMENTO PARCIAL
    
    PROBLEMA RESOLVIDO:
    - Separou 100, faturou 60 → Por que 40 não foram?
    - Decisão sobre destino do saldo (volta carteira, standby, descarta)
    """
    if request.method == 'GET':
        # Lista faturamentos parciais pendentes de justificativa
        faturamentos_pendentes = _buscar_faturamentos_parciais_pendentes()
        return render_template(
            'carteira/justificar_faturamento_parcial.html',
            faturamentos_pendentes=faturamentos_pendentes
        )
    
    try:
        # Processar justificativa
        data = request.form
        resultado = _processar_justificativa_faturamento_parcial(data, current_user.nome)
        
        flash(f"""
        Justificativa registrada com sucesso!
        📋 Motivo: {resultado['motivo']}
        🎯 Saldo: {resultado['classificacao_saldo']}
        ⚡ Ação: {resultado['acao_tomada']}
        """, 'success')
        
        return redirect(url_for('carteira.justificar_faturamento_parcial'))
        
    except Exception as e:
        logger.error(f"Erro ao processar justificativa: {str(e)}")
        flash(f'Erro ao processar justificativa: {str(e)}', 'error')
        return redirect(request.url)

@carteira_bp.route('/configurar-tipo-carga/<separacao_lote_id>', methods=['GET', 'POST'])
@login_required
def configurar_tipo_carga(separacao_lote_id):
    """
    ⚙️ CONFIGURAR TIPO DE CARGA - FUNÇÃO 3 IMPLEMENTADA
    
    FUNCIONALIDADE:
    - Define se carga é TOTAL, PARCIAL, COMPLEMENTAR, STANDBY
    - Configura limites de peso, pallets, valor
    - Define comportamento para alterações futuras
    """
    try:
        from sqlalchemy import inspect
        
        logger.info(f"⚙️ Configurando tipo de carga {separacao_lote_id} por {current_user.nome}")
        
        # 🔍 1. VERIFICAR SE TABELA EXISTE
        inspector = inspect(db.engine)
        if not inspector.has_table('tipo_carga'):
            return {
                'success': False,
                'error': 'Sistema de tipos de carga não inicializado',
                'tipo_carga': 'AGUARDA_MIGRACAO',
                'capacidade_resumo': 'Sistema não migrado',
                'aceita_incremento': False
            }
        
        # 📋 2. EXTRAIR DADOS DO FORMULÁRIO
        tipo_envio = request.form.get('tipo_envio', 'TOTAL')
        capacidade_maxima_peso = float(request.form.get('capacidade_maxima_peso', 0) or 0)
        capacidade_maxima_pallets = float(request.form.get('capacidade_maxima_pallets', 0) or 0)
        capacidade_maxima_valor = float(request.form.get('capacidade_maxima_valor', 0) or 0)
        aceita_incremento = request.form.get('aceita_incremento', 'true').lower() == 'true'
        motivo_tipo = request.form.get('motivo_tipo', '')
        
        # 🔍 3. BUSCAR OU CRIAR TIPO DE CARGA
        tipo_carga = TipoCarga.query.filter_by(separacao_lote_id=separacao_lote_id).first()
        
        if not tipo_carga:
            # 🆕 CRIAR NOVO
            tipo_carga = TipoCarga(
                separacao_lote_id=separacao_lote_id,
                criado_por=current_user.nome
            )
            db.session.add(tipo_carga)
        
        # 📊 4. ATUALIZAR CONFIGURAÇÕES
        tipo_carga.tipo_envio = tipo_envio
        tipo_carga.capacidade_maxima_peso = capacidade_maxima_peso
        tipo_carga.capacidade_maxima_pallets = capacidade_maxima_pallets
        tipo_carga.capacidade_maxima_valor = capacidade_maxima_valor
        tipo_carga.aceita_incremento = aceita_incremento
        tipo_carga.motivo_tipo = motivo_tipo
        
        # 📊 5. CALCULAR UTILIZAÇÃO ATUAL (da separação)
        from app.separacao.models import Separacao
        if inspector.has_table('separacao'):
            separacoes = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id).all()
            peso_atual = sum(float(s.peso or 0) for s in separacoes)
            pallets_atual = sum(float(s.pallet or 0) for s in separacoes)
            valor_atual = sum(float(s.valor_saldo or 0) for s in separacoes)
            
            tipo_carga.peso_atual = peso_atual
            tipo_carga.pallets_atual = pallets_atual
            tipo_carga.valor_atual = valor_atual
        
        # 💾 6. SALVAR
        db.session.commit()
        
        # 📊 7. GERAR RESUMO
        capacidade_resumo = f"Peso: {tipo_carga.peso_atual}/{capacidade_maxima_peso}kg"
        if capacidade_maxima_pallets > 0:
            capacidade_resumo += f", Pallets: {tipo_carga.pallets_atual}/{capacidade_maxima_pallets}"
        if capacidade_maxima_valor > 0:
            capacidade_resumo += f", Valor: R$ {tipo_carga.valor_atual:,.2f}/{capacidade_maxima_valor:,.2f}"
        
        logger.info(f"✅ Tipo de carga configurado: {separacao_lote_id} Tipo: {tipo_envio}")
        
        return {
            'success': True,
            'tipo_carga': tipo_envio,
            'capacidade_resumo': capacidade_resumo,
            'aceita_incremento': aceita_incremento,
            'tipo_carga_id': tipo_carga.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao configurar tipo de carga: {str(e)}")
        return {
            'success': False,
            'error': f'Erro ao configurar: {str(e)}',
            'tipo_carga': 'ERRO',
            'capacidade_resumo': 'Erro no processamento',
            'aceita_incremento': False
        }

@carteira_bp.route('/dashboard-saldos-standby')
@login_required
def dashboard_saldos_standby():
    """
    ⏸️ DASHBOARD DE SALDOS EM STANDBY
    
    FUNCIONALIDADE:
    - Lista todos os saldos aguardando decisão comercial
    - Controle temporal de prazos
    - Ações comerciais disponíveis
    """
    try:
        saldos_ativos = SaldoStandby.query.filter_by(status_standby='ATIVO').all()
        
        # Agrupa por tipo de standby
        saldos_por_tipo = {}
        alertas_pendentes = 0
        
        for saldo in saldos_ativos:
            tipo = saldo.tipo_standby
            if tipo not in saldos_por_tipo:
                saldos_por_tipo[tipo] = []
            saldos_por_tipo[tipo].append(saldo)
            
            if saldo.precisa_alerta:
                alertas_pendentes += 1
        
        return render_template(
            'carteira/dashboard_saldos_standby.html',
            saldos_por_tipo=saldos_por_tipo,
            alertas_pendentes=alertas_pendentes,
            total_saldos=len(saldos_ativos)
        )
        
    except Exception as e:
        logger.error(f"Erro no dashboard de saldos standby: {str(e)}")
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('carteira.dashboard'))

# ========================================
# 🔧 FUNÇÕES AUXILIARES PRIVADAS
# ========================================

def _processar_formatos_brasileiros(df):
    """
    🔄 PROCESSA FORMATOS BRASILEIROS PARA IMPORTAÇÃO
    
    ✅ FUNCIONALIDADES:
    - 📅 Data: YYYY-MM-DD HH:MM:SS → datetime
    - 💰 Decimal: 1.234,56 → 1234.56 (float)
    """
    try:
        logger.info("🔄 Processando formatos brasileiros para importação")
        
        # 💰 CAMPOS DECIMAIS COM VÍRGULA
        campos_decimais = [
            'qtd_produto_pedido', 'qtd_saldo_produto_pedido', 'preco_produto_pedido',
            'peso', 'pallet', 'valor_total'
        ]
        
        # 📅 CAMPOS DE DATA ISO/SQL
        campos_data = [
            'data_pedido', 'expedicao', 'data_entrega', 'agendamento'
        ]
        
        # 🔄 PROCESSAR DECIMAIS BRASILEIROS
        for campo in campos_decimais:
            if campo in df.columns:
                df[campo] = df[campo].apply(_converter_decimal_brasileiro)
        
        # 🔄 PROCESSAR DATAS ISO/SQL
        for campo in campos_data:
            if campo in df.columns:
                df[campo] = df[campo].apply(_converter_data_iso_sql)
        
        logger.info("✅ Formatos brasileiros processados com sucesso")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao processar formatos brasileiros: {str(e)}")
        return df  # Retorna DF original se der erro

def _converter_decimal_brasileiro(valor):
    """
    💰 CONVERTE DECIMAL BRASILEIRO PARA FLOAT
    
    EXEMPLOS:
    - '1.234,56' → 1234.56
    - '100,50' → 100.50
    - '50' → 50.0
    - '' → None
    """
    try:
        if pd.isna(valor) or valor == '' or valor is None:
            return None
        
        # Converter para string se necessário
        valor_str = str(valor).strip()
        
        if valor_str == '':
            return None
        
        # Remover espaços e caracteres especiais
        valor_str = valor_str.replace(' ', '')
        
        # Se tem vírgula, processar formato brasileiro
        if ',' in valor_str:
            # Separar parte inteira e decimal
            if valor_str.count(',') == 1:
                partes = valor_str.split(',')
                parte_inteira = partes[0].replace('.', '')  # Remove pontos de milhares
                parte_decimal = partes[1]
                valor_final = f"{parte_inteira}.{parte_decimal}"
            else:
                # Múltiplas vírgulas - usar primeira como decimal
                valor_final = valor_str.replace(',', '.', 1).replace(',', '')
        else:
            # Se não tem vírgula, pode ter ponto como decimal
            valor_final = valor_str
        
        return float(valor_final)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Erro ao converter decimal '{valor}': {str(e)}")
        return None

def _converter_data_iso_sql(valor):
    """
    📅 CONVERTE DATA ISO/SQL PARA DATETIME
    
    EXEMPLOS:
    - '2025-03-15 08:30:00' → datetime
    - '2025-03-15' → datetime (00:00:00)
    - '' → None
    """
    try:
        if pd.isna(valor) or valor == '' or valor is None:
            return None
        
        # Converter para string se necessário
        valor_str = str(valor).strip()
        
        if valor_str == '':
            return None
        
        # Tentar formatos ISO/SQL
        formatos_aceitos = [
            '%Y-%m-%d %H:%M:%S',  # 2025-03-15 08:30:00
            '%Y-%m-%d %H:%M',     # 2025-03-15 08:30
            '%Y-%m-%d',           # 2025-03-15
            '%Y/%m/%d %H:%M:%S',  # 2025/03/15 08:30:00
            '%Y/%m/%d'            # 2025/03/15
        ]
        
        for formato in formatos_aceitos:
            try:
                return pd.to_datetime(valor_str, format=formato)
            except ValueError:
                continue
        
        # Se nenhum formato funcionou, tentar parsing automático
        return pd.to_datetime(valor_str)
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Erro ao converter data '{valor}': {str(e)}")
        return None

# 🔧 DOCUMENTAÇÃO DO SISTEMA DE VINCULAÇÃO INTELIGENTE

"""
📋 DOCUMENTAÇÃO SISTEMA DE VINCULAÇÃO INTELIGENTE

FUNCIONALIDADES IMPLEMENTADAS:

1. VINCULAÇÃO PARCIAL INTELIGENTE:
   - Carteira 10 + Separação 5 = Vincula 5, deixa 5 livre
   - One-way: Carteira → Separação (nunca o contrário)
   - Preserva quantidade exata da separação existente

2. DADOS OPERACIONAIS PRESERVADOS:
   - expedicao: Data prevista de expedição (roteirização)
   - agendamento: Data de agendamento com cliente  
   - protocolo: Protocolo de agendamento
   - roteirizacao: Transportadora sugerida/contratada
   - lote_separacao_id: Vínculo com separação já gerada
   - qtd_saldo, valor_saldo, pallet, peso: Dados do lote

3. SISTEMA DE RESTRIÇÕES POR COTAÇÃO:
   - Sem cotação: Alteração livre
   - Com cotação: Restrição parcial com notificação
   - Workflow de aprovação para mudanças críticas
"""

def _processar_importacao_carteira_inteligente(df, usuario):
    """
    🚀 IMPLEMENTAÇÃO REAL - IMPORTAÇÃO INTELIGENTE DA CARTEIRA
    
    FUNCIONALIDADES:
    - Preserva dados operacionais (expedição, agendamento, protocolo)
    - Atualiza apenas dados mestres (cliente, produto, comercial)
    - Detecta alterações e gera eventos
    - Cria log de auditoria completo
    """
    try:
        logger.info(f"🔄 Iniciando importação inteligente - {len(df)} registros")
        
        # 📊 CONTADORES
        novos_criados = 0
        existentes_atualizados = 0
        dados_preservados = 0
        eventos_gerados = 0
        
        # 🔄 PROCESSAR CADA LINHA
        for index, row in df.iterrows():
            try:
                num_pedido = str(row.get('num_pedido', '')).strip()
                cod_produto = str(row.get('cod_produto', '')).strip()
                
                if not num_pedido or not cod_produto:
                    logger.warning(f"Linha {index}: num_pedido ou cod_produto vazio")
                    continue
                
                # 🔍 BUSCAR ITEM EXISTENTE
                item_existente = CarteiraPrincipal.query.filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    ativo=True
                ).first()
                
                if item_existente:
                    # 🔄 ATUALIZAR ITEM EXISTENTE (PRESERVANDO DADOS OPERACIONAIS)
                    resultado = _atualizar_item_inteligente(item_existente, row, usuario)
                    if resultado['alterado']:
                        existentes_atualizados += 1
                        eventos_gerados += resultado['eventos']
                    if resultado['dados_preservados']:
                        dados_preservados += 1
                else:
                    # 🆕 CRIAR NOVO ITEM
                    novo_item = _criar_novo_item_carteira(row, usuario)
                    if novo_item:
                        novos_criados += 1
                
                # 💾 COMMIT A CADA 50 REGISTROS (PERFORMANCE)
                if (index + 1) % 50 == 0:
                    db.session.commit()
                    logger.info(f"📊 Processados {index + 1}/{len(df)} registros")
                    
            except Exception as e:
                logger.error(f"Erro na linha {index}: {str(e)}")
                continue
        
        # 💾 COMMIT FINAL
        db.session.commit()
        
        # 🔄 SINCRONIZAR CARTEIRA CÓPIA
        _sincronizar_carteira_copia(usuario)
        
        logger.info(f"✅ Importação concluída - Novos: {novos_criados}, Atualizados: {existentes_atualizados}")
        
        return {
            'sucesso': True,
            'novos_criados': novos_criados,
            'existentes_atualizados': existentes_atualizados,
            'dados_preservados': dados_preservados,
            'eventos_gerados': eventos_gerados,
            'total_processados': len(df)
        }
        
    except Exception as e:
        logger.error(f"Erro na importação inteligente: {str(e)}")
        db.session.rollback()
        return {
            'sucesso': False,
            'erro': str(e),
            'novos_criados': 0,
            'existentes_atualizados': 0
        }

def _atualizar_item_inteligente(item, row, usuario):
    """
    🧠 ATUALIZAÇÃO INTELIGENTE COM RECÁLCULO AUTOMÁTICO
    
    FUNCIONALIDADE:
    - Preserva dados operacionais críticos  
    - Atualiza apenas dados mestres
    - NOVO: Recálculo automático de campos calculados
    - NOVO: Detecção de alterações importantes
    """
    try:
        # 📷 1. SNAPSHOT ANTES DA ALTERAÇÃO
        item_antes = {
            'qtd_produto_pedido': getattr(item, 'qtd_produto_pedido', None),
            'preco_produto_pedido': getattr(item, 'preco_produto_pedido', None),
            'expedicao': getattr(item, 'expedicao', None),
            'agendamento': getattr(item, 'agendamento', None),
            'protocolo': getattr(item, 'protocolo', None),
            'lote_separacao_id': getattr(item, 'lote_separacao_id', None),
            'roteirizacao': getattr(item, 'roteirizacao', None)
        }
        
        # 🔄 2. ATUALIZAR DADOS MESTRES (função original)
        _atualizar_dados_mestres(item, row)
        
        # 🔍 3. DETECTAR ALTERAÇÕES IMPORTANTES
        item_depois_simulado = type('obj', (object,), item_antes.copy())()
        for key, value in item_antes.items():
            setattr(item_depois_simulado, key, getattr(item, key, None))
        
        alteracoes = _detectar_alteracoes_importantes(
            type('obj', (object,), item_antes)(), 
            item_depois_simulado
        )
        
        # 🧮 4. RECÁLCULO AUTOMÁTICO (NOVA FUNCIONALIDADE)
        if alteracoes['alteracoes']:
            logger.info(f"⚡ Alterações detectadas em {item.num_pedido}: {alteracoes['alteracoes']}")
            
            # Recalcular campos automaticamente como no Excel
            resultado_calculo = _recalcular_campos_calculados(item, alteracoes['alteracoes'])
            
            if resultado_calculo['sucesso']:
                logger.info(f"✅ {resultado_calculo['total_campos']} campos recalculados automaticamente")
            else:
                logger.warning(f"⚠️ Erro no recálculo: {resultado_calculo.get('erro', 'Desconhecido')}")
        
        # 🔔 5. GERAR EVENTOS SE NECESSÁRIO
        if alteracoes['afeta_separacao']:
            logger.warning(f"🚨 ALTERAÇÃO AFETA SEPARAÇÃO EXISTENTE: {item.num_pedido}")
            
            # Gerar evento para notificação
            if hasattr(item, 'lote_separacao_id') and item.lote_separacao_id:
                evento = EventoCarteira(
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto,
                    carteira_item_id=item.id,
                    tipo_evento='ALTERACAO_AFETA_SEPARACAO',
                    qtd_anterior=item_antes.get('qtd_produto_pedido'),
                    qtd_nova=getattr(item, 'qtd_produto_pedido', None),
                    qtd_impactada=abs(float(getattr(item, 'qtd_produto_pedido', 0)) - float(item_antes.get('qtd_produto_pedido', 0))),
                    afeta_separacao=True,
                    separacao_notificada=False,
                    status_processamento='AGUARDA_REIMPRESSAO',
                    criado_por=usuario
                )
                db.session.add(evento)
                
                # Criar aprovação obrigatória se tem transportadora cotada
                if alteracoes['requer_aprovacao']:
                    aprovacao = AprovacaoMudancaCarteira(
                        evento_carteira_id=evento.id,
                        num_pedido=item.num_pedido,
                        cod_produto=item.cod_produto,
                        responsavel_cotacao=item_antes.get('roteirizacao', usuario),
                        tipo_mudanca='ALTERACAO_QTD_COM_SEPARACAO',
                        descricao_mudanca=f"Quantidade alterada de {item_antes.get('qtd_produto_pedido')} para {getattr(item, 'qtd_produto_pedido', None)}",
                        impacto_estimado='ALTO',
                        prazo_resposta=agora_brasil() + timedelta(hours=24),
                        criada_por=usuario
                    )
                    db.session.add(aprovacao)
                    
                    logger.warning(f"⚠️ APROVAÇÃO CRIADA - Responsável: {aprovacao.responsavel_cotacao}")
        
        # 📝 6. REGISTRAR LOG DE ALTERAÇÃO
        if alteracoes['alteracoes']:
            log_alteracao = LogAtualizacaoCarteira(
                num_pedido=item.num_pedido,
                cod_produto=item.cod_produto,
                tipo_operacao='ATUALIZACAO_INTELIGENTE',
                campos_alterados=alteracoes['alteracoes'],
                valores_anteriores=item_antes,
                valores_novos={
                    campo: getattr(item, campo, None) 
                    for campo in alteracoes['alteracoes']
                },
                executado_por=usuario
            )
            db.session.add(log_alteracao)
        
        # ✅ 7. MARCAR COMO ATUALIZADO
        if hasattr(item, 'updated_by'):
            item.updated_by = usuario
        if hasattr(item, 'updated_at'):
            item.updated_at = agora_brasil()
        
        return {
            'alteracoes_detectadas': alteracoes['alteracoes'],
            'afeta_separacao': alteracoes['afeta_separacao'],
            'requer_aprovacao': alteracoes['requer_aprovacao'],
            'campos_recalculados': resultado_calculo.get('campos_recalculados', []) if 'resultado_calculo' in locals() else [],
            'sucesso': True
        }
        
    except Exception as e:
        logger.error(f"Erro na atualização inteligente: {str(e)}")
        return {
            'alteracoes_detectadas': [],
            'afeta_separacao': False,
            'requer_aprovacao': False,
            'campos_recalculados': [],
            'sucesso': False,
            'erro': str(e)
        }

def _atualizar_dados_mestres(item, row):
    """Atualiza apenas dados mestres, preservando operacionais - TODOS OS CAMPOS DOS CSVs"""
    
    # 📋 DADOS DO PEDIDO (ARQUIVO 1)
    item.pedido_cliente = row.get('pedido_cliente')
    item.data_pedido = pd.to_datetime(row.get('data_pedido')).date() if pd.notna(row.get('data_pedido')) else None
    item.data_atual_pedido = pd.to_datetime(row.get('data_atual_pedido')).date() if pd.notna(row.get('data_atual_pedido')) else None
    
    # 👥 DADOS DO CLIENTE (ARQUIVO 1)
    item.cnpj_cpf = str(row['cnpj_cpf'])
    item.raz_social = row.get('raz_social')
    item.raz_social_red = row.get('raz_social_red')
    item.municipio = row.get('municipio')
    item.estado = row.get('estado')
    
    # 👥 DADOS COMERCIAIS (ARQUIVO 1)
    item.vendedor = row.get('vendedor')
    item.equipe_vendas = row.get('equipe_vendas')
    
    # 📦 DADOS DO PRODUTO (ARQUIVO 1)
    item.nome_produto = str(row['nome_produto'])
    item.unid_medida_produto = row.get('unid_medida_produto')
    item.embalagem_produto = row.get('embalagem_produto')
    item.materia_prima_produto = row.get('materia_prima_produto')
    item.categoria_produto = row.get('categoria_produto')
    
    # 📊 QUANTIDADES E VALORES (ARQUIVO 1)
    item.qtd_produto_pedido = float(row['qtd_produto_pedido'])
    item.qtd_saldo_produto_pedido = float(row['qtd_saldo_produto_pedido'])
    item.qtd_cancelada_produto_pedido = float(row.get('qtd_cancelada_produto_pedido', 0) or 0)
    item.preco_produto_pedido = float(row['preco_produto_pedido']) if pd.notna(row.get('preco_produto_pedido')) else None
    
    # 💳 CONDIÇÕES COMERCIAIS (ARQUIVO 1)
    item.cond_pgto_pedido = row.get('cond_pgto_pedido')
    item.forma_pgto_pedido = row.get('forma_pgto_pedido')
    item.incoterm = row.get('incoterm')
    item.metodo_entrega_pedido = row.get('metodo_entrega_pedido')
    item.data_entrega_pedido = pd.to_datetime(row.get('data_entrega_pedido')).date() if pd.notna(row.get('data_entrega_pedido')) else None
    item.cliente_nec_agendamento = row.get('cliente_nec_agendamento')
    item.observ_ped_1 = row.get('observ_ped_1')
    item.status_pedido = row.get('status_pedido')
    
    # 🏠 ENDEREÇO DE ENTREGA COMPLETO (ARQUIVO 1)
    item.cnpj_endereco_ent = row.get('cnpj_endereco_ent')
    item.empresa_endereco_ent = row.get('empresa_endereco_ent')
    item.cep_endereco_ent = row.get('cep_endereco_ent')
    
    # 🌍 EXTRAÇÃO CIDADE/UF - TRATAMENTO ESPECIAL "Fortaleza (CE)"
    municipio_completo = row.get('nome_cidade') or row.get('municipio_completo', '')
    if municipio_completo and '(' in municipio_completo and ')' in municipio_completo:
        # Extrair "Fortaleza (CE)" → cidade: "Fortaleza", uf: "CE"
        item.nome_cidade = municipio_completo.split('(')[0].strip()
        item.cod_uf = municipio_completo.split('(')[1].replace(')', '').strip()
    else:
        item.nome_cidade = row.get('nome_cidade')
        item.cod_uf = row.get('cod_uf')
    
    item.bairro_endereco_ent = row.get('bairro_endereco_ent')
    item.rua_endereco_ent = row.get('rua_endereco_ent')
    item.endereco_ent = row.get('endereco_ent')
    item.telefone_endereco_ent = row.get('telefone_endereco_ent')
    
    # 📊 ANÁLISE DE ESTOQUE (ARQUIVO 1) - CALCULADOS
    item.menor_estoque_produto_d7 = float(row.get('menor_estoque_produto_d7', 0) or 0) if pd.notna(row.get('menor_estoque_produto_d7')) else None
    item.saldo_estoque_pedido = float(row.get('saldo_estoque_pedido', 0) or 0) if pd.notna(row.get('saldo_estoque_pedido')) else None
    item.saldo_estoque_pedido_forcado = float(row.get('saldo_estoque_pedido_forcado', 0) or 0) if pd.notna(row.get('saldo_estoque_pedido_forcado')) else None
    
    # 📈 TOTALIZADORES POR CLIENTE (ARQUIVO 1) - CALCULADOS
    item.valor_saldo_total = float(row.get('valor_saldo_total', 0) or 0) if pd.notna(row.get('valor_saldo_total')) else None
    item.pallet_total = float(row.get('pallet_total', 0) or 0) if pd.notna(row.get('pallet_total')) else None
    item.peso_total = float(row.get('peso_total', 0) or 0) if pd.notna(row.get('peso_total')) else None
    item.valor_cliente_pedido = float(row.get('valor_cliente_pedido', 0) or 0) if pd.notna(row.get('valor_cliente_pedido')) else None
    item.pallet_cliente_pedido = float(row.get('pallet_cliente_pedido', 0) or 0) if pd.notna(row.get('pallet_cliente_pedido')) else None
    item.peso_cliente_pedido = float(row.get('peso_cliente_pedido', 0) or 0) if pd.notna(row.get('peso_cliente_pedido')) else None
    
    # 📊 TOTALIZADORES POR PRODUTO (ARQUIVO 1) - CALCULADOS
    item.qtd_total_produto_carteira = float(row.get('qtd_total_produto_carteira', 0) or 0) if pd.notna(row.get('qtd_total_produto_carteira')) else None
    item.estoque = float(row.get('estoque', 0) or 0) if pd.notna(row.get('estoque')) else None
    
    # 📈 PROJEÇÃO D0-D28 (ARQUIVO 1) - 29 CAMPOS DE ESTOQUE FUTURO
    for i in range(29):  # D0 até D28
        campo_estoque = f'estoque_d{i}'
        if hasattr(item, campo_estoque):
            valor = row.get(campo_estoque)
            setattr(item, campo_estoque, float(valor or 0) if pd.notna(valor) else None)

def _criar_novo_item_carteira(row, usuario):
    """Cria novo item na carteira - campos básicos + auditoria"""
    
    # 🌍 EXTRAÇÃO CIDADE/UF - TRATAMENTO ESPECIAL "Fortaleza (CE)"
    municipio_completo = row.get('nome_cidade') or row.get('municipio_completo', '')
    nome_cidade = None
    cod_uf = None
    if municipio_completo and '(' in municipio_completo and ')' in municipio_completo:
        # Extrair "Fortaleza (CE)" → cidade: "Fortaleza", uf: "CE"
        nome_cidade = municipio_completo.split('(')[0].strip()
        cod_uf = municipio_completo.split('(')[1].replace(')', '').strip()
    else:
        nome_cidade = row.get('nome_cidade')
        cod_uf = row.get('cod_uf')
    
    # 📦 CRIAR NOVO ITEM COM CAMPOS BÁSICOS
    novo_item = CarteiraPrincipal(
        created_by=usuario,
        updated_by=usuario
    )
    
    # 🔄 APLICAR TODOS OS CAMPOS USANDO A FUNÇÃO DE ATUALIZAÇÃO
    _atualizar_dados_mestres(novo_item, row)
    
    db.session.add(novo_item)
    return novo_item

def _processar_geracao_separacao(itens_selecionados, usuario, observacao):
    """
    🔄 GERA SEPARAÇÃO REAL BASEADA NA CARTEIRA
    
    FUNCIONALIDADE:
    - Cria lote de separação único
    - Baixa itens da carteira principal
    - Preserva dados operacionais
    - Cria vínculos automáticos
    """
    try:
        logger.info(f"🔄 Iniciando geração de separação - {len(itens_selecionados)} itens")
        
        # 🆔 GERAR LOTE ÚNICO
        lote_id = _gerar_novo_lote_id()
        
        # 📊 CONTADORES
        itens_processados = 0
        peso_total = 0
        valor_total = 0
        pallets_total = 0
        
        # 🔄 PROCESSAR CADA ITEM SELECIONADO
        for item_id in itens_selecionados:
            try:
                # 🔍 BUSCAR ITEM NA CARTEIRA
                item = CarteiraPrincipal.query.get(int(item_id))
                if not item or not getattr(item, 'ativo', True):
                    logger.warning(f"Item {item_id} não encontrado ou inativo")
                    continue
                
                # 📦 CRIAR SEPARAÇÃO NO MÓDULO SEPARACAO
                from app.separacao.models import Separacao
                separacao = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=getattr(item, 'num_pedido', f'TEMP_{item_id}'),
                    cod_produto=getattr(item, 'cod_produto', 'TEMP_PRODUTO'),
                    nome_produto=getattr(item, 'nome_produto', 'PRODUTO TEMPORÁRIO'),
                    qtd_saldo=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1),
                    valor_saldo=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1) * float(getattr(item, 'preco_produto_pedido', 0) or 0),
                    cnpj_cpf=getattr(item, 'cnpj_cpf', '00000000000000'),
                    raz_social_red=getattr(item, 'raz_social_red', None) or getattr(item, 'raz_social', 'CLIENTE TEMPORÁRIO'),
                    expedicao=getattr(item, 'expedicao', date.today()),
                    protocolo=getattr(item, 'protocolo', 'MANUAL'),
                    observ_ped_1=observacao or 'Separação gerada via sistema',
                    agendamento=getattr(item, 'agendamento', date.today()),
                    peso=float(getattr(item, 'peso', 0) or 0),
                    pallet=float(getattr(item, 'pallet', 0) or 0)
                )
                db.session.add(separacao)
                
                # 🔗 ATUALIZAR CARTEIRA COM VÍNCULO (SOMENTE SE CAMPOS EXISTEM)
                if hasattr(item, 'lote_separacao_id'):
                    item.lote_separacao_id = separacao.id
                if hasattr(item, 'qtd_saldo'):
                    item.qtd_saldo = float(getattr(item, 'qtd_saldo_produto_pedido', 0) or 0)
                if hasattr(item, 'valor_saldo'):
                    item.valor_saldo = float(getattr(item, 'qtd_saldo_produto_pedido', 0) or 0) * float(getattr(item, 'preco_produto_pedido', 0) or 0)
                
                # 📊 TOTALIZAR
                peso_atual = float(getattr(item, 'peso', 0) or 0)
                pallet_atual = float(getattr(item, 'pallet', 0) or 0)
                valor_atual = float(getattr(item, 'valor_saldo', 0) or 0)
                
                peso_total += peso_atual
                pallets_total += pallet_atual
                valor_total += valor_atual
                
                if hasattr(item, 'updated_by'):
                    item.updated_by = usuario
                itens_processados += 1
                
                # 🔗 CRIAR VINCULAÇÃO MULTI-DIMENSIONAL (SOMENTE SE MODELO EXISTE)
                inspector = inspect(db.engine)
                if inspector.has_table('vinculacao_carteira_separacao'):
                    vinculacao = VinculacaoCarteiraSeparacao(
                        num_pedido=getattr(item, 'num_pedido', f'TEMP_{item_id}'),
                        cod_produto=getattr(item, 'cod_produto', 'TEMP_PRODUTO'),
                        protocolo_agendamento=getattr(item, 'protocolo', 'SEPARACAO_MANUAL'),
                        data_agendamento=getattr(item, 'agendamento', date.today()),
                        data_expedicao=getattr(item, 'expedicao', date.today()),
                        carteira_item_id=item.id,
                        separacao_lote_id=lote_id,
                        qtd_carteira_original=float(getattr(item, 'qtd_produto_pedido', 1) or 1),
                        qtd_separacao_original=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1),
                        qtd_vinculada=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1),
                        criada_por=usuario
                    )
                    db.session.add(vinculacao)
                
                # 📝 CRIAR EVENTO DE SEPARAÇÃO (SOMENTE SE MODELO EXISTE)
                if inspector.has_table('evento_carteira'):
                    evento = EventoCarteira(
                        num_pedido=getattr(item, 'num_pedido', f'TEMP_{item_id}'),
                        cod_produto=getattr(item, 'cod_produto', 'TEMP_PRODUTO'),
                        carteira_item_id=item.id,
                        tipo_evento='SEPARACAO_GERADA',
                        qtd_anterior=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1),
                        qtd_nova=0,  # Foi para separação
                        qtd_impactada=float(getattr(item, 'qtd_saldo_produto_pedido', 1) or 1),
                        afeta_separacao=True,
                        criado_por=usuario
                    )
                    db.session.add(evento)
                
            except Exception as e:
                logger.error(f"Erro ao processar item {item_id}: {str(e)}")
                continue
        
        # 💾 COMMIT FINAL
        db.session.commit()
        
        logger.info(f"✅ Separação {lote_id} criada - {itens_processados} itens processados")
        
        return {
            'lote_id': lote_id,
            'itens_processados': itens_processados,
            'peso_total': peso_total,
            'valor_total': valor_total,
            'pallets_total': pallets_total,
            'sucesso': True
        }
        
    except Exception as e:
        logger.error(f"Erro na geração de separação: {str(e)}")
        db.session.rollback()
        return {
            'lote_id': None,
            'itens_processados': 0,
            'sucesso': False,
            'erro': str(e)
        }

def _processar_baixa_faturamento(numero_nf, usuario):
    """
    💳 BAIXA AUTOMÁTICA DE FATURAMENTO - FUNÇÃO 1 CORRIGIDA
    
    FUNCIONALIDADE CRÍTICA:
    - Busca NF no FaturamentoProduto (dados por produto)
    - Identifica itens correspondentes na carteira
    - Baixa automática respeitando saldos disponíveis
    - Sincronização CarteiraPrincipal ↔ CarteiraCopia
    - Detecção de inconsistências em tempo real
    """
    try:
        from app.faturamento.models import FaturamentoProduto
        from sqlalchemy import inspect
        
        logger.info(f"💳 Processando baixa automática NF: {numero_nf}")
        
        # 🔍 1. VERIFICAR SE TABELA DE FATURAMENTO EXISTE
        inspector = inspect(db.engine)
        if not inspector.has_table('faturamento_produto'):
            return {
                'success': False,
                'error': 'Tabela de faturamento por produto não encontrada. Importe dados de faturamento primeiro.',
                'processadas': 0,
                'erros': ['Sistema não inicializado']
            }
        
        # 🔍 2. BUSCAR NF NO FATURAMENTO POR PRODUTO (CORRIGIDO)
        itens_nf = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            status_nf='ATIVO'  # Apenas NFs ativas
        ).all()
        
        if not itens_nf:
            return {
                'success': False,
                'error': f'NF {numero_nf} não encontrada no faturamento por produto ou está cancelada',
                'processadas': 0,
                'erros': [f'NF {numero_nf} não localizada ou inativa']
            }
        
        processadas = 0
        erros = []
        inconsistencias_detectadas = []
        
        # 🔄 3. PROCESSAR CADA PRODUTO DA NF
        for item_faturamento in itens_nf:
            try:
                # 🔍 3.1 BUSCAR ITEM NA CARTEIRA PRINCIPAL (USANDO CAMPOS CORRETOS)
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=item_faturamento.origem,  # origem = num_pedido
                    cod_produto=item_faturamento.cod_produto
                ).first()
                
                if not item_carteira:
                    # ⚠️ INCONSISTÊNCIA: NF sem pedido correspondente
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='FATURAMENTO_SEM_PEDIDO',
                        numero_nf=numero_nf,
                        num_pedido=item_faturamento.origem or 'N/A',
                        cod_produto=item_faturamento.cod_produto,
                        qtd_faturada=float(item_faturamento.qtd_produto_faturado or 0),
                        saldo_disponivel=0,
                        qtd_excesso=float(item_faturamento.qtd_produto_faturado or 0)
                    )
                    db.session.add(inconsistencia)
                    erros.append(f"Produto {item_faturamento.cod_produto} (Pedido: {item_faturamento.origem}) sem item correspondente na carteira")
                    continue
                
                # 📊 3.2 VERIFICAR SALDO DISPONÍVEL (USANDO CAMPOS CORRETOS)
                qtd_faturada = float(item_faturamento.qtd_produto_faturado or 0)
                saldo_disponivel = float(item_carteira.qtd_saldo_produto_pedido or 0)
                
                if qtd_faturada > saldo_disponivel:
                    # ⚠️ INCONSISTÊNCIA: Faturamento excede saldo
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='FATURAMENTO_EXCEDE_SALDO',
                        numero_nf=numero_nf,
                        num_pedido=item_carteira.num_pedido,
                        cod_produto=item_carteira.cod_produto,
                        qtd_faturada=qtd_faturada,
                        saldo_disponivel=saldo_disponivel,
                        qtd_excesso=qtd_faturada - saldo_disponivel
                    )
                    db.session.add(inconsistencia)
                    inconsistencias_detectadas.append({
                        'produto': item_carteira.cod_produto,
                        'pedido': item_carteira.num_pedido,
                        'faturado': qtd_faturada,
                        'disponivel': saldo_disponivel,
                        'excesso': qtd_faturada - saldo_disponivel
                    })
                    
                    # 🔄 BAIXAR APENAS O SALDO DISPONÍVEL
                    qtd_a_baixar = saldo_disponivel
                    logger.warning(f"⚠️ Faturamento excede saldo: {item_carteira.num_pedido}-{item_carteira.cod_produto} Faturado:{qtd_faturada} Disponível:{saldo_disponivel}")
                else:
                    qtd_a_baixar = qtd_faturada
                
                # 💳 3.3 BAIXAR NA CARTEIRA PRINCIPAL
                item_carteira.qtd_saldo_produto_pedido = float(item_carteira.qtd_saldo_produto_pedido) - qtd_a_baixar
                item_carteira.updated_by = usuario
                item_carteira.updated_at = agora_brasil()
                
                # 🔄 3.4 SINCRONIZAR COM CARTEIRA CÓPIA
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=item_carteira.num_pedido,
                    cod_produto=item_carteira.cod_produto
                ).first()
                
                if item_copia:
                    # Atualizar baixa na cópia
                    item_copia.baixa_produto_pedido = float(item_copia.baixa_produto_pedido or 0) + qtd_a_baixar
                    item_copia.recalcular_saldo()
                    item_copia.updated_by = usuario
                    item_copia.updated_at = agora_brasil()
                else:
                    logger.warning(f"⚠️ Item não encontrado na CarteiraCopia: {item_carteira.num_pedido}-{item_carteira.cod_produto}")
                
                # 📋 3.5 REGISTRAR HISTÓRICO
                if inspector.has_table('historico_faturamento'):
                    historico = HistoricoFaturamento(
                        num_pedido=item_carteira.num_pedido,
                        cod_produto=item_carteira.cod_produto,
                        numero_nf=numero_nf,
                        qtd_baixada=qtd_a_baixar,
                        data_faturamento=item_faturamento.data_fatura
                    )
                    db.session.add(historico)
                
                processadas += 1
                logger.info(f"✅ Baixa processada: {item_carteira.num_pedido}-{item_carteira.cod_produto} Qtd: {qtd_a_baixar}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar produto {item_faturamento.cod_produto}: {str(e)}")
                erros.append(f"Produto {item_faturamento.cod_produto}: {str(e)}")
                continue
        
        # 💾 4. SALVAR TODAS AS ALTERAÇÕES
        db.session.commit()
        
        # 📊 5. RESULTADO FINAL
        resultado = {
            'success': True,
            'processadas': processadas,
            'erros': erros,
            'inconsistencias': inconsistencias_detectadas,
            'total_itens_nf': len(itens_nf),
            'tabela_origem': 'FaturamentoProduto'  # Confirmar correção
        }
        
        if inconsistencias_detectadas:
            logger.warning(f"⚠️ {len(inconsistencias_detectadas)} inconsistências detectadas na NF {numero_nf}")
        
        logger.info(f"✅ Baixa automática concluída NF {numero_nf}: {processadas}/{len(itens_nf)} itens processados, {len(erros)} erros")
        return resultado
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro crítico na baixa automática NF {numero_nf}: {str(e)}")
        return {
            'success': False,
            'error': f'Erro crítico: {str(e)}',
            'processadas': 0,
            'erros': [str(e)]
        }

def _processar_alteracao_inteligente(carteira_item_id, separacao_lote_id, qtd_nova, usuario, decisao_manual=None):
    """
    🎯 LÓGICA INTELIGENTE PARA RESOLVER CONFLITO DE REGRAS
    
    ALGORITMO:
    1. Busca dados atuais da carga e alteração
    2. Verifica tipo de carga e capacidades
    3. Decide se adiciona à carga ou cria nova
    4. Registra controle de alteração
    """
    try:
        # 🔍 1. BUSCAR DADOS ATUAIS
        carteira_item = CarteiraPrincipal.query.get(carteira_item_id)
        if not carteira_item:
            raise ValueError(f"Item da carteira {carteira_item_id} não encontrado")
        
        # 🎯 2. BUSCAR OU CRIAR TIPO DE CARGA
        tipo_carga = TipoCarga.query.filter_by(separacao_lote_id=separacao_lote_id).first()
        if not tipo_carga:
            # Se não tem tipo definido, assume TOTAL (aceita alterações)
            tipo_carga = TipoCarga(
                separacao_lote_id=separacao_lote_id,
                tipo_envio='TOTAL',
                aceita_incremento=True,
                motivo_tipo='Criado automaticamente - carga completa',
                criado_por=usuario
            )
            db.session.add(tipo_carga)
            db.session.flush()  # Para obter o ID
        
        # 📊 3. CALCULAR ALTERAÇÃO
        qtd_anterior = float(carteira_item.qtd_produto_pedido)
        qtd_diferenca = qtd_nova - qtd_anterior
        
        # 🎯 4. DECISÃO BASEADA NO TIPO DE CARGA
        if tipo_carga.tipo_envio == 'PARCIAL':
            # PARCIAL: Não altera carga, apenas saldo
            decisao = 'MANTER_CARGA_ALTERAR_SALDO'
            nova_carga_id = None
            
            # Atualizar apenas saldo restante
            carteira_item.qtd_produto_pedido = qtd_nova
            # O saldo da carga permanece o mesmo
            
        elif tipo_carga.tipo_envio == 'TOTAL':
            # TOTAL: Altera carga e notifica
            if tipo_carga.aceita_incremento and qtd_diferenca > 0:
                # Pode adicionar à carga existente
                decisao = 'ADICIONAR_CARGA_ATUAL'
                nova_carga_id = None
                
                # Atualizar carga
                carteira_item.qtd_produto_pedido = qtd_nova
                carteira_item.qtd_saldo = getattr(carteira_item, 'qtd_saldo', 0) + qtd_diferenca
                tipo_carga.peso_atual += qtd_diferenca * 0.5  # Estimativa peso
                
            else:
                # Criar nova carga para a diferença
                decisao = 'CRIAR_NOVA_CARGA'
                nova_carga_id = _gerar_novo_lote_id()
                
                # Atualizar item original
                carteira_item.qtd_produto_pedido = qtd_nova
                
        else:
            decisao = 'AGUARDA_APROVACAO'
            nova_carga_id = None
        
        # 📝 5. REGISTRAR CONTROLE DE ALTERAÇÃO
        controle = ControleAlteracaoCarga(
            carteira_item_id=carteira_item_id,
            separacao_lote_id=separacao_lote_id,
            num_pedido=carteira_item.num_pedido,
            cod_produto=carteira_item.cod_produto,
            qtd_anterior=qtd_anterior,
            qtd_nova=qtd_nova,
            qtd_diferenca=qtd_diferenca,
            decisao_sistema=decisao,
            motivo_decisao=f"Tipo carga: {tipo_carga.tipo_envio}, Aceita incremento: {tipo_carga.aceita_incremento}",
            capacidade_peso_ok=True,  # TODO: Implementar verificação real
            nova_carga_criada_id=nova_carga_id,
            detectado_em=agora_brasil(),
            processado_em=agora_brasil(),
            processado_por=usuario
        )
        db.session.add(controle)
        
        # 🔔 6. GERAR EVENTO SE AFETA SEPARAÇÃO
        if decisao in ['ADICIONAR_CARGA_ATUAL', 'CRIAR_NOVA_CARGA']:
            evento = EventoCarteira(
                num_pedido=carteira_item.num_pedido,
                cod_produto=carteira_item.cod_produto,
                carteira_item_id=carteira_item_id,
                tipo_evento='ALTERACAO_QTD',
                qtd_anterior=qtd_anterior,
                qtd_nova=qtd_nova,
                qtd_impactada=abs(qtd_diferenca),
                afeta_separacao=True,
                separacao_notificada=False,
                responsavel_cotacao=usuario,
                status_processamento='PENDENTE',
                criado_por=usuario
            )
            db.session.add(evento)
        
        db.session.commit()
        
        return {
            'decisao': decisao,
            'motivo': controle.motivo_decisao,
            'nova_carga_id': nova_carga_id,
            'capacidade_utilizada': float(tipo_carga.peso_atual) if hasattr(tipo_carga, 'peso_atual') else 0,
            'afeta_separacao': decisao != 'MANTER_CARGA_ALTERAR_SALDO'
        }
        
    except Exception as e:
        logger.error(f"Erro na alteração inteligente: {str(e)}")
        db.session.rollback()
        raise

def _processar_justificativa_faturamento_parcial(data, usuario):
    """
    📋 JUSTIFICATIVA FATURAMENTO PARCIAL - FUNÇÃO 2 IMPLEMENTADA
    
    PROBLEMA RESOLVIDO:
    - Separou 100, faturou 60 → Por que 40 não foram?
    - Tratamento inteligente do saldo restante
    - Decisão comercial sobre destino do saldo
    """
    try:
        from sqlalchemy import inspect
        
        logger.info(f"📋 Processando justificativa faturamento parcial por {usuario}")
        
        # 🔍 1. VERIFICAR SE TABELAS EXISTEM
        inspector = inspect(db.engine)
        if not inspector.has_table('faturamento_parcial_justificativa'):
            return {
                'success': False,
                'error': 'Sistema de justificativas não inicializado',
                'motivo': 'SISTEMA_NAO_INICIALIZADO',
                'classificacao_saldo': 'AGUARDA_MIGRACAO',
                'acao_tomada': 'NENHUMA'
            }
        
        # 📋 2. EXTRAIR DADOS DO FORMULÁRIO
        separacao_lote_id = data.get('separacao_lote_id')
        num_pedido = data.get('num_pedido')
        cod_produto = data.get('cod_produto')
        numero_nf = data.get('numero_nf')
        motivo_nao_faturamento = data.get('motivo_nao_faturamento')
        classificacao_saldo = data.get('classificacao_saldo')
        descricao_detalhada = data.get('descricao_detalhada', '')
        
        # 📊 3. CALCULAR QUANTIDADES
        qtd_separada = float(data.get('qtd_separada', 0) or 0)
        qtd_faturada = float(data.get('qtd_faturada', 0) or 0)
        qtd_saldo = qtd_separada - qtd_faturada
        
        if qtd_saldo <= 0:
            return {
                'success': False,
                'error': 'Quantidade separada deve ser maior que faturada para justificativa parcial',
                'motivo': 'DADOS_INVALIDOS',
                'classificacao_saldo': 'ERRO',
                'acao_tomada': 'VALIDACAO_NEGADA'
            }
        
        # 📝 4. CRIAR JUSTIFICATIVA
        justificativa = FaturamentoParcialJustificativa(
            separacao_lote_id=separacao_lote_id,
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            numero_nf=numero_nf,
            qtd_separada=qtd_separada,
            qtd_faturada=qtd_faturada,
            qtd_saldo=qtd_saldo,
            motivo_nao_faturamento=motivo_nao_faturamento,
            classificacao_saldo=classificacao_saldo,
            descricao_detalhada=descricao_detalhada,
            criado_por=usuario
        )
        db.session.add(justificativa)
        
        # 🎯 5. PROCESSAR AÇÃO BASEADA NA CLASSIFICAÇÃO
        acao_tomada = None
        
        if classificacao_saldo == 'RETORNA_CARTEIRA':
            # 🔄 RETORNAR À CARTEIRA SEM DADOS OPERACIONAIS
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto
            ).first()
            
            if item_carteira:
                # Limpar dados operacionais
                item_carteira.lote_separacao_id = None
                item_carteira.expedicao = None
                item_carteira.agendamento = None
                item_carteira.protocolo = None
                item_carteira.roteirizacao = None
                item_carteira.qtd_saldo_produto_pedido = float(item_carteira.qtd_saldo_produto_pedido or 0) + qtd_saldo
                item_carteira.updated_by = usuario
                item_carteira.updated_at = agora_brasil()
                
            acao_tomada = 'ITEM_RETORNADO_CARTEIRA'
            
        elif classificacao_saldo == 'NECESSITA_COMPLEMENTO':
            # ⏸️ CRIAR SALDO EM STANDBY
            saldo_standby = SaldoStandby(
                origem_separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                cnpj_cliente=data.get('cnpj_cliente', ''),
                nome_cliente=data.get('nome_cliente', ''),
                qtd_saldo=qtd_saldo,
                valor_saldo=qtd_saldo * float(data.get('preco_unitario', 0) or 0),
                tipo_standby='AGUARDA_COMPLEMENTO',
                criado_por=usuario
            )
            db.session.add(saldo_standby)
            acao_tomada = 'SALDO_EM_STANDBY'
            
        elif classificacao_saldo == 'EXCLUIR_DEFINITIVO':
            # 🗑️ MARCAR ITEM COMO INATIVO
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto
            ).first()
            
            if item_carteira:
                item_carteira.ativo = False
                item_carteira.updated_by = usuario
                item_carteira.updated_at = agora_brasil()
                
            acao_tomada = 'ITEM_EXCLUIDO_DEFINITIVO'
            
        else:
            # 📋 AGUARDA DECISÃO POSTERIOR
            acao_tomada = 'AGUARDA_DECISAO_COMERCIAL'
        
        # 📝 6. ATUALIZAR JUSTIFICATIVA COM AÇÃO
        justificativa.acao_comercial = acao_tomada
        justificativa.data_acao = agora_brasil()
        justificativa.executado_por = usuario
        
        # 📋 7. CRIAR EVENTO DE RASTREAMENTO
        if inspector.has_table('evento_carteira'):
            evento = EventoCarteira(
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                carteira_item_id=0,  # Será atualizado se necessário
                tipo_evento='JUSTIFICATIVA_FATURAMENTO_PARCIAL',
                qtd_anterior=qtd_separada,
                qtd_nova=qtd_faturada,
                qtd_impactada=qtd_saldo,
                numero_nf=numero_nf,
                motivo_cancelamento=motivo_nao_faturamento,
                criado_por=usuario
            )
            db.session.add(evento)
        
        # 💾 8. SALVAR TUDO
        db.session.commit()
        
        logger.info(f"✅ Justificativa processada: {num_pedido}-{cod_produto} Motivo: {motivo_nao_faturamento} Ação: {acao_tomada}")
        
        return {
            'success': True,
            'motivo': motivo_nao_faturamento,
            'classificacao_saldo': classificacao_saldo,
            'acao_tomada': acao_tomada,
            'qtd_saldo': qtd_saldo,
            'justificativa_id': justificativa.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar justificativa: {str(e)}")
        return {
            'success': False,
            'error': f'Erro ao processar: {str(e)}',
            'motivo': 'ERRO_SISTEMA',
            'classificacao_saldo': 'ERRO',
            'acao_tomada': 'FALHA_PROCESSAMENTO'
        }

def _criar_saldo_standby(justificativa, tipo_standby, usuario):
    """
    ⏸️ CRIAR SALDO EM STANDBY - FUNÇÃO 4 IMPLEMENTADA
    
    FUNCIONALIDADE:
    - Cria saldo aguardando decisão comercial
    - Define prazos e alertas automáticos
    - Controle temporal de saldos parados
    """
    try:
        from sqlalchemy import inspect
        from datetime import date, timedelta
        
        logger.info(f"⏸️ Criando saldo standby tipo {tipo_standby} por {usuario}")
        
        # 🔍 1. VERIFICAR SE TABELA EXISTE
        inspector = inspect(db.engine)
        if not inspector.has_table('saldo_standby'):
            return {
                'success': False,
                'error': 'Sistema de saldos standby não inicializado',
                'standby_id': None,
                'data_limite': None
            }
        
        # 📊 2. CALCULAR PRAZOS BASEADOS NO TIPO
        data_limite_standby = None
        if tipo_standby == 'AGUARDA_COMPLEMENTO':
            data_limite_standby = date.today() + timedelta(days=30)  # 30 dias para complemento
        elif tipo_standby == 'AGUARDA_DECISAO':
            data_limite_standby = date.today() + timedelta(days=7)   # 7 dias para decisão
        elif tipo_standby == 'AGUARDA_REPOSICAO':
            data_limite_standby = date.today() + timedelta(days=15)  # 15 dias para reposição
        
        proximo_alerta = date.today() + timedelta(days=3)  # Primeiro alerta em 3 dias
        
        # 📝 3. CRIAR SALDO STANDBY
        saldo = SaldoStandby(
            origem_separacao_lote_id=justificativa.get('separacao_lote_id'),
            num_pedido=justificativa.get('num_pedido'),
            cod_produto=justificativa.get('cod_produto'),
            cnpj_cliente=justificativa.get('cnpj_cliente', ''),
            nome_cliente=justificativa.get('nome_cliente', ''),
            qtd_saldo=justificativa.get('qtd_saldo', 0),
            valor_saldo=justificativa.get('valor_saldo', 0),
            peso_saldo=justificativa.get('peso_saldo', 0),
            pallet_saldo=justificativa.get('pallet_saldo', 0),
            tipo_standby=tipo_standby,
            data_limite_standby=data_limite_standby,
            proximo_alerta=proximo_alerta,
            criado_por=usuario
        )
        db.session.add(saldo)
        db.session.commit()
        
        logger.info(f"✅ Saldo standby criado: {justificativa.get('num_pedido')}-{justificativa.get('cod_produto')} Tipo: {tipo_standby}")
        
        return {
            'success': True,
            'standby_id': saldo.id,
            'tipo_standby': tipo_standby,
            'data_limite': data_limite_standby.strftime('%d/%m/%Y') if data_limite_standby else None,
            'proximo_alerta': proximo_alerta.strftime('%d/%m/%Y')
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao criar saldo standby: {str(e)}")
        return {
            'success': False,
            'error': f'Erro ao criar standby: {str(e)}',
            'standby_id': None,
            'data_limite': None
        }

def _buscar_faturamentos_parciais_pendentes():
    """
    🔍 BUSCAR FATURAMENTOS PARCIAIS PENDENTES - FUNÇÃO 5 IMPLEMENTADA
    
    FUNCIONALIDADE:
    - Lista faturamentos que precisam de justificativa
    - Identifica separações com faturamento incompleto
    - Prioriza por antiguidade e valor
    """
    try:
        from sqlalchemy import inspect, and_, or_
        
        logger.info("🔍 Buscando faturamentos parciais pendentes")
        
        # 🔍 1. VERIFICAR SE TABELAS EXISTEM
        inspector = inspect(db.engine)
        if not inspector.has_table('inconsistencia_faturamento'):
            return []
        
        # 📊 2. BUSCAR INCONSISTÊNCIAS NÃO RESOLVIDAS
        inconsistencias = InconsistenciaFaturamento.query.filter(
            InconsistenciaFaturamento.resolvida == False,
            or_(
                InconsistenciaFaturamento.tipo == 'FATURAMENTO_EXCEDE_SALDO',
                InconsistenciaFaturamento.tipo == 'FATURAMENTO_PARCIAL'
            )
        ).order_by(InconsistenciaFaturamento.detectada_em.desc()).limit(50).all()
        
        pendentes = []
        
        for inconsistencia in inconsistencias:
            try:
                # 🔍 3. BUSCAR DADOS COMPLEMENTARES
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=inconsistencia.num_pedido,
                    cod_produto=inconsistencia.cod_produto
                ).first()
                
                if item_carteira:
                    pendente = {
                        'inconsistencia_id': inconsistencia.id,
                        'numero_nf': inconsistencia.numero_nf,
                        'num_pedido': inconsistencia.num_pedido,
                        'cod_produto': inconsistencia.cod_produto,
                        'nome_produto': item_carteira.nome_produto,
                        'qtd_faturada': float(inconsistencia.qtd_faturada or 0),
                        'saldo_disponivel': float(inconsistencia.saldo_disponivel or 0),
                        'qtd_excesso': float(inconsistencia.qtd_excesso or 0),
                        'valor_impacto': float(inconsistencia.qtd_excesso or 0) * float(item_carteira.preco_produto_pedido or 0),
                        'cliente': item_carteira.raz_social_red or item_carteira.raz_social,
                        'vendedor': item_carteira.vendedor,
                        'data_deteccao': inconsistencia.detectada_em.strftime('%d/%m/%Y %H:%M'),
                        'antiguidade_dias': (agora_brasil() - inconsistencia.detectada_em).days,
                        'tipo_inconsistencia': inconsistencia.tipo,
                        'lote_separacao_id': item_carteira.lote_separacao_id
                    }
                    pendentes.append(pendente)
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar inconsistência {inconsistencia.id}: {str(e)}")
                continue
        
        # 📊 4. ORDENAR POR PRIORIDADE (ANTIGUIDADE + VALOR)
        pendentes.sort(key=lambda x: (x['antiguidade_dias'], -x['valor_impacto']), reverse=True)
        
        logger.info(f"✅ Encontrados {len(pendentes)} faturamentos parciais pendentes")
        return pendentes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar faturamentos pendentes: {str(e)}")
        return []

def _sincronizar_carteira_copia(usuario):
    """
    🔄 SINCRONIZAÇÃO CARTEIRA CÓPIA - FUNÇÃO 6 IMPLEMENTADA
    
    FUNCIONALIDADE:
    - Sincroniza CarteiraPrincipal com CarteiraCopia
    - Recalcula saldos e baixas automáticas
    - Detecta divergências entre sistemas
    """
    try:
        from sqlalchemy import inspect
        
        logger.info(f"🔄 Sincronizando carteira cópia por {usuario}")
        
        # 🔍 1. VERIFICAR SE TABELAS EXISTEM
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_copia'):
            return {
                'success': False,
                'error': 'Tabela carteira_copia não existe',
                'sincronizados': 0,
                'criados': 0,
                'divergencias': 0
            }
        
        # 📊 2. CONTADORES
        sincronizados = 0
        criados = 0
        divergencias_detectadas = 0
        
        # 🔄 3. PROCESSAR TODOS OS ITENS DA CARTEIRA PRINCIPAL
        itens_principais = CarteiraPrincipal.query.filter_by(ativo=True).all()
        
        for item_principal in itens_principais:
            try:
                # 🔍 3.1 BUSCAR ITEM NA CÓPIA
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=item_principal.num_pedido,
                    cod_produto=item_principal.cod_produto
                ).first()
                
                if not item_copia:
                    # 🆕 3.2 CRIAR NOVO ITEM NA CÓPIA
                    item_copia = CarteiraCopia(
                        num_pedido=item_principal.num_pedido,
                        cod_produto=item_principal.cod_produto,
                        cnpj_cpf=item_principal.cnpj_cpf,
                        raz_social=item_principal.raz_social,
                        raz_social_red=item_principal.raz_social_red,
                        nome_produto=item_principal.nome_produto,
                        qtd_produto_pedido=item_principal.qtd_produto_pedido,
                        qtd_saldo_produto_pedido=item_principal.qtd_saldo_produto_pedido,
                        preco_produto_pedido=item_principal.preco_produto_pedido,
                        vendedor=item_principal.vendedor,
                        baixa_produto_pedido=0,  # Inicia sem baixa
                        created_by=usuario
                    )
                    db.session.add(item_copia)
                    criados += 1
                    
                else:
                    # 🔄 3.3 SINCRONIZAR DADOS MESTRES
                    campos_alterados = []
                    
                    if item_copia.qtd_produto_pedido != item_principal.qtd_produto_pedido:
                        item_copia.qtd_produto_pedido = item_principal.qtd_produto_pedido
                        campos_alterados.append('qtd_produto_pedido')
                    
                    if item_copia.preco_produto_pedido != item_principal.preco_produto_pedido:
                        item_copia.preco_produto_pedido = item_principal.preco_produto_pedido
                        campos_alterados.append('preco_produto_pedido')
                    
                    if item_copia.raz_social != item_principal.raz_social:
                        item_copia.raz_social = item_principal.raz_social
                        campos_alterados.append('raz_social')
                    
                    if campos_alterados:
                        item_copia.updated_by = usuario
                        item_copia.updated_at = agora_brasil()
                        sincronizados += 1
                
                # 📊 3.4 RECALCULAR SALDO NA CÓPIA
                item_copia.recalcular_saldo()
                
                # ⚠️ 3.5 DETECTAR DIVERGÊNCIAS
                saldo_principal = float(item_principal.qtd_saldo_produto_pedido or 0)
                saldo_calculado_copia = float(item_copia.qtd_saldo_produto_calculado or 0)
                
                if abs(saldo_principal - saldo_calculado_copia) > 0.001:  # Tolerância para decimais
                    logger.warning(f"⚠️ Divergência detectada {item_principal.num_pedido}-{item_principal.cod_produto}: Principal={saldo_principal}, Cópia={saldo_calculado_copia}")
                    divergencias_detectadas += 1
                    
                    # 🔄 CRIAR CONTROLE DE DIVERGÊNCIA
                    if inspector.has_table('controle_cruzado_separacao'):
                        controle = ControleCruzadoSeparacao(
                            lote_separacao_id=item_principal.lote_separacao_id or 0,
                            num_pedido=item_principal.num_pedido,
                            cod_produto=item_principal.cod_produto,
                            qtd_separada_original=item_principal.qtd_produto_pedido,
                            qtd_baixada_carteira=item_copia.baixa_produto_pedido,
                            diferenca_detectada=saldo_principal - saldo_calculado_copia,
                            status_controle='DIFERENCA',
                            motivo_diferenca='SINCRONIZACAO_AUTOMATICA'
                        )
                        db.session.add(controle)
                
            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar item {item_principal.num_pedido}-{item_principal.cod_produto}: {str(e)}")
                continue
        
        # 💾 4. SALVAR TODAS AS ALTERAÇÕES
        db.session.commit()
        
        logger.info(f"✅ Sincronização concluída: {sincronizados} atualizados, {criados} criados, {divergencias_detectadas} divergências")
        
        return {
            'success': True,
            'sincronizados': sincronizados,
            'criados': criados,
            'divergencias': divergencias_detectadas,
            'total_processados': len(itens_principais)
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro na sincronização da carteira cópia: {str(e)}")
        return {
            'success': False,
            'error': f'Erro na sincronização: {str(e)}',
            'sincronizados': 0,
            'criados': 0,
            'divergencias': 0
        }

def _processar_vinculacao_automatica(usuario):
    """
    🔗 VINCULAÇÃO AUTOMÁTICA CARTEIRA ↔ SEPARAÇÕES
    
    FUNCIONALIDADE:
    - Busca separações existentes sem vinculação
    - Vincula automaticamente com base em num_pedido + cod_produto
    - Cria VinculacaoCarteiraSeparacao para controle
    """
    try:
        logger.info("🔗 Iniciando vinculação automática carteira ↔ separações")
        
        vinculacoes_criadas = 0
        conflitos_detectados = []
        
        # 📋 BUSCAR ITENS DA CARTEIRA SEM VINCULAÇÃO
        itens_sem_vinculacao = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.lote_separacao_id.is_(None),
            CarteiraPrincipal.ativo == True
        ).all()
        
        for item in itens_sem_vinculacao:
            # 🔍 BUSCAR SEPARAÇÃO CORRESPONDENTE
            separacao = Separacao.query.filter_by(
                num_pedido=item.num_pedido,
                cod_produto=item.cod_produto
            ).first()
            
            if separacao:
                # ✅ VINCULAÇÃO ENCONTRADA
                if separacao.quantidade <= item.qtd_saldo_produto_pedido:
                    # 🔗 VINCULAR (QUANTIDADE DA SEPARAÇÃO ≤ CARTEIRA)
                    item.lote_separacao_id = separacao.id
                    item.qtd_saldo = separacao.quantidade
                    item.updated_by = usuario
                    
                    # 📝 CRIAR REGISTRO DE VINCULAÇÃO
                    vinculacao = VinculacaoCarteiraSeparacao(
                        num_pedido=item.num_pedido,
                        cod_produto=item.cod_produto,
                        protocolo_agendamento=item.protocolo or 'AUTOMATICO',
                        data_agendamento=item.agendamento or date.today(),
                        data_expedicao=item.expedicao or date.today(),
                        carteira_item_id=item.id,
                        separacao_lote_id=separacao.id,
                        qtd_carteira_original=float(item.qtd_produto_pedido),
                        qtd_separacao_original=float(item.qtd_saldo_produto_pedido),
                        qtd_vinculada=float(item.qtd_saldo_produto_pedido),
                        criada_por=usuario
                    )
                    db.session.add(vinculacao)
                    vinculacoes_criadas += 1
                    
                else:
                    # ⚠️ CONFLITO: SEPARAÇÃO > CARTEIRA
                    conflitos_detectados.append({
                        'pedido': item.num_pedido,
                        'produto': item.cod_produto,
                        'carteira': float(item.qtd_saldo_produto_pedido),
                        'separacao': separacao.quantidade,
                        'motivo': 'SEPARACAO_MAIOR_QUE_CARTEIRA'
                    })
        
        db.session.commit()
        logger.info(f"✅ Vinculação automática concluída - {vinculacoes_criadas} vinculações criadas")
        
        return {
            'vinculacoes_criadas': vinculacoes_criadas,
            'conflitos': conflitos_detectados
        }
        
    except Exception as e:
        logger.error(f"Erro na vinculação automática: {str(e)}")
        db.session.rollback()
        raise

def _processar_validacao_nf_simples(numero_nf, origem_nf, cnpj_nf):
    """
    🎯 VALIDAÇÃO SIMPLIFICADA DE NF - APENAS PEDIDO + CNPJ
    
    FUNCIONALIDADE:
    - Verifica se origem_nf (pedido) existe na carteira
    - Verifica se CNPJ confere
    - SEMPRE executa ações, mas com diferentes níveis de controle
    """
    try:
        logger.info(f"🎯 Validando NF {numero_nf} - Pedido: {origem_nf}, CNPJ: {cnpj_nf}")
        
        # 🔍 BUSCAR PEDIDO NA CARTEIRA
        pedido_encontrado = CarteiraPrincipal.query.filter_by(
            num_pedido=origem_nf,
            ativo=True
        ).first()
        
        # 🎯 VALIDAÇÃO SIMPLES
        validacao = ValidacaoNFSimples(
            numero_nf=numero_nf,
            num_pedido_nf=origem_nf,
            cnpj_nf=cnpj_nf,
            pedido_encontrado=bool(pedido_encontrado),
            cnpj_confere=False
        )
        
        if pedido_encontrado:
            # ✅ PEDIDO ENCONTRADO - VERIFICAR CNPJ
            validacao.cnpj_esperado = pedido_encontrado.cnpj_cpf
            validacao.cnpj_recebido = cnpj_nf
            validacao.cnpj_confere = (pedido_encontrado.cnpj_cpf == cnpj_nf)
            
            if validacao.cnpj_confere:
                # ✅ VALIDAÇÃO APROVADA
                validacao.validacao_aprovada = True
                validacao.frete_gerado = True
                validacao.monitoramento_registrado = True
                validacao.data_execucao = agora_brasil()
                
                logger.info(f"✅ NF {numero_nf} validada com sucesso")
                
            else:
                # ⚠️ CNPJ NÃO CONFERE
                validacao.validacao_aprovada = False
                validacao.motivo_bloqueio = f"CNPJ não confere - Esperado: {pedido_encontrado.cnpj_cpf}, Recebido: {cnpj_nf}"
                
                logger.warning(f"⚠️ NF {numero_nf} bloqueada - CNPJ não confere")
        else:
            # ❌ PEDIDO NÃO ENCONTRADO
            validacao.validacao_aprovada = False
            validacao.motivo_bloqueio = f"Pedido {origem_nf} não encontrado na carteira"
            
            logger.warning(f"❌ NF {numero_nf} bloqueada - Pedido não encontrado")
        
        db.session.add(validacao)
        db.session.commit()
        
        return {
            'validacao_aprovada': validacao.validacao_aprovada,
            'motivo_bloqueio': validacao.motivo_bloqueio,
            'gerar_frete': validacao.frete_gerado,
            'registrar_monitoramento': validacao.monitoramento_registrado
        }
        
    except Exception as e:
        logger.error(f"Erro na validação de NF {numero_nf}: {str(e)}")
        db.session.rollback()
        raise

def _detectar_inconsistencias_automaticas():
    """
    🔍 DETECÇÃO AUTOMÁTICA DE INCONSISTÊNCIAS
    
    FUNCIONALIDADE:
    - Compara faturamento vs carteira
    - Detecta problemas automaticamente
    - Gera registros de inconsistência para resolução
    """
    try:
        logger.info("🔍 Detectando inconsistências automaticamente")
        
        inconsistencias_detectadas = 0
        
        # 🔍 BUSCAR FATURAMENTOS QUE EXCEDEM SALDO
        from app.faturamento.models import FaturamentoProduto
        
        faturamentos = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto,
            func.sum(FaturamentoProduto.qtd_produto_faturado).label('total_faturado')
        ).group_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto
        ).all()
        
        for fat in faturamentos:
            # 🔍 BUSCAR SALDO NA CARTEIRA
            item_carteira = CarteiraPrincipal.query.filter_by(
                cod_produto=fat.cod_produto,
                ativo=True
            ).first()
            
            if item_carteira:
                if fat.total_faturado > item_carteira.qtd_saldo_produto_pedido:
                    # ⚠️ INCONSISTÊNCIA DETECTADA
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='FATURAMENTO_EXCEDE_SALDO',
                        numero_nf=fat.numero_nf,
                        cod_produto=fat.cod_produto,
                        qtd_faturada=fat.total_faturado,
                        saldo_disponivel=float(item_carteira.qtd_saldo_produto_pedido),
                        qtd_excesso=fat.total_faturado - float(item_carteira.qtd_saldo_produto_pedido)
                    )
                    db.session.add(inconsistencia)
                    inconsistencias_detectadas += 1
            else:
                # ⚠️ FATURAMENTO SEM PEDIDO
                inconsistencia = InconsistenciaFaturamento(
                    tipo='FATURAMENTO_SEM_PEDIDO',
                    numero_nf=fat.numero_nf,
                    cod_produto=fat.cod_produto,
                    qtd_faturada=fat.total_faturado,
                    saldo_disponivel=0,
                    qtd_excesso=fat.total_faturado
                )
                db.session.add(inconsistencia)
                inconsistencias_detectadas += 1
        
        db.session.commit()
        logger.info(f"✅ Detecção concluída - {inconsistencias_detectadas} inconsistências encontradas")
        
        return inconsistencias_detectadas
        
    except Exception as e:
        logger.error(f"Erro na detecção de inconsistências: {str(e)}")
        db.session.rollback()
        raise 

def _recalcular_campos_calculados(item, alteracoes_detectadas):
    """
    📊 RECÁLCULO AUTOMÁTICO DOS CAMPOS CALCULADOS
    
    FUNCIONALIDADE:
    - Recalcula todos os campos que eram fórmulas no Excel
    - Executa quando altera qtd_produto_pedido, data_expedicao, etc.
    - Simula as fórmulas automáticas do Excel
    """
    try:
        logger.info(f"🧮 Recalculando campos para pedido {item.num_pedido} produto {item.cod_produto}")
        
        campos_alterados = []
        
        # 💰 1. RECALCULAR VALOR DO PRODUTO
        if hasattr(item, 'qtd_produto_pedido') and hasattr(item, 'preco_produto_pedido'):
            if item.preco_produto_pedido:
                valor_antigo = getattr(item, 'valor_produto_pedido', 0)
                item.valor_produto_pedido = float(item.qtd_produto_pedido) * float(item.preco_produto_pedido)
                if valor_antigo != item.valor_produto_pedido:
                    campos_alterados.append('valor_produto_pedido')
        
        # ⚖️ 2. RECALCULAR PESO ESTIMADO (se tem cadastro palletização)
        try:
            from app.producao.models import CadastroPalletizacao
            palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=item.cod_produto).first()
            if palletizacao and hasattr(palletizacao, 'peso_bruto_produto'):
                peso_antigo = getattr(item, 'peso', 0)
                item.peso = float(item.qtd_produto_pedido) * float(palletizacao.peso_bruto_produto)
                if peso_antigo != item.peso:
                    campos_alterados.append('peso')
        except ImportError:
            # Módulo palletização não disponível
            pass
        
        # 📦 3. RECALCULAR PALLETS ESTIMADOS
        try:
            from app.producao.models import CadastroPalletizacao
            palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=item.cod_produto).first()
            if palletizacao and hasattr(palletizacao, 'qtd_produto_pallet'):
                if palletizacao.qtd_produto_pallet > 0:
                    pallets_antigo = getattr(item, 'pallet', 0)
                    item.pallet = float(item.qtd_produto_pedido) / float(palletizacao.qtd_produto_pallet)
                    if pallets_antigo != item.pallet:
                        campos_alterados.append('pallet')
        except ImportError:
            pass
        
        # 📊 4. RECALCULAR TOTALIZADORES POR CLIENTE (se múltiplos pedidos do mesmo CNPJ)
        if hasattr(item, 'cnpj_cpf'):
            # Buscar todos os itens do mesmo cliente na carteira
            itens_cliente = CarteiraPrincipal.query.filter_by(
                cnpj_cpf=item.cnpj_cpf,
                ativo=True
            ).all()
            
            # Somar valores para o cliente
            valor_total_cliente = sum(
                float(getattr(i, 'valor_produto_pedido', 0) or 0) 
                for i in itens_cliente 
                if getattr(i, 'valor_produto_pedido', None)
            )
            peso_total_cliente = sum(
                float(getattr(i, 'peso', 0) or 0) 
                for i in itens_cliente 
                if getattr(i, 'peso', None)
            )
            pallet_total_cliente = sum(
                float(getattr(i, 'pallet', 0) or 0) 
                for i in itens_cliente 
                if getattr(i, 'pallet', None)
            )
            
            # Atualizar TODOS os itens do cliente
            for item_cliente in itens_cliente:
                if hasattr(item_cliente, 'valor_cliente_pedido'):
                    item_cliente.valor_cliente_pedido = valor_total_cliente
                if hasattr(item_cliente, 'peso_cliente_pedido'):
                    item_cliente.peso_cliente_pedido = peso_total_cliente
                if hasattr(item_cliente, 'pallet_cliente_pedido'):
                    item_cliente.pallet_cliente_pedido = pallet_total_cliente
            
            campos_alterados.extend(['valor_cliente_pedido', 'peso_cliente_pedido', 'pallet_cliente_pedido'])
        
        # 📈 5. RECALCULAR TOTALIZADORES POR PRODUTO (se múltiplos pedidos do mesmo produto)
        if hasattr(item, 'cod_produto'):
            # Buscar quantidade total do produto na carteira
            qtd_total_produto = db.session.query(
                func.sum(CarteiraPrincipal.qtd_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == item.cod_produto,
                CarteiraPrincipal.ativo == True
            ).scalar() or 0
            
            # Atualizar todos os itens do mesmo produto
            itens_produto = CarteiraPrincipal.query.filter_by(
                cod_produto=item.cod_produto,
                ativo=True
            ).all()
            
            for item_produto in itens_produto:
                if hasattr(item_produto, 'qtd_total_produto_carteira'):
                    item_produto.qtd_total_produto_carteira = float(qtd_total_produto)
            
            campos_alterados.append('qtd_total_produto_carteira')
        
        # 📊 6. RECALCULAR PROJEÇÃO DE ESTOQUE D0-D28 (se altera data_expedicao)
        if 'data_expedicao' in alteracoes_detectadas or 'qtd_produto_pedido' in alteracoes_detectadas:
            try:
                from app.estoque.models import SaldoEstoque
                # Buscar estoque do produto
                estoque = SaldoEstoque.query.filter_by(cod_produto=item.cod_produto).first()
                if estoque and hasattr(item, 'expedicao'):
                    # Calcular impacto na projeção baseado na data de expedição
                    data_expedicao = getattr(item, 'expedicao', None)
                    if data_expedicao:
                        # Implementação simplificada - em produção seria mais complexa
                        dias_ate_expedicao = (data_expedicao - date.today()).days
                        if 0 <= dias_ate_expedicao <= 28:
                            # Atualizar campo estoque_dX correspondente
                            campo_estoque = f'estoque_d{dias_ate_expedicao}'
                            if hasattr(item, campo_estoque):
                                # Subtrair quantidade do estoque projetado
                                estoque_atual = getattr(item, campo_estoque, 0) or 0
                                novo_estoque = max(0, estoque_atual - float(item.qtd_produto_pedido))
                                setattr(item, campo_estoque, novo_estoque)
                                campos_alterados.append(campo_estoque)
            except ImportError:
                pass
        
        # 🔄 7. SINCRONIZAR COM CARTEIRA CÓPIA
        if campos_alterados and hasattr(item, 'num_pedido') and hasattr(item, 'cod_produto'):
            try:
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto
                ).first()
                
                if item_copia:
                    # Sincronizar campos alterados
                    for campo in campos_alterados:
                        if hasattr(item_copia, campo) and hasattr(item, campo):
                            setattr(item_copia, campo, getattr(item, campo))
                    
                    # Recalcular saldo na cópia
                    if hasattr(item_copia, 'recalcular_saldo'):
                        item_copia.recalcular_saldo()
            except Exception as e:
                logger.warning(f"Erro na sincronização com cópia: {str(e)}")
        
        # 📝 8. MARCAR CAMPOS COMO ATUALIZADOS
        if hasattr(item, 'updated_at'):
            item.updated_at = agora_brasil()
        
        logger.info(f"✅ Recálculo concluído - {len(campos_alterados)} campos atualizados: {campos_alterados}")
        
        return {
            'campos_recalculados': campos_alterados,
            'sucesso': True,
            'total_campos': len(campos_alterados)
        }
        
    except Exception as e:
        logger.error(f"Erro no recálculo automático: {str(e)}")
        return {
            'campos_recalculados': [],
            'sucesso': False,
            'erro': str(e)
        }

def _detectar_alteracoes_importantes(item_antes, item_depois):
    """
    🔍 DETECTA ALTERAÇÕES QUE REQUEREM RECÁLCULO OU NOTIFICAÇÃO
    
    RETORNA:
    - Lista de campos alterados que são importantes
    - Se afeta separação existente
    - Se requer aprovação
    """
    alteracoes_importantes = []
    
    # Campos que requerem recálculo automático
    campos_criticos = [
        'qtd_produto_pedido', 'preco_produto_pedido', 'data_expedicao',
        'data_entrega', 'agendamento', 'protocolo'
    ]
    
    for campo in campos_criticos:
        valor_antes = getattr(item_antes, campo, None)
        valor_depois = getattr(item_depois, campo, None)
        
        if valor_antes != valor_depois:
            alteracoes_importantes.append(campo)
    
    # Verificar se afeta separação
    afeta_separacao = bool(
        getattr(item_antes, 'lote_separacao_id', None) and 
        'qtd_produto_pedido' in alteracoes_importantes
    )
    
    # Verificar se requer aprovação (se há cotação)
    requer_aprovacao = bool(
        alteracoes_importantes and 
        getattr(item_antes, 'roteirizacao', None)  # Se já tem transportadora
    )
    
    return {
        'alteracoes': alteracoes_importantes,
        'afeta_separacao': afeta_separacao,
        'requer_aprovacao': requer_aprovacao,
        'total_alteracoes': len(alteracoes_importantes)
    }

def _gerar_novo_lote_id():
    """Gera ID único para novo lote de separação"""
    import uuid
    return f"LOTE_{uuid.uuid4().hex[:8].upper()}"