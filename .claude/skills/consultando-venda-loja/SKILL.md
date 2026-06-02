---
name: consultando-venda-loja
description: >-
  Esta skill deve ser usada pelo Agente Lojas HORA quando o usuario pergunta
  sobre VENDAS da loja: "minhas vendas hoje", "venda 9 ja faturou?", "essa moto
  (chassi) foi vendida e por quanto?", "vendas pendentes de NFe", "qual o preco
  de tabela do modelo X a vista?", "um desconto de R$Y nesse modelo bate com a
  tabela?", "qual a margem da venda 9?". READ-only. Respeita escopo de loja via
  <loja_context>.

  USAR QUANDO:
  - "minhas vendas hoje" / "vendas pendentes de NFe"
  - "essa moto foi vendida e por quanto?"
  - "preco de tabela do modelo X a vista/a prazo"
  - "esse desconto bate com a tabela?"
  - "qual a margem da venda 9?"

  NAO USAR PARA:
  - Estoque de motos (usar consultando-estoque-loja)
  - Historico de UM chassi (usar rastreando-chassi)
  - Status de pedido HORA->Motochefe (usar acompanhando-pedido)
  - CRIAR/editar/cancelar venda ou emitir NFe (operacao de WRITE — feita na web, NAO pelo agente)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Venda — Lojas HORA (READ)

Consulta vendas ao consumidor final da Lojas HORA + valida preco/desconto + margem.
READ-only: NUNCA cria, edita, confirma, cancela venda nem emite NFe.

## REGRAS CRITICAS

### 1. RESPEITAR ESCOPO
`<loja_context>` define `--loja-ids`. Operador escopado so ve vendas da sua loja.
Venda com `loja_id` vazio (nao-atribuida) so e visivel ao admin.

### 2. DADO SENSIVEL (margem)
O modo `margem` expoe CUSTO da moto e % de margem (dado da empresa). So sai no
escopo da loja do operador. Nao divulgar custo de vendas de outra loja.

### 3. SEM WRITE
Se o usuario pedir para registrar/cancelar venda ou emitir NFe: explicar que e
operacao de escrita feita na tela web (`/hora/vendas`), nao pelo agente.

## Modos

| Modo | Quando | Args |
|------|--------|------|
| `vendas` (default) | consultar/listar vendas | `--loja-ids` [`--venda-id` `--chassi` `--status` `--somente-pendentes-nfe`] |
| `preco` | preco de tabela + validar desconto | `--modelo-id` (ou `--modelo`) `--forma-pagamento` [`--preco-final`] |
| `margem` | margem de UMA venda | `--venda-id` `--loja-ids` |

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo vendas --loja-ids 2 --somente-pendentes-nfe
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo preco --modelo-id 10 --forma-pagamento A_VISTA --preco-final 12000
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo margem --venda-id 9 --loja-ids 2
```

## Output (resumo)
- `vendas`: `{escopo_aplicado, vendas:[{id,status,loja_apelido,valor_total,nfe_status,divergencias_abertas,itens:[{numero_chassi,modelo,cor,preco_final,desconto_aplicado,desconto_percentual}]}], total_vendas}`
- `preco`: `{modelo_id,preco_tabela,preco_a_vista,preco_a_prazo,fonte, validacao_desconto?:{desconto_rs,desconto_pct,divergencia}}`
- `margem`: `{venda_id,escopo_ok,preview:{venda_total,frete,custo_moto_total,liquido,margem_bruta,margem_pct,tem_custo_faltante}}`

## Skills Relacionadas
| Skill | Quando |
|-------|--------|
| consultando-estoque-loja | estoque de motos |
| rastreando-chassi | historico de 1 chassi |
| acompanhando-pedido | pedido HORA->Motochefe |
