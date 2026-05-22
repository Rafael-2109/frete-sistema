#!/usr/bin/env python3
"""Recalculo de peso/custo de fretes CarVia gerados sobre o peso BRUTO.

Contexto (2026-05-21): ate o fix em
`app/carvia/services/documentos/carvia_frete_service.py`, fretes CarVia
podiam nascer com `peso_total = peso bruto` quando o EmbarqueItem nao
tinha `peso_cubado` propagado (varios fluxos de criacao nao preenchem a
cubagem). O calculo do frete caia silenciosamente no peso fisico,
subestimando o valor (ate ~10x para motos).

Este script reprocessa fretes PENDENTE elegiveis usando EXATAMENTE a
mesma logica da auto-criacao do service:
  - peso por item: CarviaFreteService._peso_frete_item
        = max(peso_bruto, peso_cubado), com o cubado resolvido da FONTE
          DE VERDADE (CarviaCotacaoMoto) quando o snapshot esta vazio
  - custo: CarviaFreteService._calcular_custo(..., operacao_id=None)
        (mesma chamada de _criar_frete_completo)

ESCOPO (conservador — nao toca o que ja avancou no fluxo):
  status = 'PENDENTE'
  AND status_conferencia = 'PENDENTE'
  AND embarque_id IS NOT NULL
  AND fatura_cliente_id IS NULL
  AND fatura_transportadora_id IS NULL

CAMPOS:
  - peso_total      : sempre recalculado (quando difere > tolerancia)
  - valor_cotado    : recalculado (se o calculo retornar valor)
  - valor_considerado: atualizado SOMENTE se == valor_cotado antigo
                       (preserva ajuste manual de conferencia)
  - valor_venda     : NUNCA alterado (preco comercial / cotacao aprovada)

Idempotente: fretes cujo peso recalculado nao difere do atual sao
pulados. Cargas sem cubagem (nao-moto) resolvem cubado=0 -> mantem bruto.

Uso:
    source .venv/bin/activate
    python scripts/carvia/recalcular_peso_frete_carvia.py              # dry-run (default)
    python scripts/carvia/recalcular_peso_frete_carvia.py --apply      # efetiva
    python scripts/carvia/recalcular_peso_frete_carvia.py --frete-id 149 --apply
    python scripts/carvia/recalcular_peso_frete_carvia.py --tolerancia 0.5
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def _resolver_grupo_itens(frete):
    """Retorna os EmbarqueItem que compoem o frete (mesmo agrupamento do service).

    O frete agrega por (cnpj_emitente, cnpj_destino) dentro do embarque.
    Filtra os itens reais (provisorio=False, com NF) cujas NFs estao em
    `numeros_nfs` e cujo par (cnpj_emitente resolvido, cnpj_cliente) bate
    com o do frete (CNPJs normalizados). Se o desempate por CNPJ nao casar
    nenhum (legado/dados inconsistentes), cai para todos os candidatos por NF.
    """
    from app.embarques.models import EmbarqueItem
    from app.carvia.services.documentos.carvia_frete_service import (
        CarviaFreteService,
    )
    from app.utils.cnpj_utils import normalizar_cnpj

    nfs = {n.strip() for n in (frete.numeros_nfs or '').split(',') if n.strip()}
    if not nfs:
        return []

    candidatos = EmbarqueItem.query.filter(
        EmbarqueItem.embarque_id == frete.embarque_id,
        EmbarqueItem.status == 'ativo',
        EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
        EmbarqueItem.provisorio == False,  # noqa: E712
        EmbarqueItem.nota_fiscal.in_(list(nfs)),
    ).all()
    if not candidatos:
        return []

    emit_alvo = normalizar_cnpj(frete.cnpj_emitente or '')
    dest_alvo = normalizar_cnpj(frete.cnpj_destino or '')
    grupo = []
    for item in candidatos:
        emit = normalizar_cnpj(
            CarviaFreteService._resolver_cnpj_emitente(item) or ''
        )
        dest = normalizar_cnpj(item.cnpj_cliente or '')
        if emit == emit_alvo and dest == dest_alvo:
            grupo.append(item)

    return grupo or candidatos


def main():
    parser = argparse.ArgumentParser(
        description='Recalcula peso/custo de fretes CarVia (max bruto/cubado).'
    )
    parser.add_argument(
        '--apply', action='store_true',
        help='Efetiva as alteracoes (default: dry-run).',
    )
    parser.add_argument(
        '--frete-id', type=int, default=None,
        help='Processa apenas um frete (debug).',
    )
    parser.add_argument(
        '--tolerancia', type=float, default=0.01,
        help='Diferenca minima de peso (kg) para considerar mudanca.',
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaFrete
        from app.carvia.services.documentos.carvia_frete_service import (
            CarviaFreteService,
        )
        from app.embarques.models import Embarque

        q = CarviaFrete.query.filter(
            CarviaFrete.status == 'PENDENTE',
            CarviaFrete.status_conferencia == 'PENDENTE',
            CarviaFrete.embarque_id.isnot(None),
            CarviaFrete.fatura_cliente_id.is_(None),
            CarviaFrete.fatura_transportadora_id.is_(None),
        )
        if args.frete_id:
            q = q.filter(CarviaFrete.id == args.frete_id)
        fretes = q.order_by(CarviaFrete.id).all()

        modo = 'APPLY' if args.apply else 'DRY-RUN'
        logger.info(
            '[%s] %d frete(s) PENDENTE elegivel(is) — tolerancia=%.2f kg',
            modo, len(fretes), args.tolerancia,
        )

        alterados, sem_mudanca, sem_itens, pulados = [], [], [], []

        for frete in fretes:
            embarque = db.session.get(Embarque, frete.embarque_id)
            if not embarque:
                pulados.append((frete.id, 'embarque inexistente'))
                continue

            itens = _resolver_grupo_itens(frete)
            if not itens:
                sem_itens.append(frete.id)
                continue

            peso_novo = sum(
                CarviaFreteService._peso_frete_item(it) for it in itens
            )
            if peso_novo <= 0:
                pulados.append((frete.id, 'peso resolvido = 0'))
                continue

            peso_antigo = float(frete.peso_total or 0)
            if abs(peso_novo - peso_antigo) <= args.tolerancia:
                sem_mudanca.append(frete.id)
                continue

            valor_total_nfs = (
                sum(float(it.valor or 0) for it in itens)
                or float(frete.valor_total_nfs or 0)
            )
            valor_custo_novo = CarviaFreteService._calcular_custo(
                embarque=embarque,
                itens=itens,
                peso_total=peso_novo,
                valor_total=valor_total_nfs,
                operacao_id=None,  # fiel a auto-criacao (_criar_frete_completo)
            )

            cotado_antigo = float(frete.valor_cotado or 0)
            considerado_antigo = float(frete.valor_considerado or 0)
            # So atualiza o custo se o calculo retornou um valor positivo;
            # senao mantem o atual (evita zerar por falha de cotacao).
            tem_custo = valor_custo_novo is not None and float(valor_custo_novo) > 0
            cotado_novo = float(valor_custo_novo) if tem_custo else cotado_antigo
            # Considerado acompanha o cotado apenas se nao houve ajuste manual.
            atualiza_considerado = (
                tem_custo and abs(considerado_antigo - cotado_antigo) <= 0.01
            )

            registro = {
                'id': frete.id,
                'emb': frete.embarque_id,
                'tipo': frete.tipo_carga,
                'peso_de': round(peso_antigo, 2),
                'peso_para': round(peso_novo, 2),
                'cotado_de': round(cotado_antigo, 2),
                'cotado_para': round(cotado_novo, 2),
                'considerado': 'sim' if atualiza_considerado else 'preserva',
            }
            alterados.append(registro)

            if args.apply:
                frete.peso_total = peso_novo
                if tem_custo:
                    frete.valor_cotado = cotado_novo
                    if atualiza_considerado:
                        frete.valor_considerado = cotado_novo

        if args.apply and alterados:
            db.session.commit()
            logger.info('COMMIT efetuado (%d frete[s]).', len(alterados))
        elif args.apply:
            logger.info('Nada a alterar — nenhum commit.')

        # ---------------- Relatorio ----------------
        print('\n' + '=' * 88)
        print(f'RECALCULO PESO/CUSTO FRETE CARVIA — {modo}')
        print('=' * 88)
        if alterados:
            print(f'\nALTERADOS ({len(alterados)}):')
            print(
                f'{"frete":>6} {"emb":>5} {"tipo":<11} '
                f'{"peso de->para (kg)":>26} {"cotado de->para (R$)":>26} '
                f'{"consid.":>9}'
            )
            for r in alterados:
                print(
                    f'{r["id"]:>6} {r["emb"]:>5} {r["tipo"]:<11} '
                    f'{r["peso_de"]:>11.2f} -> {r["peso_para"]:>10.2f} '
                    f'{r["cotado_de"]:>11.2f} -> {r["cotado_para"]:>10.2f} '
                    f'{r["considerado"]:>9}'
                )
        else:
            print('\nNenhum frete a alterar.')

        if sem_mudanca:
            print(f'\nJA CORRETOS / sem mudanca ({len(sem_mudanca)}): '
                  f'{sorted(sem_mudanca)}')
        if sem_itens:
            print(f'\nSEM ITENS localizaveis — PULADOS ({len(sem_itens)}): '
                  f'{sorted(sem_itens)}')
        if pulados:
            print(f'\nPULADOS por outro motivo ({len(pulados)}):')
            for fid, motivo in pulados:
                print(f'  frete {fid}: {motivo}')

        print('\n' + '-' * 88)
        print(
            f'Resumo: {len(alterados)} alterar | {len(sem_mudanca)} ja ok | '
            f'{len(sem_itens)} sem itens | {len(pulados)} pulados'
        )
        if not args.apply and alterados:
            print('DRY-RUN — rode com --apply para efetivar.')
        print('=' * 88)


if __name__ == '__main__':
    main()
