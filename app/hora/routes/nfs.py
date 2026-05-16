"""Rotas de NF de entrada (Motochefe -> HORA): upload, listagem, vinculo e match."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from app.hora.decorators import require_hora_perm

from app.hora.models import HoraLoja, HoraNfEntrada, HoraPedido
from app.hora.routes import hora_bp
from app.hora.services import nf_entrada_service, matching_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)
from app.hora.services.parsers.danfe_adapter import DanfeParseError


def _pedidos_candidatos_para_lojas(permitidas, loja_id=None, limit=50):
    """Helper: lista pedidos ABERTO/PARCIAL filtrando por lojas permitidas
    e opcionalmente por loja especifica.
    """
    query = (
        HoraPedido.query
        .filter(HoraPedido.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
    )
    if permitidas is not None:
        if not permitidas:
            return []
        query = query.filter(HoraPedido.loja_destino_id.in_(permitidas))
    if loja_id:
        query = query.filter(HoraPedido.loja_destino_id == loja_id)
    return (
        query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
        .limit(limit)
        .all()
    )


def _lojas_ativas_permitidas():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


# ------------------------------------------------------------------------
# Listagem / detalhe
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/exportar')
@require_hora_perm('nfs', 'ver')
def nfs_exportar():
    """Exporta NFs de entrada para XLSX. Filtros: data_inicio, data_fim, loja_id."""
    import io as _io

    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()
    loja_str = (request.args.get('loja_id') or '').strip()

    try:
        data_inicio = datetime.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else (date.today() - timedelta(days=30))
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else date.today()
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    escopo = lojas_permitidas_ids()
    if loja_str.isdigit():
        loja_id = int(loja_str)
        if escopo is not None and loja_id not in escopo:
            flash('Acesso negado: loja fora do seu escopo.', 'danger')
            return redirect(url_for('hora.nfs_lista'))
        lojas_filtro = [loja_id]
    else:
        lojas_filtro = list(escopo) if escopo is not None else None

    xlsx_bytes = nf_entrada_service.exportar_nfs_excel(
        data_inicio=data_inicio,
        data_fim=data_fim,
        lojas_ids=lojas_filtro,
    )

    filename = f'nfs_compra_hora_{data_inicio.isoformat()}_a_{data_fim.isoformat()}.xlsx'
    return send_file(
        _io.BytesIO(xlsx_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


@hora_bp.route('/nfs')
@require_hora_perm('nfs', 'ver')
def nfs_lista():
    numero_nf = (request.args.get('numero_nf') or '').strip() or None
    emitente = (request.args.get('emitente') or '').strip() or None
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()
    vinculo_status = (request.args.get('vinculo') or '').strip() or None
    if vinculo_status not in (None, 'vinculada', 'sem_pedido'):
        vinculo_status = None

    try:
        data_inicio = datetime.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else None
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    nfs = nf_entrada_service.listar_nfs_entrada(
        limit=200,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        numero_nf=numero_nf,
        emitente=emitente,
        loja_id=loja_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        vinculo_status=vinculo_status,
    )
    # Bulk: chassis de cada pedido vinculado (1 query vs N).
    pedido_ids = list({nf.pedido_id for nf in nfs if nf.pedido_id})
    chassis_por_pedido = matching_service.chassis_pedido_batch(pedido_ids)
    resumos = {
        nf.id: matching_service.resumo_vinculo_nf(nf, chassis_por_pedido)
        for nf in nfs
    }
    # Comparativo de valores (NF vs pedido vinculado, match/sem-match por chassi).
    comparativos_valores = matching_service.comparativos_valores_nfs_batch(nfs)
    lojas_ativas = _lojas_ativas_permitidas()
    return render_template(
        'hora/nfs_lista.html',
        nfs=nfs,
        resumos=resumos,
        comparativos_valores=comparativos_valores,
        lojas_ativas=lojas_ativas,
        filtro_numero_nf=numero_nf,
        filtro_emitente=emitente,
        filtro_loja_id=loja_id,
        filtro_data_inicio=data_ini_str,
        filtro_data_fim=data_fim_str,
        filtro_vinculo=vinculo_status,
    )


@hora_bp.route('/nfs/<int:nf_id>')
@require_hora_perm('nfs', 'ver')
def nfs_detalhe(nf_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    # Lojas permitidas: usadas tanto para "definir loja" (NF legada sem loja)
    # quanto para "alterar loja" (NF com loja ja definida).
    lojas_ativas = _lojas_ativas_permitidas()

    # Pedidos candidatos para vinculo rapido (filtrados pela loja da NF)
    pedidos_disponiveis = []
    if not nf.pedido_id and nf.loja_destino_id:
        pedidos_disponiveis = _pedidos_candidatos_para_lojas(
            permitidas=lojas_permitidas_ids(),
            loja_id=nf.loja_destino_id,
            limit=50,
        )

    # Vinculo por chassi: {chassi: {'pedido': ..., 'pedido_item': ..., 'vinculado_a_nf': bool}}
    vinculos = matching_service.vinculo_por_chassi_nf(nf.id)

    # Comparativo de valores (NF vs pedido vinculado, match/sem-match por chassi).
    comparativo_valores = matching_service.comparativo_valores_nf(nf)

    return render_template(
        'hora/nf_detalhe.html',
        nf=nf,
        pedidos_disponiveis=pedidos_disponiveis,
        lojas_ativas=lojas_ativas,
        vinculos_por_chassi=vinculos,
        comparativo_valores=comparativo_valores,
    )


# ------------------------------------------------------------------------
# Upload DANFE
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/upload', methods=['GET', 'POST'])
@require_hora_perm('nfs', 'criar')
def nfs_upload():
    """Upload DANFE PDF. Parsea via adapter e cria HoraNfEntrada + itens."""
    permitidas = lojas_permitidas_ids()
    lojas_ativas = _lojas_ativas_permitidas()

    # Pedidos por loja (para o auto-fill no JS do template)
    pedidos_disponiveis = _pedidos_candidatos_para_lojas(
        permitidas=permitidas, loja_id=None, limit=100,
    )

    if request.method == 'POST':
        arquivo = request.files.get('pdf')
        if not arquivo or arquivo.filename == '':
            flash('Selecione um arquivo PDF.', 'danger')
            return render_template(
                'hora/nf_upload.html',
                pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
            )

        pedido_id_str = request.form.get('pedido_id') or ''
        pedido_id_sugerido = int(pedido_id_str) if pedido_id_str.isdigit() else None

        loja_destino_str = request.form.get('loja_destino_id') or ''
        loja_destino_id = int(loja_destino_str) if loja_destino_str.isdigit() else None

        # Valida permissao sobre a loja selecionada
        if loja_destino_id and not usuario_tem_acesso_a_loja(loja_destino_id):
            flash('Acesso negado a essa loja.', 'danger')
            return render_template(
                'hora/nf_upload.html',
                pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
            )

        # Valida permissao sobre o pedido (se informado)
        if pedido_id_sugerido:
            ped = HoraPedido.query.get(pedido_id_sugerido)
            if not ped or (
                ped.loja_destino_id
                and not usuario_tem_acesso_a_loja(ped.loja_destino_id)
            ):
                flash('Acesso negado ao pedido selecionado.', 'danger')
                return render_template(
                    'hora/nf_upload.html',
                    pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
                )

        try:
            pdf_bytes = arquivo.read()
            nf = nf_entrada_service.importar_danfe_pdf(
                pdf_bytes=pdf_bytes,
                nome_arquivo_origem=arquivo.filename,
                pedido_id_sugerido=pedido_id_sugerido,
                loja_destino_id=loja_destino_id,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(
                f'NF {nf.numero_nf} importada ({len(nf.itens)} chassi(s)) '
                f'-> {nf.loja_destino.rotulo_display if nf.loja_destino else "sem loja"}.',
                'success',
            )
            # Se nao foi vinculada a pedido, vai para modal de match
            if not nf.pedido_id:
                return redirect(url_for('hora.nfs_match', nf_id=nf.id))
            return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
        except nf_entrada_service.NfEntradaJaImportada as exc:
            flash(str(exc), 'warning')
        except (ValueError, DanfeParseError) as exc:
            flash(f'Erro ao importar: {exc}', 'danger')
        except Exception as exc:  # pragma: no cover
            flash(f'Erro inesperado: {exc}', 'danger')

    return render_template(
        'hora/nf_upload.html',
        pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
    )


# ------------------------------------------------------------------------
# Upload em lote (N DANFEs com loja default MOTOCHEFE MATRIZ SP)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/upload-lote', methods=['GET', 'POST'])
@require_hora_perm('nfs', 'criar')
def nfs_upload_lote():
    """Upload em lote de N DANFEs com loja default MOTOCHEFE MATRIZ SP.

    Fluxo:
      - GET: tela com seletor de loja (matriz pre-selecionada) + input multiple.
      - POST: processa cada PDF, cria NFs com a loja default, retorna tela
        de resultado com cards (sucesso/duplicada/erro). Cada card de sucesso
        traz form inline para alterar a loja daquela NF (via nfs_alterar_loja).
    """
    permitidas = lojas_permitidas_ids()
    lojas_ativas = _lojas_ativas_permitidas()

    # Busca a loja default. Pode ser None se foi removida do cadastro ou se
    # esta inativa. Se o usuario nao tem acesso a essa loja, tambem nao
    # aplicamos como default (mas ele ainda pode escolher outra).
    loja_default = nf_entrada_service.get_loja_default_matriz()
    loja_default_id = None
    if loja_default and (permitidas is None or loja_default.id in permitidas):
        loja_default_id = loja_default.id

    if request.method == 'POST':
        arquivos_upload = request.files.getlist('pdfs')
        if not arquivos_upload or all(
            (not a or not a.filename) for a in arquivos_upload
        ):
            flash('Selecione um ou mais arquivos PDF.', 'danger')
            return render_template(
                'hora/nf_upload_lote.html',
                lojas_ativas=lojas_ativas,
                loja_default_id=loja_default_id,
                loja_default_label=(
                    loja_default.rotulo_display if loja_default else None
                ),
            )

        loja_str = (request.form.get('loja_destino_id') or '').strip()
        if loja_str.isdigit():
            loja_destino_id = int(loja_str)
        elif loja_default_id:
            loja_destino_id = loja_default_id
        else:
            flash(
                'Loja de destino nao foi informada e default '
                'MOTOCHEFE MATRIZ SP nao esta disponivel.',
                'danger',
            )
            return render_template(
                'hora/nf_upload_lote.html',
                lojas_ativas=lojas_ativas,
                loja_default_id=loja_default_id,
                loja_default_label=(
                    loja_default.rotulo_display if loja_default else None
                ),
            )

        if not usuario_tem_acesso_a_loja(loja_destino_id):
            flash('Acesso negado a essa loja.', 'danger')
            return render_template(
                'hora/nf_upload_lote.html',
                lojas_ativas=lojas_ativas,
                loja_default_id=loja_default_id,
                loja_default_label=(
                    loja_default.rotulo_display if loja_default else None
                ),
            )

        # Filtra apenas PDFs reais (FileStorage objects do Werkzeug). Acumula
        # ignorados para mostrar no resultado.
        arquivos: list = []
        ignorados: list[str] = []
        for f in arquivos_upload:
            if not f or not f.filename:
                continue
            if not f.filename.lower().endswith('.pdf'):
                ignorados.append(f.filename)
                continue
            try:
                arquivos.append((f.filename, f.read()))
            except Exception as exc:  # pragma: no cover
                ignorados.append(f'{f.filename} (erro de leitura: {exc})')

        if not arquivos:
            flash(
                'Nenhum PDF valido enviado.'
                + (f' Ignorados: {", ".join(ignorados)}' if ignorados else ''),
                'danger',
            )
            return render_template(
                'hora/nf_upload_lote.html',
                lojas_ativas=lojas_ativas,
                loja_default_id=loja_default_id,
                loja_default_label=(
                    loja_default.rotulo_display if loja_default else None
                ),
            )

        resultado = nf_entrada_service.importar_danfe_pdfs_lote(
            arquivos=arquivos,
            loja_destino_id=loja_destino_id,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
        )

        loja_aplicada = HoraLoja.query.get(loja_destino_id)
        return render_template(
            'hora/nf_upload_lote_resultado.html',
            resultado=resultado,
            ignorados=ignorados,
            lojas_ativas=lojas_ativas,
            loja_aplicada=loja_aplicada,
        )

    # GET
    return render_template(
        'hora/nf_upload_lote.html',
        lojas_ativas=lojas_ativas,
        loja_default_id=loja_default_id,
        loja_default_label=(
            loja_default.rotulo_display if loja_default else None
        ),
    )


# ------------------------------------------------------------------------
# Download PDF DANFE
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/download-pdf')
@require_hora_perm('nfs', 'ver')
def nfs_download_pdf(nf_id: int):
    """Redireciona para URL (S3 presigned ou local) do PDF DANFE da NF."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    if not nf.arquivo_pdf_s3_key:
        flash('PDF desta NF nao esta armazenado (import anterior a esta feature).', 'warning')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(nf.arquivo_pdf_s3_key)
    if not url:
        flash('Falha ao gerar URL do PDF.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
    return redirect(url)


# ------------------------------------------------------------------------
# Edicao manual de item da NF (corrigir chassi/motor)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/itens/<int:item_id>/editar', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_editar_item(nf_id: int, item_id: int):
    """Corrige numero_chassi e/ou numero_motor_texto_original de um item de NF.

    Use case: parser LLM inverteu chassi<->motor, ou emissor emitiu NF com
    chassi divergente do pedido (ex: digito do meio errado). Operador
    autorizado pode corrigir aqui.
    """
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'

    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    # NF sem loja atribuida: somente admin (escopo None = todas lojas) pode editar.
    # Usuario com escopo restrito nao deve editar NF "flutuante" — pode pertencer
    # a loja fora do escopo dele.
    if not nf.loja_destino_id and lojas_permitidas_ids() is not None:
        if is_ajax:
            return jsonify({
                'ok': False,
                'erro': 'NF sem loja atribuida; defina a loja antes de editar itens.'
            }), 403
        flash(
            'NF sem loja atribuida. Defina a loja de destino antes de editar itens.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    numero_chassi = (request.form.get('numero_chassi') or '').strip().upper() or None
    numero_motor = (request.form.get('numero_motor_texto_original') or '').strip() or None

    try:
        res = nf_entrada_service.editar_nf_item_manual(
            nf_id=nf.id,
            nf_item_id=item_id,
            numero_chassi=numero_chassi,
            numero_motor_texto_original=numero_motor,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        if is_ajax:
            return jsonify(res)
        # Mostra resultado da revalidacao (ex.: "casa com pedido vinculado")
        msg = f"Item atualizado — vinculo: {res.get('vinculo_status', 'n/a')}"
        if res.get('pedidos_revalidados'):
            msg += f" · pedidos revalidados: {res['pedidos_revalidados']}"
        flash(msg, 'success')
    except ValueError as exc:
        if is_ajax:
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro: {exc}', 'danger')

    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Definir loja (NF legada)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/definir-loja', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_definir_loja(nf_id: int):
    """Preenche loja_destino_id em NF legada (pre-requisito para match)."""
    from app import db
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id:
        flash('NF ja tem loja definida.', 'warning')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja_str = (request.form.get('loja_destino_id') or '').strip()
    if not loja_str.isdigit():
        flash('Selecione a loja de destino.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja_id = int(loja_str)
    if not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        flash(f'Loja {loja_id} nao encontrada.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    nf.loja_destino_id = loja_id
    db.session.commit()
    flash(f'Loja {loja.rotulo_display} definida para a NF.', 'success')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Alterar loja vinculada (NF com loja ja definida)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/alterar-loja', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_alterar_loja(nf_id: int):
    """Troca a loja_destino_id de uma NF.

    Diferente de `nfs_definir_loja` (que so funciona quando a NF nao tem
    loja), esta rota cobre o caso de NF que ja tem loja e o operador
    quer corrigir/realocar para outra. O service aplica os bloqueios de
    coerencia (recebimento ja feito em outra loja, pedido vinculado de
    outra loja, loja inativa).
    """
    nf = HoraNfEntrada.query.get_or_404(nf_id)

    # Permissao de loja ATUAL (se houver)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    # NF sem loja + escopo restrito → admin only (mesma logica de nfs_editar_item)
    if not nf.loja_destino_id and lojas_permitidas_ids() is not None:
        flash(
            'NF sem loja atribuida; apenas usuario com escopo total pode definir/alterar.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja_str = (request.form.get('loja_destino_id') or '').strip()
    if not loja_str.isdigit():
        flash('Selecione a nova loja de destino.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    nova_loja_id = int(loja_str)
    # Permissao da loja NOVA
    if not usuario_tem_acesso_a_loja(nova_loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    try:
        res = nf_entrada_service.alterar_loja_nf_entrada(
            nf_id=nf.id,
            nova_loja_id=nova_loja_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        if res.get('inalterado'):
            flash('A loja informada e a mesma ja vinculada — nada a fazer.', 'info')
        else:
            flash('Loja da NF alterada com sucesso.', 'success')
    except ValueError as exc:
        flash(f'Erro ao alterar loja: {exc}', 'danger')
    except Exception as exc:  # pragma: no cover
        flash(f'Erro inesperado: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Remover NF de entrada
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/remover', methods=['POST'])
@require_hora_perm('nfs', 'apagar')
def nfs_remover(nf_id: int):
    """Remove a NF e seus itens (cascade). Bloqueia se houver recebimento
    fisico ou devolucao a fornecedor vinculados — nesse caso o operador
    precisa cancelar/excluir essas dependencias antes.
    """
    nf = HoraNfEntrada.query.get_or_404(nf_id)

    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    # NF sem loja + escopo restrito → admin only
    if not nf.loja_destino_id and lojas_permitidas_ids() is not None:
        flash(
            'NF sem loja atribuida; apenas usuario com escopo total pode remover.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    # Tambem valida escopo do PEDIDO vinculado: remover a NF altera o status
    # do pedido (FATURADO -> ABERTO/PARCIAL), logo o usuario precisa ter
    # acesso aquele pedido tambem.
    if nf.pedido_id:
        pedido_vinc = HoraPedido.query.get(nf.pedido_id)
        if (
            pedido_vinc
            and pedido_vinc.loja_destino_id
            and not usuario_tem_acesso_a_loja(pedido_vinc.loja_destino_id)
        ):
            flash(
                'NF vinculada a pedido de loja fora do seu escopo — '
                'remocao alteraria status do pedido. Operacao bloqueada.',
                'danger',
            )
            return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    numero_nf = nf.numero_nf
    try:
        res = nf_entrada_service.remover_nf_entrada(
            nf_id=nf.id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        n_itens = len(res.get('chassis_removidos') or [])
        n_motos = len(res.get('motos_orfas_removidas') or [])
        msg = f'NF {numero_nf} removida ({n_itens} item(ns)'
        if n_motos:
            msg += f', {n_motos} moto(s) orfa(s) limpa(s)'
        msg += ').'
        flash(msg, 'success')
        return redirect(url_for('hora.nfs_lista'))
    except nf_entrada_service.NfEntradaTemDependencias as exc:
        flash(f'Nao foi possivel remover: {exc}', 'warning')
    except ValueError as exc:
        flash(f'Erro ao remover NF: {exc}', 'danger')
    except Exception as exc:  # pragma: no cover
        flash(f'Erro inesperado: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Vinculo manual rapido (form do nf_detalhe)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/vincular-pedido', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_vincular_pedido(nf_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    pedido_id_str = request.form.get('pedido_id') or ''
    if not pedido_id_str.isdigit():
        flash('Pedido invalido.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    pedido_id = int(pedido_id_str)

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        flash(f'Pedido {pedido_id} nao encontrado.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    # Valida loja
    if nf.loja_destino_id and pedido.loja_destino_id and nf.loja_destino_id != pedido.loja_destino_id:
        flash('Pedido e de loja diferente da NF.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado ao pedido selecionado.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))

    try:
        nf_entrada_service.vincular_nf_a_pedido(nf_id, pedido_id)
        flash('NF vinculada ao pedido.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))


# ------------------------------------------------------------------------
# Desvincular pedido da NF
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/desvincular-pedido', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_desvincular_pedido(nf_id: int):
    """Remove o vinculo NF -> Pedido. NF e itens permanecem intactos.

    O status do pedido ex-vinculado e recalculado automaticamente
    (pode cair de FATURADO -> PARCIALMENTE_FATURADO / ABERTO).
    """
    nf = HoraNfEntrada.query.get_or_404(nf_id)

    # Escopo da loja da NF
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    if not nf.loja_destino_id and lojas_permitidas_ids() is not None:
        flash(
            'NF sem loja atribuida; apenas usuario com escopo total pode desvincular.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    if not nf.pedido_id:
        flash('Esta NF nao esta vinculada a nenhum pedido.', 'warning')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    # Escopo do pedido atualmente vinculado (espelha bloqueio do nfs_remover):
    # desvincular muda o status do pedido, entao precisa de acesso a ele.
    pedido_vinc = HoraPedido.query.get(nf.pedido_id)
    if (
        pedido_vinc
        and pedido_vinc.loja_destino_id
        and not usuario_tem_acesso_a_loja(pedido_vinc.loja_destino_id)
    ):
        flash(
            'NF vinculada a pedido de loja fora do seu escopo — '
            'desvincular alteraria status do pedido. Operacao bloqueada.',
            'danger',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    try:
        res = nf_entrada_service.desvincular_nf_de_pedido(
            nf_id=nf.id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        numero_pedido = pedido_vinc.numero_pedido if pedido_vinc else f'#{res["pedido_id"]}'
        status_msg = f' (novo status: {res["status_pedido"]})' if res.get('status_pedido') else ''
        flash(
            f'NF desvinculada do pedido {numero_pedido}{status_msg}.',
            'success',
        )
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    except Exception as exc:  # pragma: no cover
        flash(f'Erro inesperado: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Modal de match NF x Pedido
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/match')
@require_hora_perm('nfs', 'ver')
def nfs_match(nf_id: int):
    """Modal/tela de vinculo NF -> Pedido com candidatos ordenados por match."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    # Se NF nao tem loja, nao da pra casar
    if not nf.loja_destino_id:
        flash(
            'NF ainda nao tem loja definida. Preencha a loja antes de vincular pedido.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    try:
        candidatos = matching_service.candidatos_pedidos_para_nf(nf.id)
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    # Auto-sugestao: primeiro com match > 0, senao o de maior pendente
    sugerido_id = None
    for s in candidatos:
        if s.match > 0:
            sugerido_id = s.pedido_id
            break
    if sugerido_id is None and candidatos:
        sugerido_id = candidatos[0].pedido_id

    return render_template(
        'hora/nf_match_modal.html',
        nf=nf,
        candidatos=[c.to_dict() for c in candidatos],
        sugerido_id=sugerido_id,
    )


@hora_bp.route('/nfs/<int:nf_id>/match/preview')
@require_hora_perm('nfs', 'ver')
def nfs_match_preview(nf_id: int):
    """JSON com itens NF + itens do pedido escolhido + totais (verde/vermelho)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    pedido_id_str = request.args.get('pedido_id') or ''
    if not pedido_id_str.isdigit():
        return jsonify({'ok': False, 'erro': 'pedido_id invalido'}), 400
    pedido_id = int(pedido_id_str)

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        return jsonify({'ok': False, 'erro': f'pedido {pedido_id} nao encontrado'}), 404
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado ao pedido'}), 403
    if nf.loja_destino_id and pedido.loja_destino_id and nf.loja_destino_id != pedido.loja_destino_id:
        return jsonify({'ok': False, 'erro': 'pedido de outra loja'}), 400

    try:
        data = matching_service.preview_match(nf.id, pedido.id)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400

    data['ok'] = True
    return jsonify(data)


@hora_bp.route('/nfs/<int:nf_id>/match/corrigir-pedido', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_match_corrigir_pedido(nf_id: int):
    """Copia chassi da NF para o item do pedido (preenche pendente ou substitui)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    try:
        pedido_id = int(request.form.get('pedido_id') or '')
        pedido_item_id = int(request.form.get('pedido_item_id') or '')
        nf_item_id = int(request.form.get('nf_item_id') or '')
    except ValueError:
        return jsonify({'ok': False, 'erro': 'parametros invalidos'}), 400

    try:
        res = matching_service.aplicar_correcao_pedido_item(
            nf_id=nf.id,
            pedido_id=pedido_id,
            pedido_item_id=pedido_item_id,
            nf_item_id=nf_item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        return jsonify(res)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400


@hora_bp.route('/nfs/<int:nf_id>/match/corrigir-nf', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_match_corrigir_nf(nf_id: int):
    """Copia chassi do pedido para o item da NF."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    try:
        pedido_id = int(request.form.get('pedido_id') or '')
        pedido_item_id = int(request.form.get('pedido_item_id') or '')
        nf_item_id = int(request.form.get('nf_item_id') or '')
    except ValueError:
        return jsonify({'ok': False, 'erro': 'parametros invalidos'}), 400

    try:
        res = matching_service.aplicar_correcao_nf_item(
            nf_id=nf.id,
            pedido_id=pedido_id,
            pedido_item_id=pedido_item_id,
            nf_item_id=nf_item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        return jsonify(res)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400


@hora_bp.route('/nfs/<int:nf_id>/match/confirmar', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_match_confirmar(nf_id: int):
    """Confirma vinculo final (depois de corrigir divergencias)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    pedido_id_str = (request.form.get('pedido_id') or '').strip()
    if not pedido_id_str.isdigit():
        flash('Selecione um pedido.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))

    pedido_id = int(pedido_id_str)
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        flash(f'Pedido {pedido_id} nao encontrado.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))
    if pedido.loja_destino_id != nf.loja_destino_id:
        flash('Pedido de outra loja.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))
    if not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado ao pedido selecionado.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))

    try:
        nf_entrada_service.vincular_nf_a_pedido(nf.id, pedido.id)
        flash(f'NF vinculada ao pedido {pedido.numero_pedido}.', 'success')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))


# ========================================================================
# Itens PECA em NF de entrada (XOR moto/peca aplicado em camada de UI)
# ========================================================================

@hora_bp.route('/nfs/<int:nf_id>/itens-peca/novo', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_adicionar_item_peca(nf_id: int):
    """Adiciona linha de peca em NF entrada (manual)."""
    from decimal import Decimal, InvalidOperation
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))

    try:
        peca_id_str = (request.form.get('peca_id') or '').strip()
        if not peca_id_str.isdigit():
            raise ValueError('Selecione uma peca')
        qtd_str = (request.form.get('qtd_nf') or '').strip().replace(',', '.')
        preco_str = (request.form.get('preco_real') or '').strip().replace(',', '.')
        if not qtd_str or not preco_str:
            raise ValueError('Quantidade e preco obrigatorios')
        nf_entrada_service.adicionar_item_peca_nf(
            nf_id=nf_id,
            peca_id=int(peca_id_str),
            qtd_nf=Decimal(qtd_str),
            preco_real=Decimal(preco_str),
            modelo_texto_original=(request.form.get('modelo_texto_original') or '') or None,
        )
        flash('Peca adicionada a NF.', 'success')
    except (ValueError, InvalidOperation) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))


@hora_bp.route('/nfs/<int:nf_id>/itens-peca/<int:item_id>/remover', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_remover_item_peca(nf_id: int, item_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    try:
        nf_entrada_service.remover_item_peca_nf(item_id)
        flash('Peca removida da NF.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))


@hora_bp.route('/nfs/<int:nf_id>/itens-peca/<int:item_id>/conferir', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def nfs_conferir_item_peca(nf_id: int, item_id: int):
    """Confere item peca + emite ENTRADA_NF no estoque."""
    from decimal import Decimal, InvalidOperation
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    try:
        qtd_conf = Decimal((request.form.get('qtd_conferida') or '0').replace(',', '.'))
        diverg = (request.form.get('divergencia_qtd') or 'OK').strip().upper()
        foto = request.files.get('foto')
        nf_entrada_service.conferir_item_peca_nf(
            nf_item_id=item_id,
            qtd_conferida=qtd_conf,
            divergencia_qtd=diverg,
            foto_file=foto,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(f'Peca conferida (status: {diverg}). Saldo atualizado.', 'success')
    except (ValueError, InvalidOperation) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
