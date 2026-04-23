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
from app.hora.models.venda import HoraVenda, HoraVendaItem
from app.hora.models.devolucao import (
    HoraDevolucaoFornecedor,
    HoraDevolucaoFornecedorItem,
)
from app.hora.models.peca import HoraPecaFaltando, HoraPecaFaltandoFoto
from app.hora.models.permissao import (
    HoraUserPermissao,
    MODULOS_HORA,
    ACOES_HORA,
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
    'HoraDevolucaoFornecedor',
    'HoraDevolucaoFornecedorItem',
    'HoraPecaFaltando',
    'HoraPecaFaltandoFoto',
    'HoraUserPermissao',
    'MODULOS_HORA',
    'ACOES_HORA',
]
