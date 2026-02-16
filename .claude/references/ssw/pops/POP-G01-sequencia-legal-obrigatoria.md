# POP-G01 — Sequencia Legal Obrigatoria (Carga Direta)

> **Categoria**: G — Compliance, Frota e Gestao
> **Prioridade**: P0 (URGENTE — risco legal/seguro)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael (supervisao) + operacional

---

## Objetivo

Garantir que TODA carga direta (caminhao proprio, agregado ou transportadora parceira) siga a sequencia legal obrigatoria ANTES do embarque. O descumprimento dessa sequencia pode resultar em:

- **Sinistro sem cobertura do seguro** (ESSOR)
- **Multa ANTT** (falta de CIOT)
- **Multa fiscal** (falta de MDF-e interestadual)
- **Apreensao da carga** (falta de documentacao)

---

## Trigger

**TODA carga direta**, sem excecao. Aplica-se quando:
- Caminhao proprio (VUC ou Truck) faz entrega
- Agregado e contratado para uma carga
- Transportadora parceira faz carga fechada (nao fracionado)

**NAO se aplica a**: Frete fracionado (subcontratacao via parceiro — nesse caso usar POP-C01)

---

## Pre-requisitos Gerais

- Acesso ao SSW com usuario Rafael
- NF-e do cliente disponivel (chave de 44 digitos)
- Veiculo e motorista definidos
- Conhecer destino e UFs de percurso (para MDF-e)

---

## Sequencia INVIOLAVEL

```
┌─────────────────────────────────────────────────────────────────┐
│  ORDEM DE EXECUCAO — NAO PULAR NENHUMA ETAPA                   │
│                                                                 │
│  1. Cadastrar motorista e veiculo (se nao cadastrados)          │
│  2. Consultar gerenciadora de risco (ESSOR/AT&M)                │
│  3. Emitir CT-e (ANTES do embarque)                             │
│  4. Contratar veiculo (gera CIOT se aplicavel)                  │
│  5. Criar romaneio de entregas                                  │
│  6. Criar manifesto + emitir MDF-e (se interestadual)           │
│  7. SO ENTAO: liberar embarque da mercadoria                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Passo-a-Passo Detalhado

### ETAPA 1 — Verificar cadastros (Motorista e Veiculo)

**Opcoes SSW**: [026](../relatorios/026-cadastro-veiculos.md) (veiculos), [028](../operacional/028-relacao-motoristas.md) (motoristas)

1. Acessar [opcao **026**](../relatorios/026-cadastro-veiculos.md) no SSW
2. Pesquisar pela placa do veiculo
   - **Se encontrado**: Verificar se dados estao atualizados (RNTRC, tipo, capacidade, proprietario)
   - **Se NAO encontrado**: Cadastrar — ver POP-A08
3. Acessar [opcao **028**](../operacional/028-relacao-motoristas.md)
4. Pesquisar pelo CPF do motorista
   - **Se encontrado**: Verificar se CNH esta valida e dentro da validade
   - **Se NAO encontrado**: Cadastrar — ver POP-A09

**Dados criticos do veiculo ([026](../relatorios/026-cadastro-veiculos.md))**:
| Campo | Obrigatorio | Por que |
|-------|-------------|---------|
| Placa | Sim | Identificacao no CT-e e MDF-e |
| RNTRC | Sim | SEFAZ rejeita MDF-e se invalido |
| Tipo | Sim | Define se gera MDF-e ou nao (AVIAO nao gera) |
| Proprietario | Sim | RNTRC do proprietario validado pelo SEFAZ |
| Capacidade | Sim | Usado no calculo de rateio de custo |

**Dados criticos do motorista ([028](../operacional/028-relacao-motoristas.md))**:
| Campo | Obrigatorio | Por que |
|-------|-------------|---------|
| CPF | Sim | Identificacao no MDF-e e SMP |
| CNH | Sim | Obrigatorio para transporte |
| Validade CNH | Sim | Motorista com CNH vencida = problema legal |
| Telefones | Sim | SMP automatico usa telefone do motorista |

**Verificacao Playwright**:
- Acessar [opcao 026](../relatorios/026-cadastro-veiculos.md) → pesquisar placa → verificar RNTRC preenchido e nao expirado
- Acessar [opcao 028](../operacional/028-relacao-motoristas.md) → pesquisar CPF → verificar CNH valida

---

### ETAPA 2 — Consultar Gerenciadora de Risco

**Opcao SSW relacionada**: [390](../comercial/390-cadastro-especies-mercadorias.md) (PGR), [903](../cadastros/903-parametros-gerais.md)/Gerenciamento de Risco

> **ATENCAO**: Esta etapa ocorre FORA do SSW para a CarVia atualmente.

1. Acessar sistema da gerenciadora de risco (vinculada a ESSOR Seguros)
2. Consultar **motorista** — informar CPF
   - Motorista APROVADO? → prosseguir
   - Motorista REPROVADO? → **PARAR. Nao embarcar com este motorista.**
3. Consultar **veiculo** — informar placa
   - Veiculo APROVADO? → prosseguir
   - Veiculo REPROVADO? → **PARAR. Nao embarcar neste veiculo.**

**Regras da seguradora ESSOR (a confirmar com a seguradora)**:
- [ ] Motorista e veiculo DEVEM estar aprovados na gerenciadora ANTES do inicio do transporte
- [ ] CT-e DEVE estar autorizado ANTES do inicio do transporte
- [ ] MDF-e DEVE estar ativo durante todo o transporte interestadual
- [ ] Verificar regras sobre NF emitida em UF diferente da operacao (ex: NF do RJ, operacao iniciando em SP)

**Verificacao Playwright** (parcial):
- [Opcao 390](../comercial/390-cadastro-especies-mercadorias.md): Verificar se regras de PGR estao configuradas
- [Opcao 903](../cadastros/903-parametros-gerais.md): Verificar se GR esta ativa e configurada para a gerenciadora correta

> **ACAO PENDENTE**: Confirmar com ESSOR quais sao as regras EXATAS de cobertura do seguro. Documentar neste POP apos confirmacao.

---

### ETAPA 3 — Emitir CT-e

**Opcoes SSW**: [004](../operacional/004-emissao-ctrcs.md) (emissao), [007](../operacional/007-emissao-cte-complementar.md) (autorizacao SEFAZ)

> **REGRA CRITICA**: CT-e DEVE ser emitido e autorizado pelo SEFAZ ANTES do embarque da mercadoria.

1. No SSW, alterar unidade para **CAR**
2. Acessar [opcao **004**](../operacional/004-emissao-ctrcs.md)
3. Preencher dados:
   | Campo | Valor |
   |-------|-------|
   | Tipo documento | CT-e (Normal) |
   | CNPJ Remetente | CNPJ de quem envia |
   | CNPJ Destinatario | CNPJ de quem recebe |
   | Placa de coleta | Placa REAL do veiculo (NAO usar "ARMAZEM" em carga direta) |
   | Chave NF-e | 44 digitos da NF-e |
   | Peso | Peso da carga |
   | Volumes | Quantidade de volumes |
   | Valor mercadoria | Valor total da mercadoria |
4. Clicar **Simular** — verificar se valores estao corretos
   - Se incorreto: verificar tabela de frete (420/417/418) e parametros (062)
5. Clicar **Play** (gravar) → Confirmar → **NAO enviar email ao pagador**
6. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md) → Clicar **"Enviar CT-es ao SEFAZ"**
7. Aguardar autorizacao
   - **Autorizado**: Prosseguir para etapa 4
   - **Rejeitado**: Verificar motivo na [opcao 007](../operacional/007-emissao-cte-complementar.md) (filas de CT-e). Corrigir e reenviar

**Verificacao Playwright**:
- [Opcao 007](../operacional/007-emissao-cte-complementar.md): Verificar que CT-e esta com status "Autorizado"
- Verificar que data/hora de autorizacao e ANTERIOR ao embarque

**Para detalhamento completo**: Ver POP-C02

---

### ETAPA 4 — Contratar Veiculo

**Opcao SSW**: [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)

> Formaliza o contrato de transporte com o veiculo. Gera CTRB, calcula custo, alimenta CCF (486).

1. Acessar [opcao **072**](../operacional/072-contratacao-de-veiculo-de-transferencia.md)
2. Preencher dados:
   | Campo | Valor |
   |-------|-------|
   | Placa | Placa do veiculo |
   | CEP origem | CEP de origem da carga |
   | Unidade destino | Sigla da unidade destino |
3. Sistema calcula distancia (via rota cadastrada em 403 ou Google)
4. Definir tipo de contratacao:
   | Tipo | Documentos gerados | CIOT |
   |------|-------------------|------|
   | **Carreteiro (TAC)** | CTRB + RPA | Sim, por viagem |
   | **Agregado** | OS | Sim, mensal |
   | **Frota propria** | CTRB (adiantamentos) | Nao |
5. Confirmar contratacao
6. Sistema gera automaticamente:
   - CIOT (se aplicavel) — **obrigatorio para TAC, multa ANTT se ausente**
   - Vale Pedagio — **falta pode gerar multa por radares ANTT**
   - Credito na CCF (486)

**Verificacao Playwright**:
- [Opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md): Verificar contratacao criada com CIOT e Vale Pedagio

**Para detalhamento completo**: Ver POP-D01

---

### ETAPA 5 — Criar Romaneio de Entregas

**Opcao SSW**: [035](../operacional/035-romaneio-entregas.md)

1. Acessar [opcao **035**](../operacional/035-romaneio-entregas.md)
2. Preencher dados:
   | Campo | Valor |
   |-------|-------|
   | Veiculo | Placa do veiculo |
   | Motorista | CPF do motorista |
   | Data entrega | Data prevista de entrega |
3. Selecionar CTRCs para carregar no romaneio
4. Definir sequencia de entregas (se configurado em [903](../cadastros/903-parametros-gerais.md))
5. Confirmar emissao
6. Sistema registra ocorrencia **"85 — Saiu para Entrega"** automaticamente
7. Opcional: Imprimir DACTEs e roteiro

**Verificacao Playwright**:
- [Opcao 035](../operacional/035-romaneio-entregas.md): Verificar romaneio criado com CTRCs corretos

**Para detalhamento completo**: Ver POP-D02

---

### ETAPA 6 — Criar Manifesto e Emitir MDF-e (SE INTERESTADUAL)

**Opcoes SSW**: 020 (manifesto), [025](../operacional/025-saida-veiculos.md) (saida/MDF-e)

> **OBRIGATORIO para transporte interestadual. Para transporte municipal/intermunicipal dentro do mesmo estado, verificar legislacao estadual.**

1. Acessar opcao **020**
2. Informar **carreta provisoria** (nome ficticio para identificar agrupamento, ex: "SP001")
3. Carregar CTRCs: serie + numero + DV (sem separador)
4. Verificar totais (peso, m3, valor mercadoria, frete)
5. Clicar **"Emitir o Manifesto"**
6. Informar **placa definitiva** da carreta
7. Confirmar unidade destino e previsao de chegada
8. Verificar **UFs de percurso** (sugeridas da rota 403, ajustar se necessario)
9. Confirmar emissao do Manifesto Operacional
10. Acessar [opcao **025**](../operacional/025-saida-veiculos.md)
11. Selecionar o cavalo ou manifesto (codigo de barras)
12. Desmarcar manifestos que NAO receberao saida (se houver)
13. Confirmar dados: proprietario, TAC, CTRB/OS, previsao chegada, UFs percurso
14. Sistema submete MDF-e ao SEFAZ
    - **Autorizado**: Imprimir DAMDFE para o motorista
    - **Rejeitado**: Verificar motivo. Causas comuns:
      - RNTRC invalido (corrigir em [027](../operacional/027-relacao-proprietarios-veiculos.md))
      - MDF-e duplicado (encerrar MDF-e anterior via [030](../operacional/030-chegada-de-veiculo.md))
15. Imprimir DAMDFE (escolher tipo: sintetico, sem frete, ou com frete)
16. Entregar DAMDFE ao motorista

**ATENCAO — MDF-e duplicado**:
O SEFAZ rejeita MDF-e se existir um anterior com mesma origem, destino e placa sem que a chegada tenha sido registrada ([opcao 030](../operacional/030-chegada-de-veiculo.md)). Solucao: registrar chegada do MDF-e anterior ou cancelar (opcao 024, ate 24h).

**Verificacao Playwright**:
- [Opcao 025](../operacional/025-saida-veiculos.md): Verificar MDF-e com status "Autorizado" no SEFAZ
- Verificar que DAMDFE foi gerado

**Para detalhamento completo**: Ver POP-D03

---

### ETAPA 7 — Liberar Embarque

**SO apos completar TODAS as etapas anteriores.**

Checklist final antes de liberar:
- [ ] Motorista aprovado na gerenciadora de risco
- [ ] Veiculo aprovado na gerenciadora de risco
- [ ] CT-e autorizado pelo SEFAZ (data/hora ANTERIOR ao embarque)
- [ ] Veiculo contratado ([072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) com CIOT (se TAC)
- [ ] Romaneio criado ([035](../operacional/035-romaneio-entregas.md)) com CTRCs corretos
- [ ] MDF-e autorizado pelo SEFAZ (se interestadual)
- [ ] DAMDFE impresso e entregue ao motorista (se interestadual)
- [ ] DACTEs impressos e acompanham a carga

**SO ENTAO**: Liberar o embarque da mercadoria.

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SEFAZ rejeita MDF-e: RNTRC invalido | RNTRC do proprietario expirado ou incorreto | Atualizar em [opcao 027](../operacional/027-relacao-proprietarios-veiculos.md) |
| SEFAZ rejeita MDF-e: duplicado | MDF-e anterior nao encerrado | Registrar chegada ([030](../operacional/030-chegada-de-veiculo.md)) ou cancelar (024) |
| CIOT nao gerado | Tipo de contratacao incorreto na [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) | Verificar se tipo = Carreteiro e RNTRC informado |
| Multa ANTT por falta de Vale Pedagio | Vale Pedagio nao informado na [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) | Sempre gerar Vale Pedagio na contratacao |
| SMP rejeitada | Telefone do motorista incorreto ou gerenciadora indisponivel | Corrigir telefone em [028](../operacional/028-relacao-motoristas.md) e verificar 117 |
| Seguro nao cobre sinistro | CT-e emitido APOS o embarque | NUNCA embarcar antes do CT-e autorizado |

---

## Cenarios Especiais

### Carga com multiplas NF-es
- Emitir um CT-e para cada NF-e ([opcao 004](../operacional/004-emissao-ctrcs.md)) ou usar [opcao 006](../operacional/006-emissao-cte-os.md) (lote)
- Todos os CT-es devem estar no romaneio e no manifesto

### Transporte MUNICIPAL (mesma cidade)
- CT-e pode ser substituido por RPS ([opcao 009](../operacional/009-impressao-rps-nfse.md)) se origem fiscal = destino fiscal
- MDF-e NAO e obrigatorio para transporte municipal
- Verificar legislacao municipal

### NF-e emitida em UF diferente da operacao
- [CONFIRMAR COM ESSOR] Ex: NF emitida no RJ, carga saindo de SP
- Verificar se o CT-e pode ser emitido pela CarVia (SP)
- Verificar implicacoes tributarias (ICMS)

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A08 | Cadastrar veiculo (etapa 1) |
| POP-A09 | Cadastrar motorista (etapa 1) |
| POP-G02 | Checklist gerenciadora de risco (etapa 2) |
| POP-C02 | Emitir CTe carga direta (etapa 3) |
| POP-D01 | Contratar veiculo (etapa 4) |
| POP-D02 | Romaneio de entregas (etapa 5) |
| POP-D03 | Manifesto/MDF-e (etapa 6) |

---

## Verificacao Playwright — Resumo

| Etapa | Ponto de verificacao | Como verificar |
|-------|---------------------|----------------|
| 1 | Veiculo cadastrado com RNTRC valido | [026](../relatorios/026-cadastro-veiculos.md) → pesquisar placa → campo RNTRC |
| 1 | Motorista cadastrado com CNH valida | [028](../operacional/028-relacao-motoristas.md) → pesquisar CPF → campo validade CNH |
| 2 | GR configurada | [903](../cadastros/903-parametros-gerais.md) → Gerenciamento de Risco → ativa |
| 3 | CT-e autorizado | [007](../operacional/007-emissao-cte-complementar.md) → filas → "Autorizados" |
| 4 | Contratacao com CIOT | [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) → verificar contratacao → CIOT gerado |
| 5 | Romaneio criado | [035](../operacional/035-romaneio-entregas.md) → verificar romaneio → CTRCs listados |
| 6 | MDF-e autorizado | [025](../operacional/025-saida-veiculos.md) → verificar MDF-e → status "Autorizado" |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
