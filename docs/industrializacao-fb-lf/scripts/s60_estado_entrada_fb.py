#!/usr/bin/env python3
"""S60 — FOTOGRAFA (READ-only) o estado da ENTRADA na FB (R2 / Etapa 5).

Responde 5 perguntas que fundamentam o plano do R2:
  1. As 2 NFs de retorno (LF->FB) estao autorizadas + tem XML para escriturar?
  2. Ja existe DFe na FB (company 1) com essas chaves? (a SEFAZ pode ter
     distribuido o DFe-resumo ao destinatario FB automaticamente.)
  3. Quais journals FB de ENTRADA (purchase) existem e qual o no_payment de
     cada um? (preciso de um que baixe a ATIVA 5101010001=22800 -> espelho do
     RETIND 1083 da LF; gap de config do lado FB.)
  4. A op de entrada 3252 (movimento_estoque=False) existe e esta correta?
  5. pt52 (FB entrada retorno src=26489) — config.

READ-ONLY. Producao (CIEL IT).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

# allowed [1,5]: preciso ler a NF (company LF=5) E o DFe/journals (FB=1)
CTX = {'allowed_company_ids': [1, 5], 'company_id': 1, 'lang': 'pt_BR'}

NF1, NF2 = 791437, 791441
CHAVE1 = '35260618467441000163550010000133131007914378'  # NF-1 servico 5124
CHAVE2 = '35260618467441000163550010000133141007914413'  # NF-2 insumos 5902
CONTA_ATIVA_FB = 22800   # 5101010001 (estoque em poder de terceiros) — alvo da baixa
CONTA_PASSIVA_FB = 22815  # 5101020001
DFE_MODEL = 'l10n_br_ciel_it_account.dfe'
SEP = '=' * 96


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}
        kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    print(SEP)
    print('S60 — ESTADO DA ENTRADA FB (R2 / Etapa 5)')
    print(SEP)

    # ---- 1. As 2 NFs de saida (LF->FB) autorizadas + XML presente? ----------
    print('\n[1] NFs de retorno (saida LF) — autorizacao + XML para escriturar')
    nfs = rd('account.move', [NF1, NF2],
             ['name', 'state', 'l10n_br_chave_nf', 'l10n_br_cstat_nf',
              'l10n_br_xml_aut_nfe', 'company_id', 'partner_id',
              'l10n_br_numero_nota_fiscal', 'invoice_origin', 'amount_untaxed'])
    for nf in sorted(nfs, key=lambda x: x['id']):
        xml = nf.get('l10n_br_xml_aut_nfe')
        print(f"  {nf['name']} (id {nf['id']}) state={nf['state']} "
              f"cstat={nf.get('l10n_br_cstat_nf')} "
              f"company={nf['company_id']} partner={nf['partner_id']}")
        print(f"      chave={nf.get('l10n_br_chave_nf')}")
        print(f"      XML_aut={'PRESENTE %d b' % len(xml) if xml else 'AUSENTE'} "
              f"untax={nf.get('amount_untaxed')} origin={nf.get('invoice_origin')}")

    # ---- 2. Ja existe DFe na FB (company 1) p/ essas chaves? -----------------
    print('\n[2] DFe na FB (company 1) p/ as 2 chaves — a SEFAZ ja distribuiu?')
    for tag, chave in (('NF-1', CHAVE1), ('NF-2', CHAVE2)):
        dfes = rr(DFE_MODEL,
                  [('protnfe_infnfe_chnfe', '=', chave), ('company_id', '=', 1)],
                  ['id', 'l10n_br_status', 'l10n_br_situacao_dfe',
                   'nfe_infnfe_ide_nnf', 'purchase_id', 'company_id'])
        if not dfes:
            # busca tambem SEM filtro de company (resumo pode ter caido noutra)
            qualquer = rr(DFE_MODEL, [('protnfe_infnfe_chnfe', '=', chave)],
                          ['id', 'company_id', 'l10n_br_status'])
            print(f"  {tag}: NENHUM DFe na FB. (qualquer company: {qualquer})")
        else:
            for d in dfes:
                nlin = o.execute_kw('l10n_br_ciel_it_account.dfe.line',
                                    'search_count',
                                    [[('dfe_id', '=', d['id'])]], {'context': CTX})
                print(f"  {tag}: DFe {d['id']} status={d.get('l10n_br_status')} "
                      f"situacao={d.get('l10n_br_situacao_dfe')} "
                      f"PO={d.get('purchase_id')} linhas={nlin}")

    # ---- 3. Journals FB de ENTRADA (purchase) + no_payment ------------------
    print('\n[3] Journals FB (company 1, type=purchase) + no_payment')
    # descobrir campos *payment*/*tipo_pedido* do journal
    jf = o.execute_kw('account.journal', 'fields_get', [],
                      {'attributes': ['string'], 'context': CTX})
    pay_fields = [f for f in jf if 'no_payment' in f or 'payment_id' in f]
    extra = [f for f in ('l10n_br_tipo_pedido', 'account_no_payment_id',
                         'l10n_br_no_payment') if f in jf]
    read_fields = ['id', 'name', 'code', 'type', 'company_id'] + sorted(set(pay_fields + extra))
    print(f"  (campos no_payment detectados: {sorted(set(pay_fields+extra))})")
    journals = rr('account.journal',
                  [('company_id', '=', 1), ('type', '=', 'purchase')],
                  read_fields, order='id')
    for j in journals:
        nop = j.get('account_no_payment_id')
        flag = ''
        if nop and isinstance(nop, list) and nop[0] == CONTA_ATIVA_FB:
            flag = '  <<< BAIXA ATIVA 5101010001 (alvo!)'
        print(f"  j{j['id']} [{j.get('code')}] {j['name'][:42]:42} "
              f"no_payment={nop} tipo_pedido={j.get('l10n_br_tipo_pedido')}"
              f"{flag}")

    # ---- 4. op de entrada 3252 (movimento_estoque=False) --------------------
    print('\n[4] Operacao 3252 (entrada 1902, movimento_estoque=False)')
    op_model = 'l10n_br_ciel_it_account.operacao'
    op = rr(op_model, [('id', '=', 3252)],
            ['id', 'name', 'company_id', 'l10n_br_tipo_pedido',
             'l10n_br_movimento_estoque', 'l10n_br_tipo_operacao',
             'intra_cfop', 'inter_cfop'])
    print(f"  {op if op else 'op 3252 NAO encontrada'}")

    # ---- 5. pt52 (FB entrada retorno) ---------------------------------------
    print('\n[5] picking_type pt52 (FB entrada retorno)')
    pt = rr('stock.picking.type', [('id', '=', 52)],
            ['id', 'name', 'code', 'company_id',
             'default_location_src_id', 'default_location_dest_id',
             'l10n_br_tipo_pedido'])
    print(f"  {pt if pt else 'pt52 NAO encontrado'}")

    print('\n' + SEP)
    print('FIM S60')
    print(SEP)


if __name__ == '__main__':
    main()
