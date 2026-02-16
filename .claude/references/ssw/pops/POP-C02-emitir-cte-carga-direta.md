# POP-C02 — Emitir CT-e para Carga Direta

> **Categoria**: C — Operacional: Emissao
> **Prioridade**: P1 (Alta — segundo mais frequente, mais complexo)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Emitir CT-e para cargas diretas — modalidade onde a CarVia utiliza caminhao proprio, agregado ou transportadora parceira com carga fechada. Diferente do fracionado, a carga direta exige placa real do veiculo e obriga a sequencia legal completa (POP-G01).

---

## Trigger

- Carga direta aprovada pelo cliente
- NF-e do cliente disponivel (chave de 44 digitos)
- Veiculo e motorista DEFINIDOS e APROVADOS pela gerenciadora (POP-G02)

---

## Frequencia

Por demanda — 41% dos fretes da CarVia (7 de 17 no primeiro mes).

---

## Pre-requisitos

| Requisito | Opcao SSW | Status | POP relacionado |
|-----------|-----------|--------|-----------------|
| Cliente cadastrado | [483](../cadastros/483-cadastro-clientes.md) | Deve existir | POP-A01 |
| Tabela de frete | 420 ou manual | Deve existir para rota | POP-A07 |
| NF-e do cliente | Recebida | Chave de 44 digitos | — |
| Veiculo cadastrado | [026](../relatorios/026-cadastro-veiculos.md) | RNTRC valido | POP-A08 |
| Motorista cadastrado | [028](../operacional/028-relacao-motoristas.md) | CNH valida, telefones | POP-A09 |
| Gerenciadora aprovada | Fora SSW + 390 | Motorista e veiculo aprovados | POP-G02 |

> **ATENCAO**: Este POP e a **etapa 3** do POP-G01 (Sequencia Legal Obrigatoria). As etapas 1 (cadastros) e 2 (gerenciadora) DEVEM ter sido concluidas ANTES.

---

## Passo-a-Passo

### ETAPA 1 — Verificar que etapas anteriores foram concluidas

1. Confirmar:
   - [ ] Veiculo cadastrado com RNTRC valido ([026](../relatorios/026-cadastro-veiculos.md))
   - [ ] Motorista cadastrado com CNH valida ([028](../operacional/028-relacao-motoristas.md))
   - [ ] Gerenciadora consultada — motorista e veiculo APROVADOS (POP-G02)

**Se algum item NAO estiver concluido**: PARAR e resolver antes de prosseguir.

---

### ETAPA 2 — Alterar Unidade para CAR

2. No SSW, verificar que a unidade ativa e **CAR**
   - A emissao do CT-e deve ser feita na unidade operacional CAR
   - Se estiver em MTZ ou outra unidade, trocar para CAR

---

### ETAPA 3 — Emitir Pre-CTRC (Opcao 004)

3. Acessar [opcao **004**](../operacional/004-emissao-ctrcs.md)
4. Preencher dados basicos:

| Campo | Valor | Diferenca do fracionado |
|-------|-------|------------------------|
| **Tipo documento** | CT-e Normal (N) | Igual |
| **CNPJ Remetente** | CNPJ de quem envia | Igual |
| **CNPJ Destinatario** | CNPJ de quem recebe | Igual |
| **CNPJ Pagador** | (default) | Igual |
| **Placa de coleta** | **PLACA REAL do veiculo** | ← **DIFERENTE do fracionado** |
| **Tipo de frete** | CIF ou FOB | Igual |

> **REGRA CRITICA**: Para carga direta, a placa de coleta DEVE ser a placa REAL do veiculo que fara o transporte. NUNCA usar "ARMAZEM" em carga direta.

5. Preencher dados da NF-e:

| Campo | Valor |
|-------|-------|
| **Chave NF-e** | 44 digitos (copiar e colar, verificar) |
| **Nota Fiscal** | Numero da NF-e (9 digitos) |
| **Serie** | Serie da NF-e |
| **Data emissao** | Data de emissao |
| **Peso (Kg)** | Peso total da carga |
| **Qtd Volumes** | Quantidade de volumes |
| **Valor mercadoria** | Valor total |

6. Clicar em **SIMULAR**

---

### ETAPA 4 — Verificar Simulacao

7. Analisar resultado:

| Componente | Verificar |
|------------|-----------|
| Frete Peso | Valor calculado vs cotacao aprovada |
| Despacho | Taxa fixa aplicada |
| Pedagio | Valor correto para a rota |
| GRIS | Percentual sobre valor da mercadoria |
| Taxas adicionais | TDE, TDC, etc. (se aplicaveis) |
| ICMS | Calculado automaticamente |
| **Total do frete** | Conferir com cotacao enviada ao cliente |

**Se valor DIVERGENTE**: Mesmo procedimento do POP-C01 (verificar 420, 062, polo P/R/I)

**Se carga direta com frete negociado fora da tabela**:
- Marcar "Frete Informado"
- Digitar valores manualmente
- Isso e comum em cargas diretas onde o preco foi negociado caso a caso

---

### ETAPA 5 — Gravar Pre-CTRC

8. Clicar no botao **Play** (gravar)
9. **"Confirma a emissao?"** → **Sim**
10. **"Deseja enviar email ao pagador?"** → **NAO**
11. **Pre-CTRC criado** — anotar o numero

---

### ETAPA 6 — Enviar CT-e ao SEFAZ (Opcao 007)

12. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
13. Clicar em **"DIGITADOS POR MIM"**
14. Clicar em **"Enviar CT-es ao SEFAZ"**
15. Aguardar autorizacao:
    - **Autorizado**: Prosseguir
    - **Rejeitado**: Verificar motivo e corrigir

**Verificacoes pos-autorizacao**:
- [ ] CT-e com numero definitivo e protocolo SEFAZ
- [ ] Averbacao automatica realizada (AT&M)
- [ ] Data/hora de autorizacao e ANTERIOR ao embarque previsto

---

### ETAPA 7 — Proximos Passos (Sequencia Legal)

Apos CT-e autorizado, **seguir a sequencia legal (POP-G01)**:

```
CT-e Autorizado ← VOCE ESTA AQUI
      ↓
4. Contratar veiculo (POP-D01, opcao [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md))
      ↓
5. Criar romaneio (POP-D02, opcao [035](../operacional/035-romaneio-entregas.md))
      ↓
6. Criar manifesto + MDF-e (POP-D03, opcoes [020](../operacional/020-manifesto-carga.md)/025)
      ↓
7. EMBARQUE (so apos tudo concluido)
```

**NAO embarcar a mercadoria ate completar todas as etapas.**

---

## Multiplas NF-es na Mesma Carga

Se a carga direta tem VARIAS NF-es do mesmo cliente:

### Opcao A — CT-es Individuais ([opcao 004](../operacional/004-emissao-ctrcs.md))
- Emitir um CT-e para cada NF-e
- Repetir etapas 3-6 para cada NF-e
- Todos os CT-es vao para o mesmo romaneio e manifesto

### Opcao B — CT-e em Lote ([opcao 006](../operacional/006-emissao-cte-os.md))
- Importar XMLs das NF-es via repositorio ([opcao 071](../operacional/071-contratacao-de-veiculos.md))
- [Opcao 006](../operacional/006-emissao-cte-os.md) gera pre-CTRCs em lote
- Pode agrupar por: pedido, destinatario, recebedor, EDI
- Rateio de frete entre CTRCs se necessario (opcao 061)
- Mais eficiente para muitas NF-es

### Opcao C — CT-e Unico com Multiplas NF-es
- Na [opcao 004](../operacional/004-emissao-ctrcs.md), informar varias NF-es no mesmo CT-e
- Usar quando as NF-es sao do MESMO remetente para o MESMO destinatario

---

## Diferenca entre Carga Direta e Fracionado

| Aspecto | Carga Direta (este POP) | Fracionado (POP-C01) |
|---------|------------------------|---------------------|
| Placa de coleta | **Placa REAL** | ARMAZEM |
| POP-G01 (seq. legal) | **OBRIGATORIO** | Nao se aplica |
| POP-G02 (gerenciadora) | **OBRIGATORIO** | Nao se aplica |
| Romaneio ([035](../operacional/035-romaneio-entregas.md)) | **OBRIGATORIO** | Nao necessario |
| Manifesto/MDF-e ([020](../operacional/020-manifesto-carga.md)/025) | **OBRIGATORIO se interestadual** | Nao necessario |
| Contratacao ([072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) | **OBRIGATORIO** | Nao necessario |
| Frete informado | Comum (negociacao caso a caso) | Raro (tabela 420) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Placa "ARMAZEM" em carga direta | Erro de operacao | Cancelar pre-CTRC e reemitir com placa real |
| Placa nao encontrada | Veiculo nao cadastrado em [026](../relatorios/026-cadastro-veiculos.md) | Cadastrar veiculo (POP-A08) |
| Simulacao com valor zero | Sem tabela e sem frete informado | Informar frete manualmente |
| SEFAZ rejeita: chave NF-e | Chave digitada errada | Conferir 44 digitos |
| SEFAZ rejeita: duplicidade | CT-e ja existe para esta NF | Verificar [opcao 101](../comercial/101-resultado-ctrc.md) |
| CT-e emitido APOS embarque | Violacao da sequencia legal | **RISCO CRITICO** — seguro pode nao cobrir |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Unidade ativa = CAR | Menu principal → unidade selecionada |
| Placa REAL no Pre-CTRC | [Opcao 004](../operacional/004-emissao-ctrcs.md) → alterar CTRC → campo "Placa coleta" ≠ "ARMAZEM" |
| CT-e autorizado | [Opcao 007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → CT-e presente |
| Data autorizacao < data embarque | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → data/hora autorizacao |
| Averbacao realizada | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → resumo averbacao |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G01 | Sequencia legal — este POP e a etapa 3 |
| POP-G02 | Gerenciadora de risco — etapa 2 (antes deste) |
| POP-A08 | Cadastrar veiculo — pre-requisito |
| POP-A09 | Cadastrar motorista — pre-requisito |
| POP-D01 | Contratar veiculo — proximo passo (etapa 4) |
| POP-D02 | Romaneio — proximo passo (etapa 5) |
| POP-D03 | Manifesto/MDF-e — proximo passo (etapa 6) |
| POP-C01 | Emitir CTe fracionado — variante sem sequencia legal |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
