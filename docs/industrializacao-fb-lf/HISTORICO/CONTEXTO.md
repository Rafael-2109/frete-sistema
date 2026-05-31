# CONTEXTO — Industrialização FB↔LF

> **PROTOCOLO DE RETOMADA EM NOVA SESSÃO**
>
> Esta pasta contém o roadmap auto-executável do projeto "Industrialização FB↔LF" da Nacom Goya.
> Antes de executar qualquer ação, leia os 3 arquivos nesta ordem:
>
> 1. Este arquivo (`CONTEXTO.md`) — entende o projeto
> 2. `STATUS.md` — estado atual, última task feita
> 3. `ROADMAP_TASKS.md` — próxima task a executar
>
> **Nunca** comece executando sem ler os 3.

## Atores do projeto

- **Rafael (operador)**: executa no Odoo (UI + acompanha scripts), toma decisões de produto/operação, opera testes do piloto end-to-end (PO, MO, NF). Tem acesso admin ao Odoo.
- **Claude (assistente técnico)**: escreve scripts, valida via XML-RPC/SQL, propõe próximos passos, mantém STATUS.md atualizado, monta pacotes de validação para envio ao Fiscal.
- **Fiscal/Contábil (validador final)**: recebe pacote pós-piloto (S2) e dá parecer go/no-go. Não acompanha o dia a dia.

**Sem TI separada, sem CIEL IT consultor, sem treinamento de times**. Rafael+Claude operam tudo. CIEL IT é caixa-preta — descobrimos o comportamento durante o T13 (teste end-to-end com produto qualquer).

---

## O que é este projeto

**Problema**: a NF de retorno de industrialização da LF para a FB **soma PA + componentes consumidos no estoque FB**, inflando o ativo MATERIAL DE EMBALAGEM/PRODUTO-ACABADO indevidamente. Sintoma quantificado em R$ 785.569,62 apenas para o produto MOLHO SHOYU PET 12x1,01L; total estimado em alguns milhões.

**Causa**: as DFe de retorno da LF caem no `picking_type=1 RECEB/FB` (genérico de fornecedor) que entra tudo em FB/Estoque sem distinguir CFOPs. O fluxo de subcontracting do Odoo nunca foi efetivamente ativado.

**Escopo**: forward-only — não corrige o passado, implementa o fluxo correto daqui pra frente. Passivo histórico tratado em projeto separado.

**Solução adotada (Opção 2 — Inter-company)**:
- PO de compra FB→LF dispara SO espelhado em cmp=LF via módulo `sale_purchase_inter_company_rules` (já instalado).
- SO LF + Make-To-Order + BoM normal 3695 dispara MO em cmp=LF.
- PCP LF aponta MO em cmp=LF normalmente (consumo, perda, produção).
- Componentes da FB são tratados como "estoque de terceiros" via location dedicada em cmp=LF.
- NF de retorno LF→FB com 3 CFOPs por linha (5124 PA + 5902 consumo+perda + 5903 sobra) — **Caminho C** aprovado por Fiscal/Contábil.
- Recebimento FB usa `picking_type=52 RECEB/FB/IND` (não o genérico 1).

---

## Empresas e IDs constantes

| Code | ID | CNPJ | Nome |
|---|---|---|---|
| FB | 1 | 61.724.241/0001-78 | NACOM GOYA - FB |
| SC | 3 | 61.724.241/0001-259 | NACOM GOYA - SC (fora do escopo) |
| CD | 4 | 61.724.241/0001-330 | NACOM GOYA - CD (fora do escopo) |
| LF | 5 | 18.467.441/0001-63 | LA FAMIGLIA - LF |

| res.partner | ID |
|---|---|
| LF como partner em cmp=FB | 35 |

| Locations Odoo | ID |
|---|---|
| FB/Estoque | 8 |
| LF/Estoque | 42 |
| FB/Indisponivel | 31088 |
| LF/Indisponivel | 31091 |
| Estoque Virtual/Em Trânsito (Industrialização) | 26489 |
| Locais Fisicos/Local de subcontratação | 30713 |
| **LF/Materiais de Terceiros** (T02 ✅) | **31092** |
| **LF/PA de Terceiros** (T03 ✅) | **31093** |

### Aprendizado de projeto (2026-05-28, T08)

**`stock.rule` cross-company NÃO é permitido pelo Odoo padrão**: `_check_company` rejeita rule cmp=X com `location_dest_id` em cmp=Y. Erro: "Empresas incompatíveis".

Implicação para Opção 2 (D10/D11): a movimentação física FB→LF/Materiais de Terceiros NÃO pode ser modelada como stock.rule cmp=FB. Tem que vir:
- (a) automaticamente do módulo `mrp_subcontracting + sale_purchase_inter_company_rules` no fluxo end-to-end (T13 valida), ou
- (b) via location global como ponte (re-discutir D11), ou
- (c) via NF inter-company (que é o caminho do D10 já, mas precisamos confirmar que cobre todas as etapas).

| Picking Types | ID | Cmp | Direção |
|---|---|---|---|
| RECEB/FB (genérico) | 1 | FB | incoming |
| FB/SAI/IND (saída industrialização) | 53 | FB | outgoing |
| RECEB/FB/IND (entrada retorno) | 52 | FB | incoming |
| LF/RECEB/IND (entrada remessa LF) | 64 | LF | incoming |
| FB Subcontratação (inativa) | 74 | FB | mrp_operation |
| RES Reposição p/ subcontratação | 75 | FB | outgoing |
| LF Subcontratação (inativa) | 80 | LF | mrp_operation |
| LF Reposição p/ subcontratação (inativa) | 81 | LF | outgoing |

| Routes | ID | Empresa |
|---|---|---|
| Fabricar (LF) | 134 | LF |
| FB Reposição p/ subcontratação | 162 | FB |
| LF Reposição p/ subcontratação | 166 | LF |
| Subcontracting (global, se existir) | a verificar | global |

| Produto piloto | ID Odoo |
|---|---|
| product.product 4870112 (MOLHO SHOYU PET 12X1,01L) | 27834 |
| product.template 4870112 | 42282 |
| BoM 14833 subcontract (cmp=FB, subcontractor=LF) — não usada na Opção 2 (D13) | 14833 |
| **BoM 3695 normal (cmp=LF) — usada na Opção 2 — consumption=strict pós-T10** | **3695** |
| **BoM 3646 (filha — semi BATELADA DE SHOYU)** | **3646** |
| Semi-acabado BATELADA DE SHOYU (default_code=3800018, subprocesso interno LF) | 29986 (tmpl 44550) |
| Supplierinfo PA com is_subcontractor=True (LF, R$ 35,00) | 6319 |

### Estrutura BoM hierárquica do piloto (D17)

```
PA: MOLHO SHOYU PET 12X1,01L (id=27834, tmpl=42282)
└─ BoM 3695 (LF normal, consumption=strict)
   ├─ BATELADA DE SHOYU (semi-acabado LF, id=29986) — 12,818 kg/cx
   │  └─ BoM 3646 (filha, LF normal)
   │     ├─ 8 químicos vindos da FB (acido_citrico, benzoato, corante,
   │     │     sal, sorbato, antiespumante, açúcar, aroma)
   │     ├─ MOLHO SHOYU TRADICIONAL (105000022, MP vindo da FB)
   │     └─ ÁGUA (104000017) — único insumo próprio LF
   ├─ 7 embalagens (frasco, tampa, caixa, rótulo, etiqueta, filme, fita)
   │  → todas vindas da FB (210030xxx, 207210014, 208000xxx)
   └─ (sem outros componentes)
```

**Remessa FB→LF (CFOP 5901)**: 17 componentes = 7 emb + 9 quim + 1 MP shoyu_tradicional.
**Retorno LF→FB (CFOPs)**: 1 linha 5124 (PA) + 17 linhas 5902 (consumido + perda) + 0..N linhas 5903 (sobras).
**BATELADA**: nunca aparece em NF; é puramente intra-MO LF.

| Contas contábeis FB | ID | Code | Nome |
|---|---|---|---|
| Material de Embalagem (estoque) | 22289 | 1150100002 | MATERIAL DE EMBALAGEM |
| Produto-Acabado | 22294 | 1150100007 | PRODUTO-ACABADO |
| Recebimento Físico Fiscal (transitória) | 26842 | 1150100011 | RECEBIMENTO FISICO FISCAL |
| Material em Terceiros | a buscar | 1150200001 | MATERIAL EM TERCEIROS |

---

## Decisões já aprovadas (resumo)

| # | Decisão |
|---|---|
| 1 | Caminho C — CFOP 5902 cobre consumo+perda; 5903 cobre apenas sobra |
| 2 | Apenas água é insumo próprio LF; resto vem da FB |
| 3 | Valor agregado LF = R$ 35,00/cx via supplierinfo |
| 4 | CIEL IT mapeia CFOP por linha |
| 5 | Opção B strict (bloquear consumo > remessa via consumption=strict) |
| 6 | BoMs subcontract dos outros 29 PAs sem revisão prévia |
| 7 | Escopo FB↔LF apenas (SC e CD fora) |
| 8 | 1 PO piloto de 10 cx do 4870112 |
| 9 | Virada gradual após validação Fiscal+Contábil |
| 10 | **Opção 2 (inter-company)** — MO fica em cmp=LF, PCP LF aponta no sistema |
| 11 | **Criar 2 estoques novos** (LF/Materiais de Terceiros + LF/PA de Terceiros), não renomear 30713 |
| 12 | **Criar regras nas rotas 162 e 166** |
| 13 | BoM 14833 ATIVA confirmada (sequence=25 prioritária) |
| 14 | Remessa complementar = PO complementar (nunca avulso) |
| 15 | PCP LF revisa BoMs no rollout |

Detalhes em `DECISOES.md`.

---

## Decisões em aberto

| # | Decisão | Quem decide |
|---|---|---|
| A1 | Linha 7 da BoM 14833 (X105000022 SHOYU TRADICIONAL) é semi-acabado intra ou componente FB? | PCP LF |
| A2 | Quais as contas contábeis padrão por categoria de produto (MP, semi-acabado)? Já mapeadas: embalagem (1150100002) e PA (1150100007); faltam MP/semi-acabado | Contador |
| A3 | Janela do piloto (qual semana exata) | Operação + Fiscal |
| A4 | Confirmar `intercompany_user_id=OdooBot` é suficiente ou precisa usuário dedicado | TI |

Detalhes em `ABERTOS.md`.

---

## Como executar tasks

Cada task em `ROADMAP_TASKS.md` tem o formato:

```
## T{NN} — {Título}
**Status**: ⬜ pending | 🟡 in_progress | ✅ done | ❌ failed
**Pré-requisitos**: T{XX}, T{YY}
**Bloqueia**: T{ZZ}
**Executor**: TI / Operação / Script
**Como executar**: comandos exatos
**Validação**: como confirmar que deu certo
**Saída esperada**: o que se espera ver
**Em caso de falha**: o que fazer
```

Workflow:
1. Identificar próxima task com status pending e pré-requisitos done.
2. Marcar como in_progress em `STATUS.md`.
3. Executar conforme instruções.
4. Documentar resultado em `testes/T{NN}-resultado.md`.
5. Marcar como done ou failed.
6. Atualizar `STATUS.md`.

---

## Arquivos da pasta

- `CONTEXTO.md` (este) — visão geral e IDs constantes
- `STATUS.md` — estado atual, próxima task, histórico recente
- `ROADMAP_TASKS.md` — tasks numeradas T01 em diante
- `DECISOES.md` — todas decisões aprovadas com data e responsável
- `ABERTOS.md` — pendências de decisão
- `scripts/` — scripts Python versionados (dry-run + execute)
- `testes/` — resultado de cada task executada (1 arquivo por task)
- `decisoes/` — fundamentação de cada decisão (1 arquivo por decisão maior)

---

## Como acionar suporte humano

Quando uma task exige decisão humana:
1. Documentar a questão em `ABERTOS.md`
2. Marcar a task como 🟡 `blocked_human` em `STATUS.md`
3. Esperar resposta

Quando uma task falha:
1. Documentar em `testes/T{NN}-falha-{data}.md`
2. Marcar como ❌ `failed` em `STATUS.md`
3. Não executar a próxima — esperar análise

---

## Versionamento

Este projeto é versionado em Git. Commits por marco:
- `feat(industrializacao): setup S0 concluído`
- `feat(industrializacao): piloto S1 executado`
- `docs(industrializacao): ata validação fiscal/contábil`
- etc.

Última versão de plano amplo: `roadmap_v3.0` (em /tmp; foi consolidado para esta pasta).

---

## Estimativa de esforço

| Item | Valor |
|---|---|
| Sessões Claude até final do piloto | 5–6 |
| Sessões Claude até rollout completo (30 PAs) | 7–10 |
| Tempo calendário até final do piloto | 1–2 semanas |
| Tempo calendário até rollout completo | 5–7 semanas |
| Validação Fiscal (S2) | 3–7 dias (depende do Fiscal) |

O cronograma é controlado por: (a) velocidade SEFAZ/DFe, (b) disponibilidade do Rafael, (c) SLA do Fiscal pós-piloto.
