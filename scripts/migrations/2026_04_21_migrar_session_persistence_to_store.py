"""
Migration historica: sdk_session_transcript (TEXT) → claude_session_store (JSONB).

Parseia o blob JSONL em agent_sessions.sdk_session_transcript linha-a-linha e
popula o novo SessionStore via claude_agent_sdk 0.1.64. Pre-requisito para
Fase B (remocao session_persistence.py) — sem isso, sessions pre-existentes
perdem contexto no primeiro turno pos-cutover.

Idempotente: skipa sessions que ja tem entries no store.

NAO roda em build.sh (pode demorar 10-60min dependendo do volume). Executar
manualmente no Render Shell pos-deploy:

    python scripts/migrations/2026_04_21_migrar_session_persistence_to_store.py

Volumetria esperada (estado em 2026-04-21):
- 434 total sessions; ~250 com sdk_session_transcript populado
- Tamanho medio 100KB, p99 2.1MB, total ~63MB
- Numero medio de entries por session: ~100-300
- Estimativa: 30k-75k INSERTs; ~5-15min em Render Starter PG

Progresso logado a cada 10 sessions.

FONTES:
- /tmp/subagent-findings/20260421-sessionstore-60ddbe70/phase3/plan-v2-final.md
- app/agente/sdk/session_store_adapter.py (_prepare_dsn, _IDENT_RE)
"""
import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import List, Optional

# Adiciona raiz do projeto ao sys.path quando script e executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('migrar_session_store')


def _prepare_dsn(url: str) -> str:
    """Copia de session_store_adapter._prepare_dsn (evita import Flask)."""
    url = re.sub(r"[?&]client_encoding=[^&]*", "", url)
    url = re.sub(r"[?&]options=[^&]*", "", url)
    url = re.sub(r"\?&", "?", url).rstrip("?").rstrip("&")
    return url


def _parse_jsonl(blob: str) -> List[dict]:
    """Parseia blob JSONL linha-a-linha. Skipa linhas invalidas com warning."""
    entries: List[dict] = []
    for lineno, raw in enumerate(blob.splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                entries.append(parsed)
            else:
                logger.warning(f"[parse] linha {lineno} nao e dict: {type(parsed).__name__}")
        except json.JSONDecodeError as e:
            logger.warning(f"[parse] linha {lineno} invalida: {e}")
    return entries


async def migrate(
    dry_run: bool = False,
    project_key_override: Optional[str] = None,
) -> int:
    """Executa migracao. Retorna exit code (0=ok).

    Args:
        dry_run: se True, nao faz INSERTs, so reporta o que faria.
        project_key_override: se setado, usa esse project_key em vez de derivar do cwd.
            CRITICO: as sessions no store do Render foram gravadas com cwd=
            `/opt/render/project/src` → project_key `-opt-render-project-src`.
            Rodar o script em dev local (cwd diferente) inseriria em project_key
            errado e criaria duplicatas conceituais. Solucao: rodar no Render
            Shell (cwd correto ja), OU passar `--project-key -opt-render-project-src`.
    """
    import asyncpg

    from claude_agent_sdk import project_key_for_directory

    dsn_raw = os.environ.get("DATABASE_URL")
    if not dsn_raw:
        logger.error("DATABASE_URL nao definido")
        return 1

    dsn = _prepare_dsn(dsn_raw)
    # Project key: override > cwd atual.
    # Em Render o cwd e /opt/render/project/src.
    # Em dev local e /home/rafaelnascimento/projetos/frete_sistema.
    if project_key_override:
        project_key = project_key_override
        logger.info(f"[start] project_key OVERRIDE={project_key}  dry_run={dry_run}")
    else:
        project_key = project_key_for_directory()
        logger.info(f"[start] project_key (cwd)={project_key}  dry_run={dry_run}")

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3, command_timeout=60)
    try:
        # 1. Descobre sessions com transcript legado
        rows = await pool.fetch("""
            SELECT
                session_id AS our_uuid,
                data->>'sdk_session_id' AS sdk_sid,
                sdk_session_transcript AS blob,
                length(sdk_session_transcript) AS blob_len
            FROM agent_sessions
            WHERE sdk_session_transcript IS NOT NULL
              AND length(sdk_session_transcript) > 0
            ORDER BY updated_at DESC
        """)
        total = len(rows)
        logger.info(f"[discover] {total} sessions com transcript legado")

        if total == 0:
            logger.info("[done] nenhuma sessao a migrar")
            return 0

        # 2. Migrar
        migrated = 0
        skipped_already = 0
        skipped_invalid_sid = 0
        skipped_no_entries = 0
        errored = 0
        total_entries = 0
        start_ts = time.time()

        UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

        for i, row in enumerate(rows, start=1):
            our_uuid = row['our_uuid']
            sdk_sid = row['sdk_sid']
            blob = row['blob']
            blob_len = row['blob_len']

            # O store usa sdk_session_id como session_id (nome do JSONL).
            # Fallback: our_uuid (SDK 0.1.52+ usa our_session_id como sdk_session_id se UUID valido).
            store_sid = sdk_sid or our_uuid
            if not store_sid or not UUID_RE.match(store_sid):
                logger.warning(
                    f"[{i}/{total}] skip — sdk_session_id invalido: "
                    f"our_uuid={our_uuid} sdk_sid={sdk_sid!r}"
                )
                skipped_invalid_sid += 1
                continue

            # Idempotencia: skip se ja tem entries no store (nao tentar deduplicar)
            already = await pool.fetchval("""
                SELECT 1 FROM claude_session_store
                WHERE project_key = $1 AND session_id = $2 AND subpath = ''
                LIMIT 1
            """, project_key, store_sid)
            if already:
                skipped_already += 1
                if i % 20 == 0:
                    logger.info(
                        f"[{i}/{total}] progresso: migrated={migrated} "
                        f"skipped_already={skipped_already} "
                        f"entries={total_entries}"
                    )
                continue

            # Parsear JSONL
            entries = _parse_jsonl(blob)
            if not entries:
                logger.warning(
                    f"[{i}/{total}] skip — blob vazio/invalido: "
                    f"our_uuid={our_uuid} len={blob_len}"
                )
                skipped_no_entries += 1
                continue

            if dry_run:
                migrated += 1
                total_entries += len(entries)
                logger.info(
                    f"[{i}/{total}] DRY — migraria "
                    f"{len(entries)} entries: sdk_sid={store_sid[:12]}..."
                )
                continue

            # Insert (mesmo SQL do adapter — unnest WITH ORDINALITY preserva ordem)
            try:
                await pool.execute(f"""
                    INSERT INTO claude_session_store
                        (project_key, session_id, subpath, entry, mtime)
                    SELECT $1, $2, '', e,
                           (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint
                    FROM unnest($3::jsonb[]) WITH ORDINALITY AS t(e, ord)
                    ORDER BY ord
                """,
                    project_key,
                    store_sid,
                    [json.dumps(e) for e in entries],
                )
                migrated += 1
                total_entries += len(entries)
                if i % 10 == 0 or i == total:
                    elapsed = time.time() - start_ts
                    rate = total_entries / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"[{i}/{total}] migrated={migrated} "
                        f"skipped_already={skipped_already} "
                        f"entries={total_entries} "
                        f"rate={rate:.0f}/s"
                    )
            except Exception as e:
                errored += 1
                logger.error(
                    f"[{i}/{total}] erro migrando {our_uuid}: {e}",
                    exc_info=False,
                )

        # 3. Relatorio
        elapsed = time.time() - start_ts
        logger.info(f"[done] tempo={elapsed:.1f}s")
        logger.info(f"[done] migrated={migrated}/{total}")
        logger.info(f"[done] skipped_already={skipped_already}")
        logger.info(f"[done] skipped_invalid_sid={skipped_invalid_sid}")
        logger.info(f"[done] skipped_no_entries={skipped_no_entries}")
        logger.info(f"[done] errored={errored}")
        logger.info(f"[done] total_entries_inserted={total_entries}")

        # 4. Verificacao pos-migracao
        if not dry_run:
            verify = await pool.fetchval("""
                SELECT COUNT(DISTINCT session_id)
                FROM claude_session_store
                WHERE project_key = $1 AND subpath = ''
            """, project_key)
            logger.info(f"[verify] claude_session_store tem {verify} sessions em project_key={project_key!r}")

        if errored > 0:
            logger.warning(f"[done] {errored} sessions com erro — revisar logs")
            return 2
        return 0
    finally:
        await pool.close()


def main():
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    # Parse --project-key=<key>
    project_key_override: Optional[str] = None
    for arg in sys.argv[1:]:
        if arg.startswith('--project-key='):
            project_key_override = arg.split('=', 1)[1]
            break
        if arg == '--project-key':
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                project_key_override = sys.argv[idx + 1]
                break

    if dry_run:
        logger.info("=" * 60)
        logger.info("MODO DRY-RUN — nenhum INSERT sera feito")
        logger.info("=" * 60)
    exit_code = asyncio.run(migrate(
        dry_run=dry_run,
        project_key_override=project_key_override,
    ))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
