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
from app.hora.services.auth_helper import lojas_permitidas_ids
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


@hora_bp.route('/tagplus/conta/mapeamento/listar-produtos', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_produto_map_listar_api():
    """Proxy GET /produtos no TagPlus.

    Retorna lista paginada (per_page=100) com id/codigo/nome para o operador
    ver os produtos disponiveis ao preencher o mapeamento.
    """
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        return jsonify({'ok': False, 'error': 'Conta nao configurada.'}), 404
    if not conta.token:
        return jsonify({'ok': False, 'error': 'Sem token OAuth — autorizar em /hora/tagplus/conta.'}), 400

    page = max(1, int(request.args.get('page', 1)))
    q = (request.args.get('q') or '').strip()
    params = {'per_page': 100, 'page': page}
    if q:
        params['q'] = q

    client = ApiClient(conta)
    r = client.get('/produtos', params=params)
    if r.status_code != 200:
        return jsonify({
            'ok': False,
            'http_status': r.status_code,
            'error': r.text[:300],
        }), 502

    try:
        body = r.json()
    except ValueError:
        body = []
    if isinstance(body, dict):
        body = body.get('data') or body.get('produtos') or body.get('results') or []

    # Normaliza: pega so campos uteis para a UI.
    produtos = []
    if isinstance(body, list):
        for p in body:
            if not isinstance(p, dict):
                continue
            produtos.append({
                'id': p.get('id'),
                'codigo': p.get('codigo') or p.get('cod_secundario'),
                'nome': p.get('descricao_produto') or p.get('descricao') or p.get('nome'),
                'ativo': p.get('ativo'),
            })

    return jsonify({
        'ok': True,
        'page': page,
        'count': len(produtos),
        'produtos': produtos,
    })


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
    """Lista todas as formas mapeadas. Operador pode adicionar livremente
    (sugestoes iniciais: PIX, CARTAO_CREDITO, DINHEIRO).
    """
    sugestoes = ('PIX', 'CARTAO_CREDITO', 'DINHEIRO', 'CARTAO_DEBITO', 'BOLETO', 'TRANSFERENCIA')
    todas = HoraTagPlusFormaPagamentoMap.query.order_by(
        HoraTagPlusFormaPagamentoMap.forma_pagamento_hora
    ).all()
    nomes_existentes = {m.forma_pagamento_hora for m in todas}
    rows = [{'forma': m.forma_pagamento_hora, 'map': m} for m in todas]
    # Linhas vazias para sugestoes ainda nao cadastradas (facilita primeiro setup).
    for s in sugestoes:
        if s not in nomes_existentes:
            rows.append({'forma': s, 'map': None})
    return render_template('hora/tagplus/forma_pag_map.html', rows=rows)


@hora_bp.route('/tagplus/conta/formas-pagamento/listar', methods=['GET'])
@require_hora_perm('tagplus', 'ver')
def tagplus_forma_map_listar_api():
    """Lista formas de pagamento do TagPlus.

    Estrategia em 2 passos:
      1. Tenta endpoints diretos: /formas_pagamento, /formas_pgto, /forma_pagamento.
         (No scope atual `write:nfes read:clientes write:clientes read:produtos`,
         estes retornam 403 — o endpoint existe mas falta scope).

      2. Fallback automatico: extrai IDs unicos de `faturas[].id_forma_pagamento`
         das NFes recentes (scope `write:nfes` cobre o read implicito).
    """
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        return jsonify({'ok': False, 'error': 'Conta nao configurada.'}), 404
    if not conta.token:
        return jsonify({'ok': False, 'error': 'Sem token OAuth — autorizar em /hora/tagplus/conta.'}), 400

    client = ApiClient(conta)

    # ---- Passo 1: endpoints diretos ----
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
                'fonte': 'endpoint_direto',
                'endpoint': path,
                'count': len(body) if isinstance(body, list) else 0,
                'formas': body,
            })

    # ---- Passo 2: fallback via NFes recentes ----
    # Tenta /nfes (scope write:nfes contratado garante read).
    r_nfes = client.get('/nfes', params={'per_page': 50, 'fields': 'id,faturas,status'})
    if r_nfes.status_code == 200:
        try:
            nfes = r_nfes.json() or []
        except ValueError:
            nfes = []
        if isinstance(nfes, dict):
            nfes = nfes.get('data') or nfes.get('nfes') or nfes.get('results') or []

        # Extrai IDs unicos (id -> primeiro objeto encontrado).
        formas_por_id: dict = {}
        for nf in nfes if isinstance(nfes, list) else []:
            faturas = nf.get('faturas') if isinstance(nf, dict) else None
            if not isinstance(faturas, list):
                continue
            for f in faturas:
                if not isinstance(f, dict):
                    continue
                # Schema observado em doc: faturas[].id_forma_pagamento OR faturas[].forma_pagamento (int).
                fid = f.get('id_forma_pagamento') or f.get('forma_pagamento')
                if isinstance(fid, dict):
                    obj_id = fid.get('id')
                    if obj_id is None:
                        continue
                    formas_por_id.setdefault(obj_id, {
                        'id': obj_id,
                        'descricao': fid.get('descricao') or fid.get('nome') or f'forma {obj_id}',
                        'origem_nfe_id': nf.get('id'),
                    })
                elif isinstance(fid, int):
                    formas_por_id.setdefault(fid, {
                        'id': fid,
                        'descricao': f'forma {fid} (sem descricao — extraida de NFe {nf.get("id")})',
                        'origem_nfe_id': nf.get('id'),
                    })

        if formas_por_id:
            return jsonify({
                'ok': True,
                'fonte': 'nfes_existentes',
                'count': len(formas_por_id),
                'formas': sorted(formas_por_id.values(), key=lambda x: x['id']),
                'aviso': (
                    f'Endpoint direto retornou 403 (provavel falta de scope). '
                    f'IDs extraidos de {len(nfes) if isinstance(nfes, list) else 0} NFes '
                    f'recentes. Para descricoes completas, ampliar scope OAuth ou '
                    f'consultar GET /nfes/{{id}} individualmente.'
                ),
            })

    # ---- Falha total ----
    return jsonify({
        'ok': False,
        'error': 'Endpoint direto retornou 403 e nao ha NFes para extrair IDs.',
        'tentativas_diretas': candidatos,
        'ultima_resposta_direta': {
            'endpoint': ultima_resposta[0] if ultima_resposta else None,
            'http_status': ultima_resposta[1] if ultima_resposta else None,
            'body': ultima_resposta[2] if ultima_resposta else None,
        },
        'fallback_nfes': {
            'http_status': r_nfes.status_code,
            'count': 0,
        },
        'instrucoes': (
            'Opcoes: (a) emitir 1 NFe de teste no portal TagPlus com cada forma '
            '(PIX, CARTAO_CREDITO, DINHEIRO) e clicar de novo neste botao para '
            'extrair os IDs automaticamente das NFes; (b) ampliar o scope no '
            'campo "Scopes" em /hora/tagplus/conta (adicionar `read:formas_pagamento` '
            'ou variante como `read:formas_pgto`), salvar e clicar "Re-autorizar OAuth" '
            '— scope e enviado em ?scope= na URL /authorize, nao configurado no portal.'
        ),
    }), 502


@hora_bp.route('/tagplus/conta/formas-pagamento', methods=['POST'])
@require_hora_perm('tagplus', 'editar')
def tagplus_forma_map_salvar():
    """Processa dinamicamente todas as linhas no form (form-array indexed).

    Form fields esperados (idx = 0..N):
      forma[idx]            -> nome HORA (ex: PIX, CARTAO_DEBITO, etc.)
      tagplus_id[idx]       -> ID inteiro no TagPlus (vazio = remover)
      descricao[idx]        -> texto livre (opcional)
    """
    formas_form = request.form.getlist('forma[]')
    ids_form = request.form.getlist('tagplus_id[]')
    descs_form = request.form.getlist('descricao[]')

    nomes_processados = set()
    for forma_raw, id_raw, desc_raw in zip(formas_form, ids_form, descs_form):
        forma = (forma_raw or '').strip().upper()[:20]
        tagplus_id = (id_raw or '').strip()
        descricao = (desc_raw or '').strip() or None

        if not forma:
            continue
        if forma in nomes_processados:
            flash(f'Forma duplicada no form: {forma}', 'warning')
            continue
        nomes_processados.add(forma)

        existente = HoraTagPlusFormaPagamentoMap.query.filter_by(
            forma_pagamento_hora=forma,
        ).first()

        if not tagplus_id:
            # Vazio = remover (se existir).
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
    flash(f'Mapeamentos salvos ({len(nomes_processados)} formas processadas).', 'success')
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
# 4.5) Esboco — preview do payload sem emitir
# ============================================================

@hora_bp.route('/tagplus/esboco')
@require_hora_perm('tagplus', 'ver')
def tagplus_esboco_lista():
    """Lista vendas elegíveis para teste de payload TagPlus.

    Mostra HoraVendas que ainda não emitiram NFe (status sem `APROVADA`).
    Operador escolhe uma e vê o JSON que seria enviado ao TagPlus.
    """
    # Vendas com itens, sem emissao ou em estado retomavel.
    q = (
        HoraVenda.query
        .order_by(HoraVenda.id.desc())
        .limit(50)
    )
    vendas = q.all()
    # Marcar status de emissao por venda.
    emissoes_por_venda = {
        e.venda_id: e for e in HoraTagPlusNfeEmissao.query.filter(
            HoraTagPlusNfeEmissao.venda_id.in_([v.id for v in vendas])
        ).all()
    } if vendas else {}
    rows = [{'venda': v, 'emissao': emissoes_por_venda.get(v.id)} for v in vendas]
    return render_template('hora/tagplus/esboco_lista.html', rows=rows)


def _auditar_payload_required(payload: dict) -> list[dict]:
    """Audita o payload contra os 3 campos required do POST /nfes (doc_tagplus.md:163-178).

    required: destinatario (integer), itens (Array), cfop (string mascara 9.999).
    Tambem valida campos relevantes do `Item de Venda` e `Fatura Pagamento`.

    Retorna lista de checks: [{campo, ok, detalhe}].
    """
    import re
    checks = []

    # destinatario: required integer
    dest = payload.get('destinatario')
    checks.append({
        'campo': 'destinatario',
        'ok': isinstance(dest, int) and dest > 0,
        'required': True,
        'detalhe': f'integer={dest}' if isinstance(dest, int) else f'tipo={type(dest).__name__} valor={dest!r}',
    })

    # itens: required Array (>= 1)
    itens = payload.get('itens')
    itens_ok = isinstance(itens, list) and len(itens) > 0
    checks.append({
        'campo': 'itens',
        'ok': itens_ok,
        'required': True,
        'detalhe': f'{len(itens) if isinstance(itens, list) else "—"} item(ns)',
    })
    if itens_ok:
        for idx, it in enumerate(itens):
            prod = it.get('produto') if isinstance(it, dict) else None
            qtd = it.get('qtd') if isinstance(it, dict) else None
            vu = it.get('valor_unitario') if isinstance(it, dict) else None
            checks.append({
                'campo': f'itens[{idx}].produto',
                'ok': bool(prod) and (isinstance(prod, (int, str))),
                'required': False,
                'detalhe': f'tipo={type(prod).__name__} valor={prod!r}',
            })
            checks.append({
                'campo': f'itens[{idx}].qtd',
                'ok': isinstance(qtd, (int, float)) and qtd > 0,
                'required': False,
                'detalhe': f'{qtd}',
            })
            checks.append({
                'campo': f'itens[{idx}].valor_unitario',
                'ok': isinstance(vu, (int, float)) and vu >= 0,
                'required': False,
                'detalhe': f'{vu}',
            })

    # cfop: required string mascara 9.999
    cfop = payload.get('cfop')
    checks.append({
        'campo': 'cfop',
        'ok': isinstance(cfop, str) and bool(re.match(r'^\d\.\d{3}$', cfop)),
        'required': True,
        'detalhe': f'{cfop!r} (mascara 9.999)',
    })

    # faturas (nao required pela doc, mas necessario na pratica para emissao com pagamento)
    faturas = payload.get('faturas')
    checks.append({
        'campo': 'faturas',
        'ok': isinstance(faturas, list) and len(faturas) > 0,
        'required': False,
        'detalhe': f'{len(faturas) if isinstance(faturas, list) else "—"} fatura(s)',
    })
    if isinstance(faturas, list):
        for idx, fat in enumerate(faturas):
            fp = fat.get('forma_pagamento') if isinstance(fat, dict) else None
            parcs = fat.get('parcelas') if isinstance(fat, dict) else None
            checks.append({
                'campo': f'faturas[{idx}].forma_pagamento',
                'ok': isinstance(fp, int) and fp > 0,
                'required': False,
                'detalhe': f'tipo={type(fp).__name__} valor={fp!r}',
            })
            checks.append({
                'campo': f'faturas[{idx}].parcelas',
                'ok': isinstance(parcs, list) and len(parcs) > 0,
                'required': False,
                'detalhe': f'{len(parcs) if isinstance(parcs, list) else "—"} parcela(s)',
            })

    return checks


@hora_bp.route('/tagplus/esboco/<int:venda_id>')
@require_hora_perm('tagplus', 'ver')
def tagplus_esboco_preview(venda_id: int):
    """Monta payload via PayloadBuilder SEM enviar ao TagPlus.

    Retorna JSON renderizado + auditoria dos campos required (doc_tagplus.md:163-178).
    Erros de pré-condição (forma_pagamento ausente, modelo não mapeado, CPF inválido)
    são exibidos de forma amigável para o operador corrigir antes de emitir.
    """
    from app.hora.services.tagplus.payload_builder import PayloadBuilder, PayloadBuilderError

    venda = HoraVenda.query.get_or_404(venda_id)
    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if not conta:
        flash('Conta TagPlus não configurada.', 'danger')
        return redirect(url_for('hora.tagplus_esboco_lista'))

    payload = None
    erro = None
    auditoria = None
    try:
        builder = PayloadBuilder(conta)
        payload = builder.build(venda)
        auditoria = _auditar_payload_required(payload)
    except PayloadBuilderError as exc:
        erro = {'code': exc.code, 'message': exc.message}
    except Exception as exc:  # noqa: BLE001
        logger.exception('Falha gerando esboco para venda %s', venda_id)
        erro = {'code': 'erro_inesperado', 'message': str(exc)}

    import json
    payload_json = json.dumps(payload, indent=2, ensure_ascii=False) if payload else None

    # Verifica se ja existe emissao para esta venda (evita re-emissao acidental).
    emissao_existente = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()

    return render_template(
        'hora/tagplus/esboco_preview.html',
        venda=venda,
        payload=payload,
        payload_json=payload_json,
        auditoria=auditoria,
        erro=erro,
        emissao_existente=emissao_existente,
        ambiente=conta.ambiente,
    )


@hora_bp.route('/tagplus/esboco/<int:venda_id>/emitir', methods=['POST'])
@require_hora_perm('vendas', 'criar')
def tagplus_esboco_emitir(venda_id: int):
    """Emite NFe REAL pelo esboço (mesmo enfileiramento que /vendas/<id>/nfe/emitir).

    Reusa EmissorNfeHora.enfileirar — POST /nfes com headers X-Enviar-Nota=true e
    X-Calculo-Trib-Automatico=true (envia para SEFAZ direto, status 202 esperado).
    """
    try:
        emissao_id = EmissorNfeHora.enfileirar(venda_id)
        flash(
            f'Emissão enfileirada (id={emissao_id}). Acompanhe na tela da venda '
            f'ou em "Fila de emissões".',
            'success',
        )
        return redirect(url_for('hora.venda_nfe_status', venda_id=venda_id))
    except EmissaoBloqueadaError as exc:
        flash(f'Emissão bloqueada: {exc}', 'warning')
    except RuntimeError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.tagplus_esboco_preview', venda_id=venda_id))


# ============================================================
# 4.6) Pedido de Venda — formulario manual para emissao TagPlus
# ============================================================

@hora_bp.route('/tagplus/pedido-venda/novo', methods=['GET'])
@require_hora_perm('vendas', 'criar')
def tagplus_pedido_venda_novo():
    """Formulario para criar HoraVenda manualmente (sem upload de DANFE).

    Operador preenche cliente + endereco + escolhe modelo/cor/chassi e forma de
    pagamento. Submissao cria venda + redireciona para o esboco TagPlus para o
    operador conferir o payload e emitir.

    Filtros do SELECT respeitam o escopo de loja (`lojas_permitidas_ids`).
    """
    permitidas = lojas_permitidas_ids()

    # Modelos com pelo menos 1 chassi em estoque (mesmo escopo do estoque).
    from app.hora.services.estoque_service import opcoes_filtro_estoque
    opcoes = opcoes_filtro_estoque(lojas_permitidas_ids=permitidas)
    modelos = opcoes['modelos']

    # Formas de pagamento mapeadas no TagPlus.
    formas_pagamento = (
        HoraTagPlusFormaPagamentoMap.query
        .order_by(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora)
        .all()
    )

    return render_template(
        'hora/tagplus/pedido_venda_novo.html',
        modelos=modelos,
        formas_pagamento=formas_pagamento,
    )


@hora_bp.route('/tagplus/pedido-venda', methods=['POST'])
@require_hora_perm('vendas', 'criar')
def tagplus_pedido_venda_criar():
    """Cria HoraVenda manual e redireciona para o esboco TagPlus."""
    from decimal import Decimal, InvalidOperation
    from app.hora.services import venda_service

    def _g(name: str, max_len: int = 255) -> str:
        return (request.form.get(name) or '').strip()[:max_len]

    valor_raw = _g('valor', 30)
    try:
        valor_dec = Decimal(valor_raw.replace('.', '').replace(',', '.')) \
            if ',' in valor_raw else Decimal(valor_raw)
    except (InvalidOperation, ValueError):
        flash(f'Valor invalido: {valor_raw!r}', 'danger')
        return redirect(url_for('hora.tagplus_pedido_venda_novo'))

    try:
        venda = venda_service.criar_venda_manual(
            cpf_cliente=_g('cpf', 14),
            nome_cliente=_g('nome', 200),
            cep=_g('cep', 9),
            endereco_logradouro=_g('logradouro', 255),
            endereco_numero=_g('numero_endereco', 20),
            endereco_complemento=_g('complemento', 100),
            endereco_bairro=_g('bairro', 100),
            endereco_cidade=_g('cidade', 100),
            endereco_uf=_g('uf', 2),
            numero_chassi=_g('chassi', 30),
            valor_final=valor_dec,
            forma_pagamento=_g('forma_pagamento', 20),
            telefone_cliente=_g('telefone', 20) or None,
            email_cliente=_g('email', 120) or None,
            vendedor=_g('vendedor', 100) or None,
            observacoes=_g('observacoes', 500) or None,
            criado_por=_operador(),
        )
    except ValueError as exc:
        flash(f'Erro ao criar pedido de venda: {exc}', 'danger')
        return redirect(url_for('hora.tagplus_pedido_venda_novo'))

    flash(
        f'Pedido de venda #{venda.id} criado para {venda.nome_cliente}. '
        f'Confira o esboco abaixo antes de emitir a NFe.',
        'success',
    )
    return redirect(url_for('hora.tagplus_esboco_preview', venda_id=venda.id))


@hora_bp.route('/tagplus/pedido-venda/api/cores')
@require_hora_perm('vendas', 'criar')
def tagplus_pedido_venda_api_cores():
    """JSON com cores que tem chassi disponivel para o modelo informado."""
    from app.hora.services.estoque_service import cores_disponiveis_por_modelo

    try:
        modelo_id = int(request.args.get('modelo_id', '0'))
    except ValueError:
        return jsonify({'ok': False, 'error': 'modelo_id invalido'}), 400
    if not modelo_id:
        return jsonify({'ok': True, 'cores': []})

    permitidas = lojas_permitidas_ids()
    cores = cores_disponiveis_por_modelo(
        modelo_id=modelo_id,
        lojas_permitidas_ids=permitidas,
    )
    return jsonify({'ok': True, 'cores': cores})


@hora_bp.route('/tagplus/pedido-venda/api/chassis')
@require_hora_perm('vendas', 'criar')
def tagplus_pedido_venda_api_chassis():
    """JSON com chassis disponiveis filtrados por modelo + cor."""
    from app.hora.services.estoque_service import chassis_disponiveis_para_venda

    try:
        modelo_id = int(request.args.get('modelo_id', '0'))
    except ValueError:
        return jsonify({'ok': False, 'error': 'modelo_id invalido'}), 400
    cor = (request.args.get('cor') or '').strip().upper() or None
    if not modelo_id:
        return jsonify({'ok': True, 'chassis': []})

    permitidas = lojas_permitidas_ids()
    chassis = chassis_disponiveis_para_venda(
        modelo_id=modelo_id,
        cor=cor,
        lojas_permitidas_ids=permitidas,
    )
    return jsonify({'ok': True, 'chassis': chassis})


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
