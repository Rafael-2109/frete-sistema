from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.utils.auth_decorators import require_admin

# 📦 Blueprint da produção (seguindo padrão dos outros módulos)
producao_bp = Blueprint('producao', __name__, url_prefix='/producao')

@producao_bp.route('/')
@login_required
def index():
    """Dashboard do módulo produção"""
    try:
        from sqlalchemy import func
        
        # ✅ SEGURO: Verifica se tabelas existem antes de fazer query
        if db.engine.has_table('programacao_producao'):
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
        if db.engine.has_table('cadastro_palletizacao'):
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
        if db.engine.has_table('programacao_producao'):
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
        if db.engine.has_table('cadastro_palletizacao'):
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

@producao_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo produção"""
    try:
        from sqlalchemy import func
        
        # Estatísticas básicas (apenas de produção)
        stats = {
            'total_ops': ProgramacaoProducao.query.count() if db.engine.has_table('programacao_producao') else 0,
            'ops_atrasadas': ProgramacaoProducao.query.filter_by(status='PROGRAMADA').count() if db.engine.has_table('programacao_producao') else 0,
            'produtos_palletizados': CadastroPalletizacao.query.filter_by(ativo=True).count() if db.engine.has_table('cadastro_palletizacao') else 0
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@producao_bp.route('/importar')
@login_required
@require_admin()
def importar_producao():
    """Tela para importar dados de produção"""
    return render_template('producao/importar_programacao.html')

@producao_bp.route('/importar', methods=['POST'])
@login_required
@require_admin()
def processar_importacao_producao():
    """Processar importação de programação de produção"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_producao'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('producao.importar_producao'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('producao.importar_producao'))
        
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
            return redirect(url_for('producao.importar_producao'))
        
        # Validar colunas obrigatórias
        colunas_obrigatorias = ['data_programacao', 'cod_produto', 'nome_produto', 'qtd_programada']
        
        # Mapear nomes de colunas flexíveis
        mapeamento_colunas = {
            'data_programacao': ['data_programacao', 'data', 'data_producao'],
            'cod_produto': ['cod_produto', 'codigo', 'codigo_produto'],
            'nome_produto': ['nome_produto', 'produto', 'descricao'],
            'qtd_programada': ['qtd_programada', 'quantidade', 'qtd']
        }
        
        # Normalizar nomes das colunas
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
        
        # Mapear colunas
        colunas_encontradas = {}
        for campo, possibilidades in mapeamento_colunas.items():
            for possibilidade in possibilidades:
                if possibilidade in df.columns:
                    colunas_encontradas[campo] = possibilidade
                    break
        
        # Verificar se todas as colunas obrigatórias foram encontradas
        faltando = [col for col in colunas_obrigatorias if col not in colunas_encontradas]
        if faltando:
            flash(f'Colunas obrigatórias não encontradas: {", ".join(faltando)}', 'error')
            return redirect(url_for('producao.importar_producao'))
        
        # COMPORTAMENTO: SEMPRE SUBSTITUI - Deletar todos os dados existentes
        try:
            ProgramacaoProducao.query.delete()
            db.session.commit()
            flash('✅ Dados existentes removidos (substituição completa)', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao remover dados existentes: {str(e)}', 'warning')
        
        # Processar dados
        produtos_importados = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # Extrair dados usando mapeamento
                cod_produto = str(row[colunas_encontradas['cod_produto']]).strip()
                
                if not cod_produto or cod_produto == 'nan':
                    continue
                
                # Preparar dados
                data_programacao = row[colunas_encontradas['data_programacao']]
                if isinstance(data_programacao, str):
                    try:
                        data_programacao = pd.to_datetime(data_programacao).date()
                    except:
                        data_programacao = None
                elif hasattr(data_programacao, 'date'):
                    data_programacao = data_programacao.date()
                
                if not data_programacao:
                    erros.append(f"Linha {index + 1}: Data inválida")
                    continue
                
                # Criar novo registro
                novo_produto = ProgramacaoProducao(
                    data_programacao=data_programacao,
                    cod_produto=cod_produto,
                    nome_produto=str(row[colunas_encontradas['nome_produto']]).strip(),
                    qtd_programada=float(row[colunas_encontradas['qtd_programada']] or 0),
                    created_by=current_user.nome
                )
                
                # Campos opcionais
                if 'linha_producao' in df.columns:
                    novo_produto.linha_producao = str(row.get('linha_producao', '')).strip()
                if 'cliente_produto' in df.columns:
                    novo_produto.cliente_produto = str(row.get('cliente_produto', '')).strip()
                if 'observacao_pcp' in df.columns:
                    novo_produto.observacao_pcp = str(row.get('observacao_pcp', '')).strip()
                
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
        return redirect(url_for('producao.importar_producao'))

# TODO: Implementar outras rotas conforme necessário
# - POST /importar (upload e processamento de arquivos)
# - /criar_op (nova ordem de produção)
# - /editar_rota/<id> (edição de rotas)
# - /relatorios (relatórios específicos) 