"""
DEBUG: Análise profunda do consumo de intermediários
Identifica exatamente onde o fluxo está quebrando
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app, db
from app.producao.models import ProgramacaoProducao
from app.manufatura.models import ListaMateriais, CadastroPalletizacao

def debug_fluxo_completo():
    """Debug do fluxo completo de busca de consumos"""
    app = create_app()
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 DEBUG: Consumo de ACIDO CITRICO (104000002)")
        print("="*80)

        cod_componente = '104000002'

        # PASSO 1: Verificar quem consome ACIDO CITRICO na BOM
        print(f"\n📋 PASSO 1: Quem consome {cod_componente}?")
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        print(f"   Encontrado {len(boms)} registro(s) na ListaMateriais:")
        for bom in boms:
            print(f"   ✅ {bom.cod_produto_produzido} ({bom.nome_produto_produzido}) consome {bom.qtd_utilizada} de {cod_componente}")

        if not boms:
            print("   ❌ NENHUM produto consome este componente!")
            return

        produtos_produzidos = [bom.cod_produto_produzido for bom in boms]

        # PASSO 2: Verificar se esses produtos têm programação
        print(f"\n📅 PASSO 2: Esses produtos têm programação?")
        data_inicio = date.today()
        data_fim = date.today() + timedelta(days=30)

        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto.in_(produtos_produzidos),
            ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
        ).all()

        print(f"   Encontrado {len(programacoes)} programação(ões):")
        for prog in programacoes:
            print(f"   ✅ {prog.cod_produto}: {prog.qtd_programada} un em {prog.data_programacao}")

        if not programacoes:
            print(f"   ❌ NENHUMA programação encontrada para: {produtos_produzidos}")
            print(f"   ⚠️  ESTE É O PROBLEMA! Produtos intermediários não são programados!")

        # PASSO 3: Verificar se é intermediário
        print(f"\n🔍 PASSO 3: Verificar se produtos são intermediários")
        for cod_prod in produtos_produzidos:
            produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_prod).first()

            if not produto:
                print(f"   ❌ {cod_prod}: NÃO encontrado no CadastroPalletizacao")
                continue

            eh_produzido = produto.produto_produzido

            # Consome componentes?
            tem_bom = ListaMateriais.query.filter_by(
                cod_produto_produzido=cod_prod,
                status='ativo'
            ).first() is not None

            # É usado como componente?
            eh_usado = ListaMateriais.query.filter_by(
                cod_produto_componente=cod_prod,
                status='ativo'
            ).first() is not None

            eh_intermediario = eh_produzido and tem_bom and eh_usado

            print(f"   {cod_prod}:")
            print(f"      - produto_produzido: {eh_produzido}")
            print(f"      - Tem BOM (consome): {tem_bom}")
            print(f"      - Usado como componente: {eh_usado}")
            print(f"      → É intermediário: {eh_intermediario}")

        # PASSO 4: Verificar quem consome o intermediário (upstream)
        print(f"\n⬆️  PASSO 4: Quem consome o intermediário {produtos_produzidos[0]}?")
        cod_intermediario = produtos_produzidos[0]

        boms_upstream = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_intermediario,
            ListaMateriais.status == 'ativo'
        ).all()

        print(f"   Encontrado {len(boms_upstream)} produto(s) que consomem {cod_intermediario}:")
        for bom in boms_upstream:
            print(f"   ✅ {bom.cod_produto_produzido} ({bom.nome_produto_produzido}) consome {bom.qtd_utilizada}")

            # Verificar se ESTE tem programação
            prog_upstream = ProgramacaoProducao.query.filter(
                ProgramacaoProducao.cod_produto == bom.cod_produto_produzido,
                ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
            ).first()

            if prog_upstream:
                print(f"      📅 TEM PROGRAMAÇÃO: {prog_upstream.qtd_programada} un em {prog_upstream.data_programacao}")
            else:
                print(f"      ❌ SEM PROGRAMAÇÃO")

if __name__ == '__main__':
    debug_fluxo_completo()

    print("\n" + "="*80)
    print("✅ Debug concluído!")
    print("="*80)
