"""
Supply Chain Workers — jobs RQ para processamento assincrono.

Reutiliza enqueue_job do app.portal.workers (wrapper central do projeto).
Jobs aqui sao fire-and-forget: falha no enqueue nao deve abortar a operacao
de negocio principal (graceful degradation).
"""
