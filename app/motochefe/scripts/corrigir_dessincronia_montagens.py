"""
Script para corrigir dessincronia entre PedidoVendaMotoItem e TituloAPagar
SEMPRE usa TituloAPagar como fonte da verdade
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from app.motochefe.models import PedidoVendaMotoItem
from app.motochefe.models.financeiro import TituloAPagar

def corrigir_dessincronia(dry_run=True):
    """
    Sincroniza PedidoVendaMotoItem.montagem_paga com TituloAPagar.status

    Args:
        dry_run: Se True, apenas mostra o que seria feito sem salvar
    """
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print(f"CORREÇÃO DE DESSINCRONIA - {'DRY RUN (simulação)' if dry_run else 'MODO REAL'}")
        print("=" * 80)

        # Buscar todos os itens com montagem contratada
        itens_com_montagem = PedidoVendaMotoItem.query.filter_by(
            montagem_contratada=True
        ).all()

        print(f"\nTotal de itens com montagem: {len(itens_com_montagem)}")
        print()

        correcoes = []
        erros = []

        for item in itens_com_montagem:
            # Buscar TituloAPagar correspondente
            titulo = TituloAPagar.query.filter_by(
                pedido_id=item.pedido_id,
                numero_chassi=item.numero_chassi,
                tipo='MONTAGEM'
            ).first()

            if not titulo:
                erros.append({
                    'item_id': item.id,
                    'erro': 'TituloAPagar não encontrado'
                })
                continue

            # ✅ FONTE DA VERDADE: TituloAPagar.status
            deveria_estar_pago = (titulo.status == 'PAGO')

            # Verificar se precisa correção
            if item.montagem_paga != deveria_estar_pago:
                correcoes.append({
                    'item_id': item.id,
                    'titulo_id': titulo.id,
                    'chassi': item.numero_chassi,
                    'pedido_id': item.pedido_id,
                    'estado_atual': item.montagem_paga,
                    'estado_correto': deveria_estar_pago,
                    'titulo_status': titulo.status,
                    'titulo_saldo': titulo.valor_saldo
                })

                if not dry_run:
                    item.montagem_paga = deveria_estar_pago
                    print(f"✅ Item {item.id} corrigido: {item.montagem_paga} → {deveria_estar_pago}")

        # Resultados
        print("\n" + "=" * 80)
        print("RESULTADOS:")
        print("=" * 80)

        if correcoes:
            print(f"\n⚠️  {len(correcoes)} correção(ões) necessária(s):\n")
            for c in correcoes:
                print(f"   Item ID {c['item_id']} (Pedido {c['pedido_id']}, Chassi {c['chassi']}):")
                print(f"   - Estado atual: montagem_paga = {c['estado_atual']}")
                print(f"   - Estado correto: montagem_paga = {c['estado_correto']}")
                print(f"   - TituloAPagar ID {c['titulo_id']}: status={c['titulo_status']}, saldo=R${c['titulo_saldo']}")
                print()
        else:
            print("\n✅ Nenhuma correção necessária! Tudo sincronizado.")

        if erros:
            print(f"\n❌ {len(erros)} erro(s) encontrado(s):\n")
            for e in erros:
                print(f"   Item ID {e['item_id']}: {e['erro']}")
            print()

        if not dry_run and correcoes:
            db.session.commit()
            print(f"\n💾 {len(correcoes)} registro(s) atualizado(s) no banco!")
        elif dry_run and correcoes:
            print("\n⚠️  DRY RUN: Nenhuma alteração foi salva.")
            print("   Para aplicar as correções, execute:")
            print("   python app/motochefe/scripts/corrigir_dessincronia_montagens.py --real")

        print("\n" + "=" * 80)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Corrige dessincronia de montagens')
    parser.add_argument('--real', action='store_true', help='Executar correção real (sem dry-run)')
    args = parser.parse_args()

    corrigir_dessincronia(dry_run=not args.real)
