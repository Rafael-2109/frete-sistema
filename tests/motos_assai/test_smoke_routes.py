"""Smoke tests: todas as rotas GET do blueprint motos_assai devem retornar
200 (ou 302/404 esperado) com sessão de admin autenticado.

Rotas com parâmetros `<int:id>` são testadas sem ID real (404 esperado) ou
com um ID arbitrário quando a rota pode retornar 404 gracefully.
"""

import pytest


# ---------------------------------------------------------------------------
# Dashboard + Cadastros
# ---------------------------------------------------------------------------

def test_smoke_dashboard(login_admin):
    r = login_admin.get('/motos-assai/')
    assert r.status_code == 200


def test_smoke_lojas_lista(login_admin):
    r = login_admin.get('/motos-assai/lojas')
    assert r.status_code == 200


def test_smoke_modelos_lista(login_admin):
    r = login_admin.get('/motos-assai/modelos')
    assert r.status_code == 200


def test_smoke_cd(login_admin):
    r = login_admin.get('/motos-assai/cd')
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------

def test_smoke_pedidos_lista(login_admin):
    r = login_admin.get('/motos-assai/pedidos')
    assert r.status_code == 200


def test_smoke_pedidos_upload(login_admin):
    r = login_admin.get('/motos-assai/pedidos/upload')
    assert r.status_code == 200


def test_smoke_pedido_detalhe_inexistente(login_admin):
    r = login_admin.get('/motos-assai/pedidos/999999')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Compras
# ---------------------------------------------------------------------------

def test_smoke_compras_lista(login_admin):
    r = login_admin.get('/motos-assai/compras')
    assert r.status_code == 200


def test_smoke_compras_nova(login_admin):
    r = login_admin.get('/motos-assai/compras/nova')
    assert r.status_code == 200


def test_smoke_compra_detalhe_inexistente(login_admin):
    r = login_admin.get('/motos-assai/compras/999999')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Recibos
# ---------------------------------------------------------------------------

def test_smoke_recibos_lista(login_admin):
    r = login_admin.get('/motos-assai/recibos')
    assert r.status_code == 200


def test_smoke_recibo_detalhe_inexistente(login_admin):
    r = login_admin.get('/motos-assai/recibos/999999')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Telas rápidas (operação de chão de fábrica)
# ---------------------------------------------------------------------------

def test_smoke_montagem_quick(login_admin):
    r = login_admin.get('/motos-assai/montagem')
    assert r.status_code == 200


def test_smoke_disponibilizar_quick(login_admin):
    r = login_admin.get('/motos-assai/disponibilizar')
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Separação
# ---------------------------------------------------------------------------

def test_smoke_separacao_lista(login_admin):
    r = login_admin.get('/motos-assai/separacao')
    assert r.status_code == 200


def test_smoke_separacao_tela_inexistente(login_admin):
    # Rota: /pedidos/<pedido_id>/separar/<loja_id> — sem dados reais → 404
    r = login_admin.get('/motos-assai/pedidos/999999/separar/999999')
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Faturamento
# ---------------------------------------------------------------------------

def test_smoke_faturamento_lista(login_admin):
    r = login_admin.get('/motos-assai/faturamento')
    assert r.status_code == 200


def test_smoke_faturamento_upload_nf(login_admin):
    r = login_admin.get('/motos-assai/faturamento/upload-nf')
    assert r.status_code == 200


def test_smoke_faturamento_nf_detalhe_inexistente(login_admin):
    r = login_admin.get('/motos-assai/faturamento/nfs/999999')
    assert r.status_code == 404


def test_smoke_faturamento_upload_nf_por_separacao(login_admin):
    # Upload NF com separacao_id opcional — rota mostra o form mesmo sem separação existente
    r = login_admin.get('/motos-assai/faturamento/separacao/999999/upload-nf')
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Mapa de lojas
# ---------------------------------------------------------------------------

def test_smoke_lojas_mapa(login_admin):
    r = login_admin.get('/motos-assai/lojas/mapa')
    assert r.status_code == 200


def test_smoke_lojas_geocodar_inexistente(login_admin):
    # POST para loja inexistente -> 404
    r = login_admin.post('/motos-assai/lojas/999999/geocodar',
                         content_type='application/json')
    assert r.status_code == 404
