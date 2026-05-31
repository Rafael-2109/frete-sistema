#!/usr/bin/env python3
"""
G5b — APLICAR a operacao simbolica 3252 nas linhas 1902 (insumos consumidos) do
retorno-piloto FB (Etapa 5).

Efeito: setar `l10n_br_operacao_manual=True` + `l10n_br_operacao_id=3252` nas linhas
de CFOP 1902 do account.move de ENTRADA da FB (retorno LF->FB), ENQUANTO em draft.
A op 3252 tem `l10n_br_movimento_estoque=False` -> a linha 1902 NAO gera stock.move
-> os insumos consumidos NAO re-entram no estoque (elimina o double-count R$785k).

ESCOPO: SO mexe nas linhas 1902 (insumos consumidos). NUNCA toca 1124 (PA/servico,
movimento_estoque=True) nem 1903 (sobras, re-entram). Idempotente. Guard de estado
(move deve estar em draft) — aplicar op apos posted NAO altera o stock.move ja gerado.

Notas de versao (Odoo 17, CIEL IT):
  - linhas de produto da fatura tem `display_type='product'` (NAO False) -> NAO filtrar
    por display_type; filtrar por product_id != False.
  - CFOP 1902 e' resolvido AO VIVO por `codigo_cfop` (modelo l10n_br_ciel_it_account.cfop),
    nao por id hardcoded (fallback 102, verificado 2026-05-30).

--dry-run DEFAULT (nada escrito). --execute aplica. Requer --move-id.

Uso:
  python g5b_aplicar_op3252_na_linha.py --move-id 999999            # dry-run
  python g5b_aplicar_op3252_na_linha.py --move-id 999999 --execute  # aplica
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP_MODEL = 'l10n_br_ciel_it_account.operacao'
CFOP_MODEL = 'l10n_br_ciel_it_account.cfop'
OP_SIMBOLICA = 3252        # T-G5B-OP (movimento_estoque=False, cfop_orig=False)
OP_BASE_1902 = 2027        # "Retorno de mercadoria remetida p/ industrializacao" (base documentada)
CFOP_1902_FALLBACK = 102   # verificado ao vivo 2026-05-30 (codigo_cfop='1902')

LINE_FIELDS = ['id', 'name', 'product_id', 'quantity', 'price_subtotal',
               'l10n_br_operacao_id', 'l10n_br_operacao_manual', 'l10n_br_cfop_id']


def fmt_m2o(v):
    return f"{v[0]}:{v[1].split(' ')[0]}" if isinstance(v, list) and v else str(v)


def resolve_cfop_1902_ids(o):
    """ids dos CFOP cujo codigo_cfop comeca com 1902 (resolve ao vivo; fallback 102)."""
    try:
        rows = o.search_read(CFOP_MODEL, [('codigo_cfop', '=like', '1902%')], ['id', 'codigo_cfop'], limit=10)
        ids = [r['id'] for r in rows]
        if ids:
            return ids
    except Exception as e:
        print(f"  [aviso] resolve CFOP 1902 ao vivo falhou ({e}); usando fallback {CFOP_1902_FALLBACK}")
    return [CFOP_1902_FALLBACK]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--move-id', type=int, required=True,
                    help='account.move de ENTRADA da FB (retorno LF->FB), em draft')
    ap.add_argument('--execute', action='store_true', help='aplica (default = dry-run)')
    args = ap.parse_args()
    DRY = not args.execute

    o = get_odoo_connection(); o.authenticate()

    print("=" * 100)
    print(f"G5b APLICAR op {OP_SIMBOLICA} nas linhas 1902 — move {args.move_id} — {'DRY-RUN' if DRY else 'EXECUTE'}")
    print("=" * 100)

    # -- GUARD 0: a op simbolica existe, ativa, movimento_estoque=False
    op = o.read(OP_MODEL, [OP_SIMBOLICA], ['name', 'active', 'l10n_br_movimento_estoque'])
    if not op:
        print(f"[ABORT] op {OP_SIMBOLICA} nao existe. Rode g5b_piloto_criar_operacao.py --execute primeiro.")
        return 1
    op = op[0]
    if not op['active'] or op['l10n_br_movimento_estoque'] is not False:
        print(f"[ABORT] op {OP_SIMBOLICA} invalida: active={op['active']} movimento_estoque={op['l10n_br_movimento_estoque']} (esperado active=True, movimento_estoque=False)")
        return 1
    print(f"[guard] op {OP_SIMBOLICA} OK: {op['name'].strip()!r} active={op['active']} movimento_estoque={op['l10n_br_movimento_estoque']}")

    cfop_1902_ids = resolve_cfop_1902_ids(o)
    print(f"[guard] CFOP 1902 ids (codigo_cfop like 1902%): {cfop_1902_ids}")

    # -- GUARD 1: estado do move (so draft garante supressao do stock.move)
    mv = o.read('account.move', [args.move_id],
                ['name', 'state', 'move_type', 'company_id', 'l10n_br_tipo_pedido'])
    if not mv:
        print(f"[ABORT] account.move {args.move_id} nao encontrado.")
        return 1
    mv = mv[0]
    print(f"[move] {mv['name']} state={mv['state']} type={mv['move_type']} company={fmt_m2o(mv['company_id'])}")
    if mv['state'] != 'draft':
        print(f"[AVISO] move NAO esta em draft (state={mv['state']}). Aplicar a op agora NAO altera o stock.move ja gerado (efeito = no-op fiscal-fisico).")
        if not DRY:
            print("[ABORT] recusando --execute em move nao-draft (evita falso sucesso). Reabra em draft ou trate o picking manualmente.")
            return 1

    # -- localizar linhas-alvo: CFOP 1902 OU operacao base 2027 (Odoo 17: product lines = display_type 'product')
    lines = o.search_read('account.move.line',
                          [('move_id', '=', args.move_id), ('product_id', '!=', False)],
                          LINE_FIELDS, limit=300)
    alvos, ja_ok, fora = [], [], []
    for l in lines:
        op_id = l['l10n_br_operacao_id'][0] if l['l10n_br_operacao_id'] else None
        cfop_id = l['l10n_br_cfop_id'][0] if l['l10n_br_cfop_id'] else None
        if op_id == OP_SIMBOLICA:
            ja_ok.append(l)
        elif (cfop_id in cfop_1902_ids) or (op_id == OP_BASE_1902):
            alvos.append(l)
        else:
            fora.append(l)

    print(f"\nlinhas-produto: {len(lines)} | alvo(1902)={len(alvos)} | ja_3252={len(ja_ok)} | outras(1124/1903/...)={len(fora)}")
    print("-" * 100)
    print(f"{'line':>7} {'produto':<34} {'qty':>9} {'CFOP':<10} {'op atual':<22} -> acao")
    for grp, tag in ((alvos, f'SET op={OP_SIMBOLICA}+manual'), (ja_ok, '(ja 3252, skip)'), (fora, '(1124/1903 preservada)')):
        for l in grp:
            print(f"{l['id']:>7} {(l['product_id'][1] if l['product_id'] else '?')[:34]:<34} {l['quantity']:>9} "
                  f"{fmt_m2o(l['l10n_br_cfop_id']):<10} {fmt_m2o(l['l10n_br_operacao_id']):<22} -> {tag}")

    # -- GUARD anti-falso-sucesso: 0 alvos + 0 ja_ok mas HA linhas de produto -> CFOP/op podem estar errados
    if not alvos and not ja_ok and fora:
        print(f"\n[ATENCAO] 0 linhas 1902 detectadas, mas o move tem {len(fora)} linha(s) de produto.")
        print(f"          Possiveis causas: (a) CFOP da linha != 1902 (inter-company pode vir SEM operacao/CFOP — ver ACHADOS §4),")
        print(f"          (b) este move nao e' o retorno, (c) CFOP id mudou. NAO trate como 'idempotente'. Verifique os CFOPs acima.")
        return 2

    if not alvos:
        print("\n[OK] nada a aplicar (linhas 1902 ja com op 3252). Idempotente.")
        return 0

    if DRY:
        print(f"\nDRY-RUN: {len(alvos)} linha(s) 1902 receberiam op {OP_SIMBOLICA} (movimento_estoque=False).")
        print("         1124/1903 preservadas (movimento_estoque=True). Aplicar com --execute (move em draft).")
        return 0

    ids = [l['id'] for l in alvos]
    o.execute_kw('account.move.line', 'write', [ids,
                 {'l10n_br_operacao_manual': True, 'l10n_br_operacao_id': OP_SIMBOLICA}])
    chk = o.read('account.move.line', ids, ['id', 'l10n_br_operacao_id', 'l10n_br_operacao_manual', 'l10n_br_cfop_id'])
    ok = all(c['l10n_br_operacao_id'] and c['l10n_br_operacao_id'][0] == OP_SIMBOLICA and c['l10n_br_operacao_manual'] for c in chk)
    print(f"\n[{'OK' if ok else 'FALHA'}] {len(ids)} linha(s) 1902 -> op {OP_SIMBOLICA} (manual=True). Verificado: {ok}")
    for c in chk:
        print(f"   line {c['id']}: op={fmt_m2o(c['l10n_br_operacao_id'])} manual={c['l10n_br_operacao_manual']} cfop={fmt_m2o(c['l10n_br_cfop_id'])}")
    print("   Proximo: validar/postar o move e conferir que o picking gerado NAO tem as linhas 1902 (so 1124/1903).")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main() or 0)
