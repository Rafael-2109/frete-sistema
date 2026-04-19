"""Testes F1 (cross-tipo) + F5 (cancelamento Nacom→CarVia) + R2.4 (audit).

Escopo MINIMO de integridade. Sem assuncoes.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# F1 — Conciliação cross-tipo (eh_compensacao)
# ---------------------------------------------------------------------------

class TestF1CrossTipo:
    def test_modelo_tem_campos(self, app):
        """Integridade: modelo CarviaConciliacao suporta flag +
        motivo de compensacao."""
        from app.carvia.models import CarviaConciliacao
        assert hasattr(CarviaConciliacao, 'eh_compensacao')
        assert hasattr(CarviaConciliacao, 'compensacao_motivo')

    def test_service_valida_gate_direcao(self, app):
        """Integridade: gate direcional continua bloqueando sem flag."""
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            DOCS_CREDITO, DOCS_DEBITO,
        )
        # Sanity: conjuntos hard-coded preservados
        assert 'fatura_cliente' in DOCS_CREDITO
        assert 'fatura_transportadora' in DOCS_DEBITO
        # Nao cruzam
        assert not (DOCS_CREDITO & DOCS_DEBITO)

    def test_service_aceita_flag_eh_compensacao(self, app):
        """Integridade: parametro eh_compensacao eh aceito na API do
        service."""
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        # Service nao deve ter signature nova — eh_compensacao vem no
        # doc_info dict. Validamos via code inspection.
        import inspect
        src = inspect.getsource(CarviaConciliacaoService.conciliar)
        assert 'eh_compensacao' in src
        assert 'compensacao_motivo' in src


# ---------------------------------------------------------------------------
# F5 — Cancelamento Nacom→CarVia
# ---------------------------------------------------------------------------

class TestF5Propagacao:
    def test_service_importavel(self, app):
        """Integridade: cancelar_artefatos_carvia_do_embarque eh funcao
        publica do modulo embarque_carvia_service."""
        from app.carvia.services.documentos.embarque_carvia_service import (
            cancelar_artefatos_carvia_do_embarque,
        )
        import inspect
        sig = inspect.signature(cancelar_artefatos_carvia_do_embarque)
        for p in ['embarque_id', 'usuario', 'motivo']:
            assert p in sig.parameters

    def test_service_sem_embarque_retorna_zero_cancelados(self, app):
        """Integridade: quando nao ha CarviaFrete no embarque, retorna
        estrutura esperada sem levantar excecao."""
        from app.carvia.services.documentos.embarque_carvia_service import (
            cancelar_artefatos_carvia_do_embarque,
        )
        with app.app_context():
            r = cancelar_artefatos_carvia_do_embarque(
                embarque_id=999999, usuario='test',
                motivo='teste sem artefatos',
            )
            assert isinstance(r, dict)
            assert r['cancelados_total'] == 0
            assert r['bloqueados'] == []

    def test_route_cancelar_embarque_importa_hook(self):
        """Integridade: rota de cancelamento de embarque Nacom contem o
        hook F5 (referencia ao service CarVia)."""
        import inspect
        from app.embarques import routes as embarques_routes
        src = inspect.getsource(embarques_routes.cancelar_embarque)
        assert 'cancelar_artefatos_carvia_do_embarque' in src


# ---------------------------------------------------------------------------
# R2.4 — Audit de subcontrato_id deprecated
# ---------------------------------------------------------------------------

class TestR24Audit:
    def test_script_executavel(self):
        """Integridade: script audit existe e e valido Python."""
        from pathlib import Path
        script = (
            Path(__file__).resolve().parent.parent.parent /
            'scripts' / 'carvia' /
            'audit_subcontrato_id_deprecated.py'
        )
        assert script.exists(), f'Script nao encontrado: {script}'
        # Verifica que e parseavel
        import ast
        src = script.read_text(encoding='utf-8')
        ast.parse(src)

    def test_deprecation_documentada_no_modelo(self):
        """Integridade: comentario DEPRECATED no modelo orienta novos
        devs a usar o path canonical."""
        from pathlib import Path
        modelo = (
            Path(__file__).resolve().parent.parent.parent /
            'app' / 'carvia' / 'models' / 'frete.py'
        )
        src = modelo.read_text(encoding='utf-8')
        # Verifica que o comentario esta no bloco da FK
        idx = src.find('subcontrato_id = db.Column(')
        assert idx > 0
        # 30 linhas antes devem conter o aviso
        inicio = src.rfind('\n', 0, idx - 500)
        bloco = src[inicio:idx]
        assert 'DEPRECATED' in bloco
        assert 'frete.subcontratos' in bloco
