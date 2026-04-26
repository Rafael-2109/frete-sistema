"""Modelos SQLAlchemy do módulo HORA.

Todos prefixados com `hora_` no banco. Ver docs/hora/INVARIANTES.md.
"""
from app.hora.models.cadastro import HoraLoja, HoraModelo, HoraTabelaPreco
from app.hora.models.moto import HoraMoto, HoraMotoEvento
from app.hora.models.compra import (
    HoraPedido,
    HoraPedidoItem,
    HoraNfEntrada,
    HoraNfEntradaItem,
)
from app.hora.models.recebimento import (
    HoraRecebimento,
    HoraRecebimentoConferencia,
    HoraConferenciaDivergencia,
    HoraConferenciaAuditoria,
)
from app.hora.models.venda import HoraVenda, HoraVendaItem, HoraVendaDivergencia
from app.hora.models.devolucao import (
    HoraDevolucaoFornecedor,
    HoraDevolucaoFornecedorItem,
)
from app.hora.models.peca import HoraPecaFaltando, HoraPecaFaltandoFoto
from app.hora.models.permissao import (
    HoraUserPermissao,
    MODULOS_HORA,
    ACOES_HORA,
    MODULOS_SO_VER,
)
from app.hora.models.transferencia import (
    HoraTransferencia,
    HoraTransferenciaItem,
    HoraTransferenciaAuditoria,
)
from app.hora.models.avaria import HoraAvaria, HoraAvariaFoto
from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusToken,
    HoraTagPlusProdutoMap,
    HoraTagPlusFormaPagamentoMap,
    HoraTagPlusNfeEmissao,
    NFE_STATUS_PENDENTE,
    NFE_STATUS_EM_ENVIO,
    NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_APROVADA,
    NFE_STATUS_REJEITADA_LOCAL,
    NFE_STATUS_REJEITADA_SEFAZ,
    NFE_STATUS_ERRO_INFRA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
    NFE_STATUS_CANCELADA,
    NFE_STATUS_VALIDOS,
)

__all__ = [
    'HoraLoja',
    'HoraModelo',
    'HoraTabelaPreco',
    'HoraMoto',
    'HoraMotoEvento',
    'HoraPedido',
    'HoraPedidoItem',
    'HoraNfEntrada',
    'HoraNfEntradaItem',
    'HoraRecebimento',
    'HoraRecebimentoConferencia',
    'HoraConferenciaDivergencia',
    'HoraConferenciaAuditoria',
    'HoraVenda',
    'HoraVendaItem',
    'HoraVendaDivergencia',
    'HoraDevolucaoFornecedor',
    'HoraDevolucaoFornecedorItem',
    'HoraPecaFaltando',
    'HoraPecaFaltandoFoto',
    'HoraUserPermissao',
    'MODULOS_HORA',
    'ACOES_HORA',
    'MODULOS_SO_VER',
    'HoraTransferencia',
    'HoraTransferenciaItem',
    'HoraTransferenciaAuditoria',
    'HoraAvaria',
    'HoraAvariaFoto',
    'HoraTagPlusConta',
    'HoraTagPlusToken',
    'HoraTagPlusProdutoMap',
    'HoraTagPlusFormaPagamentoMap',
    'HoraTagPlusNfeEmissao',
    'NFE_STATUS_PENDENTE',
    'NFE_STATUS_EM_ENVIO',
    'NFE_STATUS_ENVIADA_SEFAZ',
    'NFE_STATUS_APROVADA',
    'NFE_STATUS_REJEITADA_LOCAL',
    'NFE_STATUS_REJEITADA_SEFAZ',
    'NFE_STATUS_ERRO_INFRA',
    'NFE_STATUS_CANCELAMENTO_SOLICITADO',
    'NFE_STATUS_CANCELADA',
    'NFE_STATUS_VALIDOS',
]
