"""
Rotas para interface de importação TagPlus
Inclui importação via API e via Excel
"""
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta, date
from app import db
from app.integracoes.tagplus.importador_simplificado import ImportadorTagPlus
from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus
from app.integracoes.tagplus.postman_helper import PostmanHelper
from app.integracoes.tagplus.servico_importacao_excel import processar_arquivo_tagplus_web
from app.faturamento.models import FaturamentoProduto
from app.embarques.models import Embarque, EmbarqueItem
from app.carteira.models import CarteiraCopia
from sqlalchemy import and_
import os
import tempfile
import traceback
import logging

logger = logging.getLogger(__name__)

tagplus_bp = Blueprint('tagplus', __name__, url_prefix='/integracoes/tagplus')

@tagplus_bp.route('/importacao')
@login_required
def pagina_importacao():
    """Página de importação TagPlus"""
    return render_template('integracoes/tagplus_importacao.html', 
                         date=date, 
                         timedelta=timedelta)

@tagplus_bp.route('/api/testar-conexao', methods=['POST'])
@login_required
def testar_conexao():
    """Testa conexão com TagPlus"""
    try:
        dados = request.get_json()
        usuario = dados.get('usuario', 'rayssa')
        senha = dados.get('senha', 'A12345')
        api_key = dados.get('api_key')
        client_id = dados.get('client_id')
        client_secret = dados.get('client_secret')
        access_token = dados.get('access_token')
        refresh_token = dados.get('refresh_token')
        
        # Se temos access_token, usa autenticação Bearer
        if access_token:
            from app.integracoes.tagplus.auth_bearer import TagPlusAuthBearer
            auth = TagPlusAuthBearer(
                client_id=client_id,
                client_secret=client_secret,
                access_token=access_token,
                refresh_token=refresh_token
            )
            sucesso, info = auth.testar_conexao()
        else:
            # Tenta outros métodos
            importador = ImportadorTagPlus(usuario, senha, api_key, client_id, client_secret)
            sucesso, info = importador.testar_conexao()
        
        if sucesso:
            return jsonify({
                'success': True,
                'mensagem': 'Conexão estabelecida com sucesso!',
                'info': info
            })
        else:
            # Mensagem mais clara sobre o erro
            if 'authentication plugin' in str(info) or '401' in str(info):
                erro = (
                    'Erro de autenticação com TagPlus. '
                    'Você precisa autorizar a aplicação primeiro. '
                    'Use o botão "Autorizar Aplicação" para obter os tokens.'
                )
            else:
                erro = f'Falha na conexão: {info}'
                
            return jsonify({
                'success': False,
                'erro': erro
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/importar-clientes', methods=['POST'])
@login_required
def importar_clientes():
    """Importa clientes do TagPlus"""
    try:
        dados = request.get_json()
        usuario = dados.get('usuario', 'rayssa')
        senha = dados.get('senha', 'A12345')
        limite = dados.get('limite')  # None = todos
        api_key = dados.get('api_key')
        client_id = dados.get('client_id')
        client_secret = dados.get('client_secret')
        access_token = dados.get('access_token')
        refresh_token = dados.get('refresh_token')
        
        importador = ImportadorTagPlus(
            usuario, senha, api_key, client_id, client_secret,
            access_token, refresh_token
        )
        resultado = importador.importar_clientes(limite)
        
        return jsonify({
            'success': True,
            'resultado': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao importar clientes: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/importar-nfs', methods=['POST'])
@login_required
def importar_nfs():
    """Importa NFs do TagPlus"""
    try:
        dados = request.get_json()
        usuario = dados.get('usuario', 'rayssa')
        senha = dados.get('senha', 'A12345')
        api_key = dados.get('api_key')
        client_id = dados.get('client_id')
        client_secret = dados.get('client_secret')
        access_token = dados.get('access_token')
        refresh_token = dados.get('refresh_token')
        
        # Datas do período
        data_inicio_str = dados.get('data_inicio')
        data_fim_str = dados.get('data_fim')
        
        if not data_inicio_str:
            # Padrão: últimos 7 dias
            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=7)
        else:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        
        importador = ImportadorTagPlus(
            usuario, senha, api_key, client_id, client_secret,
            access_token, refresh_token
        )
        resultado = importador.importar_nfs(data_inicio, data_fim)
        
        relatorio = importador.gerar_relatorio()
        
        return jsonify({
            'success': True,
            'resultado': relatorio
        })
        
    except Exception as e:
        logger.error(f"Erro ao importar NFs: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/oauth/authorize')
@login_required
def oauth_authorize():
    """Inicia fluxo OAuth2 para autorizar aplicação"""
    try:
        client_id = request.args.get('client_id')
        if not client_id:
            flash('Client ID é obrigatório', 'error')
            return redirect(url_for('tagplus.pagina_importacao'))
        
        # URL de callback
        redirect_uri = url_for('tagplus.oauth_callback', _external=True)
        
        # Gera URL de autorização
        from app.integracoes.tagplus.auth_bearer import TagPlusAuthBearer
        auth = TagPlusAuthBearer(client_id=client_id)
        auth_url = auth.get_authorization_url(redirect_uri)
        
        # Salva client_id na sessão para usar no callback
        from flask import session
        session['tagplus_client_id'] = client_id
        
        # Redireciona para TagPlus
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar OAuth: {e}")
        flash(f'Erro ao iniciar autorização: {str(e)}', 'error')
        return redirect(url_for('tagplus.pagina_importacao'))

@tagplus_bp.route('/oauth/callback')
@login_required
def oauth_callback():
    """Callback OAuth2 - recebe código e troca por tokens"""
    try:
        from flask import session
        
        # Recupera código
        code = request.args.get('code')
        if not code:
            flash('Código de autorização não recebido', 'error')
            return redirect(url_for('tagplus.pagina_importacao'))
        
        # Recupera client_id da sessão
        client_id = session.get('tagplus_client_id')
        if not client_id:
            flash('Client ID não encontrado na sessão', 'error')
            return redirect(url_for('tagplus.pagina_importacao'))
        
        # URL de callback
        redirect_uri = url_for('tagplus.oauth_callback', _external=True)
        
        # Para trocar o código, precisamos do client_secret
        # Por segurança, vamos redirecionar para a página com o código
        return render_template(
            'integracoes/tagplus_oauth_callback.html',
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri
        )
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        flash(f'Erro no callback: {str(e)}', 'error')
        return redirect(url_for('tagplus.pagina_importacao'))

@tagplus_bp.route('/api/trocar-codigo', methods=['POST'])
@login_required
def trocar_codigo():
    """Troca código de autorização por tokens"""
    try:
        dados = request.get_json()
        code = dados.get('code')
        client_id = dados.get('client_id')
        client_secret = dados.get('client_secret')
        redirect_uri = dados.get('redirect_uri')
        
        if not all([code, client_id, client_secret, redirect_uri]):
            return jsonify({
                'success': False,
                'erro': 'Todos os campos são obrigatórios'
            }), 400
        
        # Troca código por tokens
        from app.integracoes.tagplus.auth_bearer import TagPlusAuthBearer
        auth = TagPlusAuthBearer(client_id=client_id, client_secret=client_secret)
        sucesso, resultado = auth.trocar_codigo_por_token(code, redirect_uri)
        
        if sucesso:
            return jsonify({
                'success': True,
                'access_token': resultado.get('access_token'),
                'refresh_token': resultado.get('refresh_token'),
                'expires_in': resultado.get('expires_in', 86400)
            })
        else:
            return jsonify({
                'success': False,
                'erro': f'Erro ao trocar código: {resultado}'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao trocar código: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/webhooks/info')
@login_required
def info_webhooks():
    """Retorna informações sobre configuração de webhooks"""
    
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        'webhooks': {
            'cliente': {
                'url': f"{base_url}/webhook/tagplus/cliente",
                'eventos': ['criado', 'atualizado', 'excluido'],
                'metodo': 'POST'
            },
            'nfe': {
                'url': f"{base_url}/webhook/tagplus/nfe",
                'eventos': ['autorizada', 'cancelada', 'inutilizada'],
                'metodo': 'POST'
            },
            'teste': {
                'url': f"{base_url}/webhook/tagplus/teste",
                'metodo': 'GET ou POST'
            }
        },
        'instrucoes': [
            'Configure estas URLs no painel do TagPlus',
            'Selecione os eventos que deseja receber',
            'TagPlus enviará os dados automaticamente quando o evento ocorrer',
            'Não é necessário autenticação para receber webhooks'
        ]
    })

@tagplus_bp.route('/postman')
@login_required
def pagina_postman():
    """Página para fluxo estilo Postman"""
    return render_template('integracoes/tagplus_postman.html')

@tagplus_bp.route('/teste-auth')
@login_required
def teste_auth():
    """Página de teste de autenticação"""
    return render_template('integracoes/tagplus_teste_auth.html')

@tagplus_bp.route('/api/postman/trocar-codigo', methods=['POST'])
@login_required
def postman_trocar_codigo():
    """Troca código por tokens usando fluxo Postman"""
    try:
        dados = request.get_json()
        callback_url = dados.get('callback_url')
        client_id = dados.get('client_id')
        client_secret = dados.get('client_secret')
        
        if not all([callback_url, client_id, client_secret]):
            return jsonify({
                'success': False,
                'erro': 'Todos os campos são obrigatórios'
            }), 400
        
        helper = PostmanHelper()
        
        # Extrai código da URL de callback
        code = helper.extract_code_from_callback(callback_url)
        if not code:
            return jsonify({
                'success': False,
                'erro': 'Código não encontrado na URL. Certifique-se de copiar a URL completa após autorizar.'
            }), 400
        
        # Troca código por tokens
        sucesso, resultado = helper.exchange_code_for_tokens(code, client_id, client_secret)
        
        if sucesso:
            return jsonify({
                'success': True,
                'access_token': resultado.get('access_token'),
                'refresh_token': resultado.get('refresh_token'),
                'expires_in': resultado.get('expires_in', 86400)
            })
        else:
            return jsonify({
                'success': False,
                'erro': f'Erro ao obter tokens: {resultado}'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro no fluxo Postman: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/postman/testar-token', methods=['POST'])
@login_required
def postman_testar_token():
    """Testa token obtido via Postman"""
    try:
        dados = request.get_json()
        access_token = dados.get('access_token')
        
        if not access_token:
            return jsonify({
                'success': False,
                'erro': 'Access Token é obrigatório'
            }), 400
        
        helper = PostmanHelper()
        sucesso, mensagem = helper.test_api_with_token(access_token)
        
        if sucesso:
            return jsonify({
                'success': True,
                'mensagem': mensagem
            })
        else:
            return jsonify({
                'success': False,
                'erro': mensagem
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao testar token: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/vincular-nfs')
@login_required
def vincular_nfs():
    """Interface para vincular manualmente NFs sem separação"""
    try:
        # Busca NFs sem separação do TagPlus
        nfs_sem_separacao = db.session.query(
            FaturamentoProduto
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus',
            FaturamentoProduto.origem.is_(None)  # Sem pedido vinculado
        ).filter(
            ~FaturamentoProduto.numero_nf.in_(
                db.session.query(EmbarqueItem.numero_nf).filter(
                    EmbarqueItem.numero_nf.isnot(None)
                )
            )
        ).order_by(FaturamentoProduto.data_fatura.desc()).all()
        
        # Agrupa por NF
        nfs_agrupadas = {}
        for item in nfs_sem_separacao:
            if item.numero_nf not in nfs_agrupadas:
                nfs_agrupadas[item.numero_nf] = {
                    'numero_nf': item.numero_nf,
                    'data_fatura': item.data_fatura,
                    'cnpj_cliente': item.cnpj_cliente,
                    'nome_cliente': item.nome_cliente,
                    'itens': []
                }
            nfs_agrupadas[item.numero_nf]['itens'].append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'quantidade': item.qtd_produto_faturado,
                'valor': item.valor_produto_faturado
            })
        
        return render_template(
            'integracoes/tagplus_vincular_nfs.html',
            nfs_sem_separacao=list(nfs_agrupadas.values())
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar NFs para vinculação: {e}")
        flash(f'Erro ao carregar página: {str(e)}', 'error')
        return redirect(url_for('tagplus.pagina_importacao'))

@tagplus_bp.route('/api/buscar-embarques-candidatos', methods=['POST'])
@login_required
def buscar_embarques_candidatos():
    """Busca EmbarqueItems candidatos para vinculação"""
    try:
        data = request.get_json()
        numero_nf = data.get('numero_nf')
        
        if not numero_nf:
            return jsonify({'success': False, 'message': 'Número da NF não informado'}), 400
        
        # Busca dados da NF
        nf_items = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            created_by='ImportTagPlus'
        ).all()
        
        if not nf_items:
            return jsonify({'success': False, 'message': 'NF não encontrada'}), 404
        
        # CNPJ do cliente
        cnpj_cliente = nf_items[0].cnpj_cliente.replace('.', '').replace('-', '').replace('/', '')
        
        # Busca EmbarqueItems candidatos com os mesmos critérios do score
        embarque_items = EmbarqueItem.query.join(
            Embarque,
            EmbarqueItem.embarque_id == Embarque.id
        ).join(
            CarteiraCopia,
            and_(
                EmbarqueItem.num_pedido == CarteiraCopia.num_pedido,
                EmbarqueItem.cod_produto == CarteiraCopia.cod_produto
            )
        ).filter(
            CarteiraCopia.cnpj_cpf.contains(cnpj_cliente),
            EmbarqueItem.numero_nf.is_(None),  # Ainda não faturado
            Embarque.status == 'ativo',  # Embarque ativo
            EmbarqueItem.status == 'ativo',  # Item ativo
            EmbarqueItem.erro_validacao.isnot(None)  # Tem erro de validação
        ).all()
        
        # Formata resposta
        candidatos = []
        for item in embarque_items:
            # Busca dados do pedido
            pedido = CarteiraCopia.query.filter_by(
                num_pedido=item.num_pedido,
                cod_produto=item.cod_produto
            ).first()
            
            candidatos.append({
                'id': item.id,
                'separacao_lote_id': item.separacao_lote_id,
                'num_pedido': item.num_pedido,
                'cod_produto': item.cod_produto,
                'nome_produto': pedido.nome_produto if pedido else f'Produto {item.cod_produto}',
                'qtd_separada': item.qtd_separada,
                'embarque_id': item.embarque_id,
                'erro_validacao': item.erro_validacao
            })
        
        # Produtos da NF para comparação
        produtos_nf = [{
            'cod_produto': item.cod_produto,
            'nome_produto': item.nome_produto,
            'quantidade': item.qtd_produto_faturado
        } for item in nf_items]
        
        return jsonify({
            'success': True,
            'candidatos': candidatos,
            'produtos_nf': produtos_nf
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar embarques candidatos: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500

@tagplus_bp.route('/importar-excel')
@login_required
def importar_faturamento_excel():
    """Tela de importação de faturamento TagPlus via Excel"""
    return render_template('integracoes/importar_faturamento_tagplus.html')

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@tagplus_bp.route('/api/importar-excel', methods=['POST'])
@login_required
def api_importar_faturamento_excel():
    """API para processar importação de faturamento TagPlus via Excel"""
    try:
        # Verifica se foi enviado arquivo
        if 'arquivo' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Nenhum arquivo foi enviado'
            }), 400
        
        arquivo = request.files['arquivo']
        
        # Verifica se arquivo tem nome
        if arquivo.filename == '':
            return jsonify({
                'success': False,
                'message': 'Arquivo sem nome'
            }), 400
        
        # Verifica extensão
        if not allowed_file(arquivo.filename):
            return jsonify({
                'success': False,
                'message': 'Formato de arquivo inválido. Use .xlsx ou .xls'
            }), 400
        
        # Preserva a extensão original do arquivo
        _, file_ext = os.path.splitext(arquivo.filename.lower())
        if file_ext not in ['.xls', '.xlsx']:
            file_ext = '.xlsx'  # Default para xlsx se extensão não for reconhecida
        
        logger.info(f"Processando arquivo: {arquivo.filename}, extensão detectada: {file_ext}")
        
        # Salva arquivo temporário com a extensão correta
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            arquivo.save(tmp_file.name)
            
            try:
                # Processa arquivo
                resultado = processar_arquivo_tagplus_web(
                    tmp_file.name,
                    processar_completo=request.form.get('processar_completo') == 'true'
                )
                
                return jsonify(resultado)
                
            finally:
                # Remove arquivo temporário
                if os.path.exists(tmp_file.name):
                    os.remove(tmp_file.name)
                    
    except Exception as e:
        logger.error(f"Erro na importação TagPlus: {e}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Erro ao processar arquivo: {str(e)}',
            'detalhes_erro': traceback.format_exc()
        }), 500

@tagplus_bp.route('/api/vincular-nf-embarque', methods=['POST'])
@login_required
def vincular_nf_embarque():
    """Vincula manualmente uma NF a um EmbarqueItem"""
    try:
        data = request.get_json()
        numero_nf = data.get('numero_nf')
        embarque_item_id = data.get('embarque_item_id')
        
        if not numero_nf or not embarque_item_id:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400
        
        # Busca EmbarqueItem
        embarque_item = EmbarqueItem.query.get(embarque_item_id)
        if not embarque_item:
            return jsonify({'success': False, 'message': 'EmbarqueItem não encontrado'}), 404
        
        # Verifica se já está faturado
        if embarque_item.numero_nf:
            return jsonify({'success': False, 'message': 'Este item já foi faturado'}), 400
        
        # Busca dados da NF
        nf_item = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            cod_produto=embarque_item.cod_produto
        ).first()
        
        if not nf_item:
            return jsonify({'success': False, 'message': 'Produto não encontrado na NF'}), 404
        
        # Processa vinculação usando ProcessadorFaturamentoTagPlus
        processador = ProcessadorFaturamentoTagPlus()
        
        # Atualiza EmbarqueItem
        processador._atualizar_embarque_item(nf_item, embarque_item)
        
        # Cria movimentação se ainda não existir
        processador._criar_movimentacao_estoque(nf_item, embarque_item.separacao_lote_id)
        
        # Atualiza origem no FaturamentoProduto
        if embarque_item.num_pedido:
            nf_item.origem = embarque_item.num_pedido
            # NOTA: baixa_produto_pedido agora é calculada dinamicamente via hybrid_property
        
        # Consolida em RelatorioFaturamentoImportado
        processador._consolidar_relatorio(nf_item, embarque_item.num_pedido)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'NF {numero_nf} vinculada com sucesso ao item do embarque'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao vincular NF: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500