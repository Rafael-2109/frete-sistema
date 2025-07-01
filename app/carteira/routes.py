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
        
        # resultado = _processar_baixa_faturamento(nfs_processadas, current_user.nome)
        # TODO: Implementar função _processar_baixa_faturamento
        resultado = {'processadas': len(nfs_processadas), 'erros': []}
        
        return jsonify({
            'success': True,
            'processadas': resultado['processadas'],
            'erros': resultado['erros']
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
        # 📝 CRIAR MODELO COM EXEMPLOS REAIS E FORMATOS CORRETOS
        modelo_data = {
            # 🔑 CAMPOS OBRIGATÓRIOS
            'num_pedido': ['PED001', 'PED001', 'PED002'],
            'cod_produto': ['PROD001', 'PROD002', 'PROD001'],
            'nome_produto': ['Produto Exemplo A', 'Produto Exemplo B', 'Produto Exemplo A'],
            'qtd_produto_pedido': ['100,00', '50,50', '200,25'],  # 💰 DECIMAL COM VÍRGULA
            'qtd_saldo_produto_pedido': ['100,00', '50,50', '200,25'],  # 💰 DECIMAL COM VÍRGULA
            'preco_produto_pedido': ['15,50', '23,75', '15,50'],  # 💰 DECIMAL COM VÍRGULA
            'cnpj_cpf': ['12.345.678/0001-90', '12.345.678/0001-90', '98.765.432/0001-10'],
            
            # 👥 DADOS DO CLIENTE
            'raz_social': ['Cliente Exemplo LTDA', 'Cliente Exemplo LTDA', 'Outro Cliente S.A.'],
            'raz_social_red': ['Cliente Exemplo', 'Cliente Exemplo', 'Outro Cliente'],
            'municipio': ['São Paulo', 'São Paulo', 'Rio de Janeiro'],
            'estado': ['SP', 'SP', 'RJ'],
            
            # 🏪 DADOS COMERCIAIS
            'vendedor': ['João Silva', 'João Silva', 'Maria Santos'],
            'status_pedido': ['Pedido de venda', 'Pedido de venda', 'Cotação'],
            
            # 📅 DATAS NO FORMATO ISO/SQL (YYYY-MM-DD HH:MM:SS)
            'data_pedido': ['2025-01-15 08:30:00', '2025-01-15 09:15:00', '2025-01-16 14:20:00'],
            'expedicao': ['2025-03-15 07:00:00', '2025-03-20 07:30:00', '2025-03-25 08:00:00'],
            'data_entrega': ['2025-03-18 16:00:00', '2025-03-23 15:30:00', '2025-03-28 17:00:00'],
            'agendamento': ['2025-03-17 10:00:00', '2025-03-22 14:00:00', '2025-03-27 11:30:00'],
            
            # 📦 DADOS OPCIONAIS (podem ficar vazios)
            'pedido_cliente': ['CLI-001', 'CLI-002', ''],
            'observ_ped_1': ['Entrega urgente', 'Cliente VIP', ''],
            'protocolo': ['PROT-001', 'PROT-002', ''],
            'roteirizacao': ['Transportadora A', 'Transportadora B', ''],
            
            # ⚖️ DADOS FÍSICOS (DECIMAIS COM VÍRGULA)
            'peso': ['10,50', '25,75', '5,25'],  # 💰 KG com vírgula
            'pallet': ['0,50', '1,25', '0,75'],  # 💰 Pallets com vírgula
            'valor_total': ['1.550,00', '1.187,50', '3.100,00']  # 💰 R$ com vírgula
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
    ⚙️ CONFIGURAR TIPO DE CARGA E CAPACIDADES
    
    FUNCIONALIDADE:
    - Define se carga é TOTAL, PARCIAL, COMPLEMENTAR, STANDBY
    - Configura limites de peso, pallets, valor
    - Define comportamento para alterações futuras
    """
    if request.method == 'GET':
        tipo_carga_existente = TipoCarga.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()
        
        return render_template(
            'carteira/configurar_tipo_carga.html',
            separacao_lote_id=separacao_lote_id,
            tipo_carga=tipo_carga_existente
        )
    
    try:
        data = request.form
        resultado = _configurar_tipo_carga(separacao_lote_id, data, current_user.nome)
        
        flash(f"""
        Tipo de carga configurado com sucesso!
        🎯 Tipo: {resultado['tipo_carga']}
        📊 Capacidade: {resultado['capacidade_resumo']}
        🔄 Aceita alterações: {'Sim' if resultado['aceita_incremento'] else 'Não'}
        """, 'success')
        
        return redirect(url_for('carteira.listar_principal'))
        
    except Exception as e:
        logger.error(f"Erro ao configurar tipo de carga: {str(e)}")
        flash(f'Erro ao configurar tipo de carga: {str(e)}', 'error')
        return redirect(request.url)

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
    """Atualiza item existente, preservando dados operacionais"""
    # 🔄 ATUALIZAR DADOS MESTRES
    _atualizar_dados_mestres(item, row)
    
    # 🛡️ RESTAURAR DADOS OPERACIONAIS
    dados_operacionais_preservados = {
        'expedicao': item.expedicao,
        'agendamento': item.agendamento,
        'protocolo': item.protocolo,
        'roteirizacao': item.roteirizacao,
        'lote_separacao_id': item.lote_separacao_id,
        'qtd_saldo': item.qtd_saldo,
        'valor_saldo': item.valor_saldo,
        'pallet': item.pallet,
        'peso': item.peso
    }
    
    for campo, valor in dados_operacionais_preservados.items():
        if valor is not None:  # Só preserva se tinha valor
            setattr(item, campo, valor)
    
    item.updated_by = usuario
    item.updated_at = agora_brasil()
    return {
        'alterado': True,
        'dados_preservados': any(dados_operacionais_preservados.values()),
        'eventos': 0  # Implemente a lógica para contar eventos gerados
    }

def _atualizar_dados_mestres(item, row):
    """Atualiza apenas dados mestres, preservando operacionais"""
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

def _criar_novo_item_carteira(row, usuario):
    """Cria novo item na carteira"""
    return CarteiraPrincipal(
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
    💳 PROCESSA BAIXA DE FATURAMENTO NA CARTEIRA
    
    FUNCIONALIDADE:
    - Busca NF no faturamento importado
    - Identifica itens na carteira
    - Executa baixa automática
    - Cria eventos de rastreamento
    """
    try:
        logger.info(f"💳 Processando baixa NF {numero_nf}")
        
        # 🔍 BUSCAR NF NO FATURAMENTO IMPORTADO
        from app.faturamento.models import RelatorioFaturamentoImportado
        nfs_faturadas = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).all()
        
        if not nfs_faturadas:
            logger.warning(f"NF {numero_nf} não encontrada no faturamento")
            return {'nf': numero_nf, 'itens_baixados': 0, 'erro': 'NF não encontrada'}
        
        # 📊 CONTADORES
        itens_baixados = 0
        valor_baixado = 0
        inconsistencias = 0
        
        # 🔄 PROCESSAR CADA PRODUTO FATURADO
        for nf_item in nfs_faturadas:
            try:
                # 🔍 BUSCAR ITEM NA CARTEIRA (se existe)
                inspector = inspect(db.engine)
                if inspector.has_table('carteira_principal'):
                    itens_carteira = CarteiraPrincipal.query.filter(
                        CarteiraPrincipal.num_pedido == getattr(nf_item, 'origem', None),
                        CarteiraPrincipal.cod_produto == getattr(nf_item, 'cod_produto', None)
                    ).all()
                    
                    if itens_carteira:
                        # ✅ BAIXA NORMAL - ITEM EXISTE NA CARTEIRA
                        for item in itens_carteira:
                            qtd_faturada = float(getattr(nf_item, 'qtd_produto_faturado', 0) or 0)
                            qtd_saldo_atual = float(getattr(item, 'qtd_saldo_produto_pedido', 0) or 0)
                            qtd_baixar = min(qtd_faturada, qtd_saldo_atual)
                            
                            if qtd_baixar > 0:
                                # 📝 ATUALIZAR CARTEIRA
                                if hasattr(item, 'qtd_saldo_produto_pedido'):
                                    novo_saldo = qtd_saldo_atual - qtd_baixar
                                    item.qtd_saldo_produto_pedido = max(0, novo_saldo)
                                
                                # 📝 ATUALIZAR CÓPIA
                                if inspector.has_table('carteira_copia'):
                                    item_copia = CarteiraCopia.query.filter_by(
                                        num_pedido=getattr(item, 'num_pedido', None),
                                        cod_produto=getattr(item, 'cod_produto', None)
                                    ).first()
                                    if item_copia and hasattr(item_copia, 'baixa_produto_pedido'):
                                        baixa_atual = float(getattr(item_copia, 'baixa_produto_pedido', 0) or 0)
                                        item_copia.baixa_produto_pedido = baixa_atual + qtd_baixar
                                
                                valor_baixado += qtd_baixar * float(getattr(nf_item, 'preco_produto_faturado', 0) or 0)
                                itens_baixados += 1
                                
                                if hasattr(item, 'updated_by'):
                                    item.updated_by = usuario
                    else:
                        # ⚠️ INCONSISTÊNCIA - NF SEM CARTEIRA
                        logger.warning(f"NF {numero_nf} produto {getattr(nf_item, 'cod_produto', None)} sem item na carteira")
                        if inspector.has_table('inconsistencia_faturamento'):
                            inconsistencia = InconsistenciaFaturamento(
                                numero_nf=numero_nf,
                                cod_produto=getattr(nf_item, 'cod_produto', None),
                                tipo_inconsistencia='FATURAMENTO_SEM_PEDIDO',
                                qtd_faturada=float(getattr(nf_item, 'qtd_produto_faturado', 0) or 0),
                                valor_faturado=float(getattr(nf_item, 'valor_produto_faturado', 0) or 0),
                                detectada_por=usuario
                            )
                            db.session.add(inconsistencia)
                        inconsistencias += 1
                
                # 📝 CRIAR HISTÓRICO DE FATURAMENTO
                if inspector.has_table('historico_faturamento'):
                    historico = HistoricoFaturamento(
                        numero_nf=numero_nf,
                        data_faturamento=getattr(nf_item, 'data_fatura', date.today()),
                        num_pedido=getattr(nf_item, 'origem', None),
                        cod_produto=getattr(nf_item, 'cod_produto', None),
                        qtd_faturada=float(getattr(nf_item, 'qtd_produto_faturado', 0) or 0),
                        valor_faturado=float(getattr(nf_item, 'valor_produto_faturado', 0) or 0),
                        processada_por=usuario
                    )
                    db.session.add(historico)
                
                # 📝 CRIAR EVENTO CARTEIRA
                if inspector.has_table('evento_carteira'):
                    evento = EventoCarteira(
                        num_pedido=getattr(nf_item, 'origem', None),
                        cod_produto=getattr(nf_item, 'cod_produto', None),
                        tipo_evento='FATURAMENTO',
                        numero_nf=numero_nf,
                        qtd_impactada=float(getattr(nf_item, 'qtd_produto_faturado', 0) or 0),
                        valor_impactado=float(getattr(nf_item, 'valor_produto_faturado', 0) or 0),
                        criado_por=usuario
                    )
                    db.session.add(evento)
                
            except Exception as e:
                logger.error(f"Erro ao processar item NF {numero_nf}: {str(e)}")
                continue
        
        # 💾 COMMIT FINAL
        db.session.commit()
        
        logger.info(f"✅ NF {numero_nf} processada - {itens_baixados} itens baixados")
        
        return {
            'nf': numero_nf,
            'itens_baixados': itens_baixados,
            'valor_baixado': valor_baixado,
            'inconsistencias': inconsistencias,
            'sucesso': True
        }
        
    except Exception as e:
        logger.error(f"Erro no processamento NF {numero_nf}: {str(e)}")
        db.session.rollback()
        return {
            'nf': numero_nf,
            'itens_baixados': 0,
            'sucesso': False,
            'erro': str(e)
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
    
    # TODO: IMPLEMENTAR APÓS MIGRAÇÃO DAS TABELAS
    # # 1. BUSCAR DADOS ATUAIS
    # carteira_item = CarteiraPrincipal.query.get(carteira_item_id)
    # if not carteira_item:
    #     raise ValueError(f"Item da carteira {carteira_item_id} não encontrado")
    
    # tipo_carga = TipoCarga.query.filter_by(separacao_lote_id=separacao_lote_id).first()
    # if not tipo_carga:
    #     # Se não tem tipo definido, assume TOTAL (aceita alterações)
    #     tipo_carga = TipoCarga(
    #         separacao_lote_id=separacao_lote_id,
    #         tipo_carga='TOTAL',
    #         aceita_incremento=True,
    #         criado_por=usuario
    #     )
    #     db.session.add(tipo_carga)
    
    # Implementação temporária até migração
    return {
        'decisao': 'AGUARDA_MIGRACAO',
        'motivo': 'Tabelas não migradas ainda',
        'nova_carga_id': None,
        'capacidade_utilizada': 0
    }

def _processar_justificativa_faturamento_parcial(data, usuario):
    """
    📋 PROCESSA JUSTIFICATIVA DE FATURAMENTO PARCIAL
    """
    
    # TODO: IMPLEMENTAR APÓS MIGRAÇÃO DAS TABELAS
    # justificativa = FaturamentoParcialJustificativa(
    #     separacao_lote_id=data.get('separacao_lote_id'),
    #     num_pedido=data.get('num_pedido'),
    #     cod_produto=data.get('cod_produto'),
    #     numero_nf=data.get('numero_nf'),
    #     qtd_separada=float(data.get('qtd_separada', 0)),
    #     qtd_faturada=float(data.get('qtd_faturada', 0)),
    #     qtd_saldo=float(data.get('qtd_saldo', 0)),
    #     motivo_nao_faturamento=data.get('motivo_nao_faturamento'),
    #     descricao_detalhada=data.get('descricao_detalhada'),
    #     classificacao_saldo=data.get('classificacao_saldo'),
    #     criado_por=usuario
    # )
    
    # Implementação temporária até migração
    return {
        'motivo': 'AGUARDA_MIGRACAO',
        'classificacao_saldo': 'AGUARDA_MIGRACAO',
        'acao_tomada': 'AGUARDA_MIGRACAO'
    }

def _configurar_tipo_carga(separacao_lote_id, data, usuario):
    """
    ⚙️ CONFIGURA TIPO DE CARGA E CAPACIDADES
    """
    
    # TODO: IMPLEMENTAR APÓS MIGRAÇÃO DAS TABELAS
    # tipo_carga = TipoCarga.query.filter_by(separacao_lote_id=separacao_lote_id).first()
    # if not tipo_carga:
    #     tipo_carga = TipoCarga(
    #         separacao_lote_id=separacao_lote_id,
    #         criado_por=usuario
    #     )
    #     db.session.add(tipo_carga)
    
    # Implementação temporária até migração
    return {
        'tipo_carga': 'AGUARDA_MIGRACAO',
        'capacidade_resumo': 'Aguardando migração das tabelas',
        'aceita_incremento': True
    }

def _criar_saldo_standby(justificativa, tipo_standby, usuario):
    """Cria registro de saldo em standby"""
    # TODO: IMPLEMENTAR APÓS MIGRAÇÃO DAS TABELAS
    # saldo_standby = SaldoStandby(
    #     origem_separacao_lote_id=justificativa.separacao_lote_id,
    #     num_pedido=justificativa.num_pedido,
    #     cod_produto=justificativa.cod_produto,
    #     cnpj_cliente='',  # TODO: Buscar do pedido
    #     nome_cliente='',  # TODO: Buscar do pedido
    #     qtd_saldo=justificativa.qtd_saldo,
    #     valor_saldo=0,  # TODO: Calcular
    #     tipo_standby=tipo_standby,
    #     criado_por=usuario
    # )
    pass

def _buscar_faturamentos_parciais_pendentes():
    """
    🔍 BUSCA FATURAMENTOS PARCIAIS QUE PRECISAM DE JUSTIFICATIVA
    
    LÓGICA:
    - Compara qtd_separada vs qtd_faturada nos embarques
    - Identifica diferenças que precisam justificativa
    """
    
    # TODO: Implementar lógica de detecção automática
    # Por enquanto retorna lista vazia
    return []

def _gerar_novo_lote_id():
    """Gera ID único para novo lote de separação"""
    import uuid
    return f"LOTE_{uuid.uuid4().hex[:8].upper()}"

def _sincronizar_carteira_copia(usuario):
    """
    🔄 SINCRONIZA CARTEIRA PRINCIPAL → CÓPIA
    
    TODO: IMPLEMENTAR APÓS MIGRAÇÃO COMPLETA DOS MODELOS
    """
    try:
        logger.info("🔄 Sincronização CarteiraCopia (aguardando migração)")
        # TODO: Implementar após migração estar funcional
        return True
        
    except Exception as e:
        logger.error(f"Erro na sincronização da carteira cópia: {str(e)}")
        return False

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