"""Testes do automato de cadeia de eventos da skill corrigindo-dados-assai.

_planejar_cadeia e' uma funcao PURA (so strings) — testa as transicoes de
backfill, idempotencia, alvos proibidos e estados de partida do fluxo de venda.
"""
import importlib.util
import os

import pytest

_SK = os.path.join(
    os.path.dirname(__file__),
    '../../.claude/skills/corrigindo-dados-assai/scripts/corrigindo_dados_assai.py',
)


def _load_skill():
    spec = importlib.util.spec_from_file_location('corrigindo_dados_assai', _SK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cda = _load_skill()


@pytest.mark.parametrize('partida,alvo,esperado', [
    (None, 'ESTOQUE', ['ESTOQUE']),
    ('ESTOQUE', 'MONTADA', ['MONTADA']),
    ('ESTOQUE', 'PENDENTE', ['PENDENTE']),
    ('ESTOQUE', 'DISPONIVEL', ['MONTADA', 'DISPONIVEL']),
    ('MONTADA', 'DISPONIVEL', ['DISPONIVEL']),
    ('MONTADA', 'PENDENTE', ['PENDENTE']),
    ('PENDENTE', 'MONTADA', ['PENDENCIA_RESOLVIDA', 'MONTADA']),
    ('PENDENTE', 'DISPONIVEL', ['PENDENCIA_RESOLVIDA', 'MONTADA', 'DISPONIVEL']),
    ('DISPONIVEL', 'MONTADA', ['REVERTIDA']),
    ('DISPONIVEL', 'PENDENTE', ['PENDENTE']),
    ('DISPONIVEL', 'DEMONSTRACAO', ['DEMONSTRACAO']),
    (None, 'DISPONIVEL', ['ESTOQUE', 'MONTADA', 'DISPONIVEL']),
    (None, 'PENDENTE', ['ESTOQUE', 'PENDENTE']),
])
def test_planejar_cadeia_caminhos(partida, alvo, esperado):
    cadeia, erro = cda._planejar_cadeia(partida, alvo)
    assert erro is None, erro
    assert cadeia == esperado


def test_planejar_cadeia_idempotente():
    """Ja no alvo -> cadeia vazia (skip)."""
    cadeia, erro = cda._planejar_cadeia('DISPONIVEL', 'DISPONIVEL')
    assert erro is None
    assert cadeia == []


def test_planejar_cadeia_estado_transitorio_normalizado():
    """PENDENCIA_RESOLVIDA / REVERTIDA contam como MONTADA efetivo."""
    cadeia, erro = cda._planejar_cadeia('PENDENCIA_RESOLVIDA', 'DISPONIVEL')
    assert erro is None
    assert cadeia == ['DISPONIVEL']
    cadeia2, erro2 = cda._planejar_cadeia('REVERTIDA_PARA_MONTADA', 'DISPONIVEL')
    assert erro2 is None
    assert cadeia2 == ['DISPONIVEL']


@pytest.mark.parametrize('alvo', ['FATURADA', 'SEPARADA', 'CARREGADA',
                                  'CANCELADA', 'MOTO_FALTANDO'])
def test_planejar_cadeia_alvo_proibido(alvo):
    """Estados do fluxo de venda nao sao alvo de backfill."""
    cadeia, erro = cda._planejar_cadeia('DISPONIVEL', alvo)
    assert cadeia is None
    assert erro and 'nao e operavel' in erro


@pytest.mark.parametrize('partida', ['SEPARADA', 'FATURADA', 'CARREGADA',
                                     'MOTO_FALTANDO'])
def test_planejar_cadeia_partida_fluxo_venda(partida):
    """Backfill nao opera a partir de estado do fluxo de venda."""
    cadeia, erro = cda._planejar_cadeia(partida, 'DISPONIVEL')
    assert cadeia is None
    assert erro and 'fluxo de venda' in erro


def test_status_planilha_mapeia_termos():
    """Termos da planilha mapeiam para o alvo canonico; FATURADO nao mapeia."""
    assert cda.STATUS_PLANILHA.get('DISPONÍVEL') == 'DISPONIVEL'
    assert cda.STATUS_PLANILHA.get('DEMONSTRAÇÃO') == 'DEMONSTRACAO'
    assert cda.STATUS_PLANILHA.get('PENDENTE') == 'PENDENTE'
    assert cda.STATUS_PLANILHA.get('FATURADO') is None


def test_parse_ocorrido_em_formatos():
    """Aceita ISO e DD/MM/YYYY (Brasil naive, sem tzinfo)."""
    from datetime import datetime
    assert cda._parse_ocorrido_em('2026-04-15') == datetime(2026, 4, 15)
    assert cda._parse_ocorrido_em('15/04/2026') == datetime(2026, 4, 15)
    assert cda._parse_ocorrido_em(None) is None
    assert cda._parse_ocorrido_em('') is None
    with pytest.raises(ValueError):
        cda._parse_ocorrido_em('data-invalida')


# ----- registrar-devolucao-nfd (IMP-2026-06-19-010) -------------------------
# Validacao de args + dry-run sao PUROS (nao tocam DB): o service so e' chamado
# no --confirmar. Testa o contrato do handler sem fixtures de banco.
import types  # noqa: E402


def _args_dev(**kw):
    base = dict(nf_id=None, numero_nfd=None, motivo=None, data_devolucao=None,
                chassis_json=None, chassi=None, confirmar=False, user_id=74)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_devolucao_nfd_exige_nf_id():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        numero_nfd='123', motivo='avaria', data_devolucao='2026-06-20',
        chassi='MCBRX11M123456789'))
    assert r['ok'] is False and r['tipo_erro'] == 'validacao'
    assert '--nf-id' in r['erro']


def test_devolucao_nfd_exige_numero_nfd():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, motivo='avaria', data_devolucao='2026-06-20', chassi='X'))
    assert r['ok'] is False and '--numero-nfd' in r['erro']


def test_devolucao_nfd_exige_motivo_minimo():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, numero_nfd='123', motivo='ab', data_devolucao='2026-06-20',
        chassi='X'))
    assert r['ok'] is False and 'motivo' in r['erro'].lower()


def test_devolucao_nfd_exige_data():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, numero_nfd='123', motivo='avaria', chassi='X'))
    assert r['ok'] is False and '--data-devolucao' in r['erro']


def test_devolucao_nfd_data_invalida():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, numero_nfd='123', motivo='avaria', data_devolucao='xx/yy',
        chassi='X'))
    assert r['ok'] is False and 'data' in r['erro'].lower()


def test_devolucao_nfd_exige_chassi():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, numero_nfd='123', motivo='avaria', data_devolucao='2026-06-20'))
    assert r['ok'] is False and 'chassi' in r['erro'].lower()


def test_devolucao_nfd_chassis_json_nao_lista():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=1, numero_nfd='123', motivo='avaria', data_devolucao='2026-06-20',
        chassis_json='"soh-uma-string"'))
    assert r['ok'] is False and 'chassis-json' in r['erro'].lower()


def test_devolucao_nfd_dry_run_chassi_single_normaliza():
    """Dry-run: chassi vira UPPER, data DD/MM/YYYY normaliza para ISO."""
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=7, numero_nfd='99', motivo='avaria no transporte',
        data_devolucao='20/06/2026', chassi='mcbrx11m123456789'))
    assert r.get('dry_run') is True
    assert r['modo'] == 'registrar-devolucao-nfd'
    assert r['nf_id'] == 7
    assert r['chassis'] == ['MCBRX11M123456789']
    assert r['n_chassis'] == 1
    assert r['data_devolucao'] == '2026-06-20'


def test_devolucao_nfd_dry_run_chassis_json_multi():
    r = cda._cmd_registrar_devolucao_nfd(_args_dev(
        nf_id=7, numero_nfd='99', motivo='avaria', data_devolucao='2026-06-20',
        chassis_json='["abc", "def"]'))
    assert r.get('dry_run') is True
    assert r['chassis'] == ['ABC', 'DEF']
    assert r['n_chassis'] == 2
