"""Backfill UNIVERSAL de error_signature — passivo historico do loop corretivo pessoal.

CONTEXTO (dados PROD 2026-06-04): a captura organica de error_signature so passou a existir em
2026-06-02 22:36 (Fase 3.1/3.2 — coluna + clausula no extrator). Antes disso a coluna nem existia,
entao ~110 correcoes VIVAS de 15 usuarios ficaram SEM assinatura e, portanto, invisiveis ao
casamento de reincidencia (_track_signature_recurrence) e ao painel de contencao. Este script
generaliza o backfill hardcoded do Marcus (backfill_loop_corretivo_marcus.py, user 18) para
QUALQUER usuario: varre /memories/corrections/ vivas sem assinatura e gera a error_signature via
`gerar_error_signature` (Haiku + fallback deterministico, mesma instrucao do extrator).

DIFERENCA vs backfill do Marcus: NAO funde clusters nem promove a 'mandatory' — apenas ADICIONA a
assinatura que faltou (cirurgico, preserva tudo). Fusao/promocao seguem a cargo do batch diario
(correction_count) e do write-path.

SEGURANCA:
- `--dry-run` e o DEFAULT: lista o que seria assinado, NADA e escrito.
- `--confirmar` efetiva (write). IDEMPOTENTE: correcoes que ja tem assinatura nao sao candidatas
  (filtro error_signature IS NULL) -> re-rodar nao sobrescreve nem duplica.
- Roda no banco apontado por DATABASE_URL. PROD = Render Shell APOS GO do Rafael.
  Local (localhost) = teste seguro.

Uso:
    python scripts/backfill_signature_universal.py                  # DRY-RUN, todos os usuarios
    python scripts/backfill_signature_universal.py --user-id 1      # so user 1 (DRY-RUN)
    python scripts/backfill_signature_universal.py --confirmar      # EFETIVA (write, todos)
    python scripts/backfill_signature_universal.py --limit 20 --confirmar
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CORRECTIONS_LIKE = '/memories/corrections/%'


def _split_descricao_prescricao(content):
    """Extrai (descricao, prescricao) de '[tipo] descricao\\nDO: prescricao'.

    Robusto a formatos sem prefixo/sem 'DO:' (caminho B / admin_correction): retorna o texto
    inteiro como descricao e prescricao vazia.
    """
    if not content:
        return '', ''
    txt = re.sub(r'^\s*\[[^\]]+\]\s*', '', content.strip())
    desc, sep, presc = txt.partition('\nDO:')
    if not sep:
        desc, sep, presc = txt.partition('DO:')
    return desc.strip(), presc.strip()


def _candidatas_query(user_id=None, limit=None):
    """Correcoes VIVAS (nao cold, nao directory) SEM assinatura, em /memories/corrections/."""
    from app.agente.models import AgentMemory
    q = AgentMemory.query.filter(
        AgentMemory.path.like(CORRECTIONS_LIKE),
        AgentMemory.is_directory == False,   # noqa: E712
        AgentMemory.is_cold == False,        # noqa: E712
        AgentMemory.error_signature.is_(None),
    )
    if user_id is not None:
        q = q.filter(AgentMemory.user_id == user_id)
    q = q.order_by(AgentMemory.user_id, AgentMemory.id)
    if limit:
        q = q.limit(limit)
    return q


def backfill_signatures(*, user_id=None, dry_run=True, gerar_fn=None, limit=None, verbose=False):
    """Gera error_signature para correcoes vivas sem assinatura. Retorna stats (dict).

    gerar_fn(descricao, prescricao) -> str e' injetavel: testes mockam (deterministico, sem API);
    producao usa o helper Haiku. Idempotente, dry-run-first.
    """
    from app import db
    from app.agente.services.pattern_analyzer import gerar_error_signature
    gerar = gerar_fn or (lambda d, p: gerar_error_signature(d, p))

    candidatas = _candidatas_query(user_id=user_id, limit=limit).all()
    stats = {'candidatas': len(candidatas), 'assinadas': 0, 'sem_assinatura': 0, '_usuarios': set()}

    for mem in candidatas:
        desc, presc = _split_descricao_prescricao(mem.content)
        sig = (gerar(desc, presc) or '').strip()[:64]
        if not sig:
            stats['sem_assinatura'] += 1
            if verbose:
                print(f"  [SEM ASSINATURA] id={mem.id} user={mem.user_id} '{desc[:50]}'")
            continue
        stats['_usuarios'].add(mem.user_id)
        stats['assinadas'] += 1
        if verbose:
            marca = '[DRY]' if dry_run else '[OK] '
            print(f"  {marca} id={mem.id} user={mem.user_id} -> '{sig}'  ('{desc[:48]}')")
        if not dry_run:
            mem.error_signature = sig

    if not dry_run and stats['assinadas']:
        db.session.commit()

    stats['usuarios'] = len(stats.pop('_usuarios'))
    return stats


def main():
    ap = argparse.ArgumentParser(description="Backfill universal de error_signature (loop corretivo)")
    ap.add_argument('--confirmar', action='store_true', help="EFETIVA (write). Default = dry-run.")
    ap.add_argument('--user-id', type=int, default=None, help="Restringe a um usuario (default: todos)")
    ap.add_argument('--limit', type=int, default=None, help="Maximo de correcoes a processar")
    args = ap.parse_args()
    dry_run = not args.confirmar

    from app import create_app, db
    app = create_app()
    with app.app_context():
        # PRE-FLIGHT: a coluna error_signature precisa existir (migration 3.1 aplicada).
        from sqlalchemy import inspect as _sa_inspect
        cols = {c['name'] for c in _sa_inspect(db.engine).get_columns('agent_memories')}
        if 'error_signature' not in cols:
            print("[ABORTADO] coluna error_signature ausente no banco. "
                  "Rode antes: python scripts/migrations/2026_06_02_agent_memories_error_signature.py")
            sys.exit(2)

        modo = "DRY-RUN (nada sera escrito)" if dry_run else "CONFIRMAR (WRITE)"
        alvo = f"user {args.user_id}" if args.user_id is not None else "TODOS os usuarios"
        print(f"=== BACKFILL UNIVERSAL error_signature — {alvo} — MODO: {modo} ===")

        stats = backfill_signatures(user_id=args.user_id, dry_run=dry_run,
                                    limit=args.limit, verbose=True)

        print("\n--- RESUMO ---")
        print(f"  candidatas (sem assinatura): {stats['candidatas']}")
        print(f"  assinadas{' (seriam)' if dry_run else '':<9}: {stats['assinadas']}")
        print(f"  sem assinatura gerada:       {stats['sem_assinatura']}")
        print(f"  usuarios afetados:           {stats['usuarios']}")
        print("\n=== FIM ===" + ("" if not dry_run else " (rode com --confirmar para efetivar)"))


if __name__ == '__main__':
    main()
