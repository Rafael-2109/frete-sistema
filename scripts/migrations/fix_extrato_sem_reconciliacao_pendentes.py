# -*- coding: utf-8 -*-
"""
Script v2 para corrigir extratos CONCILIADOS sem reconciliação no Odoo.

Problema: Extratos com status='CONCILIADO' mas full_reconcile_id=NULL e
          partial_reconcile_id=NULL, causados por payments manuais no Odoo
          que não usaram a conta PENDENTES (26868).

Mensagem associada:
    "Título já quitado no Odoo - extrato não reconciliado
     (payment original não usou conta PENDENTES)"

Causa adicional: O script v1 falhou porque 56 de 75 credit_line_ids
                 não existiam mais no Odoo (foram recriados com novos IDs
                 após button_draft + action_post nos moves).

Solução v2:
    1. Re-buscar credit_line_id CORRETO via move_id (estável) usando
       query batch no Odoo
    2. Atualizar credit_line_id no BD local se mudou
    3. Se a credit_line está reconciliada → sincronizar full/partial_reconcile_id
    4. Se não está reconciliada → atualizar mensagem indicando status

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_extrato_sem_reconciliacao_pendentes.py

Data: 2026-02-04 (v2)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def identificar_afetados():
    """
    Identifica extratos CONCILIADOS sem reconciliação no Odoo.
    Retorna lista de tuplas com (extrato_id, credit_line_id, move_id,
    statement_line_id, titulo_nf, titulo_parcela, ..., lote_id).
    """
    result = db.session.execute(text("""
        SELECT
            ei.id as extrato_id,
            ei.credit_line_id,
            ei.move_id,
            ei.statement_line_id,
            ei.titulo_nf,
            ei.titulo_parcela,
            ei.titulo_receber_id,
            ei.status,
            ei.mensagem,
            ei.partial_reconcile_id,
            ei.full_reconcile_id,
            ei.lote_id
        FROM extrato_item ei
        WHERE ei.status = 'CONCILIADO'
          AND ei.full_reconcile_id IS NULL
          AND ei.partial_reconcile_id IS NULL
          AND ei.credit_line_id IS NOT NULL
          AND ei.mensagem LIKE '%não usou conta PENDENTES%'
        ORDER BY ei.id
    """))

    return result.fetchall()


def extrair_id(valor):
    """Extrai ID numérico de campo Odoo (pode ser [id, 'name'] ou int)."""
    if not valor:
        return None
    if isinstance(valor, (list, tuple)):
        return valor[0] if valor else None
    return valor


def buscar_credit_lines_batch(connection, move_ids):
    """
    Busca credit lines ATUAIS no Odoo para uma lista de move_ids.
    Retorna dict: move_id → dados da credit line (com reconciliation info).

    Usa query batch para eficiência (1 query ao invés de N).
    """
    if not move_ids:
        return {}

    # Buscar todas as credit lines dos moves de uma vez
    credit_lines = connection.search_read(
        'account.move.line',
        [
            ['move_id', 'in', list(move_ids)],
            ['credit', '>', 0],
        ],
        fields=[
            'id', 'move_id', 'reconciled', 'full_reconcile_id',
            'matched_credit_ids', 'matched_debit_ids',
        ],
    )

    # Indexar por move_id (pegar a primeira credit line de cada move)
    result = {}
    for cl in credit_lines:
        move_id_val = cl.get('move_id')
        mid = extrair_id(move_id_val)
        if mid and mid not in result:
            result[mid] = cl

    return result


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 70)
        print("CORREÇÃO v2: Extratos CONCILIADOS sem Reconciliação Odoo")
        print("(Usando move_id para re-buscar credit_line_id)")
        print("=" * 70)

        try:
            # ── 1. Identificar afetados ──────────────────────────────
            print("\n1. Identificando extratos afetados...")
            afetados = identificar_afetados()

            if not afetados:
                print("   Nenhum extrato afetado encontrado!")
                print("\n" + "=" * 70)
                print("NADA A CORRIGIR")
                print("=" * 70 + "\n")
                return 0

            print(f"   Encontrados {len(afetados)} extratos para corrigir:")
            for item in afetados[:10]:
                print(
                    f"   - Extrato {item[0]}: NF {item[4]}/{item[5]} | "
                    f"credit_line={item[1]} | move_id={item[2]} | lote={item[11]}"
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

            # ── 3. Buscar credit lines ATUAIS via move_id (batch) ────
            print("\n3. Buscando credit lines atuais no Odoo via move_id (batch)...")
            move_ids = [item[2] for item in afetados if item[2]]
            print(f"   {len(move_ids)} move_ids para buscar")

            credit_por_move = buscar_credit_lines_batch(connection, move_ids)
            print(f"   {len(credit_por_move)} credit lines encontradas no Odoo")

            # ── 4. Processar cada extrato ─────────────────────────────
            print("\n4. Processando extratos...")
            stats = {
                'sincronizado': 0,
                'nao_reconciliado': 0,
                'credit_line_atualizado': 0,
                'move_sem_credit_line': 0,
                'sem_move_id': 0,
            }

            for item in afetados:
                extrato_id = item[0]
                credit_line_id_antigo = item[1]
                move_id = item[2]
                titulo_nf = item[4]
                titulo_parcela = item[5]

                # Verificar se tem move_id
                if not move_id:
                    stats['sem_move_id'] += 1
                    print(
                        f"   ✗ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"SEM move_id - impossível re-buscar"
                    )
                    continue

                # Buscar credit line atual via move_id
                cl = credit_por_move.get(move_id)
                if not cl:
                    stats['move_sem_credit_line'] += 1
                    print(
                        f"   ✗ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"Move {move_id} não tem credit line no Odoo"
                    )
                    continue

                novo_credit_line_id = cl['id']
                credit_line_mudou = (novo_credit_line_id != credit_line_id_antigo)

                if credit_line_mudou:
                    stats['credit_line_atualizado'] += 1

                # Verificar se está reconciliado no Odoo
                if cl.get('reconciled'):
                    # Extrair full_reconcile_id
                    full_reconcile_id = extrair_id(cl.get('full_reconcile_id'))

                    # Extrair partial_reconcile_id
                    partial_reconcile_id = None
                    matched_ids = (
                        cl.get('matched_debit_ids', [])
                        or cl.get('matched_credit_ids', [])
                    )
                    if matched_ids:
                        partial_reconcile_id = matched_ids[-1]

                    # Atualizar BD local
                    db.session.execute(text("""
                        UPDATE extrato_item
                        SET credit_line_id = :novo_credit,
                            full_reconcile_id = :full_rec,
                            partial_reconcile_id = :partial_rec,
                            mensagem = :msg
                        WHERE id = :extrato_id
                    """), {
                        'novo_credit': novo_credit_line_id,
                        'full_rec': full_reconcile_id,
                        'partial_rec': partial_reconcile_id,
                        'msg': (
                            f"Sincronizado v2 (move_id={move_id}): "
                            f"credit_line {'atualizado ' + str(credit_line_id_antigo) + '→' + str(novo_credit_line_id) if credit_line_mudou else 'mantido'}, "
                            f"full_reconcile={full_reconcile_id}, "
                            f"partial_reconcile={partial_reconcile_id}"
                        ),
                        'extrato_id': extrato_id,
                    })

                    stats['sincronizado'] += 1
                    label_credit = f" (credit_line {credit_line_id_antigo}→{novo_credit_line_id})" if credit_line_mudou else ""
                    print(
                        f"   ✓ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"SINCRONIZADO - full_reconcile={full_reconcile_id}{label_credit}"
                    )
                else:
                    # Não reconciliado — atualizar credit_line_id se mudou
                    if credit_line_mudou:
                        db.session.execute(text("""
                            UPDATE extrato_item
                            SET credit_line_id = :novo_credit,
                                mensagem = :msg
                            WHERE id = :extrato_id
                        """), {
                            'novo_credit': novo_credit_line_id,
                            'msg': (
                                f"credit_line atualizado v2 ({credit_line_id_antigo}→{novo_credit_line_id}), "
                                f"extrato pendente de reconciliação no Odoo (move_id={move_id})"
                            ),
                            'extrato_id': extrato_id,
                        })
                    else:
                        db.session.execute(text("""
                            UPDATE extrato_item
                            SET mensagem = :msg
                            WHERE id = :extrato_id
                        """), {
                            'msg': (
                                f"credit_line verificado v2 (id={novo_credit_line_id}), "
                                f"extrato pendente de reconciliação no Odoo (move_id={move_id})"
                            ),
                            'extrato_id': extrato_id,
                        })

                    stats['nao_reconciliado'] += 1
                    label_credit = f" (credit_line {credit_line_id_antigo}→{novo_credit_line_id})" if credit_line_mudou else ""
                    print(
                        f"   ⚠ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"NÃO RECONCILIADO no Odoo{label_credit}"
                    )

            # ── 5. Resumo ────────────────────────────────────────────
            print("\n5. Resumo:")
            print(f"   - Sincronizados (reconciliados no Odoo): {stats['sincronizado']}")
            print(f"   - Não reconciliados no Odoo: {stats['nao_reconciliado']}")
            print(f"   - Credit line IDs atualizados: {stats['credit_line_atualizado']}")
            print(f"   - Move sem credit line no Odoo: {stats['move_sem_credit_line']}")
            if stats['sem_move_id'] > 0:
                print(f"   - Sem move_id: {stats['sem_move_id']}")

            # ── 6. Commit ────────────────────────────────────────────
            total_alterados = stats['sincronizado'] + stats['nao_reconciliado']
            if total_alterados > 0:
                db.session.commit()
                print("\n" + "=" * 70)
                print("CONCLUÍDO COM SUCESSO!")
                print(f"  - {stats['sincronizado']} extratos sincronizados (reconciliados no Odoo)")
                print(f"  - {stats['nao_reconciliado']} com credit_line atualizado (pendente reconciliação)")
                print(f"  - {stats['move_sem_credit_line']} moves sem credit line no Odoo")
                print(f"  - {stats['credit_line_atualizado']} credit_line_ids corrigidos")
                print("=" * 70 + "\n")
            else:
                print("\n" + "=" * 70)
                print("NENHUM EXTRATO ALTERADO")
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
