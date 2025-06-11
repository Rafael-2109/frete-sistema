import os
import pandas as pd
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.faturamento.forms import UploadRelatorioForm  # certifique-se de que o caminho está correto
from app.utils.helpers import limpar_valor
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

faturamento_bp = Blueprint('faturamento', __name__,url_prefix='/faturamento')

UPLOAD_FOLDER = 'uploads/faturamento'
ALLOWED_EXTENSIONS = {'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def revalidar_embarques_pendentes(nfs_importadas):
    """
    Re-valida embarques que tinham NFs pendentes e agora podem ser validadas
    """
    from app.embarques.models import EmbarqueItem
    from app.fretes.routes import validar_cnpj_embarque_faturamento
    
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
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            try:
                df = pd.read_excel(filepath)
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

                for _, row in df.iterrows():
                    numero_nf = str(row["Número da Nota Fiscal"])
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

                for nf in nfs_importadas:
                    sincronizar_entrega_por_nf(nf)

                flash('Relatório importado e entregas sincronizadas com sucesso.', 'success')
                return redirect(url_for('faturamento.importar_relatorio'))

            except Exception as e:
                flash(f'Erro ao processar o arquivo: {e}', 'danger')
                return redirect(request.url)

        flash('Tipo de arquivo não permitido. Envie um .xlsx', 'danger')
        return redirect(request.url)

    return render_template('faturamento/importar_relatorio.html', form=form)

@faturamento_bp.route('/sincronizar-orphas')
@login_required
def sincronizar_orphas():
    """Sincroniza NFs órfãs - ROTA SIMPLES PARA USO ÚNICO"""
    try:
        from app.monitoramento.models import EntregaMonitorada
        
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
    if numero_nf := request.args.get('numero_nf'):
        query = query.filter(RelatorioFaturamentoImportado.numero_nf.ilike(f"%{numero_nf}%"))
    if cnpj_cliente := request.args.get('cnpj_cliente'):
        query = query.filter(RelatorioFaturamentoImportado.cnpj_cliente.ilike(f"%{cnpj_cliente}%"))
    if nome_cliente := request.args.get('nome_cliente'):
        query = query.filter(RelatorioFaturamentoImportado.nome_cliente.ilike(f"%{nome_cliente}%"))
    if vendedor := request.args.get('vendedor'):
        query = query.filter(RelatorioFaturamentoImportado.vendedor.ilike(f"%{vendedor}%"))

    # 2) Descobrir qual coluna e direção de ordenação
    sort = request.args.get('sort', 'data_fatura')      # padrão
    direction = request.args.get('direction', 'desc')   # padrão

    # 3) Definir mapa de colunas ordenáveis
    sortable_columns = {
        'numero_nf':           RelatorioFaturamentoImportado.numero_nf,
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

    # 6) Render
    return render_template(
        'faturamento/listar_relatorios.html',
        relatorios=paginacao.items,
        paginacao=paginacao,
        sort=sort,
        direction=direction,
    )

