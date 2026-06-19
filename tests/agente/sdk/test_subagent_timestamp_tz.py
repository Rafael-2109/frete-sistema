"""TDD do fix de fuso em _parse_iso_timestamp (2026-06-19).

`agent_invocation_metrics.started_at` vinha do JSONL do subagente (ISO 'Z' = UTC)
mas era gravado UTC-naive, enquanto `recorded_at` usa Brasil-naive. Resultado:
206/206 metricas com started_at ~3h ADIANTADO (started_at > recorded_at, impossivel),
quebrando analise temporal por janela. Fix: converter UTC->Brasil antes de virar naive.
"""
from datetime import datetime, timezone

from app.agente.sdk.subagent_reader import _parse_iso_timestamp


def test_iso_z_utc_convertido_para_brasil_naive():
    # 10:11:53Z (UTC) -> 07:11:53 Brasil (UTC-3), naive
    r = _parse_iso_timestamp("2026-06-19T10:11:53.399Z")
    assert r is not None and r.tzinfo is None
    assert (r.year, r.month, r.day, r.hour, r.minute) == (2026, 6, 19, 7, 11)


def test_iso_offset_convertido_para_brasil():
    r = _parse_iso_timestamp("2026-06-19T10:11:53+00:00")
    assert r.tzinfo is None and r.hour == 7


def test_epoch_ms_convertido_para_brasil():
    ts_ms = int(datetime(2026, 6, 19, 10, 11, 53, tzinfo=timezone.utc).timestamp() * 1000)
    r = _parse_iso_timestamp(ts_ms)
    assert r is not None and r.tzinfo is None and r.hour == 7


def test_datetime_aware_convertido_para_brasil():
    aware = datetime(2026, 6, 19, 10, 11, 53, tzinfo=timezone.utc)
    r = _parse_iso_timestamp(aware)
    assert r.tzinfo is None and r.hour == 7


def test_iso_naive_mantido_como_brasil():
    # sem fuso -> assume ja Brasil, mantem
    r = _parse_iso_timestamp("2026-06-19T07:11:53")
    assert r.tzinfo is None and r.hour == 7


def test_none_retorna_none():
    assert _parse_iso_timestamp(None) is None


def test_regressao_started_nao_fica_no_futuro():
    # antes do fix: started(UTC 10:11) > recorded(Brasil 07:18) -> bug.
    # depois: started(Brasil 07:11) <= recorded(Brasil 07:18).
    started = _parse_iso_timestamp("2026-06-19T10:11:53.399Z")
    assert started is not None
    recorded_brasil = datetime(2026, 6, 19, 7, 18, 13)
    assert started <= recorded_brasil
