# 09 — Contabilidade

> **Fonte**: `visao_geral_contabilidade.htm` (11/01/2024)
> **Links internos**: 40 | **Imagens**: 0

## Sumario

Contabilidade integrada online. Lancamentos automaticos pela operacao + lancamentos manuais complementares + fechamento mensal.

---

## 2 Modos de Uso

### Contabilidade Externa
- Transmissao via relatorios manuais
- Principal: **Diario Auxiliar de Clientes** (opção 529)
- EDI automatizado possivel para grandes volumes (desenvolvimento sob medida)

### Contabilidade no SSW
- Lancamentos automaticos em tempo real + batch diario
- Lancamentos manuais complementares no fim do mes
- Liberacao pelo Suporte SSW apos configuracao completa
- **Irreversivel**: lancamentos iniciam a partir da liberacao, nao retroage

---

## Configuracoes

| Opcao | Funcao |
|-------|--------|
| [540](../contabilidade/540-plano-de-contas.md) | Plano de Contas (ate 9 niveis: 1=Ativo, 2=Passivo, 5=Resultado) |
| [541](../contabilidade/541-lancamentos-automaticos.md) | Lancamentos automaticos — contas por processo |
| [526](../fiscal/526-planilhas-conferencia-contabil.md) | Lancamentos automaticos por Evento (despesas [opção 475](../financeiro/475-contas-a-pagar.md)) |
| 557 | Historico Padrao (para lancamentos manuais) |
| [904](../cadastros/904-bancos-contas-bancarias.md) | Contas Caixa por unidade contabil |

---

## Processamento Contabil

> Conciliacao diaria → Encerramento mensal → Fechamento → Impedimento de novos lancamentos

| Opcao | Funcao |
|-------|--------|
| [558](../contabilidade/558-lancamentos-manuais.md) | Lancamentos manuais complementares |
| 543 | Consulta de lancamentos (automaticos + manuais) |
| [556](../fiscal/556-livros-auxiliares.md) | Livro Auxiliar de Saidas — agrupa CTRCs em LOTES por caracteristicas contabeis/fiscais |
| 656 | Livro Auxiliar de Entradas — agrupa documentos Contas a Pagar (creditos ICMS/PIS/COFINS) |
| 705 | Contabilizacao da depreciacao (ativo imobilizado [opção 704](../logistica/704-ativo-imobilizado.md)) |
| 634 | Termo de Abertura e Encerramento |
| [559](../contabilidade/559-saldo-contas-fechamento.md) | Saldo das contas + fechamento contabil (impede novos lancamentos) |
| 566 | ARE — Apuracao de Resultado do Exercicio (zera contas resultado, inicia novo periodo) |

---

## Livros e Arquivos

| Opcao | Documento |
|-------|-----------|
| 545 | Livro Diario (ordem cronologica, coluna LANCAMENTO) |
| 549 | Balancete de Verificacao (metodo partidas dobradas) |
| [548](../fiscal/548-ncms-impostos-creditaveis.md) | Livro Razao (metodo partidas dobradas) |
| 561 | Balanco Patrimonial |
| 562 | DRE — Demonstracao do Resultado do Exercicio |
| [534](../fiscal/534-ecd-escrituracao-contabil-digital.md) | **ECD** — Escrituracao Contabil Digital (SPED Contabil) |
| [570](../contabilidade/570-ecf-escrituracao-contabil-fiscal.md) | **ECF** — Escrituracao Contabil-Fiscal (SPED ECF) |
| 564 | SPED FCONT (ate 2015 — substituido por ECD/ECF) |

---

## Fluxo

```
Configuracao                   Processamento                    Arquivos
540 Plano de Contas     →  558 Lancamentos manuais      →  545 Diario
541 Lanc. automaticos   →  543 Consulta lancamentos     →  549 Balancete
526 Lanc. por Evento    →  559 Saldo + Fechamento       →  548 Razao
                        →  566 ARE (fim exercicio)       →  534 ECD
                                                         →  570 ECF
```

---

## Contexto CarVia

### Opcoes que CarVia usa
| Opcao | Status | Quem Faz |
|-------|--------|----------|
| G04 (Contabilidade) | EXTERNO | Escritorio contabil |

> CarVia usa contabilidade **externa** — escritorio contabil executa todos os processos contabeis. Nenhuma opcao deste modulo e operada internamente.

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| — | — | — |

> Nenhuma opcao contabil e prioritaria para a equipe CarVia. Se internalizar contabilidade futuramente, o modulo inteiro (plano de contas, lancamentos, fechamento) se torna relevante.

### Opcoes relacionadas (outros modulos)
| Opcao | Modulo | Relevancia |
|-------|--------|------------|
| [512](../fiscal/512-sped-fiscal-icms-ipi.md) | Fiscal | SPED Fiscal — gerado pelo escritorio contabil |
| [515](../fiscal/515-sped-contribuicoes.md) | Fiscal | SPED Contribuicoes — gerado pelo escritorio contabil |
| 567 | Fiscal | Fechamento fiscal — executado pelo escritorio contabil |

### Responsaveis
- **Atual**: Escritorio contabil (terceirizado)
- **Futuro**: Sem plano de internalizacao no momento
