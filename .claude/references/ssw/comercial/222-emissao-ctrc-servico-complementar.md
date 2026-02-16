# Opcao 222 — Emissao de CTRC para Cobrar Servico Complementar

> **Modulo**: Comercial
> **Paginas de ajuda**: 3 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Emite CTRC Complementar generico para cobranca de servicos complementares de um CTRC de referencia, informando-se manualmente os valores a serem cobrados. Utilizada quando nao ha tabela automatica cadastrada.

## Quando Usar
- Cobrar servico complementar nao tabelado (sem calculo automatico)
- Emitir CTRC de reembolso de despesas ao cliente
- Cobrar servicos especificos: descarga, veiculo dedicado, estadia (quando nao usar opcoes especializadas)

## Pre-requisitos
- CTRC de referencia autorizado pelo SEFAZ
- Para reembolso de despesas: lancamento previo no Contas a Pagar (opcao 475) com imagem anexada
- Para reembolso com autorizacao previa do cliente: opcao 381 habilitada + e-mail do cliente

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Motivo do complemento | Sim | C=complementar geral, D=descarga, V=veiculo dedicado, E=estadia, R=reembolso |
| Num Lancam despesa | Condicional | Habilitado apenas para motivo R. Numero da despesa lancada na opcao 475 |
| CTRC | Sim | Sigla e numero ou codigo de barras do CTRC de referencia |

### Tela Principal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Parcelas do CTRC Complementar | Sim | Valores a serem cobrados nos respectivos campos (frete, pedagio, GRIS, etc.) |
| Motivo | Sim | Mesmo campo da tela inicial (C/D/V/E/R) |
| Emitir no municipio | Sim | O=cidade origem, D=cidade destino, U=unidade destino |
| Tipo do documento | Sim | C=CTRC, R=RPS. CTRC so pode ser emitido na origem (identico ao CTRC de referencia) |
| Tipo de mercadoria | Nao | Apenas para uso no CTRC Complementar, sem afetar calculo do frete |
| Reembolso ao parceiro | Sim | S=valor repassado ao parceiro (opcao 408), N=nao reembolsado (TOL tera comissao normal) |
| Observacoes | Nao | Texto impresso tambem na DACTE. Motivo e gravado para uso em programas EDI |

## Fluxo de Uso

### Complemento Geral (C/D/V/E)
1. Informar CTRC de referencia e motivo
2. Preencher valores das parcelas a serem cobradas
3. Definir municipio de emissao e tipo de documento
4. Configurar reembolso ao parceiro (S/N)
5. CTRC Complementar e enviado ao SEFAZ via opcao 007

### Reembolso de Despesas (R)
1. Lancar despesa no Contas a Pagar (opcao 475) e anexar imagem justificativa
2. Anotar numero do lancamento
3. Gerar CTRC Complementar via opcao 222, informando numero do lancamento
4. Se cliente exige autorizacao previa (opcao 381): informar e-mail do cliente
5. Solicitacao de autorizacao e enviada automaticamente por e-mail (botao de autorizar com um clique)
6. Alternativamente, usar opcao 201 para informar autorizacao manual
7. Apos autorizacao, pre-CTRC e enviado automaticamente ao SEFAZ (opcao 007)
8. CTRC autorizado fica disponivel para faturamento conforme configuracoes do cliente (opcao 384)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 622 | Alternativa para servicos COM calculo automatico usando tabelas da opcao 423 |
| 423 | Cadastro de tabelas para servicos complementares (usadas pela opcao 622) |
| 475 | Contas a Pagar — lancamento de despesa para reembolso (motivo R) |
| 381 | Configuracao de cliente que exige autorizacao previa para reembolso |
| 201 | Informar autorizacao manual do cliente para reembolso (alternativa ao e-mail) |
| 007 | Envio do CTRC Complementar ao SEFAZ |
| 384 | Configuracoes de faturamento do cliente |
| 408 | Cadastro de parceiros para reembolso |
| 223 | Relacao de CTRCs principais com seus respectivos complementares |
| 015 | CTRC Complementar especializado: Agendamento |
| 016 | CTRC Complementar especializado: Reentrega, Devolucao, Recoleta |
| 089 | CTRC Complementar especializado: Paletizacao |
| 099 | CTRC Complementar especializado: Estadia |
| 199 | CTRC Complementar especializado: Armazenagem |
| 301 | CTRC Complementar para Manifesto |
| 520 | CTRC Complementar especializado: ICMS |

## Observacoes e Gotchas
- **Restricoes de emissao**: emissor, UFs de inicio/fim da prestacao e tipos de servicos do CTRC Complementar devem ser os mesmos do CTRC de referencia
- **Limite**: ate 10 CTRCs Complementares por CTRC de Referencia (conforme Manual de Orientacao do Contribuinte - CT-e)
- **CTRC Simplificado (opcao 004) NAO pode ter CTRC Complementar gerado**
- **Subcontrato complementar**: nao e possivel quando CT-e foi emitido por contratante que tambem usa SSW. Contratante deve emitir primeiro um CT-e Complementar para sobre este emitir-se um Subcontrato
- **RPS - Codigo de Servico**: utilizado codigo 1602 (geral) e 1104 (estadia)
- **Cobranca no CTRC principal**: servicos complementares podem ser cobrados diretamente no CTRC principal conforme exigencias do destinatario (opcoes 483 e 423)
- **Diferenca da opcao 622**: opcao 222 e generica (valores manuais); opcao 622 usa tabelas automaticas (opcao 423)
- **Faturamento de reembolso**: alguns dominios estao ajustados para que o faturamento do CTRC Complementar de Reembolso so ocorra junto com o CTRC de referencia
