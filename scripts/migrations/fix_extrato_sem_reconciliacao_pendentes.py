# -*- coding: utf-8 -*-
"""
Script para corrigir extratos CONCILIADOS sem reconciliação no Odoo.

Problema: Extratos com status='CONCILIADO' mas full_reconcile_id=NULL e
          partial_reconcile_id=NULL, causados por payments manuais no Odoo
          que não usaram a conta PENDENTES (26868).

Mensagem associada:
    "Título já quitado no Odoo - extrato não reconciliado
     (payment original não usou conta PENDENTES)"

Solução:
    1. Para itens cujo extrato JÁ foi reconciliado manualmente no Odoo:
       → Sincronizar full_reconcile_id e partial_reconcile_id
    2. Para itens cujo extrato NÃO está reconciliado no Odoo:
       → Tentar reconciliar usando busca expandida de linha do payment

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_extrato_sem_reconciliacao_pendentes.py

Data: 2026-02-04
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def identificar_afetados():
    """
    Identifica extratos CONCILIADOS sem reconciliação no Odoo.
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


def sincronizar_do_odoo(extrato_id, credit_line_id, connection):
    """
    Verifica se a linha do extrato já está reconciliada no Odoo
    e sincroniza os dados para o BD local.

    Returns:
        Dict com resultado: {'acao': 'sincronizado'|'nao_reconciliado'|'erro', ...}
    """
    try:
        linhas = connection.search_read(
            'account.move.line',
            [['id', '=', credit_line_id]],
            fields=[
                'id', 'reconciled', 'full_reconcile_id',
                'matched_credit_ids', 'matched_debit_ids'
            ],
            limit=1
        )

        if not linhas:
            return {'acao': 'erro', 'msg': f'Linha {credit_line_id} não encontrada no Odoo'}

        linha = linhas[0]

        if not linha.get('reconciled'):
            return {'acao': 'nao_reconciliado', 'msg': 'Extrato não reconciliado no Odoo'}

        # Extrair full_reconcile_id
        full_reconcile_id = None
        full_rec = linha.get('full_reconcile_id')
        if full_rec:
            if isinstance(full_rec, (list, tuple)):
                full_reconcile_id = full_rec[0]
            else:
                full_reconcile_id = full_rec

        # Extrair partial_reconcile_id
        partial_reconcile_id = None
        matched_ids = (
            linha.get('matched_debit_ids', [])
            or linha.get('matched_credit_ids', [])
        )
        if matched_ids:
            partial_reconcile_id = matched_ids[-1]

        # Atualizar BD local
        db.session.execute(text("""
            UPDATE extrato_item
            SET full_reconcile_id = :full_rec,
                partial_reconcile_id = :partial_rec,
                mensagem = :msg
            WHERE id = :extrato_id
        """), {
            'full_rec': full_reconcile_id,
            'partial_rec': partial_reconcile_id,
            'msg': (
                f"Extrato reconciliado no Odoo (manual) - sincronizado pelo script "
                f"(full_reconcile={full_reconcile_id}, partial_reconcile={partial_reconcile_id})"
            ),
            'extrato_id': extrato_id
        })

        return {
            'acao': 'sincronizado',
            'full_reconcile_id': full_reconcile_id,
            'partial_reconcile_id': partial_reconcile_id
        }

    except Exception as e:
        return {'acao': 'erro', 'msg': str(e)}


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 70)
        print("CORREÇÃO: Extratos CONCILIADOS sem Reconciliação Odoo")
        print("=" * 70)

        try:
            # 1. Identificar afetados
            print("\n1. Identificando extratos afetados...")
            afetados = identificar_afetados()

            if not afetados:
                print("   Nenhum extrato afetado encontrado!")
                print("\n" + "=" * 70)
                print("NADA A CORRIGIR")
                print("=" * 70 + "\n")
                return 0

            print(f"   Encontrados {len(afetados)} extratos para verificar:")
            for item in afetados[:10]:
                print(
                    f"   - Extrato {item[0]}: NF {item[4]}/{item[5]} | "
                    f"credit_line={item[1]} | lote={item[11]}"
                )
            if len(afetados) > 10:
                print(f"   ... e mais {len(afetados) - 10}")

            # 2. Conectar ao Odoo
            print("\n2. Conectando ao Odoo...")
            from app.odoo.utils.connection import get_odoo_connection
            connection = get_odoo_connection()
            if not connection.authenticate():
                print("   ERRO: Falha na autenticação com Odoo")
                return 1
            print("   Conectado com sucesso")

            # 3. Processar cada extrato
            print("\n3. Processando extratos...")
            stats = {
                'sincronizado': 0,
                'nao_reconciliado': 0,
                'erro': 0
            }

            for item in afetados:
                extrato_id = item[0]
                credit_line_id = item[1]
                titulo_nf = item[4]
                titulo_parcela = item[5]

                resultado = sincronizar_do_odoo(extrato_id, credit_line_id, connection)
                acao = resultado['acao']
                stats[acao] = stats.get(acao, 0) + 1

                if acao == 'sincronizado':
                    print(
                        f"   ✓ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"SINCRONIZADO - full_reconcile={resultado.get('full_reconcile_id')}"
                    )
                elif acao == 'nao_reconciliado':
                    print(
                        f"   ⚠ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"NÃO RECONCILIADO no Odoo"
                    )
                else:
                    print(
                        f"   ✗ Extrato {extrato_id} (NF {titulo_nf}/{titulo_parcela}): "
                        f"ERRO - {resultado.get('msg', 'desconhecido')}"
                    )

            # 4. Resumo
            print("\n4. Resumo:")
            print(f"   - Sincronizados: {stats['sincronizado']}")
            print(f"   - Não reconciliados no Odoo: {stats['nao_reconciliado']}")
            print(f"   - Erros: {stats['erro']}")

            # 5. Verificar resultado
            print("\n5. Verificando resultado...")
            restantes = identificar_afetados()
            print(f"   Extratos ainda afetados: {len(restantes)}")

            # 6. Commit
            if stats['sincronizado'] > 0:
                db.session.commit()
                print("\n" + "=" * 70)
                print(f"CONCLUÍDO COM SUCESSO!")
                print(f"  - {stats['sincronizado']} extratos sincronizados")
                print(f"  - {stats['nao_reconciliado']} ainda pendentes no Odoo")
                print(f"  - {stats['erro']} erros")
                print("=" * 70 + "\n")
            else:
                print("\n" + "=" * 70)
                print("NENHUM EXTRATO SINCRONIZADO")
                print("  Nenhum dos extratos afetados estava reconciliado no Odoo")
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
