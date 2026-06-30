"""Semaforo Redis que LIMITA emissoes de CTe SSW concorrentes.

Causa-raiz do problema original: cada emissao e 1 job na fila `high`, consumida
por varios workers (start_workers NUM_WORKERS + worker_atacadao --workers 2) =>
ate ~9-12 emissoes Playwright rodavam ao mesmo tempo => o SSW saturava (o popup
do frete nao abria em 30s) => taxa de erro ~55%. Medido: ~0% com <=5 simultaneas.

Correcao: um semaforo Redis limita a K emissoes concorrentes (default 3, < 5
seguro). Job excedente re-enfileira sem rodar. Sem Redis => fail-open (nao
limita, comportamento de hoje).
"""
from __future__ import annotations

import app.portal.workers as pw


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, k):
        self.store[k] = self.store.get(k, 0) + 1
        return self.store[k]

    def decr(self, k):
        self.store[k] = self.store.get(k, 0) - 1
        return self.store[k]

    def expire(self, k, t):
        pass

    def set(self, k, v, **kw):
        self.store[k] = v


def test_adquirir_slot_respeita_o_teto(monkeypatch):
    from app.carvia.workers import ssw_cte_jobs as m
    fake = _FakeRedis()
    monkeypatch.setattr(pw, 'get_redis_connection', lambda: fake)
    monkeypatch.setenv('CARVIA_SSW_MAX_CONCORRENTES', '3')

    assert [m._adquirir_slot_ssw() for _ in range(3)] == [True, True, True]
    assert m._adquirir_slot_ssw() is False        # 4o excede o teto
    assert fake.store[m._SSW_SLOTS_KEY] == 3       # o 4o devolveu o slot


def test_liberar_slot_devolve_ao_pool(monkeypatch):
    from app.carvia.workers import ssw_cte_jobs as m
    fake = _FakeRedis()
    monkeypatch.setattr(pw, 'get_redis_connection', lambda: fake)
    monkeypatch.setenv('CARVIA_SSW_MAX_CONCORRENTES', '2')

    m._adquirir_slot_ssw()
    m._adquirir_slot_ssw()                          # 2/2
    assert m._adquirir_slot_ssw() is False          # cheio
    m._liberar_slot_ssw()                           # libera 1 -> 1/2
    assert m._adquirir_slot_ssw() is True           # agora cabe


def test_liberar_slot_nunca_abaixo_de_zero(monkeypatch):
    from app.carvia.workers import ssw_cte_jobs as m
    fake = _FakeRedis()
    monkeypatch.setattr(pw, 'get_redis_connection', lambda: fake)
    m._liberar_slot_ssw()                           # nada ocupado
    assert fake.store.get(m._SSW_SLOTS_KEY, 0) == 0


def test_fail_open_sem_redis(monkeypatch):
    from app.carvia.workers import ssw_cte_jobs as m
    monkeypatch.setattr(pw, 'get_redis_connection', lambda: None)
    # sem Redis NAO limita: nunca bloqueia a emissao (degrada para o de hoje)
    assert all(m._adquirir_slot_ssw() for _ in range(10))


def test_default_serial_um_por_vez(monkeypatch):
    """Sem env, o default e SERIAL: 1 emissao por vez, a 2a espera (re-enfileira)."""
    from app.carvia.workers import ssw_cte_jobs as m
    fake = _FakeRedis()
    monkeypatch.setattr(pw, 'get_redis_connection', lambda: fake)
    monkeypatch.delenv('CARVIA_SSW_MAX_CONCORRENTES', raising=False)

    assert m._adquirir_slot_ssw() is True       # 1a roda
    assert m._adquirir_slot_ssw() is False      # 2a espera — sem concorrencia
    m._liberar_slot_ssw()                       # 1a terminou
    assert m._adquirir_slot_ssw() is True       # agora a proxima entra


def test_max_concorrentes_le_env(monkeypatch):
    from app.carvia.workers import ssw_cte_jobs as m
    monkeypatch.setenv('CARVIA_SSW_MAX_CONCORRENTES', '7')
    assert m._ssw_max_concorrentes() == 7
    monkeypatch.delenv('CARVIA_SSW_MAX_CONCORRENTES', raising=False)
    assert m._ssw_max_concorrentes() == 1           # default: 1 por vez (serial)
