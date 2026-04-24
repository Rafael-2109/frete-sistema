"""SystemNotifier — API publica para qualquer ponto do codigo disparar alerta."""
from typing import List, Optional

from app import db
from app.chat.models import ChatMessage
from app.chat.services.thread_service import ThreadService
from app.utils.json_helpers import sanitize_for_json
from app.utils.logging_config import logger


VALID_NIVEIS = {'INFO', 'ATENCAO', 'CRITICO'}


class SystemNotifier:

    @staticmethod
    def alert(
        user_ids: List[int],
        source: str,
        titulo: str,
        content: str,
        deep_link: Optional[str] = None,
        nivel: str = 'INFO',
        dados: Optional[dict] = None,
    ):
        """
        Dispara alerta do sistema para um ou mais usuarios.

        Cada usuario recebe na sua 'caixa de entrada' system_dm (criada lazy).
        Publica via SSE para entrega imediata se conectado.
        """
        if nivel not in VALID_NIVEIS:
            raise ValueError(f'nivel invalido: {nivel}')

        from app.auth.models import Usuario
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        if not users:
            logger.warning(f'[CHAT] SystemNotifier: nenhum usuario encontrado em {user_ids}')
            return []

        body = f'**{titulo}**\n\n{content}'
        payload_dados = sanitize_for_json(dados or {})

        msgs = []
        for u in users:
            thread = ThreadService.get_or_create_system_dm(u)
            msg = ChatMessage(
                thread_id=thread.id,
                sender_type='system',
                sender_system_source=source,
                content=body,
                deep_link=deep_link,
                nivel=nivel,
                dados=payload_dados,
            )
            db.session.add(msg)
            db.session.flush()
            thread.last_message_at = msg.criado_em
            msgs.append((u, thread, msg))

        db.session.commit()

        # Publicar fora da transacao (best-effort)
        from app.chat.realtime.publisher import publish
        for u, thread, msg in msgs:
            publish(u.id, 'message_new', {
                'thread_id': thread.id,
                'message_id': msg.id,
                'preview': titulo,
                'sender_type': 'system',
                'source': source,
                'nivel': nivel,
                'deep_link': deep_link,
                'criado_em': msg.criado_em.isoformat() if msg.criado_em else None,
            })

        logger.info(
            f'[CHAT] SystemNotifier: {len(msgs)} alertas disparados '
            f'(source={source}, nivel={nivel})'
        )
        return msgs
