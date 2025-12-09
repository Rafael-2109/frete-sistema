import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app import db
# MIGRADO: SaldoEstoque -> SaldoEstoqueCompativel (02/09/2025)
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
# from app.estoque.models import SaldoEstoque
from app.estoque.services.compatibility_layer import SaldoEstoque
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.utils.timezone import agora_brasil
from app.utils.valores_brasileiros import formatar_valor_brasileiro
import logging
import tempfile
import os
import io
from datetime import datetime, timedelta
import random
from sqlalchemy import inspect, func, extract
from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
from app.carteira.models import CarteiraPrincipal
from io import BytesIO
from app.estoque import estoque_bp

logger = logging.getLogger(__name__)


def converter_projecao_para_resumo(projecao):
    """Converte projeção do novo sistema para formato do resumo esperado pelas telas"""
    if not projecao:
        return None
    
    # Garantir que valores numéricos nunca sejam None
    menor_estoque_d7 = projecao.get('menor_estoque_d7')
    if menor_estoque_d7 is None:
        menor_estoque_d7 = 0
    
    estoque_atual = projecao.get('estoque_atual', 0)
    if estoque_atual is None:
        estoque_atual = 0
    
    # NOVO: Calcular disponibilidade (quando estoque > 0)
    data_disponivel = None
    qtd_disponivel = None
    dias_disponivel = None
    
    # Verificar projeção para encontrar quando terá estoque > 0
    projecao_lista = projecao.get('projecao', [])
    for dia_info in projecao_lista:
        # Usar SALDO (Est. Inicial - Saída) como no workspace
        est_inicial = dia_info.get('saldo_inicial', 0) or 0
        saida = dia_info.get('saida', 0) or 0
        saldo = est_inicial - saida
        
        if saldo > 0:
            data_disponivel = dia_info.get('data')
            qtd_disponivel = saldo
            # Calcular dias até disponível
            if data_disponivel:
                try:
                    data_disp_obj = datetime.strptime(data_disponivel, '%Y-%m-%d')
                    hoje = datetime.now()
                    dias_disponivel = (data_disp_obj - hoje).days
                except Exception as e:
                    dias_disponivel = None
            break
    
    # NOVO: Buscar quantidade total na carteira de pedidos
    cod_produto = projecao.get('cod_produto', '')
    qtd_total_carteira = 0
    if cod_produto:
        try:
            # IMPORTANTE: Considerar UnificacaoCodigos
            from app.estoque.models import UnificacaoCodigos
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(str(cod_produto))
            
            # Somar qtd_saldo_produto_pedido de todos os pedidos do produto e códigos unificados
            soma_carteira = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ Filtrar apenas saldo positivo
            ).scalar()
            qtd_total_carteira = float(soma_carteira) if soma_carteira else 0
        except Exception as e:
            logger.error(f"Erro ao buscar carteira para produto {cod_produto}: {e}")
            qtd_total_carteira = 0
    
    # NOVO: Buscar quantidade total na programação de produção
    qtd_total_producao = 0
    if cod_produto:
        try:
            # IMPORTANTE: Considerar UnificacaoCodigos
            from app.estoque.models import UnificacaoCodigos
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(str(cod_produto))
            
            # Somar qtd_programada de todas as programações futuras do produto e códigos unificados
            hoje = datetime.now().date()
            soma_producao = db.session.query(
                func.sum(ProgramacaoProducao.qtd_programada)
            ).filter(
                ProgramacaoProducao.cod_produto.in_(codigos_relacionados),
                ProgramacaoProducao.data_programacao >= hoje
            ).scalar()
            qtd_total_producao = float(soma_producao) if soma_producao else 0
        except Exception as e:
            logger.error(f"Erro ao buscar produção para produto {cod_produto}: {e}")
            qtd_total_producao = 0
    
    # NOVO CRITÉRIO DE STATUS:
    # - Se Ruptura 7d > 0 então OK
    # - Senão se data disponível em até D+7 então ATENÇÃO
    # - Senão CRÍTICO
    if menor_estoque_d7 > 0:
        status_ruptura = 'OK'
    elif dias_disponivel is not None and dias_disponivel <= 7:
        status_ruptura = 'ATENÇÃO'
    else:
        status_ruptura = 'CRÍTICO'
    
    # Para previsao_ruptura, usar menor_estoque_d7 ao invés de dia_ruptura
    previsao_ruptura = menor_estoque_d7
    
    return {
        'cod_produto': projecao.get('cod_produto', ''),
        'nome_produto': projecao.get('nome_produto', ''),
        'estoque_inicial': estoque_atual,
        'estoque_atual': estoque_atual,
        'menor_estoque_d7': menor_estoque_d7,
        'previsao_ruptura': previsao_ruptura,  # Agora é um número, não uma data
        'status_ruptura': status_ruptura,
        'qtd_total_carteira': qtd_total_carteira,  # ATUALIZADO: Soma real da carteira
        'qtd_total_producao': qtd_total_producao,  # NOVO: Soma da produção
        'projecao': projecao.get('projecao', []),
        # NOVO: Campos de disponibilidade
        'data_disponivel': data_disponivel,
        'qtd_disponivel': qtd_disponivel,
        'dias_disponivel': dias_disponivel
    }

# 📦 Blueprint do estoque (seguindo padrão dos outros módulos)

# Registrar filtro de formatação brasileira para o template
@estoque_bp.app_template_filter('valor_br')
def valor_br_filter(value, decimais=0):
    """Filtro Jinja2 para formatar valores no padrão brasileiro"""
    if value is None or value == '':
        return '0'
    
    try:
        valor_float = float(value)
        if decimais == 0:
            return f"{valor_float:,.0f}".replace(',', '.')
        else:
            valor_formatado = f"{valor_float:,.{decimais}f}"
            valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"R$ {valor_formatado}"
    except (ValueError, TypeError):
        return 'R$ 0,00'

@estoque_bp.route('/')
@login_required
def index():
    """Dashboard do módulo estoque"""
    try:
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
    observacao_filtro = request.args.get('observacao', '')  # NOVO: Filtro de observações
    
    # Paginação
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    per_page = 200  # 200 itens por página conforme solicitado
    
    try:
        inspector = inspect(db.engine)
        
        if inspector.has_table('movimentacao_estoque'):
            # Query base
            query = MovimentacaoEstoque.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
            if tipo_movimentacao:
                query = query.filter(MovimentacaoEstoque.tipo_movimentacao == tipo_movimentacao)
            # NOVO: Filtro de observações com ILIKE
            if observacao_filtro:
                query = query.filter(MovimentacaoEstoque.observacao.ilike(f'%{observacao_filtro}%'))
            
            # Ordenação e paginação
            movimentacoes = query.order_by(MovimentacaoEstoque.data_movimentacao.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 🔧 CARREGAR TIPOS DOS DADOS REAIS para o dropdown
            tipos_disponiveis = sorted(set(
                m.tipo_movimentacao for m in MovimentacaoEstoque.query.all() 
                if m.tipo_movimentacao
            ))
        else:
            movimentacoes = None
            tipos_disponiveis = []
    except Exception:
        movimentacoes = None
        tipos_disponiveis = []
    
    return render_template('estoque/listar_movimentacoes.html',
                         movimentacoes=movimentacoes,
                         cod_produto=cod_produto,
                         tipo_movimentacao=tipo_movimentacao,
                         observacao_filtro=observacao_filtro,  # NOVO: Passar filtro de observações
                         tipos_disponiveis=tipos_disponiveis)

@estoque_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo estoque"""
    try:
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
def importar_movimentacoes():
    """Tela para importar movimentações de estoque"""
    return render_template('estoque/importar_movimentacoes.html')

@estoque_bp.route('/movimentacoes/importar', methods=['POST'])
@login_required
def processar_importacao_movimentacoes():
    """Processar importação de movimentações de estoque"""
    try:
        
        
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
        tipos_permitidos = ['AVARIA', 'EST INICIAL', 'DEVOLUÇÃO', 'PRODUÇÃO', 'RETRABALHO', 'FATURAMENTO', 'AJUSTE']
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
                        except Exception as e:
                            try:
                                data_movimentacao = pd.to_datetime(data_movimentacao).date()
                            except Exception as e:
                                logger.error(f"Erro ao converter data_movimentacao: {e}")
                                data_movimentacao = None
                    elif hasattr(data_movimentacao, 'date'):
                        data_movimentacao = data_movimentacao.date()
                else:
                    data_movimentacao = None
                
                if not data_movimentacao:
                    erros.append(f"Linha {index + 1}: Data inválida") # type: ignore
                    continue
                
                # 📝 DADOS BÁSICOS
                nome_produto = str(row.get('nome_produto', '')).strip()
                qtd_movimentacao = float(row.get('qtd_movimentacao', 0) or 0)
                local_movimentacao = str(row.get('local_movimentacao', '')).strip()
                
                # 🔗 VERIFICAR/CRIAR PRODUTO NO CADASTRO DE PALLETIZAÇÃO
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
                
                # 📝 CAMPOS OPCIONAIS
                observacao = ''
                if 'observacao' in df.columns:
                    observacao = str(row.get('observacao', '')).strip()

                # 🔧 PRODUÇÃO COM CONSUMO AUTOMÁTICO DE COMPONENTES
                if tipo_movimentacao == 'PRODUÇÃO':
                    from app.estoque.services.consumo_producao_service import ServicoConsumoProducao

                    resultado_producao = ServicoConsumoProducao.processar_producao_com_consumo(
                        cod_produto=cod_produto,
                        qtd_produzida=qtd_movimentacao,
                        data_movimentacao=data_movimentacao,
                        nome_produto=nome_produto,
                        local_movimentacao=local_movimentacao,
                        observacao=observacao,
                        usuario=current_user.nome
                    )

                    if resultado_producao['sucesso']:
                        produtos_importados += 1

                        # Log de consumos e produções automáticas
                        n_consumos = len(resultado_producao.get('consumos', []))
                        n_producoes_auto = len(resultado_producao.get('producoes_automaticas', []))
                        if n_consumos > 0 or n_producoes_auto > 0:
                            logger.info(
                                f"📦 Produção {cod_produto}: "
                                f"{n_consumos} consumos, {n_producoes_auto} produções automáticas"
                            )

                        # Registrar avisos (sem bloquear)
                        for aviso in resultado_producao.get('avisos', []):
                            logger.warning(f"⚠️ Linha {index + 1}: {aviso}")
                    else:
                        erros.append(f"Linha {index + 1}: {resultado_producao.get('erro', 'Erro desconhecido na produção')}")
                    continue

                # ➕ CRIAR NOVO REGISTRO para outros tipos (sempre adiciona)
                nova_movimentacao = MovimentacaoEstoque()
                nova_movimentacao.tipo_movimentacao = tipo_movimentacao
                nova_movimentacao.cod_produto = cod_produto
                nova_movimentacao.nome_produto = nome_produto
                nova_movimentacao.local_movimentacao = local_movimentacao
                nova_movimentacao.data_movimentacao = data_movimentacao
                nova_movimentacao.qtd_movimentacao = qtd_movimentacao
                nova_movimentacao.criado_por = current_user.nome
                nova_movimentacao.observacao = observacao

                if 'documento_origem' in df.columns:
                    nova_movimentacao.documento_origem = str(row.get('documento_origem', '')).strip()

                db.session.add(nova_movimentacao)
                produtos_importados += 1
                
            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
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
# 🔍 API PARA BUSCA DE PRODUTOS
# ========================================

@estoque_bp.route('/api/buscar-produto/<codigo>')
@login_required
def buscar_produto_api(codigo):
    """API para buscar produtos por código ou nome (dropdown com sugestões)"""
    try:
        # Buscar produtos na tabela cadastro_palletizacao (CÓDIGO ou NOME)
        
        produtos = CadastroPalletizacao.query.filter(
            db.or_(
                CadastroPalletizacao.cod_produto.ilike(f'%{codigo}%'),
                CadastroPalletizacao.nome_produto.ilike(f'%{codigo}%')
            ),
            CadastroPalletizacao.ativo == True
        ).limit(15).all()
        
        if produtos:
            sugestoes = []
            for produto in produtos:
                sugestoes.append({
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto or 'Nome não cadastrado',
                    'display': f"{produto.cod_produto} - {produto.nome_produto or 'Nome não cadastrado'}"
                })
            
            return jsonify({
                'success': True,
                'sugestoes': sugestoes,
                'total': len(sugestoes)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nenhum produto encontrado',
                'sugestoes': []
            })
            
    except Exception as e:
        logger.error(f"Erro ao buscar produtos com '{codigo}': {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'sugestoes': []
        })


# ========================================
# 🆕 NOVA MOVIMENTAÇÃO MANUAL
# ========================================

@estoque_bp.route('/movimentacoes/nova')
@login_required
def nova_movimentacao():
    """Redireciona para listagem onde há modal de nova movimentação"""
    # Capturar parâmetros da URL para abrir modal com dados pré-preenchidos
    cod_produto = request.args.get('cod_produto')
    tipo = request.args.get('tipo')
    
    # Redirecionar para listagem com parâmetros para abrir modal automaticamente
    if cod_produto and tipo:
        return redirect(url_for('estoque.listar_movimentacoes', 
                               nova_mov=1, 
                               cod_produto=cod_produto, 
                               tipo=tipo))
    else:
        return redirect(url_for('estoque.listar_movimentacoes', nova_mov=1))

@estoque_bp.route('/movimentacoes/nova', methods=['POST'])
@login_required
def processar_nova_movimentacao():
    """Processar nova movimentação manual via modal"""
    try:
        # Capturar dados do formulário
        cod_produto = request.form.get('cod_produto', '').strip()
        nome_produto = request.form.get('nome_produto', '').strip()
        tipo_movimentacao = request.form.get('tipo_movimentacao', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        data_movimentacao = request.form.get('data_movimentacao', '').strip()
        local_movimentacao = request.form.get('local_movimentacao', '').strip()
        documento_origem = request.form.get('documento_origem', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        # Validações básicas
        if not cod_produto:
            return jsonify({'success': False, 'message': 'Código do produto é obrigatório'})
        
        if not tipo_movimentacao:
            return jsonify({'success': False, 'message': 'Tipo de movimentação é obrigatório'})
            
        if not quantidade:
            return jsonify({'success': False, 'message': 'Quantidade é obrigatória'})
            
        if not data_movimentacao:
            return jsonify({'success': False, 'message': 'Data é obrigatória'})
        
        # Converter quantidade para float
        try:
            quantidade_float = float(quantidade)
        except ValueError:
            return jsonify({'success': False, 'message': 'Quantidade deve ser um número válido'})
        
        # Verificar se produto existe
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()
        
        if not produto:
            return jsonify({'success': False, 'message': f'Produto {cod_produto} não encontrado no cadastro'})
        
        # Converter data
        try:
            data_movimentacao_dt = datetime.strptime(data_movimentacao, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Data inválida'})
        
        # Criar nova movimentação
        nova_movimentacao = MovimentacaoEstoque()
        nova_movimentacao.cod_produto = cod_produto
        nova_movimentacao.nome_produto = nome_produto or produto.nome_produto
        nova_movimentacao.tipo_movimentacao = tipo_movimentacao
        nova_movimentacao.qtd_movimentacao = quantidade_float
        nova_movimentacao.data_movimentacao = data_movimentacao_dt
        nova_movimentacao.local_movimentacao = local_movimentacao or 'ESTOQUE PRINCIPAL'
        nova_movimentacao.observacao = observacao
        nova_movimentacao.criado_por = current_user.nome
        nova_movimentacao.documento_origem = documento_origem
        
        db.session.add(nova_movimentacao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Movimentação de {quantidade_float} UN do produto {cod_produto} registrada com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar nova movimentação: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor. Tente novamente.'
        })


# ========================================
# ✏️ EDITAR MOVIMENTAÇÃO
# ========================================

@estoque_bp.route('/movimentacoes/<int:id>/editar')
@login_required
def editar_movimentacao(id):
    """Carregar dados da movimentação para edição - TODOS OS CAMPOS"""
    movimentacao = MovimentacaoEstoque.query.get_or_404(id)

    # Por segurança, só permitir edição de movimentações recentes (últimos 30 dias)
    limite_edicao = datetime.now().date() - timedelta(days=30)

    if movimentacao.data_movimentacao < limite_edicao:
        return jsonify({
            'success': False,
            'message': 'Não é possível editar movimentações antigas (mais de 30 dias)'
        })

    # Retornar TODOS os dados da movimentação para o modal
    return jsonify({
        'success': True,
        'movimentacao': {
            # Dados básicos
            'id': movimentacao.id,
            'cod_produto': movimentacao.cod_produto,
            'nome_produto': movimentacao.nome_produto,
            'tipo_movimentacao': movimentacao.tipo_movimentacao,
            'qtd_movimentacao': float(movimentacao.qtd_movimentacao) if movimentacao.qtd_movimentacao else 0,
            'data_movimentacao': movimentacao.data_movimentacao.strftime('%Y-%m-%d') if movimentacao.data_movimentacao else '',
            'local_movimentacao': movimentacao.local_movimentacao or '',
            'observacao': movimentacao.observacao or '',

            # Campos de vínculos (Pedidos, NF, Embarque)
            'separacao_lote_id': movimentacao.separacao_lote_id or '',
            'numero_nf': movimentacao.numero_nf or '',
            'num_pedido': movimentacao.num_pedido or '',
            'tipo_origem': movimentacao.tipo_origem or '',
            'status_nf': movimentacao.status_nf or '',
            'codigo_embarque': movimentacao.codigo_embarque or '',
            'pedido_compras_id': movimentacao.pedido_compras_id or '',

            # Campos Odoo (Rastreabilidade)
            'odoo_picking_id': movimentacao.odoo_picking_id or '',
            'odoo_move_id': movimentacao.odoo_move_id or '',
            'purchase_line_id': movimentacao.purchase_line_id or '',

            # Campos de auditoria
            'criado_em': movimentacao.criado_em.strftime('%d/%m/%Y %H:%M') if movimentacao.criado_em else '',
            'criado_por': movimentacao.criado_por or '',
            'atualizado_em': movimentacao.atualizado_em.strftime('%d/%m/%Y %H:%M') if movimentacao.atualizado_em else '',
            'atualizado_por': movimentacao.atualizado_por or '',
            'ativo': movimentacao.ativo
        }
    })

@estoque_bp.route('/movimentacoes/<int:id>/editar', methods=['POST'])
@login_required
def processar_edicao_movimentacao(id):
    """Processar edição de movimentação"""
    try:
        movimentacao = MovimentacaoEstoque.query.get_or_404(id)
        
        # Verificar limite de edição
        limite_edicao = datetime.now().date() - timedelta(days=30)
        
        if movimentacao.data_movimentacao < limite_edicao:
            return jsonify({
                'success': False,
                'message': 'Não é possível editar movimentações antigas (mais de 30 dias)'
            })
        
        # Capturar dados do formulário
        tipo_movimentacao = request.form.get('tipo_movimentacao', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        data_movimentacao = request.form.get('data_movimentacao', '').strip()
        local_movimentacao = request.form.get('local_movimentacao', '').strip()
        documento_origem = request.form.get('documento_origem', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        # Validações básicas
        if not tipo_movimentacao:
            return jsonify({'success': False, 'message': 'Tipo de movimentação é obrigatório'})
            
        if not quantidade:
            return jsonify({'success': False, 'message': 'Quantidade é obrigatória'})
            
        if not data_movimentacao:
            return jsonify({'success': False, 'message': 'Data é obrigatória'})
        
        # Converter quantidade para float
        try:
            quantidade_float = float(quantidade)
        except ValueError:
            return jsonify({'success': False, 'message': 'Quantidade deve ser um número válido'})
        
        # Converter data
        try:
            data_movimentacao_dt = datetime.strptime(data_movimentacao, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Data inválida'})
        
        # Atualizar movimentação
        movimentacao.tipo_movimentacao = tipo_movimentacao
        movimentacao.qtd_movimentacao = quantidade_float
        movimentacao.data_movimentacao = data_movimentacao_dt
        movimentacao.local_movimentacao = local_movimentacao or 'ESTOQUE PRINCIPAL'
        movimentacao.observacao = observacao
        movimentacao.atualizado_por = current_user.nome
        
        # Adicionar campo documento_origem se existir
        if hasattr(movimentacao, 'documento_origem'):
            movimentacao.documento_origem = documento_origem
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Movimentação do produto {movimentacao.cod_produto} atualizada com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao editar movimentação {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor. Tente novamente.'
        })


# ========================================
# 🆕 UNIFICAÇÃO DE CÓDIGOS
# ========================================

@estoque_bp.route('/unificacao-codigos')
@login_required
def listar_unificacao_codigos():
    """Lista unificações de códigos"""
    
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
                    erros.append(f"Linha {index + 1}: Códigos obrigatórios") # type: ignore
                    continue
                
                try:
                    codigo_origem = int(codigo_origem)
                    codigo_destino = int(codigo_destino)
                except (ValueError, TypeError):
                    erros.append(f"Linha {index + 1}: Códigos devem ser inteiros") # type: ignore
                    continue
                
                if codigo_origem == codigo_destino:
                    erros.append(f"Linha {index + 1}: Códigos não podem ser iguais") # type: ignore
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
                    erros.append(f"Linha {index + 1}: Ciclo detectado {codigo_destino}→{codigo_origem}") # type: ignore
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
                erros.append(f"Linha {index + 1}: {str(e)}") # type: ignore
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
        # Obter parâmetros de filtro e ordenação
        codigo_produto = request.args.get('codigo_produto', '').strip()
        status_ruptura = request.args.get('status_ruptura', '').strip()
        limite_param = request.args.get('limite', '50')
        page = request.args.get('page', 1, type=int)
        ordem_coluna = request.args.get('ordem', 'codigo')  # codigo, produto, estoque, carteira, ruptura, status
        ordem_direcao = request.args.get('dir', 'asc')  # asc ou desc
        
        # NOVO: Filtros de subcategorias
        categoria_filtro = request.args.get('categoria', '').strip()
        embalagem_filtro = request.args.get('embalagem', '').strip()
        materia_prima_filtro = request.args.get('materia_prima', '').strip()
        linha_producao_filtro = request.args.get('linha_producao', '').strip()
        
        # Validar limite
        try:
            limite = int(limite_param)
            if limite not in [50, 100, 200]:
                limite = 50
        except Exception as e:
            logger.error(f"Erro ao validar limite: {e}")
            limite = 50
        
        # Obter todos os produtos com movimentação de estoque
        produtos = SaldoEstoque.obter_produtos_com_estoque()
        
        # Filtrar por código se especificado
        if codigo_produto:
            produtos = [p for p in produtos if codigo_produto.lower() in str(p.get('cod_produto', '')).lower() or 
                       codigo_produto.lower() in str(p.get('nome_produto', '')).lower()]
        
        # NOVO: Aplicar filtros de subcategorias se houver
        produtos_codigos = [p.get('cod_produto') for p in produtos]
        if categoria_filtro or embalagem_filtro or materia_prima_filtro or linha_producao_filtro:
            # Buscar produtos com as categorias especificadas
            query = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.cod_produto.in_(produtos_codigos)
            )
            
            if categoria_filtro:
                query = query.filter(CadastroPalletizacao.categoria_produto == categoria_filtro)
            if embalagem_filtro:
                query = query.filter(CadastroPalletizacao.tipo_embalagem == embalagem_filtro)
            if materia_prima_filtro:
                query = query.filter(CadastroPalletizacao.tipo_materia_prima == materia_prima_filtro)
            if linha_producao_filtro:
                query = query.filter(CadastroPalletizacao.linha_producao == linha_producao_filtro)
            
            produtos_filtrados_codes = [p.cod_produto for p in query.all()]
            produtos = [p for p in produtos if p.get('cod_produto') in produtos_filtrados_codes]
        
        # Para melhorar performance, processar apenas uma amostra para estatísticas
        # e processar apenas os necessários para exibição
        total_produtos = len(produtos)
        
        # Se houver muitos produtos, fazer amostragem para estatísticas
        if total_produtos > 200:
            # Amostrar 200 produtos para estatísticas rápidas
            produtos_amostra = random.sample(produtos, min(200, total_produtos))
        else:
            produtos_amostra = produtos
        
        # Estatísticas aproximadas baseadas na amostra
        produtos_criticos = 0
        produtos_atencao = 0
        produtos_ok = 0
        
        # Processar apenas produtos da página atual + amostra para estatísticas
        produtos_com_resumo = []
        
        # Primeiro processar a amostra para estatísticas
        for produto in produtos_amostra[:50]:  # Limitar ainda mais para performance
            # USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
            projecao = ServicoEstoqueSimples.get_projecao_completa(produto.get('cod_produto'), dias=7)
            # Converter para formato compatível
            resumo = converter_projecao_para_resumo(projecao) if projecao else None
            if resumo:
                # Contadores de status
                if resumo['status_ruptura'] == 'CRÍTICO':
                    produtos_criticos += 1
                elif resumo['status_ruptura'] == 'ATENÇÃO':
                    produtos_atencao += 1
                else:
                    produtos_ok += 1
        
        # Estimar estatísticas para o total se foi amostrado
        if total_produtos > 50:
            fator = total_produtos / 50
            produtos_criticos = int(produtos_criticos * fator)
            produtos_atencao = int(produtos_atencao * fator)
            produtos_ok = int(produtos_ok * fator)
        
        # Agora processar apenas os produtos da página atual
        inicio = (page - 1) * limite
        fim = inicio + limite
        produtos_pagina = produtos[inicio:fim]
        
        produtos_resumo = []
        for produto in produtos_pagina:
            # USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
            projecao = ServicoEstoqueSimples.get_projecao_completa(produto.get('cod_produto'), dias=28)
            # Converter para formato compatível
            resumo = converter_projecao_para_resumo(projecao) if projecao else None
            if resumo:
                produtos_resumo.append(resumo)
        
        # Aplicar ordenação server-side nos resultados da página
        if ordem_coluna == 'codigo':
            produtos_resumo.sort(key=lambda x: x['cod_produto'], reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'produto':
            produtos_resumo.sort(key=lambda x: x['nome_produto'], reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'estoque':
            produtos_resumo.sort(key=lambda x: x.get('estoque_inicial', 0) if x.get('estoque_inicial') is not None else 0, reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'carteira':
            produtos_resumo.sort(key=lambda x: x.get('qtd_total_carteira', 0) if x.get('qtd_total_carteira') is not None else 0, reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'producao':
            # Ordenação para coluna Produção
            produtos_resumo.sort(key=lambda x: x.get('qtd_total_producao', 0) if x.get('qtd_total_producao') is not None else 0, reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'disponivel':
            # Ordenação especial para Disponível
            # Se ASC: ordena D+ crescente, mas dentro de cada D+ ordena qtd decrescente
            # Se DESC: ordena D+ decrescente, mas dentro de cada D+ ordena qtd crescente
            def sort_key_disponivel(x):
                dias = x.get('dias_disponivel')
                qtd = x.get('qtd_disponivel', 0) if x.get('qtd_disponivel') else 0
                
                # Se não tem disponibilidade, vai pro final
                if dias is None:
                    return (999999, 0) if ordem_direcao == 'asc' else (-999999, 0)
                
                # Para ASC: ordena por dias crescente, qtd decrescente
                if ordem_direcao == 'asc':
                    return (dias, -qtd)
                # Para DESC: ordena por dias decrescente, qtd crescente  
                else:
                    return (-dias, qtd)
                    
            produtos_resumo.sort(key=sort_key_disponivel)
        elif ordem_coluna == 'ruptura':
            produtos_resumo.sort(key=lambda x: x['previsao_ruptura'] if x['previsao_ruptura'] is not None else float('inf'), reverse=(ordem_direcao == 'desc'))
        elif ordem_coluna == 'status':
            # Ordenar por prioridade: CRÍTICO > ATENÇÃO > OK
            status_ordem = {'CRÍTICO': 0, 'ATENÇÃO': 1, 'OK': 2}
            produtos_resumo.sort(key=lambda x: status_ordem.get(x['status_ruptura'], 3), reverse=(ordem_direcao == 'desc'))
        
        # Calcular total de páginas
        total_filtrado = total_produtos
        total_paginas = (total_filtrado + limite - 1) // limite
        
        # Estatísticas
        estatisticas = {
            'total_produtos': total_produtos,
            'produtos_exibidos': len(produtos_resumo),
            'produtos_criticos': produtos_criticos,
            'produtos_atencao': produtos_atencao,
            'produtos_ok': produtos_ok,
            'total_filtrado': total_filtrado
        }
        
        # NOVO: Buscar valores únicos para os filtros
        categorias = db.session.query(CadastroPalletizacao.categoria_produto).distinct().filter(
            CadastroPalletizacao.categoria_produto.isnot(None)
        ).order_by(CadastroPalletizacao.categoria_produto).all()
        categorias = [c[0] for c in categorias if c[0]]
        
        embalagens = db.session.query(CadastroPalletizacao.tipo_embalagem).distinct().filter(
            CadastroPalletizacao.tipo_embalagem.isnot(None)
        ).order_by(CadastroPalletizacao.tipo_embalagem).all()
        embalagens = [e[0] for e in embalagens if e[0]]
        
        materias_primas = db.session.query(CadastroPalletizacao.tipo_materia_prima).distinct().filter(
            CadastroPalletizacao.tipo_materia_prima.isnot(None)
        ).order_by(CadastroPalletizacao.tipo_materia_prima).all()
        materias_primas = [m[0] for m in materias_primas if m[0]]
        
        linhas_producao = db.session.query(CadastroPalletizacao.linha_producao).distinct().filter(
            CadastroPalletizacao.linha_producao.isnot(None)
        ).order_by(CadastroPalletizacao.linha_producao).all()
        linhas_producao = [linha[0] for linha in linhas_producao if linha[0]]
        
        return render_template('estoque/saldo_estoque.html',
                             produtos=produtos_resumo,
                             estatisticas=estatisticas,
                             limite_exibicao=limite < total_produtos,
                             page=page,
                             total_paginas=total_paginas,
                             limite=limite,
                             codigo_produto=codigo_produto,
                             status_ruptura=status_ruptura,
                             categoria_filtro=categoria_filtro,
                             embalagem_filtro=embalagem_filtro,
                             materia_prima_filtro=materia_prima_filtro,
                             linha_producao_filtro=linha_producao_filtro,
                             categorias=categorias,
                             embalagens=embalagens,
                             materias_primas=materias_primas,
                             linhas_producao=linhas_producao)
        
    except Exception as e:
        import traceback
        logger.error(f"Erro ao carregar saldo de estoque: {str(e)}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        flash(f'❌ Erro ao carregar saldo de estoque: {str(e)}', 'error')
        return render_template('estoque/saldo_estoque.html',
                             produtos=[],
                             estatisticas={'total_produtos': 0, 'produtos_exibidos': 0, 
                                         'produtos_criticos': 0, 'produtos_atencao': 0, 'produtos_ok': 0,
                                         'total_filtrado': 0},
                             limite_exibicao=False,
                             page=1,
                             total_paginas=1,
                             limite=50,
                             codigo_produto='',
                             status_ruptura='',
                             # Adicionar campos que faltavam
                             categoria_filtro='',
                             embalagem_filtro='',
                             materia_prima_filtro='',
                             linha_producao_filtro='',
                             categorias=[],
                             embalagens=[],
                             materias_primas=[],
                             linhas_producao=[])

@estoque_bp.route('/saldo-estoque/api/produto/<cod_produto>')
@login_required
def api_saldo_produto(cod_produto):
    """API para obter dados detalhados de um produto específico"""
    try:
        # USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
        # Obter projeção completa
        projecao = ServicoEstoqueSimples.get_projecao_completa(cod_produto, dias=28)
        resumo = converter_projecao_para_resumo(projecao) if projecao else None
        
        if not resumo:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        # Se não tem nome, buscar do MovimentacaoEstoque
        if not resumo.get('nome_produto') or resumo['nome_produto'] == f'Produto {cod_produto}':
            produto = MovimentacaoEstoque.query.filter_by(
                cod_produto=str(cod_produto),
                ativo=True
            ).first()
            if produto:
                resumo['nome_produto'] = produto.nome_produto
        
        return jsonify({
            'success': True,
            'produto': resumo
        })
        
    except Exception as e:
        logger.error(f"Erro na API saldo produto {cod_produto}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estoque_bp.route('/saldo-estoque/processar-ajuste', methods=['POST'])
@login_required
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

@estoque_bp.route('/movimentacoes/baixar-modelo')
@login_required
def baixar_modelo_movimentacoes():
    """Download do modelo Excel para importação de movimentações"""
    try:
        
        # Criar modelo Excel
        modelo_data = {
            'data_movimentacao': ['2025-07-16'],
            'cod_produto': ['EXEMPLO001'],
            'nome_produto': ['Produto de exemplo'],
            'tipo_movimentacao': ['ENTRADA'],  # ENTRADA ou SAIDA
            'qtd_movimentacao': [100],
            'observacao': ['Observação da movimentação'],
            'local_movimentacao': ['Linha de Produção']
        }
        
        df = pd.DataFrame(modelo_data)
        
        # Criar Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Movimentações')
            
            # Adicionar instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES': [
                    '1. Preencha todos os campos obrigatórios',
                    '2. Data deve estar no formato YYYY-MM-DD',
                    '3. Tipo movimentação: ENTRADA ou SAIDA',
                    '4. Quantidade deve ser numérica',
                    '5. Salve o arquivo e importe na tela de movimentações'
                ]
            })
            instrucoes.to_excel(writer, index=False, sheet_name='Instruções')
        
        output.seek(0)
        
        response = make_response(output.read())
        response.headers['Content-Disposition'] = f'attachment; filename=modelo_movimentacoes_{datetime.now().strftime("%Y%m%d")}.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar modelo: {str(e)}")
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('estoque.index'))

@estoque_bp.route('/movimentacoes/exportar-dados')
@login_required
def exportar_dados_movimentacoes():
    """Exporta dados de movimentações para Excel"""
    try:        
        # Buscar movimentações
        movimentacoes = MovimentacaoEstoque.query.order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()
        
        # Converter para dicionário
        dados = []
        for mov in movimentacoes:
            dados.append({
                'ID': mov.id,
                'data_movimentacao': mov.data_movimentacao.strftime('%d/%m/%Y') if mov.data_movimentacao else '',
                'cod_produto': str(mov.cod_produto),
                'nome_produto': mov.nome_produto,
                'tipo_movimentacao': mov.tipo_movimentacao,
                'qtd_movimentacao': formatar_valor_brasileiro(mov.qtd_movimentacao),
                'observacao': mov.observacao,
                'local_movimentacao': mov.local_movimentacao,
                'separacao_lote_id': mov.separacao_lote_id,
                'numero_nf': mov.numero_nf,
                'num_pedido': mov.num_pedido,
                'tipo_origem': mov.tipo_origem,
                'status_nf': mov.status_nf,
                'codigo_embarque': mov.codigo_embarque,
                'criado_em': mov.criado_em.strftime('%d/%m/%Y %H:%M') if mov.criado_em else '',
                'criado_por': mov.criado_por,
                'atualizado_em': mov.atualizado_em.strftime('%d/%m/%Y %H:%M') if mov.atualizado_em else '',
                'atualizado_por': mov.atualizado_por,
                'ativo': mov.ativo
            })
        
        df = pd.DataFrame(dados)
        
        # Criar Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Movimentações')
            
            # Adicionar resumo
            resumo = pd.DataFrame({
                'Estatísticas': [
                    f'Total de movimentações: {len(dados)}',
                    f'Exportado em: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    f'Sistema de Fretes'
                ]
            })
            resumo.to_excel(writer, index=False, sheet_name='Resumo')
        
        output.seek(0)
        
        response = make_response(output.read())
        response.headers['Content-Disposition'] = f'attachment; filename=movimentacoes_estoque_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados: {str(e)}")
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('estoque.index'))


@estoque_bp.route('/excluir_movimentacao/<int:id>', methods=['DELETE', 'GET'])
@login_required
def excluir_movimentacao(id):
    """
    Excluir uma movimentação de estoque via AJAX sem recarregar a página
    """
    try:
        movimentacao = MovimentacaoEstoque.query.get_or_404(id)
        
        # Log da exclusão
        logger.info(f"Excluindo movimentação ID {id}: {movimentacao.cod_produto} - {movimentacao.tipo_movimentacao}")
        
        # Guardar dados para retornar
        cod_produto = movimentacao.cod_produto
        tipo = movimentacao.tipo_movimentacao
        
        db.session.delete(movimentacao)
        db.session.commit()
        
        # Se for requisição AJAX (DELETE), retornar JSON
        if request.method == 'DELETE':
            return jsonify({
                'success': True,
                'message': f'Movimentação {tipo} do produto {cod_produto} excluída com sucesso.'
            })
        else:
            # Se for GET (fallback), redirecionar
            flash(f'Movimentação {tipo} do produto {cod_produto} excluída com sucesso.', 'success')
            return redirect(url_for('estoque.listar_movimentacoes'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir movimentação {id}: {str(e)}")
        
        if request.method == 'DELETE':
            return jsonify({
                'success': False,
                'message': f'Erro ao excluir movimentação: {str(e)}'
            }), 500
        else:
            flash(f'Erro ao excluir movimentação: {str(e)}', 'danger')
            return redirect(url_for('estoque.listar_movimentacoes'))


# Sistema híbrido removido - usando novo sistema de estoque em tempo real

@estoque_bp.route('/saldo-estoque/api/subcategorias')
@login_required
def api_subcategorias():
    """API para obter valores únicos de subcategorias para filtros"""
    try:
        # Buscar valores únicos de cada campo
        categorias = db.session.query(CadastroPalletizacao.categoria_produto).distinct().filter(
            CadastroPalletizacao.categoria_produto.isnot(None)
        ).order_by(CadastroPalletizacao.categoria_produto).all()
        categorias = [c[0] for c in categorias if c[0]]
        
        embalagens = db.session.query(CadastroPalletizacao.tipo_embalagem).distinct().filter(
            CadastroPalletizacao.tipo_embalagem.isnot(None)
        ).order_by(CadastroPalletizacao.tipo_embalagem).all()
        embalagens = [e[0] for e in embalagens if e[0]]
        
        materias_primas = db.session.query(CadastroPalletizacao.tipo_materia_prima).distinct().filter(
            CadastroPalletizacao.tipo_materia_prima.isnot(None)
        ).order_by(CadastroPalletizacao.tipo_materia_prima).all()
        materias_primas = [m[0] for m in materias_primas if m[0]]
        
        linhas_producao = db.session.query(CadastroPalletizacao.linha_producao).distinct().filter(
            CadastroPalletizacao.linha_producao.isnot(None)
        ).order_by(CadastroPalletizacao.linha_producao).all()
        linhas_producao = [linha[0] for linha in linhas_producao if linha[0]]
        
        return jsonify({
            'success': True,
            'categorias': categorias,
            'embalagens': embalagens,
            'materias_primas': materias_primas,
            'linhas_producao': linhas_producao
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar subcategorias: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estoque_bp.route('/api/cardex/<cod_produto>/pedidos-previstos')
@login_required
def api_pedidos_previstos_cardex(cod_produto):
    """API para buscar pedidos previstos para consumo do produto com detalhes por dia"""
    try:
        # Importar modelos necessários
        from app.separacao.models import Separacao
        from app.estoque.models import UnificacaoCodigos

        # Obter códigos unificados
        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(str(cod_produto))

        # Buscar pedidos dos próximos 28 dias
        hoje = datetime.now().date()
        data_limite = hoje + timedelta(days=28)

        # Buscar pedidos da Separacao que não foram sincronizados (projeção de saída)
        pedidos_query = db.session.query(
            Separacao.expedicao,
            Separacao.num_pedido,
            Separacao.pedido_cliente,
            Separacao.cnpj_cpf,
            Separacao.raz_social_red,
            Separacao.nome_cidade,
            Separacao.cod_uf,
            Separacao.qtd_saldo,
            Separacao.status,
            Separacao.agendamento,
            Separacao.protocolo,
            Separacao.observ_ped_1,
            Separacao.rota,
            Separacao.sub_rota
        ).filter(
            Separacao.cod_produto.in_(codigos_relacionados),
            Separacao.sincronizado_nf == False,  # Apenas não sincronizados
            Separacao.status != 'CANCELADO',  # Não cancelados
            Separacao.expedicao >= hoje,
            Separacao.expedicao <= data_limite
        ).order_by(
            Separacao.expedicao,
            Separacao.num_pedido
        ).all()

        # Agrupar pedidos por data
        pedidos_por_data = {}
        total_geral = 0

        for pedido in pedidos_query:
            data_str = pedido.expedicao.strftime('%Y-%m-%d') if pedido.expedicao else 'Sem data'

            if data_str not in pedidos_por_data:
                pedidos_por_data[data_str] = {
                    'data': data_str,
                    'dia_semana': pedido.expedicao.strftime('%A').capitalize() if pedido.expedicao else '',
                    'pedidos': [],
                    'total_quantidade': 0,
                    'total_pedidos': 0
                }

            # Adicionar pedido ao dia
            pedidos_por_data[data_str]['pedidos'].append({
                'num_pedido': pedido.num_pedido,
                'pedido_cliente': pedido.pedido_cliente or '-',
                'cliente': pedido.raz_social_red or 'Cliente não identificado',
                'cnpj': pedido.cnpj_cpf,
                'cidade': pedido.nome_cidade,
                'uf': pedido.cod_uf,
                'quantidade': float(pedido.qtd_saldo or 0),
                'status': pedido.status,
                'agendamento': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                'protocolo': pedido.protocolo or '',
                'observacoes': pedido.observ_ped_1 or '',
                'rota': f"{pedido.rota or ''}{' / ' + pedido.sub_rota if pedido.sub_rota else ''}"
            })

            pedidos_por_data[data_str]['total_quantidade'] += float(pedido.qtd_saldo or 0)
            pedidos_por_data[data_str]['total_pedidos'] += 1
            total_geral += float(pedido.qtd_saldo or 0)

        # Converter para lista ordenada
        resultado = list(pedidos_por_data.values())
        resultado.sort(key=lambda x: x['data'])

        # Adicionar numeração de dias (D+0, D+1, etc)
        for idx, dia in enumerate(resultado):
            dias_diff = (datetime.strptime(dia['data'], '%Y-%m-%d').date() - hoje).days if dia['data'] != 'Sem data' else -1
            dia['dia_label'] = f"D+{dias_diff}" if dias_diff >= 0 else "Sem data"

        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'total_geral': total_geral,
            'total_dias_com_pedidos': len(resultado),
            'total_pedidos': sum(d['total_pedidos'] for d in resultado),
            'dados': resultado
        })

    except Exception as e:
        logger.error(f"Erro ao buscar pedidos previstos para {cod_produto}: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500