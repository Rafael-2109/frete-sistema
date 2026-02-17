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
from app.utils.timezone import agora_utc_naive

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

@motochefe_bp.route('/carga-inicial/fase4')
@login_required
def fase4():
    """Página de importação Fase 4: Pedidos e Vendas"""
    if not current_user.pode_acessar_motochefe():
        flash('Acesso negado ao sistema MotoChefe.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('motochefe/carga_inicial/fase4.html')


@motochefe_bp.route('/carga-inicial/fase4/importar', methods=['POST'])
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

        # 2. LER MODO DE OPERAÇÃO
        modo = request.form.get('modo', 'COMPLETO')  # COMPLETO ou HISTORICO

        # 3. CARREGAR DATAFRAMES
        # ✅ Forçar numero_pedido e numero_chassi como string para preservar zeros à esquerda e evitar .0
        df_pedidos = pd.read_excel(file_pedidos, sheet_name=0, dtype={'numero_pedido': str, 'cliente_cnpj': str})
        df_itens = pd.read_excel(file_itens, sheet_name=0, dtype={'numero_pedido': str, 'numero_chassi': str})

        # ✅ LIMPAR ESPAÇOS EM BRANCO de colunas críticas (resolve "03.09JR " vs "03.09JR")
        if 'numero_pedido' in df_pedidos.columns:
            df_pedidos['numero_pedido'] = df_pedidos['numero_pedido'].fillna('').astype(str).str.strip()
        if 'cliente_cnpj' in df_pedidos.columns:
            df_pedidos['cliente_cnpj'] = df_pedidos['cliente_cnpj'].fillna('').astype(str).str.strip()
        if 'numero_pedido' in df_itens.columns:
            df_itens['numero_pedido'] = df_itens['numero_pedido'].fillna('').astype(str).str.strip()
        if 'numero_chassi' in df_itens.columns:
            df_itens['numero_chassi'] = df_itens['numero_chassi'].fillna('').astype(str).str.strip()

        # 4. IMPORTAR PEDIDOS COM O MODO ESPECIFICADO
        resultado = ImportacaoFase4Service.importar_pedidos_completo(
            df_pedidos,
            df_itens,
            usuario=current_user.nome,
            modo=modo
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


# ============================================================
# IMPORTAÇÃO HISTÓRICA - FASES 5, 6 E 7
# ============================================================

@motochefe_bp.route('/carga-inicial/historico')
@login_required
def importacao_historico():
    """Página de importação histórica (Fases 5, 6, 7)"""
    if not current_user.pode_acessar_motochefe():
        flash('Acesso negado ao sistema MotoChefe.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('motochefe/carga_inicial/historico.html')


@motochefe_bp.route('/carga-inicial/historico/download-template')
@login_required
def download_template_historico():
    """Download do template Excel de importação histórica"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    try:
        from app.motochefe.services.importacao_historico_service import gerar_template_historico_excel

        arquivo = gerar_template_historico_excel()

        return send_file(
            arquivo,
            as_attachment=True,
            download_name='MotoChefe_Importacao_Historica.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'Erro ao gerar template: {str(e)}', 'danger')
        return redirect(url_for('motochefe.importacao_historico'))


@motochefe_bp.route('/carga-inicial/historico/preview', methods=['POST'])
@login_required
@csrf_exempt
def preview_historico():
    """Preview dos dados do Excel antes de importar"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    try:
        if 'arquivo' not in request.files:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum arquivo enviado'
            }), 400

        file = request.files['arquivo']

        if not file or not arquivo_permitido(file.filename):
            return jsonify({
                'sucesso': False,
                'mensagem': 'Arquivo inválido. Use .xlsx ou .xls'
            }), 400

        # Ler Excel
        excel_file = pd.ExcelFile(file)
        abas_presentes = excel_file.sheet_names

        # Validar abas obrigatórias
        abas_necessarias = ['Comissoes', 'Montagens', 'Movimentacoes']
        abas_faltando = [aba for aba in abas_necessarias if aba not in abas_presentes]

        if abas_faltando:
            return jsonify({
                'sucesso': False,
                'mensagem': f"Abas faltando: {', '.join(abas_faltando)}"
            }), 400

        # Carregar DataFrames
        df_comissoes = pd.read_excel(excel_file, sheet_name='Comissoes')
        df_montagens = pd.read_excel(excel_file, sheet_name='Montagens')
        df_movimentacoes = pd.read_excel(excel_file, sheet_name='Movimentacoes')

        # Preparar preview
        preview = {
            'comissoes': {
                'total': len(df_comissoes),
                'colunas': list(df_comissoes.columns),
                'primeiras_linhas': df_comissoes.head(5).fillna('').to_dict(orient='records')
            },
            'montagens': {
                'total': len(df_montagens),
                'colunas': list(df_montagens.columns),
                'primeiras_linhas': df_montagens.head(5).fillna('').to_dict(orient='records')
            },
            'movimentacoes': {
                'total': len(df_movimentacoes),
                'colunas': list(df_movimentacoes.columns),
                'primeiras_linhas': df_movimentacoes.head(5).fillna('').to_dict(orient='records')
            }
        }

        # Salvar arquivo temporariamente para importação posterior
        filename = secure_filename(f"historico_{current_user.id}_{agora_utc_naive().strftime('%Y%m%d%H%M%S')}.xlsx")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.seek(0)  # Reset file pointer
        file.save(filepath)

        return jsonify({
            'sucesso': True,
            'mensagem': 'Preview carregado com sucesso',
            'preview': preview,
            'arquivo_temp': filename
        })

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao ler arquivo: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500


@motochefe_bp.route('/carga-inicial/historico/importar', methods=['POST'])
@login_required
@csrf_exempt
def importar_historico():
    """Executa importação histórica completa (Fases 5, 6, 7)"""
    if not current_user.pode_acessar_motochefe():
        return jsonify({'erro': 'Acesso negado'}), 403

    try:
        # Buscar arquivo temporário
        arquivo_temp = request.json.get('arquivo_temp')
        if not arquivo_temp:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Arquivo não encontrado. Faça o preview novamente.'
            }), 400

        filepath = os.path.join(UPLOAD_FOLDER, arquivo_temp)
        if not os.path.exists(filepath):
            return jsonify({
                'sucesso': False,
                'mensagem': 'Arquivo temporário expirado. Faça o upload novamente.'
            }), 400

        # Carregar Excel
        excel_file = pd.ExcelFile(filepath)
        df_comissoes = pd.read_excel(excel_file, sheet_name='Comissoes')
        df_montagens = pd.read_excel(excel_file, sheet_name='Montagens')
        df_movimentacoes = pd.read_excel(excel_file, sheet_name='Movimentacoes')

        # Importar serviços
        from app.motochefe.services.importacao_historico_service import (
            importar_comissoes_historico,
            importar_montagens_historico,
            importar_movimentacoes_historico
        )

        resultados = {}

        # FASE 5: COMISSÕES
        resultado_fase5 = importar_comissoes_historico(df_comissoes, usuario=current_user.nome)
        resultados['fase5'] = {
            'sucesso': resultado_fase5.sucesso,
            'mensagem': resultado_fase5.mensagem,
            'comissoes_criadas': resultado_fase5.comissoes_criadas,
            'comissoes_pagas': resultado_fase5.comissoes_pagas,
            'comissoes_pendentes': resultado_fase5.comissoes_pendentes,
            'lotes_criados': resultado_fase5.movimentacoes_pai_criadas,
            'valor_total_pago': float(resultado_fase5.valor_total_pago),
            'erros': resultado_fase5.erros,
            'avisos': resultado_fase5.avisos
        }

        if not resultado_fase5.sucesso:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro na Fase 5 (Comissões)',
                'resultados': resultados
            }), 400

        # FASE 6: MONTAGENS
        resultado_fase6 = importar_montagens_historico(df_montagens, usuario=current_user.nome)
        resultados['fase6'] = {
            'sucesso': resultado_fase6.sucesso,
            'mensagem': resultado_fase6.mensagem,
            'itens_atualizados': resultado_fase6.itens_atualizados,
            'titulos_receber': resultado_fase6.titulos_receber_criados,
            'titulos_pagar': resultado_fase6.titulos_pagar_criados,
            'movimentacoes_recebimento': resultado_fase6.movimentacoes_recebimento,
            'movimentacoes_pagamento': resultado_fase6.movimentacoes_pagamento,
            'valor_deduzido_venda': float(resultado_fase6.valor_total_deduzido_venda),
            'erros': resultado_fase6.erros,
            'avisos': resultado_fase6.avisos
        }

        if not resultado_fase6.sucesso:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro na Fase 6 (Montagens)',
                'resultados': resultados
            }), 400

        # FASE 7: MOVIMENTAÇÕES
        resultado_fase7 = importar_movimentacoes_historico(df_movimentacoes, usuario=current_user.nome)
        resultados['fase7'] = {
            'sucesso': resultado_fase7.sucesso,
            'mensagem': resultado_fase7.mensagem,
            'titulos_receber': resultado_fase7.titulos_receber_criados,
            'titulos_pagar': resultado_fase7.titulos_pagar_criados,
            'movimentacoes_recebimento': resultado_fase7.movimentacoes_recebimento,
            'movimentacoes_pagamento': resultado_fase7.movimentacoes_pagamento,
            'valor_deduzido_venda': float(resultado_fase7.valor_total_deduzido_venda),
            'erros': resultado_fase7.erros,
            'avisos': resultado_fase7.avisos
        }

        if not resultado_fase7.sucesso:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro na Fase 7 (Movimentações)',
                'resultados': resultados
            }), 400

        # Limpar arquivo temporário
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'sucesso': True,
            'mensagem': '✅ Importação histórica concluída com sucesso!',
            'resultados': resultados
        })

    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'mensagem': f'❌ Erro fatal: {str(e)}',
            'erro_detalhado': traceback.format_exc()
        }), 500
