"""Helper de logging de boot — silenciavel via env NACOM_QUIET_BOOT.

Motivacao (BUG #1, 2026-06-08): varios modulos imprimem diagnosticos de boot
(`✅ Tipos PostgreSQL registrados`, `⚠️ ADAPTER ATIVO`, etc.) em escopo de
modulo — executam no `import app`, ANTES de `create_app()`. Quando o Agente Web
roda um script de skill via Bash, esses prints poluem o output capturado
(stdout + stderr juntos), atrapalhando o parsing do resultado.

Regras:
- `boot_log()` escreve SEMPRE em `sys.stderr` (NUNCA em stdout — stdout e
  reservado ao resultado de scripts CLI). Isso ja corrige o vazamento de
  `app/database/__init__.py`, que imprimia em stdout real.
- Silenciavel via `NACOM_QUIET_BOOT` (1/true/yes/on). O hook PreToolUse do
  agente (`app/agente/sdk/hooks.py`) seta essa env em todo comando Bash, de modo
  que o boot dos scripts roda quieto no contexto do agente. Em dev/PROD (gunicorn,
  worker, execucao manual) a env NAO esta setada -> os logs de boot aparecem
  normalmente.
- `force=True` ignora o silenciamento: para erros de boot que devem aparecer
  sempre, mesmo no contexto do agente.

Modulo PURO (apenas `os` + `sys`) — importavel ultra-cedo durante o boot, sem
disparar imports pesados nem ciclos.
"""
import os
import sys

_TRUTHY = {'1', 'true', 'yes', 'on'}


def _quiet() -> bool:
    return os.getenv('NACOM_QUIET_BOOT', '').strip().lower() in _TRUTHY


def boot_log(msg: str, *, force: bool = False) -> None:
    """Imprime diagnostico de boot em stderr, silenciavel por NACOM_QUIET_BOOT.

    Args:
        msg: mensagem a imprimir.
        force: se True, imprime mesmo com NACOM_QUIET_BOOT ligado (erros de boot).
    """
    if not force and _quiet():
        return
    print(msg, file=sys.stderr)
