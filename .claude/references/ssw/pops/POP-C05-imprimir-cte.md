# POP-C05 — Imprimir/Reimprimir CT-e

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: JA FAZ
> **Opcoes SSW**: 007, 025, 038
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Imprimir ou reimprimir o DACTE (Documento Auxiliar do CT-e Eletronico) — a versao impressa do CT-e autorizado. O DACTE acompanha a mercadoria durante o transporte e serve como comprovante fiscal.

---

## Quando Executar (Trigger)

- CT-e autorizado precisa ser impresso pela primeira vez
- DACTE foi perdido ou danificado (reimprimir)
- Cliente solicita copia do DACTE
- Fiscalizacao exige apresentacao do documento
- Auditoria interna ou externa requer copia
- Transportadora parceira solicita copia para arquivo

---

## Frequencia

Por demanda — processo ocasional, mas importante conhecer.

---

## Pre-requisitos

- CT-e JA autorizado pelo SEFAZ (status "Autorizado")
- Numero do CT-e (serie + numero) ou chave de acesso (44 digitos)
- Impressora configurada (matricial para formulario fiscal ou laser/jato para A4)

---

## Passo-a-Passo

### ETAPA 1 — Impressao Inicial (Apos Autorizacao)

#### Cenario A — Impressao Automatica (Modo A na opcao 903)

1. Se configurado Modo A (Automatico) na [opcao 903](../cadastros/903-parametros-gerais.md):
   - CT-e e autorizado automaticamente
   - Sistema pergunta: **"Deseja imprimir CT-es autorizados?"**
   - Clicar **Sim**
   - DACTE e impresso na impressora matricial (formulario fiscal) ou laser (A4)

#### Cenario B — Impressao Manual (Modo M ou S na [opcao 903](../cadastros/903-parametros-gerais.md))

2. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
3. Na tela inicial, verificar: **"QUANTIDADE DE CTRCS AUTORIZADOS"**
4. Clicar em link ou botao **"Imprimir CT-es Autorizados"**
5. Sistema lista CT-es autorizados pendentes de impressao
6. Selecionar CT-es a imprimir (todos ou faixa especifica)
7. Clicar **Imprimir**
8. DACTE e impresso

---

### ETAPA 2 — Reimpressao (CT-e Ja Impresso)

#### Metodo A — Reimpressao pela Opcao 007

9. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
10. Procurar secao **"Reimpressao"** ou link **"Informando-se faixas de CTRCs"**
11. Informar faixa de CT-es a reimprimir:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **CT-e inicial** | Numero do primeiro CT-e | Sem a serie (sigla) |
| **CT-e final** | Numero do ultimo CT-e | Ou mesmo numero se for um so |
| **Selecionar** | MEUS ou TODOS | MEUS = digitados por mim, TODOS = por qualquer usuario |

12. Clicar **Imprimir**
13. Sistema imprime DACTEs selecionados

#### Metodo B — Reimpressao pela Opcao 025 (Se CT-e em Manifesto)

14. Se CT-e ja foi incluido em Manifesto (MDF-e):
   - Acessar [opcao **025**](../operacional/025-saida-veiculos.md) (Saida de veiculos)
   - Pesquisar pelo Manifesto que contem o CT-e
   - Usar funcao de impressao do Manifesto (imprime MDF-e + DACTEs dos CT-es)

#### Metodo C — Reimpressao pela Opcao 038 (Se CT-e Entregue)

15. Se CT-e ja foi baixado (entregue):
   - Acessar [opcao **038**](../operacional/038-baixa-entregas-ocorrencias.md) (Baixa de entregas)
   - Pesquisar pelo CT-e
   - Usar funcao de impressao (imprime DACTE + comprovante de entrega)

---

### ETAPA 3 — Reimpressao por NF-e (Quando Nao Sabe o Numero do CT-e)

16. Acessar [opcao **007**](../operacional/007-emissao-cte-complementar.md)
17. Secao **"Informando-se faixas de NOTAS FISCAIS"**
18. Informar:

| Campo | Valor |
|-------|-------|
| **NF-e inicial** | Numero da primeira NF-e |
| **NF-e final** | Numero da ultima NF-e |
| **Selecionar** | MEUS ou TODOS |

19. Sistema busca CT-es correspondentes as NF-es
20. Clicar **Imprimir**

> **Nota**: Sistema considera apenas NF-es digitadas nas ultimas 3 horas para evitar duplicacoes. Se CT-e for mais antigo, usar faixa de CT-es (Metodo A).

---

### ETAPA 4 — Impressao de CT-e Especifico (Consulta pela Opcao 101)

21. Se nao souber o numero exato do CT-e:
   - Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) (Consulta de CTRC)
   - Pesquisar por: chave NF-e, CNPJ remetente, destinatario, periodo
   - Anotar numero do CT-e
   - Usar Metodo A (faixa de CT-es) com numero inicial = final

---

### ETAPA 5 — Conferir Impressao

22. Apos imprimir, conferir:
   - [ ] Chave de acesso (44 digitos) esta legivel
   - [ ] Codigo de barras (se houver) esta legivel
   - [ ] Dados do remetente e destinatario corretos
   - [ ] Valor do frete correto
   - [ ] Protocolo de autorizacao SEFAZ presente
   - [ ] Data/hora de emissao e autorizacao presentes

---

## Diferenca entre Tipos de Impressao

| Tipo | Quando | Opcao SSW | Impressora |
|------|--------|-----------|------------|
| **Formulario fiscal** | CT-e em papel timbrado (raro hoje) | 007 | Matricial |
| **A4 (DACTE)** | Padrao atual — documento auxiliar | 007, 025, 038 | Laser / Jato |
| **Digital (sem papel)** | Operacao paperless — PDF | 007 (salvar PDF) | Nao imprime |

---

## Contexto CarVia

### Hoje
Rafael imprime CT-es quando necessario:
- Operacao e predominantemente digital (sem papel)
- Cliente recebe XML do CT-e por e-mail
- DACTE impresso apenas quando cliente solicita ou fiscalizacao exige

### Futuro (com POP implantado)
- Formalizar quando imprimir vs quando nao imprimir
- Criar arquivo digital (PDFs) para auditoria
- Treinar equipe para reimprimir sem depender do Rafael

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Sistema nao encontra CT-e | Numero digitado errado | Usar [opcao 101](../comercial/101-resultado-ctrc.md) para confirmar numero correto |
| "CT-e nao autorizado" | CT-e ainda em pre-CTRC | Enviar ao SEFAZ primeiro ([opcao 007](../operacional/007-emissao-cte-complementar.md)) |
| Impressao sai cortada ou ilegivel | Configuracao de impressora errada | Configurar impressora (link "CONFIGURAR SEU MICRO" no menu) |
| Codigo de barras ilegivel | Impressora matricial de baixa qualidade | Usar impressora laser/jato |
| Reimpressao de CT-e antigo (> 3h) por NF-e | Restricao do sistema | Usar faixa de CT-es (Metodo A) em vez de faixa de NF-es |
| DACTE sem protocolo SEFAZ | CT-e rejeitado ou cancelado | Verificar status na [opcao 101](../comercial/101-resultado-ctrc.md) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CT-e autorizado | [Opcao 007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → CT-e presente |
| Protocolo SEFAZ | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e → protocolo presente |
| DACTE impresso | Documento fisico em maos com chave de acesso legivel |
| Configuracao de impressora | Link "VERIFICAR" no menu principal → impressora OK |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — autorizacao antes da impressao |
| POP-C02 | Emitir CTe carga direta — autorizacao antes da impressao |
| POP-D03 | Manifesto/MDF-e — impressao de CT-es via manifesto |
| POP-D05 | Baixa de entrega — impressao de CT-es baixados |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
