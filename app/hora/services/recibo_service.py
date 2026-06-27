"""Recibo Simples (documento NAO-fiscal) de pecas/oficina — roadmap #1b.

Gera, a partir de uma HoraVenda, um recibo das PECAS (motos saem com NFe).
Numeracao sequencial GLOBAL (sequence hora_recibo_numero_seq), PDF via
weasyprint persistido no S3, com envio por e-mail (reusa EmailSender) e
WhatsApp (reusa whatsapp_notify). Coexiste com a NFe da venda.

Fronteira do modulo: reusa apenas utilitarios compartilhados (EmailSender,
whatsapp_notify, FileStorage) — nenhuma logica de modulo vizinho.
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Optional

from flask import render_template

from app import db
from app.utils.logging_config import logger
from app.utils.timezone import agora_utc_naive
from app.utils.file_storage import FileStorage
from app.hora.models import (
    HoraRecibo, HoraVenda, RECIBO_STATUS_EMITIDO, RECIBO_STATUS_CANCELADO,
)


class ReciboError(Exception):
    """Erro de negocio na geracao/operacao de recibo (mensagem amigavel)."""


def _itens_peca(venda: HoraVenda) -> list:
    return list(getattr(venda, 'itens_peca', None) or [])


def _proximo_numero() -> int:
    """Proximo numero sequencial GLOBAL do recibo (via sequence dedicada)."""
    from sqlalchemy import text
    return int(db.session.execute(text("SELECT nextval('hora_recibo_numero_seq')")).scalar())


def _render_pdf_bytes(venda: HoraVenda, recibo: HoraRecibo) -> bytes:
    """Renderiza o HTML do recibo e converte para PDF (weasyprint)."""
    from weasyprint import HTML  # lazy import (custo de boot)
    html_str = render_template(
        'hora/imprimir_recibo.html',
        venda=venda,
        recibo=recibo,
        itens_peca=_itens_peca(venda),
    )
    return HTML(string=html_str).write_pdf()


def gerar_recibo(venda_id: int, usuario: Optional[str] = None) -> HoraRecibo:
    """Gera um Recibo Simples das pecas de uma venda. Retorna o HoraRecibo.

    Levanta ReciboError se a venda nao existir ou nao tiver pecas. O PDF e
    renderizado e enviado ao S3 (best-effort: se o S3 falhar, o recibo e criado
    sem pdf_s3_key e o PDF pode ser re-renderizado on demand em baixar_pdf_bytes).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ReciboError('Venda não encontrada.')

    itens = _itens_peca(venda)
    if not itens:
        raise ReciboError(
            'Recibo Simples cobre apenas peças/oficina — esta venda não tem peças.'
        )

    valor_total = sum((Decimal(str(ip.preco_final or 0)) for ip in itens), Decimal('0'))

    recibo = HoraRecibo(
        numero=_proximo_numero(),
        venda_id=venda.id,
        valor_total=valor_total,
        status=RECIBO_STATUS_EMITIDO,
        emitido_em=agora_utc_naive(),
        emitido_por=(usuario or '').strip()[:100] or None,
    )
    db.session.add(recibo)
    db.session.flush()  # garante recibo.id/numero para o PDF

    # PDF -> S3 (best-effort: nao bloqueia a emissao do recibo).
    try:
        pdf_bytes = _render_pdf_bytes(venda, recibo)
        storage = FileStorage()
        s3_key = storage.save_file(
            file=BytesIO(pdf_bytes),
            folder='hora/recibos',
            filename=f'{recibo.numero_display}.pdf',
        )
        recibo.pdf_s3_key = s3_key or None
    except Exception as exc:  # noqa: BLE001 — PDF/S3 nao deve impedir o recibo
        logger.warning('HORA recibo %s: falha ao gerar/subir PDF (best-effort): %s',
                       recibo.numero, exc)

    db.session.commit()
    logger.info('HORA recibo %s gerado para venda=%s valor=%s',
                recibo.numero_display, venda.id, valor_total)
    return recibo


def baixar_pdf_bytes(recibo_id: int) -> bytes:
    """Retorna os bytes do PDF do recibo (download do S3; fallback re-render)."""
    recibo = HoraRecibo.query.get(recibo_id)
    if not recibo:
        raise ReciboError('Recibo não encontrado.')

    if recibo.pdf_s3_key:
        conteudo = FileStorage().download_file(recibo.pdf_s3_key)
        if conteudo:
            return conteudo
        logger.warning('HORA recibo %s: PDF ausente no storage — re-renderizando',
                       recibo.numero)

    # Fallback: re-renderiza on-the-fly a partir da venda.
    venda = HoraVenda.query.get(recibo.venda_id)
    if not venda:
        raise ReciboError('Venda do recibo não encontrada para re-renderizar o PDF.')
    return _render_pdf_bytes(venda, recibo)


def enviar_recibo_email(
    recibo_id: int,
    usuario: Optional[str] = None,
    destinatario_override: Optional[str] = None,
) -> dict:
    """Envia o PDF do recibo por e-mail ao cliente. Levanta ReciboError em falha."""
    from app.hora.services.hora_email import HoraEmailConfig, hora_email_sender
    from app.hora.services.nf_email_service import NF_EMAIL_FROM, NF_EMAIL_FROM_NAME

    recibo = HoraRecibo.query.get(recibo_id)
    if not recibo:
        raise ReciboError('Recibo não encontrado.')
    venda = HoraVenda.query.get(recibo.venda_id)
    destinatario = (destinatario_override or (venda.email_cliente if venda else None) or '').strip()
    if not destinatario:
        raise ReciboError('Venda sem e-mail do cliente — preencha o e-mail antes de enviar.')
    if not HoraEmailConfig.is_configured():
        raise ReciboError('Envio de e-mail não configurado (variáveis HORA_EMAIL_* — falta HORA_EMAIL_PASSWORD).')

    pdf = baixar_pdf_bytes(recibo_id)
    filename = f'{recibo.numero_display}.pdf'
    nome = (venda.nome_cliente if venda else 'Cliente') or 'Cliente'
    corpo = (
        f'<div style="font-family: Arial, sans-serif; color:#333;">'
        f'<p>Olá, {nome}!</p>'
        f'<p>Segue em anexo o seu recibo <strong>{recibo.numero_display}</strong> '
        f'referente às peças/serviços da Motochefe SP.</p>'
        f'<p style="margin-top:20px; color:#666; font-size:12px;">'
        f'Documento não-fiscal. Motochefe SP.</p></div>'
    )
    resultado = hora_email_sender.send(
        to=destinatario,
        subject=f'Recibo {recibo.numero_display} — Motochefe SP',
        body_html=corpo,
        attachments=[(filename, pdf)],
        from_email=NF_EMAIL_FROM,
        from_name=NF_EMAIL_FROM_NAME,
    )
    if not resultado.get('success'):
        raise ReciboError(f'Falha no envio: {resultado.get("error") or "erro desconhecido"}')
    logger.info('HORA recibo %s enviado por e-mail para %s', recibo.numero_display, destinatario)
    return {'destinatario': destinatario, 'numero': recibo.numero_display}


def enviar_recibo_whatsapp(
    recibo_id: int,
    usuario: Optional[str] = None,
    telefone_override: Optional[str] = None,
) -> dict:
    """Envia o PDF do recibo por WhatsApp ao cliente. Levanta ReciboError em falha."""
    import base64
    from app.utils.whatsapp_dispatch import send_whatsapp_unificado

    recibo = HoraRecibo.query.get(recibo_id)
    if not recibo:
        raise ReciboError('Recibo não encontrado.')
    venda = HoraVenda.query.get(recibo.venda_id)
    telefone = (telefone_override or (venda.telefone_cliente if venda else None) or '').strip()
    if not telefone:
        raise ReciboError('Venda sem telefone do cliente — preencha antes de enviar por WhatsApp.')

    pdf = baixar_pdf_bytes(recibo_id)
    nome = (venda.nome_cliente if venda else 'Cliente') or 'Cliente'
    texto = (
        f'Olá, {nome}! Segue o seu recibo {recibo.numero_display} '
        f'(peças/serviços) — Motochefe SP. Documento não-fiscal.'
    )
    resp = send_whatsapp_unificado(
        telefone, texto,
        anexo_b64=base64.b64encode(pdf).decode('ascii'),
        anexo_filename=f'{recibo.numero_display}.pdf',
    )
    if not resp.get('ok'):
        raise ReciboError(f'Falha no envio por WhatsApp: {resp}')
    logger.info('HORA recibo %s enviado por WhatsApp para %s', recibo.numero_display, telefone)
    return {'telefone': telefone, 'numero': recibo.numero_display}


def cancelar_recibo(recibo_id: int, usuario: Optional[str] = None,
                    motivo: Optional[str] = None) -> HoraRecibo:
    """Cancela (anula) um recibo emitido. Idempotente para ja cancelados."""
    recibo = HoraRecibo.query.get(recibo_id)
    if not recibo:
        raise ReciboError('Recibo não encontrado.')
    if recibo.status == RECIBO_STATUS_CANCELADO:
        return recibo
    recibo.status = RECIBO_STATUS_CANCELADO
    recibo.cancelado_em = agora_utc_naive()
    recibo.cancelado_por = (usuario or '').strip()[:100] or None
    recibo.cancelamento_motivo = (motivo or '').strip()[:500] or None
    db.session.commit()
    return recibo
