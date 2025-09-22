#!/usr/bin/env python3
"""
Script para testar a performance do módulo comercial
Compara o antes e depois das otimizações

Autor: Sistema de Fretes
Data: 21/01/2025
"""

import sys
import os
import time
import statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario
from app.comercial.services.cliente_service import ClienteService
from app.comercial.services.agregacao_service import AgregacaoComercialService
from flask_login import login_user


def medir_tempo(funcao, *args, **kwargs):
    """Mede o tempo de execução de uma função"""
    inicio = time.time()
    resultado = funcao(*args, **kwargs)
    tempo = time.time() - inicio
    return tempo, resultado


def testar_dashboard_antigo():
    """Testa o dashboard com a implementação antiga (N+1 queries)"""
    print("\n📊 Testando Dashboard ANTIGO (com N+1)...")

    # Simular código antigo
    from sqlalchemy import distinct
    from app.carteira.models import CarteiraPrincipal

    # Buscar equipes
    equipes_carteira = db.session.query(
        distinct(CarteiraPrincipal.equipe_vendas)
    ).filter(
        CarteiraPrincipal.equipe_vendas.isnot(None),
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).limit(5).all()  # Limitar para teste rápido

    equipes = [e[0] for e in equipes_carteira if e[0]]

    tempo_total = 0
    queries_count = 0

    # Para cada equipe (N+1 problem)
    for equipe in equipes:
        # Query 1: obter clientes
        clientes_cnpj = ClienteService.obter_clientes_por_equipe(equipe)
        queries_count += 1

        # Para cada cliente (nested N+1)
        for cnpj in clientes_cnpj[:10]:  # Limitar para teste
            # Query N: calcular valor
            inicio = time.time()
            valor = ClienteService.calcular_valor_em_aberto(cnpj, 'em_aberto')
            tempo_total += time.time() - inicio
            queries_count += 1

    return tempo_total, queries_count


def testar_dashboard_novo():
    """Testa o dashboard com a implementação otimizada"""
    print("\n🚀 Testando Dashboard NOVO (otimizado)...")

    inicio = time.time()
    resultado = AgregacaoComercialService.obter_dashboard_completo_otimizado()
    tempo_total = time.time() - inicio

    return tempo_total, len(resultado)


def testar_vendedores_antigo(equipe):
    """Testa vendedores com implementação antiga"""
    print(f"\n📊 Testando Vendedores ANTIGO para equipe {equipe}...")

    from sqlalchemy import distinct
    from app.carteira.models import CarteiraPrincipal

    # Buscar vendedores
    vendedores = db.session.query(
        distinct(CarteiraPrincipal.vendedor)
    ).filter(
        CarteiraPrincipal.equipe_vendas == equipe,
        CarteiraPrincipal.vendedor.isnot(None)
    ).limit(5).all()  # Limitar para teste

    vendedores_list = [v[0] for v in vendedores if v[0]]

    tempo_total = 0
    queries_count = 0

    # Para cada vendedor (N+1)
    for vendedor in vendedores_list:
        clientes_cnpj = ClienteService.obter_clientes_por_vendedor(vendedor)
        queries_count += 1

        # Para cada cliente (nested N+1)
        for cnpj in clientes_cnpj[:5]:  # Limitar
            inicio = time.time()
            valor = ClienteService.calcular_valor_em_aberto(cnpj, 'em_aberto')
            tempo_total += time.time() - inicio
            queries_count += 1

    return tempo_total, queries_count


def testar_vendedores_novo(equipe):
    """Testa vendedores com implementação otimizada"""
    print(f"\n🚀 Testando Vendedores NOVO para equipe {equipe}...")

    inicio = time.time()
    resultado = AgregacaoComercialService.obter_vendedores_equipe_otimizado(equipe)
    tempo_total = time.time() - inicio

    return tempo_total, len(resultado)


def testar_clientes_batch():
    """Testa cálculo de valores em batch"""
    print("\n🔬 Testando cálculo de valores em batch...")

    # Pegar alguns CNPJs para teste
    from app.carteira.models import CarteiraPrincipal
    from sqlalchemy import distinct

    cnpjs = db.session.query(
        distinct(CarteiraPrincipal.cnpj_cpf)
    ).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).limit(50).all()

    cnpjs_list = [c[0] for c in cnpjs if c[0]]

    # Teste 1: Método antigo (um por vez)
    print("  Método antigo (um por vez)...")
    inicio = time.time()
    for cnpj in cnpjs_list:
        ClienteService.calcular_valor_em_aberto(cnpj, 'em_aberto')
    tempo_antigo = time.time() - inicio

    # Teste 2: Método novo (batch)
    print("  Método novo (batch)...")
    inicio = time.time()
    valores = AgregacaoComercialService.calcular_valores_batch(cnpjs_list)
    tempo_novo = time.time() - inicio

    return tempo_antigo, tempo_novo, len(cnpjs_list)


def main():
    """Executa todos os testes de performance"""
    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("TESTE DE PERFORMANCE - MÓDULO COMERCIAL")
        print("="*80)
        print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Importar modelos necessários
        from app.carteira.models import CarteiraPrincipal

        resultados = {}

        try:
            # 1. Dashboard
            print("\n" + "-"*50)
            print("1. DASHBOARD DE EQUIPES")
            print("-"*50)

            tempo_antigo, queries_antigo = testar_dashboard_antigo()
            print(f"   ❌ Antigo: {tempo_antigo:.2f}s com ~{queries_antigo} queries")

            tempo_novo, equipes = testar_dashboard_novo()
            print(f"   ✅ Novo: {tempo_novo:.2f}s com 1 query ({equipes} equipes)")

            melhoria = ((tempo_antigo - tempo_novo) / tempo_antigo * 100) if tempo_antigo > 0 else 0
            print(f"   📈 Melhoria: {melhoria:.1f}% mais rápido")

            resultados['dashboard'] = {
                'antigo': tempo_antigo,
                'novo': tempo_novo,
                'melhoria': melhoria
            }

            # 2. Vendedores
            print("\n" + "-"*50)
            print("2. VENDEDORES POR EQUIPE")
            print("-"*50)

            # Pegar uma equipe para teste
            equipe_teste = db.session.query(
                CarteiraPrincipal.equipe_vendas
            ).filter(
                CarteiraPrincipal.equipe_vendas.isnot(None)
            ).first()

            if equipe_teste:
                equipe_nome = equipe_teste[0]

                tempo_antigo, queries_antigo = testar_vendedores_antigo(equipe_nome)
                print(f"   ❌ Antigo: {tempo_antigo:.2f}s com ~{queries_antigo} queries")

                tempo_novo, vendedores = testar_vendedores_novo(equipe_nome)
                print(f"   ✅ Novo: {tempo_novo:.2f}s com 1 query ({vendedores} vendedores)")

                melhoria = ((tempo_antigo - tempo_novo) / tempo_antigo * 100) if tempo_antigo > 0 else 0
                print(f"   📈 Melhoria: {melhoria:.1f}% mais rápido")

                resultados['vendedores'] = {
                    'antigo': tempo_antigo,
                    'novo': tempo_novo,
                    'melhoria': melhoria
                }

            # 3. Cálculo em Batch
            print("\n" + "-"*50)
            print("3. CÁLCULO DE VALORES")
            print("-"*50)

            tempo_antigo, tempo_novo, qtd = testar_clientes_batch()
            print(f"   ❌ Antigo: {tempo_antigo:.2f}s para {qtd} CNPJs")
            print(f"   ✅ Novo: {tempo_novo:.2f}s para {qtd} CNPJs")

            melhoria = ((tempo_antigo - tempo_novo) / tempo_antigo * 100) if tempo_antigo > 0 else 0
            print(f"   📈 Melhoria: {melhoria:.1f}% mais rápido")

            resultados['batch'] = {
                'antigo': tempo_antigo,
                'novo': tempo_novo,
                'melhoria': melhoria
            }

            # 4. Estatísticas Rápidas
            print("\n" + "-"*50)
            print("4. ESTATÍSTICAS GERAIS")
            print("-"*50)

            inicio = time.time()
            stats = AgregacaoComercialService.obter_estatisticas_rapidas()
            tempo = time.time() - inicio

            print(f"   ✅ Carregado em {tempo:.2f}s")
            print(f"   - Equipes: {stats['total_equipes']}")
            print(f"   - Vendedores: {stats['total_vendedores']}")
            print(f"   - Clientes: {stats['total_clientes']}")
            print(f"   - Valor Total: R$ {stats['valor_total_aberto']:,.2f}")

            # Resumo Final
            print("\n" + "="*80)
            print("📊 RESUMO DOS RESULTADOS")
            print("="*80)

            media_melhoria = statistics.mean([r['melhoria'] for r in resultados.values()])

            print(f"\n✅ Melhoria média: {media_melhoria:.1f}%")

            if media_melhoria > 70:
                print("🎉 EXCELENTE! Otimização alcançou a meta de 70%+")
            elif media_melhoria > 50:
                print("👍 BOM! Otimização significativa")
            else:
                print("⚠️ Otimização abaixo do esperado")

            print("\n💡 Recomendações:")
            print("   1. Execute os testes em horário de pico para resultados reais")
            print("   2. Monitore continuamente após deploy")
            print("   3. Considere implementar cache Redis para melhorias adicionais")

        except Exception as e:
            print(f"\n❌ ERRO durante teste: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()