"""
Script para identificar e remover NFDs de vasilhame do modulo de devolucoes

Essas devoluçoes de pallet/vasilhame devem ser gerenciadas no modulo de pallet,
não no módulo de devoluções de produtos.

Para executar:
    python scripts/remover_nfds_vasilhame.py

Para remover:
    python scripts/remover_nfds_vasilhame.py --confirmar
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.devolucao.models import NFDevolucao
from app.odoo.utils.connection import get_odoo_connection


def buscar_nfds_vasilhame():
    """
    Identifica NFDs no sistema que correspondem a devoluções de vasilhame no Odoo
    """
    print("\n" + "=" * 70)
    print("IDENTIFICANDO NFDs DE VASILHAME NO MODULO DE DEVOLUCOES")
    print("=" * 70)

    # Buscar todas as NFDs que têm odoo_nota_credito_id (vieram do reversao_service)
    nfds_com_odoo = NFDevolucao.query.filter(
        NFDevolucao.odoo_nota_credito_id.isnot(None),
        NFDevolucao.ativo == True
    ).all()

    if not nfds_com_odoo:
        print("\n✅ Nenhuma NFD com vinculo Odoo encontrada.")
        return []

    print(f"\n📋 Verificando {len(nfds_com_odoo)} NFDs com vinculo Odoo...")

    # Conectar ao Odoo para verificar tipo_pedido
    try:
        odoo = get_odoo_connection()
    except Exception as e:
        print(f"❌ Erro ao conectar ao Odoo: {e}")
        return []

    nfds_vasilhame = []

    for nfd in nfds_com_odoo:
        try:
            # Buscar no Odoo
            nc_data = odoo.execute_kw(
                'account.move',
                'search_read',
                [[('id', '=', nfd.odoo_nota_credito_id)]],
                {'fields': ['name', 'l10n_br_tipo_pedido', 'partner_id']}
            )

            if nc_data and nc_data[0].get('l10n_br_tipo_pedido') == 'vasilhame':
                nfds_vasilhame.append({
                    'nfd': nfd,
                    'tipo_pedido': nc_data[0].get('l10n_br_tipo_pedido'),
                    'nome_odoo': nc_data[0].get('name'),
                    'partner': nc_data[0].get('partner_id', [None, 'N/A'])[1] if nc_data[0].get('partner_id') else 'N/A'
                })
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar NFD {nfd.id}: {e}")

    return nfds_vasilhame


def listar_nfds_vasilhame(nfds):
    """Lista NFDs de vasilhame encontradas"""
    if not nfds:
        print("\n✅ Nenhuma NFD de vasilhame encontrada no modulo de devolucoes!")
        return

    print(f"\n⚠️ Encontradas {len(nfds)} NFDs de vasilhame:\n")
    print(f"{'ID':>6} | {'Numero NFD':>12} | {'Nome Odoo':>20} | {'Parceiro':<30}")
    print("-" * 80)

    for item in nfds:
        nfd = item['nfd']
        print(f"{nfd.id:>6} | {(nfd.numero_nfd or '-'):>12} | {(item['nome_odoo'] or '-')[:20]:>20} | {item['partner'][:30]:<30}")


def remover_nfds_vasilhame(nfds, confirmar=False):
    """Remove (soft delete) NFDs de vasilhame"""
    if not nfds:
        print("\n✅ Nenhuma NFD para remover.")
        return 0

    if not confirmar:
        print(f"\n⚠️ {len(nfds)} NFDs serão marcadas como inativas.")
        print("   Execute com --confirmar para efetivar a remoção.")
        return 0

    count = 0
    for item in nfds:
        nfd = item['nfd']
        nfd.ativo = False
        # Também atualiza observação para rastreabilidade
        if nfd.descricao_motivo:
            nfd.descricao_motivo += '\n[REMOVIDO] NFD de vasilhame - deve ser gerenciada no modulo de pallet'
        else:
            nfd.descricao_motivo = '[REMOVIDO] NFD de vasilhame - deve ser gerenciada no modulo de pallet'
        count += 1

    db.session.commit()
    print(f"\n✅ {count} NFDs marcadas como inativas!")
    return count


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Buscar NFDs de vasilhame
        nfds_vasilhame = buscar_nfds_vasilhame()

        # Listar
        listar_nfds_vasilhame(nfds_vasilhame)

        if nfds_vasilhame:
            # Verificar se deve confirmar
            confirmar = '--confirmar' in sys.argv

            if not confirmar:
                print("\n" + "-" * 70)
                print("Para remover, execute:")
                print("  python scripts/remover_nfds_vasilhame.py --confirmar")
                print("-" * 70)

            remover_nfds_vasilhame(nfds_vasilhame, confirmar=confirmar)
