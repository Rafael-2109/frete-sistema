"""RQ worker dedicado a tarefas HORA: emissao de NFe via TagPlus + import via imagem.

Queues consumidas:
    hora_nfe              — emissao/cancelamento/cce de NFe via TagPlus
    hora_pedidos_imagem   — geracao de XLSX equivalente para pedido criado via imagem (OCR)

Comando para rodar (Render ou local):

    python worker_hora_nfe.py

Variaveis de ambiente obrigatorias:
    REDIS_URL                 (URL do Redis)
    HORA_TAGPLUS_ENC_KEY      (Fernet key para encriptar tokens/secrets — necessaria para hora_nfe)

Variaveis opcionais (necessarias para hora_pedidos_imagem):
    ANTHROPIC_API_KEY         (so necessaria no parser na rota; o worker
                                que GERA XLSX a partir do pedido ja persistido
                                NAO usa Anthropic — usa apenas openpyxl + S3)

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
        queues = ['hora_nfe', 'hora_pedidos_imagem']
        log.info(
            'worker_hora_nfe conectado em %s; consumindo queues=%s',
            redis_url, queues,
        )

        with Connection(redis_conn):
            worker = Worker([Queue(name) for name in queues])
            worker.work()


if __name__ == '__main__':
    main()
