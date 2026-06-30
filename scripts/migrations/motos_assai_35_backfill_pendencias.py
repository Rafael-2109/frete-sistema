"""Backfill 35: cria assai_pendencia para todo chassi cujo ULTIMO evento e
PENDENTE e que ainda nao tem ficha de pendencia (legado pre-Spec 1).

Regra (espelha §12.4 do spec):
  - se o evento PENDENTE veio de devolucao (dados_extras['origem']=='devolucao_nfd')
    -> categoria=REVISAO, origem=DEVOLUCAO, devolucao_item_id resolvido pelo
       AssaiDevolucaoItem.evento_pendencia_id == evento.id;
  - senao -> categoria=INDETERMINADA, origem=GALPAO; descricao do observacao /
    dados_extras['descricao']; chassi_doador de dados_extras; detalhes.legacy_backfill=true.

Reusa pendencia_service.abrir_pendencia passando evento_pendente_id explicito
(nao emite 2o PENDENTE). NAO consta no build.sh (padrao 32/33: aplicar manual).

Flags: dry-run (default), --confirmar (efetiva), --check (sai !=0 se sobrou PENDENTE
sem ficha).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import func  # noqa: E402

from app import create_app, db  # noqa: E402
from app.motos_assai.models import (  # noqa: E402
    AssaiMotoEvento, AssaiPendencia, AssaiDevolucaoItem,
    EVENTO_PENDENTE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_DEVOLUCAO,
)
from app.motos_assai.services import pendencia_service  # noqa: E402


def chassis_pendentes_sem_ficha():
    """Eventos PENDENTE que sao o ULTIMO evento do chassi e nao tem ficha aberta."""
    sub = (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )
    ultimos_pendentes = (
        db.session.query(AssaiMotoEvento)
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .all()
    )
    # Exclui chassis que ja tem QUALQUER ficha aberta (idempotencia).
    com_ficha = {
        c for (c,) in db.session.query(AssaiPendencia.chassi).filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        ).distinct().all()
    }
    return [ev for ev in ultimos_pendentes if ev.chassi not in com_ficha]


def _params_ficha(ev):
    """Deriva (categoria, origem, descricao, devolucao_item_id, chassi_doador)."""
    dados = ev.dados_extras if isinstance(ev.dados_extras, dict) else {}
    descricao = ev.observacao or dados.get('descricao') or 'Pendencia legada (backfill)'
    chassi_doador = dados.get('chassi_doador')

    if dados.get('origem') == 'devolucao_nfd':
        item = (
            AssaiDevolucaoItem.query
            .filter_by(evento_pendencia_id=ev.id)
            .first()
        )
        return (
            PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_ORIGEM_DEVOLUCAO,
            descricao, (item.id if item else None), chassi_doador,
        )
    return (
        PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
        descricao, None, chassi_doador,
    )


def backfill(confirmar=False):
    """Cria as fichas faltantes. Dry-run (default) nao grava. Retorna {plano, criadas}."""
    alvos = chassis_pendentes_sem_ficha()
    criadas = 0
    for ev in alvos:
        categoria, origem, descricao, dev_item_id, doador = _params_ficha(ev)
        if not confirmar:
            continue
        detalhes = {'legacy_backfill': True}
        if doador:
            detalhes['chassi_doador'] = doador
        pendencia_service.abrir_pendencia(
            chassi=ev.chassi,
            categoria=categoria,
            origem=origem,
            descricao=descricao,
            evento_pendente_id=ev.id,
            devolucao_item_id=dev_item_id,
            operador_id=ev.operador_id,
            detalhes=detalhes,
        )
        criadas += 1
    if confirmar:
        db.session.commit()
    else:
        db.session.rollback()
    return {'plano': len(alvos), 'criadas': criadas}


def verificar():
    """Retorna quantos chassis PENDENTE ainda estao sem ficha (0 = cobertura ok)."""
    return len(chassis_pendentes_sem_ficha())


def main():
    parser = argparse.ArgumentParser(description='Backfill 35 — fichas de pendencia legadas.')
    parser.add_argument('--confirmar', action='store_true', help='Efetiva (default: dry-run).')
    parser.add_argument('--check', action='store_true',
                        help='So verifica cobertura; sai 1 se sobrou PENDENTE sem ficha.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.check:
            restantes = verificar()
            if restantes:
                print(f'[FAIL] {restantes} chassi(s) PENDENTE sem ficha.')
                sys.exit(1)
            print('[ok] cobertura completa: 0 PENDENTE sem ficha.')
            sys.exit(0)

        res = backfill(confirmar=args.confirmar)
        modo = 'CONFIRMADO' if args.confirmar else 'DRY-RUN'
        print(f'[{modo}] plano={res["plano"]} criadas={res["criadas"]}')
        if not args.confirmar and res['plano']:
            print('  (rode novamente com --confirmar para efetivar)')


if __name__ == '__main__':
    main()
