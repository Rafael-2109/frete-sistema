"""Corrige motos presas em DEVOLVIDA por CANCELAMENTO DE RESERVA de venda.

CONTEXTO (bug 2026-06-26)
-------------------------
Remover uma moto de um pedido, cancelar/descartar o pedido ou ter a NFe
cancelada via backfill emitia o evento `DEVOLVIDA`. Como `DEVOLVIDA` esta em
`EVENTOS_FORA_ESTOQUE` (estoque_service) e o estado da moto = ultimo evento
(invariante 4), a moto sumia do estoque disponivel e NAO podia ser revendida —
apesar de os comentarios do codigo dizerem "devolve/libera ao estoque".

A correcao no codigo troca esses call-sites por `devolver_ao_estoque`, que
re-emite o ULTIMO estado-em-estoque anterior (RECEBIDA/CONFERIDA/...). Este
script corrige o PASSIVO ja gravado em producao com o mesmo metodo.

ESTRATEGIA (aditivo, reversivel — nao apaga o DEVOLVIDA)
-------------------------------------------------------
Para cada chassi-alvo, chama `devolver_ao_estoque`, que re-emite o tipo do
ultimo evento em EVENTOS_EM_ESTOQUE (preservando a loja desse estado). Vence
por MAX(id). O DEVOLVIDA do bug e preservado no historico.

SELECAO (idempotente + discriminador a prova)
---------------------------------------------
Chassi cujo ULTIMO evento (por MAX id, mesma derivacao do estoque_service) e
`DEVOLVIDA` E `origem_tabela IN ('hora_venda','hora_venda_item')`. Esse par de
origens e emitido SOMENTE por cancelar/remover/descartar pedido e backfill de
NFe cancelada (sentido A — a moto nao saiu fisicamente). Devolucao ao
FORNECEDOR (`hora_devolucao_fornecedor_item`), do CLIENTE
(`hora_devolucao_venda_item`), DESCARTE de recebimento
(`hora_recebimento_conferencia`) e EMPRESTIMO (`hora_emprestimo_moto`) ficam de
fora — nesses casos a moto realmente saiu e DEVOLVIDA esta correto.
Apos a correcao o ultimo evento vira o estado-em-estoque re-emitido e o chassi
sai da selecao — re-executar e no-op.

USO
---
    # Dry-run contra PROD (NAO escreve):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_devolvida_reserva_presa.py

    # Executar contra PROD:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_devolvida_reserva_presa.py --confirmar
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.hora.services.moto_service import devolver_ao_estoque  # noqa: E402

OPERADOR_FIX = 'FIX_DEVOLVIDA_RESERVA_2026_06_26'
DETALHE_FIX = (
    'Restauracao ao estoque: cancelamento/remocao de reserva de venda havia '
    'emitido DEVOLVIDA (fora do estoque), prendendo a moto. Estado anterior '
    'restaurado. Ver app/hora/CLAUDE.md (Reserva cancelada devolve ao estoque).'
)

# Origens de DEVOLVIDA que sao "cancelamento de reserva" (sentido A).
ORIGENS_SENTIDO_A = ('hora_venda', 'hora_venda_item')

# Chassi-alvo: ultimo evento (MAX id) = DEVOLVIDA com origem de venda.
SQL_ALVOS = text("""
WITH ult AS (
    SELECT DISTINCT ON (numero_chassi)
           numero_chassi, tipo, origem_tabela, origem_id, loja_id
    FROM hora_moto_evento
    ORDER BY numero_chassi, id DESC
)
SELECT numero_chassi, origem_tabela, origem_id, loja_id
FROM ult
WHERE tipo = 'DEVOLVIDA'
  AND origem_tabela IN ('hora_venda', 'hora_venda_item')
ORDER BY numero_chassi
""")


def identificar_alvos() -> list[dict]:
    rows = db.session.execute(SQL_ALVOS).fetchall()
    return [
        {
            'numero_chassi': r.numero_chassi,
            'origem_tabela': r.origem_tabela,
            'origem_id': r.origem_id,
            'loja_id': r.loja_id,
        }
        for r in rows
    ]


def executar(alvos: list[dict]) -> int:
    corrigidos = 0
    for a in alvos:
        ev = devolver_ao_estoque(
            numero_chassi=a['numero_chassi'],
            origem_tabela=a['origem_tabela'],
            origem_id=a['origem_id'],
            loja_id=a['loja_id'],  # fallback se nao houver estado-em-estoque anterior
            operador=OPERADOR_FIX,
            detalhe=DETALHE_FIX,
        )
        print(f'  {a["numero_chassi"]} -> {ev.tipo} (loja_id={ev.loja_id})')
        corrigidos += 1
    db.session.commit()
    return corrigidos


def main():
    parser = argparse.ArgumentParser(
        description='Fix: motos presas em DEVOLVIDA por cancelamento de reserva de venda',
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
        print('FIX DEVOLVIDA — motos presas por cancelamento de reserva de venda')
        print('=' * 78)
        print(f'Chassis-alvo (ultimo=DEVOLVIDA, origem in {ORIGENS_SENTIDO_A}): {len(alvos)}')
        for a in alvos[:15]:
            print(f'  {a["numero_chassi"]}  loja_id={a["loja_id"]}  '
                  f'origem={a["origem_tabela"]}#{a["origem_id"]}')
        if len(alvos) > 15:
            print(f'  ... (+{len(alvos) - 15} chassis)')
        print()

        if not alvos:
            print('Nada a corrigir (selecao vazia). Idempotencia: provavelmente ja executado.')
            return

        if not args.confirmar:
            print('*** DRY-RUN — nenhuma alteracao foi feita. Use --confirmar para executar. ***')
            return

        print('*** EXECUTANDO COM --confirmar ***')
        corrigidos = executar(alvos)
        print(f'  {corrigidos} chassi(s) restaurado(s) ao estoque (operador={OPERADOR_FIX}).')

        # Verificacao pos: a selecao deve zerar.
        restantes = identificar_alvos()
        print()
        print(f'VERIFICACAO POS: chassis ainda presos em DEVOLVIDA/venda: {len(restantes)}')
        if restantes:
            print('  !! ATENCAO: selecao nao zerou — investigar:')
            for a in restantes[:10]:
                print(f'    {a["numero_chassi"]}')
        else:
            print('  OK — todos os alvos restaurados ao estoque.')


if __name__ == '__main__':
    main()
