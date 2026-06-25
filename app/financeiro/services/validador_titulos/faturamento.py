"""
Fonte de faturamento do Validador de Titulos x Bancos.

O faturamento (notas emitidas) vem da tabela `contas_a_receber`, ja sincronizada
do Odoo — NAO e enviado por upload. Cada titulo vira um dict com a chave NF-PARC,
para os comparativos "faturado sem boleto" e "boleto sem nota".

`montar_faturamento` (puro) transforma registros em dicts; `carregar_faturamento`
consulta o banco com filtros.
"""

from typing import List, Optional

from app.financeiro.services.validador_titulos.normalizador import montar_nf_parc_partes

# Empresas: 1=FB, 2=SC, 3=CD. Default = FB + CD (as que emitem boleto, conforme planilha).
EMPRESAS_PADRAO = (1, 3)


def montar_faturamento(registros) -> List[dict]:
    """Transforma registros de ContasAReceber em dicts com a chave NF-PARC."""
    faturamento = []
    for r in registros:
        faturamento.append({
            "nf_parc": montar_nf_parc_partes(r.titulo_nf, r.parcela),
            "empresa": getattr(r, "empresa", None),
            "titulo_nf": r.titulo_nf,
            "parcela": r.parcela,
            "cnpj": getattr(r, "cnpj", None),
            "cliente": getattr(r, "raz_social", None),
            "uf": getattr(r, "uf_cliente", None),
            "vencimento": getattr(r, "vencimento", None),
            "valor": getattr(r, "valor_original", None),
            "tipo_titulo": getattr(r, "tipo_titulo", None),
            "parcela_paga": getattr(r, "parcela_paga", None),
        })
    return faturamento


def carregar_faturamento(
    empresas: Optional[tuple] = EMPRESAS_PADRAO,
    somente_em_aberto: bool = True,
    vencimento_de=None,
    vencimento_ate=None,
) -> List[dict]:
    """
    Consulta `contas_a_receber` e devolve o faturamento como lista de dicts.

    Args:
        empresas: tupla de codigos de empresa (1=FB, 2=SC, 3=CD). None = todas.
        somente_em_aberto: se True, apenas parcelas nao pagas (boleto ativo).
        vencimento_de / vencimento_ate: recorte opcional por data de vencimento.
    """
    from app.financeiro.models import ContasAReceber

    query = ContasAReceber.query
    if empresas:
        query = query.filter(ContasAReceber.empresa.in_(tuple(empresas)))
    if somente_em_aberto:
        query = query.filter(ContasAReceber.parcela_paga.is_(False))
    if vencimento_de:
        query = query.filter(ContasAReceber.vencimento >= vencimento_de)
    if vencimento_ate:
        query = query.filter(ContasAReceber.vencimento <= vencimento_ate)

    return montar_faturamento(query.all())
