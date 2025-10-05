#!/usr/bin/env python3
"""
Script para verificar e criar tabelas do sistema MotoChefe
Uso: python app/motochefe/scripts/verificar_e_criar_tabelas.py
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import inspect, text

def verificar_tabelas():
    """Verifica quais tabelas do MotoChefe existem no banco"""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        tabelas_existentes = inspector.get_table_names()

        tabelas_motochefe = [
            'equipe_vendas_moto',
            'vendedor_moto',
            'transportadora_moto',
            'cliente_moto',
            'modelo_moto',
            'moto',
            'pedido_venda_moto',
            'pedido_venda_moto_item',
            'titulo_financeiro',
            'comissao_vendedor',
            'embarque_moto',
            'embarque_pedido',
            'custos_operacionais',
            'despesa_mensal'
        ]

        print("\n" + "="*60)
        print("VERIFICAÇÃO DE TABELAS DO SISTEMA MOTOCHEFE")
        print("="*60)

        tabelas_faltando = []
        for tabela in tabelas_motochefe:
            existe = tabela in tabelas_existentes
            status = "✅ EXISTE" if existe else "❌ NÃO EXISTE"
            print(f"{status:15} | {tabela}")

            if not existe:
                tabelas_faltando.append(tabela)

        print("="*60)

        if tabelas_faltando:
            print(f"\n⚠️  FALTAM {len(tabelas_faltando)} TABELAS!")
            print("\nOpções:")
            print("1. Execute o SQL: app/motochefe/scripts/create_tables.sql")
            print("2. Ou rode: python app/motochefe/scripts/verificar_e_criar_tabelas.py --criar")
            return False
        else:
            print("\n✅ TODAS AS 14 TABELAS ESTÃO CRIADAS!")

            # Verificar se há dados em custos_operacionais
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM custos_operacionais")).scalar()
                if result == 0:
                    print("\n⚠️  Tabela custos_operacionais está VAZIA!")
                    print("Execute o INSERT do SQL para adicionar custos padrão.")
                else:
                    print(f"✅ Custos operacionais: {result} registro(s)")
            except Exception as e:
                print(f"❌ Erro ao verificar custos: {e}")

            return True

def criar_tabelas():
    """Cria as tabelas usando SQLAlchemy"""
    app = create_app()

    with app.app_context():
        print("\n🔨 Criando tabelas do MotoChefe...")

        try:
            # Importar todos os models para registrar no metadata
            from app.motochefe.models import (
                EquipeVendasMoto, VendedorMoto, TransportadoraMoto, ClienteMoto,
                ModeloMoto, Moto,
                PedidoVendaMoto, PedidoVendaMotoItem,
                TituloFinanceiro, ComissaoVendedor,
                EmbarqueMoto, EmbarquePedido,
                CustosOperacionais, DespesaMensal
            )

            # Criar apenas as tabelas que não existem
            db.create_all()

            print("✅ Tabelas criadas com sucesso!")
            print("\n✅ SISTEMA PRONTO PARA USO!")
            print("\n⚠️  IMPORTANTE: Configure os custos operacionais acessando:")
            print("   /motochefe/custos")

        except Exception as e:
            print(f"\n❌ ERRO ao criar tabelas: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == '__main__':
    if '--criar' in sys.argv:
        criar_tabelas()
    else:
        verificar_tabelas()
