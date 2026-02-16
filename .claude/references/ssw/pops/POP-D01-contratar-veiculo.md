# POP-D01 — Contratar Veiculo para Carga Direta

> **Categoria**: D — Operacional: Transporte e Entrega
> **Prioridade**: P1 (Alta — formalizar custos de carga direta)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Ninguem (nao sabe o que e)
> **Executor futuro**: Rafael

---

## Objetivo

Formalizar a contratacao do veiculo para carga direta no SSW (opcao 072), gerando CTRB (Conhecimento de Transporte para terceiros) ou OS (Ordem de Servico), CIOT obrigatorio (ANTT) e Vale Pedagio. Sem esta contratacao, nao ha registro formal do custo da carga direta, a CCF nao e alimentada, e a CarVia pode receber multa ANTT pela falta de CIOT.

---

## Trigger

- Carga direta aprovada
- Veiculo e motorista definidos e aprovados pela gerenciadora (POP-G02)
- CT-e autorizado (POP-C02)
- **Etapa 4** do POP-G01 (Sequencia Legal Obrigatoria)

---

## Frequencia

Por demanda — a cada carga direta (41% dos fretes CarVia).

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Veiculo cadastrado | [026](../relatorios/026-cadastro-veiculos.md) | Placa, tipo (Frota/Agregado/Carreteiro), RNTRC |
| Proprietario cadastrado | [027](../operacional/027-relacao-proprietarios-veiculos.md) | CPF/CNPJ, dados bancarios |
| Fornecedor com CCF | [478](../financeiro/478-cadastro-fornecedores.md) | CCF ativa = S |
| CT-e autorizado | [007](../operacional/007-emissao-cte-complementar.md) | CT-e com status "Autorizado" (POP-C02) |
| Gerenciadora aprovada | Fora SSW + 390 | Motorista e veiculo aprovados (POP-G02) |
| Rota cadastrada | [403](../cadastros/403-rotas.md) | Distancia e previsao de chegada entre unidades |

> **Este POP e a etapa 4** do POP-G01 (Sequencia Legal). As etapas 1-3 DEVEM estar concluidas.

---

## Passo-a-Passo

### ETAPA 1 — Acessar Opcao 072

1. Acessar [opcao **072**](../operacional/072-contratacao-de-veiculo-de-transferencia.md) (Contratacao de Veiculo de Transferencia)
2. Informar **placa do veiculo** (cavalo/tracao)
3. Sistema exibe informacoes do veiculo ([opcao 026](../relatorios/026-cadastro-veiculos.md)) e links uteis:
   - Cadastro de veiculo ([026](../relatorios/026-cadastro-veiculos.md))
   - Conta Corrente Fornecedor ([486](../financeiro/486-conta-corrente-fornecedor.md))
   - Consulta CIOT/ANTT

---

### ETAPA 2 — Informar Origem e Destino

4. Preencher campos obrigatorios:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CEP origem** | CEP da cidade de origem | Ex: CEP de Santana de Parnaiba |
| **Unidade destino** | Sigla da unidade destino | Ex: CGR (Campo Grande) |
| **Passar por unidades** | Unidades intermediarias | Opcional — ordena rota para Vale Pedagio |
| **Previsao de chegada** | Data prevista | Sugerida pela tabela de rotas ([403](../cadastros/403-rotas.md)) |
| **Distancia** | Automatico | Calculada entre unidades ([403](../cadastros/403-rotas.md)) |

---

### ETAPA 3 — Definir Tipo de Carga e Valor

5. Informar tipo de carga (Resolucao ANTT 5867/2020)
6. Preencher valores:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Valor a Pagar** | Remuneracao da viagem | Negociado com proprietario |
| **Combustivel** | Valor de combustivel | Debitado na CCF se informado |
| **Pedagio** | Valor de pedagio | Debitado na CCF se informado |
| **Outros** | Outras despesas | Debitados na CCF se informados |
| **Taxa adm PEF** | Taxa administrativa | Se usando PEF |

7. Sistema exibe **Tabela ANTT** (frete minimo) como referencia:
   - Resolucao 5867/2020 e 6076/2026
   - Apenas informativo — SSW nao bloqueia valor abaixo do minimo

> **ATENCAO**: Se existe tabela de remuneracao cadastrada (opcao 399 por rota ou 499 por veiculo), o valor e sugerido automaticamente. Opcao 499 tem prioridade sobre 399.

---

### ETAPA 4 — CIOT (Automatico)

8. Sistema gera CIOT automaticamente conforme tipo:

| Tipo veiculo | CIOT | Vigencia | Encerramento |
|-------------|------|----------|--------------|
| **Carreteiro** | CIOT por viagem | 1 viagem | Automatico |
| **Agregado** | CIOT 30 dias | 30 dias | Proximo CIOT ou acerto CCF |
| **Frota** | NAO gera CIOT | — | — |

9. Verificar CIOT gerado:
   - Numero do CIOT
   - Vigencia
   - Valor

> **RISCO ANTT**: CIOT de agregado sem encerramento por mais de 60 dias **bloqueia** emissao de novos CIOTs.

---

### ETAPA 5 — Vale Pedagio (Obrigatorio para Terceiros)

10. **Obrigatorio** para carreteiros e agregados (Resolucao ANTT 2.885/2008)
11. Informar dados do Vale Pedagio:

| Campo | Valor |
|-------|-------|
| **Fornecedor** | Empresa habilitada ANTT (TARGET, SEM PARAR, etc.) |
| **Valor** | Valor estimado de pedagios na rota |
| **Validade** | Ate previsao de chegada |

12. Dados do Vale Pedagio sao **inseridos automaticamente no MDF-e** ([opcao 025](../operacional/025-saida-veiculos.md))

> **MULTA**: Falta de Vale Pedagio gera multa eletronica em radares ANTT.

**Fornecedores de CIOT gratuito (emergencia)**:
- TARGET: https://www.transportesbra.com.br/vectiofretepublico/
- REPOM: https://www1.repom.com.br/geracao-de-ciot/

---

### ETAPA 6 — Confirmar Contratacao

13. Verificar resumo:
    - Veiculo e proprietario corretos
    - Origem/destino corretos
    - Valor a pagar correto
    - CIOT gerado
    - Vale Pedagio informado (se terceiro)
14. Clicar em **Confirmar**
15. Sistema gera automaticamente:

| Documento | Tipo veiculo | Descricao |
|-----------|-------------|-----------|
| **CTRB** | Carreteiro | Conhecimento + RPA com retencoes INSS/IR |
| **OS** | Agregado | Ordem de Servico sem retencoes (retencoes no acerto) |
| **CTRB** | Frota | Para adiantamentos |

16. Sistema credita CCF do fornecedor automaticamente ([opcao 486](../financeiro/486-conta-corrente-fornecedor.md))
17. Sistema cria lancamento automatico no Contas a Pagar ([opcao 475](../financeiro/475-contas-a-pagar.md))
18. **Contratacao concluida** — anotar numero do CTRB/OS

---

### ETAPA 7 — Proximo Passo (Sequencia Legal)

Apos contratacao, seguir para:

```
Contratacao concluida ← VOCE ESTA AQUI
      ↓
5. Criar romaneio (POP-D02, [opcao 035](../operacional/035-romaneio-entregas.md))
      ↓
6. Criar manifesto + MDF-e (POP-D03, opcoes [020](../operacional/020-manifesto-carga.md)/[025](../operacional/025-saida-veiculos.md))
      ↓
7. EMBARQUE (so apos tudo concluido)
```

---

## Tres Tipos de Contratacao

| Aspecto | Carreteiro | Agregado | Frota |
|---------|------------|----------|-------|
| **Documento** | CTRB a cada viagem | OS na viagem | CTRB para adiantamentos |
| **CIOT** | Por viagem (automatico) | 30 dias (automatico) | Nao gera |
| **Vale Pedagio** | Obrigatorio | Obrigatorio | Nao obrigatorio |
| **Retencoes** | INSS/IR no CTRB (PF) | No acerto CCF | Nao aplica |
| **CCF** | Nao ha (pagamento direto) | Sim (credito/debito/acerto) | Nao aplica |
| **Acerto** | Pagamento direto | Periodico via CCF (486) | Controle interno |
| **PEF** | Opcional | Opcional | Nao aplica |

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| Contratacao formal | **Nao sabe o que e** | CTRB/OS via [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) |
| CIOT | Nao emite | Automatico via [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) |
| Vale Pedagio | Nao registra | Obrigatorio para terceiros |
| Registro de custo | Informal | Automatico (CCF + Contas a Pagar) |
| Resultado por CTRC | So receita | Receita - custo = resultado |
| Relatorio viagens | Nao tem | [Opcao 056](../relatorios/056-informacoes-gerenciais.md), relatorio [020](../operacional/020-manifesto-carga.md) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Veiculo nao encontrado | Nao cadastrado em [026](../relatorios/026-cadastro-veiculos.md) | Cadastrar (POP-A08) |
| CCF nao ativa | Fornecedor sem CCF em [478](../financeiro/478-cadastro-fornecedores.md) | Ativar CCF na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |
| CIOT nao gerado | Tipo veiculo = Frota | Frota nao gera CIOT (correto) |
| Vale Pedagio obrigatorio | Terceiro sem Vale Pedagio | Informar fornecedor e valor |
| Valor abaixo do minimo ANTT | Frete abaixo da tabela | Apenas informativo — ajustar se necessario |
| Rota sem distancia | Rota nao cadastrada em [403](../cadastros/403-rotas.md) | Cadastrar rota (POP-A04) |
| CIOT bloqueado ANTT | Agregado com CIOT > 60 dias sem encerrar | Encerrar CIOT anterior via acerto CCF ([486](../financeiro/486-conta-corrente-fornecedor.md)) |
| Proprietario nao cadastrado | Falta [opcao 027](../operacional/027-relacao-proprietarios-veiculos.md) | Cadastrar proprietario |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CTRB/OS emitido | [Opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) → placa → CTRB/OS gerado com numero |
| CIOT gerado | [Opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) → CIOT com numero e vigencia |
| CCF creditada | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → fornecedor → extrato → credito da contratacao |
| Vale Pedagio registrado | [Opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) → dados Vale Pedagio preenchidos |
| Contas a Pagar | Opcao 477 → lancamento automatico gerado |
| Veiculo cadastrado | [Opcao 026](../relatorios/026-cadastro-veiculos.md) → placa → tipo correto |
| Proprietario cadastrado | [Opcao 027](../operacional/027-relacao-proprietarios-veiculos.md) → CPF/CNPJ → dados preenchidos |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G01 | Sequencia legal — este POP e a etapa 4 |
| POP-G02 | Gerenciadora de risco — etapa 2 (antes deste) |
| POP-C02 | Emitir CTe carga direta — etapa 3 (antes deste) |
| POP-A08 | Cadastrar veiculo — pre-requisito |
| POP-A09 | Cadastrar motorista — pre-requisito |
| POP-D02 | Romaneio — proximo passo (etapa 5) |
| POP-D03 | Manifesto/MDF-e — proximo passo (etapa 6) |
| POP-F02 | CCF — credito automatico da contratacao |
| POP-F01 | Contas a pagar — lancamento automatico |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
