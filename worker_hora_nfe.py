"""RQ worker dedicado a emissao de NFe HORA via TagPlus.

Queue: `hora_nfe`. Comando para rodar (Render ou local):

    python worker_hora_nfe.py

Variaveis de ambiente obrigatorias:
    REDIS_URL                 (URL do Redis)
    HORA_TAGPLUS_ENC_KEY      (Fernet key para encriptar tokens/secrets)

Logs em STDOUT (formato compativel com Render).
"""
import logging
import os
import sys

# Garante import de app.* a partir da raiz do projeto.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis import Redis  # noqa: E402
from rq import Connection, Queue, Worker  # noqa: E402

from app import create_app  # noqa: E402


def main() -> None:
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
    )
    log = logging.getLogger('worker_hora_nfe')

    app = create_app()
    with app.app_context():
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            log.error('REDIS_URL nao configurado — abortando.')
            sys.exit(1)

        redis_conn = Redis.from_url(redis_url)
        log.info('worker_hora_nfe conectado em %s; consumindo queue=hora_nfe', redis_url)

        with Connection(redis_conn):
            worker = Worker([Queue('hora_nfe')])
            worker.work()


if __name__ == '__main__':
    main()
