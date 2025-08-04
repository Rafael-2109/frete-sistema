"""
API para importação de pedidos não-Odoo
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
from app.carteira.services.importacao_nao_odoo import ImportadorPedidosNaoOdoo

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
    """Upload e processamento de arquivo Excel com pedidos não-Odoo"""
    try:
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        
        # Verificar se arquivo foi selecionado
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Verificar extensão
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Tipo de arquivo não permitido. Use Excel (.xlsx ou .xls)'
            }), 400
        
        # Criar diretório temporário se não existir
        upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        
        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        
        try:
            # Processar importação
            importador = ImportadorPedidosNaoOdoo(
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            resultado = importador.importar_arquivo(filepath)
            
            # Limpar arquivo temporário
            os.remove(filepath)
            
            if resultado['success']:
                return jsonify(resultado), 200
            else:
                return jsonify(resultado), 400
                
        except Exception as e:
            # Limpar arquivo em caso de erro
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e
            
    except Exception as e:
        logger.error(f"Erro no upload de arquivo não-Odoo: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao processar arquivo: {str(e)}'
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