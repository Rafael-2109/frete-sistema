# 03 — Comercial

> **Fonte**: `visao_geral_comercial.htm` (16/04/2022)
> **Links internos**: 44 | **Imagens**: 1

## Sumario

Gestao comercial: clientes, vendas, tabelas de frete, vendedores e resultado.

---

## 1. Cliente

| Opcao | Funcao |
|-------|--------|
| [483](../cadastros/483-cadastro-clientes.md) | **Principal** — cadastro de caracteristicas, necessidades, exigencias |
| [102](../comercial/102-consulta-ctrc.md) | Consulta da situacao do cliente |
| [056](../relatorios/056-informacoes-gerenciais.md)/[011](../operacional/011-identificacao-volumes.md) | CTRCs atrasados de entrega (avaliacao diaria obrigatoria) |
| 106 | Performance de entregas por cliente |
| [056](../relatorios/056-informacoes-gerenciais.md)/[073](../operacional/073-controle-de-contratacao.md) | Monitoracao de clientes (volume de fretes diario) |
| [925](../cadastros/925-cadastro-usuarios.md) | Acesso direto ao SSW para CNPJs do cliente (opção 426) |

---

## 2. Vendas

| Opcao | Funcao |
|-------|--------|
| [100](../comercial/100-geracao-emails-clientes.md) | Disparador de emails (base de toda transportadora) |
| [001](../operacional/001-cadastro-coletas.md) (Cotacao) | Cotacao de fretes para venda pelo SAC |
| [335](../comercial/335-acoes-vendas.md) | Agenda de vendas |

---

## 3. Fretes — Hierarquia de Calculo

**Prioridade do calculo (1 = maior)**:
1. Frete informado por usuario autorizado ([opção 925](../cadastros/925-cadastro-usuarios.md))
2. Cotacao (opção 002)
3. Tabelas do cliente (vide abaixo)
4. Tabelas por rota ([opção 420](../comercial/417-418-420-tabelas-frete.md))
5. Tabela Generica ([opção 923](../comercial/923-cadastro-tabelas-ntc-generica.md))

### Tipos de Tabela do Cliente

| Opcao | Tipo | Descricao |
|-------|------|-----------|
| [417](../comercial/417-418-420-tabelas-frete.md) | Combinada | Combina peso + valor da mercadoria |
| [418](../comercial/417-418-420-tabelas-frete.md) | Percentual | Basicamente funcao do valor da mercadoria |
| [420](../comercial/417-418-420-tabelas-frete.md) | Por Rota | Tabela generica por rota |
| [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Generica | Tabela fallback da transportadora |
| [427](../comercial/427-resultado-por-cliente.md) | NTC (formato padrao) | Usada para calcular **Desconto sobre NTC** |

### Regras de selecao de tabela
- Escolhida por **origem + destino** da operacao
- Mais especifica tem prioridade (cidade > UF)
- Restricoes adicionais: mercadoria, remetente
- Tetos de uso quando multiplas tabelas atendem

### Gestao de tabelas
| Opcao | Funcao |
|-------|--------|
| [903](../cadastros/903-parametros-gerais.md)/Frete | Datas de vencimento, inativacao, apagamento |
| 518 | Aprovacao centralizada de tabelas |
| 905/906 | Reajustes massificados |
| [903](../cadastros/903-parametros-gerais.md)/Adicional | Reajuste emergencial/temporario |
| [423](../comercial/423-parametros-comerciais-cliente.md) | Reajuste emergencial/temporario (alternativo) |

---

## 4. Vendedor

| Opcao | Funcao |
|-------|--------|
| [415](../comercial/415-gerenciamento-vendedores.md) | Comissionamento por conquista/manutencao de clientes |
| 067 | Comissionamento de supervisores/suporte |
| [056](../relatorios/056-informacoes-gerenciais.md)/300 | Relatorios diarios de acompanhamento |
| [119](../comercial/119-cadastro-clientes-ocorrencias.md) | Relatorios de visitas |
| [397](../comercial/397-metas-clientes-alvo.md) | Metas de vendas e clientes alvo |

---

## 5. Resultado Comercial

| Opcao | Funcao |
|-------|--------|
| [056](../relatorios/056-informacoes-gerenciais.md)/031 | CTRCs com resultado comercial negativo (**avaliacao diaria**) |
| [102](../comercial/102-consulta-ctrc.md)/Resultado | Resultado por CTRC |
| [102](../comercial/102-consulta-ctrc.md)/Geral | Resultado por cliente |
| 449 | Resultado por cliente, faixa de peso e rota |
| 469 | Resultados minimos |
| 400 | Simulacao de tabelas em negociacao |
| [100](../comercial/100-geracao-emails-clientes.md) | Comunicar reajustes por email |

---

## Contexto CarVia

### Opcoes que CarVia usa

| Opcao | POP | Status | Quem Faz |
|-------|-----|--------|----------|
| 002 | B01 | ATIVO | Rafael (transicao para Jessica pendente) |

> Cotacao manual via opcao 002. Jessica deve assumir (PEND-09).

### Opcoes que CarVia NAO usa (mas deveria)

| Opcao | POP | Funcao | Impacto |
|-------|-----|--------|---------|
| [062](../comercial/062-parametros-frete.md) | B02, B03 | Parametros de frete | Rafael nao conhece — simulacao pode calcular preco errado |
| [101](../comercial/101-resultado-ctrc.md) | B04 | Resultado por CTRC | Nunca analisou lucratividade no SSW |
| [056](../relatorios/056-informacoes-gerenciais.md) | B05 | Relatorios gerenciais | Nunca acessou — perdendo visao estrategica |
| [004](../operacional/004-emissao-ctrcs.md) | B02 | Emissao CTRCs (formacao preco) | Usado na emissao mas nao para entender formacao de preco |
| [903](../cadastros/903-parametros-gerais.md) | B02 | Parametros gerais (config frete) | Usado para outros fins mas nao para formacao de preco |

### Responsaveis

- **Atual**: Rafael (cotacao manual)
- **Futuro**: Jessica (cotacao — PEND-09), Rafael (analise comercial, parametros)
