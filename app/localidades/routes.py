import pandas as pd
import openpyxl
import tempfile
import os
from datetime import datetime
from io import BytesIO
from sqlalchemy import inspect

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import login_required

from app import db
from app.localidades.forms import CidadeForm
from app.localidades.models import Cidade, CadastroRota, CadastroSubRota
from app.permissions.decorators import check_permission as require_permission
from app.utils.timezone import agora_utc_naive

localidades_bp = Blueprint('localidades', __name__, url_prefix='/localidades')

@localidades_bp.route('/')
@login_required
def index():
    """Dashboard do módulo localidades"""
    try:
        inspector = inspect(db.engine)
        
        # Estatísticas de cidades
        total_cidades = Cidade.query.count() if inspector.has_table('cidades') else 0
        
        # Estatísticas de rotas
        if inspector.has_table('cadastro_rota'):
            total_rotas = CadastroRota.query.count()
            rotas_ativas = CadastroRota.query.filter_by(ativa=True).count()
        else:
            total_rotas = rotas_ativas = 0
            
        # Estatísticas de sub-rotas
        if inspector.has_table('cadastro_sub_rota'):
            total_sub_rotas = CadastroSubRota.query.count()
            sub_rotas_ativas = CadastroSubRota.query.filter_by(ativa=True).count()
        else:
            total_sub_rotas = sub_rotas_ativas = 0
        
    except Exception:
        total_cidades = total_rotas = rotas_ativas = total_sub_rotas = sub_rotas_ativas = 0
    
    return render_template('localidades/dashboard.html',
                         total_cidades=total_cidades,
                         total_rotas=total_rotas,
                         rotas_ativas=rotas_ativas,
                         total_sub_rotas=total_sub_rotas,
                         sub_rotas_ativas=sub_rotas_ativas)

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

    filename = f"export_cidades_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@localidades_bp.route('/ajax/cidades_por_uf/<uf>')
@login_required
def cidades_por_uf(uf):
    cidades = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all()
    return jsonify([cidade.nome for cidade in cidades])

@localidades_bp.route('/ajax/cidades_por_uf_ibge/<uf>')
@login_required
def cidades_por_uf_ibge(uf):
    """Retorna cidades com codigo IBGE para autocomplete CarVia."""
    cidades = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all()
    return jsonify([{'nome': c.nome, 'codigo_ibge': c.codigo_ibge} for c in cidades])

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
    # Filtros
    cod_uf = request.args.get('cod_uf', '')
    rota = request.args.get('rota', '')
    
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('cadastro_rota'):
            # Query base
            query = CadastroRota.query.filter_by(ativa=True)
            
            # Aplicar filtros
            if cod_uf:
                query = query.filter(CadastroRota.cod_uf == cod_uf)
            if rota:
                query = query.filter(CadastroRota.rota.ilike(f'%{rota}%'))
            
            # Ordenação
            rotas = query.order_by(CadastroRota.cod_uf).all()
            
            # 🔧 CARREGAR UFS DOS DADOS REAIS
            ufs_disponiveis = sorted(set(
                r.cod_uf for r in CadastroRota.query.all() 
                if r.cod_uf
            ))
        else:
            rotas = []
            ufs_disponiveis = []
    except Exception:
        rotas = []
        ufs_disponiveis = []
    
    return render_template('localidades/listar_rotas.html',
                         rotas=rotas,
                         cod_uf=cod_uf,
                         rota=rota,
                         ufs_disponiveis=ufs_disponiveis)

@localidades_bp.route('/sub-rotas')
@login_required
def listar_sub_rotas():
    """Lista cadastro de sub-rotas (detalhamento por cidade)"""
    # Filtros
    cod_uf = request.args.get('cod_uf', '')
    nome_cidade = request.args.get('nome_cidade', '')
    sub_rota = request.args.get('sub_rota', '')
    
    # Paginação
    try:
        page = int(request.args.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    per_page = 200  # 200 itens por página conforme solicitado
    
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('cadastro_sub_rota'):
            # Query base
            query = CadastroSubRota.query.filter_by(ativa=True)
            
            # Aplicar filtros
            if cod_uf:
                query = query.filter(CadastroSubRota.cod_uf == cod_uf)
            if nome_cidade:
                query = query.filter(CadastroSubRota.nome_cidade.ilike(f'%{nome_cidade}%'))
            if sub_rota:
                query = query.filter(CadastroSubRota.sub_rota.ilike(f'%{sub_rota}%'))
            
            # Ordenação e paginação
            sub_rotas = query.order_by(CadastroSubRota.cod_uf, CadastroSubRota.nome_cidade).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Buscar opções dos filtros
            opcoes_ufs = sorted(set(
                sr.cod_uf for sr in CadastroSubRota.query.with_entities(CadastroSubRota.cod_uf).distinct() 
                if sr.cod_uf and sr.cod_uf.strip()
            ))
            
            opcoes_cidades = sorted(set(
                sr.nome_cidade for sr in CadastroSubRota.query.with_entities(CadastroSubRota.nome_cidade).distinct() 
                if sr.nome_cidade and sr.nome_cidade.strip()
            ))
        else:
            sub_rotas = None
            opcoes_ufs = []
            opcoes_cidades = []
    except Exception:
        sub_rotas = None
        opcoes_ufs = []
        opcoes_cidades = []
    
    return render_template('localidades/listar_sub_rotas.html',
                         sub_rotas=sub_rotas,
                         cod_uf=cod_uf,
                         nome_cidade=nome_cidade,
                         sub_rota=sub_rota,
                         opcoes_ufs=opcoes_ufs,
                         opcoes_cidades=opcoes_cidades)

# =====================================
# 📤 ROTAS DE IMPORTAÇÃO 
# =====================================

@localidades_bp.route('/rotas/importar')
@login_required
@require_permission('localidades', 'importar', 'editar')  # Sistema novo: módulo.função.nível
def importar_rotas():
    """Tela para importar rotas"""
    return render_template('localidades/importar_rotas.html')

@localidades_bp.route('/rotas/importar', methods=['POST'])
@login_required
def processar_importacao_rotas():
    """Processar importação de cadastro de rotas"""
    try:
        import pandas as pd
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
                    erros.append(f"Linha {index + 1}: UF '{cod_uf}' não existe no cadastro de cidades") # type: ignore
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
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
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
@require_permission('localidades', 'importar', 'editar')  # Sistema novo: mesmo nível que rotas
def importar_sub_rotas():
    """Tela para importar sub-rotas"""
    return render_template('localidades/importar_sub_rotas.html')

@localidades_bp.route('/sub-rotas/importar', methods=['POST'])
@login_required
def processar_importacao_sub_rotas():
    """Processar importação de cadastro de sub-rotas"""
    try:
        import pandas as pd
        import tempfile
        import os
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
                nome_cidade = str(row.get('CIDADE', '')).strip() if pd.notna(row.get('CIDADE')) else ''  # ✅ REMOVIDO .upper()
                sub_rota = str(row.get('SUB ROTA', '')).strip() if pd.notna(row.get('SUB ROTA')) else ''
                
                if not cod_uf or cod_uf == 'NAN' or not nome_cidade or nome_cidade == 'NAN' or not sub_rota or sub_rota == 'NAN':
                    continue
                
                # ✅ VALIDAR COMBINAÇÃO CIDADE+UF com busca case-insensitive
                cidade_existe = Cidade.query.filter(
                    Cidade.uf == cod_uf,
                    Cidade.nome.ilike(nome_cidade)
                ).first()
                if not cidade_existe:
                    erros.append(f"Linha {index + 1}: Combinação '{nome_cidade}/{cod_uf}' não existe no cadastro de cidades") # type: ignore
                    continue
                
                # ✅ USAR O NOME REAL DA CIDADE DO BANCO para garantir consistência
                nome_cidade_real = cidade_existe.nome
                
                # Verificar se já existe (chave única: UF + Cidade)
                sub_rota_existente = CadastroSubRota.query.filter_by(cod_uf=cod_uf, nome_cidade=nome_cidade_real).first()
                
                if sub_rota_existente:
                    # ✏️ ATUALIZAR EXISTENTE (substitui sub rota)
                    sub_rota_existente.sub_rota = sub_rota
                    sub_rota_existente.ativa = True  # Reativar se estava inativo
                    sub_rotas_atualizadas += 1
                else:
                    # ➕ CRIAR NOVO
                    nova_sub_rota = CadastroSubRota()
                    nova_sub_rota.cod_uf = cod_uf
                    nova_sub_rota.nome_cidade = nome_cidade_real  # ✅ USAR NOME REAL DO BANCO
                    nova_sub_rota.sub_rota = sub_rota
                    nova_sub_rota.ativa = True
                    
                    db.session.add(nova_sub_rota)
                    sub_rotas_importadas += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
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

# ========== EXPORTS PARA ROTAS ==========

@localidades_bp.route('/rotas/baixar-modelo')
@login_required
def baixar_modelo_rotas():
    """Baixar modelo Excel para importação de rotas"""
    try:
        from io import BytesIO
        
        # Dados exemplo conforme arquivo CSV 9
        dados_exemplo = {
            'cod_uf': ['ES', 'RJ', 'SP', 'MG'],
            'rota': ['ESPÍRITO SANTO', 'RIO DE JANEIRO', 'SÃO PAULO', 'MINAS GERAIS']
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # Instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Campos obrigatórios: cod_uf, rota',
                    '2. cod_uf deve ter 2 caracteres (ES, RJ, SP, MG)',
                    '3. UF deve existir no cadastro de cidades',
                    '4. Comportamento: SUBSTITUI se UF já existe',
                    '5. Rota única por UF',
                    '6. Validação automática de UF'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_rotas.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('localidades.listar_rotas'))

@localidades_bp.route('/rotas/exportar-dados')
@login_required
def exportar_dados_rotas():
    """Exportar dados existentes de rotas"""
    try:
        from io import BytesIO
        
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('cadastro_rota'):
            rotas = CadastroRota.query.filter_by(ativa=True).order_by(
                CadastroRota.cod_uf
            ).all()
        else:
            rotas = []
        
        if not rotas:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('localidades.listar_rotas'))
        
        # Converter para Excel
        dados_export = []
        for r in rotas:
            dados_export.append({
                'cod_uf': r.cod_uf,
                'rota': r.rota,
                'ativa': 'Sim' if r.ativa else 'Não'
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rotas', index=False)
            
            # Estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total Rotas', 'UFs Atendidas', 'Rotas Ativas'],
                'Valor': [
                    len(rotas),
                    len(set(r.cod_uf for r in rotas)),
                    len([r for r in rotas if r.ativa])
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=rotas_export_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('localidades.listar_rotas'))

# ========== EXPORTS PARA SUB-ROTAS ==========

@localidades_bp.route('/sub-rotas/baixar-modelo')
@login_required
def baixar_modelo_sub_rotas():
    """Baixar modelo Excel para importação de sub-rotas"""
    try:
        from io import BytesIO
        
        # Dados exemplo conforme arquivo CSV 10
        dados_exemplo = {
            'cod_uf': ['ES', 'ES', 'RJ', 'RJ'],
            'nome_cidade': ['VITÓRIA', 'SERRA', 'RIO DE JANEIRO', 'NITERÓI'],
            'sub_rota': ['CENTRO ES', 'GRANDE VITÓRIA', 'ZONA SUL RJ', 'REGIÃO OCEÂNICA']
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # Instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Campos obrigatórios: cod_uf, nome_cidade, sub_rota',
                    '2. cod_uf deve ter 2 caracteres (ES, RJ, SP, MG)',
                    '3. Combinação UF+Cidade deve existir no cadastro de cidades',
                    '4. Comportamento: SUBSTITUI se UF+Cidade já existe',
                    '5. Sub-rota única por combinação UF+Cidade',
                    '6. Validação automática de cidade e UF'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_sub_rotas.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('localidades.listar_sub_rotas'))

@localidades_bp.route('/sub-rotas/exportar-dados')
@login_required
def exportar_dados_sub_rotas():
    """Exportar dados existentes de sub-rotas"""
    try:
        from io import BytesIO
        
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('cadastro_sub_rota'):
            sub_rotas = CadastroSubRota.query.filter_by(ativa=True).order_by(
                CadastroSubRota.cod_uf, CadastroSubRota.nome_cidade
            ).all()
        else:
            sub_rotas = []
        
        if not sub_rotas:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('localidades.listar_sub_rotas'))
        
        # Converter para Excel
        dados_export = []
        for sr in sub_rotas:
            dados_export.append({
                'cod_uf': sr.cod_uf,
                'nome_cidade': sr.nome_cidade,
                'sub_rota': sr.sub_rota,
                'ativa': 'Sim' if sr.ativa else 'Não'
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sub Rotas', index=False)
            
            # Estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total Sub-Rotas', 'UFs Atendidas', 'Cidades Atendidas', 'Sub-Rotas Ativas'],
                'Valor': [
                    len(sub_rotas),
                    len(set(sr.cod_uf for sr in sub_rotas)),
                    len(set(sr.nome_cidade for sr in sub_rotas)),
                    len([sr for sr in sub_rotas if sr.ativa])
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=sub_rotas_export_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('localidades.listar_sub_rotas'))
