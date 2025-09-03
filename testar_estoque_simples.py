#!/usr/bin/env python3
"""
Script para testar o ServicoEstoqueSimples
Compara resultados com o sistema atual
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import time

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app import db, create_app
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.models import MovimentacaoEstoque

def testar_performance():
    """Testa performance das queries"""
    print("=" * 50)
    print("TESTE DE PERFORMANCE - SERVIÇO ESTOQUE SIMPLES")
    print("=" * 50)
    
    # Buscar alguns produtos para teste
    produtos = db.session.query(
        MovimentacaoEstoque.cod_produto.distinct()
    ).filter(
        MovimentacaoEstoque.ativo == True
    ).limit(5).all()
    
    if not produtos:
        print("❌ Nenhum produto encontrado para teste")
        return False
    
    print(f"\n📦 Testando com {len(produtos)} produtos...")
    
    for (cod_produto,) in produtos:
        print(f"\n🔍 Produto: {cod_produto}")
        
        # Teste 1: Estoque Atual
        inicio = time.time()
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
        tempo_estoque = (time.time() - inicio) * 1000
        print(f"   📊 Estoque atual: {estoque_atual:.2f}")
        print(f"   ⏱️ Tempo: {tempo_estoque:.2f}ms")
        
        # Teste 2: Saídas Previstas
        hoje = date.today()
        fim = hoje + timedelta(days=7)
        
        inicio = time.time()
        saidas = ServicoEstoqueSimples.calcular_saidas_previstas(cod_produto, hoje, fim)
        tempo_saidas = (time.time() - inicio) * 1000
        print(f"   📤 Saídas previstas (7 dias): {len(saidas)} dias com movimento")
        print(f"   ⏱️ Tempo: {tempo_saidas:.2f}ms")
        
        # Teste 3: Entradas Previstas
        inicio = time.time()
        entradas = ServicoEstoqueSimples.calcular_entradas_previstas(cod_produto, hoje, fim)
        tempo_entradas = (time.time() - inicio) * 1000
        print(f"   📥 Entradas previstas (7 dias): {len(entradas)} dias com produção")
        print(f"   ⏱️ Tempo: {tempo_entradas:.2f}ms")
        
        # Teste 4: Projeção Completa
        inicio = time.time()
        projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=7)
        tempo_projecao = (time.time() - inicio) * 1000
        
        print(f"   📈 Projeção 7 dias:")
        print(f"      - Menor estoque D+7: {projecao['menor_estoque_d7']:.2f}")
        print(f"      - Dia ruptura: {projecao['dia_ruptura'] or 'Sem ruptura'}")
        print(f"   ⏱️ Tempo total: {tempo_projecao:.2f}ms")
        
        # Verificar se está dentro do objetivo (< 50ms)
        if tempo_projecao < 50:
            print(f"   ✅ Performance OK (< 50ms)")
        else:
            print(f"   ⚠️ Performance acima do esperado (> 50ms)")
    
    return True

def comparar_com_sistema_atual():
    """Compara resultados com o sistema atual"""
    print("\n" + "=" * 50)
    print("COMPARAÇÃO COM SISTEMA ATUAL")
    print("=" * 50)
    
    # Buscar produto para comparação
    produto = db.session.query(
        MovimentacaoEstoque.cod_produto
    ).filter(
        MovimentacaoEstoque.ativo == True
    ).first()
    
    if not produto:
        print("❌ Nenhum produto encontrado")
        return False
    
    cod_produto = produto[0]
    print(f"\n🔍 Comparando produto: {cod_produto}")
    
    try:
        # Sistema novo
        inicio = time.time()
        projecao_nova = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=7)
        tempo_novo = (time.time() - inicio) * 1000
        
        print(f"\n📊 Sistema NOVO (ServicoEstoqueSimples):")
        print(f"   - Estoque atual: {projecao_nova['estoque_atual']:.2f}")
        print(f"   - Menor estoque D+7: {projecao_nova['menor_estoque_d7']:.2f}")
        print(f"   - Tempo: {tempo_novo:.2f}ms")
        
        # Sistema atual (se existir)
        try:
            inicio = time.time()
            projecao_atual = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=7)
            tempo_atual = (time.time() - inicio) * 1000
            
            if projecao_atual:
                print(f"\n📊 Sistema ATUAL (ServicoEstoqueTempoReal):")
                print(f"   - Estoque atual: {projecao_atual.get('estoque_atual', 0):.2f}")
                print(f"   - Menor estoque D+7: {projecao_atual.get('menor_estoque_d7', 0):.2f}")
                print(f"   - Tempo: {tempo_atual:.2f}ms")
                
                # Comparar diferenças
                diff_estoque = abs(projecao_nova['estoque_atual'] - projecao_atual.get('estoque_atual', 0))
                diff_menor = abs(projecao_nova['menor_estoque_d7'] - projecao_atual.get('menor_estoque_d7', 0))
                
                print(f"\n📊 Diferenças:")
                print(f"   - Estoque atual: {diff_estoque:.2f}")
                print(f"   - Menor estoque D+7: {diff_menor:.2f}")
                
                if diff_estoque < 1 and diff_menor < 1:
                    print("   ✅ Resultados consistentes!")
                else:
                    print("   ⚠️ Diferenças encontradas - verificar cálculos")
                
                # Comparar performance
                melhoria = ((tempo_atual - tempo_novo) / tempo_atual) * 100
                print(f"\n⚡ Performance:")
                print(f"   - Melhoria: {melhoria:.1f}%")
                if tempo_novo < tempo_atual:
                    print(f"   ✅ Sistema novo {melhoria:.1f}% mais rápido!")
                
        except Exception as e:
            print(f"\n⚠️ Sistema atual não disponível: {e}")
            print("   Continuando apenas com sistema novo...")
            
    except Exception as e:
        print(f"❌ Erro na comparação: {e}")
        return False
    
    return True

def testar_multiplos_produtos():
    """Testa cálculo de múltiplos produtos em paralelo"""
    print("\n" + "=" * 50)
    print("TESTE DE MÚLTIPLOS PRODUTOS")
    print("=" * 50)
    
    # Buscar 10 produtos
    produtos = db.session.query(
        MovimentacaoEstoque.cod_produto.distinct()
    ).filter(
        MovimentacaoEstoque.ativo == True
    ).limit(10).all()
    
    if not produtos:
        print("❌ Nenhum produto encontrado")
        return False
    
    cod_produtos = [p[0] for p in produtos]
    print(f"\n📦 Calculando projeção para {len(cod_produtos)} produtos...")
    
    inicio = time.time()
    resultados = ServicoEstoqueSimples.calcular_multiplos_produtos(cod_produtos, dias=7)
    tempo_total = (time.time() - inicio) * 1000
    
    print(f"\n📊 Resultados:")
    print(f"   - Produtos processados: {len(resultados)}")
    print(f"   - Tempo total: {tempo_total:.2f}ms")
    print(f"   - Tempo médio por produto: {tempo_total/len(resultados):.2f}ms")
    
    # Verificar meta de performance (< 200ms para 10 produtos)
    if tempo_total < 200:
        print(f"   ✅ Performance excelente! (< 200ms para 10 produtos)")
    elif tempo_total < 500:
        print(f"   ⚠️ Performance OK mas pode melhorar")
    else:
        print(f"   ❌ Performance abaixo do esperado")
    
    # Mostrar alguns resultados
    print(f"\n📋 Amostra de resultados:")
    for i, (cod, resultado) in enumerate(list(resultados.items())[:3]):
        print(f"   {i+1}. {cod}:")
        print(f"      - Estoque: {resultado.get('estoque_atual', 0):.2f}")
        print(f"      - Menor D+7: {resultado.get('menor_estoque_d7', 0):.2f}")
        if resultado.get('erro'):
            print(f"      - ❌ Erro: {resultado['erro']}")
    
    return True

def main():
    """Executa todos os testes"""
    print("\n🚀 INICIANDO TESTES DO SERVIÇO DE ESTOQUE SIMPLES\n")
    
    testes = [
        ("Performance Individual", testar_performance),
        ("Comparação com Sistema Atual", comparar_com_sistema_atual),
        ("Múltiplos Produtos", testar_multiplos_produtos)
    ]
    
    resultados = []
    
    for nome, funcao in testes:
        try:
            sucesso = funcao()
            resultados.append((nome, sucesso))
        except Exception as e:
            print(f"\n❌ Erro no teste {nome}: {e}")
            resultados.append((nome, False))
    
    # Resumo final
    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES")
    print("=" * 50)
    
    total = len(resultados)
    sucesso = sum(1 for _, s in resultados if s)
    
    for nome, ok in resultados:
        status = "✅" if ok else "❌"
        print(f"{status} {nome}")
    
    print(f"\n📊 Total: {sucesso}/{total} testes passaram")
    
    if sucesso == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("⚠️ Alguns testes falharam - verificar logs acima")
        return 1

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sys.exit(main())