"""
CLI de conversao de extrato bancario SRM Bank (PDF) -> OFX.

A logica de parse/validacao/geracao vive no service compartilhado
`app/financeiro/services/extrato_pdf_srm_service.py` (consumido tambem pela
rota web `routes/conversor_extrato_srm.py`). Este arquivo e' apenas a casca CLI.

USO
---
    source .venv/bin/activate

    # 1) Validar (nao gera nada, so confere a integridade):
    python app/financeiro/scripts/importar_extrato_pdf_srm.py --check \\
        ~/Extrato-1780942825963.pdf ~/Extrato-1780942894579.pdf

    # 2) Gerar OFX (default: ao lado do PDF; ou --out DIR):
    python app/financeiro/scripts/importar_extrato_pdf_srm.py --ofx \\
        --out /tmp/ofx ~/Extrato-*.pdf

O OFX gerado e' importado pela tela nativa do Odoo (Conciliacao Bancaria ->
Importar Extrato) no journal cujo bank_account_id casa com a conta do PDF.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.financeiro.services.extrato_pdf_srm_service import (  # noqa: E402
    parse_pdf, validar, gerar_ofx, analisar_continuidade,
)


def _imprimir_resumo(nome, resumo, erros, warnings):
    print(f'\n=== {nome} ===')
    if resumo:
        print(f"  conta {resumo['conta']} (banco {resumo['banco']}) | "
              f"periodo {resumo['periodo']}")
        print(f"  transacoes: {resumo['n_transacoes']} "
              f"(com hora: {resumo['com_hora']}, sem hora: {resumo['sem_hora']})")
        print(f"  saldo anterior: {resumo['saldo_anterior']} | "
              f"saldo final: {resumo['saldo_final']}")
        print(f"  creditos: {resumo['creditos']} | debitos: {resumo['debitos']}")
    for w in warnings:
        print(f'  [WARN] {w}')
    for e in erros:
        print(f'  [ERRO] {e}')
    print(f"  >> {'OK - integro' if not erros else 'REJEITADO'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description='Conversor de extrato SRM Bank (PDF -> OFX).')
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--check', action='store_true',
                       help='So valida a integridade (nao gera arquivo).')
    grupo.add_argument('--ofx', action='store_true',
                       help='Valida e gera OFX (so se a validacao passar).')
    ap.add_argument('--out', default=None,
                    help='Diretorio de saida do OFX (default: ao lado do PDF).')
    ap.add_argument('pdfs', nargs='+', help='Caminhos dos PDFs.')
    args = ap.parse_args(argv)

    falhas = 0
    parsings = []
    for caminho in args.pdfs:
        nome = os.path.basename(caminho)
        try:
            parsed = parse_pdf(caminho, nome=nome)
        except Exception as exc:  # parsing fatal
            print(f'\n=== {nome} ===\n  [ERRO] falha no parse: {exc}')
            falhas += 1
            continue
        ok, erros, warnings, resumo = validar(parsed)
        _imprimir_resumo(nome, resumo, erros, warnings)
        if not ok:
            falhas += 1
            continue
        parsings.append((caminho, parsed))

    # Validacao de continuidade entre arquivos (saldo final -> SALDO ANTERIOR)
    if len(parsings) > 1:
        print('\n=== CONTINUIDADE ENTRE ARQUIVOS ===')
        for c in analisar_continuidade([p for _, p in parsings]):
            estado = 'continuo' if c['continuo'] else f"GAP de {c['gap']}"
            print(f"  {c['de']} (fim {c['fim']}) -> "
                  f"{c['para']} (SALDO ANTERIOR {c['ini']}): {estado}")

    if args.ofx:
        for caminho, parsed in parsings:
            base = os.path.splitext(os.path.basename(caminho))[0]
            destino_dir = args.out or os.path.dirname(os.path.abspath(caminho))
            os.makedirs(destino_dir, exist_ok=True)
            destino = os.path.join(destino_dir, base + '.ofx')
            with open(destino, 'w', encoding='latin-1') as fh:
                fh.write(gerar_ofx(parsed))
            print(f'  [OFX] {destino} ({len(parsed["transacoes"])} transacoes)')

    if falhas:
        print(f'\n{falhas} arquivo(s) REJEITADO(S).')
        return 1
    print('\nTodos os arquivos integros.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
