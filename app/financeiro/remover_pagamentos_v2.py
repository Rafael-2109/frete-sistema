#!/usr/bin/env python3
"""
Script para remover pagamentos duplicados no Odoo - Versão 2
============================================================

Abordagem direta: tenta deletar diretamente usando unlink.
Pagamentos isolados (não reconciliados) podem ser deletados.

Uso:
    python remover_pagamentos_v2.py

Autor: Rafael
Data: 2025-12-16
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.odoo.utils.connection import get_odoo_connection


def extrair_ids_do_arquivo():
    """Extrai os IDs de pagamento do arquivo ids_remover.md"""
    arquivo = Path(__file__).parent / "ids_remover.md"

    ids = []
    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Pula o cabeçalho (primeira linha)
    for i, linha in enumerate(linhas[1:], start=2):
        if not linha.strip():
            continue

        partes = linha.strip().split('\t')
        if len(partes) >= 1:
            try:
                id_pagamento = int(partes[0])
                ids.append(id_pagamento)
            except ValueError:
                pass

    return ids


def main():
    # Extrai IDs do arquivo
    print("Extraindo IDs do arquivo ids_remover.md...")
    ids = extrair_ids_do_arquivo()
    print(f"✓ {len(ids)} IDs extraídos\n")

    if not ids:
        print("❌ Nenhum ID encontrado!")
        sys.exit(1)

    # Conecta ao Odoo
    print("Conectando ao Odoo...")
    connection = get_odoo_connection()

    if not connection.authenticate():
        print("❌ Falha na autenticação com Odoo!")
        sys.exit(1)

    print("✓ Conectado ao Odoo\n")

    # Verifica quantos existem antes
    print("Verificando quantos pagamentos existem ANTES...")
    existentes_antes = connection.search(
        'account.payment',
        [['id', 'in', ids]]
    )
    print(f"Encontrados: {len(existentes_antes)} de {len(ids)}\n")

    # Remove em lotes
    LOTE = 20  # Lotes menores para evitar timeout
    total = len(ids)
    removidos = 0
    erros = []

    print(f"{'='*60}")
    print("INICIANDO REMOÇÃO")
    print(f"{'='*60}\n")

    for i in range(0, total, LOTE):
        lote_ids = ids[i:i+LOTE]
        lote_num = (i // LOTE) + 1
        total_lotes = (total + LOTE - 1) // LOTE

        print(f"Lote {lote_num}/{total_lotes}: IDs {lote_ids[0]} a {lote_ids[-1]}...", end=" ", flush=True)

        try:
            # Primeiro verifica quais existem neste lote
            existentes = connection.search(
                'account.payment',
                [['id', 'in', lote_ids]]
            )

            if not existentes:
                print("⚠ Nenhum encontrado (já removidos?)")
                continue

            # Tenta deletar diretamente
            result = connection.execute_kw(
                'account.payment',
                'unlink',
                [existentes]
            )

            if result:
                removidos += len(existentes)
                print(f"✓ {len(existentes)} removidos")
            else:
                print(f"⚠ Retorno inesperado: {result}")

        except Exception as e:
            erro_str = str(e)

            # Se o erro for de reconciliação, tenta um por um
            if "reconciled" in erro_str.lower() or "cannot be deleted" in erro_str.lower():
                print(f"⚠ Alguns reconciliados, tentando um por um...")

                for id_pag in lote_ids:
                    try:
                        # Verifica se existe
                        existe = connection.search(
                            'account.payment',
                            [['id', '=', id_pag]]
                        )

                        if not existe:
                            continue

                        connection.execute_kw(
                            'account.payment',
                            'unlink',
                            [[id_pag]]
                        )
                        removidos += 1

                    except Exception as e2:
                        erro_msg = f"ID {id_pag}: {str(e2)[:100]}"
                        erros.append(erro_msg)
            else:
                erro_msg = f"Lote {lote_num}: {erro_str[:200]}"
                erros.append(erro_msg)
                print(f"❌ Erro: {erro_str[:100]}")

    # Verifica quantos existem depois
    print(f"\n{'='*60}")
    print("VERIFICAÇÃO FINAL")
    print(f"{'='*60}\n")

    print("Verificando quantos pagamentos existem DEPOIS...")
    existentes_depois = connection.search(
        'account.payment',
        [['id', 'in', ids]]
    )
    print(f"Encontrados: {len(existentes_depois)} de {len(ids)}")

    realmente_removidos = len(existentes_antes) - len(existentes_depois)

    print(f"\n{'='*60}")
    print("RESUMO")
    print(f"{'='*60}")
    print(f"Total de IDs fornecidos: {total}")
    print(f"Existiam antes: {len(existentes_antes)}")
    print(f"Existem depois: {len(existentes_depois)}")
    print(f"Realmente removidos: {realmente_removidos}")

    if erros:
        print(f"\nErros encontrados: {len(erros)}")
        for erro in erros[:20]:  # Mostra só os primeiros 20
            print(f"  - {erro}")
        if len(erros) > 20:
            print(f"  ... e mais {len(erros) - 20} erros")

    if existentes_depois:
        print(f"\n⚠️ IDs que ainda existem (não foram removidos):")
        print(f"  {existentes_depois[:20]}")
        if len(existentes_depois) > 20:
            print(f"  ... e mais {len(existentes_depois) - 20}")


if __name__ == '__main__':
    main()
