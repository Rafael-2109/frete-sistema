from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.utils.auth_decorators import require_admin

# 📦 Blueprint do estoque (seguindo padrão dos outros módulos)
estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

@estoque_bp.route('/')
@login_required
def index():
    """Dashboard do módulo estoque"""
    try:
        from sqlalchemy import func, extract
        from datetime import datetime
        
        # ✅ SEGURO: Verifica se tabela existe antes de fazer query
        if db.engine.has_table('movimentacao_estoque'):
            total_movimentacoes = MovimentacaoEstoque.query.count()
            
            # Movimentações do mês atual
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            
            entradas_mes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.ilike('%entrada%'),
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).count()
            
            saidas_mes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.ilike('%saida%'),
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).count()
            
            # Produtos únicos movimentados
            produtos_movimentados = MovimentacaoEstoque.query.with_entities(
                MovimentacaoEstoque.cod_produto
            ).distinct().count()
            
            # Locais únicos de movimentação
            locais_movimentacao = MovimentacaoEstoque.query.with_entities(
                MovimentacaoEstoque.local_movimentacao
            ).filter(MovimentacaoEstoque.local_movimentacao.isnot(None)).distinct().count()
            
            # Quantidade total movimentada
            qtd_total_movimentada = db.session.query(
                func.sum(MovimentacaoEstoque.qtd_movimentacao)
            ).scalar() or 0
            
            # Movimentações recentes (últimos 10 registros)
            movimentacoes_recentes = MovimentacaoEstoque.query.order_by(
                MovimentacaoEstoque.data_movimentacao.desc()
            ).limit(10).all()
            
            # Tipos de movimentação do último mês
            tipos_movimentacao = db.session.query(
                MovimentacaoEstoque.tipo_movimentacao,
                func.count(MovimentacaoEstoque.id).label('quantidade')
            ).filter(
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).group_by(MovimentacaoEstoque.tipo_movimentacao).all()
        else:
            total_movimentacoes = entradas_mes = saidas_mes = produtos_movimentados = 0
            locais_movimentacao = qtd_total_movimentada = 0
            movimentacoes_recentes = tipos_movimentacao = []
            
    except Exception as e:
        # ✅ FALLBACK: Se der erro, zera tudo
        total_movimentacoes = entradas_mes = saidas_mes = produtos_movimentados = 0
        locais_movimentacao = qtd_total_movimentada = 0
        movimentacoes_recentes = tipos_movimentacao = []
    
    return render_template('estoque/dashboard.html',
                         total_movimentacoes=total_movimentacoes,
                         entradas_mes=entradas_mes,
                         saidas_mes=saidas_mes,
                         produtos_movimentados=produtos_movimentados,
                         locais_movimentacao=locais_movimentacao,
                         qtd_total_movimentada=qtd_total_movimentada,
                         movimentacoes_recentes=movimentacoes_recentes,
                         tipos_movimentacao=tipos_movimentacao)

@estoque_bp.route('/movimentacoes')
@login_required
def listar_movimentacoes():
    """Lista movimentações de estoque"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    tipo_movimentacao = request.args.get('tipo_movimentacao', '')
    
    try:
        if db.engine.has_table('movimentacao_estoque'):
            # Query base
            query = MovimentacaoEstoque.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
            if tipo_movimentacao:
                query = query.filter(MovimentacaoEstoque.tipo_movimentacao == tipo_movimentacao)
            
            # Ordenação (limitado a 100 registros mais recentes)
            movimentacoes = query.order_by(MovimentacaoEstoque.data_movimentacao.desc()).limit(100).all()
        else:
            movimentacoes = []
    except Exception:
        movimentacoes = []
    
    return render_template('estoque/listar_movimentacoes.html',
                         movimentacoes=movimentacoes,
                         cod_produto=cod_produto,
                         tipo_movimentacao=tipo_movimentacao)

@estoque_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo estoque"""
    try:
        from sqlalchemy import func
        
        # Estatísticas básicas
        stats = {
            'total_movimentacoes': MovimentacaoEstoque.query.count(),
            'movimentacoes_mes': MovimentacaoEstoque.query.filter(
                func.extract('month', MovimentacaoEstoque.data_movimentacao) == func.extract('month', func.now())
            ).count()
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@estoque_bp.route('/movimentacoes/importar')
@login_required
@require_admin()
def importar_movimentacoes():
    """Tela para importar movimentações de estoque"""
    return render_template('estoque/importar_movimentacoes.html')

@estoque_bp.route('/movimentacoes/importar', methods=['POST'])
@login_required
@require_admin()
def processar_importacao_movimentacoes():
    """Processar importação de movimentações de estoque"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('estoque.importar_movimentacoes'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('estoque.importar_movimentacoes'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('estoque.importar_movimentacoes'))
        
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
            return redirect(url_for('estoque.importar_movimentacoes'))
        
        # 🎯 MAPEAMENTO EXATO conforme arquivo 6 - movimentações de estoque
        colunas_esperadas = {
            'tipo_movimentacao': 'tipo_movimentacao',
            'cod_produto': 'cod_produto',
            'nome_produto': 'nome_produto',
            'local_movimentacao': 'local_movimentacao',
            'data_movimentacao': 'data_movimentacao',
            'qtd_movimentacao': 'qtd_movimentacao'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = ['tipo_movimentacao', 'cod_produto', 'nome_produto', 'data_movimentacao', 'qtd_movimentacao']
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('estoque.importar_movimentacoes'))
        
        # ✅ VALIDAR TIPOS DE MOVIMENTAÇÃO PERMITIDOS
        tipos_permitidos = ['AVARIA', 'EST INICIAL', 'DEVOLUÇÃO', 'PRODUÇÃO', 'RETRABALHO']
        if 'tipo_movimentacao' in df.columns:
            tipos_invalidos = df[df['tipo_movimentacao'].notna() & ~df['tipo_movimentacao'].isin(tipos_permitidos)]['tipo_movimentacao'].unique()
            if len(tipos_invalidos) > 0:
                flash(f'❌ Tipos de movimentação inválidos: {", ".join(tipos_invalidos)}. Permitidos: {", ".join(tipos_permitidos)}', 'error')
                return redirect(url_for('estoque.importar_movimentacoes'))
        
        # COMPORTAMENTO: SEMPRE ADICIONA - Não remove dados existentes
        produtos_importados = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                cod_produto = str(row.get('cod_produto', '')).strip() if pd.notna(row.get('cod_produto')) else ''
                tipo_movimentacao = str(row.get('tipo_movimentacao', '')).strip() if pd.notna(row.get('tipo_movimentacao')) else ''
                
                if not cod_produto or cod_produto == 'nan' or not tipo_movimentacao or tipo_movimentacao == 'nan':
                    continue
                
                # 📅 PROCESSAR DATA
                data_movimentacao = row.get('data_movimentacao')
                if pd.notna(data_movimentacao):
                    if isinstance(data_movimentacao, str):
                        try:
                            # Formato brasileiro DD/MM/YYYY
                            data_movimentacao = pd.to_datetime(data_movimentacao, format='%d/%m/%Y').date()
                        except:
                            try:
                                data_movimentacao = pd.to_datetime(data_movimentacao).date()
                            except:
                                data_movimentacao = None
                    elif hasattr(data_movimentacao, 'date'):
                        data_movimentacao = data_movimentacao.date()
                else:
                    data_movimentacao = None
                
                if not data_movimentacao:
                    erros.append(f"Linha {index + 1}: Data inválida")
                    continue
                
                # 📝 DADOS BÁSICOS
                nome_produto = str(row.get('nome_produto', '')).strip()
                qtd_movimentacao = float(row.get('qtd_movimentacao', 0) or 0)
                local_movimentacao = str(row.get('local_movimentacao', '')).strip()
                
                # ➕ CRIAR NOVO REGISTRO (sempre adiciona)
                nova_movimentacao = MovimentacaoEstoque()
                nova_movimentacao.tipo_movimentacao = tipo_movimentacao
                nova_movimentacao.cod_produto = cod_produto
                nova_movimentacao.nome_produto = nome_produto
                nova_movimentacao.local_movimentacao = local_movimentacao
                nova_movimentacao.data_movimentacao = data_movimentacao
                nova_movimentacao.qtd_movimentacao = qtd_movimentacao
                nova_movimentacao.created_by = current_user.nome
                
                # 📝 CAMPOS OPCIONAIS
                if 'observacao' in df.columns:
                    nova_movimentacao.observacao = str(row.get('observacao', '')).strip()
                if 'documento_origem' in df.columns:
                    nova_movimentacao.documento_origem = str(row.get('documento_origem', '')).strip()
                
                db.session.add(nova_movimentacao)
                produtos_importados += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        # Mensagens de resultado
        if produtos_importados > 0:
            mensagem = f"✅ Importação concluída: {produtos_importados} movimentações adicionadas"
            if erros:
                mensagem += f". {len(erros)} erros encontrados."
            flash(mensagem, 'success')
        else:
            flash("⚠️ Nenhuma movimentação foi importada.", 'warning')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('estoque.listar_movimentacoes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('estoque.importar_movimentacoes'))

# TODO: Implementar outras rotas conforme necessário
# - /movimentar (nova movimentação manual)
# - /relatorios (relatórios específicos) 