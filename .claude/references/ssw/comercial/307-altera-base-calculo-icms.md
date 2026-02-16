# Opcao 307 — Altera Base de Calculo de ICMS

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Altera a base de calculo de ICMS de CTRCs (Pre-CTRCs) antes do envio ao SEFAZ, sem alterar o valor do frete a receber. Util para casos de Substituicao Tributaria ou reducao de base de calculo conforme legislacao.

## Quando Usar
- Necessario aplicar reducao de base de calculo de ICMS conforme legislacao
- Cliente possui regime especial de Substituicao Tributaria
- Base de calculo do ICMS deve ser diferente do valor total do frete

## Pre-requisitos
- Pre-CTRC gerado (ainda nao enviado ao SEFAZ)
- Conhecimento da legislacao tributaria vigente para calcular base correta
- Para Substituicao Tributaria por cliente: parametrizacao na opcao 388

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC (com DV) | Sim | Serie/numero com DV do CTRC a ter base de calculo reduzida |
| Base de calculo | Sim | Nova base de calculo do frete para calculo do ICMS (calculada conforme legislacao vigente) |

## Fluxo de Uso
1. Informar serie e numero do Pre-CTRC (com DV)
2. Calcular nova base de calculo do ICMS conforme legislacao tributaria
3. Informar nova base de calculo no campo correspondente
4. Salvar alteracao
5. Pre-CTRC e submetido a aprovacao do SEFAZ via opcao 007 com a base alterada
6. Valor do frete a receber permanece inalterado

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 007 | Envio do Pre-CTRC ao SEFAZ para aprovacao (apos alteracao da base) |
| 388 | Parametrizacao de Substituicao Tributaria por cliente (automatiza processo) |

## Observacoes e Gotchas
- **Valor do frete NAO altera**: a alteracao afeta APENAS a base de calculo do ICMS, o frete a receber permanece o mesmo
- **Pre-CTRC**: alteracao deve ser feita ANTES do envio ao SEFAZ (opcao 007)
- **Responsabilidade da transportadora**: calculo da nova base deve obedecer legislacao vigente. SSW nao calcula automaticamente
- **Substituicao Tributaria automatica**: pode ser parametrizada por cliente na opcao 388 (evita alteracao manual a cada CTRC)
- **DV obrigatorio**: informar serie/numero COM digito verificador
- **Legislacao**: reducao de base de calculo e comum em operacoes interestaduais com substituicao tributaria ou regimes especiais (ex: Simples Nacional, ICMS diferido, etc.)
