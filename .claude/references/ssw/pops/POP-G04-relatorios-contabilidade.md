# POP-G04 — Extrair Relatorios para Contabilidade

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: JA FAZ (contabilidade externa)
> **Opcoes SSW**: [512](../fiscal/512-sped-fiscal-icms-ipi.md), [515](../fiscal/515-sped-contribuicoes.md), 567
> **Executor atual**: Contabilidade externa
> **Executor futuro**: Contabilidade externa

---

## Objetivo

Documentar o processo de geracao e extracao dos relatorios fiscais obrigatorios que a contabilidade externa precisa extrair mensalmente do SSW para cumprimento de obrigacoes acessorias (SPED Fiscal ICMS/IPI e SPED Contribuicoes PIS/COFINS).

---

## Quando Executar (Trigger)

- **Mensal**: Obrigacao acessoria ate o dia [CONFIRMAR: prazo legal] do mes seguinte
- **Apos finalizacao**: Todos os lancamentos de entrada (despesas) e saida (CTRCs) do mes devem estar finalizados

---

## Frequencia

Mensal — Todo mes, sem excecao.

---

## Pre-requisitos

| Item | Opcao SSW | O que verificar |
|------|-----------|-----------------|
| Lancamentos finalizados | [007](../operacional/007-emissao-cte-complementar.md), 475 | Todos os CTRCs e despesas do mes lancados |
| Inscricao Estadual ativa | [401](../cadastros/401-cadastro-unidades.md) | IE da unidade CAR configurada |
| Regime tributario definido | [401](../cadastros/401-cadastro-unidades.md) | Regime PIS/COFINS (cumulativo/nao-cumulativo) |
| Certificado digital valido | 903/Certificados | Certificado A1 (.PFX) dentro da validade |
| Validadores instalados | PC local | Validador SPED Fiscal e SPED Contribuicoes (Receita Federal) |
| Periodo fiscal aberto | 567 | Mes ainda nao fechado (primeira geracao) ou reaberto (correcoes) |

---

## Passo-a-Passo

### ETAPA 1 — Conferencia Pre-Geracao

**Antes de gerar os arquivos SPED, conferir:**

#### 1.1 — Verificar Emissoes do Mes (CTRCs)

1. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md) — Emissao de CTe
2. Filtrar por periodo: mes completo (ex: 01/02/2026 a 29/02/2026)
3. Verificar filas:
   - **Autorizados**: Todos os CTRCs do mes devem estar aqui
   - **Rejeitados**: Nenhum CTRC pode estar rejeitado sem resolucao
   - **Cancelados**: Conferir se cancelamentos sao intencionais

**Checklist**:
- [ ] Todos os CTRCs emitidos no mes foram autorizados pelo SEFAZ
- [ ] Nenhum CTRC rejeitado pendente
- [ ] Cancelamentos justificados e documentados

#### 1.2 — Verificar Despesas do Mes (Entradas)

4. Acessar opcao **475** — Contas a Pagar
5. Filtrar por periodo de entrada: mes completo
6. Verificar lancamentos:
   - **Eventos corretos**: Cada despesa com evento apropriado (503)
   - **Dados fiscais completos**: Modelo, CFOP, valores, base ICMS, creditos PIS/COFINS
   - **XMLs importados**: Preferir importacao automatica vs. digitacao manual

**Checklist**:
- [ ] Todas as NF-es de entrada do mes foram lancadas
- [ ] Eventos configurados corretamente (503)
- [ ] Creditos PIS/COFINS marcados (se regime nao-cumulativo)
- [ ] Retencoes informadas (IRRF, INSS, ISS, PIS, COFINS)

#### 1.3 — Verificar Configuracoes Fiscais

7. Acessar [opcao **401**](../cadastros/401-cadastro-unidades.md) — Cadastro de Unidades
8. Selecionar unidade **CAR**
9. Verificar:

| Campo | Valor esperado | Por que |
|-------|----------------|---------|
| Inscricao Estadual | [IE da CarVia em SP] | Identifica a empresa no SPED Fiscal |
| Regime ICMS | [CONFIRMAR: Normal/Simples] | Determina apuracao ICMS |
| Regime PIS/COFINS | [CONFIRMAR: Cumulativo/Nao-cumulativo] | Determina creditos PIS/COFINS |
| CNPJ | CNPJ da CarVia | Raiz do CNPJ para SPED Contribuicoes |

10. Acessar opcao **410** — Tributacao de ICMS
11. Verificar aliquotas por UF destino (ex: SP 12%, RJ 12%, etc.)

**Checklist**:
- [ ] IE configurada corretamente
- [ ] Regime ICMS correto
- [ ] Regime PIS/COFINS correto
- [ ] Aliquotas ICMS por UF atualizadas

---

### ETAPA 2 — Gerar SPED Fiscal ICMS/IPI (Opcao 512)

**Obrigacao**: Mensal, por Inscricao Estadual.

#### 2.1 — Acessar Opcao 512

1. Acessar [opcao **512**](../fiscal/512-sped-fiscal-icms-ipi.md) — SPED Fiscal ICMS/IPI
2. Informar:

| Campo | Valor |
|-------|-------|
| Periodo | MM/AAAA (ex: 02/2026) |
| Unidade | CAR (selecionar pela Inscricao Estadual) |

3. Clicar **"Gerar Arquivo SPED Fiscal"**

#### 2.2 — Sistema Processa

**O que acontece automaticamente**:
- Sistema consolida todos os lancamentos do mes:
  - **Saidas**: CTRCs autorizados ([007](../operacional/007-emissao-cte-complementar.md))
  - **Entradas**: Despesas lancadas (475)
- Gera arquivo `.txt` no formato SPED Fiscal (layout EFD-ICMS/IPI)
- **FECHA automaticamente** o periodo fiscal (opcao 567) para unidades com mesma IE
  - **Bloqueio retroativo**: Apos fechamento, nao e possivel alterar CTRCs ou despesas do periodo

4. Salvar arquivo em local seguro (ex: `SPED_Fiscal_CarVia_022026.txt`)

#### 2.3 — Validar no Validador SPED Fiscal

5. Abrir **Validador SPED Fiscal** (programa da Receita Federal)
6. Carregar arquivo gerado (`SPED_Fiscal_CarVia_022026.txt`)
7. Validador verifica:
   - Estrutura do arquivo (blocos, registros)
   - Consistencia de totais (ICMS, valores)
   - Chaves de acesso de CTRCs (valida com SEFAZ)
   - Completude de campos obrigatorios

**Resultados possiveis**:
- **Validacao OK**: Arquivo pronto para transmissao
- **Erros/Avisos**: Corrigir no SSW → reabrir periodo (567) → corrigir lancamentos → gerar novamente

8. Se validacao OK: Salvar arquivo validado

#### 2.4 — Transmitir ao SEFAZ

9. Acessar portal SEFAZ SP (ou sistema especifico da SEFAZ)
10. Fazer upload do arquivo SPED Fiscal validado
11. Aguardar processamento
12. Receber protocolo de entrega

**Checklist**:
- [ ] Arquivo gerado sem erros
- [ ] Validador SPED aprovou arquivo
- [ ] Transmissao ao SEFAZ bem-sucedida
- [ ] Protocolo de entrega recebido e arquivado

---

### ETAPA 3 — Gerar SPED Contribuicoes PIS/COFINS (Opcao 515)

**Obrigacao**: Mensal, por raiz de CNPJ.

> **Atencao**: [Opcao 515](../fiscal/515-sped-contribuicoes.md) NAO tem documentacao dedicada. Campos e processo baseados em pratica comum SSW. **[CONFIRMAR detalhes com SSW Suporte]**

#### 3.1 — Acessar Opcao 515

1. Acessar [opcao **515**](../fiscal/515-sped-contribuicoes.md) — SPED Contribuicoes PIS/COFINS
2. Informar:

| Campo | Valor |
|-------|-------|
| Periodo | MM/AAAA (ex: 02/2026) |
| [CONFIRMAR: Filtro por CNPJ ou automatico?] | Raiz CNPJ CarVia |

3. Clicar **[CONFIRMAR: nome do botao para gerar arquivo]**

#### 3.2 — Sistema Processa

**O que acontece automaticamente**:
- Sistema consolida lancamentos por raiz de CNPJ:
  - **Receitas**: CTRCs autorizados (valores de frete)
  - **Despesas**: Despesas com creditos PIS/COFINS (eventos configurados em 503)
- Calcula:
  - **Regime Cumulativo**: PIS 0,65% + COFINS 3% sobre receita bruta
  - **Regime Nao-Cumulativo**: PIS 1,65% + COFINS 7,6% sobre receita, menos creditos de despesas
- Gera arquivo `.txt` no formato SPED Contribuicoes (layout EFD-Contribuicoes)
- **FECHA automaticamente** o periodo fiscal (opcao 567) por raiz de CNPJ

4. Salvar arquivo em local seguro (ex: `SPED_Contribuicoes_CarVia_022026.txt`)

#### 3.3 — Validar no Validador SPED Contribuicoes

5. Abrir **Validador SPED Contribuicoes** (programa da Receita Federal)
6. Carregar arquivo gerado
7. Validador verifica:
   - Estrutura do arquivo
   - Apuracao PIS/COFINS (receitas, creditos, debitos)
   - CST (Codigo de Situacao Tributaria) corretos
   - Completude de campos

**Resultados possiveis**:
- **Validacao OK**: Arquivo pronto para transmissao
- **Erros/Avisos**: Corrigir no SSW → reabrir periodo (567) → corrigir → gerar novamente

8. Se validacao OK: Salvar arquivo validado

#### 3.4 — Transmitir a Receita Federal

9. Acessar **Receitanet** (programa da Receita Federal)
10. Fazer upload do arquivo SPED Contribuicoes validado
11. Aguardar processamento
12. Receber protocolo de entrega

**Checklist**:
- [ ] Arquivo gerado sem erros
- [ ] Validador SPED Contribuicoes aprovou arquivo
- [ ] Transmissao a Receita bem-sucedida
- [ ] Protocolo de entrega recebido e arquivado

---

### ETAPA 4 — Fechamento Fiscal (Opcao 567)

**Observacao**: O fechamento fiscal (567) e **AUTOMATICO** ao gerar SPED Fiscal ([512](../fiscal/512-sped-fiscal-icms-ipi.md)) e SPED Contribuicoes ([515](../fiscal/515-sped-contribuicoes.md)).

#### 4.1 — Verificar Fechamento

1. Acessar opcao **567** — Fechamento Fiscal
2. Selecionar periodo (mes/ano)
3. Verificar status:
   - **Fechado**: Periodo bloqueado para alteracoes
   - **Aberto**: Periodo ainda nao fechado

**Criterios de fechamento**:
- **SPED Fiscal ([512](../fiscal/512-sped-fiscal-icms-ipi.md))**: Fecha por **Inscricao Estadual** (IE)
  - Todas as unidades com mesma IE ficam bloqueadas
- **SPED Contribuicoes ([515](../fiscal/515-sped-contribuicoes.md))**: Fecha por **raiz de CNPJ**
  - Todas as unidades com mesma raiz CNPJ ficam bloqueadas

#### 4.2 — Reabrir Periodo (Se Necessario)

**Quando**: Necessario corrigir lancamentos apos envio de arquivo substituto ao SEFAZ.

4. Acessar opcao **567**
5. Selecionar periodo fechado
6. Clicar **[CONFIRMAR: botao para reabrir periodo]**
7. Sistema reabre periodo → permite alteracoes
8. Corrigir lancamentos ([007](../operacional/007-emissao-cte-complementar.md), 475)
9. Gerar novamente SPED Fiscal/Contribuicoes (arquivo SUBSTITUTO)
10. Validar e transmitir arquivo substituto

> **Risco**: Usuarios SSW (equipe SSW Suporte) **nao conseguem** fazer fechamento/reabertura pela opcao 567. Somente usuario da transportadora.

---

### ETAPA 5 — Relatorios de Conferencia (Opcional)

Antes ou apos gerar SPED, a contabilidade pode extrair relatorios para conferencia manual.

#### 5.1 — Livro ICMS (Opcao 433)

1. Acessar opcao **433** — Livro ICMS
2. Selecionar periodo
3. Gerar relatorio

**Dados exibidos**:
- Saidas (CTRCs): Valor total, Base ICMS, ICMS devido
- Entradas (Despesas): Valor total, Base ICMS, ICMS a creditar
- Apuracao: ICMS a recolher = ICMS devido - ICMS creditado

#### 5.2 — Livro ISS (Opcao 633)

4. Acessar opcao **633** — Livro ISS
5. Selecionar periodo
6. Gerar relatorio

**Dados exibidos**:
- RPS/NFS-e emitidos (transporte municipal)
- Base de calculo ISS
- ISS devido
- ISS retido (se houver)

#### 5.3 — SINTEGRA (Opcao 496)

**Observacao**: SINTEGRA foi substituido por SPED Fiscal na maioria dos estados. Verificar se SP ainda exige.

7. Acessar opcao **496** — Arquivo SINTEGRA
8. Informar periodo e IE
9. Gerar arquivo (se exigido)

#### 5.4 — DIFAL (Opcao 471)

**DIFAL** = Diferencial de Aliquota (ICMS interestadual para consumidor final nao-contribuinte).

10. Acessar opcao **471** — [CONFIRMAR: nome exato da opcao DIFAL]
11. Gerar relatorio de DIFAL do periodo
12. Verificar se ha valores a recolher

> **Aplicacao CarVia**: Se a CarVia transportar para consumidor final (pessoa fisica) em outro estado, pode haver DIFAL. [CONFIRMAR se aplica ao modelo de negocio]

---

## Contexto CarVia

### Hoje

A **contabilidade externa** ja extrai os relatorios fiscais do SSW mensalmente. Processo:

1. Contabilidade acessa SSW com usuario proprio
2. Gera SPED Fiscal ([512](../fiscal/512-sped-fiscal-icms-ipi.md)) e SPED Contribuicoes ([515](../fiscal/515-sped-contribuicoes.md))
3. Valida nos validadores da Receita
4. Transmite ao SEFAZ e Receita Federal
5. Arquiva protocolos

**Equipe CarVia (Rafael/Jaqueline)**:
- **Nao executa** este processo — contabilidade cuida
- **Responsabilidade CarVia**: Garantir que lancamentos ([007](../operacional/007-emissao-cte-complementar.md), 475) estao corretos e completos antes do prazo
- **Prazo interno**: Lancamentos finalizados ate dia [CONFIRMAR: dia do mes] para contabilidade processar

### Futuro (mesmo processo)

Com a implantacao de POPs anteriores (C01, C02, F01), a qualidade dos lancamentos melhora:
- Menos erros em CTRCs (emissao padronizada)
- Despesas organizadas por evento (503)
- Menor risco de retrabalho para contabilidade

**Beneficio indireto**:
- Contabilidade gasta menos tempo corrigindo erros
- Menor risco de multas fiscais por inconsistencias
- Arquivo SPED gerado mais rapido

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SPED Fiscal rejeita CTe | Chave de acesso invalida ou CTe cancelado sem constar no arquivo | Conferir [opcao 007](../operacional/007-emissao-cte-complementar.md) — filas de CTes. Incluir cancelamentos no arquivo |
| Validador SPED rejeita arquivo | Campos obrigatorios vazios (ex: CFOP, Base ICMS) | Corrigir lancamento (475), reabrir periodo (567), gerar novamente |
| Creditos PIS/COFINS nao aparecem | Evento (503) sem "Credita PIS/COFINS"=S | Corrigir evento (503), relancar despesa ou ajustar manualmente |
| Periodo nao fecha automaticamente | Geracao SPED sem sucesso | Verificar log de erros. Fechar manualmente (567) se necessario |
| DIFAL nao calculado | CTe para consumidor final sem marcacao | [CONFIRMAR: campo especifico no CTe para DIFAL] |
| Arquivo substituto nao aceito | Periodo nao reaberto antes de corrigir | Reabrir periodo (567) ANTES de corrigir lancamentos |

---

## Regras Especificas da Receita (A Confirmar)

| Regra | Status | Fonte |
|-------|--------|-------|
| Prazo envio SPED Fiscal | [CONFIRMAR: ate dia X do mes seguinte] | Legislacao ICMS SP |
| Prazo envio SPED Contribuicoes | [CONFIRMAR: ate dia X do mes seguinte] | Instrucao Normativa RFB |
| SINTEGRA ainda obrigatorio em SP? | [CONFIRMAR] | SEFAZ SP |
| DIFAL aplica-se a transporte para PF? | [CONFIRMAR] | Convenio ICMS 93/2015 |
| Simples Nacional: obrigacoes diferentes? | [CONFIRMAR: se CarVia e Simples] | Lei Complementar 123/2006 |

> **Acao**: Contabilidade externa deve confirmar esses detalhes com base na situacao tributaria especifica da CarVia.

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Periodo fiscal aberto | 567 → periodo → status "Aberto" |
| CTRCs do mes autorizados | [007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → filtrar periodo |
| Despesas do mes lancadas | 475 → filtrar por data entrada → verificar lista |
| IE configurada | [401](../cadastros/401-cadastro-unidades.md) → unidade CAR → campo IE preenchido |
| Regime PIS/COFINS | [401](../cadastros/401-cadastro-unidades.md) → unidade CAR → regime |
| Certificado digital valido | 903/Certificados → validade > data atual |
| SPED Fiscal gerado | [CONFIRMAR: log de geracao ou historico] |
| SPED Contribuicoes gerado | [CONFIRMAR: log de geracao ou historico] |
| Periodo fechado apos geracao | 567 → periodo → status "Fechado" |

> **Nota**: A validacao dos arquivos e transmissao ao SEFAZ/Receita ocorre FORA do SSW (validadores e portais governamentais). Playwright verifica apenas a geracao no SSW.

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — lancamentos de saida ([007](../operacional/007-emissao-cte-complementar.md)) |
| POP-C02 | Emitir CTe carga direta — lancamentos de saida ([007](../operacional/007-emissao-cte-complementar.md)) |
| POP-F01 | Lancar contas a pagar — lancamentos de entrada (475) |
| POP-G03 | Controlar custos de frota — despesas de frota integram SPED |
| POP-F04 | Conciliar banco — pre-requisito para fechamento contabil (F11) |

---

## Observacoes Finais

### Diferenca SPED Fiscal vs. SPED Contribuicoes

| Aspecto | SPED Fiscal ([512](../fiscal/512-sped-fiscal-icms-ipi.md)) | SPED Contribuicoes ([515](../fiscal/515-sped-contribuicoes.md)) |
|---------|-------------------|--------------------------|
| Tributo | ICMS + IPI | PIS + COFINS |
| Ambito | Estadual (SEFAZ) | Federal (Receita Federal) |
| Fechamento | Por IE | Por raiz CNPJ |
| Layout | EFD-ICMS/IPI | EFD-Contribuicoes |
| Obrigatorio para | Todos contribuintes ICMS/IPI | Lucro Real ou Presumido (regime nao-cumulativo) |

### SSW Atualiza Regras Automaticamente

O SSW recebe atualizacoes mensais da equipe SSW Sistemas com:
- Novas aliquotas de ICMS por UF
- Mudancas em CST (Codigo de Situacao Tributaria)
- Ajustes em layouts SPED conforme Receita/SEFAZ

> **Responsabilidade CarVia**: Manter SSW atualizado (atualizacoes automaticas ou via suporte SSW).

### Contabilidade Externa Experiente

A contabilidade da CarVia tem experiencia com **100+ transportadoras SSW**. Conhece:
- Todas as opcoes fiscais ([512](../fiscal/512-sped-fiscal-icms-ipi.md), [515](../fiscal/515-sped-contribuicoes.md), 567, 433, 496, etc.)
- Erros comuns de validadores SPED
- Inconsistencias tipicas em lancamentos

> **Rafael/Jaqueline nao precisam dominar** este POP em detalhes. O objetivo e **documentar o que a contabilidade faz** para referencia futura e treinamento de novos funcionarios.

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
