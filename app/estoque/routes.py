import io
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos, SaldoEstoque
from app.utils.auth_decorators import require_admin
from app.utils.timezone import agora_brasil
from app.utils.valores_brasileiros import formatar_valor_brasileiro
from app.utils.timezone import formatar_data_brasil
import logging

logger = logging.getLogger(__name__)

# 📦 Blueprint do estoque (seguindo padrão dos outros módulos)
estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

@estoque_bp.route('/')
@login_required
def index():
    """Dashboard do módulo estoque"""
    try:
        from sqlalchemy import inspect, extract, func
        from datetime import datetime
        inspector = inspect(db.engine)
        
        # ✅ SEGURO: Verifica se tabela existe antes de fazer query
        if inspector.has_table('movimentacao_estoque'):
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
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if inspector.has_table('movimentacao_estoque'):
            # Query base
            query = MovimentacaoEstoque.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
            if tipo_movimentacao:
                query = query.filter(MovimentacaoEstoque.tipo_movimentacao == tipo_movimentacao)
            
            # Ordenação (limitado a 100 registros mais recentes)
            movimentacoes = query.order_by(MovimentacaoEstoque.data_movimentacao.desc()).limit(100).all()
            
            # 🔧 CARREGAR TIPOS DE MOVIMENTAÇÃO DOS DADOS REAIS
            tipos_movimentacao_disponiveis = sorted(set(
                m.tipo_movimentacao for m in MovimentacaoEstoque.query.all() 
                if m.tipo_movimentacao
            ))
        else:
            movimentacoes = []
            tipos_movimentacao_disponiveis = []
    except Exception:
        movimentacoes = []
        tipos_movimentacao_disponiveis = []
    
    return render_template('estoque/listar_movimentacoes.html',
                         movimentacoes=movimentacoes,
                         cod_produto=cod_produto,
                         tipo_movimentacao=tipo_movimentacao,
                         tipos_movimentacao_disponiveis=tipos_movimentacao_disponiveis)

@estoque_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo estoque"""
    try:
        from sqlalchemy import inspect, func
        inspector = inspect(db.engine)
        
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
                
                # 🔗 VERIFICAR/CRIAR PRODUTO NO CADASTRO DE PALLETIZAÇÃO
                from app.producao.models import CadastroPalletizacao
                produto_palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                
                if not produto_palletizacao:
                    # Auto-criar produto no cadastro se não existir (conforme solicitação)
                    produto_palletizacao = CadastroPalletizacao()
                    produto_palletizacao.cod_produto = cod_produto
                    produto_palletizacao.nome_produto = nome_produto
                    produto_palletizacao.palletizacao = 0  # Zerado conforme solicitação
                    produto_palletizacao.peso_bruto = 0
                    produto_palletizacao.created_by = current_user.nome
                    
                    db.session.add(produto_palletizacao)
                
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

# ========================================
# 🆕 CRUD MANUAL DE MOVIMENTAÇÕES
# ========================================

@estoque_bp.route('/movimentacoes/nova')
@login_required
@require_admin()
def nova_movimentacao():
    """Formulário para nova movimentação manual"""
    from datetime import date
    return render_template('estoque/nova_movimentacao.html', 
                         data_hoje=date.today().strftime('%Y-%m-%d'))

@estoque_bp.route('/movimentacoes/nova', methods=['POST'])
@login_required
@require_admin()
def processar_nova_movimentacao():
    """Processar nova movimentação manual"""
    try:
        # Extrair dados do formulário
        cod_produto = request.form.get('cod_produto', '').strip()
        nome_produto = request.form.get('nome_produto', '').strip()
        tipo_movimentacao = request.form.get('tipo_movimentacao', '').strip()
        data_movimentacao = request.form.get('data_movimentacao')
        qtd_movimentacao = request.form.get('qtd_movimentacao')
        local_movimentacao = request.form.get('local_movimentacao', '').strip()
        documento_origem = request.form.get('documento_origem', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        # Validações básicas
        if not all([cod_produto, nome_produto, tipo_movimentacao, data_movimentacao, qtd_movimentacao, local_movimentacao]):
            flash('❌ Todos os campos obrigatórios devem ser preenchidos!', 'error')
            return redirect(url_for('estoque.nova_movimentacao'))
        
        # Converter dados
        try:
            if qtd_movimentacao is None:
                raise ValueError("Quantidade é obrigatória")
            qtd_movimentacao = float(qtd_movimentacao)
            
            if data_movimentacao is None:
                raise ValueError("Data é obrigatória")
            data_movimentacao = datetime.strptime(data_movimentacao, '%Y-%m-%d').date()
        except ValueError as e:
            flash(f'❌ Erro nos dados: {str(e)}', 'error')
            return redirect(url_for('estoque.nova_movimentacao'))
        
        if qtd_movimentacao == 0:
            flash('❌ Quantidade não pode ser zero!', 'error')
            return redirect(url_for('estoque.nova_movimentacao'))
        
        # Verificar se o produto existe no cadastro de palletização
        from app.producao.models import CadastroPalletizacao
        produto_palletizacao = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        
        if not produto_palletizacao:
            # Auto-criar produto no cadastro se não existir (conforme solicitação)
            produto_palletizacao = CadastroPalletizacao()
            produto_palletizacao.cod_produto = cod_produto
            produto_palletizacao.nome_produto = nome_produto
            produto_palletizacao.palletizacao = 0  # Zerado conforme solicitação
            produto_palletizacao.peso_bruto = 0
            produto_palletizacao.created_by = current_user.nome
            
            db.session.add(produto_palletizacao)
            flash(f'ℹ️ Produto {cod_produto} criado automaticamente no cadastro de palletização', 'info')
        
        # Criar nova movimentação
        nova_movimentacao = MovimentacaoEstoque()
        nova_movimentacao.tipo_movimentacao = tipo_movimentacao
        nova_movimentacao.cod_produto = cod_produto
        nova_movimentacao.nome_produto = nome_produto
        nova_movimentacao.local_movimentacao = local_movimentacao
        nova_movimentacao.data_movimentacao = data_movimentacao
        nova_movimentacao.qtd_movimentacao = qtd_movimentacao
        nova_movimentacao.documento_origem = documento_origem if documento_origem else None
        nova_movimentacao.observacao = observacao if observacao else None
        nova_movimentacao.created_by = current_user.nome
        
        db.session.add(nova_movimentacao)
        db.session.commit()
        
        # Mensagem de sucesso
        tipo_operacao = "ENTRADA" if qtd_movimentacao > 0 else "SAÍDA"
        flash(f'✅ Movimentação criada com sucesso: {tipo_operacao} de {abs(qtd_movimentacao)} unidades do produto {cod_produto}', 'success')
        
        return redirect(url_for('estoque.listar_movimentacoes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao criar movimentação: {str(e)}', 'error')
        return redirect(url_for('estoque.nova_movimentacao'))

@estoque_bp.route('/movimentacoes/<int:id>')
@login_required
def visualizar_movimentacao(id):
    """Visualizar detalhes de uma movimentação"""
    movimentacao = MovimentacaoEstoque.query.get_or_404(id)
    return render_template('estoque/visualizar_movimentacao.html', movimentacao=movimentacao)

@estoque_bp.route('/movimentacoes/editar/<int:id>')
@login_required
@require_admin()
def editar_movimentacao(id):
    """Formulário para editar movimentação existente"""
    movimentacao = MovimentacaoEstoque.query.get_or_404(id)
    return render_template('estoque/editar_movimentacao.html', movimentacao=movimentacao)

@estoque_bp.route('/movimentacoes/editar/<int:id>', methods=['POST'])
@login_required
@require_admin()
def processar_edicao_movimentacao(id):
    """Processar edição de movimentação existente"""
    try:
        movimentacao = MovimentacaoEstoque.query.get_or_404(id)
        
        # Extrair dados do formulário
        nome_produto = request.form.get('nome_produto', '').strip()
        tipo_movimentacao = request.form.get('tipo_movimentacao', '').strip()
        data_movimentacao = request.form.get('data_movimentacao')
        qtd_movimentacao = request.form.get('qtd_movimentacao')
        local_movimentacao = request.form.get('local_movimentacao', '').strip()
        documento_origem = request.form.get('documento_origem', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        # Validações básicas
        if not all([nome_produto, tipo_movimentacao, data_movimentacao, qtd_movimentacao, local_movimentacao]):
            flash('❌ Todos os campos obrigatórios devem ser preenchidos!', 'error')
            return redirect(url_for('estoque.editar_movimentacao', id=id))
        
        # Converter dados
        try:
            if qtd_movimentacao is None:
                raise ValueError("Quantidade é obrigatória")
            qtd_movimentacao = float(qtd_movimentacao)
            
            if data_movimentacao is None:
                raise ValueError("Data é obrigatória")
            data_movimentacao = datetime.strptime(data_movimentacao, '%Y-%m-%d').date()
        except ValueError as e:
            flash(f'❌ Erro nos dados: {str(e)}', 'error')
            return redirect(url_for('estoque.editar_movimentacao', id=id))
        
        if qtd_movimentacao == 0:
            flash('❌ Quantidade não pode ser zero!', 'error')
            return redirect(url_for('estoque.editar_movimentacao', id=id))
        
        # Atualizar movimentação
        movimentacao.nome_produto = nome_produto
        movimentacao.tipo_movimentacao = tipo_movimentacao
        movimentacao.data_movimentacao = data_movimentacao
        movimentacao.qtd_movimentacao = qtd_movimentacao
        movimentacao.local_movimentacao = local_movimentacao
        movimentacao.documento_origem = documento_origem if documento_origem else None
        movimentacao.observacao = observacao if observacao else None
        movimentacao.updated_by = current_user.nome
        
        db.session.commit()
        
        # Mensagem de sucesso
        flash(f'✅ Movimentação {id} atualizada com sucesso!', 'success')
        
        return redirect(url_for('estoque.listar_movimentacoes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao atualizar movimentação: {str(e)}', 'error')
        return redirect(url_for('estoque.editar_movimentacao', id=id))

@estoque_bp.route('/movimentacoes/excluir/<int:id>')
@login_required
@require_admin()
def excluir_movimentacao(id):
    """Excluir movimentação de estoque"""
    try:
        movimentacao = MovimentacaoEstoque.query.get_or_404(id)
        
        # Guardar informações para a mensagem
        tipo_mov = movimentacao.tipo_movimentacao
        cod_produto = movimentacao.cod_produto
        qtd = movimentacao.qtd_movimentacao
        
        # Excluir do banco
        db.session.delete(movimentacao)
        db.session.commit()
        
        flash(f'✅ Movimentação excluída com sucesso: {tipo_mov} de {qtd} unidades do produto {cod_produto}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao excluir movimentação: {str(e)}', 'error')
    
    return redirect(url_for('estoque.listar_movimentacoes'))

@estoque_bp.route('/movimentacoes/baixar-modelo')
@login_required
def baixar_modelo_movimentacoes():
    """Baixar modelo Excel para importação de movimentações de estoque"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        # Colunas exatas conforme arquivo CSV
        dados_exemplo = {
            'tipo_movimentacao': ['EST INICIAL', 'AVARIA', 'DEVOLUÇÃO', 'PRODUÇÃO', 'RETRABALHO'],
            'cod_produto': [4089056, 4320162, 4729098, 4080177, 4210155],
            'nome_produto': [
                'PEPINO FATIADO BAG 6X1,01 KG - SUBWAY',
                'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO',
                'OL. MIS AZEITE DE OLIVA VD 12X500 ML - ST ISABEL',
                'PEPINOS EM RODELAS AGRIDOCE VD 12X440G - CAMPO BELO',
                'AZEITONA PRETA INTEIRA POUCH 12x400 GR - CAMPO BELO'
            ],
            'local_movimentacao': ['EST INICIAL', 'EXPEDIÇÃO', 'RECEBIMENTO', 'PRODUÇÃO', 'DEVOLUÇÕES'],
            'data_movimentacao': ['20/01/2025', '21/01/2025', '22/01/2025', '23/01/2025', '24/01/2025'],
            'qtd_movimentacao': [1489, -50, 200, 300, -25]
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
                    '2. Campos obrigatórios: tipo_movimentacao, cod_produto, nome_produto, data_movimentacao, qtd_movimentacao',
                    '3. Tipos permitidos: EST INICIAL, AVARIA, DEVOLUÇÃO, PRODUÇÃO, RETRABALHO',
                    '4. Data no formato DD/MM/YYYY',
                    '5. Quantidade pode ser negativa (saídas)',
                    '6. local_movimentacao é opcional',
                    '7. Comportamento: SEMPRE ADICIONA (histórico)',
                    '8. Nunca remove dados existentes'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_movimentacoes_estoque.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('estoque.listar_movimentacoes'))

@estoque_bp.route('/movimentacoes/exportar-dados')
@login_required
def exportar_dados_movimentacoes():
    """Exportar dados existentes de movimentações de estoque"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        from datetime import datetime
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('movimentacao_estoque'):
            movimentacoes = MovimentacaoEstoque.query.filter_by(ativo=True).order_by(
                MovimentacaoEstoque.data_movimentacao.desc()
            ).limit(1000).all()  # Limitar a 1000 para performance
        else:
            movimentacoes = []
        
        if not movimentacoes:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('estoque.listar_movimentacoes'))
        
        # Converter para Excel
        dados_export = []
        for m in movimentacoes:
            dados_export.append({
                'tipo_movimentacao': m.tipo_movimentacao,
                'cod_produto': m.cod_produto,
                'nome_produto': m.nome_produto,
                'local_movimentacao': m.local_movimentacao or '',
                'data_movimentacao': m.data_movimentacao.strftime('%d/%m/%Y') if m.data_movimentacao else '',
                'qtd_movimentacao': m.qtd_movimentacao,
                'observacao': m.observacao or '',
                'documento_origem': m.documento_origem or ''
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Movimentações Estoque', index=False)
            
            # Estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total Registros', 'Produtos Únicos', 'Tipos Únicos', 'Movimentação Total'],
                'Valor': [
                    len(movimentacoes),
                    len(set(m.cod_produto for m in movimentacoes)),
                    len(set(m.tipo_movimentacao for m in movimentacoes)),
                    sum(m.qtd_movimentacao for m in movimentacoes)
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=movimentacoes_estoque_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('estoque.listar_movimentacoes'))


# ========================================
# 🔄 MÓDULO DE UNIFICAÇÃO DE CÓDIGOS
# ========================================

@estoque_bp.route('/unificacao-codigos')
@login_required
def listar_unificacao_codigos():
    """Lista unificações de códigos"""
    from sqlalchemy import inspect
    
    # Definir variáveis no escopo da função para evitar UnboundLocalError
    codigo_busca = request.args.get('codigo_busca', '')
    status_filtro = request.args.get('status', '')
    
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('unificacao_codigos'):
            # Query base
            query = UnificacaoCodigos.query
            
            # Aplicar filtros
            if codigo_busca:
                try:
                    codigo_int = int(codigo_busca)
                    query = query.filter(
                        db.or_(
                            UnificacaoCodigos.codigo_origem == codigo_int,
                            UnificacaoCodigos.codigo_destino == codigo_int
                        )
                    )
                except ValueError:
                    pass
            
            if status_filtro == 'ativo':
                query = query.filter(UnificacaoCodigos.ativo.is_(True))
            elif status_filtro == 'inativo':
                query = query.filter(UnificacaoCodigos.ativo.is_(False))
            
            # Ordenação
            unificacoes = query.order_by(UnificacaoCodigos.created_at.desc()).limit(500).all()
            
            # Estatísticas
            total_unificacoes = UnificacaoCodigos.query.count()
            ativas = UnificacaoCodigos.query.filter_by(ativo=True).count()
            inativas = total_unificacoes - ativas
            
        else:
            unificacoes = []
            total_unificacoes = ativas = inativas = 0
            
    except Exception as e:
        unificacoes = []
        total_unificacoes = ativas = inativas = 0
    
    return render_template('estoque/listar_unificacao_codigos.html',
                         unificacoes=unificacoes,
                         total_unificacoes=total_unificacoes,
                         ativas=ativas,
                         inativas=inativas,
                         codigo_busca=codigo_busca,
                         status_filtro=status_filtro)

@estoque_bp.route('/unificacao-codigos/novo')
@login_required
def nova_unificacao_codigo():
    """Tela para criar nova unificação de código"""
    return render_template('estoque/nova_unificacao_codigo.html')

@estoque_bp.route('/unificacao-codigos/novo', methods=['POST'])
@login_required
def processar_nova_unificacao():
    """Processar criação de nova unificação"""
    try:
        codigo_origem = request.form.get('codigo_origem', '').strip()
        codigo_destino = request.form.get('codigo_destino', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        # Validações
        if not codigo_origem or not codigo_destino:
            flash('❌ Código origem e destino são obrigatórios!', 'error')
            return redirect(url_for('estoque.nova_unificacao_codigo'))
        
        try:
            codigo_origem = int(codigo_origem)
            codigo_destino = int(codigo_destino)
        except ValueError:
            flash('❌ Códigos devem ser números inteiros!', 'error')
            return redirect(url_for('estoque.nova_unificacao_codigo'))
        
        if codigo_origem == codigo_destino:
            flash('❌ Código origem deve ser diferente do código destino!', 'error')
            return redirect(url_for('estoque.nova_unificacao_codigo'))
        
        # Verificar se já existe unificação para este par
        existe = UnificacaoCodigos.query.filter_by(
            codigo_origem=codigo_origem,
            codigo_destino=codigo_destino
        ).first()
        
        if existe:
            flash('❌ Já existe uma unificação para este par de códigos!', 'error')
            return redirect(url_for('estoque.nova_unificacao_codigo'))
        
        # Verificar ciclos (evitar A->B e B->A)
        ciclo = UnificacaoCodigos.query.filter_by(
            codigo_origem=codigo_destino,
            codigo_destino=codigo_origem
        ).first()
        
        if ciclo:
            flash(f'❌ Ciclo detectado! Já existe unificação {codigo_destino} → {codigo_origem}', 'error')
            return redirect(url_for('estoque.nova_unificacao_codigo'))
        
        # Criar nova unificação
        nova_unificacao = UnificacaoCodigos()
        nova_unificacao.codigo_origem = codigo_origem
        nova_unificacao.codigo_destino = codigo_destino
        nova_unificacao.observacao = observacao
        nova_unificacao.created_by = current_user.nome
        nova_unificacao.data_ativacao = agora_brasil()
        
        db.session.add(nova_unificacao)
        db.session.commit()
        
        flash(f'✅ Unificação criada: {codigo_origem} → {codigo_destino}', 'success')
        return redirect(url_for('estoque.listar_unificacao_codigos'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao criar unificação: {str(e)}', 'error')
        return redirect(url_for('estoque.nova_unificacao_codigo'))

@estoque_bp.route('/unificacao-codigos/toggle/<int:id>')
@login_required
def toggle_unificacao_codigo(id):
    """Ativa/Desativa unificação de código"""
    try:
        unificacao = UnificacaoCodigos.query.get_or_404(id)
        motivo = request.args.get('motivo', '')
        
        if unificacao.ativo:
            unificacao.desativar(usuario=current_user.nome, motivo=motivo)
            flash(f'🔴 Unificação {unificacao.codigo_origem} → {unificacao.codigo_destino} DESATIVADA', 'warning')
        else:
            unificacao.ativar(usuario=current_user.nome)
            flash(f'🟢 Unificação {unificacao.codigo_origem} → {unificacao.codigo_destino} ATIVADA', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao alterar status: {str(e)}', 'error')
    
    return redirect(url_for('estoque.listar_unificacao_codigos'))

@estoque_bp.route('/unificacao-codigos/importar')
@login_required
def importar_unificacao_codigos():
    """Tela para importar unificações de códigos"""
    return render_template('estoque/importar_unificacao_codigos.html')

@estoque_bp.route('/unificacao-codigos/importar', methods=['POST'])
@login_required
def processar_importacao_unificacao():
    """Processar importação de unificações de códigos"""
    try:
        import pandas as pd
        import tempfile
        import os
        from werkzeug.utils import secure_filename
        
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('estoque.importar_unificacao_codigos'))
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(url_for('estoque.importar_unificacao_codigos'))
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(url_for('estoque.importar_unificacao_codigos'))
        
        # 📁 CORREÇÃO: Ler arquivo uma vez e usar bytes para ambas operações
        original_filename = arquivo.filename
        
        # Ler o arquivo uma vez e usar os bytes
        arquivo.seek(0)  # Garantir que está no início
        file_content = arquivo.read()  # Ler todo o conteúdo uma vez
        
        # 📁 Para processamento, criar arquivo temporário dos bytes
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file.write(file_content)  # Usar os bytes já lidos
            temp_filepath = temp_file.name

        try:
            # Processar arquivo
            if original_filename.lower().endswith('.xlsx'):
                df = pd.read_excel(temp_filepath)
            else:
                df = pd.read_csv(temp_filepath, encoding='utf-8', sep=';')
        finally:
            # 🗑️ Remover arquivo temporário
            try:
                os.unlink(temp_filepath)
            except OSError:
                pass  # Ignorar se não conseguir remover
        
        # Verificar colunas obrigatórias
        colunas_obrigatorias = ['codigo_origem', 'codigo_destino']
        colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('estoque.importar_unificacao_codigos'))
        
        unificacoes_importadas = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                codigo_origem = row.get('codigo_origem')
                codigo_destino = row.get('codigo_destino')
                observacao = str(row.get('observacao', '')).strip()
                
                # Validações
                if pd.isna(codigo_origem) or pd.isna(codigo_destino):
                    erros.append(f"Linha {index + 1}: Códigos obrigatórios")
                    continue
                
                try:
                    codigo_origem = int(codigo_origem)
                    codigo_destino = int(codigo_destino)
                except (ValueError, TypeError):
                    erros.append(f"Linha {index + 1}: Códigos devem ser inteiros")
                    continue
                
                if codigo_origem == codigo_destino:
                    erros.append(f"Linha {index + 1}: Códigos não podem ser iguais")
                    continue
                
                # Verificar se já existe
                existe = UnificacaoCodigos.query.filter_by(
                    codigo_origem=codigo_origem,
                    codigo_destino=codigo_destino
                ).first()
                
                if existe:
                    if not existe.ativo:
                        # Reativar unificação existente
                        existe.ativar(usuario=current_user.nome)
                        unificacoes_importadas += 1
                    continue
                
                # Verificar ciclos
                ciclo = UnificacaoCodigos.query.filter_by(
                    codigo_origem=codigo_destino,
                    codigo_destino=codigo_origem
                ).first()
                
                if ciclo:
                    erros.append(f"Linha {index + 1}: Ciclo detectado {codigo_destino}→{codigo_origem}")
                    continue
                
                # Criar nova unificação
                nova_unificacao = UnificacaoCodigos()
                nova_unificacao.codigo_origem = codigo_origem
                nova_unificacao.codigo_destino = codigo_destino
                nova_unificacao.observacao = observacao
                nova_unificacao.created_by = current_user.nome
                nova_unificacao.data_ativacao = agora_brasil()
                
                db.session.add(nova_unificacao)
                unificacoes_importadas += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                continue
        
        db.session.commit()
        
        # Mensagens de resultado
        if unificacoes_importadas > 0:
            flash(f"✅ {unificacoes_importadas} unificações importadas com sucesso!", 'success')
        
        if erros[:5]:  # Mostrar apenas os primeiros 5 erros
            for erro in erros[:5]:
                flash(f"❌ {erro}", 'error')
        
        return redirect(url_for('estoque.listar_unificacao_codigos'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('estoque.importar_unificacao_codigos'))

@estoque_bp.route('/unificacao-codigos/baixar-modelo')
@login_required
def baixar_modelo_unificacao():
    """Baixar modelo Excel para importação de unificações"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        # Dados exemplo conforme arquivo CSV 7
        dados_exemplo = {
            'codigo_origem': [4080177, 4320162, 4729098, 4210155],
            'codigo_destino': [4729098, 4080177, 4320162, 4729098],
            'observacao': [
                'Mesmo produto - códigos diferentes para clientes',
                'Unificação por similaridade',
                'Consolidação de estoque',
                'Padronização de códigos'
            ]
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # Instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Campos obrigatórios: codigo_origem, codigo_destino',
                    '2. Códigos devem ser números inteiros',
                    '3. Código origem ≠ código destino',
                    '4. Sistema evita ciclos automaticamente',
                    '5. Se unificação existe inativa, será reativada',
                    '6. Observação é opcional mas recomendada',
                    '7. Para efeitos de estoque: códigos são tratados como mesmo produto',
                    '8. Telas mostram sempre código original'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_unificacao_codigos.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('estoque.listar_unificacao_codigos'))

@estoque_bp.route('/unificacao-codigos/exportar-dados')
@login_required
def exportar_dados_unificacao():
    """Exportar dados existentes de unificações"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        from datetime import datetime
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
        if inspector.has_table('unificacao_codigos'):
            unificacoes = UnificacaoCodigos.query.order_by(
                UnificacaoCodigos.created_at.desc()
            ).all()
        else:
            unificacoes = []
        
        if not unificacoes:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('estoque.listar_unificacao_codigos'))
        
        # Converter para Excel
        dados_export = []
        for u in unificacoes:
            dados_export.append({
                'codigo_origem': u.codigo_origem,
                'codigo_destino': u.codigo_destino,
                'observacao': u.observacao or '',
                'ativo': 'Sim' if u.ativo else 'Não',
                'created_at': u.created_at.strftime('%d/%m/%Y %H:%M') if u.created_at else '',
                'created_by': u.created_by or '',
                'data_ativacao': u.data_ativacao.strftime('%d/%m/%Y %H:%M') if u.data_ativacao else '',
                'data_desativacao': u.data_desativacao.strftime('%d/%m/%Y %H:%M') if u.data_desativacao else '',
                'motivo_desativacao': u.motivo_desativacao or ''
            })
        
        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Unificações', index=False)
            
            # Estatísticas
            ativas = len([u for u in unificacoes if u.ativo])
            inativas = len(unificacoes) - ativas
            
            stats = pd.DataFrame({
                'Estatística': ['Total Unificações', 'Ativas', 'Inativas', 'Códigos Origem Únicos', 'Códigos Destino Únicos'],
                'Valor': [
                    len(unificacoes),
                    ativas,
                    inativas,
                    len(set(u.codigo_origem for u in unificacoes)),
                    len(set(u.codigo_destino for u in unificacoes))
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=unificacao_codigos_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('estoque.listar_unificacao_codigos'))

@estoque_bp.route('/saldo-estoque')
@login_required  
def saldo_estoque():
    """Dashboard principal do saldo de estoque com projeção de 29 dias"""
    try:
        # Obter todos os produtos com movimentação de estoque
        produtos = SaldoEstoque.obter_produtos_com_estoque()
        
        # Estatísticas gerais
        total_produtos = len(produtos)
        produtos_criticos = 0
        produtos_atencao = 0
        
        # Processar resumo de cada produto (limitado para performance)
        limite = min(50, len(produtos))  # Máximo 50 produtos na tela inicial
        produtos_resumo = []
        
        for produto in produtos[:limite]:
            resumo = SaldoEstoque.obter_resumo_produto(produto.cod_produto, produto.nome_produto)
            if resumo:
                produtos_resumo.append(resumo)
                
                # Contadores de status
                if resumo['status_ruptura'] == 'CRÍTICO':
                    produtos_criticos += 1
                elif resumo['status_ruptura'] == 'ATENÇÃO':
                    produtos_atencao += 1
        
        # Estatísticas
        estatisticas = {
            'total_produtos': total_produtos,
            'produtos_exibidos': len(produtos_resumo),
            'produtos_criticos': produtos_criticos,
            'produtos_atencao': produtos_atencao,
            'produtos_ok': len(produtos_resumo) - produtos_criticos - produtos_atencao
        }
        
        return render_template('estoque/saldo_estoque.html',
                             produtos=produtos_resumo,
                             estatisticas=estatisticas,
                             limite_exibicao=limite < total_produtos)
        
    except Exception as e:
        flash(f'❌ Erro ao carregar saldo de estoque: {str(e)}', 'error')
        return render_template('estoque/saldo_estoque.html',
                             produtos=[],
                             estatisticas={'total_produtos': 0, 'produtos_exibidos': 0, 
                                         'produtos_criticos': 0, 'produtos_atencao': 0, 'produtos_ok': 0},
                             limite_exibicao=False)

@estoque_bp.route('/saldo-estoque/api/produto/<cod_produto>')
@login_required
def api_saldo_produto(cod_produto):
    """API para obter dados detalhados de um produto específico"""
    try:
        # Buscar nome do produto
        produto = MovimentacaoEstoque.query.filter_by(
            cod_produto=str(cod_produto),
            ativo=True
        ).first()
        
        if not produto:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        # Obter resumo completo
        resumo = SaldoEstoque.obter_resumo_produto(cod_produto, produto.nome_produto)
        
        if not resumo:
            return jsonify({'error': 'Erro ao calcular projeção'}), 500
        
        return jsonify({
            'success': True,
            'produto': resumo
        })
        
    except Exception as e:
        logger.error(f"Erro na API saldo produto {cod_produto}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estoque_bp.route('/saldo-estoque/processar-ajuste', methods=['POST'])
@login_required
@require_admin()
def processar_ajuste_estoque():
    """Processa ajuste de estoque via modal"""
    try:
        data = request.get_json()
        
        cod_produto = data.get('cod_produto')
        qtd_ajuste = data.get('qtd_ajuste')
        motivo = data.get('motivo', '')
        
        if not cod_produto or qtd_ajuste is None:
            return jsonify({'error': 'Código do produto e quantidade são obrigatórios'}), 400
        
        try:
            qtd_ajuste = float(qtd_ajuste)
        except ValueError:
            return jsonify({'error': 'Quantidade deve ser um número'}), 400
        
        if qtd_ajuste == 0:
            return jsonify({'error': 'Quantidade não pode ser zero'}), 400
        
        # Processar ajuste
        SaldoEstoque.processar_ajuste_estoque(
            cod_produto=cod_produto,
            qtd_ajuste=qtd_ajuste,
            motivo=motivo,
            usuario=current_user.nome
        )
        
        return jsonify({
            'success': True,
            'message': f'✅ Ajuste de {qtd_ajuste} unidades processado com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar ajuste: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estoque_bp.route('/saldo-estoque/filtrar')
@login_required
def filtrar_saldo_estoque():
    """Filtra produtos do saldo de estoque"""
    try:
        # Parâmetros de filtro
        codigo_produto = request.args.get('codigo_produto', '')
        status_ruptura = request.args.get('status_ruptura', '')
        limite = int(request.args.get('limite', 50))
        
        # Obter produtos
        produtos = SaldoEstoque.obter_produtos_com_estoque()
        produtos_filtrados = []
        
        for produto in produtos:
            # Filtro por código
            if codigo_produto and codigo_produto not in str(produto.cod_produto):
                continue
                
            resumo = SaldoEstoque.obter_resumo_produto(produto.cod_produto, produto.nome_produto)
            if not resumo:
                continue
                
            # Filtro por status
            if status_ruptura and resumo['status_ruptura'] != status_ruptura:
                continue
                
            produtos_filtrados.append(resumo)
            
            # Limite
            if len(produtos_filtrados) >= limite:
                break
        
        return jsonify({
            'success': True,
            'produtos': produtos_filtrados,
            'total_encontrados': len(produtos_filtrados)
        })
        
    except Exception as e:
        logger.error(f"Erro ao filtrar saldo estoque: {str(e)}")
        return jsonify({'error': str(e)}), 500 