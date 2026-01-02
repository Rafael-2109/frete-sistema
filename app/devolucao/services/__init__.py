"""
Servicos do modulo de devolucoes
================================

Services disponiveis:
- NFDService: Importacao e vinculacao de NFDs do Odoo
- NFDXMLParser: Parsing de XML de NFD
- AIResolverService: Resolucao inteligente via Claude Haiku 4.5
"""

from app.devolucao.services.nfd_service import (
    NFDService,
    get_nfd_service,
    importar_nfds_odoo,
)

from app.devolucao.services.nfd_xml_parser import (
    NFDXMLParser,
    extrair_nfs_referenciadas,
    extrair_itens_nfd,
    parsear_nfd_completo,
)

from app.devolucao.services.ai_resolver_service import (
    AIResolverService,
    get_ai_resolver,
    ResultadoResolucaoProduto,
    ResultadoExtracaoObservacao,
    ResultadoNormalizacaoUnidade,
    ProdutoSugestao,
)

__all__ = [
    # NFD Service
    'NFDService',
    'get_nfd_service',
    'importar_nfds_odoo',

    # XML Parser
    'NFDXMLParser',
    'extrair_nfs_referenciadas',
    'extrair_itens_nfd',
    'parsear_nfd_completo',

    # AI Resolver (Claude Haiku 4.5)
    'AIResolverService',
    'get_ai_resolver',
    'ResultadoResolucaoProduto',
    'ResultadoExtracaoObservacao',
    'ResultadoNormalizacaoUnidade',
    'ProdutoSugestao',
]
