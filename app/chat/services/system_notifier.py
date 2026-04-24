"""SystemNotifier — API publica para qualquer ponto do codigo disparar alerta."""
from typing import List, Optional

from app import db
from app.chat.models import ChatAttachment, ChatMessage
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
        attachments: Optional[List[dict]] = None,
    ):
        """
        Dispara alerta do sistema para um ou mais usuarios.

        Cada usuario recebe na sua 'caixa de entrada' system_dm (criada lazy).
        Publica via SSE para entrega imediata se conectado.

        Args:
            attachments: lista opcional de dicts com
                {s3_key, filename, mime_type, size_bytes}.
                Cada anexo vira um `ChatAttachment` vinculado a TODAS as
                mensagens disparadas (mesmo S3 key, sem re-upload).
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

        # Pass 1: garantir que TODAS as threads existem antes de inserir msgs.
        # ThreadService.get_or_create_system_dm faz commit interno ao criar —
        # thread vazia e benigna se pass 2 falhar (proximo alert reutiliza).
        threads_by_user = {u.id: ThreadService.get_or_create_system_dm(u) for u in users}

        # Pass 2: inserir TODAS as mensagens em transacao unica (atomico).
        # Se falhar no meio, rollback desfaz msgs nao-commitadas; threads do pass 1
        # permanecem como caixas vazias reutilizaveis.
        msgs = []
        for u in users:
            thread = threads_by_user[u.id]
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
            # Anexos: 1 ChatAttachment por anexo por mensagem.
            for att in (attachments or []):
                db.session.add(ChatAttachment(
                    message_id=msg.id,
                    s3_key=att['s3_key'],
                    filename=att['filename'],
                    mime_type=att['mime_type'],
                    size_bytes=att['size_bytes'],
                ))
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
