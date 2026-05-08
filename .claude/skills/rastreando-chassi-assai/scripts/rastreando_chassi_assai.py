#!/usr/bin/env python3
"""
Script: rastreando_chassi_assai.py

Historico completo de UM chassi do modulo Motos Assai.

Uso:
    --chassi MZX1234        # OBRIGATORIO

Exit codes:
    0 - sucesso (encontrado=true ou false)
    1 - validacao (chassi vazio)
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
    from app import create_app, db  # noqa: E402, F401


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _run(chassi: str):
    from app.motos_assai.models import (
        AssaiMoto, AssaiReciboMotochefe, AssaiReciboItem,
        AssaiSeparacaoItem, AssaiSeparacao, AssaiNfQpa, AssaiNfQpaItem,
        SEPARACAO_STATUS_CANCELADA,
    )
    from app.motos_assai.services.moto_evento_service import (
        eventos_chassi, status_efetivo,
    )
    from app.motos_assai.services.chassi_validator import validar_chassi

    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        return {'encontrado': False, 'erro': 'chassi vazio', 'exit_code': 1}

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        return {
            'encontrado': False, 'chassi': chassi_norm,
            'mensagem': 'Chassi nao cadastrado em assai_moto',
            'exit_code': 0,
        }

    eventos = eventos_chassi(chassi_norm, limit=100)
    status = status_efetivo(chassi_norm)

    # Recibo de origem (se existe item de recibo com este chassi)
    recibo_item = (
        AssaiReciboItem.query
        .filter_by(chassi=chassi_norm)
        .order_by(AssaiReciboItem.id.asc())
        .first()
    )
    recibo_origem = None
    if recibo_item:
        recibo = AssaiReciboMotochefe.query.get(recibo_item.recibo_id)
        if recibo:
            recibo_origem = {
                'id': recibo.id,
                'compra_id': recibo.compra_id,
                'data_recebimento': recibo.data_recebimento,
                'status': recibo.status,
            }

    # Separacao ativa
    sep_item = (
        AssaiSeparacaoItem.query
        .filter_by(chassi=chassi_norm)
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA)
        .order_by(AssaiSeparacaoItem.id.desc())
        .first()
    )
    separacao_ativa = None
    if sep_item:
        sep = AssaiSeparacao.query.get(sep_item.separacao_id)
        separacao_ativa = {
            'separacao_id': sep.id,
            'pedido_id': sep.pedido_id,
            'loja_id': sep.loja_id,
            'status': sep.status,
            'item_id': sep_item.id,
        }

    # NF Q.P.A.
    nf_item = AssaiNfQpaItem.query.filter_by(chassi=chassi_norm).first()
    nf_qpa = None
    if nf_item:
        nf = AssaiNfQpa.query.get(nf_item.nf_id)
        if nf:
            nf_qpa = {
                'nf_id': nf.id,
                'numero_nf': nf.numero_nf,
                'data_emissao': nf.data_emissao,
                'status_match': getattr(nf_item, 'status_match', None),
            }

    # Regex check (signature: validar_chassi(chassi: str, modelo_id: Optional[int]))
    regex_result = validar_chassi(chassi_norm, moto.modelo_id)

    return {
        'encontrado': True,
        'chassi': chassi_norm,
        'moto': {
            'id': moto.id,
            'modelo_id': moto.modelo_id,
            'modelo_codigo': moto.modelo.codigo if moto.modelo else None,
            'cor': moto.cor,
            'motor': moto.motor,
            'ano': moto.ano,
            'criada_em': moto.criada_em,
        },
        'status_efetivo': status,
        'eventos': [
            {
                'id': e.id, 'tipo': e.tipo, 'ocorrido_em': e.ocorrido_em,
                'operador_id': e.operador_id,
                'operador_nome': e.operador.nome if e.operador else None,
                'observacao': e.observacao,
                'dados_extras': e.dados_extras or {},
            }
            for e in eventos
        ],
        'recibo_origem': recibo_origem,
        'separacao_ativa': separacao_ativa,
        'nf_qpa': nf_qpa,
        'regex_check': regex_result,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='rastreando_chassi_assai')
    parser.add_argument('--chassi', required=True, help='Chassi (obrigatorio)')
    args = parser.parse_args()

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
        with app.app_context():
            result = _run(args.chassi)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
