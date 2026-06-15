"""Testa o monitor anti-upgrade (D8 + hook SessionStart). `ler_flag`/`mensagem_alerta`
são puros; `verificar_e_gravar_flag` usa o provisionador (odoo injetado) + grava o flag."""
from app.odoo.estoque.provisioning.monitor_sa_industrializacao import (
    gravar_flag, ler_flag, mensagem_alerta, verificar_e_gravar_flag)
from app.odoo.estoque.provisioning.sa_retorno_industrializacao import (
    SA_G1_NAME, SA_G2_NAME, CRON_G1_NAME, CRON_G2_NAME, SA_BODY_G1, SA_BODY_G2)
from tests.odoo.services.test_provisioning_sa_industrializacao import FakeOdoo


# ── mensagem_alerta (puro) ────────────────────────────────────────────────────
def test_mensagem_alerta_silencio_quando_saudavel():
    assert mensagem_alerta(None) is None
    assert mensagem_alerta({'acao_necessaria': False, 'detalhes': []}) is None


def test_mensagem_alerta_lista_pendencias():
    flag = {'acao_necessaria': True, 'verificado_em': '2026-06-15T10:00:00',
            'detalhes': [{'artefato': SA_G1_NAME, 'status': 'AUSENTE', 'acao': 're-aplicar'},
                         {'artefato': CRON_G1_NAME, 'status': 'OK', 'acao': None}]}
    msg = mensagem_alerta(flag)
    assert msg is not None
    assert 'RE-APLICAÇÃO' in msg
    assert SA_G1_NAME in msg
    assert 'provisionar --confirmar' in msg
    assert CRON_G1_NAME not in msg          # só pendências (acao != None)


# ── flag round-trip ───────────────────────────────────────────────────────────
def test_flag_round_trip(tmp_path):
    p = str(tmp_path / 'health.json')
    status = {'ok': False, 'acao_necessaria': True, 'detalhes': [], 'verificado_em': 'x'}
    gravar_flag(status, p)
    assert ler_flag(p) == status


def test_ler_flag_ausente_retorna_none(tmp_path):
    assert ler_flag(str(tmp_path / 'nao_existe.json')) is None


# ── verificar_e_gravar_flag (D8) ──────────────────────────────────────────────
def _saudavel():
    return FakeOdoo(
        sas={SA_G1_NAME: {'id': 1, 'code': SA_BODY_G1}, SA_G2_NAME: {'id': 2, 'code': SA_BODY_G2}},
        crons={CRON_G1_NAME: {'id': 10, 'active': True, 'ir_actions_server_id': [1, 'g1']},
               CRON_G2_NAME: {'id': 11, 'active': True, 'ir_actions_server_id': [2, 'g2']}})


def test_verificar_e_gravar_flag_saudavel(tmp_path):
    p = str(tmp_path / 'health.json')
    status = verificar_e_gravar_flag(flag_path=p, odoo=_saudavel())
    assert status['ok'] is True
    assert status['acao_necessaria'] is False
    assert ler_flag(p)['ok'] is True            # gravou o flag
    assert mensagem_alerta(ler_flag(p)) is None  # hook fica em silêncio


def test_verificar_e_gravar_flag_detecta_sumico(tmp_path):
    p = str(tmp_path / 'health.json')
    fake = _saudavel()
    del fake.sas[SA_G1_NAME]                      # upgrade apagou a SA G1
    status = verificar_e_gravar_flag(flag_path=p, odoo=fake)
    assert status['acao_necessaria'] is True
    assert fake.escritas == []                    # checagem é READ-only
    msg = mensagem_alerta(ler_flag(p))
    assert msg and SA_G1_NAME in msg              # hook avisaria a próxima sessão
