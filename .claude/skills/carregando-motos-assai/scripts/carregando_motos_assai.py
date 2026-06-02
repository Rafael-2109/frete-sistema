#!/usr/bin/env python3
"""carregando_motos_assai.py — Motos Assai carregamento (READ + WRITE).

Etapa fisica entre Separacao(FECHADA) e NF Q.P.A. (escaneia chassi por chassi).
Reusa carregamento_service; NAO reimplementa logica.

READ (sem auth):
  --listar [--status --pedido-id --loja-id --separacao-id]
  --detalhar --carregamento-id N
WRITE (--user-id obrigatorio + pode_acessar_motos_assai; --dry-run default / --confirmar):
  --iniciar --pedido-id --loja-id
  --escanear --carregamento-id --chassi
  --cancelar-item --item-id
  --finalizar --carregamento-id
  --cancelar --carregamento-id --motivo   (motivo >=3 chars)
  --alterar --carregamento-id             (reabre FINALIZADO -> EM_CARREGAMENTO)

Exit: 0 ok · 2 args invalidos · 3 sem autorizacao · 4 dry-run preview · 5 erro de service.
"""
import sys
import os
import json
import argparse
import time
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    return str(o)


def _run_listar(status, pedido_id, loja_id, separacao_id):
    sql = ("SELECT c.id, c.status, c.pedido_id, c.loja_id, c.separacao_id, "
           "c.iniciado_em, c.finalizado_em, "
           "(SELECT COUNT(*) FROM assai_carregamento_item i WHERE i.carregamento_id=c.id) AS n_itens "
           "FROM assai_carregamento c WHERE 1=1")
    p = {}
    if status:
        sql += " AND c.status=:st"
        p['st'] = status
    if pedido_id:
        sql += " AND c.pedido_id=:pid"
        p['pid'] = pedido_id
    if loja_id:
        sql += " AND c.loja_id=:lid"
        p['lid'] = loja_id
    if separacao_id:
        sql += " AND c.separacao_id=:sid"
        p['sid'] = separacao_id
    sql += " ORDER BY c.id DESC"
    rows = db.session.execute(text(sql), p).fetchall()
    cs = [{'id': r.id, 'status': r.status, 'pedido_id': r.pedido_id, 'loja_id': r.loja_id,
           'separacao_id': r.separacao_id, 'iniciado_em': r.iniciado_em,
           'finalizado_em': r.finalizado_em, 'n_itens': r.n_itens} for r in rows]
    return {'carregamentos': cs, 'total': len(cs)}


def _run_detalhar(carregamento_id):
    hdr = db.session.execute(text(
        "SELECT id, status, pedido_id, loja_id, separacao_id, iniciado_em, finalizado_em, "
        "cancelado_em, motivo_cancelamento FROM assai_carregamento WHERE id=:id"),
        {'id': carregamento_id}).fetchone()
    if hdr is None:
        return {'erro': 'carregamento_nao_encontrado', 'carregamento_id': carregamento_id}
    itens = db.session.execute(text(
        "SELECT i.id, i.chassi, mo.descricao_qpa AS modelo, i.escaneado_em "
        "FROM assai_carregamento_item i "
        "LEFT JOIN assai_modelo mo ON mo.id=i.modelo_id "
        "WHERE i.carregamento_id=:id ORDER BY i.id"), {'id': carregamento_id}).fetchall()
    return {
        'id': hdr.id, 'status': hdr.status, 'pedido_id': hdr.pedido_id, 'loja_id': hdr.loja_id,
        'separacao_id': hdr.separacao_id, 'iniciado_em': hdr.iniciado_em,
        'finalizado_em': hdr.finalizado_em, 'cancelado_em': hdr.cancelado_em,
        'motivo_cancelamento': hdr.motivo_cancelamento,
        'itens': [{'item_id': r.id, 'chassi': r.chassi, 'modelo': r.modelo or '—',
                   'escaneado_em': r.escaneado_em} for r in itens],
        'total_itens': len(itens),
    }


def _run_write(a):
    if not a.user_id:
        return {'erro': 'user_id_obrigatorio', '_exit': 2}
    from app.auth.models import Usuario
    u = Usuario.query.get(a.user_id)
    if u is None or not u.pode_acessar_motos_assai():
        return {'erro': 'sem_autorizacao_motos_assai', 'user_id': a.user_id, '_exit': 3}

    from app.motos_assai.services import carregamento_service as cs
    from app.motos_assai.services.carregamento_service import CarregamentoError

    if a.iniciar:
        if not (a.pedido_id and a.loja_id):
            return {'erro': 'pedido_id_e_loja_id_obrigatorios', '_exit': 2}
        op, fn, args_ = 'iniciar', cs.criar_carregamento, (a.pedido_id, a.loja_id, a.user_id)
    elif a.escanear:
        if not (a.carregamento_id and a.chassi):
            return {'erro': 'carregamento_id_e_chassi_obrigatorios', '_exit': 2}
        op, fn, args_ = 'escanear', cs.escanear_carregamento_item, (a.carregamento_id, a.chassi, a.user_id)
    elif a.cancelar_item:
        if not a.item_id:
            return {'erro': 'item_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'cancelar_item', cs.cancelar_carregamento_item, (a.item_id, a.user_id)
    elif a.finalizar:
        if not a.carregamento_id:
            return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'finalizar', cs.finalizar_carregamento, (a.carregamento_id, a.user_id)
    elif a.cancelar:
        if not a.carregamento_id:
            return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        if not a.motivo or len(a.motivo.strip()) < 3:
            return {'erro': 'motivo_obrigatorio', '_exit': 2}
        op, fn, args_ = 'cancelar', cs.cancelar_carregamento, (a.carregamento_id, a.motivo, a.user_id)
    elif a.alterar:
        if not a.carregamento_id:
            return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'alterar', cs.alterar_carregamento, (a.carregamento_id, a.user_id)
    else:
        return {'erro': 'nenhuma_operacao', '_exit': 2}

    if not a.confirmar:
        return {'dry_run': True, 'op': op, 'args': list(args_[:-1]),
                'aviso': 'sem --confirmar: nada foi alterado', '_exit': 4}

    try:
        ret = fn(*args_)            # service faz flush()
        db.session.commit()         # caller commita (flush no service, commit no caller)
        out = {'ok': True, 'op': op}
        if hasattr(ret, 'id'):
            out['id'] = ret.id
        return out
    except CarregamentoError as e:
        db.session.rollback()
        return {'erro': str(e), 'op': op, 'tipo': type(e).__name__, '_exit': 5}


def main():
    pa = argparse.ArgumentParser()
    pa.add_argument('--listar', action='store_true')
    pa.add_argument('--detalhar', action='store_true')
    pa.add_argument('--iniciar', action='store_true')
    pa.add_argument('--escanear', action='store_true')
    pa.add_argument('--cancelar-item', dest='cancelar_item', action='store_true')
    pa.add_argument('--finalizar', action='store_true')
    pa.add_argument('--cancelar', action='store_true')
    pa.add_argument('--alterar', action='store_true')
    pa.add_argument('--status')
    pa.add_argument('--pedido-id', dest='pedido_id', type=int)
    pa.add_argument('--loja-id', dest='loja_id', type=int)
    pa.add_argument('--separacao-id', dest='separacao_id', type=int)
    pa.add_argument('--carregamento-id', dest='carregamento_id', type=int)
    pa.add_argument('--item-id', dest='item_id', type=int)
    pa.add_argument('--chassi')
    pa.add_argument('--motivo')
    pa.add_argument('--user-id', dest='user_id', type=int)
    pa.add_argument('--confirmar', action='store_true')
    a = pa.parse_args()

    t0 = time.time()
    app = create_app()
    with app.app_context():
        if a.listar:
            out = _run_listar(a.status, a.pedido_id, a.loja_id, a.separacao_id)
        elif a.detalhar:
            out = _run_detalhar(a.carregamento_id)
        else:
            out = _run_write(a)

    if isinstance(out, dict):
        out['_debug'] = {'ms': int((time.time() - t0) * 1000)}
    print(json.dumps(out, default=_json_default, ensure_ascii=False, indent=2))
    sys.exit(out.get('_exit', 0) if isinstance(out, dict) else 0)


if __name__ == '__main__':
    main()
