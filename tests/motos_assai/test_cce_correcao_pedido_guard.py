"""IMP-2026-06-23-009: CCe de 'correcao de pedido' que cita motos por chassi era
classificada como CHASSI (cce_llm_fallback infere CHASSI por presenca de chassi) e
o apply tentava TROCAR chassis na NF. Guard: pelo TEXTO BRUTO, se e correcao de
PEDIDO (e nao de CHASSI), nao trocar — registrar para revisao manual."""
from app.motos_assai.services.cce_service import _parece_correcao_de_pedido


def test_pedido_sem_marcador_chassi_e_pedido():
    dados = {'texto_correcao_bruto': 'CORRECAO DE PEDIDO: numero do pedido alterado de 123 para 456'}
    assert _parece_correcao_de_pedido(dados) is True


def test_correcao_de_chassi_nao_e_pedido():
    dados = {'texto_correcao_bruto': 'CORRECAO DE CHASSI - SAINDO: DOT LA2025 BRANCO ENTRANDO: DOT LA2026 BRANCO'}
    assert _parece_correcao_de_pedido(dados) is False


def test_ambos_marcadores_chassi_prevalece():
    # Se o texto fala de chassi explicitamente, NAO downgrade (deixa o fluxo CHASSI seguir).
    dados = {'texto_correcao_bruto': 'CORRECAO DE PEDIDO e tambem CORRECAO DE CHASSI'}
    assert _parece_correcao_de_pedido(dados) is False


def test_texto_vazio_ou_invalido_nao_e_pedido():
    assert _parece_correcao_de_pedido({}) is False
    assert _parece_correcao_de_pedido({'texto_correcao_bruto': ''}) is False
    assert _parece_correcao_de_pedido(None) is False


def test_acentuado_correcao_de_pedido():
    dados = {'texto_correcao_bruto': 'CORREÇÃO DE PEDIDO — número do pedido errado'}
    assert _parece_correcao_de_pedido(dados) is True
