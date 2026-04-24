"""
Task 21 — hook de notificacao de recebimento finalizado.

Dispara alerta do sistema quando um RecebimentoLf conclui (ok ou erro).
Chamado pelo worker recebimento_lf_jobs.py nos pontos de finalizacao.

Uso (workers/recebimento_lf_jobs.py, apos transfer_status ser definido):

    from app.chat.hooks.recebimento import notify_recebimento_finalizado
    try:
        notify_recebimento_finalizado(recebimento)
    except Exception as e:
        logger.error(f'[CHAT hook] notify falhou: {e}', exc_info=True)

SEMPRE proteger com try/except — alerta nao pode quebrar o worker.
"""
from typing import List, Optional

from sqlalchemy import select

from app import db
from app.auth.models import Usuario
from app.chat.services.system_notifier import SystemNotifier
from app.utils.logging_config import logger


def _get_recebimento_operators(_recebimento=None) -> List[int]:
    """Lista de user_ids que devem receber alerta de recebimento.

    MVP: operadores com `sistema_logistica=True` OU administradores.
    Futuro: tabela dedicada de destinatarios por tipo de evento (parametro
    `_recebimento` fica reservado para decidir destinatarios por company_id).
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


def notify_recebimento_finalizado(recebimento, destinatarios: Optional[List[int]] = None):
    """Envia alerta do sistema ao concluir recebimento.

    Args:
        recebimento: instancia de RecebimentoLf com status/transfer_status setados
        destinatarios: opcional — lista de user_ids. Se None, deriva de flags.

    Nao levanta excecoes — loga e engolе falhas.
    """
    try:
        if destinatarios is None:
            destinatarios = _get_recebimento_operators(_recebimento=recebimento)
        if not destinatarios:
            logger.warning(
                f'[CHAT hook] sem destinatarios para recebimento {recebimento.id}'
            )
            return

        status = getattr(recebimento, 'transfer_status', None) or recebimento.status
        if status == 'erro':
            titulo = f'Recebimento #{recebimento.id} concluiu com ERRO'
            nivel = 'CRITICO'
        else:
            titulo = f'Recebimento #{recebimento.id} concluido'
            nivel = 'INFO'

        nf = getattr(recebimento, 'numero_nf', None) or '-'
        erro_msg = getattr(recebimento, 'transfer_erro_mensagem', None) or ''
        content_lines = [f'NF {nf} — status: {status}']
        if erro_msg and status == 'erro':
            content_lines.append(f'Erro: {erro_msg[:200]}')
        content = '\n'.join(content_lines)

        SystemNotifier.alert(
            user_ids=destinatarios,
            source='recebimento',
            titulo=titulo,
            content=content,
            deep_link=f'/recebimento/{recebimento.id}',
            nivel=nivel,
            dados={
                'recebimento_id': recebimento.id,
                'nf': nf,
                'status': status,
            },
        )
        logger.info(
            f'[CHAT hook] notify_recebimento_finalizado: id={recebimento.id} '
            f'status={status} destinatarios={len(destinatarios)}'
        )
    except Exception as e:
        logger.error(f'[CHAT hook] notify_recebimento_finalizado falhou: {e}', exc_info=True)
