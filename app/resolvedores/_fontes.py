"""Mapeamento fonte -> (Model, campos ORM, filtro_saldo) para as fachadas CLI.

Compartilhado por cidade/grupo/uf/cliente (_cli). Suporta as 3 fontes: carteira, separacao, entregas.
Retorna: (Model, nome_attr_cnpj, nome_attr_nome, nome_attr_uf, nome_attr_cidade, filtro_saldo).
"""


def fonte_cli(fonte: str):
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.monitoramento.models import EntregaMonitorada

    if fonte == 'carteira':
        return (CarteiraPrincipal, 'cnpj_cpf', 'raz_social_red', 'cod_uf', 'nome_cidade',
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0)
    if fonte == 'separacao':
        return (Separacao, 'cnpj_cpf', 'raz_social_red', 'cod_uf', 'nome_cidade',
                (Separacao.sincronizado_nf == False) & (Separacao.qtd_saldo > 0))
    # entregas (default da split)
    return (EntregaMonitorada, 'cnpj_cliente', 'cliente', 'uf', 'municipio',
            EntregaMonitorada.status_finalizacao.is_(None))
