# Opcao 437 — Faturamento Manual

> **Modulo**: Contas a Receber / Faturamento (menu: Contas a Receber > Faturamento > 437)
> **Status CarVia**: ATIVO (E02)
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw0114 | Verificado via Playwright em 16/02/2026

## Funcao

Permite faturar CTRCs manualmente, selecionando individualmente quais documentos comporao cada fatura. Diferente da opcao 436 (faturamento geral/automatico) que agrupa CTRCs automaticamente conforme regras do cliente (opcao 384), a opcao 437 da ao operador controle total sobre quais CTRCs incluir em cada fatura. Usada para clientes com tipo de faturamento M (manual) cadastrado na opcao 384.

## Diferenca entre Opcao 437 e Opcao 436

| Aspecto | Opcao 437 (Manual) | Opcao 436 (Geral/Automatico) |
|---------|--------------------|-----------------------------|
| **Selecao de CTRCs** | Operador seleciona individualmente | Sistema agrupa automaticamente por regras |
| **Tipo de cliente** | Tipo = M (manual) na opcao 384 | Tipo = A (automatico) na opcao 384 |
| **Volume** | Ideal para poucos CTRCs ou selecao customizada | Ideal para alto volume com regras padronizadas |
| **Periodicidade** | Por demanda do operador | Conforme periodicidade cadastrada (mensal, quinzenal, etc.) |
| **Flexibilidade** | Alta — pode incluir/excluir CTRCs especificos | Baixa — segue regras rigidamente |
| **Automacao** | Nao automatizavel | Pode ser agendada (opcao 903 as 6:00h) |

## Quando Usar

- Faturar clientes com tipo M (manual) cadastrado na opcao 384
- Selecionar CTRCs especificos para compor uma fatura
- Faturar CTRCs de adicionais (debitos/creditos da opcao 459) separadamente
- Quando o cliente necessita de faturas customizadas (ex: separar por obra, projeto ou pedido)
- Faturar cliente especifico mesmo que esteja configurado como automatico (opcao 436 tambem permite)

## Pre-requisitos

- Usuario em unidade **MTZ** (matriz) — faturamento so pode ser feito na matriz
- CTRCs autorizados pelo SEFAZ (opcao 007)
- Cliente cadastrado com parametros de faturamento (opcao 384)
- Mes contabil nao fechado (opcao 559)
- Recomendado: verificar CTRCs disponiveis na opcao 435 (POP-E01)

## Campos / Interface

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**
>
> Campos reais da tela ssw0114 (24 inputs visiveis):

### Tela Inicial

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **CNPJ do cliente pagador** | Sim | Identifica o cliente para listar CTRCs disponiveis |
| **[CONFIRMAR: Filial de cobranca]** | Nao | Pode filtrar por unidade de cobranca conforme opcao 384 |

### Lista de CTRCs Disponiveis

Apos informar CNPJ, o sistema exibe CTRCs disponiveis para faturamento:

| Coluna | Descricao |
|--------|-----------|
| **Selecionar** | Checkbox para incluir CTRC na fatura |
| **Numero CTRC** | Numero e serie do CTe |
| **Data emissao** | Data de emissao do CTe |
| **Valor frete** | Valor do frete do CTe |
| **Remetente** | Nome do remetente |
| **Destinatario** | Nome do destinatario |
| **[CONFIRMAR: Adicionais]** | Debitos/creditos da opcao 459 associados ao CTe |

### Dados da Fatura

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Data emissao** | Sim | Data de emissao da fatura. Ate 15 dias passados ou 5 dias futuros |
| **Vencimento** | Sim | Calculado conforme prazo na opcao 384, ou informado manualmente |
| **Banco/Carteira** | Nao | Conforme opcao 384. Carteira 999 = cobranca propria (sem boleto) |
| **Observacoes** | Nao | Texto adicional impresso na fatura |

## Fluxo de Uso

1. Trocar para unidade **MTZ** (se necessario)
2. Verificar CTRCs disponiveis na opcao 435 (recomendado — POP-E01)
3. Acessar opcao 437
4. Informar CNPJ do cliente pagador
5. Sistema lista CTRCs disponiveis para faturamento
6. Selecionar CTRCs desejados
7. Verificar total da fatura
8. Preencher/confirmar data de emissao e vencimento
9. Confirmar geracao da fatura
10. Anotar numero da fatura gerada
11. Fatura enviada por e-mail automaticamente (se e-mail cadastrado na opcao 384)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 384 | Define regras de faturamento do cliente (tipo M/A, prazo, banco, e-mail, separacao) |
| 435 | Pre-faturamento — lista CTRCs disponiveis para verificacao antes de faturar |
| 436 | Faturamento geral — alternativa automatica para clientes tipo A |
| 443 | Gera arquivo de remessa de cobranca bancaria |
| 444 | Recepciona arquivo de retorno da cobranca |
| 457 | Manutencao de faturas — consultar, prorrogar, protestar faturas geradas |
| 459 | Relacao de adicionais — debitos e creditos incluidos no faturamento |
| 462 | Bloqueio financeiro — CTRCs bloqueados NAO aparecem para faturamento |
| 509 | Geracao de pre-fatura — pode gerar pre-fatura para posterior confirmacao na 437 |
| 559 | Fechamento contabil — impede faturamento retroativo em mes fechado |

## Observacoes e Gotchas

- **Usuario MTZ obrigatorio**: Faturamento so pode ser executado por usuario logado na unidade MTZ (matriz)
- **Contabilidade fechada**: Nao pode faturar com data de emissao cujo mes esteja fechado (opcao 559)
- **Adicionais (459)**: Verificar se debitos (TDE, diaria, etc.) e creditos (descontos) foram cadastrados na opcao 459 ANTES de faturar. Adicionais nao cadastrados nao aparecem na fatura
- **Bloqueio financeiro (462)**: CTRCs bloqueados nao aparecem na lista de disponiveis
- **Credito maior que fatura**: Fatura nao e gerada se creditos forem maiores que soma dos fretes
- **Separacao de faturas**: Conforme parametro da opcao 384 (CIF/FOB, mercadoria, UF destino, CNPJ, etc.)
- **Envio por e-mail**: Faturas sao enviadas automaticamente por e-mail nas primeiras horas do dia seguinte (se e-mail cadastrado na 384)
- **Arquivo morto**: CTRCs emitidos ha mais de 1 ano podem estar no arquivo morto. Na opcao 435, marcar "Ler morto = S" para localizacao

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturar manualmente — POP completo passo-a-passo para esta opcao |
| POP-E01 | Pre-faturamento — verificar CTRCs antes de faturar |
| POP-E03 | Faturamento automatico — alternativa para clientes tipo A (opcao 436) |
| POP-E04 | Cobranca bancaria — proximo passo apos faturamento |
| POP-E05 | Liquidar fatura — registrar pagamento recebido |
| POP-E06 | Manutencao de faturas — ajustar fatura gerada |
| POP-C03 | CTe complementar — complemento entra no faturamento via 435/437 |
| POP-C04 | Custos extras — adicionais vinculados a CTes que passam pela 437 |
| POP-C06 | Cancelar CTe — cancelamento pode exigir desfaturar via 437 |
| POP-F05 | Bloqueio financeiro — CTRCs bloqueados nao aparecem na 437 |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | ATIVO — CarVia ja fatura manualmente pela opcao 437 |
| **Quem faz hoje** | Rafael |
| **Executor futuro** | Jaqueline |
| **Processo atual** | Rafael fatura → envia para Jessica → Jessica envia ao cliente. Sem boleto, sem cobranca bancaria. Cliente deposita na conta |
| **Gaps** | Sem pre-faturamento (435), sem boleto (444), sem liquidacao (458), sem envio automatico por e-mail |
| **POPs dependentes** | POP-E02 (padronizacao), POP-E01 (pre-faturamento), POP-E04 (boleto) |
