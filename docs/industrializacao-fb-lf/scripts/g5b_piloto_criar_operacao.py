#!/usr/bin/env python3
"""
PILOTO G5b — criar operacao de retorno de insumo SIMBOLICA (movimento_estoque=False).

Cópia FIEL da op 2027 (mantém CFOP/impostos/tudo) virando SÓ movimento_estoque=False,
e SEM cfop_orig (aplicada MANUALMENTE no piloto — não muda os retornos globais).
Garante zero impacto fiscal (esta op NÃO tem ICMS; impostos preservados pela cópia).

--dry-run DEFAULT (não escreve). --execute cria via copy() + aplica overrides.
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP = 'l10n_br_ciel_it_account.operacao'
OP_BASE = 2027  # "Retorno de mercadoria remetida p/ industrializacao" (cfop_orig=5902->1902, movimento_estoque=True)
NOVO_NOME = 'Retorno insumo industrializ. SIMBOLICO (G5b PILOTO) FB-LF'
CHECK_FIELDS = ['name', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv', 'l10n_br_tipo_operacao',
                'l10n_br_tipo_pedido_entrada', 'l10n_br_cfop_orig_id', 'l10n_br_intra_cfop_id']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    DRY = not args.execute
    o = get_odoo_connection(); o.authenticate()

    base = o.read(OP, [OP_BASE], CHECK_FIELDS)[0]
    print("=" * 92)
    print(f"PILOTO G5b — {'DRY-RUN' if DRY else 'EXECUTE'}")
    print("=" * 92)
    print(f"[base] op {OP_BASE}: {base['name'].strip()}")
    print(f"   movimento_estoque={base['l10n_br_movimento_estoque']} cfop_orig={base['l10n_br_cfop_orig_id']} "
          f"intra={base['l10n_br_intra_cfop_id']} tipo_ped_ent={base['l10n_br_tipo_pedido_entrada']}")
    print(f"\n[plano] criar CÓPIA com overrides:")
    print(f"   name = '{NOVO_NOME}'")
    print(f"   l10n_br_movimento_estoque = False   (<-- o lever G5b)")
    print(f"   l10n_br_cfop_orig_id = False         (<-- nao auto-selecionar; aplicar manual no piloto)")
    print(f"   [resto IDÊNTICO à 2027: CFOP intra 1902, impostos, tipo_pedido — preserva fiscal]")

    # ja existe?
    existe = o.search_read(OP, [('name', '=', NOVO_NOME)], ['id'], limit=1)
    if existe:
        print(f"\n   JÁ EXISTE: op id={existe[0]['id']} (idempotente, nada a criar)")
        return

    if DRY:
        print("\nDRY-RUN: nada criado. --execute para criar a operação (config isolada, reversível).")
        return

    novo_id = o.execute_kw(OP, 'copy', [OP_BASE, {
        'name': NOVO_NOME,
        'l10n_br_movimento_estoque': False,
        'l10n_br_cfop_orig_id': False,
    }])
    chk = o.read(OP, [novo_id], CHECK_FIELDS)[0]
    print(f"\n[OK] criada op id={novo_id}")
    print(f"   name={chk['name']} movimento_estoque={chk['l10n_br_movimento_estoque']} "
          f"cfop_orig={chk['l10n_br_cfop_orig_id']} intra={chk['l10n_br_intra_cfop_id']}")
    print(f"   -> aplicar MANUALMENTE na linha 1902 do retorno-piloto (l10n_br_operacao_manual=True + l10n_br_operacao_id={novo_id})")


if __name__ == '__main__':
    main()
