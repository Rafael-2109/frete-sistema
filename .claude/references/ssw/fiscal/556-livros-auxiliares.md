# Opcao 556 — Livros Auxiliares (Diario, Saidas, Entradas)

> **Modulo**: Fiscal
> **Paginas de ajuda**: 3 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Gera Livros Auxiliares contabeis: Livro Diario (opcao 545), Livro Auxiliar de Saidas (opcao 556) e Livro Auxiliar de Entradas (opcao 656). Permite escrituracao resumida por lotes conforme legislacao IR, comercial e NBCs, mantendo documentos individualizados disponiveis para verificacao.

## Quando Usar
- Emitir Livro Diario obrigatorio (registro cronologico de lancamentos)
- Gerar Livro Auxiliar de Saidas para formalizar lancamento de lotes de CTRCs/Subcontratos/NFPS
- Gerar Livro Auxiliar de Entradas para documentar lotes de creditos a recuperar (Contas a Pagar)
- Atender exigencias contabeis/fiscais de livros auxiliares
- Obter relacao de documentos que compoem um lote

## Pre-requisitos
- Contabilidade SSW ativada (para lancamento em lotes)
- Regime Debito/Credito (ICMS) ou Nao-Cumulativa (PIS/COFINS) para lotes de entradas
- Multiempresas configurado (opcao 401) se aplicavel
- Termos de Abertura e Encerramento (opcao 634) para Livros Auxiliares

## Campos / Interface

### Livro Diario (Opcao 545)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Periodo contabil | Sim* | Periodo contabil dos lancamentos |
| Periodo de inclusao | Sim* | Periodo em que lancamentos foram incluidos |
| Lote | Nao | Numero do lote contabil |
| Valor | Nao | Filtro alternativo (apenas lancamentos com este valor) |
| Livro Numero | Sim | Numero do Livro Diario |
| Pagina inicial | Sim | Pagina inicial do Livro |

*Informar periodo contabil OU periodo de inclusao (ou ambos)

### Livro Auxiliar de Saidas (Opcao 556)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Empresa | Sim* | Empresa (se multiempresas - opcao 401) |
| Lotes | Sim | Faixa de lotes desejado |
| Selecionar | Sim | C = CTRC, S = Subcontrato, N = NFPS, T = Todos |
| Livro numero | Sim | Numero do Livro Auxiliar |
| Pagina inicial | Sim | Numero da pagina inicial |

*Obrigatorio se multiempresas

### Livro Auxiliar de Entradas (Opcao 656)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Empresa | Sim* | Empresa (se multiempresas - opcao 401) |
| Lotes | Sim | Faixa de lotes desejado |
| Selecionar | Sim | C = CT-e, N = NF-e, T = Todos |
| Livro numero | Sim | Numero do Livro Auxiliar |
| Pagina inicial | Sim | Numero da pagina inicial |

*Obrigatorio se multiempresas

## Fluxo de Uso

### Emitir Livro Diario
1. Acessar opcao 545
2. Informar periodo (contabil OU inclusao, ou ambos)
3. Opcionalmente filtrar por lote ou valor
4. Informar numero do Livro e pagina inicial
5. Gerar Livro Diario
6. Verificar que saidas aparecem apenas como lotes (detalhamento no Livro Auxiliar Saidas)

### Emitir Livro Auxiliar de Saidas
1. Acessar opcao 556
2. Selecionar empresa (se multiempresas)
3. Informar faixa de lotes
4. Escolher tipo de documento (CTRC/Subcontrato/NFPS/Todos)
5. Informar numero do Livro e pagina inicial
6. Gerar Livro Auxiliar
7. Emitir Termos de Abertura e Encerramento (opcao 634)

### Emitir Livro Auxiliar de Entradas
1. Acessar opcao 656
2. Selecionar empresa (se multiempresas)
3. Informar faixa de lotes
4. Escolher tipo de documento (CT-e/NF-e/Todos)
5. Informar numero do Livro e pagina inicial
6. Gerar Livro Auxiliar
7. Emitir Termos de Abertura e Encerramento (opcao 634)

### Consultar Lote de um Documento
- **Saidas (CTRC)**: opcao 101/Fiscal
- **Entradas (despesa)**: opcao 475

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 545 | Livro Diario (obrigatorio) |
| 556 | Livro Auxiliar de Saidas (lotes de CTRCs/Subcontratos/NFPS) |
| 656 | Livro Auxiliar de Entradas (lotes de creditos a recuperar) |
| 634 | Termos de Abertura e Encerramento (obrigatorio para Livros Auxiliares) |
| 401 | Multiempresas, regime tributacao |
| 101 | Consulta lote do CTRC (Fiscal) |
| 475 | Contas a Pagar (consulta lote da despesa, origem lotes de entradas) |
| 512 | SPED FISCAL (apuracao ICMS, compensa creditos lotes) |
| 515 | SPED Contribuicoes (apuracao PIS/COFINS, compensa creditos lotes) |

## Observacoes e Gotchas

### Legislacao e Conceito
- **Base legal**: legislacao IR, legislacao comercial e NBCs admitem escrituracao resumida quando operacoes sao numerosas
- **Requisitos**: usar livros auxiliares para registros individualizados e conservar documentos para verificacao
- **Grande volume**: transporte de cargas gera volume massivo de documentos contabeis

### Livro Diario
- **Obrigatorio**: livro contabil obrigatorio, registra operacoes cronologicamente
- **Todos os lancamentos**: automaticos ou manuais, apresentados dia a dia
- **Saidas resumidas**: devido ao volume, saidas aparecem apenas como lotes (detalhamento no Livro Auxiliar Saidas)
- **Praticidade**: resumo por lotes reduz tamanho do Livro Diario

### Livro Auxiliar de Saidas (Opcao 556)
- **Conceito de lotes**: documentos homogeneos agrupados por tipo, dia e local de expedicao
- **Agrupamento automatico**: ocorre nas primeiras horas do dia seguinte
- **Contabilidade cita lotes**: nao os CTRCs individuais
- **Relacao de CTRCs**: obter nesta opcao 556 (composicao do lote)
- **Lote do CTRC**: consultar na opcao 101/Fiscal
- **Termos obrigatorios**: primeira e ultima pagina devem ter Termo de Abertura e Encerramento (opcao 634)
- **Funcao burocratica**: geracao do Livro NAO altera formacao automatica de lotes, decisao de emitir e do contador

### Livro Auxiliar de Entradas (Opcao 656)
- **Condicoes para lotes**: so ocorre com (1) Contabilidade SSW ativada E (2) Debito/Credito (ICMS) ou Nao-Cumulativa (PIS/COFINS)
- **Contas do Ativo**: lotes de ICMS, PIS e COFINS a recuperar
- **Grande volume**: despesas que geram creditos de impostos (faturas de CTRCs no Contas a Pagar)
- **Um lote por lancamento**: cada Numero de Lancamento (opcao 475) gera um lote (opcao 656)
- **Compensacao**: creditos lancados em Ativo sao compensados com impostos a recolher (Passivo) na apuracao (opcoes 512 e 515)
- **Funcao burocratica**: geracao do Livro NAO altera formacao de lotes, decisao de emitir e do contador

### Praticidade vs Burocracia
- **Lancamentos contabeis**: citam lotes, NAO documentos individuais
- **Livros Auxiliares**: fornecem detalhamento individualizado conforme legislacao
- **Decisao de emitir**: cabe ao contador (funcao burocratica, nao afeta contabilidade)
- **Termos**: Livros Auxiliares devem ter Termos de Abertura e Encerramento (opcao 634)

### Tipos de Documentos
- **Saidas**: C = CTRC, S = Subcontrato, N = NFPS, T = Todos
- **Entradas**: C = CT-e, N = NF-e, T = Todos

### Multiempresas
- Campo "Empresa" obrigatorio se transportadora usa multiempresas (opcao 401)
- Livros separados por empresa
