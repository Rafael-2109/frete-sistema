from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
    session,
    send_from_directory,
    send_file,
)
from flask_login import login_required, current_user
from datetime import datetime, date
from app.utils.timezone import agora_utc_naive
from sqlalchemy import and_, or_, desc, func
import os
import logging
import math
from app.transportadoras.models import Transportadora
from app.fretes.forms import LancamentoFreteirosForm
from app import db
from app.utils.memory_cache import TTLCache

# Cache do dashboard (TTL 120s — dados de contagem mudam lentamente)
_dashboard_cache = TTLCache(ttl=120)

# 🔒 Importar decoradores de permissão
from app.utils.auth_decorators import require_financeiro, require_profiles
from app.embarques.models import Embarque, EmbarqueItem
from app.faturamento.models import RelatorioFaturamentoImportado
from app.fretes.models import (
    FreteLancado,
    Frete,
    FaturaFrete,
    DespesaExtra,
    ContaCorrenteTransportadora,
    AprovacaoFrete,
    ConhecimentoTransporte,
)
from app.fretes.email_models import EmailAnexado
from app.utils.email_handler import EmailHandler
from app.fretes.forms import (
    FreteForm,
    FaturaFreteForm,
    DespesaExtraForm,
    FiltroFretesForm,
    LancamentoCteForm,
    FiltroFaturasForm,
    FiltroFreteirosForm,
)
from app.utils.calculadora_frete import calcular_valor_frete_pela_tabela
from app.utils.valores_brasileiros import converter_valor_brasileiro
from app.utils.cnpj_utils import normalizar_cnpj
from app.utils.tabela_frete_manager import TabelaFreteManager

# Configurar logger
logger = logging.getLogger(__name__)

fretes_bp = Blueprint("fretes", __name__, url_prefix="/fretes")

# =================== ROTAS PARA O NOVO SISTEMA DE FRETES ===================


@fretes_bp.route("/")
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def index():
    """Dashboard principal do sistema de fretes"""
    # Estatisticas com cache (evita 5 COUNT queries a cada visita)
    def _fetch_dashboard_stats():
        return {
            'total': Frete.query.count(),
            'pendentes': Frete.query.filter_by(status="PENDENTE").count(),
            'aprovacoes': AprovacaoFrete.query.filter_by(status="PENDENTE").count(),
            'faturas': FaturaFrete.query.filter_by(status_conferencia="PENDENTE").count(),
            'sem_nfs': Frete.query.filter(
                or_(Frete.numeros_nfs.is_(None), Frete.numeros_nfs == "", Frete.numeros_nfs == "N/A")
            ).count(),
        }

    stats = _dashboard_cache.get_or_set('dashboard_stats', _fetch_dashboard_stats)
    total_fretes = stats['total']
    fretes_pendentes = stats['pendentes']
    aprovacoes_pendentes = stats['aprovacoes']
    faturas_conferir = stats['faturas']
    fretes_sem_nfs = stats['sem_nfs']

    # Fretes recentes (sem cache — lista curta, muda frequentemente)
    fretes_recentes = Frete.query.order_by(desc(Frete.criado_em)).limit(10).all()

    return render_template(
        "fretes/dashboard.html",
        total_fretes=total_fretes,
        fretes_pendentes=fretes_pendentes,
        aprovacoes_pendentes=aprovacoes_pendentes,
        faturas_conferir=faturas_conferir,
        fretes_sem_nfs=fretes_sem_nfs,
        fretes_recentes=fretes_recentes,
    )


@fretes_bp.route("/analises")
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def analises():
    """
    Página de análises de fretes com gráficos e filtros
    """
    from app.fretes.services.analises_service import (
        analise_por_uf,
        analise_por_transportadora,
        analise_por_cidade,
        analise_por_subrota,
        analise_por_cliente,
        analise_por_mes,
        analise_por_modalidade,
    )

    # Capturar filtros da URL
    data_inicio_str = request.args.get("data_inicio", "")
    data_fim_str = request.args.get("data_fim", "")
    transportadora_id = request.args.get("transportadora_id", "")
    uf = request.args.get("uf", "")
    status = request.args.get("status", "")
    tipo_analise = request.args.get(
        "tipo_analise", "uf"
    )  # uf, cidade, subrota, transportadora, cliente, mes, modalidade

    # Converter datas
    data_inicio = None
    data_fim = None

    try:
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d")
    except ValueError:
        flash("Data inicial inválida. Use o formato AAAA-MM-DD.", "warning")

    try:
        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d")
    except ValueError:
        flash("Data final inválida. Use o formato AAAA-MM-DD.", "warning")

    # Converter IDs para int
    transportadora_id_int = None
    if transportadora_id:
        try:
            transportadora_id_int = int(transportadora_id)
        except ValueError:
            pass

    # Executar análises baseado no tipo
    dados = []

    if tipo_analise == "uf":
        dados = analise_por_uf(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, status=status
        )
    elif tipo_analise == "cidade":
        dados = analise_por_cidade(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, uf=uf, status=status
        )
    elif tipo_analise == "subrota":
        dados = analise_por_subrota(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, uf=uf, status=status
        )
    elif tipo_analise == "transportadora":
        dados = analise_por_transportadora(data_inicio=data_inicio, data_fim=data_fim, uf=uf, status=status)
    elif tipo_analise == "cliente":
        dados = analise_por_cliente(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, uf=uf, status=status
        )
    elif tipo_analise == "mes":
        dados = analise_por_mes(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, uf=uf, status=status
        )
    elif tipo_analise == "modalidade":
        dados = analise_por_modalidade(
            data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, uf=uf, status=status
        )

    # Buscar dados para os gráficos principais (independente do filtro)
    # Gráfico 1: Por UF
    dados_uf = analise_por_uf(
        data_inicio=data_inicio, data_fim=data_fim, transportadora_id=transportadora_id_int, status=status
    )

    # Gráfico 2: Por Transportadora
    dados_transportadora = analise_por_transportadora(data_inicio=data_inicio, data_fim=data_fim, uf=uf, status=status)

    # Listar transportadoras para o filtro
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()

    # Lista de UFs únicas
    ufs = db.session.query(Frete.uf_destino).distinct().order_by(Frete.uf_destino).all()
    ufs = [uf[0] for uf in ufs]

    return render_template(
        "fretes/analises.html",
        dados=dados,
        dados_uf=dados_uf,
        dados_transportadora=dados_transportadora,
        transportadoras=transportadoras,
        ufs=ufs,
        # Filtros aplicados
        data_inicio=data_inicio_str,
        data_fim=data_fim_str,
        transportadora_id=transportadora_id,
        uf=uf,
        status=status,
        tipo_analise=tipo_analise,
    )


@fretes_bp.route("/analises/api/data")
@login_required
@require_financeiro()
def analises_api_data():
    """
    API para drill-down dinâmico
    Query params:
        - filters: JSON string com filtros aplicados
        - group_by: Dimensão para agrupar
        - incluir_transportadora: true/false (default: true)
        - incluir_freteiro: true/false (default: true)

    Exemplo:
        /analises/api/data?filters=[{"type":"uf","value":"SP"}]&group_by=mes&incluir_transportadora=true&incluir_freteiro=false
    """
    from app.fretes.services.analises_service import analise_dinamica
    import json

    # Parsear filtros
    filters_json = request.args.get("filters", "[]")
    try:
        filtros = json.loads(filters_json)
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao parsear filtros: {str(e)}"}), 400

    group_by = request.args.get("group_by", "uf")

    # Parsear checkboxes (default: ambos marcados)
    incluir_transportadora = request.args.get("incluir_transportadora", "true").lower() == "true"
    incluir_freteiro = request.args.get("incluir_freteiro", "true").lower() == "true"

    # Validar group_by
    valid_dimensions = ["uf", "transportadora", "modalidade", "mes", "subrota", "cliente"]
    if group_by not in valid_dimensions:
        return jsonify({"success": False, "error": "Dimensão inválida"}), 400

    try:
        # Buscar dados
        dados = analise_dinamica(
            filtros=filtros,
            group_by=group_by,
            incluir_transportadora=incluir_transportadora,
            incluir_freteiro=incluir_freteiro,
        )

        return jsonify(
            {
                "success": True,
                "filtros_aplicados": filtros,
                "agrupado_por": group_by,
                "incluir_transportadora": incluir_transportadora,
                "incluir_freteiro": incluir_freteiro,
                "dados": dados,
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro ao buscar dados: {str(e)}"}), 500


@fretes_bp.route("/analises/api/export-excel")
@login_required
@require_financeiro()
def analises_api_export_excel():
    """
    Exporta os dados da análise atual para Excel
    Query params:
        - filters: JSON string com filtros aplicados
        - group_by: Dimensão para agrupar
        - incluir_transportadora: true/false (default: true)
        - incluir_freteiro: true/false (default: true)
    """
    from app.fretes.services.analises_service import analise_dinamica
    import json
    import pandas as pd
    from io import BytesIO
    from flask import send_file

    # Parsear filtros
    filters_json = request.args.get("filters", "[]")
    try:
        filtros = json.loads(filters_json)
    except Exception as e:
        flash(f"Erro ao parsear filtros: {str(e)}", "danger")
        return redirect(url_for("fretes.analises"))

    group_by = request.args.get("group_by", "uf")

    # Parsear checkboxes (default: ambos marcados)
    incluir_transportadora = request.args.get("incluir_transportadora", "true").lower() == "true"
    incluir_freteiro = request.args.get("incluir_freteiro", "true").lower() == "true"

    # Validar group_by
    valid_dimensions = ["uf", "transportadora", "modalidade", "mes", "subrota", "cliente"]
    if group_by not in valid_dimensions:
        flash("Dimensão inválida", "danger")
        return redirect(url_for("fretes.analises"))

    try:
        # Buscar dados
        dados = analise_dinamica(
            filtros=filtros,
            group_by=group_by,
            incluir_transportadora=incluir_transportadora,
            incluir_freteiro=incluir_freteiro,
        )

        if not dados:
            flash("Nenhum dado disponível para exportação", "warning")
            return redirect(url_for("fretes.analises"))

        # Preparar DataFrame
        df_data = []
        for item in dados:
            df_data.append(
                {
                    "Dimensão": item["label"],
                    "Qtd Fretes": item["qtd_fretes"],
                    "Frete Bruto (R$)": item["valor_frete_bruto"],  # Frete bruto
                    "ICMS (R$)": item["total_icms"],
                    "PIS/COFINS (R$)": item["total_pis_cofins"],
                    "Frete Líquido (R$)": item["valor_frete"],  # Frete líquido (já calculado)
                    "Despesas (R$)": item["valor_despesa"],
                    "Custo Total (R$)": item["total_custo"],
                    "Valor NF (R$)": item["valor_nf"],
                    "Peso (KG)": item["peso"],
                    "% s/ Valor": item["percentual_valor"],
                    "R$/KG": item["valor_por_kg"],
                }
            )

        df = pd.DataFrame(df_data)

        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Análise")

            # Formatar colunas
            worksheet = writer.sheets["Análise"]

            # Ajustar largura das colunas
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].fillna('').astype(str).map(len).max(), len(col))
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

        output.seek(0)

        # Gerar nome do arquivo baseado nos filtros
        filter_names = "_".join([f"{f['type']}-{f['value']}" for f in filtros]) if filtros else "todos"
        filename = f"analise_fretes_{group_by}_{filter_names}.xlsx"

        # Sanitizar nome do arquivo
        import re

        filename = re.sub(r"[^\w\-_\.]", "_", filename)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        flash(f"Erro ao exportar dados: {str(e)}", "danger")
        return redirect(url_for("fretes.analises"))


@fretes_bp.route("/listar")
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def listar_fretes():
    """Lista todos os fretes com filtros"""
    from sqlalchemy import cast, String

    form = FiltroFretesForm(request.args)

    # Popular choices de transportadoras no formulário
    transportadoras = Transportadora.query.all()
    form.transportadora_id.choices = [("", "Todas as transportadoras")] + [
        (t.id, t.razao_social) for t in transportadoras
    ]

    query = Frete.query

    # ✅ NOVO: Filtro por ID do frete (busca direta)
    if form.frete_id.data:
        try:
            frete_id = int(form.frete_id.data.strip())
            query = query.filter(Frete.id == frete_id)
        except ValueError:
            pass

    # ✅ CORREÇÃO: Filtro por número do embarque usando cast para string
    if form.embarque_numero.data:
        query = query.join(Embarque).filter(cast(Embarque.numero, String).ilike(f"%{form.embarque_numero.data}%"))

    if form.cnpj_cliente.data:
        query = query.filter(Frete.cnpj_cliente.ilike(f"%{form.cnpj_cliente.data}%"))

    if form.nome_cliente.data:
        query = query.filter(Frete.nome_cliente.ilike(f"%{form.nome_cliente.data}%"))

    if form.numero_cte.data:
        query = query.filter(Frete.numero_cte.ilike(f"%{form.numero_cte.data}%"))

    if form.numero_fatura.data:
        query = query.join(FaturaFrete).filter(FaturaFrete.numero_fatura.ilike(f"%{form.numero_fatura.data}%"))

    # ✅ NOVO: Filtro por número da NF
    if form.numero_nf.data:
        query = query.filter(Frete.numeros_nfs.contains(form.numero_nf.data))

    # ✅ NOVO: Filtro por número da NF de Devolução (via DespesaExtra)
    if form.numero_nfd.data:
        query = query.join(DespesaExtra).filter(
            DespesaExtra.numero_nfd.ilike(f"%{form.numero_nfd.data}%")
        )

    # ✅ NOVO: Filtro por transportadora
    if form.transportadora_id.data:
        try:
            transportadora_id = int(form.transportadora_id.data)
            query = query.filter(Frete.transportadora_id == transportadora_id)
        except (ValueError, TypeError):
            pass

    if form.status.data:
        query = query.filter(Frete.status == form.status.data)

    if form.data_inicio.data:
        query = query.filter(Frete.criado_em >= form.data_inicio.data)

    if form.data_fim.data:
        query = query.filter(Frete.criado_em <= form.data_fim.data)

    fretes = query.order_by(desc(Frete.criado_em)).paginate(
        page=request.args.get("page", 1, type=int), per_page=50, error_out=False
    )

    return render_template("fretes/listar_fretes.html", fretes=fretes, form=form)


@fretes_bp.route("/lancar_cte", methods=["GET", "POST"])
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def lancar_cte():
    """Lançamento de CTe com base na NF - primeiro mostra fretes que contêm a NF"""
    form = LancamentoCteForm()
    embarque_encontrado = None
    fretes_existentes = []  # Fretes já criados que contêm essa NF
    frete_para_processar = None  # Frete selecionado pelo usuário

    # Busca faturas disponíveis
    faturas_disponiveis = (
        FaturaFrete.query.filter_by(status_conferencia="PENDENTE").order_by(desc(FaturaFrete.criado_em)).all()
    )

    # ✅ CAPTURA FATURA PRÉ-SELECIONADA DO GET (quando vem de /fretes/lancar_cte?fatura_id=4)
    fatura_preselecionada_id = request.args.get("fatura_id", type=int)

    if form.validate_on_submit():
        numero_nf = form.numero_nf.data
        fatura_frete_id = request.form.get("fatura_frete_id")
        frete_selecionado_id = request.form.get("frete_selecionado_id")  # ID do frete escolhido pelo usuário

        if not fatura_frete_id:
            flash("Selecione uma fatura de frete!", "error")
            return render_template(
                "fretes/lancar_cte.html",
                form=form,
                faturas_disponiveis=faturas_disponiveis,
                fatura_preselecionada_id=fatura_preselecionada_id,
            )

        # Busca NF no faturamento
        nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()

        if not nf_faturamento:
            flash(f"NF {numero_nf} não encontrada no faturamento!", "error")
            return render_template(
                "fretes/lancar_cte.html",
                form=form,
                faturas_disponiveis=faturas_disponiveis,
                fatura_preselecionada_id=fatura_preselecionada_id,
            )

        # Busca embarque que contém essa NF
        embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).first()

        if not embarque_item:
            flash(f"NF {numero_nf} não encontrada em nenhum embarque!", "error")
            return render_template(
                "fretes/lancar_cte.html",
                form=form,
                faturas_disponiveis=faturas_disponiveis,
                fatura_preselecionada_id=fatura_preselecionada_id,
            )

        embarque_encontrado = embarque_item.embarque

        # ETAPA 1: Busca todos os fretes existentes que contêm essa NF
        fretes_existentes = Frete.query.filter(Frete.numeros_nfs.contains(numero_nf)).all()

        # Se há um frete selecionado pelo usuário, prepara para processamento
        if frete_selecionado_id:
            frete_para_processar = db.session.get(Frete,frete_selecionado_id) if frete_selecionado_id else None
            if not frete_para_processar:
                flash("Frete selecionado não encontrado!", "error")
                return redirect(url_for("fretes.lancar_cte"))

            # Verifica se já tem CTe lançado
            if frete_para_processar.numero_cte:
                flash(f"Este frete já possui CTe {frete_para_processar.numero_cte} lançado!", "warning")
                return redirect(url_for("fretes.visualizar_frete", frete_id=frete_para_processar.id))

        # Se não há fretes existentes, verifica se pode criar um novo
        elif not fretes_existentes:
            cnpj_cliente = nf_faturamento.cnpj_cliente

            # Verifica se já existe frete para este CNPJ neste embarque
            frete_existente = Frete.query.filter(
                and_(Frete.embarque_id == embarque_encontrado.id, Frete.cnpj_cliente == cnpj_cliente)
            ).first()

            if frete_existente:
                flash(
                    f"Já existe frete para o CNPJ {cnpj_cliente} no embarque {embarque_encontrado.numero}!", "warning"
                )
                return redirect(url_for("fretes.visualizar_frete", frete_id=frete_existente.id))

            # Pode criar novo frete - redireciona para criação
            flash(f"Nenhum frete encontrado com a NF {numero_nf}. Redirecionando para criação de novo frete...", "info")
            return redirect(
                url_for("fretes.criar_novo_frete_por_nf", numero_nf=numero_nf, fatura_frete_id=fatura_frete_id)
            )

    return render_template(
        "fretes/lancar_cte.html",
        form=form,
        embarque_encontrado=embarque_encontrado,
        fretes_existentes=fretes_existentes,
        frete_para_processar=frete_para_processar,
        faturas_disponiveis=faturas_disponiveis,
        fatura_preselecionada_id=fatura_preselecionada_id,
    )


@fretes_bp.route("/criar_novo_frete_por_nf")
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def criar_novo_frete_por_nf():
    """Cria novo frete baseado em uma NF específica"""
    numero_nf = request.args.get("numero_nf")
    fatura_frete_id = request.args.get("fatura_frete_id")

    if not numero_nf or not fatura_frete_id:
        flash("Parâmetros inválidos!", "error")
        return redirect(url_for("fretes.lancar_cte"))

    # Busca NF no faturamento
    nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
    if not nf_faturamento:
        flash(f"NF {numero_nf} não encontrada no faturamento!", "error")
        return redirect(url_for("fretes.lancar_cte"))

    # Busca embarque que contém essa NF
    embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).first()
    if not embarque_item:
        flash(f"NF {numero_nf} não encontrada em nenhum embarque!", "error")
        return redirect(url_for("fretes.lancar_cte"))

    embarque_encontrado = embarque_item.embarque
    cnpj_cliente = nf_faturamento.cnpj_cliente

    # Busca todas as NFs do mesmo CNPJ neste embarque
    outras_nfs = RelatorioFaturamentoImportado.query.filter_by(cnpj_cliente=cnpj_cliente).all()
    numeros_nfs_cnpj = [nf.numero_nf for nf in outras_nfs]

    itens_embarque_cnpj = EmbarqueItem.query.filter(
        and_(EmbarqueItem.embarque_id == embarque_encontrado.id, EmbarqueItem.nota_fiscal.in_(numeros_nfs_cnpj))
    ).all()

    if not itens_embarque_cnpj:
        flash(f"Nenhuma NF do CNPJ {cnpj_cliente} encontrada no embarque {embarque_encontrado.numero}!", "error")
        return redirect(url_for("fretes.lancar_cte"))

    # Prepara dados para lançamento do frete
    total_peso = sum(
        float(nf.peso_bruto or 0)
        for nf in outras_nfs
        if nf.numero_nf in [item.nota_fiscal for item in itens_embarque_cnpj]
    )
    total_valor = sum(
        float(nf.valor_total or 0)
        for nf in outras_nfs
        if nf.numero_nf in [item.nota_fiscal for item in itens_embarque_cnpj]
    )
    numeros_nfs = ",".join([item.nota_fiscal for item in itens_embarque_cnpj])

    frete_data = {
        "embarque": embarque_encontrado,
        "cnpj_cliente": cnpj_cliente,
        "nome_cliente": nf_faturamento.nome_cliente,
        "transportadora_id": embarque_encontrado.transportadora_id,
        "tipo_carga": embarque_encontrado.tipo_carga,
        "peso_total": total_peso,
        "valor_total_nfs": total_valor,
        "quantidade_nfs": len(itens_embarque_cnpj),
        "numeros_nfs": numeros_nfs,
        "itens_embarque": itens_embarque_cnpj,
        "fatura_frete_id": fatura_frete_id,
    }

    return render_template("fretes/criar_novo_frete.html", frete_data=frete_data, numero_nf_original=numero_nf)


@fretes_bp.route("/processar_cte_frete_existente", methods=["POST"])
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def processar_cte_frete_existente():
    """Processa lançamento de CTe em frete já existente"""
    try:
        frete_id = request.form.get("frete_id")
        fatura_frete_id = request.form.get("fatura_frete_id")

        if not frete_id:
            flash("ID do frete não informado!", "error")
            return redirect(url_for("fretes.lancar_cte"))

        if not fatura_frete_id:
            flash("ID da fatura não informado!", "error")
            return redirect(url_for("fretes.lancar_cte"))

        frete = Frete.query.get_or_404(frete_id)
        fatura = FaturaFrete.query.get_or_404(fatura_frete_id)

        # Verifica se já tem CTe lançado
        if frete.numero_cte:
            flash(f"Este frete já possui CTe {frete.numero_cte} lançado!", "warning")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

        # ✅ VALIDAÇÃO: Transportadora da fatura deve ser a mesma do frete (ou do mesmo grupo)
        if frete.transportadora_id != fatura.transportadora_id:
            if not frete.transportadora.pertence_mesmo_grupo(fatura.transportadora_id):
                flash(
                    f"❌ Erro: A transportadora da fatura ({fatura.transportadora.razao_social}) é diferente da transportadora do frete ({frete.transportadora.razao_social}) e não pertencem ao mesmo grupo!",
                    "error",
                )
                return redirect(url_for("fretes.lancar_cte", fatura_id=fatura_frete_id))
            else:
                grupo_nome = frete.transportadora.grupo.nome if frete.transportadora.grupo else "mesmo grupo"
                flash(
                    f"⚠️ Transportadoras diferentes mas do {grupo_nome}. Vinculação permitida.",
                    "info",
                )

        # ✅ VINCULA A FATURA AO FRETE EXISTENTE
        if not frete.fatura_frete_id:
            frete.fatura_frete_id = fatura_frete_id
            flash(f"✅ Fatura {fatura.numero_fatura} vinculada ao frete #{frete.id}", "success")
        elif frete.fatura_frete_id != int(fatura_frete_id):
            # Se já tem fatura vinculada mas é diferente, alerta
            fatura_atual = frete.fatura_frete
            flash(
                f"⚠️ Atenção: Frete já tinha fatura {fatura_atual.numero_fatura} vinculada. Trocando para {fatura.numero_fatura}",
                "warning",
            )
            frete.fatura_frete_id = fatura_frete_id

        # ✅ PRÉ-PREENCHE VENCIMENTO DA FATURA
        if fatura.vencimento and not frete.vencimento:
            frete.vencimento = fatura.vencimento
            flash(f'📅 Vencimento preenchido automaticamente: {fatura.vencimento.strftime("%d/%m/%Y")}', "info")

        db.session.commit()

        # Redireciona para edição do frete para lançar CTe
        flash(f"Frete #{frete.id} selecionado. Agora lance os dados do CTe.", "info")
        return redirect(url_for("fretes.editar_frete", frete_id=frete.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao processar frete: {str(e)}", "error")
        return redirect(url_for("fretes.lancar_cte"))


@fretes_bp.route("/processar_lancamento_frete", methods=["POST"])
@login_required
def processar_lancamento_frete():
    """Processa o lançamento efetivo do frete"""
    try:
        # Dados do formulário
        embarque_id = request.form.get("embarque_id")
        cnpj_cliente = request.form.get("cnpj_cliente")
        nome_cliente = request.form.get("nome_cliente")
        transportadora_id = request.form.get("transportadora_id")
        tipo_carga = request.form.get("tipo_carga")
        peso_total = float(request.form.get("peso_total"))
        valor_total_nfs = float(request.form.get("valor_total_nfs"))
        quantidade_nfs = int(request.form.get("quantidade_nfs"))
        numeros_nfs = request.form.get("numeros_nfs")
        fatura_frete_id = request.form.get("fatura_frete_id")

        embarque = Embarque.query.get_or_404(embarque_id)

        # Pega dados da tabela conforme tipo de carga
        if tipo_carga == "DIRETA":
            # Para carga direta, dados vêm do embarque
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(embarque)
            tabela_dados["icms_destino"] = embarque.icms_destino or 0
        else:
            # Para carga fracionada, dados vêm de qualquer item do CNPJ
            item_referencia = EmbarqueItem.query.filter(
                and_(EmbarqueItem.embarque_id == embarque_id, EmbarqueItem.cnpj_cliente == cnpj_cliente)
            ).first()

            tabela_dados = TabelaFreteManager.preparar_dados_tabela(item_referencia)
            tabela_dados["icms_destino"] = item_referencia.icms_destino or 0

        # Calcula valor cotado usando a tabela
        valor_cotado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total, valor_total_nfs)

        # Cria o frete
        novo_frete = Frete(
            embarque_id=embarque_id,
            cnpj_cliente=cnpj_cliente,
            nome_cliente=nome_cliente,
            transportadora_id=transportadora_id,
            tipo_carga=tipo_carga,
            modalidade=tabela_dados["modalidade"],
            uf_destino=embarque.itens[0].uf_destino,  # Pega do primeiro item
            cidade_destino=embarque.itens[0].cidade_destino,
            peso_total=peso_total,
            valor_total_nfs=valor_total_nfs,
            quantidade_nfs=quantidade_nfs,
            numeros_nfs=numeros_nfs,
            # Valores
            valor_cotado=valor_cotado,
            valor_considerado=valor_cotado,  # Inicialmente igual ao cotado
            # Fatura
            fatura_frete_id=fatura_frete_id,
            # Controle
            criado_por=current_user.nome,
            lancado_em=agora_utc_naive(),
            lancado_por=current_user.nome,
        )

        # Atribui campos da tabela usando TabelaFreteManager
        TabelaFreteManager.atribuir_campos_objeto(novo_frete, tabela_dados)
        novo_frete.tabela_icms_destino = tabela_dados["icms_destino"]

        db.session.add(novo_frete)
        db.session.commit()

        flash(f"Frete lançado com sucesso! Valor cotado: R$ {valor_cotado:.2f}", "success")
        return redirect(url_for("fretes.visualizar_frete", frete_id=novo_frete.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao lançar frete: {str(e)}", "error")
        return redirect(url_for("fretes.lancar_cte"))


@fretes_bp.route("/<int:frete_id>")
@login_required
def visualizar_frete(frete_id):
    """Visualiza detalhes de um frete específico"""
    from app.fretes.email_models import EmailAnexado

    frete = Frete.query.get_or_404(frete_id)
    despesas_extras = DespesaExtra.query.filter_by(frete_id=frete_id).all()
    movimentacoes_conta = ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).all()

    # Buscar emails anexados às despesas deste frete
    emails_anexados = EmailAnexado.query.join(DespesaExtra).filter(DespesaExtra.frete_id == frete_id).all()

    # Buscar CTes relacionados do Odoo (sugestões)
    ctes_relacionados = frete.buscar_ctes_relacionados()

    # ✅ BUSCAR CTes VINCULADOS (usa backref 'conhecimentos_transporte')
    # Retorna TODOS os CTes com frete_id = frete.id
    ctes_vinculados = frete.conhecimentos_transporte if frete.conhecimentos_transporte else []

    return render_template(
        "fretes/visualizar_frete.html",
        frete=frete,
        despesas_extras=despesas_extras,
        movimentacoes_conta=movimentacoes_conta,
        emails_anexados=emails_anexados,
        ctes_relacionados=ctes_relacionados,
        ctes_vinculados=ctes_vinculados,
    )


@fretes_bp.route("/<int:frete_id>/editar", methods=["GET", "POST"])
@login_required
def editar_frete(frete_id):
    """Edita dados do CTe e valores do frete"""
    frete = Frete.query.get_or_404(frete_id)

    # ✅ VALIDAÇÃO: Não permitir lançar CTe sem fatura vinculada
    if not frete.fatura_frete_id:
        flash("❌ Este frete não possui fatura vinculada! Para lançar CTe é obrigatório ter fatura.", "error")
        flash("💡 Fluxo correto: Fretes → Faturas → Criar Fatura → Lançar CTe através da fatura", "info")
        flash("🔄 Ou se você já tem uma fatura, use: Fretes → Lançar CTe → Selecione a fatura → Busque pela NF", "info")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

    form = FreteForm(obj=frete)

    # ✅ NOVO: Buscar CTes relacionados para sugestão (sempre busca, permite trocar CTe)
    ctes_sugeridos = frete.buscar_ctes_relacionados()
    if ctes_sugeridos:
        current_app.logger.info(f"🔍 Encontrados {len(ctes_sugeridos)} CTes sugeridos para frete #{frete.id}")

    # ✅ CORREÇÃO: Auto-preencher vencimento da fatura
    if frete.fatura_frete and frete.fatura_frete.vencimento and not frete.vencimento:
        frete.vencimento = frete.fatura_frete.vencimento
        form.vencimento.data = frete.fatura_frete.vencimento

    if form.validate_on_submit():
        frete.numero_cte = form.numero_cte.data
        # ✅ REMOVIDO: data_emissao_cte (conforme solicitado)
        frete.vencimento = form.vencimento.data

        # ✅ CONVERTENDO VALORES COM VÍRGULA usando função centralizada
        frete.valor_cte = converter_valor_brasileiro(form.valor_cte.data) if form.valor_cte.data else None
        frete.valor_considerado = (
            converter_valor_brasileiro(form.valor_considerado.data) if form.valor_considerado.data else None
        )
        frete.valor_pago = converter_valor_brasileiro(form.valor_pago.data) if form.valor_pago.data else None

        frete.considerar_diferenca = form.considerar_diferenca.data
        frete.observacoes_aprovacao = form.observacoes_aprovacao.data

        # Verifica se precisa de aprovação
        requer_aprovacao = False
        motivo_aprovacao = ""

        # Regra 1: Diferença entre Valor Considerado e Valor Cotado > R$ 5,00
        if frete.valor_considerado and frete.valor_cotado:
            diferenca_considerado_cotado = abs(frete.valor_considerado - frete.valor_cotado)
            if diferenca_considerado_cotado > 5.00:
                requer_aprovacao = True
                motivo_aprovacao += (
                    f"Diferença de R$ {diferenca_considerado_cotado:.2f} entre valor considerado e cotado. "
                )

        # Regra 2: Diferença entre Valor Pago e Valor Cotado > R$ 5,00
        if frete.valor_pago and frete.valor_cotado:
            diferenca_pago_cotado = abs(frete.valor_pago - frete.valor_cotado)
            if diferenca_pago_cotado > 5.00:
                requer_aprovacao = True
                motivo_aprovacao += f"Diferença de R$ {diferenca_pago_cotado:.2f} entre valor pago e cotado. "

        # ✅ NOVA LÓGICA: Baseada em diferença de R$ 5,00
        if requer_aprovacao:
            frete.requer_aprovacao = True
            frete.status = "EM_TRATATIVA"  # Novo status

            # Remove aprovações antigas
            AprovacaoFrete.query.filter_by(frete_id=frete.id).delete()

            # Cria nova solicitação de aprovação
            aprovacao = AprovacaoFrete(
                frete_id=frete.id, solicitado_por=current_user.nome, motivo_solicitacao=motivo_aprovacao.strip()
            )
            db.session.add(aprovacao)
        else:
            # Se não requer aprovação, marca como lançado
            frete.status = "LANCADO"
            frete.lancado_em = agora_utc_naive()
            frete.lancado_por = current_user.nome

        # ✅ NOVA LÓGICA: Conta corrente baseada na função deve_lancar_conta_corrente
        deve_lancar, motivo = frete.deve_lancar_conta_corrente()

        if deve_lancar and frete.valor_pago and frete.valor_considerado:
            diferenca = frete.diferenca_considerado_pago()
            if diferenca != 0:
                # Remove movimentações antigas deste frete
                ContaCorrenteTransportadora.query.filter_by(frete_id=frete.id).delete()

                # Cria nova movimentação
                tipo_mov = "CREDITO" if diferenca > 0 else "DEBITO"
                descricao = f"Frete {frete.id} - CTe {frete.numero_cte} - {motivo}"

                movimentacao = ContaCorrenteTransportadora(
                    transportadora_id=frete.transportadora_id,
                    frete_id=frete.id,
                    tipo_movimentacao=tipo_mov,
                    valor_diferenca=abs(diferenca),
                    valor_credito=diferenca if diferenca > 0 else 0,
                    valor_debito=abs(diferenca) if diferenca < 0 else 0,
                    descricao=descricao,
                    criado_por=current_user.nome,
                )
                db.session.add(movimentacao)

        db.session.commit()
        flash("Frete atualizado com sucesso!", "success")

        # ✅ DETECTA QUAL BOTÃO FOI CLICADO
        acao = request.form.get("acao")

        if acao == "salvar_e_lancar_cte":
            # Redireciona para lançar CTe da mesma fatura
            return redirect(url_for("fretes.lancar_cte", fatura_id=frete.fatura_frete_id))
        elif acao == "salvar_e_visualizar_fatura":
            # Redireciona para visualizar a fatura
            return redirect(url_for("fretes.visualizar_fatura", fatura_id=frete.fatura_frete_id))
        else:
            # Fallback: comportamento original
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

    return render_template("fretes/editar_frete.html", form=form, frete=frete, ctes_sugeridos=ctes_sugeridos)


@fretes_bp.route("/<int:frete_id>/vincular-cte/<int:cte_id>", methods=["POST"])
@login_required
def vincular_cte_ao_frete(frete_id, cte_id):
    """
    Vincula um ConhecimentoTransporte ao Frete via FK
    Chamado via AJAX quando usuário clica em "Usar este CTe"
    """
    try:
        from app.fretes.models import ConhecimentoTransporte
        from datetime import datetime

        # Buscar frete e CTe
        frete = Frete.query.get_or_404(frete_id)
        cte = ConhecimentoTransporte.query.get_or_404(cte_id)

        # ✅ VALIDAÇÃO: CTe já vinculado a outro frete?
        if cte.frete_id and cte.frete_id != frete_id:
            return jsonify({"sucesso": False, "erro": f"Este CTe já está vinculado ao frete #{cte.frete_id}"}), 400

        # ✅ DESVINCULAR CTes antigos deste frete (se houver)
        ConhecimentoTransporte.query.filter_by(frete_id=frete_id).update(
            {"frete_id": None, "vinculado_manualmente": False, "vinculado_em": None, "vinculado_por": None}
        )

        # ✅ VINCULAR novo CTe
        cte.frete_id = frete_id
        cte.vinculado_manualmente = True
        cte.vinculado_em = agora_utc_naive()
        cte.vinculado_por = current_user.nome

        db.session.commit()

        current_app.logger.info(f"✅ CTe {cte.numero_cte} vinculado ao frete #{frete_id} por {current_user.nome}")

        return jsonify(
            {
                "sucesso": True,
                "mensagem": f"CTe {cte.numero_cte} vinculado com sucesso!",
                "cte": {
                    "numero": cte.numero_cte,
                    "serie": cte.serie_cte,
                    "valor_frete": float(cte.valor_frete) if cte.valor_frete else 0,
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Erro ao vincular CTe ao frete: {str(e)}")
        return jsonify({"sucesso": False, "erro": f"Erro ao vincular CTe: {str(e)}"}), 500


@fretes_bp.route("/<int:frete_id>/lancar-odoo", methods=["POST"])
@login_required
@require_financeiro()
def lancar_frete_odoo(frete_id):
    """
    Enfileira lançamento de frete no Odoo (processamento assíncrono)

    Retorna job_id para acompanhamento do status via polling.
    O processamento real é feito pelo worker na fila 'odoo_lancamento'.
    """
    try:
        from app.fretes.workers.lancamento_odoo_jobs import lancar_frete_job
        from app.portal.workers import enqueue_job

        # Buscar frete
        frete = Frete.query.get_or_404(frete_id)

        # ========================================
        # VALIDAÇÃO: Já foi lançado?
        # ========================================
        if frete.status == "LANCADO_ODOO" and frete.odoo_invoice_id:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "Frete já foi lançado no Odoo",
                        "erro": f"Invoice ID: {frete.odoo_invoice_id}",
                    }
                ),
                400,
            )

        # ========================================
        # VALIDAÇÃO: Buscar CTe - PRIORIZA SEMPRE O CTe VINCULADO
        # ========================================
        cte = None
        chave_cte = None

        # PRIORIDADE 1: Vínculo explícito (frete_cte_id) - SEMPRE priorizar
        if frete.frete_cte_id:
            # Tentar pelo relationship primeiro
            cte = frete.cte

            # Se relationship falhar, buscar explicitamente pelo ID
            if not cte:
                cte = db.session.get(ConhecimentoTransporte,frete.frete_cte_id) if frete.frete_cte_id else None

            if cte:
                chave_cte = cte.chave_acesso
                logger.info(f"✅ Usando CTe VINCULADO: {cte.numero_cte} (ID {cte.id})")
            else:
                # CTe vinculado não existe mais
                logger.warning(f"⚠️ CTe vinculado ID {frete.frete_cte_id} não encontrado!")
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "CTe vinculado não encontrado",
                            "erro": f"O CTe vinculado (ID {frete.frete_cte_id}) não existe mais. Vincule outro CTe.",
                        }
                    ),
                    400,
                )

        # PRIORIDADE 2: CTe vinculado via backref (conhecimentos_transporte)
        # Só usa se tiver EXATAMENTE 1 CTe vinculado
        if not cte and frete.conhecimentos_transporte:
            ctes_vinculados = [ct for ct in frete.conhecimentos_transporte if ct.ativo]
            if len(ctes_vinculados) == 1:
                cte = ctes_vinculados[0]
                chave_cte = cte.chave_acesso
                logger.info(f"✅ Usando CTe vinculado (backref): {cte.numero_cte} (ID {cte.id})")
            elif len(ctes_vinculados) > 1:
                # Múltiplos CTes vinculados - requer seleção manual via frete_cte_id
                ctes_info = [f"CTe {c.numero_cte}" for c in ctes_vinculados[:5]]
                ctes_msg = ", ".join(ctes_info)
                if len(ctes_vinculados) > 5:
                    ctes_msg += f" e mais {len(ctes_vinculados) - 5}..."

                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": f"Múltiplos CTes vinculados ({len(ctes_vinculados)}): {ctes_msg}",
                            "erro": "Por favor, selecione manualmente o CTe correto antes de lançar",
                            "error_type": "MULTIPLOS_CTES",
                        }
                    ),
                    400,
                )

        # PRIORIDADE 3: Busca automática por NFs + CNPJ (SOMENTE se não houver CTe vinculado)
        if not cte:
            logger.info("🔍 Buscando CTe por NFs em comum + CNPJ...")
            ctes_relacionados = frete.buscar_ctes_relacionados()

            if not ctes_relacionados:
                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": "Nenhum CTe relacionado encontrado",
                            "erro": "É necessário vincular um CTe manualmente para lançar no Odoo",
                        }
                    ),
                    400,
                )

            if len(ctes_relacionados) > 1:
                # Listar CTes sugeridos na mensagem de erro
                ctes_info = [f"CTe {c.numero_cte}" for c in ctes_relacionados[:5]]
                ctes_msg = ", ".join(ctes_info)
                if len(ctes_relacionados) > 5:
                    ctes_msg += f" e mais {len(ctes_relacionados) - 5}..."

                return (
                    jsonify(
                        {
                            "sucesso": False,
                            "mensagem": f"Múltiplos CTes sugeridos ({len(ctes_relacionados)}): {ctes_msg}",
                            "erro": "Por favor, vincule manualmente o CTe correto antes de lançar",
                            "error_type": "MULTIPLOS_CTES",
                        }
                    ),
                    400,
                )

            cte = ctes_relacionados[0]
            chave_cte = cte.chave_acesso

        if not chave_cte or len(chave_cte) != 44:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "Chave do CTe inválida",
                        "erro": f"Chave possui {len(chave_cte) if chave_cte else 0} caracteres (esperado 44)",
                    }
                ),
                400,
            )

        # Obter data de vencimento (do JSON ou do frete)
        data = request.get_json() or {}
        data_vencimento = data.get("data_vencimento")

        if not data_vencimento and frete.vencimento:
            data_vencimento = frete.vencimento.strftime("%Y-%m-%d")

        # ========================================
        # ENFILEIRAR JOB
        # ========================================
        logger.info(f"📋 Enfileirando lançamento de frete #{frete_id} na fila 'odoo_lancamento'")

        job = enqueue_job(
            lancar_frete_job,
            frete_id,
            current_user.nome,
            request.remote_addr,
            chave_cte,  # Agora opcional (4º param) - job busca automaticamente se None
            data_vencimento,
            queue_name="odoo_lancamento",
            timeout="10m",
        )

        logger.info(f"✅ Job {job.id} enfileirado para frete #{frete_id}")

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "Lançamento enfileirado com sucesso",
                    "job_id": job.id,
                    "frete_id": frete_id,
                    "status": "queued",
                }
            ),
            202,
        )  # 202 Accepted

    except Exception as e:
        logger.error(f"Erro ao enfileirar lançamento de frete: {e}")
        import traceback

        traceback.print_exc()

        return jsonify({"sucesso": False, "mensagem": "Erro ao enfileirar lançamento", "erro": str(e)}), 500


@fretes_bp.route("/<int:frete_id>/auditoria-odoo")
@login_required
def auditoria_odoo(frete_id):
    """
    Exibe a auditoria completa do lançamento no Odoo
    """
    from app.fretes.models import LancamentoFreteOdooAuditoria

    # Buscar frete
    frete = Frete.query.get_or_404(frete_id)

    # Buscar auditorias ordenadas por etapa
    auditorias = (
        LancamentoFreteOdooAuditoria.query.filter_by(frete_id=frete_id)
        .order_by(LancamentoFreteOdooAuditoria.etapa)
        .all()
    )

    if not auditorias:
        flash("Nenhuma auditoria encontrada para este frete. Ele ainda não foi lançado no Odoo.", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

    # Calcular estatísticas
    total_tempo_ms = sum(a.tempo_execucao_ms or 0 for a in auditorias)
    etapas_sucesso = sum(1 for a in auditorias if a.status == "SUCESSO")

    # Calcular erros reais (descontando retentativas que foram corrigidas)
    etapas_erro_total = sum(1 for a in auditorias if a.status == "ERRO")
    etapas_retentativa = 0

    for auditoria in auditorias:
        if auditoria.status == "ERRO":
            # Verificar se há uma etapa de sucesso posterior com mesmo número
            for proxima in auditorias:
                if (
                    proxima.etapa == auditoria.etapa
                    and proxima.status == "SUCESSO"
                    and proxima.executado_em > auditoria.executado_em
                ):
                    etapas_retentativa += 1
                    break

    etapas_erro = etapas_erro_total - etapas_retentativa

    return render_template(
        "fretes/auditoria_odoo.html",
        frete=frete,
        auditorias=auditorias,
        total_tempo_ms=total_tempo_ms,
        etapas_sucesso=etapas_sucesso,
        etapas_retentativa=etapas_retentativa,
        etapas_erro=etapas_erro,
    )


def _calcular_componentes_analise(frete, tabela_dados, transportadora_config):
    """
    Calcula componentes detalhados e resumo para a tela de análise de diferenças.
    Função auxiliar reutilizável para diferentes fontes de tabela (embarque ou cadastrada).

    Args:
        frete: Objeto Frete (para peso_total, valor_total_nfs)
        tabela_dados: Dict normalizado com campos da tabela (sem prefixo)
        transportadora_config: Dict com configurações da transportadora (pós-mínimo, etc.)

    Returns:
        tuple: (componentes, resumo_cotacao, configuracao_info)
    """
    from app.utils.calculadora_frete import CalculadoraFrete

    peso_real = frete.peso_total
    valor_mercadoria = frete.valor_total_nfs

    # Usar calculadora centralizada para obter resultado detalhado
    resultado_calculo = CalculadoraFrete.calcular_frete_unificado(
        peso=peso_real,
        valor_mercadoria=valor_mercadoria,
        tabela_dados=tabela_dados,
        transportadora_optante=tabela_dados.get("transportadora_optante", True),
        transportadora_config=transportadora_config,
        cidade={"icms": tabela_dados.get("icms_destino", 0)},
        codigo_ibge=None,
    )

    # Extrair detalhes do cálculo
    detalhes = resultado_calculo.get("detalhes", {})

    # ========== COMPONENTES DETALHADOS ==========

    # Valores da tabela (agora de tabela_dados, funciona com qualquer fonte)
    tab_valor_kg = tabela_dados.get("valor_kg", 0) or 0
    tab_percentual_valor = tabela_dados.get("percentual_valor", 0) or 0
    tab_frete_minimo_peso = tabela_dados.get("frete_minimo_peso", 0) or 0
    tab_frete_minimo_valor = tabela_dados.get("frete_minimo_valor", 0) or 0
    tab_percentual_gris = tabela_dados.get("percentual_gris", 0) or 0
    tab_percentual_adv = tabela_dados.get("percentual_adv", 0) or 0
    tab_percentual_rca = tabela_dados.get("percentual_rca", 0) or 0
    tab_pedagio_por_100kg = tabela_dados.get("pedagio_por_100kg", 0) or 0

    # Peso considerado
    peso_minimo_tabela = tab_frete_minimo_peso
    peso_considerado = detalhes.get("peso_para_calculo", peso_real)

    # Frete base (peso + valor)
    frete_peso = (peso_considerado * tab_valor_kg) if tab_valor_kg else 0
    frete_valor = (
        (valor_mercadoria * (tab_percentual_valor / 100)) if tab_percentual_valor else 0
    )
    frete_base = detalhes.get("frete_base", frete_peso + frete_valor)

    # Componentes adicionais (com valores mínimos aplicados)
    gris = detalhes.get("gris", 0)
    adv = detalhes.get("adv", 0)
    rca = detalhes.get("rca", 0)
    pedagio = detalhes.get("pedagio", 0)
    tas = detalhes.get("valor_tas", 0)
    despacho = detalhes.get("valor_despacho", 0)
    valor_cte_tabela = detalhes.get("valor_cte", 0)

    # Componentes antes e depois do mínimo
    componentes_antes = detalhes.get("componentes_antes_minimo", 0)
    componentes_depois = detalhes.get("componentes_apos_minimo", 0)

    # Totais
    total_liquido_antes_minimo = detalhes.get("frete_liquido_antes_minimo", 0)
    total_liquido = resultado_calculo.get("valor_bruto", 0)  # Valor sem ICMS após mínimo
    total_bruto_cotacao = resultado_calculo.get("valor_com_icms", 0)
    valor_liquido_transportadora = resultado_calculo.get("valor_liquido", 0)

    # ICMS
    percentual_icms_cotacao = resultado_calculo.get("icms_aplicado", 0)
    valor_icms_cotacao = total_bruto_cotacao - total_liquido if percentual_icms_cotacao > 0 else 0

    # Ajuste de mínimo
    frete_minimo_valor = tab_frete_minimo_valor
    ajuste_minimo_valor = max(0, frete_minimo_valor - total_liquido_antes_minimo)

    # Informações sobre pedágio
    if tab_pedagio_por_100kg and peso_considerado > 0:
        if transportadora_config.get("pedagio_por_fracao", True):
            fracoes_100kg = float(math.ceil(peso_considerado / 100))
            tipo_pedagio = "por fração"
        else:
            fracoes_100kg = peso_considerado / 100
            tipo_pedagio = "direto"
    else:
        fracoes_100kg = 0
        tipo_pedagio = "não aplicado"

    # ========== MONTAGEM DOS COMPONENTES PARA VISUALIZAÇÃO ==========

    componentes = [
        {
            "nome": "Peso Considerado",
            "valor_tabela": f"Mín: {peso_minimo_tabela:.2f} kg",
            "valor_usado": f"{peso_real:.2f} kg",
            "formula": f"max({peso_real:.2f}, {peso_minimo_tabela:.2f})",
            "valor_calculado": peso_considerado,
            "unidade": "kg",
            "tipo": "peso",
        },
        {
            "nome": "Frete por Peso",
            "valor_tabela": f"R$ {tab_valor_kg:.4f}/kg",
            "valor_usado": f"{peso_considerado:.2f} kg",
            "formula": f"{peso_considerado:.2f} × {tab_valor_kg:.4f}",
            "valor_calculado": frete_peso,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 0,
            "pos_minimo": False,
        },
        {
            "nome": "Frete por Valor (%)",
            "valor_tabela": f"{tab_percentual_valor:.2f}%",
            "valor_usado": f"R$ {valor_mercadoria:.2f}",
            "formula": f"{valor_mercadoria:.2f} × {tab_percentual_valor:.2f}%",
            "valor_calculado": frete_valor,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 1,
            "pos_minimo": False,
        },
        {
            "nome": "Frete Base",
            "valor_tabela": "Peso + Valor",
            "valor_usado": f"R$ {frete_peso:.2f} + R$ {frete_valor:.2f}",
            "formula": f"{frete_peso:.2f} + {frete_valor:.2f}",
            "valor_calculado": frete_base,
            "unidade": "R$",
            "tipo": "subtotal",
            "pos_minimo": False,
        },
    ]

    # GRIS com indicação de mínimo e posição
    gris_minimo = tabela_dados.get("gris_minimo", 0) or 0
    gris_calculado = (
        (valor_mercadoria * (tab_percentual_gris / 100)) if tab_percentual_gris else 0
    )
    componentes.append(
        {
            "nome": f'GRIS {"(PÓS-MÍNIMO)" if transportadora_config["aplica_gris_pos_minimo"] else ""}',
            "valor_tabela": f"{tab_percentual_gris:.2f}% (Mín: R$ {gris_minimo:.2f})",
            "valor_usado": f"R$ {valor_mercadoria:.2f}",
            "formula": f"max({valor_mercadoria:.2f} × {tab_percentual_gris:.2f}%, {gris_minimo:.2f})",
            "valor_calculado": gris,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 2,
            "pos_minimo": transportadora_config["aplica_gris_pos_minimo"],
            "tem_minimo": gris_minimo > 0,
            "valor_sem_minimo": gris_calculado,
        }
    )

    # ADV com indicação de mínimo e posição
    adv_minimo = tabela_dados.get("adv_minimo", 0) or 0
    adv_calculado = (
        (valor_mercadoria * (tab_percentual_adv / 100)) if tab_percentual_adv else 0
    )
    componentes.append(
        {
            "nome": f'ADV {"(PÓS-MÍNIMO)" if transportadora_config["aplica_adv_pos_minimo"] else ""}',
            "valor_tabela": f"{tab_percentual_adv:.2f}% (Mín: R$ {adv_minimo:.2f})",
            "valor_usado": f"R$ {valor_mercadoria:.2f}",
            "formula": f"max({valor_mercadoria:.2f} × {tab_percentual_adv:.2f}%, {adv_minimo:.2f})",
            "valor_calculado": adv,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 3,
            "pos_minimo": transportadora_config["aplica_adv_pos_minimo"],
            "tem_minimo": adv_minimo > 0,
            "valor_sem_minimo": adv_calculado,
        }
    )

    # RCA
    componentes.append(
        {
            "nome": f'RCA {"(PÓS-MÍNIMO)" if transportadora_config["aplica_rca_pos_minimo"] else ""}',
            "valor_tabela": f"{tab_percentual_rca:.2f}%",
            "valor_usado": f"R$ {valor_mercadoria:.2f}",
            "formula": f"{valor_mercadoria:.2f} × {tab_percentual_rca:.2f}%",
            "valor_calculado": rca,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 4,
            "pos_minimo": transportadora_config["aplica_rca_pos_minimo"],
        }
    )

    # Pedágio com tipo de cálculo
    componentes.append(
        {
            "nome": f'Pedágio ({tipo_pedagio}) {"(PÓS-MÍNIMO)" if transportadora_config["aplica_pedagio_pos_minimo"] else ""}',
            "valor_tabela": f"R$ {tab_pedagio_por_100kg:.2f}/100kg",
            "valor_usado": f'{peso_considerado:.2f} kg = {fracoes_100kg:.2f} {"frações" if transportadora_config["pedagio_por_fracao"] else "× 100kg"}',
            "formula": f"{fracoes_100kg:.2f} × R$ {tab_pedagio_por_100kg:.2f}",
            "valor_calculado": pedagio,
            "unidade": "R$",
            "tipo": "valor",
            "input_index": 5,
            "pos_minimo": transportadora_config["aplica_pedagio_pos_minimo"],
        }
    )

    # Valores fixos - Sempre mostrar todos para consistência
    current_input_index = 6
    for nome, valor, campo_config in [
        ("TAS", tas, "aplica_tas_pos_minimo"),
        ("Despacho", despacho, "aplica_despacho_pos_minimo"),
        ("CT-e", valor_cte_tabela, "aplica_cte_pos_minimo"),
    ]:
        componentes.append(
            {
                "nome": f'{nome} (fixo) {"(PÓS-MÍNIMO)" if transportadora_config[campo_config] else ""}',
                "valor_tabela": f"R$ {valor:.2f}",
                "valor_usado": "Valor fixo",
                "formula": "Valor fixo",
                "valor_calculado": valor,
                "unidade": "R$",
                "tipo": "valor",
                "input_index": current_input_index,
                "pos_minimo": transportadora_config[campo_config],
            }
        )
        current_input_index += 1

    # Subtotal antes do mínimo
    componentes.append(
        {
            "nome": "Subtotal ANTES do Mínimo",
            "valor_tabela": "Componentes pré-mínimo",
            "valor_usado": f"Base + componentes",
            "formula": f"Base ({frete_base:.2f}) + Componentes ({componentes_antes:.2f})",
            "valor_calculado": total_liquido_antes_minimo,
            "unidade": "R$",
            "tipo": "subtotal_pre",
        }
    )

    # Aplicação do frete mínimo
    componentes.append(
        {
            "nome": "Aplicação Frete Mínimo",
            "valor_tabela": f"Mín: R$ {frete_minimo_valor:.2f}",
            "valor_usado": f"R$ {total_liquido_antes_minimo:.2f}",
            "formula": f"max({total_liquido_antes_minimo:.2f}, {frete_minimo_valor:.2f})",
            "valor_calculado": max(total_liquido_antes_minimo, frete_minimo_valor),
            "unidade": "R$",
            "tipo": "ajuste",
            "observacao": f"Ajuste de R$ {ajuste_minimo_valor:.2f}" if ajuste_minimo_valor > 0 else "Sem ajuste",
        }
    )

    # Componentes pós-mínimo (se houver)
    if componentes_depois > 0:
        componentes.append(
            {
                "nome": "Componentes PÓS-MÍNIMO",
                "valor_tabela": "Soma pós-mínimo",
                "valor_usado": "Calculado",
                "formula": "Componentes aplicados após mínimo",
                "valor_calculado": componentes_depois,
                "unidade": "R$",
                "tipo": "subtotal_pos",
            }
        )

    # Total líquido final
    componentes.append(
        {
            "nome": "TOTAL LÍQUIDO (sem ICMS)",
            "valor_tabela": "Final",
            "valor_usado": "Calculado",
            "formula": f"Após mínimo ({max(total_liquido_antes_minimo, frete_minimo_valor):.2f}) + Pós ({componentes_depois:.2f})",
            "valor_calculado": total_liquido,
            "unidade": "R$",
            "tipo": "total",
        }
    )

    # ICMS
    icms_proprio = tabela_dados.get("icms_proprio")
    fonte_icms = "ICMS Tabela Comercial" if icms_proprio and icms_proprio > 0 else "ICMS Legislação"

    if percentual_icms_cotacao > 0:
        componentes.append(
            {
                "nome": f"{fonte_icms}",
                "valor_tabela": f"{percentual_icms_cotacao * 100:.2f}%",
                "valor_usado": f"R$ {total_liquido:.2f}",
                "formula": f"{total_liquido:.2f} / (1 - {percentual_icms_cotacao:.4f}) - {total_liquido:.2f}",
                "valor_calculado": valor_icms_cotacao,
                "unidade": "R$",
                "tipo": "icms",
                "fonte": fonte_icms,
            }
        )

    # Total bruto
    componentes.append(
        {
            "nome": "TOTAL BRUTO (com ICMS)",
            "valor_tabela": "Final",
            "valor_usado": "Calculado",
            "formula": f"{total_liquido:.2f} + {valor_icms_cotacao:.2f}",
            "valor_calculado": total_bruto_cotacao,
            "unidade": "R$",
            "tipo": "total_final",
        }
    )

    # Informações adicionais sobre a configuração
    configuracao_info = {
        "transportadora_optante": tabela_dados.get("transportadora_optante", True),
        "icms_proprio": icms_proprio,
        "fonte_icms": fonte_icms,
        "componentes_pre": componentes_antes,
        "componentes_pos": componentes_depois,
        "pedagio_tipo": tipo_pedagio,
        "tem_ajuste_minimo": ajuste_minimo_valor > 0,
        "valor_ajuste": ajuste_minimo_valor,
    }

    # Resumos
    resumo_cotacao = {
        "total_liquido": total_liquido,
        "percentual_icms": percentual_icms_cotacao,
        "valor_icms": valor_icms_cotacao,
        "total_bruto": total_bruto_cotacao,
        "valor_liquido_transportadora": valor_liquido_transportadora,
    }

    return componentes, resumo_cotacao, configuracao_info


@fretes_bp.route("/analise-diferencas/<int:frete_id>")
@login_required
def analise_diferencas(frete_id):
    """Mostra análise detalhada das diferenças com dados da tabela - com toggle Embarque/Cadastrada"""
    frete = Frete.query.get_or_404(frete_id)

    from app.utils.tabela_frete_manager import TabelaFreteManager

    # Buscar configuração da transportadora (NÃO muda entre fontes)
    transportadora_config = {
        "aplica_gris_pos_minimo": False,
        "aplica_adv_pos_minimo": False,
        "aplica_rca_pos_minimo": False,
        "aplica_pedagio_pos_minimo": False,
        "aplica_tas_pos_minimo": False,
        "aplica_despacho_pos_minimo": False,
        "aplica_cte_pos_minimo": False,
        "pedagio_por_fracao": True,
    }

    if frete.transportadora:
        transp = frete.transportadora
        if hasattr(transp, "aplica_gris_pos_minimo"):
            transportadora_config = {
                "aplica_gris_pos_minimo": transp.aplica_gris_pos_minimo or False,
                "aplica_adv_pos_minimo": transp.aplica_adv_pos_minimo or False,
                "aplica_rca_pos_minimo": transp.aplica_rca_pos_minimo or False,
                "aplica_pedagio_pos_minimo": transp.aplica_pedagio_pos_minimo or False,
                "aplica_tas_pos_minimo": transp.aplica_tas_pos_minimo or False,
                "aplica_despacho_pos_minimo": transp.aplica_despacho_pos_minimo or False,
                "aplica_cte_pos_minimo": transp.aplica_cte_pos_minimo or False,
                "pedagio_por_fracao": transp.pedagio_por_fracao if hasattr(transp, "pedagio_por_fracao") else True,
            }

    # ========== FONTE 1: Tabela Embarque (dados fixados no fechamento) ==========
    tabela_dados_embarque = TabelaFreteManager.preparar_dados_tabela(frete)
    tabela_dados_embarque["icms_destino"] = frete.tabela_icms_destino
    tabela_dados_embarque["transportadora_optante"] = frete.transportadora.optante if frete.transportadora else True

    componentes_embarque, resumo_embarque, config_info_embarque = _calcular_componentes_analise(
        frete, tabela_dados_embarque, transportadora_config
    )

    # ========== FONTE 2: Tabela Cadastrada (com reavaliação de vínculo integrada) ==========
    # Estratégia: primeiro tenta resolver via CidadeAtendida (vínculo atual).
    # Se encontrar, usa essa tabela como "cadastrada" (pode ser diferente da congelada).
    # Se não encontrar, faz fallback pelo nome_tabela congelado no frete.
    tabela_cadastrada = None
    tabela_nao_encontrada = False
    componentes_cadastrada = None
    resumo_cadastrada = None
    tabela_dados_cadastrada = None
    reavaliacao_info = None

    from app.tabelas.models import TabelaFrete as TabelaFreteModel
    from sqlalchemy import func as sa_func
    from app.vinculos.models import CidadeAtendida
    from app.utils.localizacao import LocalizacaoService

    try:
        tabela_via_vinculo = None  # Tabela encontrada via reavaliação de vínculo

        if frete.tipo_carga == 'FRACIONADA':
            # --- REAVALIAÇÃO FRACIONADA ---
            # 1. Buscar todas as nome_tabela disponíveis em TabelaFrete
            tabelas_disponiveis = TabelaFreteModel.query.filter(
                TabelaFreteModel.transportadora_id == frete.transportadora_id,
                TabelaFreteModel.uf_destino == frete.uf_destino,
                TabelaFreteModel.tipo_carga == frete.tipo_carga,
                TabelaFreteModel.modalidade == frete.modalidade,
            ).with_entities(TabelaFreteModel.nome_tabela).distinct().all()
            lista_nome_tabela = [t[0] for t in tabelas_disponiveis]

            if lista_nome_tabela:
                # 2. Resolver cidade do frete
                cidade = LocalizacaoService.buscar_cidade_por_nome(frete.cidade_destino, frete.uf_destino)
                if cidade:
                    # 3. Buscar vínculo atual em CidadeAtendida
                    vinculo = CidadeAtendida.query.filter(
                        CidadeAtendida.cidade_id == cidade.id,
                        CidadeAtendida.transportadora_id == frete.transportadora_id,
                        CidadeAtendida.nome_tabela.in_(lista_nome_tabela),
                    ).first()

                    if vinculo:
                        # 4. Buscar TabelaFrete completa com nome_tabela do vínculo
                        tabela_via_vinculo = TabelaFreteModel.query.filter(
                            TabelaFreteModel.transportadora_id == frete.transportadora_id,
                            sa_func.upper(sa_func.trim(TabelaFreteModel.nome_tabela)) == sa_func.upper(sa_func.trim(vinculo.nome_tabela)),
                            TabelaFreteModel.uf_origem == 'SP',
                            TabelaFreteModel.uf_destino == frete.uf_destino,
                            TabelaFreteModel.tipo_carga == frete.tipo_carga,
                            TabelaFreteModel.modalidade == frete.modalidade,
                        ).first()

                        if tabela_via_vinculo:
                            nome_tabela_original = (frete.tabela_nome_tabela or '').strip()
                            nome_tabela_atual = (vinculo.nome_tabela or '').strip()
                            reavaliacao_info = {
                                'nome_tabela_original': nome_tabela_original,
                                'nome_tabela_atual': nome_tabela_atual,
                                'mudou': nome_tabela_original.upper() != nome_tabela_atual.upper(),
                                'cidade_resolvida': cidade.nome,
                                'cidade_uf': cidade.uf,
                                'tipo': 'FRACIONADA',
                                'tabelas_avaliadas': 1,
                                'icms_cidade': cidade.icms,
                            }

        elif frete.tipo_carga == 'DIRETA':
            # --- REAVALIAÇÃO DIRETA ---
            # 1. Obter itens ativos do embarque
            itens = [i for i in frete.embarque.itens if i.status == 'ativo']
            if itens:
                # 2. Para cada item, coletar vínculos atualizados
                tabelas_candidatas = set()
                cidades_resolvidas = []
                cidades_nao_resolvidas = []

                for item in itens:
                    cidade_item = LocalizacaoService.buscar_cidade_por_nome(item.cidade_destino, item.uf_destino)
                    if not cidade_item:
                        cidades_nao_resolvidas.append(f"{item.cidade_destino}/{item.uf_destino}")
                        continue

                    cidades_resolvidas.append(f"{cidade_item.nome}/{cidade_item.uf}")

                    # Buscar TabelaFrete disponíveis para este item
                    tabelas_item = TabelaFreteModel.query.filter(
                        TabelaFreteModel.transportadora_id == frete.transportadora_id,
                        TabelaFreteModel.uf_destino == item.uf_destino,
                        TabelaFreteModel.tipo_carga == 'DIRETA',
                        TabelaFreteModel.modalidade == frete.modalidade,
                    ).with_entities(TabelaFreteModel.nome_tabela).distinct().all()
                    nomes_tabela_item = [t[0] for t in tabelas_item]

                    if nomes_tabela_item:
                        vinculos_item = CidadeAtendida.query.filter(
                            CidadeAtendida.cidade_id == cidade_item.id,
                            CidadeAtendida.transportadora_id == frete.transportadora_id,
                            CidadeAtendida.nome_tabela.in_(nomes_tabela_item),
                        ).all()
                        for v in vinculos_item:
                            tabelas_candidatas.add(v.nome_tabela)

                if tabelas_candidatas:
                    # 3. Para CADA candidata, simular cálculo e selecionar a MAIS CARA
                    from app.utils.calculadora_frete import CalculadoraFrete

                    melhor_tabela = None
                    melhor_valor_bruto = -1
                    melhor_tabela_obj = None

                    for nome_tabela_candidata in tabelas_candidatas:
                        tabela_obj = TabelaFreteModel.query.filter(
                            TabelaFreteModel.transportadora_id == frete.transportadora_id,
                            sa_func.upper(sa_func.trim(TabelaFreteModel.nome_tabela)) == sa_func.upper(sa_func.trim(nome_tabela_candidata)),
                            TabelaFreteModel.uf_origem == 'SP',
                            TabelaFreteModel.uf_destino == frete.uf_destino,
                            TabelaFreteModel.tipo_carga == 'DIRETA',
                            TabelaFreteModel.modalidade == frete.modalidade,
                        ).first()

                        if not tabela_obj:
                            continue

                        dados_candidata = TabelaFreteManager.preparar_dados_tabela(tabela_obj)
                        dados_candidata["transportadora_optante"] = frete.transportadora.optante if frete.transportadora else True
                        dados_candidata["icms_destino"] = frete.tabela_icms_destino or 0

                        resultado_calculo = CalculadoraFrete.calcular_frete_unificado(
                            peso=frete.peso_total,
                            valor_mercadoria=frete.valor_total_nfs,
                            tabela_dados=dados_candidata,
                            transportadora_optante=dados_candidata.get("transportadora_optante", True),
                            transportadora_config=transportadora_config,
                            cidade={"icms": dados_candidata.get("icms_destino", 0)},
                            codigo_ibge=None,
                        )

                        valor_bruto = resultado_calculo.get("valor_bruto", 0) or 0
                        if valor_bruto > melhor_valor_bruto:
                            melhor_valor_bruto = valor_bruto
                            melhor_tabela = nome_tabela_candidata
                            melhor_tabela_obj = tabela_obj

                    if melhor_tabela_obj:
                        tabela_via_vinculo = melhor_tabela_obj

                        nome_tabela_original = (frete.tabela_nome_tabela or '').strip()
                        nome_tabela_atual = (melhor_tabela or '').strip()
                        reavaliacao_info = {
                            'nome_tabela_original': nome_tabela_original,
                            'nome_tabela_atual': nome_tabela_atual,
                            'mudou': nome_tabela_original.upper() != nome_tabela_atual.upper(),
                            'cidades_resolvidas': cidades_resolvidas,
                            'cidades_nao_resolvidas': cidades_nao_resolvidas,
                            'todas_cidades_resolvidas': len(cidades_nao_resolvidas) == 0,
                            'tipo': 'DIRETA',
                            'tabelas_avaliadas': len(tabelas_candidatas),
                        }

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Erro na reavaliação de vínculo para frete #{frete.id}: {e}")
        tabela_via_vinculo = None

    # Decidir qual tabela usar como "cadastrada":
    # Prioridade 1: tabela via reavaliação de vínculo (CidadeAtendida)
    # Prioridade 2: tabela pelo nome_tabela congelado (fallback)
    if tabela_via_vinculo:
        tabela_cadastrada = tabela_via_vinculo
        tabela_dados_cadastrada = TabelaFreteManager.preparar_dados_tabela(tabela_cadastrada)
        # Para FRACIONADA com cidade resolvida, usar ICMS da cidade atual
        if reavaliacao_info and reavaliacao_info.get('icms_cidade'):
            tabela_dados_cadastrada["icms_destino"] = reavaliacao_info['icms_cidade']
        else:
            tabela_dados_cadastrada["icms_destino"] = frete.tabela_icms_destino or 0
        tabela_dados_cadastrada["transportadora_optante"] = frete.transportadora.optante if frete.transportadora else True

        componentes_cadastrada, resumo_cadastrada, _ = _calcular_componentes_analise(
            frete, tabela_dados_cadastrada, transportadora_config
        )
    else:
        # Fallback: buscar pelo nome_tabela congelado no frete
        tabela_cadastrada = TabelaFreteModel.query.filter(
            TabelaFreteModel.transportadora_id == frete.transportadora_id,
            sa_func.upper(sa_func.trim(TabelaFreteModel.nome_tabela)) == sa_func.upper(sa_func.trim(frete.tabela_nome_tabela or '')),
            TabelaFreteModel.uf_origem == 'SP',
            TabelaFreteModel.uf_destino == frete.uf_destino,
            TabelaFreteModel.tipo_carga == frete.tipo_carga,
            TabelaFreteModel.modalidade == frete.modalidade,
        ).first()

        if tabela_cadastrada:
            tabela_dados_cadastrada = TabelaFreteManager.preparar_dados_tabela(tabela_cadastrada)
            tabela_dados_cadastrada["icms_destino"] = frete.tabela_icms_destino
            tabela_dados_cadastrada["transportadora_optante"] = frete.transportadora.optante if frete.transportadora else True

            componentes_cadastrada, resumo_cadastrada, _ = _calcular_componentes_analise(
                frete, tabela_dados_cadastrada, transportadora_config
            )
        else:
            tabela_nao_encontrada = True

    # ========== RENDER ==========
    resumo_cte = {"total_liquido": None, "percentual_icms": None, "valor_icms": None, "total_bruto": frete.valor_cte}

    return render_template(
        "fretes/analise_diferencas.html",
        frete=frete,
        # Dados Embarque (padrão - renderizados no HTML)
        componentes=componentes_embarque,
        tabela_dados=tabela_dados_embarque,
        resumo_cotacao=resumo_embarque,
        configuracao_info=config_info_embarque,
        # Dados Cadastrada (com reavaliação integrada, injetados como JSON para JS)
        componentes_cadastrada=componentes_cadastrada,
        tabela_dados_cadastrada=tabela_dados_cadastrada,
        resumo_cadastrada=resumo_cadastrada,
        reavaliacao_info=reavaliacao_info,
        # Controle
        resumo_cte=resumo_cte,
        transportadora_config=transportadora_config,
        tabela_nao_encontrada=tabela_nao_encontrada,
        tabela_cadastrada=tabela_cadastrada,
    )


# =================== FATURAS DE FRETE ===================


@fretes_bp.route("/faturas")
@login_required
@require_financeiro()  # 🔒 BLOQUEADO para vendedores
def listar_faturas():
    """Lista faturas de frete com filtros"""
    form = FiltroFaturasForm(request.args)

    # Popular choices de transportadoras no formulário
    transportadoras = Transportadora.query.all()
    form.transportadora_id.choices = [("", "Todas as transportadoras")] + [
        (t.id, t.razao_social) for t in transportadoras
    ]

    query = FaturaFrete.query

    # Aplicar filtros
    if form.numero_fatura.data:
        query = query.filter(FaturaFrete.numero_fatura.ilike(f"%{form.numero_fatura.data}%"))

    if form.transportadora_id.data:
        try:
            transportadora_id = int(form.transportadora_id.data)
            query = query.filter(FaturaFrete.transportadora_id == transportadora_id)
        except (ValueError, TypeError):
            pass

    if form.numero_nf.data:
        # Busca faturas que contêm fretes com esta NF
        faturas_com_nf = (
            db.session.query(Frete.fatura_frete_id)
            .filter(Frete.numeros_nfs.contains(form.numero_nf.data), Frete.fatura_frete_id.isnot(None))
            .distinct()
            .subquery()
        )
        query = query.filter(FaturaFrete.id.in_(faturas_com_nf))

    if form.status_conferencia.data:
        query = query.filter(FaturaFrete.status_conferencia == form.status_conferencia.data)

    if form.data_emissao_de.data:
        query = query.filter(FaturaFrete.data_emissao >= form.data_emissao_de.data)

    if form.data_emissao_ate.data:
        query = query.filter(FaturaFrete.data_emissao <= form.data_emissao_ate.data)

    if form.data_vencimento_de.data:
        query = query.filter(FaturaFrete.vencimento >= form.data_vencimento_de.data)

    if form.data_vencimento_ate.data:
        query = query.filter(FaturaFrete.vencimento <= form.data_vencimento_ate.data)

    faturas = query.order_by(desc(FaturaFrete.criado_em)).paginate(
        page=request.args.get("page", 1, type=int), per_page=20, error_out=False
    )

    return render_template("fretes/listar_faturas.html", faturas=faturas, form=form)


@fretes_bp.route("/api/transportadoras/buscar")
@login_required
def api_buscar_transportadoras():
    """Busca transportadoras para autocomplete com suporte a grupo empresarial.

    Se a busca encontrar uma transportadora que pertence a um grupo,
    retorna tambem as demais do mesmo grupo (identificadas por badge).
    Busca por: razao_social, CNPJ, ou nome do grupo.
    """
    busca = request.args.get('busca', '')
    try:
        from app.transportadoras.models import GrupoTransportadora

        query = db.session.query(Transportadora).filter(
            Transportadora.ativo == True  # noqa: E712
        )
        if busca:
            busca_like = f'%{busca}%'

            # IDs de grupos cujo nome bate com a busca
            grupos_match = db.session.query(GrupoTransportadora.id).filter(
                GrupoTransportadora.nome.ilike(busca_like),
                GrupoTransportadora.ativo == True  # noqa: E712
            ).subquery()

            query = query.filter(
                or_(
                    Transportadora.razao_social.ilike(busca_like),
                    Transportadora.cnpj.ilike(busca_like),
                    Transportadora.grupo_transportadora_id.in_(
                        db.session.query(grupos_match.c.id)
                    ),
                )
            )

        # Buscar resultados primarios
        query = query.order_by(Transportadora.razao_social).limit(50)
        transportadoras = query.all()

        # Expandir grupos: se uma transportadora pertence a um grupo,
        # incluir as demais do grupo (que nao estejam ja no resultado)
        ids_resultado = {t.id for t in transportadoras}
        grupo_ids = {t.grupo_transportadora_id for t in transportadoras if t.grupo_transportadora_id}

        membros_grupo = []
        if grupo_ids:
            membros_grupo = Transportadora.query.filter(
                Transportadora.grupo_transportadora_id.in_(grupo_ids),
                Transportadora.ativo == True,  # noqa: E712
                ~Transportadora.id.in_(ids_resultado),
            ).order_by(Transportadora.razao_social).all()

        # Montar resultado com info de grupo
        resultado = []
        for t in transportadoras:
            item = {
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
                'freteiro': getattr(t, 'freteiro', False),
                'grupo': t.grupo.nome if t.grupo_transportadora_id and t.grupo else None,
            }
            resultado.append(item)

        # Adicionar membros do grupo (marcados como expansao)
        for t in membros_grupo:
            resultado.append({
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
                'freteiro': getattr(t, 'freteiro', False),
                'grupo': t.grupo.nome if t.grupo_transportadora_id and t.grupo else None,
                'via_grupo': True,
            })

        return jsonify({'sucesso': True, 'transportadoras': resultado})
    except Exception as e:
        logging.getLogger(__name__).error(f"Erro ao buscar transportadoras: {e}")
        return jsonify({'erro': str(e)}), 500


@fretes_bp.route("/faturas/nova", methods=["GET", "POST"])
@login_required
def nova_fatura():
    """Cadastra nova fatura de frete"""
    form = FaturaFreteForm()
    if form.validate_on_submit():
        nova_fatura = FaturaFrete(
            transportadora_id=request.form.get("transportadora_id"),
            numero_fatura=form.numero_fatura.data,
            data_emissao=form.data_emissao.data,
            valor_total_fatura=converter_valor_brasileiro(form.valor_total_fatura.data),
            vencimento=form.vencimento.data,
            observacoes_conferencia=form.observacoes_conferencia.data,
            criado_por=current_user.nome,
        )

        # Upload do arquivo PDF
        if form.arquivo_pdf.data:
            try:
                # 🌐 Usar sistema S3 para salvar PDFs
                from app.utils.file_storage import get_file_storage

                storage = get_file_storage()

                file_path = storage.save_file(file=form.arquivo_pdf.data, folder="faturas", allowed_extensions=["pdf"])

                if file_path:
                    nova_fatura.arquivo_pdf = file_path
                else:
                    flash("❌ Erro ao salvar arquivo PDF da fatura.", "danger")
                    return render_template("fretes/nova_fatura.html", form=form)

            except Exception as e:
                flash(f"❌ Erro ao salvar PDF: {str(e)}", "danger")
                return render_template("fretes/nova_fatura.html", form=form)

        db.session.add(nova_fatura)
        db.session.commit()

        flash("Fatura cadastrada com sucesso!", "success")
        return redirect(url_for("fretes.listar_faturas"))

    return render_template("fretes/nova_fatura.html", form=form)


@fretes_bp.route("/faturas/<int:fatura_id>/conferir")
@login_required
def conferir_fatura(fatura_id):
    """Inicia o processo de conferência de uma fatura"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    # Busca todos os CTes (fretes) da fatura
    fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()

    # ✅ Busca despesas extras vinculadas a esta fatura via FK
    despesas_extras = DespesaExtra.query.filter_by(fatura_frete_id=fatura.id).all()

    # Analisa status dos documentos
    documentos_status = []
    valor_total_cotado = 0
    valor_total_cte = 0
    valor_total_considerado = 0
    valor_total_pago = 0

    # Analisa CTes
    for frete in fretes:
        # ✅ LÓGICA ORIGINAL RESTRITIVA (CORRIGIDA):
        # CTe é considerado LANÇADO apenas se tem número, valor E valor_pago
        if frete.numero_cte and frete.valor_cte and frete.valor_pago:
            status_doc = "LANÇADO"
        elif frete.status in ["APROVADO", "CONFERIDO"]:
            status_doc = "APROVADO"
        else:
            status_doc = "PENDENTE"

        # ✅ DEBUG: Mostra detalhes do CTe
        print(
            f"  CTe Frete #{frete.id}: numero_cte={frete.numero_cte}, valor_cte={frete.valor_cte}, valor_pago={frete.valor_pago}, status_frete={frete.status} → STATUS: {status_doc}"
        )

        documentos_status.append(
            {
                "tipo": "CTe",
                "numero": frete.numero_cte or f"Frete #{frete.id}",
                "valor_cotado": frete.valor_cotado or 0,
                "valor_cte": frete.valor_cte or 0,
                "valor_considerado": frete.valor_considerado or 0,
                "valor_pago": frete.valor_pago or 0,
                "status": status_doc,
                "cliente": frete.nome_cliente,
                "frete_id": frete.id,
            }
        )

        valor_total_cotado += frete.valor_cotado or 0
        valor_total_cte += frete.valor_cte or 0
        valor_total_considerado += frete.valor_considerado or 0
        valor_total_pago += frete.valor_pago or 0

    # Analisa Despesas Extras
    for despesa in despesas_extras:
        # ✅ LÓGICA ATUALIZADA: Verifica FK em vez de observações
        # Despesa é considerada LANÇADA apenas se tem documento preenchido E está vinculada à fatura
        if (
            despesa.numero_documento
            and despesa.numero_documento != "PENDENTE_FATURA"
            and despesa.valor_despesa
            and despesa.fatura_frete_id is not None
        ):
            status_doc = "LANÇADO"
        else:
            status_doc = "PENDENTE"

        # ✅ DEBUG: Mostra detalhes da despesa
        fatura_vinculada = "SIM" if despesa.fatura_frete_id is not None else "NÃO"
        documento_ok = "SIM" if (despesa.numero_documento and despesa.numero_documento != "PENDENTE_FATURA") else "NÃO"
        print(
            f"  Despesa #{despesa.id}: numero_documento={despesa.numero_documento}, valor={despesa.valor_despesa}, fatura_vinculada={fatura_vinculada}, documento_ok={documento_ok} → STATUS: {status_doc}"
        )

        # ✅ Identifica se despesa tem fatura vinculada via FK
        cliente_obs = "Despesa Extra"
        if despesa.fatura_frete_id:
            fatura_vinculada_obj = db.session.get(FaturaFrete,despesa.fatura_frete_id) if despesa.fatura_frete_id else None
            if fatura_vinculada_obj:
                cliente_obs = f"Despesa Extra (Fatura: {fatura_vinculada_obj.numero_fatura})"

        documentos_status.append(
            {
                "tipo": "Despesa",
                "numero": despesa.numero_documento or f"Despesa #{despesa.id}",
                "valor_cotado": despesa.valor_despesa or 0,  # ✅ CORRIGIDO: DespesaExtra não tem valor_cotado
                "valor_cte": despesa.valor_despesa,
                "valor_considerado": despesa.valor_despesa,
                "valor_pago": despesa.valor_despesa,
                "status": status_doc,
                "cliente": cliente_obs,
                "despesa_id": despesa.id,
            }
        )

        valor_total_cotado += despesa.valor_despesa or 0  # ✅ CORRIGIDO: usar valor_despesa
        valor_total_cte += despesa.valor_despesa
        valor_total_considerado += despesa.valor_despesa
        valor_total_pago += despesa.valor_despesa

    # ✅ DEBUG: Conta documentos por status para diagnóstico
    status_count = {}
    for doc in documentos_status:
        status = doc["status"]
        status_count[status] = status_count.get(status, 0) + 1

    # ✅ DEBUG DETALHADO: Log da análise de status
    print(f"\n=== DEBUG CONFERÊNCIA FATURA {fatura.numero_fatura} ===")
    print(f"Total documentos analisados: {len(documentos_status)}")
    print(f"CTes encontrados: {len([d for d in documentos_status if d['tipo'] == 'CTe'])}")
    print(f"Despesas encontradas: {len([d for d in documentos_status if d['tipo'] == 'Despesa'])}")
    print(f"Status count: {status_count}")

    # ✅ DEBUG: Lista todos os documentos e seus status
    print("Detalhes dos documentos:")
    for i, doc in enumerate(documentos_status, 1):
        print(f"  {i}. {doc['tipo']} - {doc['numero']} - STATUS: {doc['status']} - Cliente: {doc['cliente']}")

    # ✅ DEBUG: Validação detalhada por documento
    print("DEBUG VALIDAÇÃO DETALHADA:")
    for doc in documentos_status:
        status_ok = doc["status"] in ["APROVADO", "LANÇADO"]
        print(f"  - {doc['tipo']} {doc['numero']}: status='{doc['status']}' → Válido: {status_ok}")

    # ✅ DEBUG: Validação final
    todos_aprovados_calc = all(doc["status"] in ["APROVADO", "LANÇADO"] for doc in documentos_status)
    print(f"Todos aprovados (calculado): {todos_aprovados_calc}")

    # Se não há documentos, considera como aprovado (fatura vazia)
    if len(documentos_status) == 0:
        print("ATENÇÃO: Fatura sem documentos - considerando como aprovada")
        todos_aprovados_calc = True

    print(f"Resultado final todos_aprovados: {todos_aprovados_calc}")
    print("=" * 50)

    # Verifica se todos os documentos estão aprovados/lançados
    todos_aprovados = todos_aprovados_calc

    # Verifica tolerância de R$ 1,00 entre valor da fatura e valor considerado
    diferenca_fatura_considerado = abs(fatura.valor_total_fatura - valor_total_considerado)
    fatura_dentro_tolerancia = diferenca_fatura_considerado <= 1.00

    # ✅ DEBUG: Validação final
    print(
        f"DEBUG FINAL - Pode aprovar: todos_aprovados={todos_aprovados} AND fatura_dentro_tolerancia={fatura_dentro_tolerancia}"
    )
    print(f"  - Valor fatura: R$ {fatura.valor_total_fatura:.2f}")
    print(f"  - Valor considerado total: R$ {valor_total_considerado:.2f}")
    print(f"  - Diferença: R$ {diferenca_fatura_considerado:.2f}")
    print(f"  - Pode aprovar: {todos_aprovados and fatura_dentro_tolerancia}")

    # Análise de valores
    analise_valores = {
        "valor_fatura": fatura.valor_total_fatura,
        "valor_cotado": valor_total_cotado,
        "valor_total_cte": valor_total_cte,
        "valor_total_considerado": valor_total_considerado,
        "valor_total_pago": valor_total_pago,
        "diferenca_fatura_considerado": diferenca_fatura_considerado,
        "fatura_dentro_tolerancia": fatura_dentro_tolerancia,
        "diferenca_considerado_pago": abs(valor_total_considerado - valor_total_pago),
    }

    return render_template(
        "fretes/conferir_fatura.html",
        fatura=fatura,
        documentos_status=documentos_status,
        analise_valores=analise_valores,
        todos_aprovados=todos_aprovados,
        pode_aprovar=todos_aprovados and fatura_dentro_tolerancia,
    )


@fretes_bp.route("/faturas/<int:fatura_id>/aprovar_conferencia", methods=["POST"])
@login_required
def aprovar_conferencia_fatura(fatura_id):
    """Aprova a conferência de uma fatura"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    try:
        valor_final = request.form.get("valor_final")
        observacoes = request.form.get("observacoes", "")

        # Converte valor final
        if valor_final:
            valor_final_float = float(valor_final.replace(",", "."))
        else:
            # Calcula total pago dos documentos
            fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
            despesas_extras = []
            for frete in fretes:
                despesas_extras.extend(frete.despesas_extras)

            valor_final_float = sum(f.valor_pago or 0 for f in fretes) + sum(d.valor_despesa for d in despesas_extras)

        # Atualiza fatura
        fatura.valor_total_fatura = valor_final_float
        fatura.status_conferencia = "CONFERIDO"
        fatura.conferido_por = current_user.nome
        fatura.conferido_em = agora_utc_naive()
        fatura.observacoes_conferencia = observacoes

        # Bloqueia edição dos fretes e despesas
        fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
        for frete in fretes:
            if frete.status != "BLOQUEADO":
                frete.status = "CONFERIDO"

        db.session.commit()

        flash(
            f"✅ Fatura {fatura.numero_fatura} conferida com sucesso! Valor atualizado para R$ {valor_final_float:.2f}. Agora você pode lançar no Odoo.",
            "success",
        )
        return redirect(url_for("fretes.visualizar_fatura", fatura_id=fatura_id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao conferir fatura: {str(e)}", "error")
        return redirect(url_for("fretes.conferir_fatura", fatura_id=fatura_id))


@fretes_bp.route("/faturas/<int:fatura_id>/reabrir", methods=["POST"])
@login_required
def reabrir_fatura(fatura_id):
    """Reabre uma fatura conferida, liberando para edição novamente"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    try:
        motivo = request.form.get("motivo_reabertura", "")

        # ✅ VALIDAÇÃO: Verifica se pode reabrir
        if fatura.status_conferencia != "CONFERIDO":
            flash("❌ Apenas faturas conferidas podem ser reabertas!", "error")
            return redirect(url_for("fretes.listar_faturas"))

        # ✅ VERIFICA STATUS DOS DOCUMENTOS ANTES DE REABRIR
        fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
        despesas_extras = []
        for frete in fretes:
            despesas_extras.extend(frete.despesas_extras)

        # Conta documentos pendentes
        documentos_pendentes = 0
        for frete in fretes:
            if not frete.numero_cte or not frete.valor_cte:
                documentos_pendentes += 1

        for despesa in despesas_extras:
            if despesa.numero_documento == "PENDENTE_FATURA":
                documentos_pendentes += 1

        # ⚠️ AVISO se há documentos pendentes (mas permite reabertura)
        if documentos_pendentes > 0:
            flash(
                f"⚠️ ATENÇÃO: Há {documentos_pendentes} documento(s) pendente(s) nesta fatura. Certifique-se de completar antes de conferir novamente.",
                "warning",
            )

        # Atualiza status da fatura
        fatura.status_conferencia = "PENDENTE"
        fatura.observacoes_conferencia = f"REABERTA EM {agora_utc_naive().strftime('%d/%m/%Y %H:%M')} por {current_user.nome} - {motivo}\n\n{fatura.observacoes_conferencia or ''}"

        # Libera edição dos fretes
        for frete in fretes:
            if frete.status == "CONFERIDO":
                frete.status = "LANCADO"  # Volta ao status anterior

        db.session.commit()

        flash(
            f"✅ Fatura {fatura.numero_fatura} reaberta com sucesso! Fretes e despesas liberados para edição.",
            "success",
        )
        return redirect(url_for("fretes.listar_faturas"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao reabrir fatura: {str(e)}", "error")
        return redirect(url_for("fretes.listar_faturas"))


@fretes_bp.route("/faturas/<int:fatura_id>/editar", methods=["GET", "POST"])
@login_required
def editar_fatura(fatura_id):
    """Edita uma fatura existente"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    # Verifica se fatura pode ser editada
    if fatura.status_conferencia == "CONFERIDO":
        flash('❌ Fatura conferida não pode ser editada! Use a opção "Reabrir" primeiro.', "error")
        return redirect(url_for("fretes.listar_faturas"))

    if request.method == "POST":
        try:
            # ✅ Captura nome antigo antes de alterar (para mensagem)
            numero_fatura_antigo = fatura.numero_fatura
            numero_fatura_novo = request.form.get("numero_fatura")

            # ✅ Despesas extras já vinculadas via FK - não precisa atualizar nada
            # O vínculo é pelo ID da fatura, não pelo nome

            # Atualiza dados da fatura
            fatura.numero_fatura = numero_fatura_novo
            fatura.data_emissao = datetime.strptime(request.form.get("data_emissao"), "%Y-%m-%d").date()
            fatura.valor_total_fatura = converter_valor_brasileiro(request.form.get("valor_total_fatura"))
            fatura.vencimento = (
                datetime.strptime(request.form.get("vencimento"), "%Y-%m-%d").date()
                if request.form.get("vencimento")
                else None
            )
            fatura.transportadora_id = int(request.form.get("transportadora_id"))

            db.session.commit()

            if numero_fatura_novo != numero_fatura_antigo:
                flash(
                    f'✅ Fatura editada com sucesso! Nome alterado de "{numero_fatura_antigo}" para "{numero_fatura_novo}".',
                    "success",
                )
            else:
                flash(f"✅ Fatura {fatura.numero_fatura} atualizada com sucesso!", "success")

            return redirect(url_for("fretes.listar_faturas"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar fatura: {str(e)}", "error")

    transportadoras = Transportadora.query.all()
    return render_template("fretes/editar_fatura.html", fatura=fatura, transportadoras=transportadoras)


@fretes_bp.route("/faturas/<int:fatura_id>/visualizar")
@login_required
def visualizar_fatura(fatura_id):
    """Visualiza uma fatura sem permitir edição"""
    try:
        logger.info(f"🔍 Tentando visualizar fatura ID: {fatura_id}")

        fatura = FaturaFrete.query.get_or_404(fatura_id)

        logger.info(f"✅ Fatura encontrada: {fatura.numero_fatura} - {fatura.transportadora.razao_social}")

        # Verificar se todos os métodos do modelo funcionam
        total_fretes = fatura.total_fretes()
        total_despesas = fatura.total_despesas_extras()

        logger.info(f"📊 Dados da fatura - Fretes: {total_fretes}, Despesas: {total_despesas}")

        return render_template("fretes/visualizar_fatura.html", fatura=fatura)

    except Exception as e:
        logger.error(f"❌ Erro ao visualizar fatura {fatura_id}: {str(e)}")
        logger.error(f"❌ Detalhes do erro: {type(e).__name__}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")

        flash(f"Erro ao visualizar fatura: {str(e)}", "error")
        return redirect(url_for("fretes.listar_faturas"))


@fretes_bp.route("/faturas/<int:fatura_id>/excluir", methods=["POST"])
@login_required
def excluir_fatura(fatura_id):
    """Exclui uma fatura com validações inteligentes"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    try:
        # Verifica se fatura está conferida
        if fatura.status_conferencia == "CONFERIDO":
            flash("❌ Fatura conferida não pode ser excluída!", "error")
            return redirect(url_for("fretes.listar_faturas"))

        # ✅ NOVA LÓGICA: Verifica fretes com CTe lançado vs sem CTe
        fretes_com_cte = Frete.query.filter(Frete.fatura_frete_id == fatura_id, Frete.numero_cte.isnot(None)).count()

        fretes_sem_cte = Frete.query.filter(Frete.fatura_frete_id == fatura_id, Frete.numero_cte.is_(None)).count()

        # Se há fretes com CTe, não pode excluir
        if fretes_com_cte > 0:
            flash(
                f'❌ Não é possível excluir a fatura {fatura.numero_fatura}. Há {fretes_com_cte} frete(s) com CTe lançado. Use "Cancelar CTe" primeiro.',
                "error",
            )
            return redirect(url_for("fretes.listar_faturas"))

        # ✅ PERMITE EXCLUSÃO se só há fretes sem CTe
        if fretes_sem_cte > 0:
            # Remove vinculação dos fretes sem CTe com a fatura
            fretes_vinculados = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
            for frete in fretes_vinculados:
                frete.fatura_frete_id = None
                frete.vencimento = None  # Remove vencimento também

            flash(f"ℹ️  {fretes_sem_cte} frete(s) sem CTe foram desvinculados da fatura.", "info")

        # Exclui despesas extras relacionadas se houver
        despesas_excluidas = DespesaExtra.query.filter(
            DespesaExtra.observacoes.contains(f"Fatura: {fatura.numero_fatura}")
        ).count()

        DespesaExtra.query.filter(DespesaExtra.observacoes.contains(f"Fatura: {fatura.numero_fatura}")).delete(
            synchronize_session=False
        )

        if despesas_excluidas > 0:
            flash(f"ℹ️  {despesas_excluidas} despesa(s) extra(s) foram excluídas.", "info")

        # Salva dados para o flash
        numero_fatura = fatura.numero_fatura
        transportadora = fatura.transportadora.razao_social

        # Exclui a fatura
        db.session.delete(fatura)
        db.session.commit()

        flash(f"✅ Fatura {numero_fatura} excluída com sucesso! Transportadora: {transportadora}", "success")
        return redirect(url_for("fretes.listar_faturas"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir fatura: {str(e)}", "error")
        return redirect(url_for("fretes.listar_faturas"))


# =================== EXPORTAÇÃO DE FATURAS ===================


@fretes_bp.route("/faturas/exportar")
@login_required
@require_financeiro()
def exportar_faturas():
    """Tela de exportação de faturas com filtros"""
    form = FiltroFaturasForm(request.args)

    # Popular choices de transportadoras
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
    form.transportadora_id.choices = [("", "Todas as transportadoras")] + [
        (t.id, t.razao_social) for t in transportadoras
    ]

    return render_template("fretes/exportar_faturas.html", form=form)


@fretes_bp.route("/faturas/exportar/excel")
@login_required
@require_financeiro()
def exportar_faturas_excel():
    """
    Exporta faturas para Excel com 2 abas:
    - Aba "Faturas": Dados resumidos das faturas
    - Aba "Detalhes": Dados denormalizados (fretes + despesas)
    """
    from io import BytesIO
    import pandas as pd

    # Capturar filtros
    transportadora_id = request.args.get("transportadora_id", "")
    status_conferencia = request.args.get("status_conferencia", "")
    data_emissao_de = request.args.get("data_emissao_de", "")
    data_emissao_ate = request.args.get("data_emissao_ate", "")
    data_vencimento_de = request.args.get("data_vencimento_de", "")
    data_vencimento_ate = request.args.get("data_vencimento_ate", "")

    # Montar query base
    query = FaturaFrete.query

    # Aplicar filtros
    if transportadora_id:
        try:
            query = query.filter(FaturaFrete.transportadora_id == int(transportadora_id))
        except (ValueError, TypeError):
            pass

    if status_conferencia:
        query = query.filter(FaturaFrete.status_conferencia == status_conferencia)

    if data_emissao_de:
        try:
            data_de = datetime.strptime(data_emissao_de, "%Y-%m-%d").date()
            query = query.filter(FaturaFrete.data_emissao >= data_de)
        except ValueError:
            pass

    if data_emissao_ate:
        try:
            data_ate = datetime.strptime(data_emissao_ate, "%Y-%m-%d").date()
            query = query.filter(FaturaFrete.data_emissao <= data_ate)
        except ValueError:
            pass

    if data_vencimento_de:
        try:
            data_de = datetime.strptime(data_vencimento_de, "%Y-%m-%d").date()
            query = query.filter(FaturaFrete.vencimento >= data_de)
        except ValueError:
            pass

    if data_vencimento_ate:
        try:
            data_ate = datetime.strptime(data_vencimento_ate, "%Y-%m-%d").date()
            query = query.filter(FaturaFrete.vencimento <= data_ate)
        except ValueError:
            pass

    # Executar query
    faturas = query.order_by(desc(FaturaFrete.data_emissao)).all()

    if not faturas:
        flash("Nenhuma fatura encontrada com os filtros selecionados.", "warning")
        return redirect(url_for("fretes.exportar_faturas"))

    # ========== ABA 1: FATURAS ==========
    dados_faturas = []
    for fatura in faturas:
        dados_faturas.append({
            "ID": fatura.id,
            "Número Fatura": fatura.numero_fatura,
            "Transportadora": fatura.transportadora.razao_social if fatura.transportadora else "",
            "CNPJ Transportadora": fatura.transportadora.cnpj if fatura.transportadora else "",
            "Data Emissão": fatura.data_emissao.strftime("%d/%m/%Y") if fatura.data_emissao else "",
            "Vencimento": fatura.vencimento.strftime("%d/%m/%Y") if fatura.vencimento else "",
            "Valor Total Fatura": float(fatura.valor_total_fatura or 0),
            "Status": fatura.status_conferencia,
            "Qtd Fretes": fatura.total_fretes(),
            "Valor Total Fretes": float(fatura.valor_total_fretes() or 0),
            "Qtd Despesas": fatura.total_despesas_extras(),
            "Valor Total Despesas": float(fatura.valor_total_despesas_extras() or 0),
            "Conferido Por": fatura.conferido_por or "",
            "Conferido Em": fatura.conferido_em.strftime("%d/%m/%Y %H:%M") if fatura.conferido_em else "",
            "Criado Por": fatura.criado_por or "",
            "Criado Em": fatura.criado_em.strftime("%d/%m/%Y %H:%M") if fatura.criado_em else "",
        })

    df_faturas = pd.DataFrame(dados_faturas)

    # ========== ABA 2: DETALHES (Denormalizado) ==========
    dados_detalhes = []

    for fatura in faturas:
        # Dados base da fatura
        dados_fatura_base = {
            "Fatura ID": fatura.id,
            "Número Fatura": fatura.numero_fatura,
            "Transportadora": fatura.transportadora.razao_social if fatura.transportadora else "",
            "Data Emissão Fatura": fatura.data_emissao.strftime("%d/%m/%Y") if fatura.data_emissao else "",
            "Vencimento Fatura": fatura.vencimento.strftime("%d/%m/%Y") if fatura.vencimento else "",
            "Valor Total Fatura": float(fatura.valor_total_fatura or 0),
            "Status Fatura": fatura.status_conferencia,
        }

        # Adicionar fretes
        for frete in fatura.fretes:
            # Buscar dados do CTe vinculado (se houver)
            cte_chave = ""
            cte_valor = ""
            cte_status = ""

            if frete.cte:
                cte_chave = frete.cte.chave_acesso or ""
                cte_valor = float(frete.cte.valor_total or 0) if frete.cte.valor_total else ""
                cte_status = frete.cte.odoo_status_descricao or ""

            dados_linha = {
                **dados_fatura_base,
                "Tipo": "FRETE",
                "Frete ID": frete.id,
                "Número CTe": frete.numero_cte or "",
                "Chave CTe": cte_chave,
                "Valor CTe (Sistema)": cte_valor,
                "Status CTe": cte_status,
                "Cliente": frete.nome_cliente or "",
                "CNPJ Cliente": frete.cnpj_cliente or "",
                "NFs": frete.numeros_nfs or "",
                "Qtd NFs": frete.quantidade_nfs or 0,
                "UF Destino": frete.uf_destino or "",
                "Cidade Destino": frete.cidade_destino or "",
                "Peso Total": float(frete.peso_total or 0),
                "Valor Total NFs": float(frete.valor_total_nfs or 0),
                "Valor Cotado": float(frete.valor_cotado or 0),
                "Valor CTe (Frete)": float(frete.valor_cte or 0),
                "Valor Considerado": float(frete.valor_considerado or 0),
                "Valor Pago": float(frete.valor_pago or 0),
                "Status Frete": frete.status or "",
                "Data Emissão CTe": frete.data_emissao_cte.strftime("%d/%m/%Y") if frete.data_emissao_cte else "",
                "Vencimento Frete": frete.vencimento.strftime("%d/%m/%Y") if frete.vencimento else "",
                # Campos de despesa (vazios para fretes)
                "Tipo Despesa": "",
                "Setor Responsável": "",
                "Motivo Despesa": "",
                "Tipo Documento": "",
                "Número Documento": "",
                "Valor Despesa": "",
                "Vencimento Despesa": "",
            }
            dados_detalhes.append(dados_linha)

        # Adicionar despesas extras
        for despesa in fatura.todas_despesas_extras():
            # Chave do CTe da despesa (se houver)
            despesa_cte_chave = despesa.chave_cte or ""

            dados_linha = {
                **dados_fatura_base,
                "Tipo": "DESPESA",
                "Frete ID": despesa.frete_id or "",
                "Número CTe": despesa.numero_documento if despesa.tipo_documento == "CTE" else "",
                "Chave CTe": despesa_cte_chave,
                "Valor CTe (Sistema)": "",
                "Status CTe": despesa.status or "",
                "Cliente": despesa.frete.nome_cliente if despesa.frete else "",
                "CNPJ Cliente": despesa.frete.cnpj_cliente if despesa.frete else "",
                "NFs": despesa.frete.numeros_nfs if despesa.frete else "",
                "Qtd NFs": despesa.frete.quantidade_nfs if despesa.frete else "",
                "UF Destino": despesa.frete.uf_destino if despesa.frete else "",
                "Cidade Destino": despesa.frete.cidade_destino if despesa.frete else "",
                "Peso Total": "",
                "Valor Total NFs": "",
                "Valor Cotado": "",
                "Valor CTe (Frete)": "",
                "Valor Considerado": "",
                "Valor Pago": "",
                "Status Frete": "",
                "Data Emissão CTe": "",
                "Vencimento Frete": "",
                # Campos de despesa
                "Tipo Despesa": despesa.tipo_despesa or "",
                "Setor Responsável": despesa.setor_responsavel or "",
                "Motivo Despesa": despesa.motivo_despesa or "",
                "Tipo Documento": despesa.tipo_documento or "",
                "Número Documento": despesa.numero_documento or "",
                "Valor Despesa": float(despesa.valor_despesa or 0),
                "Vencimento Despesa": despesa.vencimento_despesa.strftime("%d/%m/%Y") if despesa.vencimento_despesa else "",
            }
            dados_detalhes.append(dados_linha)

    df_detalhes = pd.DataFrame(dados_detalhes)

    # ========== GERAR EXCEL ==========
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Aba 1: Faturas
        df_faturas.to_excel(writer, index=False, sheet_name="Faturas")

        # Formatar colunas da aba Faturas
        worksheet_faturas = writer.sheets["Faturas"]
        for column in worksheet_faturas.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet_faturas.column_dimensions[column_letter].width = adjusted_width

        # Aba 2: Detalhes (se houver dados)
        if not df_detalhes.empty:
            df_detalhes.to_excel(writer, index=False, sheet_name="Detalhes")

            # Formatar colunas da aba Detalhes
            worksheet_detalhes = writer.sheets["Detalhes"]
            for column in worksheet_detalhes.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet_detalhes.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)

    # Nome do arquivo
    data_atual = agora_utc_naive().strftime("%Y%m%d_%H%M%S")
    filename = f"faturas_frete_{data_atual}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# =================== DESPESAS EXTRAS ===================


@fretes_bp.route("/despesas/nova", methods=["GET", "POST"])
@login_required
def nova_despesa_extra_por_nf():
    """Novo fluxo: Lançamento de despesa extra buscando frete por NF"""
    if request.method == "POST":
        numero_nf = request.form.get("numero_nf")

        if not numero_nf:
            flash("Digite o número da NF!", "error")
            return render_template("fretes/nova_despesa_extra_por_nf.html")

        # Busca fretes que contêm essa NF
        fretes_encontrados = Frete.query.filter(Frete.numeros_nfs.contains(numero_nf)).all()

        if not fretes_encontrados:
            flash(f"Nenhum frete encontrado com a NF {numero_nf}!", "error")
            return render_template("fretes/nova_despesa_extra_por_nf.html")

        # Se encontrou fretes, mostra para seleção
        return render_template("fretes/selecionar_frete_despesa.html", fretes=fretes_encontrados, numero_nf=numero_nf)

    return render_template("fretes/nova_despesa_extra_por_nf.html")


@fretes_bp.route("/despesas/criar/<int:frete_id>", methods=["GET", "POST"])
@login_required
def criar_despesa_extra_frete(frete_id):
    """Etapa 2: Criar despesa extra para frete selecionado"""
    from app.utils.email_handler import EmailHandler
    from app.fretes.email_models import EmailAnexado

    frete = Frete.query.get_or_404(frete_id)
    form = DespesaExtraForm()

    # Popular choices de transportadoras (todas ativas)
    transportadoras_ativas = Transportadora.query.order_by(Transportadora.razao_social).all()
    form.transportadora_id.choices = [('', f'-- Usar transportadora do frete ({frete.transportadora.razao_social}) --')] + [
        (str(t.id), t.razao_social) for t in transportadoras_ativas
    ]

    if form.validate_on_submit():
        # Cria e salva a despesa imediatamente
        despesa = DespesaExtra(
            frete_id=frete_id,
            fatura_frete_id=None,  # ✅ Despesa sem fatura inicialmente
            transportadora_id=form.transportadora_id.data if form.transportadora_id.data else None,  # ✅ NOVO: Transportadora alternativa
            tipo_despesa=form.tipo_despesa.data,
            setor_responsavel=form.setor_responsavel.data,
            motivo_despesa=form.motivo_despesa.data,
            tipo_documento="PENDENTE_DOCUMENTO",  # Será definido ao vincular fatura
            numero_documento="PENDENTE_FATURA",  # OBRIGATÓRIO: FATURA PRIMEIRO, DOCUMENTO DEPOIS
            valor_despesa=converter_valor_brasileiro(form.valor_despesa.data),
            vencimento_despesa=None,
            observacoes=form.observacoes.data,
            criado_por=current_user.nome,
        )

        # Salva a despesa primeiro para obter o ID
        db.session.add(despesa)
        db.session.commit()

        # Processa e salva emails anexados IMEDIATAMENTE
        emails_salvos = 0
        if form.emails_anexados.data:
            email_handler = EmailHandler()

            for arquivo_email in form.emails_anexados.data:
                if arquivo_email and arquivo_email.filename:
                    try:
                        # Processa metadados
                        metadados = email_handler.processar_email_msg(arquivo_email)

                        # Faz upload para S3/local
                        arquivo_email.seek(0)  # Volta ao início do arquivo
                        caminho = email_handler.upload_email(arquivo_email, despesa.id, current_user.nome)

                        if caminho and metadados:
                            # Salva no banco de dados
                            email_anexado = EmailAnexado(
                                despesa_extra_id=despesa.id,
                                nome_arquivo=arquivo_email.filename,
                                caminho_s3=caminho,
                                tamanho_bytes=metadados.get("tamanho_bytes", 0),
                                remetente=metadados.get("remetente"),
                                destinatarios=metadados.get("destinatarios", "[]"),
                                cc=metadados.get("cc", "[]"),  # Salva CC
                                bcc=metadados.get("bcc", "[]"),  # Salva BCC
                                assunto=metadados.get("assunto"),
                                data_envio=metadados.get("data_envio"),
                                tem_anexos=metadados.get("tem_anexos", False),
                                qtd_anexos=metadados.get("qtd_anexos", 0),
                                conteudo_preview=metadados.get("conteudo_preview"),
                                criado_por=current_user.nome,
                            )
                            db.session.add(email_anexado)
                            emails_salvos += 1

                    except Exception as e:
                        current_app.logger.error(f"Erro ao processar email {arquivo_email.filename}: {str(e)}")
                        flash(f"⚠️ Erro ao processar email {arquivo_email.filename}", "warning")

            # Commit dos emails
            if emails_salvos > 0:
                db.session.commit()
                flash(f"✅ {emails_salvos} email(s) anexado(s) com sucesso!", "success")

        flash("Despesa extra cadastrada com sucesso!", "success")

        # Redireciona direto para visualização do frete
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

    return render_template("fretes/criar_despesa_extra_frete.html", form=form, frete=frete)


@fretes_bp.route("/despesas/confirmar", methods=["GET", "POST"])
@login_required
def confirmar_despesa_extra():
    """Etapa 3: Pergunta sobre fatura para despesa já criada"""
    despesa_id = session.get("despesa_criada_id")
    despesa_data = session.get("despesa_data")

    if not despesa_data:
        flash("Dados da despesa não encontrados. Reinicie o processo.", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    if not despesa_id:
        flash("Despesa não encontrada. Reinicie o processo.", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
    if not despesa:
        flash("Despesa não encontrada no banco.", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    frete = db.session.get(Frete,despesa_data["frete_id"]) if despesa_data["frete_id"] else None
    if not frete:
        flash("Frete não encontrado!", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    if request.method == "POST":
        tem_fatura = request.form.get("tem_fatura") == "sim"

        if not tem_fatura:
            # Salva despesa sem fatura
            try:
                despesa = DespesaExtra(
                    frete_id=despesa_data["frete_id"],
                    fatura_frete_id=None,  # ✅ Despesa sem fatura
                    tipo_despesa=despesa_data["tipo_despesa"],
                    setor_responsavel=despesa_data["setor_responsavel"],
                    motivo_despesa=despesa_data["motivo_despesa"],
                    tipo_documento=despesa_data["tipo_documento"],
                    numero_documento=despesa_data["numero_documento"],
                    valor_despesa=despesa_data["valor_despesa"],
                    vencimento_despesa=(
                        datetime.fromisoformat(despesa_data["vencimento_despesa"]).date()
                        if despesa_data["vencimento_despesa"]
                        else None
                    ),
                    observacoes=despesa_data["observacoes"],
                    criado_por=current_user.nome,
                )

                db.session.add(despesa)
                db.session.commit()

                # Processa emails anexados após criar a despesa
                if session.get("emails_temporarios"):
                    # NOTA: Como os arquivos não persistem entre requests,
                    # precisamos processar os emails ANTES de redirecionar
                    # Esta é uma limitação do fluxo atual
                    flash("⚠️ Os emails devem ser anexados diretamente no formulário de criação.", "warning")

                # Limpa dados da sessão
                session.pop("despesa_data", None)
                session.pop("emails_temporarios", None)
                session.pop("emails_para_anexar", None)

                flash("Despesa extra cadastrada com sucesso!", "success")
                return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

            except Exception as e:
                flash(f"Erro ao salvar despesa: {str(e)}", "error")
                return redirect(url_for("fretes.nova_despesa_extra_por_nf"))
        else:
            # Tem fatura - redireciona para seleção
            return redirect(url_for("fretes.selecionar_fatura_despesa"))

    # ✅ ALTERADO: Busca TODAS as faturas disponíveis (não só da mesma transportadora)
    # Permite vincular despesas extras a faturas de qualquer transportadora
    faturas_disponiveis = (
        FaturaFrete.query.filter_by(status_conferencia="PENDENTE").order_by(desc(FaturaFrete.criado_em)).all()
    )

    return render_template(
        "fretes/confirmar_despesa_extra.html",
        despesa_data=despesa_data,
        frete=frete,
        faturas_disponiveis=faturas_disponiveis,
    )


@fretes_bp.route("/despesas/selecionar_fatura", methods=["GET", "POST"])
@login_required
def selecionar_fatura_despesa():
    """Etapa 4: Seleciona fatura e finaliza despesa"""
    despesa_data = session.get("despesa_data")

    if not despesa_data:
        flash("Dados da despesa não encontrados. Reinicie o processo.", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    frete = db.session.get(Frete,despesa_data["frete_id"]) if despesa_data["frete_id"] else None
    if not frete:
        flash("Frete não encontrado!", "error")
        return redirect(url_for("fretes.nova_despesa_extra_por_nf"))

    # ✅ ALTERADO: Busca TODAS as faturas disponíveis (não só da mesma transportadora)
    # Permite vincular despesas extras a faturas de qualquer transportadora
    faturas_disponiveis = (
        FaturaFrete.query.filter_by(status_conferencia="PENDENTE").order_by(desc(FaturaFrete.criado_em)).all()
    )

    if request.method == "POST":
        fatura_id = request.form.get("fatura_id")
        tipo_documento_cobranca = request.form.get("tipo_documento_cobranca")
        valor_cobranca = request.form.get("valor_cobranca")
        numero_cte_documento = request.form.get("numero_cte_documento")  # ✅ NOVO CAMPO

        if not fatura_id:
            flash("Selecione uma fatura!", "error")
            return render_template(
                "fretes/selecionar_fatura_despesa.html",
                despesa_data=despesa_data,
                frete=frete,
                faturas_disponiveis=faturas_disponiveis,
            )

        try:
            # Busca a fatura selecionada
            fatura = db.session.get(FaturaFrete,fatura_id) if fatura_id else None
            if not fatura:
                flash("Fatura não encontrada!", "error")
                return render_template(
                    "fretes/selecionar_fatura_despesa.html",
                    despesa_data=despesa_data,
                    frete=frete,
                    faturas_disponiveis=faturas_disponiveis,
                )

            # Converte valor da cobrança
            valor_cobranca_float = (
                float(valor_cobranca.replace(",", ".")) if valor_cobranca else despesa_data["valor_despesa"]
            )

            # **DEFINE VENCIMENTO: FATURA TEM PRIORIDADE**
            vencimento_final = (
                fatura.vencimento
                if fatura.vencimento
                else (
                    datetime.fromisoformat(despesa_data["vencimento_despesa"]).date()
                    if despesa_data["vencimento_despesa"]
                    else None
                )
            )

            # Salva despesa com fatura
            despesa = DespesaExtra(
                frete_id=despesa_data["frete_id"],
                fatura_frete_id=fatura.id,  # ✅ FK direta para a fatura
                tipo_despesa=despesa_data["tipo_despesa"],
                setor_responsavel=despesa_data["setor_responsavel"],
                motivo_despesa=despesa_data["motivo_despesa"],
                tipo_documento=tipo_documento_cobranca,  # Usa o tipo do documento de cobrança
                numero_documento="PENDENTE_FATURA",  # ✅ DOCUMENTO SERÁ PREENCHIDO APÓS FATURA
                valor_despesa=valor_cobranca_float,  # Usa o valor da cobrança
                vencimento_despesa=vencimento_final,  # **USA VENCIMENTO DA FATURA**
                observacoes=despesa_data["observacoes"] or "",  # ✅ Sem "Fatura:" - usa FK
                criado_por=current_user.nome,
            )

            db.session.add(despesa)
            db.session.commit()

            # Limpa dados da sessão
            session.pop("despesa_data", None)

            flash("Despesa extra cadastrada com fatura vinculada!", "success")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

        except Exception as e:
            flash(f"Erro ao salvar despesa: {str(e)}", "error")
            return render_template(
                "fretes/selecionar_fatura_despesa.html",
                despesa_data=despesa_data,
                frete=frete,
                faturas_disponiveis=faturas_disponiveis,
            )

    return render_template(
        "fretes/selecionar_fatura_despesa.html",
        despesa_data=despesa_data,
        frete=frete,
        faturas_disponiveis=faturas_disponiveis,
    )


@fretes_bp.route("/<int:frete_id>/despesas/nova", methods=["GET", "POST"])
@login_required
def nova_despesa_extra(frete_id):
    """Adiciona despesa extra ao frete - NÃO vincula automaticamente à fatura do frete"""
    frete = Frete.query.get_or_404(frete_id)
    form = DespesaExtraForm()

    # Popular choices de transportadoras (todas ativas)
    transportadoras_ativas = Transportadora.query.order_by(Transportadora.razao_social).all()
    form.transportadora_id.choices = [('', f'-- Usar transportadora do frete ({frete.transportadora.razao_social}) --')] + [
        (str(t.id), t.razao_social) for t in transportadoras_ativas
    ]

    if form.validate_on_submit():
        despesa = DespesaExtra(
            frete_id=frete_id,
            fatura_frete_id=None,  # ✅ Despesa sem fatura inicialmente
            transportadora_id=form.transportadora_id.data if form.transportadora_id.data else None,  # ✅ NOVO: Transportadora alternativa
            tipo_despesa=form.tipo_despesa.data,
            setor_responsavel=form.setor_responsavel.data,
            motivo_despesa=form.motivo_despesa.data,
            # ✅ CORRIGIDO: NÃO vincula automaticamente à fatura
            tipo_documento="PENDENTE_DOCUMENTO",  # Será definido ao vincular fatura MANUALMENTE
            numero_documento="PENDENTE_FATURA",  # ✅ PENDENTE até vinculação manual
            valor_despesa=converter_valor_brasileiro(form.valor_despesa.data),
            vencimento_despesa=None,  # Será definido ao vincular fatura
            observacoes=form.observacoes.data,  # ✅ SEM referência automática à fatura
            criado_por=current_user.nome,
        )

        db.session.add(despesa)
        db.session.commit()

        flash('✅ Despesa extra criada! Para vinculá-la a uma fatura, use "Gerenciar Despesas Extras".', "success")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

    return render_template("fretes/nova_despesa_extra.html", form=form, frete=frete)


# =================== CONTA CORRENTE ===================


@fretes_bp.route("/conta_corrente/<int:transportadora_id>")
@login_required
def conta_corrente_transportadora(transportadora_id):
    """Visualiza conta corrente de uma transportadora"""
    transportadora = Transportadora.query.get_or_404(transportadora_id)

    movimentacoes = (
        ContaCorrenteTransportadora.query.filter_by(transportadora_id=transportadora_id)
        .order_by(desc(ContaCorrenteTransportadora.criado_em))
        .all()
    )

    # Calcula saldos
    total_creditos = sum(m.valor_credito for m in movimentacoes if m.status == "ATIVO")
    total_debitos = sum(m.valor_debito for m in movimentacoes if m.status == "ATIVO")
    saldo_atual = total_debitos - total_creditos

    return render_template(
        "fretes/conta_corrente.html",
        transportadora=transportadora,
        movimentacoes=movimentacoes,
        total_creditos=total_creditos,
        total_debitos=total_debitos,
        saldo_atual=saldo_atual,
    )


# =================== APROVAÇÕES ===================


@fretes_bp.route("/aprovacoes")
@login_required
def listar_aprovacoes():
    """Lista aprovações pendentes"""
    aprovacoes = AprovacaoFrete.query.filter_by(status="PENDENTE").order_by(desc(AprovacaoFrete.solicitado_em)).all()

    return render_template("fretes/listar_aprovacoes.html", aprovacoes=aprovacoes)


@fretes_bp.route("/aprovacoes/<int:aprovacao_id>", methods=["GET", "POST"])
@login_required
def processar_aprovacao(aprovacao_id):
    """Processa aprovação de frete - Nova tela com casos A e B"""
    aprovacao = AprovacaoFrete.query.get_or_404(aprovacao_id)
    frete = aprovacao.frete

    if request.method == "POST":
        acao = request.form.get("acao")
        observacoes = request.form.get("observacoes", "")
        lancar_diferenca = request.form.get("lancar_diferenca") == "on"

        if acao == "APROVAR":
            # Aprova o frete
            aprovacao.status = "APROVADO"
            aprovacao.aprovador = current_user.nome
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes

            frete.status = "APROVADO"
            frete.aprovado_por = current_user.nome
            frete.aprovado_em = agora_utc_naive()
            frete.observacoes_aprovacao = observacoes

            # ✅ Se aprovado, verifica se deve lançar diferença na conta corrente
            if lancar_diferenca and frete.valor_pago and frete.valor_considerado:
                diferenca = frete.diferenca_considerado_pago()
                if diferenca != 0:
                    # Remove movimentações antigas
                    ContaCorrenteTransportadora.query.filter_by(frete_id=frete.id).delete()

                    # Cria movimentação aprovada
                    tipo_mov = "CREDITO" if diferenca > 0 else "DEBITO"
                    descricao = f"Frete {frete.id} - CTe {frete.numero_cte} - Diferença Aprovada"

                    movimentacao = ContaCorrenteTransportadora(
                        transportadora_id=frete.transportadora_id,
                        frete_id=frete.id,
                        tipo_movimentacao=tipo_mov,
                        valor_diferenca=abs(diferenca),
                        valor_credito=diferenca if diferenca > 0 else 0,
                        valor_debito=abs(diferenca) if diferenca < 0 else 0,
                        descricao=descricao,
                        criado_por=current_user.nome,
                    )
                    db.session.add(movimentacao)

            flash("Frete aprovado com sucesso!", "success")

        elif acao == "REJEITAR":
            aprovacao.status = "REJEITADO"
            aprovacao.aprovador = current_user.nome
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes

            frete.status = "REJEITADO"
            frete.observacoes_aprovacao = observacoes

            flash("Frete rejeitado!", "warning")

        db.session.commit()
        return redirect(url_for("fretes.listar_aprovacoes"))

    # Calcula os dados para exibição dos casos
    caso_a = caso_b = None

    if frete.valor_considerado and frete.valor_cotado:
        diff_considerado_cotado = frete.valor_considerado - frete.valor_cotado
        if abs(diff_considerado_cotado) > 5.00:
            caso_a = {
                "valor_considerado": frete.valor_considerado,
                "valor_cotado": frete.valor_cotado,
                "diferenca": diff_considerado_cotado,
            }

    if frete.valor_pago and frete.valor_considerado:
        diff_pago_considerado = frete.valor_pago - frete.valor_considerado
        if abs(diff_pago_considerado) > 5.00:
            caso_b = {
                "valor_pago": frete.valor_pago,
                "valor_considerado": frete.valor_considerado,
                "diferenca": diff_pago_considerado,
            }

    return render_template(
        "fretes/processar_aprovacao_nova.html", aprovacao=aprovacao, frete=frete, caso_a=caso_a, caso_b=caso_b
    )


# =================== ROTAS EXISTENTES (COMPATIBILIDADE) ===================


@fretes_bp.route("/antigo/<int:embarque_id>")
@login_required
def visualizar_fretes_lancados(embarque_id):
    embarque = Embarque.query.get_or_404(embarque_id)
    fretes = embarque.fretes_lancados

    total_frete = sum(f.valor_frete for f in fretes)
    total_peso = sum(f.peso for f in fretes)
    total_valor_nf = sum(f.valor_nf for f in fretes)

    return render_template(
        "fretes/visualizar_fretes.html",
        embarque=embarque,
        fretes=fretes,
        total_frete=total_frete,
        total_peso=total_peso,
        total_valor_nf=total_valor_nf,
    )


@fretes_bp.route("/buscar", methods=["GET", "POST"])
@login_required
def buscar_frete():
    if request.method == "POST":
        nf = request.form.get("nf")
        resultados = FreteLancado.query.filter(FreteLancado.nota_fiscal.ilike(f"%{nf}%")).all()
        return render_template("fretes/buscar_frete.html", resultados=resultados, nf=nf)
    return render_template("fretes/buscar_frete.html")


@fretes_bp.route("/divergencias")
@login_required
def listar_divergencias():
    divergentes = (
        FreteLancado.query.filter(FreteLancado.divergencia.isnot(None)).order_by(FreteLancado.criado_em.desc()).all()
    )
    return render_template("fretes/listar_divergencias.html", fretes=divergentes)


@fretes_bp.route("/<int:id>/editar_divergencia", methods=["GET", "POST"])
@login_required
def editar_divergencia(id):
    frete = FreteLancado.query.get_or_404(id)

    if request.method == "POST":
        nova_div = request.form.get("divergencia")
        frete.divergencia = nova_div
        db.session.commit()
        flash("Divergência atualizada com sucesso!", "success")
        return redirect(url_for("fretes.listar_divergencias"))

    return render_template("fretes/editar_divergencia.html", frete=frete)


@fretes_bp.route("/embarques/<int:id>/lancar_fretes", methods=["GET", "POST"])
@login_required
def lancar_fretes_embarque(id):
    embarque = Embarque.query.get_or_404(id)
    itens = embarque.itens

    if request.method == "POST":
        for item in itens:
            prefix = f"{item.id}"
            peso = request.form.get(f"peso_{prefix}")
            valor_nf = request.form.get(f"valor_nf_{prefix}")
            transportadora = request.form.get(f"transportadora_{prefix}")
            valor_frete = request.form.get(f"frete_{prefix}")
            modalidade = request.form.get(f"modalidade_{prefix}")
            cte = request.form.get(f"cte_{prefix}")
            vencimento = request.form.get(f"vencimento_{prefix}")
            fatura = request.form.get(f"fatura_{prefix}")
            divergencia = request.form.get(f"divergencia_{prefix}")

            # Apenas salvar se houver valor de frete preenchido
            if valor_frete:
                # Verifica duplicidade (exibe, mas permite)
                existente = FreteLancado.query.filter_by(nota_fiscal=item.nota_fiscal).first()

                frete = FreteLancado(
                    embarque_id=embarque.id,
                    nota_fiscal=item.nota_fiscal,
                    cliente=item.cliente,
                    cidade_destino=item.cidade_destino,
                    uf_destino=item.uf_destino,
                    transportadora_id=transportadora,
                    peso=float(peso) if peso else None,
                    valor_nf=float(valor_nf) if valor_nf else None,
                    valor_frete=float(valor_frete),
                    modalidade=modalidade,
                    cte=cte,
                    vencimento=vencimento if vencimento else None,
                    fatura=fatura,
                    divergencia=divergencia,
                    tipo_carga=embarque.tipo_carga or "FRACIONADA",
                )
                db.session.add(frete)

        db.session.commit()
        flash("Fretes lançados com sucesso!", "success")
        return redirect(url_for("embarques.visualizar_embarque", id=embarque.id))

    return render_template("fretes/lancar_fretes.html", embarque=embarque, itens=itens)


@fretes_bp.route("/lancar_antigo", methods=["GET", "POST"])
@login_required
def lancar_frete():
    # Rota simplificada para compatibilidade
    if request.method == "POST":
        flash("Use o novo sistema de lançamento de CTe em /fretes/lancar_cte", "info")
        return redirect(url_for("fretes.lancar_cte"))

    transportadoras = Transportadora.query.all()
    return render_template("fretes/lancar_frete_antigo.html", transportadoras=transportadoras)


@fretes_bp.route("/simulador_antigo", methods=["GET", "POST"])
@login_required
def simulador():
    # Rota simplificada para compatibilidade - redireciona para novo sistema
    flash("Simulador movido para o novo sistema. Use as cotações em /cotacao/", "info")
    return redirect(url_for("fretes.index"))


# =================== FUNÇÕES AUXILIARES PARA GATILHOS ===================


def verificar_cte_existente_para_embarque(embarque_id, cnpj_cliente=None):
    """
    Verifica se ja existe CTe lancado para um embarque e CNPJ.

    Checa AMBOS os modulos:
    - Nacom (Frete): numero_cte preenchido
    - CarVia (CarviaFrete): valor_cte preenchido (CTe real, nao auto-gerado)
    """
    # --- Nacom ---
    query = Frete.query.filter_by(embarque_id=embarque_id)
    if cnpj_cliente:
        query = query.filter_by(cnpj_cliente=cnpj_cliente)
    fretes_nacom = query.filter(Frete.numero_cte.isnot(None)).all()

    # --- CarVia: CTe real (valor_cte preenchido) ---
    try:
        from app.carvia.models import CarviaFrete
        carvia_fretes = CarviaFrete.query.filter(
            CarviaFrete.embarque_id == embarque_id,
            CarviaFrete.status != 'CANCELADO',
            CarviaFrete.valor_cte.isnot(None),
        ).all()
    except Exception:
        carvia_fretes = []

    return fretes_nacom + carvia_fretes


def _is_nacom_item(item):
    """True se EmbarqueItem e Nacom (nao CarVia).

    CarVia items identificados por:
    1. carvia_cotacao_id IS NOT NULL (marcador canonico)
    2. separacao_lote_id LIKE 'CARVIA-%' (marcador legado/fallback)
    """
    if item.carvia_cotacao_id:
        return False
    if item.separacao_lote_id and str(item.separacao_lote_id).startswith('CARVIA-'):
        return False
    return True


def verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente):
    """
    Verifica se um frete pode ser lançado automaticamente
    REQUISITOS RIGOROSOS (TODOS DEVEM SER ATENDIDOS):
    0. Portaria deve ter dado saída (embarque.data_embarque preenchida)
    1. TODAS as NFs Nacom do embarque devem estar preenchidas
    2. TODAS as NFs Nacom do embarque devem estar no faturamento
    3. TODOS os CNPJs devem coincidir entre embarque e faturamento
    4. Não pode já existir frete para este CNPJ/embarque
    """
    # REQUISITO 0: Portaria deve ter dado saída
    embarque = db.session.get(Embarque, embarque_id)
    if not embarque or not embarque.data_embarque:
        return False, "Aguardando saída da portaria para lançamento de frete"

    # Verifica se já existe frete
    frete_existente = Frete.query.filter(
        and_(Frete.embarque_id == embarque_id, Frete.cnpj_cliente == cnpj_cliente)
    ).first()

    if frete_existente:
        return False, f"Já existe frete para CNPJ {cnpj_cliente} no embarque {embarque_id}"

    # Busca APENAS itens ATIVOS Nacom do embarque (exclui CarVia)
    itens_embarque = EmbarqueItem.query.filter(
        EmbarqueItem.embarque_id == embarque_id,
        EmbarqueItem.status == "ativo",
        EmbarqueItem.carvia_cotacao_id.is_(None),
        db.or_(
            EmbarqueItem.separacao_lote_id.is_(None),
            ~EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
        ),
    ).all()

    if not itens_embarque:
        return False, "Nenhum item Nacom ativo encontrado no embarque"

    # REQUISITO 1: TODAS as NFs dos itens ATIVOS devem estar preenchidas
    itens_sem_nf = [item for item in itens_embarque if not item.nota_fiscal or item.nota_fiscal.strip() == ""]
    if itens_sem_nf:
        return False, f"Existem {len(itens_sem_nf)} item(ns) ativo(s) sem NF preenchida no embarque"

    # REQUISITO 2: TODAS as NFs dos itens ATIVOS devem estar no faturamento
    nfs_embarque = [item.nota_fiscal for item in itens_embarque]
    from app.faturamento.models import RelatorioFaturamentoImportado

    nfs_faturamento = []
    nfs_nao_encontradas = []

    for nf in nfs_embarque:
        nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
        if nf_fat:
            nfs_faturamento.append(nf_fat)
        else:
            nfs_nao_encontradas.append(nf)

    if nfs_nao_encontradas:
        return False, f"NFs não encontradas no faturamento: {', '.join(nfs_nao_encontradas)}"

    # REQUISITO 3: TODOS os CNPJs dos itens ATIVOS devem coincidir entre embarque e faturamento
    erros_cnpj = []

    for item in itens_embarque:
        nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=item.nota_fiscal).first()

        if nf_fat:
            # Se o item não tem CNPJ, atualiza com o do faturamento
            if not item.cnpj_cliente:
                item.cnpj_cliente = nf_fat.cnpj_cliente
                db.session.commit()

            # Verifica se coincidem (normaliza CNPJs para comparação)
            if normalizar_cnpj(item.cnpj_cliente) != normalizar_cnpj(nf_fat.cnpj_cliente):
                erros_cnpj.append(
                    f"NF {item.nota_fiscal}: Embarque({item.cnpj_cliente}) ≠ Faturamento({nf_fat.cnpj_cliente})"
                )

    if erros_cnpj:
        return False, f"CNPJs divergentes: {'; '.join(erros_cnpj)}"

    # REQUISITO 4: Verifica se há itens ATIVOS com erro de validação
    itens_com_erro = [item for item in itens_embarque if item.erro_validacao]
    if itens_com_erro:
        return False, f"Existem {len(itens_com_erro)} item(ns) ativo(s) com erro de validação no embarque"

    # REQUISITO 5: Verifica se há pelo menos uma NF do CNPJ específico
    cnpj_normalizado = normalizar_cnpj(cnpj_cliente)
    itens_cnpj = [item for item in itens_embarque if normalizar_cnpj(item.cnpj_cliente) == cnpj_normalizado]
    if not itens_cnpj:
        return False, f"Nenhuma NF do CNPJ {cnpj_cliente} encontrada no embarque"

    return True, f"Todos os requisitos atendidos para CNPJ {cnpj_cliente} ({len(itens_cnpj)} NFs)"


def lancar_frete_automatico(embarque_id, cnpj_cliente, usuario="Sistema"):
    """
    Lança frete automaticamente seguindo as regras específicas:

    DIRETA - deverá calcular o frete total do embarque através da tabela gravada no embarque
    considerando o valor total e peso total dos itens do embarque.
    Ao lançar o frete, deverá ser lançado o valor do frete proporcional ao peso de cada CNPJ.

    FRACIONADA - Deverá ser calculado o valor do frete através da tabela contida no item do embarque
    e considerado o valor e peso total do CNPJ dos itens do embarque.

    FOB - Não gera frete automaticamente
    """
    try:
        # Verifica requisitos
        pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente)
        if not pode_lancar:
            return False, motivo

        embarque = db.session.get(Embarque,embarque_id) if embarque_id else None
        if not embarque:
            return False, "Embarque não encontrado"

        # Busca transportadora para verificar FOB
        transportadora = db.session.get(Transportadora,embarque.transportadora_id) if embarque.transportadora_id else None

        # Busca dados do CNPJ no faturamento
        nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(cnpj_cliente=cnpj_cliente).first()
        if not nf_faturamento:
            return False, "Dados do CNPJ não encontrados no faturamento"

        # Busca itens ATIVOS Nacom do embarque para este CNPJ (exclui CarVia)
        itens_embarque_cnpj = []
        for item in embarque.itens:
            if item.status == "ativo" and item.nota_fiscal and _is_nacom_item(item):
                nf_fat = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=item.nota_fiscal, cnpj_cliente=cnpj_cliente
                ).first()
                if nf_fat:
                    itens_embarque_cnpj.append(item)

        if not itens_embarque_cnpj:
            return False, "Nenhuma NF do CNPJ encontrada no embarque"

        # Calcula totais das NFs deste CNPJ
        nfs_deste_cnpj = RelatorioFaturamentoImportado.query.filter(
            and_(
                RelatorioFaturamentoImportado.cnpj_cliente == cnpj_cliente,
                RelatorioFaturamentoImportado.numero_nf.in_([item.nota_fiscal for item in itens_embarque_cnpj]),
            )
        ).all()

        peso_total_cnpj = sum(float(nf.peso_bruto or 0) for nf in nfs_deste_cnpj)
        valor_total_cnpj = sum(float(nf.valor_total or 0) for nf in nfs_deste_cnpj)
        numeros_nfs = ",".join([item.nota_fiscal for item in itens_embarque_cnpj])

        # ✅ FOB - COLETA: Cria Frete com valores zerados
        if transportadora and transportadora.razao_social == "FOB - COLETA":
            from app.utils.tabela_frete_manager import TabelaFreteManager

            tabela_dados_fob = TabelaFreteManager.preparar_cotacao_fob()

            novo_frete = Frete(
                embarque_id=embarque_id,
                cnpj_cliente=cnpj_cliente,
                nome_cliente=nf_faturamento.nome_cliente,
                transportadora_id=embarque.transportadora_id,
                tipo_carga=embarque.tipo_carga,
                modalidade='FOB',
                uf_destino=itens_embarque_cnpj[0].uf_destino,
                cidade_destino=itens_embarque_cnpj[0].cidade_destino,
                peso_total=peso_total_cnpj,
                valor_total_nfs=valor_total_cnpj,
                quantidade_nfs=len(itens_embarque_cnpj),
                numeros_nfs=numeros_nfs,
                valor_cotado=0,
                valor_considerado=0,
                fatura_frete_id=None,
                criado_por=usuario,
                lancado_em=agora_utc_naive(),
                lancado_por=usuario,
            )

            TabelaFreteManager.atribuir_campos_objeto(novo_frete, tabela_dados_fob)
            novo_frete.tabela_icms_destino = 0

            db.session.add(novo_frete)
            db.session.commit()

            return True, f"Frete FOB lancado (R$ 0,00) - ID: {novo_frete.id}"

        # LÓGICA ESPECÍFICA POR TIPO DE CARGA
        if embarque.tipo_carga == "DIRETA":
            # ========== CARGA DIRETA ==========
            # Calcular frete total do embarque através da tabela do embarque
            # considerando valor total e peso total dos itens do embarque

            # Busca dados da tabela do embarque
            from app.utils.tabela_frete_manager import TabelaFreteManager

            tabela_dados = TabelaFreteManager.preparar_dados_tabela(embarque)
            tabela_dados["icms_destino"] = embarque.icms_destino or 0

            # Calcula totais do embarque inteiro (apenas itens ATIVOS Nacom, exclui CarVia)
            todas_nfs_embarque = []
            for item in embarque.itens:
                if item.status == "ativo" and item.nota_fiscal and _is_nacom_item(item):
                    nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=item.nota_fiscal).first()
                    if nf_fat:
                        todas_nfs_embarque.append(nf_fat)

            peso_total_embarque = sum(float(nf.peso_bruto or 0) for nf in todas_nfs_embarque)
            valor_total_embarque = sum(float(nf.valor_total or 0) for nf in todas_nfs_embarque)

            # Calcula frete total do embarque
            valor_frete_total_embarque = calcular_valor_frete_pela_tabela(
                tabela_dados, peso_total_embarque, valor_total_embarque
            )

            # Calcula valor proporcional ao peso do CNPJ
            if peso_total_embarque > 0:
                proporcao_peso = peso_total_cnpj / peso_total_embarque
                valor_cotado = valor_frete_total_embarque * proporcao_peso
            else:
                valor_cotado = 0

        else:
            # ========== CARGA FRACIONADA ==========
            # Calcular através da tabela contida no item do embarque
            # considerando valor e peso total do CNPJ dos itens do embarque

            # Pega dados da tabela de qualquer item do CNPJ (são iguais)
            from app.utils.tabela_frete_manager import TabelaFreteManager

            item_ref = itens_embarque_cnpj[0]
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(item_ref)
            tabela_dados["icms_destino"] = item_ref.icms_destino or 0

            # Calcula frete usando valor e peso total do CNPJ
            valor_cotado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total_cnpj, valor_total_cnpj)

        # Cria o frete
        novo_frete = Frete(
            embarque_id=embarque_id,
            cnpj_cliente=cnpj_cliente,
            nome_cliente=nf_faturamento.nome_cliente,
            transportadora_id=embarque.transportadora_id,
            tipo_carga=embarque.tipo_carga,
            modalidade=tabela_dados["modalidade"],
            uf_destino=itens_embarque_cnpj[0].uf_destino,
            cidade_destino=itens_embarque_cnpj[0].cidade_destino,
            peso_total=peso_total_cnpj,
            valor_total_nfs=valor_total_cnpj,
            quantidade_nfs=len(itens_embarque_cnpj),
            numeros_nfs=numeros_nfs,
            # Valores
            valor_cotado=valor_cotado,
            valor_considerado=valor_cotado,
            # Fatura
            fatura_frete_id=None,
            # Controle
            criado_por=usuario,
            lancado_em=agora_utc_naive(),
            lancado_por=usuario,
        )

        # Atribui campos da tabela usando TabelaFreteManager
        TabelaFreteManager.atribuir_campos_objeto(novo_frete, tabela_dados)
        novo_frete.tabela_icms_destino = tabela_dados["icms_destino"]

        db.session.add(novo_frete)
        db.session.commit()

        # Determina o método de cálculo usado
        metodo_calculo = "DIRETA (proporcional ao peso)" if embarque.tipo_carga == "DIRETA" else "FRACIONADA (por CNPJ)"

        return True, f"Frete lançado automaticamente - ID: {novo_frete.id} ({metodo_calculo}) - R$ {valor_cotado:.2f}"

    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao lançar frete: {str(e)}"


def cancelar_frete_por_embarque(embarque_id, cnpj_cliente=None, usuario="Sistema"):
    """
    Cancela fretes quando um embarque é cancelado
    """
    try:
        query = Frete.query.filter_by(embarque_id=embarque_id)

        if cnpj_cliente:
            query = query.filter_by(cnpj_cliente=cnpj_cliente)

        fretes = query.filter(Frete.status != "CANCELADO").all()

        for frete in fretes:
            frete.status = "CANCELADO"
            # Adiciona observação sobre o cancelamento
            obs_atual = frete.observacoes_aprovacao or ""
            frete.observacoes_aprovacao = f"{obs_atual}\nCancelado automaticamente em {agora_utc_naive().strftime('%d/%m/%Y %H:%M')} por {usuario} devido ao cancelamento do embarque."

        db.session.commit()

        return True, f"{len(fretes)} frete(s) cancelado(s)"

    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao cancelar fretes: {str(e)}"


# =================== ROTAS PARA INTEGRAÇÃO COM EMBARQUES ===================


@fretes_bp.route("/verificar_cte_embarque/<int:embarque_id>")
@login_required
def verificar_cte_embarque(embarque_id):
    """API para verificar se existem CTes lançados para um embarque"""
    fretes_com_cte = verificar_cte_existente_para_embarque(embarque_id)

    if fretes_com_cte:
        dados = []
        for frete in fretes_com_cte:
            dados.append(
                {
                    "id": frete.id,
                    "cnpj_cliente": frete.cnpj_cliente,
                    "nome_cliente": frete.nome_cliente,
                    "numero_cte": frete.numero_cte,
                    "valor_cte": frete.valor_cte,
                    "status": frete.status,
                }
            )

        return jsonify(
            {
                "tem_cte": True,
                "quantidade": len(fretes_com_cte),
                "fretes": dados,
                "mensagem": f"Existem {len(fretes_com_cte)} frete(s) com CTe lançado para este embarque",
            }
        )

    return jsonify(
        {"tem_cte": False, "quantidade": 0, "fretes": [], "mensagem": "Nenhum CTe lançado para este embarque"}
    )


# Função removida - cancelamento de embarques é gerenciado pelo módulo embarques
# A verificação de CTe é feita através da rota verificar_cte_embarque


@fretes_bp.route("/gatilho_lancamento", methods=["POST"])
@login_required
def gatilho_lancamento_frete():
    """
    Gatilho manual para lançamento automático de frete
    Pode ser chamado quando NF é adicionada ao embarque ou importada no faturamento
    """
    data = request.get_json()
    embarque_id = data.get("embarque_id")
    cnpj_cliente = data.get("cnpj_cliente")

    if not embarque_id or not cnpj_cliente:
        return jsonify({"sucesso": False, "mensagem": "embarque_id e cnpj_cliente são obrigatórios"}), 400

    sucesso, mensagem = lancar_frete_automatico(embarque_id, cnpj_cliente, usuario=current_user.nome)

    return jsonify({"sucesso": sucesso, "mensagem": mensagem})


@fretes_bp.route("/corrigir_nfs_fretes")
@login_required
def corrigir_nfs_fretes():
    """Corrige fretes existentes que não têm o campo numeros_nfs preenchido"""
    try:
        # Busca fretes que não têm numeros_nfs preenchido ou está vazio
        fretes_para_corrigir = Frete.query.filter(
            or_(Frete.numeros_nfs.is_(None), Frete.numeros_nfs == "", Frete.numeros_nfs == "N/A")
        ).all()

        fretes_corrigidos = 0

        for frete in fretes_para_corrigir:
            # ✅ CORREÇÃO: Busca itens ATIVOS do embarque deste CNPJ
            itens_embarque = EmbarqueItem.query.filter(
                and_(
                    EmbarqueItem.embarque_id == frete.embarque_id,
                    EmbarqueItem.cnpj_cliente == frete.cnpj_cliente,
                    EmbarqueItem.status == "ativo",
                    EmbarqueItem.nota_fiscal.isnot(None),
                )
            ).all()

            if itens_embarque:
                # Extrai os números das NFs
                numeros_nfs = [item.nota_fiscal for item in itens_embarque if item.nota_fiscal]
                if numeros_nfs:
                    frete.numeros_nfs = ",".join(numeros_nfs)
                    frete.quantidade_nfs = len(numeros_nfs)
                    fretes_corrigidos += 1

        db.session.commit()

        flash(f"✅ {fretes_corrigidos} frete(s) corrigido(s) com sucesso!", "success")
        return redirect(url_for("fretes.index"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao corrigir fretes: {str(e)}", "error")
        return redirect(url_for("fretes.index"))


# =================== FUNÇÃO PARA LANÇAMENTO AUTOMÁTICO ===================


def validar_cnpj_embarque_faturamento(embarque_id):
    """
    Valida se os CNPJs das NFs no embarque coincidem com os CNPJs no faturamento

    REGRAS IMPLEMENTADAS:
    a) Conferir se a NF está no faturamento
    b) Conferir se o CNPJ bate com o do faturamento
    c) Atualizar peso e valor da NF no embarque a partir do faturamento
    d) NÃO SUBSTITUIR dados do embarque pelos dados da NF
    """
    try:
        from app.faturamento.models import RelatorioFaturamentoImportado

        embarque = db.session.get(Embarque,embarque_id) if embarque_id else None
        if not embarque:
            return False, "Embarque não encontrado"

        erros_encontrados = []
        itens_com_erro = 0
        itens_sem_nf = 0

        for item in embarque.itens:
            # ✅ CORREÇÃO: Só valida itens ATIVOS
            if item.status != "ativo":
                continue

            # Itens CarVia: NFs gerenciadas pelo modulo CarVia, nao pelo faturamento Nacom
            if item.carvia_cotacao_id:
                if item.erro_validacao:
                    item.erro_validacao = None
                continue

            # REQUISITO: Todas as NFs dos itens ATIVOS devem estar preenchidas
            if not item.nota_fiscal or item.nota_fiscal.strip() == "":
                item.erro_validacao = "NF_NAO_PREENCHIDA"
                erros_encontrados.append(f"Item {item.cliente} - {item.pedido}: NF não preenchida")
                itens_com_erro += 1
                itens_sem_nf += 1
                continue

            # REGRA a: Conferir se a NF está no faturamento
            nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=item.nota_fiscal).first()

            if not nf_faturamento:
                # NF não encontrada - marca como pendente mas permite continuar o processo
                item.erro_validacao = "NF_PENDENTE_FATURAMENTO"
                # Não conta como erro crítico - permite lançamento de frete
                continue

            # REGRA b: Conferir se a NF pertence ao cliente correto
            # ✅ CORREÇÃO: Se o item tem CNPJ, verifica se a NF pertence a este CNPJ
            if item.cnpj_cliente:
                # Normalizar CNPJs para comparação (remove formatação)
                cnpj_item_normalizado = normalizar_cnpj(item.cnpj_cliente)
                cnpj_nf_normalizado = normalizar_cnpj(nf_faturamento.cnpj_cliente)

                if cnpj_item_normalizado != cnpj_nf_normalizado:
                    # ✅ CORREÇÃO: NF não pertence ao cliente - APAGA APENAS a NF, mantém todos os outros dados
                    nf_original = item.nota_fiscal
                    item.erro_validacao = f"NF_DIVERGENTE: NF {nf_original} pertence ao CNPJ {nf_faturamento.cnpj_cliente}, não a {item.cnpj_cliente}"
                    item.nota_fiscal = None  # ✅ APAGA APENAS a NF divergente

                    # ✅ MANTÉM todos os outros dados: CNPJ, peso, valor, tabelas, separação, etc.
                    # NÃO toca em nada além da NF e do erro_validacao

                    erros_encontrados.append(
                        f"NF {nf_original} foi removida pois pertence ao CNPJ {nf_faturamento.cnpj_cliente}, não a {item.cnpj_cliente}"
                    )
                    itens_com_erro += 1
                    continue

                # ✅ CNPJ BATE: Atualiza peso e valor da NF no embarque
                item.peso = float(nf_faturamento.peso_bruto or 0)
                item.valor = float(nf_faturamento.valor_total or 0)
                item.erro_validacao = None  # Limpa erro se estava OK

            else:
                # ✅ CORREÇÃO: Item sem CNPJ não pode ter NF preenchida
                # Mantém a NF para posterior validação quando o faturamento for importado
                # Esta validação será refeita quando o CNPJ for definido
                item.erro_validacao = f"CLIENTE_NAO_DEFINIDO: Defina o cliente antes de preencher a NF"

                # ✅ MANTÉM a NF para validação posterior (quando faturamento for importado)
                # NÃO apaga a NF - apenas marca como pendente de definição de cliente
                # Se o usuário informar o CNPJ depois, a validação será refeita

                erros_encontrados.append(f"NF {item.nota_fiscal} está pendente - defina o cliente primeiro")
                itens_com_erro += 1
                continue

        db.session.commit()

        if itens_sem_nf > 0:
            return (
                False,
                f"❌ {itens_sem_nf} item(ns) sem NF preenchida. Todos os itens devem ter NF para lançar fretes.",
            )

        if erros_encontrados:
            return False, f"❌ Encontrados {itens_com_erro} erro(s): {'; '.join(erros_encontrados)}"

        return True, f"✅ Todos os requisitos atendidos! {len(embarque.itens)} NF(s) validada(s) com sucesso"

    except Exception as e:
        return False, f"Erro na validação: {str(e)}"


def processar_lancamento_automatico_fretes(embarque_id=None, cnpj_cliente=None, usuario="Sistema"):
    """
    Processa lançamento automático de fretes com REGRAS RIGOROSAS:

    REQUISITOS OBRIGATÓRIOS:
    d) Verificar se todas as NFs daquele embarque estão validadas
    e) Lançar o frete respeitando o tipo_carga ("FRACIONADA", "DIRETA")

    Pode ser chamado:
    - Ao salvar embarque (embarque_id fornecido)
    - Ao importar faturamento (cnpj_cliente fornecido)
    """
    try:
        fretes_lancados = []

        if embarque_id:
            # Cenário 1: Embarque foi salvo
            embarque = db.session.get(Embarque,embarque_id) if embarque_id else None
            if not embarque:
                return False, "Embarque não encontrado"

            # REQUISITO: Portaria deve ter dado saída (early return para performance)
            if not embarque.data_embarque:
                return True, "Aguardando saída da portaria para lançamento de frete"

            # VALIDAÇÃO RIGOROSA: Todas as NFs devem estar validadas
            sucesso_validacao, resultado_validacao = validar_cnpj_embarque_faturamento(embarque_id)

            if not sucesso_validacao:
                # Se há erros, não lança fretes
                return True, resultado_validacao

            # ✅ Todas as NFs estão validadas - procede com lançamento
            # Busca todos os CNPJs únicos deste embarque
            # ✅ CORREÇÃO: Busca CNPJs únicos deste embarque (apenas itens ATIVOS)
            cnpjs_embarque = (
                db.session.query(EmbarqueItem.cnpj_cliente)
                .filter(EmbarqueItem.embarque_id == embarque_id)
                .filter(EmbarqueItem.status == "ativo")
                .filter(EmbarqueItem.nota_fiscal.isnot(None))
                .filter(EmbarqueItem.cnpj_cliente.isnot(None))
                .filter(EmbarqueItem.erro_validacao.is_(None))
                .distinct()
                .all()
            )

            for (cnpj,) in cnpjs_embarque:
                if cnpj:
                    sucesso, resultado = tentar_lancamento_frete_automatico(embarque_id, cnpj, usuario)
                    if sucesso:
                        fretes_lancados.append(resultado)

        elif cnpj_cliente:
            # Cenário 2: Faturamento foi importado
            # ✅ CORREÇÃO: Busca embarques que têm NFs deste CNPJ preenchidas (apenas itens ATIVOS)
            embarques_com_cnpj = (
                db.session.query(EmbarqueItem.embarque_id)
                .filter(EmbarqueItem.cnpj_cliente == cnpj_cliente)
                .filter(EmbarqueItem.status == "ativo")
                .filter(EmbarqueItem.nota_fiscal.isnot(None))
                .distinct()
                .all()
            )

            for (embarque_id_encontrado,) in embarques_com_cnpj:
                # Verifica se portaria já deu saída neste embarque
                embarque_obj = db.session.get(Embarque, embarque_id_encontrado)
                if not embarque_obj or not embarque_obj.data_embarque:
                    continue  # Portaria não deu saída ainda

                # VALIDAÇÃO RIGOROSA para cada embarque
                sucesso_validacao, _ = validar_cnpj_embarque_faturamento(embarque_id_encontrado)

                # Só lança se TODOS os requisitos estiverem atendidos
                if "✅ Todos os requisitos atendidos" in _:
                    sucesso, resultado = tentar_lancamento_frete_automatico(
                        embarque_id_encontrado, cnpj_cliente, usuario
                    )
                    if sucesso:
                        fretes_lancados.append(resultado)

        if fretes_lancados:
            return (
                True,
                f"✅ {len(fretes_lancados)} frete(s) lançado(s) automaticamente seguindo as regras DIRETA/FRACIONADA!",
            )
        else:
            return True, "ℹ️ Nenhum frete foi lançado automaticamente. Verifique se todos os requisitos estão atendidos."

    except Exception as e:
        return False, f"Erro no processamento automático: {str(e)}"


def tentar_lancamento_frete_automatico(embarque_id, cnpj_cliente, usuario="Sistema"):
    """
    Tenta lançar um frete específico para um embarque + CNPJ
    """
    try:
        # Verifica se já existe frete para esta combinação
        frete_existente = Frete.query.filter(
            and_(Frete.embarque_id == embarque_id, Frete.cnpj_cliente == cnpj_cliente)
        ).first()

        if frete_existente:
            return False, f"Frete já existe: #{frete_existente.id}"

        # Verifica se pode lançar (requisitos atendidos)
        pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(embarque_id, cnpj_cliente)
        if not pode_lancar:
            return False, motivo

        # Lança o frete automaticamente
        sucesso, resultado = lancar_frete_automatico(embarque_id, cnpj_cliente, usuario)
        return sucesso, resultado

    except Exception as e:
        return False, f"Erro ao tentar lançamento: {str(e)}"


# =================== GERENCIAMENTO DE DESPESAS EXTRAS ===================


@fretes_bp.route("/despesas/gerenciar", methods=["GET"])
@login_required
def gerenciar_despesas_extras():
    """Lista despesas extras para gerenciamento (vinculação a faturas, etc.)"""
    # Filtros
    filtro_nf = request.args.get("filtro_nf", "").strip()
    filtro_documento = request.args.get("filtro_documento", "").strip()
    filtro_tipo_despesa = request.args.get("filtro_tipo_despesa", "").strip()
    filtro_transportadora = request.args.get("filtro_transportadora", "").strip()
    filtro_com_fatura = request.args.get("filtro_com_fatura", "").strip()
    aba_ativa = request.args.get("aba", "sem")

    # Paginação
    pagina_sem = request.args.get("pagina_sem", 1, type=int)
    pagina_com = request.args.get("pagina_com", 1, type=int)
    por_pagina = 20

    # Buscar tipos de despesa distintos para o filtro
    tipos_despesa_query = db.session.query(DespesaExtra.tipo_despesa).distinct().order_by(DespesaExtra.tipo_despesa).all()
    tipos_despesa = [t[0] for t in tipos_despesa_query if t[0]]

    # Função para aplicar filtros comuns
    def aplicar_filtros(query):
        if filtro_nf:
            query = query.filter(Frete.numeros_nfs.ilike(f"%{filtro_nf}%"))
        if filtro_documento:
            query = query.filter(DespesaExtra.numero_documento.ilike(f"%{filtro_documento}%"))
        if filtro_tipo_despesa:
            query = query.filter(DespesaExtra.tipo_despesa == filtro_tipo_despesa)
        if filtro_transportadora:
            query = query.filter(
                or_(
                    Transportadora.razao_social.ilike(f"%{filtro_transportadora}%"),
                    Transportadora.cnpj.ilike(f"%{filtro_transportadora}%")
                )
            )
        return query

    # Query base para despesas SEM fatura
    query_sem_fatura = (
        db.session.query(DespesaExtra)
        .join(Frete)
        .join(Transportadora, Frete.transportadora_id == Transportadora.id)
        .filter(DespesaExtra.fatura_frete_id.is_(None))
    )
    query_sem_fatura = aplicar_filtros(query_sem_fatura)

    # Query base para despesas COM fatura
    query_com_fatura = (
        db.session.query(DespesaExtra)
        .join(Frete)
        .join(Transportadora, Frete.transportadora_id == Transportadora.id)
        .filter(DespesaExtra.fatura_frete_id.isnot(None))
    )
    query_com_fatura = aplicar_filtros(query_com_fatura)

    # Se filtro_com_fatura estiver definido, filtra nas duas queries
    if filtro_com_fatura == "sim":
        # Mostra apenas COM fatura
        despesas_sem_fatura_paginadas = query_sem_fatura.filter(False).paginate(
            page=1, per_page=por_pagina, error_out=False
        )
        despesas_com_fatura_paginadas = query_com_fatura.order_by(desc(DespesaExtra.criado_em)).paginate(
            page=pagina_com, per_page=por_pagina, error_out=False
        )
    elif filtro_com_fatura == "nao":
        # Mostra apenas SEM fatura
        despesas_sem_fatura_paginadas = query_sem_fatura.order_by(desc(DespesaExtra.criado_em)).paginate(
            page=pagina_sem, per_page=por_pagina, error_out=False
        )
        despesas_com_fatura_paginadas = query_com_fatura.filter(False).paginate(
            page=1, per_page=por_pagina, error_out=False
        )
    else:
        # Mostra ambas
        despesas_sem_fatura_paginadas = query_sem_fatura.order_by(desc(DespesaExtra.criado_em)).paginate(
            page=pagina_sem, per_page=por_pagina, error_out=False
        )
        despesas_com_fatura_paginadas = query_com_fatura.order_by(desc(DespesaExtra.criado_em)).paginate(
            page=pagina_com, per_page=por_pagina, error_out=False
        )

    return render_template(
        "fretes/gerenciar_despesas_extras.html",
        despesas_sem_fatura=despesas_sem_fatura_paginadas,
        despesas_com_fatura=despesas_com_fatura_paginadas,
        filtro_nf=filtro_nf,
        filtro_documento=filtro_documento,
        filtro_tipo_despesa=filtro_tipo_despesa,
        filtro_transportadora=filtro_transportadora,
        filtro_com_fatura=filtro_com_fatura,
        aba_ativa=aba_ativa,
        tipos_despesa=tipos_despesa,
    )


@fretes_bp.route("/despesas/<int:despesa_id>/vincular_fatura", methods=["GET", "POST"])
@login_required
def vincular_despesa_fatura(despesa_id):
    """Vincula uma despesa extra existente a uma fatura"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    frete = db.session.get(Frete,despesa.frete_id) if despesa.frete_id else None

    # ✅ ALTERADO: Busca TODAS as faturas disponíveis (não só da mesma transportadora)
    # Permite vincular despesas extras a faturas de qualquer transportadora
    faturas_disponiveis = (
        FaturaFrete.query.filter_by(status_conferencia="PENDENTE").order_by(desc(FaturaFrete.criado_em)).all()
    )

    if request.method == "POST":
        fatura_id = request.form.get("fatura_id")
        tipo_documento_cobranca = request.form.get("tipo_documento_cobranca")
        valor_cobranca = request.form.get("valor_cobranca")
        numero_cte_documento = request.form.get("numero_cte_documento")  # ✅ NOVO CAMPO

        if not fatura_id:
            flash("Selecione uma fatura!", "error")
            return render_template(
                "fretes/vincular_despesa_fatura.html",
                despesa=despesa,
                frete=frete,
                faturas_disponiveis=faturas_disponiveis,
            )

        try:
            # Busca a fatura selecionada
            fatura = db.session.get(FaturaFrete,fatura_id) if fatura_id else None
            if not fatura:
                flash("Fatura não encontrada!", "error")
                return render_template(
                    "fretes/vincular_despesa_fatura.html",
                    despesa=despesa,
                    frete=frete,
                    faturas_disponiveis=faturas_disponiveis,
                )

            # Converte valor da cobrança
            valor_cobranca_float = float(valor_cobranca.replace(",", ".")) if valor_cobranca else despesa.valor_despesa

            # Atualiza a despesa
            despesa.tipo_documento = tipo_documento_cobranca
            despesa.valor_despesa = valor_cobranca_float
            # ✅ ATUALIZA NÚMERO DO DOCUMENTO
            despesa.numero_documento = numero_cte_documento if numero_cte_documento else "PENDENTE_FATURA"

            # **COPIA VENCIMENTO DA FATURA PARA A DESPESA**
            if fatura.vencimento:
                despesa.vencimento_despesa = fatura.vencimento

            # ✅ VINCULA VIA FK em vez de observações
            despesa.fatura_frete_id = fatura.id
            # Observações permanecem sem o padrão "Fatura:"

            db.session.commit()

            flash(f"Despesa extra vinculada à fatura {fatura.numero_fatura} com sucesso!", "success")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

        except Exception as e:
            flash(f"Erro ao vincular despesa à fatura: {str(e)}", "error")
            return render_template(
                "fretes/vincular_despesa_fatura.html",
                despesa=despesa,
                frete=frete,
                faturas_disponiveis=faturas_disponiveis,
            )

    return render_template(
        "fretes/vincular_despesa_fatura.html", despesa=despesa, frete=frete, faturas_disponiveis=faturas_disponiveis
    )


@fretes_bp.route("/despesas/<int:despesa_id>/desvincular_fatura", methods=["POST"])
@login_required
def desvincular_despesa_fatura(despesa_id):
    """Desvincula uma despesa extra de sua fatura com validações robustas"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)

    try:
        # ✅ VALIDAÇÃO: Verifica se há fatura para desvincular via FK
        if despesa.fatura_frete_id is None:
            flash("⚠️ Esta despesa não está vinculada a nenhuma fatura!", "warning")
            return redirect(url_for("fretes.gerenciar_despesas_extras"))

        # ✅ VALIDAÇÃO CRÍTICA: Bloqueia desvinculação de fatura conferida
        fatura_vinculada = db.session.get(FaturaFrete,despesa.fatura_frete_id) if despesa.fatura_frete_id else None
        if fatura_vinculada and fatura_vinculada.status_conferencia == "CONFERIDO":
            flash("❌ Não é possível desvincular despesa de fatura já CONFERIDA!", "error")
            return redirect(url_for("fretes.gerenciar_despesas_extras"))

        # ✅ DESVINCULAÇÃO VIA FK (simples e seguro)
        despesa.fatura_frete_id = None

        # ✅ RESET CAMPOS: Volta despesa ao estado "sem fatura"
        despesa.numero_documento = "PENDENTE_FATURA"
        despesa.vencimento_despesa = None
        # Observações permanecem intactas

        db.session.commit()

        # ✅ LOG DEBUG: Para troubleshooting
        nome_fatura_debug = fatura_vinculada.numero_fatura if fatura_vinculada else "Desconhecida"
        print(
            f"DEBUG: Despesa #{despesa.id} desvinculada da fatura '{nome_fatura_debug}' (fatura_frete_id={despesa.fatura_frete_id})"
        )

        flash(f"✅ Despesa extra desvinculada da fatura {nome_fatura_debug} com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao desvincular despesa da fatura: {str(e)}", "error")

    return redirect(url_for("fretes.gerenciar_despesas_extras"))


@fretes_bp.route("/despesas/<int:despesa_id>/editar_documento", methods=["GET", "POST"])
@login_required
def editar_documento_despesa(despesa_id):
    """Permite editar o número do documento APENAS se houver fatura vinculada"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)

    # ✅ CORRIGIDO: Valida se a DESPESA tem fatura vinculada (não o frete)
    if not despesa.fatura_frete_id:
        flash("⚠️ Para preencher o número do documento, a fatura deve estar vinculada primeiro!", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    if request.method == "POST":
        numero_documento = request.form.get("numero_documento", "").strip()
        tipo_documento = request.form.get("tipo_documento", "")

        if not numero_documento:
            flash("Número do documento é obrigatório!", "error")
        elif numero_documento == "PENDENTE_FATURA":
            flash("Este número não é permitido!", "error")
        else:
            try:
                despesa.numero_documento = numero_documento
                despesa.tipo_documento = tipo_documento

                db.session.commit()
                flash("Documento atualizado com sucesso!", "success")
                return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

            except Exception as e:
                flash(f"Erro ao atualizar documento: {str(e)}", "error")

    # ✅ CORRIGIDO: Passa a fatura DA DESPESA (não a fatura do frete)
    return render_template("fretes/editar_documento_despesa.html", despesa=despesa, fatura=despesa.fatura_frete)


@fretes_bp.route("/contas_correntes")
@login_required
def listar_contas_correntes():
    """Lista todas as contas correntes das transportadoras"""
    try:
        # Busca todas as transportadoras com movimentações de conta corrente

        transportadoras_com_conta = (
            db.session.query(
                Transportadora.id,
                Transportadora.razao_social,
                func.sum(ContaCorrenteTransportadora.valor_credito).label("total_creditos"),
                func.sum(ContaCorrenteTransportadora.valor_debito).label("total_debitos"),
                func.count(ContaCorrenteTransportadora.id).label("total_movimentacoes"),
            )
            .join(ContaCorrenteTransportadora, Transportadora.id == ContaCorrenteTransportadora.transportadora_id)
            .filter(ContaCorrenteTransportadora.status == "ATIVO")
            .group_by(Transportadora.id, Transportadora.razao_social)
            .all()
        )

        # Calcula saldo para cada transportadora
        contas_correntes = []
        for tp in transportadoras_com_conta:
            # ✅ CONVERSÃO EXPLÍCITA: Decimal -> float para garantir formatação correta no template
            total_creditos = float(tp.total_creditos or 0)
            total_debitos = float(tp.total_debitos or 0)
            saldo_atual = total_debitos - total_creditos  # Positivo = transportadora deve para empresa

            contas_correntes.append(
                {
                    "transportadora_id": tp.id,
                    "transportadora_nome": tp.razao_social,
                    "total_creditos": total_creditos,
                    "total_debitos": total_debitos,
                    "saldo_atual": saldo_atual,
                    "total_movimentacoes": tp.total_movimentacoes,
                }
            )

        # Ordena por saldo (maiores débitos primeiro)
        contas_correntes.sort(key=lambda x: x["saldo_atual"], reverse=True)

        return render_template("fretes/contas_correntes.html", contas_correntes=contas_correntes)

    except Exception as e:
        flash(f"Erro ao carregar contas correntes: {str(e)}", "error")
        return redirect(url_for("fretes.index"))


@fretes_bp.route("/<int:frete_id>/excluir", methods=["POST"])
@login_required
def excluir_frete(frete_id):
    """Exclui um frete (CTe) com validações inteligentes"""
    frete = Frete.query.get_or_404(frete_id)

    try:
        # ✅ NOVA LÓGICA: Permite exclusão se não requer mais aprovação
        requer_aprovacao_atual, motivos = frete.requer_aprovacao_por_valor()

        # Verifica se fatura está conferida
        if frete.fatura_frete and frete.fatura_frete.status_conferencia == "CONFERIDO":
            flash("❌ Não é possível excluir CTe de fatura conferida!", "error")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # ✅ NOVA VALIDAÇÃO: Se estava aprovado mas agora valores são iguais, permite exclusão
        if frete.status == "APROVADO" and requer_aprovacao_atual:
            flash(
                "❌ Não é possível excluir CTe aprovado que ainda requer aprovação! Motivos: " + "; ".join(motivos),
                "error",
            )
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # Remove movimentações da conta corrente relacionadas
        ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).delete()

        # Remove aprovações relacionadas
        AprovacaoFrete.query.filter_by(frete_id=frete_id).delete()

        # Salva dados para o flash
        numero_cte = frete.numero_cte or f"Frete #{frete.id}"
        cliente = frete.nome_cliente
        transportadora = frete.transportadora.razao_social

        # Exclui o frete
        db.session.delete(frete)
        db.session.commit()

        flash(
            f"✅ CTe {numero_cte} excluído com sucesso! Cliente: {cliente} | Transportadora: {transportadora}",
            "success",
        )
        return redirect(url_for("fretes.listar_fretes"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir CTe: {str(e)}", "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))


@fretes_bp.route("/<int:frete_id>/cancelar_cte", methods=["POST"])
@login_required
def cancelar_cte(frete_id):
    """Cancela apenas o CTe, mantendo o frete (fluxo reverso)"""
    frete = Frete.query.get_or_404(frete_id)

    try:
        # Verifica se fatura está conferida
        if frete.fatura_frete and frete.fatura_frete.status_conferencia == "CONFERIDO":
            flash("❌ Não é possível cancelar CTe de fatura conferida!", "error")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # Verifica se tem CTe para cancelar
        if not frete.numero_cte:
            flash("❌ Este frete não possui CTe para cancelar!", "error")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # Salva dados para o flash
        numero_cte = frete.numero_cte
        cliente = frete.nome_cliente

        # ✅ CANCELA APENAS O CTE - FRETE VOLTA AO STATUS PENDENTE
        frete.numero_cte = None
        frete.valor_cte = None
        frete.data_emissao_cte = None
        frete.vencimento = None
        frete.status = "PENDENTE"
        frete.fatura_frete_id = None  # Remove vinculação com fatura

        # Limpa campos de aprovação
        frete.aprovado_por = None
        frete.aprovado_em = None
        frete.observacoes_aprovacao = None
        frete.requer_aprovacao = False

        # Remove movimentações da conta corrente relacionadas
        ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).delete()

        # Remove aprovações relacionadas
        AprovacaoFrete.query.filter_by(frete_id=frete_id).delete()

        db.session.commit()

        flash(
            f"✅ CTe {numero_cte} cancelado com sucesso! Frete #{frete.id} voltou ao status PENDENTE. Cliente: {cliente}",
            "success",
        )
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cancelar CTe: {str(e)}", "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))


@fretes_bp.route("/<int:frete_id>/desvincular_fatura", methods=["POST"])
@login_required
def desvincular_frete_fatura(frete_id):
    """Desvincula um frete da fatura (cancela CTe se existir e remove vínculo)"""
    frete = Frete.query.get_or_404(frete_id)

    try:
        # Guarda referência da fatura para redirect
        fatura_id = frete.fatura_frete_id

        # Verifica se fatura está conferida
        if frete.fatura_frete and frete.fatura_frete.status_conferencia == "CONFERIDO":
            flash("❌ Não é possível remover frete de fatura conferida!", "error")
            if fatura_id:
                return redirect(url_for("fretes.visualizar_fatura", fatura_id=fatura_id))
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # Verifica se está vinculado a alguma fatura
        if not frete.fatura_frete_id:
            flash("❌ Este frete não está vinculado a nenhuma fatura!", "error")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))

        # Salva dados para o flash
        numero_cte = frete.numero_cte or f"Frete #{frete.id}"
        cliente = frete.nome_cliente
        numero_fatura = frete.fatura_frete.numero_fatura if frete.fatura_frete else "N/A"
        tinha_cte = frete.numero_cte is not None

        # ✅ DESVINCULA DA FATURA E CANCELA CTe SE EXISTIR
        frete.fatura_frete_id = None
        frete.vencimento = None
        frete.status = "PENDENTE"

        # Se tinha CTe, limpa os dados do CTe
        if tinha_cte:
            frete.numero_cte = None
            frete.valor_cte = None
            frete.data_emissao_cte = None

        # Limpa campos de aprovação
        frete.aprovado_por = None
        frete.aprovado_em = None
        frete.observacoes_aprovacao = None
        frete.requer_aprovacao = False

        # Remove movimentações da conta corrente relacionadas
        ContaCorrenteTransportadora.query.filter_by(frete_id=frete_id).delete()

        # Remove aprovações relacionadas
        AprovacaoFrete.query.filter_by(frete_id=frete_id).delete()

        db.session.commit()

        if tinha_cte:
            flash(
                f"✅ Frete removido da fatura {numero_fatura}! CTe {numero_cte} cancelado. Cliente: {cliente}",
                "success",
            )
        else:
            flash(
                f"✅ Frete #{frete.id} removido da fatura {numero_fatura}! Cliente: {cliente}",
                "success",
            )

        # Retorna para a fatura
        if fatura_id:
            return redirect(url_for("fretes.visualizar_fatura", fatura_id=fatura_id))
        return redirect(url_for("fretes.listar_faturas"))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao desvincular frete da fatura: {str(e)}", "error")
        if frete.fatura_frete_id:
            return redirect(url_for("fretes.visualizar_fatura", fatura_id=frete.fatura_frete_id))
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete_id))


@fretes_bp.route("/despesas/<int:despesa_id>/excluir", methods=["POST"])
@login_required
def excluir_despesa_extra(despesa_id):
    """Exclui uma despesa extra se a fatura não estiver conferida"""
    from app.devolucao.models import FreteDevolucao

    despesa = DespesaExtra.query.get_or_404(despesa_id)
    frete = despesa.frete

    try:
        # Salva dados para o flash
        tipo_despesa = despesa.tipo_despesa
        numero_documento = despesa.numero_documento
        valor = despesa.valor_despesa

        # ✅ NOVO: Se for despesa de devolução, excluir também o FreteDevolucao vinculado
        frete_devolucao_excluido = False
        if tipo_despesa == 'DEVOLUÇÃO' and hasattr(despesa, 'frete_devolucao_vinculado') and despesa.frete_devolucao_vinculado:
            frete_dev = despesa.frete_devolucao_vinculado
            # Soft delete do FreteDevolucao (mesmo comportamento da rota de exclusão de frete)
            frete_dev.ativo = False
            frete_dev.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            frete_dev.atualizado_em = agora_utc_naive()
            frete_devolucao_excluido = True

        # Exclui a despesa
        db.session.delete(despesa)
        db.session.commit()

        msg = f"✅ Despesa extra excluída com sucesso! Tipo: {tipo_despesa} | Documento: {numero_documento} | Valor: R$ {valor:.2f}"
        if frete_devolucao_excluido:
            msg += " | Frete de retorno também foi excluído da tela de ocorrências."
        flash(msg, "success")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir despesa extra: {str(e)}", "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))


@fretes_bp.route("/fatura/<int:fatura_id>/download")
@login_required
def download_pdf_fatura(fatura_id):
    """Serve PDFs de faturas (S3 e locais)"""
    fatura = FaturaFrete.query.get_or_404(fatura_id)

    if not fatura.arquivo_pdf:
        flash("❌ Esta fatura não possui arquivo PDF.", "warning")
        return redirect(request.referrer or url_for("fretes.listar_faturas"))

    try:
        from app.utils.file_storage import get_file_storage

        storage = get_file_storage()

        # Para arquivos S3 (novos)
        if not fatura.arquivo_pdf.startswith("uploads/"):
            url = storage.get_file_url(fatura.arquivo_pdf)
            if url:
                return redirect(url)
            else:
                flash("❌ Erro ao gerar link do arquivo.", "danger")
                return redirect(request.referrer)
        else:
            # Para arquivos locais (antigos)
            pasta = os.path.dirname(fatura.arquivo_pdf)
            nome_arquivo = os.path.basename(fatura.arquivo_pdf)
            return send_from_directory(os.path.join(current_app.root_path, "static", pasta), nome_arquivo)

    except Exception as e:
        flash(f"❌ Erro ao baixar arquivo: {str(e)}", "danger")
        return redirect(request.referrer)


# ============================================================================
# LANÇAMENTO FRETEIROS
# ============================================================================


@fretes_bp.route("/lancamento_freteiros")
@login_required
@require_financeiro()  # 🔒 RESTRITO - apenas financeiro pode lançar freteiros
def lancamento_freteiros():
    """
    Tela para lançamento de fretes dos freteiros
    Mostra todos os freteiros com fretes e despesas extras pendentes
    """

    # Formulário de filtros
    filtro_form = FiltroFreteirosForm(request.args)

    # Popular choices de transportadoras no formulário
    todos_freteiros = Transportadora.query.filter_by(freteiro=True).order_by(Transportadora.razao_social).all()
    filtro_form.transportadora_id.choices = [("", "Todos os freteiros")] + [
        (t.id, t.razao_social) for t in todos_freteiros
    ]

    # ✅ APLICAR FILTROS
    filtro_transportadora = filtro_form.transportadora_id.data

    # Busca apenas transportadoras marcadas como freteiros
    query_freteiros = Transportadora.query.filter_by(freteiro=True)

    # ✅ APLICA FILTRO se especificado
    if filtro_transportadora:
        query_freteiros = query_freteiros.filter(Transportadora.id == filtro_transportadora)

    freteiros = query_freteiros.all()

    dados_freteiros = []

    for freteiro in freteiros:
        # ✅ FRETES PENDENTES - SEMPRE COM DATA DE EMBARQUE PREENCHIDA
        fretes_pendentes = (
            Frete.query.join(Embarque)
            .filter(
                Frete.transportadora_id == freteiro.id,
                Embarque.status == "ativo",  # Apenas embarques ativos
                Embarque.data_embarque.isnot(None),  # ✅ SEMPRE com data de embarque preenchida
                db.or_(Frete.numero_cte.is_(None), Frete.numero_cte == "", Frete.valor_cte.is_(None)),
            )
            .all()
        )

        # ✅ DESPESAS EXTRAS PENDENTES - SEMPRE COM DATA DE EMBARQUE PREENCHIDA
        # ✅ NOVO: Considera transportadora_efetiva (campo transportadora_id da despesa OU transportadora do frete)
        despesas_pendentes = (
            db.session.query(DespesaExtra)
            .join(Frete)
            .join(Embarque)
            .filter(
                # ✅ NOVO: Transportadora efetiva = despesa.transportadora_id OU frete.transportadora_id
                db.or_(
                    # Caso 1: Despesa tem transportadora_id explícito
                    DespesaExtra.transportadora_id == freteiro.id,
                    # Caso 2: Despesa não tem transportadora_id → usa do frete
                    db.and_(
                        DespesaExtra.transportadora_id.is_(None),
                        Frete.transportadora_id == freteiro.id
                    )
                ),
                Embarque.status == "ativo",  # Apenas embarques ativos
                Embarque.data_embarque.isnot(None),  # ✅ SEMPRE com data de embarque preenchida
                db.or_(
                    DespesaExtra.numero_documento.is_(None),
                    DespesaExtra.numero_documento == "",
                    DespesaExtra.numero_documento == "PENDENTE_FATURA",
                ),
            )
            .all()
        )

        # 🆕 Organiza despesas extras por embarque
        despesas_por_embarque = {}
        for despesa in despesas_pendentes:
            embarque_id = despesa.frete.embarque_id
            if embarque_id not in despesas_por_embarque:
                despesas_por_embarque[embarque_id] = []
            despesas_por_embarque[embarque_id].append(despesa)

        if fretes_pendentes or despesas_pendentes:
            # Organiza fretes por embarque
            fretes_por_embarque = {}
            total_valor = 0
            peso_total_transportadora = 0
            valor_nf_total_transportadora = 0
            valor_cotado_total_transportadora = 0

            for frete in fretes_pendentes:
                embarque_id = frete.embarque_id
                if embarque_id not in fretes_por_embarque:
                    fretes_por_embarque[embarque_id] = {
                        "embarque": frete.embarque,
                        "fretes": [],
                        "despesas_extras": despesas_por_embarque.get(embarque_id, []),  # 🆕 Inclui despesas do embarque
                        "total_cotado": 0,
                        "total_considerado": 0,
                    }

                # **FORÇA CÁLCULO** do peso total APENAS das NFs específicas do frete
                if frete.embarque and frete.numeros_nfs:
                    # Pega apenas as NFs que pertencem a este frete
                    nfs_frete = [nf.strip() for nf in frete.numeros_nfs.split(",") if nf.strip()]
                    frete.peso_total = sum(
                        [
                            item.peso or 0
                            for item in frete.embarque.itens
                            if item.peso
                            and item.nota_fiscal
                            and item.nota_fiscal.strip() in nfs_frete
                            and item.status == "ativo"
                        ]
                    )
                else:
                    frete.peso_total = 0

                # **FORÇA CÁLCULO** valor NF do frete através APENAS dos itens que pertencem a este frete específico
                if frete.embarque and frete.numeros_nfs:
                    # Pega apenas as NFs que pertencem a este frete
                    nfs_frete = [nf.strip() for nf in frete.numeros_nfs.split(",") if nf.strip()]
                    frete.valor_nf = sum(
                        [
                            item.valor or 0
                            for item in frete.embarque.itens
                            if item.valor
                            and item.nota_fiscal
                            and item.nota_fiscal.strip() in nfs_frete
                            and item.status == "ativo"
                        ]
                    )
                else:
                    frete.valor_nf = 0

                fretes_por_embarque[embarque_id]["fretes"].append(frete)
                fretes_por_embarque[embarque_id]["total_cotado"] += frete.valor_cotado or 0
                fretes_por_embarque[embarque_id]["total_considerado"] += (
                    frete.valor_considerado or frete.valor_cotado or 0
                )

                # Soma totais da transportadora usando valores calculados
                total_valor += frete.valor_considerado or frete.valor_cotado or 0
                peso_total_transportadora += frete.peso_total
                valor_nf_total_transportadora += frete.valor_nf
                valor_cotado_total_transportadora += frete.valor_cotado or 0

            # 🆕 Adiciona embarques que têm apenas despesas extras (sem fretes)
            for embarque_id, despesas in despesas_por_embarque.items():
                if embarque_id not in fretes_por_embarque and despesas:
                    # Embarque só tem despesas extras, sem fretes
                    embarque = despesas[0].frete.embarque
                    fretes_por_embarque[embarque_id] = {
                        "embarque": embarque,
                        "fretes": [],
                        "despesas_extras": despesas,
                        "total_cotado": 0,
                        "total_considerado": 0,
                    }

            dados_freteiros.append(
                {
                    "freteiro": freteiro,
                    "fretes_por_embarque": fretes_por_embarque,
                    "total_pendencias": len(fretes_pendentes) + len(despesas_pendentes),
                    "total_valor": total_valor + sum([d.valor_despesa or 0 for d in despesas_pendentes]),
                    "peso_total": peso_total_transportadora,
                    "valor_nf_total": valor_nf_total_transportadora,
                    "valor_cotado_total": valor_cotado_total_transportadora,
                }
            )

    return render_template(
        "fretes/lancamento_freteiros.html",
        dados_freteiros=dados_freteiros,
        form=LancamentoFreteirosForm(),
        filtro_form=filtro_form,
        filtro_selecionado=filtro_transportadora,
        hoje=date.today(),
    )


@fretes_bp.route("/emitir_fatura_freteiro/<int:transportadora_id>", methods=["POST"])
@login_required
@require_financeiro()  # 🔒 RESTRITO - apenas financeiro pode emitir faturas de freteiros
def emitir_fatura_freteiro(transportadora_id):
    """
    Emite fatura para um freteiro com base nos lançamentos selecionados
    """

    form = LancamentoFreteirosForm()
    transportadora = Transportadora.query.get_or_404(transportadora_id)

    if not transportadora.freteiro:
        flash("Erro: Transportadora não é um freteiro", "danger")
        return redirect(url_for("fretes.lancamento_freteiros"))

    if form.validate_on_submit():
        try:
            # Pega os IDs dos fretes e despesas selecionados via request.form
            fretes_selecionados = request.form.getlist("fretes_selecionados")
            despesas_selecionadas = request.form.getlist("despesas_selecionadas")

            if not fretes_selecionados and not despesas_selecionadas:
                flash("Selecione pelo menos um lançamento para emitir a fatura", "warning")
                return redirect(url_for("fretes.lancamento_freteiros"))

            data_vencimento = form.data_vencimento.data
            observacoes = form.observacoes.data or ""

            # Calcula valor total da fatura
            valor_total_fatura = 0
            ctes_criados = []

            # Captura valores considerados alterados por embarque (se houver)
            valores_considerados_embarque = {}
            for key, value in request.form.items():
                if key.startswith("valor_considerado_") and value:
                    embarque_id = key.replace("valor_considerado_", "")
                    try:
                        valores_considerados_embarque[int(embarque_id)] = float(value)
                    except (ValueError, TypeError):
                        pass

            # 🆕 Captura valores alterados das despesas extras
            valores_despesas_alterados = {}
            for key, value in request.form.items():
                if key.startswith("valor_despesa_") and value:
                    despesa_id = key.replace("valor_despesa_", "")
                    try:
                        valores_despesas_alterados[int(despesa_id)] = float(value)
                    except (ValueError, TypeError):
                        pass

            # Aplica rateio por peso se valores foram alterados
            rateios_por_embarque = {}
            for embarque_id, valor_novo in valores_considerados_embarque.items():
                # Busca fretes do embarque selecionados
                fretes_embarque = [
                    db.session.get(Frete,int(fid))
                    for fid in fretes_selecionados
                    if db.session.get(Frete,int(fid)) and db.session.get(Frete,int(fid)).embarque_id == embarque_id
                ]

                if fretes_embarque:
                    # Calcula peso total
                    peso_total = sum(
                        [
                            sum([item.peso for item in frete.embarque.itens if item.peso])
                            for frete in fretes_embarque
                            if frete.embarque
                        ]
                    )

                    if peso_total > 0:
                        # Calcula rateio por peso
                        for frete in fretes_embarque:
                            peso_frete = (
                                sum([item.peso for item in frete.embarque.itens if item.peso]) if frete.embarque else 0
                            )
                            valor_rateado = (peso_frete / peso_total) * valor_novo
                            rateios_por_embarque[frete.id] = valor_rateado

            # Processa fretes selecionados
            for frete_id in fretes_selecionados:
                frete = db.session.get(Frete,int(frete_id)) if int(frete_id) else None
                if frete and frete.transportadora_id == transportadora_id:
                    # Usa valor rateado se existe, senão usa valor original
                    valor_considerado = (
                        rateios_por_embarque.get(frete.id) or frete.valor_considerado or frete.valor_cotado
                    )
                    valor_total_fatura += valor_considerado

                    # Gera nome do CTe
                    data_embarque = frete.embarque.data_embarque or frete.embarque.data_prevista_embarque
                    data_str = data_embarque.strftime("%d/%m/%Y") if data_embarque else "S/Data"
                    nfs_str = frete.numeros_nfs[:50] + ("..." if len(frete.numeros_nfs) > 50 else "")

                    nome_cte = f"Frete ({data_str}) NFs {nfs_str}"

                    # Atualiza frete
                    frete.numero_cte = nome_cte
                    frete.valor_cte = valor_considerado
                    frete.valor_considerado = valor_considerado
                    frete.valor_pago = valor_considerado
                    frete.vencimento = data_vencimento
                    frete.status = "APROVADO"
                    frete.aprovado_por = current_user.nome
                    frete.aprovado_em = agora_utc_naive()

                    ctes_criados.append(nome_cte)

            # Processa despesas extras selecionadas
            for despesa_id in despesas_selecionadas:
                despesa = db.session.get(DespesaExtra,int(despesa_id)) if int(despesa_id) else None
                # ✅ CORRIGIDO: Usa transportadora_efetiva (pode ser diferente do frete)
                if despesa and despesa.transportadora_efetiva.id == transportadora_id:
                    # 🆕 Usa valor alterado se existir, senão usa valor original
                    valor_despesa_final = valores_despesas_alterados.get(int(despesa_id)) or despesa.valor_despesa
                    valor_total_fatura += valor_despesa_final

                    # 🆕 Atualiza o valor da despesa no banco se foi alterado
                    if int(despesa_id) in valores_despesas_alterados:
                        despesa.valor_despesa = valores_despesas_alterados[int(despesa_id)]

                    # Preenche documento da despesa
                    despesa.tipo_documento = "CTE"
                    despesa.numero_documento = f"Despesa {despesa.tipo_despesa}"
                    despesa.vencimento_despesa = data_vencimento

                    ctes_criados.append(f"Despesa: {despesa.tipo_despesa} - R$ {valor_despesa_final:.2f}")

            # Cria a fatura (limitando o nome para caber nos 50 caracteres do banco)
            data_venc_str = data_vencimento.strftime("%d/%m/%Y")
            # Encurta nome da transportadora para caber no limite de 50 caracteres
            # Formato: "Fech [NOME] [DD/MM/YYYY]" = 5 + espaços + nome + 10 = máx 50
            max_chars_nome = 50 - 5 - 1 - 10 - 1  # 33 chars para o nome
            nome_transportadora = transportadora.razao_social[:max_chars_nome]
            nome_fatura = f"Fech {nome_transportadora} {data_venc_str}"[:50]  # Garantia extra

            nova_fatura = FaturaFrete(
                transportadora_id=transportadora_id,
                numero_fatura=nome_fatura,
                data_emissao=agora_utc_naive().date(),
                valor_total_fatura=valor_total_fatura,
                vencimento=data_vencimento,
                status_conferencia="CONFERIDO",  # Automaticamente conferida
                conferido_por=current_user.nome,
                conferido_em=agora_utc_naive(),
                observacoes_conferencia=f"Fatura criada automaticamente via lançamento freteiros. {observacoes}",
                criado_por=current_user.nome,
            )

            db.session.add(nova_fatura)
            db.session.flush()  # Para obter o ID

            # Vincula fretes à fatura
            for frete_id in fretes_selecionados:
                frete = db.session.get(Frete,int(frete_id)) if int(frete_id) else None
                if frete:
                    frete.fatura_frete_id = nova_fatura.id

            # ✅ Vincula despesas à fatura via FK
            for despesa_id in despesas_selecionadas:
                despesa = db.session.get(DespesaExtra,int(despesa_id)) if int(despesa_id) else None
                if despesa:
                    despesa.fatura_frete_id = nova_fatura.id

            db.session.commit()

            flash(
                f"""
                <strong>Fatura criada com sucesso!</strong><br>
                <strong>Fatura:</strong> {nova_fatura.numero_fatura}<br>
                <strong>Valor Total:</strong> R$ {valor_total_fatura:,.2f}<br>
                <strong>CTes Criados:</strong> {len(ctes_criados)}<br>
                <strong>Vencimento:</strong> {data_vencimento.strftime('%d/%m/%Y')}
            """,
                "success",
            )

            return redirect(url_for("fretes.listar_faturas"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao emitir fatura: {str(e)}", "danger")
            return redirect(url_for("fretes.lancamento_freteiros"))

    flash("Dados inválidos no formulário", "danger")
    return redirect(url_for("fretes.lancamento_freteiros"))


@fretes_bp.route("/despesa/<int:despesa_id>/anexar-email-ajax", methods=["POST"])
@login_required
def anexar_email_ajax(despesa_id):
    """Rota AJAX para anexar email (.msg ou .eml) a uma despesa extra"""
    try:
        # Busca a despesa
        despesa = DespesaExtra.query.get_or_404(despesa_id)

        # Verifica se foi enviado um arquivo
        if "arquivo_email" not in request.files:
            return jsonify({"success": False, "message": "Nenhum arquivo enviado"}), 400

        arquivo_email = request.files["arquivo_email"]

        if arquivo_email.filename == "":
            return jsonify({"success": False, "message": "Nenhum arquivo selecionado"}), 400

        # Verifica extensão - aceita .msg e .eml
        filename_lower = arquivo_email.filename.lower()
        if not (filename_lower.endswith(".msg") or filename_lower.endswith(".eml")):
            return jsonify({"success": False, "message": "Arquivo deve ser .msg ou .eml"}), 400

        # Processa o email de acordo com a extensão
        email_handler = EmailHandler()

        if filename_lower.endswith(".msg"):
            metadados = email_handler.processar_email_msg(arquivo_email)
        else:  # .eml
            metadados = email_handler.processar_email_eml(arquivo_email)

        if not metadados:
            return jsonify({"success": False, "message": "Erro ao processar email"}), 500

        # Faz upload do arquivo
        caminho = email_handler.upload_email(arquivo_email, despesa.id, current_user.nome)

        if not caminho:
            return jsonify({"success": False, "message": "Erro ao fazer upload do email"}), 500

        # Cria registro no banco
        email_anexado = EmailAnexado(
            despesa_extra_id=despesa.id,
            nome_arquivo=arquivo_email.filename,
            caminho_s3=caminho,
            tamanho_bytes=metadados.get("tamanho_bytes", 0),
            remetente=metadados.get("remetente", ""),
            destinatarios=metadados.get("destinatarios", "[]"),
            cc=metadados.get("cc", "[]"),
            bcc=metadados.get("bcc", "[]"),
            assunto=metadados.get("assunto", ""),
            data_envio=metadados.get("data_envio"),
            tem_anexos=metadados.get("tem_anexos", False),
            qtd_anexos=metadados.get("qtd_anexos", 0),
            conteudo_preview=metadados.get("conteudo_preview", ""),
            criado_por=current_user.nome,
        )

        db.session.add(email_anexado)
        db.session.commit()

        current_app.logger.info(f"✅ Email anexado com sucesso à despesa #{despesa_id} por {current_user.nome}")

        return jsonify(
            {
                "success": True,
                "message": "Email anexado com sucesso",
                "email_id": email_anexado.id,
                "total_emails": len(despesa.emails_anexados),
            }
        )

    except Exception as e:
        current_app.logger.error(f"❌ Erro ao anexar email: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =================== DESPESAS EXTRAS - VINCULAÇÃO CTe E LANÇAMENTO ODOO ===================


@fretes_bp.route("/despesas/<int:despesa_id>/vincular_cte", methods=["GET", "POST"])
@login_required
def vincular_cte_despesa(despesa_id):
    """
    Tela para vincular CTe Complementar a uma despesa extra.
    Mostra sugestões de CTe organizadas por prioridade.
    """
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesa = DespesaExtra.query.get_or_404(despesa_id)

    # Se despesa já está lançada no Odoo, não permite edição
    if despesa.status == "LANCADO_ODOO":
        flash("Despesa já foi lançada no Odoo e não pode ser alterada.", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    if request.method == "POST":
        cte_id = request.form.get("cte_id")

        if not cte_id:
            flash("Selecione um CTe para vincular.", "error")
            return redirect(url_for("fretes.vincular_cte_despesa", despesa_id=despesa_id))

        sucesso, mensagem = DespesaCteService.vincular_cte(
            despesa_id=despesa_id, cte_id=int(cte_id), usuario=current_user.nome
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))
        else:
            flash(mensagem, "error")
            return redirect(url_for("fretes.vincular_cte_despesa", despesa_id=despesa_id))

    # GET: Buscar sugestões de CTe
    resultado = DespesaCteService.buscar_ctes_sugestao(despesa_id)

    if resultado.get("erro"):
        flash(resultado["erro"], "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    return render_template(
        "fretes/vincular_cte_despesa.html",
        despesa=despesa,
        frete=resultado["frete"],
        sugestoes_prioridade_0=resultado.get("sugestoes_prioridade_0", []),  # CTe Normal do frete
        sugestoes_prioridade_1=resultado["sugestoes_prioridade_1"],
        sugestoes_prioridade_2=resultado["sugestoes_prioridade_2"],
        sugestoes_prioridade_3=resultado["sugestoes_prioridade_3"],
        sugestoes_prioridade_4=resultado.get("sugestoes_prioridade_4", []),  # CTes Normais via NFs
    )


@fretes_bp.route("/despesas/<int:despesa_id>/desvincular_cte", methods=["POST"])
@login_required
def desvincular_cte_despesa(despesa_id):
    """Remove o vínculo de CTe de uma despesa extra."""
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesa = DespesaExtra.query.get_or_404(despesa_id)

    sucesso, mensagem = DespesaCteService.desvincular_cte(despesa_id=despesa_id, usuario=current_user.nome)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "error")

    return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))


@fretes_bp.route("/despesas/<int:despesa_id>/vincular_cte_manual", methods=["GET", "POST"])
@login_required
def vincular_cte_manual_despesa(despesa_id):
    """
    Página para vincular CTe manualmente a uma despesa extra.
    Permite busca por prefixo de CNPJ da transportadora e cliente, sem validar NFs.
    """
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesa = DespesaExtra.query.get_or_404(despesa_id)
    frete = Frete.query.get_or_404(despesa.frete_id)

    if request.method == "POST":
        cte_id = request.form.get("cte_id")
        if not cte_id:
            flash("Nenhum CTe selecionado", "error")
            return redirect(url_for("fretes.vincular_cte_manual_despesa", despesa_id=despesa_id))

        sucesso, mensagem = DespesaCteService.vincular_cte_manual(
            despesa_id=despesa_id, cte_id=int(cte_id), usuario=current_user.nome
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))
        else:
            flash(mensagem, "error")
            return redirect(url_for("fretes.vincular_cte_manual_despesa", despesa_id=despesa_id))

    # GET: Buscar CTes com filtros
    prefixo_transportadora = request.args.get("prefixo_transportadora", "")
    prefixo_cliente = request.args.get("prefixo_cliente", "")
    numero_cte = request.args.get("numero_cte", "")

    # Se não houver filtros, usar valores padrão do frete
    if not prefixo_transportadora and not prefixo_cliente and not numero_cte:
        # Busca inicial com valores do frete
        resultado = DespesaCteService.buscar_ctes_manual(despesa_id=despesa_id)
    else:
        # Busca com filtros informados
        resultado = DespesaCteService.buscar_ctes_manual(
            despesa_id=despesa_id,
            prefixo_cnpj_transportadora=prefixo_transportadora if prefixo_transportadora else None,
            prefixo_cnpj_cliente=prefixo_cliente if prefixo_cliente else None,
            numero_cte=numero_cte if numero_cte else None
        )

    if resultado.get("erro"):
        flash(resultado["erro"], "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=frete.id))

    return render_template(
        "fretes/vincular_cte_manual_despesa.html",
        despesa=despesa,
        frete=frete,
        ctes=resultado.get("ctes", []),
        filtros=resultado.get("filtros_aplicados", {}),
        prefixo_transportadora=prefixo_transportadora or resultado.get("filtros_aplicados", {}).get("prefixo_transportadora", ""),
        prefixo_cliente=prefixo_cliente or resultado.get("filtros_aplicados", {}).get("prefixo_cliente", ""),
        numero_cte=numero_cte
    )


@fretes_bp.route("/despesas/<int:despesa_id>/lancar_odoo", methods=["POST"])
@login_required
def lancar_despesa_odoo(despesa_id):
    """
    Enfileira lançamento de despesa extra no Odoo (processamento assíncrono)

    Retorna job_id para acompanhamento do status via polling.
    O processamento real é feito pelo worker na fila 'odoo_lancamento'.
    """
    try:
        from app.fretes.workers.lancamento_odoo_jobs import lancar_despesa_job
        from app.portal.workers import enqueue_job

        despesa = DespesaExtra.query.get_or_404(despesa_id)

        # ========================================
        # VALIDAÇÕES
        # ========================================
        if not despesa.tipo_documento or despesa.tipo_documento.upper() != "CTE":
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": f'Tipo de documento "{despesa.tipo_documento}" não suportado para lançamento no Odoo',
                        "erro": "Apenas despesas com documento CTe podem ser lançadas no Odoo",
                    }
                ),
                400,
            )

        if not despesa.despesa_cte_id:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "CTe não vinculado",
                        "erro": "Vincule um CTe Complementar antes de lançar no Odoo",
                    }
                ),
                400,
            )

        if despesa.status == "LANCADO_ODOO" and despesa.odoo_invoice_id:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "Despesa já foi lançada no Odoo",
                        "erro": f"Invoice ID: {despesa.odoo_invoice_id}",
                    }
                ),
                400,
            )

        # Permitir reprocessamento para status VINCULADO_CTE ou PENDENTE (após rollback)
        # Nota: DespesaExtra não tem status 'ERRO' - quando falha, volta para VINCULADO_CTE
        status_permitidos = ["VINCULADO_CTE", "PENDENTE"]
        if despesa.status not in status_permitidos:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": f'Status "{despesa.status}" não permite lançamento',
                        "erro": f'Status esperado: {", ".join(status_permitidos)}',
                    }
                ),
                400,
            )

        # Obter data de vencimento do request
        data = request.get_json() or {}
        data_vencimento = data.get("data_vencimento")

        if not data_vencimento and despesa.vencimento_despesa:
            data_vencimento = despesa.vencimento_despesa.strftime("%Y-%m-%d")

        # ========================================
        # ENFILEIRAR JOB
        # ========================================
        logger.info(f"📋 Enfileirando lançamento de despesa #{despesa_id} na fila 'odoo_lancamento'")

        job = enqueue_job(
            lancar_despesa_job,
            despesa_id,
            current_user.nome,
            request.remote_addr,
            data_vencimento,
            queue_name="odoo_lancamento",
            timeout="10m",
        )

        logger.info(f"✅ Job {job.id} enfileirado para despesa #{despesa_id}")

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "Lançamento enfileirado com sucesso",
                    "job_id": job.id,
                    "despesa_id": despesa_id,
                    "status": "queued",
                }
            ),
            202,
        )  # 202 Accepted

    except Exception as e:
        current_app.logger.error(f"Erro ao enfileirar lançamento de despesa: {str(e)}")
        return jsonify({"sucesso": False, "mensagem": f"Erro ao enfileirar lançamento", "erro": str(e)}), 500


@fretes_bp.route("/despesas/<int:despesa_id>/marcar_lancado", methods=["POST"])
@login_required
def marcar_despesa_lancado(despesa_id):
    """
    Marca uma despesa como LANCADO (para NFS/Recibo que não vão para Odoo).
    Permite anexar comprovante opcional.
    """
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesa = DespesaExtra.query.get_or_404(despesa_id)

    # Validar se é NFS ou Recibo (não CTe)
    if despesa.tipo_documento == "CTe":
        flash("Despesas com CTe devem ser lançadas no Odoo.", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    if despesa.status == "LANCADO_ODOO" or despesa.status == "LANCADO":
        flash("Despesa já foi lançada.", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    # Processar upload de comprovante se enviado
    if "comprovante" in request.files:
        arquivo = request.files["comprovante"]
        if arquivo and arquivo.filename:
            # Salvar arquivo (implementar lógica de upload S3 similar ao email)
            from app.utils.email_handler import EmailHandler

            email_handler = EmailHandler()

            # Usar mesmo bucket/path do email
            caminho = email_handler.upload_email(arquivo, despesa_id, current_user.nome)
            if caminho:
                despesa.comprovante_path = caminho
                despesa.comprovante_nome_arquivo = arquivo.filename

    # Atualizar status
    sucesso, mensagem = DespesaCteService.atualizar_status_lancado(despesa_id=despesa_id, tipo_lancamento="LANCADO")

    if sucesso:
        flash("Despesa marcada como lançada com sucesso.", "success")
    else:
        flash(mensagem, "error")

    return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))


@fretes_bp.route("/despesas/<int:despesa_id>/auditoria_odoo")
@login_required
def auditoria_despesa_odoo(despesa_id):
    """Exibe auditoria de lançamento Odoo para uma despesa extra."""
    from app.fretes.models import LancamentoFreteOdooAuditoria

    despesa = DespesaExtra.query.get_or_404(despesa_id)

    auditorias = (
        LancamentoFreteOdooAuditoria.query.filter_by(despesa_extra_id=despesa_id)
        .order_by(LancamentoFreteOdooAuditoria.etapa)
        .all()
    )

    return render_template("fretes/auditoria_despesa_odoo.html", despesa=despesa, auditorias=auditorias)


@fretes_bp.route("/despesas/<int:despesa_id>/lancar_nfs_recibo", methods=["POST"])
@login_required
def lancar_nfs_recibo(despesa_id):
    """
    Lança uma despesa NFS/Recibo com número do documento e comprovante opcional.
    Retorna JSON para AJAX.
    """
    from datetime import datetime
    from werkzeug.utils import secure_filename
    import os

    try:
        despesa = DespesaExtra.query.get_or_404(despesa_id)

        # Validar se não é CTe (CTe vai para Odoo) - aceita CTE ou CTe
        if despesa.tipo_documento and despesa.tipo_documento.upper() == "CTE":
            return jsonify({"success": False, "message": "Despesas com CTe devem ser lançadas no Odoo, não aqui."}), 400

        # Validar status
        if despesa.status in ["LANCADO", "LANCADO_ODOO"]:
            return jsonify({"success": False, "message": "Despesa já foi lançada."}), 400

        # Obter dados do formulário
        tipo_documento = request.form.get("tipo_documento", "NFS")
        numero_documento = request.form.get("numero_documento", "").strip()
        vencimento = request.form.get("vencimento")
        observacoes = request.form.get("observacoes", "").strip()

        # Validar número do documento
        if not numero_documento:
            return jsonify({"success": False, "message": "Número do documento é obrigatório."}), 400

        # Atualizar dados da despesa
        despesa.tipo_documento = tipo_documento
        despesa.numero_documento = numero_documento

        if vencimento:
            try:
                despesa.vencimento_despesa = datetime.strptime(vencimento, "%Y-%m-%d").date()
            except ValueError:
                pass  # Ignora se data inválida

        if observacoes:
            if despesa.observacoes:
                despesa.observacoes += f"\n[{agora_utc_naive().strftime('%d/%m/%Y %H:%M')}] {observacoes}"
            else:
                despesa.observacoes = f"[{agora_utc_naive().strftime('%d/%m/%Y %H:%M')}] {observacoes}"

        # Processar upload de comprovante se enviado
        if "comprovante" in request.files:
            arquivo = request.files["comprovante"]
            if arquivo and arquivo.filename:
                try:
                    # Salvar arquivo usando S3 ou local
                    from app.utils.file_storage import FileStorage

                    file_storage = FileStorage()

                    # Gerar nome único
                    filename = secure_filename(arquivo.filename)
                    nome_arquivo = (
                        f"comprovantes/despesa_{despesa_id}_{agora_utc_naive().strftime('%Y%m%d%H%M%S')}_{filename}"
                    )

                    # Upload para S3
                    caminho = file_storage.save_file(arquivo, nome_arquivo)
                    if caminho:
                        despesa.comprovante_path = caminho
                        despesa.comprovante_nome_arquivo = arquivo.filename
                    else:
                        # Fallback: salvar localmente
                        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "comprovantes")
                        os.makedirs(upload_folder, exist_ok=True)
                        arquivo_path = os.path.join(upload_folder, nome_arquivo.replace("comprovantes/", ""))
                        arquivo.save(arquivo_path)
                        despesa.comprovante_path = f"uploads/comprovantes/{nome_arquivo.replace('comprovantes/', '')}"
                        despesa.comprovante_nome_arquivo = arquivo.filename

                except Exception as e:
                    current_app.logger.error(f"Erro ao fazer upload do comprovante: {e}")
                    # Continua sem o comprovante

        # Atualizar status para LANCADO
        despesa.status = "LANCADO"

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Despesa #{despesa_id} lançada com sucesso.",
                "despesa_id": despesa_id,
                "status": despesa.status,
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao lançar despesa NFS/Recibo: {e}")
        return jsonify({"success": False, "message": f"Erro ao lançar despesa: {str(e)}"}), 500


@fretes_bp.route("/despesas/<int:despesa_id>/download_comprovante")
@login_required
def download_comprovante_despesa(despesa_id):
    """Download do comprovante de uma despesa extra."""
    import os

    despesa = DespesaExtra.query.get_or_404(despesa_id)

    if not despesa.comprovante_path:
        flash("Despesa não possui comprovante anexado.", "warning")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    try:
        # Verificar se é S3 ou local
        if despesa.comprovante_path.startswith("http") or despesa.comprovante_path.startswith("s3://"):
            # Redirect para URL do S3
            from app.utils.file_storage import FileStorage

            file_storage = FileStorage()
            url = file_storage.get_file_url(despesa.comprovante_path)
            if url:
                return redirect(url)
            else:
                flash("Erro ao gerar link do comprovante.", "error")
                return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))
        else:
            # Arquivo local
            arquivo_path = os.path.join(current_app.root_path, "static", despesa.comprovante_path)
            if os.path.exists(arquivo_path):
                return send_file(
                    arquivo_path, download_name=despesa.comprovante_nome_arquivo or "comprovante", as_attachment=True
                )
            else:
                flash("Arquivo do comprovante não encontrado.", "error")
                return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar comprovante: {e}")
        flash(f"Erro ao baixar comprovante: {str(e)}", "error")
        return redirect(url_for("fretes.visualizar_frete", frete_id=despesa.frete_id))


@fretes_bp.route("/api/despesas/pendentes_vinculacao")
@login_required
def api_despesas_pendentes_vinculacao():
    """API: Lista despesas com tipo_documento=CTe pendentes de vinculação."""
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesas = DespesaCteService.get_despesas_pendentes_vinculacao()

    return jsonify(
        {
            "total": len(despesas),
            "despesas": [
                {
                    "id": d.id,
                    "frete_id": d.frete_id,
                    "tipo_despesa": d.tipo_despesa,
                    "valor": d.valor_despesa,
                    "status": d.status,
                }
                for d in despesas
            ],
        }
    )


@fretes_bp.route("/api/despesas/pendentes_lancamento")
@login_required
def api_despesas_pendentes_lancamento():
    """API: Lista despesas prontas para lançamento no Odoo."""
    from app.fretes.services.despesa_cte_service import DespesaCteService

    despesas = DespesaCteService.get_despesas_pendentes_lancamento()

    return jsonify(
        {
            "total": len(despesas),
            "despesas": [
                {
                    "id": d.id,
                    "frete_id": d.frete_id,
                    "tipo_despesa": d.tipo_despesa,
                    "valor": d.valor_despesa,
                    "cte_numero": d.cte.numero_cte if d.cte else None,
                    "status": d.status,
                }
                for d in despesas
            ],
        }
    )


# =================== JOBS ASSÍNCRONOS - LANÇAMENTO ODOO ===================


@fretes_bp.route("/job/<job_id>/status", methods=["GET"])
@login_required
def job_status(job_id):
    """
    Consulta status de um job de lançamento Odoo

    Usado para polling do frontend enquanto o job está processando.

    Returns:
        JSON com status do job:
        - job_id: ID do job
        - status: queued, started, finished, failed
        - status_display: Texto amigável
        - result: Resultado se concluído
        - error: Erro se falhou
    """
    from app.fretes.workers.lancamento_odoo_jobs import get_job_status

    try:
        status = get_job_status(job_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Erro ao consultar status do job {job_id}: {e}")
        return (
            jsonify({"job_id": job_id, "status": "error", "status_display": "Erro ao consultar", "error": str(e)}),
            500,
        )


@fretes_bp.route("/faturas/<int:fatura_id>/lancar-lote", methods=["POST"])
@login_required
@require_financeiro()
def lancar_lote_fatura(fatura_id):
    """
    Enfileira lançamento em lote de todos os fretes e despesas de uma fatura

    Processa todos os itens da fatura de forma assíncrona.

    Body JSON (opcional):
        - data_vencimento: str (YYYY-MM-DD) - Se informado e fatura não tem vencimento, salva na fatura
    """
    try:
        from app.fretes.workers.lancamento_odoo_jobs import lancar_lote_job
        from app.portal.workers import enqueue_job
        from datetime import datetime

        # Validar fatura
        fatura = FaturaFrete.query.get_or_404(fatura_id)

        # ========================================
        # VENCIMENTO: Recebe do body e salva na fatura se não tiver
        # ========================================
        data = request.get_json() or {}
        data_vencimento_str = data.get("data_vencimento")

        # Se fatura não tem vencimento e foi informado um, salva
        if not fatura.vencimento and data_vencimento_str:
            try:
                fatura.vencimento = datetime.strptime(data_vencimento_str, "%Y-%m-%d").date()
                db.session.commit()
                logger.info(f"📅 Vencimento {data_vencimento_str} salvo na fatura #{fatura_id}")
            except ValueError as e:
                return jsonify({"sucesso": False, "mensagem": "Data de vencimento inválida", "erro": str(e)}), 400

        # Usa vencimento da fatura (pode ter sido salvo agora ou já existia)
        data_vencimento = None
        if fatura.vencimento:
            data_vencimento = fatura.vencimento.strftime("%Y-%m-%d")

        if not data_vencimento:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "Fatura não possui vencimento",
                        "erro": "Informe a data de vencimento para lançar no Odoo",
                    }
                ),
                400,
            )

        # Contar itens
        qtd_fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).count()
        qtd_despesas = DespesaExtra.query.filter_by(fatura_frete_id=fatura_id).count()

        if qtd_fretes == 0 and qtd_despesas == 0:
            return (
                jsonify(
                    {
                        "sucesso": False,
                        "mensagem": "Fatura não possui fretes ou despesas para lançar",
                        "erro": "Nenhum item encontrado",
                    }
                ),
                400,
            )

        # Enfileirar job de lote
        logger.info(
            f"📋 Enfileirando lançamento em lote - Fatura #{fatura_id} ({qtd_fretes} fretes, {qtd_despesas} despesas) - Vencimento: {data_vencimento}"
        )

        job = enqueue_job(
            lancar_lote_job,
            fatura_id,
            current_user.nome,
            request.remote_addr,
            data_vencimento,  # Novo parâmetro: vencimento da fatura
            queue_name="odoo_lancamento",
            timeout="30m",  # 30 minutos para lotes
        )

        logger.info(f"✅ Job de lote {job.id} enfileirado para fatura #{fatura_id}")

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": f"Lançamento em lote enfileirado ({qtd_fretes} fretes, {qtd_despesas} despesas)",
                    "job_id": job.id,
                    "fatura_id": fatura_id,
                    "total_fretes": qtd_fretes,
                    "total_despesas": qtd_despesas,
                    "status": "queued",
                }
            ),
            202,
        )  # 202 Accepted

    except Exception as e:
        logger.error(f"Erro ao enfileirar lançamento em lote: {e}")
        import traceback

        traceback.print_exc()

        return jsonify({"sucesso": False, "mensagem": "Erro ao enfileirar lançamento em lote", "erro": str(e)}), 500


@fretes_bp.route("/faturas/<int:fatura_id>/status-lancamento", methods=["GET"])
@login_required
def verificar_status_lancamento_fatura(fatura_id):
    """
    Retorna status de lançamento dos documentos de uma fatura no Odoo

    Usado pelo JavaScript para mostrar resumo e habilitar botão de lançamento.

    Returns:
        JSON com:
        - total_fretes: int
        - fretes_lancados: int
        - fretes_pendentes: int
        - total_despesas: int
        - despesas_lancadas: int
        - despesas_pendentes: int
        - vencimento_fatura: str (YYYY-MM-DD) ou null
        - vencimentos_passados: List[Dict] com docs que têm vencimento < hoje
    """
    from datetime import date

    try:
        fatura = FaturaFrete.query.get_or_404(fatura_id)

        # Buscar fretes
        fretes = Frete.query.filter_by(fatura_frete_id=fatura_id).all()
        fretes_lancados = sum(1 for f in fretes if f.status == "LANCADO_ODOO")
        fretes_pendentes = len(fretes) - fretes_lancados

        # Buscar despesas
        despesas = DespesaExtra.query.filter_by(fatura_frete_id=fatura_id).all()
        despesas_lancadas = sum(1 for d in despesas if d.status == "LANCADO_ODOO")
        despesas_pendentes = len(despesas) - despesas_lancadas

        # Verificar vencimento da fatura
        vencimento_fatura = None
        vencimento_passado = False
        hoje = date.today()

        if fatura.vencimento:
            vencimento_fatura = fatura.vencimento.strftime("%Y-%m-%d")
            vencimento_passado = fatura.vencimento < hoje

        # Lista de documentos com vencimento passado (para detalhe)
        vencimentos_passados = []
        if vencimento_passado and vencimento_fatura:
            vencimentos_passados.append({"tipo": "Fatura", "id": fatura.id, "vencimento": vencimento_fatura})

        return jsonify(
            {
                "sucesso": True,
                "total_fretes": len(fretes),
                "fretes_lancados": fretes_lancados,
                "fretes_pendentes": fretes_pendentes,
                "total_despesas": len(despesas),
                "despesas_lancadas": despesas_lancadas,
                "despesas_pendentes": despesas_pendentes,
                "vencimento_fatura": vencimento_fatura,
                "vencimento_passado": vencimento_passado,
                "vencimentos_passados": vencimentos_passados,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao verificar status de lançamento: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@fretes_bp.route("/jobs/pendentes", methods=["GET"])
@login_required
def jobs_pendentes():
    """
    Lista jobs pendentes e em processamento na fila 'odoo_lancamento'

    Usado para exibir na tela de auditoria os lançamentos em andamento.
    """
    from rq import Queue
    from rq.job import Job
    from app.portal.workers import get_redis_connection

    try:
        conn = get_redis_connection()
        queue = Queue("odoo_lancamento", connection=conn)

        # Jobs na fila (pendentes)
        jobs_queued = []
        for job in queue.jobs[:50]:  # Limitar a 50
            jobs_queued.append(
                {
                    "job_id": job.id,
                    "status": "queued",
                    "status_display": "Na fila",
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "func_name": job.func_name,
                    "args": _extract_job_args(job),
                }
            )

        # Jobs em execução
        workers = queue.connection.smembers("rq:workers:odoo_lancamento")
        jobs_started = []

        # Buscar jobs de todos os workers
        started_registry = queue.started_job_registry
        for job_id in started_registry.get_job_ids()[:20]:
            try:
                job = Job.fetch(job_id, connection=conn)
                jobs_started.append(
                    {
                        "job_id": job.id,
                        "status": "started",
                        "status_display": "Em processamento",
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "func_name": job.func_name,
                        "args": _extract_job_args(job),
                    }
                )
            except Exception:
                pass

        # Jobs falhados recentemente
        failed_registry = queue.failed_job_registry
        jobs_failed = []
        for job_id in failed_registry.get_job_ids()[:10]:
            try:
                job = Job.fetch(job_id, connection=conn)
                jobs_failed.append(
                    {
                        "job_id": job.id,
                        "status": "failed",
                        "status_display": "Falhou",
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                        "func_name": job.func_name,
                        "args": _extract_job_args(job),
                        "error": str(job.exc_info)[:200] if job.exc_info else None,
                    }
                )
            except Exception:
                pass

        return jsonify(
            {
                "sucesso": True,
                "fila": "odoo_lancamento",
                "total_pendentes": len(jobs_queued),
                "total_processando": len(jobs_started),
                "total_falhados": len(jobs_failed),
                "jobs_pendentes": jobs_queued,
                "jobs_processando": jobs_started,
                "jobs_falhados": jobs_failed,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar jobs pendentes: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@fretes_bp.route("/lote/<int:fatura_id>/progresso", methods=["GET"])
@login_required
def progresso_lote(fatura_id):
    """
    Retorna o progresso em tempo real de um lançamento de lote.

    Usado para acompanhar o lançamento de fatura completa (fretes + despesas).
    Os dados são armazenados no Redis durante o processamento do job.
    """
    from app.fretes.workers.lancamento_odoo_jobs import _obter_progresso_lote

    try:
        progresso = _obter_progresso_lote(fatura_id)

        if progresso:
            return jsonify({"sucesso": True, "encontrado": True, "progresso": progresso})
        else:
            # Não há progresso no Redis - pode ser que o lote não esteja em processamento
            # ou que já tenha sido concluído há mais de 1 hora (TTL do Redis)
            return jsonify(
                {"sucesso": True, "encontrado": False, "mensagem": "Nenhum lançamento em andamento para esta fatura"}
            )

    except Exception as e:
        logger.error(f"Erro ao obter progresso do lote {fatura_id}: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500


def _extract_job_args(job):
    """Extrai argumentos do job de forma segura para exibição, incluindo dados extras"""
    try:
        args = job.args or []
        if not args:
            return {}

        func_name = job.func_name or ""

        # lancar_frete_job(frete_id, usuario_nome, usuario_ip, cte_chave, data_vencimento)
        if "lancar_frete_job" in func_name:
            frete_id = args[0] if len(args) > 0 else None
            usuario = args[1] if len(args) > 1 else None
            cte_chave = args[3] if len(args) > 3 else None  # 4º param agora

            # Buscar dados adicionais do frete (sem lazy loading)
            resultado = {
                "tipo": "frete",
                "frete_id": frete_id,
                "cte_chave": cte_chave[:20] + "..." if cte_chave and len(cte_chave) > 20 else cte_chave,
                "usuario": usuario,
            }

            # Tentar buscar número do CTe e transportadora
            if cte_chave:
                try:
                    cte = ConhecimentoTransporte.query.filter_by(chave_acesso=cte_chave).first()
                    if cte:
                        resultado["cte_numero"] = cte.numero_cte
                        resultado["transportadora"] = cte.nome_emitente[:30] if cte.nome_emitente else None
                except Exception:
                    pass

            # Tentar buscar dados do frete (fatura)
            if frete_id:
                try:
                    frete = db.session.get(Frete,frete_id) if frete_id else None
                    if frete:
                        resultado["fatura_numero"] = frete.fatura_frete.numero_fatura if frete.fatura_frete else None
                        resultado["valor_cte"] = float(frete.valor_cte) if frete.valor_cte else None
                except Exception:
                    pass

            return resultado

        # lancar_despesa_job(despesa_id, usuario_nome, usuario_ip, data_vencimento)
        if "lancar_despesa_job" in func_name:
            despesa_id = args[0] if len(args) > 0 else None

            resultado = {"tipo": "despesa", "despesa_id": despesa_id, "usuario": args[1] if len(args) > 1 else None}

            # Tentar buscar dados da despesa
            if despesa_id:
                try:
                    despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
                    if despesa:
                        resultado["tipo_despesa"] = despesa.tipo_despesa
                        resultado["valor"] = float(despesa.valor_despesa) if despesa.valor_despesa else None
                        if despesa.cte:
                            resultado["cte_numero"] = despesa.cte.numero_cte
                except Exception:
                    pass

            return resultado

        # lancar_lote_job(fatura_frete_id, usuario_nome, usuario_ip)
        if "lancar_lote_job" in func_name:
            fatura_id = args[0] if len(args) > 0 else None

            resultado = {"tipo": "lote", "fatura_id": fatura_id, "usuario": args[1] if len(args) > 1 else None}

            # Tentar buscar dados da fatura
            if fatura_id:
                try:
                    fatura = db.session.get(FaturaFrete,fatura_id) if fatura_id else None
                    if fatura:
                        resultado["fatura_numero"] = fatura.numero_fatura
                        resultado["transportadora"] = (
                            fatura.transportadora.razao_social if fatura.transportadora else None
                        )
                        resultado["total_fretes"] = len(fatura.fretes) if fatura.fretes else 0
                except Exception:
                    pass

            return resultado

        return {"args": str(args)[:100]}

    except Exception:
        return {}


# =================== AUDITORIA DE LANÇAMENTOS ODOO ===================


@fretes_bp.route("/auditoria-lancamentos")
@login_required
@require_financeiro()
def auditoria_lancamentos():
    """
    Tela de listagem dos lançamentos de frete/despesa no Odoo.
    Mostra status geral de cada lançamento com visualização inline das etapas.
    """
    from app.fretes.models import LancamentoFreteOdooAuditoria
    from sqlalchemy import func, case

    # Parâmetros de filtro
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    filtro_status = request.args.get("status", "")  # SUCESSO, ERRO, todos
    filtro_tipo = request.args.get("tipo", "")  # frete, despesa, todos
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    # Subquery para pegar a última etapa de cada lançamento (agrupado por chave_cte)
    # e verificar se teve erro em alguma etapa
    subquery_lancamentos = db.session.query(
        LancamentoFreteOdooAuditoria.chave_cte,
        LancamentoFreteOdooAuditoria.frete_id,
        LancamentoFreteOdooAuditoria.despesa_extra_id,
        func.max(LancamentoFreteOdooAuditoria.etapa).label("ultima_etapa"),
        func.max(LancamentoFreteOdooAuditoria.executado_em).label("ultimo_executado"),
        func.max(LancamentoFreteOdooAuditoria.dfe_id).label("dfe_id"),
        func.max(LancamentoFreteOdooAuditoria.purchase_order_id).label("po_id"),
        func.max(LancamentoFreteOdooAuditoria.invoice_id).label("invoice_id"),
        func.max(LancamentoFreteOdooAuditoria.executado_por).label("executado_por"),
        func.sum(case((LancamentoFreteOdooAuditoria.status == "ERRO", 1), else_=0)).label("qtd_erros"),
    ).group_by(
        LancamentoFreteOdooAuditoria.chave_cte,
        LancamentoFreteOdooAuditoria.frete_id,
        LancamentoFreteOdooAuditoria.despesa_extra_id,
    )

    # Aplicar filtros
    if filtro_tipo == "frete":
        subquery_lancamentos = subquery_lancamentos.filter(LancamentoFreteOdooAuditoria.frete_id.isnot(None))
    elif filtro_tipo == "despesa":
        subquery_lancamentos = subquery_lancamentos.filter(LancamentoFreteOdooAuditoria.despesa_extra_id.isnot(None))

    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            subquery_lancamentos = subquery_lancamentos.filter(LancamentoFreteOdooAuditoria.executado_em >= dt_inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
            dt_fim = dt_fim.replace(hour=23, minute=59, second=59)
            subquery_lancamentos = subquery_lancamentos.filter(LancamentoFreteOdooAuditoria.executado_em <= dt_fim)
        except ValueError:
            pass

    # Ordenar por data mais recente
    subquery_lancamentos = subquery_lancamentos.order_by(desc("ultimo_executado"))

    # Executar subquery
    lancamentos_raw = subquery_lancamentos.all()

    # Filtrar por status após agregar
    if filtro_status == "SUCESSO":
        lancamentos_raw = [row for row in lancamentos_raw if row.qtd_erros == 0 and row.ultima_etapa == 16]
    elif filtro_status == "ERRO":
        lancamentos_raw = [row for row in lancamentos_raw if row.qtd_erros > 0 or row.ultima_etapa < 16]
    elif filtro_status == "INCOMPLETO":
        lancamentos_raw = [row for row in lancamentos_raw if row.qtd_erros == 0 and row.ultima_etapa < 16]

    # Paginação manual
    total = len(lancamentos_raw)
    total_pages = math.ceil(total / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    lancamentos_paginated = lancamentos_raw[start:end]

    # Buscar detalhes dos fretes e despesas
    lancamentos = []
    for row in lancamentos_paginated:
        item = {
            "chave_cte": row.chave_cte,
            "frete_id": row.frete_id,
            "despesa_extra_id": row.despesa_extra_id,
            "ultima_etapa": row.ultima_etapa,
            "ultimo_executado": row.ultimo_executado,
            "dfe_id": row.dfe_id,
            "po_id": row.po_id,
            "invoice_id": row.invoice_id,
            "executado_por": row.executado_por,
            "qtd_erros": row.qtd_erros,
            "status": (
                "SUCESSO"
                if row.qtd_erros == 0 and row.ultima_etapa == 16
                else ("ERRO" if row.qtd_erros > 0 else "INCOMPLETO")
            ),
            "tipo": "frete" if row.frete_id else "despesa",
            "frete": None,
            "despesa": None,
        }

        # Buscar frete ou despesa
        if row.frete_id:
            item["frete"] = db.session.get(Frete,row.frete_id) if row.frete_id else None
        if row.despesa_extra_id:
            item["despesa"] = db.session.get(DespesaExtra,row.despesa_extra_id) if row.despesa_extra_id else None

        lancamentos.append(item)

    return render_template(
        "fretes/auditoria_lancamentos.html",
        lancamentos=lancamentos,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        filtro_status=filtro_status,
        filtro_tipo=filtro_tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@fretes_bp.route("/api/auditoria-lancamentos/<chave_cte>")
@login_required
def api_auditoria_detalhes(chave_cte):
    """
    API: Retorna detalhes das etapas de um lançamento específico.
    Usado para exibir inline na tela de listagem.
    """
    from app.fretes.models import LancamentoFreteOdooAuditoria

    frete_id = request.args.get("frete_id", type=int)
    despesa_id = request.args.get("despesa_id", type=int)

    query = LancamentoFreteOdooAuditoria.query.filter_by(chave_cte=chave_cte)

    if frete_id:
        query = query.filter_by(frete_id=frete_id)
    if despesa_id:
        query = query.filter_by(despesa_extra_id=despesa_id)

    auditorias = query.order_by(LancamentoFreteOdooAuditoria.etapa).all()

    return jsonify(
        {
            "total": len(auditorias),
            "etapas": [
                {
                    "id": a.id,
                    "etapa": a.etapa,
                    "etapa_descricao": a.etapa_descricao,
                    "modelo_odoo": a.modelo_odoo,
                    "metodo_odoo": a.metodo_odoo,
                    "acao": a.acao,
                    "status": a.status,
                    "mensagem": a.mensagem,
                    "erro_detalhado": a.erro_detalhado[:500] if a.erro_detalhado else None,
                    "tempo_execucao_ms": a.tempo_execucao_ms,
                    "executado_em": a.executado_em.strftime("%d/%m/%Y %H:%M:%S") if a.executado_em else None,
                    "dfe_id": a.dfe_id,
                    "purchase_order_id": a.purchase_order_id,
                    "invoice_id": a.invoice_id,
                }
                for a in auditorias
            ],
        }
    )


@fretes_bp.route("/faturas/exportar-fechamento-freteiros")
@login_required
@require_profiles('administrador', 'gerente_financeiro', 'financeiro', 'logistica')
def exportar_fechamento_freteiros():
    """
    Exporta fechamento de freteiros com 2 abas:
    - Aba "Detalhamento": Dados individuais de cada frete/despesa
    - Aba "Resumo": Totais por transportadora com dados bancários

    Filtros via query string: transportadora_id, data_criacao_de, data_criacao_ate
    """
    from io import BytesIO
    import pandas as pd
    from flask import make_response
    import locale

    # Função para formatar valores no padrão brasileiro
    def formatar_valor_br(valor):
        """Formata valor com milhar (.) e decimal (,) com 2 casas"""
        if valor is None or valor == 0:
            return "0,00"
        # Formata com 2 casas decimais e substitui separadores
        valor_str = f"{valor:,.2f}"
        # Troca . por # temporariamente, depois , por . e # por ,
        valor_str = valor_str.replace(",", "#").replace(".", ",").replace("#", ".")
        return valor_str

    # Capturar filtros
    transportadora_id = request.args.get("transportadora_id", "")
    data_criacao_de = request.args.get("data_criacao_de", "")
    data_criacao_ate = request.args.get("data_criacao_ate", "")

    # Montar query base - apenas transportadoras que são freteiros
    query = FaturaFrete.query.join(Transportadora).filter(
        Transportadora.freteiro == True
    )

    # Aplicar filtros
    if transportadora_id:
        try:
            query = query.filter(FaturaFrete.transportadora_id == int(transportadora_id))
        except (ValueError, TypeError):
            pass

    # Filtro por data de CRIAÇÃO da fatura
    if data_criacao_de:
        try:
            data_de = datetime.strptime(data_criacao_de, "%Y-%m-%d")
            query = query.filter(FaturaFrete.criado_em >= data_de)
        except ValueError:
            pass

    if data_criacao_ate:
        try:
            data_ate = datetime.strptime(data_criacao_ate, "%Y-%m-%d")
            # Adiciona 1 dia para incluir todo o dia final
            data_ate = data_ate.replace(hour=23, minute=59, second=59)
            query = query.filter(FaturaFrete.criado_em <= data_ate)
        except ValueError:
            pass

    # Executar query
    faturas = query.order_by(desc(FaturaFrete.criado_em)).all()

    if not faturas:
        flash("Nenhuma fatura de freteiro encontrada com os filtros selecionados.", "warning")
        return redirect(url_for("fretes.listar_faturas"))

    # ========== ABA 1: DETALHAMENTO ==========
    dados_detalhamento = []

    for fatura in faturas:
        transportadora = fatura.transportadora

        # Processar FRETES da fatura
        for frete in fatura.fretes:
            dados_detalhamento.append({
                "CNPJ Transportadora": transportadora.cnpj if transportadora else "",
                "Transportadora": transportadora.razao_social if transportadora else "",
                "Tipo": "Frete",
                "Fatura": fatura.numero_fatura,
                "CTE": frete.numero_cte or "",
                "NFs": frete.numeros_nfs or "",
                "Cliente": frete.nome_cliente or "",
                "Valor NFs": formatar_valor_br(float(frete.valor_total_nfs or 0)),
                "Peso NFs": formatar_valor_br(float(frete.peso_total or 0)),
                "Valor Frete/Despesa": formatar_valor_br(float(frete.valor_cte or frete.valor_cotado or 0)),
                "Transp. Original (Frete)": "",  # ✅ Vazio para fretes (mesma transportadora)
            })

        # Processar DESPESAS EXTRAS da fatura
        for despesa in fatura.todas_despesas_extras():
            # Buscar dados do frete vinculado à despesa
            frete_despesa = despesa.frete if despesa.frete else None
            nfs_despesa = frete_despesa.numeros_nfs if frete_despesa else ""
            cliente_despesa = frete_despesa.nome_cliente if frete_despesa else ""
            valor_nfs_despesa = float(frete_despesa.valor_total_nfs or 0) if frete_despesa else 0
            peso_nfs_despesa = float(frete_despesa.peso_total or 0) if frete_despesa else 0

            # ✅ NOVO: Indicar quando despesa usa transportadora alternativa
            transportadora_frete = ""
            if despesa.usa_transportadora_alternativa and frete_despesa:
                transportadora_frete = frete_despesa.transportadora.razao_social if frete_despesa.transportadora else ""

            dados_detalhamento.append({
                "CNPJ Transportadora": transportadora.cnpj if transportadora else "",
                "Transportadora": transportadora.razao_social if transportadora else "",
                "Tipo": despesa.tipo_despesa or "Despesa Extra",
                "Fatura": fatura.numero_fatura,
                "CTE": despesa.numero_documento or "",
                "NFs": nfs_despesa,
                "Cliente": cliente_despesa,
                "Valor NFs": formatar_valor_br(valor_nfs_despesa),
                "Peso NFs": formatar_valor_br(peso_nfs_despesa),
                "Valor Frete/Despesa": formatar_valor_br(float(despesa.valor_despesa or 0)),
                "Transp. Original (Frete)": transportadora_frete,  # ✅ NOVO: Mostra se é diferente
            })

    df_detalhamento = pd.DataFrame(dados_detalhamento)

    # ========== ABA 2: RESUMO POR TRANSPORTADORA ==========
    # Agrupar valores por transportadora
    resumo_transportadoras = {}
    transportadoras_info = {}

    for fatura in faturas:
        transportadora = fatura.transportadora
        if not transportadora:
            continue

        transp_id = transportadora.id

        # Armazenar informações da transportadora
        if transp_id not in transportadoras_info:
            transportadoras_info[transp_id] = transportadora
            resumo_transportadoras[transp_id] = 0

        # Somar fretes
        for frete in fatura.fretes:
            resumo_transportadoras[transp_id] += float(frete.valor_cte or frete.valor_cotado or 0)

        # Somar despesas extras
        for despesa in fatura.todas_despesas_extras():
            resumo_transportadoras[transp_id] += float(despesa.valor_despesa or 0)

    # Montar dados do resumo
    dados_resumo = []
    for transp_id, valor_total in resumo_transportadoras.items():
        t = transportadoras_info[transp_id]

        # Formatar tipo de conta
        tipo_conta_formatado = ""
        if t.tipo_conta:
            tipo_conta_formatado = t.tipo_conta.replace("corrente", "Corrente").replace("poupanca", "Poupança")

        dados_resumo.append({
            "CNPJ": t.cnpj or "",
            "Transportadora": t.razao_social or "",
            "Banco": t.banco or "",
            "Agência": t.agencia or "",
            "Conta": t.conta or "",
            "Tipo Conta": tipo_conta_formatado,
            "PIX": t.pix or "",
            "CPF/CNPJ Favorecido": t.cpf_cnpj_favorecido or "",
            "Obs. Financeira": t.obs_financ or "",
            "Valor Total": formatar_valor_br(valor_total),
        })

    df_resumo = pd.DataFrame(dados_resumo)

    # Ordenar resumo por transportadora (alfabético)
    if not df_resumo.empty:
        df_resumo = df_resumo.sort_values("Transportadora", ascending=True)

    # ========== GERAR EXCEL ==========
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Aba 1: Detalhamento
        if not df_detalhamento.empty:
            df_detalhamento.to_excel(writer, index=False, sheet_name="Detalhamento")
            # Ajustar larguras
            worksheet = writer.sheets["Detalhamento"]
            for idx, col in enumerate(df_detalhamento.columns):
                max_length = max(df_detalhamento[col].fillna('').astype(str).map(len).max(), len(col)) + 2
                col_letter = chr(65 + idx) if idx < 26 else "A" + chr(65 + idx - 26)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)

        # Aba 2: Resumo
        if not df_resumo.empty:
            df_resumo.to_excel(writer, index=False, sheet_name="Resumo por Transportadora")
            worksheet = writer.sheets["Resumo por Transportadora"]
            for idx, col in enumerate(df_resumo.columns):
                max_length = max(df_resumo[col].fillna('').astype(str).map(len).max(), len(col)) + 2
                col_letter = chr(65 + idx) if idx < 26 else "A" + chr(65 + idx - 26)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)

    output.seek(0)

    # Criar resposta
    response = make_response(output.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = f"attachment; filename=fechamento_freteiros_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return response


# =============================================================================
# RELATÓRIO DE ANÁLISE DE FRETES
# =============================================================================

@fretes_bp.route("/relatorios/analise-fretes")
@login_required
@require_financeiro()
def relatorio_analise_fretes():
    """Página do relatório de análise de fretes"""
    transportadoras = Transportadora.query.filter_by(ativo=True).order_by(Transportadora.razao_social).all()
    return render_template(
        "fretes/relatorio_analise_fretes.html",
        transportadoras=transportadoras
    )


@fretes_bp.route("/api/relatorios/analise-fretes", methods=["POST"])
@login_required
@require_financeiro()
def api_relatorio_analise_fretes():
    """API para gerar relatório Excel de análise de fretes"""
    from app.fretes.services.relatorio_analise_fretes_service import (
        buscar_dados_relatorio,
        gerar_excel_relatorio
    )

    try:
        data = request.json or {}
        data_inicio = data.get("data_inicio")
        data_fim = data.get("data_fim")
        transportadora_id = data.get("transportadora_id")
        abrir_despesa_tipo = data.get("abrir_despesa_tipo", False)

        # Validações
        if not data_inicio or not data_fim:
            return jsonify({"error": "Período obrigatório (data_inicio e data_fim)"}), 400

        # Converter transportadora_id para int se informado
        if transportadora_id:
            try:
                transportadora_id = int(transportadora_id)
            except (ValueError, TypeError):
                transportadora_id = None

        logger.info(f"Gerando relatório de análise de fretes: {data_inicio} a {data_fim}, transportadora={transportadora_id}, abrir_despesa_tipo={abrir_despesa_tipo}")

        # Buscar dados e gerar Excel
        dados = buscar_dados_relatorio(data_inicio, data_fim, transportadora_id)

        # Verificar se há dados
        if not dados['fretes']:
            return jsonify({
                "error": f"Nenhum frete encontrado no período {data_inicio} a {data_fim}. "
                         f"Foram encontradas {len(dados['faturamento_por_nf'])} NFs no faturamento, "
                         "mas nenhuma está associada a um frete cadastrado."
            }), 404

        output = gerar_excel_relatorio(dados, data_inicio, data_fim, abrir_despesa_tipo=abrir_despesa_tipo)

        filename = f"analise_fretes_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.exception(f"Erro ao gerar relatório de análise de fretes: {e}")
        return jsonify({"error": f"Erro ao gerar relatório: {str(e)}"}), 500
