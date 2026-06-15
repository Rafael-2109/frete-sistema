#!/usr/bin/env python3
"""s71 — CANARY do body G1 (genealogia + montagem) contra o ORÁCULO.

Cada modo DERIVA o corpo do PRÓPRIO `SA_BODY_G1` (sem cópia/drift) e roda server-side
via uma `ir.actions.server` EFÊMERA (create→run→unlink, padrão `s49`) — valida o código
REAL que a SA persistente vai executar.

Modos:
  (default)          GENEALOGIA `safe_eval` vs oráculo `descobrir_fonte_nf2` — estágio 1.
                     READ-only: trunca `SA_BODY_G1` antes da MONTAGEM + log → ZERO NF criada.
  --montagem         MONTAGEM → DRAFT NF-2 — estágio 2. Trunca `SA_BODY_G1` antes do
                     `# === POST` (genealogia + montagem + recompute + remap + R3, SEM
                     `action_post`) + log do `nf2.id`. dry-run default; **--confirmar cria
                     1 `account.move` DRAFT** (RETIND 1083, hash=False, NÃO posta, NÃO SEFAZ).
  --deletar NF2_ID   CLEANUP do draft do estágio 2. Guard: só deleta `state=draft` E
                     `journal_id == RETIND 1083`. dry-run default; --confirmar executa.

🔴 --montagem --confirmar e --deletar --confirmar ESCREVEM no Odoo de PRODUÇÃO (CIEL IT):
   cada um exige go FRESCO do Rafael.

Uso: python docs/industrializacao-fb-lf/scripts/s71_canary_g1_genealogia.py [NF1_ID] [--montagem [--confirmar]]
     python docs/industrializacao-fb-lf/scripts/s71_canary_g1_genealogia.py --deletar NF2_ID [--confirmar]
     (default NF1 = 791437, piloto VND/2026/00384)
"""
import argparse
import os
import sys
import re
# raiz da worktree onde este script vive (NÃO o checkout principal — provisioning/ só existe aqui)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.provisioning.sa_retorno_industrializacao import SA_BODY_G1, RETIND
from app.odoo.estoque.scripts.descoberta_industrializacao import DescobertaIndustrializacaoService

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
CHAVE_REMESSA_ESPERADA = '35260661724241000178550010000946041007356795'


def _run_sa_efemera(o, code, *, name, active_id, log_like):
    """create→run(active_id=NF-1)→unlink de uma `ir.actions.server` state=code. Retorna
    (msg do log mais recente que casa `log_like`, erro de run). A SA é deletada; o que o
    body criar (ex.: a NF-2 draft) PERSISTE — esse é o ponto do estágio 2."""
    mid = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': name, 'model_id': mid, 'state': 'code', 'code': code}], {'context': CTX})
    print(f"SA canary {sa} criada; rodando active_id={active_id}...")
    err = None
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=active_id, active_ids=[active_id])},
                     timeout_override=180)
    except Exception as e:
        err = str(e)[:240]
        print('  run aviso:', err)
    lg = o.execute_kw('ir.logging', 'search_read', [[('message', '=like', log_like)]],
                      {'fields': ['message'], 'order': 'id desc', 'limit': 1, 'context': CTX})
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"SA canary {sa} DELETADA")
    return (lg[0]['message'] if lg else None), err


# ── ESTÁGIO 1 — genealogia safe_eval vs oráculo (READ-only, ZERO NF) ──────────────
def modo_genealogia(o, nf1):
    # 1) ORÁCULO (Python testado) — READ
    oracle = DescobertaIndustrializacaoService(o).descobrir_fonte_nf2(nf1)
    exp_comps = sorted([(c['product_id'], round(c['qty'], 4)) for c in oracle['componentes']])
    print(f"ORÁCULO: ncomp={len(oracle['componentes'])} total={oracle['total']:.5f} "
          f"remessa_pick={oracle['remessa']['picking_id']}")

    # 2) corpo do canary = genealogia do SA_BODY_G1 (truncada antes da montagem) + log
    head = SA_BODY_G1.split('# === MONTAGEM')[0].rstrip()
    canary = head + (
        "\n        _total = sum(acc[p.id] * precos.get(p.id, p.standard_price) for p in comps)"
        "\n        _comps = sorted([(p.id, round(acc[p.id], 4)) for p in comps])"
        "\n        log('CANARY-G1 ncomp=%s total=%s chave=%s comps=%s' % "
        "(len(comps), round(_total, 5), chave_remessa or 'FALTA', str(_comps)))\n")

    # 3) SA EFÊMERA read-only (NADA de account.move) — create → run(active_id=nf1) → unlink
    msg, err = _run_sa_efemera(o, canary, name='ZZ CANARY G1 READONLY - DELETAR',
                               active_id=nf1, log_like='CANARY-G1 %')
    if not msg:
        print('❌ sem log CANARY-G1 — a SA não chegou ao log (genealogia errou OU pulou; ver run aviso):', err)
        return

    print('\nLOG:', msg[:700])
    m = re.search(r'ncomp=(\d+) total=([\d.]+) chave=(\S+) comps=(\[.*\])', msg)
    if not m:
        print('❌ log não parseável'); return
    sa_n, sa_total, sa_chave = int(m.group(1)), float(m.group(2)), m.group(3)
    sa_comps = sorted(eval(m.group(4)))

    print('\n=== COMPARAÇÃO body(safe_eval) vs ORÁCULO ===')
    ok_n = sa_n == len(oracle['componentes'])
    ok_t = abs(sa_total - oracle['total']) < 0.01
    ok_c = sa_chave == CHAVE_REMESSA_ESPERADA
    ok_comps = sa_comps == exp_comps
    print(f"  ncomp:  body={sa_n} oráculo={len(oracle['componentes'])}  {'✅' if ok_n else '❌ DIVERGE'}")
    print(f"  total:  body={sa_total:.5f} oráculo={oracle['total']:.5f}  {'✅' if ok_t else '❌ DIVERGE'}")
    print(f"  chave:  body={sa_chave[:20]}...  {'✅' if ok_c else '❌ DIVERGE'}")
    print(f"  comps:  {'✅ idênticos (product_id+qty)' if ok_comps else '❌ DIVERGE'}")
    if not ok_comps:
        print('    body :', sa_comps)
        print('    orácl:', exp_comps)
    print('\n' + ('✅✅ CANARY G1 GENEALOGIA OK — safe_eval == oráculo'
                  if all([ok_n, ok_t, ok_c, ok_comps]) else '❌ CANARY G1 FALHOU — corrigir antes de prosseguir'))


# ── ESTÁGIO 2 — montagem → DRAFT NF-2 (gate go fresco) ────────────────────────────
def modo_montagem(o, nf1, *, confirmar):
    # corpo = SA_BODY_G1 truncado ANTES do action_post (genealogia+montagem+recompute+remap+R3) + log
    head = SA_BODY_G1.split('# === POST')[0].rstrip()
    canary = head + (
        "\n        _nl = len(nf2.invoice_line_ids.filtered(lambda x: x.display_type == 'product'))"
        "\n        log('CANARY-G1-MONTAGEM nf2=%s state=%s journal=%s n_linhas=%s total=%s origin=%s refs=%s' % "
        "(nf2.id, nf2.state, nf2.journal_id.id, _nl, nf2.amount_untaxed, nf2.invoice_origin, len(nf2.referencia_ids)))\n")

    if not confirmar:
        print("DRY-RUN — corpo do canary de montagem (NÃO roda a SA, NÃO cria draft).")
        print("Trunca SA_BODY_G1 em '# === POST' → monta a NF-2 e PARA antes do action_post.\n")
        print("--- final do corpo (após o R3, com o log de montagem) ---")
        print(canary[-900:])
        print("\n🔴 Para CRIAR o draft (1 account.move em RETIND 1083, gate go FRESCO): adicione --confirmar")
        return

    msg, err = _run_sa_efemera(o, canary, name='ZZ CANARY G1 MONTAGEM - DELETAR DRAFT DEPOIS',
                               active_id=nf1, log_like='CANARY-G1-MONTAGEM %')
    if not msg:
        print('❌ sem log CANARY-G1-MONTAGEM — a montagem não chegou ao log (ver run aviso):', err)
        return

    print('\nLOG:', msg[:700])
    m = re.search(r'nf2=(\d+) state=(\S+) journal=(\d+) n_linhas=(\d+) total=([\d.]+) origin=(\S+) refs=(\d+)', msg)
    if not m:
        print('❌ log não parseável'); return
    nf2_id, state, journal, nl, total, refs = (int(m.group(1)), m.group(2), int(m.group(3)),
                                               int(m.group(4)), float(m.group(5)), int(m.group(7)))
    print(f"\n✅ DRAFT criado: nf2_id={nf2_id} state={state} journal={journal} "
          f"n_linhas={nl} total={total:.5f} refs={refs}")
    if state not in ('draft', 'False'):
        print(f"  ⚠️ state={state} (esperado draft — o truncamento NÃO deveria ter postado!)")
    if journal != RETIND:
        print(f"  ⚠️ journal={journal} (esperado RETIND {RETIND})")
    print(f"\nPRÓXIMO (READ — validar vs oráculo):\n"
          f"  python -m app.odoo.estoque.orchestrators.saida_retorno_industrializacao validar "
          f"--nf1-servico {nf1} --nf2-id {nf2_id}")
    print(f"CLEANUP (gate go FRESCO):\n"
          f"  python {os.path.relpath(sys.argv[0])} --deletar {nf2_id} --confirmar")


# ── CLEANUP — deletar o draft do estágio 2 (guard state+journal) ──────────────────
def modo_deletar(o, nf2_id, *, confirmar):
    rows = o.execute_kw('account.move', 'read',
                        [[nf2_id], ['state', 'journal_id', 'name', 'invoice_origin']], {'context': CTX})
    if not rows:
        print(f'❌ account.move {nf2_id} não encontrado'); return
    mv = rows[0]
    jid = mv['journal_id'][0] if isinstance(mv['journal_id'], list) else mv['journal_id']
    print(f"alvo: nf2={nf2_id} name={mv.get('name')} state={mv['state']} journal={jid} origin={mv.get('invoice_origin')}")
    # GUARDS — nunca deletar algo postado ou de outro journal
    if mv['state'] not in ('draft', False):
        print(f"❌ GUARD: state={mv['state']} (só deleto draft) — abortado"); return
    if jid != RETIND:
        print(f"❌ GUARD: journal={jid} (esperado RETIND {RETIND}) — abortado"); return
    if not confirmar:
        print(f"\nDRY-RUN — passaria nos guards. Para DELETAR: --deletar {nf2_id} --confirmar"); return
    o.execute_kw('account.move', 'unlink', [[nf2_id]], {'context': CTX})
    print(f"✅ draft {nf2_id} DELETADO (zero rabo)")


# ── ESTÁGIO 3 — postar a NF-2 (baixa PASSIVA) / reverter (gate go fresco) ──────────
def modo_postar(o, nf2_id, *, confirmar):
    # POST server-side (igual ao regime de produção: o body G1 faz nf2.action_post()).
    # action_post baixa a PASSIVA 26667 (lançamento contábil). NÃO transmite SEFAZ (cstat vazio).
    code = (
        "nf2 = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "_before = nf2.state\n"
        "_err = ''\n"
        "try:\n"
        "    nf2.action_post()\n"
        "except Exception as e:\n"
        "    _err = str(e)[:200]\n"
        "log('CANARY-G1-POST nf2=%%s before=%%s state=%%s cstat=%%s err=%%s' %% "
        "(nf2.id, _before, nf2.state, nf2.l10n_br_cstat_nf or 'vazio', _err))\n" % nf2_id)
    if not confirmar:
        print("DRY-RUN — corpo da SA de POST (server-side, NÃO roda):\n")
        print(code)
        print("🔴 action_post baixa a PASSIVA 26667 (lançamento contábil; journal hash=False, "
              "REVERSÍVEL). NÃO transmite SEFAZ (cstat fica vazio). Para postar: --confirmar")
        return
    msg, err = _run_sa_efemera(o, code, name='ZZ CANARY G1 POST - REVERTER DEPOIS',
                               active_id=nf2_id, log_like='CANARY-G1-POST %')
    if not msg:
        print('❌ sem log CANARY-G1-POST — o post não chegou ao log (ver run aviso):', err); return
    print('\nLOG:', msg[:400])
    m = re.search(r'nf2=(\d+) before=(\S+) state=(\S+) cstat=(\S+) err=(.*)', msg)
    if not m:
        print('❌ log não parseável'); return
    nid, before, state, cstat, perr = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    print(f"\n{'✅' if state == 'posted' else '❌'} POST: nf2={nid} {before}→{state} cstat={cstat} "
          f"err={perr or '(nenhum)'}")
    if cstat not in ('vazio', 'False'):
        print(f"  🔴 ATENÇÃO: cstat={cstat} (esperado vazio — action_post NÃO deveria transmitir SEFAZ!)")
    print(f"\nPRÓXIMO (READ — baixa PASSIVA pelo ciclo):\n"
          f"  python -m app.odoo.estoque.orchestrators.saida_retorno_industrializacao medir "
          f"--nf1-servico 791437 --nf2-id {nid}")
    print(f"CLEANUP (gate go FRESCO — desfaz o post):\n"
          f"  python {os.path.relpath(sys.argv[0])} --reverter {nid} --confirmar")


def modo_reverter(o, nf2_id, *, confirmar):
    """Cleanup do estágio 3: posted→draft (button_draft, journal hash=False)→unlink. Guard journal."""
    rows = o.execute_kw('account.move', 'read',
                        [[nf2_id], ['state', 'journal_id', 'name', 'invoice_origin']], {'context': CTX})
    if not rows:
        print(f'❌ account.move {nf2_id} não encontrado'); return
    mv = rows[0]
    jid = mv['journal_id'][0] if isinstance(mv['journal_id'], list) else mv['journal_id']
    print(f"alvo: nf2={nf2_id} name={mv.get('name')} state={mv['state']} journal={jid} origin={mv.get('invoice_origin')}")
    if jid != RETIND:
        print(f"❌ GUARD: journal={jid} (esperado RETIND {RETIND}) — abortado"); return
    if mv['state'] not in ('posted', 'draft'):
        print(f"❌ GUARD: state={mv['state']} (só posted/draft) — abortado"); return
    if not confirmar:
        print(f"\nDRY-RUN — passaria nos guards. Para REVERTER+DELETAR: --reverter {nf2_id} --confirmar"); return
    if mv['state'] == 'posted':
        o.execute_kw('account.move', 'button_draft', [[nf2_id]], {'context': CTX})
        print('  posted → draft (button_draft)')
    o.execute_kw('account.move', 'unlink', [[nf2_id]], {'context': CTX})
    print(f"✅ nf2 {nf2_id} REVERTIDO + DELETADO (zero rabo)")


def main():
    ap = argparse.ArgumentParser(description='Canary do body G1 (estágios 1-3 do RUNBOOK fluxo 1.1.4).')
    ap.add_argument('nf1', nargs='?', type=int, default=791437,
                    help='NF-1 serviço de SAÍDA (default piloto 791437)')
    ap.add_argument('--montagem', action='store_true',
                    help='estágio 2: monta a NF-2 em DRAFT (gate --confirmar)')
    ap.add_argument('--postar', type=int, metavar='NF2_ID', default=None,
                    help='estágio 3: posta o draft da NF-2 — baixa PASSIVA (gate --confirmar)')
    ap.add_argument('--deletar', type=int, metavar='NF2_ID', default=None,
                    help='cleanup do draft do estágio 2 (guard: state=draft + journal RETIND)')
    ap.add_argument('--reverter', type=int, metavar='NF2_ID', default=None,
                    help='cleanup do estágio 3: posted→draft→unlink (guard: journal RETIND)')
    ap.add_argument('--confirmar', action='store_true',
                    help='EXECUTA a escrita Odoo (default = dry-run). 🔴 go FRESCO por escrita.')
    args = ap.parse_args()

    o = get_odoo_connection(); assert o.authenticate(), 'FALHA AUTH'
    if args.reverter is not None:
        modo_reverter(o, args.reverter, confirmar=args.confirmar)
    elif args.deletar is not None:
        modo_deletar(o, args.deletar, confirmar=args.confirmar)
    elif args.postar is not None:
        modo_postar(o, args.postar, confirmar=args.confirmar)
    elif args.montagem:
        modo_montagem(o, args.nf1, confirmar=args.confirmar)
    else:
        modo_genealogia(o, args.nf1)


if __name__ == '__main__':
    main()
