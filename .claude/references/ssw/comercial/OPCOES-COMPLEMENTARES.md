# Opcoes Complementares — Modulo Comercial

> **Modulo**: Comercial
> **Opcoes**: 428, 431, 433, 435, 469, 518
> **Atualizado em**: 2026-02-14

Este documento consolida opcoes complementares do modulo comercial do SSW que possuem documentacao mais simples ou sao suporte a processos principais.

---

## Opcao 428 — Recepcao Capa Remessa Comprovantes

### Funcao
Recebe Capa de Remessa de Comprovantes enviada pela subcontratada (que usa seu proprio SSW). Credita comissao na Conta Corrente do Fornecedor (CCF) da subcontratada.

### Quando Usar
- Subcontratado envia comprovantes de entrega fisicos
- Creditar comissao de recepcao via Capa (forma C)
- Arquivar comprovantes de entrega

### Campos Principais
- **CNPJ subcontratado**: fornecedor emitente
- **Numero Capa**: numero da capa enviada
- **Lista CTRCs**: comprovantes recebidos

### Integracao
- **401**: Unidade - config "Arquiva Comprovante de Entregas"
- **408**: Comissao unidades - forma C (Capa) de credito CCF
- **486**: Conta Corrente Fornecedor - credito comissao
- **607**: Conferencia fatura subcontratado

### Gotchas
- **Capa TEM PRIORIDADE** sobre Mapa/Fatura para credito CCF
- Subcontratado DEVE usar seu proprio SSW
- Apenas unidade MTZ ou configurada (opcao 401) pode arquivar

---

## Opcao 431 — Unidades do Mesmo Armazem

### Funcao
Agrupa unidades que compartilham o mesmo armazem fisico. Permite processos integrados (comissionamento, romaneio, OS) reconhecerem CTRCs de todas unidades do grupo.

### Quando Usar
- Varias unidades operam no mesmo local fisico
- Emissao de romaneio/OS unificado
- Demonstrativo remuneracao consolidado

### Campos Principais
- **Unidade principal**: unidade que centraliza operacao
- **Unidades do grupo**: lista de unidades no mesmo armazem

### Integracao
- **075**: Emissao OS - reconhece CTRCs do grupo
- **076**: Demonstrativo remuneracao - consolida grupo
- **401**: Cadastro unidades
- **409**: Remuneracao veiculos - processos no grupo

### Gotchas
- Todo processo (opcao 409, 076, 075) deve ser executado na MESMA unidade
- CTRCs de unidades do grupo sao reconhecidos automaticamente
- Util para hubs com multiplas operacoes/CNPJs

---

## Opcao 433 — [Consulta/Relatorio Especifico]

**Nota**: Arquivo consolidado nao disponivel. Consultar ajuda SSW para detalhes.

---

## Opcao 435 — [Consulta/Relatorio Especifico]

**Nota**: Arquivo consolidado nao disponivel. Consultar ajuda SSW para detalhes.

---

## Opcao 469 — [Impressao/Relatorio]

**Nota**: Arquivo consolidado nao disponivel. Consultar ajuda SSW para detalhes.

### Referencia Provavel
- Opcao 468: Impressao de Tabelas de Fretes (documentado em 417-418-420)
- Possivelmente relacionado a impressoes comerciais

---

## Opcao 518 — [Especifico]

**Nota**: Arquivo consolidado nao disponivel. Consultar ajuda SSW para detalhes.

---

## Fluxo Geral - Comprovantes e Comissionamento

### Ciclo Completo Parceria SSW:
1. **Emissao CTRC** (opcao 004): calcula comissao expedicao/recepcao
2. **Operacao**: subcontratado executa servico no seu SSW
3. **Entrega**: comprovantes fisicos coletados
4. **Capa Remessa** (opcao 428): subcontratado envia comprovantes + capa
5. **Recepcao Capa** (opcao 428): subcontratante recebe e arquiva
6. **Credito CCF** (opcao 486): comissao creditada automaticamente (forma C)
7. **Acerto**: saldo CCF → Contas a Pagar (opcao 475)

### Ciclo Completo Agregado:
1. **Cadastro tabela** (opcao 409): remuneracao por veiculo
2. **Operacao**: veiculo coleta/entrega CTRCs
3. **Demonstrativo** (opcao 076): previa remuneracao por periodo
4. **Conferencia**: proprietario valida valores
5. **Emissao OS** (opcao 075): processa e credita CCF (opcao 486)
6. **Acerto**: saldo CCF → Contas a Pagar (opcao 475) → CTRB/RPA

### Unidades Mesmo Armazem:
1. **Configuracao** (opcao 431): agrupar unidades
2. **Emissao CTRCs**: por qualquer unidade do grupo
3. **Romaneio** (opcao 035): consolida grupo
4. **Remuneracao** (opcao 076/075): calcula grupo inteiro
5. **Relatorio** (opcao 056): resultado consolidado

---

## Integracao Geral

| Opcao | Papel no Fluxo |
|-------|----------------|
| 428 | Recebe capa → credita CCF |
| 431 | Agrupa unidades → processos consolidados |
| 075 | Emite OS → credita CCF agregado |
| 076 | Demonstrativo → previa remuneracao |
| 408 | Comissao unidades → calculo |
| 409 | Remuneracao veiculos → calculo |
| 486 | CCF → controle debitos/creditos |
| 475 | Contas Pagar → acerto final |
| 056 | Relatorios gerenciais |

---

## Observacoes Gerais

### Arquivo de Comprovantes
- Apenas unidades configuradas (opcao 401: "Arquiva Comprovante = S")
- Padrao: apenas MTZ arquiva
- Evita duplicacao entre unidades

### Formas Credito CCF (Comissao Parcerias)
1. **M - Mapa**: processamento batch (opcao 903)
2. **F - Fatura**: conferencia manual (opcao 607)
3. **C - Capa**: recepcao capa (opcao 428) - **PRIORIDADE**

### Unidades Compartilhadas
- Mesmo armazem fisico ≠ mesma unidade fiscal
- Permite otimizacao operacional mantendo separacao contabil
- Processos reconhecem CTRCs automaticamente

### Rastreabilidade
- Comissoes: opcao 392 mostra em qual MAPA foi paga
- Capas: historico recepcao
- OS: link para CCF e CTRB/RPA
