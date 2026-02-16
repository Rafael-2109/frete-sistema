# Opcao 435 — CTRCs Disponiveis para Faturamento

> **Modulo**: Financeiro
> **URL ajuda**: `/ajuda/ssw0103.htm`
> **Atualizado em**: 2026-02-15

## Funcao

Relaciona os CTRCs disponiveis para faturamento e aponta ajustes necessarios, principalmente a existencia do e-mail do cliente devidamente cadastrado.

## Quando usar

- Antes do faturamento (opcao 436/437), para verificar quais CTRCs estao prontos
- Identificar clientes sem e-mail cadastrado (bloqueio de envio de fatura)
- Conferir parametros de faturamento por cliente (tipo, periodicidade, separacao)
- Gerar relatorio Excel dos CTRCs disponiveis

## Pre-requisitos

- CTRCs autorizados pelo SEFAZ (opcao 007)
- Cliente cadastrado com dados de faturamento (opcao 384)

## Campos / Interface

### Filtros de Selecao

| Campo | Descricao |
|-------|-----------|
| CTRCs autorizados ate | Data limite de autorizacao SEFAZ |
| Sigla das filiais | Filtro por unidade |
| CNPJ Cliente / CNPJ Grupo | Cliente individual ou grupo (opcao 583). Escolher C ou O |
| Banco | Banco de cobranca cadastrado no cliente (opcao 384). Carteira propria = 999 |
| Valor minimo do CTRC (R$) | Valor minimo do CTRC para inclusao |
| Valor minimo fatura | Valor minimo da fatura resultante |
| Situacao do CTRC | **I** = impressos, **E** = comprovantes arquivados (opcao 428), **B** = entregues/baixados |
| Periodicidade faturamento | Conforme cadastro cliente (opcao 384): **M** = mensal, **Q** = quinzenal, **D** = decenal, **S** = semanal, **I** = diario, **T** = todos |
| Relatorio lista | Tipo de listagem |
| Considerar bloq. financeiro | Incluir CTRCs bloqueados pela opcao 462 |
| Considerar CTRCs a vista | **Cuidado**: normalmente ja estao sendo cobrados na entrega |
| Classificado por | Criterio de ordenacao |
| Gerar em Excel | Exporta resultado conforme filtros |
| Ler morto | **S** = pesquisa CTRCs no arquivo morto (emitidos ha mais de 1 ano) |

### Colunas do Relatorio

| Coluna | Descricao |
|--------|-----------|
| EM | Numero da empresa (multiempresa, opcao 401) |
| TIP | Tipo faturamento: **A** = automatico, **M** = manual |
| PER | Periodicidade: **M** = mensal, **Q** = quinzenal, **D** = decenal, **S** = semanal, **I** = diario |
| FIL_COB | Unidade de cobranca |
| ENT | Entregador da fatura (opcao 384) |
| PRAZ | Prazo de vencimento da fatura |
| BAN/CART | Banco e carteira da cobranca bancaria |
| CIDADE | Cidade de cobranca do cliente |
| SEPARA FAT | Quebra de faturas: **1** = CIF/FOB/TERC, **2** = COD MERCAD, **3** = COMPLEM, **4** = ICMS/ISS, **5** = ADIC/ABAT, **6** = UNID EXPED, **7** = UF DESTINO, **8** = FOB DIRIG, **9** = PJ/PF, **C** = CIDADE, **K** = KG, **J** = CNPJ (opcao 384) |
| BLOQUEADO | Frete bloqueado para faturamento (opcao 462) |
| ARQUIVO MORTO | Necessario retornar do arquivo morto para faturar (opcao 101) |
| ENV | **X** = fatura enviada por e-mail |
| E-MAILS | E-mails cadastrados para envio |

## Fluxo de Uso

1. Acessar opcao 435
2. Preencher filtros (data autorizacao, filiais, periodicidade)
3. Gerar relatorio
4. Verificar coluna ENV e E-MAILS — clientes sem e-mail nao receberao fatura
5. Verificar coluna BLOQUEADO — resolver pendencias antes de faturar
6. Se necessario, gerar Excel para analise detalhada
7. Prosseguir para opcao 436 (faturamento geral) ou 437 (faturamento manual)

## Integracao com outras opcoes

| Opcao | Relacao |
|-------|---------|
| 384 | Cadastro do cliente/faturamento — parametros TIP, PER, BAN, CART, SEPARA FAT, ENT, PRAZ |
| 436 | Faturamento Geral — proximo passo (automatico) |
| 437 | Faturamento Manual — proximo passo (manual) |
| 459 | Relacao de adicionais (debitos/creditos) disponiveis para faturar |
| 462 | Bloqueio financeiro de CTRCs |
| 428 | Comprovantes de entrega arquivados |
| 583 | Grupos de clientes (filtro CNPJ Grupo) |
| 401 | Configuracao multiempresa |
| 101 | Retornar CTRCs do arquivo morto |
| 039 | Ocorrencias operacionais tipo BAIXA (consideradas disponiveis) |

## Observacoes / Gotchas

- CTRCs com serie **999** NAO sao considerados disponiveis
- CTRCs com ocorrencias tipo **BAIXA** (opcao 039, "so para efeito de frete") SAO listados como disponiveis
- **CTRCs a vista**: cuidado ao marcar este filtro — normalmente ja estao sendo cobrados na entrega da mercadoria
- **Arquivo morto**: CTRCs com mais de 1 ano precisam ser retornados do morto (opcao 101) antes de poderem ser faturados
- A maioria dos parametros do relatorio vem do cadastro do cliente na **opcao 384** — ajustar la primeiro

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C03](../pops/POP-C03-emitir-cte-complementar.md) | Emitir cte complementar |
| [POP-C04](../pops/POP-C04-custos-extras.md) | Custos extras |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E02](../pops/POP-E02-faturar-manualmente.md) | Faturar manualmente |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
| [POP-F05](../pops/POP-F05-bloqueio-financeiro-ctrc.md) | Bloqueio financeiro ctrc |
