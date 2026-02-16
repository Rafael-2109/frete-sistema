# CarVia — Status de Adocao por POP

> **Criado em**: 2026-02-16
> **Fonte**: CARVIA_OPERACAO.md (secao 8) + CATALOGO_POPS.md
> **Objetivo**: Permitir ao agente saber se um POP e teorico ou se a CarVia ja executa no dia-a-dia

---

## Legenda

| Status | Significado |
|--------|-------------|
| **ATIVO** | CarVia ja executa este processo |
| **PARCIAL** | CarVia faz, mas incompleto ou sem padrao |
| **NAO IMPLANTADO** | Nunca fizeram, mas sabem que precisam |
| **NAO CONHECE** | Rafael nao sabe que existe ou como funciona |
| **EXTERNO** | Processo feito por terceiro (contabilidade, seguradora) |

---

## Tabela Completa

| POP | Nome | Status CarVia | Quem Faz Hoje | Executor Futuro | Bloqueador | Opcoes SSW |
|-----|------|---------------|---------------|-----------------|------------|------------|
| **A01** | Cadastrar cliente | ATIVO | Rafael | Jessica/Rafael | — | 483, 384 |
| **A02** | Cadastrar unidade parceira | ATIVO | Rafael | Rafael | — | 401 |
| **A03** | Cadastrar cidades atendidas | ATIVO | Rafael | Rafael | — | 402 |
| **A04** | Cadastrar rotas | ATIVO | Rafael | Rafael | — | 403 |
| **A05** | Cadastrar fornecedor | ATIVO | Rafael | Rafael | — | 478 |
| **A06** | Cadastrar custos/comissoes | ATIVO | Rafael | Rafael | — | 408 |
| **A07** | Cadastrar tabelas de preco | ATIVO | Rafael | Rafael | — | 420 |
| **A08** | Cadastrar veiculo | PARCIAL | Rafael | Rafael | Cadastro incompleto — falta RNTRC de alguns | 026 |
| **A09** | Cadastrar motorista | PARCIAL | Rafael | Rafael | Cadastro sob demanda, sem processo formal | 028 |
| **A10** | Implantar nova rota completa | ATIVO | Rafael | Rafael | — | 401→402→403→478→408→420 |
| **B01** | Cotar frete para cliente | ATIVO | Rafael | Jessica | Transicao Rafael→Jessica pendente | 002 |
| **B02** | Entender formacao de preco | NAO CONHECE | — | Rafael | Doc 062 disponivel (campos [CONFIRMAR]). Validar via Playwright | 004, 062, 903 |
| **B03** | Configurar parametros de frete | NAO CONHECE | — | Rafael | Doc 062 disponivel (campos [CONFIRMAR]). Validar via Playwright | 062 |
| **B04** | Resultado por CTRC | NAO IMPLANTADO | — | Rafael | Nunca analisou lucratividade no SSW | 101 |
| **B05** | Relatorios gerenciais | NAO IMPLANTADO | — | Rafael/Jessica | Nunca acessou opcao 056 | 056 |
| **C01** | Emitir CTe fracionado | ATIVO | Rafael | Rafael/Jaqueline | — | 004, 007 |
| **C02** | Emitir CTe carga direta | ATIVO | Rafael | Rafael | — | 004, 007 |
| **C03** | Emitir CTe complementar | NAO IMPLANTADO | — | Rafael | Nunca emitiu, nao sabe como | 007 |
| **C04** | Registrar custos extras | NAO CONHECE | — | Rafael | Nao sabe onde cadastrar TDE/diaria | 459 |
| **C05** | Imprimir CTe | ATIVO | Rafael | Rafael | — | 007 |
| **C06** | Cancelar CTe | NAO IMPLANTADO | — | Rafael | Nunca precisou, mas sabe que existe | 007 |
| **C07** | Carta de correcao CTe | NAO IMPLANTADO | — | Rafael | Nunca precisou | 007 |
| **D01** | Contratar veiculo | NAO CONHECE | — | Rafael | Nao sabe o que e CTRB/CIOT formal | 072 |
| **D02** | Criar romaneio | PARCIAL | Rafael | Rafael | Pouca pratica, faz esporadicamente | 035 |
| **D03** | Manifesto / MDF-e | NAO IMPLANTADO | — | Rafael | **RISCO LEGAL** — obrigatorio interestadual, nunca fez | 020, 025 |
| **D04** | Chegada de veiculo | NAO IMPLANTADO | — | Stephanie | Relevante quando usar transferencias | 030 |
| **D05** | Baixa de entrega | NAO IMPLANTADO | — | Stephanie | Fundamental para fechar ciclo, nao faz | 038 |
| **D06** | Registrar ocorrencias | NAO IMPLANTADO | — | Stephanie | Nao registra no SSW | 033, 038, 108 |
| **D07** | Comprovantes de entrega | NAO IMPLANTADO | — | Stephanie | Nao controla no SSW | 040, 049, 428 |
| **E01** | Pre-faturamento (verificar CTRCs) | NAO IMPLANTADO | — | Jaqueline | Nao verifica antes de faturar | 435 |
| **E02** | Faturar manualmente | ATIVO | Rafael | Jaqueline | Funcional, sem boleto | 437 |
| **E03** | Faturar automaticamente | NAO IMPLANTADO | — | Jaqueline | Volume atual nao justifica (17 fretes/mes) | 436 |
| **E04** | Cobranca bancaria (boleto) | NAO IMPLANTADO | — | Jaqueline | Sem configuracao bancaria no SSW | 444 |
| **E05** | Liquidar fatura | NAO IMPLANTADO | — | Jaqueline | Cliente deposita, nao da baixa no SSW | 048, 458 |
| **E06** | Manter faturas | NAO IMPLANTADO | — | Jaqueline | Nunca prorrogou/protestou | 457 |
| **F01** | Contas a pagar | NAO IMPLANTADO | — | Jaqueline | Pagamentos controlados fora do SSW | 475 |
| **F02** | CCF (conta corrente fornecedor) | NAO IMPLANTADO | — | Jaqueline | Sem controle de saldo com parceiros | 486 |
| **F03** | Liquidar despesa | NAO IMPLANTADO | — | Jaqueline | Depende de F01 | 476 |
| **F04** | Conciliar banco | NAO IMPLANTADO | — | Jaqueline | Conciliacao manual (Rafael calcula) | 569 |
| **F05** | Bloqueio financeiro CTRC | NAO IMPLANTADO | — | Rafael | Nunca bloqueou | 462 |
| **F06** | Aprovar despesas | NAO IMPLANTADO | — | Rafael | Depende de F01 | 560 |
| **G01** | Sequencia legal obrigatoria | PARCIAL | Rafael | Rafael | Opera por intuicao, sem checklist formal | 004→007→035→020→025 |
| **G02** | Checklist gerenciadora risco | PARCIAL | Rafael | Rafael | Segue parcialmente — depende ESSOR | Fora SSW + 390 |
| **G03** | Custos de frota | NAO IMPLANTADO | — | Rafael | 2 caminhoes, sem controle no SSW | 026, 320, 131, 475 |
| **G04** | Relatorios contabilidade | EXTERNO | Contabilidade | Contabilidade | — | 512, 515, 567 |

---

## Resumo de Adocao

| Status | Quantidade | % |
|--------|-----------|---|
| ATIVO | 13 | 29% |
| PARCIAL | 5 | 11% |
| NAO IMPLANTADO | 22 | 49% |
| NAO CONHECE | 4 | 9% |
| EXTERNO | 1 | 2% |
| **TOTAL** | **45** | **100%** |

---

## Riscos Criticos

| POP | Risco | Impacto |
|-----|-------|---------|
| **D03** (MDF-e) | Obrigatorio para transporte interestadual | Multa fiscal + seguro pode nao cobrir sinistro |
| **G01** (Sequencia legal) | CT-e deve ser anterior ao embarque | Sinistro sem cobertura ESSOR |
| **D01** (Contratar veiculo) | Sem CIOT formal = multa ANTT | Multa + bloqueio cadastral |
| **B02/B03** (Formacao preco) | Doc 062 disponivel, campos [CONFIRMAR] | Simulacao pode calcular preco errado — validar via Playwright |

---

## Pendencias Operacionais

| # | Pendencia | POPs Relacionados | Responsavel | Urgencia |
|---|-----------|-------------------|-------------|----------|
| PEND-01 | Configurar seguradora ESSOR no SSW | G01, G02 | Rafael + ESSOR | URGENTE |
| PEND-02 | Aprender MDF-e antes de carga interestadual | D03 | Rafael | URGENTE |
| PEND-03 | Configurar banco/carteira para boleto | E04 | Rafael + banco | ALTA |
| PEND-04 | Implantar contas a pagar no SSW | F01, F02, F03 | Jaqueline | ALTA |
| PEND-05 | Implantar liquidacao de faturas | E05, F04 | Jaqueline | ALTA |
| PEND-06 | Descobrir e configurar evento 503 | F01 | Rafael | ALTA |
| PEND-07 | Validar campos da opcao 062 via Playwright (doc ja existe) | B02, B03 | Rafael | ALTA |
| PEND-08 | Treinar Stephanie em baixa/ocorrencias | D05, D06, D07 | Rafael | MEDIA |
| PEND-09 | Treinar Jessica em cotacao SSW | B01 | Rafael | MEDIA |
| PEND-10 | Treinar Jaqueline em faturamento | E01, E02, E03 | Rafael | MEDIA |
