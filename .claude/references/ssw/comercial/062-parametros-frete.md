# Opcao 062 — Parametros de Frete

> **Modulo**: Comercial
> **Status CarVia**: NAO CONHECE (opcao nunca explorada pela CarVia)
> **Atualizado em**: 2026-02-16

## Funcao

Configura parametros que controlam o calculo de frete no SSW, incluindo desconto maximo permitido, resultado comercial minimo e custos adicionais aplicados na formacao de preco. Esta opcao e referenciada pela opcao 101 (Resultado CTRC) como fonte de parametros de calculo de resultado.

## Quando Usar

- Setup inicial da transportadora (configuracao base de calculo de frete)
- Simulacao (opcao 004) ou cotacao (opcao 002) retornando valores inesperados
- Ajuste de limites de desconto para negociacao comercial
- Configuracao de custos adicionais que afetam o resultado comercial
- Revisao periodica de parametros de precificacao

## Pre-requisitos

- Acesso com usuario com permissao para configuracao comercial [CONFIRMAR: usuario MTZ necessario?]
- Tabelas de frete cadastradas e ativas (opcoes 417/418/420)
- Custos/comissoes de subcontratacao cadastrados (opcao 408)

## Campos / Interface

> **[CONFIRMAR]**: A opcao 062 NAO possui documentacao dedicada nos arquivos de ajuda SSW coletados. Os campos abaixo sao baseados em referencias indiretas encontradas na documentacao da opcao 101 (Resultado CTRC) e nos POPs B02 e B03. **Todos os campos devem ser validados no ambiente SSW real.**

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Desconto maximo** | [CONFIRMAR] | Percentual maximo de desconto permitido sobre o preco de tabela. Referenciado na opcao 101. Pode complementar ou substituir limites da opcao 469 (por rota) |
| **Resultado comercial minimo** | [CONFIRMAR] | Percentual minimo de lucro exigido para aprovacao do frete. Referenciado na opcao 101. Pode complementar ou substituir limites da opcao 469 (por rota) |
| **Custos adicionais** | [CONFIRMAR] | Custos extras que afetam o calculo do resultado comercial. Mencionados no CATALOGO_POPS como funcao da opcao 062 |
| **[CONFIRMAR: outros campos]** | — | Podem existir campos adicionais nao referenciados na documentacao disponivel |

## Relacao com Opcoes Similares

A opcao 062 pode ter sobreposicao de funcionalidade com outras opcoes de parametrizacao. A hierarquia de prioridade **precisa ser confirmada**:

| Parametro | Opcao 062 | Opcao 469 (por rota) | Opcao 423 (por cliente) | Opcao 903 (geral) |
|-----------|-----------|---------------------|------------------------|-------------------|
| Desconto maximo | [CONFIRMAR] | Sim — por rota | Sim — por cliente | Sim — geral |
| Resultado minimo | [CONFIRMAR] | Sim — por rota | Nao | Nao |
| Custos adicionais | [CONFIRMAR] | Nao | Nao | Parcial (seguro, GRIS custo) |

**Hipotese**: A opcao 062 pode conter parametros GLOBAIS que a 469 (por rota) e a 423 (por cliente) sobreescrevem com valores especificos. Se estiver vazia ou com valores incorretos, o calculo pode falhar ou produzir resultados inesperados.

## Fluxo de Uso

1. Acessar opcao 062 [CONFIRMAR: caminho do menu]
2. Verificar campos disponiveis e valores atuais
3. Configurar desconto maximo (se campo existir)
4. Configurar resultado comercial minimo (se campo existir)
5. Configurar custos adicionais (se campo existir)
6. Gravar configuracao
7. Testar: simular frete na opcao 004 e verificar se resultado esta coerente

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | Emissao de CTRCs — usa parametros da 062 no calculo de simulacao (confirmado: POP-B02:14,21-26) |
| 002 | Cotacao de frete — usa limites da 062 para desconto e resultado minimo (confirmado: POP-B02:21-26 + POP-B03:22) |
| 101 | Resultado por CTRC — referencia explicitamente a opcao 062 para desconto maximo e resultado minimo |
| 417/418/420 | Tabelas de frete — definem valores base; 062 define limites sobre esses valores |
| 408 | Custos/comissoes — alimentam resultado comercial junto com parametros da 062 |
| 469 | Limites de cotacao por rota — pode complementar ou ser complementada pela 062 |
| 423 | Parametros comerciais por cliente — desconto maximo por cliente pode sobrescrever 062 |
| 903 | Parametros gerais — cubagem, seguro, GRIS; 062 pode complementar com outros parametros |

## Observacoes e Gotchas

- **PRIORIDADE ALTA para CarVia**: Esta opcao e identificada como possivel causa raiz de simulacoes incorretas na opcao 004 (POP-B02, problema recorrente)
- **Rafael NAO CONHECE esta opcao**: Nunca acessou. Investigar com prioridade (PEND-07 em CARVIA_STATUS.md)
- **Sem documentacao de ajuda SSW**: Diferente de outras opcoes, a 062 nao tem paginas de ajuda coletadas. Confirmar funcionalidade diretamente no sistema
- **[CONFIRMAR]**: Verificar se opcao 062 esta acessivel na instalacao atual da CarVia e quais campos estao disponiveis
- **Risco se nao configurada**: Calculo de frete pode usar defaults que nao refletem a realidade comercial da CarVia, resultando em precos incorretos

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-B02 | Formacao de preco — documenta componentes do calculo que a 062 parametriza |
| POP-B03 | Parametros de frete — POP dedicado a configurar esta e outras opcoes de parametrizacao |
| POP-B01 | Cotar frete — cotacao usa limites configurados aqui |
| POP-B04 | Resultado por CTRC — resultado e calculado com parametros da 062 |
| POP-B05 | Relatorios gerenciais — RC Minimo da 062 determina relatorio 031 |
| POP-C01 | Emitir CTe fracionado — verificacao de frete usa parametros da 062 |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | NAO CONHECE |
| **Bloqueador** | Opcao 062 desconhecida — pode ser causa de simulacao incorreta |
| **Responsavel futuro** | Rafael |
| **Pendencia** | PEND-07 — Descobrir e configurar opcao 062 |
| **POPs dependentes** | POP-B02, POP-B03 |
