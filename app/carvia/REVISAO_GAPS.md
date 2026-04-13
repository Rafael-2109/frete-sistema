# Revisao Completa do Modulo CarVia — Fluxograma + Gaps de Consistencia/Processo

**Data da revisao**: 03/03/2026
**Versao do modulo**: ~10.8K LOC, 24 arquivos Python, 28 templates, 11 tabelas

## STATUS DE RESOLUCAO (atualizado 12/04/2026)

**36 de 37 gaps originais resolvidos** (GAP-31 adiado por design) **+ auditoria W1-W14 concluida + Refator 2.1 implementado (12/04/2026)**.

| Sessao | Gaps | Status |
|--------|------|--------|
| 1 (P0) | GAP-05, GAP-06 | CONCLUIDO |
| 2 (P1) | GAP-02, GAP-03, GAP-15 | CONCLUIDO |
| 3 (P1) | GAP-28, GAP-29 | CONCLUIDO |
| 4 (P1) | GAP-23, GAP-11 | CONCLUIDO |
| 5 (P2) | GAP-01, GAP-04, GAP-14, GAP-17, GAP-18, GAP-24, GAP-25, GAP-35 | CONCLUIDO |
| 6 (P2) | GAP-37, GAP-09, GAP-10, GAP-12, GAP-13, GAP-21, GAP-30, GAP-34 | CONCLUIDO |
| 7 (P3) | GAP-07, GAP-08, GAP-16*, GAP-19/36, GAP-20, GAP-22, GAP-26, GAP-27, GAP-32, GAP-33 | CONCLUIDO |

*GAP-16 ja estava corrigido pelo GAP-04 (CONFERIDO bloqueia todas as acoes incluindo Recotar).
GAP-31 (historico de status) adiado — melhoria futura, requer tabela de historico dedicada.

### Migrations pendentes de execucao em producao:
- `scripts/migrations/gap10_unique_parcial_movimentacoes.py` (.sql)
- `scripts/migrations/gap34_gin_index_nfs_referenciadas.py` (.sql)
- `scripts/migrations/gap08_cascade_junction_nf_fk.py` (.sql)
- `scripts/migrations/carvia_fatura_cliente_auditoria.py` (.sql) **← novo (Refator 2.1)**

---

## AUDITORIA W1-W14 (concluida em 12/04/2026)

Plano: `/.claude/plans/shiny-wiggling-harbor.md` (v3). 12 commits aplicados.

| ID | Descricao | Status | Commit |
|----|-----------|--------|--------|
| W1 | editar_cte_valor ignora status fatura | CONCLUIDO | Sprint 1 (`55a30be0`) |
| W2 | NF cancelar/desvincular com deps | CONCLUIDO | Sprint 2 (`8a6665f8`) |
| W3 | absorvido por W2 | CONCLUIDO | — |
| W4 parte 1 | Desanexar sub + editar valor sub | CONCLUIDO | Sprint 2 (`8a6665f8`) |
| **W4 parte 2** | **Gate de valor em CONFERIR FT** | **CONCLUIDO 12/04/2026** | sessao atual (R$ 1,00 tolerancia) |
| W5 | CTe nao recalcula fatura | CONCLUIDO | Sprint 1 |
| W6 | Cancelar op cascadeia subs | CONCLUIDO | Sprint 1 + fix round 2 (`e4d6c03e`) |
| W7 | Desativar tabela/grupo | CONCLUIDO | Sprint 2 |
| W8 | Admin bypass CarviaFrete | CONCLUIDO | Sprint 0 (remocao) |
| W9 | Savepoint-per-NF importacao | CONCLUIDO | `155088c9` |
| W10 N1 | FC <-> Conciliacao bidirecional | CONCLUIDO | Sprint 2 |
| W10 N2 | FC wrapper de Conciliacao | CONCLUIDO | Sprint 3 (`452d3e9b`) + Sprint 4 (`935c1df2` FC_VIRTUAL → MANUAL) |
| W11 | NF tardia bloqueia | CONCLUIDO | Sprint 3 (interpretacao restritiva) |
| W12 | N/A (ja atomico) | — | — |
| W13 | Despesa COMISSAO imutavel | CONCLUIDO | Sprint 1 + fix round 1 |

---

## REFATORACOES 2.x

| ID | Descricao | Status |
|----|-----------|--------|
| 2.1 | **status_conferencia em CarviaFaturaCliente** | **CONCLUIDO 12/04/2026** (sessao atual — manual puro) |
| 2.2 | FC wrapper de Conciliacao | CONCLUIDO (virou W10 N2 + Sprint 4) |
| 2.3 | Bloqueios no model (pode_*) | CONCLUIDO (Sprint 0) |
| 2.4 | Remover `CarviaFrete.subcontrato_id` deprecated | **PENDENTE** (debito tecnico — Prioridade Media) |
| 2.5 | `CarviaFreteNf` junction table | **PENDENTE** (debito tecnico — Prioridade Alta, problema de performance atual via ILIKE sem indice) |
| 2.6 | Extrair `FaturaClienteService` e `FaturaTransportadoraService` | **PENDENTE** (debito tecnico — Prioridade Media, refator progressivo) |
| 2.7 | Dropar campos mortos de `CarviaOperacao` | **PENDENTE** (debito tecnico — Prioridade Baixa) |

---

## DEBITO TECNICO PENDENTE (Refators 2.4-2.7)

Documentado em `/.claude/plans/sequential-wibbling-kahn.md` Secao 4 P3. Nao abordado no ciclo de 12/04/2026 porque:

- **2.5** tem impacto potencial em performance (ILIKE sem indice) — deveria ser priorizado em sprint proprio porque e risco real. Plano v3 elevou para prioridade media, mas ainda nao foi implementado.
- **2.4** requer migracao de dados + atualizar 5+ code paths que ainda usam `CarviaFrete.subcontrato_id` (FK deprecated). Risco de divergencia entre path novo (`subcontratos` 1:N via `frete_id`) e antigo.
- **2.6** e refatoracao progressiva — pode ser feito incrementalmente em cada nova feature de fatura.
- **2.7** e limpeza simples mas baixa prioridade.

---

## MUDANCAS EM 12/04/2026 (sessao atual)

### W4 parte 2 — Gate de valor na conferencia de Fatura Transportadora
- **Arquivo**: `app/carvia/routes/fatura_routes.py:1666-1707` (`conferir_fatura_transportadora`)
- **Adicao**: Gate 2 apos Gate 1 — valida `abs(fatura.valor_total - soma(sub.valor_considerado)) <= R$ 1,00`
- **Tolerancia**: R$ 1,00 (espelhando `app/fretes/routes.py:2196`)
- **Template**: `app/templates/carvia/faturas_transportadora/detalhe.html` — badge de tolerancia + botao CONFERIDO desabilitado quando fora de tolerancia
- **Sem migration** — reutiliza campos existentes

### Refator 2.1 — Conferencia gerencial em CarviaFaturaCliente
- **Decisao**: gate MANUAL puro, sem validacao automatica. Pagamento independente.
- **Migration**: `scripts/migrations/carvia_fatura_cliente_auditoria.py` + `.sql`
  - 4 colunas: `status_conferencia`, `conferido_por`, `conferido_em`, `observacoes_conferencia`
  - Indice parcial em `status_conferencia`
- **Modelo** (`app/carvia/models/faturas.py`): campos adicionados + `pode_editar()` estendido para bloquear CONFERIDO antes de PAGA (alinhado com `CarviaFaturaTransportadora.pode_editar()`)
- **Rotas novas** (`fatura_routes.py`):
  - `POST /faturas-cliente/<id>/aprovar` — sem gate, grava auditoria
  - `POST /faturas-cliente/<id>/reabrir-conferencia` — exige motivo
- **Template** (`faturas_cliente/detalhe.html`): badge no cabecalho, secao de conferencia no card "Status e Acoes", modais de Aprovar/Reabrir, historico de conferencia em `<details>`
- **CLAUDE.md R4**: atualizado com secao "Bifurcacao venda/compra" + referencia ao gate de valor e conferencia manual

---

## 1. FLUXOGRAMA COMPLETO

### 1.1 Fluxo Principal — Do Upload a Cobranca

```
                         ┌─────────────────────────────┐
                         │     UPLOAD DE ARQUIVOS       │
                         │  (PDF + XML, multi-arquivo)  │
                         └─────────────┬───────────────┘
                                       │
                         ┌─────────────▼───────────────┐
                         │   CLASSIFICACAO AUTOMATICA   │
                         │                              │
                         │  .xml → NF-e (mod=55)?       │
                         │         CTe (mod=57)?        │
                         │  .pdf → DACTE? DANFE? Fatura?│
                         └──┬──────┬──────┬─────────┬──┘
                            │      │      │         │
              ┌─────────────▼┐ ┌───▼────┐ │   ┌─────▼──────────┐
              │  NF-e / DANFE│ │CTe XML/│ │   │  Fatura PDF     │
              │  → CarviaNf  │ │DACTE   │ │   │  (multi-pagina) │
              │  + NfItens   │ │        │ │   │                 │
              └──────┬───────┘ └───┬────┘ │   └────────┬────────┘
                     │             │      │            │
                     │    ┌────────▼──────┴─┐   ┌──────▼──────────┐
                     │    │ CNPJ == CarVia?  │   │ Beneficiario =  │
                     │    │                  │   │ transportadora?  │
                     │    ├──SIM─┐  ┌─NAO──┤   ├──SIM──┐ ┌─NAO──┤
                     │    │      │  │      │   │       │ │      │
                     │  ┌─▼──────┴┐┌▼──────┴┐ ┌▼───────┴┐┌▼──────┴┐
                     │  │Operacao ││Subcon-  │ │Fat.     ││Fat.    │
                     │  │(CTe     ││trato   │ │Transp.  ││Cliente │
                     │  │CarVia)  ││(CTe    │ │         ││        │
                     │  │RASCUNHO ││Sub)    │ │PENDENTE ││PENDENTE│
                     │  └─────────┘└────────┘ └─────────┘└────────┘
                     │       ▲          ▲           ▲          ▲
                     │       │          │           │          │
                     └───────┴──── MATCHING + LINKING ─────────┘
                          (re-linking retroativo, ordem independente)
```

### 1.2 Ciclo de Vida — Operacao (CarviaOperacao)

```
  ┌──────────┐     add subcontrato     ┌────────┐   todos subs    ┌────────────┐    fatura     ┌──────────┐
  │ RASCUNHO ├────(cotacao ok)────────►│ COTADO ├──confirmados───►│ CONFIRMADO ├───criada────►│ FATURADO │
  └─────┬────┘                         └────┬───┘                 └──────┬─────┘               └──────────┘
        │                                   │                            │                        (terminal)
        │         ┌───────────┐             │         ┌───────────┐      │
        └────────►│ CANCELADO │◄────────────┘         │ CANCELADO │◄─────┘
                  └───────────┘                       └───────────┘
                  (de qualquer exceto FATURADO)
                  Cascata: cancela subs ativos
                  ⚠ GAP-2: subs CONFERIDO nao sao cancelados
                  ⚠ GAP-3: sem downgrade ao cancelar subs
```

### 1.3 Ciclo de Vida — Subcontrato (CarviaSubcontrato)

```
  ┌──────────┐   cotacao ok    ┌────────┐   confirmacao   ┌────────────┐   fatura    ┌──────────┐   conferencia   ┌───────────┐
  │ PENDENTE ├───────────────►│ COTADO ├──manual────────►│ CONFIRMADO ├──criada───►│ FATURADO ├───────────────►│ CONFERIDO │
  └─────┬────┘                └───┬────┘                  └──────┬─────┘            └──────────┘                └───────────┘
        │                        │                               │                   (bloqueia                   (terminal)
        │     ┌───────────┐      │       ┌───────────┐           │                    cancel)
        └────►│ CANCELADO │◄─────┘       │ CANCELADO │◄──────────┘
              └───────────┘              └───────────┘
              (de qualquer exceto FATURADO)
              ⚠ GAP-4: valor_acertado editavel em CONFERIDO
              ⚠ GAP-15: re-vinculacao nao ajusta status
```

### 1.4 Ciclo de Vida — Fatura Cliente (CarviaFaturaCliente)

```
  ┌──────────┐                ┌─────────┐               ┌──────┐
  │ PENDENTE ├──(emissao)───►│ EMITIDA ├──(pagamento)─►│ PAGA │
  └─────┬────┘                └────┬────┘               └──────┘
        │                         │
        │    ┌───────────┐        │
        └───►│ CANCELADA │◄───────┘
             └───────────┘
  ⚠ GAP-1: EMITIDA nunca setado automaticamente
  ⚠ GAP-5: transicoes sem restricao de ordem (PAGA→PENDENTE via status endpoint)
  ⚠ GAP-5: status revertido sem remover movimentacao financeira
```

### 1.5 Ciclo de Vida — Fatura Transportadora (2 status independentes)

```
  Conferencia:
  ┌──────────┐               ┌────────────────┐               ┌───────────┐
  │ PENDENTE ├──────────────►│ EM_CONFERENCIA ├──────────────►│ CONFERIDO │
  └──────────┘               └───────┬────────┘               └───────────┘
                                     │             ⚠ GAP-32: so CONFERIDO
                              ┌──────▼──────┐       registra quem conferiu
                              │ DIVERGENTE  │
                              └─────────────┘

  Pagamento (independente):
  ┌──────────┐               ┌──────┐
  │ PENDENTE ├──────────────►│ PAGO │
  └──────────┘               └──────┘
```

### 1.6 Ciclo de Vida — Despesa (CarviaDespesa)

```
  ┌──────────┐               ┌──────┐
  │ PENDENTE ├──(pagamento)─►│ PAGO │
  └─────┬────┘               └──────┘
        │
        │    ┌───────────┐
        └───►│ CANCELADO │
             └───────────┘
  ⚠ GAP-6: PAGO→PENDENTE via status endpoint sem remover movimentacao
```

### 1.7 Fluxo Financeiro — Fluxo de Caixa + Extrato

```
  ┌───────────────┐    pagar     ┌─────────────────────────┐
  │ Fat. Cliente  ├────────────►│ CarviaContaMovimentacao  │
  │ (a receber)   │   CREDITO   │                          │
  └───────────────┘              │  UNIQUE(tipo_doc, doc_id)│
                                 │                          │
  ┌───────────────┐    pagar     │  Saldo = SUM(CREDITO)   │
  │ Fat. Transp.  ├────────────►│       - SUM(DEBITO)     │
  │ (a pagar)     │   DEBITO    │                          │
  └───────────────┘              │  ⚠ GAP-10: tipo=ajuste  │
                                 │    com doc_id impede     │
  ┌───────────────┐    pagar     │    multiplos ajustes     │
  │ Despesas      ├────────────►│                          │
  │ (a pagar)     │   DEBITO    └─────────────────────────┘
  └───────────────┘
```

---

## 2. GAPS IDENTIFICADOS — 37 TOTAL

### Legenda de Severidade

| Severidade | Descricao |
|------------|-----------|
| **CRITICO** | Causa inconsistencia financeira ou dados corrompidos |
| **ALTO** | Processo quebrado ou fluxo sem saida |
| **MEDIO** | Funcionalidade incompleta mas workaround existe |
| **BAIXO** | Usabilidade ou robustez |

---

### CATEGORIA 1: Consistencia de Status (6 gaps)

#### GAP-01 — Status EMITIDA nunca setado automaticamente [MEDIO]
- **Arquivo**: `fatura_routes.py:132` (criacao) e `fluxo_caixa_routes.py:185` (pagamento)
- **Problema**: Faturas cliente nascem PENDENTE e vao direto para PAGA pelo fluxo de caixa, pulando EMITIDA
- **Evidencia**: O status EMITIDA so pode ser setado via endpoint manual `atualizar_status_fatura_cliente` (linha 304)
- **Impacto**: Status EMITIDA existe no modelo mas e efetivamente morto no fluxo automatico
- **Risco**: Relatorios que filtram por EMITIDA nunca mostram dados

#### GAP-02 — Subcontratos CONFERIDO nao cancelados em cascata [ALTO]
- **Arquivo**: `operacao_routes.py:423-426`
- **Problema**: `notin_(['FATURADO', 'CANCELADO'])` inclui CONFERIDO no cancelamento, mas a regra de negocio diz que CONFERIDO e pos-FATURADO e nao deveria ser cancelavel
- **Evidencia**: Filtro exclui FATURADO e CANCELADO, mas nao CONFERIDO
- **Impacto**: Subcontratos CONFERIDO ficam vinculados a operacao CANCELADO — estado inconsistente
- **Correcao**: Adicionar CONFERIDO ao `notin_` ou bloquear cancelamento de operacao com subs CONFERIDO

#### GAP-03 — Operacao sem downgrade ao cancelar todos subcontratos [ALTO]
- **Arquivo**: `operacao_routes.py:625-650` (`cancelar_subcontrato`)
- **Problema**: Ao cancelar o ultimo subcontrato ativo, a operacao permanece CONFIRMADO com 0 subs ativos
- **Evidencia**: `confirmar_subcontrato` (linha 600) tem logica de upgrade mas `cancelar_subcontrato` nao tem logica de downgrade
- **Impacto**: Operacao CONFIRMADO sem subcontratos — estado impossivel, elegivel para faturamento mas sem valor
- **Correcao**: Apos cancelar sub, verificar se ha subs ativos. Se nao, reverter operacao para RASCUNHO ou COTADO

#### GAP-04 — valor_acertado editavel em subcontrato CONFERIDO [MEDIO]
- **Arquivo**: `operacao_routes.py:653-676` (`atualizar_valor_subcontrato`)
- **Problema**: Nenhuma validacao de status antes de alterar valor_acertado
- **Evidencia**: Endpoint aceita qualquer sub que pertenca a operacao, sem checar status
- **Impacto**: Alterar valor de sub CONFERIDO contradiz semantica de conferencia finalizada

#### GAP-05 — Transicao de status de fatura cliente sem restricao + desync financeiro [CRITICO]
- **Arquivo**: `fatura_routes.py:304-311` e `fluxo_caixa_routes.py:268-275`
- **Problema**: Endpoint `atualizar_status_fatura_cliente` permite qualquer transicao (PAGA→PENDENTE) sem remover movimentacao em `carvia_conta_movimentacoes`
- **Evidencia**: Linha 310 — `fatura.status = novo_status` sem validacao de origem. O endpoint correto seria `api_fluxo_caixa_desfazer` que remove a movimentacao
- **Impacto**: Saldo da conta fica inconsistente — movimentacao CREDITO permanece mas fatura volta para PENDENTE
- **Correcao**: Validar transicoes permitidas OU ao reverter status PAGA, chamar logica de desfazer

#### GAP-06 — Despesa status revertido sem remover movimentacao [CRITICO]
- **Arquivo**: `despesa_routes.py:207-233`
- **Problema**: Identico ao GAP-05 mas para despesas
- **Evidencia**: `despesa.status = novo_status` aceita PAGO→PENDENTE sem chamar `api_fluxo_caixa_desfazer`
- **Impacto**: Movimentacao DEBITO permanece mas despesa mostra PENDENTE

---

### CATEGORIA 2: Integridade Referencial (4 gaps)

#### GAP-07 — Operacao sem exclusao mas com cascade delete-orphan [BAIXO]
- **Arquivo**: `models.py:192-197`
- **Problema**: `cascade='all, delete-orphan'` nos subcontratos, mas nao existe rota de exclusao de operacao
- **Impacto**: Cascade nunca acionado. Risco real: re-vinculacao de sub deixa operacao anterior orfao (composto com GAP-03)

#### GAP-08 — Junction carvia_operacao_nfs sem ondelete CASCADE [BAIXO]
- **Arquivo**: `models.py:241-246`
- **Problema**: FK `nf_id` sem `ondelete='CASCADE'`
- **Impacto**: Exclusao direta de NF via SQL deixaria junctions orfas. Sem rota de exclusao via app, risco apenas operacional

#### GAP-09 — Itens de fatura com FKs NULL permanentes sem alerta [MEDIO]
- **Arquivo**: `linking_service.py:640-645`
- **Problema**: Linking que falha gera warning no log mas nao notifica o usuario
- **Evidencia**: `stats['nfs_nao_resolvidas'] += 1` + `logger.warning(...)` — sem indicacao na UI
- **Impacto**: Itens de fatura sem operacao_id/nf_id ficam desvinculados permanentemente
- **Correcao**: Mostrar badge/alerta na tela de detalhe da fatura para itens nao resolvidos

#### GAP-10 — UNIQUE(tipo_doc, doc_id) impede multiplos ajustes [MEDIO]
- **Arquivo**: `models.py:602-604`
- **Problema**: Para `tipo_doc='ajuste'`, `doc_id` precisa ser unico. Nao ha endpoint de ajuste na UI
- **Impacto**: Se necessario dois ajustes manuais, o segundo falharia com IntegrityError
- **Correcao**: Usar timestamp ou autoincrement como doc_id para ajustes, ou remover UNIQUE para tipo_doc=ajuste

---

### CATEGORIA 3: Tratamento de Erros (5 gaps)

#### GAP-11 — Importacao armazena resultado em session Flask [ALTO]
- **Arquivo**: `importacao_routes.py:48-50`
- **Problema**: Resultado do parsing (muitos dados) armazenado na sessao. Session cookie tem ~4KB
- **Evidencia**: `session['carvia_importacao'] = resultado` — pode truncar silenciosamente
- **Impacto**: Sessao expirada ou dados truncados = perda total do trabalho de upload
- **Correcao**: Armazenar em banco (tabela temporaria) ou Redis com TTL

#### GAP-12 — Upload sem validacao de tamanho/tipo [MEDIO]
- **Arquivo**: `importacao_routes.py:22-37`
- **Problema**: Nenhuma validacao de extensao, MIME type ou tamanho de arquivo
- **Evidencia**: `conteudo = f.read()` sem limites
- **Impacto**: Arquivos invalidos causam erro nos parsers; arquivos grandes consomem memoria

#### GAP-13 — Wizard manual sem CSRF via WTForms [MEDIO]
- **Arquivo**: `operacao_routes.py:192-344`
- **Problema**: Fluxo MANUAL_SEM_CTE usa `request.form` diretamente, nao WTForms
- **Impacto**: Depende do CSRF global do Flask-WTF e do `{{ csrf_token() }}` manual no template

#### GAP-14 — Pagamento sem verificar se ja esta PAGO [MEDIO]
- **Arquivo**: `fluxo_caixa_routes.py:179-211`
- **Problema**: `api_fluxo_caixa_pagar()` verifica CANCELADO mas nao verifica se ja esta PAGO
- **Evidencia**: Fatura cliente (linha 183): checa CANCELADA. Despesa (linha 205): checa CANCELADO. Nenhum checa PAGO/PAGA
- **Impacto**: IntegrityError capturado (linha 234) mas status sobrescrito desnecessariamente. UX confusa
- **Correcao**: Adicionar `if doc.status == 'PAGA': return erro 'Ja pago'`

#### GAP-15 — Re-vinculacao de subcontrato sem ajuste de status [ALTO]
- **Arquivo**: `subcontrato_routes.py:278-306`
- **Problema**: Sub CONFIRMADO re-vinculado a nova operacao mantem status CONFIRMADO com cotacao diferente
- **Impacto**: Operacao anterior pode ficar CONFIRMADO sem subs (GAP-03 composto). Nova operacao ganha sub CONFIRMADO sem que todos seus subs estejam confirmados

---

### CATEGORIA 4: Consistencia Frontend/Backend (4 gaps)

#### GAP-16 — Botao Recotar visivel para sub CONFIRMADO [BAIXO]
- **Arquivo**: `app/templates/carvia/detalhe_operacao.html:254`
- **Problema**: `{% if sub.status not in ('FATURADO', 'CANCELADO') %}` mostra botao para CONFIRMADO
- **Impacto**: Recotar altera valor_cotado sem invalidar confirmacao — semanticamente questionavel

#### GAP-17 — Input number vs formato BR para valor_acertado [MEDIO]
- **Arquivo**: `app/templates/carvia/detalhe_operacao.html:304`
- **Problema**: `type="number"` com `step="0.01"` + backend `type=float` — browser PT-BR pode aceitar virgula
- **Impacto**: Valor com virgula (1.234,56) retorna None do `request.form.get(..., type=float)`. `valor_acertado` setado para None silenciosamente

#### GAP-18 — Wizard perde selecoes ao erro de validacao [MEDIO]
- **Arquivo**: `operacao_routes.py:219-223`
- **Problema**: Ao retornar template apos erro de valor CTe, NFs selecionadas e transportadora sao perdidas
- **Impacto**: Usuario precisa refazer todas as selecoes do wizard

#### GAP-19 — Busca de fatura transportadora limitada [BAIXO]
- **Arquivo**: `fatura_routes.py:343-347`
- **Problema**: So busca por `numero_fatura`, nao por nome/cnpj da transportadora
- **Impacto**: Comparar com faturas cliente que buscam por nome + cnpj + numero

---

### CATEGORIA 5: Processos Incompletos (4 gaps)

#### GAP-20 — Sem fluxo de exclusao para nenhuma entidade [BAIXO]
- **Problema**: Nenhum endpoint DELETE para NF, despesa ou fatura
- **Impacto**: Intencional para auditoria, mas nao documentado como decisao de design

#### GAP-21 — MANUAL_FRETEIRO sem proximo passo claro [MEDIO]
- **Arquivo**: `operacao_routes.py:159-189`
- **Problema**: Operacao criada sem subcontrato, status RASCUNHO permanente
- **Impacto**: Sem indicacao na UI de que precisa adicionar subcontrato para avancar

#### GAP-22 — Subcontrato importado sem indicacao de faturamento pendente [BAIXO]
- **Problema**: CTes subcontratados importados criam subs sem `fatura_transportadora_id`
- **Impacto**: Processo de faturamento via UI e implicito, sem alerta

#### GAP-23 — Operacao FATURADO sem caminho de correcao [ALTO]
- **Arquivo**: `operacao_routes.py:368-370`
- **Problema**: Operacao FATURADO nao pode ser editada nem cancelada. Se faturada erroneamente (ex: fatura PDF importada com matching errado), nao ha saida
- **Impacto**: Dado corrompido sem possibilidade de correcao pela UI
- **Correcao**: Implementar "desvincular fatura" que reverte operacao para CONFIRMADO

---

### CATEGORIA 6: Validacoes Ausentes (4 gaps)

#### GAP-24 — Fatura cliente com valor_total = 0 [MEDIO]
- **Arquivo**: `fatura_routes.py:121-123`
- **Problema**: `sum(float(op.cte_valor or 0))` pode ser 0 se todas ops tem cte_valor NULL
- **Impacto**: Fatura com R$ 0,00 criada no sistema

#### GAP-25 — Fatura transportadora com valor_total = 0 [MEDIO]
- **Arquivo**: `fatura_routes.py:416-418`
- **Problema**: Identico ao GAP-24 para faturas transportadora

#### GAP-26 — CNPJ sem validacao de digitos verificadores [BAIXO]
- **Arquivo**: `forms.py:15-18`
- **Problema**: `Length(min=14, max=20)` aceita strings invalidas
- **Impacto**: CNPJs invalidos gravados no banco, quebrando matching posterior

#### GAP-27 — Chave de acesso sem validacao de 44 digitos exatos [BAIXO]
- **Arquivo**: `forms.py:36`
- **Problema**: `Length(max=44)` aceita menos de 44 caracteres
- **Impacto**: Chaves parciais gravadas, quebrando dedup por chave

---

### CATEGORIA 7: Concorrencia (3 gaps)

#### GAP-28 — Race condition no numero_sequencial_transportadora [ALTO]
- **Arquivo**: `operacao_routes.py:314-318` e `subcontrato_routes.py:141-145`
- **Problema**: `MAX() + 1` sem lock — dois usuarios podem gerar mesmo numero
- **Evidencia**: Unique index parcial protege via IntegrityError, mas codigo nao trata especificamente
- **Correcao**: `SELECT ... FOR UPDATE` ou retry com tratamento de IntegrityError especifico

#### GAP-29 — Race condition no faturamento de operacoes [ALTO]
- **Arquivo**: `fatura_routes.py:108-114`
- **Problema**: `SELECT ... WHERE status='CONFIRMADO' AND fatura_id IS NULL` sem `FOR UPDATE`
- **Impacto**: Mesma operacao vinculada a duas faturas simultaneas

#### GAP-30 — Duplo clique na confirmacao de importacao [MEDIO]
- **Arquivo**: `importacao_routes.py:60-83`
- **Problema**: Session limpa apos salvar, mas duas requests simultaneas podem processar antes do pop
- **Impacto**: Duplicatas parciais (UNIQUE protege NFs/faturas, mas CTes sem chave podem duplicar)

---

### CATEGORIA 8: Auditoria (3 gaps)

#### GAP-31 — Mudancas de status sem registro historico [MEDIO]
- **Problema**: Nenhuma tabela de historico de status para operacoes, subcontratos ou faturas
- **Impacto**: Impossivel saber quem mudou status ou quando (exceto pagamento com pago_por/pago_em)

#### GAP-32 — So CONFERIDO registra quem conferiu [MEDIO]
- **Arquivo**: `fatura_routes.py:619-628`
- **Problema**: EM_CONFERENCIA e DIVERGENTE nao registram autor
- **Impacto**: Sem rastreabilidade de quem marcou como DIVERGENTE

#### GAP-33 — Alteracao de cubagem sem auditoria [BAIXO]
- **Arquivo**: `api_routes.py:567-621`
- **Problema**: Altera peso_cubado/peso_utilizado sem registrar quem alterou ou valor anterior
- **Impacto**: Peso alterado afeta cotacao — sem rastro de alteracao

---

### CATEGORIA 9: Outros Gaps de Consistencia (4 gaps)

#### GAP-34 — Full table scan em vincular_nf_a_operacoes_orfas [MEDIO]
- **Arquivo**: `linking_service.py:272-311`
- **Problema**: Carrega TODAS operacoes com nfs_referenciadas_json em memoria
- **Impacto**: Degrada com crescimento do banco (chamado a cada importacao de NF)

#### GAP-35 — Edicao de vencimento permitida em fatura PAGA [MEDIO]
- **Arquivo**: `fatura_routes.py:256-288`
- **Problema**: Bloqueia CANCELADA mas nao PAGA
- **Impacto**: Editar vencimento de fatura paga nao tem sentido operacional

#### GAP-36 — Busca em listar_faturas_transportadora incompleta [BAIXO]
- **Arquivo**: `fatura_routes.py:343-347`
- **Problema**: So busca por numero_fatura (fatura cliente busca por nome + cnpj + numero)

#### GAP-37 — Ordenacao por valor_final usa valor_cotado [MEDIO]
- **Arquivo**: `subcontrato_routes.py:59`
- **Problema**: `'valor_final': CarviaSubcontrato.valor_cotado` — deveria ser `COALESCE(valor_acertado, valor_cotado)`
- **Evidencia**: `valor_final` e @property Python, nao pode ser usado em ORDER BY SQL
- **Impacto**: Ordenacao enganosa quando existem valor_acertado diferentes

---

## 3. MATRIZ DE PRIORIZACAO

### P0 — CRITICO (corrigir imediatamente)

| Gap | Descricao | Arquivo |
|-----|-----------|---------|
| GAP-05 | Status fatura revertido sem remover movimentacao financeira | `fatura_routes.py:304-311` |
| GAP-06 | Status despesa revertido sem remover movimentacao financeira | `despesa_routes.py:207-233` |

### P1 — ALTO (corrigir em breve)

| Gap | Descricao | Arquivo |
|-----|-----------|---------|
| GAP-03 | Operacao CONFIRMADO sem subcontratos apos cancel | `operacao_routes.py:625-650` |
| GAP-23 | Operacao FATURADO sem caminho de correcao | `operacao_routes.py:368-370` |
| GAP-28 | Race condition numero_sequencial | `operacao_routes.py:314-318` |
| GAP-29 | Race condition faturamento duplo | `fatura_routes.py:108-114` |
| GAP-02 | Subs CONFERIDO em operacao CANCELADO | `operacao_routes.py:423-426` |
| GAP-15 | Re-vinculacao sem ajuste de status | `subcontrato_routes.py:278-306` |
| GAP-11 | Dados de importacao na session Flask | `importacao_routes.py:48-50` |

### P2 — MEDIO (melhorar)

| Gap | Descricao |
|-----|-----------|
| GAP-01 | Status EMITIDA morto no fluxo |
| GAP-04 | valor_acertado editavel em CONFERIDO |
| GAP-09 | Itens fatura sem FKs sem alerta na UI |
| GAP-10 | UNIQUE impede multiplos ajustes |
| GAP-12 | Upload sem validacao tamanho/tipo |
| GAP-13 | Wizard sem WTForms/CSRF |
| GAP-14 | Pagamento sem verificar ja-PAGO |
| GAP-17 | Input number vs formato BR |
| GAP-18 | Wizard perde selecoes ao erro |
| GAP-21 | MANUAL_FRETEIRO sem proximo passo |
| GAP-24/25 | Faturas com valor R$ 0 |
| GAP-30 | Duplo clique importacao |
| GAP-31 | Sem historico de status |
| GAP-34 | Full table scan linking |
| GAP-35 | Edicao vencimento em fatura PAGA |
| GAP-37 | Ordenacao valor_final incorreta |

### P3 — BAIXO (considerar)

| Gap | Descricao |
|-----|-----------|
| GAP-07 | Cascade nunca acionado |
| GAP-08 | Junction sem ondelete CASCADE |
| GAP-16 | Botao Recotar em CONFIRMADO |
| GAP-19/36 | Busca limitada em listas |
| GAP-20 | Sem exclusao (pode ser intencional) |
| GAP-22 | Sub importado sem alerta faturamento |
| GAP-26 | CNPJ sem validacao digitos |
| GAP-27 | Chave acesso sem validacao 44d |
| GAP-32 | Auditoria parcial em conferencia |
| GAP-33 | Cubagem sem auditoria |

---

## 4. NOTAS

- Todos os gaps foram verificados contra o codigo em 03/03/2026
- Numeros de linha referem-se aos arquivos em `app/carvia/routes/` e `app/carvia/`
- Nao ha gaps de performance incluidos nesta revisao
- Cada gap tem arquivo e linha para referencia direta caso se deseje implementar correcoes
