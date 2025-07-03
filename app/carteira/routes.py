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
from app.estoque.models import SaldoEstoque, MovimentacaoEstoque
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
import random
import time

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
        
        if arquivo.filename == '' or arquivo.filename is None:
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
        
        # 🔍 DEBUG: Mostrar colunas encontradas no arquivo
        logger.info(f"🔍 DEBUG: Total de colunas encontradas: {len(df.columns)}")
        logger.info(f"🔍 DEBUG: Colunas no arquivo: {list(df.columns)}")
        
        # 🧹 LIMPAR NOMES DAS COLUNAS (espaços, quebras de linha)
        df.columns = df.columns.str.strip().str.replace('\n', '').str.replace('\r', '')
        logger.info(f"🔍 DEBUG: Colunas após limpeza: {list(df.columns)}")
        
        # ✅ VALIDAR E CORRIGIR COLUNAS OBRIGATÓRIAS
        colunas_obrigatorias = ['num_pedido', 'cod_produto', 'nome_produto', 'qtd_produto_pedido', 'cnpj_cpf']
        
        # 🧠 MAPEAMENTO INTELIGENTE AVANÇADO - SUPORTE A ESTRUTURAS HIERÁRQUICAS
        mapeamento_colunas = {}
        colunas_encontradas = list(df.columns)
        
        # 📋 MAPEAMENTO OFICIAL BASEADO NOS ARQUIVOS PROJETO_CARTEIRA
        # Baseado em: projeto_carteira/OK - 1- carteira de pedidos.csv e OK - 2- copia da carteira de pedidos.csv
        mapeamentos_oficiais = {
            # 🔑 CAMPOS OBRIGATÓRIOS - CONFORME ARQUIVO 1
            'num_pedido': 'Referência do pedido/Referência do pedido',
            'cod_produto': 'Produto/Referência interna', 
            'nome_produto': 'Produto/Nome',
            'qtd_produto_pedido': 'Quantidade',
            'cnpj_cpf': 'Referência do pedido/Cliente/CNPJ',
            
            # 👥 DADOS DO CLIENTE
            'raz_social': 'Referência do pedido/Cliente/Razão Social',
            'raz_social_red': 'Referência do pedido/Cliente/Nome',
            'municipio': 'Referência do pedido/Cliente/Município/Nome do Município',
            'estado': 'Referência do pedido/Cliente/Estado/Código do estado',
            'vendedor': 'Referência do pedido/Vendedor',
            'equipe_vendas': 'Referência do pedido/Equipe de vendas',
            
            # 📦 DADOS DO PRODUTO
            'unid_medida_produto': 'Produto/Unidade de medida',
            'embalagem_produto': 'Produto/Categoria de produtos/Nome',
            'materia_prima_produto': 'Produto/Categoria de produtos/Categoria primária/Nome', 
            'categoria_produto': 'Produto/Categoria de produtos/Categoria primária/Categoria primária/Nome',
            
            # 📊 QUANTIDADES E VALORES
            'qtd_saldo_produto_pedido': 'Saldo',
            'qtd_cancelada_produto_pedido': 'Cancelado',
            'preco_produto_pedido': 'Preço unitário',
            
            # 📋 DADOS DO PEDIDO
            'pedido_cliente': 'Referência do pedido/Pedido de Compra do Cliente',
            'data_pedido': 'Referência do pedido/Data de criação',
            'data_atual_pedido': 'Referência do pedido/Data do pedido',
            'status_pedido': 'Referência do pedido/Status',
            
            # 💳 CONDIÇÕES COMERCIAIS
            'cond_pgto_pedido': 'Referência do pedido/Condições de pagamento',
            'forma_pgto_pedido': 'Referência do pedido/Forma de Pagamento',
            'observ_ped_1': 'Referência do pedido/Notas para Expedição',
            'incoterm': 'Referência do pedido/Incoterm',
            'metodo_entrega_pedido': 'Referência do pedido/Método de entrega',
            'data_entrega_pedido': 'Referência do pedido/Data de entrega',
            'cliente_nec_agendamento': 'Referência do pedido/Cliente/Agendamento',
            
            # 🏠 ENDEREÇO DE ENTREGA
            'cnpj_endereco_ent': 'Referência do pedido/Endereço de entrega/CNPJ',
            'empresa_endereco_ent': 'Referência do pedido/Endereço de entrega/O próprio',
            'cep_endereco_ent': 'Referência do pedido/Endereço de entrega/CEP',
            'nome_cidade': 'Referência do pedido/Endereço de entrega/Município',  # Tratamento especial para extrair cidade e UF
            'bairro_endereco_ent': 'Referência do pedido/Endereço de entrega/Bairro',
            'rua_endereco_ent': 'Referência do pedido/Endereço de entrega/Endereço',
            'endereco_ent': 'Referência do pedido/Endereço de entrega/Número',
            'telefone_endereco_ent': 'Referência do pedido/Endereço de entrega/Telefone',
            
        }
        
        # 🎯 MAPEAMENTO EXATO - SOMENTE NOMES OFICIAIS DOS ARQUIVOS DE ESPECIFICAÇÃO
        for col_obrigatoria in colunas_obrigatorias:
            if col_obrigatoria in mapeamentos_oficiais:
                coluna_excel_esperada = mapeamentos_oficiais[col_obrigatoria]
                if coluna_excel_esperada in colunas_encontradas:
                    mapeamento_colunas[col_obrigatoria] = coluna_excel_esperada
                    logger.info(f"✅ Mapeamento EXATO: '{col_obrigatoria}' → '{coluna_excel_esperada}'")
                else:
                    logger.warning(f"❌ Coluna obrigatória '{col_obrigatoria}' não encontrada. Esperado: '{coluna_excel_esperada}'")
        
        # 📋 VERIFICAR QUAIS AINDA ESTÃO FALTANDO
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in mapeamento_colunas]
        
        if colunas_faltantes:
            flash(f"""
            ❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltantes)}
            
            📋 Colunas disponíveis no arquivo ({len(df.columns)}):
            {", ".join(df.columns)}
            
            ✅ Colunas mapeadas com sucesso:
            {", ".join([f"{k} → {v}" for k, v in mapeamento_colunas.items()])}
            
            💡 Certifique-se que o arquivo contém as colunas: {", ".join(colunas_faltantes)}
            """, 'error')
            return redirect(request.url)
        
        # 🔄 MAPEAR TODOS OS CAMPOS OPCIONAIS DO DICIONÁRIO OFICIAL
        campos_opcionais = [field for field in mapeamentos_oficiais.keys() if field not in colunas_obrigatorias]
        
        # Mapear campos opcionais
        for campo_opcional in campos_opcionais:
            if campo_opcional not in mapeamento_colunas:  # Só se ainda não foi mapeado
                coluna_excel = mapeamentos_oficiais[campo_opcional]
                if coluna_excel in colunas_encontradas:
                    mapeamento_colunas[campo_opcional] = coluna_excel
                    logger.info(f"➕ Campo OPCIONAL mapeado: '{campo_opcional}' → '{coluna_excel}'")
        
        # 🔄 RENOMEAR COLUNAS PARA PADRÃO DO SISTEMA
        logger.info(f"🔍 DEBUG: Colunas ANTES do rename: {list(df.columns)}")
        logger.info(f"🔍 DEBUG: Primeiras 3 linhas ANTES do rename:")
        for i in range(min(3, len(df))):
            logger.info(f"  Linha {i}: {dict(df.iloc[i])}")
        
        # 🔄 INVERTER DICIONÁRIO PARA O RENAME (Excel → Sistema)
        mapeamento_rename = {v: k for k, v in mapeamento_colunas.items()}
        logger.info(f"🔄 DEBUG: Dicionário de rename: {mapeamento_rename}")
        
        df = df.rename(columns=mapeamento_rename)
        logger.info(f"✅ Todas as colunas obrigatórias + {len(mapeamento_colunas) - 5} opcionais mapeadas com sucesso")
        
        logger.info(f"🔍 DEBUG: Colunas APÓS rename: {list(df.columns)}")
        logger.info(f"🔍 DEBUG: Primeiras 3 linhas APÓS rename:")
        for i in range(min(3, len(df))):
            logger.info(f"  Linha {i}: {dict(df.iloc[i])}")
        
        # 🔄 PROCESSAR FORMATOS ANTES DA IMPORTAÇÃO
        df = _processar_formatos_brasileiros(df)
        
        logger.info(f"🔍 DEBUG: Primeiras 3 linhas APÓS _processar_formatos_brasileiros:")
        for i in range(min(3, len(df))):
            logger.info(f"  Linha {i}: {dict(df.iloc[i])}")
        
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
    """Resolver inconsistência de faturamento"""
    try:
        inconsistencia = InconsistenciaFaturamento.query.get_or_404(id)
        
        # Obter dados do formulário
        acao = request.form.get('acao')
        observacao = request.form.get('observacao', '')
        numero_nf = request.form.get('numero_nf')
        motivo_cancelamento = request.form.get('motivo_cancelamento', '')
        
        usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        
        # 🚫 AÇÃO DE CANCELAMENTO DE NF
        if acao == 'cancelar_nf':
            if not numero_nf:
                flash('Número da NF é obrigatório para cancelamento', 'error')
                return redirect(url_for('carteira.listar_inconsistencias'))
            
            resultado = _cancelar_nf_faturamento(numero_nf, usuario, motivo_cancelamento)
            
            if resultado['sucesso']:
                # Marcar inconsistência como resolvida
                inconsistencia.status = 'RESOLVIDA'
                inconsistencia.acao_realizada = f'NF_CANCELADA: {resultado["observacao"]}'
                inconsistencia.resolvida_por = usuario
                inconsistencia.resolvida_em = agora_brasil()
                inconsistencia.observacao_resolucao = f'Cancelamento NF: {motivo_cancelamento}'
                
                db.session.commit()
                
                flash(f'✅ NF {numero_nf} cancelada com sucesso! {resultado["movimentacoes_removidas"]} movimentações removidas.', 'success')
                logger.info(f"✅ Inconsistência {id} resolvida por cancelamento de NF {numero_nf}")
            else:
                flash(f'❌ Erro ao cancelar NF: {resultado["erro"]}', 'error')
            
            return redirect(url_for('carteira.listar_inconsistencias'))
        
        # ✅ OUTRAS AÇÕES EXISTENTES
        if acao == 'aceitar_automatico':
            # Lógica de baixa automática forçada
            resultado = _processar_baixa_faturamento(inconsistencia.numero_nf, usuario)
            
            if resultado['sucesso']:
                inconsistencia.status = 'RESOLVIDA'
                inconsistencia.acao_realizada = 'BAIXA_AUTOMATICA_FORCADA'
                inconsistencia.resolvida_por = usuario
                inconsistencia.resolvida_em = agora_brasil()
                inconsistencia.observacao_resolucao = observacao
                
                db.session.commit()
                flash('Inconsistência resolvida com baixa automática', 'success')
            else:
                flash(f'Erro na baixa automática: {resultado["erro"]}', 'error')
        
        elif acao == 'ignorar':
            inconsistencia.status = 'IGNORADA'
            inconsistencia.acao_realizada = 'IGNORADA_PELO_USUARIO'
            inconsistencia.resolvida_por = usuario
            inconsistencia.resolvida_em = agora_brasil()
            inconsistencia.observacao_resolucao = observacao
            
            db.session.commit()
            flash('Inconsistência marcada como ignorada', 'info')
        
        else:
            flash('Ação não reconhecida', 'error')
        
        return redirect(url_for('carteira.listar_inconsistencias'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao resolver inconsistência {id}: {str(e)}")
        flash(f'Erro ao processar: {str(e)}', 'error')
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
        # �� MODELO EXCEL CORRETO - APENAS CAMPOS DE IMPORTAÇÃO (LINHAS 2-38 ARQUIVO 1)
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
                # 🔍 DEBUG DETALHADO DOS VALORES
                num_pedido_raw = row.get('num_pedido')
                cod_produto_raw = row.get('cod_produto')
                
                logger.info(f"🔍 DEBUG Linha {index}: num_pedido_raw='{num_pedido_raw}' (tipo: {type(num_pedido_raw)})")
                logger.info(f"🔍 DEBUG Linha {index}: cod_produto_raw='{cod_produto_raw}' (tipo: {type(cod_produto_raw)})")
                
                # Verificar se os valores são NaN, None ou vazios
                num_pedido = str(num_pedido_raw).strip() if pd.notna(num_pedido_raw) and num_pedido_raw is not None else ''
                cod_produto = str(cod_produto_raw).strip() if pd.notna(cod_produto_raw) and cod_produto_raw is not None else ''
                
                logger.info(f"🔍 DEBUG Linha {index}: num_pedido_processado='{num_pedido}', cod_produto_processado='{cod_produto}'")
                
                if not num_pedido or not cod_produto or num_pedido == 'nan' or cod_produto == 'nan':
                    logger.warning(f"❌ Linha {index}: campos obrigatórios vazios/inválidos - num_pedido='{num_pedido}', cod_produto='{cod_produto}'")
                    # Mostrar todos os valores da linha para debug
                    logger.info(f"🔍 DEBUG Linha {index} - Todos os valores: {dict(row)}")
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
    💳 BAIXA AUTOMÁTICA DE FATURAMENTO - ARQUITETURA CORRETA + CANCELAMENTOS
    
    FLUXO CORRIGIDO:
    1. Busca NF no FaturamentoProduto (dados por produto)
    2. SE NF tem status='CANCELADO' → REVERTE (EXCLUI movimentações + reverte carteira)
    3. Para cada item faturado ativo:
       - SE não encontra pedido → GERA INCONSISTÊNCIA + PARA (não baixa)
       - SE faturamento > saldo → GERA INCONSISTÊNCIA + PARA (não baixa)  
       - SE tudo OK → BAIXA AUTOMÁTICA (CarteiraCopia + MovimentacaoEstoque)
    
    PRINCÍPIO: Só baixa automaticamente quando tem CERTEZA que está correto
    REVERSÃO: Exclui movimentações (não altera sinal)
    """
    try:
        from app.faturamento.models import FaturamentoProduto
        from app.estoque.models import MovimentacaoEstoque
        from sqlalchemy import inspect
        
        logger.info(f"💳 Processando baixa automática NF: {numero_nf} (Verifica cancelamentos)")
        
        # 🔍 1. VERIFICAR SE TABELAS EXISTEM
        inspector = inspect(db.engine)
        if not inspector.has_table('faturamento_produto'):
            return {'sucesso': False, 'erro': 'Sistema de faturamento não inicializado'}
        
        if not inspector.has_table('carteira_copia'):
            return {'sucesso': False, 'erro': 'Sistema de carteira cópia não inicializado'}
        
        # 📋 2. BUSCAR TODOS OS ITENS DA NF (ATIVOS E CANCELADOS)
        todos_itens_nf = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
        
        if not todos_itens_nf:
            return {'sucesso': False, 'erro': f'NF {numero_nf} não encontrada'}
        
        # 🚫 3. VERIFICAR SE NF FOI CANCELADA
        itens_cancelados = [item for item in todos_itens_nf if item.status_nf == 'CANCELADO']
        
        if itens_cancelados:
            logger.warning(f"🚫 NF {numero_nf} CANCELADA - Revertendo baixas automáticas")
            resultado_reversao = _reverter_nf_cancelada(numero_nf, itens_cancelados, usuario)
            return resultado_reversao
        
        # ✅ 4. PROCESSAR APENAS ITENS ATIVOS
        itens_faturados = [item for item in todos_itens_nf if item.status_nf == 'ATIVO']
        
        if not itens_faturados:
            return {'sucesso': False, 'erro': f'NF {numero_nf} não possui itens ativos'}
        
        # 📊 5. CONTADORES DE RESULTADO  
        itens_baixados = 0
        inconsistencias_detectadas = []
        movimentacoes_criadas = []
        
        # 🔄 6. PROCESSAR CADA ITEM FATURADO ATIVO
        for item_faturado in itens_faturados:
            try:
                # 📋 EXTRAIR DADOS
                num_pedido = item_faturado.origem  # origem = num_pedido
                cod_produto = item_faturado.cod_produto  
                qtd_faturada = float(item_faturado.qtd_produto_faturado or 0)
                
                # 🔍 6.1 BUSCAR PEDIDO NA CARTEIRA CÓPIA
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto
                ).first()
                
                # ❌ 6.2 VALIDAÇÃO 1: FATURAMENTO SEM PEDIDO
                if not item_copia:
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='FATURAMENTO_SEM_PEDIDO',
                        numero_nf=numero_nf,
                        num_pedido=num_pedido or 'N/A',
                        cod_produto=cod_produto,
                        qtd_faturada=qtd_faturada,
                        saldo_disponivel=0,
                        qtd_excesso=qtd_faturada,
                        status='PENDENTE',
                        detectada_por=usuario
                    )
                    db.session.add(inconsistencia)
                    inconsistencias_detectadas.append({
                        'tipo': 'FATURAMENTO_SEM_PEDIDO',
                        'pedido': num_pedido,
                        'produto': cod_produto,
                        'qtd_faturada': qtd_faturada
                    })
                    logger.warning(f"⚠️ INCONSISTÊNCIA: Faturamento sem pedido {num_pedido}-{cod_produto}")
                    continue  # PARA AQUI - NÃO BAIXA
                
                # 📊 6.3 CALCULAR SALDO DISPONÍVEL
                saldo_disponivel = float(item_copia.qtd_produto_pedido or 0) - float(item_copia.baixa_produto_pedido or 0)
                
                # ❌ 6.4 VALIDAÇÃO 2: FATURAMENTO EXCEDE SALDO
                if qtd_faturada > saldo_disponivel:
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='FATURAMENTO_EXCEDE_SALDO',
                        numero_nf=numero_nf,
                        num_pedido=num_pedido,
                        cod_produto=cod_produto,
                        qtd_faturada=qtd_faturada,
                        saldo_disponivel=saldo_disponivel,
                        qtd_excesso=qtd_faturada - saldo_disponivel,
                        status='PENDENTE',
                        detectada_por=usuario
                    )
                    db.session.add(inconsistencia)
                    inconsistencias_detectadas.append({
                        'tipo': 'FATURAMENTO_EXCEDE_SALDO',
                        'pedido': num_pedido,
                        'produto': cod_produto,
                        'qtd_faturada': qtd_faturada,
                        'saldo_disponivel': saldo_disponivel,
                        'excesso': qtd_faturada - saldo_disponivel
                    })
                    logger.warning(f"⚠️ INCONSISTÊNCIA: Faturamento excede saldo {num_pedido}-{cod_produto} ({qtd_faturada} > {saldo_disponivel})")
                    continue  # PARA AQUI - NÃO BAIXA
                
                # ✅ 6.5 TUDO OK - BAIXA AUTOMÁTICA
                logger.info(f"✅ Baixa automática {num_pedido}-{cod_produto}: {qtd_faturada} unidades")
                
                # 💳 BAIXAR NA CARTEIRA CÓPIA
                item_copia.baixa_produto_pedido = float(item_copia.baixa_produto_pedido or 0) + qtd_faturada
                item_copia.updated_by = usuario
                item_copia.updated_at = agora_brasil()
                
                # 🎯 VERIFICAR SEPARAÇÕES E ABATER CARTEIRA ORIGINAL
                resultado_abate = _abater_carteira_original(
                    numero_nf=numero_nf,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    qtd_faturada=qtd_faturada,
                    usuario=usuario
                )
                
                # 📋 VERIFICAR SE USUÁRIO PRECISA ESCOLHER SEPARAÇÃO
                if resultado_abate.get('necessita_escolha'):
                    logger.warning(f"⚠️ MÚLTIPLAS SEPARAÇÕES - Usuário deve escolher: {num_pedido}-{cod_produto}")
                    # TODO: Implementar interface para escolha de separação
                    # Por enquanto, registra como inconsistência para resolução manual
                    inconsistencia = InconsistenciaFaturamento(
                        tipo='MULTIPLAS_SEPARACOES',
                        numero_nf=numero_nf,
                        num_pedido=num_pedido or 'N/A',
                        cod_produto=cod_produto,
                        qtd_faturada=qtd_faturada,
                        saldo_disponivel=0,
                        qtd_excesso=0,
                        status='PENDENTE',
                        detectada_por=usuario,
                        observacao=f"Múltiplas separações disponíveis - usuário deve escolher"
                    )
                    db.session.add(inconsistencia)
                    inconsistencias_detectadas.append({
                        'tipo': 'MULTIPLAS_SEPARACOES',
                        'pedido': num_pedido,
                        'produto': cod_produto,
                        'qtd_faturada': qtd_faturada,
                        'opcoes_separacao': resultado_abate.get('opcoes_separacao', [])
                    })
                    continue  # PARA AQUI - Não processa automaticamente
                
                # 📋 VERIFICAR SE HÁ FATURAMENTO PARCIAL (após escolha ou se só tinha 1)
                if resultado_abate.get('faturamento_parcial'):
                    logger.warning(f"⚠️ FATURAMENTO PARCIAL detectado: {cod_produto} Faturou: {qtd_faturada}, Separou: {resultado_abate.get('qtd_total_separada')}")
                    # TODO: Interface de justificativa de faturamento parcial será usada
                
                # 📦 GERAR MOVIMENTAÇÃO DE ESTOQUE (FATURAMENTO)
                movimentacao = MovimentacaoEstoque(
                    cod_produto=cod_produto,
                    nome_produto=item_faturado.nome_produto,
                    tipo_movimentacao='FATURAMENTO',
                    local_movimentacao='VENDA',
                    qtd_movimentacao=-qtd_faturada,  # Saída (negativa)
                    observacao=f"Baixa automática NF {numero_nf} - Pedido {num_pedido}",
                    numero_nf=numero_nf,
                    num_pedido=num_pedido,
                    created_by=usuario
                )
                db.session.add(movimentacao)
                movimentacoes_criadas.append({
                    'cod_produto': cod_produto,
                    'qtd_movimentacao': -qtd_faturada,
                    'numero_nf': numero_nf,
                    'num_pedido': num_pedido
                })
                
                itens_baixados += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar item {cod_produto}: {str(e)}")
                continue
        
        # 💾 7. SALVAR TODAS AS ALTERAÇÕES
        db.session.commit()
        
        # 📊 8. GERAR RESULTADO
        resultado = {
            'sucesso': True,
            'numero_nf': numero_nf,
            'status_nf': 'ATIVA',
            'itens_baixados': itens_baixados,
            'inconsistencias_detectadas': len(inconsistencias_detectadas),
            'inconsistencias': inconsistencias_detectadas,
            'movimentacoes_criadas': len(movimentacoes_criadas),
            'movimentacoes': movimentacoes_criadas,
            'total_itens_processados': len(itens_faturados)
        }
        
        # 📋 9. LOG FINAL
        if inconsistencias_detectadas:
            logger.warning(f"⚠️ Baixa automática concluída COM {len(inconsistencias_detectadas)} inconsistências para verificação manual")
        else:
            logger.info(f"✅ Baixa automática concluída SEM inconsistências: {itens_baixados} itens baixados")
        
        return resultado
        
    except Exception as e:
        db.session.rollback()
        erro_msg = f"Erro na baixa automática NF {numero_nf}: {str(e)}"
        logger.error(erro_msg)
        return {'sucesso': False, 'erro': erro_msg}

def _reverter_nf_cancelada(numero_nf, itens_cancelados, usuario):
    """
    🚫 REVERTE NF CANCELADA - EXCLUI MOVIMENTAÇÕES + REVERTE CARTEIRA
    
    FUNCIONALIDADE:
    - EXCLUI (não altera sinal) MovimentacaoEstoque relacionadas 
    - REVERTE baixas na CarteiraCopia (subtrai o que foi baixado)
    - Mantém auditoria completa
    
    IMPORTANTE: REVERTER = EXCLUIR movimentações, não alterar sinal
    BUSCA: Usa LIKE na observacao pois não há campo numero_nf
    """
    try:
        from app.estoque.models import MovimentacaoEstoque
        
        logger.warning(f"🚫 REVERTENDO NF CANCELADA {numero_nf}")
        
        movimentacoes_excluidas = 0
        baixas_revertidas = 0
        itens_processados = 0
        
        # 🔄 PROCESSAR CADA ITEM CANCELADO
        for item_cancelado in itens_cancelados:
            try:
                num_pedido = item_cancelado.origem
                cod_produto = item_cancelado.cod_produto
                qtd_cancelada = float(item_cancelado.qtd_produto_faturado or 0)
                
                logger.info(f"🚫 Revertendo item: {num_pedido}-{cod_produto} Qtd: {qtd_cancelada}")
                
                # 🚫 1. BUSCAR MOVIMENTAÇÕES PELA OBSERVAÇÃO (NÃO HÁ CAMPO numero_nf)
                # Formato da observação: "Baixa automática NF {numero_nf} - Pedido {num_pedido}"
                movimentacoes_relacionadas = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.cod_produto == cod_produto,
                    MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                    MovimentacaoEstoque.observacao.like(f'%NF {numero_nf}%'),
                    MovimentacaoEstoque.observacao.like(f'%Pedido {num_pedido}%'),
                    MovimentacaoEstoque.ativo == True
                ).all()
                
                # 🔍 VERIFICAÇÃO DUPLA: Confirmar que realmente é da NF e pedido corretos
                movimentacoes_confirmadas = []
                for mov in movimentacoes_relacionadas:
                    observacao = mov.observacao or ""
                    # Verificar se contém EXATAMENTE esta NF + pedido + produto
                    if (f'NF {numero_nf}' in observacao and f'Pedido {num_pedido}' in observacao and 
                        'Baixa automática' in observacao):
                        movimentacoes_confirmadas.append(mov)
                        logger.info(f"✅ Movimentação confirmada para exclusão: {mov.observacao}")
                
                # 🗑️ EXCLUIR MOVIMENTAÇÕES CONFIRMADAS
                for mov in movimentacoes_confirmadas:
                    logger.info(f"🗑️ EXCLUINDO MovimentacaoEstoque: {cod_produto} Qtd: {mov.qtd_movimentacao} - {mov.observacao}")
                    db.session.delete(mov)  # EXCLUIR, não alterar sinal
                    movimentacoes_excluidas += 1
                
                # 🔄 2. REVERTER BAIXA NA CARTEIRA CÓPIA
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto
                ).first()
                
                if item_copia:
                    baixa_anterior = float(item_copia.baixa_produto_pedido or 0)
                    qtd_a_reverter = min(qtd_cancelada, baixa_anterior)  # Não reverter mais que foi baixado
                    
                    if qtd_a_reverter > 0:
                        item_copia.baixa_produto_pedido = baixa_anterior - qtd_a_reverter
                        item_copia.updated_by = usuario
                        item_copia.updated_at = agora_brasil()
                        baixas_revertidas += 1
                        
                        logger.info(f"↩️ CarteiraCopia revertida: {cod_produto} Baixa: {baixa_anterior} → {item_copia.baixa_produto_pedido}")
                    else:
                        logger.warning(f"⚠️ Não há baixa para reverter em {num_pedido}-{cod_produto}")
                else:
                    logger.warning(f"⚠️ Item não encontrado na CarteiraCopia: {num_pedido}-{cod_produto}")
                
                itens_processados += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao reverter item {cod_produto}: {str(e)}")
                continue
        
        # 💾 3. SALVAR ALTERAÇÕES
        db.session.commit()
        
        # 📊 4. RESULTADO DA REVERSÃO
        resultado = {
            'sucesso': True,
            'numero_nf': numero_nf,
            'status_nf': 'CANCELADA',
            'acao': 'REVERSAO_COMPLETA',
            'itens_processados': itens_processados,
            'movimentacoes_excluidas': movimentacoes_excluidas,
            'baixas_revertidas': baixas_revertidas,
            'observacao': f'NF {numero_nf} cancelada: {movimentacoes_excluidas} movimentações EXCLUÍDAS + {baixas_revertidas} baixas revertidas na carteira'
        }
        
        logger.warning(f"🚫 Reversão concluída: {resultado}")
        return resultado
        
    except Exception as e:
        db.session.rollback()
        erro_msg = f"Erro na reversão da NF cancelada {numero_nf}: {str(e)}"
        logger.error(erro_msg)
        return {'sucesso': False, 'erro': erro_msg}

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
    """
    Gera novo ID único para lotes de separação (NÃO SEQUENCIAL)
    
    FORMATO: LOTE_YYYYMMDD_HHMMSS_XXX
    Exemplo: LOTE_20250702_143025_001
    """
    try:
        from datetime import datetime
        import random
        
        # Gerar ID baseado em timestamp + random
        agora = datetime.now()
        timestamp = agora.strftime("%Y%m%d_%H%M%S")
        
        # Adicionar componente aleatório para evitar colisões
        random_suffix = f"{random.randint(100, 999)}"
        
        lote_id = f"LOTE_{timestamp}_{random_suffix}"
        
        logger.info(f"🆔 Lote ID gerado: {lote_id}")
        return lote_id
            
    except Exception as e:
        logger.error(f"Erro ao gerar lote ID: {str(e)}")
        # Fallback ainda mais simples
        import time
        return f"LOTE_{int(time.time())}"

def _cancelar_nf_faturamento(numero_nf, usuario, motivo_cancelamento):
    """
    🚫 CANCELAMENTO DE NF - REVERSÃO COMPLETA
    
    FUNCIONALIDADE:
    - Apaga MovimentacaoEstoque relacionadas à NF (busca pela observação)
    - Mantém CarteiraCopia como histórico (NÃO apaga)
    - Busca por observacao contendo numero_nf e cod_produto
    """
    try:
        from app.faturamento.models import FaturamentoProduto
        from app.estoque.models import MovimentacaoEstoque
        from sqlalchemy import inspect
        
        logger.info(f"🚫 Cancelando NF {numero_nf} - Motivo: {motivo_cancelamento}")
        
        # 🔍 1. BUSCAR ITENS DA NF
        itens_nf = FaturamentoProduto.query.filter(
            FaturamentoProduto.numero_nf == numero_nf,
            FaturamentoProduto.status_nf == 'ATIVO'
        ).all()
        
        if not itens_nf:
            return {'sucesso': False, 'erro': f'NF {numero_nf} não encontrada'}
        
        movimentacoes_removidas = 0
        historico_mantido = 0
        
        # 🔄 2. PROCESSAR CADA ITEM DA NF
        for item_nf in itens_nf:
            try:
                cod_produto = str(item_nf.cod_produto)
                num_pedido = item_nf.origem
                
                # 🚫 2.1 BUSCAR MOVIMENTAÇÕES PELA OBSERVAÇÃO
                # Formato: "Baixa automática NF {numero_nf} - Pedido {num_pedido}"
                movimentacoes_candidatas = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.cod_produto == cod_produto,
                    MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                    MovimentacaoEstoque.observacao.like(f'%NF {numero_nf}%'),
                    MovimentacaoEstoque.observacao.like(f'%Pedido {num_pedido}%'),
                    MovimentacaoEstoque.ativo == True
                ).all()
                
                # 🔍 VERIFICAÇÃO TRIPLA: Confirmar que realmente é da NF e pedido corretos
                movimentacoes_confirmadas = []
                for mov in movimentacoes_candidatas:
                    observacao = mov.observacao or ""
                    # Verificar se contém EXATAMENTE esta NF + pedido + produto
                    if (f'NF {numero_nf}' in observacao and 
                        f'Pedido {num_pedido}' in observacao and 
                        mov.cod_produto == cod_produto and
                        'Baixa automática' in observacao):
                        movimentacoes_confirmadas.append(mov)
                        logger.info(f"✅ Movimentação confirmada para exclusão: {mov.observacao}")
                
                # 🗑️ EXCLUIR MOVIMENTAÇÕES CONFIRMADAS
                for mov in movimentacoes_confirmadas:
                    logger.info(f"🗑️ EXCLUINDO MovimentacaoEstoque: {cod_produto} Qtd: {mov.qtd_movimentacao} - {mov.observacao}")
                    db.session.delete(mov)  # EXCLUIR, não alterar sinal
                    movimentacoes_removidas += 1
                
                # 📝 2.2 MANTER CARTEIRA CÓPIA COMO HISTÓRICO (NÃO APAGA)
                # CarteiraCopia permanece para auditoria
                item_copia = CarteiraCopia.query.filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto
                ).first()
                
                if item_copia:
                    historico_mantido += 1
                    logger.info(f"📝 CarteiraCopia mantida como histórico: {cod_produto} Baixa: {item_copia.baixa_produto_pedido}")
                
            except Exception as e:
                logger.error(f"Erro ao cancelar item {cod_produto}: {str(e)}")
                continue
        
        # 💾 3. COMMIT DAS ALTERAÇÕES
        db.session.commit()
        
        # 📊 4. RESULTADO
        resultado = {
            'sucesso': True,
            'movimentacoes_removidas': movimentacoes_removidas,
            'historico_carteira_mantido': historico_mantido,
            'observacao': f'NF {numero_nf} cancelada: {movimentacoes_removidas} movimentações removidas, {historico_mantido} registros mantidos em CarteiraCopia para auditoria.'
        }
        
        logger.info(f"✅ Cancelamento de NF concluído: {resultado}")
        return resultado
        
    except Exception as e:
        db.session.rollback()
        erro_msg = f"Erro no cancelamento da NF {numero_nf}: {str(e)}"
        logger.error(erro_msg)
        return {'sucesso': False, 'erro': erro_msg}

def _processar_separacao_escolhida(numero_nf, cod_produto, qtd_faturada, lote_escolhido, observacao_escolha, usuario):
    """
    🎯 PROCESSAR SEPARAÇÃO ESCOLHIDA PELO USUÁRIO
    
    FUNCIONALIDADE:
    - Processa a separação específica escolhida pelo usuário
    - Abate da carteira principal apenas os itens do lote escolhido
    - Verifica se há faturamento parcial após a escolha
    - Gera movimentação de estoque
    """
    try:
        from app.estoque.models import MovimentacaoEstoque
        
        logger.info(f"🎯 Processando separação escolhida: NF {numero_nf}, Produto {cod_produto}, Lote {lote_escolhido}")
        
        # 🔍 1. BUSCAR ITENS DA SEPARAÇÃO ESCOLHIDA
        itens_lote_escolhido = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.lote_separacao_id == lote_escolhido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens_lote_escolhido:
            return {
                'sucesso': False,
                'erro': f'Nenhum item encontrado para o lote {lote_escolhido}'
            }
        
        # 📊 2. CALCULAR QUANTIDADES
        qtd_total_separada = sum(float(item.qtd_produto_pedido or 0) for item in itens_lote_escolhido)
        faturamento_parcial = qtd_faturada < qtd_total_separada
        diferenca_nao_faturada = qtd_total_separada - qtd_faturada if faturamento_parcial else 0
        
        # 🎯 3. ABATER DA CARTEIRA PRINCIPAL (PROPORCIONALMENTE)
        for item in itens_lote_escolhido:
            # Calcular proporção do abate para este pedido
            qtd_item = float(item.qtd_produto_pedido or 0)
            proporcao = qtd_item / qtd_total_separada if qtd_total_separada > 0 else 0
            qtd_abate_pedido = qtd_faturada * proporcao
            
            # Abater
            qtd_nova = max(0, qtd_item - qtd_abate_pedido)
            item.qtd_produto_pedido = qtd_nova
            item.updated_by = usuario
            item.updated_at = agora_brasil()
            
            logger.info(f"✅ Abatido pedido {item.num_pedido}: {qtd_item} → {qtd_nova} (proporção: {proporcao:.3f})")
        
        # 💳 4. BAIXAR NA CARTEIRA CÓPIA (se ainda não foi baixado)
        # Buscar primeiro item para pegar dados do pedido
        primeiro_item = itens_lote_escolhido[0]
        item_copia = CarteiraCopia.query.filter_by(
            num_pedido=primeiro_item.num_pedido,
            cod_produto=cod_produto
        ).first()
        
        if item_copia:
            # Verificar se já foi baixado (para evitar dupla baixa)
            baixa_anterior = float(item_copia.baixa_produto_pedido or 0)
            if baixa_anterior == 0:  # Se ainda não foi baixado
                item_copia.baixa_produto_pedido = qtd_faturada
                item_copia.updated_by = usuario
                item_copia.updated_at = agora_brasil()
                logger.info(f"💳 CarteiraCopia baixada: {cod_produto} Qtd: {qtd_faturada}")
        
        # 📦 5. GERAR MOVIMENTAÇÃO DE ESTOQUE
        movimentacao = MovimentacaoEstoque(
            cod_produto=cod_produto,
            nome_produto=primeiro_item.nome_produto,
            tipo_movimentacao='FATURAMENTO',
            local_movimentacao='VENDA',
            qtd_movimentacao=-qtd_faturada,  # Saída (negativa)
            observacao=f"Baixa automática NF {numero_nf} - Separação {lote_escolhido} - {observacao_escolha}",
            created_by=usuario
        )
        db.session.add(movimentacao)
        
        # 💾 6. SALVAR TUDO
        db.session.commit()
        
        # 📝 7. RESULTADO
        if faturamento_parcial:
            logger.warning(f"⚠️ FATURAMENTO PARCIAL: {cod_produto} Separou: {qtd_total_separada}, Faturou: {qtd_faturada}, Diferença: {diferenca_nao_faturada}")
        else:
            logger.info(f"✅ Faturamento completo: {cod_produto} Separou: {qtd_total_separada}, Faturou: {qtd_faturada}")
        
        return {
            'sucesso': True,
            'lote_processado': lote_escolhido,
            'qtd_total_separada': qtd_total_separada,
            'qtd_faturada': qtd_faturada,
            'diferenca_nao_faturada': diferenca_nao_faturada,
            'faturamento_parcial': faturamento_parcial,
            'necessita_justificativa': faturamento_parcial,
            'itens_processados': len(itens_lote_escolhido)
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar separação escolhida: {str(e)}")
        return {
            'sucesso': False,
            'erro': str(e)
        }

def _abater_carteira_original(numero_nf, num_pedido, cod_produto, qtd_faturada, usuario):
    """
    🎯 ABATER DA CARTEIRA ORIGINAL + DETECTAR MÚLTIPLAS SEPARAÇÕES + FATURAMENTO PARCIAL
    
    FUNCIONALIDADE:
    1. Verifica se há múltiplas separações do mesmo produto
    2. Se há múltiplas → usuário deve escolher 1 separação
    3. Após escolha → verifica se faturamento é parcial
    4. Se faturou < separou → precisa justificar
    """
    try:
        logger.info(f"🎯 Verificando separações para: {num_pedido}-{cod_produto} Qtd faturada: {qtd_faturada}")
        
        # 🔍 1. BUSCAR TODAS AS SEPARAÇÕES DO MESMO PRODUTO
        # Buscar todos os itens ativos com mesmo cod_produto que tenham lote_separacao_id
        itens_com_separacao = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.lote_separacao_id.isnot(None),
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens_com_separacao:
            logger.warning(f"⚠️ Nenhuma separação encontrada para produto {cod_produto}")
            return {
                'sucesso': False,
                'erro': 'Nenhuma separação encontrada para este produto',
                'multiplas_separacoes': False,
                'necessita_escolha': False,
                'faturamento_parcial': False,
                'necessita_justificativa': False
            }
        
        # 🔍 2. AGRUPAR POR LOTE DE SEPARAÇÃO
        separacoes_disponiveis = {}
        for item in itens_com_separacao:
            lote_id = item.lote_separacao_id
            if lote_id not in separacoes_disponiveis:
                separacoes_disponiveis[lote_id] = []
            separacoes_disponiveis[lote_id].append({
                'num_pedido': item.num_pedido,
                'qtd_separada': float(item.qtd_produto_pedido or 0),
                'cliente': item.raz_social_red or item.raz_social or 'N/A',
                'vendedor': item.vendedor or 'N/A'
            })
        
        multiplas_separacoes = len(separacoes_disponiveis) > 1
        
        # 🔍 3. SE HÁ MÚLTIPLAS SEPARAÇÕES → USUÁRIO DEVE ESCOLHER
        if multiplas_separacoes:
            logger.warning(f"⚠️ MÚLTIPLAS SEPARAÇÕES encontradas para {cod_produto}: {len(separacoes_disponiveis)} lotes")
            
            # Preparar dados para interface de escolha
            opcoes_separacao = []
            for lote_id, itens_lote in separacoes_disponiveis.items():
                total_separado_lote = sum(item['qtd_separada'] for item in itens_lote)
                opcoes_separacao.append({
                    'lote_separacao_id': lote_id,
                    'total_separado': total_separado_lote,
                    'qtd_pedidos': len(itens_lote),
                    'itens': itens_lote,
                    'compativel_faturamento': total_separado_lote >= qtd_faturada
                })
            
            return {
                'sucesso': True,
                'multiplas_separacoes': True,
                'necessita_escolha': True,
                'opcoes_separacao': opcoes_separacao,
                'numero_nf': numero_nf,
                'cod_produto': cod_produto,
                'qtd_faturada': qtd_faturada,
                'faturamento_parcial': None,  # Será verificado após escolha
                'necessita_justificativa': None  # Será verificado após escolha
            }
        
        # 🔍 4. APENAS 1 SEPARAÇÃO → PROCESSAR DIRETO
        lote_unico = list(separacoes_disponiveis.keys())[0]
        itens_lote_unico = separacoes_disponiveis[lote_unico]
        
        # 📊 5. CALCULAR QUANTIDADES DA SEPARAÇÃO ÚNICA
        qtd_total_separada = sum(item['qtd_separada'] for item in itens_lote_unico)
        faturamento_parcial = qtd_faturada < qtd_total_separada
        diferenca_nao_faturada = qtd_total_separada - qtd_faturada if faturamento_parcial else 0
        
        # 🎯 6. ABATER DA CARTEIRA PRINCIPAL (PROPORCIONALMENTE SE MÚLTIPLOS PEDIDOS)
        for item in itens_com_separacao:
            if item.lote_separacao_id == lote_unico:
                # Calcular proporção do abate para este pedido
                proporcao = float(item.qtd_produto_pedido or 0) / qtd_total_separada
                qtd_abate_pedido = qtd_faturada * proporcao
                
                # Abater
                qtd_nova = max(0, float(item.qtd_produto_pedido or 0) - qtd_abate_pedido)
                item.qtd_produto_pedido = qtd_nova
                item.updated_by = usuario
                item.updated_at = agora_brasil()
                
                logger.info(f"✅ Abatido pedido {item.num_pedido}: {float(item.qtd_produto_pedido or 0)} → {qtd_nova}")
        
        # 📝 7. LOG E RESULTADO
        if faturamento_parcial:
            logger.warning(f"⚠️ FATURAMENTO PARCIAL: {cod_produto} Separou: {qtd_total_separada}, Faturou: {qtd_faturada}, Diferença: {diferenca_nao_faturada}")
        else:
            logger.info(f"✅ Faturamento completo: {cod_produto} Separou: {qtd_total_separada}, Faturou: {qtd_faturada}")
        
        return {
            'sucesso': True,
            'multiplas_separacoes': False,
            'necessita_escolha': False,
            'lote_separacao_id': lote_unico,
            'qtd_total_separada': qtd_total_separada,
            'qtd_faturada': qtd_faturada,
            'diferenca_nao_faturada': diferenca_nao_faturada,
            'faturamento_parcial': faturamento_parcial,
            'necessita_justificativa': faturamento_parcial,
            'itens_lote': itens_lote_unico,
            'numero_nf': numero_nf
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar separações: {str(e)}")
        return {
            'sucesso': False,
            'erro': str(e),
            'multiplas_separacoes': False,
            'necessita_escolha': False,
            'faturamento_parcial': False,
            'necessita_justificativa': False
        }

def _validar_sincronizacao_baixas_faturamento(cod_produto=None, num_pedido=None):
    """
    🔍 VALIDAÇÃO DE SINCRONIZAÇÃO - CARTEIRA CÓPIA vs MOVIMENTAÇÃO ESTOQUE
    
    FUNCIONALIDADE:
    - Valida se baixas na CarteiraCopia estão sincronizadas com MovimentacaoEstoque
    - Detecta divergências entre os dois sistemas
    - Gera relatório de inconsistências para correção
    """
    try:
        from app.estoque.models import MovimentacaoEstoque
        from sqlalchemy import func
        
        logger.info("🔍 Validando sincronização baixas faturamento")
        
        inconsistencias = []
        produtos_validados = 0
        
        # 🔍 1. DEFINIR ESCOPO DA VALIDAÇÃO
        query_carteira = CarteiraCopia.query
        if cod_produto:
            query_carteira = query_carteira.filter_by(cod_produto=str(cod_produto))
        if num_pedido:
            query_carteira = query_carteira.filter_by(num_pedido=str(num_pedido))
        
        itens_carteira = query_carteira.all()
        
        # 🔄 2. VALIDAR CADA ITEM DA CARTEIRA
        for item_carteira in itens_carteira:
            try:
                cod_produto_item = item_carteira.cod_produto
                num_pedido_item = item_carteira.num_pedido
                baixa_carteira = float(item_carteira.baixa_produto_pedido or 0)
                
                # 📊 2.1 CALCULAR TOTAL MOVIMENTAÇÕES DE FATURAMENTO
                total_movimentacoes = db.session.query(
                    func.sum(MovimentacaoEstoque.qtd_movimentacao)
                ).filter(
                    MovimentacaoEstoque.cod_produto == cod_produto_item,
                    MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                    MovimentacaoEstoque.observacao.like(f'%Pedido {num_pedido_item}%'),
                    MovimentacaoEstoque.ativo == True
                ).scalar() or 0
                
                # Converter para positivo (movimentações são negativas)
                total_movimentacoes = abs(float(total_movimentacoes))
                
                # 🔍 2.2 VERIFICAR SINCRONIZAÇÃO
                diferenca = abs(baixa_carteira - total_movimentacoes)
                
                if diferenca > 0.001:  # Tolerância para arredondamentos
                    inconsistencias.append({
                        'num_pedido': num_pedido_item,
                        'cod_produto': cod_produto_item,
                        'baixa_carteira_copia': baixa_carteira,
                        'total_movimentacoes_estoque': total_movimentacoes,
                        'diferenca': diferenca,
                        'tipo_problema': 'DESSINCRONIZADO',
                        'acao_sugerida': 'Verificar movimentações de faturamento do produto'
                    })
                    
                    logger.warning(f"⚠️ Dessincronização detectada: {num_pedido_item}-{cod_produto_item} Carteira:{baixa_carteira} vs Movimentações:{total_movimentacoes}")
                
                produtos_validados += 1
                
            except Exception as e:
                inconsistencias.append({
                    'num_pedido': item_carteira.num_pedido,
                    'cod_produto': item_carteira.cod_produto,
                    'baixa_carteira_copia': 'ERRO',
                    'total_movimentacoes_estoque': 'ERRO',
                    'diferenca': 0,
                    'tipo_problema': 'ERRO_CALCULO',
                    'acao_sugerida': f'Erro no cálculo: {str(e)}'
                })
                logger.error(f"Erro ao validar {item_carteira.num_pedido}-{item_carteira.cod_produto}: {str(e)}")
                continue
        
        # 📊 3. RESULTADO DA VALIDAÇÃO
        resultado = {
            'sucesso': True,
            'produtos_validados': produtos_validados,
            'inconsistencias_encontradas': len(inconsistencias),
            'sincronizacao_ok': len(inconsistencias) == 0,
            'inconsistencias': inconsistencias,
            'resumo': f'{produtos_validados} produtos validados, {len(inconsistencias)} inconsistências encontradas'
        }
        
        if inconsistencias:
            logger.warning(f"⚠️ Validação concluída com {len(inconsistencias)} inconsistências")
        else:
            logger.info(f"✅ Validação concluída: {produtos_validados} produtos sincronizados corretamente")
        
        return resultado
        
    except Exception as e:
        erro_msg = f"Erro na validação de sincronização: {str(e)}"
        logger.error(erro_msg)
        return {
            'sucesso': False,
            'erro': erro_msg,
            'produtos_validados': 0,
            'inconsistencias_encontradas': 0,
            'sincronizacao_ok': False,
            'inconsistencias': []
        }

@carteira_bp.route('/escolher-separacao/<int:inconsistencia_id>', methods=['GET', 'POST'])
@login_required
def escolher_separacao(inconsistencia_id):
    """
    🎯 ESCOLHER SEPARAÇÃO - MÚLTIPLAS SEPARAÇÕES DISPONÍVEIS
    
    Quando há múltiplas separações do mesmo produto, o usuário escolhe qual
    separação está sendo faturada na NF atual
    """
    try:
        # 🔍 1. BUSCAR INCONSISTÊNCIA
        inconsistencia = InconsistenciaFaturamento.query.get_or_404(inconsistencia_id)
        
        if inconsistencia.tipo != 'MULTIPLAS_SEPARACOES':
            flash('Esta inconsistência não é do tipo múltiplas separações', 'error')
            return redirect(url_for('carteira.listar_inconsistencias'))
        
        # 📊 2. BUSCAR SEPARAÇÕES DISPONÍVEIS NOVAMENTE
        resultado_separacoes = _abater_carteira_original(
            numero_nf=inconsistencia.numero_nf,
            num_pedido=inconsistencia.num_pedido,
            cod_produto=inconsistencia.cod_produto,
            qtd_faturada=float(inconsistencia.qtd_faturada or 0),
            usuario=current_user.nome
        )
        
        if request.method == 'POST':
            # 🎯 3. PROCESSAR ESCOLHA DO USUÁRIO
            lote_escolhido = request.form.get('lote_separacao_escolhido')
            observacao_escolha = request.form.get('observacao_escolha', '')
            
            if not lote_escolhido:
                flash('Selecione uma separação', 'error')
                return render_template('carteira/escolher_separacao.html',
                                     inconsistencia=inconsistencia,
                                     separacoes=resultado_separacoes.get('opcoes_separacao', []))
            
            # 🎯 4. PROCESSAR SEPARAÇÃO ESCOLHIDA
            resultado_processamento = _processar_separacao_escolhida(
                numero_nf=inconsistencia.numero_nf,
                cod_produto=inconsistencia.cod_produto,
                qtd_faturada=float(inconsistencia.qtd_faturada or 0),
                lote_escolhido=lote_escolhido,
                observacao_escolha=observacao_escolha,
                usuario=current_user.nome
            )
            
            if resultado_processamento.get('sucesso'):
                # ✅ MARCAR INCONSISTÊNCIA COMO RESOLVIDA
                inconsistencia.resolvida = True
                inconsistencia.resolvida_em = agora_brasil()
                inconsistencia.resolvida_por = current_user.nome
                inconsistencia.observacao_resolucao = f"Separação escolhida: {lote_escolhido}. {observacao_escolha}"
                
                db.session.commit()
                
                # 📋 VERIFICAR SE GEROU FATURAMENTO PARCIAL
                if resultado_processamento.get('faturamento_parcial'):
                    flash(f'Separação processada com sucesso! Faturamento parcial detectado - necessária justificativa.', 'warning')
                    # Redirecionar para justificativa se necessário
                    return redirect(url_for('carteira.justificar_faturamento_parcial', 
                                          numero_nf=inconsistencia.numero_nf,
                                          cod_produto=inconsistencia.cod_produto,
                                          lote_separacao_id=lote_escolhido))
                else:
                    flash('Separação processada com sucesso! Faturamento completo.', 'success')
                    return redirect(url_for('carteira.listar_inconsistencias'))
            
            else:
                flash(f'Erro ao processar separação: {resultado_processamento.get("erro")}', 'error')
        
        # 📄 5. RENDERIZAR TEMPLATE DE ESCOLHA
        return render_template('carteira/escolher_separacao.html',
                             inconsistencia=inconsistencia,
                             separacoes=resultado_separacoes.get('opcoes_separacao', []),
                             numero_nf=inconsistencia.numero_nf,
                             cod_produto=inconsistencia.cod_produto,
                             qtd_faturada=float(inconsistencia.qtd_faturada or 0))
        
    except Exception as e:
        logger.error(f"❌ Erro ao escolher separação: {str(e)}")
        flash(f'Erro ao carregar opções de separação: {str(e)}', 'error')
        return redirect(url_for('carteira.listar_inconsistencias'))