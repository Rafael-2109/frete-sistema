"""
Frente 2-A: o botao "Agendar" na carteira agrupada deve aparecer APENAS para
Atacadao e Assai (Sendas).

O backend expoe `grupo_cliente` por separacao (em
/carteira/api/separacoes-compactas-lote) via helper `_grupo_cliente_por_cnpj`,
que espelha app/carteira/services/agrupamento_service.py: Assai usa o portal
Sendas, logo o codigo de grupo do template e' 'sendas'.

Teste determinista (sem banco): valida o mapeamento CNPJ -> grupo_cliente.
"""
import pytest

from app.carteira.routes.separacoes_api import _grupo_cliente_por_cnpj


@pytest.mark.parametrize(
    "cnpj,esperado",
    [
        ("93209765000100", "atacadao"),  # prefixo Atacadao S.A.
        ("75315333000100", "atacadao"),  # prefixo Atacadao S.A.
        ("00063960000100", "atacadao"),  # prefixo Atacadao S.A.
        ("06057223000100", "sendas"),    # prefixo Assai -> portal Sendas
        ("01157555000100", "outros"),    # Tenda: sem portal automatico nesta tela
        ("11222333000181", "outros"),    # CNPJ qualquer
        (None, "outros"),                # sem CNPJ
        ("", "outros"),                  # CNPJ vazio
    ],
)
def test_grupo_cliente_por_cnpj(cnpj, esperado):
    assert _grupo_cliente_por_cnpj(cnpj) == esperado
