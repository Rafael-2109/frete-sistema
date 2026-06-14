#!/usr/bin/env python3
"""S49 — TESTE REVERSIVEL: o recompute do XML da' p/ forcar via SERVER ACTION?
Roda `action_previsualizar_xml_nfe()` (= o botao "Pre Visualizar XML NF-e" que o Playwright
clica p/ destravar o SEFAZ 225) SERVER-SIDE numa SA, na NF-1 posted. NAO transmite.

Mede os campos de XML/NFe ANTES vs DEPOIS: se algo materializa server-side, a via SA esta'
validada p/ o recompute (e a transmissao via `action_gerar_nfe` na SA fica plausivel).
Se nada muda, o recompute exige a UI (Playwright).

REVERSIVEL: preview nao transmite (NF segue posted, situacao=rascunho). Cleanup via s37.

MODOS:
  (sem flag)   READ: lista os campos xml/nfe da NF-1 + valores atuais (lens)
  --executar   SA roda action_previsualizar_xml_nfe na NF-1 + mede diff antes/depois
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 791437   # NF-1 servico posted (VND/2026/00384)
KEYS = ['xml', 'nfe', 'infnfe', 'chave', 'situacao', 'motivo', 'cstat', 'protocolo',
        'autoriz', 'danfe', 'valida', 'recibo', 'lote']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    ap.add_argument('--nf1', type=int, default=NF1)
    args = ap.parse_args()
    nf = args.nf1
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    campos = sorted([f for f in fg if any(k in f.lower() for k in KEYS)
                     and fg[f].get('type') not in ('one2many', 'many2many')])

    def snap():
        rec = rr('account.move', [('id', '=', nf)], campos)
        if not rec:
            return {}
        r = rec[0]
        out = {}
        for f in campos:
            v = r.get(f)
            if isinstance(v, str) and len(v) > 40:
                out[f] = f"<str len={len(v)}>"
            elif isinstance(v, list):
                out[f] = f"m2o:{v[1] if len(v) > 1 else v}"
            else:
                out[f] = v
        return out

    print("=" * 92)
    print(f"S49 — preview XML via SA (REVERSIVEL) na NF-1 {nf}")
    print("=" * 92)
    antes = snap()
    print(f"  {len(campos)} campos xml/nfe. Estado ANTES (nao-vazios):")
    for f in campos:
        if antes.get(f) not in (False, None, '', 0, 0.0):
            print(f"    {f:40} = {antes[f]}")

    if not args.executar:
        print("\n  [DRY-RUN] nada escrito. Aplicar (reversivel, nao transmite): --executar")
        return

    code = (
        "nf = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(%d)\n"
        "res=None; err=''\n"
        "try:\n"
        "    res = nf.action_previsualizar_xml_nfe()\n"
        "except Exception as e:\n"
        "    err=str(e)[:240]\n"
        "rk = (sorted(list(res.keys()))[:8] if isinstance(res, dict) else 'nao-dict')\n"
        "log('S49-RESULT inv=%%s ret_keys=%%s err=%%s situacao=%%s chave=%%s' %% (str(nf.ids), str(rk), err, nf.l10n_br_situacao_nf, nf.l10n_br_chave_nf))\n"
    ) % nf
    model_id = o.execute_kw('ir.model', 'search', [[('model', '=', 'account.move')]], {'context': CTX})[0]
    sa = o.execute_kw('ir.actions.server', 'create',
                      [{'name': 'ZZ TESTE S49 PREVIEW XML - DELETAR', 'model_id': model_id,
                        'state': 'code', 'code': code}], {'context': CTX})
    print(f"\n  SA {sa} criada; rodando action_previsualizar_xml_nfe server-side...")
    try:
        o.execute_kw('ir.actions.server', 'run', [[sa]],
                     {'context': dict(CTX, active_model='account.move', active_id=False, active_ids=[])})
    except Exception as e:
        print(f"  SA run aviso: {str(e)[:200]}")
    lg = rr('ir.logging', [('message', '=like', 'S49-RESULT%')], ['message'], order='id desc', limit=1)
    if lg:
        print(f"  LOG: {lg[0]['message'][:400]}")
    o.execute_kw('ir.actions.server', 'unlink', [[sa]], {'context': CTX})
    print(f"  SA {sa} DELETADA")

    depois = snap()
    print(f"\n  === DIFF (campos que MUDARAM com o preview) ===")
    mudou = [f for f in campos if antes.get(f) != depois.get(f)]
    if mudou:
        for f in mudou:
            print(f"    {f:40} {antes.get(f)}  ->  {depois.get(f)}")
        print(f"\n  >>> ✅ o preview server-side MATERIALIZOU {len(mudou)} campo(s) => via SA VIAVEL p/ recompute.")
        print(f"      Proximo: transmitir via SA (action_gerar_nfe) — IRREVERSIVEL, go.")
    else:
        print(f"    (nenhum campo mudou)")
        print(f"\n  >>> ⚠️ preview nao persistiu campos via SA. Pode ainda ter recomputado interno;")
        print(f"      decisao segura = Playwright (s47). Ou testar action_gerar_nfe direto via SA (risco 225 recuperavel).")


if __name__ == '__main__':
    main()
