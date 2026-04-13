"""
Modelos do Modulo CarVia
========================

Gestao de frete subcontratado:
- NFs importadas (DANFE PDF / XML NF-e / Manual)
- Operacoes (1 CTe CarVia = N NFs do mesmo cliente/destino)
- Subcontratos (1 por transportadora por operacao)
- Faturas Cliente (CarVia -> cliente)
- Faturas Transportadora (subcontratado -> CarVia)

GAP-20 — DECISAO DE DESIGN: AUSENCIA INTENCIONAL DE DELETE
Nenhuma entidade CarVia possui endpoint de exclusao. Registros sao CANCELADOS
(status='CANCELADO') em vez de deletados. Motivos:
1. Rastreabilidade: historico completo de operacoes para auditoria fiscal
2. Integridade referencial: NFs, CTes, faturas e subcontratos interligados por FKs
3. Documentos fiscais (NF-e, CT-e) nao podem ser apagados por regulamentacao
Se exclusao for necessaria no futuro, implementar soft-delete com campo `excluido_em`.

Split em dominios: documentos, faturas, financeiro, cte_custos, config_moto,
clientes, cotacao, tabelas, admin, frete.
"""

# Documentos (NF, Operacao, Subcontrato)
from app.carvia.models.documentos import (  # noqa: F401
    CarviaNf, CarviaNfItem, CarviaNfVeiculo,
    CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
)

# Faturas (Cliente + Transportadora)
from app.carvia.models.faturas import (  # noqa: F401
    CarviaFaturaCliente, CarviaFaturaClienteItem,
    CarviaFaturaTransportadoraItem, CarviaFaturaTransportadora,
)

# Financeiro (Despesa, Receita, Movimentacao, Extrato, Conciliacao)
from app.carvia.models.financeiro import (  # noqa: F401
    CarviaDespesa, CarviaReceita, CarviaContaMovimentacao,
    CarviaExtratoLinha, CarviaConciliacao,
)

# CTe Complementar + Custos Entrega
from app.carvia.models.cte_custos import (  # noqa: F401
    CarviaCteComplementar, CarviaCustoEntrega, CarviaCustoEntregaAnexo,
    CarviaEmissaoCteComplementar,
)

# Config + Modelos Moto
from app.carvia.models.config_moto import (  # noqa: F401
    CarviaCategoriaMoto, CarviaModeloMoto, CarviaEmpresaCubagem,
    CarviaPrecoCategoriaMoto, CarviaConfig,
)

# Clientes
from app.carvia.models.clientes import (  # noqa: F401
    CarviaCliente, CarviaClienteEndereco,
)

# Cotacao Comercial
from app.carvia.models.cotacao import (  # noqa: F401
    CarviaCotacao, CarviaCotacaoMoto, CarviaPedido, CarviaPedidoItem,
)

# Tabelas de Frete + Grupos Cliente
from app.carvia.models.tabelas import (  # noqa: F401
    CarviaGrupoCliente, CarviaGrupoClienteMembro,
    CarviaTabelaFrete, CarviaCidadeAtendida,
)

# Auditoria Admin
from app.carvia.models.admin import CarviaAdminAudit  # noqa: F401

# Frete + Emissao CTe
from app.carvia.models.frete import CarviaFrete, CarviaEmissaoCte  # noqa: F401

# Comissao
from app.carvia.models.comissao import (  # noqa: F401
    CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
)

# Aprovacao de Subcontratos (tratativa)
from app.carvia.models.aprovacao import (  # noqa: F401
    CarviaAprovacaoSubcontrato, STATUS_APROVACAO,
)

# Conta Corrente Transportadoras
from app.carvia.models.conta_corrente import (  # noqa: F401
    CarviaContaCorrenteTransportadora, TIPOS_MOVIMENTACAO_CC, STATUS_CC,
)


__all__ = [
    # Documentos
    'CarviaNf', 'CarviaNfItem', 'CarviaNfVeiculo',
    'CarviaOperacao', 'CarviaOperacaoNf', 'CarviaSubcontrato',
    # Faturas
    'CarviaFaturaCliente', 'CarviaFaturaClienteItem',
    'CarviaFaturaTransportadoraItem', 'CarviaFaturaTransportadora',
    # Financeiro
    'CarviaDespesa', 'CarviaReceita', 'CarviaContaMovimentacao',
    'CarviaExtratoLinha', 'CarviaConciliacao',
    # CTe/Custos
    'CarviaCteComplementar', 'CarviaCustoEntrega', 'CarviaCustoEntregaAnexo',
    'CarviaEmissaoCteComplementar',
    # Config/Moto
    'CarviaCategoriaMoto', 'CarviaModeloMoto', 'CarviaEmpresaCubagem',
    'CarviaPrecoCategoriaMoto', 'CarviaConfig',
    # Clientes
    'CarviaCliente', 'CarviaClienteEndereco',
    # Cotacao
    'CarviaCotacao', 'CarviaCotacaoMoto', 'CarviaPedido', 'CarviaPedidoItem',
    # Tabelas/Grupos
    'CarviaGrupoCliente', 'CarviaGrupoClienteMembro',
    'CarviaTabelaFrete', 'CarviaCidadeAtendida',
    # Admin
    'CarviaAdminAudit',
    # Frete
    'CarviaFrete', 'CarviaEmissaoCte',
    # Comissao
    'CarviaComissaoFechamento', 'CarviaComissaoFechamentoCte',
    # Aprovacao Subcontratos
    'CarviaAprovacaoSubcontrato', 'STATUS_APROVACAO',
    # Conta Corrente
    'CarviaContaCorrenteTransportadora', 'TIPOS_MOVIMENTACAO_CC', 'STATUS_CC',
]
