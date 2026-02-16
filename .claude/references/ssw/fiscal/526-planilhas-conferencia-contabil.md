# Opcao 526 — Planilhas para Conferencia Contabil

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Gera relatorio de contas contabeis com base nos documentos existentes no financeiro. Fornece relacao e valor total de documentos fiscais e financeiros emitidos e recebidos para conciliacao contabil. Tambem permite cadastrar conta contabil de credito do evento (opcao 526 na configuracao de eventos).

## Quando Usar
- Conciliar saldo de contas contabeis com saldo da contabilidade
- Obter relacao detalhada de documentos que compoem saldo de conta
- Auditar duplicatas a receber (banco/carteira), cartoes, fretes a vista
- Verificar CT-es disponiveis para faturar
- Consultar contas do passivo pendentes de liquidacao

## Pre-requisitos
- Documentos fiscais e financeiros lancados no sistema
- Contas contabeis configuradas
- Eventos com conta contabil de credito (opcao 526 na configuracao)
- Multiempresas configurado (opcao 401) se aplicavel

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Empresa | Sim* | Empresa a processar (se multiempresa - opcao 401) |
| Conta contabil | Sim | Conta desejada (link mostra contas disponiveis) |
| Data saldo contabil | Sim | Data DDMMAA para relacao de documentos (conciliacao) |

*Obrigatorio se multiempresas

## Fluxo de Uso
1. Acessar opcao 588 (planilhas para conferencia contabil)
2. Selecionar empresa (se multiempresas)
3. Escolher conta contabil no link (lista contas disponiveis)
4. Informar data do saldo contabil (DDMMAA)
5. Executar processamento
6. Aguardar disponibilizacao do arquivo na opcao 156
7. Consultar relatorio gerado na opcao 156

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 588 | Geracao da planilha (opcao atual) |
| 156 | Visualizacao do relatorio gerado |
| 526 | Configuracao conta contabil credito do evento |
| 475 | Contas a Pagar (origem dados contas passivo) |
| 401 | Multiempresas |

## Observacoes e Gotchas

### Contas Disponiveis
Sistema gera planilhas para as seguintes contas:
- **CT-es disponiveis para faturar**: conhecimentos autorizados ainda nao faturados
- **Duplicatas a receber (banco)**: titulos em cobranca bancaria
- **Duplicatas a receber (carteira)**: titulos em carteira propria
- **Cartoes a receber**: valores a receber de cartoes de credito/debito
- **Fretes a vista a receber**: fretes a vista ainda nao liquidados
- **Contas do Passivo**: contas configuradas como credito do evento (opcao 526)

### Contas do Passivo
- Ao selecionar qualquer conta do passivo, sistema gera documentos pendentes de liquidacao do Contas a Pagar (opcao 475)
- Apenas contas informadas como credito do evento na opcao 526 sao apresentadas

### Processamento
- **Processamento por conta**: devido ao grande volume de documentos de transportadoras, processamento e executado por conta contabil individualmente
- **Disponibilizacao assincrona**: arquivo e disponibilizado na opcao 156 apos processamento (nao e imediato)
- **Conciliacao**: conta e considerada conciliada quando saldo bate com saldo da contabilidade

### Configuracao de Eventos
- Opcao 526 tambem e usada na configuracao de eventos para informar conta contabil de credito
- Esta configuracao define quais contas do passivo estarao disponiveis na geracao de planilhas

### Formato de Data
- **Data saldo contabil**: formato DDMMAA (6 digitos)
- Data define ponto de corte para relacao de documentos (inclui documentos ate esta data)
