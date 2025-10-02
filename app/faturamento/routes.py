import os
import pandas as pd
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
from app.embarques.models import EmbarqueItem, Embarque
from app.fretes.routes import validar_cnpj_embarque_faturamento
from app.monitoramento.models import EntregaMonitorada
from datetime import datetime
from sqlalchemy import func

faturamento_bp = Blueprint('faturamento', __name__,url_prefix='/faturamento')

# Pasta para compatibilidade com arquivos antigos
UPLOAD_FOLDER = 'uploads/faturamento'
ALLOWED_EXTENSIONS = {'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def revalidar_embarques_pendentes(nfs_importadas):
    """
    Re-valida embarques que tinham NFs pendentes e agora podem ser validadas
    """
    
    print(f"\n🔄 RE-VALIDANDO EMBARQUES PENDENTES após importação de {len(nfs_importadas)} NFs")
    
    # Busca todos os itens de embarque com status pendente
    itens_pendentes = EmbarqueItem.query.filter(
        EmbarqueItem.erro_validacao.like('%NF_PENDENTE_FATURAMENTO%')
    ).all()
    
    embarques_revalidados = set()
    itens_corrigidos = 0
    
    for item in itens_pendentes:
        if item.nota_fiscal in nfs_importadas:
            embarques_revalidados.add(item.embarque_id)
    
    # Re-valida os embarques que tinham NFs importadas
    for embarque_id in embarques_revalidados:
        try:
            sucesso, resultado = validar_cnpj_embarque_faturamento(embarque_id)
            print(f"📦 Embarque {embarque_id}: {resultado}")
            if not sucesso and "NF_DIVERGENTE" in resultado:
                itens_corrigidos += 1
        except Exception as e:
            print(f"❌ Erro ao re-validar embarque {embarque_id}: {e}")
    
    if embarques_revalidados:
        db.session.commit()
        print(f"✅ {len(embarques_revalidados)} embarques re-validados, {itens_corrigidos} NFs divergentes corrigidas")
        return f"{len(embarques_revalidados)} embarques re-validados após importação"
    
    return None

# ===== ROTA DE IMPORTAÇÃO REMOVIDA =====
# Esta funcionalidade foi removida conforme solicitação do usuário  
# O sistema agora usa apenas sincronização via Odoo

@faturamento_bp.route('/sincronizar-orphas')
@login_required
def sincronizar_orphas():
    """Sincroniza NFs órfãs - ROTA SIMPLES PARA USO ÚNICO"""
    try:
        
        # Busca NFs do faturamento
        nfs_faturamento = RelatorioFaturamentoImportado.query.all()
        nfs_fat_set = {nf.numero_nf for nf in nfs_faturamento}
        
        # Busca NFs do monitoramento
        nfs_monitoramento = EntregaMonitorada.query.all()
        nfs_mon_set = {nf.numero_nf for nf in nfs_monitoramento}
        
        # Identifica órfãs
        nfs_orphas = nfs_fat_set - nfs_mon_set
        
        if not nfs_orphas:
            flash('✅ Todas as NFs já estão sincronizadas!', 'success')
            return redirect(url_for('faturamento.listar_relatorios'))
        
        # Sincroniza as órfãs
        sucesso = 0
        erros = 0
        
        for numero_nf in nfs_orphas:
            try:
                sincronizar_entrega_por_nf(numero_nf)
                sucesso += 1
            except Exception as e:
                print(f"Erro ao sincronizar NF {numero_nf}: {e}")
                erros += 1
        
        db.session.commit()
        
        # Mensagem de resultado
        if sucesso > 0:
            flash(f'✅ Sincronização concluída! {sucesso} NFs sincronizadas com sucesso!', 'success')
        
        if erros > 0:
            flash(f'⚠️ {erros} NFs tiveram erro na sincronização (verifique os logs)', 'warning')
        
        # Redireciona para monitoramento para ver resultado
        return redirect(url_for('monitoramento.listar_entregas'))
        
    except Exception as e:
        flash(f'❌ Erro durante sincronização: {str(e)}', 'danger')
        return redirect(url_for('faturamento.listar_relatorios'))

@faturamento_bp.route('/listar', methods=['GET'])
def listar_relatorios():
    query = RelatorioFaturamentoImportado.query

    # 1) Filtros:
    # 🆕 FILTRO DE STATUS (padrão: apenas ativas)
    mostrar_inativas = request.args.get('mostrar_inativas', 'false').lower() == 'true'
    if not mostrar_inativas:
        query = query.filter(RelatorioFaturamentoImportado.ativo == True)
    
    if numero_nf := request.args.get('numero_nf'):
        query = query.filter(RelatorioFaturamentoImportado.numero_nf.ilike(f"%{numero_nf}%"))
    if cnpj_cliente := request.args.get('cnpj_cliente'):
        query = query.filter(RelatorioFaturamentoImportado.cnpj_cliente.ilike(f"%{cnpj_cliente}%"))
    if nome_cliente := request.args.get('nome_cliente'):
        query = query.filter(RelatorioFaturamentoImportado.nome_cliente.ilike(f"%{nome_cliente}%"))
    if vendedor := request.args.get('vendedor'):
        query = query.filter(RelatorioFaturamentoImportado.vendedor.ilike(f"%{vendedor}%"))
    
    # 🆕 NOVOS FILTROS SOLICITADOS
    if incoterm := request.args.get('incoterm'):
        query = query.filter(RelatorioFaturamentoImportado.incoterm.ilike(f"%{incoterm}%"))
    if origem := request.args.get('origem'):
        query = query.filter(RelatorioFaturamentoImportado.origem.ilike(f"%{origem}%"))
    
    # 🆕 FILTROS DE DATA (DE/ATÉ)
    if data_de := request.args.get('data_de'):
        try:
            data_de_parsed = datetime.strptime(data_de, '%Y-%m-%d').date()
            query = query.filter(RelatorioFaturamentoImportado.data_fatura >= data_de_parsed)
        except ValueError:
            pass
    
    if data_ate := request.args.get('data_ate'):
        try:
            data_ate_parsed = datetime.strptime(data_ate, '%Y-%m-%d').date()
            query = query.filter(RelatorioFaturamentoImportado.data_fatura <= data_ate_parsed)
        except ValueError:
            pass

    # 2) Descobrir qual coluna e direção de ordenação
    sort = request.args.get('sort', 'data_fatura')      # padrão
    direction = request.args.get('direction', 'desc')   # padrão

    # 3) Definir mapa de colunas ordenáveis
    sortable_columns = {
        'numero_nf': RelatorioFaturamentoImportado.numero_nf,
        'origem': RelatorioFaturamentoImportado.origem,
        'cnpj_cliente': RelatorioFaturamentoImportado.cnpj_cliente,
        'data_fatura': RelatorioFaturamentoImportado.data_fatura,
        'nome_cliente': RelatorioFaturamentoImportado.nome_cliente,
        'valor_total': RelatorioFaturamentoImportado.valor_total,
        'nome_transportadora': RelatorioFaturamentoImportado.nome_transportadora,
        'municipio': RelatorioFaturamentoImportado.municipio,
        'estado': RelatorioFaturamentoImportado.estado,
        'incoterm': RelatorioFaturamentoImportado.incoterm,
        'vendedor': RelatorioFaturamentoImportado.vendedor,
    }

    # 4) Aplicar .order_by() caso o sort seja válido
    if sort in sortable_columns:
        coluna = sortable_columns[sort]
        if direction == 'desc':
            coluna = coluna.desc()
        query = query.order_by(coluna)
    else:
        # Se não houver, ordena por data_fatura desc (exemplo)
        query = query.order_by(RelatorioFaturamentoImportado.data_fatura.desc())

    # 5) Paginação
    page = request.args.get('page', 1, type=int)
    per_page = 20
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # 6) Buscar valores únicos para os filtros dropdown (apenas Incoterm)
    incoterms_unicos = db.session.query(RelatorioFaturamentoImportado.incoterm).distinct().filter(
        RelatorioFaturamentoImportado.incoterm.isnot(None),
        RelatorioFaturamentoImportado.incoterm != ''
    ).order_by(RelatorioFaturamentoImportado.incoterm).all()
    incoterms_list = [item[0] for item in incoterms_unicos if item[0]]

    # 7) Render
    return render_template(
        'faturamento/listar_relatorios.html',
        relatorios=paginacao.items,
        paginacao=paginacao,
        sort=sort,
        direction=direction,
        mostrar_inativas=mostrar_inativas,
        incoterms_list=incoterms_list,
    )

def sincronizar_nfs_pendentes_embarques(nfs_importadas):
    """
    ✅ CORREÇÃO: Sincroniza NFs que estão em embarques mas não estavam no monitoramento
    
    Esta função resolve o problema de NFs que foram:
    1. Adicionadas ao embarque ANTES de serem importadas no faturamento
    2. Não foram sincronizadas automaticamente porque não existiam no faturamento na época
    3. Agora que foram importadas, precisam ser sincronizadas retroativamente
    
    Args:
        nfs_importadas (list): Lista das NFs que acabaram de ser importadas
    
    Returns:
        int: Número de NFs de embarques que foram sincronizadas
    """
    
    try:
        print(f"[DEBUG] 🔍 Buscando NFs de embarques que precisam ser sincronizadas...")
        
        # ✅ CORREÇÃO: Tratamento robusto de transação para evitar InFailedSqlTransaction
        try:
            # Busca TODAS as NFs que estão em embarques ativos
            nfs_em_embarques = db.session.query(EmbarqueItem.nota_fiscal).filter(
                EmbarqueItem.nota_fiscal.isnot(None),
                EmbarqueItem.nota_fiscal != '',
                EmbarqueItem.status == 'ativo'
            ).join(Embarque).filter(
                Embarque.status == 'ativo'
            ).distinct().all()
            
            nfs_em_embarques_set = {nf[0] for nf in nfs_em_embarques}
            print(f"[DEBUG] 📦 Total de NFs únicas em embarques ativos: {len(nfs_em_embarques_set)}")
            
        except Exception as e:
            print(f"[DEBUG] ❌ Erro ao buscar NFs em embarques: {e}")
            # Força rollback se houver erro na consulta
            try:
                db.session.rollback()
            except Exception:
                pass
            return 0
        
        try:
            # Busca NFs que JÁ estão no monitoramento
            nfs_no_monitoramento = db.session.query(EntregaMonitorada.numero_nf).distinct().all()
            nfs_no_monitoramento_set = {nf[0] for nf in nfs_no_monitoramento}
            print(f"[DEBUG] 📊 Total de NFs no monitoramento: {len(nfs_no_monitoramento_set)}")
            
        except Exception as e:
            print(f"[DEBUG] ❌ Erro ao buscar NFs no monitoramento: {e}")
            # Força rollback se houver erro na consulta
            try:
                db.session.rollback()
            except Exception:
                pass
            return 0
        
        # Calcula NFs que estão em embarques MAS NÃO estão no monitoramento
        nfs_pendentes_sincronizacao = nfs_em_embarques_set - nfs_no_monitoramento_set
        print(f"[DEBUG] ⚠️ NFs pendentes de sincronização: {len(nfs_pendentes_sincronizacao)}")
        
        if not nfs_pendentes_sincronizacao:
            print(f"[DEBUG] ✅ Todas as NFs de embarques já estão sincronizadas")
            return 0
        
        # Filtra apenas as NFs que TÊM faturamento (importadas)
        nfs_faturadas_pendentes = []
        for nf in nfs_pendentes_sincronizacao:
            try:
                fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
                if fat:
                    nfs_faturadas_pendentes.append(nf)
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao buscar faturamento para NF {nf}: {e}")
                # Força rollback se houver erro
                try:
                    db.session.rollback()
                except Exception:
                    pass
                continue
        
        print(f"[DEBUG] 🎯 NFs em embarques COM faturamento que precisam sincronizar: {len(nfs_faturadas_pendentes)}")
        
        # Sincroniza as NFs pendentes que têm faturamento
        contador_sincronizadas = 0
        for nf in nfs_faturadas_pendentes:
            try:
                print(f"[DEBUG] 🔄 Sincronizando NF de embarque: {nf}")
                sincronizar_entrega_por_nf(nf)
                contador_sincronizadas += 1
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao sincronizar NF {nf}: {e}")
                # Força rollback se houver erro
                try:
                    db.session.rollback()
                except Exception:
                    pass
        
        print(f"[DEBUG] ✅ Total de NFs de embarques sincronizadas: {contador_sincronizadas}")
        return contador_sincronizadas
        
    except Exception as e:
        print(f"[DEBUG] ❌ Erro geral na sincronização de NFs pendentes: {e}")
        # Força rollback da sessão principal se houver erro
        try:
            db.session.rollback()
        except Exception:
            pass
        return 0

@faturamento_bp.route('/inativar-nfs', methods=['POST'])
@login_required
def inativar_nfs():
    """
    🗑️ INATIVAR NFs SELECIONADAS
    
    Remove as NFs do monitoramento e marca como inativas no faturamento
    """
    try:
        nfs_selecionadas = request.form.getlist('nfs_selecionadas')
        
        if not nfs_selecionadas:
            return jsonify({
                'success': False,
                'message': 'Nenhuma NF foi selecionada!'
            }), 400
        
        # Estatísticas
        nfs_inativadas = 0
        nfs_removidas_monitoramento = 0
        erros = []
        
        
        for numero_nf in nfs_selecionadas:
            try:
                # 1. Marca NF como inativa no faturamento
                nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
                
                if nf_faturamento:
                    if nf_faturamento.ativo:  # Só inativa se estiver ativa
                        nf_faturamento.ativo = False
                        nf_faturamento.inativado_em = datetime.utcnow()
                        nf_faturamento.inativado_por = current_user.nome if current_user.is_authenticated else 'Sistema'
                        nfs_inativadas += 1
                    
                    # 2. Remove do monitoramento
                    entrega_monitorada = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
                    if entrega_monitorada:
                        db.session.delete(entrega_monitorada)
                        nfs_removidas_monitoramento += 1
                else:
                    erros.append(f"NF {numero_nf} não encontrada no faturamento")
                    
            except Exception as e:
                erros.append(f"NF {numero_nf}: {str(e)}")
        
        # Salva alterações
        db.session.commit()
        
        # Prepara mensagem de resultado
        mensagens = []
        if nfs_inativadas > 0:
            mensagens.append(f"{nfs_inativadas} NF(s) inativada(s)")
        if nfs_removidas_monitoramento > 0:
            mensagens.append(f"{nfs_removidas_monitoramento} removida(s) do monitoramento")
        if erros:
            mensagens.append(f"{len(erros)} erro(s)")
        
        sucesso = nfs_inativadas > 0
        mensagem = "Processamento concluído: " + ", ".join(mensagens)
        
        if erros and len(erros) <= 3:  # Mostra erros se poucos
            mensagem += f"\nErros: {'; '.join(erros)}"
        
        return jsonify({
            'success': sucesso,
            'message': mensagem,
            'stats': {
                'nfs_inativadas': nfs_inativadas,
                'nfs_removidas_monitoramento': nfs_removidas_monitoramento,
                'erros': len(erros)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    
# =====================================
# 🆕 ROTAS PARA FATURAMENTO POR PRODUTO
# =====================================

@faturamento_bp.route('/produtos')
@login_required
def listar_faturamento_produtos():
    """Lista faturamento detalhado por produto"""
    # Filtros
    numero_nf = request.args.get('numero_nf', '')  # Add missing numero_nf filter
    nome_cliente = request.args.get('nome_cliente', '')
    cod_produto = request.args.get('cod_produto', '')
    vendedor = request.args.get('vendedor', '')
    estado = request.args.get('estado', '')
    incoterm = request.args.get('incoterm', '')
    # FIXED: Match frontend parameter names
    data_de = request.args.get('data_inicio', '')  # Frontend sends data_inicio
    data_ate = request.args.get('data_fim', '')    # Frontend sends data_fim
    municipio = request.args.get('municipio', '')
    
    # Paginação - CORRIGIDO
    try:
        page = int(request.args.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    
    try:
        per_page = int(request.args.get('per_page', '50'))  # ✅ CONFIGURÁVEL - padrão 50
        if per_page not in [20, 50, 100, 200]:  # Limitar opções válidas
            per_page = 50
    except (ValueError, TypeError):
        per_page = 50
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if inspector.has_table('faturamento_produto'):
            # Query base - CORRIGIDO: sem filtro ativo (campo não existe)
            query = FaturamentoProduto.query
            
            # ✅ CONTAR TOTAL ANTES DOS FILTROS para baseline
            total_registros_sistema = query.count()
            
            # Aplicar filtros com logs para debug
            filtros_aplicados = []
            
            if numero_nf and numero_nf.strip():
                query = query.filter(FaturamentoProduto.numero_nf.ilike(f'%{numero_nf.strip()}%'))
                filtros_aplicados.append(f"NF: {numero_nf}")
            
            if nome_cliente and nome_cliente.strip():
                query = query.filter(FaturamentoProduto.nome_cliente.ilike(f'%{nome_cliente.strip()}%'))
                filtros_aplicados.append(f"Cliente: {nome_cliente}")
                
            if cod_produto and cod_produto.strip():
                query = query.filter(FaturamentoProduto.cod_produto.ilike(f'%{cod_produto.strip()}%'))
                filtros_aplicados.append(f"Produto: {cod_produto}")
                
            if vendedor and vendedor.strip():
                query = query.filter(FaturamentoProduto.vendedor.ilike(f'%{vendedor.strip()}%'))
                filtros_aplicados.append(f"Vendedor: {vendedor}")
                
            if estado and estado.strip():
                query = query.filter(FaturamentoProduto.estado.ilike(f'%{estado.strip()}%'))
                filtros_aplicados.append(f"Estado: {estado}")
                
            if incoterm and incoterm.strip():
                query = query.filter(FaturamentoProduto.incoterm.ilike(f'%{incoterm.strip()}%'))
                filtros_aplicados.append(f"Incoterm: {incoterm}")
                
            if municipio and municipio.strip():
                query = query.filter(FaturamentoProduto.municipio.ilike(f'%{municipio.strip()}%'))
                filtros_aplicados.append(f"Município: {municipio}")
            
            # Log dos filtros aplicados
            if filtros_aplicados:
                print(f"DEBUG: Filtros aplicados: {', '.join(filtros_aplicados)}")

            # Filtros de data
            if data_de:
                try:
                    data_de_obj = datetime.strptime(data_de, '%Y-%m-%d').date()
                    query = query.filter(FaturamentoProduto.data_fatura >= data_de_obj)
                except ValueError:
                    pass
                    
            if data_ate:
                try:
                    data_ate_obj = datetime.strptime(data_ate, '%Y-%m-%d').date()
                    query = query.filter(FaturamentoProduto.data_fatura <= data_ate_obj)
                except ValueError:
                    pass
            
            # ✅ CONTAR REGISTROS APÓS FILTROS
            total_registros_filtrados = query.count()
            
            # Ordenação e paginação
            faturamentos = query.order_by(FaturamentoProduto.data_fatura.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # ✅ ESTATÍSTICAS DO MÊS CORRENTE (não baseadas nos filtros)
            from datetime import date
            mes_atual = date.today().replace(day=1)  # Primeiro dia do mês atual
            
            query_mes_atual = FaturamentoProduto.query.filter(
                FaturamentoProduto.data_fatura >= mes_atual
            )
            
            total_valor_faturado = query_mes_atual.with_entities(func.sum(FaturamentoProduto.valor_produto_faturado)).scalar() or 0
            total_quantidade = query_mes_atual.with_entities(func.sum(FaturamentoProduto.qtd_produto_faturado)).scalar() or 0
            total_peso = query_mes_atual.with_entities(func.sum(FaturamentoProduto.peso_total)).scalar() or 0
            produtos_unicos = query_mes_atual.with_entities(FaturamentoProduto.cod_produto).distinct().count()
            
            # Buscar opções dos filtros
            opcoes_estados = sorted(set(
                f.estado for f in FaturamentoProduto.query.with_entities(FaturamentoProduto.estado).distinct() 
                if f.estado and f.estado.strip()
            ))
            
            opcoes_incoterms = sorted(set(
                f.incoterm for f in FaturamentoProduto.query.with_entities(FaturamentoProduto.incoterm).distinct() 
                if f.incoterm and f.incoterm.strip()
            ))
            
            opcoes_vendedores = sorted(set(
                f.vendedor for f in FaturamentoProduto.query.with_entities(FaturamentoProduto.vendedor).distinct() 
                if f.vendedor and f.vendedor.strip()
            ))
        else:
            faturamentos = None
            total_registros_sistema = 0
            total_registros_filtrados = 0
            total_valor_faturado = 0
            total_quantidade = 0
            total_peso = 0  # Add missing total_peso
            produtos_unicos = 0
            opcoes_estados = []
            opcoes_incoterms = []
            opcoes_vendedores = []
            from datetime import date
            mes_atual = date.today().replace(day=1)  # Initialize mes_atual for empty case
    except Exception:
        faturamentos = None
        total_registros_sistema = 0
        total_registros_filtrados = 0
        total_valor_faturado = 0
        total_quantidade = 0
        total_peso = 0  # Add missing total_peso
        produtos_unicos = 0
        opcoes_estados = []
        opcoes_incoterms = []
        opcoes_vendedores = []
        from datetime import date
        mes_atual = date.today().replace(day=1)  # Initialize mes_atual for error case
    
    return render_template('faturamento/listar_produtos.html',
                        produtos=faturamentos,
                        pagination=faturamentos,
                        total_registros_sistema=total_registros_sistema,
                        total_registros_filtrados=total_registros_filtrados,
                        total_valor_faturado=total_valor_faturado,
                        total_quantidade=total_quantidade,
                        total_peso=total_peso,
                        produtos_unicos=produtos_unicos,
                        mes_atual=mes_atual.strftime('%m/%Y'),
                        # FIXED: Match frontend variable names
                        ufs_disponiveis=opcoes_estados,
                        incoterms_disponiveis=opcoes_incoterms,
                        vendedores_disponiveis=opcoes_vendedores,
                        per_page=per_page,  # Add per_page to template context
                        filtros={
                            'numero_nf': numero_nf,       # Add numero_nf to filters
                            'nome_cliente': nome_cliente,
                            'cod_produto': cod_produto,
                            'vendedor': vendedor,
                            'estado': estado,
                            'incoterm': incoterm,
                            'data_inicio': data_de,   # Keep frontend naming
                            'data_fim': data_ate,     # Keep frontend naming
                            'municipio': municipio
                        })

@faturamento_bp.route('/produtos/api/estatisticas')
@login_required
def api_estatisticas_produtos():
    """API para estatísticas do faturamento por produto"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        # Estatísticas básicas
        stats = {
            'total_produtos': db.session.query(FaturamentoProduto.cod_produto).distinct().count(),
            'total_nfs': db.session.query(FaturamentoProduto.numero_nf).distinct().count(),
            'total_clientes': db.session.query(FaturamentoProduto.cnpj_cliente).distinct().count(),
            'valor_total': db.session.query(func.sum(FaturamentoProduto.valor_produto_faturado)).scalar() or 0
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@faturamento_bp.route('/produtos/exportar-dados')
@login_required 
def exportar_dados_faturamento():
    """Exportar dados existentes de faturamento por produto"""
    try:
        from flask import make_response
        from io import BytesIO
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('faturamento_produto'):
            produtos = FaturamentoProduto.query.order_by(
                FaturamentoProduto.numero_nf.desc()
            ).all()
        else:
            produtos = []
        
        if not produtos:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('faturamento.listar_faturamento_produtos'))
        
        # Converter para formato Excel com colunas exatas
        dados_export = []
        for p in produtos:
            dados_export.append({
                'Linhas da fatura/NF-e': p.numero_nf,
                'Linhas da fatura/Parceiro/CNPJ': p.cnpj_cliente,
                'Linhas da fatura/Parceiro': p.nome_cliente,
                'Linhas da fatura/Parceiro/Município': f"{p.municipio} ({p.estado})" if p.municipio and p.estado else p.municipio,
                'Linhas da fatura/Produto/Referência': p.cod_produto,
                'Linhas da fatura/Produto/Nome': p.nome_produto,
                'Linhas da fatura/Quantidade': p.qtd_produto_faturado,
                'Peso Unitário (kg)': p.peso_unitario_produto if p.peso_unitario_produto else 0,
                'Peso Total (kg)': p.peso_total if p.peso_total else 0,
                'Linhas da fatura/Valor Total do Item da NF': f"{p.valor_produto_faturado:,.2f}".replace('.', ',').replace(',', '.', 1),
                'Linhas da fatura/Data': p.data_fatura.strftime('%d/%m/%Y') if p.data_fatura else '',
                'Status': getattr(p, 'status_nf', ''),
                'Vendedor': p.vendedor,
                'Incoterm': p.incoterm
            })
        
        df = pd.DataFrame(dados_export)
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Faturamento Produto', index=False)
            
            # Aba de estatísticas
            stats = pd.DataFrame({
                'Estatística': ['Total de Registros', 'NFs Únicas', 'Produtos Únicos', 'Total Valor'],
                'Valor': [
                    len(produtos),
                    len(set(p.numero_nf for p in produtos)),
                    len(set(p.cod_produto for p in produtos)), 
                    f"R$ {sum(p.valor_produto_faturado for p in produtos):,.2f}"
                ]
            })
            stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        output.seek(0)
        
        # Criar resposta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=faturamento_produto_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('faturamento.listar_faturamento_produtos'))

# =====================================
# 🆕 ROTAS PARA SISTEMA INTEGRADO DE FATURAMENTO
# =====================================

@faturamento_bp.route('/')
@faturamento_bp.route('/dashboard')
@login_required
def dashboard_faturamento():
    """Dashboard principal do faturamento integrado"""
    try:
        from datetime import date
        from sqlalchemy import func
        
        # Calcular estatísticas do mês atual
        mes_atual = date.today().replace(day=1)
        
        # NFs faturadas no mês
        nfs_faturadas_mes = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.data_fatura >= mes_atual,
            RelatorioFaturamentoImportado.ativo == True
        ).count()
        
        # Valor faturado no mês
        valor_faturado_mes = db.session.query(
            func.sum(RelatorioFaturamentoImportado.valor_total)
        ).filter(
            RelatorioFaturamentoImportado.data_fatura >= mes_atual,
            RelatorioFaturamentoImportado.ativo == True
        ).scalar() or 0
        
        # Quantidade de itens faturados no mês (soma das quantidades)
        qtd_itens_faturados_mes = 0
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            if inspector.has_table('faturamento_produto'):
                resultado = db.session.query(
                    func.sum(FaturamentoProduto.qtd_produto_faturado)
                ).filter(
                    FaturamentoProduto.data_fatura >= mes_atual
                ).scalar()
                
                qtd_itens_faturados_mes = float(resultado) if resultado else 0
                print(f"[DEBUG] Qtd itens faturados: {qtd_itens_faturados_mes}")
        except Exception as e:
            print(f"[DEBUG] Erro ao calcular itens faturados: {e}")
            qtd_itens_faturados_mes = 0
        
        # Última sincronização do Odoo
        ultima_sincronizacao = "Nunca"
        ultima_nf = RelatorioFaturamentoImportado.query.order_by(
            RelatorioFaturamentoImportado.criado_em.desc()
        ).first()
        if ultima_nf and ultima_nf.criado_em:
            ultima_sincronizacao = ultima_nf.criado_em.strftime('%d/%m/%Y %H:%M')
        
        # Logs de atividade recentes
        logs_atividade = [
            {
                'timestamp': '18/07/2025 15:30',
                'mensagem': 'Sistema iniciado com sucesso',
                'tipo': 'info',
                'usuario': current_user.nome
            }
        ]
        
        # Formatar valor em padrão brasileiro
        from app.utils.valores_brasileiros import formatar_valor_brasileiro
        valor_faturado_mes_formatado = formatar_valor_brasileiro(valor_faturado_mes)
        
        # Formatar quantidade como número inteiro com separador de milhar
        qtd_itens_formatada = f"{int(qtd_itens_faturados_mes):,.0f}".replace(',', '.')
        
        # Formatar NFs faturadas com separador de milhar
        nfs_faturadas_formatada = f"{nfs_faturadas_mes:,.0f}".replace(',', '.')
        
        return render_template('faturamento/dashboard_faturamento.html',
                             nfs_faturadas_mes=nfs_faturadas_formatada,
                             qtd_itens_faturados_mes=qtd_itens_formatada,
                             valor_faturado_mes=valor_faturado_mes_formatado,
                             ultima_sincronizacao=ultima_sincronizacao,
                             logs_atividade=logs_atividade)
        
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('faturamento.listar_relatorios'))

@faturamento_bp.route('/cancelar-nf-devolvida', methods=['POST'])
@login_required
def cancelar_nf_devolvida():
    """
    Cancela NF devolvida - marca como Cancelado e reverte estoque

    Comporta-se exatamente como uma NF cancelada pelo Odoo, mas para devoluções manuais
    """
    try:
        # Verificar se é admin
        if current_user.perfil != 'administrador':
            return jsonify({
                'success': False,
                'message': 'Apenas administradores podem cancelar NFs'
            }), 403

        numero_nf = request.form.get('numero_nf')
        origem = request.form.get('origem')  # Número do pedido

        if not numero_nf:
            return jsonify({
                'success': False,
                'message': 'Número da NF é obrigatório'
            }), 400

        # Importar modelos necessários
        from app.estoque.models import MovimentacaoEstoque

        # Estatísticas para resposta
        produtos_cancelados = 0
        movimentacoes_revertidas = 0

        # 1. Marcar todos os produtos da NF como Cancelado em FaturamentoProduto
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()

        if not produtos_nf:
            return jsonify({
                'success': False,
                'message': f'Nenhum produto encontrado para a NF {numero_nf}'
            }), 404

        for produto in produtos_nf:
            if produto.status_nf != 'Cancelado':
                produto.status_nf = 'Cancelado'
                produto.updated_at = datetime.now()
                produto.updated_by = f'Cancelamento Manual - {current_user.nome}'
                produtos_cancelados += 1

        # 2. Marcar movimentações de estoque como inativas (reverte o estoque)
        movimentacoes = MovimentacaoEstoque.query.filter_by(
            numero_nf=numero_nf,
            ativo=True  # Apenas movimentações ativas
        ).all()

        for mov in movimentacoes:
            # Marcar como inativa para reverter o estoque
            mov.ativo = False
            mov.status_nf = 'CANCELADO'
            mov.atualizado_em = datetime.now()
            mov.atualizado_por = f'Cancelamento Manual - {current_user.nome}'
            mov.observacao = f'{mov.observacao or ""} | NF Devolvida - Cancelada manualmente em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            movimentacoes_revertidas += 1

        # 3. Marcar RelatorioFaturamentoImportado como inativo também
        relatorio_nf = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
        if relatorio_nf and relatorio_nf.ativo:
            relatorio_nf.ativo = False
            relatorio_nf.inativado_em = datetime.now()
            relatorio_nf.inativado_por = f'Cancelamento Manual - {current_user.nome}'

        # Salvar todas as alterações
        db.session.commit()

        # Preparar mensagem de resposta
        mensagem_detalhes = []
        if produtos_cancelados > 0:
            mensagem_detalhes.append(f'{produtos_cancelados} produtos marcados como cancelados')
        if movimentacoes_revertidas > 0:
            mensagem_detalhes.append(f'{movimentacoes_revertidas} movimentações revertidas')

        mensagem = f'NF {numero_nf} cancelada com sucesso! ' + ', '.join(mensagem_detalhes)

        return jsonify({
            'success': True,
            'message': mensagem,
            'detalhes': {
                'produtos_cancelados': produtos_cancelados,
                'movimentacoes_revertidas': movimentacoes_revertidas
            },
            'recarregar': True  # Solicitar recarga da página para atualizar a lista
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar NF: {str(e)}'
        }), 500

@faturamento_bp.route('/dashboard-reconciliacao')
@login_required
def dashboard_reconciliacao():
    """Dashboard de reconciliação - visualizar inconsistências"""
    try:
        # Importar o serviço de reconciliação (movido para faturamento)
        from app.faturamento.services.reconciliacao_service import ReconciliacaoService
        
        # Executar análise de inconsistências
        reconciliacao = ReconciliacaoService()
        inconsistencias = reconciliacao.identificar_inconsistencias()
        
        return render_template('faturamento/dashboard_reconciliacao.html',
                             inconsistencias=inconsistencias)
        
    except Exception as e:
        flash(f'Erro ao carregar dashboard de reconciliação: {str(e)}', 'error')
        return redirect(url_for('faturamento.dashboard_faturamento'))

@faturamento_bp.route('/conciliacao-manual')
@login_required
def tela_conciliacao_manual():
    """Tela para conciliação manual de inconsistências"""
    try:
        # Filtros da URL
        tipo = request.args.get('tipo', '')
        numero = request.args.get('numero', '')
        cliente = request.args.get('cliente', '')
        produto = request.args.get('produto', '')
        
        # Importar o serviço de reconciliação
        from app.faturamento.services.reconciliacao_service import ReconciliacaoService
        
        reconciliacao = ReconciliacaoService()
        inconsistencias_raw = reconciliacao.identificar_inconsistencias()
        
        # Converter para formato unificado para a tela
        inconsistencias = []
        
        # NFs órfãs
        if not tipo or tipo == 'nfs_orfas':
            for nf in inconsistencias_raw.get('nfs_orfas', []):
                # Converter objeto para dict antes do filtro
                nf_dict = {
                    'numero_nf': nf.get('numero_nf', ''),
                    'nome_cliente': nf.get('nome_cliente', ''),
                    'cod_produto': ''  # NFs órfãs não têm produto específico
                }
                if _filtrar_item(nf_dict, numero, cliente, produto):
                    inconsistencias.append({
                        'id': f"nf_{nf['numero_nf']}",
                        'tipo': 'nf_orfa',
                        'numero_nf': nf['numero_nf'],
                        'nome_cliente': nf['nome_cliente'],
                        'municipio': nf.get('municipio', ''),
                        'estado': nf.get('estado', ''),
                        'data_fatura': nf.get('data_fatura'),
                        'valor_total': nf.get('valor_total'),
                        'origem': nf.get('origem', ''),
                        'resolvido': False
                    })
        
        # Separações órfãs
        if not tipo or tipo == 'separacoes_orfas':
            for sep in inconsistencias_raw.get('separacoes_sem_nf', []):
                # Converter objeto para dict antes do filtro
                sep_dict = {
                    'numero_nf': '',  # Separações órfãs não têm NF
                    'nome_cliente': '',  # Não disponível na separação
                    'cod_produto': sep.get('cod_produto', '')
                }
                if _filtrar_item(sep_dict, numero, cliente, produto):
                    inconsistencias.append({
                        'id': f"sep_{sep['lote_id']}",
                        'tipo': 'separacao_orfa',
                        'lote_separacao': sep['lote_id'],
                        'cod_produto': sep.get('cod_produto', ''),
                        'nome_produto': sep.get('nome_produto', ''),
                        'cliente': sep.get('cliente', ''),
                        'qtd_separada': sep.get('qtd_saldo', 0),
                        'valor_separado': 0,  # Não disponível na separação
                        'data_separacao': sep.get('data_separacao'),
                        'resolvido': False
                    })
        
        # Divergências de valor (por enquanto vazio - implementar quando necessário)
        if not tipo or tipo == 'divergencias_valor':
            for div in inconsistencias_raw.get('divergencias_quantidade', []):
                div_dict = {
                    'numero_nf': div.get('numero_nf', ''),
                    'nome_cliente': div.get('nome_cliente', ''),
                    'cod_produto': div.get('cod_produto', '')
                }
                if _filtrar_item(div_dict, numero, cliente, produto):
                    inconsistencias.append({
                        'id': f"div_{div.get('id', '')}",
                        'tipo': 'divergencia_valor',
                        'numero_nf': div.get('numero_nf', ''),
                        'cod_produto': div.get('cod_produto', ''),
                        'nome_produto': div.get('nome_produto', ''),
                        'nome_cliente': div.get('nome_cliente', ''),
                        'valor_divergencia': div.get('valor_divergencia', 0),
                        'resolvido': False
                    })
        
        # Divergências de quantidade
        if not tipo or tipo == 'divergencias_quantidade':
            for div in inconsistencias_raw.get('divergencias_quantidade', []):
                if _filtrar_item(div, numero, cliente, produto):
                    inconsistencias.append({
                        'id': f"div_qtd_{div.numero_nf}_{div.cod_produto}",
                        'tipo': 'divergencia_quantidade',
                        'numero_nf': div.numero_nf,
                        'cod_produto': div.cod_produto,
                        'qtd_nf': getattr(div, 'qtd_nf', 0),
                        'qtd_separacao': getattr(div, 'qtd_separacao', 0),
                        'resolvido': False
                    })
        
        total_registros = len(inconsistencias)
        
        return render_template('faturamento/tela_conciliacao_manual.html',
                             inconsistencias=inconsistencias,
                             total_registros=total_registros)
        
    except Exception as e:
        flash(f'Erro ao carregar tela de conciliação: {str(e)}', 'error')
        return redirect(url_for('faturamento.dashboard_reconciliacao'))

def _filtrar_item(item, numero, cliente, produto):
    """
    Função auxiliar para filtrar itens na conciliação manual
    """
    if numero and numero.lower() not in str(item.get('numero_nf', '')).lower():
        return False
    if cliente and cliente.lower() not in str(item.get('nome_cliente', '')).lower():
        return False
    if produto and produto.lower() not in str(item.get('cod_produto', '')).lower():
        return False
    return True

@faturamento_bp.route('/justificativas-parciais')
@login_required
def justificativas_parciais():
    """Tela de justificativas de faturamento parcial"""
    try:
        # Filtros
        status = request.args.get('status', '')
        tipo = request.args.get('tipo', '')
        numero_nf = request.args.get('numero_nf', '')
        cliente = request.args.get('cliente', '')
        produto = request.args.get('produto', '')
        
        # ✅ BUSCAR DADOS REAIS do modelo FaturamentoParcialJustificativa
        from app.carteira.models import FaturamentoParcialJustificativa
        
        query = FaturamentoParcialJustificativa.query
        
        # Aplicar filtros
        if numero_nf:
            query = query.filter(FaturamentoParcialJustificativa.numero_nf.ilike(f'%{numero_nf}%'))
        if produto:
            query = query.filter(FaturamentoParcialJustificativa.cod_produto.ilike(f'%{produto}%'))
        if tipo:
            query = query.filter(FaturamentoParcialJustificativa.motivo_nao_faturamento == tipo)
        
        justificativas_raw = query.order_by(FaturamentoParcialJustificativa.criado_em.desc()).limit(50).all()
        
        # ✅ CONVERTER para formato compatível com template
        justificativas = []
        for just in justificativas_raw:
            # ✅ CORRETO: Buscar dados do produto em FaturamentoProduto (tem cod_produto + dados cliente)
            produto_dados = FaturamentoProduto.query.filter_by(
                numero_nf=just.numero_nf,
                cod_produto=just.cod_produto
            ).first()
            
            # ✅ USAR separacao_lote_id para buscar dados da separação
            separacao_dados = None
            if just.separacao_lote_id:
                from app.separacao.models import Separacao
                separacao_dados = Separacao.query.filter_by(
                    separacao_lote_id=just.separacao_lote_id,
                    cod_produto=just.cod_produto
                ).first()
            
            justificativa_convertida = {
                'id': just.id,
                'numero_nf': just.numero_nf,
                'cod_produto': just.cod_produto,
                'qtd_separada': float(just.qtd_separada or 0),
                'qtd_faturada': float(just.qtd_faturada or 0),
                'qtd_saldo': float(just.qtd_saldo or 0),
                'justificativa': just.descricao_detalhada or 'Sem descrição',
                'motivo_automatico': just.motivo_nao_faturamento,
                'data_criacao': just.criado_em,
                'aprovado_por': just.criado_por,
                'classificacao_saldo': just.classificacao_saldo,
                'acao_comercial': just.acao_comercial,
                'separacao_lote_id': just.separacao_lote_id,  # ✅ ADICIONAR campo importante
                # Campos calculados/derivados
                'tipo_divergencia': 'quantidade',  # Sempre quantidade para parciais
                'status': 'justificado' if just.acao_comercial else 'pendente',
                'automatico': True,  # Justificativas automáticas
                # ✅ CORRETO: Dados do cliente via FaturamentoProduto
                'nome_cliente': produto_dados.nome_cliente if produto_dados else 'Cliente não encontrado',
                'municipio': produto_dados.municipio if produto_dados else '',
                'estado': produto_dados.estado if produto_dados else '',
                'nome_produto': produto_dados.nome_produto if produto_dados else 'Produto não encontrado',
                'origem': just.num_pedido,  # ✅ CORRETO: origem = num_pedido na justificativa
                # ✅ DADOS DA SEPARAÇÃO se disponível
                'rota': separacao_dados.rota if separacao_dados else '',
                'agendamento': separacao_dados.agendamento if separacao_dados else None,
                'protocolo': separacao_dados.protocolo if separacao_dados else ''
            }
            justificativas.append(justificativa_convertida)
        
        total_registros = len(justificativas)
        
        # Resumo para os cards - baseado em dados reais
        resumo = {
            'pendentes': len([j for j in justificativas if j['status'] == 'pendente']),
            'justificadas': len([j for j in justificativas if j['status'] == 'justificado']),
            'automaticas_mes': total_registros,  # Todas são automáticas
            'valor_total_divergencias': sum(j['qtd_saldo'] for j in justificativas)
        }
        
        return render_template('faturamento/justificativas_parciais.html',
                             justificativas=justificativas,
                             total_registros=total_registros,
                             resumo=resumo)
        
    except Exception as e:
        flash(f'Erro ao carregar justificativas: {str(e)}', 'error')
        return redirect(url_for('faturamento.dashboard_faturamento'))

@faturamento_bp.route('/status-processamento')
@login_required
def status_processamento():
    """Dashboard de status do processamento"""
    try:
        # TODO: Implementar dashboard de status
        return render_template('faturamento/status_processamento.html')
        
    except Exception as e:
        flash(f'Erro ao carregar status: {str(e)}', 'error')
        return redirect(url_for('faturamento.dashboard_faturamento'))

@faturamento_bp.route('/relatorio-auditoria')
@login_required
def relatorio_auditoria():
    """Relatório de auditoria"""
    try:
        # TODO: Implementar relatório de auditoria
        return render_template('faturamento/relatorio_auditoria.html')
        
    except Exception as e:
        flash(f'Erro ao carregar relatório: {str(e)}', 'error')
        return redirect(url_for('faturamento.dashboard_faturamento'))

# =====================================
# 🔄 APIs PARA FUNCIONALIDADES DINÂMICAS
# =====================================

@faturamento_bp.route('/api/excluir-nf/<string:numero_nf>', methods=['DELETE'])
@login_required
def api_excluir_nf(numero_nf):
    """API para excluir NF (apenas administradores)"""
    try:
        # Verificar se o usuário é administrador
        if current_user.perfil != 'administrador':
            return jsonify({
                'success': False,
                'error': 'Apenas administradores podem excluir notas fiscais'
            }), 403
        
        # Buscar a NF em RelatorioFaturamentoImportado
        nf_relatorio = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
        
        if not nf_relatorio:
            return jsonify({
                'success': False,
                'error': f'Nota fiscal {numero_nf} não encontrada'
            }), 404
        
        # Buscar e deletar todas as linhas em FaturamentoProduto
        produtos_deletados = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
        qtd_produtos = len(produtos_deletados)
        
        for produto in produtos_deletados:
            db.session.delete(produto)
        
        # Deletar a NF do RelatorioFaturamentoImportado
        db.session.delete(nf_relatorio)
        
        # Commit das alterações
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'NF {numero_nf} excluída com sucesso',
            'produtos_deletados': qtd_produtos
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erro ao excluir NF: {str(e)}'
        }), 500

@faturamento_bp.route('/api/sincronizar-odoo', methods=['POST'])
@login_required
def api_sincronizar_odoo():
    """API para sincronizar com Odoo"""
    try:
        # Importar o serviço do Odoo
        from app.odoo.services.faturamento_service import importar_faturamento_odoo
        
        # Executar importação
        resultado = importar_faturamento_odoo()
        
        if resultado.get('sucesso'):
            return jsonify({
                'success': True,
                'message': f"Sincronização concluída! {resultado.get('registros_importados', 0)} registros importados."
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('erro', 'Erro na sincronização')
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro na sincronização: {str(e)}'
        })

@faturamento_bp.route('/api/processar-pendencias', methods=['POST'])
@login_required
def api_processar_pendencias():
    """API para processar pendências automaticamente"""
    try:
        # Importar o processador
        from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
        
        processador = ProcessadorFaturamento()
        resultado = processador.processar_nfs_importadas()
        
        return jsonify({
            'success': True,
            'message': f"Processamento concluído! {resultado.get('processadas', 0)} NFs processadas."
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro no processamento: {str(e)}'
        })

@faturamento_bp.route('/api/reconciliacao-automatica', methods=['POST'])
@login_required
def api_reconciliacao_automatica():
    """API para reconciliação automática"""
    try:
        # Importar o serviço
        from app.faturamento.services.reconciliacao_service import ReconciliacaoService
        
        reconciliacao = ReconciliacaoService()
        resultado = reconciliacao.reconciliacao_automatica()
        
        return jsonify({
            'success': True,
            'resolvidas': resultado.get('resolvidas', 0),
            'message': f"Reconciliação automática concluída!"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro na reconciliação: {str(e)}'
        })

@faturamento_bp.route('/api/status-cards')
@login_required
def api_status_cards():
    """API para atualizar cards de status"""
    try:
        from datetime import date
        from sqlalchemy import func
        
        mes_atual = date.today().replace(day=1)
        
        # Recalcular estatísticas
        nfs_processadas_mes = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.criado_em >= mes_atual,
            RelatorioFaturamentoImportado.ativo == True
        ).count()
        
        nfs_pendentes = 5  # TODO: Calcular real
        
        valor_faturado_mes = 0
        try:
            if db.engine.has_table('faturamento_produto'):
                valor_faturado_mes = db.session.query(
                    func.sum(FaturamentoProduto.valor_produto_faturado)
                ).filter(
                    FaturamentoProduto.data_fatura >= mes_atual
                ).scalar() or 0
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'nfs_processadas_mes': nfs_processadas_mes,
            'nfs_pendentes': nfs_pendentes,
            'valor_faturado_mes': f"{valor_faturado_mes:,.2f}".replace('.', ',').replace(',', '.', 1),
            'ultima_sincronizacao': 'Agora mesmo'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@faturamento_bp.route('/api/exportar-inconsistencias')
@login_required
def api_exportar_inconsistencias():
    """API para exportar inconsistências em Excel"""
    try:
        # TODO: Implementar exportação
        return jsonify({
            'success': False,
            'message': 'Função em desenvolvimento'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })
