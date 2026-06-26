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

# Documentos (NF, Operacao, Subcontrato, EnderecoCorrecao, ConferenciaHistorico,
#             VinculoTransferencia triangular)
from app.carvia.models.documentos import (  # noqa: F401
    CarviaNf, CarviaNfItem, CarviaNfVeiculo,
    CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
    CarviaEnderecoCorrecao,
    CarviaConferenciaHistorico,
    CarviaNfVinculoTransferencia,
)

# Faturas (Cliente + Transportadora)
from app.carvia.models.faturas import (  # noqa: F401
    CarviaFaturaCliente, CarviaFaturaClienteItem,
    CarviaFaturaTransportadoraItem, CarviaFaturaTransportadora,
)

# Financeiro (Despesa, Receita, Movimentacao, Extrato, Conciliacao, PreVinculo, HistoricoMatch)
from app.carvia.models.financeiro import (  # noqa: F401
    CarviaDespesa, CarviaReceita, CarviaContaMovimentacao,
    CarviaExtratoLinha, CarviaConciliacao,
    CarviaPreVinculoExtratoCotacao,
    CarviaHistoricoMatchExtrato,
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

# Cotacao Comercial + Cotacao Rapida Publica (lead sem login)
from app.carvia.models.cotacao import (  # noqa: F401
    CarviaCotacao, CarviaCotacaoMoto, CarviaPedido, CarviaPedidoItem,
    CarviaCotacaoRapidaPublica,
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

# Anexos polimorficos (Frete + Subcontrato)
from app.carvia.models.anexos import CarviaAnexo  # noqa: F401

# Comprovantes de Pagamento (N:N com cotacao / NF / CTe CarVia / fatura cliente)
from app.carvia.models.comprovante import (  # noqa: F401
    CarviaComprovantePagamento, CarviaComprovanteVinculo,
)

# Carta de Correção (CCe) — N:N com cotacao / NF
from app.carvia.models.carta_correcao import (  # noqa: F401
    CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo,
)

# Comissao
from app.carvia.models.comissao import (  # noqa: F401
    CarviaComissaoFechamento, CarviaComissaoFechamentoCte, CarviaComissaoAjuste,
)

# Aprovacao de Fretes (tratativa)
from app.carvia.models.aprovacao import (  # noqa: F401
    CarviaAprovacaoFrete, STATUS_APROVACAO,
)

# Conta Corrente Transportadoras
from app.carvia.models.conta_corrente import (  # noqa: F401
    CarviaContaCorrenteTransportadora, TIPOS_MOVIMENTACAO_CC, STATUS_CC,
)

# Coletas ("papel de pao") — agrupa N NFs em 1 veiculo (stream 3)
from app.carvia.models.coleta import (  # noqa: F401
    CarviaColeta, CarviaColetaNf,
    COLETA_STATUS_RASCUNHO, COLETA_STATUS_COLETADA, COLETA_STATUS_CANCELADA,
    COLETA_STATUSES, COLETA_TIPO_DESPESA,
)

# Recebimento por chassi da coleta (stream 4)
from app.carvia.models.coleta_recebimento import (  # noqa: F401
    CarviaColetaRecebimento, CarviaColetaRecebimentoChassi,
    RECEB_STATUS_EM_RECEBIMENTO, RECEB_STATUS_CONCLUIDO, RECEB_STATUS_COM_DIVERGENCIA,
    RECEB_STATUSES, CHASSI_STATUS_VINCULADO, CHASSI_STATUS_ALERTA, normalizar_chassi,
)

# Portal do Cliente — usuario externo (stream 5)
from app.carvia.models.portal import (  # noqa: F401
    CarviaPortalUsuario, CarviaPortalUsuarioCnpj,
    PORTAL_STATUS_PENDENTE, PORTAL_STATUS_ATIVO, PORTAL_STATUS_REJEITADO, PORTAL_STATUS_BLOQUEADO,
    PORTAL_STATUSES, PORTAL_ESCOPO_CNPJ_DIRETO, PORTAL_ESCOPO_CLIENTE_COMERCIAL, PORTAL_ESCOPOS,
)


__all__ = [
    # Documentos
    'CarviaNf', 'CarviaNfItem', 'CarviaNfVeiculo',
    'CarviaOperacao', 'CarviaOperacaoNf', 'CarviaSubcontrato',
    'CarviaEnderecoCorrecao', 'CarviaConferenciaHistorico',
    'CarviaNfVinculoTransferencia',
    # Faturas
    'CarviaFaturaCliente', 'CarviaFaturaClienteItem',
    'CarviaFaturaTransportadoraItem', 'CarviaFaturaTransportadora',
    # Financeiro
    'CarviaDespesa', 'CarviaReceita', 'CarviaContaMovimentacao',
    'CarviaExtratoLinha', 'CarviaConciliacao',
    'CarviaPreVinculoExtratoCotacao',
    'CarviaHistoricoMatchExtrato',
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
    'CarviaCotacaoRapidaPublica',
    # Tabelas/Grupos
    'CarviaGrupoCliente', 'CarviaGrupoClienteMembro',
    'CarviaTabelaFrete', 'CarviaCidadeAtendida',
    # Admin
    'CarviaAdminAudit',
    # Frete
    'CarviaFrete', 'CarviaEmissaoCte',
    # Anexos polimorficos
    'CarviaAnexo',
    # Comprovantes de Pagamento
    'CarviaComprovantePagamento', 'CarviaComprovanteVinculo',
    # Carta de Correção (CCe)
    'CarviaCartaCorrecao', 'CarviaCartaCorrecaoVinculo',
    # Comissao
    'CarviaComissaoFechamento', 'CarviaComissaoFechamentoCte', 'CarviaComissaoAjuste',
    # Aprovacao Fretes
    'CarviaAprovacaoFrete', 'STATUS_APROVACAO',
    # Conta Corrente
    'CarviaContaCorrenteTransportadora', 'TIPOS_MOVIMENTACAO_CC', 'STATUS_CC',
    # Coletas (papel de pao)
    'CarviaColeta', 'CarviaColetaNf',
    'COLETA_STATUS_RASCUNHO', 'COLETA_STATUS_COLETADA', 'COLETA_STATUS_CANCELADA',
    'COLETA_STATUSES', 'COLETA_TIPO_DESPESA',
    # Recebimento por chassi (stream 4)
    'CarviaColetaRecebimento', 'CarviaColetaRecebimentoChassi',
    'RECEB_STATUS_EM_RECEBIMENTO', 'RECEB_STATUS_CONCLUIDO', 'RECEB_STATUS_COM_DIVERGENCIA',
    'RECEB_STATUSES', 'CHASSI_STATUS_VINCULADO', 'CHASSI_STATUS_ALERTA', 'normalizar_chassi',
    # Portal do Cliente (stream 5)
    'CarviaPortalUsuario', 'CarviaPortalUsuarioCnpj',
    'PORTAL_STATUS_PENDENTE', 'PORTAL_STATUS_ATIVO', 'PORTAL_STATUS_REJEITADO', 'PORTAL_STATUS_BLOQUEADO',
    'PORTAL_STATUSES', 'PORTAL_ESCOPO_CNPJ_DIRETO', 'PORTAL_ESCOPO_CLIENTE_COMERCIAL', 'PORTAL_ESCOPOS',
]
