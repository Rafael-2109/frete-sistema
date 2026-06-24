import gc
import re

from flask import (
    render_template, redirect, url_for, flash, Response,
    current_app, request, jsonify, abort,
)
from flask_login import login_required, current_user
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import gerar_excel_qpa
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    AssaiNfQpa, AssaiNfQpaItem,
    AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiLoja,
    AssaiCce,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
)
from app.utils.file_storage import FileStorage
from app.motos_assai.forms import UploadNfQpaForm
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    importar_nf_qpa, NfQpaParseError, NfQpaJaImportadaError,
    NfQpaDocumentoCceError,
    vincular_nf_manualmente, VincularNfError,
)
from app.motos_assai.services.cancelamento_nf_service import (
    cancelar_nf_qpa, CancelamentoValidationError,
)
from app.motos_assai.services.modelo_service import listar_modelos
from app.motos_assai.routes._filtro_helpers import coletar_chassi_modelo


@motos_assai_bp.route('/faturamento')
@login_required
@require_motos_assai
def faturamento_lista():
    """Lista de SEPARACOES fechadas/faturadas + NFs Q.P.A. (vinculadas E orfas).

    Atualizado 2026-05-18 (Rafael):
      - Separa em 2 secoes: PRONTAS PARA FATURAR (FECHADA, sem NF ativa) e
        FATURADAS (FATURADA com NF BATEU). A mistura antiga confundia operador.
      - NFs orfas (sem BATEU ou sem separacao) permanece como 3a secao.
    """
    # Filtro chassi/modelo (2026-05-20): aplicado as separacoes (via
    # AssaiSeparacaoItem) e as NFs orfas (via AssaiNfQpaItem / AssaiMoto).
    filtros = coletar_chassi_modelo()
    f_chassi = filtros.get('chassi')
    f_modelo_id = filtros.get('modelo_id')
    tem_filtro = bool(f_chassi or f_modelo_id)

    # === Separacoes FECHADA/FATURADA com NF vinculada via outerjoin ===
    sep_q = (
        db.session.query(AssaiSeparacao, AssaiNfQpa)
        .outerjoin(AssaiNfQpa, AssaiNfQpa.separacao_id == AssaiSeparacao.id)
        .filter(AssaiSeparacao.status.in_([SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA]))
    )
    if tem_filtro:
        sep_sub = db.session.query(AssaiSeparacaoItem.separacao_id)
        if f_chassi:
            sep_sub = sep_sub.filter(
                AssaiSeparacaoItem.chassi.ilike(f'%{f_chassi.upper()}%')
            )
        if f_modelo_id:
            sep_sub = sep_sub.filter(AssaiSeparacaoItem.modelo_id == f_modelo_id)
        sep_q = sep_q.filter(AssaiSeparacao.id.in_(sep_sub))
    sep_rows = (
        sep_q
        .order_by(AssaiSeparacao.fechada_em.desc().nullslast(),
                  AssaiSeparacao.iniciada_em.desc())
        .limit(250)
        .all()
    )

    # Itens de TODAS as separacoes em batch (evita N+1 ao montar accordion)
    sep_ids = [s.id for s, _nf in sep_rows]
    items_por_sep: dict = {}
    if sep_ids:
        items_rows = (
            db.session.query(AssaiSeparacaoItem, AssaiMoto, AssaiModelo)
            .join(AssaiMoto, AssaiMoto.chassi == AssaiSeparacaoItem.chassi)
            .join(AssaiModelo, AssaiModelo.id == AssaiSeparacaoItem.modelo_id)
            .filter(AssaiSeparacaoItem.separacao_id.in_(sep_ids))
            .order_by(AssaiSeparacaoItem.separacao_id, AssaiSeparacaoItem.id)
            .all()
        )
        for item, moto, modelo in items_rows:
            items_por_sep.setdefault(item.separacao_id, []).append({
                'chassi': item.chassi,
                'modelo_codigo': modelo.codigo,
                'modelo_nome': modelo.nome,
                'cor': moto.cor or '-',
                'valor_unitario': float(item.valor_unitario_qpa or 0),
            })

    # === CCes vinculadas em batch (cobre separacoes COM NF + NFs orfas) ===
    # Coleta TODOS os nf_ids que aparecem na tela (separacoes com NF + NFs orfas
    # que ainda nao foram carregadas — populadas abaixo).
    sep_nf_ids = [nf.id for _sep, nf in sep_rows if nf is not None]

    # === NFs orfas: status_match != BATEU OU separacao_id NULL ===
    nf_orfa_q = (
        AssaiNfQpa.query
        .filter(
            db.or_(
                AssaiNfQpa.separacao_id.is_(None),
                AssaiNfQpa.status_match != NF_STATUS_BATEU,
            )
        )
    )
    if tem_filtro:
        nf_sub = db.session.query(AssaiNfQpaItem.nf_id)
        if f_chassi:
            nf_sub = nf_sub.filter(
                AssaiNfQpaItem.chassi.ilike(f'%{f_chassi.upper()}%')
            )
        if f_modelo_id:
            # NfQpaItem nao tem modelo_id (so modelo_extraido texto). Resolve o
            # modelo via AssaiMoto: chassis cadastrados com o modelo informado.
            chassis_do_modelo = (
                db.session.query(AssaiMoto.chassi)
                .filter(AssaiMoto.modelo_id == f_modelo_id)
            )
            nf_sub = nf_sub.filter(AssaiNfQpaItem.chassi.in_(chassis_do_modelo))
        nf_orfa_q = nf_orfa_q.filter(AssaiNfQpa.id.in_(nf_sub))
    nfs_orfas_rows = (
        nf_orfa_q
        .order_by(AssaiNfQpa.importada_em.desc())
        .limit(250)
        .all()
    )

    # Batch CCe (1 query cobre separacoes + orfas)
    todos_nf_ids = sep_nf_ids + [n.id for n in nfs_orfas_rows]
    cces_por_nf: dict = {}
    if todos_nf_ids:
        cces_rows = (
            AssaiCce.query
            .filter(AssaiCce.nf_id.in_(todos_nf_ids))
            .order_by(AssaiCce.nf_id, AssaiCce.sequencia_cce)
            .all()
        )
        for c in cces_rows:
            cces_por_nf.setdefault(c.nf_id, []).append({
                'id': c.id,
                'protocolo': c.protocolo_cce,
                'sequencia': c.sequencia_cce,
                'tipo': c.tipo_correcao,
                'status': c.status,
            })

    # Fallback CNPJ → AssaiLoja: pre-carrega para NFs orfas sem loja_id.
    # Evita exibir UF/cidade "-" quando o regex LJ\d+ falhou mas existe AssaiLoja
    # com o mesmo CNPJ destinatario.
    cnpjs_sem_loja = list({
        re.sub(r'\D', '', nf.destinatario_cnpj or '')
        for nf in nfs_orfas_rows
        if not nf.loja_id and nf.destinatario_cnpj
    })
    loja_por_cnpj: dict = {}
    if cnpjs_sem_loja:
        lojas_fallback = (
            AssaiLoja.query
            .filter(AssaiLoja.cnpj.in_(cnpjs_sem_loja))
            .all()
        )
        loja_por_cnpj = {
            re.sub(r'\D', '', loja.cnpj): loja for loja in lojas_fallback
        }

    def _loja_efetiva(nf_obj):
        """Loja resolvida diretamente OU via fallback CNPJ."""
        if nf_obj.loja_id and nf_obj.loja:
            return nf_obj.loja
        cnpj_clean = re.sub(r'\D', '', nf_obj.destinatario_cnpj or '')
        return loja_por_cnpj.get(cnpj_clean)

    # Particionar: prontas (FECHADA sem NF ativa) vs faturadas (FATURADA + NF)
    separacoes_prontas = []
    separacoes_faturadas = []
    for sep, nf in sep_rows:
        loja = sep.loja
        row = {
            'sep': sep,
            'nf': nf,
            'loja': loja,
            'loja_uf': (loja.uf if loja else '') or '-',
            'loja_cidade': (loja.cidade if loja else '') or '-',
            'pedido_numero': sep.pedido.numero if sep.pedido else '-',
            'items': items_por_sep.get(sep.id, []),
            'qtd_items': len(items_por_sep.get(sep.id, [])),
            'cces': cces_por_nf.get(nf.id, []) if nf else [],
        }
        if sep.status == SEPARACAO_STATUS_FATURADA and nf is not None:
            separacoes_faturadas.append(row)
        else:
            # FECHADA, ou FATURADA sem NF (edge raro). Vai para "prontas".
            separacoes_prontas.append(row)

    # Items das NFs orfas em batch
    nf_orfa_ids = [n.id for n in nfs_orfas_rows]
    items_por_nf: dict = {}
    if nf_orfa_ids:
        nf_items = (
            AssaiNfQpaItem.query
            .filter(AssaiNfQpaItem.nf_id.in_(nf_orfa_ids))
            .order_by(AssaiNfQpaItem.nf_id, AssaiNfQpaItem.id)
            .all()
        )
        for it in nf_items:
            items_por_nf.setdefault(it.nf_id, []).append({
                'chassi': it.chassi,
                'modelo_extraido': it.modelo_extraido or '-',
                'valor_extraido': float(it.valor_extraido or 0),
                'tipo_divergencia': it.tipo_divergencia,
            })

    nfs_orfas = []
    for nf in nfs_orfas_rows:
        # Loja resolvida via fallback CNPJ (display). O CNPJ destinatario da NF
        # eh a chave de match — o modal vincular usa nf.destinatario_cnpj direto.
        loja_eff = _loja_efetiva(nf)
        nfs_orfas.append({
            'nf': nf,
            'loja': loja_eff,
            'loja_uf': (loja_eff.uf if loja_eff else '') or '-',
            'loja_cidade': (loja_eff.cidade if loja_eff else '') or '-',
            # Loja SEM razao social — apenas "numero nome".
            # Quando NF nao tem loja resolvida nem via fallback CNPJ, mostra
            # marcador discreto (NAO mostra razao social do destinatario_nome).
            'loja_label': (
                f'{loja_eff.numero} {loja_eff.nome}' if loja_eff
                else '— sem loja identificada —'
            ),
            'items': items_por_nf.get(nf.id, []),
            'qtd_items': len(items_por_nf.get(nf.id, [])),
            'cces': cces_por_nf.get(nf.id, []),
        })

    return render_template(
        'motos_assai/faturamento/lista_separacoes.html',
        separacoes_prontas=separacoes_prontas,
        separacoes_faturadas=separacoes_faturadas,
        nfs_orfas=nfs_orfas,
        # Mantido para retrocompatibilidade caso outro lugar leia `separacoes`
        separacoes=separacoes_prontas + separacoes_faturadas,
        filtros_aplicados=filtros,
        modelos=listar_modelos(somente_ativos=True),
    )


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>/pdf')
@login_required
@require_motos_assai
def faturamento_nf_pdf(nf_id):
    """Redireciona para presigned URL S3 (ou serve local) do PDF original da NF Q.P.A.

    Bloqueia se a NF nao tem `pdf_s3_key` (NF importada antes do campo existir
    ou upload S3 falhou na importacao).
    """
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    if not nf.pdf_s3_key:
        flash(
            f'NF {nf.numero or nf.id} nao tem PDF armazenado '
            '(importada antes do campo existir ou upload S3 falhou).',
            'warning',
        )
        return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf_id))

    storage = FileStorage()
    if not storage.file_exists(nf.pdf_s3_key):
        current_app.logger.warning(
            'pdf_s3_key sumiu do storage: %s (nf %s)', nf.pdf_s3_key, nf_id,
        )
        flash('Arquivo PDF nao encontrado no storage.', 'danger')
        return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf_id))

    # S3 presigned (visualizacao inline)
    if storage.use_s3 and not nf.pdf_s3_key.startswith('uploads/'):
        url = storage.get_presigned_url(nf.pdf_s3_key, expires_in=300)
        if not url:
            abort(500)
        return redirect(url)

    # Local
    url = storage.get_file_url(nf.pdf_s3_key)
    if not url:
        abort(500)
    return redirect(url)


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/excel')
@login_required
@require_motos_assai
def faturamento_solicitacao_excel(separacao_id):
    try:
        bytes_xlsx, s3_key = gerar_excel_qpa(separacao_id, current_user.id)
    except ValueError as e:
        # H3: separação em status inválido para geração de Excel
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.faturamento_lista'))
    # H1: s3_key pode ser None se FileStorage falhar — log mas não bloquear download
    if not s3_key:
        current_app.logger.error('S3 save falhou para separacao %s', separacao_id)
    return Response(
        bytes_xlsx,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="solicitacao_qpa_{separacao_id}.xlsx"',
        },
    )


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/upload-nf', methods=['GET', 'POST'])
@motos_assai_bp.route('/faturamento/upload-nf', methods=['GET', 'POST'], defaults={'separacao_id': None})
@login_required
@require_motos_assai
def faturamento_upload_nf(separacao_id):
    """Upload de 1 ou N PDFs de NF Q.P.A.

    - 1 PDF + sucesso → redirect para detalhe (UX antiga preservada).
    - 1 PDF + erro/duplicada → flash + render upload novamente.
    - N PDFs (qualquer combinação de sucesso/erro) → render relatório batch.
    """
    form = UploadNfQpaForm()
    if form.validate_on_submit():
        arquivos = form.pdfs.data or []
        # MultipleFileField pode entregar lista com 1 FileStorage vazio em alguns edge cases
        arquivos = [f for f in arquivos if f and getattr(f, 'filename', '')]
        resultados = []  # cada item: dict(filename, status, nf, erro)
        for f in arquivos:
            try:
                nf = importar_nf_qpa(
                    pdf_bytes=f.read(),
                    nome_arquivo=f.filename,
                    importada_por_id=current_user.id,
                )
                resultados.append({
                    'filename': f.filename,
                    'status': 'ok',
                    'status_match': nf.status_match,
                    'nf_id': nf.id,
                    'nf_numero': nf.numero,
                    'erro': None,
                })
            except NfQpaJaImportadaError as e:
                resultados.append({
                    'filename': f.filename,
                    'status': 'duplicada',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': str(e),
                })
            except NfQpaDocumentoCceError as e:
                # PDF de CCe enviado ao endpoint de NF (IMP-2026-06-23-008):
                # NAO cria NF orfa — orienta a usar a tela de CCe.
                resultados.append({
                    'filename': f.filename,
                    'status': 'documento_errado',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': str(e),
                })
            except NfQpaParseError as e:
                resultados.append({
                    'filename': f.filename,
                    'status': 'erro_parse',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': str(e),
                })
            except Exception as e:
                # Qualquer outra excecao (IntegrityError, decimal, anthropic,
                # AttributeError, OperationalError...): NAO aborta o lote.
                # Limpa a sessao (evita contaminar o proximo arquivo) e
                # registra como 'falha' VISIVEL no relatorio — em vez de o
                # arquivo sumir sem rastro (importar_nf_qpa commita por
                # arquivo, entao os ja processados ficam e os demais somem).
                db.session.rollback()
                current_app.logger.exception(
                    'Falha inesperada ao importar NF Q.P.A. (arquivo %s)',
                    f.filename,
                )
                resultados.append({
                    'filename': f.filename,
                    'status': 'falha',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': f'{type(e).__name__}: {e}',
                })
            finally:
                # Libera memoria entre arquivos do lote (IMP-2026-06-23-002):
                # sem isto o pico era a SOMA de varios PDFs+respostas LLM em voo.
                try:
                    f.close()
                except Exception:
                    pass
                gc.collect()

        # 1 arquivo + sucesso → preserva UX antiga
        if len(resultados) == 1 and resultados[0]['status'] == 'ok':
            r = resultados[0]
            flash(f'NF {r["nf_numero"]} importada — status: {r["status_match"]}', 'success')
            return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=r['nf_id']))

        # 1 arquivo + erro → flash e re-render upload
        if len(resultados) == 1 and resultados[0]['status'] != 'ok':
            r = resultados[0]
            categoria = 'warning' if r['status'] == 'duplicada' else 'danger'
            prefix = 'Erro ao parsear NF: ' if r['status'] == 'erro_parse' else ''
            flash(f'{prefix}{r["erro"]}', categoria)
            return render_template('motos_assai/faturamento/upload_nf.html', form=form, separacao_id=separacao_id)

        # N arquivos → relatório batch
        resumo = {
            'total': len(resultados),
            'ok': sum(1 for r in resultados if r['status'] == 'ok'),
            'duplicada': sum(1 for r in resultados if r['status'] == 'duplicada'),
            'erro_parse': sum(1 for r in resultados if r['status'] == 'erro_parse'),
            'falha': sum(1 for r in resultados if r['status'] == 'falha'),
            'documento_errado': sum(1 for r in resultados if r['status'] == 'documento_errado'),
        }
        return render_template(
            'motos_assai/faturamento/upload_nf_resultado.html',
            resultados=resultados, resumo=resumo, separacao_id=separacao_id,
        )

    return render_template('motos_assai/faturamento/upload_nf.html', form=form, separacao_id=separacao_id)


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>')
@login_required
@require_motos_assai
def faturamento_nf_detalhe(nf_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    items = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).all()

    # GAP-1 fix (Plano Fase 4 S7=a): detectar sep criada via NF para auto-abrir
    # Modal Expedição. Heuristica: AssaiPedidoExcel da sep com versao=1 e
    # motivo_regeneracao='criada_via_nf_importada' (gravado em separacao_service
    # quando ajustar_separacao_pela_nf cria sep em FATURADA — linha 1481).
    sep_criada_via_nf = False
    if nf.separacao_id:
        from app.motos_assai.models import AssaiPedidoExcel
        excel_v1 = (
            AssaiPedidoExcel.query
            .filter_by(separacao_id=nf.separacao_id, versao=1)
            .first()
        )
        sep_criada_via_nf = bool(
            excel_v1 and excel_v1.motivo_regeneracao == 'criada_via_nf_importada'
        )

    # Migration 29: devolucoes vinculadas a esta NF (NFds).
    from app.motos_assai.services import listar_devolucoes_da_nf, itens_da_nf_para_tela
    from app.motos_assai.forms import DevolucaoNfForm
    devolucoes_da_nf = listar_devolucoes_da_nf(nf_id)
    # Form + itens carregados para popular o modal de devolucao embutido na propria tela.
    # Modal so e renderizado se nf.status_match != 'CANCELADA' (template controla).
    form_devolucao = DevolucaoNfForm() if nf.status_match != 'CANCELADA' else None
    itens_devolucao = (
        itens_da_nf_para_tela(nf_id) if nf.status_match != 'CANCELADA' else []
    )

    return render_template(
        'motos_assai/faturamento/nf_detalhe.html',
        nf=nf, items=items,
        sep_criada_via_nf=sep_criada_via_nf,
        devolucoes_da_nf=devolucoes_da_nf,
        form_devolucao=form_devolucao,
        itens_devolucao=itens_devolucao,
    )


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>/cancelar', methods=['POST'])
def faturamento_cancelar_nf(nf_id):
    """AJAX cancelar NF Q.P.A. (Plano 3 Task 23).

    N-B1: SEM decorators de tela. Valida sessao manualmente.

    Body JSON:
        { "motivo": "texto >= 3 chars" }

    Returns:
        200 {ok: true, nf_id: N, status_match: "CANCELADA"}
        400 {ok: false, erro: "..."}
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    motivo = (payload.get('motivo') or '').strip()
    try:
        nf = cancelar_nf_qpa(nf_id, motivo=motivo, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'nf_id': nf.id, 'status_match': nf.status_match})
    except CancelamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao cancelar NF %s', nf_id)
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500


@motos_assai_bp.route('/faturamento/sep/<int:sep_id>/expedicao', methods=['POST'])
def faturamento_definir_expedicao(sep_id):
    """AJAX setar expedicao + agendamento + protocolo em sep recem-criada (S7=a).

    Modal Expedicao - Plano 3 Task 12.
    N-B1: SEM decorators de tela. Valida sessao manualmente.

    Body JSON:
        {
            "expedicao": "YYYY-MM-DD",          // obrigatorio
            "agendamento": "YYYY-MM-DD" | null,  // opcional
            "protocolo": "..." | null,           // opcional
            "agendamento_confirmado": bool       // opcional
        }
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    sep = AssaiSeparacao.query.get_or_404(sep_id)

    payload = request.get_json(silent=True) or {}
    expedicao_s = (payload.get('expedicao') or '').strip()
    agendamento_s = (payload.get('agendamento') or '').strip()
    protocolo = (payload.get('protocolo') or '').strip() or None
    confirmado = bool(payload.get('agendamento_confirmado', False))

    from datetime import datetime
    try:
        if not expedicao_s:
            return jsonify({'ok': False, 'erro': 'Expedicao obrigatoria'}), 400
        sep.expedicao = datetime.strptime(expedicao_s, '%Y-%m-%d').date()
        if agendamento_s:
            sep.agendamento = datetime.strptime(agendamento_s, '%Y-%m-%d').date()
        if protocolo:
            sep.protocolo = protocolo
        sep.agendamento_confirmado = confirmado

        # Propagar para espelho Nacom (best-effort)
        try:
            from app.motos_assai.services.separacao_mirror_service import (
                propagar_4_campos_para_espelho,
            )
            propagar_4_campos_para_espelho(sep.id)
        except Exception as e:
            current_app.logger.warning(
                'propagar_4_campos_para_espelho falhou para sep %s: %s', sep_id, e,
            )

        db.session.commit()
        return jsonify({'ok': True, 'sep_id': sep.id})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': f'Data invalida: {e}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao setar expedicao sep %s', sep_id)
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>/vincular-manual', methods=['POST'])
def faturamento_vincular_nf_manual_ajax(nf_id):
    """AJAX: vincular NF NAO_RECONCILIADO manualmente a um pedido.

    Regra (2026-05-14): match por **CNPJ destinatario** da NF — chave
    deterministica entre NF (`destinatario_cnpj`) e Pedido (via `AssaiLoja.cnpj`
    da `AssaiPedidoVendaLoja`). O frontend envia apenas `pedido_id`; o backend
    deriva tudo a partir de `nf.destinatario_cnpj`.

    Body JSON:
        {pedido_id: int}

    N-B1 fix: sem decorator de tela; valida sessao manualmente.
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    try:
        pedido_id = int(payload['pedido_id'])
    except (KeyError, TypeError, ValueError):
        return jsonify({
            'ok': False, 'erro': 'pedido_id obrigatorio',
        }), 400

    try:
        resultado = vincular_nf_manualmente(
            nf_id, pedido_id, operador_id=current_user.id,
        )
        db.session.commit()
        return jsonify({
            'ok': resultado.get('ok', False),
            'sep_alvo_id': resultado.get('sep_alvo_id'),
            'sep_criada_via_nf': resultado.get('sep_criada_via_nf', False),
            'razao': resultado.get('razao', ''),
            'chassis_adicionados': resultado.get('chassis_adicionados', []),
            'chassis_removidos': resultado.get('chassis_removidos', []),
            'chassis_desconhecidos': resultado.get('chassis_desconhecidos', []),
        })
    except VincularNfError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao vincular NF %s manualmente', nf_id)
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500


@motos_assai_bp.route('/faturamento/api/pedidos-por-cnpj/<string:cnpj>')
@login_required
@require_motos_assai
def faturamento_pedidos_por_cnpj_ajax(cnpj):
    """AJAX: lista pedidos ABERTO/PARCIALMENTE_FATURADO cuja loja (via
    `AssaiPedidoVendaLoja`) tenha o mesmo CNPJ informado.

    CNPJ e a chave deterministica de match NF <-> Pedido — a NF traz
    `destinatario_cnpj`, o pedido traz CNPJ via cabecalho da loja.

    Consumido pelo modal "Vincular NF manualmente" — quando o operador abre
    o modal, JS chama este endpoint passando `nf.destinatario_cnpj` (sanitizado
    em ambos os lados via re.sub(r'\\D', '', ...)).

    Retorna tambem a loja resolvida (numero + nome) para o modal exibir.
    """
    cnpj_normalizado = re.sub(r'\D', '', cnpj or '')
    if not cnpj_normalizado:
        return jsonify({
            'ok': False, 'erro': 'CNPJ vazio ou invalido',
        }), 400

    # Normaliza in-memory — a tabela AssaiLoja eh pequena (cadastros Sendas/Assai)
    todas_lojas = AssaiLoja.query.all()
    lojas_match = [
        ll for ll in todas_lojas
        if re.sub(r'\D', '', ll.cnpj or '') == cnpj_normalizado
    ]
    # Code review #3: AssaiLoja.cnpj sem UNIQUE — se houver duplicacao,
    # retorna erro explicito em vez de escolher silenciosamente.
    if len(lojas_match) > 1:
        return jsonify({
            'ok': False,
            'erro': f'CNPJ {cnpj} ambiguo: {len(lojas_match)} lojas cadastradas '
                    f'com esse CNPJ (ids: {[ll.id for ll in lojas_match]}). '
                    'Corrija o cadastro em /motos-assai/lojas.',
        }), 409
    loja = lojas_match[0] if lojas_match else None
    if not loja:
        return jsonify({
            'ok': False,
            'erro': f'Nenhuma loja cadastrada com CNPJ {cnpj}. '
                    'Cadastre em /motos-assai/lojas antes de vincular.',
        }), 404

    pedidos = (
        db.session.query(AssaiPedidoVenda)
        .join(
            AssaiPedidoVendaLoja,
            AssaiPedidoVendaLoja.pedido_id == AssaiPedidoVenda.id,
        )
        .filter(
            AssaiPedidoVendaLoja.loja_id == loja.id,
            AssaiPedidoVenda.status.in_([
                PEDIDO_STATUS_ABERTO,
                PEDIDO_STATUS_PARCIALMENTE_FATURADO,
            ]),
        )
        .order_by(AssaiPedidoVenda.numero)
        .all()
    )
    return jsonify({
        'ok': True,
        'cnpj': cnpj_normalizado,
        'loja': {
            'id': loja.id, 'numero': loja.numero, 'nome': loja.nome,
            'cnpj': loja.cnpj,
        },
        'pedidos': [
            {'id': p.id, 'numero': p.numero, 'status': p.status}
            for p in pedidos
        ],
    })
