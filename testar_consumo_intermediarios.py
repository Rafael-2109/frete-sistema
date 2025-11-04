"""
Teste de consumo recursivo de intermediários
Caso Real: 4350150 → SALMOURA → Componentes
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app, db
from app.producao.models import ProgramacaoProducao
from app.manufatura.services.projecao_estoque_service import ServicoProjecaoEstoque

def criar_programacao_teste():
    """Cria programação de teste para 4350150"""
    app = create_app()
    with app.app_context():
        # Limpar programações de teste anteriores
        ProgramacaoProducao.query.filter_by(cod_produto='4350150').delete()

        # Criar programação de teste
        data_teste = date.today() + timedelta(days=2)

        prog = ProgramacaoProducao(
            cod_produto='4350150',
            nome_produto='AZEITONA VERDE RECHEADA - POUCH 18X170 G - CAMPO BELO',
            data_programacao=data_teste,
            qtd_programada=933,
        )

        db.session.add(prog)
        db.session.commit()

        print(f"✅ Programação criada: {prog.cod_produto} - {prog.qtd_programada} un em {data_teste}")
        return data_teste

def testar_projecao_componentes():
    """Testa projeção de todos os componentes do 4350150"""
    app = create_app()
    with app.app_context():
        service = ServicoProjecaoEstoque()

        data_teste = date.today() + timedelta(days=2)
        data_inicio = date.today()
        data_fim = date.today() + timedelta(days=30)

        print("\n" + "="*80)
        print("TESTE: Consumo recursivo de intermediários")
        print("="*80)

        # Estrutura esperada do 4350150
        componentes = {
            '102030601': {'nome': 'AZEITONA VERDE RECHEADA', 'qtd_unitaria': 2.7, 'tipo': 'DIRETO'},
            '201030023': {'nome': 'CAIXA DE PAPELAO', 'qtd_unitaria': 1.0, 'tipo': 'DIRETO'},
            '201030051': {'nome': 'CANTONEIRA', 'qtd_unitaria': 0.035714, 'tipo': 'DIRETO'},
            '205032230': {'nome': 'BOBINA FILME', 'qtd_unitaria': 0.122, 'tipo': 'DIRETO'},
            '207210014': {'nome': 'ETIQUETA', 'qtd_unitaria': 1.0, 'tipo': 'DIRETO'},
            '208000010': {'nome': 'FITA ADESIVA', 'qtd_unitaria': 1.1, 'tipo': 'DIRETO'},
            '301000001': {'nome': 'SALMOURA', 'qtd_unitaria': 2.34, 'tipo': 'INTERMEDIARIO'},
        }

        # Componentes indiretos (via SALMOURA)
        componentes_indiretos = {
            '104000002': {'nome': 'ACIDO CITRICO', 'qtd_por_salmoura': 0.005},
            '104000004': {'nome': 'BENZOATO', 'qtd_por_salmoura': 0.0015},
            '104000015': {'nome': 'SAL SEM IODO', 'qtd_por_salmoura': 0.04},
            '104000017': {'nome': 'AGUA', 'qtd_por_salmoura': 0.9535},
        }

        qtd_programada = 933
        qtd_salmoura_necessaria = qtd_programada * 2.34  # 2183.22

        print(f"\n📦 Produto: 4350150 (AZEITONA VERDE RECHEADA)")
        print(f"📅 Programação: {qtd_programada} un em {data_teste}")
        print(f"🧪 Salmoura necessária: {qtd_salmoura_necessaria:.2f} kg")

        # Testar SALMOURA (intermediário)
        print(f"\n{'='*80}")
        print(f"🔍 TESTANDO: 301000001 (SALMOURA - INTERMEDIÁRIO)")
        print(f"{'='*80}")

        saidas_salmoura = service._calcular_saidas_por_bom('301000001', data_inicio, data_fim)

        print(f"\n📊 Total de saídas encontradas: {len(saidas_salmoura)}")

        for saida in saidas_salmoura:
            print(f"\n  Tipo: {saida['tipo']}")
            print(f"  Data: {saida['data']}")
            print(f"  Quantidade: {saida['quantidade']:.2f}")
            print(f"  Produto produzido: {saida.get('produto_produzido', 'N/A')}")
            if saida['tipo'] == 'CONSUMO_INDIRETO':
                print(f"  ⚡ Via intermediário: {saida.get('via_intermediario', 'N/A')}")
                print(f"  ⚡ Componente final: {saida.get('componente_final', 'N/A')}")

        # Testar componentes indiretos
        print(f"\n{'='*80}")
        print(f"🧪 TESTANDO COMPONENTES INDIRETOS (via SALMOURA)")
        print(f"{'='*80}")

        for cod_componente, info in componentes_indiretos.items():
            print(f"\n🔍 {cod_componente} ({info['nome']})")

            saidas = service._calcular_saidas_por_bom(cod_componente, data_inicio, data_fim)

            qtd_esperada = qtd_salmoura_necessaria * info['qtd_por_salmoura']

            print(f"  Quantidade esperada: {qtd_esperada:.2f}")
            print(f"  Saídas encontradas: {len(saidas)}")

            if saidas:
                for saida in saidas:
                    print(f"    ✅ {saida['tipo']}: {saida['quantidade']:.2f} em {saida['data']}")
                    if saida['tipo'] == 'CONSUMO_INDIRETO':
                        print(f"       Via: {saida.get('via_intermediario', 'N/A')}")
            else:
                print(f"    ❌ ERRO: Nenhuma saída encontrada! (esperado {qtd_esperada:.2f})")

        # Testar um componente direto (para comparação)
        print(f"\n{'='*80}")
        print(f"🔍 TESTANDO COMPONENTE DIRETO (para comparação)")
        print(f"{'='*80}")

        print(f"\n🔍 102030601 (AZEITONA VERDE RECHEADA - DIRETO)")
        saidas_azeitona = service._calcular_saidas_por_bom('102030601', data_inicio, data_fim)

        qtd_esperada_azeitona = qtd_programada * 2.7
        print(f"  Quantidade esperada: {qtd_esperada_azeitona:.2f}")
        print(f"  Saídas encontradas: {len(saidas_azeitona)}")

        if saidas_azeitona:
            for saida in saidas_azeitona:
                print(f"    ✅ {saida['tipo']}: {saida['quantidade']:.2f} em {saida['data']}")
        else:
            print(f"    ❌ ERRO: Nenhuma saída encontrada!")

if __name__ == '__main__':
    print("🧪 Iniciando teste de consumo recursivo de intermediários...")

    # Criar programação de teste
    data_teste = criar_programacao_teste()

    # Executar testes
    testar_projecao_componentes()

    print("\n" + "="*80)
    print("✅ Teste concluído!")
    print("="*80)
