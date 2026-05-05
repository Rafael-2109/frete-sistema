"""
Data fix: Recalcula valor_cotado para CarviaFretes que ficaram zerados.

Data: 2026-05-05
Bug original: app/carvia/services/documentos/carvia_frete_service.py
  ::_calcular_custo_rateio() multiplicava Decimal * float, lanca TypeError
  silencioso engolido pelo try/except, retornava None. Cai em fallback
  _calcular_custo_tabela_item que falha porque itens CarVia tem
  tabela_nome_tabela=NULL. Resultado: 19 de 21 fretes DIRETA com
  valor_cotado=0 — impossivel realizar conferencia.

Esta migration recalcula `valor_cotado` (e `valor_considerado` quando
acompanha cotado) para fretes ATIVOS com valor_cotado IS NULL OR = 0
usando o mesmo CarviaFreteService._calcular_custo() ja corrigido. Nao
recalcula fretes ja CONFERIDOS/FATURADOS (read-only).

Idempotente: recalcula apenas fretes que ainda nao tem valor_cotado
preenchido. Reexecucao nao causa efeito colateral.
"""

import sys
from pathlib import Path

# sys.path.insert OBRIGATORIO antes de `from app import ...` (prod Render).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaFrete
        from app.carvia.services.documentos.carvia_frete_service import (
            CarviaFreteService,
        )
        from app.embarques.models import Embarque, EmbarqueItem

        # Buscar fretes ativos com valor_cotado zerado
        fretes_quebrados = CarviaFrete.query.filter(
            db.or_(
                CarviaFrete.valor_cotado.is_(None),
                CarviaFrete.valor_cotado == 0,
            ),
            CarviaFrete.status.notin_(['CANCELADO', 'FATURADO']),
        ).all()

        print(f'[INFO] Fretes para recalcular: {len(fretes_quebrados)}')

        recalculados = 0
        falhas = 0
        sem_embarque = 0

        for frete in fretes_quebrados:
            if not frete.embarque_id:
                # Frete backfill manual (sem embarque) — pula
                sem_embarque += 1
                continue

            embarque = db.session.get(Embarque, frete.embarque_id)
            if not embarque:
                falhas += 1
                print(f'  [SKIP] Frete #{frete.id}: embarque {frete.embarque_id} nao existe')
                continue

            # Buscar itens CarVia ATIVOS do mesmo grupo (cnpj_emitente, cnpj_destino)
            itens_grupo = EmbarqueItem.query.filter(
                EmbarqueItem.embarque_id == embarque.id,
                EmbarqueItem.status == 'ativo',
                EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
                EmbarqueItem.provisorio == False,  # noqa: E712
                EmbarqueItem.cnpj_cliente == frete.cnpj_destino,
            ).all()

            valor_custo = CarviaFreteService._calcular_custo(
                embarque=embarque,
                itens=itens_grupo,
                peso_total=float(frete.peso_total or 0),
                valor_total=float(frete.valor_total_nfs or 0),
                operacao_id=frete.operacao_id,
            )

            if valor_custo and valor_custo > 0:
                novo_valor = round(float(valor_custo), 2)
                # Atualizar valor_cotado
                frete.valor_cotado = novo_valor
                # Atualizar valor_considerado se tambem zerado (paridade com criacao)
                if not frete.valor_considerado:
                    frete.valor_considerado = novo_valor
                recalculados += 1
                print(
                    f'  [OK] Frete #{frete.id} (emb {frete.embarque_id}): '
                    f'valor_cotado={novo_valor:.2f}'
                )
            else:
                falhas += 1
                print(
                    f'  [FAIL] Frete #{frete.id} (emb {frete.embarque_id}): '
                    f'_calcular_custo retornou {valor_custo}'
                )

        if recalculados > 0:
            db.session.commit()
            print(f'\n[COMMIT] {recalculados} fretes atualizados')
        else:
            print('\n[NOOP] Nenhum frete atualizado')

        print(f'\n[RESUMO]')
        print(f'  Recalculados:  {recalculados}')
        print(f'  Falhas:        {falhas}')
        print(f'  Sem embarque:  {sem_embarque}')
        print(f'  Total tentado: {len(fretes_quebrados)}')


if __name__ == '__main__':
    main()
