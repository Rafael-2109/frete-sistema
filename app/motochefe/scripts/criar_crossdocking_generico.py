#!/usr/bin/env python3
"""
Script: Criar registro CrossDocking genérico
Data: 2025-10-08
Descrição: Insere o único registro genérico de CrossDocking compartilhado por todos os clientes
"""
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from app.motochefe.models import CrossDocking
from decimal import Decimal

def criar_crossdocking_generico():
    """
    Cria o registro único genérico de CrossDocking
    Se já existir, atualiza os valores padrão
    """
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("CRIAÇÃO DO CROSSDOCKING GENÉRICO")
        print("=" * 70)

        # Verificar se já existe
        crossdocking = CrossDocking.query.first()

        if crossdocking:
            print(f"⚠️  CrossDocking já existe: {crossdocking.nome} (ID: {crossdocking.id})")
            resposta = input("Deseja atualizar os valores padrão? (s/n): ")

            if resposta.lower() != 's':
                print("❌ Operação cancelada pelo usuário.")
                return

            print("\n📝 Atualizando valores...")
            modo = 'atualizado'
        else:
            print("✅ Nenhum CrossDocking encontrado. Criando novo registro...")
            crossdocking = CrossDocking()
            modo = 'criado'

        # Configurar valores padrão
        crossdocking.nome = "CrossDocking Genérico"
        crossdocking.descricao = "Registro único compartilhado por todos os clientes com crossdocking=True"

        # Movimentação
        crossdocking.custo_movimentacao = Decimal('50.00')
        crossdocking.incluir_custo_movimentacao = True

        # Precificação
        crossdocking.tipo_precificacao = 'TABELA'  # Valores: TABELA, MARKUP
        crossdocking.markup = Decimal('0.00')  # Usado se tipo_precificacao='MARKUP'

        # Comissão
        crossdocking.tipo_comissao = 'FIXA_EXCEDENTE'  # Valores: FIXA_EXCEDENTE, PERCENTUAL
        crossdocking.valor_comissao_fixa = Decimal('200.00')
        crossdocking.percentual_comissao = Decimal('0.00')
        crossdocking.comissao_rateada = True

        # Parcelamento e Prazo
        crossdocking.permitir_prazo = False
        crossdocking.permitir_parcelamento = True
        crossdocking.permitir_montagem = True

        # Ativo
        crossdocking.ativo = True

        # Salvar
        if modo == 'criado':
            db.session.add(crossdocking)

        db.session.commit()

        print("\n" + "=" * 70)
        print(f"✅ CrossDocking {modo} com sucesso!")
        print("=" * 70)
        print(f"\n📋 DADOS DO REGISTRO:\n")
        print(f"  ID: {crossdocking.id}")
        print(f"  Nome: {crossdocking.nome}")
        print(f"  Descrição: {crossdocking.descricao}")
        print(f"\n💰 MOVIMENTAÇÃO:")
        print(f"  Custo: R$ {crossdocking.custo_movimentacao}")
        print(f"  Incluir no preço: {crossdocking.incluir_custo_movimentacao}")
        print(f"\n💵 PRECIFICAÇÃO:")
        print(f"  Tipo: {crossdocking.tipo_precificacao}")
        print(f"  Markup: {crossdocking.markup}%")
        print(f"\n💼 COMISSÃO:")
        print(f"  Tipo: {crossdocking.tipo_comissao}")
        print(f"  Valor Fixo: R$ {crossdocking.valor_comissao_fixa}")
        print(f"  Percentual: {crossdocking.percentual_comissao}%")
        print(f"  Rateada: {crossdocking.comissao_rateada}")
        print(f"\n⚙️  OPÇÕES:")
        print(f"  Permitir Prazo: {crossdocking.permitir_prazo}")
        print(f"  Permitir Parcelamento: {crossdocking.permitir_parcelamento}")
        print(f"  Permitir Montagem: {crossdocking.permitir_montagem}")
        print(f"\n📊 STATUS:")
        print(f"  Ativo: {crossdocking.ativo}")
        print("\n" + "=" * 70)
        print("⚠️  PRÓXIMOS PASSOS:")
        print("=" * 70)
        print("1. Configure a Tabela de Preços em /motochefe/crossdocking/tabela-precos")
        print("2. Cadastre clientes marcando 'CrossDocking' quando necessário")
        print("3. Ajuste os valores padrão através da interface de edição")
        print("=" * 70)

if __name__ == '__main__':
    try:
        criar_crossdocking_generico()
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
