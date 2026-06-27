"""Step 4 — recupera a loja real das vendas presas na MATRIZ SEM departamento.

CONTEXTO
--------
Complemento do `fix_loja_matriz_por_departamento.py` (Step 3, que corrige as que
JA tem `tagplus_departamento`). Restam as vendas FATURADO presas na matriz
(loja_id=matriz/NULL) SEM `tagplus_departamento` — o de-para sozinho nao alcanca.
Todas tem `nf_saida_chave_44`, entao sao recuperaveis via TagPlus: re-busca a NFe
pela chave-44, le `pedido_os_vinculada` -> `departamento.descricao` e grava
`tagplus_departamento`. Com o codigo de auto-cura (pedido_backfill_service,
commit ae677b1c6), assim que o departamento mapeia uma loja real a loja e
aplicada via `definir_loja_venda` (corrige loja_id + re-emite VENDIDA).

Reusa o service existente `executar_backfill_pedidos_vendas_legadas` — NAO
reimplementa. Universo: HoraVenda FATURADO + tagplus_pedido_id IS NULL +
nf_saida_chave_44 NOT NULL (inclui as 151).

REQUISITOS DE AMBIENTE
----------------------
- DATABASE_URL apontando para PROD (passar DATABASE_URL="$DATABASE_URL_PROD").
- HORA_TAGPLUS_ENC_KEY (Fernet) — para descriptografar as credenciais TagPlus.
- Conta TagPlus ativa com scope read:pedidos + read:nfes.
- Rede para a API TagPlus. Operacao LONGA (pagina /nfes por venda) — rodar em
  background. Idempotente: vendas com tagplus_pedido_id ja preenchido sao puladas.

USO
---
    # Previa (NAO escreve): mostra o tamanho do universo.
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/backfill_loja_151_via_tagplus.py

    # Executa:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/backfill_loja_151_via_tagplus.py --confirmar

    # Limitar (teste incremental):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/hora/backfill_loja_151_via_tagplus.py --confirmar --limite 10
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402

OPERADOR_FIX = 'FIX_LOJA_151_2026_06_27'


def main():
    parser = argparse.ArgumentParser(
        description='Step 4: recupera loja real das vendas sem departamento via TagPlus',
    )
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de fato (sem essa flag, so mostra o universo)')
    parser.add_argument('--limite', type=int, default=None,
                        help='processa no maximo N vendas (default: todas)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from app.hora.services.tagplus import pedido_backfill_service as pbs

        universo = pbs.contar_universo_vendas_legadas()
        print('=' * 78)
        print('BACKFILL LOJA via TagPlus — vendas FATURADO sem tagplus_pedido_id')
        print('=' * 78)
        print(f'Universo (FATURADO + tagplus_pedido_id NULL + chave_44 NOT NULL): {universo}')

        if not os.environ.get('HORA_TAGPLUS_ENC_KEY'):
            print('\nERRO: HORA_TAGPLUS_ENC_KEY ausente no ambiente — necessaria para '
                  'descriptografar as credenciais TagPlus. Abortando.')
            sys.exit(2)

        if not args.confirmar:
            print('\n*** PREVIA — nada foi executado. Use --confirmar para rodar. ***')
            return

        print(f'\n*** EXECUTANDO (operador={OPERADOR_FIX}, limite={args.limite}) ***')
        print('Operacao longa (pagina /nfes por venda). Progresso a cada 25 vendas...\n')

        ultimo = {'n': 0}

        def _progress(snapshot):
            proc = snapshot.get('processadas', 0)
            if proc - ultimo['n'] >= 25 or proc == universo:
                ultimo['n'] = proc
                print(f'  ... processadas={proc} enriquecidas={snapshot.get("enriquecidas",0)} '
                      f'sem_nfe={snapshot.get("sem_nfe",0)} sem_pedido={snapshot.get("sem_pedido",0)} '
                      f'erro={snapshot.get("erro_pedido",0)}', flush=True)

        resultado = pbs.executar_backfill_pedidos_vendas_legadas(
            operador=OPERADOR_FIX, limite=args.limite, progress_callback=_progress,
        )

        print('\nRESULTADO:')
        for k in ('processadas', 'enriquecidas', 'inalteradas', 'sem_pedido',
                  'sem_nfe', 'erro_pedido'):
            print(f'  {k}: {resultado.get(k, 0)}')
        n_erros = len(resultado.get('erros', []))
        if n_erros:
            print(f'\n  {n_erros} venda(s) sem recuperacao (amostra):')
            for e in resultado.get('erros', [])[:10]:
                print(f'    venda #{e.get("venda_id")}: {e.get("mensagem","")[:120]}')
        print('\nProximo passo: as enriquecidas com departamento mapeado ja tiveram a loja '
              'aplicada (auto-cura). As restantes (sem_pedido/sem_nfe) ficam para revisao manual.')


if __name__ == '__main__':
    main()
