# Revisao do Fluxo SSW — Rafael Nascimento

**Data**: 2026-02-21
**Objetivo**: Mapear o fluxo real do Rafael no SSW, cruzar com o que esta implementado/documentado, identificar gaps e proximos passos.
**Status**: MAPEAMENTO COMPLETO — Em fase de investigacao de gaps

---

## PREMISSAS CONFIRMADAS

### Cadastros OK (ja implementados com scripts Playwright)
- **401** — Unidades
- **402** — Cidades Atendidas
- **403** — Rotas
- **408** — Comissao geral + por cidade
- **420** — Tabela por Rota
- **478** — Cadastro de fornecedores
- **483** — Cadastro de cliente (sob demanda)

---

## FLUXO REAL — PONTO A PONTO

### 1. COTACAO (Opcao 002)

**Quem faz**: Jessica
**Tipo**: Apenas fracionado (NAO tem tabela de carga direta cadastrada)
**Produto principal**: Motos em caixas (dimensoes variam por modelo)

#### Gaps identificados:

| Gap | Detalhe | Impacto |
|-----|---------|---------|
| **Cubagem por modelo** | SSW NAO tem cadastro de embalagem por produto. Cubagem e Kg/m3 configuravel por cliente (423), geral (903) ou por tabela (420). Como cada modelo de moto tem caixa diferente, a cubagem padrao nao e assertiva. | Cotacao imprecisa |
| **Carga direta** | Nao possui tabela cadastrada para carga direta/lotacao. Nao sabe como contratar. | Nao consegue cotar carga direta no SSW |

#### Opcoes de solucao para cubagem:
1. **Tabela interna** (sistema de fretes): cadastrar dimensoes por modelo de moto
2. **Opcao 423** (por cliente): configurar cubagem media do cliente predominante
3. **Manual**: informar volume (m3) na cotacao via `--cubagem`

#### Situacao da carga direta:
- Para cotar carga direta: criar tabelas na 420 para rotas de lotacao + entender opcao 072
- Carga direta exige fluxo pos-CTe diferente: Romaneio (035) -> Manifesto (020) -> MDF-e (025) -> Embarque

---

### 2. NEGOCIACAO E SUBCONTRATO

**Quem faz**: Jessica negocia com cliente. Jessica contrata parceiro.

#### Modelo operacional confirmado:
- **Parceiros fixos por unidade**: Cada unidade (BVH, CGR, etc.) tem transportadora cadastrada via 478/485/408
  - Exemplo: Transperola para BVH
- **Redespacho**: CarVia emite CT-e -> Parceiro emite CT-e de redespacho/subcontratacao
- **NAO usa opcao 072** (contratacao formal)
- **NAO gera CIOT** (nao precisa — no redespacho, CIOT e responsabilidade do parceiro que opera o veiculo)
- **NAO registra subcontrato** em nenhum local — confia que as tabelas de comissao (408) calculem corretamente
- **NAO sabe onde conferir** se o valor da comissao esta correto

#### Excecoes ao modelo fracionado:
- Carga direta (lotacao/fechada): contrata veiculo especifico
- Frota: veiculo proprio da CarVia

#### Analise de risco CIOT:
| Cenario | CIOT necessario? | Responsavel |
|---------|-----------------|-------------|
| Fracionado com parceiro (redespacho) | NAO para CarVia | Parceiro emite no seu CT-e de redespacho |
| Carga direta com terceiro | **SIM** | CarVia (via opcao 072) |
| Frota propria | NAO | Nao se aplica |

#### Onde conferir resultado/comissao (Rafael nao usa hoje):
- **Opcao 101** — Resultado por CTRC (receita - despesas = margem)
- **Opcao 056** — Relatorio 031 (CTRCs com prejuizo)
- **Opcao 449** — Resultado por cliente

---

### 3. EMISSAO DE CT-e (Opcao 004)

**Quem faz**: Rafael
**Tipo**: Fracionado com placa ARMAZEM
**Problema recorrente**: Frete NAO vem calculado corretamente na simulacao

#### Comportamento atual:
- Emite CT-e na opcao 004
- Seleciona placa ARMAZEM (fracionado)
- Simulacao frequentemente retorna valor errado ou zero
- **Informa o valor do frete manualmente** e segue

#### Tabelas cadastradas:
- Formato: `CARP-[sigla][polo]` (ex: CARP-FEIP)
- Todas as tabelas seguem esse padrao

#### Causas provaveis do frete incorreto:

| Causa | Verificacao |
|-------|-------------|
| Cidade destino nao vinculada na 402 | Opcao 402 -> procurar cidade -> conferir classificacao P/R/I |
| Tabela 420 inativa | Opcao 420 -> procurar CARP-XXX -> campo Ativa = S? |
| Rota 403 nao associada corretamente | Opcao 403 -> verificar se rota CARP-XXX existe para origem/destino |
| Classificacao P/R/I incorreta | Opcao 402 -> distancia vs classificacao |
| SSW usando tabela generica (923) em vez da especifica (420) | Prioridade: Rota (427) > UF (420) > Generica (923) |

#### Impacto do frete manual:
- Operacionalmente funciona
- **Prejudica resultado comercial (opcao 101)** — sistema nao compara receita vs custo calculado
- Dificulta analise de rentabilidade por rota/cliente

---

### 4. ENVIO SEFAZ

**Quem faz**: Rafael
**Como**: Clica "Enviar os meus CTe-s para a Sefaz" na tela 004

#### O que o SSW oferece:
A opcao dedicada para envio/autorizacao e a **007**. Porem, a opcao 903 configura **modo de envio**:

| Modo | Comportamento |
|------|--------------|
| **A** (Automatico) | SSW envia automaticamente a cada 1 minuto |
| **S** (Auto sem impressao) | Mesmo, sem exigir impressao |
| **M** (Manual) | Operador executa manualmente |

**CONFIRMADO via Playwright (903 → Autorizacao, campo t_modo_env)**: Modo = **M (Manual)**. Rafael precisa clicar manualmente para enviar. Se quiser automatizar, basta alterar para **A** ou **S** na 903.

---

### 5. GNRE (Opcao 160)

**Quando**: SSW avisa quando necessario (operacoes interestaduais com DIFAL)
**Quem faz**: Rafael
**Fluxo**: Opcao 160 gera a guia -> pagamento manual

**Pendencia**: Confirmar regime tributario da CarVia (Simples Nacional = possivel isencao via STF).

---

### 6. MANIFESTO E MDF-e (Opcoes 020/025)

**Quem faz**: Rafael
**Quando**: APENAS para frota propria ou carga direta onde transportador nao emite

#### Fluxo:
```
Opcao 020 (Manifesto Operacional):
  -> Montar carga (agrupar CT-es)
  -> Informar placa real, destino, previsao
  -> Emitir manifesto

Opcao 025 (Saida + MDF-e):
  -> Localizar veiculo por placa
  -> Confirmar saida
  -> MDF-e enviado ao SEFAZ automaticamente
  -> Imprimir DAMDFE para motorista
```

**MDF-e obrigatorio** para transporte interestadual. No redespacho (fracionado), o parceiro e quem emite o MDF-e.

**Pendencia**: Quem registra a chegada (opcao 030)? CarVia ou parceiro?

---

### 7. FATURAMENTO (Opcao 437)

**Quem faz**: Rafael
**Tipo**: Manual (opcao 437)
**Observacao**: E a UNICA etapa financeira que Rafael executa hoje no SSW.

---

### 8. PARTE LEGAL ENCERRADA

Para **fracionado com redespacho**: sim — CTe + SEFAZ + GNRE + Faturamento encerra.
Para **carga direta/frota**: faltam 072 (contratacao) e 035 (romaneio) antes do manifesto.

---

## PROCESSOS QUE RAFAEL NAO FAZ MAS SABE QUE PRECISA

| # | Necessidade | Opcao SSW | Status | Fluxo SSW |
|---|------------|-----------|--------|-----------|
| N1 | Conferir CTe subcontratacao contra CarVia | 475 (aba Disponiveis) | **NAO FUNCIONA** — 475/477/071 nao exibem CTes | EM INVESTIGACAO |
| N2 | Registrar subcontrato p/ contas a pagar | 475 -> 486 -> 476 | NAO FAZ | Incluir despesa -> programar -> liquidar |
| N3 | Registrar custo extra (descarga/chapa) | 442 [CONFIRMAR] | NAO FAZ | TDE, diaria, descarga manual |
| N4 | Finalizar entrega + comprovante | 038 -> 040 -> 428 | NAO FAZ | Baixar entrega -> capear -> arquivar |
| N5 | Pagar frete ao subcontratado | 475 -> 476 | NAO FAZ | Programar pagamento -> liquidar |
| N6 | Baixa do recebimento (cliente pagou) | 457 -> 569 | NAO FAZ | Liquidar fatura -> conciliar banco |
| N7 | Conferir entrega pelo subcontratado | 133 / 108 | NAO FAZ | Minhas Ocorrencias -> Instrucoes |

### Detalhamento dos processos faltantes:

#### N1 — Conferir CTe subcontratacao (PROBLEMA CRITICO)
- **Situacao**: Rafael tentou opcoes 475, 477 e 071 — nenhuma exibe CT-es emitidos contra a CarVia
- **Hipoteses**: certificado digital nao configurado, tela incorreta, CNPJ parceiro nao bate
- **Status**: EM INVESTIGACAO (ver secao abaixo)

#### N2 — Registrar subcontrato para pagamento
- **Fluxo**: 475 (Contas a Pagar) -> 486 (CCF) -> 476 (Liquidacao)
- **Pre-requisito**: Fornecedor (478) com CCF ativada (fg_cc=S)

#### N3 — Custo extra (descarga/chapa/ajudante)
- **Opcao**: 442 (Debito/Credito CTRC/Fatura) [CONFIRMAR via Playwright]
- **Tipos**: TDE (dificuldade), diaria, descarga manual, re-entrega, agendamento
- **Apos registrar**: aparece na 435 (pre-faturamento) -> pode cobrar do cliente na fatura

#### N4 — Finalizar entrega + comprovante
- **Fluxo**: 038 (baixar entrega) -> 040 (capear comprovantes) -> 428 (arquivar)
- **Captura**: SSW Mobile (motorista fotografa) ou escaneamento fisico (SSWScan)
- **Exigencia legal**: SIM — prova juridica de entrega. Sem comprovante: seguradora pode negar sinistro
- **Prazo retencao**: 5 anos recomendado

#### N5 — Pagar frete ao subcontratado
- **Fluxo**: 475 (incluir despesa) -> 476 (liquidar = PIX/transferencia) -> 569 (conciliar)
- **Formas**: A vista (PIX), cheque, PEF
- **Integracao**: Liquidacao gera lancamento contabil automatico

#### N6 — Baixa do recebimento (cliente pagou)
- **Fluxo**: 437 (faturar, ja faz) -> 444 (cobranca/boleto) -> 457 (liquidar) -> 569 (conciliar)
- **Rafael faz hoje**: Apenas o 437. Etapas 444/457/569 NAO faz.
- **Impacto**: CTRCs ficam "em aberto" nos relatorios, impossivel analisar lucro real

#### N7 — Conferir entrega pelo subcontratado
- **133** (Minhas Ocorrencias): CarVia como origem — acompanha o que parceiros registraram
- **108** (Instrucoes): Parceiro como destino — envia instrucoes de resolucao
- Se parceiro opera como unidade tipo T no SSW -> baixas visiveis em tempo real na 133
- Se parceiro NAO usa SSW -> comunicacao manual + registro na 038

---

## PROBLEMA CRITICO: CTe SUBCONTRATACAO NAO APARECE

### Descricao
Rafael confirmou que opcoes **475, 477 e 071 NAO exibem CT-es emitidos contra a CarVia** pelos parceiros (transportadoras subcontratadas que emitem CT-e de redespacho).

### Hipoteses de investigacao

| # | Hipotese | Como verificar |
|---|---------|----------------|
| H1 | Certificado digital nao esta configurado/ativo no SSW | Opcao 903 -> secao Certificado Digital -> verificar validade e status |
| H2 | Tela correta e outra (ex: 608 importacao XMLs) | Testar opcao 608 via Playwright |
| H3 | Parceiro emite CT-e com CNPJ diferente do esperado | Conferir CNPJ do parceiro no CT-e vs CNPJ no 478 |
| H4 | Configuracao de dominio/empresa impede | Opcao 903 -> parametros de empresa -> verificar dominio |
| H5 | DFe (Distribuicao NF-e) nao esta habilitado | SSW precisa de config especifica para puxar XMLs do SEFAZ |
| H6 | 475 so mostra NF-e, nao CT-e | Verificar se 475 filtra por tipo de documento |

### Investigacao via Playwright (2026-02-21)

#### Fase 1 — Leitura inicial da 903 e 475

| Secao | O que encontramos |
|-------|-------------------|
| 903 tela inicial | 17 secoes, dominio CV1 MTZ, ultima alteracao rafael 17/02/26 |
| 903 secoes relevantes | "Certificados digitais", "Emissao de CTRCs" |
| 475 tela inicial | Campo `chave_nfe` (maxLength 50), link "Disponiveis para programacao" |
| 475 link DISP | Botao presente: `ajaxEnvia('DISP', 1)` |

#### Fase 2 — Navegacao nas secoes internas

**903 → Certificados Digitais (ssw1970):**
| Campo | Valor |
|-------|-------|
| CNPJ | 62.312.605/0001-75 (CarVia) |
| Certificadora | Secretaria da Receita Federal do Brasil - RFB |
| Validade | **21/08/26 (VALIDO — 6 meses restantes)** |
| RNTRC | 58506755 |

**CONCLUSAO**: Certificado **OK**. NAO e problema de certificado.

**903 → Emissao de CTRCs (ssw2688):**
| Campo | Valor | Observacao |
|-------|-------|-----------|
| Nao busca XML nos Portais NF-e/CT-e | **0000 a 0000** (HHMM) | Padrao doc = 0000-0600. Com 0000-0000 a funcionalidade pode estar **desativada** |

**CONCLUSAO**: Configuracao **suspeita**. O intervalo de "nao busca" deveria ter pelo menos 1h (ex: 0000-0600). Com 0000-0000, o SSW pode interpretar como funcionalidade desativada.

**475 → Disponiveis para programacao (ssw0094):**
| Resultado | Detalhes |
|-----------|----------|
| **NENHUM REGISTRO ENCONTRADO** | Tela funciona corretamente (colunas: CNPJ, Fornecedor, Pedido, NFe, Emissao, CNPJ Destino, Destinatario, CFOP, Valor NFe, Chave NFe) mas nao ha dados |

**CONCLUSAO**: A tela existe e funciona. O problema e que **nao ha XMLs capturados pelo SSW**.

#### Fase 3 — Secoes adicionais da 903

**903 → Autorizacao e operacao com Pre-CTRC (ssw1959):**
| Configuracao | Valor | Significado |
|-------------|-------|-------------|
| Tabela Generica | S | Usa tabela generica |
| Sem pesagem | S | Nao exige pesagem |
| Sem cubagem | S | Nao exige cubagem |
| Sem recubagem | S | Nao exige recubagem |
| Sem Romaneio/Packing | S | |
| Sem captura SSWBAR | S | |
| **Modo de envio ao SEFAZ** | **M (Manual)** | **CONFIRMADO: Rafael clica "Enviar" na 004** |
| Pre-CTRC Manifesto (020) | N | |
| Pre-CTRC Saida (025) | N | |
| Pre-CTRC Romaneio (035) | N | |

**903 → Operacao (ssw1960) — Destaques:**
| Configuracao | Valor |
|-------------|-------|
| CTRB/OS obrigatoria (todos) | N (nenhum tipo obrigatorio) |
| Evitar duplicidade CT-e em MDF-e | S |
| **Emitir auto Subcontrato/Redespacho na chegada** | **N** |
| Imprime DACTE para comprovar entrega | S |
| Captura dados recebedor (038/Mobile) | C (por cliente) |
| Custo transferencia | R$0,15/ton/Km |
| Evento CTRB PF/PJ | 5101 (Frete Transf. Veiculos Terceiros) |
| Evento pedagio | 5403 (Pedagios) |
| Bloqueio CTRC mesma NF (opc 4) | 1 dia |
| Bloqueio CTRC mesma NF (opc 6) | 15 dias |

**903 → Outros (ssw1972):**
| Configuracao | Valor |
|-------------|-------|
| Custo seguro (% vlr mercadoria) | 0,030 (3%) |
| Custo GRIS (% vlr mercadoria) | 0,000 |
| Paga comissao sobre CTRCs | **L (Liquidado)** — so paga quando liquidar |
| Retirar ICMS da base remun agregado | N |
| Reter Previdencia Social carreteiros | N |
| Reter SEST/SENAT carreteiros | N |
| Controle orcamentario | N |
| Aprovacao centralizada despesas | N |
| Aprovacao centralizada pedidos | N |
| **CNPJ tag autXML** | **(VAZIO!)** |

### Diagnostico Consolidado (revisado 21/02/26 13:45)

**O que sabemos com certeza:**

| Fato | Status | Fonte |
|------|--------|-------|
| Certificado digital valido | **OK** (vence 21/08/26) | 903/Certificados (Playwright) |
| Parceiros emitem CT-e com CNPJ CarVia | **SIM** | Confirmado pelo Rafael |
| IE ativa (necessaria para DFe) | **PROVAVELMENTE OK** — CarVia emite CT-e, logo IE esta ativa | Inferencia logica |
| 475 Disponiveis — com filtro padrao | **VAZIO** | Playwright |
| 475 Disponiveis — com "Mais de 90 dias" | **VAZIO** | Playwright |
| 475 Disponiveis — sem filtro "minha unidade" | **VAZIO** (pagina em branco) | Playwright |

**O que NAO sabemos:**

| Duvida | Por que nao sabemos |
|--------|---------------------|
| Horario 0000-0000 desativa a busca? | Ambiguo: pode ser "sem blackout = busca 24h" OU "invalido = desativado". Documentacao diz minimo 1h, mas nao esclarece o caso 0000-0000 |
| DFe esta ativo no servidor SSW? | Nao temos acesso administrativo. Opcao 920 (IE/dominios) nao abre no login do rafael |
| Ha outra configuracao que bloqueia? | Podem existir configs de servidor que nao aparecem nas telas |

**CORRECAO**: O campo "CNPJ tag autXML" (903/Outros, vazio) NAO e relevante para receber XMLs. Esse campo autoriza CNPJ adicional a baixar XMLs que a CarVia EMITE. Nao afeta a busca DFe de documentos de terceiros.

**CONCLUSAO**: O servico DFe (busca automatica de XMLs no portal SEFAZ) **NAO esta funcionando** para o dominio CV1. A 475 "Disponiveis para programacao" esta vazia independente de filtros — ZERO documentos foram capturados. A causa exata requer contato com o suporte SSW.

#### Fase 4 — Testes de filtro na 475 (21/02/26)

| Teste | Filtro | Resultado |
|-------|--------|----------|
| Padrao | Ultimos 90 dias + Destinatario minha unidade | NENHUM REGISTRO |
| Mais de 90 dias | Historico completo + Destinatario minha unidade | NENHUM REGISTRO |
| Sem filtro unidade | Toggle "Destinatario minha unidade" desligado | Pagina em branco (sem grid) |
| Ambos | Sem filtro unidade + Mais de 90 dias | NENHUM REGISTRO |

**Conclusao filtros**: NAO e problema de filtro. Nenhum XML existe no sistema.

### Proximos passos da investigacao

| # | Acao | Prioridade | Status |
|---|------|-----------|--------|
| ~~I1~~ | ~~Ajustar "Nao busca XML" para 0000-0600~~ | ~~ALTA~~ | INCERTO se e a causa — precisa confirmar com SSW |
| I2 | Importar XML manualmente via 608 para testar pipeline | MEDIA | Precisa de arquivo XML real de CT-e de parceiro |
| ~~I3~~ | ~~Confirmar com parceiros se emitem com CNPJ CarVia~~ | ~~MEDIA~~ | **CONFIRMADO: SIM** |
| **I4** | **Contatar suporte SSW**: "(41)3336-0877 — Perguntar se DFe esta ativo para dominio CV1" | **ALTA** | PENDENTE |
| I5 | Verificar opcao 920 (IE/dominios) — nao acessivel pelo login rafael | MEDIA | Requer perfil admin ou suporte SSW |
| I6 | Testar alterar horario 0000-0000 para 0000-0600 apos confirmar com SSW | MEDIA | Aguarda I4 |

### Achados bonus da investigacao

**Confirmados via 903:**
- **G6 RESOLVIDO**: Modo SEFAZ = **M (Manual)** — Rafael clica manualmente, nao e automatico
- **Comissao paga quando liquidar** (nao quando emitir) — impacto: comissao so e paga se fatura for liquidada na 457
- **Emitir auto Subcontrato na chegada = N** — nao gera subcontrato automaticamente quando veiculo chega
- **Eventos financeiros configurados**: CTRB PF/PJ = 5101, Pedagio = 5403

---

## GAPS CONSOLIDADOS

### Operacionais (o que faz mas com problema)

| # | Gap | Prioridade | Onde resolver |
|---|-----|-----------|---------------|
| G1 | Cubagem por modelo de moto (cotacao) | ALTA | Tabela interna + opcao 423 |
| G2 | Tabela de carga direta (420) | MEDIA | Opcao 420 + fluxo 072/035/020/025 |
| G3 | Conferir resultado/comissao | ALTA | Opcoes 101, 056 rel.031, 449 |
| G4 | Registro formal subcontrato carga direta (072) | MEDIA | Opcao 072 (so carga direta) |
| G5 | Frete nao calcula automaticamente no CTe | ALTA | Diagnostico tabelas 402/403/420 |
| ~~G6~~ | ~~Modo envio SEFAZ (A/M/S)~~ | ~~RESOLVIDO~~ | **M (Manual)** — confirmado via Playwright |
| G7 | Registro de chegada (030) — quem faz? | MEDIA | Definir com parceiros |
| G8 | Romaneio (035) para carga direta | MEDIA | POP-D02 |

### Processos nao implantados (N1-N7)

| # | Gap | Prioridade | Risco |
|---|-----|-----------|-------|
| G9 | CTe subcontratacao nao conferido (N1) | **CRITICA** | Paga sem conferir + nao aparece |
| G10 | Contas a pagar nao registrado (N2) | ALTA | Sem controle financeiro |
| G11 | Custo extra nao registrado (N3) | MEDIA | Perde margem |
| G12 | Entrega sem comprovante (N4) | ALTA | Risco juridico/seguro |
| G13 | Pagamento fora do SSW (N5) | ALTA | Sem rastreio |
| G14 | Recebimento sem baixa (N6) | ALTA | Contas a receber impreciso |
| G15 | Sem rastreio de entrega (N7) | MEDIA | Sem visibilidade |

### Conhecimento

| # | Gap | Impacto |
|---|-----|---------|
| K1 | Carga direta formalmente | Nao expande operacao |
| K2 | Opcao 072 (contratacao) | Risco ANTT em carga direta |
| K3 | Opcoes 101/056/449 (resultado) | Nao acompanha rentabilidade |
| K4 | Por que frete nao calcula no CTe | Trabalho manual desnecessario |
| K5 | Opcao 160 (GNRE) — confirmar regime tributario | Compliance fiscal |
| K6 | Opcao 475 (contas a pagar) | Nao confere CT-es recebidos |
| K7 | Opcao 486 (CCF) | Nao controla saldo fornecedor |
| K8 | Opcao 457 (liquidar fatura) | Nao registra recebimentos |
| K9 | Opcoes 133/108 (ocorrencias) | Sem rastreio entregas |
| K10 | Opcao 038/428 (comprovantes) | Risco juridico |

---

## MAPA COMPLETO: O QUE CARVIA FAZ vs NAO FAZ

### FAZ (operacional):
```
002 (cotar) -> 004 (CTe) -> SEFAZ -> 160 (GNRE se necessario) -> 020/025 (MDF-e so frota/direta) -> 437 (faturar)
```

### NAO FAZ (pos-faturamento):
```
444 (cobranca) -> 457 (liquidar recebimento) -> 569 (conciliar banco)
475 (contas pagar) -> 476 (pagar fornecedor) -> 569 (conciliar)
038/428 (comprovante entrega) -> 133/108 (rastrear ocorrencias)
442 (custos extras) -> 101 (conferir resultado)
```

---

## DECISOES TOMADAS

1. **CIOT nao e problema para fracionado** — no modelo de redespacho, a responsabilidade e do parceiro
2. **Cubagem precisa de solucao hibrida** — tabela interna de dimensoes + configuracao na 423
3. **Frete manual no CT-e e workaround** — causa raiz esta nas tabelas 402/403/420
4. **Faturamento (437) e a UNICA etapa financeira** que Rafael faz hoje
5. **CNPJ tag autXML (903/Outros) NAO e relevante** para receber XMLs de terceiros — so afeta documentos que CarVia emite
6. **475 vazia NAO e filtro** — testado com "Mais de 90 dias" e sem "Destinatario minha unidade" — ZERO documentos no sistema
7. **Causa raiz provavel**: servico DFe nao esta ativo/configurado para dominio CV1 — requer contato com suporte SSW

---

## PROXIMAS ETAPAS

### Imediato:
- [x] Mapear fluxo completo Rafael
- [x] Identificar gaps
- [x] Registrar em documento de revisao
- [x] **Investigar CTe subcontratacao** — certificado OK, filtros testados, DFe nao funciona
- [x] **Testar filtros 475** — VAZIO independente de filtro (confirmado via Playwright)
- [ ] **Contatar suporte SSW** — (41)3336-0877 — perguntar: "O DFe esta ativo para dominio CV1?"
- [ ] **Obter XML de CT-e** de parceiro para testar importacao manual via 608

### Curto prazo:
- [ ] Diagnosticar frete nao calculado na 004 (verificar tabelas reais via Playwright)
- [ ] Validar opcao 442 via Playwright (custos extras)
- [ ] Ensinar opcoes 101/056/449 para conferencia de resultado

### Medio prazo:
- [ ] Implantar fluxo contas a pagar (475 -> 476)
- [ ] Implantar fluxo comprovante entrega (038 -> 428)
- [ ] Implantar fluxo liquidacao recebimento (457 -> 569)
- [ ] Implantar rastreio ocorrencias (133/108)
