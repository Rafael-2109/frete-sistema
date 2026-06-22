"""Retry de desbloqueio na emissao de CTe SSW (NF 39058 MGS ELETRO, 2026-06-22).

Bug de producao: o script `emitir_cte_004.py` (commit f728e5cb5) passou a
DESBLOQUEAR o cliente bloqueado sozinho (grava Transportar=S na opcao 389) e
ABORTAR a emissao retornando `retentar=True` + `cliente_desbloqueado=True`,
esperando que o orquestrador re-emita. O worker `emitir_cte_ssw_job` nunca
implementou esse retry — marcava ERRO "Cliente bloqueado" falso (o cliente JA
estava desbloqueado). Estes testes travam o contrato dos dois lados:

  1. retry: o worker re-emite UMA vez quando o script sinaliza retentar.
  2. classificador: 'desbloqueado' nao e falso-positivado como CLIENTE_BLOQUEADO,
     mas 'bloqueado' real continua detectado.

Testes puros (sem app/db) — exercitam o helper e o classificador isolados.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# 1. Retry de desbloqueio no worker
# --------------------------------------------------------------------------- #

def test_retry_reemite_uma_vez_quando_cliente_desbloqueado(monkeypatch):
    """retentar=True + cliente_desbloqueado=True => re-emite e usa a 2a passada."""
    from app.carvia.workers import ssw_cte_jobs as m

    res_desbloqueio = {
        'sucesso': False, 'retentar': True, 'cliente_desbloqueado': True,
        'resultado': {'avisos_tratados': ['CLIENTE_BLOQUEADO',
                                          'CLIENTE_DESBLOQUEADO',
                                          'DESBLOQUEADO_RETENTAR']},
    }
    res_ok = {'sucesso': True, 'ctrc': 'CAR-999-9'}
    seq = iter([res_desbloqueio, res_ok])

    chamadas = {'exec': 0, 'liberar': 0, 'etapa': 0}

    def fake_exec(_args):
        chamadas['exec'] += 1
        return next(seq)

    monkeypatch.setattr(m, '_executar_script_cte', fake_exec)
    monkeypatch.setattr(m, '_liberar_conexao_antes_playwright',
                        lambda: chamadas.__setitem__('liberar', chamadas['liberar'] + 1))

    out = m._emitir_cte_com_retry_desbloqueio(
        object(),
        marcar_etapa_retry=lambda: chamadas.__setitem__('etapa', chamadas['etapa'] + 1),
        _sleep=lambda _s: None,
    )

    assert out is res_ok                 # usou o resultado da 2a passada
    assert chamadas['exec'] == 2         # 1 inicial + 1 retry
    assert chamadas['etapa'] == 1        # marcou etapa antes de re-emitir
    assert chamadas['liberar'] == 1      # liberou conexao antes do 2o Playwright


def test_sem_retentar_nao_reemite(monkeypatch):
    """Bloqueio real (desbloqueio falhou, sem retentar) => uma unica passada."""
    from app.carvia.workers import ssw_cte_jobs as m

    res_bloqueio_real = {
        'sucesso': False,
        'resultado': {'avisos_tratados': ['CLIENTE_BLOQUEADO',
                                          'CLIENTE_BLOQUEADO_ABORT']},
    }
    chamadas = {'exec': 0}

    def fake_exec(_args):
        chamadas['exec'] += 1
        return res_bloqueio_real

    monkeypatch.setattr(m, '_executar_script_cte', fake_exec)
    monkeypatch.setattr(m, '_liberar_conexao_antes_playwright', lambda: None)

    out = m._emitir_cte_com_retry_desbloqueio(object(), _sleep=lambda _s: None)

    assert out is res_bloqueio_real
    assert chamadas['exec'] == 1         # NAO re-emitiu


def test_retry_no_maximo_uma_vez(monkeypatch):
    """Se a 2a passada AINDA pede retentar, para (sem loop infinito)."""
    from app.carvia.workers import ssw_cte_jobs as m

    res = {'sucesso': False, 'retentar': True, 'cliente_desbloqueado': True}
    chamadas = {'exec': 0}

    def fake_exec(_args):
        chamadas['exec'] += 1
        return res

    monkeypatch.setattr(m, '_executar_script_cte', fake_exec)
    monkeypatch.setattr(m, '_liberar_conexao_antes_playwright', lambda: None)

    out = m._emitir_cte_com_retry_desbloqueio(object(), _sleep=lambda _s: None)

    assert out is res
    assert chamadas['exec'] == 2         # 1 inicial + 1 retry, e PARA


# --------------------------------------------------------------------------- #
# 2. Classificador de erro SSW — 'desbloqueado' nao e bloqueio
# --------------------------------------------------------------------------- #

def test_desbloqueado_nao_e_classificado_como_bloqueado():
    """Regex (?<!des)bloqueado: 'desbloqueado' nao dispara CLIENTE_BLOQUEADO."""
    from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService

    resultado = {'erro': 'cliente pagador desbloqueado com sucesso'}
    assert SswEmissaoService.detectar_erro_ssw(resultado) is None


def test_bloqueio_real_continua_detectado():
    from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService

    resultado = {'erro': 'cliente pagador bloqueado para transporte (opcao 389)'}
    msg = SswEmissaoService.detectar_erro_ssw(resultado)
    assert msg is not None
    assert 'bloqueado' in msg.lower()
