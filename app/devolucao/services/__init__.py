"""
Servicos do modulo de devolucoes
================================

Services disponiveis:
- NFDService: Importacao e vinculacao de NFDs do Odoo
- ReversaoService: Importacao de NFs revertidas do Odoo
- NFDXMLParser: Parsing de XML de NFD
- AIResolverService: Resolucao inteligente via Claude Haiku 4.5
"""

from app.devolucao.services.nfd_service import (
    NFDService,
    get_nfd_service,
    importar_nfds_odoo,
)

from app.devolucao.services.reversao_service import (
    ReversaoService,
    get_reversao_service,
    importar_reversoes_odoo,
)

from app.devolucao.services.monitoramento_sync_service import (
    MonitoramentoSyncService,
    get_monitoramento_sync_service,
    sincronizar_monitoramento,
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

    # Reversao Service
    'ReversaoService',
    'get_reversao_service',
    'importar_reversoes_odoo',

    # Monitoramento Sync Service
    'MonitoramentoSyncService',
    'get_monitoramento_sync_service',
    'sincronizar_monitoramento',

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
