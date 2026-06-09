"""
Testes do lock de re-entrada no lancamento Odoo (anti duplo-clique).

Cobre o fix de IMP-2026-06-08-001: o pipeline de 16 etapas NAO tinha lock
distribuido. Quando o usuario clicava 2x no botao (a Etapa 6
`action_gerar_po_dfe` demora ~1min), duas execucoes concorrentes do MESMO
frete/despesa chamavam a Etapa 6 em paralelo, gerando DOIS POs + DUAS invoices
duplicados no Odoo.

O fix adiciona `_adquirir_lock_lancamento` / `_liberar_lock_lancamento`
(Redis SET NX EX, fail-open), espelhando o padrao ja validado em
`app/recebimento/workers/recebimento_lf_jobs.py`.

Estes testes nao tocam o banco: mockam o Redis via monkeypatch.
"""
import contextlib

from app.fretes.workers import lancamento_odoo_jobs as jobs


class FakeRedis:
    """Redis em memoria simulando SET NX EX + delete (como redis-py)."""

    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):
        # redis-py retorna None quando NX falha (chave ja existe), True se gravou
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)


def test_adquirir_lock_primeira_vez_sucesso(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(jobs, '_get_redis_connection', lambda: fake)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True


def test_adquirir_lock_segunda_vez_negado(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(jobs, '_get_redis_connection', lambda: fake)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True
    # Segunda aquisicao do MESMO frete deve falhar (lock ativo = duplo-clique)
    assert jobs._adquirir_lock_lancamento('frete', 123) is False


def test_lock_por_entidade_independente(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(jobs, '_get_redis_connection', lambda: fake)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True
    # Outro frete nao e' bloqueado, e despesa usa namespace proprio
    assert jobs._adquirir_lock_lancamento('frete', 456) is True
    assert jobs._adquirir_lock_lancamento('despesa', 123) is True


def test_liberar_lock_permite_readquirir(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(jobs, '_get_redis_connection', lambda: fake)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True
    assert jobs._adquirir_lock_lancamento('frete', 123) is False
    jobs._liberar_lock_lancamento('frete', 123)
    # Apos liberar, pode readquirir (job concluiu → proximo lancamento permitido)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True


def test_adquirir_lock_fail_open_redis_indisponivel(monkeypatch):
    # Redis None → fail-open (NAO bloqueia lancamento)
    monkeypatch.setattr(jobs, '_get_redis_connection', lambda: None)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True


def test_adquirir_lock_fail_open_redis_excecao(monkeypatch):
    def boom():
        raise RuntimeError("redis down")
    monkeypatch.setattr(jobs, '_get_redis_connection', boom)
    assert jobs._adquirir_lock_lancamento('frete', 123) is True


def test_lancar_frete_job_aborta_se_lock_ativo(monkeypatch):
    """Lock ja retido (outro job processando) → aborta SEM abrir contexto Flask."""
    monkeypatch.setattr(jobs, '_adquirir_lock_lancamento', lambda tipo, eid: False)

    ctx_aberto = {'flag': False}

    @contextlib.contextmanager
    def fake_ctx():
        ctx_aberto['flag'] = True
        yield
    monkeypatch.setattr(jobs, '_app_context_safe', fake_ctx)

    resultado = jobs.lancar_frete_job(frete_id=999, usuario_nome='Teste')

    assert resultado['success'] is False
    assert resultado['skipped'] is True
    assert resultado['error_type'] == 'LANCAMENTO_EM_ANDAMENTO'
    # Nao abriu contexto Flask → service/banco/Odoo nao foram tocados
    assert ctx_aberto['flag'] is False


def test_lancar_despesa_job_aborta_se_lock_ativo(monkeypatch):
    monkeypatch.setattr(jobs, '_adquirir_lock_lancamento', lambda tipo, eid: False)

    ctx_aberto = {'flag': False}

    @contextlib.contextmanager
    def fake_ctx():
        ctx_aberto['flag'] = True
        yield
    monkeypatch.setattr(jobs, '_app_context_safe', fake_ctx)

    resultado = jobs.lancar_despesa_job(despesa_id=999, usuario_nome='Teste')

    assert resultado['success'] is False
    assert resultado['skipped'] is True
    assert resultado['error_type'] == 'LANCAMENTO_EM_ANDAMENTO'
    assert ctx_aberto['flag'] is False


def test_lock_liberado_no_finally_apos_erro(monkeypatch):
    """Se o job falhar dentro do contexto, o lock DEVE ser liberado (finally)."""
    liberados = []
    monkeypatch.setattr(jobs, '_adquirir_lock_lancamento', lambda tipo, eid: True)
    monkeypatch.setattr(
        jobs, '_liberar_lock_lancamento',
        lambda tipo, eid: liberados.append((tipo, eid))
    )

    @contextlib.contextmanager
    def ctx_que_explode():
        raise RuntimeError("falha simulada dentro do contexto")
        yield  # pragma: no cover
    monkeypatch.setattr(jobs, '_app_context_safe', ctx_que_explode)

    resultado = jobs.lancar_frete_job(frete_id=777, usuario_nome='Teste')

    assert resultado['success'] is False
    assert resultado['error_type'] == 'ERRO_INESPERADO'
    # Lock liberado mesmo com excecao
    assert ('frete', 777) in liberados
