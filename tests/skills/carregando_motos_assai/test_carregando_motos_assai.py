"""Testes determinísticos da skill carregando-motos-assai (Onda F).

Mock de atributos reais (db, Usuario, carregamento_service) + importlib.
Zero DB, zero PROD, zero app_context. READ shaping + WRITE dispatch/salvaguardas.
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py"


def _load():
    spec = importlib.util.spec_from_file_location("carregando_motos_assai_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["carregando_motos_assai_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


def _row(**kw):
    return SimpleNamespace(**kw)


def _args(**kw):
    base = dict(iniciar=False, escanear=False, cancelar_item=False, finalizar=False,
                cancelar=False, alterar=False, status=None, pedido_id=None, loja_id=None,
                separacao_id=None, carregamento_id=None, item_id=None, chassi=None,
                motivo=None, user_id=10, confirmar=False)
    base.update(kw)
    return SimpleNamespace(**base)


def _fake_user(ok=True):
    u = MagicMock()
    u.pode_acessar_motos_assai.return_value = ok
    return u


# ---------------------------------------------------------------- READ
def test_listar_shaping():
    m = _load()
    rows = [_row(id=1, status="EM_CARREGAMENTO", pedido_id=9, loja_id=2, separacao_id=5,
                 iniciado_em="2026-06-01", finalizado_em=None, n_itens=3)]
    with patch.object(m, "db", MagicMock()) as dbm:
        dbm.session.execute.return_value.fetchall.return_value = rows
        res = m._run_listar(status="EM_CARREGAMENTO", pedido_id=None, loja_id=None, separacao_id=None)
    assert res["total"] == 1
    c = res["carregamentos"][0]
    assert c["id"] == 1 and c["status"] == "EM_CARREGAMENTO" and c["n_itens"] == 3


def test_listar_filtro_status_no_sql():
    m = _load()
    with patch.object(m, "db", MagicMock()) as dbm:
        dbm.session.execute.return_value.fetchall.return_value = []
        m._run_listar(status="FINALIZADO", pedido_id=None, loja_id=None, separacao_id=9)
        sql = dbm.session.execute.call_args[0][0].text
    assert "c.status=:st" in sql and "c.separacao_id=:sid" in sql


def test_detalhar_nao_encontrado():
    m = _load()
    with patch.object(m, "db", MagicMock()) as dbm:
        dbm.session.execute.return_value.fetchone.return_value = None
        res = m._run_detalhar(999)
    assert res["erro"] == "carregamento_nao_encontrado"


def test_detalhar_shaping():
    m = _load()
    hdr = _row(id=1, status="EM_CARREGAMENTO", pedido_id=9, loja_id=2, separacao_id=5,
               iniciado_em="2026-06-01", finalizado_em=None, cancelado_em=None,
               motivo_cancelamento=None)
    itens = [_row(id=11, chassi="MZX1", modelo="SOL", escaneado_em="2026-06-01")]
    with patch.object(m, "db", MagicMock()) as dbm:
        dbm.session.execute.return_value.fetchone.return_value = hdr
        dbm.session.execute.return_value.fetchall.return_value = itens
        res = m._run_detalhar(1)
    assert res["id"] == 1 and res["total_itens"] == 1
    assert res["itens"][0]["chassi"] == "MZX1" and res["itens"][0]["modelo"] == "SOL"


# ---------------------------------------------------------------- WRITE salvaguardas
def test_write_sem_user_id_erro():
    m = _load()
    res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, user_id=None))
    assert res["erro"] == "user_id_obrigatorio" and res["_exit"] == 2


def test_write_sem_autorizacao_exit3():
    m = _load()
    with patch("app.auth.models.Usuario") as U:
        U.query.get.return_value = _fake_user(ok=False)
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2))
    assert res["_exit"] == 3 and res["erro"] == "sem_autorizacao_motos_assai"


def test_iniciar_dry_run_nao_chama_service_exit4():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.criar_carregamento") as cc:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, confirmar=False))
    cc.assert_not_called()
    assert res["_exit"] == 4 and res["dry_run"] is True and res["op"] == "iniciar"
    assert res["args"] == [9, 2]


def test_iniciar_confirmar_chama_service_e_commita():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.criar_carregamento",
               return_value=MagicMock(id=7)) as cc, \
         patch.object(m, "db", MagicMock()) as dbm:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, confirmar=True))
    cc.assert_called_once_with(9, 2, 10)
    dbm.session.commit.assert_called_once()
    assert res["ok"] is True and res["id"] == 7


def test_escanear_confirmar():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.escanear_carregamento_item",
               return_value=MagicMock(id=33)) as ec, \
         patch.object(m, "db", MagicMock()):
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(escanear=True, carregamento_id=1, chassi="MZX9", confirmar=True))
    ec.assert_called_once_with(1, "MZX9", 10)
    assert res["ok"] is True


def test_cancelar_exige_motivo():
    m = _load()
    with patch("app.auth.models.Usuario") as U:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(cancelar=True, carregamento_id=1, motivo=None, confirmar=True))
    assert res["erro"] == "motivo_obrigatorio" and res["_exit"] == 2


def test_finalizar_confirmar():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.finalizar_carregamento",
               return_value=None) as fc, \
         patch.object(m, "db", MagicMock()):
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(finalizar=True, carregamento_id=1, confirmar=True))
    fc.assert_called_once_with(1, 10)
    assert res["ok"] is True


def test_exception_state_error_reportada():
    m = _load()
    from app.motos_assai.services.carregamento_service import CarregamentoStateError
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.alterar_carregamento",
               side_effect=CarregamentoStateError("ja EM_CARREGAMENTO")), \
         patch.object(m, "db", MagicMock()):
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(alterar=True, carregamento_id=1, confirmar=True))
    assert "ja EM_CARREGAMENTO" in res["erro"]
    assert res["tipo"] == "CarregamentoStateError" and res["_exit"] == 5


def test_nenhuma_operacao():
    m = _load()
    with patch("app.auth.models.Usuario") as U:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args())  # nenhum flag de op
    assert res["erro"] == "nenhuma_operacao" and res["_exit"] == 2
