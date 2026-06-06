"""Service de notificação WhatsApp para o módulo Lojas HORA.

Responsável por formatar e enviar notificações de pedidos de venda e NFe
via WhatsApp, tanto para o grupo HORA quanto para o vendedor responsável.

Uso típico (chamado pelo worker H3):
    from app.hora.services.tagplus.notificacao_whatsapp import processar_notificacao
    processar_notificacao(registro_id)

Ou para enfileirar:
    from app.hora.services.tagplus.notificacao_whatsapp import enfileirar_notificacao
    enfileirar_notificacao('PEDIDO', venda_id)
    enfileirar_notificacao('NFE', emissao_id)
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

from sqlalchemy import func, or_

from app.utils.whatsapp_notify import send_whatsapp, WhatsAppNotifyError
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

QUEUE_NAME = 'hora_nfe'


# ─── Helpers de formatação ────────────────────────────────────────────────────

def _valor_br(v) -> str:
    """Formata valor monetário no padrão brasileiro: R$ 1.234,56."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 'R$ 0,00'
    return f'R$ {f:_.2f}'.replace('.', ',').replace('_', '.')


def _data_br(s) -> str:
    """Formata string ou date como dd/mm/aaaa. Retorna '' se nulo."""
    if s is None:
        return ''
    if hasattr(s, 'strftime'):
        return s.strftime('%d/%m/%Y')
    return str(s)


# ─── Resolução de entidades ───────────────────────────────────────────────────

def _resolver_vendedor(nome: Optional[str]):
    """Busca usuário com WhatsApp autorizado que corresponda ao nome do vendedor.

    Faz match case-insensitive em vendedor_vinculado OU nome.
    Retorna instância de Usuario ou None.
    """
    if not nome or not nome.strip():
        return None

    from app.auth.models import Usuario

    alvo = nome.strip().lower()
    return (
        Usuario.query
        .filter(
            Usuario.whatsapp_autorizado.is_(True),
            Usuario.status == 'ativo',
            Usuario.telefone.isnot(None),
            or_(
                func.lower(Usuario.vendedor_vinculado) == alvo,
                func.lower(Usuario.nome) == alvo,
            ),
        )
        .first()
    )


def _carregar_pedido(venda_id: int):
    """Carrega HoraVenda por id. Retorna None se não encontrado."""
    from app.hora.models.venda import HoraVenda
    return HoraVenda.query.get(venda_id)


def _carregar_nfe(emissao_id: int):
    """Carrega HoraTagPlusNfeEmissao por id. Retorna None se não encontrada."""
    from app.hora.models.tagplus import HoraTagPlusNfeEmissao
    return HoraTagPlusNfeEmissao.query.get(emissao_id)


# ─── Formatadores de mensagem ─────────────────────────────────────────────────

def _formatar_itens(itens) -> str:
    """Formata lista de itens de venda para mensagem WhatsApp (até 30 itens)."""
    if not itens:
        return ''

    linhas = []
    for item in itens[:30]:
        # Acesso defensivo aos atributos do item e da moto
        moto = getattr(item, 'moto', None)
        chassi = getattr(moto, 'numero_chassi', None) or getattr(item, 'numero_chassi', '—')
        cor = getattr(moto, 'cor', None) or ''

        modelo_obj = getattr(moto, 'modelo', None)
        modelo_nome = getattr(modelo_obj, 'nome_modelo', None) or ''

        partes = [f'• *{chassi}*']
        if modelo_nome:
            partes.append(modelo_nome)
        if cor:
            partes.append(cor)

        linhas.append(' · '.join(partes))

    return '\n'.join(linhas)


def _formatar_pedido(venda) -> str:
    """Formata mensagem de novo pedido de venda para WhatsApp."""
    loja_nome = None
    if getattr(venda, 'loja', None):
        loja_nome = getattr(venda.loja, 'nome', None)

    linhas = [
        f'🛒 *Novo pedido confirmado — Nº {venda.id}*',
        '',
        f'👤 Cliente: {venda.nome_cliente or "—"}',
    ]

    vendedor = getattr(venda, 'vendedor', None)
    if vendedor:
        linhas.append(f'🧑‍💼 Vendedor: {vendedor}')

    linhas.append(f'💰 Valor: {_valor_br(venda.valor_total)}')

    if loja_nome:
        linhas.append(f'🏪 Loja: {loja_nome}')

    itens = getattr(venda, 'itens', None) or []
    if itens:
        linhas.append('')
        linhas.append('🏍 *Motos do pedido:*')
        linhas.append(_formatar_itens(itens))

    return '\n'.join(linhas)


def _formatar_nfe(venda, emissao) -> str:
    """Formata mensagem de NFe emitida para WhatsApp."""
    loja_nome = None
    if venda and getattr(venda, 'loja', None):
        loja_nome = getattr(venda.loja, 'nome', None)

    numero_nfe = getattr(emissao, 'numero_nfe', None) or getattr(emissao, 'tagplus_nfe_id', '—')
    linhas = [
        f'🧾 *NF emitida — Nº {numero_nfe}*',
        '',
    ]

    if venda:
        linhas.append(f'👤 Cliente: {venda.nome_cliente or "—"}')

        vendedor = getattr(venda, 'vendedor', None)
        if vendedor:
            linhas.append(f'🧑‍💼 Vendedor: {vendedor}')

        linhas.append(f'💰 Valor: {_valor_br(venda.valor_total)}')

    if loja_nome:
        linhas.append(f'🏪 Loja: {loja_nome}')

    chave = getattr(emissao, 'chave_44', None)
    if chave:
        linhas.append(f'🔑 Chave: {chave}')

    # Itens vêm da venda (NFe não expõe itens diretamente no model local)
    itens = (getattr(venda, 'itens', None) or []) if venda else []
    if itens:
        linhas.append('')
        linhas.append('🏍 *Motos faturadas:*')
        linhas.append(_formatar_itens(itens))

    return '\n'.join(linhas)


# ─── Download do DANFE ────────────────────────────────────────────────────────

def _baixar_danfe_pdf(emissao) -> Optional[bytes]:
    """Tenta baixar o PDF da NFe via TagPlus. Retorna bytes ou None (best-effort)."""
    try:
        from app.hora.models.tagplus import HoraTagPlusConta
        from app.hora.services.tagplus.api_client import ApiClient

        conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
        if not conta:
            logger.warning('HORA notificacao: sem conta TagPlus ativa para baixar DANFE')
            return None

        tagplus_nfe_id = getattr(emissao, 'tagplus_nfe_id', None)
        if not tagplus_nfe_id:
            logger.info('HORA notificacao: emissao sem tagplus_nfe_id — sem PDF')
            return None

        api = ApiClient(conta)
        r = api.get(f'/nfes/pdf/recibo_a4/{tagplus_nfe_id}')

        if r.status_code != 200:
            logger.warning('HORA notificacao: TagPlus retornou %s ao baixar PDF', r.status_code)
            return None

        conteudo = r.content
        content_type = (r.headers or {}).get('Content-Type', '') if hasattr(r, 'headers') else ''
        if not ('pdf' in content_type.lower() or conteudo[:4] == b'%PDF'):
            logger.warning('HORA notificacao: resposta TagPlus não é PDF (ct=%s)', content_type)
            return None

        return conteudo

    except Exception as exc:
        logger.warning('HORA notificacao: falha ao baixar DANFE (best-effort): %s', exc)
        return None


# ─── Envio de mensagens ───────────────────────────────────────────────────────

def _enviar_para_destinos(reg, texto: str, anexo_b64: Optional[str],
                          anexo_filename: Optional[str], vendedor) -> None:
    """Envia a notificação para o grupo e/ou vendedor de forma idempotente.

    Atualiza os campos enviado_grupo, enviado_vendedor e status no registro
    (sem commit — chamador deve commitar).
    """
    group_jid = os.environ.get('HORA_TAGPLUS_NOTIFY_GROUP_JID', '').strip()
    if not group_jid:
        reg.status = 'ERRO'
        reg.erro = 'GROUP_JID não configurado (HORA_TAGPLUS_NOTIFY_GROUP_JID)'
        return

    grupo_ok = reg.enviado_grupo  # já enviado antes?

    # Envio para o grupo
    if not grupo_ok:
        try:
            send_whatsapp(
                group_jid, texto,
                skip_rate_limit=True,
                anexo_b64=anexo_b64,
                anexo_filename=anexo_filename,
            )
            reg.enviado_grupo = True
            grupo_ok = True
        except WhatsAppNotifyError as exc:
            logger.error('HORA notificacao: falha ao enviar para grupo %s: %s', group_jid, exc)
            reg.enviado_grupo = False
            grupo_ok = False

    # Envio para o vendedor (apenas se houver vendedor com telefone)
    if reg.enviado_vendedor is not True:
        if vendedor and getattr(vendedor, 'telefone', None):
            try:
                send_whatsapp(
                    vendedor.telefone, texto,
                    skip_rate_limit=True,
                    anexo_b64=anexo_b64,
                    anexo_filename=anexo_filename,
                )
                reg.enviado_vendedor = True
            except WhatsAppNotifyError as exc:
                logger.warning('HORA notificacao: falha ao enviar para vendedor: %s', exc)
                reg.enviado_vendedor = False
        # Se não há vendedor, mantém None (não aplicável)

    # Status final
    if not grupo_ok:
        reg.status = 'ERRO'
    elif reg.enviado_vendedor is False:
        reg.status = 'PARCIAL'
    else:
        reg.status = 'ENVIADO'

    reg.enviado_em = agora_utc_naive()


# ─── Processamento principal ──────────────────────────────────────────────────

def processar_notificacao(registro_id: int) -> None:
    """Processa uma notificação WhatsApp para pedido ou NFe.

    Ponto de entrada chamado pelo worker RQ (H3). Idempotente: flags
    enviado_grupo/enviado_vendedor impedem reenvio em caso de retry.

    Args:
        registro_id: ID de HoraTagPlusNotificacaoWhatsapp.
    """
    from app import db
    from app.hora.models.tagplus import HoraTagPlusNotificacaoWhatsapp

    reg = db.session.get(HoraTagPlusNotificacaoWhatsapp, registro_id)
    if not reg:
        logger.error('HORA notificacao: registro %s não encontrado', registro_id)
        return

    reg.status = 'PROCESSANDO'
    reg.tentativas = (reg.tentativas or 0) + 1
    db.session.commit()

    # Kill switch global
    enabled = os.environ.get('HORA_TAGPLUS_NOTIFY_ENABLED', 'true').strip().lower()
    if enabled in ('false', '0', 'no'):
        reg.status = 'IGNORADO'
        reg.erro = 'HORA_TAGPLUS_NOTIFY_ENABLED desabilitado'
        db.session.commit()
        return

    anexo_b64 = None
    anexo_filename = None

    try:
        if reg.tipo == 'NFE':
            emissao = _carregar_nfe(reg.ref_id)
            if not emissao:
                reg.status = 'ERRO'
                reg.erro = f'HoraTagPlusNfeEmissao {reg.ref_id} não encontrada'
                db.session.commit()
                return

            venda = getattr(emissao, 'venda', None)

            # Preenche metadados do registro
            reg.numero = getattr(emissao, 'numero_nfe', None)
            reg.cliente_nome = venda.nome_cliente if venda else None
            reg.valor = venda.valor_total if venda else None
            reg.vendedor_nome = venda.vendedor if venda else None
            reg.loja_nome = (
                venda.loja.nome
                if venda and getattr(venda, 'loja', None)
                else None
            )

            texto = _formatar_nfe(venda, emissao)

            pdf = _baixar_danfe_pdf(emissao)
            if pdf:
                nfe_ref = getattr(emissao, 'numero_nfe', None) or getattr(emissao, 'tagplus_nfe_id', registro_id)
                anexo_b64 = base64.b64encode(pdf).decode()
                anexo_filename = f'danfe_{nfe_ref}.pdf'
                reg.anexou_pdf = True

        elif reg.tipo == 'PEDIDO':
            venda = _carregar_pedido(reg.ref_id)
            if not venda:
                reg.status = 'ERRO'
                reg.erro = f'HoraVenda {reg.ref_id} não encontrada'
                db.session.commit()
                return

            # Preenche metadados do registro
            reg.numero = str(venda.id)
            reg.cliente_nome = venda.nome_cliente
            reg.valor = venda.valor_total
            reg.vendedor_nome = venda.vendedor
            reg.loja_nome = (
                venda.loja.nome
                if getattr(venda, 'loja', None)
                else None
            )

            texto = _formatar_pedido(venda)
            # Pedido não tem PDF

        else:
            reg.status = 'ERRO'
            reg.erro = f'Tipo desconhecido: {reg.tipo}'
            db.session.commit()
            return

        vendedor = _resolver_vendedor(reg.vendedor_nome)
        _enviar_para_destinos(reg, texto, anexo_b64, anexo_filename, vendedor)
        db.session.commit()

    except Exception as exc:
        logger.exception('HORA notificacao: erro inesperado ao processar %s', registro_id)
        try:
            reg.status = 'ERRO'
            reg.erro = str(exc)[:300]
            db.session.commit()
        except Exception:
            pass


# ─── Enfileiramento ───────────────────────────────────────────────────────────

def enfileirar_notificacao(tipo: str, ref_id: int) -> None:
    """Cria ou reutiliza registro de notificação e enfileira no RQ.

    Idempotente: se já existe registro ENVIADO, ignora. Se existe em outro
    status, reutiliza para retry. Se não existe, cria novo PENDENTE.

    Não propaga exceções — não pode quebrar o caller (webhook / confirmar_venda).

    Args:
        tipo: 'PEDIDO' ou 'NFE'.
        ref_id: ID da HoraVenda (PEDIDO) ou HoraTagPlusNfeEmissao (NFE).
    """
    try:
        from app import db
        from app.hora.models.tagplus import HoraTagPlusNotificacaoWhatsapp

        reg = (
            HoraTagPlusNotificacaoWhatsapp.query
            .filter_by(tipo=tipo, ref_id=ref_id)
            .first()
        )

        if reg and reg.status == 'ENVIADO':
            logger.info('HORA notificacao: %s/%s já enviado, ignorando', tipo, ref_id)
            return

        if not reg:
            reg = HoraTagPlusNotificacaoWhatsapp(tipo=tipo, ref_id=ref_id, status='PENDENTE')
            db.session.add(reg)
            db.session.commit()

        registro_id = reg.id

        # Enfileira na fila hora_nfe
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            from rq import Queue
            from redis import Redis

            Queue(QUEUE_NAME, connection=Redis.from_url(redis_url)).enqueue(
                'app.hora.workers.emissao_nfe_worker.processar_notificacao',
                registro_id,
            )
        else:
            # Fallback síncrono (dev sem Redis)
            logger.info('HORA notificacao: sem REDIS_URL, processando sincronamente')
            processar_notificacao(registro_id)

    except Exception as exc:
        logger.exception('HORA notificacao: falha ao enfileirar notificacao %s/%s: %s',
                         tipo, ref_id, exc)


def reenfileirar(registro_id: int) -> None:
    """Reseta status para PENDENTE e reenfileira o job no RQ.

    Usado pelo reenvio manual da tela de histórico (H4). Sempre reenfileira
    independentemente do status atual (força retry mesmo em ENVIADO).

    Não propaga exceções — loga e segue.

    Args:
        registro_id: ID de HoraTagPlusNotificacaoWhatsapp.
    """
    try:
        from app import db
        from app.hora.models.tagplus import HoraTagPlusNotificacaoWhatsapp

        reg = db.session.get(HoraTagPlusNotificacaoWhatsapp, registro_id)
        if not reg:
            logger.error('HORA notificacao reenfileirar: registro %s não encontrado', registro_id)
            return

        reg.status = 'PENDENTE'
        reg.erro = None
        db.session.commit()

        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            from rq import Queue
            from redis import Redis

            Queue(QUEUE_NAME, connection=Redis.from_url(redis_url)).enqueue(
                'app.hora.workers.emissao_nfe_worker.processar_notificacao',
                registro_id,
            )
        else:
            # Fallback síncrono (dev sem Redis)
            logger.info('HORA notificacao: sem REDIS_URL, processando sincronamente')
            processar_notificacao(registro_id)

    except Exception as exc:
        logger.exception('HORA notificacao: falha ao reenfileirar %s: %s', registro_id, exc)
