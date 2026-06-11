"""Data-fix: backfill de ponteiros s3_archive_* para archives orfaos em S3.

Contexto (bug 2026-06-11): `_resolve_our_session_uuid` usava
`AgentSession.data['sdk_session_id'].astext`, mas a coluna `data` e declarada
como db.JSON GENERICO (models.py:65) cujo comparator NAO expoe `.astext`. O
hook _stop_hook SEMPRE passa o SDK ID efemero, entao o Caso 2 (resolucao via
data->>'sdk_session_id') estourava AttributeError -> o tar.gz era enviado ao S3
mas o ponteiro s3_archive_key NUNCA era gravado na AgentSession -> archive orfao.

Fix do codigo: session_archive.py (Caso 2 agora via SQL raw `->>`). Este script
reconcilia os archives JA criados orfaos: para cada .tar.gz em agent-archive/
sem ponteiro, resolve nosso UUID (via session_id OU data->>'sdk_session_id') e
grava os ponteiros usando LastModified/Size do proprio objeto S3.

Sem DDL — data fix Python only (UPDATE em agent_sessions.data JSONB).
Idempotente: sessao que ja tem s3_archive_key apontando para o arquivo e pulada.
NAO deleta nada do S3 (os 7 orfaos sem sessao no banco sao apenas reportados).

PROD: exportar DATABASE_URL=$DATABASE_URL_PROD + credenciais S3 antes de rodar.

Uso:
    python scripts/migrations/2026_06_11_backfill_s3_archive_orfaos.py            # dry-run
    python scripts/migrations/2026_06_11_backfill_s3_archive_orfaos.py --amostra 10
    python scripts/migrations/2026_06_11_backfill_s3_archive_orfaos.py --confirmar
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

S3_PREFIX = "agent-archive/"


def _listar_archives_s3():
    """Lista objetos em agent-archive/. Retorna lista de dicts {key,id,size,last_modified}."""
    import boto3
    bucket = os.environ.get("S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION")
    if not bucket:
        raise RuntimeError("S3_BUCKET_NAME ausente no ambiente")
    s3 = boto3.client("s3", region_name=region)
    paginator = s3.get_paginator("list_objects_v2")
    out = []
    for page in paginator.paginate(Bucket=bucket, Prefix=S3_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            base = key.rsplit("/", 1)[-1]
            if not base.endswith(".tar.gz"):
                continue
            out.append({
                "key": key,
                "id": base[: -len(".tar.gz")],
                "size": obj["Size"],
                # LastModified e' UTC tz-aware; normaliza p/ UTC naive isoformat
                # (mesmo padrao de agora_utc_naive() usado no codigo de producao)
                "last_modified": obj["LastModified"].replace(tzinfo=None).isoformat(),
            })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmar", action="store_true", help="aplica (default: dry-run)")
    parser.add_argument("--amostra", type=int, default=8, help="quantos antes/depois mostrar")
    args = parser.parse_args()

    from app import create_app, db
    from sqlalchemy import text as _sql_text
    from app.agente.sdk.session_archive import _resolve_our_session_uuid

    app = create_app()
    with app.app_context():
        archives = _listar_archives_s3()
        print(f"archives em {S3_PREFIX}: {len(archives)}")

        stats = {"ja_ok": 0, "backfilled": 0, "sem_sessao": 0}
        mostrados = 0

        for a in archives:
            key, sid, size, at = a["key"], a["id"], a["size"], a["last_modified"]

            # Idempotencia: ja existe sessao apontando para este arquivo?
            ja = db.session.execute(
                _sql_text(
                    "SELECT 1 FROM agent_sessions "
                    "WHERE data->>'s3_archive_key' = :k LIMIT 1"
                ),
                {"k": key},
            ).first()
            if ja is not None:
                stats["ja_ok"] += 1
                continue

            our_uuid = _resolve_our_session_uuid(sid)
            if not our_uuid:
                stats["sem_sessao"] += 1
                continue

            patch = {
                "s3_archive": key,
                "s3_archive_key": key,
                "s3_archive_at": at,
                "s3_archive_size": size,
            }

            if mostrados < args.amostra:
                mostrados += 1
                # session_id Teams compartilha prefixo longo entre janelas; o
                # sufixo (timestamp) e' o que distingue -> mostrar inicio + fim.
                sid_show = our_uuid if len(our_uuid) <= 50 else f"{our_uuid[:24]}...{our_uuid[-20:]}"
                print(f"[BACKFILL] arquivo={sid[:18]} -> session_id={sid_show}")
                print(f"           key={key}  size={size}B  at={at}")

            if args.confirmar:
                db.session.execute(
                    _sql_text("""
                        UPDATE agent_sessions
                        SET data = COALESCE(data, CAST('{}' AS jsonb))
                                   || CAST(:patch AS jsonb)
                        WHERE session_id = :sid
                    """),
                    {"sid": our_uuid, "patch": json.dumps(patch)},
                )
            stats["backfilled"] += 1

        if args.confirmar:
            db.session.commit()
            print("\nCOMMIT aplicado.")
        else:
            db.session.rollback()
            print("\nDRY-RUN — nada gravado.")

        print(
            f"resultado: ja_ok={stats['ja_ok']} backfilled={stats['backfilled']} "
            f"sem_sessao(orfao_irrecuperavel)={stats['sem_sessao']} total={len(archives)}"
        )


if __name__ == "__main__":
    main()
