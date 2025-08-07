#!/usr/bin/env python3
"""
Script de Teste de Performance do Sistema de Estoque em Tempo Real
Verifica se as consultas estão dentro do limite de 100ms
"""

import os
import sys
import time
import random
from datetime import date, timedelta
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.api_tempo_real import APIEstoqueTempoReal
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal


def medir_tempo(func, *args, **kwargs):
    """Mede o tempo de execução de uma função"""
    inicio = time.perf_counter()
    resultado = func(*args, **kwargs)
    fim = time.perf_counter()
    tempo_ms = (fim - inicio) * 1000
    return resultado, tempo_ms


def criar_dados_teste(num_produtos=100, num_movimentacoes=500):
    """Cria dados de teste no banco"""
    print(f"\n📝 Criando {num_produtos} produtos e {num_movimentacoes} movimentações...")
    
    produtos_criados = []
    hoje = date.today()
    
    # Criar produtos
    for i in range(num_produtos):
        cod_produto = f"TEST_{i:04d}"
        
        estoque = EstoqueTempoReal(
            cod_produto=cod_produto,
            nome_produto=f"Produto Teste {i}",
            saldo_atual=Decimal(str(random.randint(0, 1000)))
        )
        db.session.add(estoque)
        produtos_criados.append(cod_produto)
    
    # Criar movimentações previstas
    for _ in range(num_movimentacoes):
        cod_produto = random.choice(produtos_criados)
        data_prevista = hoje + timedelta(days=random.randint(1, 30))
        
        mov = MovimentacaoPrevista(
            cod_produto=cod_produto,
            data_prevista=data_prevista,
            entrada_prevista=Decimal(str(random.randint(0, 100))),
            saida_prevista=Decimal(str(random.randint(0, 100)))
        )
        db.session.add(mov)
    
    db.session.commit()
    print(f"✅ Dados de teste criados")
    return produtos_criados


def testar_consulta_workspace(produtos, num_testes=10):
    """Testa performance da consulta workspace"""
    print(f"\n🔍 Testando consulta workspace com {len(produtos)} produtos...")
    
    tempos = []
    for i in range(num_testes):
        # Selecionar produtos aleatórios
        num_produtos = random.randint(5, 20)
        produtos_selecionados = random.sample(produtos, min(num_produtos, len(produtos)))
        
        # Medir tempo
        resultado, tempo_ms = medir_tempo(
            APIEstoqueTempoReal.consultar_workspace,
            produtos_selecionados
        )
        
        tempos.append(tempo_ms)
        status = "✅" if tempo_ms < 100 else "❌"
        print(f"  Teste {i+1:2d}: {tempo_ms:6.2f}ms {status} ({len(produtos_selecionados)} produtos)")
    
    # Estatísticas
    tempo_medio = sum(tempos) / len(tempos)
    tempo_max = max(tempos)
    tempo_min = min(tempos)
    
    print(f"\n  📊 Estatísticas:")
    print(f"     Média: {tempo_medio:.2f}ms")
    print(f"     Mínimo: {tempo_min:.2f}ms")
    print(f"     Máximo: {tempo_max:.2f}ms")
    
    return tempo_medio < 100


def testar_consulta_individual(produtos, num_testes=20):
    """Testa performance da consulta individual"""
    print(f"\n🔍 Testando consulta individual...")
    
    tempos = []
    for i in range(num_testes):
        cod_produto = random.choice(produtos)
        
        # Medir tempo
        resultado, tempo_ms = medir_tempo(
            APIEstoqueTempoReal.consultar_produto,
            cod_produto
        )
        
        tempos.append(tempo_ms)
        status = "✅" if tempo_ms < 100 else "❌"
        print(f"  Teste {i+1:2d}: {tempo_ms:6.2f}ms {status}")
    
    # Estatísticas
    tempo_medio = sum(tempos) / len(tempos)
    tempo_max = max(tempos)
    tempo_min = min(tempos)
    
    print(f"\n  📊 Estatísticas:")
    print(f"     Média: {tempo_medio:.2f}ms")
    print(f"     Mínimo: {tempo_min:.2f}ms")
    print(f"     Máximo: {tempo_max:.2f}ms")
    
    return tempo_medio < 100


def testar_consulta_rupturas(num_testes=10):
    """Testa performance da consulta de rupturas"""
    print(f"\n🔍 Testando consulta de rupturas...")
    
    tempos = []
    for i in range(num_testes):
        dias = random.randint(3, 14)
        
        # Medir tempo
        resultado, tempo_ms = medir_tempo(
            APIEstoqueTempoReal.consultar_rupturas,
            dias
        )
        
        tempos.append(tempo_ms)
        status = "✅" if tempo_ms < 100 else "❌"
        print(f"  Teste {i+1:2d}: {tempo_ms:6.2f}ms {status} ({dias} dias)")
    
    # Estatísticas
    tempo_medio = sum(tempos) / len(tempos)
    tempo_max = max(tempos)
    tempo_min = min(tempos)
    
    print(f"\n  📊 Estatísticas:")
    print(f"     Média: {tempo_medio:.2f}ms")
    print(f"     Mínimo: {tempo_min:.2f}ms")
    print(f"     Máximo: {tempo_max:.2f}ms")
    
    return tempo_medio < 100


def testar_calculo_ruptura(produtos, num_testes=10):
    """Testa performance do cálculo de ruptura"""
    print(f"\n🔍 Testando cálculo de ruptura D+7...")
    
    tempos = []
    for i in range(num_testes):
        cod_produto = random.choice(produtos)
        
        # Medir tempo
        resultado, tempo_ms = medir_tempo(
            ServicoEstoqueTempoReal.calcular_ruptura_d7,
            cod_produto
        )
        
        tempos.append(tempo_ms)
        status = "✅" if tempo_ms < 100 else "❌"
        print(f"  Teste {i+1:2d}: {tempo_ms:6.2f}ms {status}")
    
    # Estatísticas
    tempo_medio = sum(tempos) / len(tempos)
    tempo_max = max(tempos)
    tempo_min = min(tempos)
    
    print(f"\n  📊 Estatísticas:")
    print(f"     Média: {tempo_medio:.2f}ms")
    print(f"     Mínimo: {tempo_min:.2f}ms")
    print(f"     Máximo: {tempo_max:.2f}ms")
    
    return tempo_medio < 100


def limpar_dados_teste():
    """Remove dados de teste"""
    print("\n🧹 Limpando dados de teste...")
    
    # Remover produtos de teste
    EstoqueTempoReal.query.filter(
        EstoqueTempoReal.cod_produto.like('TEST_%')
    ).delete()
    
    # Remover movimentações de teste
    MovimentacaoPrevista.query.filter(
        MovimentacaoPrevista.cod_produto.like('TEST_%')
    ).delete()
    
    db.session.commit()
    print("✅ Dados de teste removidos")


def main():
    """Função principal de teste"""
    print("""
╔══════════════════════════════════════════════════════╗
║    TESTE DE PERFORMANCE - ESTOQUE TEMPO REAL        ║
║         Objetivo: Todas consultas < 100ms           ║
╚══════════════════════════════════════════════════════╝
    """)
    
    app = create_app()
    
    with app.app_context():
        # Limpar dados antigos de teste
        limpar_dados_teste()
        
        # Criar dados de teste
        produtos = criar_dados_teste(
            num_produtos=100,
            num_movimentacoes=500
        )
        
        # Executar testes
        resultados = []
        
        # Teste 1: Consulta Workspace
        resultado = testar_consulta_workspace(produtos)
        resultados.append(("Consulta Workspace", resultado))
        
        # Teste 2: Consulta Individual
        resultado = testar_consulta_individual(produtos)
        resultados.append(("Consulta Individual", resultado))
        
        # Teste 3: Consulta Rupturas
        resultado = testar_consulta_rupturas()
        resultados.append(("Consulta Rupturas", resultado))
        
        # Teste 4: Cálculo Ruptura
        resultado = testar_calculo_ruptura(produtos)
        resultados.append(("Cálculo Ruptura D+7", resultado))
        
        # Limpar dados de teste
        limpar_dados_teste()
        
        # Resumo final
        print("""
╔══════════════════════════════════════════════════════╗
║                  RESUMO DOS TESTES                   ║
╚══════════════════════════════════════════════════════╝
        """)
        
        todos_passaram = True
        for nome, passou in resultados:
            status = "✅ PASSOU" if passou else "❌ FALHOU"
            print(f"  {nome:25s}: {status}")
            if not passou:
                todos_passaram = False
        
        print()
        if todos_passaram:
            print("🎉 TODOS OS TESTES PASSARAM!")
            print("✅ Sistema atende ao requisito de performance < 100ms")
        else:
            print("❌ ALGUNS TESTES FALHARAM")
            print("⚠️  Sistema precisa de otimização")
        
        return 0 if todos_passaram else 1


if __name__ == '__main__':
    exit(main())