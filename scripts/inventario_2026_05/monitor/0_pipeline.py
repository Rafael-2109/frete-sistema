"""SCRIPT 0: Orquestrador. Roda os 4 scripts em sequencia.

Uso:
    python 0_pipeline.py                      # Roda tudo
    python 0_pipeline.py --skip=1             # Pula script 1 (usa cache)
    python 0_pipeline.py --so=4               # Roda so o 4 (assume cache existente)

Cache: /tmp/inventario_monitor/ (CSVs intermediarios — script 1, 2, 3)
Output final: docs/inventario-2026-05/07-relatorios/MONITOR_DIFF_<timestamp>.xlsx
"""
import argparse
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def rodar(script_name, extra_args=None):
    """Executa um dos scripts via subprocess com mesmo Python."""
    path = os.path.join(HERE, script_name)
    cmd = [sys.executable, path]
    if extra_args:
        cmd.extend(extra_args)
    print(f'\n>>> Rodando {script_name} <<<')
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f'ERRO em {script_name} (returncode={r.returncode})')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip', default='', help='Lista CSV de scripts a pular (ex: 1,2)')
    ap.add_argument('--so', default='', help='Roda APENAS este script (ex: 4)')
    ap.add_argument('--cache-dir', default=None)
    ap.add_argument('--inv-path', default=None,
                    help='Caminho COMPILADO INV (para script 3)')
    ap.add_argument('--data-inicio', default=None,
                    help='YYYY-MM-DD (para script 2)')
    args = ap.parse_args()

    skip = set(args.skip.split(',')) if args.skip else set()
    so = args.so.strip() if args.so else None

    extras_comuns = []
    if args.cache_dir:
        extras_comuns += ['--cache-dir', args.cache_dir]

    scripts = [
        ('1', '1_baixar_estoques.py', list(extras_comuns)),
        ('2', '2_baixar_movimentacoes.py',
         list(extras_comuns) + (['--data-inicio', args.data_inicio] if args.data_inicio else [])),
        ('3', '3_agregar_lote.py',
         list(extras_comuns) + (['--inv-path', args.inv_path] if args.inv_path else [])),
        ('4', '4_gerar_diffs.py', list(extras_comuns)),
    ]

    for num, name, extras in scripts:
        if so and so != num:
            continue
        if num in skip:
            print(f'(skip {num})')
            continue
        rodar(name, extras)

    print('\nPipeline concluido.')


if __name__ == '__main__':
    main()
