import os
import pandas as pd
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.faturamento.forms import UploadRelatorioForm  # certifique-se de que o caminho está correto
from app.utils.helpers import limpar_valor
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
from app.embarques.models import EmbarqueItem, Embarque
from app.fretes.routes import validar_cnpj_embarque_faturamento
from app.monitoramento.models import EntregaMonitorada
from datetime import datetime

# 🌐 Importar sistema de arquivos S3
from app.utils.file_storage import get_file_storage

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

@faturamento_bp.route('/importar-relatorio', methods=['GET', 'POST'])
@login_required
def importar_relatorio():
    form = UploadRelatorioForm()

    if form.validate_on_submit():
        file = form.arquivo.data

        if file and file.filename.endswith('.xlsx'):
            try:
                # 📁 CORREÇÃO: Capturar filename antes de processar arquivo
                original_filename = file.filename
                
                # Ler o arquivo uma vez e usar os bytes para ambas operações
                file.seek(0)  # Garantir que está no início
                file_content = file.read()  # Ler todo o conteúdo uma vez
                
                # 🌐 Usar sistema S3 para salvar arquivo
                storage = get_file_storage()
                
                # Criar um objeto BytesIO para simular arquivo para o S3
                from io import BytesIO
                file_for_s3 = BytesIO(file_content)
                file_for_s3.name = original_filename  # Usar filename capturado
                
                file_path = storage.save_file(
                    file=file_for_s3,
                    folder='faturamento',
                    allowed_extensions=['xlsx']
                )
                
                if not file_path:
                    flash('❌ Erro ao salvar arquivo no sistema!', 'danger')
                    return redirect(request.url)
                
                # 📁 Para processamento, criar arquivo temporário dos bytes
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                    temp_file.write(file_content)  # Usar os bytes já lidos
                    temp_filepath = temp_file.name

                # Processar arquivo Excel
                df = pd.read_excel(temp_filepath)
                df = df.drop_duplicates(subset=["Número da Nota Fiscal"])

                df["Número da Nota Fiscal"] = df["Número da Nota Fiscal"].apply(
                    lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)
                )
                df["Total da Nota Fiscal"] = df["Total da Nota Fiscal"].apply(limpar_valor)
                df["Peso Bruto"] = df["Peso Bruto"].apply(limpar_valor)
                df["Data da fatura de cliente/fornecedor"] = pd.to_datetime(
                    df["Data da fatura de cliente/fornecedor"], errors='coerce'
                )

                nfs_importadas = []
                linhas_ignoradas = 0
                nfs_duplicatas = 0
                
                # 🔍 DEBUG: Mostrar colunas disponíveis no Excel
                print(f"[DEBUG] 📋 Colunas disponíveis no Excel: {list(df.columns)}")
                print(f"[DEBUG] 📊 Total de linhas no Excel: {len(df)}")

                for index, row in df.iterrows():
                    linha_num = index + 2  # +2 porque Excel começa na linha 1 e tem header
                    
                    # Validação 1: Número da NF não pode estar vazio
                    numero_nf_raw = row.get("Número da Nota Fiscal")
                    if pd.isna(numero_nf_raw) or str(numero_nf_raw).strip() == '' or str(numero_nf_raw).lower() == 'nan':
                        print(f"[DEBUG] ❌ Linha {linha_num}: NF vazia ou inválida: '{numero_nf_raw}'")
                        linhas_ignoradas += 1
                        continue
                        
                    numero_nf = str(numero_nf_raw).strip()
                    
                    # Validação 2: Origem (pedido) não pode estar vazio - campo crítico
                    origem = row.get("Origem")
                    if pd.isna(origem) or str(origem).strip() == '' or str(origem).lower() == 'nan':
                        print(f"[DEBUG] ❌ Linha {linha_num}: Origem vazia para NF {numero_nf}: '{origem}'")
                        linhas_ignoradas += 1
                        continue
                    
                    # Verifica se NF já existe
                    existe = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
                    if existe:
                        print(f"[DEBUG] ⚠️ Linha {linha_num}: NF {numero_nf} já existe no banco")
                        nfs_duplicatas += 1
                        continue
                    
                    print(f"[DEBUG] ✅ Linha {linha_num}: NF {numero_nf} será importada (Origem: {origem})")

                    nf = RelatorioFaturamentoImportado(
                        numero_nf=numero_nf,
                        data_fatura=row["Data da fatura de cliente/fornecedor"],
                        cnpj_cliente=row.get("CNPJ"),
                        nome_cliente=row.get("Nome de exibição do usuário na fatura"),
                        valor_total=row.get("Total da Nota Fiscal"),
                        peso_bruto=row.get("Peso Bruto"),
                        cnpj_transportadora=row.get("Carrier/Transportadora/CNPJ"),
                        nome_transportadora=row.get("Carrier/Transportadora"),
                        municipio=row.get("Parceiro/Município/Nome do Município"),
                        estado=row.get("Parceiro/Estado/Código do estado"),
                        codigo_ibge=row.get("Parceiro/Município/Código IBGE"),
                        origem=row.get("Origem"),
                        incoterm=row.get("Incoterm"),
                        vendedor=row.get("Usuário")
                    )
                    db.session.add(nf)
                    nfs_importadas.append(numero_nf)

                db.session.commit()
                
                # 🗑️ Remover arquivo temporário
                try:
                    os.unlink(temp_filepath)
                except OSError:
                    pass  # Ignorar se não conseguir remover

                # Re-validar embarques que estavam pendentes
                try:
                    resultado_revalidacao = revalidar_embarques_pendentes(nfs_importadas)
                    if resultado_revalidacao:
                        flash(f"🔄 {resultado_revalidacao}", "info")
                except Exception as e:
                    print(f"Erro na re-validação de embarques: {e}")

                # Lançamento automático de fretes após importar faturamento
                try:
                    from app.fretes.routes import processar_lancamento_automatico_fretes
                    
                    # Para cada CNPJ importado, tenta lançar fretes automaticamente
                    cnpjs_importados = set()
                    for _, row in df.iterrows():
                        cnpj = row.get("CNPJ")
                        if cnpj:
                            cnpjs_importados.add(cnpj)
                    
                    for cnpj in cnpjs_importados:
                        if cnpj:
                            sucesso, resultado = processar_lancamento_automatico_fretes(
                                cnpj_cliente=cnpj,
                                usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
                            )
                            if sucesso and "lançado(s) automaticamente" in resultado:
                                flash(f"✅ {resultado}", "success")
                                
                except Exception as e:
                    print(f"Erro no lançamento automático de fretes: {e}")

                # ✅ NOVA FUNCIONALIDADE: Sincroniza entregas + NFs pendentes em embarques
                nfs_sincronizadas = 0
                nfs_em_embarques_sincronizadas = 0
                
                # 1. Sincroniza NFs importadas normalmente
                for nf in nfs_importadas:
                    sincronizar_entrega_por_nf(nf)
                    nfs_sincronizadas += 1
                
                # 2. CORREÇÃO PRINCIPAL: Busca NFs que estão em embarques mas não foram sincronizadas
                try:
                    nfs_em_embarques_sincronizadas = sincronizar_nfs_pendentes_embarques(nfs_importadas)
                    if nfs_em_embarques_sincronizadas > 0:
                        flash(f"🔄 {nfs_em_embarques_sincronizadas} NFs de embarques anteriores foram sincronizadas para o monitoramento", "info")
                except Exception as e:
                    print(f"Erro ao sincronizar NFs pendentes: {e}")
                
                print(f"[DEBUG] Sincronização: {nfs_sincronizadas} NFs normais + {nfs_em_embarques_sincronizadas} NFs de embarques")
                
                # Mensagens de resultado melhoradas
                if len(nfs_importadas) > 0:
                    flash(f'✅ Relatório importado com sucesso! {len(nfs_importadas)} NFs processadas.', 'success')
                else:
                    flash(f'⚠️ Nenhuma NF foi importada! Verifique os logs para detalhes.', 'warning')
                
                flash(f'📁 Arquivo salvo no sistema de armazenamento.', 'info')
                
                if linhas_ignoradas > 0:
                    flash(f'⚠️ {linhas_ignoradas} linhas foram ignoradas (NF ou Origem vazios).', 'warning')
                
                if nfs_duplicatas > 0:
                    flash(f'🔄 {nfs_duplicatas} NFs já existiam no banco (duplicatas).', 'info')
                
                return redirect(url_for('faturamento.importar_relatorio'))

            except Exception as e:
                flash(f'❌ Erro ao processar o arquivo: {e}', 'danger')
                return redirect(request.url)

        flash('❌ Tipo de arquivo não permitido. Envie um .xlsx', 'danger')
        return redirect(request.url)

    return render_template('faturamento/importar_relatorio.html', form=form)

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
        'numero_nf':           RelatorioFaturamentoImportado.numero_nf,
        'origem':              RelatorioFaturamentoImportado.origem,
        'cnpj_cliente':        RelatorioFaturamentoImportado.cnpj_cliente,
        'data_fatura':         RelatorioFaturamentoImportado.data_fatura,
        'nome_cliente':        RelatorioFaturamentoImportado.nome_cliente,
        'valor_total':         RelatorioFaturamentoImportado.valor_total,
        'nome_transportadora': RelatorioFaturamentoImportado.nome_transportadora,
        'municipio':           RelatorioFaturamentoImportado.municipio,
        'estado':              RelatorioFaturamentoImportado.estado,
        'incoterm':            RelatorioFaturamentoImportado.incoterm,
        'vendedor':            RelatorioFaturamentoImportado.vendedor,
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
        
        # Busca NFs que JÁ estão no monitoramento
        nfs_no_monitoramento = db.session.query(EntregaMonitorada.numero_nf).distinct().all()
        nfs_no_monitoramento_set = {nf[0] for nf in nfs_no_monitoramento}
        print(f"[DEBUG] 📊 Total de NFs no monitoramento: {len(nfs_no_monitoramento_set)}")
        
        # Calcula NFs que estão em embarques MAS NÃO estão no monitoramento
        nfs_pendentes_sincronizacao = nfs_em_embarques_set - nfs_no_monitoramento_set
        print(f"[DEBUG] ⚠️ NFs pendentes de sincronização: {len(nfs_pendentes_sincronizacao)}")
        
        if not nfs_pendentes_sincronizacao:
            print(f"[DEBUG] ✅ Todas as NFs de embarques já estão sincronizadas")
            return 0
        
        # Filtra apenas as NFs que TÊM faturamento (importadas)
        nfs_faturadas_pendentes = []
        for nf in nfs_pendentes_sincronizacao:
            fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
            if fat:
                nfs_faturadas_pendentes.append(nf)
        
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
        
        print(f"[DEBUG] ✅ Total de NFs de embarques sincronizadas: {contador_sincronizadas}")
        return contador_sincronizadas
        
    except Exception as e:
        print(f"[DEBUG] ❌ Erro geral na sincronização de NFs pendentes: {e}")
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
def listar_faturamento_produto():
    """Lista faturamento detalhado por produto"""
    # Filtros
    nome_cliente = request.args.get('nome_cliente', '')
    cod_produto = request.args.get('cod_produto', '')
    vendedor = request.args.get('vendedor', '')
    estado = request.args.get('estado', '')
    incoterm = request.args.get('incoterm', '')
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    
    # Paginação
    try:
        page = int(request.args.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    per_page = 200  # 200 itens por página conforme solicitado
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if inspector.has_table('faturamento_produto'):
            # Query base
            query = FaturamentoProduto.query.filter_by(ativo=True)
            
            # Aplicar filtros
            if nome_cliente:
                query = query.filter(FaturamentoProduto.nome_cliente.ilike(f'%{nome_cliente}%'))
            if cod_produto:
                query = query.filter(FaturamentoProduto.cod_produto.ilike(f'%{cod_produto}%'))
            if vendedor:
                query = query.filter(FaturamentoProduto.vendedor.ilike(f'%{vendedor}%'))
            if estado:
                query = query.filter(FaturamentoProduto.estado == estado)
            if incoterm:
                query = query.filter(FaturamentoProduto.incoterm.ilike(f'%{incoterm}%'))
                
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
            
            # Ordenação e paginação
            faturamentos = query.order_by(FaturamentoProduto.data_fatura.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
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
            opcoes_estados = []
            opcoes_incoterms = []
            opcoes_vendedores = []
    except Exception:
        faturamentos = None
        opcoes_estados = []
        opcoes_incoterms = []
        opcoes_vendedores = []
    
    return render_template('faturamento/listar_produtos.html',
                         faturamentos=faturamentos,
                         nome_cliente=nome_cliente,
                         cod_produto=cod_produto,
                         vendedor=vendedor,
                         estado=estado,
                         incoterm=incoterm,
                         data_de=data_de,
                         data_ate=data_ate,
                         opcoes_estados=opcoes_estados,
                         opcoes_incoterms=opcoes_incoterms,
                         opcoes_vendedores=opcoes_vendedores)

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

@faturamento_bp.route('/produtos/importar', methods=['GET', 'POST'])
@login_required
def importar_faturamento_produtos():
    """Importar dados de faturamento por produto"""
    if request.method == 'GET':
        return render_template('faturamento/importar_produtos.html')
    
    # POST - Processar importação
    try:
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(request.url)
            
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(request.url)
            
        if not arquivo.filename.lower().endswith(('.xlsx', '.csv')):
            flash('Tipo de arquivo não suportado! Use apenas .xlsx ou .csv', 'error')
            return redirect(request.url)
        
        # 📁 CORREÇÃO: Ler arquivo uma vez e usar bytes para ambas operações
        original_filename = arquivo.filename
        
        # Ler o arquivo uma vez e usar os bytes para ambas operações
        arquivo.seek(0)  # Garantir que está no início
        file_content = arquivo.read()  # Ler todo o conteúdo uma vez
        
        # 🌐 Usar sistema S3 para salvar arquivo
        file_storage = get_file_storage()
        
        # Criar um objeto BytesIO para simular arquivo para o S3
        from io import BytesIO
        file_for_s3 = BytesIO(file_content)
        file_for_s3.name = original_filename
        
        try:
            # Salvar no S3/storage
            file_path = file_storage.save_file(
                file=file_for_s3,
                folder='faturamento',
                allowed_extensions=['xlsx', 'csv']
            )
        except Exception as e:
            print(f"Erro ao salvar no S3: {e}")
            file_path = None
        
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
        
        # Validar colunas obrigatórias
        colunas_obrigatorias = ['numero_nf', 'data_fatura', 'cnpj_cliente', 'nome_cliente', 
                               'cod_produto', 'nome_produto', 'qtd_produto_faturado',
                               'preco_produto_faturado', 'valor_produto_faturado']
        
        # 🎯 MAPEAMENTO EXATO conforme especificação do usuário
        colunas_esperadas = {
            'numero_nf': 'Linhas da fatura/NF-e',
            'cnpj_cliente': 'Linhas da fatura/Parceiro/CNPJ',
            'nome_cliente': 'Linhas da fatura/Parceiro',
            'municipio_estado': 'Linhas da fatura/Parceiro/Município',
            'origem': 'Linhas da fatura/Origem',
            'status_nf': 'Status',
            'cod_produto': 'Linhas da fatura/Produto/Referência',
            'nome_produto': 'Linhas da fatura/Produto/Nome',
            'qtd_produto_faturado': 'Linhas da fatura/Quantidade',
            'valor_produto_faturado': 'Linhas da fatura/Valor Total do Item da NF',
            'data_fatura': 'Linhas da fatura/Data',
            'vendedor': 'Vendedor',
            'incoterm': 'Incoterm'
        }
        
        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias_excel = [
            'Linhas da fatura/Parceiro/CNPJ',
            'Linhas da fatura/Parceiro',
            'Linhas da fatura/Produto/Referência',
            'Linhas da fatura/Parceiro/Município',
            'Linhas da fatura/Produto/Nome',
            'Linhas da fatura/Valor Total do Item da NF',
            'Linhas da fatura/Quantidade',
            'Linhas da fatura/Data'
        ]
        
        colunas_faltando = [col for col in colunas_obrigatorias_excel if col not in df.columns]
        if colunas_faltando:
            flash(f'❌ Colunas obrigatórias não encontradas: {", ".join(colunas_faltando)}', 'error')
            return redirect(request.url)
        
        # 🔄 FORWARD FILL - Conforme especificação
        campos_forward_fill = ['Status', 'Vendedor', 'Incoterm']
        for campo in campos_forward_fill:
            if campo in df.columns:
                df[campo] = df[campo].fillna(method='ffill')
        
        # 🏙️ PROCESSAR CIDADE/ESTADO do formato "Cidade (UF)"
        def extrair_cidade_uf(texto):
            if pd.isna(texto) or str(texto).strip() == '':
                return '', ''
            
            import re
            texto = str(texto).strip()
            match = re.search(r'^(.+?)\s*\(([A-Z]{2})\)$', texto)
            if match:
                return match.group(1).strip(), match.group(2).strip()
            else:
                return texto, ''
        
        # Aplicar extração de cidade/estado
        if 'Linhas da fatura/Parceiro/Município' in df.columns:
            cidades_ufs = df['Linhas da fatura/Parceiro/Município'].apply(extrair_cidade_uf)
            df['municipio'] = [item[0] for item in cidades_ufs]
            df['estado'] = [item[1] for item in cidades_ufs]
        
        # 💰 CONVERTER VALORES BRASILEIROS (3.281,10)
        def converter_valor_br(valor):
            if pd.isna(valor):
                return 0.0
            valor_str = str(valor).strip().replace('R$', '').replace(' ', '')
            if ',' in valor_str:
                valor_str = valor_str.replace('.', '').replace(',', '.')
            try:
                return float(valor_str)
            except:
                return 0.0
        
        if 'Linhas da fatura/Valor Total do Item da NF' in df.columns:
            df['valor_convertido'] = df['Linhas da fatura/Valor Total do Item da NF'].apply(converter_valor_br)
        
        if 'Linhas da fatura/Quantidade' in df.columns:
            df['qtd_convertida'] = df['Linhas da fatura/Quantidade'].apply(converter_valor_br)
        
        # ✅ VALIDAR STATUS PERMITIDOS
        status_permitidos = ['Lançado', 'Cancelado', 'Provisório']
        if 'Status' in df.columns:
            status_invalidos = df[df['Status'].notna() & ~df['Status'].isin(status_permitidos)]['Status'].unique()
            if len(status_invalidos) > 0:
                flash(f'❌ Status inválidos encontrados: {", ".join(status_invalidos)}. Permitidos: {", ".join(status_permitidos)}', 'error')
                return redirect(request.url)
        
        # Processar dados
        produtos_importados = 0
        produtos_atualizados = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # 📋 EXTRAIR DADOS usando nomes exatos das colunas Excel
                numero_nf = str(row.get('Linhas da fatura/NF-e', '')).strip() if pd.notna(row.get('Linhas da fatura/NF-e')) else ''
                cod_produto = str(row.get('Linhas da fatura/Produto/Referência', '')).strip() if pd.notna(row.get('Linhas da fatura/Produto/Referência')) else ''
                
                if not numero_nf or numero_nf == 'nan' or not cod_produto or cod_produto == 'nan':
                    continue
                
                # Verificar se já existe (NF + Produto = chave única)
                produto_existente = FaturamentoProduto.query.filter_by(
                    numero_nf=numero_nf,
                    cod_produto=cod_produto
                ).first()
                
                # 📅 PROCESSAR DATA
                data_fatura = row.get('Linhas da fatura/Data')
                if pd.notna(data_fatura):
                    if isinstance(data_fatura, str):
                        try:
                            # Formato brasileiro DD/MM/YYYY
                            data_fatura = pd.to_datetime(data_fatura, format='%d/%m/%Y').date()
                        except:
                            try:
                                data_fatura = pd.to_datetime(data_fatura).date()
                            except:
                                data_fatura = None
                    elif hasattr(data_fatura, 'date'):
                        data_fatura = data_fatura.date()
                else:
                    data_fatura = None
                
                # 💰 VALORES
                qtd = row.get('qtd_convertida', 0) or 0
                valor_total = row.get('valor_convertido', 0) or 0
                
                # 🧮 CALCULAR PREÇO UNITÁRIO (valor_total / quantidade)
                preco_unitario = 0.0
                if qtd > 0 and valor_total > 0:
                    preco_unitario = valor_total / qtd
                
                # 📝 DADOS BÁSICOS
                cnpj_cliente = str(row.get('Linhas da fatura/Parceiro/CNPJ', '')).strip()
                nome_cliente = str(row.get('Linhas da fatura/Parceiro', '')).strip()
                nome_produto = str(row.get('Linhas da fatura/Produto/Nome', '')).strip()
                
                # Criar ou atualizar produto
                if produto_existente:
                    # ✏️ ATUALIZAR EXISTENTE
                    produto_existente.data_fatura = data_fatura
                    produto_existente.cnpj_cliente = cnpj_cliente
                    produto_existente.nome_cliente = nome_cliente
                    produto_existente.nome_produto = nome_produto
                    produto_existente.qtd_produto_faturado = qtd
                    produto_existente.preco_produto_faturado = preco_unitario
                    produto_existente.valor_produto_faturado = valor_total
                    
                    # 🌍 CAMPOS PROCESSADOS
                    produto_existente.municipio = row.get('municipio', '')
                    produto_existente.estado = row.get('estado', '')
                    produto_existente.vendedor = str(row.get('Vendedor', '')).strip()
                    produto_existente.incoterm = str(row.get('Incoterm', '')).strip()
                    produto_existente.origem = str(row.get('Linhas da fatura/Origem', '')).strip()
                    produto_existente.status_nf = str(row.get('Status', '')).strip()
                    
                    produto_existente.updated_by = current_user.nome
                    produtos_atualizados += 1
                    
                else:
                    # ➕ CRIAR NOVO
                    novo_produto = FaturamentoProduto()
                    novo_produto.numero_nf = numero_nf
                    novo_produto.data_fatura = data_fatura
                    novo_produto.cnpj_cliente = cnpj_cliente
                    novo_produto.nome_cliente = nome_cliente
                    novo_produto.cod_produto = cod_produto
                    novo_produto.nome_produto = nome_produto
                    novo_produto.qtd_produto_faturado = qtd
                    novo_produto.preco_produto_faturado = preco_unitario
                    novo_produto.valor_produto_faturado = valor_total
                    novo_produto.municipio = row.get('municipio', '')
                    novo_produto.estado = row.get('estado', '')
                    novo_produto.vendedor = str(row.get('Vendedor', '')).strip()
                    novo_produto.incoterm = str(row.get('Incoterm', '')).strip()
                    novo_produto.origem = str(row.get('Linhas da fatura/Origem', '')).strip()
                    novo_produto.status_nf = str(row.get('Status', '')).strip()
                    novo_produto.created_by = current_user.nome
                    
                    db.session.add(novo_produto)
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
        
        return redirect(url_for('faturamento.listar_faturamento_produto'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro durante importação: {str(e)}', 'error')
        return redirect(url_for('faturamento.importar_faturamento_produtos'))

@faturamento_bp.route('/produtos/baixar-modelo')
@login_required
def baixar_modelo_faturamento():
    """Baixar modelo Excel para importação de faturamento por produto"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        
        # Colunas exatas conforme arquivo CSV
        colunas_modelo = [
            'Linhas da fatura/NF-e',
            'Linhas da fatura/Parceiro/CNPJ', 
            'Linhas da fatura/Parceiro',
            'Linhas da fatura/Parceiro/Município',
            'Linhas da fatura/Produto/Referência',
            'Linhas da fatura/Produto/Nome',
            'Linhas da fatura/Quantidade',
            'Linhas da fatura/Valor Total do Item da NF',
            'Linhas da fatura/Data',
            'Status',
            'Vendedor', 
            'Incoterm'
        ]
        
        # Criar DataFrame com exemplo
        dados_exemplo = {
            'Linhas da fatura/NF-e': [128944, '', ''],
            'Linhas da fatura/Parceiro/CNPJ': ['75.315.333/0103-33', '', ''],
            'Linhas da fatura/Parceiro': ['ATACADAO 103', '', ''],
            'Linhas da fatura/Parceiro/Município': ['Olímpia (SP)', '', ''],
            'Linhas da fatura/Produto/Referência': [4220179, 4729098, 4320162],
            'Linhas da fatura/Produto/Nome': [
                'AZEITONA PRETA AZAPA - VD 12X360 GR - CAMPO BELO',
                'OL. MIS AZEITE DE OLIVA VD 12X500 ML - ST ISABEL', 
                'AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO'
            ],
            'Linhas da fatura/Quantidade': [10, 5, 8],
            'Linhas da fatura/Valor Total do Item da NF': ['3.281,10', '850,75', '1.200,00'],
            'Linhas da fatura/Data': ['27/06/2025', '', ''],
            'Status': ['Lançado', '', ''],
            'Vendedor': ['12 SCHIAVINATTO REP COM SC LTDA', '', ''],
            'Incoterm': ['[CIF] CIF', '', '']
        }
        
        df = pd.DataFrame(dados_exemplo)
        
        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Aba principal
            df.to_excel(writer, sheet_name='Dados', index=False)
            
            # Aba de instruções
            instrucoes = pd.DataFrame({
                'INSTRUÇÕES IMPORTANTES': [
                    '1. Use as colunas EXATAMENTE como estão nomeadas',
                    '2. O Forward Fill preencherá campos vazios automaticamente',
                    '3. Campos obrigatórios: NF, CNPJ, Cliente, Município, Código Produto',
                    '4. Status permitidos: Lançado, Cancelado, Provisório',
                    '5. Data no formato DD/MM/YYYY',
                    '6. Valores brasileiros aceitos: 3.281,10',
                    '7. Cidade e UF: formato "Cidade (UF)"',
                    '8. Forward Fill funciona para Status, Vendedor e Incoterm'
                ]
            })
            instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        
        output.seek(0)
        
        # Criar resposta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=modelo_faturamento_produto.xlsx'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('faturamento.listar_faturamento_produto'))

@faturamento_bp.route('/produtos/exportar-dados')
@login_required 
def exportar_dados_faturamento():
    """Exportar dados existentes de faturamento por produto"""
    try:
        import pandas as pd
        from flask import make_response
        from io import BytesIO
        from sqlalchemy import inspect
        
        # 🔧 CORREÇÃO: Definir inspector na função
        inspector = inspect(db.engine)
        
        # Buscar dados
        if inspector.has_table('faturamento_produto'):
            produtos = FaturamentoProduto.query.filter_by(ativo=True).order_by(
                FaturamentoProduto.numero_nf.desc()
            ).all()
        else:
            produtos = []
        
        if not produtos:
            flash('Nenhum dado encontrado para exportar.', 'warning')
            return redirect(url_for('faturamento.listar_faturamento_produto'))
        
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
        return redirect(url_for('faturamento.listar_faturamento_produto'))
