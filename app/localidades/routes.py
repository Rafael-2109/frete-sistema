from flask import request, render_template, Blueprint, send_file, jsonify

from flask_login import login_required

from app.localidades.forms import CidadeForm

from app.localidades.models import Cidade, CadastroRota, CadastroSubRota
from app import db

from io import BytesIO

import openpyxl

from datetime import datetime

localidades_bp = Blueprint('localidades', __name__,url_prefix='/localidades')

@localidades_bp.route('/cidades', methods=['GET'])
@login_required
def cadastrar_cidade():
    form = CidadeForm()
    uf = request.args.get('uf')
    cidade_nome = request.args.get('cidade')
    microrregiao = request.args.get('microrregiao')
    mesorregiao = request.args.get('mesorregiao')

    # Iniciar a query para cidades
    query = Cidade.query.order_by(Cidade.uf).order_by(Cidade.nome)

    # Aplicar filtros conforme parâmetros enviados
    if uf:
        query = query.filter(Cidade.uf == uf)

    if cidade_nome:
        query = query.filter(Cidade.nome == cidade_nome)

    if microrregiao:
        query = query.filter(Cidade.microrregiao == microrregiao)

    if mesorregiao:
        query = query.filter(Cidade.mesorregiao == mesorregiao)

    # Executar a query após filtros
    cidades = query.order_by(Cidade.nome).all()

    # Populando selects corretamente
    cidade_nome = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all() if uf else []
    microrregioes = sorted({c.microrregiao for c in Cidade.query.filter_by(uf=uf).all() if c.microrregiao}) if uf else []
    mesorregioes = sorted({c.mesorregiao for c in Cidade.query.filter_by(uf=uf).all() if c.mesorregiao}) if uf else []

    return render_template('localidades/cidades.html',
                           cidades=cidades,
                           form=form,
                           microrregioes=microrregioes,
                           mesorregioes=mesorregioes,
                           filtros=request.args)


    
@localidades_bp.route('/exportar_cidades', methods=['GET'])
@login_required
def exportar_cidades():
    form = CidadeForm()
    uf = request.args.get('uf')
    microrregiao = request.args.get('microrregiao')
    mesorregiao = request.args.get('mesorregiao')

    query = Cidade.query
    if uf:
        query = query.filter_by(uf=uf)
    if microrregiao:
        query = query.filter_by(microrregiao=microrregiao)
    if mesorregiao:
        query = query.filter_by(mesorregiao=mesorregiao)

    cidades = query.all()

    output = BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['Transportadora', 'Cidade', 'UF', 'Codigo IBGE', 'Tabela', 'Lead Time', 'Microrregião', 'Mesorregião'])

    for c in cidades:
        sheet.append(['', c.nome, c.uf, c.codigo_ibge, '', '', c.microrregiao, c.mesorregiao])

    workbook.save(output)
    output.seek(0)

    filename = f"export_cidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@localidades_bp.route('/ajax/cidades_por_uf/<uf>')
@login_required
def cidades_por_uf(uf):
    cidades = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all()
    return jsonify([cidade.nome for cidade in cidades])

@localidades_bp.route('/ajax/microrregioes_por_uf/<uf>')
@login_required
def microrregioes_por_uf(uf):
    microrregioes = Cidade.query.filter_by(uf=uf).distinct(Cidade.microrregiao).all()
    micros = sorted(set(c.microrregiao for c in microrregioes if c.microrregiao))
    return jsonify(micros)

@localidades_bp.route('/ajax/mesorregioes_por_uf/<uf>')
@login_required
def mesorregioes_por_uf(uf):
    mesorregioes = Cidade.query.filter_by(uf=uf).distinct(Cidade.mesorregiao).all()
    mesos = sorted(set(c.mesorregiao for c in mesorregioes if c.mesorregiao))
    return jsonify(mesos)


# =====================================
# 🚚 ROTAS MOVIDAS DE /producao/ 
# =====================================
# Rotas e Sub-rotas são cadastros de regiões/destinos para fretes

@localidades_bp.route('/rotas')
@login_required
def listar_rotas():
    """Lista cadastro de rotas principais por UF"""
    try:
        rotas = CadastroRota.query.filter_by(ativa=True).order_by(CadastroRota.cod_uf).all() if db.engine.has_table('cadastro_rota') else []
    except Exception:
        rotas = []
    
    return render_template('localidades/listar_rotas.html', rotas=rotas)

@localidades_bp.route('/sub-rotas')
@login_required
def listar_sub_rotas():
    """Lista cadastro de sub-rotas (detalhamento por cidade)"""
    # Filtros
    cod_uf = request.args.get('cod_uf', '')
    nome_cidade = request.args.get('nome_cidade', '')
    
    try:
        if db.engine.has_table('cadastro_sub_rota'):
            # Query base
            query = CadastroSubRota.query.filter_by(ativa=True)
            
            # Aplicar filtros
            if cod_uf:
                query = query.filter(CadastroSubRota.cod_uf.ilike(f'%{cod_uf}%'))
            if nome_cidade:
                query = query.filter(CadastroSubRota.nome_cidade.ilike(f'%{nome_cidade}%'))
            
            # Ordenação
            sub_rotas = query.order_by(CadastroSubRota.cod_uf, CadastroSubRota.nome_cidade).all()
        else:
            sub_rotas = []
    except Exception:
        sub_rotas = []
    
    return render_template('localidades/listar_sub_rotas.html',
                         sub_rotas=sub_rotas,
                         cod_uf=cod_uf,
                         nome_cidade=nome_cidade)

# =====================================
# 📤 ROTAS DE IMPORTAÇÃO 
# =====================================

@localidades_bp.route('/rotas/importar')
@login_required
def importar_rotas():
    """Tela para importar cadastro de rotas"""
    return render_template('localidades/importar_rotas.html')

@localidades_bp.route('/rotas/importar', methods=['POST'])
@login_required
def processar_importacao_rotas():
    """Processar importação de cadastro de rotas"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        from flask import flash, redirect, url_for, request
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('localidades.importar_rotas'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('localidades.importar_rotas'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('localidades.importar_rotas'))
        
        # Processar arquivo temporário
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                arquivo.save(temp_file.name)
                
                if arquivo.filename.lower().endswith('.xlsx'):
                    df = pd.read_excel(temp_file.name)
                else:
                    df = pd.read_csv(temp_file.name, encoding='utf-8', sep=';')
                
                os.unlink(temp_file.name)
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
            return redirect(url_for('localidades.importar_rotas'))
        
        # 🎯 MAPEAMENTO EXATO conforme arquivo 9 - cadastro de rotas
        colunas_esperadas = {
            'cod_uf': 'ESTADO',
            'rota': 'ROTA'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = ['ESTADO', 'ROTA']
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('localidades.importar_rotas'))
        
        # COMPORTAMENTO: SUBSTITUI/ADICIONA - Substitui rota se UF já existe
        rotas_importadas = 0
        rotas_atualizadas = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_uf = str(row.get('ESTADO', '')).strip().upper() if pd.notna(row.get('ESTADO')) else ''
                rota = str(row.get('ROTA', '')).strip() if pd.notna(row.get('ROTA')) else ''
                
                if not cod_uf or cod_uf == 'NAN' or not rota or rota == 'NAN':
                    continue
                
                # ✅ VALIDAR UF (deve existir no cadastro de cidades)
                cidade_existe = Cidade.query.filter_by(uf=cod_uf).first()
                if not cidade_existe:
                    erros.append(f"Linha {index + 1}: UF '{cod_uf}' não existe no cadastro de cidades")
                    continue
                
                # Verificar se já existe
                rota_existente = CadastroRota.query.filter_by(cod_uf=cod_uf).first()
                
                if rota_existente:
                    # ✏️ ATUALIZAR EXISTENTE (substitui rota)
                    rota_existente.rota = rota
                    rota_existente.ativa = True  # Reativar se estava inativo
                    rotas_atualizadas += 1
                else:
                    # ➕ CRIAR NOVO
                    nova_rota = CadastroRota()
                    nova_rota.cod_uf = cod_uf
                    nova_rota.rota = rota
                    nova_rota.ativa = True
                    
                    db.session.add(nova_rota)
                    rotas_importadas += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        # Mensagens de resultado
        if rotas_importadas > 0 or rotas_atualizadas > 0:
            mensagem = f"✅ Importação concluída: {rotas_importadas} novas rotas, {rotas_atualizadas} atualizadas"
            if erros:
                mensagem += f". {len(erros)} erros encontrados."
            flash(mensagem, 'success')
        else:
            flash("⚠️ Nenhuma rota foi importada.", 'warning')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('localidades.listar_rotas'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('localidades.importar_rotas'))

@localidades_bp.route('/sub-rotas/importar')
@login_required
def importar_sub_rotas():
    """Tela para importar cadastro de sub-rotas"""
    return render_template('localidades/importar_sub_rotas.html')

@localidades_bp.route('/sub-rotas/importar', methods=['POST'])
@login_required
def processar_importacao_sub_rotas():
    """Processar importação de cadastro de sub-rotas"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        from flask import flash, redirect, url_for, request
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('localidades.importar_sub_rotas'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('localidades.importar_sub_rotas'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('localidades.importar_sub_rotas'))
        
        # Processar arquivo temporário
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                arquivo.save(temp_file.name)
                
                if arquivo.filename.lower().endswith('.xlsx'):
                    df = pd.read_excel(temp_file.name)
                else:
                    df = pd.read_csv(temp_file.name, encoding='utf-8', sep=';')
                
                os.unlink(temp_file.name)
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
            return redirect(url_for('localidades.importar_sub_rotas'))
        
        # 🎯 MAPEAMENTO EXATO conforme arquivo 10 - cadastro de sub rotas
        colunas_esperadas = {
            'cod_uf': 'ESTADO',
            'nome_cidade': 'CIDADE',
            'sub_rota': 'SUB ROTA'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = ['ESTADO', 'CIDADE', 'SUB ROTA']
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('localidades.importar_sub_rotas'))
        
        # COMPORTAMENTO: SUB ROTA ÚNICA POR COMBINAÇÃO UF+CIDADE
        sub_rotas_importadas = 0
        sub_rotas_atualizadas = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_uf = str(row.get('ESTADO', '')).strip().upper() if pd.notna(row.get('ESTADO')) else ''
                nome_cidade = str(row.get('CIDADE', '')).strip().upper() if pd.notna(row.get('CIDADE')) else ''
                sub_rota = str(row.get('SUB ROTA', '')).strip() if pd.notna(row.get('SUB ROTA')) else ''
                
                if not cod_uf or cod_uf == 'NAN' or not nome_cidade or nome_cidade == 'NAN' or not sub_rota or sub_rota == 'NAN':
                    continue
                
                # ✅ VALIDAR COMBINAÇÃO CIDADE+UF (deve existir no cadastro de cidades)
                cidade_existe = Cidade.query.filter_by(uf=cod_uf, nome=nome_cidade).first()
                if not cidade_existe:
                    erros.append(f"Linha {index + 1}: Combinação '{nome_cidade}/{cod_uf}' não existe no cadastro de cidades")
                    continue
                
                # Verificar se já existe (chave única: UF + Cidade)
                sub_rota_existente = CadastroSubRota.query.filter_by(cod_uf=cod_uf, nome_cidade=nome_cidade).first()
                
                if sub_rota_existente:
                    # ✏️ ATUALIZAR EXISTENTE (substitui sub rota)
                    sub_rota_existente.sub_rota = sub_rota
                    sub_rota_existente.ativa = True  # Reativar se estava inativo
                    sub_rotas_atualizadas += 1
                else:
                    # ➕ CRIAR NOVO
                    nova_sub_rota = CadastroSubRota()
                    nova_sub_rota.cod_uf = cod_uf
                    nova_sub_rota.nome_cidade = nome_cidade
                    nova_sub_rota.sub_rota = sub_rota
                    nova_sub_rota.ativa = True
                    
                    db.session.add(nova_sub_rota)
                    sub_rotas_importadas += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        # Mensagens de resultado
        if sub_rotas_importadas > 0 or sub_rotas_atualizadas > 0:
            mensagem = f"✅ Importação concluída: {sub_rotas_importadas} novas sub-rotas, {sub_rotas_atualizadas} atualizadas"
            if erros:
                mensagem += f". {len(erros)} erros encontrados."
            flash(mensagem, 'success')
        else:
            flash("⚠️ Nenhuma sub-rota foi importada.", 'warning')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('localidades.listar_sub_rotas'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('localidades.importar_sub_rotas'))
