"""
Fix: Vincular CTe Complementares a faturas cliente existentes.

Problema: itens de fatura que referenciam CTe Complementares (pelo cte_numero real)
ficavam com operacao_id=NULL porque o LinkingService so buscava CarviaOperacao.
O CTe Comp tambem ficava com fatura_cliente_id=NULL, e o valor_total da fatura
nao incluia o valor do CTe Comp.

Correcao: usa o novo metodo vincular_ctes_complementares_da_fatura() e
re-executa vincular_itens_fatura_cliente() para resolver itens pendentes.

Caso especifico: Fatura 89-2 (id=137) + CTe Comp COMP-001 (id=1, cte_numero=121).

Pode ser executado multiplas vezes (idempotente).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def run():
    from app import create_app, db
    app = create_app()

    with app.app_context():
        from app.carvia.models import (
            CarviaFaturaCliente, CarviaFaturaClienteItem,
        )
        from app.carvia.services.documentos.linking_service import LinkingService

        linker = LinkingService()

        # Buscar faturas com itens sem operacao_id (vinculacao pendente)
        subq = db.session.query(
            CarviaFaturaClienteItem.fatura_cliente_id
        ).filter(
            CarviaFaturaClienteItem.operacao_id.is_(None),
            CarviaFaturaClienteItem.cte_numero.isnot(None),
        ).distinct().subquery()

        faturas = CarviaFaturaCliente.query.filter(
            CarviaFaturaCliente.id.in_(db.session.query(subq))
        ).all()

        if not faturas:
            print("Nenhuma fatura com itens pendentes encontrada.")
            return

        print(f"Encontradas {len(faturas)} fatura(s) com itens pendentes:")
        for f in faturas:
            print(f"  - Fatura #{f.id} ({f.numero_fatura}): R$ {float(f.valor_total or 0):.2f}")

        total_comp = 0
        total_ops = 0

        for fatura in faturas:
            print(f"\n--- Processando fatura #{fatura.id} ({fatura.numero_fatura}) ---")

            # 1. Re-executar vincular_itens_fatura_cliente (resolve operacao_id via CTe Comp)
            link_stats = linker.vincular_itens_fatura_cliente(fatura.id, auto_criar_nf=True)
            ops = link_stats.get('operacoes_resolvidas', 0)
            comps = link_stats.get('cte_comp_resolvidos', 0)
            total_ops += ops
            total_comp += comps
            if ops or comps:
                print(f"  Itens resolvidos: {ops} operacoes, {comps} CTe Comps")

            # 2. Vincular CTe Comps a fatura + recalcular valor_total
            comp_stats = linker.vincular_ctes_complementares_da_fatura(fatura.id)
            if comp_stats['cte_comp_vinculados'] > 0:
                print(
                    f"  CTe Comps vinculados: {comp_stats['cte_comp_vinculados']}"
                    f"  Valor: R$ {comp_stats['valor_total_anterior']:.2f}"
                    f" -> R$ {comp_stats['valor_total_novo']:.2f}"
                )
            else:
                print(f"  Nenhum CTe Comp novo para vincular")

        db.session.commit()
        print(f"\n=== Concluido: {total_ops} ops + {total_comp} CTe Comps resolvidos ===")


if __name__ == '__main__':
    run()
