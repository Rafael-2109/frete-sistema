#!/usr/bin/env python3
"""
Script: acompanhando_saida_assai.py

Consulta separacoes (EM_SEPARACAO/FECHADA/FATURADA/CANCELADA) e NFs Q.P.A.

Exit codes:
    0 - sucesso
    2 - erro infra
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

with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db  # noqa: E402

from sqlalchemy import func  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _serializar_separacao(sep):
    from app.motos_assai.models import (
        AssaiSeparacaoItem, AssaiModelo, AssaiLoja,
    )

    total_chassis = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).count()

    rows = (
        db.session.query(AssaiModelo.codigo, func.count(AssaiSeparacaoItem.id))
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.modelo_id == AssaiModelo.id)
        .filter(AssaiSeparacaoItem.separacao_id == sep.id)
        .group_by(AssaiModelo.codigo)
        .all()
    )
    total_modelos = [{'modelo': c, 'qtd': int(q)} for c, q in rows]

    loja = AssaiLoja.query.get(sep.loja_id)
    return {
        'id': sep.id,
        'pedido_id': sep.pedido_id,
        'loja_id': sep.loja_id,
        'loja_numero': loja.numero if loja else None,
        'loja_nome': loja.nome if loja else None,
        'loja_uf': loja.uf if loja else None,
        'status': sep.status,
        'iniciada_em': sep.iniciada_em,
        'fechada_em': getattr(sep, 'fechada_em', None),
        'total_chassis': total_chassis,
        'total_modelos': total_modelos,
    }


def _serializar_nf_qpa(nf):
    from app.motos_assai.models import AssaiNfQpaItem

    total_itens = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).count()
    total_divergentes = (
        AssaiNfQpaItem.query
        .filter_by(nf_id=nf.id)
        .filter(AssaiNfQpaItem.tipo_divergencia.isnot(None))
        .count()
    )

    return {
        'id': nf.id,
        'numero': nf.numero,
        'chave_44': nf.chave_44,
        'data_emissao': nf.data_emissao,
        'status_match': nf.status_match,
        'loja_id': nf.loja_id,
        'separacao_id': nf.separacao_id,
        'destinatario_cnpj': nf.destinatario_cnpj,
        'destinatario_nome': nf.destinatario_nome,
        'valor_total': nf.valor_total,
        'importada_em': nf.importada_em,
        'total_itens': total_itens,
        'total_divergentes': total_divergentes,
    }


def _run(args):
    from app.motos_assai.models import (
        AssaiSeparacao, AssaiNfQpa,
        SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
        NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    )

    separacoes = []
    nfs_qpa = []

    if args.separacao_id:
        sep = AssaiSeparacao.query.get(args.separacao_id)
        if sep:
            separacoes = [_serializar_separacao(sep)]
    elif args.somente_abertas:
        seps = (
            AssaiSeparacao.query
            .filter(AssaiSeparacao.status.in_([
                SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
            ]))
            .order_by(AssaiSeparacao.id.desc())
            .limit(50)
            .all()
        )
        separacoes = [_serializar_separacao(s) for s in seps]
    elif args.nfs_recentes:
        nfs = AssaiNfQpa.query.order_by(AssaiNfQpa.id.desc()).limit(20).all()
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]
    elif args.divergentes:
        nfs = (
            AssaiNfQpa.query
            .filter(AssaiNfQpa.status_match.in_([
                NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
            ]))
            .order_by(AssaiNfQpa.id.desc())
            .limit(50)
            .all()
        )
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]
    else:
        # Default: ultimas 20 separacoes + 20 NFs
        seps = AssaiSeparacao.query.order_by(AssaiSeparacao.id.desc()).limit(20).all()
        nfs = AssaiNfQpa.query.order_by(AssaiNfQpa.id.desc()).limit(20).all()
        separacoes = [_serializar_separacao(s) for s in seps]
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]

    return {
        'separacoes': separacoes,
        'nfs_qpa': nfs_qpa,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='acompanhando_saida_assai')
    parser.add_argument('--separacao-id', type=int)
    parser.add_argument('--somente-abertas', action='store_true')
    parser.add_argument('--nfs-recentes', action='store_true')
    parser.add_argument('--divergentes', action='store_true')
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
