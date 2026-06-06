# app/integracoes/tagplus/services/notificacao_whatsapp_service.py
"""Serviço de notificação WhatsApp para pedido/NF do TagPlus.

Processamento assíncrono em Thread(daemon=False), espelhando o padrão do
WhatsApp bot (app/whatsapp/services.py: R1 thread non-daemon, R2 commit retry,
R3 re-fetch, R5 cleanup no finally). Best-effort: falhas degradam e ficam no
registro tagplus_notificacao_whatsapp.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import Optional

from sqlalchemy import func, or_

from app.utils.whatsapp_notify import send_whatsapp, WhatsAppNotifyError
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

DELAYS_BUSCA = [1, 3, 5]


def _resolver_vendedor(nome: Optional[str]):
    """Resolve o nome do vendedor (TagPlus) -> Usuario autorizado no WhatsApp.

    Match case-insensitive por `vendedor_vinculado` OU `nome`, exigindo
    `whatsapp_autorizado=True`, `status='ativo'` e `telefone` preenchido.
    Retorna o Usuario ou None (fallback só-grupo).
    """
    if not nome or not nome.strip():
        return None
    from app.auth.models import Usuario

    alvo = nome.strip().lower()
    return (
        Usuario.query
        .filter(Usuario.whatsapp_autorizado.is_(True))
        .filter(Usuario.status == 'ativo')
        .filter(Usuario.telefone.isnot(None))
        .filter(or_(
            func.lower(Usuario.vendedor_vinculado) == alvo,
            func.lower(Usuario.nome) == alvo,
        ))
        .first()
    )


def _commit_with_retry() -> bool:
    """Commit com retry para SSL drop do Render PostgreSQL (espelha WhatsApp bot)."""
    from app import db
    try:
        db.session.commit()
        return True
    except Exception as exc:
        s = str(exc).lower()
        if 'ssl' in s or 'connection' in s or 'closed' in s:
            logger.warning(f"[TAGPLUS-NOTIF] Conexao perdida no commit: {exc}")
            db.session.rollback(); db.session.close()
            return False
        raise


def _get_api():
    """Cliente OAuth da integração principal (conta 'notas')."""
    from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
    return TagPlusOAuth2V2(api_type='notas')


def _buscar_nfe_com_retry(api, tagplus_id: str) -> Optional[dict]:
    for i, delay in enumerate(DELAYS_BUSCA):
        try:
            r = api.make_request('GET', f'/nfes/{tagplus_id}')
            if r is not None and r.status_code == 200:
                return r.json() or None
        except Exception as exc:
            logger.warning(f"[TAGPLUS-NOTIF] GET /nfes/{tagplus_id} erro: {exc}")
        if i < len(DELAYS_BUSCA) - 1:
            time.sleep(delay)
    return None


def _buscar_pedido(api, pedido_id) -> Optional[dict]:
    """GET /pedidos/{id}. 401 = scope read:pedidos ausente -> propaga sinal."""
    try:
        r = api.make_request('GET', f'/pedidos/{pedido_id}')
    except Exception as exc:
        logger.warning(f"[TAGPLUS-NOTIF] GET /pedidos/{pedido_id} erro: {exc}")
        return None
    if r is None:
        return None
    if r.status_code == 401:
        raise PermissionError('scope read:pedidos ausente (GET /pedidos 401)')
    if r.status_code != 200:
        return None
    return r.json() or None


def _buscar_pedido_com_retry(api, pedido_id) -> Optional[dict]:
    for i, delay in enumerate(DELAYS_BUSCA):
        ped = _buscar_pedido(api, pedido_id)
        if ped:
            return ped
        if i < len(DELAYS_BUSCA) - 1:
            time.sleep(delay)
    return None


def _baixar_danfe_pdf(api, tagplus_id: str) -> Optional[bytes]:
    try:
        r = api.make_request('GET', f'/nfes/pdf/recibo_a4/{tagplus_id}')
    except Exception as exc:
        logger.warning(f"[TAGPLUS-NOTIF] PDF DANFE {tagplus_id} erro: {exc}")
        return None
    if r is None or r.status_code != 200:
        return None
    ctype = (r.headers.get('Content-Type') or '').lower()
    if 'pdf' not in ctype and not (r.content[:4] == b'%PDF'):
        logger.warning(f"[TAGPLUS-NOTIF] DANFE {tagplus_id} não é PDF (ctype={ctype})")
        return None
    return r.content


def _enviar_para_destinos(reg, texto, anexo_b64, anexo_filename, vendedor):
    """Envia ao grupo e (se houver) à DM do vendedor. Atualiza flags/status."""
    grupo_jid = os.environ.get('TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID', '').strip()
    if not grupo_jid:
        reg.status = 'ERRO'
        reg.erro = 'TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID não configurado'
        return

    grupo_ok = False
    try:
        send_whatsapp(grupo_jid, texto, skip_rate_limit=True,
                      anexo_b64=anexo_b64, anexo_filename=anexo_filename)
        grupo_ok = True
    except WhatsAppNotifyError as exc:
        reg.erro = f'Grupo: {exc}'
    reg.enviado_grupo = grupo_ok

    if vendedor is not None and getattr(vendedor, 'telefone', None):
        reg.vendedor_user_id = getattr(vendedor, 'id', None)
        try:
            send_whatsapp(vendedor.telefone, texto, skip_rate_limit=True,
                          anexo_b64=anexo_b64, anexo_filename=anexo_filename)
            reg.enviado_vendedor = True
        except WhatsAppNotifyError as exc:
            reg.enviado_vendedor = False
            reg.erro = ((reg.erro or '') + f' | Vendedor: {exc}').strip(' |')
    else:
        reg.enviado_vendedor = None

    if not grupo_ok:
        reg.status = 'ERRO'
    elif reg.enviado_vendedor is False:
        reg.status = 'PARCIAL'
    else:
        reg.status = 'ENVIADO'
    reg.enviado_em = agora_utc_naive()


def processar_notificacao_async(app, registro_id: int) -> None:
    """Thread entrypoint: busca dados, formata, resolve vendedor, envia destinos."""
    from app import db
    from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
    from app.integracoes.tagplus.services import formatador_notificacao as fmt

    with app.app_context():
        reg = None
        try:
            reg = db.session.get(TagPlusNotificacaoWhatsapp, registro_id)
            if not reg:
                logger.error(f"[TAGPLUS-NOTIF] Registro {registro_id} não encontrado")
                return
            reg.status = 'PROCESSANDO'
            reg.tentativas = (reg.tentativas or 0) + 1
            _commit_with_retry()

            api = _get_api()
            vendedor_nome = None
            anexo_b64 = None
            anexo_filename = None

            if reg.tipo == 'NFE':
                nfe = _buscar_nfe_com_retry(api, reg.tagplus_id)
                if not nfe:
                    reg.status = 'ERRO'; reg.erro = 'NFe não encontrada na API após retries'
                    _commit_with_retry(); return
                reg.numero = str(nfe.get('numero') or '')
                reg.cliente_nome = (nfe.get('destinatario') or {}).get('razao_social')
                reg.valor = nfe.get('valor_nota')
                pedido_vinc = (nfe.get('pedido_os_vinculada') or {}).get('id')
                if pedido_vinc:
                    try:
                        ped = _buscar_pedido(api, pedido_vinc)
                        if ped:
                            vendedor_nome = (ped.get('vendedor') or {}).get('nome')
                    except PermissionError:
                        reg.erro = 'Sem scope read:pedidos: vendedor da NF não resolvido'
                reg.vendedor_nome = vendedor_nome
                texto = fmt.formatar_nfe(nfe, vendedor_nome=vendedor_nome)
                pdf = _baixar_danfe_pdf(api, reg.tagplus_id)
                if pdf:
                    anexo_b64 = base64.b64encode(pdf).decode()
                    anexo_filename = f"danfe_{reg.numero or reg.tagplus_id}.pdf"
                    reg.anexou_pdf = True
                else:
                    reg.erro = ((reg.erro or '') + ' | PDF indisponível, enviado só texto').strip(' |')

            elif reg.tipo == 'PEDIDO':
                try:
                    ped = _buscar_pedido_com_retry(api, reg.tagplus_id)
                except PermissionError:
                    reg.status = 'ERRO'
                    reg.erro = 'Sem scope read:pedidos — reautorizar OAuth (read:pedidos)'
                    _commit_with_retry(); return
                if not ped:
                    reg.status = 'ERRO'; reg.erro = 'Pedido não encontrado na API após retries'
                    _commit_with_retry(); return
                reg.numero = str(ped.get('numero') or '')
                reg.cliente_nome = (ped.get('cliente') or {}).get('razao_social')
                reg.valor = ped.get('valor_total')
                vendedor_nome = (ped.get('vendedor') or {}).get('nome')
                reg.vendedor_nome = vendedor_nome
                texto = fmt.formatar_pedido(ped)
            else:
                reg.status = 'IGNORADO'; reg.erro = f'tipo desconhecido: {reg.tipo}'
                _commit_with_retry(); return

            vendedor = _resolver_vendedor(vendedor_nome)
            _enviar_para_destinos(reg, texto, anexo_b64, anexo_filename, vendedor)

            reg = db.session.get(TagPlusNotificacaoWhatsapp, registro_id) or reg
            _commit_with_retry()
            logger.info(f"[TAGPLUS-NOTIF] {reg.tipo} {reg.tagplus_id} -> {reg.status}")

        except Exception as exc:
            logger.error(f"[TAGPLUS-NOTIF] Erro registro {registro_id}: {exc}", exc_info=True)
            try:
                r = db.session.get(TagPlusNotificacaoWhatsapp, registro_id)
                if r:
                    r.status = 'ERRO'; r.erro = f'Erro interno: {str(exc)[:300]}'
                    db.session.commit()
            except Exception:
                pass
        finally:
            try:
                db.session.remove()
            except Exception:
                pass


def disparar_thread(app, registro_id: int) -> None:
    """Dispara o processamento em Thread(daemon=False) (R1 do WhatsApp bot)."""
    import threading
    t = threading.Thread(
        target=processar_notificacao_async, args=(app, registro_id), daemon=False,
        name=f"tagplus-notif-{registro_id}",
    )
    t.start()
