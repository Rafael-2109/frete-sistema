"""RQ worker job: gerar XLSX equivalente em background para pedido criado via imagem.

Quando um operador sobe imagem em /hora/pedidos/importar-imagem e confirma,
a rota cria HoraPedido com origem='IMAGEM' e enfileira este job na queue
`hora_pedidos_imagem`. O job:

  1. Carrega HoraPedido + itens + loja_destino.
  2. Valida idempotencia (job nao re-roda se XLSX ja foi gerado).
  3. Gera XLSX no formato canonico via pedido_xlsx_builder.
  4. Faz upload do XLSX ao S3 em `hora/pedidos/imagem-import/<id>.xlsx`.
  5. UPDATE hora_pedido SET xlsx_origem_s3_key, xlsx_origem_gerado_em.

O XLSX gerado e nice-to-have (auditoria) — falha aqui NAO trava o pedido.
Operador pode continuar usando o sistema normalmente; o botao de download
do XLSX equivalente fica oculto/grisaille no detalhe ate o job concluir.

Queue: `hora_pedidos_imagem`. Listener: `worker_hora_nfe.py` (escuta
multiplas queues — adicionado em 2026-05-08).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _ensure_app_context():
    """Garante app_context. RQ pode invocar fora do contexto Flask.

    Returns ctx se criou um novo contexto (caller deve fazer ctx.pop()), None caso contrario.
    """
    from flask import current_app
    try:
        current_app._get_current_object()  # noqa: SLF001
        return None
    except RuntimeError:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        return ctx


def gerar_xlsx_para_pedido_imagem_job(pedido_id: int) -> dict:
    """Gera XLSX equivalente para HoraPedido com origem='IMAGEM' e faz upload S3.

    Idempotente: se xlsx_origem_s3_key ja preenchido, retorna sem refazer.

    Args:
        pedido_id: id do HoraPedido criado via /pedidos/importar-imagem.

    Returns:
        Dict com {pedido_id, status, s3_key (se gerou), gerado_em (ISO)}.

    Levanta:
        - Nao levanta excecao para o caller — captura tudo e loga.
          Falha aqui nao deve travar a fila do RQ. Retorna status='erro'
          com message para inspecao.
    """
    ctx = _ensure_app_context()
    try:
        from app import db
        from app.hora.models import HoraPedido
        from app.hora.services.pedido_xlsx_builder import build_xlsx_de_pedido
        from app.utils.file_storage import FileStorage
        from app.utils.timezone import agora_utc_naive

        pedido = db.session.get(HoraPedido, pedido_id)
        if pedido is None:
            logger.warning('Pedido %s nao encontrado — job descartado.', pedido_id)
            return {'pedido_id': pedido_id, 'status': 'pedido_nao_encontrado'}

        if pedido.origem != 'IMAGEM':
            logger.info(
                'Pedido %s tem origem=%s (nao IMAGEM) — job descartado.',
                pedido_id, pedido.origem,
            )
            return {'pedido_id': pedido_id, 'status': 'origem_nao_imagem'}

        if pedido.xlsx_origem_s3_key:
            logger.info(
                'Pedido %s ja tem xlsx_origem_s3_key=%s — idempotente, descartando.',
                pedido_id, pedido.xlsx_origem_s3_key,
            )
            return {
                'pedido_id': pedido_id,
                'status': 'ja_gerado',
                's3_key': pedido.xlsx_origem_s3_key,
            }

        # Gera bytes do XLSX
        try:
            xlsx_bytes = build_xlsx_de_pedido(pedido)
        except ValueError as exc:
            logger.exception(
                'Falha ao gerar XLSX para pedido %s: %s', pedido_id, exc,
            )
            return {
                'pedido_id': pedido_id,
                'status': 'erro_build',
                'message': str(exc),
            }

        # Upload S3
        import io
        buf = io.BytesIO(xlsx_bytes)
        nome_xlsx = f'{pedido.numero_pedido}.xlsx'
        buf.name = nome_xlsx
        try:
            s3_key = FileStorage().save_file(
                buf,
                folder='hora/pedidos/imagem-import',
                filename=nome_xlsx,
                allowed_extensions=['xlsx'],
            )
        except Exception as exc:
            logger.exception(
                'Falha no upload S3 do XLSX para pedido %s: %s', pedido_id, exc,
            )
            return {
                'pedido_id': pedido_id,
                'status': 'erro_upload',
                'message': str(exc),
            }

        if not s3_key:
            logger.warning('FileStorage retornou s3_key vazio para pedido %s', pedido_id)
            return {
                'pedido_id': pedido_id,
                'status': 'erro_upload',
                'message': 's3_key vazio',
            }

        # Atualiza pedido
        agora = agora_utc_naive()
        pedido.xlsx_origem_s3_key = s3_key
        pedido.xlsx_origem_gerado_em = agora
        db.session.commit()

        logger.info(
            'XLSX gerado e uploaded para pedido %s: s3_key=%s',
            pedido_id, s3_key,
        )
        return {
            'pedido_id': pedido_id,
            'status': 'ok',
            's3_key': s3_key,
            'gerado_em': agora.isoformat(),
        }
    finally:
        if ctx is not None:
            ctx.pop()


def enfileirar_gerar_xlsx_para_pedido_imagem(pedido_id: int):
    """Enfileira o job na queue `hora_pedidos_imagem`. Retorna o job RQ.

    Caller (rota de confirmacao) deve chamar isto APOS o commit do
    HoraPedido para evitar race com a transacao do banco.

    Falha de Redis nao trava a criacao do pedido — caller deve tratar
    excecao e logar (pedido fica sem XLSX equivalente, mas usavel).
    """
    import os

    from redis import Redis
    from rq import Queue

    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        raise RuntimeError(
            'REDIS_URL ausente — fila hora_pedidos_imagem indisponivel'
        )

    redis_conn = Redis.from_url(redis_url)
    queue = Queue('hora_pedidos_imagem', connection=redis_conn)
    job = queue.enqueue(
        'app.hora.workers.pedido_imagem_worker.gerar_xlsx_para_pedido_imagem_job',
        pedido_id,
        job_timeout=120,
        result_ttl=3600,  # mantem resultado 1h para inspecao
        failure_ttl=86400,  # mantem falhas 24h
    )
    logger.info(
        'Job enfileirado: gerar XLSX para pedido %s (job_id=%s)',
        pedido_id, job.id,
    )
    return job
