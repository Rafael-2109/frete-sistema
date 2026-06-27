"""Envio da NF (DANFE PDF) por e-mail ao cliente — roadmap #4 (Lojas HORA).

Reusa, como utilitarios compartilhados:
  - `app/notificacoes/email_sender.py` (EmailSender generico, backend SMTP).
  - `_baixar_danfe_pdf` do fluxo de notificacao WhatsApp (mesmo modulo HORA).

Fronteira do modulo respeitada: nenhuma logica de negocio de modulos vizinhos
e importada — apenas o utilitario de envio e o download de DANFE ja usado pelo
HORA. Remetente fixo `financeiro@motochefesp.com.br` (conta Hostinger; env
`HORA_NF_EMAIL_FROM` permite sobrescrever). A conta SMTP autenticada (envs
EMAIL_*) deve ser a propria caixa `financeiro@` para o envelope bater com o From
(Hostinger rejeita From divergente do usuario autenticado).

Pre-condicoes para enviar:
  - venda FATURADA;
  - e-mail do cliente preenchido (ou destinatario_override);
  - emissao NFe APROVADA com PDF disponivel no TagPlus;
  - envio de e-mail configurado (envs EMAIL_*).

Toda tentativa (sucesso ou falha) e registrada em hora_venda_auditoria
(acao ENVIOU_NF_EMAIL) — "salvar historico" do roadmap.
"""
from __future__ import annotations

import os
from typing import Optional

from app.utils.logging_config import logger

NF_EMAIL_FROM = os.environ.get('HORA_NF_EMAIL_FROM', 'financeiro@motochefesp.com.br')
NF_EMAIL_FROM_NAME = os.environ.get('HORA_NF_EMAIL_FROM_NAME', 'Motochefe SP — Financeiro')


class NfEmailError(Exception):
    """Erro de negocio ao enviar a NF por e-mail (mensagem amigavel ao operador)."""


def _montar_corpo_html(venda, numero_nfe) -> str:
    """Monta o corpo HTML do e-mail da NF (estilo inline — e-mail, nao template)."""
    nome = (getattr(venda, 'nome_cliente', None) or 'Cliente').strip()
    return (
        '<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">'
        f'<p>Olá, {nome}!</p>'
        f'<p>Segue em anexo a sua Nota Fiscal <strong>nº {numero_nfe}</strong> '
        'referente à sua compra na Motochefe SP.</p>'
        '<p>Qualquer dúvida, estamos à disposição.</p>'
        '<p style="margin-top: 24px; color: #666; font-size: 13px;">'
        'Motochefe SP — Faturamento<br>'
        'Esta mensagem foi enviada automaticamente.</p>'
        '</div>'
    )


def enviar_nf_por_email(
    venda_id: int,
    usuario: Optional[str] = None,
    destinatario_override: Optional[str] = None,
) -> dict:
    """Envia a DANFE PDF da venda por e-mail ao cliente e registra auditoria.

    Levanta NfEmailError em pre-condicao nao satisfeita ou falha de envio.
    Retorna dict {destinatario, numero_nfe, message_id} em caso de sucesso.
    """
    from app import db
    from app.hora.models.venda import HoraVenda, VENDA_STATUS_FATURADO
    from app.hora.models.tagplus import NFE_STATUS_APROVADA
    from app.hora.services import venda_audit
    from app.hora.services.tagplus.notificacao_whatsapp import _baixar_danfe_pdf
    from app.notificacoes.email_sender import email_sender, EmailConfig

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise NfEmailError('Venda não encontrada.')

    destinatario = (destinatario_override or venda.email_cliente or '').strip()
    if not destinatario:
        raise NfEmailError(
            'Venda sem e-mail do cliente — preencha o e-mail no pedido antes de enviar.'
        )

    if venda.status != VENDA_STATUS_FATURADO:
        raise NfEmailError(
            f'A NF só pode ser enviada após o faturamento (status atual: {venda.status}).'
        )

    emissao = getattr(venda, 'emissao_nfe', None)
    if not emissao or emissao.status != NFE_STATUS_APROVADA or not emissao.tagplus_nfe_id:
        raise NfEmailError('NFe aprovada não encontrada para esta venda.')

    if not EmailConfig.is_configured():
        raise NfEmailError(
            'Envio de e-mail não configurado no servidor (variáveis EMAIL_* ausentes).'
        )

    pdf = _baixar_danfe_pdf(emissao)
    if not pdf:
        raise NfEmailError('Não foi possível obter a DANFE em PDF no TagPlus.')

    numero_nfe = emissao.numero_nfe or emissao.tagplus_nfe_id
    filename = f'NF_{numero_nfe}.pdf'
    assunto = f'Nota Fiscal {numero_nfe} — Motochefe SP'
    corpo_html = _montar_corpo_html(venda, numero_nfe)

    resultado = email_sender.send(
        to=destinatario,
        subject=assunto,
        body_html=corpo_html,
        attachments=[(filename, pdf)],
        from_email=NF_EMAIL_FROM,
        from_name=NF_EMAIL_FROM_NAME,
    )
    ok = bool(resultado.get('success'))

    # Historico/auditoria (roadmap #4) — registra tentativa de envio (sucesso/falha).
    detalhe = f'para={destinatario} nf={numero_nfe} status={"OK" if ok else "FALHA"}'
    if not ok:
        detalhe += f' erro={resultado.get("error")}'
    venda_audit.registrar_auditoria(
        venda_id=venda.id,
        usuario=usuario or '',
        acao='ENVIOU_NF_EMAIL',
        detalhe=detalhe[:500],
    )
    db.session.commit()

    if not ok:
        logger.warning('HORA NF e-mail: falha ao enviar venda=%s: %s',
                       venda.id, resultado.get('error'))
        raise NfEmailError(
            f'Falha no envio: {resultado.get("error") or "erro desconhecido"}'
        )

    logger.info('HORA NF e-mail: enviada venda=%s para=%s nf=%s',
                venda.id, destinatario, numero_nfe)
    return {
        'destinatario': destinatario,
        'numero_nfe': numero_nfe,
        'message_id': resultado.get('message_id'),
    }
