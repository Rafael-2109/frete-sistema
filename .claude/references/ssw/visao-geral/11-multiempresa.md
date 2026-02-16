# 11 — Multiempresa

> **Fonte**: `visao_geral_multiempresa.htm` (18/10/2025)
> **Links internos**: 60 | **Imagens**: 0

## Sumario

Permite que um dominio SSW seja usado por diversas empresas (CNPJs raiz diferentes). Operacional integrado; fiscal, financeiro e contabil independentes.

---

## Conceito

- Cada empresa = CNPJ raiz diferente
- Unidades com mesmo CNPJ raiz = mesma empresa
- Apenas o **operacional** e compartilhado
- **Fiscal, financeiro e contabil** sao independentes por empresa

---

## Configuracao

- Equipe SSW transforma dominio em multiempresa
- Informa numero da empresa (1, 2, 3...) e matriz contabil ([opção 401](../cadastros/401-cadastro-unidades.md))
- Novas unidades ([opção 401](../cadastros/401-cadastro-unidades.md)): numero da empresa e automatico pelo CNPJ raiz

---

## Opcoes por Empresa

> Nas opcoes abaixo, sempre deve-se escolher a empresa antes.

### Cadastros
| Opcao | Funcao |
|-------|--------|
| [401](../cadastros/401-cadastro-unidades.md) | Cadastro de Unidades |
| [904](../cadastros/904-bancos-contas-bancarias.md) | Parametros do Banco |
| [026](../relatorios/026-cadastro-veiculos.md) | Cadastro de Veiculos |
| [925](../cadastros/925-cadastro-usuarios.md) | Cadastro de Usuarios |

### Contas a Receber
| Opcao | Funcao |
|-------|--------|
| [435](../financeiro/435-pre-faturamento.md) | CTRCs disponiveis para faturar |
| 459 | Adicionais disponiveis para faturar |
| [509](../fiscal/509-geracao-pre-fatura.md) | Geracao de pre-fatura |
| [436](../financeiro/436-faturamento-geral.md) | Faturamento geral |
| 437 | Faturamento manual |
| 547 | Faturamento manual de DANFEs |
| 465 | Troca de bancos de faturas |
| 451 | Reversao de fretes |
| [442](../financeiro/442-credito-debito-ctrc-fatura.md) | Solicitar credito/debito em CTRC/fatura |
| 527 | Aprovar credito/debito em CTRC/fatura |
| [048](../operacional/048-liquidacao-vista.md) | Liquidacao de CTRC/fatura |
| 452 | Fretes liquidados na unidade |
| 480 | Controle de cobrancas |
| 411 | Relacao CTRCs liquidados |
| 505 | Clientes inadimplentes |

### Contas a Pagar
| Opcao | Funcao |
|-------|--------|
| [476](../financeiro/476-liquidacao-despesas.md) | Liquidacao de despesas |
| 477 | Consulta de despesas |
| 488 | Consulta de despesas parcial |
| 544 | Relatorio de retencoes das despesas |
| 489 | Relacao de CTRBs emitidos |
| 522 | Geracao/recepcao arquivo contas a pagar |
| 677 | Cadastro de produtos |

### Financeiro
| Opcao | Funcao |
|-------|--------|
| [456](../financeiro/456-conta-corrente.md) | Conta corrente de banco |
| [571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md) | Adiantamentos e creditos nao identificados |

### Parcerias
| Opcao | Funcao |
|-------|--------|
| [486](../financeiro/486-conta-corrente-fornecedor.md) | Conta Corrente do Fornecedor |
| 611 | Saldos de CCFs |
| [438](../financeiro/438-repassa-faturas-agencia.md) | Repasse de faturas para agencias |
| 607 | Verificacao de faturas do subcontratado |

### Contabilidade
| Opcao | Funcao |
|-------|--------|
| 568 | Inicializacao contabilidade |
| [558](../contabilidade/558-lancamentos-manuais.md) | Lancamentos manuais |
| 543 | Consulta de lancamentos |
| [559](../contabilidade/559-saldo-contas-fechamento.md) | Saldos das contas e fechamento |
| 549 | Balancete de verificacao |
| 545 | Livro Diario |
| [548](../fiscal/548-ncms-impostos-creditaveis.md) | Livro Razao |
| [556](../fiscal/556-livros-auxiliares.md) | Livro Auxiliar de Saidas |
| 561 | Balanco Patrimonial |
| 564 | SPED FCONT |
| 566 | ARE |
| [534](../fiscal/534-ecd-escrituracao-contabil-digital.md) | ECD |

### Imobilizado
| Opcao | Funcao |
|-------|--------|
| [704](../logistica/704-ativo-imobilizado.md) | Cadastro do imobilizado |
| 705 | Contabilizacao da depreciacao |
| 706 | Realizacao do inventario |

### Fiscal
| Opcao | Funcao |
|-------|--------|
| 567 | Fechamento fiscal |
| [570](../contabilidade/570-ecf-escrituracao-contabil-fiscal.md) | SPED ECF |
| 490 | Comprovante rendimentos pagos e IR retido |
| 151 | Comprovante anual de retencoes |

---

## Contexto CarVia

### Opcoes que CarVia usa
| Opcao | Status | Quem Faz |
|-------|--------|----------|
| — | NAO APLICAVEL | — |

> CarVia e empresa **unica** (1 CNPJ, 1 filial operacional). Modulo multiempresa nao se aplica.

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| — | — | — |

> Nenhuma opcao multiempresa e relevante no cenario atual.

### Responsaveis
- **Atual**: N/A (modulo nao utilizado)
- **Futuro**: Se CarVia abrir filiais ou operar com CNPJs distintos, modulo se torna relevante
