import os
import pandas as pd
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
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

                for _, row in df.iterrows():
                    # Validação 1: Número da NF não pode estar vazio
                    numero_nf_raw = row.get("Número da Nota Fiscal")
                    if pd.isna(numero_nf_raw) or str(numero_nf_raw).strip() == '' or str(numero_nf_raw).lower() == 'nan':
                        linhas_ignoradas += 1
                        continue
                        
                    numero_nf = str(numero_nf_raw).strip()
                    
                    # Validação 2: Origem (pedido) não pode estar vazio - campo crítico
                    origem = row.get("Origem")
                    if pd.isna(origem) or str(origem).strip() == '' or str(origem).lower() == 'nan':
                        linhas_ignoradas += 1
                        continue
                    
                    # Verifica se NF já existe
                    existe = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
                    if existe:
                        continue

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

                # Mensagens de resultado
                flash(f'✅ Relatório importado com sucesso! {len(nfs_importadas)} NFs processadas.', 'success')
                flash(f'📁 Arquivo salvo no sistema de armazenamento.', 'info')
                
                if linhas_ignoradas > 0:
                    flash(f'⚠️ {linhas_ignoradas} linhas foram ignoradas (NF ou Origem vazios).', 'warning')
                
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

