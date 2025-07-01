from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.utils.auth_decorators import require_admin
from datetime import datetime
from sqlalchemy import inspect

# 📦 Blueprint da produção (seguindo padrão dos outros módulos)
producao_bp = Blueprint('producao', __name__, url_prefix='/producao')

@producao_bp.route('/')
@login_required
def index():
    """Dashboard do módulo produção"""
    try:
        from sqlalchemy import func
        
        # ✅ SEGURO: Verifica se tabelas existem antes de fazer query
        inspector = inspect(db.engine)
        if inspector.has_table('programacao_producao'):
            total_programacao = ProgramacaoProducao.query.count()
            
            # Produtos únicos programados
            produtos_programados = ProgramacaoProducao.query.with_entities(
                ProgramacaoProducao.cod_produto
            ).distinct().count()
            
            # Linhas de produção únicas
            linhas_producao = ProgramacaoProducao.query.with_entities(
                ProgramacaoProducao.linha_producao
            ).filter(ProgramacaoProducao.linha_producao.isnot(None)).distinct().count()
            
            # Quantidade total programada
            qtd_total_programada = db.session.query(
                func.sum(ProgramacaoProducao.qtd_programada)
            ).scalar() or 0
            
            # Programação recente (últimos 10)
            programacao_recente = ProgramacaoProducao.query.order_by(
                ProgramacaoProducao.data_programacao.desc()
            ).limit(10).all()
        else:
            total_programacao = produtos_programados = linhas_producao = 0
            qtd_total_programada = 0
            programacao_recente = []
        
        # Dados de palletização
        if inspector.has_table('cadastro_palletizacao'):
            produtos_palletizados = CadastroPalletizacao.query.filter_by(ativo=True).count()
            
            # Peso total estimado (soma dos pesos)
            peso_total_estimado = db.session.query(
                func.sum(CadastroPalletizacao.peso_bruto)
            ).filter_by(ativo=True).scalar() or 0
            
            # Palletização recente (últimos 10)
            palletizacao_recente = CadastroPalletizacao.query.filter_by(
                ativo=True
            ).order_by(CadastroPalletizacao.updated_at.desc()).limit(10).all()
        else:
            produtos_palletizados = peso_total_estimado = 0
            palletizacao_recente = []
            
    except Exception as e:
        # ✅ FALLBACK: Se der erro, zera tudo
        total_programacao = produtos_programados = linhas_producao = 0
        qtd_total_programada = peso_total_estimado = produtos_palletizados = 0
        programacao_recente = palletizacao_recente = []
    
    return render_template('producao/dashboard.html',
                         total_programacao=total_programacao,
                         produtos_programados=produtos_programados,
                         produtos_palletizados=produtos_palletizados,
                         linhas_producao=linhas_producao,
                         qtd_total_programada=qtd_total_programada,
                         peso_total_estimado=peso_total_estimado,
                         programacao_recente=programacao_recente,
                         palletizacao_recente=palletizacao_recente)

@producao_bp.route('/programacao')
@login_required
def listar_programacao():
    """Lista programação de produção"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    status = request.args.get('status', '')
    
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('programacao_producao'):
            # Query base
            query = ProgramacaoProducao.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(ProgramacaoProducao.cod_produto.ilike(f'%{cod_produto}%'))
            if status:
                query = query.filter(ProgramacaoProducao.status == status)
            
            # Ordenação
            programacoes = query.order_by(ProgramacaoProducao.data_programacao).all()
        else:
            programacoes = []
    except Exception:
        programacoes = []
    
    return render_template('producao/listar_programacao.html',
                         programacoes=programacoes,
                         cod_produto=cod_produto,
                         status=status)

# 🚚 ROTAS MOVIDAS PARA /localidades/ pois são cadastros de regiões/destinos
# - /localidades/rotas (lista rotas por UF)
# - /localidades/sub-rotas (lista sub-rotas por cidade)

@producao_bp.route('/palletizacao')
@login_required
def listar_palletizacao():
    """Lista cadastro de palletização (com medidas!)"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    
    try:
        if inspector.has_table('cadastro_palletizacao'):
            # Query base
            query = CadastroPalletizacao.query.filter_by(ativo=True)
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(CadastroPalletizacao.cod_produto.ilike(f'%{cod_produto}%'))
            
            # Ordenação
            palletizacoes = query.order_by(CadastroPalletizacao.cod_produto).all()
        else:
            palletizacoes = []
    except Exception:
        palletizacoes = []
    
    return render_template('producao/listar_palletizacao.html',
                         palletizacoes=palletizacoes,
                         cod_produto=cod_produto)

@producao_bp.route('/palletizacao/importar')
@login_required
@require_admin()
def importar_palletizacao():
    """Tela para importar cadastro de palletização"""
    return render_template('producao/importar_palletizacao.html')

@producao_bp.route('/palletizacao/importar', methods=['POST'])
@login_required
@require_admin()
def processar_importacao_palletizacao():
    """Processar importação de cadastro de palletização"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_palletizacao'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_palletizacao'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('producao.importar_palletizacao'))
        
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
            return redirect(url_for('producao.importar_palletizacao'))
        
        # 🎯 MAPEAMENTO EXATO conforme arquivo 8 - cadastro palletização e peso bruto
        colunas_esperadas = {
            'cod_produto': 'Cód.Produto',
            'nome_produto': 'Descrição Produto',
            'palletizacao': 'PALLETIZACAO',
            'peso_bruto': 'PESO BRUTO',
            'altura_cm': 'altura_cm',
            'largura_cm': 'largura_cm',
            'comprimento_cm': 'comprimento_cm'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = ['Cód.Produto', 'Descrição Produto', 'PALLETIZACAO', 'PESO BRUTO']
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('producao.importar_palletizacao'))
        
        # COMPORTAMENTO: SUBSTITUI/ADICIONA - Atualiza existente ou cria novo
        produtos_importados = 0
        produtos_atualizados = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_produto = str(row.get('Cód.Produto', '')).strip() if pd.notna(row.get('Cód.Produto')) else ''
                
                if not cod_produto or cod_produto == 'nan':
                    continue
                
                # Verificar se já existe
                palletizacao_existente = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                
                # 📝 DADOS BÁSICOS
                nome_produto = str(row.get('Descrição Produto', '')).strip()
                palletizacao = float(row.get('PALLETIZACAO', 0) or 0)
                peso_bruto = float(row.get('PESO BRUTO', 0) or 0)
                
                # 📏 MEDIDAS OPCIONAIS
                altura_cm = float(row.get('altura_cm', 0) or 0) if pd.notna(row.get('altura_cm')) else 0
                largura_cm = float(row.get('largura_cm', 0) or 0) if pd.notna(row.get('largura_cm')) else 0
                comprimento_cm = float(row.get('comprimento_cm', 0) or 0) if pd.notna(row.get('comprimento_cm')) else 0
                
                if palletizacao_existente:
                    # ✏️ ATUALIZAR EXISTENTE
                    palletizacao_existente.nome_produto = nome_produto
                    palletizacao_existente.palletizacao = palletizacao
                    palletizacao_existente.peso_bruto = peso_bruto
                    palletizacao_existente.altura_cm = altura_cm
                    palletizacao_existente.largura_cm = largura_cm
                    palletizacao_existente.comprimento_cm = comprimento_cm
                    palletizacao_existente.updated_by = current_user.nome
                    palletizacao_existente.ativo = True  # Reativar se estava inativo
                    produtos_atualizados += 1
                else:
                    # ➕ CRIAR NOVO
                    nova_palletizacao = CadastroPalletizacao()
                    nova_palletizacao.cod_produto = cod_produto
                    nova_palletizacao.nome_produto = nome_produto
                    nova_palletizacao.palletizacao = palletizacao
                    nova_palletizacao.peso_bruto = peso_bruto
                    nova_palletizacao.altura_cm = altura_cm
                    nova_palletizacao.largura_cm = largura_cm
                    nova_palletizacao.comprimento_cm = comprimento_cm
                    nova_palletizacao.created_by = current_user.nome
                    nova_palletizacao.ativo = True
                    
                    db.session.add(nova_palletizacao)
                    produtos_importados += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        # Mensagens de resultado
        if produtos_importados > 0 or produtos_atualizados > 0:
            mensagem = f"✅ Importação concluída: {produtos_importados} novos produtos, {produtos_atualizados} atualizados"
            if erros:
                mensagem += f". {len(erros)} erros encontrados."
            flash(mensagem, 'success')
        else:
            flash("⚠️ Nenhum produto foi importado.", 'warning')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('producao.listar_palletizacao'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('producao.importar_palletizacao'))

@producao_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo produção"""
    try:
        from sqlalchemy import func
        
        # Estatísticas básicas (apenas de produção)
        stats = {
            'total_ops': ProgramacaoProducao.query.count() if inspector.has_table('programacao_producao') else 0,
            'ops_atrasadas': ProgramacaoProducao.query.filter_by(status='PROGRAMADA').count() if inspector.has_table('programacao_producao') else 0,
            'produtos_palletizados': CadastroPalletizacao.query.filter_by(ativo=True).count() if inspector.has_table('cadastro_palletizacao') else 0
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@producao_bp.route('/programacao/importar')
@login_required
@require_admin()
def importar_programacao():
    """Tela para importar programação de produção"""
    return render_template('producao/importar_programacao.html')

@producao_bp.route('/programacao/importar', methods=['POST'])
@login_required
@require_admin()
def processar_importacao_programacao():
    """Processar importação de programação de produção"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_programacao'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_programacao'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('producao.importar_programacao'))
        
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
            return redirect(url_for('producao.importar_programacao'))
        
        # 🎯 MAPEAMENTO EXATO conforme arquivo 5 - programação de produção
        colunas_esperadas = {
            'data_programacao': 'DATA',
            'linha_producao': 'SEÇÃO / MÁQUINA', 
            'cod_produto': 'CÓDIGO',
            'observacao_pcp': 'OP',
            'nome_produto': 'DESCRIÇÃO',
            'cliente_produto': 'CLIENTE',
            'qtd_programada': 'QTDE'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = ['DATA', 'CÓDIGO', 'DESCRIÇÃO', 'QTDE']
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('producao.importar_programacao'))
        
        # COMPORTAMENTO: SEMPRE SUBSTITUI - Deletar todos os dados existentes
        try:
            ProgramacaoProducao.query.delete()
            db.session.commit()
            flash('✅ Dados existentes removidos (substituição completa)', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover dados existentes: {str(e)}', 'warning')
        
        # Processar dados (agora com constraint que inclui cliente)
        produtos_importados = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_produto = str(row.get('CÓDIGO', '')).strip() if pd.notna(row.get('CÓDIGO')) else ''
                
                if not cod_produto or cod_produto == 'nan':
                    continue
                
                # 📅 PROCESSAR DATA
                data_programacao = row.get('DATA')
                if pd.notna(data_programacao):
                    if isinstance(data_programacao, str):
                        try:
                            # Formato brasileiro DD/MM/YYYY
                            data_programacao = pd.to_datetime(data_programacao, format='%d/%m/%Y').date()
                        except:
                            try:
                                data_programacao = pd.to_datetime(data_programacao).date()
                            except:
                                data_programacao = None
                    elif hasattr(data_programacao, 'date'):
                        data_programacao = data_programacao.date()
                else:
                    data_programacao = None
                
                if not data_programacao:
                    erros.append(f"Linha {index + 1}: Data inválida")
                    continue
                
                # 📝 DADOS BÁSICOS
                nome_produto = str(row.get('DESCRIÇÃO', '')).strip()
                qtd_programada = float(row.get('QTDE', 0) or 0)
                
                # ➕ CRIAR NOVO REGISTRO (constraint agora inclui cliente)
                novo_produto = ProgramacaoProducao()
                novo_produto.data_programacao = data_programacao
                novo_produto.cod_produto = cod_produto
                novo_produto.nome_produto = nome_produto
                novo_produto.qtd_programada = qtd_programada
                novo_produto.created_by = current_user.nome
                
                # 🔧 CAMPOS ESPECÍFICOS CONFORME EXCEL
                novo_produto.linha_producao = str(row.get('SEÇÃO / MÁQUINA', '')).strip()
                novo_produto.cliente_produto = str(row.get('CLIENTE', '')).strip()
                novo_produto.observacao_pcp = str(row.get('OP', '')).strip() if row.get('OP') != 'nan' else ''
                
                db.session.add(novo_produto)
                produtos_importados += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        # Mensagens de resultado
        if produtos_importados > 0:
            mensagem = f"✅ Importação concluída: {produtos_importados} produtos programados (substituição completa)"
            if erros:
                mensagem += f". {len(erros)} erros encontrados."
            flash(mensagem, 'success')
        else:
            flash("⚠️ Nenhum produto foi importado.", 'warning')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('producao.listar_programacao'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('producao.importar_programacao'))

# TODO: Implementar outras rotas conforme necessário
# - POST /importar (upload e processamento de arquivos)
# - /criar_op (nova ordem de produção)
# - /editar_rota/<id> (edição de rotas)
# - /relatorios (relatórios específicos)

@producao_bp.route('/programacao/baixar-modelo')
@login_required
def baixar_modelo_programacao():
    """Baixar modelo Excel para importação de programação de produção"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        # Colunas exatas conforme arquivo CSV
        dados_exemplo = {
            'DATA': ['27/06/2025', '28/06/2025', '29/06/2025'],
            'SEÇÃO / MÁQUINA': ['1104', '1105', '1106'],
            'CÓDIGO': [4080177, 4729098, 4320162],
            'OP': ['OP001', 'OP002', ''],
            'DESCRIÇÃO': [
                'PEPINOS EM RODELAS AGRIDOCE VD 12X440G - CAMPO BELO',
                'OL. MIS AZEITE DE OLIVA VD 12X500 ML - ST ISABEL',
                'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO'
            ],
            'CLIENTE': ['CAMPO BELO', 'CAMPO BELO', 'CAMPO BELO'],
            'QTDE': [500, 300, 200]
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # Instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Use as colunas EXATAMENTE como estão nomeadas',
                    '2. DATA no formato DD/MM/YYYY',
                    '3. Campos obrigatórios: DATA, CÓDIGO, DESCRIÇÃO, QTDE',
                    '4. SEÇÃO / MÁQUINA: linha de produção',
                    '5. OP: observação do PCP (opcional)',
                    '6. CLIENTE: marca/cliente do produto',
                    '7. Comportamento: SUBSTITUI todos os dados existentes'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_programacao_producao.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('producao.listar_programacao'))

@producao_bp.route('/programacao/exportar-dados')
@login_required
def exportar_dados_programacao():
    """Exportar dados existentes de programação de produção"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        # Buscar dados
        if inspector.has_table('programacao_producao'):
            programacao = ProgramacaoProducao.query.filter_by(ativo=True).order_by(
                ProgramacaoProducao.data_programacao.desc()
            ).all()
        else:
            programacao = []
        
        if not programacao:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('producao.listar_programacao'))
        
        # Converter para Excel
        dados_export = []
        for p in programacao:
            dados_export.append({
                'DATA': p.data_programacao.strftime('%d/%m/%Y') if p.data_programacao else '',
                'SEÇÃO / MÁQUINA': p.linha_producao or '',
                'CÓDIGO': p.cod_produto,
                'OP': p.observacao_pcp or '',
                'DESCRIÇÃO': p.nome_produto,
                'CLIENTE': p.cliente_produto or '',
                'QTDE': p.qtd_programada
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Programação Produção', index=False)
            
            # Estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total Registros', 'Produtos Únicos', 'Linhas Produção', 'Qtd Total'],
                'Valor': [
                    len(programacao),
                    len(set(p.cod_produto for p in programacao)),
                    len(set(p.linha_producao for p in programacao if p.linha_producao)),
                    sum(p.qtd_programada for p in programacao)
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=programacao_producao_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('producao.listar_programacao'))

@producao_bp.route('/palletizacao/baixar-modelo')
@login_required
def baixar_modelo_palletizacao():
    """Baixar modelo Excel para importação de palletização"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        dados_exemplo = {
            'Cód.Produto': [4210155, 4210156, 4210157],
            'Descrição Produto': [
                'AZEITONA PRETA INTEIRA POUCH 12x400 GR - CAMPO BELO',
                'AZEITONA VERDE INTEIRA POUCH 12x400 GR - CAMPO BELO',
                'PALMITO INTEIRO VD 12x300 GR - CAMPO BELO'
            ],
            'PALLETIZACAO': [80, 90, 100],
            'PESO BRUTO': [9, 8.5, 7.2],
            'altura_cm': [120, 115, 110],
            'largura_cm': [80, 80, 80],
            'comprimento_cm': [100, 100, 100]
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Use as colunas EXATAMENTE como estão nomeadas',
                    '2. Campos obrigatórios: Cód.Produto, Descrição Produto, PALLETIZACAO, PESO BRUTO',
                    '3. PALLETIZACAO: fator para converter qtd em pallets',
                    '4. PESO BRUTO: fator para converter qtd em peso',
                    '5. Medidas em cm são opcionais (altura, largura, comprimento)',
                    '6. Volume m³ será calculado automaticamente',
                    '7. Comportamento: SUBSTITUI/ADICIONA por produto'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_palletizacao.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('producao.listar_palletizacao'))

@producao_bp.route('/palletizacao/exportar-dados')
@login_required
def exportar_dados_palletizacao():
    """Exportar dados existentes de palletização"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        if inspector.has_table('cadastro_palletizacao'):
            palletizacao = CadastroPalletizacao.query.filter_by(ativo=True).order_by(
                CadastroPalletizacao.cod_produto
            ).all()
        else:
            palletizacao = []
        
        if not palletizacao:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('producao.listar_palletizacao'))
        
        dados_export = []
        for p in palletizacao:
            dados_export.append({
                'Cód.Produto': p.cod_produto,
                'Descrição Produto': p.nome_produto,
                'PALLETIZACAO': p.palletizacao,
                'PESO BRUTO': p.peso_bruto,
                'altura_cm': p.altura_cm or '',
                'largura_cm': p.largura_cm or '',
                'comprimento_cm': p.comprimento_cm or '',
                'volume_m3': p.volume_m3
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Palletização', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=palletizacao_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('producao.listar_palletizacao')) 