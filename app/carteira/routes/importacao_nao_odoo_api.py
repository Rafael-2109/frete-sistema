"""
API para importação de pedidos não-Odoo
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
from app import db
from app.carteira.services.importacao_nao_odoo import ImportadorPedidosNaoOdoo
from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)

importacao_nao_odoo_api = Blueprint('importacao_nao_odoo_api', __name__)

# Configurações
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
UPLOAD_FOLDER = 'temp_uploads'

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@importacao_nao_odoo_api.route('/api/importacao-nao-odoo/upload', methods=['POST'])
@login_required
def upload_arquivo():
    """Upload e processamento de MÚLTIPLOS arquivos Excel com pedidos não-Odoo"""
    try:
        # Verificar se arquivos foram enviados
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400

        # ✅ SUPORTE A MÚLTIPLOS ARQUIVOS - Pega todos os arquivos
        files = request.files.getlist('file')

        if not files or len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400

        # Verificar se pelo menos um arquivo foi selecionado
        files_validos = [f for f in files if f.filename != '']
        if not files_validos:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400

        # Criar diretório temporário se não existir
        upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

        # ✅ PROCESSAR MÚLTIPLOS ARQUIVOS
        resultados_geral = {
            'total_arquivos': len(files_validos),
            'arquivos_processados': 0,
            'arquivos_com_erro': 0,
            'total_pedidos_importados': 0,
            'detalhes_por_arquivo': [],
            'erros_globais': [],
            'avisos_globais': [],
            'clientes_pendentes': []  # ✅ NOVO: Lista de clientes que precisam cadastro
        }

        usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

        for file in files_validos:
            resultado_arquivo = {
                'nome_arquivo': file.filename,
                'success': False,
                'pedidos_importados': 0,
                'erros': [],
                'avisos': [],
                'pendente_cadastro': False  # ✅ NOVO: Flag de pendente
            }

            try:
                # Verificar extensão
                if not allowed_file(file.filename):
                    resultado_arquivo['erros'].append('Tipo de arquivo não permitido. Use Excel (.xlsx ou .xls)')
                    resultados_geral['arquivos_com_erro'] += 1
                    resultados_geral['detalhes_por_arquivo'].append(resultado_arquivo)
                    continue

                # Salvar arquivo temporariamente
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_path, filename)
                file.save(filepath)

                try:
                    # Processar importação
                    importador = ImportadorPedidosNaoOdoo(usuario=usuario)
                    resultado = importador.importar_arquivo(filepath)

                    # Limpar arquivo temporário
                    os.remove(filepath)

                    # Consolidar resultado
                    if resultado['success']:
                        resultado_arquivo['success'] = True
                        resultado_arquivo['pedidos_importados'] = resultado.get('pedidos_importados', 0)
                        resultado_arquivo['avisos'] = resultado.get('avisos', [])
                        resultados_geral['arquivos_processados'] += 1
                        resultados_geral['total_pedidos_importados'] += resultado.get('pedidos_importados', 0)
                    elif resultado.get('pendente_cadastro'):
                        # ✅ CLIENTE PRECISA SER CADASTRADO
                        resultado_arquivo['pendente_cadastro'] = True
                        resultado_arquivo['avisos'] = resultado.get('avisos', [])

                        # Adicionar cliente à lista de pendentes
                        dados_cliente_novo = resultado.get('dados_cliente_novo')
                        if dados_cliente_novo:
                            dados_cliente_novo['arquivo_origem'] = file.filename
                            resultados_geral['clientes_pendentes'].append(dados_cliente_novo)

                        # Não conta como erro nem como processado
                    else:
                        resultado_arquivo['erros'] = resultado.get('erros', [])
                        resultado_arquivo['avisos'] = resultado.get('avisos', [])
                        resultados_geral['arquivos_com_erro'] += 1

                except Exception as e:
                    # Limpar arquivo em caso de erro
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    resultado_arquivo['erros'].append(f'Erro ao processar: {str(e)}')
                    resultados_geral['arquivos_com_erro'] += 1

            except Exception as e:
                resultado_arquivo['erros'].append(f'Erro no arquivo: {str(e)}')
                resultados_geral['arquivos_com_erro'] += 1

            finally:
                # Adicionar resultado do arquivo ao resultado geral
                resultados_geral['detalhes_por_arquivo'].append(resultado_arquivo)

        # ✅ VERIFICAR SE HÁ CLIENTES PENDENTES DE CADASTRO
        if resultados_geral['clientes_pendentes']:
            return jsonify({
                'success': False,
                'pendente_cadastro': True,  # ✅ Flag para abrir modal
                'mensagem': f"{len(resultados_geral['clientes_pendentes'])} cliente(s) precisa(m) ser cadastrado(s)",
                **resultados_geral
            }), 200  # Retorna 200 porque não é erro, é pendência

        # ✅ GERAR EXCEL COM ERROS (se houver)
        excel_erros_base64 = None
        if resultados_geral['arquivos_com_erro'] > 0:
            try:
                import pandas as pd
                from io import BytesIO
                import base64

                erros_data = []

                # Coletar todos os erros
                for arquivo_detalhe in resultados_geral['detalhes_por_arquivo']:
                    if arquivo_detalhe.get('erros'):
                        for erro in arquivo_detalhe['erros']:
                            erros_data.append({
                                'Arquivo': arquivo_detalhe['nome_arquivo'],
                                'Erro': erro,
                                'Data/Hora': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')
                            })

                if erros_data:
                    df_erros = pd.DataFrame(erros_data)

                    # Criar Excel em memória
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_erros.to_excel(writer, index=False, sheet_name='Erros de Importação')

                    output.seek(0)

                    # Converter para base64
                    excel_erros_base64 = base64.b64encode(output.getvalue()).decode()
                    logger.info(f"Excel de erros gerado com {len(erros_data)} erro(s)")

            except Exception as e:
                logger.error(f"Erro ao gerar Excel de erros: {e}")

        # Determinar sucesso geral
        sucesso_geral = resultados_geral['arquivos_processados'] > 0

        # Montar mensagem de resposta
        if sucesso_geral:
            mensagem = f"Processados {resultados_geral['arquivos_processados']} de {resultados_geral['total_arquivos']} arquivos. "
            mensagem += f"Total de {resultados_geral['total_pedidos_importados']} pedidos importados."

            if resultados_geral['arquivos_com_erro'] > 0:
                mensagem += f" {resultados_geral['arquivos_com_erro']} arquivo(s) com erro."

            response_data = {
                'success': True,
                'mensagem': mensagem,
                **resultados_geral
            }

            if excel_erros_base64:
                response_data['excel_erros'] = excel_erros_base64

            return jsonify(response_data), 200
        else:
            response_data = {
                'success': False,
                'error': f"Nenhum arquivo foi processado com sucesso. {resultados_geral['arquivos_com_erro']} erro(s).",
                **resultados_geral
            }

            if excel_erros_base64:
                response_data['excel_erros'] = excel_erros_base64

            return jsonify(response_data), 400

    except Exception as e:
        logger.error(f"Erro no upload de arquivos não-Odoo: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao processar arquivos: {str(e)}'
        }), 500

@importacao_nao_odoo_api.route('/api/importacao-nao-odoo/validar', methods=['POST'])
@login_required
def validar_arquivo():
    """Valida arquivo Excel sem importar (preview)"""
    try:
        # Similar ao upload, mas apenas valida
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Arquivo inválido'
            }), 400
        
        # Salvar temporariamente
        upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        
        try:
            # Criar importador mas não executar
            importador = ImportadorPedidosNaoOdoo()
            
            # Ler e validar arquivo
            import pandas as pd
            df = pd.read_excel(filepath, header=None, engine='openpyxl')
            
            # Debug: Mostrar conteúdo do arquivo
            logger.info("=== CONTEÚDO DO ARQUIVO EXCEL ===")
            for idx, row in df.iterrows():
                valores = []
                for col in range(len(row)):
                    val = row.iloc[col]
                    if pd.notna(val):
                        valores.append(f"Col{col}: {val}")
                if valores:
                    logger.info(f"Linha {idx}: {' | '.join(valores)}")
            logger.info("=== FIM DO CONTEÚDO ===")
            
            # Detectar modelo da planilha
            modelo = importador.detectar_modelo(df)
            if not modelo:
                return jsonify({
                    'success': False,
                    'error': 'Modelo de planilha não reconhecido. Verifique se é o formato correto.'
                }), 400
            
            # Extrair dados para preview
            dados_cabecalho = importador.extrair_dados_cabecalho(df, modelo)
            
            # Se houver CNPJ, buscar cliente
            cliente_info = None
            if dados_cabecalho.get('cnpj_cpf'):
                cliente = importador.buscar_dados_cliente(dados_cabecalho['cnpj_cpf'])
                if cliente:
                    cliente_info = {
                        'encontrado': True,
                        'raz_social': cliente.raz_social,
                        'raz_social_red': cliente.raz_social_red,
                        'municipio': cliente.municipio,
                        'estado': cliente.estado
                    }
                else:
                    cliente_info = {
                        'encontrado': False,
                        'cnpj': dados_cabecalho['cnpj_cpf'],
                        'mensagem': 'Cliente não cadastrado'
                    }
            
            # Extrair produtos para preview
            produtos = importador.extrair_dados_produtos(df, modelo)
            
            # Limpar arquivo
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'preview': {
                    'cabecalho': dados_cabecalho,
                    'cliente': cliente_info,
                    'produtos': produtos,
                    'total_produtos': len(produtos),
                    'erros': importador.erros,
                    'avisos': importador.avisos
                }
            })
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e
            
    except Exception as e:
        logger.error(f"Erro na validação de arquivo não-Odoo: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao validar arquivo: {str(e)}'
        }), 500

@importacao_nao_odoo_api.route('/api/importacao-nao-odoo/template', methods=['GET'])
@login_required
def download_template():
    """Retorna informações sobre o template esperado"""
    return jsonify({
        'success': True,
        'template': {
            'modelos_suportados': {
                'modelo_1': {
                    'identificacao': 'CNPJ* na célula C8',
                    'campos_cabecalho': {
                        'D13': 'Número do pedido do representante (obrigatório)',
                        'D8': 'CNPJ do cliente (obrigatório)',
                        'D12': 'Número do pedido do cliente (opcional)',
                        'E5': 'Data de entrega (opcional)'
                    },
                    'produtos': {
                        'inicio': 'Linha 19',
                        'colunas': {
                            'B': 'Código do produto',
                            'J': 'Quantidade solicitada',
                            'K': 'Valor negociado'
                        }
                    }
                },
                'modelo_2': {
                    'identificacao': 'CNPJ* na célula B8',
                    'campos_cabecalho': {
                        'C14': 'Número do pedido do representante (obrigatório)',
                        'C8': 'CNPJ do cliente (obrigatório)',
                        'C13': 'Número do pedido do cliente (opcional)',
                        'D5': 'Data de entrega (opcional)'
                    },
                    'produtos': {
                        'inicio': 'Linha 20',
                        'colunas': {
                            'A': 'Código do produto',
                            'G': 'Quantidade solicitada',
                            'H': 'Valor negociado'
                        }
                    }
                }
            },
            'observacoes': [
                'O sistema detecta automaticamente o modelo baseado na posição do campo CNPJ*',
                'O CNPJ deve estar previamente cadastrado no sistema',
                'Produtos são importados apenas quando quantidade é diferente de vazio e maior que zero',
                'Valores numéricos podem usar vírgula ou ponto como separador decimal'
            ]
        }
    })

@importacao_nao_odoo_api.route('/api/listar-vendedores-equipes', methods=['GET'])
@login_required
def listar_vendedores_equipes():
    """Lista vendedores e equipes únicos para seleção no modal"""
    try:
        from app.carteira.models import CadastroCliente
        from sqlalchemy import distinct

        # Buscar vendedores únicos (não nulos e não vazios)
        vendedores = db.session.query(distinct(CadastroCliente.vendedor))\
            .filter(CadastroCliente.vendedor.isnot(None))\
            .filter(CadastroCliente.vendedor != '')\
            .filter(CadastroCliente.cliente_ativo == True)\
            .order_by(CadastroCliente.vendedor)\
            .all()

        # Buscar equipes únicas (não nulas e não vazias)
        equipes = db.session.query(distinct(CadastroCliente.equipe_vendas))\
            .filter(CadastroCliente.equipe_vendas.isnot(None))\
            .filter(CadastroCliente.equipe_vendas != '')\
            .filter(CadastroCliente.cliente_ativo == True)\
            .order_by(CadastroCliente.equipe_vendas)\
            .all()

        return jsonify({
            'success': True,
            'vendedores': [v[0] for v in vendedores],
            'equipes': [e[0] for e in equipes]
        })

    except Exception as e:
        logger.error(f"Erro ao listar vendedores/equipes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@importacao_nao_odoo_api.route('/api/cadastrar-cliente-e-importar', methods=['POST'])
@login_required
def cadastrar_cliente_e_importar():
    """
    Cadastra cliente(s) novo(s) e reimporta os arquivos

    Payload esperado:
    {
        "clientes": [
            {
                "cnpj": "12345678000199",
                "dados_receita": {...},
                "vendedor": "João Silva",
                "equipe_vendas": "GERAL"
            }
        ],
        "arquivos_pendentes": ["arquivo1.xlsx", "arquivo2.xlsx"]
    }
    """
    try:
        data = request.get_json()

        if not data or 'clientes' not in data:
            return jsonify({
                'success': False,
                'error': 'Dados de clientes não fornecidos'
            }), 400

        clientes_criados = []
        erros_criacao = []
        usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

        # Criar todos os clientes
        for cliente_data in data['clientes']:
            try:
                importador = ImportadorPedidosNaoOdoo(usuario=usuario)

                novo_cliente = importador.criar_cliente_automatico(
                    dados_receita=cliente_data['dados_receita'],
                    vendedor=cliente_data['vendedor'],
                    equipe_vendas=cliente_data['equipe_vendas']
                )

                if novo_cliente:
                    clientes_criados.append({
                        'cnpj': novo_cliente.cnpj_cpf,
                        'nome': novo_cliente.raz_social,
                        'vendedor': novo_cliente.vendedor,
                        'equipe': novo_cliente.equipe_vendas
                    })
                    logger.info(f"✅ Cliente {novo_cliente.cnpj_cpf} criado com sucesso")
                else:
                    erros_criacao.append(f"Erro ao criar cliente {cliente_data.get('cnpj', 'N/A')}")

            except Exception as e:
                logger.error(f"Erro ao criar cliente: {e}")
                erros_criacao.append(f"Cliente {cliente_data.get('cnpj', 'N/A')}: {str(e)}")

        # Se todos os clientes foram criados, retornar sucesso
        # O frontend vai reenviar os arquivos automaticamente
        if len(clientes_criados) == len(data['clientes']):
            return jsonify({
                'success': True,
                'mensagem': f'{len(clientes_criados)} cliente(s) cadastrado(s) com sucesso',
                'clientes_criados': clientes_criados,
                'reenviar_importacao': True  # Flag para frontend reenviar arquivos
            }), 200
        else:
            return jsonify({
                'success': False,
                'mensagem': f'Erros ao cadastrar clientes',
                'clientes_criados': clientes_criados,
                'erros': erros_criacao
            }), 400

    except Exception as e:
        logger.error(f"Erro no cadastro de clientes: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao processar cadastro: {str(e)}'
        }), 500