#!/usr/bin/env python3
"""
Script: consultando_estoque_assai.py

Consulta pipeline do modulo Motos Assai (B2B Q.P.A. Sendas).
Estado atual da moto = ultimo evento em assai_moto_evento.

Uso:
    --resumo                    # totais + por_modelo
    --modelo SOL                # filtro por codigo de modelo
    --por-modelo                # agrupa por modelo
    --por-estagio               # agrupa por evento

Exit codes:
    0 - sucesso
    1 - validacao falhou
    2 - erro infra (DB)
"""
import sys
import os
import json
import argparse
import contextlib
import io
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Suprimir logs barulhentos durante create_app() para nao poluir stdout
with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db  # noqa: E402

from sqlalchemy import func  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _query_pipeline(modelo_filtro=None):
    """Retorna rows: chassi, modelo, evento_atual.

    Para cada chassi distinto, pega o evento de maior id (mais recente).
    """
    from app.motos_assai.models import (
        AssaiMoto, AssaiMotoEvento, AssaiModelo,
    )

    # Subquery: ultimo evento por chassi
    ultimo_id_por_chassi = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('max_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    q = (
        db.session.query(
            AssaiMoto.chassi,
            AssaiMoto.modelo_id,
            AssaiModelo.codigo.label('modelo_codigo'),
            AssaiModelo.nome.label('modelo_nome'),
            AssaiMoto.cor,
            AssaiMotoEvento.tipo.label('evento_atual'),
            AssaiMotoEvento.ocorrido_em.label('evento_em'),
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiMoto.modelo_id)
        .outerjoin(
            ultimo_id_por_chassi,
            ultimo_id_por_chassi.c.chassi == AssaiMoto.chassi,
        )
        .outerjoin(
            AssaiMotoEvento,
            AssaiMotoEvento.id == ultimo_id_por_chassi.c.max_id,
        )
    )

    if modelo_filtro:
        q = q.filter(AssaiModelo.codigo == modelo_filtro.upper())

    return q.all()


def _query_motos_pendentes():
    """Lista motos em estado PENDENTE com a descricao da pendencia."""
    from app.motos_assai.models import (
        AssaiMotoEvento, EVENTO_PENDENTE,
    )

    ultimo_id_por_chassi = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('max_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    rows = (
        db.session.query(
            AssaiMotoEvento.chassi,
            AssaiMotoEvento.observacao,
            AssaiMotoEvento.ocorrido_em,
        )
        .join(
            ultimo_id_por_chassi,
            ultimo_id_por_chassi.c.max_id == AssaiMotoEvento.id,
        )
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .all()
    )

    return [
        {
            'chassi': r.chassi,
            'descricao_pendencia': r.observacao or '',
            'criado_em': r.ocorrido_em,
        }
        for r in rows
    ]


def _agregar(rows):
    """Agrega rows do _query_pipeline em totais/por_modelo."""
    from app.motos_assai.models import (
        EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
        EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_FATURADA,
    )

    totais = {
        'estoque': 0, 'montada': 0, 'pendente': 0,
        'disponivel': 0, 'separada': 0, 'faturada': 0,
    }
    por_modelo: dict = {}

    mapa_evento_chave = {
        EVENTO_ESTOQUE: 'estoque',
        EVENTO_MONTADA: 'montada',
        EVENTO_PENDENTE: 'pendente',
        EVENTO_DISPONIVEL: 'disponivel',
        EVENTO_SEPARADA: 'separada',
        EVENTO_FATURADA: 'faturada',
    }

    for r in rows:
        chave = mapa_evento_chave.get(r.evento_atual)
        if not chave:
            continue  # CANCELADA, MOTO_FALTANDO, REVERTIDA, PENDENCIA_RESOLVIDA
        totais[chave] += 1

        m_codigo = r.modelo_codigo or '?'
        if m_codigo not in por_modelo:
            por_modelo[m_codigo] = {
                'modelo': m_codigo,
                'estoque': 0, 'montada': 0, 'pendente': 0,
                'disponivel': 0, 'separada': 0, 'faturada': 0,
            }
        por_modelo[m_codigo][chave] += 1

    return totais, sorted(por_modelo.values(), key=lambda x: x['modelo'])


def _run(args):
    rows = _query_pipeline(modelo_filtro=args.modelo)
    totais, por_modelo = _agregar(rows)
    motos_pendentes = _query_motos_pendentes()

    # Por CD nao implementado nesta versao
    por_cd: list = []

    vazio = sum(totais.values()) == 0

    return {
        'totais': totais,
        'por_modelo': por_modelo,
        'por_cd': por_cd,
        'motos_pendentes': motos_pendentes,
        'vazio': vazio,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='consultando_estoque_assai')
    parser.add_argument('--resumo', action='store_true', help='Resumo geral')
    parser.add_argument('--modelo', help='Filtro por codigo de modelo (SOL, X11_MINI, DOT)')
    parser.add_argument('--por-modelo', action='store_true', help='Agrupa por modelo')
    parser.add_argument('--por-estagio', action='store_true', help='Agrupa por evento')
    args = parser.parse_args()

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
