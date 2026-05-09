"""Testes do scope_injector — bloco <loja_context> injetado por turno."""
import pytest

from app.agente_lojas.services.scope_injector import build_loja_context_block


class TestScopeInjector:
    def test_admin_ve_todas(self):
        """Perfil administrador NUNCA tem restricao de loja."""
        block = build_loja_context_block(perfil='administrador', loja_hora_id=3)
        assert 'pode_ver_todas: true' in block
        assert 'loja_ids_permitidas: null' in block
        # NAO deve mencionar a loja_id especifica
        assert 'usuario_loja_hora_id' not in block

    def test_admin_sem_loja(self):
        """Admin sem loja_hora_id setado tambem ve todas."""
        block = build_loja_context_block(perfil='administrador', loja_hora_id=None)
        assert 'pode_ver_todas: true' in block

    def test_usuario_sem_loja_ve_todas(self):
        """Usuario nao-admin SEM loja_hora_id (loja_hora_id=None) tem acesso total.

        Caso documentado: usuario do time central que precisa ver todas as
        lojas mas nao eh admin formal.
        """
        block = build_loja_context_block(perfil='vendedor', loja_hora_id=None)
        assert 'pode_ver_todas: true' in block

    @pytest.mark.parametrize("loja_id", [1, 2, 3, 99])
    def test_usuario_escopado(self, loja_id):
        """Usuario com loja_hora_id setada veh apenas a propria loja."""
        block = build_loja_context_block(perfil='vendedor', loja_hora_id=loja_id)
        assert 'pode_ver_todas: false' in block
        assert f'loja_ids_permitidas: [{loja_id}]' in block
        assert f'loja_default: {loja_id}' in block
        assert f'usuario_loja_hora_id: {loja_id}' in block

    def test_xml_estrutura_valida(self):
        """Bloco deve ser XML-like fechado corretamente."""
        block = build_loja_context_block(perfil='vendedor', loja_hora_id=1)
        assert block.startswith('<loja_context>')
        assert block.rstrip().endswith('</loja_context>')

    def test_admin_xml_estrutura_valida(self):
        block = build_loja_context_block(perfil='administrador', loja_hora_id=1)
        assert block.startswith('<loja_context>')
        assert block.rstrip().endswith('</loja_context>')
