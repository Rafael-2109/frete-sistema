#!/usr/bin/env python3
"""
Script de Inicialização da Sincronização Incremental

ESTRATÉGIA SIMPLES E EFICAZ:
1. Executa sincronização IMEDIATAMENTE (recupera dados perdidos no deploy)
2. Inicia scheduler para rodar a cada 30 minutos
3. Busca sempre 40 minutos (10 minutos de sobreposição)

Isso GARANTE que nenhum dado seja perdido durante deploys!

Uso:
    python iniciar_sincronizacao_incremental.py
"""

import subprocess
import sys
import os

def main():
    """Inicia o scheduler de sincronização incremental"""

    print("="*60)
    print("🚀 INICIANDO SINCRONIZAÇÃO INCREMENTAL")
    print("="*60)
    print()
    print("📋 Estratégia:")
    print("1. Sincronização imediata (recupera dados do deploy)")
    print("2. Execuções a cada 30 minutos")
    print("3. Janela de 40 minutos (sobreposição de segurança)")
    print()
    print("="*60)

    # Caminho do script do scheduler
    scheduler_path = os.path.join(
        os.path.dirname(__file__),
        'app',
        'scheduler',
        'sincronizacao_incremental_simples.py'
    )

    if not os.path.exists(scheduler_path):
        print(f"❌ Erro: Script não encontrado em {scheduler_path}")
        sys.exit(1)

    try:
        # Executar o scheduler
        print("\n▶️  Iniciando scheduler...")
        print("-"*60)

        # Usar subprocess para manter o output em tempo real
        process = subprocess.Popen(
            [sys.executable, scheduler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Mostrar output em tempo real
        for line in iter(process.stdout.readline, ''):
            print(line, end='')

        process.wait()

    except KeyboardInterrupt:
        print("\n\n👋 Scheduler interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao executar scheduler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()