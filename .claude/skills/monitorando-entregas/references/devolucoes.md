# Fluxo de Devoluções

## Visão Geral

Devolução é quando o cliente retorna mercadoria para a Nacom Goya. O fluxo envolve:

1. **Registro da NFD** (NF de Devolução) - recebida do cliente
2. **Abertura de Ocorrência** - para tratativa
3. **Resolução** - decisão sobre o destino da mercadoria

---

## Tabelas Envolvidas

```
entregas_monitoradas
└── nf_devolucao (NFD recebida)
    ├── nf_devolucao_linha (produtos)
    └── ocorrencia_devolucao (tratativa)
```

---

## Status da NFD (nf_devolucao.status)

| Status | Descrição |
|--------|-----------|
| `REGISTRADA` | NFD cadastrada no sistema (default) |
| `VALIDADA` | NFD validada pelo fiscal |
| `SINCRONIZADA` | Sincronizada com Odoo |
| `PROCESSADA` | Processada completamente |
| `CANCELADA` | NFD cancelada |

---

## Status da Ocorrência (ocorrencia_devolucao.status)

| Status | Descrição |
|--------|-----------|
| `ABERTA` | Ocorrência aberta, aguardando tratativa (default) |
| `EM_ANALISE` | Em análise pela área responsável |
| `AGUARDANDO_RETORNO` | Aguardando mercadoria retornar ao CD |
| `RESOLVIDA` | Tratativa concluída |
| `CANCELADA` | Ocorrência cancelada |

---

## Destino da Mercadoria (ocorrencia_devolucao.destino)

| Destino | Descrição |
|---------|-----------|
| `INDEFINIDO` | Ainda não definido (default) |
| `ESTOQUE` | Retorna ao estoque para revenda |
| `DESCARTE` | Será descartada |
| `REPROCESSO` | Vai para reprocessamento |
| `FORNECEDOR` | Devolvida ao fornecedor |

---

## Localização Atual (ocorrencia_devolucao.localizacao_atual)

| Local | Descrição |
|-------|-----------|
| `CLIENTE` | Ainda no cliente (default) |
| `TRANSITO` | Em trânsito de volta |
| `CD` | No Centro de Distribuição |

---

## Categorias de Ocorrência

| Categoria | Subcategorias Comuns |
|-----------|---------------------|
| `QUALIDADE` | Produto avariado, vencido, fora do padrão |
| `COMERCIAL` | Erro de pedido, desistência, preço errado |
| `LOGISTICA` | Atraso, extravio, entrega errada |
| `FISCAL` | Erro de NF, CFOP, impostos |

---

## Responsável pela Tratativa

| Responsável | Quando Aplicar |
|-------------|---------------|
| `INDEFINIDO` | Não definido ainda (default) |
| `QUALIDADE` | Problema com produto |
| `COMERCIAL` | Problema de venda/negociação |
| `LOGISTICA` | Problema de transporte/entrega |
| `FISCAL` | Problema de documentação |

---

## Origem do Problema

| Origem | Descrição |
|--------|-----------|
| `INDEFINIDO` | Não identificada (default) |
| `FABRICACAO` | Erro na produção |
| `ARMAZENAGEM` | Erro no armazém |
| `TRANSPORTE` | Erro no transporte |
| `COMERCIAL` | Erro comercial (venda) |

---

## Momento da Devolução

| Momento | Descrição |
|---------|-----------|
| `INDEFINIDO` | Não identificado (default) |
| `RECUSA` | Cliente recusou na entrega |
| `POS_ENTREGA` | Após aceitar a entrega |

---

## Fluxo Típico

```
1. NFD chega (XML/PDF)
   ↓
2. Sistema registra em nf_devolucao
   ↓
3. Abre ocorrencia_devolucao automaticamente
   ↓
4. Analista classifica (categoria, responsável)
   ↓
5. Define destino da mercadoria
   ↓
6. Acompanha retorno ao CD (se aplicável)
   ↓
7. Resolve ocorrência
```

---

## Queries Úteis

### Devoluções Abertas por Categoria
```sql
SELECT oc.categoria, COUNT(*) as qtd
FROM ocorrencia_devolucao oc
WHERE oc.status = 'ABERTA' AND oc.ativo = true
GROUP BY oc.categoria
ORDER BY qtd DESC;
```

### NFDs Aguardando Retorno
```sql
SELECT nfd.numero_nfd, nfd.nome_emitente, oc.data_previsao_retorno
FROM nf_devolucao nfd
JOIN ocorrencia_devolucao oc ON oc.nf_devolucao_id = nfd.id
WHERE oc.localizacao_atual = 'TRANSITO'
  AND oc.status = 'AGUARDANDO_RETORNO'
ORDER BY oc.data_previsao_retorno;
```

### Devoluções por Responsável
```sql
SELECT oc.responsavel, COUNT(*) as abertas
FROM ocorrencia_devolucao oc
WHERE oc.status IN ('ABERTA', 'EM_ANALISE')
  AND oc.ativo = true
GROUP BY oc.responsavel;
```
