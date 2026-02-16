# Opção 084 — Informar Pesos e Volumes de NFs (opção 148 — Resultados de Cubagem/Pesagem)

> **Módulo**: Operacional — Controle de Cubagem e Pesagem
> **Páginas de ajuda**: 1 página consolidada (opção 148)
> **Atualizado em**: 2026-02-14

## Função
Permite informar manualmente pesos e volumes de Notas Fiscais. Relatório opção 148 mostra ganhos de fretes proporcionados por cubagens e pesagens realizadas, comparando com dados originais dos pré-CTRCs.

## Quando Usar
- Informar peso e cubagem de NFs manualmente (opção 084)
- Avaliar ganhos de frete após cubagem/pesagem (opção 148)
- Verificar resultados de SSWBalança e cubadoras
- Analisar diferenças entre cubagens declaradas e cubagens reais

## Pré-requisitos
- CTRCs emitidos na unidade
- Cliente configurado para pesagem/cubagem (opção 381 e opção 388/Outros)

## Meios de Cubagem e Pesagem
- **SSWBalança e cubadoras**: Webservice SSW para pesagem/cubagem de NRs (volumes)
- **Opção 084**: Informar pesos e volumes de NFs manualmente
- **Opção 184**: Pesagem e cubagem manual de NRs
- **Opção 185**: Cubagem de volumes com Régua SSW

## Campos / Interface — Opção 148 (Relatório)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade | Sim | Unidade emissora dos pré-CTRCs |
| CNPJ pagador | Não | Cliente pagador (opcional) |
| Período | Sim | Período de emissão dos pré-CTRCs (máximo 31 dias) |

## Colunas do Relatório
| Coluna | Descrição |
|--------|-----------|
| M3_ORIG | m3 informado na emissão do CTRC |
| KG_ORIG | Peso total dos volumes informado na emissão do CTRC |
| VOL | Quantidade de volumes do CTRC |
| NR | Número da etiqueta de identificação do volume |
| HORA | Hora em que a cubagem foi efetuada |
| M3_CUB | M3 de cada volume apurado (cubadora, régua SSW, etc.) |
| M3_CTRC | M3 total do CTRC (soma dos M3_CUB por volume) |
| %CRES | % de crescimento de M3_CTRC em relação ao M3_ORIG |
| KG_BAL | Peso (Kg) apurado pela balança/cubadora para cada volume |
| KG_CTRC | Kg total do CTRC (soma dos KG_BAL por volume) |
| %CRES | % de crescimento do peso em relação ao original |
| CUB_OBRIG | Obrigatoriedade do cliente remetente (opção 381): P=pesagem, C=cubagem, A=ambos |
| CALC_FRT | Uso no cálculo do frete (opção 388/Outros): P=peso, C=cubagem, A=ambos |
| FRT_ORIG | Frete sem considerar novas pesagens/cubagens (original) |
| FRT | Frete final considerando novas pesagens/cubagens |
| % CRES | Crescimento efetivo do frete final em relação ao original |

## Indicador Importante
- **(3)** mostra crescimento dos m3
- **(2)** mostra crescimento dos Kg
- **(1)** mostra crescimento do frete (pode não refletir crescimentos de m3/Kg)

## Fluxo de Uso
1. Cliente configurado para cubagem/pesagem obrigatória (opção 381)
2. Definir se dados são usados no cálculo do frete (opção 388/Outros)
3. Realizar cubagem/pesagem por um dos meios disponíveis
4. Gerar relatório opção 148 para avaliar ganhos de frete
5. Comparar FRT_ORIG vs FRT para verificar crescimento

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 084 | Informar pesos e volumes de NFs manualmente |
| 148 | Relatório de resultados de cubagem e pesagem |
| 184 | Pesagem e cubagem manual de NRs |
| 185 | Cubagem com Régua SSW |
| 381 | Configuração de obrigatoriedade de cubagem/pesagem por cliente |
| 388 | Configuração de uso no cálculo do frete (Outros) |
| 101 | Visualização de dimensões capturadas (DANFEs/NRs) |
| SSWBalança | Webservice SSW para pesagem automática |
| Cubadoras | Webservice SSW para cubagem automática |

## Observações e Gotchas
- **Cubagem obrigatória**: Cliente configurado na opção 381 (pesagem, cubagem ou ambos)
- **Uso no frete**: Configurado na opção 388/Outros (peso, cubagem ou ambos)
- **Cubagem pós-autorização**: Pode ser efetuada após autorização SEFAZ, útil apenas para avaliação (não altera frete)
- **Descarga automática**: Volumes que passam por cubadoras (webservice SSW) têm situação atualizada como descarregado na unidade
- **Crescimento não proporcional**: Crescimento de m3/Kg pode não refletir proporcionalmente no frete
- **Dimensões capturadas**: Disponibilizadas na opção 101 / DANFEs / NRs com indicativo de uso no frete
- **Webservice SSW**: https://ssw.inf.br/ws/sswNrRecepcao/help.html
