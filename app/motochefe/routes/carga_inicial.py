"""
Rotas de Carga Inicial - Sistema MotoChefe
Data: 14/10/2025

Importação passo-a-passo de dados históricos
"""
from flask import render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.services.importacao_carga_inicial import ImportacaoCargaInicialService
from app.motochefe.services.importacao_fase4_pedidos import ImportacaoFase4Service


# Desabilitar CSRF para uploads
def csrf_exempt(func):
    """Decorator para desabilitar CSRF em rotas específicas"""
    func.csrf_exempt = True
    return func


# ============================================================
# CONFIGURAÇÕES DE UPLOAD
# ============================================================

UPLOAD_FOLDER = '/tmp/motochefe_uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def arquivo_permitido(filename):
    """Verifica se extensão é permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# PÁGINA PRINCIPAL - CARGA INICIAL
# ============================================================

@motochefe_bp.route('/carga-inicial')
@login_required
def carga_inicial():
    """Página principal de carga inicial"""
    if not current_user.pode_acessar_motochefe():
        flash('Acesso negado ao sistema MotoChefe.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('motochefe/carga_inicial/index.html')


# ============================================================
# DOWNLOAD DE TEMPLATES
# ============================================================

@motochefe_bp.route('/carga-inicial/download-template/<fase>')
@login_required
def download_template(fase):
    """Download de template Excel por fase"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    try:
        if fase == 'fase1':
            arquivo = ImportacaoCargaInicialService.gerar_template_fase1()
            nome = 'MotoChefe_Fase1_Configuracoes.xlsx'
        elif fase == 'fase2':
            arquivo = ImportacaoCargaInicialService.gerar_template_fase2()
            nome = 'MotoChefe_Fase2_Cadastros.xlsx'
        elif fase == 'fase3':
            arquivo = ImportacaoCargaInicialService.gerar_template_fase3()
            nome = 'MotoChefe_Fase3_ProdutosClientes.xlsx'
        elif fase == 'fase4':
            arquivo = ImportacaoFase4Service.gerar_template_fase4()
            nome = 'MotoChefe_Fase4_Pedidos.xlsx'
        else:
            flash('Fase inválida', 'danger')
            return redirect(url_for('motochefe.carga_inicial'))

        return send_file(
            arquivo,
            as_attachment=True,
            download_name=nome,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'Erro ao gerar template: {str(e)}', 'danger')
        return redirect(url_for('motochefe.carga_inicial'))


# ============================================================
# IMPORTAÇÃO FASE 1: CONFIGURAÇÕES BASE
# ============================================================

@motochefe_bp.route('/carga-inicial/fase1', methods=['POST'])
@login_required
@csrf_exempt
def importar_fase1():
    """Importa arquivos da Fase 1"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    resultados = {}
    erros_criticos = []

    try:
        # 1. Equipes de Vendas
        if 'equipes' in request.files:
            file = request.files['equipes']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_equipes_vendas(
                    df,
                    usuario=current_user.nome
                )
                resultados['equipes'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Equipes: {resultado.mensagem}")

        # 2. Transportadoras
        if 'transportadoras' in request.files and not erros_criticos:
            file = request.files['transportadoras']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_transportadoras(
                    df,
                    usuario=current_user.nome
                )
                resultados['transportadoras'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Transportadoras: {resultado.mensagem}")

        # 3. Empresas
        if 'empresas' in request.files and not erros_criticos:
            file = request.files['empresas']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_empresas(
                    df,
                    usuario=current_user.nome
                )
                resultados['empresas'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Empresas: {resultado.mensagem}")

        # 4. CrossDocking
        if 'crossdocking' in request.files and not erros_criticos:
            file = request.files['crossdocking']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_crossdocking(
                    df,
                    usuario=current_user.nome
                )
                resultados['crossdocking'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"CrossDocking: {resultado.mensagem}")

        # 5. Custos Operacionais
        if 'custos' in request.files and not erros_criticos:
            file = request.files['custos']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_custos_operacionais(
                    df,
                    usuario=current_user.nome
                )
                resultados['custos'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Custos: {resultado.mensagem}")

        # Retornar resultado
        if erros_criticos:
            return jsonify({
                'sucesso': False,
                'mensagem': '❌ Erros encontrados na importação',
                'erros': erros_criticos,
                'resultados': resultados
            }), 400
        else:
            return jsonify({
                'sucesso': True,
                'mensagem': '✅ Fase 1 importada com sucesso!',
                'resultados': resultados
            })

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'❌ Erro fatal: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500


# ============================================================
# IMPORTAÇÃO FASE 2: CADASTROS DEPENDENTES
# ============================================================

@motochefe_bp.route('/carga-inicial/fase2', methods=['POST'])
@login_required
@csrf_exempt
def importar_fase2():
    """Importa arquivos da Fase 2"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    resultados = {}
    erros_criticos = []

    try:
        # 1. Vendedores
        if 'vendedores' in request.files:
            file = request.files['vendedores']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_vendedores(
                    df,
                    usuario=current_user.nome
                )
                resultados['vendedores'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Vendedores: {resultado.mensagem}")

        # 2. Modelos
        if 'modelos' in request.files and not erros_criticos:
            file = request.files['modelos']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_modelos(
                    df,
                    usuario=current_user.nome
                )
                resultados['modelos'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Modelos: {resultado.mensagem}")

        # Retornar resultado
        if erros_criticos:
            return jsonify({
                'sucesso': False,
                'mensagem': '❌ Erros encontrados na importação',
                'erros': erros_criticos,
                'resultados': resultados
            }), 400
        else:
            return jsonify({
                'sucesso': True,
                'mensagem': '✅ Fase 2 importada com sucesso!',
                'resultados': resultados
            })

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'❌ Erro fatal: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500


# ============================================================
# IMPORTAÇÃO FASE 3: PRODUTOS E CLIENTES
# ============================================================

@motochefe_bp.route('/carga-inicial/fase3', methods=['POST'])
@login_required
@csrf_exempt
def importar_fase3():
    """Importa arquivos da Fase 3"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    resultados = {}
    erros_criticos = []

    try:
        # 1. Clientes
        if 'clientes' in request.files:
            file = request.files['clientes']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_clientes(
                    df,
                    usuario=current_user.nome
                )
                resultados['clientes'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Clientes: {resultado.mensagem}")

        # 2. Motos
        if 'motos' in request.files and not erros_criticos:
            file = request.files['motos']
            if file and arquivo_permitido(file.filename):
                df = pd.read_excel(file)
                resultado = ImportacaoCargaInicialService.importar_motos(
                    df,
                    usuario=current_user.nome
                )
                resultados['motos'] = resultado.to_dict()
                if not resultado.sucesso:
                    erros_criticos.append(f"Motos: {resultado.mensagem}")

        # Retornar resultado
        if erros_criticos:
            return jsonify({
                'sucesso': False,
                'mensagem': '❌ Erros encontrados na importação',
                'erros': erros_criticos,
                'resultados': resultados
            }), 400
        else:
            return jsonify({
                'sucesso': True,
                'mensagem': '✅ Fase 3 importada com sucesso! Sistema pronto para operação.',
                'resultados': resultados
            })

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'❌ Erro fatal: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500

# ============================================================
# IMPORTAÇÃO FASE 4: PEDIDOS E VENDAS
# ============================================================

@motochefe_bp.route('/carga-inicial/fase4', methods=['POST'])
@login_required
@csrf_exempt
def importar_fase4():
    """
    Importa arquivos da Fase 4: Pedidos e Vendas
    ⚠️ TODAS as funções automáticas são executadas:
    - Atualizar status das motos
    - Gerar títulos financeiros (A RECEBER)
    - Gerar títulos a pagar (PENDENTES)
    - Calcular vencimentos
    """
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    try:
        # 1. LER ARQUIVOS EXCEL
        file_pedidos = request.files.get('pedidos')
        file_itens = request.files.get('itens')

        if not file_pedidos or not file_itens:
            return jsonify({
                'sucesso': False,
                'mensagem': '❌ Envie os arquivos de Pedidos e Itens'
            }), 400

        # 2. CARREGAR DATAFRAMES
        df_pedidos = pd.read_excel(file_pedidos, sheet_name=0)
        df_itens = pd.read_excel(file_itens, sheet_name=0)

        # 3. IMPORTAR PEDIDOS COM TODAS AS FUNÇÕES AUTOMÁTICAS
        resultado = ImportacaoFase4Service.importar_pedidos_completo(
            df_pedidos,
            df_itens,
            usuario=current_user.username
        )

        # 4. RETORNAR RESULTADO
        if resultado.sucesso:
            return jsonify({
                'sucesso': True,
                'mensagem': resultado.mensagem,
                'detalhes': resultado.to_dict()
            })
        else:
            return jsonify({
                'sucesso': False,
                'mensagem': resultado.mensagem,
                'erros': resultado.erros,
                'avisos': resultado.avisos
            }), 400

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'❌ Erro fatal: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500
