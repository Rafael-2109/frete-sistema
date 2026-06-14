#!/usr/bin/env python3
"""S18 — Passo 2 (Forma B): montar a NF-INSUMOS (5902) SEPARADA desde o inicio,
no journal RETIND 1083, derivando as linhas da REMESSA (fonte determinista =
invariante 5902=5901), NAO da BoM subcontract (que so o azeite tem).

Corrige o s15 (GATE 1c): a fonte dos componentes e' a REMESSA real do ciclo
(RPI/2026/00245), nao a BoM type=subcontract. Funciona p/ o 4870112 (shoyu, sem
subcontract) — provado em S17 que o shoyu TEM retorno real com 16x5902 (moves
709632/708286, montados pela Josefa/Histaina a mao).

VEICULO: server action (server-side garante os computes fiscais como o robo).
Cria UM account.move novo (out_invoice, journal 1083, partner FB=1) + N linhas
5902 (op 2864, qty/price da remessa) + recompute. SEM action_post, SEM SEFAZ.
Fica em DRAFT p/ inspecao; --cleanup deleta. Autorizacao Rafael por escrita.

MODOS:
  (sem flag)         dry-run READ: acha a remessa + lista as N linhas que serao criadas
  --remessa MOVE     usa outra remessa (default 735679 = RPI/2026/00245 do piloto)
  --confirmar        cria SA + roda (cria NF-insumos draft + N x 5902 + recompute) + le + DELETA a SA
  --cleanup NF_ID    button_draft (se preciso) + unlink da NF-insumos de teste
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
J_RETIND = 1083        # RETORNO INDUSTRIALIZACAO INSUMOS (sale LF, no_payment=True + 26667 PASSIVA)
PARTNER_FB = 1         # NACOM GOYA - FB (destinatario do retorno LF->FB)
OP_5902 = 2864         # Retorno de Industrializacao por encomenda (CFOP 5902 / CST 50)
REMESSA_PILOTO = 735679  # RPI/2026/00245


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--remessa', type=int, default=REMESSA_PILOTO, metavar='MOVE')
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--cleanup', type=int, metavar='NF_ID')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    def rr(model, domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)

    # ---------- CLEANUP ----------
    if args.cleanup:
        nf = args.cleanup
        st = rd('account.move', [nf], ['state', 'name'])
        if not st:
            print(f"  NF {nf}: ja nao existe"); return
        if st[0]['state'] == 'posted':
            o.execute_kw('account.move', 'button_draft', [[nf]], {'context': CTX})
            print(f"  NF {nf}: posted -> draft")
        try:
            o.execute_kw('account.move', 'unlink', [[nf]], {'context': CTX})
            print(f"  NF {nf} ({st[0].get('name')}) DELETADA")
        except Exception as e:
            o.execute_kw('account.move', 'button_cancel', [[nf]], {'context': CTX})
            print(f"  NF {nf} unlink falhou ({str(e)[:80]}); CANCELADA")
        return

    # ---------- ler a remessa (fonte) ----------
    rem = rd('account.move', [args.remessa],
             ['name', 'state', 'journal_id', 'partner_id', 'amount_total'])
    assert rem, f"remessa {args.remessa} nao encontrada"
    rem = rem[0]
    rlines = rr('account.move.line',
                [('move_id', '=', args.remessa), ('display_type', '=', 'product')],
                ['product_id', 'l10n_br_cfop_codigo', 'quantity', 'price_unit', 'price_subtotal'],
                order='id')
    total_src = sum(l.get('price_subtotal') or 0 for l in rlines)

    print("=" * 90)
    print("S18 — Passo 2 (Forma B): NF-INSUMOS separada no RETIND 1083, fonte = REMESSA")
    print("=" * 90)
    print(f"  Remessa-fonte : move {rem['id']} {rem['name']} state={rem['state']} "
          f"journal={m2o(rem['journal_id'])} (CFOP 5901)")
    print(f"  -> NF-insumos : account.move NOVO (out_invoice) journal={J_RETIND} (RETIND) "
          f"partner={PARTNER_FB} (FB) op-linha={OP_5902} (->5902/CST50)")
    print(f"\n  {len(rlines)} linhas a criar (qty/price da remessa = invariante 5902=5901):")
    for l in rlines:
        print(f"     {m2o(l['product_id'])[:48]:48} qty={l['quantity']} pu={l['price_unit']} "
              f"sub={l['price_subtotal']}")
    print(f"\n  total esperado da NF-insumos ~= R$ {total_src:.2f} (= soma 5901 da remessa)")
    print(f"  efeito: 0 SEFAZ, draft only; baixa PASSIVA so mede no post (GATE 0 ja provou o mecanismo)")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito no Odoo. Com 'go': --confirmar")
        return

    # ---------- EXECUTAR via server action ----------
    code = (
        "rem = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "rlines = rem.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "move = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({\n"
        "    'move_type':'out_invoice','journal_id':%d,'partner_id':%d,'company_id':5,\n"
        "    'invoice_date': fields.Date.context_today(env['account.move'])})\n"
        "criadas=0; erros=[]\n"
        "for rl in rlines:\n"
        "    try:\n"
        "        env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({\n"
        "            'move_id':move.id,'product_id':rl.product_id.id,'quantity':rl.quantity,\n"
        "            'l10n_br_operacao_id':%d,'price_unit':rl.price_unit})\n"
        "        criadas+=1\n"
        "    except Exception as e:\n"
        "        erros.append('%%s:%%s'%%(rl.product_id.default_code,str(e)[:50]))\n"
        "try:\n"
        "    move.onchange_l10n_br_calcular_imposto(); move.onchange_l10n_br_calcular_imposto_btn()\n"
        "except Exception as e:\n"
        "    log('S18 recompute erro: %%s'%%str(e)[:140])\n"
        "pl = move.invoice_line_ids.filtered(lambda l: l.display_type=='product')\n"
        "cfops = dict((c, list(pl.mapped('l10n_br_cfop_codigo')).count(c)) for c in set(pl.mapped('l10n_br_cfop_codigo')))\n"
        "csts = dict((c, list(pl.mapped('l10n_br_icms_cst')).count(c)) for c in set(pl.mapped('l10n_br_icms_cst')))\n"
        "contas = list(set(pl.mapped('account_id.code')))\n"
        "log('S18-RESULT inv=%%s criadas=%%s total=%%s cfops=%%s csts=%%s contas=%%s amount=%%s erros=%%s' %% (str(move.ids), criadas, len(pl), str(cfops), str(csts), str(contas), move.amount_total, str(erros[:3])))\n"
    ) % (args.remessa, J_RETIND, PARTNER_FB, OP_5902)

    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    print("\n  [1] criando server action de teste...")
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S18 NF-INSUMOS - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"      SA criada: {sa}")
    print("  [2] executando a SA (cria NF-insumos draft + linhas 5902 + recompute)...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
        print("      SA executada.")
    except Exception as e:
        print(f"      SA run aviso: {str(e)[:160]}")

    logs = rr('ir.logging', [('message', 'like', 'S18%')], ['message'], order='id desc', limit=4)
    nf_id = None
    for lg in logs:
        print(f"  LOG: {lg['message'][:300]}")
        if 'S18-RESULT' in lg['message'] and 'inv=[' in lg['message']:
            try:
                nf_id = int(lg['message'].split('inv=[')[1].split(']')[0].split(',')[0])
            except Exception:
                pass
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")

    if nf_id:
        nl = rr('account.move.line', [('move_id', '=', nf_id), ('display_type', '=', 'product')],
                ['product_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'account_id', 'price_unit'])
        print(f"\n  >>> NF-insumos criada: move {nf_id} ({len(nl)} linhas)")
        print(f"      CFOPs={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))} "
              f"contas={sorted(set(m2o(x.get('account_id')).split('|')[-1][:12] for x in nl))}")
        print(f"  >>> inspecionar/limpar: --cleanup {nf_id}")


if __name__ == '__main__':
    main()
