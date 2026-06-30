"""Backfill: corrige mojibake (encoding duplo UTF-8->Latin-1) em pessoal_transacoes.

Recupera o historico legivel ('AndrÃ©a' -> 'Andréa') e recompoe historico_completo.
Idempotente (so toca registros com sinal de mojibake). Dry-run default.

    python scripts/migrations/pessoal_corrigir_mojibake.py --dry-run
    python scripts/migrations/pessoal_corrigir_mojibake.py --apply
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.pessoal.models import PessoalTransacao
from app.pessoal.services.parsers.base_parser import (
    desfazer_mojibake, normalizar_historico, limpar_prefixo_descricao,
)


def _recompor_hc(historico, descricao):
    partes = [normalizar_historico(historico)]
    if descricao:
        d = normalizar_historico(limpar_prefixo_descricao(descricao))
        if d:
            partes.append(d)
    return ' | '.join(p for p in partes if p)


def main(apply: bool):
    app = create_app()
    with app.app_context():
        afetadas = PessoalTransacao.query.filter(
            db.or_(
                PessoalTransacao.historico.like('%Ã%'),
                PessoalTransacao.historico.like('%Â%'),
                PessoalTransacao.descricao.like('%Ã%'),
                PessoalTransacao.descricao.like('%Â%'),
            )
        ).all()
        print(f"=== Backfill mojibake — registros com sinal: {len(afetadas)} ===")
        n = 0
        for t in afetadas:
            h_new = desfazer_mojibake(t.historico)
            d_new = desfazer_mojibake(t.descricao) if t.descricao else t.descricao
            hc_new = _recompor_hc(h_new, d_new)
            if (h_new, d_new, hc_new) != (t.historico, t.descricao, t.historico_completo):
                print(f"  id={t.id} conta={t.conta_id}: '{t.historico}' -> '{h_new}'")
                t.historico = h_new
                t.descricao = d_new
                t.historico_completo = hc_new
                n += 1
        print(f"Corrigidos: {n}")
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
