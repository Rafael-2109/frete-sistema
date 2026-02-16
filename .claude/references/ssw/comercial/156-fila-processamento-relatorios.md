# Opcao 156 — Fila de Processamento de Relatorios

> **Modulo**: Comercial
> **Paginas de ajuda**: 12 paginas consolidadas (referencias cruzadas de outras opcoes)
> **Atualizado em**: 2026-02-14

## Funcao
Fila centralizada para processamento e visualizacao de relatorios gerados por diversas opcoes do sistema. Opcoes que geram relatorios pesados ou demorados (periodos extensos, grande volume de dados) enfileiram o processamento nesta opcao, evitando sobrecarga dos servidores e travamento da operacao.

## Quando Usar
- Visualizar relatorios gerados por outras opcoes (453, 484, 516, 529, 200, 921, 355, 900, 550, 161, 162, 552)
- Acompanhar status de processamento de relatorios em fila
- Baixar relatorios ja processados
- Verificar erros em processamentos de planilhas ou relatorios

## Pre-requisitos
- Relatorio previamente solicitado em outra opcao do sistema
- Numero do arquivo/relatorio (quando aplicavel)
- Processamento concluido (para visualizacao)

## Opcoes que Utilizam a Fila 156

### Opcao 453 — Fretes Expedidos/Recebidos por Unidade
- **Entrada**: CNPJ/raiz/CPF do cliente, periodo de emissao/autorizacao/entrega
- **Saida**: Totais de fretes expedidos e recebidos por unidade

### Opcao 484 — Performance de Cobranças
- **Entrada**: Periodo de emissao das faturas
- **Saida**: Indicadores de performance (liquidacao no prazo, atrasos, juros, descontos, despesas bancarias)
- **Colunas**: Nao liquidada, Ate dia vencimento, Ate 3/10/15/30/60/90/120 dias, Qtde fatura, Valor CTRC, Valor debitos, Valor creditos, Valor final, Juro liquidado, Desconto liquidado, Valor pago, Despesa de banco, Valor prorrogado

### Opcao 516 — Relatorio de Movimento
- **Entrada**: Periodo de emissao, tributacao ICMS (C=com ICMS/ISS, S=sem tributacao, A=ambos)
- **Saida**: CTRCs emitidos com valores de ICMS/ISS

### Opcao 529 — Diario Auxiliar de Clientes
- **Entrada**: Unidade expedidora, periodo de autorizacao (max 31 dias), livro numero, pagina inicial, posicao de clientes (S/N), termo de abertura/fechamento
- **Saida**: Livro Auxiliar com posicao de clientes (SAIDAS e RECEBIMENTOS por dia, SALDOS a pagar)
- **Observacao**: NAO faz parte da Contabilidade SSW (uso externo)

### Opcao 200 — Relacao de Manifestos Operacionais
- **Entrada**: Periodo de emissao (max 31 dias), unidade origem/destino, placa do cavalo, CPF do motorista, tipo de arquivo (T=texto, E=Excel)
- **Saida**: Relacao de Manifestos com conferente carga (opcao 020) e conferente descarga (opcao 064)
- **Fila obrigatoria**: Se inicio do periodo for anterior a 60 dias

### Opcao 921 — Gera Banco de Dados de Tabelas de Fretes
- **Entrada**: Tipo de tabela (C=Combinada, P=Percentual, V=Volumes, M=M3, R=Promocional por Rota), unidade responsavel, ultimo movimento, periodo de inclusao/alteracao, CNPJ cliente
- **Saida**: Planilha detalhando tabelas de fretes cadastradas

### Opcao 355 — Mapas e Arquivos Gerados
- **Entrada**: Numero arquivo averbacao, numero mapa comissao vendedor, numero mapa comissao agencia, arquivo Excel (S/N)
- **Saida**: Relatorios de comissoes de vendedores/unidades e arquivo de averbacao (numeros disponiveis na opcao 392)
- **Observacao**: Transportadora com integracao Webservice com segurados deve usar relatorio 165 (opcao 056)

### Opcao 900 — Gera Banco de Dados de CTRCs/Manifestos
- **Entrada**: Data de emissao do CTRC, data de faturamento, data de liquidacao, data de entrega, situacao (P=pendentes, E=entregues, T=todos)
- **Saida**: Planilha com dados basicos de CTRCs/Manifestos emitidos
- **Observacao**: Sem restricao de periodo (permite desde inicio da operacao SSW)

### Opcao 550 — Composicao dos Fretes dos CTRCs
- **Entrada**: Unidade (E=expedidora, R=receptora, P=responsavel pelo pagador) OU CNPJ pagador, considerar (T=todos, X=todos menos cancelados, C=apenas cancelados), periodo de expedicao, faixa de faturas (com DV)
- **Saida**: Planilha Excel detalhando composicao do frete dos CTRCs, Subcontratos e RPSs

### Opcao 161 — Pesquisa de Ocorrencias em Lote (CTRC Devolucao)
- **Entrada**: CNPJ cliente/grupo (C=cliente, G=grupo opcao 583), base de dados (P=ativa, M=arquivo morto), tipo de dado (N=NF, P=pedido, C=CTRC, E=CT-e), coluna da serie (se NF), coluna, linhas, arquivo CSV (max 5000 linhas)
- **Saida**: Planilha complementada com informacoes adicionais
- **Observacao**: Considera apenas CTRCs normais de devolucao (ignora complementares e cancelados). Bloqueia processamento de outro arquivo enquanto um esta em fila.

### Opcao 162 — Pesquisa de Ocorrencias em Lote (Coleta)
- **Entrada**: CNPJ cliente/grupo (C=cliente, G=grupo opcao 583), tipo de dado (N=NF, P=pedido, C=Coleta), coluna da serie (se NF), coluna, linhas, arquivo CSV (max 5000 linhas)
- **Saida**: Planilha complementada com informacoes adicionais
- **Observacao**: Considera coletas normais e reversas (ignora pre-cadastradas e canceladas). Bloqueia processamento de outro arquivo enquanto um esta em fila.

### Opcao 552 — Gerar Arquivos Fiscais do MDF-e
- **Entrada**: MDF-e inicio/fim (faixa continua, mesmo emissor e serie), tipos de documentos (CT-e PDF, CT-e XML, MDF-e PDF, MDF-e XML)
- **Saida**: Arquivos compactados por tipo de documento (solicitados pela ANTT)
- **Observacao**: Usar com parcimonia em momentos de pouca operacao (sobrecarrega servidores)

## Fluxo de Uso

### Gerar e Visualizar Relatorio
1. Acessar opcao geradora do relatorio (ex: 484, 900, 550)
2. Preencher filtros e parametros
3. Clicar em "Ver Fila" ou equivalente
4. Acompanhar status de processamento na opcao 156
5. Quando concluido, baixar/visualizar relatorio

### Acompanhar Processamento
1. Acessar opcao 156 diretamente
2. Verificar lista de relatorios em fila
3. Aguardar conclusao do processamento
4. Baixar relatorio concluido

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 020 | Emissao de Manifesto Operacional (conferente carga usado no relatorio 200) |
| 048 | Liquidacao de faturas (dados usados em performance de cobranças opcao 484) |
| 056 | Relatorio 165 para conferencia de averbacao (alternativa para opcao 355 com Webservice) |
| 064 | Conclusao de descarga (conferente descarga usado no relatorio 200) |
| 123 | Cadastro de Produtos no Almoxarifado |
| 392 | Mostra numeros de arquivo de averbacao e mapas de comissao (usado na opcao 355) |
| 442 | Lancamento de debitos/creditos em faturas (usado na opcao 484) |
| 444 | Recebimento de arquivo de retorno bancario (juros/descontos considerados na opcao 484) |
| 453 | Fretes Expedidos/Recebidos por Unidade |
| 457 | Lancamento de debitos/creditos e prorrogacao (usado na opcao 484) |
| 460 | Relatorio de ocorrencias do arquivo de retorno (juros/descontos de boletos) |
| 475 | Contas a Pagar |
| 484 | Performance de Cobranças |
| 516 | Relatorio de Movimento |
| 529 | Diario Auxiliar de Clientes |
| 532 | Prorrogacao de vencimentos (usado na opcao 484) |
| 550 | Composicao dos Fretes dos CTRCs |
| 583 | Cadastro de grupos de clientes (usado nas opcoes 161 e 162) |
| 634 | Termo de Abertura e Fechamento de Livros (usado na opcao 529) |
| 900 | Gera Banco de Dados de CTRCs/Manifestos |
| 921 | Gera Banco de Dados de Tabelas de Fretes |
| 161 | Pesquisa de Ocorrencias em Lote (CTRC Devolucao) |
| 162 | Pesquisa de Ocorrencias em Lote (Coleta) |
| 200 | Relacao de Manifestos Operacionais |
| 355 | Mapas e Arquivos Gerados |
| 552 | Gerar Arquivos Fiscais do MDF-e |

## Observacoes e Gotchas
- **Fila obrigatoria para periodos extensos**: Relatorios com periodo anterior a 60 dias (opcao 200) ou sem restricao de periodo (opcao 900) sempre vao para fila
- **Bloqueio de processamento concorrente**: Opcoes 161 e 162 bloqueiam processamento de outro arquivo enquanto um esta sendo processado
- **Limite de linhas em CSV**: Planilhas das opcoes 161 e 162 devem ter no maximo 5000 linhas
- **Sobrecarga de servidores**: Opcao 552 (MDF-e) deve ser usada com parcimonia em momentos de pouca operacao
- **Formato CSV**: Opcoes de importacao de planilhas exigem formato CSV
- **Diario Auxiliar NAO e contabilidade SSW**: Opcao 529 gera livro para uso externo, nao integrado a contabilidade do sistema
- **Juros/descontos de boletos**: Aparecem na opcao 484 apos recebimento do arquivo de retorno (opcao 444)
- **Periodo maximo de 31 dias**: Opcoes 529 e 200 limitam periodo de consulta
- **Tipos de tabela de frete**: C=Combinada, P=Percentual, V=Volumes, M=M3, R=Promocional por Rota (opcao 921)
- **Base de dados**: Opcao 161 permite consultar base ativa (P) ou arquivo morto (M)
- **Faixa continua de MDF-es**: Opcao 552 exige MDF-es do mesmo emissor e mesma serie
- **Ver Fila**: Link presente em diversas opcoes abre diretamente a opcao 156 para acompanhamento

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
