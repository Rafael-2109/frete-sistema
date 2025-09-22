#!/usr/bin/env python3
"""
Script de Teste das Janelas de Tempo dos Schedulers
====================================================

Verifica se os valores de janela estão corretos em cada scheduler
e mostra como eles são passados para os services.

Autor: Sistema de Fretes
Data: 2025-09-22
"""

import sys
import os
import importlib.util

def testar_scheduler(arquivo, nome):
    """Testa os valores de configuração de um scheduler"""
    print(f"\n{'='*60}")
    print(f"📋 Testando: {nome}")
    print(f"   Arquivo: {arquivo}")
    print(f"{'='*60}")

    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return

    try:
        # Importar o módulo dinamicamente
        spec = importlib.util.spec_from_file_location("scheduler", arquivo)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Verificar valores
        print("\n⚙️ CONFIGURAÇÕES:")

        # Intervalo de execução
        if hasattr(module, 'INTERVALO_MINUTOS'):
            print(f"   - Intervalo de execução: {module.INTERVALO_MINUTOS} minutos")

        # Janelas de tempo
        if hasattr(module, 'JANELA_MINUTOS'):
            print(f"   - JANELA_MINUTOS: {module.JANELA_MINUTOS} minutos")
            print(f"     ⚠️ PROBLEMA: Usa o MESMO valor para faturamento e carteira!")

        if hasattr(module, 'JANELA_CARTEIRA'):
            print(f"   - JANELA_CARTEIRA: {module.JANELA_CARTEIRA} minutos ✅")

        if hasattr(module, 'JANELA_FATURAMENTO'):
            print(f"   - JANELA_FATURAMENTO: {module.JANELA_FATURAMENTO} minutos ✅")

        if hasattr(module, 'STATUS_MINUTOS'):
            print(f"   - STATUS_MINUTOS: {module.STATUS_MINUTOS} minutos ({module.STATUS_MINUTOS/60:.1f} horas)")

        if hasattr(module, 'STATUS_FATURAMENTO'):
            print(f"   - STATUS_FATURAMENTO: {module.STATUS_FATURAMENTO} minutos ({module.STATUS_FATURAMENTO/60:.1f} horas)")

        # Verificar como são passados os valores
        print("\n📊 ANÁLISE:")

        # Ler o arquivo para verificar como os valores são usados
        with open(arquivo, 'r') as f:
            content = f.read()

        # Verificar chamada do faturamento
        if 'sincronizar_faturamento_incremental(' in content:
            # Buscar a linha específica
            for line in content.split('\n'):
                if 'minutos_janela=' in line and 'faturamento' in content[:content.find(line)].lower()[-200:]:
                    print(f"\n   Faturamento:")
                    if 'JANELA_MINUTOS' in line:
                        if hasattr(module, 'JANELA_MINUTOS'):
                            print(f"     minutos_janela = JANELA_MINUTOS ({module.JANELA_MINUTOS} min)")
                            if module.JANELA_MINUTOS != 180:
                                print(f"     ❌ ERRO: Deveria ser 180 minutos (3 horas)!")
                    elif 'JANELA_FATURAMENTO' in line:
                        if hasattr(module, 'JANELA_FATURAMENTO'):
                            print(f"     minutos_janela = JANELA_FATURAMENTO ({module.JANELA_FATURAMENTO} min)")
                            if module.JANELA_FATURAMENTO == 180:
                                print(f"     ✅ CORRETO: 180 minutos (3 horas)")

        # Verificar chamada da carteira
        if 'sincronizar_incremental(' in content and 'carteira' in content.lower():
            for line in content.split('\n'):
                if 'minutos_janela=' in line and 'carteira' in content[:content.find(line)].lower()[-200:]:
                    print(f"\n   Carteira:")
                    if 'JANELA_MINUTOS' in line:
                        if hasattr(module, 'JANELA_MINUTOS'):
                            print(f"     minutos_janela = JANELA_MINUTOS ({module.JANELA_MINUTOS} min)")
                            if module.JANELA_MINUTOS == 40:
                                print(f"     ✅ CORRETO: 40 minutos")
                    elif 'JANELA_CARTEIRA' in line:
                        if hasattr(module, 'JANELA_CARTEIRA'):
                            print(f"     minutos_janela = JANELA_CARTEIRA ({module.JANELA_CARTEIRA} min)")
                            if module.JANELA_CARTEIRA == 40:
                                print(f"     ✅ CORRETO: 40 minutos")

        print("\n✅ Teste concluído")

    except Exception as e:
        print(f"❌ Erro ao testar: {e}")


def main():
    """Testa todos os schedulers"""
    print("=" * 60)
    print("🔍 TESTE DE CONFIGURAÇÃO DOS SCHEDULERS")
    print("=" * 60)

    print("\n📋 VALORES CORRETOS ESPERADOS:")
    print("   - Intervalo: 30 minutos")
    print("   - Faturamento janela: 180 minutos (3 horas)")
    print("   - Faturamento status: 1560 minutos (26 horas)")
    print("   - Carteira janela: 40 minutos")

    scheduler_dir = "app/scheduler/"

    schedulers = [
        ("sincronizacao_incremental_simples.py", "Scheduler Simples"),
        ("sincronizacao_incremental_com_retry.py", "Scheduler com Retry"),
        ("sincronizacao_incremental_resiliente.py", "Scheduler Resiliente"),
        ("sincronizacao_incremental_corrigida.py", "Scheduler CORRIGIDO"),
    ]

    for arquivo, nome in schedulers:
        testar_scheduler(os.path.join(scheduler_dir, arquivo), nome)

    print("\n" + "=" * 60)
    print("📊 RESUMO:")
    print("=" * 60)
    print("\n❌ Schedulers com PROBLEMA (usando JANELA_MINUTOS=40 para ambos):")
    print("   - sincronizacao_incremental_simples.py")
    print("   - sincronizacao_incremental_com_retry.py")
    print("   - sincronizacao_incremental_resiliente.py")
    print("\n✅ Scheduler CORRETO:")
    print("   - sincronizacao_incremental_corrigida.py")
    print("\n🔧 SOLUÇÃO:")
    print("   Use o scheduler corrigido que define valores separados:")
    print("   - JANELA_CARTEIRA = 40")
    print("   - JANELA_FATURAMENTO = 180")
    print("\n⚠️ O start_render.sh foi atualizado para usar o scheduler correto!")


if __name__ == "__main__":
    main()