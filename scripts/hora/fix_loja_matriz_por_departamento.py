"""Corrige vendas presas na MATRIZ (loja_id=MORAH) para a loja FISICA real.

CONTEXTO
--------
Toda NFe da Lojas HORA sai com o CNPJ da matriz (invariante fiscal — CLAUDE.md
secao 7). No import DANFE e no backfill TagPlus, `venda_service._resolver_loja_por_cnpj`
(venda_service.py:281) resolve a loja pelo CNPJ do EMITENTE — que e SEMPRE a matriz.
Como a matriz esta cadastrada como `HoraLoja` ativa, o lookup casa nela e grava
`hora_venda.loja_id = MATRIZ` no header E no evento `VENDIDA` (origem do dado
corrompido). A loja FISICA real, nesses casos, vive em `hora_venda.tagplus_departamento`
e e resolvida pelo de-para `hora_tagplus_departamento_map.loja_id`.

Este script corrige o PASSIVO das vendas cujo `tagplus_departamento` mapeia para
uma loja real diferente da loja gravada (tipicamente a matriz).

POR QUE `definir_loja_venda` (e nao UPDATE cru / nao a rota tagplus_departamento_map_aplicar)
---------------------------------------------------------------------------------------------
A rota `tagplus_departamento_map_aplicar` (tagplus_routes.py:2125) so atualiza o
HEADER (`hora_venda.loja_id`) — deixa o evento `HoraMotoEvento.VENDIDA` apontando
para a matriz, entao o historico do chassi / "Eventos recentes" / estoque com
status=VENDIDA continuam exibindo a matriz. `venda_service.definir_loja_venda`
(venda_service.py:2332) corrige o HEADER **e** re-emite o evento `VENDIDA` com a
loja correta **e** resolve a divergencia `CNPJ_DESCONHECIDO`, com auditoria
`DEFINIU_LOJA`. E a ferramenta completa.

GUARDA DE UF (CFOP)
-------------------
Espelha a defesa da rota: NAO troca a loja se a UF da loja-destino difere da UF
da loja-origem (evitaria mudar CFOP em re-emissao pos-cancelamento). Hoje todas as
lojas HORA sao SP, entao nada e pulado — a guarda protege expansao multi-UF futura.

SELECAO (idempotente)
---------------------
Vendas com `tagplus_departamento` que normaliza para um `departamento_map` com
`loja_id` preenchido, cujo `hora_venda.loja_id` difere desse `loja_id`, e status
!= CANCELADO (venda cancelada nao deve emitir VENDIDA). Apos a correcao, loja_id
== loja do mapa e a venda sai da selecao — re-executar e no-op.

USO
---
    # Dry-run contra PROD (NAO escreve):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_loja_matriz_por_departamento.py

    # Executar contra PROD:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/fix_loja_matriz_por_departamento.py --confirmar
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.hora.models import HoraLoja, HoraTagPlusDepartamentoMap, HoraVenda  # noqa: E402
from app.hora.models.venda import VENDA_STATUS_CANCELADO  # noqa: E402
from app.hora.services.tagplus.pedido_service import normalizar_departamento  # noqa: E402
from app.hora.services.venda_service import definir_loja_venda  # noqa: E402

OPERADOR_FIX = 'FIX_LOJA_MATRIZ_2026_06_27'


def identificar_alvos() -> tuple[list[dict], list[dict]]:
    """Retorna (alvos, pulados_uf).

    alvo = {venda_id, loja_atual, loja_atual_nome, loja_nova, loja_nova_nome, departamento}
    """
    mapas = {
        m.departamento_norm: m
        for m in HoraTagPlusDepartamentoMap.query
        .filter(HoraTagPlusDepartamentoMap.loja_id.isnot(None)).all()
    }
    lojas = {l.id: l for l in HoraLoja.query.all()}

    vendas = (
        HoraVenda.query
        .filter(HoraVenda.tagplus_departamento.isnot(None))
        .filter(HoraVenda.status != VENDA_STATUS_CANCELADO)
        .all()
    )

    alvos: list[dict] = []
    pulados_uf: list[dict] = []
    for v in vendas:
        norm = normalizar_departamento(v.tagplus_departamento)
        mapa = mapas.get(norm)
        if mapa is None or v.loja_id == mapa.loja_id:
            continue

        loja_origem = lojas.get(v.loja_id) if v.loja_id else None
        loja_destino = lojas.get(mapa.loja_id)
        uf_o = (loja_origem.uf or '').upper() if loja_origem else None
        uf_d = (loja_destino.uf or '').upper() if loja_destino else None
        registro = {
            'venda_id': v.id,
            'loja_atual': v.loja_id,
            'loja_atual_nome': (loja_origem.apelido if loja_origem else None),
            'loja_nova': mapa.loja_id,
            'loja_nova_nome': (loja_destino.apelido if loja_destino else None),
            'departamento': v.tagplus_departamento,
        }
        if uf_o and uf_d and uf_o != uf_d:
            pulados_uf.append(registro)
            continue
        alvos.append(registro)

    return alvos, pulados_uf


def executar(alvos: list[dict]) -> int:
    corrigidos = 0
    for a in alvos:
        # definir_loja_venda: atualiza header + re-emite VENDIDA com a loja
        # correta + resolve CNPJ_DESCONHECIDO + auditoria DEFINIU_LOJA + commit.
        definir_loja_venda(
            venda_id=a['venda_id'],
            loja_id=a['loja_nova'],
            usuario=OPERADOR_FIX,
        )
        corrigidos += 1
    return corrigidos


def main():
    parser = argparse.ArgumentParser(
        description='Fix: vendas presas na matriz -> loja fisica real (via departamento_map)',
    )
    parser.add_argument(
        '--confirmar', action='store_true',
        help='executa de fato (sem essa flag, so dry-run)',
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        alvos, pulados_uf = identificar_alvos()

        print('=' * 78)
        print('FIX LOJA — vendas atribuidas a MATRIZ -> loja fisica (departamento_map)')
        print('=' * 78)

        # Resumo por destino.
        por_destino: dict[str, dict] = {}
        for a in alvos:
            k = f"{a['loja_nova']} ({a['loja_nova_nome']})"
            d = por_destino.setdefault(k, {'n': 0})
            d['n'] += 1
        print(f'Vendas a corrigir: {len(alvos)}')
        for k, d in sorted(por_destino.items()):
            print(f'  -> {k}: {d["n"]}')
        if pulados_uf:
            print(f'PULADAS por UF diferente (guarda CFOP): {len(pulados_uf)}')
            for a in pulados_uf[:10]:
                print(f'    venda #{a["venda_id"]} {a["loja_atual_nome"]} -> '
                      f'{a["loja_nova_nome"]} (departamento={a["departamento"]!r})')
        print()
        for a in alvos[:15]:
            print(f'  venda #{a["venda_id"]}  loja {a["loja_atual"]} '
                  f'({a["loja_atual_nome"]}) -> {a["loja_nova"]} ({a["loja_nova_nome"]})  '
                  f'departamento={a["departamento"]!r}')
        if len(alvos) > 15:
            print(f'  ... (+{len(alvos) - 15} vendas)')
        print()

        if not alvos:
            print('Nada a corrigir (selecao vazia). Idempotencia: provavelmente ja executado.')
            return

        if not args.confirmar:
            print('*** DRY-RUN — nenhuma alteracao foi feita. Use --confirmar para executar. ***')
            return

        print('*** EXECUTANDO COM --confirmar ***')
        corrigidos = executar(alvos)
        print(f'  {corrigidos} venda(s) corrigida(s) via definir_loja_venda '
              f'(operador={OPERADOR_FIX}).')

        restantes, _ = identificar_alvos()
        print()
        print(f'VERIFICACAO POS: vendas ainda atribuidas a loja errada: {len(restantes)}')
        if restantes:
            print('  !! ATENCAO: selecao nao zerou — investigar:')
            for a in restantes[:10]:
                print(f'    venda #{a["venda_id"]}')
        else:
            print('  OK — todas as vendas-alvo reatribuidas a loja fisica real.')


if __name__ == '__main__':
    main()
