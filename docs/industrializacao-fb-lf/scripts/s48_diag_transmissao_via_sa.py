#!/usr/bin/env python3
"""S48 — DIAGNOSTICO READ-only: a transmissao SEFAZ da' p/ fazer via SERVER ACTION
(server-side) em vez de Playwright (browser)?

Pergunta do Rafael (2026-06-14). O provado e' Playwright (UI forca recompute dos
nfe_infnfe_* -> cstat 100; XML-RPC direto deixa stale -> SEFAZ 225). A via SA NAO foi
testada. Este script LE o mecanismo p/ responder com fato:

  1. Os campos nfe_infnfe_* sao COMPUTE (auto, recomputam server-side) ou ONCHANGE
     (so disparam na UI / chamada explicita)? -> define se uma SA consegue forca-los.
  2. Quais botoes/metodos a view form do account.move expoe p/ NFe (preview/transmitir)
     -> o nome do metodo que a SA chamaria.
  3. O metodo do "Pre Visualizar XML" existe como metodo publico chamavel server-side?

READ-ONLY. Nao escreve, nao transmite.
"""
import sys
import re
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 791437   # NF de servico posted (referencia p/ ler estado dos campos)


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # ---- 1. campos nfe_infnfe_* : compute vs onchange ----
    print("=" * 92)
    print("### 1. CAMPOS nfe_infnfe_* — compute (auto server-side) vs nao-stored/onchange")
    print("=" * 92)
    fg = o.execute_kw('account.move', 'fields_get', [],
                      {'attributes': ['string', 'type', 'store', 'readonly', 'related', 'depends'], 'context': CTX})
    infnfe = sorted([f for f in fg if f.startswith('nfe_infnfe') or 'infnfe' in f.lower()])
    print(f"  {len(infnfe)} campos infnfe. Amostra (store/depends define se a SA recomputa):")
    amostra = infnfe[:18]
    n_compute = 0; n_store = 0
    for f in amostra:
        meta = fg[f]
        dep = meta.get('depends')
        st = meta.get('store')
        is_compute = bool(dep)  # campo com depends = computed
        if is_compute: n_compute += 1
        if st: n_store += 1
        print(f"    {f:34} type={meta.get('type'):8} store={st} depends={dep if dep else '-'}")
    total_compute = sum(1 for f in infnfe if fg[f].get('depends'))
    total_store = sum(1 for f in infnfe if fg[f].get('store'))
    print(f"  >>> dos {len(infnfe)}: {total_compute} tem depends (computed), {total_store} stored.")
    print(f"      computed+stored => recomputam server-side (a SA conseguiria forcar via .modified()/recompute).")
    print(f"      sem depends/store => populados por metodo (preview/gerar) — achar o metodo (passo 2).")

    # ---- 2. botoes NFe na view form (arch) ----
    print("\n" + "=" * 92)
    print("### 2. BOTOES/METODOS de NFe na view form do account.move")
    print("=" * 92)
    views = rr('ir.ui.view', [('model', '=', 'account.move'), ('type', '=', 'form')],
               ['name', 'arch_db'], limit=80)
    metodos = {}   # name -> string do botao
    for v in views:
        arch = v.get('arch_db') or ''
        if 'nfe' not in arch.lower() and 'xml' not in arch.lower():
            continue
        for m in re.finditer(r'<button\b[^>]*>', arch):
            tag = m.group(0)
            nm = re.search(r'name="([^"]+)"', tag)
            if not nm:
                continue
            name = nm.group(1)
            if not any(k in name.lower() for k in ['nfe', 'xml', 'sefaz', 'transmit', 'envio', 'preview', 'previa', 'gerar']):
                continue
            stt = re.search(r'string="([^"]*)"', tag)
            metodos[name] = stt.group(1) if stt else metodos.get(name, '')
    if metodos:
        for name, label in sorted(metodos.items()):
            tipo = 'metodo Python' if not name.startswith('%') else 'action'
            print(f"    name={name:42} string={label!r:34} ({tipo})")
    else:
        print("    (nenhum botao nfe/xml achado nas views form — pode estar em template herdado)")
    print(f"\n  >>> o botao 'Pre Visualizar XML NF-e' e o 'Transmitir/Gerar NF-e' chamam estes metodos.")
    print(f"      Uma SA pode chamar o MESMO metodo server-side (ex.: nf.<metodo>()).")

    # ---- 3. metodos publicos candidatos existem? ----
    print("\n" + "=" * 92)
    print("### 3. METODOS candidatos chamaveis server-side (existencia)")
    print("=" * 92)
    candidatos = ['action_gerar_nfe', 'gerar_nfe', 'action_preview_danfe', 'preview_xml_nfe',
                  'action_visualizar_xml', 'action_pre_visualizar_xml', 'l10n_br_gerar_nfe',
                  'action_post', 'button_nfe_enviar', 'action_send_nfe']
    # nao ha introspeccao direta de metodos via XML-RPC; inferimos pelos names dos botoes (passo 2)
    achados = [c for c in candidatos if c in metodos]
    print(f"    candidatos presentes como botao (confirmados): {achados or '(nenhum nos names; ver passo 2)'}")
    print(f"    >>> metodo de transmissao = o name do botao 'Transmitir/Gerar NF-e' do passo 2.")
    print(f"\n  CONCLUSAO p/ decisao SA-vs-Playwright:")
    print(f"    - se nfe_infnfe_* sao COMPUTED (passo 1): SA forca recompute (.modified/.flush) + chama o metodo (passo 2) => SA VIAVEL (a testar — rejeicao 225 e' recuperavel).")
    print(f"    - se sao populados pelo metodo preview: a SA chama preview_xml + transmitir, mesma sequencia da UI, server-side.")
    print(f"    - PROVADO ate aqui: so Playwright (NFe 93549). SA = hipotese plausivel NAO testada.")


if __name__ == '__main__':
    main()
