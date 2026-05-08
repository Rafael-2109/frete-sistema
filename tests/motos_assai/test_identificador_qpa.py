"""Testes de regressao para IdentificadorDocumento apos modificacoes do Plano 2 Motos Assai.

Verifica que:
- PDF Q.P.A. (CNPJ 53.780.554/0001-15) identifica corretamente como 'QPA'
- PDF Assai nativo (CNPJ Sendas + Consinco) NAO e confundido com QPA
- PDF Atacadao continua funcionando normalmente
"""
import pytest
from app.pedidos.leitura.identificador import IdentificadorDocumento


def _make_identificador(texto: str) -> IdentificadorDocumento:
    """Cria IdentificadorDocumento com texto_primeira_pagina pre-definido (sem abrir PDF)."""
    ident = IdentificadorDocumento()
    ident.texto_primeira_pagina = texto
    ident.texto_completo = texto
    return ident


def test_identificar_qpa_por_cnpj_emissor():
    """PDF com CNPJ Q.P.A. (53.780.554/0001-15) deve retornar rede 'QPA' com alta confianca."""
    texto = (
        "PEDIDO DE COMPRAS 21439695/L\n"
        "FORNECEDOR 4442498\n"
        "R. Social Q.P.A DISTRIBUICAO LTDA           CNPJ 53.780.554/0001-15\n"
        "DADOS PARA FATURAMENTO\n"
        "R. Social SENDAS DISTRIBUIDORA S/A LJ12     CNPJ 06.057.223/0272-90\n"
        "ENDEREÇO PARA ENTREGA\n"
        "Cidade JUNDIAI - SP"
    )
    ident = _make_identificador(texto)
    rede, conf = ident._identificar_rede()
    assert rede == 'QPA', f"Esperava 'QPA', veio '{rede}'"
    assert conf >= 0.95, f"Confianca esperada >= 0.95, veio {conf}"


def test_identificar_assai_nao_classifica_como_qpa():
    """PDF Assai nativo (CNPJ Sendas + Consinco) sem CNPJ QPA deve retornar 'ASSAI', nao 'QPA'.

    Este e o teste critico para garantir que a remocao do padrao
    r'PEDIDO\\s+DE\\s+COMPRAS\\s+\\d+/[A-Z]' de PADROES_TEXTO_REDE['QPA']
    nao causou regressao inversa.
    """
    texto = (
        "PEDIDO DE COMPRAS 12345/X\n"
        "SENDAS DISTRIBUIDORA S/A LJ12\n"
        "CNPJ 06.057.223/0272-90\n"
        "Sistema Consinco\n"
        "ASSAI ATACADISTA"
    )
    ident = _make_identificador(texto)
    rede, conf = ident._identificar_rede()
    assert rede == 'ASSAI', (
        f"PDF Assai nativo deveria ser identificado como 'ASSAI', veio '{rede}'. "
        f"Verificar se padrao Consinco/Sendas esta em PADROES_TEXTO_REDE['ASSAI']."
    )


def test_identificar_atacadao_nao_afetado():
    """Atacadao continua funcionando — texto com padroes Atacadao deve retornar 'ATACADAO'."""
    texto = (
        "Atacadao S.A. PEDIDO 99999\n"
        "CNPJ 75.315.333/0001-09\n"
        "CCPMERM01\n"
        "Proposta de Compra"
    )
    ident = _make_identificador(texto)
    rede, conf = ident._identificar_rede()
    assert rede == 'ATACADAO', f"Esperava 'ATACADAO', veio '{rede}'"
