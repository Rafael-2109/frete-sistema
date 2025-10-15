#!/usr/bin/env python3
"""
Script de Limpeza do Módulo MotoCHEFE
Data: 06/01/2025
Descrição: Limpa todas as tabelas do módulo MotoCHEFE para resetar dados de teste
ATENÇÃO: Este script APAGA TODOS OS DADOS do módulo MotoCHEFE
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app import create_app, db
from app.motochefe.models import (
    # Cadastros
    VendedorMoto, EquipeVendasMoto, TabelaPrecoEquipe,
    TransportadoraMoto, ClienteMoto, EmpresaVendaMoto,
    CrossDocking, TabelaPrecoCrossDocking,
    # Produtos
    ModeloMoto, Moto,
    # Vendas
    PedidoVendaMoto, PedidoVendaAuditoria, PedidoVendaMotoItem,
    # Financeiro
    TituloFinanceiro, ComissaoVendedor, MovimentacaoFinanceira, TituloAPagar,
    # Logística
    EmbarqueMoto, EmbarquePedido,
    # Operacional
    CustosOperacionais, DespesaMensal
)


def limpar_tabelas():
    """
    Limpa TODAS as tabelas do módulo MotoCHEFE
    Ordem de deleção respeita dependências de FK
    """
    print("=" * 80)
    print("SCRIPT DE LIMPEZA - MÓDULO MOTOCHEFE")
    print("=" * 80)
    print("\n⚠️  ATENÇÃO: Este script irá APAGAR TODOS OS DADOS do módulo MotoCHEFE\n")

    resposta = input("Tem certeza que deseja continuar? Digite 'SIM' para confirmar: ")

    if resposta.strip().upper() != 'SIM':
        print("\n❌ Operação cancelada pelo usuário.")
        return

    print("\n🔄 Iniciando limpeza das tabelas...\n")

    try:
        # Ordem de deleção (das mais dependentes para as menos)

        # 1. Financeiro (ordem: MovimentacaoFinanceira -> TituloAPagar -> ComissaoVendedor -> TituloFinanceiro)
        print("1️⃣  Limpando MovimentacaoFinanceira...")
        count = MovimentacaoFinanceira.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("2️⃣  Limpando TituloAPagar...")
        count = TituloAPagar.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("3️⃣  Limpando ComissaoVendedor...")
        count = ComissaoVendedor.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("4️⃣  Limpando TituloFinanceiro...")
        count = TituloFinanceiro.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 2. Logística (depende de Pedido e Transportadora)
        print("5️⃣  Limpando EmbarquePedido...")
        count = EmbarquePedido.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("6️⃣  Limpando EmbarqueMoto...")
        count = EmbarqueMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("7️⃣  Limpando PedidoVendaAuditoria...")
        count = PedidoVendaAuditoria.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 3. Vendas (depende de Cliente, Vendedor, Moto)
        print("8️⃣  Limpando PedidoVendaMotoItem...")
        count = PedidoVendaMotoItem.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("8️⃣  Limpando PedidoVendaMoto...")
        count = PedidoVendaMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 4. Produtos (depende de Modelo)
        print("9️⃣  Limpando Moto...")
        count = Moto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("🔟 Limpando ModeloMoto...")
        count = ModeloMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 5. Tabela de Preços (depende de Equipe/CrossDocking e Modelo)
        print("1️⃣1️⃣  Limpando TabelaPrecoCrossDocking...")
        count = TabelaPrecoCrossDocking.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣2️⃣  Limpando TabelaPrecoEquipe...")
        count = TabelaPrecoEquipe.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 6. Cadastros (ordem: Cliente -> Vendedor -> Equipe/CrossDocking -> demais)
        print("1️⃣3️⃣  Limpando ClienteMoto...")
        count = ClienteMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣4️⃣  Limpando VendedorMoto...")
        count = VendedorMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣5️⃣  Limpando EquipeVendasMoto...")
        count = EquipeVendasMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣6️⃣  Limpando CrossDocking...")
        count = CrossDocking.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣7️⃣  Limpando TransportadoraMoto...")
        count = TransportadoraMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("1️⃣8️⃣  Limpando EmpresaVendaMoto...")
        count = EmpresaVendaMoto.query.delete()
        print(f"   ✅ {count} registros removidos")

        # 7. Operacional
        print("1️⃣9️⃣  Limpando DespesaMensal...")
        count = DespesaMensal.query.delete()
        print(f"   ✅ {count} registros removidos")

        print("2️⃣0️⃣  Limpando CustosOperacionais...")
        count = CustosOperacionais.query.delete()
        print(f"   ✅ {count} registros removidos")

        # Commit das alterações
        db.session.commit()

        print("\n" + "=" * 80)
        print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print("\n📋 PRÓXIMOS PASSOS:")
        print("   1. Configure as equipes de vendas com os novos campos")
        print("   2. Configure CrossDocking (se necessário)")
        print("   3. Cadastre transportadoras, clientes e vendedores")
        print("   4. Cadastre modelos de motos")
        print("   5. Configure tabela de preços por equipe (se tipo_precificacao='TABELA')")
        print("   6. Configure tabela de preços CrossDocking (se crossdocking.tipo_precificacao='TABELA')")
        print("\n")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERRO durante a limpeza: {str(e)}")
        print("   Todas as alterações foram revertidas (ROLLBACK)")
        return False

    return True


def verificar_limpeza():
    """Verifica se as tabelas foram limpas corretamente"""
    print("\n🔍 Verificando limpeza...")

    tabelas_verificar = [
        ('MovimentacaoFinanceira', MovimentacaoFinanceira),
        ('TituloAPagar', TituloAPagar),
        ('ComissaoVendedor', ComissaoVendedor),
        ('TituloFinanceiro', TituloFinanceiro),
        ('EmbarquePedido', EmbarquePedido),
        ('EmbarqueMoto', EmbarqueMoto),
        ('PedidoVendaAuditoria', PedidoVendaAuditoria),
        ('PedidoVendaMotoItem', PedidoVendaMotoItem),
        ('PedidoVendaMoto', PedidoVendaMoto),
        ('Moto', Moto),
        ('ModeloMoto', ModeloMoto),
        ('TabelaPrecoCrossDocking', TabelaPrecoCrossDocking),
        ('TabelaPrecoEquipe', TabelaPrecoEquipe),
        ('ClienteMoto', ClienteMoto),
        ('VendedorMoto', VendedorMoto),
        ('EquipeVendasMoto', EquipeVendasMoto),
        ('CrossDocking', CrossDocking),
        ('TransportadoraMoto', TransportadoraMoto),
        ('EmpresaVendaMoto', EmpresaVendaMoto),
        ('DespesaMensal', DespesaMensal),
        ('CustosOperacionais', CustosOperacionais),
    ]

    todas_vazias = True

    for nome_tabela, modelo in tabelas_verificar:
        count = modelo.query.count()
        if count > 0:
            print(f"   ⚠️  {nome_tabela}: {count} registros restantes")
            todas_vazias = False
        else:
            print(f"   ✅ {nome_tabela}: vazia")

    if todas_vazias:
        print("\n✅ Todas as tabelas foram limpas com sucesso!")
    else:
        print("\n⚠️  Algumas tabelas ainda contêm dados. Verifique dependências de FK.")


if __name__ == '__main__':
    # Criar app Flask
    app = create_app()

    with app.app_context():
        sucesso = limpar_tabelas()

        if sucesso:
            verificar_limpeza()
