"""Propagacao da flag `local_cd` (CD de expedicao) da Coleta CarVia para os destinos
EXTERNOS ao CarVia: `embarque_itens` (item CarVia) e `entregas_monitoradas` (origem CARVIA).

## Por que aqui (app/utils)

A FONTE da flag e a Coleta CarVia (`CarviaColeta.local_cd`). O `coleta_service` ja propaga
para os documentos do proprio CarVia (CarviaNf / CarviaPedido / CarviaCotacao). Faltavam dois
destinos que vivem FORA do CarVia e que o modulo NAO pode importar (R1 — `app/carvia/CLAUDE.md`):
`EmbarqueItem` (`app/embarques`) e `EntregaMonitorada` (`app/monitoramento`). Esta funcao mora
em `app/utils` (zona neutra, importavel por todos) e e chamada via lazy import pelo coleta_service.

## Contrato

- **Idempotente**: aplica o mesmo `local_cd` a todos os registros da NF; rodar 2x nao muda nada.
- **Sem commit**: faz UPDATE em massa (`synchronize_session=False`) e deixa o commit para o
  caller (o route do CarVia commita ao fim do fluxo). O mesmo helper e reusado pelo backfill,
  que commita explicitamente.
- **Match do EmbarqueItem**: `separacao_lote_id LIKE 'CARVIA-%'` + `nota_fiscal == numero_nf`
  (mesmo criterio de `sincronizar_entregas_carvia.py`). NUNCA toca itens Nacom.
- **Match da EntregaMonitorada**: `numero_nf == numero_nf` + `origem == 'CARVIA'` (NFs Nacom
  com mesmo numero ficam intactas — colisao tratada igual ao sincronizador de entregas).
"""


def propagar_local_cd_carvia(numero_nf, local_cd):
    """Propaga `local_cd` para o EmbarqueItem CarVia e a EntregaMonitorada CarVia da NF.

    Retorna o total de linhas atualizadas (embarque_itens + entregas_monitoradas).
    No-op (retorna 0) se faltar `numero_nf` ou `local_cd`.
    """
    if not numero_nf or not local_cd:
        return 0

    from app.embarques.models import EmbarqueItem
    from app.monitoramento.models import EntregaMonitorada

    afetados = (
        EmbarqueItem.query
        .filter(
            EmbarqueItem.nota_fiscal == numero_nf,
            EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            EmbarqueItem.local_cd.isnot(None),
            EmbarqueItem.local_cd != local_cd,
        )
        .update({'local_cd': local_cd}, synchronize_session=False)
    )

    afetados += (
        EntregaMonitorada.query
        .filter(
            EntregaMonitorada.numero_nf == numero_nf,
            EntregaMonitorada.origem == 'CARVIA',
            EntregaMonitorada.local_cd != local_cd,
        )
        .update({'local_cd': local_cd}, synchronize_session=False)
    )

    return afetados
