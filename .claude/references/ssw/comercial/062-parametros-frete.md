# Opcao 062 — Parametros de Frete

> **Modulo**: Gestao / Resultado (menu: Gestão > Resultado > 062)
> **Status CarVia**: ACESSIVEL — tela e um relatorio de filtro, NAO configuracao de parametros
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw0189 | Verificado via Playwright em 16/02/2026

## Funcao

**CORRECAO**: A opcao 062 NAO e uma tela de configuracao de parametros como inferido anteriormente. E um **relatorio de parametros de avaliacao de CTRCs** (titulo real: "Relatório de Parâm de Avaliação de CTRCs"). Permite gerar um relatorio filtrado por unidade e estado.

A funcao real e **consultar/imprimir** os parametros que controlam a avaliacao de resultado de CTRCs — NAO e configurar esses parametros.

## Quando Usar

- Consultar parametros de avaliacao de CTRCs configurados para uma unidade
- Gerar relatorio de parametros por estado de destino
- Verificar configuracao atual antes de alterar em outra opcao

## Pre-requisitos

- Acesso ao SSW com usuario da unidade (login normal)

## Campos / Interface — VERIFICADOS

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**

### Tela de Filtros (unica tela)

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **Que partem da unidade** | f2 / id=2 | Opcional | Sigla da unidade (maxlen=3). Link "findfil" abre lookup de filiais |
| **Para o estado** | f3 / id=3 | Opcional | UF destino (maxlen=2) |

### Acoes Disponiveis

| Botao | Acao |
|-------|------|
| **►** (Enviar) | `ajaxEnvia('ENV', 0)` — gera o relatorio |
| **×** (Fechar) | `btnClose()` — fecha a tela |
| **?** (Ajuda) | Abre ajuda SSW |

**Observacao**: A tela e extremamente simples — apenas 2 campos de filtro e um botao de enviar. NAO ha campos de configuracao de desconto maximo, resultado minimo ou custos adicionais. Esses parametros provavelmente sao configurados em OUTRA opcao (903, 469 ou 423).

## Relacao com Opcoes Similares

| Parametro | Opcao 062 (relatorio) | Opcao 469 (por rota) | Opcao 423 (por cliente) | Opcao 903 (geral) |
|-----------|----------------------|---------------------|------------------------|-------------------|
| Desconto maximo | Apenas consulta | Sim — por rota | Sim — por cliente | Sim — geral |
| Resultado minimo | Apenas consulta | Sim — por rota | Nao | Nao |
| Custos adicionais | Apenas consulta | Nao | Nao | Parcial (seguro, GRIS custo) |

**Conclusao**: A opcao 062 APENAS EXIBE parametros configurados em outras opcoes. NAO e ela que configura.

## Fluxo de Uso

1. Acessar opcao 062 (menu: Gestao > Resultado)
2. Opcionalmente filtrar por unidade (f2) e/ou estado (f3)
3. Clicar ► para gerar relatorio
4. Analisar parametros exibidos

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

- **CORRECAO IMPORTANTE**: Opcao 062 NAO e configuracao — e apenas um relatorio de consulta
- **Opcao ACESSIVEL**: Verificado em 16/02/2026 — abre em popup como ssw0189, funciona normalmente
- **Causa raiz de simulacoes incorretas DESCARTADA**: Como 062 e apenas relatorio, os parametros que afetam calculo sao configurados em 903, 469 ou 423
- **Investigar**: Quais opcoes realmente configuram os parametros que 062 exibe (provavelmente 903 ou 469)

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
| **Adocao** | VERIFICADO — tela acessivel (relatorio, nao configuracao) |
| **Bloqueador** | DESCARTADO — opcao 062 e apenas relatorio. Parametros ficam em 903/469/423 |
| **Responsavel futuro** | Rafael |
| **Pendencia** | Identificar onde configurar os parametros que 062 exibe |
| **POPs dependentes** | POP-B02, POP-B03 (referenciam 062 como fonte, mas 062 apenas consulta) |
