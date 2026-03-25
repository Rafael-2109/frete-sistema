#!/usr/bin/env python3
"""Teste de extracao de veiculos (chassi/motor/cor) das NFs de teste.

Uso:
    source .venv/bin/activate
    python scripts/test_danfe_veiculos.py
"""

import logging
import os
import sys
import time

# Ajustar path para importar o parser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.carvia.services.danfe_pdf_parser import DanfePDFParser

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

NF_DIR = "/mnt/c/Users/rafael.nascimento/Downloads/NF"


def testar_nf(pdf_path: str) -> dict:
    """Testa uma NF e retorna resultado resumido."""
    nome = os.path.basename(pdf_path)
    parser = DanfePDFParser(pdf_path=pdf_path)

    if not parser.is_valid():
        return {'arquivo': nome, 'status': 'INVALIDO', 'veiculos': []}

    # Gate check
    tem_veiculo = parser._tem_indicativo_veiculo()

    if not tem_veiculo:
        return {
            'arquivo': nome,
            'status': 'SEM_VEICULO (gate)',
            'numero_nf': parser.get_numero_nf(),
            'veiculos': [],
        }

    # Extrair veiculos
    t0 = time.time()
    veiculos = parser.get_veiculos_info()
    elapsed = time.time() - t0

    return {
        'arquivo': nome,
        'status': 'OK' if veiculos else 'SEM_RESULTADO_LLM',
        'numero_nf': parser.get_numero_nf(),
        'qtd_veiculos': len(veiculos),
        'tempo_s': round(elapsed, 2),
        'veiculos': veiculos,
    }


def main():
    if not os.path.isdir(NF_DIR):
        print(f"Diretorio nao encontrado: {NF_DIR}")
        sys.exit(1)

    pdfs = sorted([
        os.path.join(NF_DIR, f)
        for f in os.listdir(NF_DIR)
        if f.lower().endswith('.pdf')
    ])

    print(f"\n{'='*80}")
    print(f"Teste de extracao de veiculos — {len(pdfs)} PDFs")
    print(f"{'='*80}\n")

    total_veiculos = 0
    total_com_veiculo = 0
    total_sem_veiculo = 0
    total_tempo = 0.0

    for pdf_path in pdfs:
        resultado = testar_nf(pdf_path)
        nome = resultado['arquivo']

        if resultado['status'] == 'SEM_VEICULO (gate)':
            print(f"  SKIP  {nome} (NF {resultado.get('numero_nf', '?')}) — sem indicativo de veiculo")
            total_sem_veiculo += 1
            continue

        if resultado['status'] == 'INVALIDO':
            print(f"  ERRO  {nome} — PDF invalido")
            continue

        qtd = resultado.get('qtd_veiculos', 0)
        tempo = resultado.get('tempo_s', 0)
        total_tempo += tempo

        if qtd > 0:
            total_com_veiculo += 1
            total_veiculos += qtd
            print(f"  OK    {nome} (NF {resultado.get('numero_nf', '?')}) "
                  f"— {qtd} veiculo(s) em {tempo}s")
            for v in resultado['veiculos']:
                modelo = v.get('modelo', '-')
                chassi = v.get('chassi', '-')
                motor = v.get('numero_motor', '-')
                cor = v.get('cor', '-')
                ano = v.get('ano_modelo', '')
                print(f"          {modelo:<20} chassi={chassi}  motor={motor}  "
                      f"cor={cor}  {ano}")
        else:
            print(f"  VAZIO {nome} (NF {resultado.get('numero_nf', '?')}) "
                  f"— gate passou mas LLM nao extraiu ({tempo}s)")

    print(f"\n{'='*80}")
    print(f"RESUMO:")
    print(f"  Total PDFs:       {len(pdfs)}")
    print(f"  Com veiculo:      {total_com_veiculo} ({total_veiculos} unidades)")
    print(f"  Sem veiculo:      {total_sem_veiculo} (gate)")
    print(f"  Tempo API total:  {total_tempo:.1f}s")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
