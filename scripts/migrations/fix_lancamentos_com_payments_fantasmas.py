# -*- coding: utf-8 -*-
"""
Script para corrigir lançamentos com erro "já estão reconciliados" e
"nada a pagar", causados por títulos quitados manualmente no Odoo
antes do sistema tentar lançar.

Problema:
    - 46 lançamentos com erro: "Você está tentando reconciliar alguns
      lançamentos que já estão reconciliados."
    - 4 lançamentos com erro: "Não é possível registrar um pagamento
      porque não há mais nada a pagar nos itens de diário selecionados."
    - Todos criaram payment no Odoo (fantasma) mas não reconciliaram
    - status=CONFIRMADO com erro_lancamento preenchido

Solução:
    1. Verificar no Odoo se o título (odoo_move_line_id) está reconciliado
    2. Se sim: sincronizar full_reconcile_id, marcar LANCADO, limpar erro
    3. Listar payments fantasmas para revisão manual no Odoo

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_lancamentos_com_payments_fantasmas.py

Data: 2026-02-04
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def extrair_id(valor):
    """Extrai ID numérico de campo Odoo (pode ser [id, 'name'] ou int)."""
    if not valor:
        return None
    if isinstance(valor, (list, tuple)):
        return valor[0] if valor else None
    return valor


def identificar_afetados():
    """
    Identifica lançamentos com erro de reconciliação.
    """
    result = db.session.execute(text("""
        SELECT
            lc.id as lanc_id,
            lc.comprovante_id,
            lc.odoo_move_line_id,
            lc.odoo_payment_id,
            lc.odoo_payment_name,
            lc.odoo_full_reconcile_id,
            lc.odoo_full_reconcile_extrato_id,
            lc.nf_numero,
            lc.parcela,
            lc.erro_lancamento,
            lc.status,
            cpb.odoo_statement_line_id,
            cpb.odoo_move_id as comp_move_id
        FROM lancamento_comprovante lc
        JOIN comprovante_pagamento_boleto cpb ON cpb.id = lc.comprovante_id
        WHERE lc.erro_lancamento LIKE '%já estão reconciliados%'
           OR lc.erro_lancamento LIKE '%nada a pagar%'
        ORDER BY lc.id
    """))

    return result.fetchall()


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 70)
        print("CORREÇÃO: Lançamentos com Erro de Reconciliação + Payments Fantasmas")
        print("=" * 70)

        try:
            # ── 1. Identificar afetados ──────────────────────────────
            print("\n1. Identificando lançamentos afetados...")
            afetados = identificar_afetados()

            if not afetados:
                print("   Nenhum lançamento afetado encontrado!")
                print("\n" + "=" * 70)
                print("NADA A CORRIGIR")
                print("=" * 70 + "\n")
                return 0

            print(f"   Encontrados {len(afetados)} lançamentos para corrigir:")
            for item in afetados[:10]:
                print(
                    f"   - Lanc {item[0]}: NF {item[7]}/{item[8]} | "
                    f"titulo={item[2]} | payment={item[3]} | "
                    f"erro={'já_reconciliado' if 'já estão reconciliados' in (item[9] or '') else 'nada_a_pagar'}"
                )
            if len(afetados) > 10:
                print(f"   ... e mais {len(afetados) - 10}")

            # ── 2. Conectar ao Odoo ──────────────────────────────────
            print("\n2. Conectando ao Odoo...")
            from app.odoo.utils.connection import get_odoo_connection
            connection = get_odoo_connection()
            if not connection.authenticate():
                print("   ERRO: Falha na autenticação com Odoo")
                return 1
            print("   Conectado com sucesso")

            # ── 3. Buscar títulos no Odoo (batch) ────────────────────
            print("\n3. Buscando títulos no Odoo (batch)...")
            titulo_ids = list({item[2] for item in afetados if item[2]})
            print(f"   {len(titulo_ids)} títulos únicos para verificar")

            titulos = connection.search_read(
                'account.move.line',
                [['id', 'in', titulo_ids]],
                fields=[
                    'id', 'reconciled', 'full_reconcile_id',
                    'amount_residual', 'matched_credit_ids', 'matched_debit_ids',
                ],
            )
            titulos_por_id = {t['id']: t for t in titulos}
            print(f"   {len(titulos_por_id)} títulos encontrados no Odoo")

            # ── 4. Processar cada lançamento ──────────────────────────
            print("\n4. Processando lançamentos...")
            stats = {
                'sincronizado': 0,
                'titulo_nao_reconciliado': 0,
                'titulo_nao_encontrado': 0,
            }
            payments_fantasmas = []

            for item in afetados:
                lanc_id = item[0]
                comprovante_id = item[1]
                titulo_id = item[2]
                payment_id = item[3]
                payment_name = item[4]
                nf_numero = item[7]
                parcela = item[8]
                comp_move_id = item[12]

                titulo = titulos_por_id.get(titulo_id)
                if not titulo:
                    stats['titulo_nao_encontrado'] += 1
                    print(
                        f"   ✗ Lanc {lanc_id} (NF {nf_numero}/{parcela}): "
                        f"Título {titulo_id} não encontrado no Odoo"
                    )
                    continue

                titulo_reconciliado = titulo.get('reconciled', False)
                titulo_residual = abs(float(titulo.get('amount_residual', 0)))

                if titulo_reconciliado or titulo_residual < 0.01:
                    # Título quitado — sincronizar e marcar LANCADO
                    full_reconcile_id = extrair_id(titulo.get('full_reconcile_id'))

                    # Verificar extrato
                    full_reconcile_extrato_id = None
                    if comp_move_id:
                        try:
                            linhas_ext = connection.search_read(
                                'account.move.line',
                                [['move_id', '=', comp_move_id], ['credit', '>', 0]],
                                fields=['id', 'reconciled', 'full_reconcile_id'],
                                limit=1,
                            )
                            if linhas_ext and linhas_ext[0].get('reconciled'):
                                full_reconcile_extrato_id = extrair_id(
                                    linhas_ext[0].get('full_reconcile_id')
                                )
                        except Exception:
                            pass

                    # Atualizar BD local
                    db.session.execute(text("""
                        UPDATE lancamento_comprovante
                        SET status = 'LANCADO',
                            lancado_em = NOW(),
                            lancado_por = 'script_fix_fantasmas',
                            erro_lancamento = NULL,
                            odoo_full_reconcile_id = :full_rec,
                            odoo_full_reconcile_extrato_id = :full_rec_ext
                        WHERE id = :lanc_id
                    """), {
                        'full_rec': full_reconcile_id,
                        'full_rec_ext': full_reconcile_extrato_id,
                        'lanc_id': lanc_id,
                    })

                    # Marcar comprovante como reconciliado
                    db.session.execute(text("""
                        UPDATE comprovante_pagamento_boleto
                        SET odoo_is_reconciled = TRUE
                        WHERE id = :comp_id
                    """), {'comp_id': comprovante_id})

                    stats['sincronizado'] += 1
                    print(
                        f"   ✓ Lanc {lanc_id} (NF {nf_numero}/{parcela}): "
                        f"SINCRONIZADO - full_reconcile={full_reconcile_id}"
                        f"{', extrato=' + str(full_reconcile_extrato_id) if full_reconcile_extrato_id else ''}"
                    )

                    # Registrar payment fantasma
                    if payment_id:
                        payments_fantasmas.append({
                            'lanc_id': lanc_id,
                            'payment_id': payment_id,
                            'payment_name': payment_name,
                            'nf': f"{nf_numero}/{parcela}",
                        })
                else:
                    stats['titulo_nao_reconciliado'] += 1
                    print(
                        f"   ⚠ Lanc {lanc_id} (NF {nf_numero}/{parcela}): "
                        f"Título NÃO reconciliado (residual={titulo_residual:.2f})"
                    )

            # ── 5. Resumo ────────────────────────────────────────────
            print("\n5. Resumo:")
            print(f"   - Sincronizados (título quitado no Odoo): {stats['sincronizado']}")
            print(f"   - Título não reconciliado: {stats['titulo_nao_reconciliado']}")
            print(f"   - Título não encontrado no Odoo: {stats['titulo_nao_encontrado']}")

            # ── 6. Payments fantasmas ─────────────────────────────────
            if payments_fantasmas:
                print(f"\n6. PAYMENTS FANTASMAS no Odoo ({len(payments_fantasmas)}):")
                print("   Estes payments foram criados mas NÃO reconciliaram.")
                print("   AÇÃO MANUAL NECESSÁRIA: cancelar ou reconciliar no Odoo.")
                print()
                for pf in payments_fantasmas:
                    print(
                        f"   ⚠ Payment ID={pf['payment_id']} ({pf['payment_name']}) "
                        f"- Lanc {pf['lanc_id']} (NF {pf['nf']})"
                    )
                print()
                print(
                    f"   URL Odoo (exemplo): "
                    f"https://odoo.nacomgoya.com.br/web#id={payments_fantasmas[0]['payment_id']}"
                    f"&model=account.payment&view_type=form"
                )

            # ── 7. Commit ────────────────────────────────────────────
            if stats['sincronizado'] > 0:
                db.session.commit()
                print("\n" + "=" * 70)
                print("CONCLUÍDO COM SUCESSO!")
                print(f"  - {stats['sincronizado']} lançamentos sincronizados")
                print(f"  - {len(payments_fantasmas)} payments fantasmas identificados")
                print("=" * 70 + "\n")
            else:
                print("\n" + "=" * 70)
                print("NENHUM LANÇAMENTO ALTERADO")
                print("=" * 70 + "\n")

            return 0

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())
