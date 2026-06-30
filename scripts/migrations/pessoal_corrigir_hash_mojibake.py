"""Deleta duplicatas criadas pelo efeito colateral do fix de mojibake.

Enquanto desfazer_mojibake esteve em normalizar_historico, o hash de dedup mudou para
registros com mojibake; reimportar o mesmo extrato gerava hash novo -> nao casava ->
duplicava. Apos REVERTER (normalizar_historico voltou a ser estavel), reimportacoes
voltam a casar. Resta limpar as duplicatas ja criadas.

Uma duplicata = registro com mojibake no historico ('Ã'/'Â') que tem um GEMEO ja
corrigido (mesma conta/data/valor/tipo, historico limpo). O gemeo (original, backfilled,
possivelmente com vinculos/split) e preservado; a duplicata mojibake e deletada.

Dry-run default.
    python scripts/migrations/pessoal_corrigir_hash_mojibake.py --dry-run
    python scripts/migrations/pessoal_corrigir_hash_mojibake.py --apply
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.pessoal.models import PessoalTransacao
from app.pessoal.services.parsers.base_parser import desfazer_mojibake


def main(apply: bool):
    app = create_app()
    with app.app_context():
        mojibake = PessoalTransacao.query.filter(
            db.or_(PessoalTransacao.historico.like('%Ã%'), PessoalTransacao.historico.like('%Â%'))
        ).all()
        print(f"=== Registros com mojibake no historico: {len(mojibake)} ===")
        deletadas = 0
        for m in mojibake:
            h_limpo = desfazer_mojibake(m.historico)
            gemeo = PessoalTransacao.query.filter(
                PessoalTransacao.conta_id == m.conta_id, PessoalTransacao.data == m.data,
                PessoalTransacao.valor == m.valor, PessoalTransacao.tipo == m.tipo,
                PessoalTransacao.historico == h_limpo, PessoalTransacao.id != m.id,
            ).first()
            if gemeo:
                print(f"  DUP id={m.id} '{m.historico[:30]}' -> deletar (gemeo original={gemeo.id})")
                db.session.delete(m)
                deletadas += 1
            else:
                # mojibake sem gemeo = registro legitimo nao-backfilled -> so corrigir o texto
                print(f"  FIX id={m.id} (sem gemeo) -> corrigir historico p/ '{h_limpo[:30]}'")
                m.historico = h_limpo
                m.descricao = desfazer_mojibake(m.descricao) if m.descricao else m.descricao

        print(f"\nDuplicatas deletadas: {deletadas}")
        if apply:
            db.session.commit()
            print("APLICADO (commit).")
        else:
            db.session.rollback()
            print("DRY-RUN (rollback) — rode com --apply para gravar.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    main(apply=args.apply)
