# 10 — Fiscal

> **Fonte**: `visao_geral_fiscal.htm` (28/03/2022)
> **Links internos**: 55 | **Imagens**: 0

## Sumario

Obrigacoes fiscais integradas: estadual (ICMS/CT-e/MDF-e), federal (PIS/COFINS), municipal (ISS/RPS). Geracao de arquivos nos layouts do fisco.

---

## Configuracoes

### Estadual
| Opcao | Funcao |
|-------|--------|
| [401](../cadastros/401-cadastro-unidades.md) | Inscricao Estadual + dados fiscais + Simples Nacional |
| 410 | Tributacao ICMS (configurado pelo SSW) |
| [903](../cadastros/903-parametros-gerais.md)/Certificado | Certificado digital A1 (PFX + senha) por CNPJ raiz |
| SEFAZ | CNPJ credenciado na UF (verificar [aqui](https://www.cte.fazenda.gov.br)) |
| 920 | CT-es, MDF-es, NF-es — certificados + numeracao fiscal (usar nova serie) |

### Federal
| Opcao | Funcao |
|-------|--------|
| [401](../cadastros/401-cadastro-unidades.md) | Regime de incidencia PIS/COFINS por CNPJ (alteravel so pelo SSW) |
| [903](../cadastros/903-parametros-gerais.md) | Regime de incidencia — visualizacao de todas as unidades |

### Municipal
| Opcao | Funcao |
|-------|--------|
| [401](../cadastros/401-cadastro-unidades.md) | Inscricao Municipal + dados fiscais. Numeracao RPS pelo SSW |
| [402](../cadastros/402-cidades-atendidas.md) | Aliquota de ISS por municipio |

---

## Operacao

### Emissao de documentos
| Opcao | Documento |
|-------|-----------|
| [004](../operacional/004-emissao-ctrcs.md)/005/[006](../operacional/006-emissao-cte-os.md) | Emissao de CT-es (estadual) e RPSs (municipal) |
| [007](../operacional/007-emissao-cte-complementar.md) | Envio CT-es ao SEFAZ para autorizacao |
| [020](../operacional/020-manifesto-carga.md)/[025](../operacional/025-saida-veiculos.md) | Manifestos → geracao de MDF-e (enviados ao SEFAZ) |
| 008 | Impressao de subcontrato nao fiscal |
| [009](../operacional/009-impressao-rps-nfse.md) | Impressao de RPS |
| 014 | Envio de RPS as prefeituras → NFS-e |

---

## Relatorios e Arquivos Fiscais

### Fechamento
| Opcao | Funcao |
|-------|--------|
| **567** | **Fechamento fiscal** — impede alteracao posterior |
| 563 | Relacao CTRCs com impostos (Excel) |

### Estadual
| Opcao | Arquivo/Relatorio |
|-------|-------------------|
| **[512](../fiscal/512-sped-fiscal-icms-ipi.md)** | SPED Fiscal (ICMS/IPI) |
| 433 | Livro de saidas/entradas ICMS (conferencia) |
| 496 | Arquivo SINTEGRA (conferencia) |
| 432 | Cadastro de CFOPs (credito ICMS) |
| 471 | Livro DIFAL do ICMS |
| 514 | Aliquotas Simples Nacional |
| 777 | Livro Eletronico DF (apenas Distrito Federal) |

### Federal
| Opcao | Arquivo/Relatorio |
|-------|-------------------|
| **515** | SPED Contribuicoes (PIS/COFINS) |
| [503](../fiscal/503-manutencao-de-eventos.md) | Configuracao credito PIS/COFINS por Evento |

### Municipal
| Opcao | Arquivo/Relatorio |
|-------|-------------------|
| 633 | Livro saidas/entradas ISS |
| 502 | Arquivo valor total prestacoes por municipio (util para GIA) |

### Complementares
| Opcao | Funcao |
|-------|--------|
| [520](../fiscal/520-substituicao-cte-complementacao-icms.md) | Anulacao e complemento de frete (quando nao possivel alterar CT-e) |
| [736](../logistica/736-carta-correcao-eletronica.md) | Carta de Correcao eletronica (sem alteracao fiscal) |
| [551](../fiscal/551-emissao-nfe.md) | NF-e avulsa (devolucao a fornecedor, venda de imobilizado) |
| 489 | Relacao CTRBs com retencoes (INSS, IR, SEST/SENAT) |
| 531 | Tornar fiscal documentos nao-fiscais emitidos pela [opção 004](../operacional/004-emissao-ctrcs.md)/[006](../operacional/006-emissao-cte-os.md) |
| 151 | Retencoes impostos federais PJ (IR, PIS, COFINS, CSLL) |
| 490 | Comprovante rendimentos pagos e IR retido |
| 599 | DIRF (retencao IR para PF) |

---

## Contexto CarVia

### Opcoes que CarVia usa
| Opcao | Status | Quem Faz |
|-------|--------|----------|
| G04 (Obrigacoes fiscais) | EXTERNO | Escritorio contabil |
| [512](../fiscal/512-sped-fiscal-icms-ipi.md) | EXTERNO | Escritorio contabil (SPED Fiscal) |
| [515](../fiscal/515-sped-contribuicoes.md) | EXTERNO | Escritorio contabil (SPED Contribuicoes) |

> CarVia depende do escritorio contabil para todas as obrigacoes fiscais (SPED, DCTF, GIA).

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| [503](../fiscal/503-manutencao-de-eventos.md) | Manutencao de eventos (credito PIS/COFINS) | Pode ser necessaria para contas a pagar (POP F01) — PEND-06 no CARVIA_STATUS |

### Responsaveis
- **Atual**: Escritorio contabil (terceirizado)
- **Futuro**: Sem plano de internalizacao no momento
