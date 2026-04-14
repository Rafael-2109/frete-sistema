"""Backfill: popula carvia_historico_match_extrato a partir de conciliacoes existentes.

Varre todas `CarviaConciliacao` com `tipo_documento='fatura_cliente'` em ordem
cronologica e gera UM evento em `CarviaHistoricoMatchExtrato` por conciliacao.

Append-only (sem dedup): se o usuario conciliou 3x a mesma descricao com o
mesmo CNPJ, as 3 vezes viram 3 eventos (cada uma conta como ocorrencia).

**Idempotencia**: para permitir rerodar o backfill sem inflar contadores,
este script limpa previamente eventos com `conciliacao_id` que ainda
aponta para conciliacoes existentes — deleta o que ja veio do backfill
anterior, preservando eventos organicos (que podem ter `conciliacao_id=NULL`
se gerados antes deste ponteiro existir, embora no escopo atual sempre seja
preenchido pelo hook em `conciliar()`).

Uso:
    source .venv/bin/activate
    python scripts/backfill_historico_match_extrato.py

Opcoes:
    --dry-run     Nao grava, so conta o que seria gravado
    --limite N    Processa apenas N conciliacoes (debug)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db


def backfill(dry_run=False, limite=None):
    from sqlalchemy.orm import joinedload

    from app.carvia.models import (
        CarviaConciliacao,
        CarviaFaturaCliente,
        CarviaHistoricoMatchExtrato,
    )
    from app.carvia.services.financeiro.carvia_historico_match_service import (
        CarviaHistoricoMatchService,
    )
    from app.utils.timezone import agora_utc_naive

    print("=" * 70)
    print("Backfill: carvia_historico_match_extrato")
    print(f"Modo: {'DRY-RUN' if dry_run else 'REAL'}")
    if limite:
        print(f"Limite: {limite} conciliacoes")
    print("=" * 70)

    # 1. Limpeza idempotente (apenas eventos com conciliacao_id ainda vigente)
    if not dry_run:
        deletados = db.session.execute(db.text("""
            DELETE FROM carvia_historico_match_extrato
            WHERE conciliacao_id IS NOT NULL
              AND conciliacao_id IN (SELECT id FROM carvia_conciliacoes)
        """)).rowcount
        db.session.commit()
        print(f"[CLEANUP] {deletados} eventos pre-existentes removidos (idempotencia)")
    else:
        print("[CLEANUP] Pulado (dry-run)")

    # 2. Busca todas conciliacoes fatura_cliente com extrato_linha eager loaded.
    # FIX M5: joinedload(extrato_linha) elimina 1 query por conciliacao.
    query = (
        CarviaConciliacao.query
        .options(joinedload(CarviaConciliacao.extrato_linha))
        .filter_by(tipo_documento='fatura_cliente')
        .order_by(CarviaConciliacao.conciliado_em.asc(), CarviaConciliacao.id.asc())
    )
    if limite:
        query = query.limit(limite)

    conciliacoes = query.all()
    total = len(conciliacoes)
    print(f"[FETCH] {total} conciliacoes fatura_cliente encontradas")

    if total == 0:
        print("[DONE] Nada a processar")
        return

    # 2.1 Pre-carrega TODAS as faturas em UMA query (dict indexado por id).
    # FIX M5: substitui 1 query `session.get(CarviaFaturaCliente, ...)` por
    # conciliacao por uma unica query `IN (...)`.
    doc_ids = list({c.documento_id for c in conciliacoes})
    if doc_ids:
        faturas = {
            f.id: f for f in CarviaFaturaCliente.query.filter(
                CarviaFaturaCliente.id.in_(doc_ids)
            ).all()
        }
    else:
        faturas = {}
    print(f"[FETCH] {len(faturas)} faturas cliente pre-carregadas")

    # 3. Processa cada conciliacao
    processadas = 0
    inseridas = 0
    skipped_linha_ausente = 0
    skipped_fatura_ausente = 0
    skipped_sem_cnpj = 0
    skipped_sem_tokens = 0

    for conc in conciliacoes:
        processadas += 1

        # Acesso O(1) via joinedload (sem query adicional)
        linha = conc.extrato_linha
        if not linha:
            skipped_linha_ausente += 1
            continue

        # Acesso O(1) via dict pre-carregado
        fatura = faturas.get(conc.documento_id)
        if not fatura:
            skipped_fatura_ausente += 1
            continue

        cnpj = (fatura.cnpj_cliente or '').strip()
        if not cnpj:
            skipped_sem_cnpj += 1
            continue

        tokens = CarviaHistoricoMatchService.tokens_chave(linha.descricao)
        if not tokens:
            skipped_sem_tokens += 1
            continue

        if dry_run:
            inseridas += 1
            continue

        # FIX M6: fallback quando conciliado_em e None (raro mas possivel em
        # dados antigos). Sem o fallback, o INSERT viola NOT NULL do
        # registrado_em e o lote inteiro de 100 e silenciosamente rolado.
        registrado_em = conc.conciliado_em or agora_utc_naive()

        # INSERT com timestamp preservando ordem cronologica
        novo = CarviaHistoricoMatchExtrato(
            descricao_linha_raw=(linha.descricao or '')[:500],
            descricao_tokens=tokens[:500],
            cnpj_pagador=cnpj,
            tipo_documento='fatura_cliente',
            conciliacao_id=conc.id,
            registrado_em=registrado_em,
        )
        db.session.add(novo)
        inseridas += 1

        # Commit em lotes para nao estourar session
        if inseridas % 100 == 0:
            db.session.commit()
            print(f"  [PROGRESS] {inseridas}/{total} inseridas...")

    if not dry_run:
        db.session.commit()

    # 4. Relatorio
    print()
    print("=" * 70)
    print(f"[STATS] Conciliacoes processadas: {processadas}")
    print(f"[STATS] Eventos {'seriam' if dry_run else 'foram'} inseridos: {inseridas}")
    if skipped_linha_ausente:
        print(f"[SKIP]  Linha de extrato ausente: {skipped_linha_ausente}")
    if skipped_fatura_ausente:
        print(f"[SKIP]  Fatura ausente: {skipped_fatura_ausente}")
    if skipped_sem_cnpj:
        print(f"[SKIP]  Fatura sem CNPJ pagador: {skipped_sem_cnpj}")
    if skipped_sem_tokens:
        print(f"[SKIP]  Descricao sem tokens uteis (stopwords/vazia): {skipped_sem_tokens}")

    if not dry_run:
        # Sanity check: total na tabela
        total_tabela = db.session.execute(db.text(
            "SELECT COUNT(*) FROM carvia_historico_match_extrato"
        )).scalar()
        print(f"[DB]    Total na tabela apos backfill: {total_tabela}")

        # Top 5 CNPJs mais frequentes
        top = db.session.execute(db.text("""
            SELECT cnpj_pagador, COUNT(*) as ocorrencias
            FROM carvia_historico_match_extrato
            GROUP BY cnpj_pagador
            ORDER BY ocorrencias DESC
            LIMIT 5
        """)).fetchall()
        if top:
            print()
            print("[TOP 5 CNPJs]:")
            for cnpj, ocorr in top:
                print(f"  {cnpj} → {ocorr} ocorrencia(s)")

    print("=" * 70)
    print(f"[DONE] Backfill {'simulado' if dry_run else 'concluido'}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='Nao grava, so conta')
    parser.add_argument('--limite', type=int, default=None,
                        help='Processar apenas N conciliacoes')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        backfill(dry_run=args.dry_run, limite=args.limite)
