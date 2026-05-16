"""
Geracao SPED ECD — execucao standalone (sem worker RQ).

Versao da iteracao: lida de `app.relatorios_fiscais.services.sped_ecd_constantes.VERSAO_SPED`
(fonte unica da verdade — bump la antes de regerar).

Periodo: 01/07/2024 a 31/12/2024 (consistente entre iteracoes para comparacao com PVA).
Output: /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_{VERSAO_SPED}_3COMPANIES.txt

Uso:
    source .venv/bin/activate
    python scripts/sped_ecd/gerar_sped.py

Protocolo apos rodar (ver app/relatorios_fiscais/CLAUDE.md secao "PROTOCOLO DE NOVA VERSAO"):
    1. Append linha em HISTORICO DE ITERACOES (SPED_ECD_PLANO.md)
    2. Atualizar STATUS das CATEGORIAs corrigidas
    3. Enviar arquivo ao PVA externo, receber PDF, atualizar PLANO
"""
import os
import sys
import time
from datetime import date

# sys.path para rodar como standalone
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main() -> int:
    from app import create_app
    from app.relatorios_fiscais.services.sped_ecd_constantes import VERSAO_SPED

    output_path = (
        f'/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_'
        f'{VERSAO_SPED}_3COMPANIES.txt'
    )
    tag = f'[{VERSAO_SPED}]'

    app = create_app()

    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        from app.relatorios_fiscais.services.sped_ecd_service import (
            gerar_sped_ecd_centralizado,
            validar_arquivo_gerado,
        )

        t0 = time.time()
        print(f'{tag} Conectando ao Odoo...', flush=True)
        conn = get_odoo_connection()
        if not conn.authenticate():
            print(f'{tag} ERRO: autenticacao Odoo falhou', flush=True)
            return 1
        print(f'{tag} Conectado em {time.time() - t0:.1f}s', flush=True)

        params = {
            'date_ini': date(2024, 7, 1),
            'date_fim': date(2024, 12, 31),
            'qualif_socio': '205',
            'notas_explicativas': '',
        }

        ultima_etapa = ['']
        def progresso(info: dict):
            etapa = info.get('etapa', '') or ''
            msg = info.get('mensagem', '') or ''
            if etapa and etapa != ultima_etapa[0]:
                ultima_etapa[0] = etapa
                elapsed = time.time() - t0
                print(f'{tag} [{elapsed:>6.1f}s] [{etapa}] {msg}', flush=True)
            elif info.get('progresso_chunk'):
                elapsed = time.time() - t0
                print(f'{tag} [{elapsed:>6.1f}s] streaming: {info["progresso_chunk"]}', flush=True)

        print(f'{tag} Gerando SPED ECD (3 companies, 6 meses)...', flush=True)
        sped = gerar_sped_ecd_centralizado(conn, params, progresso_callback=progresso)

        # Salvar
        sped.seek(0, 2)  # SEEK_END
        tamanho = sped.tell()
        sped.seek(0)
        with open(output_path, 'wb') as f:
            f.write(sped.read())
        sped.seek(0)
        elapsed_total = time.time() - t0
        size_mb = tamanho / 1024 / 1024
        print(f'\n{tag} Arquivo salvo: {output_path}', flush=True)
        print(f'{tag} Tamanho: {size_mb:.2f} MB | Duracao: {elapsed_total:.1f}s', flush=True)

        # Validar
        print(f'\n{tag} Validando via SpedEcdValidator...', flush=True)
        resultado = validar_arquivo_gerado(sped)
        n_err = len(resultado['erros'])
        n_warn = len(resultado['warnings'])
        print(f'{tag} Valido: {resultado["valido"]} | Erros: {n_err} | Warnings: {n_warn}', flush=True)

        if n_err > 0:
            print(f'\n{tag} === PRIMEIROS 20 ERROS ===', flush=True)
            for e in resultado['erros'][:20]:
                print(f"{tag} [{e.get('severidade', '')}] {e.get('registro', '')}: {e.get('titulo', '')}", flush=True)

        if n_warn > 0:
            print(f'\n{tag} === PRIMEIROS 10 WARNINGS ===', flush=True)
            for w in resultado['warnings'][:10]:
                print(f"{tag} [{w.get('severidade', '')}] {w.get('registro', '')}: {w.get('titulo', '')}", flush=True)

        # Sanity check: contar I250 negativos
        import subprocess
        result = subprocess.run(
            ['grep', '-c', '|I250|.*|-[0-9]', output_path],
            capture_output=True, text=True,
        )
        n_neg = result.stdout.strip() or '0'
        print(f'\n{tag} I250 com VL_DC negativo: {n_neg} (esperado 0)', flush=True)

        print(f'\n{tag} === PROXIMOS PASSOS ===', flush=True)
        print(f'{tag} 1. Append linha no HISTORICO de SPED_ECD_PLANO.md', flush=True)
        print(f'{tag} 2. Enviar {output_path} ao PVA', flush=True)
        print(f'{tag} 3. Apos PVA: atualizar STATUS das CATEGORIAs', flush=True)

        return 0 if resultado['valido'] and n_neg == '0' else 2


if __name__ == '__main__':
    sys.exit(main())
