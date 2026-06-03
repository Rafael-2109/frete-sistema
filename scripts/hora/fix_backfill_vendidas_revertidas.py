"""Corrige as motos VENDIDAS revertidas a RECEBIDA pelo backfill 2026-05-16.

CONTEXTO
--------
O `backfill_recebimentos.py` (operador BACKFILL_2026_05_16) re-processou TODAS
as NFs de entrada sem olhar o estado atual do chassi. Para motos que ja haviam
sido VENDIDAS, ele emitiu um evento RECEBIDA novo (id/timestamp = momento do
backfill). Como o estado da moto = ultimo evento, essas motos voltaram a contar
como "em estoque". Impacto medido em PROD: 505 chassis cujo ultimo estado real
era VENDIDA passaram a aparecer como RECEBIDA.

ESTRATEGIA (metodo A1 — aditivo, reversivel)
--------------------------------------------
Re-emite um evento VENDIDA (id/timestamp novos) para cada chassi-alvo, herdando
`loja_id` / `origem_tabela` / `origem_id` do ultimo evento VENDIDA original.
Vence por MAX(id) E MAX(timestamp). NAO apaga o RECEBIDA do backfill (preserva
o historico de que a moto passou pela loja). A data real da venda continua em
`hora_venda.data_venda` e no evento VENDIDA original.

A blindagem em `criar_recebimento_automatico_da_nf` impede a recorrencia; este
script corrige o passivo ja gravado.

SELECAO (idempotente)
---------------------
Chassi cujo ULTIMO evento (por MAX id) e RECEBIDA/operador=BACKFILL_2026_05_16
E cujo ultimo evento real (ignorando o backfill) era VENDIDA. Apos a correcao,
o ultimo evento vira VENDIDA e o chassi sai da selecao — re-executar e no-op.

USO
---
    # Dry-run contra PROD (NAO escreve):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_backfill_vendidas_revertidas.py

    # Executar contra PROD:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_backfill_vendidas_revertidas.py --confirmar
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.hora.services.moto_service import registrar_evento  # noqa: E402

OPERADOR_BACKFILL = 'BACKFILL_2026_05_16'
OPERADOR_FIX = 'FIX_BACKFILL_2026_06_03'
DETALHE_FIX = (
    'Reemissao VENDIDA: backfill 2026-05-16 emitiu RECEBIDA por cima de moto '
    'ja vendida, revertendo o estado para estoque. Estado real restaurado. '
    'Ver app/hora/CLAUDE.md (Guarda do recebimento automatico).'
)

# Chassi-alvo: ultimo evento (MAX id) = RECEBIDA/backfill E ultimo evento real
# (ignorando o backfill) = VENDIDA. Herda loja/origem do ultimo VENDIDA.
SQL_ALVOS = text("""
WITH ult AS (
    SELECT DISTINCT ON (numero_chassi) numero_chassi, tipo, operador
    FROM hora_moto_evento
    ORDER BY numero_chassi, id DESC
),
ult_nao_backfill AS (
    SELECT DISTINCT ON (numero_chassi) numero_chassi, tipo AS tipo_real
    FROM hora_moto_evento
    WHERE operador IS DISTINCT FROM :op_backfill
    ORDER BY numero_chassi, id DESC
),
ult_vendida AS (
    SELECT DISTINCT ON (numero_chassi)
           numero_chassi, loja_id, origem_tabela, origem_id
    FROM hora_moto_evento
    WHERE tipo = 'VENDIDA'
    ORDER BY numero_chassi, id DESC
)
SELECT u.numero_chassi, uv.loja_id, uv.origem_tabela, uv.origem_id
FROM ult u
JOIN ult_nao_backfill nb ON nb.numero_chassi = u.numero_chassi
JOIN ult_vendida uv       ON uv.numero_chassi = u.numero_chassi
WHERE u.tipo = 'RECEBIDA'
  AND u.operador = :op_backfill
  AND nb.tipo_real = 'VENDIDA'
ORDER BY u.numero_chassi
""")


def identificar_alvos() -> list[dict]:
    rows = db.session.execute(SQL_ALVOS, {'op_backfill': OPERADOR_BACKFILL}).fetchall()
    return [
        {
            'numero_chassi': r.numero_chassi,
            'loja_id': r.loja_id,
            'origem_tabela': r.origem_tabela,
            'origem_id': r.origem_id,
        }
        for r in rows
    ]


def executar(alvos: list[dict]) -> int:
    corrigidos = 0
    for a in alvos:
        registrar_evento(
            numero_chassi=a['numero_chassi'],
            tipo='VENDIDA',
            origem_tabela=a['origem_tabela'],
            origem_id=a['origem_id'],
            loja_id=a['loja_id'],
            operador=OPERADOR_FIX,
            detalhe=DETALHE_FIX,
        )
        corrigidos += 1
    db.session.commit()
    return corrigidos


def main():
    parser = argparse.ArgumentParser(
        description='Fix: motos VENDIDAS revertidas a RECEBIDA pelo backfill 2026-05-16',
    )
    parser.add_argument(
        '--confirmar', action='store_true',
        help='executa de fato (sem essa flag, so dry-run)',
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        alvos = identificar_alvos()
        print('=' * 78)
        print('FIX BACKFILL — motos VENDIDAS revertidas a RECEBIDA (metodo A1)')
        print('=' * 78)
        print(f'Chassis-alvo (ultimo=RECEBIDA/backfill, estado real=VENDIDA): {len(alvos)}')
        for a in alvos[:10]:
            print(f'  {a["numero_chassi"]}  loja_id={a["loja_id"]}  '
                  f'origem={a["origem_tabela"]}#{a["origem_id"]}')
        if len(alvos) > 10:
            print(f'  ... (+{len(alvos) - 10} chassis)')
        print()

        if not alvos:
            print('Nada a corrigir (selecao vazia). Idempotencia: provavelmente ja executado.')
            return

        if not args.confirmar:
            print('*** DRY-RUN — nenhuma alteracao foi feita. Use --confirmar para executar. ***')
            return

        print('*** EXECUTANDO COM --confirmar ***')
        corrigidos = executar(alvos)
        print(f'  {corrigidos} evento(s) VENDIDA reemitido(s) (operador={OPERADOR_FIX}).')

        # Verificacao pos: a selecao deve zerar.
        restantes = identificar_alvos()
        print()
        print(f'VERIFICACAO POS: chassis ainda como RECEBIDA/backfill+VENDIDA: {len(restantes)}')
        if restantes:
            print('  !! ATENCAO: selecao nao zerou — investigar:')
            for a in restantes[:10]:
                print(f'    {a["numero_chassi"]}')
        else:
            print('  OK — todos os alvos restaurados para VENDIDA.')


if __name__ == '__main__':
    main()
