#!/usr/bin/env python3
"""S61 — Journal FB de ENTRADA-INSUMOS (R2.1) — espelho do RETIND 1083 da LF.

A NF-2 (insumos 5902, op 3252 simbolica) escriturada na FB precisa baixar a
ATIVA 5101010001 (conta 22800 = "estoque em poder de terceiros"). NENHUM journal
FB de entrada aponta essa conta no no_payment hoje (s60). Este script cria um
journal dedicado (NAO mexe em j1001/j1011 — afetaria outros fluxos).

Espelho contabil:
  LF saida  (RETIND 1083): type=sale     no_payment=26667 (PASSIVA 5101020001 LF)
  FB entrada (este, novo): type=purchase no_payment=22800 (ATIVA  5101010001 FB)

Modos:
  --dry-run     (DEFAULT) mostra a spec + idempotencia (NAO escreve)
  --criar       cria o journal (escrita; reversivel via --deletar)
  --deletar ID  deleta o journal criado (cleanup)

PRODUCAO (CIEL IT). Escrita SO com --criar e go explicito.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 1, 'lang': 'pt_BR'}
CONTA_ATIVA_FB = 22800   # 5101010001 ESTOQUE EM PODER DE TERCEIROS (ATIVA)
SPEC = {
    'name': 'ENTRADA RETORNO INDUSTRIALIZACAO INSUMOS',
    'code': 'ENTRI',
    'type': 'purchase',
    'company_id': 1,                       # FB
    'l10n_br_no_payment': True,
    'account_no_payment_id': CONTA_ATIVA_FB,
    'default_account_id': CONTA_ATIVA_FB,  # espelha o ENTIN FB (default=no_payment)
    'restrict_mode_hash_table': False,     # reversivel (entrada NAO vai SEFAZ)
    # l10n_br_tipo_pedido_entrada deixado VAZIO de proposito: o journal sera
    # FORCADO (journal_id) na invoice da NF-2 pelo script de escrituracao (R2.3),
    # como o RETIND fez na LF — evita capturar outros fluxos de entrada.
}
SEP = '=' * 96


def main():
    args = sys.argv[1:]
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}
        kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # ---- cleanup ----
    if '--deletar' in args:
        jid = int(args[args.index('--deletar') + 1])
        j = rr('account.journal', [('id', '=', jid)], ['name', 'code', 'company_id'])
        if not j:
            print(f'journal {jid} nao existe (ja deletado?)')
            return
        print(f'DELETANDO journal {jid}: {j[0]}')
        o.execute_kw('account.journal', 'unlink', [[jid]], {'context': CTX})
        print('  -> deletado.')
        return

    print(SEP)
    print('S61 — Journal FB ENTRADA-INSUMOS (R2.1)')
    print(SEP)

    # idempotencia: o journal-alvo e' de ENTRADA (purchase). Os sale com
    # no_payment=22800 (RPI/SNA/SPI = SAIDA, debitam a ATIVA) NAO servem p/
    # a entrada — type inverte o sinal do no_payment.
    todos = rr('account.journal',
               [('company_id', '=', 1),
                ('account_no_payment_id', '=', CONTA_ATIVA_FB)],
               ['id', 'name', 'code', 'type'])
    existentes = [j for j in todos if j['type'] == 'purchase']  # so entrada
    sale_ref = [j for j in todos if j['type'] == 'sale']
    by_code = rr('account.journal',
                 [('company_id', '=', 1), ('code', '=', SPEC['code'])],
                 ['id', 'name', 'code'])
    print(f"\n  Journal FB PURCHASE com no_payment=22800 (ATIVA — alvo): "
          f"{existentes if existentes else 'NENHUM (gap da ENTRADA confirmado)'}")
    print(f"  (ref) Journal FB SALE com no_payment=22800 (saida, NAO serve): "
          f"{[(j['id'], j['code']) for j in sale_ref]}")
    print(f"  Journal FB com code='{SPEC['code']}' hoje: "
          f"{by_code if by_code else 'NENHUM (code livre)'}")

    print('\n  SPEC do journal a criar:')
    for k, v in SPEC.items():
        print(f'    {k:30} = {v}')

    if existentes:
        print('\n  ⚠️  JA EXISTE journal FB com no_payment=22800 — reusar em vez de criar.')
        return

    if '--criar' not in args:
        print('\n  [DRY-RUN] nada escrito. Para criar: --criar')
        print(SEP)
        return

    if by_code:
        print(f"\n  ABORT: code '{SPEC['code']}' ja em uso (j{by_code[0]['id']}). Escolher outro.")
        return

    print('\n  [CRIAR] criando journal...')
    jid = o.execute_kw('account.journal', 'create', [dict(SPEC)], {'context': CTX})
    print(f'  -> journal CRIADO id={jid}')
    chk = rr('account.journal', [('id', '=', jid)],
             ['id', 'name', 'code', 'type', 'company_id',
              'account_no_payment_id', 'l10n_br_no_payment', 'default_account_id'])
    print(f'  verificacao: {chk}')
    print(SEP)


if __name__ == '__main__':
    main()
