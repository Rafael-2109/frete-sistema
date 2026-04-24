"""
Task 22 — hook de notificacao de DFE bloqueado (Fase 2 recebimento).

Dispara alerta quando validacao NF vs PO gera bloqueio. Chamado pelo
job/service de validacao fiscal nos pontos onde o bloqueio e criado.

Uso (app/recebimento/services/odoo_po_service.py ou similar, ao criar divergencia):

    from app.chat.hooks.dfe_bloqueado import notify_dfe_bloqueado
    try:
        notify_dfe_bloqueado(
            dfe_id=dfe.id,
            nf_numero=dfe.numero_nf,
            motivo='Divergencia de preco no item 3',
        )
    except Exception as e:
        logger.error(f'[CHAT hook] dfe bloqueado notify falhou: {e}')
"""
from typing import List, Optional

from sqlalchemy import select

from app import db
from app.auth.models import Usuario
from app.chat.services.system_notifier import SystemNotifier
from app.utils.logging_config import logger


def _get_recebimento_operators() -> List[int]:
    """Operadores de recebimento (mesma logica do hook de recebimento).

    Futuro: lista dedicada por tipo de evento DFE.
    """
    operadores = db.session.execute(
        select(Usuario.id).where(
            Usuario.status == 'ativo',
            db.or_(
                Usuario.sistema_logistica.is_(True),
                Usuario.perfil == 'administrador',
            ),
        )
    ).scalars().all()
    return list(operadores)


def notify_dfe_bloqueado(
    dfe_id: int,
    nf_numero: str,
    motivo: str,
    fornecedor: Optional[str] = None,
    destinatarios: Optional[List[int]] = None,
):
    """Envia alerta ATENCAO ao criar bloqueio de DFE.

    Nao levanta excecoes — loga e engolе.
    """
    try:
        if destinatarios is None:
            destinatarios = _get_recebimento_operators()
        if not destinatarios:
            logger.warning(f'[CHAT hook] sem destinatarios para DFE bloqueado {dfe_id}')
            return

        titulo = f'DFE bloqueado: NF {nf_numero}'
        content_lines = [f'Motivo: {motivo[:500]}']
        if fornecedor:
            content_lines.insert(0, f'Fornecedor: {fornecedor}')
        content = '\n'.join(content_lines)

        SystemNotifier.alert(
            user_ids=destinatarios,
            source='dfe',
            titulo=titulo,
            content=content,
            deep_link=f'/recebimento/dfe/{dfe_id}',
            nivel='ATENCAO',
            dados={
                'dfe_id': dfe_id,
                'nf_numero': nf_numero,
                'motivo': motivo,
                'fornecedor': fornecedor,
            },
        )
        logger.info(
            f'[CHAT hook] notify_dfe_bloqueado: dfe={dfe_id} nf={nf_numero} '
            f'destinatarios={len(destinatarios)}'
        )
    except Exception as e:
        logger.error(f'[CHAT hook] notify_dfe_bloqueado falhou: {e}', exc_info=True)
