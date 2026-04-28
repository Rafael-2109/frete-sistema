"""Rotas TagPlus: configuracao, OAuth, mapeamentos, webhook e operacoes NFe.

Detalhes: app/hora/EMISSAO_NFE_ENGENHARIA.md secoes 7 (OAuth), 10 (rotas).

Convencoes:
  - `tagplus.*` (admin/ops): protegido por `require_hora_perm('tagplus', acao)`.
  - `nfe/*` (acoes na venda): protegido por `require_hora_perm('vendas', acao)`.
  - `webhook` e callback OAuth: publicos (validacao por secret/state).
"""
from __future__ import annotations

import hmac
import logging
import secrets

from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import (
    HoraModelo,
    HoraVenda,
)
from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusFormaPagamentoMap,
    HoraTagPlusNfeEmissao,
    HoraTagPlusProdutoMap,
    NFE_STATUS_VALIDOS,
)
from app.hora.routes import hora_bp
from app.hora.services.tagplus.api_client import ApiClient
from app.hora.services.tagplus.cancelador_nfe import (
    CanceladorNfe,
    CancelamentoBloqueadoError,
)
from app.hora.services.tagplus.cce_service import CceError, CceService
from app.hora.services.tagplus.crypto import encrypt
from app.hora.services.tagplus.emissor_nfe import (
    EmissaoBloqueadaError,
    EmissorNfeHora,
)
from app.hora.services.tagplus.oauth_client import OAuthClient

logger = logging.getLogger(__name__)


def _operador() -> str:
    return getattr(current_user, 'nome', None) or 'desconhecido'


# ============================================================
# 1) Conta TagPlus — singleton (config + OAuth)
# ============================================================

@hora_bp.route('/tagplus/conta', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_conta():
    """Mostra conta ativa ou form para cadastrar a primeira."""
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    return render_template(
        'hora/tagplus/conta_form.html',
        conta=conta,
    )


@hora_bp.route('/tagplus/conta', methods=['POST'])
@require_hora_perm('tagplus', 'editar')
def tagplus_conta_salvar():
    """Cria/atualiza conta ativa. Encripta client_secret antes de persistir."""
    client_id = (request.form.get('client_id') or '').strip()
    client_secret = (request.form.get('client_secret') or '').strip()
    redirect_uri = (request.form.get('redirect_uri') or '').strip() or None
    ambiente = (request.form.get('ambiente') or 'producao').strip()
    scope = (request.form.get('scope_contratado') or
             'write:nfes read:clientes write:clientes read:produtos').strip()

    if not client_id:
        flash('client_id obrigatorio.', 'danger')
        return redirect(url_for('hora.tagplus_conta'))

    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        if not client_secret:
            flash('client_secret obrigatorio na primeira configuracao.', 'danger')
            return redirect(url_for('hora.tagplus_conta'))
        conta = HoraTagPlusConta(
            client_id=client_id,
            client_secret_encrypted=encrypt(client_secret),
            webhook_secret=secrets.token_urlsafe(32),
            ativo=True,
        )
        db.session.add(conta)
    else:
        conta.client_id = client_id
        if client_secret:
            conta.client_secret_encrypted = encrypt(client_secret)

    conta.redirect_uri = redirect_uri
    conta.ambiente = ambiente if ambiente in ('producao', 'homologacao') else 'producao'
    conta.scope_contratado = scope

    db.session.commit()
    flash('Conta TagPlus salva.', 'success')
    return redirect(url_for('hora.tagplus_conta'))


@hora_bp.route('/tagplus/conta/oauth')
@require_hora_perm('tagplus', 'editar')
def tagplus_oauth_iniciar():
    """Gera state CSRF e redireciona para developers.tagplus.com.br/authorize."""
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        flash('Cadastre a conta antes de iniciar OAuth.', 'danger')
        return redirect(url_for('hora.tagplus_conta'))

    state = secrets.token_urlsafe(32)
    conta.oauth_state_last = state
    db.session.commit()

    url = OAuthClient(conta).get_authorization_url(state=state)
    return redirect(url)


@hora_bp.route('/tagplus/conta/callback')
def tagplus_oauth_callback():
    """Callback do TagPlus apos autorizacao. NAO requer login (publico)
    porque o portal redireciona direto. Validacao por `state`.
    """
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or not state:
        return render_template(
            'hora/tagplus/oauth_result.html',
            ok=False, mensagem='Faltam parametros code/state.',
        ), 400

    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        return render_template(
            'hora/tagplus/oauth_result.html',
            ok=False, mensagem='Conta ativa nao encontrada.',
        ), 400

    if not conta.oauth_state_last or not hmac.compare_digest(state, conta.oauth_state_last):
        return render_template(
            'hora/tagplus/oauth_result.html',
            ok=False, mensagem='State invalido (possivel CSRF). Refaca o fluxo.',
        ), 400

    try:
        OAuthClient(conta).exchange_code(code)
    except Exception as exc:
        logger.exception('Falha exchange_code TagPlus: %s', exc)
        return render_template(
            'hora/tagplus/oauth_result.html',
            ok=False,
            mensagem='Falha na troca de tokens. Veja os logs do servidor para detalhes.',
        ), 500

    # Sucesso: consome state apenas apos exchange_code dar OK.
    conta.oauth_state_last = None
    db.session.commit()

    return render_template('hora/tagplus/oauth_result.html', ok=True, mensagem='Tokens obtidos com sucesso.')


@hora_bp.route('/tagplus/conta/refresh', methods=['POST'])
@require_hora_perm('tagplus', 'editar')
def tagplus_oauth_refresh():
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        flash('Conta nao configurada.', 'danger')
        return redirect(url_for('hora.tagplus_conta'))
    try:
        OAuthClient(conta)._do_refresh()  # noqa: SLF001
        flash('Token renovado.', 'success')
    except Exception as exc:
        flash(f'Falha ao renovar: {exc}', 'danger')
    return redirect(url_for('hora.tagplus_conta'))


@hora_bp.route('/tagplus/conta/checklist')
@require_hora_perm('tagplus', 'ver')
def tagplus_checklist():
    """Diagnostico de configuracao. Chama endpoints leves do TagPlus."""
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    checks: list[dict] = []
    api_ok = False

    if not conta:
        checks.append({'item': 'Conta TagPlus ativa', 'status': 'erro', 'mensagem': 'Nao configurada.'})
    else:
        checks.append({
            'item': 'Conta TagPlus ativa', 'status': 'ok',
            'mensagem': f'ambiente={conta.ambiente} scope={conta.scope_contratado}',
        })
        if not conta.token:
            checks.append({'item': 'Token OAuth', 'status': 'erro', 'mensagem': 'Faltando — refazer OAuth.'})
        else:
            checks.append({
                'item': 'Token OAuth', 'status': 'ok',
                'mensagem': f'expira em {conta.token.expires_at}',
            })
            try:
                client = ApiClient(conta)
                # Probe leve dentro do scope `read:produtos` — `/usuario_atual` nao existe
                # na API TagPlus (ver scripts/doc_tagplus.md). `?per_page=1` reduz payload.
                r = client.get('/produtos', params={'per_page': 1})
                if r.status_code == 200:
                    api_ok = True
                    body = r.json() if r.content else []
                    qtd = len(body) if isinstance(body, list) else 'n/a'
                    checks.append({
                        'item': 'GET /produtos (probe)', 'status': 'ok',
                        'mensagem': f'API OK (retornou {qtd} item).',
                    })
                else:
                    checks.append({
                        'item': 'GET /produtos (probe)', 'status': 'erro',
                        'mensagem': f'HTTP {r.status_code}: {r.text[:200]}',
                    })
            except Exception as exc:
                checks.append({'item': 'GET /produtos (probe)', 'status': 'erro', 'mensagem': str(exc)})

    # Mapeamentos.
    qtd_modelos = HoraModelo.query.filter_by(ativo=True).count()
    qtd_modelos_mapeados = HoraTagPlusProdutoMap.query.count()
    checks.append({
        'item': 'Mapeamento de produtos',
        'status': 'ok' if qtd_modelos_mapeados >= qtd_modelos and qtd_modelos > 0 else 'aviso',
        'mensagem': f'{qtd_modelos_mapeados}/{qtd_modelos} modelos mapeados.',
    })
    qtd_formas = HoraTagPlusFormaPagamentoMap.query.count()
    checks.append({
        'item': 'Mapeamento de formas de pagamento',
        'status': 'ok' if qtd_formas >= 3 else 'aviso',
        'mensagem': f'{qtd_formas} formas mapeadas (esperado: PIX, CARTAO_CREDITO, DINHEIRO).',
    })

    return render_template(
        'hora/tagplus/checklist.html',
        conta=conta, checks=checks, api_ok=api_ok,
    )


# ============================================================
# 2) Mapeamentos
# ============================================================

@hora_bp.route('/tagplus/conta/mapeamento', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_produto_map_lista():
    """Lista mapeamentos modelo HORA -> produto TagPlus."""
    modelos = HoraModelo.query.order_by(HoraModelo.nome_modelo).all()
    maps = {m.modelo_id: m for m in HoraTagPlusProdutoMap.query.all()}
    rows = [{'modelo': m, 'map': maps.get(m.id)} for m in modelos]
    return render_template('hora/tagplus/produto_map.html', rows=rows)


@hora_bp.route('/tagplus/conta/mapeamento', methods=['POST'])
@require_hora_perm('tagplus', 'editar')
def tagplus_produto_map_salvar():
    """Upsert dos mapeamentos a partir do form (1 linha por modelo)."""
    for modelo in HoraModelo.query.all():
        prefix = f'modelo_{modelo.id}_'
        tagplus_id = (request.form.get(prefix + 'tagplus_id') or '').strip()
        codigo = (request.form.get(prefix + 'codigo') or '').strip() or None
        cfop = (request.form.get(prefix + 'cfop') or '5.403').strip() or '5.403'

        existente = HoraTagPlusProdutoMap.query.filter_by(modelo_id=modelo.id).first()

        if not tagplus_id:
            # Limpa se vazio.
            if existente:
                db.session.delete(existente)
            continue

        if len(tagplus_id) > 50:
            flash(f'tagplus_id invalido para modelo {modelo.nome_modelo} (>50 chars): {tagplus_id}', 'danger')
            continue

        if existente:
            existente.tagplus_produto_id = tagplus_id
            existente.tagplus_codigo = codigo
            existente.cfop_default = cfop
        else:
            db.session.add(HoraTagPlusProdutoMap(
                modelo_id=modelo.id,
                tagplus_produto_id=tagplus_id,
                tagplus_codigo=codigo,
                cfop_default=cfop,
            ))

    db.session.commit()
    flash('Mapeamentos salvos.', 'success')
    return redirect(url_for('hora.tagplus_produto_map_lista'))


@hora_bp.route('/tagplus/conta/formas-pagamento', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_forma_map_lista():
    formas_hora = ('PIX', 'CARTAO_CREDITO', 'DINHEIRO')
    maps = {m.forma_pagamento_hora: m for m in HoraTagPlusFormaPagamentoMap.query.all()}
    rows = [{'forma': f, 'map': maps.get(f)} for f in formas_hora]
    return render_template('hora/tagplus/forma_pag_map.html', rows=rows)


@hora_bp.route('/tagplus/conta/formas-pagamento/listar', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_forma_map_listar_api():
    """Proxy que chama GET /formas_pagamento na API TagPlus.

    O portal TagPlus nao tem botao de exportar formas de pagamento; este
    endpoint puxa a lista via API para o operador copiar os IDs.
    """
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        return jsonify({'ok': False, 'error': 'Conta nao configurada.'}), 404
    if not conta.token:
        return jsonify({'ok': False, 'error': 'Sem token OAuth — autorizar em /hora/tagplus/conta.'}), 400

    client = ApiClient(conta)
    # Tenta endpoints possiveis. A doc nao explicita o path canonico
    # (scripts/doc_tagplus.md menciona forma_pagamento como ID inteiro mas
    # nao expoe o endpoint GET). Convencao TagPlus: recursos sempre no plural.
    candidatos = ['/formas_pagamento', '/formas_pgto', '/forma_pagamento']
    ultima_resposta = None
    for path in candidatos:
        r = client.get(path, params={'per_page': 100})
        ultima_resposta = (path, r.status_code, r.text[:300])
        if r.status_code == 200:
            try:
                body = r.json()
            except ValueError:
                body = []
            if isinstance(body, dict):
                body = body.get('data') or body.get('results') or body.get('formas_pagamento') or []
            return jsonify({
                'ok': True,
                'endpoint': path,
                'count': len(body) if isinstance(body, list) else 0,
                'formas': body,
            })

    return jsonify({
        'ok': False,
        'error': 'Endpoint de formas de pagamento nao encontrado.',
        'tentativas': candidatos,
        'ultima_resposta': {
            'endpoint': ultima_resposta[0] if ultima_resposta else None,
            'http_status': ultima_resposta[1] if ultima_resposta else None,
            'body': ultima_resposta[2] if ultima_resposta else None,
        },
        'fallback': (
            'Como fallback: emitir uma NFe de teste no portal TagPlus com cada forma '
            '(PIX, CARTAO_CREDITO, DINHEIRO) e depois consultar GET /nfes/{id} — o campo '
            'faturas[].id_forma_pagamento traz o ID inteiro a usar.'
        ),
    }), 502


@hora_bp.route('/tagplus/conta/formas-pagamento', methods=['POST'])
@require_hora_perm('tagplus', 'editar')
def tagplus_forma_map_salvar():
    formas_hora = ('PIX', 'CARTAO_CREDITO', 'DINHEIRO')
    for forma in formas_hora:
        tagplus_id = (request.form.get(f'{forma}_tagplus_id') or '').strip()
        descricao = (request.form.get(f'{forma}_descricao') or '').strip() or None

        existente = HoraTagPlusFormaPagamentoMap.query.filter_by(forma_pagamento_hora=forma).first()

        if not tagplus_id:
            if existente:
                db.session.delete(existente)
            continue

        try:
            tagplus_id_int = int(tagplus_id)
        except ValueError:
            flash(f'tagplus_id invalido para {forma}: {tagplus_id}', 'danger')
            continue

        if existente:
            existente.tagplus_forma_id = tagplus_id_int
            existente.descricao = descricao
        else:
            db.session.add(HoraTagPlusFormaPagamentoMap(
                forma_pagamento_hora=forma,
                tagplus_forma_id=tagplus_id_int,
                descricao=descricao,
            ))
    db.session.commit()
    flash('Mapeamentos de forma de pagamento salvos.', 'success')
    return redirect(url_for('hora.tagplus_forma_map_lista'))


# ============================================================
# 3) Webhook publico
# ============================================================

@hora_bp.route('/tagplus/webhook', methods=['POST'])
def tagplus_webhook():
    """Receiver publico. Valida X-Hub-Secret e enfileira processamento.

    Responde 200 rapido para nao causar timeout/retry no TagPlus. O processamento
    real (GET /nfes/{id} + atualizar HoraVenda + emitir HoraMotoEvento) roda no
    worker RQ.
    """
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        return jsonify({'ok': False, 'error': 'sem conta ativa'}), 503

    secret_recebido = request.headers.get('X-Hub-Secret', '')
    if not conta.webhook_secret or not hmac.compare_digest(
        secret_recebido, conta.webhook_secret,
    ):
        logger.warning('Webhook TagPlus com secret invalido (origem=%s)', request.remote_addr)
        return jsonify({'ok': False, 'error': 'secret invalido'}), 401

    try:
        body = request.get_json(force=True, silent=True) or {}
    except Exception:
        body = {}

    event_type = body.get('event_type')
    data = body.get('data', [])
    if not event_type or not isinstance(data, list):
        return jsonify({'ok': False, 'error': 'body invalido'}), 400

    # Enfileira processamento (rapido, libera o TagPlus).
    try:
        from rq import Queue
        from redis import Redis
        import os
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            redis_conn = Redis.from_url(redis_url)
            queue = Queue(EmissorNfeHora.QUEUE_NAME, connection=redis_conn)
            queue.enqueue(
                'app.hora.workers.emissao_nfe_worker.processar_webhook',
                conta.id, event_type, data,
            )
        else:
            # Fallback sincrono (dev sem Redis).
            from app.hora.services.tagplus.webhook_handler import WebhookHandler
            WebhookHandler.processar(conta.id, event_type, data)
    except Exception as exc:
        logger.exception('Falha enfileirando webhook: %s', exc)
        # Mesmo assim respondemos 200 — reconciliacao recupera depois.

    return jsonify({'ok': True}), 200


# ============================================================
# 4) Fila de emissoes (gestao)
# ============================================================

@hora_bp.route('/tagplus/emissoes')
@require_hora_perm('tagplus', 'ver')
def tagplus_emissoes_lista():
    status_filtro = (request.args.get('status') or '').strip().upper() or None
    if status_filtro and status_filtro not in NFE_STATUS_VALIDOS:
        status_filtro = None

    q = HoraTagPlusNfeEmissao.query.order_by(HoraTagPlusNfeEmissao.criado_em.desc())
    if status_filtro:
        q = q.filter_by(status=status_filtro)
    emissoes = q.limit(300).all()
    return render_template(
        'hora/tagplus/emissoes_lista.html',
        emissoes=emissoes,
        status_filtro=status_filtro,
        status_validos=NFE_STATUS_VALIDOS,
    )


# ============================================================
# 5) Acoes na venda (NFe)
# ============================================================

@hora_bp.route('/vendas/<int:venda_id>/nfe')
@require_hora_perm('vendas', 'ver')
def venda_nfe_status(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
    return render_template(
        'hora/tagplus/nfe_status.html',
        venda=venda, emissao=emissao,
    )


@hora_bp.route('/vendas/<int:venda_id>/nfe/emitir', methods=['POST'])
@require_hora_perm('vendas', 'criar')
def venda_nfe_emitir(venda_id: int):
    try:
        emissao_id = EmissorNfeHora.enfileirar(venda_id)
        flash(f'Emissao enfileirada (id={emissao_id}). Acompanhe o status.', 'success')
    except EmissaoBloqueadaError as exc:
        flash(f'Emissao bloqueada: {exc}', 'warning')
    except RuntimeError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))


@hora_bp.route('/vendas/<int:venda_id>/nfe/cancelar', methods=['POST'])
@require_hora_perm('vendas', 'apagar')
def venda_nfe_cancelar(venda_id: int):
    justificativa = (request.form.get('justificativa') or '').strip()
    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
    if not emissao:
        flash('Sem emissao para esta venda.', 'warning')
        return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))
    try:
        CanceladorNfe.cancelar(emissao.id, justificativa, _operador())
        flash('Cancelamento solicitado. Aguardando confirmacao SEFAZ.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    except CancelamentoBloqueadoError as exc:
        flash(f'Bloqueado: {exc}', 'warning')
    except Exception as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))


@hora_bp.route('/vendas/<int:venda_id>/nfe/cce', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def venda_nfe_cce(venda_id: int):
    texto = (request.form.get('texto_correcao') or '').strip()
    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
    if not emissao:
        flash('Sem emissao para esta venda.', 'warning')
        return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))
    try:
        CceService.gerar(emissao.id, texto)
        flash('CC-e emitida.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    except CceError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))


# ============================================================
# 6) Proxy DANFE / XML
# ============================================================

@hora_bp.route('/vendas/<int:venda_id>/nfe/danfe.pdf')
@require_hora_perm('vendas', 'ver')
def venda_nfe_danfe_pdf(venda_id: int):
    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
    if not emissao or not emissao.tagplus_nfe_id:
        abort(404)
    client = ApiClient(emissao.conta)
    r = client.get(f'/nfes/pdf/recibo_a4/{emissao.tagplus_nfe_id}')
    if r.status_code != 200:
        return jsonify({
            'ok': False, 'http_status': r.status_code,
            'detalhe': r.text[:500],
        }), 502
    filename = f'danfe_{emissao.numero_nfe or emissao.tagplus_nfe_id}.pdf'
    return Response(
        r.content,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'inline; filename="{filename}"'},
    )


@hora_bp.route('/vendas/<int:venda_id>/nfe/xml')
@require_hora_perm('vendas', 'ver')
def venda_nfe_xml(venda_id: int):
    """Proxy do XML — primeiro tenta gerar_link_xml, senao baixa direto."""
    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
    if not emissao or not emissao.tagplus_nfe_id:
        abort(404)
    client = ApiClient(emissao.conta)

    # Tenta endpoint que retorna URL temporaria.
    r_link = client.get(f'/nfes/gerar_link_xml/{emissao.tagplus_nfe_id}')
    if r_link.status_code == 200:
        try:
            body = r_link.json()
            url = body.get('url') if isinstance(body, dict) else None
            if url:
                return redirect(url)
        except ValueError:
            pass

    # Fallback: tenta baixar XML direto.
    r = client.get(f'/nfes/xml/{emissao.tagplus_nfe_id}')
    if r.status_code != 200:
        return jsonify({
            'ok': False, 'http_status': r.status_code,
            'detalhe': r.text[:500],
        }), 502

    filename = f'nfe_{emissao.numero_nfe or emissao.tagplus_nfe_id}.xml'
    return Response(
        r.content,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
