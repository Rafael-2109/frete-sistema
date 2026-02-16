# Opcao 221 — Geracao em Lote de CTRCs Complementares

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Emite automaticamente CTRCs Complementares para fretes emitidos a menor, quando o peso de calculo aumenta devido a novas pesagens e cubagens realizadas apos a autorizacao do CTRC original.

## Quando Usar
- Cliente possui CTRCs autorizados nos ultimos 90 dias que tiveram aumento no peso de calculo
- Necessario cobrar frete complementar devido a reajuste de peso
- Frete complementar atinge valor minimo parametrizado

## Pre-requisitos
- Opcao 388: cliente deve estar com "Usa da cubadora/balanca" diferente de "N"
- CTRCs originais devem estar autorizados pelo SEFAZ
- Periodo de busca: ultimos 90 dias

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ pagador | Sim | Cliente para o qual os CTRCs Complementares serao gerados automaticamente |
| Data autorizacao CTRC (periodo) | Sim | Seleciona CTRCs autorizados no periodo (ultimos 90 dias) para verificacao de frete complementar |
| Frete minimo (R$) | Sim | Valor minimo que o frete complementar deve ter para que o CTRC Complementar seja emitido |
| Ver fila | Nao | Botao que redireciona para opcao 156 (relacao de CTRCs Complementares gerados) |

## Fluxo de Uso
1. Informar CNPJ do cliente pagador (deve ter cubadora/balanca habilitada na opcao 388)
2. Definir periodo de data de autorizacao dos CTRCs originais (ate 90 dias atras)
3. Parametrizar valor minimo de frete complementar para emissao
4. Executar geracao automatica
5. CTRCs Complementares sao enviados para autorizacao SEFAZ via opcao 007
6. Consultar relacao de CTRCs gerados na opcao 156

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 388 | Cadastro do cliente — campo "Usa da cubadora/balanca" deve estar diferente de "N" |
| 007 | Envio dos CTRCs Complementares para autorizacao do SEFAZ |
| 156 | Consulta da relacao de CTRCs Complementares gerados |
| 520 | Alternativa para complementar APENAS imposto (ICMS ou ISS) do CTRC, sem mexer no frete |

## Observacoes e Gotchas
- **CTRCs Complementares sao emitidos APENAS para efeito de frete** (nao alteram impostos)
- **Restricoes de emissao**: emissor, UFs de inicio/fim da prestacao e tipos de servicos do CTRC Complementar devem ser os mesmos do CTRC de referencia
- **Diferenca da opcao 520**: esta opcao 221 complementa FRETE devido a peso; opcao 520 complementa IMPOSTO (ICMS/ISS)
- **Periodo limitado**: apenas CTRCs autorizados nos ultimos 90 dias podem ser complementados
- **Frete minimo evita emissoes desnecessarias**: valores muito baixos de complemento podem nao justificar a emissao do documento fiscal
