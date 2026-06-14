#!/usr/bin/env python3
"""S54 — FASE B via SERVER ACTION (alternativa ao Playwright/s47). Transmite as 2 NFs ao
SEFAZ chamando, numa SA server-side, a MESMA sequencia do Playwright:
    nf.action_previsualizar_xml_nfe()   # = clicar "Pre Visualizar XML" -> forca recompute do XML
    nf.action_gerar_nfe()               # = clicar "Transmitir NF-e"     -> envia a' SEFAZ
Numa SA os 2 rodam na MESMA transacao (o recompute do preview fica no cache p/ o gerar_nfe).

Provado (s49): o preview roda server-side SEM erro apos os gaps de cadastro corrigidos
(incoterm/s51 + pagamento+carrier/s53). Falta a transmissao real (IRREVERSIVEL, tpAmb=1).

🔴 IRREVERSIVEL: action_gerar_nfe envia a' SEFAZ PRODUCAO. Rejeicao (cstat!=100) e' RECUPERAVEL
(NF nao autoriza, corrige e reenvia OU cai no Playwright). Autorizacao (cstat=100) e' final.

SAGA (1 go por transmissao):
  --transmitir-nf1 NF1       SA preview+gerar na NF-1 + polling cstat
  --transmitir-nf2 NF1 NF2   cross-refNFe (chave NF-1 -> NF-2) + SA preview+gerar na NF-2
  --validar NF1 NF2          delega ao s47 --validar (cstat=100 + baixa + refNFe)

MODOS:
  (sem flag) NF1 NF2   dry-run: estado + plano
Opcoes: --poll-ciclos N (default 12) --poll-intervalo SEG (default 15)
"""
import sys
import time
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
LF = 5
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


def chave_ok(c):
    return bool(c) and len(str(c)) == 44


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nfs', nargs='*', type=int)
    ap.add_argument('--transmitir-nf1', type=int, metavar='NF1_ID')
    ap.add_argument('--transmitir-nf2', nargs=2, type=int, metavar=('NF1_ID', 'NF2_ID'))
    ap.add_argument('--saga', nargs=2, type=int, metavar=('NF1_ID', 'NF2_ID'),
                    help='ENCADEIA as 2: transmite NF-1 -> cross-ref -> transmite NF-2 (1 execucao)')
    ap.add_argument('--confirmar', action='store_true', help='go DUPLO p/ a --saga (irreversivel)')
    ap.add_argument('--poll-ciclos', type=int, default=12)
    ap.add_argument('--poll-intervalo', type=int, default=15)
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(ids, fields):
        return o.execute_kw('account.move', 'read', [list(ids)], {'fields': fields, 'context': CTX})

    SEFAZ = ['name', 'state', 'l10n_br_situacao_nf', 'l10n_br_chave_nf', 'l10n_br_cstat_nf',
             'l10n_br_xmotivo_nf', 'l10n_br_total_nfe']

    def estado(nf):
        h = rd([nf], SEFAZ)
        return h[0] if h else None

    def transmitir_sa(nf):
        """Roda a SA (preview + gerar_nfe) e faz polling do cstat/chave."""
        code = (
            "nf = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
            "err=''\n"
            "try:\n"
            "    nf.action_previsualizar_xml_nfe()\n"
            "except Exception as e:\n"
            "    err='preview:'+str(e)[:120]\n"
            "try:\n"
            "    nf.action_gerar_nfe()\n"
            "except Exception as e:\n"
            "    err=err+' gerar:'+str(e)[:200]\n"
            "log('S54-RESULT inv=%%s situacao=%%s cstat=%%s chave=%%s xmotivo=%%s err=%%s' %% (str(nf.ids), nf.l10n_br_situacao_nf, nf.l10n_br_cstat_nf, nf.l10n_br_chave_nf, (nf.l10n_br_xmotivo_nf or '')[:70], err))\n"
        ) % nf
        model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
        sa = o.execute_kw('ir.actions.server', 'create',
                          [{'name': 'ZZ S54 TRANSMITIR VIA SA - DELETAR', 'model_id': model_id,
                            'state': 'code', 'code': code}], {'context': CTX})
        print(f"  SA {sa} criada; rodando action_previsualizar_xml_nfe + action_gerar_nfe server-side...")
        try:
            o.execute_kw('ir.actions.server', 'run', [[sa]],
                         {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])},
                         timeout_override=180)
        except Exception as e:
            print(f"  SA run aviso: {str(e)[:200]}")
        lg = rr('ir.logging', [('message', '=like', 'S54-RESULT%')], ['message'], order='id desc', limit=1)
        if lg:
            print(f"  LOG: {lg[0]['message'][:400]}")
        o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
        # polling
        for i in range(args.poll_ciclos):
            h = estado(nf)
            sit = h.get('l10n_br_situacao_nf'); chave = h.get('l10n_br_chave_nf'); cstat = h.get('l10n_br_cstat_nf')
            print(f"    poll {i+1}/{args.poll_ciclos}: situacao={sit} cstat={cstat} chave={'OK' if chave_ok(chave) else (chave or '-')} xmotivo={(h.get('l10n_br_xmotivo_nf') or '')[:50]}")
            if sit in ('autorizado', 'excecao_autorizado') and chave_ok(chave):
                return {'sucesso': True, 'chave': chave, 'cstat': cstat, 'situacao': sit, 'name': h.get('name')}
            if sit in ('rejeitado', 'erro', 'denegado'):
                return {'sucesso': False, 'cstat': cstat, 'situacao': sit, 'xmotivo': h.get('l10n_br_xmotivo_nf')}
            if i < args.poll_ciclos - 1:
                time.sleep(args.poll_intervalo)
        h = estado(nf)
        return {'sucesso': chave_ok(h.get('l10n_br_chave_nf')) and h.get('l10n_br_situacao_nf') == 'autorizado',
                'cstat': h.get('l10n_br_cstat_nf'), 'situacao': h.get('l10n_br_situacao_nf'),
                'chave': h.get('l10n_br_chave_nf'), 'xmotivo': h.get('l10n_br_xmotivo_nf')}

    # ===== TRANSMITIR NF-1 =====
    if args.transmitir_nf1:
        nf1 = args.transmitir_nf1
        h = estado(nf1)
        assert h, "NF-1 inexistente"
        if h['state'] != 'posted':
            print(f"  ❌ NF-1 {nf1} state={h['state']} (precisa posted)"); return
        if h.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h.get('l10n_br_chave_nf')):
            print(f"  ✅ NF-1 JA autorizada: chave={h['l10n_br_chave_nf']}"); return
        print("=" * 92)
        print(f"### TRANSMITINDO NF-1 (servico) {nf1} {h.get('name')} VIA SA — SEFAZ PRODUCAO, IRREVERSIVEL")
        print("=" * 92)
        res = transmitir_sa(nf1)
        print(f"\n  RESULTADO NF-1: {res}")
        if res['sucesso']:
            print(f"  ✅ NF-1 AUTORIZADA — chave={res['chave']} | proximo: --transmitir-nf2 {nf1} <NF2>")
        else:
            print(f"  ❌ NF-1 nao autorizada (cstat={res.get('cstat')} situacao={res.get('situacao')} xmotivo={res.get('xmotivo')})")
            print(f"     rejeicao = recuperavel: corrigir o apontado + reenviar, OU usar Playwright (s47 --transmitir-nf1 {nf1}).")
        return

    # ===== CROSS-REF + TRANSMITIR NF-2 =====
    if args.transmitir_nf2:
        nf1, nf2 = args.transmitir_nf2
        h1 = estado(nf1); h2 = estado(nf2)
        assert h1 and h2, "NF inexistente"
        chave1 = h1.get('l10n_br_chave_nf')
        if not (h1.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(chave1)):
            print(f"  ❌ NF-1 ainda nao autorizada (chave={chave1}). Transmita a NF-1 antes."); return
        if h2['state'] != 'posted':
            print(f"  ❌ NF-2 {nf2} state={h2['state']}"); return
        if h2.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h2.get('l10n_br_chave_nf')):
            print(f"  ✅ NF-2 JA autorizada: chave={h2['l10n_br_chave_nf']}"); return
        # cross-refNFe chave NF-1 -> NF-2 (idempotente) ANTES de transmitir
        refs = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
        if chave1 in {r.get('l10n_br_chave_nf') for r in refs}:
            print(f"  [cross-ref] chave NF-1 ja' presente na NF-2 ({len(refs)} refNFe)")
        else:
            o.execute_kw('account.move', 'write', [[nf2], {
                'referencia_ids': [(0, 0, {'l10n_br_chave_nf': chave1, 'company_id': LF})]}],
                {'context': dict(CTX, check_move_validity=False)})
            refs = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
            print(f"  [cross-ref] chave NF-1 gravada na NF-2 ✅ ({len(refs)} refNFe: {[r['l10n_br_chave_nf'][-12:] for r in refs]})")
        print("=" * 92)
        print(f"### TRANSMITINDO NF-2 (insumos) {nf2} {h2.get('name')} VIA SA — SEFAZ PRODUCAO, IRREVERSIVEL")
        print("=" * 92)
        res = transmitir_sa(nf2)
        print(f"\n  RESULTADO NF-2: {res}")
        if res['sucesso']:
            print(f"  ✅ NF-2 AUTORIZADA — chave={res['chave']} | proximo: --validar {nf1} {nf2} (ou s47 --validar)")
        else:
            print(f"  ❌ NF-2 nao autorizada (cstat={res.get('cstat')} xmotivo={res.get('xmotivo')}). Rejeicao recuperavel.")
        return

    # ===== SAGA ENCADEADA: NF-1 -> cross-ref -> NF-2 (1 execucao, go duplo) =====
    if args.saga:
        nf1, nf2 = args.saga
        h1 = estado(nf1); h2 = estado(nf2)
        assert h1 and h2, "NF inexistente"
        print("=" * 92)
        print(f"### SAGA via SA — transmite NF-1 -> cross-refNFe -> transmite NF-2 (SEFAZ PRODUCAO, IRREVERSIVEL x2)")
        print("=" * 92)
        for label, h in [('NF-1 servico', h1), ('NF-2 insumos', h2)]:
            print(f"  {label} {h['id'] if 'id' in h else '?'} {h.get('name')}: state={h['state']} "
                  f"situacao={h.get('l10n_br_situacao_nf')} cstat={h.get('l10n_br_cstat_nf') or '-'} vNF={h.get('l10n_br_total_nfe')}")
        problemas = [f"NF-{i+1} state={h['state']}" for i, h in enumerate([h1, h2]) if h['state'] != 'posted']
        if not args.confirmar:
            print(f"\n  [DRY-RUN saga] go duplo: --saga {nf1} {nf2} --confirmar")
            print(f"  ordem: (1) transmite NF-1; se autorizar -> (2) grava chave NF-1 na NF-2 -> (3) transmite NF-2.")
            print(f"  se a NF-1 REJEITAR, a NF-2 NAO e' transmitida (aborta).")
            return
        if problemas:
            print(f"\n  ❌ ABORTADO: {problemas}"); return

        # (1) NF-1
        print(f"\n--- [1/3] TRANSMITINDO NF-1 {nf1} ---")
        if h1.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h1.get('l10n_br_chave_nf')):
            res1 = {'sucesso': True, 'chave': h1['l10n_br_chave_nf']}
            print(f"  (NF-1 ja autorizada: {res1['chave']})")
        else:
            res1 = transmitir_sa(nf1)
        print(f"  RESULTADO NF-1: {res1}")
        if not res1['sucesso']:
            print(f"\n  ❌ NF-1 nao autorizada -> SAGA ABORTADA (NF-2 NAO transmitida). "
                  f"Rejeicao recuperavel: corrigir + reenviar, ou Playwright (s47).")
            return
        chave1 = res1['chave']

        # (2) cross-refNFe chave NF-1 -> NF-2
        print(f"\n--- [2/3] CROSS-REFNFe: chave NF-1 -> NF-2 ---")
        refs = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
        if chave1 in {r.get('l10n_br_chave_nf') for r in refs}:
            print(f"  chave NF-1 ja' presente na NF-2 ({len(refs)} refNFe)")
        else:
            o.execute_kw('account.move', 'write', [[nf2], {
                'referencia_ids': [(0, 0, {'l10n_br_chave_nf': chave1, 'company_id': LF})]}],
                {'context': dict(CTX, check_move_validity=False)})
            refs = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
            print(f"  chave NF-1 gravada ✅ ({len(refs)} refNFe: {[r['l10n_br_chave_nf'][-12:] for r in refs]})")

        # (3) NF-2
        print(f"\n--- [3/3] TRANSMITINDO NF-2 {nf2} ---")
        h2b = estado(nf2)
        if h2b.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h2b.get('l10n_br_chave_nf')):
            res2 = {'sucesso': True, 'chave': h2b['l10n_br_chave_nf']}
            print(f"  (NF-2 ja autorizada: {res2['chave']})")
        else:
            res2 = transmitir_sa(nf2)
        print(f"  RESULTADO NF-2: {res2}")

        # resumo
        print("\n" + "=" * 92)
        f1 = estado(nf1); f2 = estado(nf2)
        print(f"  NF-1 {f1.get('name')}: situacao={f1.get('l10n_br_situacao_nf')} cstat={f1.get('l10n_br_cstat_nf')} chave={'OK' if chave_ok(f1.get('l10n_br_chave_nf')) else '-'}")
        print(f"  NF-2 {f2.get('name')}: situacao={f2.get('l10n_br_situacao_nf')} cstat={f2.get('l10n_br_cstat_nf')} chave={'OK' if chave_ok(f2.get('l10n_br_chave_nf')) else '-'}")
        if res1['sucesso'] and res2['sucesso']:
            print(f"\n  ✅✅ AS 2 AUTORIZADAS. >>> validar: python docs/industrializacao-fb-lf/scripts/s47_transmitir_saga_sefaz.py --validar {nf1} {nf2}")
        else:
            print(f"\n  ⚠️ NF-2 nao autorizada (NF-1 ja' transmitida). Rejeicao recuperavel — corrigir NF-2 + reenviar, ou Playwright (s47 --transmitir-nf2 {nf1} {nf2}).")
        return

    # ===== DRY-RUN =====
    if len(args.nfs) < 2:
        print("uso (dry-run): python s54_transmitir_via_sa.py NF1_ID NF2_ID"); return
    nf1, nf2 = args.nfs[0], args.nfs[1]
    print("=" * 92)
    print("S54 — DRY-RUN: transmissao via SA (preview + gerar_nfe server-side). NADA transmitido.")
    print("=" * 92)
    for label, nf in [('NF-1 servico', nf1), ('NF-2 insumos', nf2)]:
        h = estado(nf)
        if not h:
            print(f"  {label} {nf}: INEXISTENTE ❌"); continue
        print(f"  {label} {nf}: {h.get('name')} state={h['state']} situacao={h.get('l10n_br_situacao_nf')} "
              f"cstat={h.get('l10n_br_cstat_nf') or '-'} vNF={h.get('l10n_br_total_nfe')}")
    print(f"\n  PLANO (via SA, 1 go por transmissao):")
    print(f"    1) --transmitir-nf1 {nf1}        (SA preview+gerar, irreversivel)")
    print(f"    2) --transmitir-nf2 {nf1} {nf2}  (cross-ref + SA preview+gerar, irreversivel)")
    print(f"    3) --validar {nf1} {nf2}         (via s47)")


if __name__ == '__main__':
    main()
