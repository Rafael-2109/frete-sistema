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
    from sqlalchemy import inspect
    
    # Filtros
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    cod_produto = request.args.get('cod_produto', '')
    nome_produto = request.args.get('nome_produto', '')
    linha_producao_filtro = request.args.get('linha_producao', '')  # 🔧 RENOMEADO para evitar conflito
    
    # Paginação
    try:
        page = int(request.args.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    per_page = 200  # 200 itens por página conforme solicitado
    
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('programacao_producao'):
            # Query base - CORRIGIDO: sem filtro ativo (campo não existe)
            query = ProgramacaoProducao.query
            
            # Aplicar filtros
            if data_de:
                try:
                    data_de_obj = datetime.strptime(data_de, '%Y-%m-%d').date()
                    query = query.filter(ProgramacaoProducao.data_programacao >= data_de_obj)
                except Exception as e:
                    pass
            
            if data_ate:
                try:
                    data_ate_obj = datetime.strptime(data_ate, '%Y-%m-%d').date()
                    query = query.filter(ProgramacaoProducao.data_programacao <= data_ate_obj)
                except Exception as e:
                    pass
            
            if cod_produto:
                query = query.filter(ProgramacaoProducao.cod_produto.ilike(f'%{cod_produto}%'))
            
            if nome_produto:
                query = query.filter(ProgramacaoProducao.nome_produto.ilike(f'%{nome_produto}%'))
            
            if linha_producao_filtro:
                query = query.filter(ProgramacaoProducao.linha_producao.ilike(f'%{linha_producao_filtro}%'))
            
            # Ordenação e paginação
            pagination = query.order_by(ProgramacaoProducao.data_programacao.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            programacao = pagination.items  # Template espera 'programacao'
            
            # 🔧 BUSCAR OPÇÕES PARA OS DROPDOWNS (de todos os registros, não só filtrados)
            todos_registros = ProgramacaoProducao.query.all()
            codigos_produtos = sorted(set(p.cod_produto for p in todos_registros if p.cod_produto))
            nomes_produtos = sorted(set(p.nome_produto for p in todos_registros if p.nome_produto))
            linhas_producao = sorted(set(p.linha_producao for p in todos_registros if p.linha_producao))
            
            # Cálculos para o template
            total_quantidade = sum(p.qtd_programada for p in programacao) if programacao else 0
            produtos_unicos = len(set(p.cod_produto for p in programacao)) if programacao else 0
            linhas_unicas = len(set(p.linha_producao for p in programacao if p.linha_producao)) if programacao else 0
        else:
            pagination = None
            programacao = []
            codigos_produtos = []
            nomes_produtos = []
            linhas_producao = []
            total_quantidade = 0
            produtos_unicos = 0
            linhas_unicas = 0
    except Exception as e:
        print(f"Erro na programação: {e}")
        pagination = None
        programacao = []
        codigos_produtos = []
        nomes_produtos = []
        linhas_producao = []
        total_quantidade = 0
        produtos_unicos = 0
        linhas_unicas = 0

    return render_template('producao/listar_programacao.html',
                         programacao=programacao,  # ✅ Template espera 'programacao'
                         pagination=pagination,
                         total_quantidade=total_quantidade,
                         produtos_unicos=produtos_unicos,
                         linhas_unicas=linhas_unicas,
                         codigos_produtos=codigos_produtos,
                         nomes_produtos=nomes_produtos,
                         linhas_producao=linhas_producao,
                         data_de=data_de,
                         data_ate=data_ate,
                         cod_produto=cod_produto,
                         nome_produto=nome_produto,
                         linha_producao=linha_producao_filtro)  # 🔧 PASSA O FILTRO COM NOME ORIGINAL

# 🚚 ROTAS MOVIDAS PARA /localidades/ pois são cadastros de regiões/destinos
# - /localidades/rotas (lista rotas por UF)
# - /localidades/sub-rotas (lista sub-rotas por cidade)

@producao_bp.route('/palletizacao')
@login_required
def listar_palletizacao():
    """Lista cadastro de palletização (com medidas!)"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    nome_produto = request.args.get('nome_produto', '')
    palletizacao_filtro = request.args.get('palletizacao', '')
    peso_bruto_filtro = request.args.get('peso_bruto', '')
    
    # Paginação
    try:
        page = int(request.args.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    per_page = 200  # 200 itens por página conforme solicitado
    
    try:
        # 🔧 CORREÇÃO: Definir inspector na função
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if inspector.has_table('cadastro_palletizacao'):
            # Query base
            query = CadastroPalletizacao.query.filter_by(ativo=True)
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(CadastroPalletizacao.cod_produto.ilike(f'%{cod_produto}%'))
            
            if nome_produto:
                query = query.filter(CadastroPalletizacao.nome_produto.ilike(f'%{nome_produto}%'))
                
            if palletizacao_filtro:
                try:
                    palletizacao_val = float(palletizacao_filtro)
                    query = query.filter(CadastroPalletizacao.palletizacao == palletizacao_val)
                except Exception as e:
                    pass
                    
            if peso_bruto_filtro:
                try:
                    peso_val = float(peso_bruto_filtro)
                    query = query.filter(CadastroPalletizacao.peso_bruto == peso_val)
                except Exception as e:
                    pass
            
            # Ordenação e paginação
            pagination = query.order_by(CadastroPalletizacao.cod_produto).paginate(
                page=page, per_page=per_page, error_out=False
            )
            palletizacao = pagination.items  # Template espera 'palletizacao'
            
            # 🔧 BUSCAR OPÇÕES PARA OS DROPDOWNS (todos os registros ativos)
            todos_registros = CadastroPalletizacao.query.filter_by(ativo=True).all()
            codigos_produtos = sorted(set(p.cod_produto for p in todos_registros if p.cod_produto))
            nomes_produtos = sorted(set(p.nome_produto for p in todos_registros if p.nome_produto))
            fatores_palletizacao = sorted(set(p.palletizacao for p in todos_registros if p.palletizacao))
            pesos_brutos = sorted(set(p.peso_bruto for p in todos_registros if p.peso_bruto))
        else:
            pagination = None
            palletizacao = []
            codigos_produtos = []
            nomes_produtos = []
            fatores_palletizacao = []
            pesos_brutos = []
    except Exception as e:
        print(f"Erro na rota palletização: {e}")
        pagination = None
        palletizacao = []
        codigos_produtos = []
        nomes_produtos = []
        fatores_palletizacao = []
        pesos_brutos = []
    
    return render_template('producao/listar_palletizacao.html',
                         palletizacao=palletizacao,
                         pagination=pagination,
                         cod_produto=cod_produto,
                         nome_produto=nome_produto,
                         palletizacao_filtro=palletizacao_filtro,
                         peso_bruto_filtro=peso_bruto_filtro,
                         codigos_produtos=codigos_produtos,
                         nomes_produtos=nomes_produtos,
                         fatores_palletizacao=fatores_palletizacao,
                         pesos_brutos=pesos_brutos)

@producao_bp.route('/palletizacao/importar')
@login_required
def importar_palletizacao():
    """Tela para importar cadastro de palletização"""
    return render_template('producao/importar_palletizacao.html')

@producao_bp.route('/palletizacao/importar', methods=['POST'])
@login_required
def processar_importacao_palletizacao():
    """Processar importação de cadastro de palletização"""
    try:
        import pandas as pd
        import tempfile
        import os
        
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
            # ✅ CORREÇÃO: Usar savepoint para cada item do loop
            # Isso permite rollback individual sem perder itens já processados
            try:
                db.session.begin_nested()  # Savepoint

                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_produto = str(row.get('Cód.Produto', '')).strip() if pd.notna(row.get('Cód.Produto')) else ''

                if not cod_produto or cod_produto == 'nan':
                    db.session.rollback()  # Libera savepoint vazio
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

                # 🏷️ NOVOS CAMPOS DE SUBCATEGORIAS (opcionais)
                categoria_produto = str(row.get('CATEGORIA', '')).strip() if pd.notna(row.get('CATEGORIA')) else None
                subcategoria = str(row.get('SUBCATEGORIA', '')).strip() if pd.notna(row.get('SUBCATEGORIA')) else None
                tipo_materia_prima = str(row.get('MATERIA_PRIMA', '')).strip() if pd.notna(row.get('MATERIA_PRIMA')) else None
                tipo_embalagem = str(row.get('EMBALAGEM', '')).strip() if pd.notna(row.get('EMBALAGEM')) else None
                linha_producao = str(row.get('LINHA_PRODUCAO', '')).strip() if pd.notna(row.get('LINHA_PRODUCAO')) else None

                # 🔧 NOVOS CAMPOS DE PRODUÇÃO (opcionais)
                produto_comprado = str(row.get('PRODUTO_COMPRADO', 'NAO')).strip().upper() == 'SIM' if pd.notna(row.get('PRODUTO_COMPRADO')) else False
                produto_produzido = str(row.get('PRODUTO_PRODUZIDO', 'NAO')).strip().upper() == 'SIM' if pd.notna(row.get('PRODUTO_PRODUZIDO')) else False
                produto_vendido = str(row.get('PRODUTO_VENDIDO', 'SIM')).strip().upper() == 'SIM' if pd.notna(row.get('PRODUTO_VENDIDO')) else True
                disparo_producao = str(row.get('DISPARO_PRODUCAO', '')).strip() if pd.notna(row.get('DISPARO_PRODUCAO')) else None
                lead_time_mto = int(row.get('LEAD_TIME_MTO', 0) or 0) if pd.notna(row.get('LEAD_TIME_MTO')) else None
                custo_produto = float(row.get('CUSTO_PRODUTO', 0) or 0) if pd.notna(row.get('CUSTO_PRODUTO')) else None

                if palletizacao_existente:
                    # ✏️ ATUALIZAR EXISTENTE
                    palletizacao_existente.nome_produto = nome_produto
                    palletizacao_existente.palletizacao = palletizacao
                    palletizacao_existente.peso_bruto = peso_bruto
                    palletizacao_existente.altura_cm = altura_cm
                    palletizacao_existente.largura_cm = largura_cm
                    palletizacao_existente.comprimento_cm = comprimento_cm
                    # Atualizar novos campos de subcategorias
                    palletizacao_existente.categoria_produto = categoria_produto
                    palletizacao_existente.tipo_materia_prima = tipo_materia_prima
                    palletizacao_existente.tipo_embalagem = tipo_embalagem
                    palletizacao_existente.linha_producao = linha_producao
                    # 🔧 CORRIGIDO: Atualizar campos de produção
                    palletizacao_existente.produto_comprado = produto_comprado
                    palletizacao_existente.produto_produzido = produto_produzido
                    palletizacao_existente.produto_vendido = produto_vendido
                    palletizacao_existente.disparo_producao = disparo_producao
                    palletizacao_existente.lead_time_mto = lead_time_mto
                    palletizacao_existente.custo_produto = custo_produto
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
                    # Adicionar novos campos de subcategorias
                    nova_palletizacao.categoria_produto = categoria_produto
                    nova_palletizacao.tipo_materia_prima = tipo_materia_prima
                    nova_palletizacao.tipo_embalagem = tipo_embalagem
                    nova_palletizacao.linha_producao = linha_producao
                    # 🔧 CORRIGIDO: Adicionar campos de produção
                    nova_palletizacao.produto_comprado = produto_comprado
                    nova_palletizacao.produto_produzido = produto_produzido
                    nova_palletizacao.produto_vendido = produto_vendido
                    nova_palletizacao.disparo_producao = disparo_producao
                    nova_palletizacao.lead_time_mto = lead_time_mto
                    nova_palletizacao.custo_produto = custo_produto
                    nova_palletizacao.created_by = current_user.nome
                    nova_palletizacao.ativo = True

                    db.session.add(nova_palletizacao)
                    produtos_importados += 1

                db.session.commit()  # Commit do savepoint (libera para o próximo item)

            except Exception as e:
                db.session.rollback()  # ✅ CORREÇÃO: Rollback do savepoint individual
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
                continue

        # ✅ NOTA: Commit já feito item a item via savepoints, não precisa de commit global

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
        inspector = inspect(db.engine)
        
        # Estatísticas básicas (apenas de produção)
        stats = {
            'total_ops': ProgramacaoProducao.query.count() if inspector.has_table('programacao_producao') else 0,
            'ops_atrasadas': ProgramacaoProducao.query.filter_by(status='PROGRAMADA').count() if inspector.has_table('programacao_producao') else 0,
            'produtos_palletizados': CadastroPalletizacao.query.filter_by(ativo=True).count() if inspector.has_table('cadastro_palletizacao') else 0
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        print(f"Erro na API estatísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@producao_bp.route('/programacao/importar')
@login_required
def importar_programacao():
    """Tela para importar programação de produção"""
    return render_template('producao/importar_programacao.html')

@producao_bp.route('/programacao/importar', methods=['POST'])
@login_required
def processar_importacao_programacao():
    """Processar importação de programação de produção"""
    try:
        import pandas as pd
        import tempfile
        import os
        
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
            
            # Deletar todas as programações existentes
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
            # ✅ CORREÇÃO: Usar savepoint para cada item do loop
            try:
                db.session.begin_nested()  # Savepoint

                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_produto = str(row.get('CÓDIGO', '')).strip() if pd.notna(row.get('CÓDIGO')) else ''

                if not cod_produto or cod_produto == 'nan':
                    db.session.rollback()  # Libera savepoint vazio
                    continue

                # 📅 PROCESSAR DATA
                data_programacao = row.get('DATA')
                if pd.notna(data_programacao):
                    if isinstance(data_programacao, str):
                        try:
                            # Formato brasileiro DD/MM/YYYY
                            data_programacao = pd.to_datetime(data_programacao, format='%d/%m/%Y').date()
                        except Exception:
                            try:
                                data_programacao = pd.to_datetime(data_programacao).date()
                            except Exception:
                                data_programacao = None
                    elif hasattr(data_programacao, 'date'):
                        data_programacao = data_programacao.date()
                else:
                    data_programacao = None

                if not data_programacao:
                    db.session.rollback()  # Libera savepoint
                    erros.append(f"Linha {index + 1}: Data inválida") # type: ignore
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
                novo_produto.linha_producao = str(row.get('SEÇÃO / MÁQUINA', '')).strip() if pd.notna(row.get('SEÇÃO / MÁQUINA')) else ''
                novo_produto.cliente_produto = str(row.get('CLIENTE', '')).strip() if pd.notna(row.get('CLIENTE')) else ''
                novo_produto.observacao_pcp = str(row.get('OP', '')).strip() if pd.notna(row.get('OP')) else ''

                db.session.add(novo_produto)
                produtos_importados += 1

                db.session.commit()  # Commit do savepoint

            except Exception as e:
                db.session.rollback()  # ✅ CORREÇÃO: Rollback do savepoint individual
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
                continue

        # ✅ NOTA: Commit já feito item a item via savepoints
        
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
        from datetime import datetime
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('programacao_producao'):
            programacoes = ProgramacaoProducao.query.order_by(
                ProgramacaoProducao.data_programacao.desc()
            ).limit(1000).all()  # Limitar a 1000 para performance
        else:
            programacoes = []
        
        if not programacoes:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('producao.listar_programacao'))
        
        # Converter para Excel
        dados_export = []
        for p in programacoes:
            dados_export.append({
                'DATA': p.data_programacao.strftime('%d/%m/%Y') if p.data_programacao else '',
                'SEÇÃO / MÁQUINA': p.linha_producao,
                'CÓDIGO': p.cod_produto,
                'OP': p.observacao_pcp or '',
                'DESCRIÇÃO': p.nome_produto,
                'CLIENTE': p.cliente_produto,
                'QTDE': p.qtd_programada,
                'created_at': p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else '',
                'created_by': p.created_by or ''
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Programação Produção', index=False)
            
            # Estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total Programações', 'Produtos Únicos', 'Linhas de Produção', 'Quantidade Total'],
                'Valor': [
                    len(programacoes),
                    len(set(p.cod_produto for p in programacoes)),
                    len(set(p.linha_producao for p in programacoes if p.linha_producao)),
                    sum(p.qtd_programada for p in programacoes if p.qtd_programada)
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
            'comprimento_cm': [100, 100, 100],
            'CATEGORIA': ['MOLHOS', 'ÓLEOS', 'CONSERVAS'],
            'MATERIA_PRIMA': ['KETCHUP', 'OL. MISTO', 'AZ VSC'],
            'EMBALAGEM': ['GALÃO 4X3,05', 'GARRAFA 12X500', 'BD 6X2'],
            'LINHA_PRODUCAO': ['LF', 'LF', '1105']
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
                    '6. Campos de categorização opcionais: CATEGORIA, MATERIA_PRIMA, EMBALAGEM, LINHA_PRODUCAO',
                    '7. Volume m³ será calculado automaticamente',
                    '8. Comportamento: SUBSTITUI/ADICIONA por produto'
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

@producao_bp.route('/palletizacao/nova')
@login_required
def nova_palletizacao():
    """Formulário para nova palletização"""
    return render_template('producao/nova_palletizacao.html')

@producao_bp.route('/palletizacao/nova', methods=['POST'])
@login_required
def processar_nova_palletizacao():
    """Processar nova palletização"""
    try:
        cod_produto = request.form.get('cod_produto', '').strip()
        nome_produto = request.form.get('nome_produto', '').strip()
        palletizacao = request.form.get('palletizacao', '').replace(',', '.')
        peso_bruto = request.form.get('peso_bruto', '').replace(',', '.')
        altura_cm = request.form.get('altura_cm', '').replace(',', '.') or None
        largura_cm = request.form.get('largura_cm', '').replace(',', '.') or None
        comprimento_cm = request.form.get('comprimento_cm', '').replace(',', '.') or None
        # Novos campos de categorização
        categoria_produto = request.form.get('categoria_produto', '').strip() or None
        tipo_materia_prima = request.form.get('tipo_materia_prima', '').strip() or None
        tipo_embalagem = request.form.get('tipo_embalagem', '').strip() or None
        linha_producao = request.form.get('linha_producao', '').strip() or None
        
        # Validações básicas
        if not cod_produto or not nome_produto:
            flash('❌ Código e nome do produto são obrigatórios!', 'error')
            return redirect(url_for('producao.nova_palletizacao'))
        
        if not palletizacao or not peso_bruto:
            flash('❌ Palletização e peso bruto são obrigatórios!', 'error')
            return redirect(url_for('producao.nova_palletizacao'))
        
        # Verificar se já existe
        existente = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        if existente:
            flash(f'❌ Produto {cod_produto} já possui cadastro de palletização!', 'error')
            return redirect(url_for('producao.nova_palletizacao'))
        
        try:
            palletizacao = float(palletizacao)
            peso_bruto = float(peso_bruto)
            altura_cm = float(altura_cm) if altura_cm else 0
            largura_cm = float(largura_cm) if largura_cm else 0
            comprimento_cm = float(comprimento_cm) if comprimento_cm else 0
        except ValueError:
            flash('❌ Valores numéricos inválidos!', 'error')
            return redirect(url_for('producao.nova_palletizacao'))
        
        # Criar novo registro
        nova_palletizacao = CadastroPalletizacao()
        nova_palletizacao.cod_produto = cod_produto
        nova_palletizacao.nome_produto = nome_produto
        nova_palletizacao.palletizacao = palletizacao
        nova_palletizacao.peso_bruto = peso_bruto
        nova_palletizacao.altura_cm = altura_cm
        nova_palletizacao.largura_cm = largura_cm
        nova_palletizacao.comprimento_cm = comprimento_cm
        # Novos campos de categorização
        nova_palletizacao.categoria_produto = categoria_produto
        nova_palletizacao.tipo_materia_prima = tipo_materia_prima
        nova_palletizacao.tipo_embalagem = tipo_embalagem
        nova_palletizacao.linha_producao = linha_producao
        nova_palletizacao.created_by = current_user.nome
        nova_palletizacao.ativo = True
        
        db.session.add(nova_palletizacao)
        db.session.commit()
        
        flash(f'✅ Palletização do produto {cod_produto} criada com sucesso!', 'success')
        return redirect(url_for('producao.listar_palletizacao'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao criar palletização: {str(e)}', 'error')
        return redirect(url_for('producao.nova_palletizacao'))

@producao_bp.route('/palletizacao/editar/<int:id>')
@login_required
def editar_palletizacao(id):
    """Formulário para editar palletização"""
    palletizacao = CadastroPalletizacao.query.get_or_404(id)
    return render_template('producao/editar_palletizacao.html', palletizacao=palletizacao)

@producao_bp.route('/palletizacao/editar/<int:id>', methods=['POST'])
@login_required
def processar_edicao_palletizacao(id):
    """Processar edição de palletização"""
    try:
        palletizacao = CadastroPalletizacao.query.get_or_404(id)
        
        nome_produto = request.form.get('nome_produto', '').strip()
        palletizacao_valor = request.form.get('palletizacao', '').replace(',', '.')
        peso_bruto = request.form.get('peso_bruto', '').replace(',', '.')
        altura_cm = request.form.get('altura_cm', '').replace(',', '.') or None
        largura_cm = request.form.get('largura_cm', '').replace(',', '.') or None
        comprimento_cm = request.form.get('comprimento_cm', '').replace(',', '.') or None
        
        # Validações básicas
        if not nome_produto:
            flash('❌ Nome do produto é obrigatório!', 'error')
            return redirect(url_for('producao.editar_palletizacao', id=id))
        
        if not palletizacao_valor or not peso_bruto:
            flash('❌ Palletização e peso bruto são obrigatórios!', 'error')
            return redirect(url_for('producao.editar_palletizacao', id=id))
        
        try:
            palletizacao_valor = float(palletizacao_valor)
            peso_bruto = float(peso_bruto)
            altura_cm = float(altura_cm) if altura_cm else 0
            largura_cm = float(largura_cm) if largura_cm else 0
            comprimento_cm = float(comprimento_cm) if comprimento_cm else 0
        except ValueError:
            flash('❌ Valores numéricos inválidos!', 'error')
            return redirect(url_for('producao.editar_palletizacao', id=id))
        
        # Atualizar registro
        palletizacao.nome_produto = nome_produto
        palletizacao.palletizacao = palletizacao_valor
        palletizacao.peso_bruto = peso_bruto
        palletizacao.altura_cm = altura_cm
        palletizacao.largura_cm = largura_cm
        palletizacao.comprimento_cm = comprimento_cm
        palletizacao.updated_by = current_user.nome
        
        db.session.commit()
        
        flash(f'✅ Palletização do produto {palletizacao.cod_produto} atualizada com sucesso!', 'success')
        return redirect(url_for('producao.listar_palletizacao'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao atualizar palletização: {str(e)}', 'error')
        return redirect(url_for('producao.editar_palletizacao', id=id))

@producao_bp.route('/palletizacao/excluir/<int:id>', methods=['GET', 'DELETE'])
@login_required
def excluir_palletizacao(id):
    """Excluir palletização (soft delete)"""
    try:
        palletizacao = CadastroPalletizacao.query.get_or_404(id)
        cod_produto = palletizacao.cod_produto

        # Soft delete - marcar como inativo
        palletizacao.ativo = False
        palletizacao.updated_by = current_user.nome

        db.session.commit()

        # Se for requisição AJAX (DELETE), retornar JSON
        if request.method == 'DELETE' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'sucesso': True,
                'mensagem': f'Produto {cod_produto} excluído com sucesso!'
            })

        # Caso contrário, redirecionar (compatibilidade com GET)
        flash(f'✅ Palletização do produto {cod_produto} excluída com sucesso!', 'success')
        return redirect(url_for('producao.listar_palletizacao'))

    except Exception as e:
        db.session.rollback()

        # Se for requisição AJAX, retornar JSON
        if request.method == 'DELETE' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'sucesso': False,
                'erro': f'Erro ao excluir: {str(e)}'
            }), 500

        flash(f'❌ Erro ao excluir palletização: {str(e)}', 'error')
        return redirect(url_for('producao.listar_palletizacao'))

@producao_bp.route('/palletizacao/api/produto/<cod_produto>')
@login_required
def api_produto_palletizacao(cod_produto):
    """API para buscar produto no cadastro de palletização"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if not inspector.has_table('cadastro_palletizacao'):
            return jsonify({'success': False, 'error': 'Tabela não encontrada'})
        
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        
        if produto:
            return jsonify({
                'success': True,
                'produto': {
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'palletizacao': produto.palletizacao,
                    'peso_bruto': produto.peso_bruto,
                    'altura_cm': produto.altura_cm,
                    'largura_cm': produto.largura_cm,
                    'comprimento_cm': produto.comprimento_cm,
                    'volume_m3': produto.volume_m3 if hasattr(produto, 'volume_m3') else 0
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Produto não encontrado'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@producao_bp.route('/palletizacao/api/criar', methods=['POST'])
@login_required
def api_criar_produto_palletizacao():
    """API para criar produto no cadastro de palletização"""
    try:
        from flask import request
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'})
        
        cod_produto = data.get('cod_produto')
        nome_produto = data.get('nome_produto')
        
        if not cod_produto or not nome_produto:
            return jsonify({'success': False, 'error': 'Código e nome do produto são obrigatórios'})
        
        # Verificar se já existe
        existe = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        if existe:
            return jsonify({'success': False, 'error': 'Produto já existe no cadastro'})
        
        # Criar novo produto
        novo_produto = CadastroPalletizacao()
        novo_produto.cod_produto = cod_produto
        novo_produto.nome_produto = nome_produto
        novo_produto.palletizacao = float(data.get('palletizacao', 1))
        novo_produto.peso_bruto = float(data.get('peso_bruto', 0))
        novo_produto.altura_cm = float(data.get('altura_cm', 0)) if data.get('altura_cm') else None
        novo_produto.largura_cm = float(data.get('largura_cm', 0)) if data.get('largura_cm') else None
        novo_produto.comprimento_cm = float(data.get('comprimento_cm', 0)) if data.get('comprimento_cm') else None
        novo_produto.created_by = current_user.nome
        
        db.session.add(novo_produto)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Produto {cod_produto} criado com sucesso',
            'produto': {
                'cod_produto': novo_produto.cod_produto,
                'nome_produto': novo_produto.nome_produto
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@producao_bp.route('/palletizacao/api/editar/<int:id>', methods=['PUT'])
@login_required
def editar_palletizacao_api(id):
    """API para editar produto via modal"""
    try:
        # Buscar produto
        produto = db.session.get(CadastroPalletizacao,id) if id else None

        if not produto:
            return jsonify({'sucesso': False, 'erro': 'Produto não encontrado'}), 404

        # Obter dados do JSON
        dados = request.get_json()

        # Validações
        if not dados.get('nome_produto'):
            return jsonify({'sucesso': False, 'erro': 'Nome do produto é obrigatório'}), 400

        if not dados.get('palletizacao') or dados['palletizacao'] <= 0:
            return jsonify({'sucesso': False, 'erro': 'Palletização deve ser maior que zero'}), 400

        if not dados.get('peso_bruto') or dados['peso_bruto'] <= 0:
            return jsonify({'sucesso': False, 'erro': 'Peso bruto deve ser maior que zero'}), 400

        # Atualizar campos
        produto.nome_produto = dados['nome_produto']
        produto.palletizacao = dados['palletizacao']
        produto.peso_bruto = dados['peso_bruto']
        produto.altura_cm = dados.get('altura_cm')
        produto.largura_cm = dados.get('largura_cm')
        produto.comprimento_cm = dados.get('comprimento_cm')
        produto.categoria_produto = dados.get('categoria_produto')
        produto.subcategoria = dados.get('subcategoria')
        produto.tipo_materia_prima = dados.get('tipo_materia_prima')
        produto.tipo_embalagem = dados.get('tipo_embalagem')
        produto.linha_producao = dados.get('linha_producao')
        produto.produto_comprado = dados.get('produto_comprado', False)
        produto.produto_produzido = dados.get('produto_produzido', False)
        produto.produto_vendido = dados.get('produto_vendido', False)
        produto.disparo_producao = dados.get('disparo_producao')
        produto.lead_time_mto = dados.get('lead_time_mto')
        produto.custo_produto = dados.get('custo_produto')
        produto.updated_by = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Produto {produto.cod_produto} atualizado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@producao_bp.route('/palletizacao/exportar-dados')
@login_required
def exportar_dados_palletizacao():
    """Exportar dados existentes de palletização"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        from datetime import datetime
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
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
                'CATEGORIA': p.categoria_produto or '',
                'SUBCATEGORIA': p.subcategoria or '',
                'MATERIA_PRIMA': p.tipo_materia_prima or '',
                'EMBALAGEM': p.tipo_embalagem or '',
                'LINHA_PRODUCAO': p.linha_producao or '',
                'PALLETIZACAO': p.palletizacao,
                'PESO BRUTO': p.peso_bruto,
                'altura_cm': p.altura_cm or '',
                'largura_cm': p.largura_cm or '',
                'comprimento_cm': p.comprimento_cm or '',
                'volume_m3': p.volume_m3 if hasattr(p, 'volume_m3') else 0,
                'PRODUTO_COMPRADO': 'SIM' if p.produto_comprado else 'NAO',
                'PRODUTO_PRODUZIDO': 'SIM' if p.produto_produzido else 'NAO',
                'PRODUTO_VENDIDO': 'SIM' if p.produto_vendido else 'NAO',
                'DISPARO_PRODUCAO': p.disparo_producao or '',
                'LEAD_TIME_MTO': p.lead_time_mto or '',
                'CUSTO_PRODUTO': p.custo_produto or ''
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Palletização', index=False)
            
            # 🔧 ADICIONADO: Aba de estatísticas como nas outras funções
            stats = pd.DataFrame({
                'Estatística': ['Total Produtos', 'Média Palletização', 'Média Peso Bruto', 'Volume Total m³'],
                'Valor': [
                    len(palletizacao),
                    sum(p.palletizacao for p in palletizacao) / len(palletizacao) if palletizacao else 0,
                    sum(p.peso_bruto for p in palletizacao) / len(palletizacao) if palletizacao else 0,
                    sum(p.volume_m3 for p in palletizacao if hasattr(p, 'volume_m3') and p.volume_m3)
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=palletizacao_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('producao.listar_palletizacao')) 