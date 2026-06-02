#!/usr/bin/env python3
"""
setar_tipo_produto.py — FASE 1 da operação Remessa FB->LF (industrialização).

Seta `l10n_br_tipo_produto = '01'` (Matéria Prima) nos produtos que estão com
o campo vazio (False), bloqueando o pré-flight fiscal (gate tipo_produto_ausente).

CONTEXTO: produtos 105000002 (pid 27914) e 105000044 (pid 27733) são insumos
(cod[0]=1) destinados a remessa FB->LF de industrialização. Toda a família 105*
usa '01'. Sem isso o pré-flight fiscal retorna PRE_FLIGHT_BLOQUEADO.

CAMPO (verificado ao vivo 2026-06-02 via fields_get):
  - product.product.l10n_br_tipo_produto = related store:False -> product_tmpl_id.l10n_br_tipo_produto
  - product.template.l10n_br_tipo_produto = store:True (campo REAL)
  => Este script escreve no PRODUCT.TEMPLATE (campo real, store=True).
  Selection '01' = "01 - Matéria Prima".

SIDE-EFFECTS (memória ciel_it_quirks):
  - quirk #2: product.write({weight}) NÃO persiste -> NÃO tocamos weight.
  - quirk #7/G035: barcode inválido quebra SEFAZ -> NÃO tocamos barcode; PROVAMOS que não muda.
  Este script escreve APENAS l10n_br_tipo_produto. Captura before/after de campos
  sensíveis (weight, barcode, ncm, origem, name, default_code, standard_price) para
  PROVAR que não houve efeito colateral.

USO:
  python setar_tipo_produto.py                 # dry-run (default) — NÃO escreve
  python setar_tipo_produto.py --confirmar     # efetiva (escreve l10n_br_tipo_produto)
  python setar_tipo_produto.py --pids 27914,27733 --valor 01   # override explícito

REGRAS:
  - --dry-run é DEFAULT. Sem --confirmar, só calcula e mostra o plano.
  - Idempotente: produto que já tem o valor alvo -> NOOP (não escreve).
  - Verificação pós-write: re-lê os campos e compara com snapshot (operação viva).
"""
import argparse
import json
import sys
import time

# product.product ids -> default_code (escopo fixo desta operação)
PIDS_DEFAULT = [27914, 27733]
VALOR_ALVO_DEFAULT = '01'  # 01 - Matéria Prima

# Campos que NÃO devem mudar — provados via before/after (anti side-effect)
CAMPOS_SENSIVEIS = [
    'default_code', 'name', 'weight', 'barcode',
    'l10n_br_ncm_id', 'l10n_br_origem', 'standard_price',
]


def _snapshot(odoo, pids):
    """Lê estado de product.product + valor real no template. Retorna dict por pid."""
    prods = odoo.search_read(
        'product.product', [['id', 'in', pids]],
        ['id', 'product_tmpl_id', 'active', 'l10n_br_tipo_produto'] + CAMPOS_SENSIVEIS,
    )
    snap = {}
    for p in prods:
        snap[p['id']] = {
            'pid': p['id'],
            'tmpl_id': p['product_tmpl_id'][0] if p.get('product_tmpl_id') else None,
            'tmpl_label': p['product_tmpl_id'][1] if p.get('product_tmpl_id') else None,
            'active': p.get('active'),
            'l10n_br_tipo_produto': p.get('l10n_br_tipo_produto'),
            'sensiveis': {c: p.get(c) for c in CAMPOS_SENSIVEIS},
        }
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pids', default=None,
                    help='CSV de product.product ids (default escopo fixo 27914,27733)')
    ap.add_argument('--valor', default=VALOR_ALVO_DEFAULT,
                    help="Valor de l10n_br_tipo_produto (default '01' Matéria Prima)")
    ap.add_argument('--confirmar', action='store_true',
                    help='Efetiva o write. Sem isso = dry-run (default).')
    args = ap.parse_args()

    pids = ([int(x) for x in args.pids.split(',')] if args.pids else list(PIDS_DEFAULT))
    valor = args.valor.strip()
    dry_run = not args.confirmar

    sys.path.insert(0, '.')
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()

        t0 = time.time()
        # Valida que valor está na selection
        fg = odoo.execute_kw('product.template', 'fields_get',
                             [['l10n_br_tipo_produto']], {'attributes': ['selection']})
        selecao = dict(fg['l10n_br_tipo_produto']['selection'])
        if valor not in selecao:
            print(json.dumps({'status': 'FALHA_VALOR_INVALIDO', 'valor': valor,
                              'validos': selecao}, ensure_ascii=False, indent=2))
            sys.exit(2)

        before = _snapshot(odoo, pids)
        if len(before) != len(pids):
            faltando = [p for p in pids if p not in before]
            print(json.dumps({'status': 'FALHA_PRODUTO_NAO_ENCONTRADO',
                              'faltando': faltando}, ensure_ascii=False, indent=2))
            sys.exit(2)

        # Decidir quem precisa de write (idempotência)
        plano = []
        tmpls_a_escrever = []
        for pid in pids:
            atual = before[pid]['l10n_br_tipo_produto']
            precisa = (atual != valor)
            plano.append({
                'pid': pid, 'tmpl_id': before[pid]['tmpl_id'],
                'tmpl_label': before[pid]['tmpl_label'],
                'tipo_antes': atual, 'tipo_alvo': valor,
                'acao': 'WRITE' if precisa else 'NOOP_JA_OK',
            })
            if precisa:
                tmpls_a_escrever.append(before[pid]['tmpl_id'])

        resultado = {
            'status': 'DRY_RUN_OK' if dry_run else None,
            'dry_run': dry_run,
            'valor_alvo': valor,
            'valor_alvo_label': selecao[valor],
            'escreve_em': 'product.template.l10n_br_tipo_produto (store=True)',
            'plano': plano,
            'before': before,
        }

        if dry_run:
            resultado['after'] = None
            resultado['tempo_ms'] = int((time.time() - t0) * 1000)
            print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
            sys.exit(4)

        # --confirmar: escreve SOMENTE l10n_br_tipo_produto no TEMPLATE
        if tmpls_a_escrever:
            odoo.write('product.template', tmpls_a_escrever,
                       {'l10n_br_tipo_produto': valor})

        after = _snapshot(odoo, pids)

        # Verificação anti side-effect: campos sensíveis idênticos before/after
        side_effects = []
        for pid in pids:
            for c in CAMPOS_SENSIVEIS:
                if before[pid]['sensiveis'][c] != after[pid]['sensiveis'][c]:
                    side_effects.append({
                        'pid': pid, 'campo': c,
                        'antes': before[pid]['sensiveis'][c],
                        'depois': after[pid]['sensiveis'][c],
                    })
            # confirmar que tipo ficou correto
        todos_ok = all(after[pid]['l10n_br_tipo_produto'] == valor for pid in pids)

        resultado['status'] = ('EXECUTADO' if (todos_ok and not side_effects)
                               else 'EXECUTADO_COM_ALERTA')
        resultado['after'] = after
        resultado['side_effects_detectados'] = side_effects
        resultado['todos_com_valor_alvo'] = todos_ok
        resultado['tempo_ms'] = int((time.time() - t0) * 1000)
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
        sys.exit(0 if (todos_ok and not side_effects) else 1)


if __name__ == '__main__':
    main()
