#!/usr/bin/env python3
"""G5b — vasculhar estrutura fiscal CIEL IT (READ-ONLY).
Fase 1: campos configuraveis da operacao (estoque/conta/journal/cfop).
Fase 2: GRANULARIDADE — operacao/cfop é por LINHA ou por CABECALHO?
Fase 3: lista operacoes de industrializacao (remessa/retorno/entrada)."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP_MODEL = 'l10n_br_ciel_it_account.operacao'
KW_ESTOQUE = ('estoque', 'movimento', 'picking', 'atualiza', 'gera', 'stock', 'inventario')
KW_CONTA = ('conta', 'account', 'diario', 'journal', 'contrapartida', 'financeiro', 'valoracao')
KW_CFOP = ('cfop', 'tipo', 'natureza', 'fiscal')


def dump_fields(o, model, kws, label):
    print(f"\n--- campos de {model} ({label}) ---")
    try:
        fg = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
    except Exception as e:
        print(f"  ERRO/inexistente: {e}"); return {}
    hits = {f: m for f, m in fg.items() if any(k in f.lower() for k in kws)}
    for f in sorted(hits):
        m = hits[f]
        print(f"  {f:42s} {m.get('type'):10s} {m.get('relation') or ''}  | {m.get('string')}")
    return fg


def main():
    o = get_odoo_connection(); o.authenticate()

    print("=" * 96)
    print("FASE 1 — campos configuraveis de l10n_br_ciel_it_account.operacao")
    print("=" * 96)
    fg_op = dump_fields(o, OP_MODEL, KW_ESTOQUE, 'ESTOQUE')
    dump_fields(o, OP_MODEL, KW_CONTA, 'CONTA/JOURNAL')
    dump_fields(o, OP_MODEL, KW_CFOP, 'CFOP/TIPO')
    print(f"\n  total de campos na operacao: {len(fg_op)}")

    print("\n" + "=" * 96)
    print("FASE 2 — GRANULARIDADE: operacao/cfop por LINHA ou CABECALHO?")
    print("=" * 96)
    for model, lbl in [('account.move', 'NF cabecalho'), ('account.move.line', 'NF LINHA'),
                       ('stock.move', 'movimento estoque (linha fisica)'),
                       ('stock.picking', 'picking cabecalho')]:
        fg = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        rel = {f: fg[f] for f in fg if ('operacao' in f.lower() or 'cfop' in f.lower()
               or (f.lower().startswith('l10n_br') and ('op' in f.lower() or 'cfop' in f.lower())))}
        print(f"\n  [{lbl}] {model}:")
        for f in sorted(rel):
            print(f"     {f:40s} {rel[f].get('type'):10s} {rel[f].get('relation') or ''} | {rel[f].get('string')}")
        if not rel:
            print("     (sem campo operacao/cfop)")

    print("\n" + "=" * 96)
    print("FASE 3 — operacoes de industrializacao (remessa/retorno/entrada)")
    print("=" * 96)
    ops = o.search_read(OP_MODEL,
                        ['|', '|', '|', ('name', 'ilike', 'industrializ'), ('name', 'ilike', 'remessa'),
                         ('name', 'ilike', 'retorno'), ('name', 'ilike', 'retrabalho')],
                        ['id', 'name'], limit=60)
    print(f"  {len(ops)} operacoes:")
    for op in sorted(ops, key=lambda x: x['id']):
        print(f"    id={op['id']:<5} {op['name']}")


if __name__ == '__main__':
    main()
