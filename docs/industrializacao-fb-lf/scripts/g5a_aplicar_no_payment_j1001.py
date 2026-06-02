#!/usr/bin/env python3
"""G5a — setar account_no_payment_id=22800 (5101010001 ATIVA) no journal j1001 (FB ENTSI).

Efeito: na ENTRADA FB de retorno, as linhas 1902 simbolicas (CST51, sem pagamento)
passam a CREDITAR 5101010001 = baixa da conta ATIVA da remessa (fecha o ciclo na FB).
Sinal VALIDADO ao vivo (ACHADOS sessao 5: j1011/j868/j993).

⚠️ CONFIG GLOBAL (prospectiva): afeta TODAS as ENTSI futuras em j1001 (hoje ~100%
industrializacao da LF). Reversivel pela config (--reverter limpa o campo), mas NAO
desfaz lancamentos ja postados na janela.

DRY-RUN e' o DEFAULT. So efetiva com --confirmar. --reverter faz rollback (limpa).
1 unico write (account.journal[1001].write). NAO cria tipo.pedido.diario por padrao
(roteamento ja e' pelo campo do journal — redundante); use --criar-tpd se quiser o
cinto-de-seguranca.

PRE-REQUISITO recomendado: medir R1 antes (conta que a op 3252 debita na 1902 sem
stock.move) — ver PROPOSTA §7 passo 1.
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
J1001 = 1001
CONTA_ATIVA = 22800   # 5101010001 REMESSA INDUSTRIALIZAÇÃO (ATIVA), company FB


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', help='efetiva o write (default = dry-run)')
    ap.add_argument('--reverter', action='store_true', help='rollback: limpa o no_payment do j1001')
    ap.add_argument('--criar-tpd', action='store_true',
                    help='tambem cria tipo.pedido.diario(FB, serv-industrializacao->j1001) — redundante')
    args = ap.parse_args()
    dry = not args.confirmar
    alvo = False if args.reverter else CONTA_ATIVA

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ---- PRE-CHECKS ----
    j = rd('account.journal', [J1001],
           ['id', 'name', 'code', 'type', 'company_id', 'account_no_payment_id'])
    assert j, f"journal {J1001} nao encontrado"
    j = j[0]
    assert j['type'] == 'purchase', f"j{J1001} type={j['type']} (esperado purchase)"
    assert isinstance(j['company_id'], list) and j['company_id'][0] == 1, "j1001 nao e company FB(1)"

    conta = rd('account.account', [CONTA_ATIVA], ['id', 'code', 'name', 'account_type', 'company_id'])
    assert conta, f"conta {CONTA_ATIVA} nao encontrada"
    conta = conta[0]
    assert conta['code'] == '5101010001', f"conta {CONTA_ATIVA} code={conta['code']} (esperado 5101010001)"
    assert conta['account_type'] == 'asset_current', f"conta {CONTA_ATIVA} type={conta['account_type']}"
    assert conta['company_id'][0] == 1, "conta 22800 nao e company FB(1)"

    atual = j.get('account_no_payment_id')
    atual_id = atual[0] if isinstance(atual, list) and atual else False

    print("=" * 80)
    print(f"G5a — {'ROLLBACK (limpar)' if args.reverter else 'setar no_payment'} no j{J1001}")
    print("=" * 80)
    print(f"  journal : j{j['id']} {j['code']} ({j['name']}) type={j['type']} company=FB(1)")
    print(f"  conta   : {conta['code']} id={CONTA_ATIVA} {conta['name']} ({conta['account_type']})")
    print(f"  ANTES   : account_no_payment_id = {m2o(atual)}")
    print(f"  DEPOIS  : account_no_payment_id = {alvo if alvo else '(vazio)'}")
    if args.criar_tpd:
        print("  + criar tipo.pedido.diario(company=FB, l10n_br_tipo_pedido_entrada=serv-industrializacao -> j1001)")

    # idempotencia
    if atual_id == (alvo or False):
        print("\n  >>> JA esta no estado alvo — nada a fazer.")
        return

    if dry:
        print("\n  [DRY-RUN] nada foi escrito. Para efetivar: --confirmar (apos 'go' FRESCO do Rafael).")
        return

    # ---- WRITE (1 comando) ----
    o.execute_kw('account.journal', 'write', [[J1001], {'account_no_payment_id': alvo or False}],
                 {'context': CTX})
    # re-check ao vivo
    pos = rd('account.journal', [J1001], ['account_no_payment_id'])[0]
    print(f"\n  EXECUTADO. POS-CHECK no_payment = {m2o(pos.get('account_no_payment_id'))}")

    if args.criar_tpd and not args.reverter:
        TPD = 'l10n_br_ciel_it_account.tipo.pedido.diario'
        ja = o.execute_kw(TPD, 'search_count',
                          [[('company_id', '=', 1), ('l10n_br_tipo_pedido_entrada', '=', 'serv-industrializacao')]],
                          {'context': CTX})
        if ja:
            print(f"  tipo.pedido.diario(FB, serv-industrializacao) JA existe ({ja}) — nao recria.")
        else:
            nid = o.execute_kw(TPD, 'create',
                               [{'company_id': 1, 'l10n_br_tipo_pedido_entrada': 'serv-industrializacao',
                                 'journal_id': J1001}], {'context': CTX})
            print(f"  tipo.pedido.diario criado id={nid}")


if __name__ == '__main__':
    main()
