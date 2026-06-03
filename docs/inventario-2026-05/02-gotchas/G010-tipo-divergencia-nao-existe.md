<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G010 — AjusteEstoqueInventario nao tem campo `tipo_divergencia`

> **Papel:** G010 — AjusteEstoqueInventario nao tem campo `tipo_divergencia`.

**Descoberta**: 2026-05-18 sub-piloto bulk 10 produtos (re-execucao apos checkpoint)
**Severidade**: HIGH (bloqueia criacao de ajustes compensatorios — cascateia para F5a_FALHA em todo o chunk)
**Status**: corrigido em `09_executar_onda1_bulk.py:541, 590`

---

## Sintoma

```
ERROR bulk_onda chunk 1: criar_transferencia falhou:
'tipo_divergencia' is an invalid keyword argument for AjusteEstoqueInventario
```

Apos criar picking 317307 (state=draft, 11 moves), execucao falha ao tentar
salvar ajustes compensatorios. Resultado:

1. Picking 317307 fica orfao em `draft` no Odoo (precisa cancel manual)
2. Os 10 ajustes ficam `picking_id_odoo=317307` mas `fase_pipeline=F5a_FALHA`
3. Tentativa subsequente sem cleanup gera novos pickings + duplica problema

## Causa raiz

O script `09_executar_onda1_bulk.py` (logica L12/G009 — compensatorio FIFO)
inventou um campo `tipo_divergencia` na linha 541 que **nao existe no modelo
`AjusteEstoqueInventario`**.

Campos validos do modelo (`app/odoo/models/ajuste_estoque_inventario.py`):
- `ciclo`, `cod_produto`, `tipo_produto`, `company_id`
- `lote_inventariado`, `lote_odoo`, `lote_origem`, `lote_destino`
- `qtd_inventario`, `qtd_odoo`, `qtd_ajuste`, `custo_medio`
- `acao_decidida`, `status`, `fase_pipeline`
- `picking_id_odoo`, `invoice_id_odoo`, `chave_nfe`
- `erro_msg`, `criado_em`, `criado_por`
- (auditoria: `aprovado_em`, `aprovado_por`, `external_id_operacao`, `canary_passou`)

NAO HA `tipo_divergencia`.

## Solucao

Substituir `tipo_divergencia` por marker dentro de `erro_msg` (campo Text livre):

```python
# Antes
ajustes_compensatorios_a_criar.append({
    ...
    'tipo_divergencia': 'COMPENSATORIO_FALTA_ESTOQUE',
    ...
})
novo = AjusteEstoqueInventario(
    ...
    tipo_divergencia=payload_comp['tipo_divergencia'],  # ERRO
    ...
)

# Depois
ajustes_compensatorios_a_criar.append({
    ...
    'tipo_divergencia_marker': 'COMPENSATORIO_FALTA_ESTOQUE',  # marker local
    ...
})
novo = AjusteEstoqueInventario(
    ...
    criado_por=executado_por,
    erro_msg=(
        f'[{payload_comp["tipo_divergencia_marker"]}] '
        f'Compensatorio origem_ajuste={payload_comp["origem_ajuste_id"]}'
    ),
)
```

## Lesson learned

Antes de adicionar kwargs ao construtor de um modelo SQLAlchemy:
1. Ler o `class XYZ(db.Model)` para confirmar campos
2. Adicionar test que faz `Model(campo=valor)` para validar
3. Modelo nao tem `tipo_divergencia` — usar `erro_msg` com prefix bracket

## Recovery dos casos historicos

Picking 317307 + 10 ajustes orfaos foram cancelados/resetados em 2026-05-18:
- Picking 317307: `action_cancel` via XML-RPC (sem invoice/SEFAZ associada)
- DB: `UPDATE ... SET picking_id_odoo=NULL, fase_pipeline=NULL, erro_msg=NULL`

## Ref

- G009 (compensatorio FIFO multi-lote)
- D006 secao L18 (a ser adicionada)
