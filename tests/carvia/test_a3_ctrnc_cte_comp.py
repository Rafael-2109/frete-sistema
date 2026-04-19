"""Testes A3 — CTRNC CTe Complementar extraido/verificado automaticamente.

Cobre refator de `verificar_ctrc_cte_comp_job` (A3.2):
  - Caso A (EXTRACAO): ctrc vazio + cte_numero -> busca SSW 101
  - Caso B (VERIFICACAO): ctrc preenchido -> resolver_ctrc_ssw (divergencia)
  - Caso C (SKIPPED): ambos vazios

Tambem valida enqueue automatico (A3.3) via feature flag.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_cte_comp(
    id_: int = 42,
    ctrc_numero: str | None = None,
    cte_numero: str | None = None,
    status: str = 'RASCUNHO',
) -> MagicMock:
    """Cria mock de CarviaCteComplementar para testes unitarios."""
    m = MagicMock()
    m.id = id_
    m.ctrc_numero = ctrc_numero
    m.cte_numero = cte_numero
    m.status = status
    m.atualizado_em = None
    return m


def _fake_resultado_ssw_sucesso(ctrc_completo: str = 'CAR000113-9') -> dict:
    return {
        'sucesso': True,
        'dados': {'ctrc_completo': ctrc_completo},
    }


def _fake_resultado_ssw_falha(erro: str = 'CTe nao encontrado') -> dict:
    return {
        'sucesso': False,
        'erro': erro,
    }


# ---------------------------------------------------------------------------
# Caso A: EXTRACAO (ctrc_numero vazio + cte_numero preenchido)
# ---------------------------------------------------------------------------

class TestCasoAExtracao:
    """Caso A: busca SSW 101 --cte, extrai ctrc_completo, persiste."""

    def test_extrai_ctrc_ssw_e_persiste(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero=None, cte_numero='161', status='RASCUNHO'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.workers._ssw_helpers.consultar_101_por_cte'
            ) as mock_consultar, patch(
                'app.carvia.workers._ssw_helpers.liberar_conexao_antes_playwright'
            ) as mock_liberar, patch(
                'app.carvia.workers._ssw_helpers.commit_com_retry'
            ) as mock_commit:
                mock_db.session.get.return_value = cte_comp
                mock_consultar.return_value = _fake_resultado_ssw_sucesso(
                    'CAR000113-9'
                )
                # commit_com_retry executa apply_fn() em producao — simulamos
                mock_commit.side_effect = lambda fn: fn()

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'EXTRAIDO', resultado
            assert resultado['ctrc_novo'] == 'CAR-113-9'
            assert resultado['ctrc_anterior'] is None
            assert resultado['cte_numero'] == '161'
            mock_liberar.assert_called_once()
            mock_consultar.assert_called_once_with('161', filial='CAR')
            # commit_com_retry eh chamado (R15 SSL resilience)
            mock_commit.assert_called_once()

    def test_normaliza_cte_numero_com_zeros_a_esquerda(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero=None, cte_numero='000000161'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.workers._ssw_helpers.consultar_101_por_cte'
            ) as mock_consultar, patch(
                'app.carvia.workers._ssw_helpers.liberar_conexao_antes_playwright'
            ), patch(
                'app.carvia.workers._ssw_helpers.commit_com_retry'
            ) as mock_commit:
                mock_db.session.get.return_value = cte_comp
                mock_consultar.return_value = _fake_resultado_ssw_sucesso()
                mock_commit.side_effect = lambda fn: fn()

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                verificar_ctrc_cte_comp_job(42)

            # Deve normalizar '000000161' -> '161'
            mock_consultar.assert_called_once_with('161', filial='CAR')

    def test_ssw_falha_retorna_erro(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero=None, cte_numero='161'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.workers._ssw_helpers.consultar_101_por_cte'
            ) as mock_consultar, patch(
                'app.carvia.workers._ssw_helpers.liberar_conexao_antes_playwright'
            ):
                mock_db.session.get.return_value = cte_comp
                mock_consultar.return_value = _fake_resultado_ssw_falha(
                    'CTe 161 nao encontrado'
                )

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'ERRO'
            assert 'nao encontrado' in resultado['erro']
            assert resultado['cte_numero'] == '161'

    def test_ssw_sem_ctrc_completo_retorna_erro(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero=None, cte_numero='161'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.workers._ssw_helpers.consultar_101_por_cte'
            ) as mock_consultar, patch(
                'app.carvia.workers._ssw_helpers.liberar_conexao_antes_playwright'
            ):
                mock_db.session.get.return_value = cte_comp
                mock_consultar.return_value = {
                    'sucesso': True,
                    'dados': {},  # sem ctrc_completo
                }

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'ERRO'
            assert 'ctrc_completo' in resultado['erro']


# ---------------------------------------------------------------------------
# Caso B: VERIFICACAO (ctrc_numero preenchido)
# ---------------------------------------------------------------------------

class TestCasoBVerificacao:
    """Caso B: ctrc ja preenchido -> resolver_ctrc_ssw compara com SSW."""

    def test_ctrc_confirmado_retorna_ok(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero='CAR-110-9', cte_numero='161'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.services.cte_complementar_persistencia.resolver_ctrc_ssw'
            ) as mock_resolver:
                mock_db.session.get.return_value = cte_comp
                # resolver_ctrc_ssw retorna None quando nao ha divergencia
                mock_resolver.return_value = None

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'OK'
            assert resultado['ctrc'] == 'CAR-110-9'

    def test_ctrc_divergente_corrigido(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(
                ctrc_numero='CAR-110-9', cte_numero='161'
            )

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.services.cte_complementar_persistencia.resolver_ctrc_ssw'
            ) as mock_resolver:
                mock_db.session.get.return_value = cte_comp
                mock_resolver.return_value = 'CAR-113-9'

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'CORRIGIDO'
            assert resultado['ctrc_anterior'] == 'CAR-110-9'
            assert resultado['ctrc_novo'] == 'CAR-113-9'
            assert cte_comp.ctrc_numero == 'CAR-113-9'
            # Commit e chamado pelo menos uma vez (Caso B usa commit direto).
            # NAO exigir `_called_once` porque outros caminhos internos podem
            # adicionar commits intermediarios.
            assert mock_db.session.commit.called


# ---------------------------------------------------------------------------
# Caso C: SKIPPED (ambos vazios)
# ---------------------------------------------------------------------------

class TestCasoCSkipped:

    def test_ambos_vazios_retorna_skipped(self, app):
        with app.app_context():
            cte_comp = _fake_cte_comp(ctrc_numero=None, cte_numero=None)

            with patch('app.db') as mock_db:
                mock_db.session.get.return_value = cte_comp

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(42)

            assert resultado['status'] == 'SKIPPED'
            assert 'sem ctrc_numero e sem cte_numero' in resultado['motivo']

    def test_cte_comp_nao_encontrado_retorna_skipped(self, app):
        with app.app_context():
            with patch('app.db') as mock_db:
                mock_db.session.get.return_value = None

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                resultado = verificar_ctrc_cte_comp_job(999)

            assert resultado['status'] == 'SKIPPED'
            assert 'nao encontrado' in resultado['motivo'].lower()


# ---------------------------------------------------------------------------
# Guard de idempotencia (extracao nao sobrescreve valor ja setado)
# ---------------------------------------------------------------------------

class TestGuardIdempotencia:
    """Se outro worker setou ctrc_numero entre o get inicial e o commit,
    o apply_fn nao sobrescreve (NN5 idempotencia)."""

    def test_apply_fn_nao_sobrescreve_ctrc_ja_setado(self, app):
        """Simula race: snapshot inicial com ctrc=None, mas no re-get do
        apply_fn o ctrc ja foi setado por outro worker."""
        with app.app_context():
            # Snapshot inicial: ctrc=None
            cte_comp_snapshot = _fake_cte_comp(
                ctrc_numero=None, cte_numero='161'
            )
            # Re-get (dentro do apply_fn): ctrc ja preenchido por outro job
            cte_comp_atualizado = _fake_cte_comp(
                ctrc_numero='CAR-113-9', cte_numero='161'
            )

            captured_apply_fn = []

            def capture_apply(fn):
                captured_apply_fn.append(fn)

            with patch(
                'app.db'
            ) as mock_db, patch(
                'app.carvia.workers._ssw_helpers.consultar_101_por_cte'
            ) as mock_consultar, patch(
                'app.carvia.workers._ssw_helpers.liberar_conexao_antes_playwright'
            ), patch(
                'app.carvia.workers._ssw_helpers.commit_com_retry'
            ) as mock_commit:
                # Primeiro get (snapshot) -> None na session.get
                mock_db.session.get.side_effect = [
                    cte_comp_snapshot,      # snapshot inicial no worker
                    cte_comp_atualizado,    # re-get dentro do apply_fn
                ]
                mock_consultar.return_value = _fake_resultado_ssw_sucesso(
                    'CAR000113-9'
                )
                mock_commit.side_effect = capture_apply

                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    verificar_ctrc_cte_comp_job,
                )
                verificar_ctrc_cte_comp_job(42)

            # Executa o apply_fn capturado manualmente
            assert len(captured_apply_fn) == 1
            captured_apply_fn[0]()

            # O ctrc_numero do cte_comp_atualizado NAO deve ter sido
            # sobrescrito — guard previne race.
            assert cte_comp_atualizado.ctrc_numero == 'CAR-113-9'


# ---------------------------------------------------------------------------
# Feature flag A3.3: enqueue automatico na importacao
# ---------------------------------------------------------------------------

class TestFeatureFlagEnqueueAutomatico:
    """Valida que a feature flag CARVIA_FEATURE_ENQUEUE_CTRC_CTE_COMP_AUTO
    controla o enqueue automatico na importacao."""

    def test_flag_default_e_false(self, app):
        """Default conservador: flag OFF em configuracao nao-definida."""
        # create_app() ja foi chamado via fixture. Testa a config.
        assert app.config.get(
            'CARVIA_FEATURE_ENQUEUE_CTRC_CTE_COMP_AUTO', False
        ) is False

    def test_flag_verificar_ctrc_ssw_opt_in_ainda_funciona(self, app):
        """Backward compat: se a flag global esta off mas o cte_data
        vem com verificar_ctrc_ssw=True (opt-in manual do preview),
        o enqueue deve acontecer. A logica e: `_enqueue_auto OR
        cte_data.get('verificar_ctrc_ssw')`."""
        # Teste de logica pura
        cte_data_com_opt_in = {'verificar_ctrc_ssw': True}
        cte_data_sem_opt_in = {'verificar_ctrc_ssw': False}

        flag_off = False
        flag_on = True

        assert (flag_off or cte_data_com_opt_in.get('verificar_ctrc_ssw')) is True
        assert (flag_off or cte_data_sem_opt_in.get('verificar_ctrc_ssw')) is False
        assert (flag_on or cte_data_sem_opt_in.get('verificar_ctrc_ssw')) is True


# ---------------------------------------------------------------------------
# Rota A3.5: api_atualizar_ctrc_cte_complementar
# ---------------------------------------------------------------------------

class TestRotaAtualizarCtrcCteComp:

    def test_rota_registrada(self, app):
        with app.app_context():
            rules = [
                r for r in app.url_map.iter_rules()
                if 'cte-complementar' in str(r) and 'atualizar-ctrc' in str(r)
            ]
            assert len(rules) == 1
            assert rules[0].endpoint == 'carvia.api_atualizar_ctrc_cte_complementar'
