<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-24
-->
# Spec — Calibração da proatividade do Agente Web (evasão → meio-termo por risco)

> **Papel:** especificação de design para corrigir a evasão do Agente Web — ele passou a recusar
> operações simples quando não há skill que as cubra (ou a skill é read-only), em vez de executá-las
> com salvaguarda. A correção reconcilia as regras de escrita do `system_prompt.md` em torno de um
> **eixo único de risco/reversibilidade** (não "existência de skill"), eliminando a contradição que
> produz a recusa. **Abra quando:** for revisar (4-mãos) ou implementar a calibração do prompt.
> **Status:** PROPOSTA APROVADA (2026-06-24, sessão dev 4-mãos) — implementação pendente.

## Indice

- [Contexto](#contexto)
- [Sintoma e evidência](#sintoma-e-evidência)
- [Diagnóstico: contradição entre regras, não excesso de cautela](#diagnóstico-contradição-entre-regras-não-excesso-de-cautela)
- [Princípio único: salvaguarda por risco (a SOT)](#princípio-único-salvaguarda-por-risco-a-sot)
- [Mudanças regra-a-regra](#mudanças-regra-a-regra)
- [Dependências fora do prompt](#dependências-fora-do-prompt)
- [Governança (PAD-CTX)](#governança-pad-ctx)
- [Critérios de sucesso](#critérios-de-sucesso)
- [Fora de escopo (YAGNI)](#fora-de-escopo-yagni)

## Contexto

O Agente Web (`app/agente/`, Claude Agent SDK) operava de forma "inconsequente" no passado —
ex.: UPDATE no banco sem confirmação (IMP-2026-05-21-001, IMP-2026-06-22-003), operação destrutiva
em massa sem salvaguarda (IMP-2026-06-19-006). A resposta foi endurecer o `system_prompt.md` com
salvaguardas de escrita (cannot_do, R3, R11/.1/.2, R12.1/.2). O pêndulo passou do ponto: o agente
ficou **evasivo** — recusa operações simples e reversíveis quando não há skill que as cubra, ou
quando a skill existe mas é read-only.

O usuário (dono do sistema) pediu calibração: um meio-termo que não o obrigue a "criar skill para
tudo", confiando nas salvaguardas pós-fato já existentes (avaliação de scripts ad-hoc +
Improvement Dialogue D8).

## Sintoma e evidência

Medição em PROD (2026-06-24):

- **Não é trava universal.** `agent_adhoc_script` registrou **1.456 execuções ad-hoc** na semana de
  22/06 (7 usuários), volume estável/crescente — o agente age muito quando decide agir.
- **A evasão é cirúrgica**, no caso "skill existe mas não cobre a escrita". Exemplo do próprio dia:
  **IMP-2026-06-24-002 (severity `critical`)** — *"gerindo-carvia: skill é read-only e não suporta
  UPDATE em carvia_fretes"*. A usuária (Barbara) queria atualizar o `valor_cotado` de **um** frete;
  a skill existe mas é read-only; o agente **registrou e parou** em vez de executar com salvaguarda.

## Diagnóstico: contradição entre regras, não excesso de cautela

O `system_prompt.md` v4.4.0 **já tem o antídoto** — mas ele é contraditado:

- **R9** ("skill inexistente não é motivo para RECUSAR… execute pelo caminho disponível com
  salvaguardas") cobre apenas o caso **skill INEXISTENTE**.
- Quando a skill **existe porém não cobre a escrita** (read-only/incompleta), entram **R12.2**
  (*"existe skill? Use — NUNCA manipule as tabelas via SQL cru… verifique o inventário ANTES de
  recorrer a mcp__sql de escrita ou Bash"*) e **R5** (*"Bash NÃO substitui MCP — NUNCA improvise
  SQL… use mcp__sql"*). Lidas juntas: "existe skill (mesmo read-only) ⇒ SQL/Bash proibido".
- O agente, diante de uma regra permissiva (R9) e várias proibitivas com "NUNCA", resolve a
  ambiguidade pelo lado cauteloso (L1 Segurança) → **evasão**.
- **Agravante de proporção:** ~7 regras/sub-regras de salvaguarda com linguagem "NUNCA/proibido"
  (cannot_do, R3, R11, R11.1, R11.2, R12.1, R12.2) contra **uma só** dizendo "execute mesmo assim"
  (R9). O peso retórico empurra para a recusa.

**Causa-raiz:** o agente decide pela pergunta errada — *"existe skill?"* — quando deveria decidir
por *"qual o risco/reversibilidade da operação?"*.

## Princípio único: salvaguarda por risco (a SOT)

O que decide a salvaguarda é a **natureza da operação**, não a existência de skill. A skill é o
**caminho preferido quando cobre** a operação (aplica invariantes que o SQL ignora); sua ausência
ou incompletude (read-only) **não bloqueia** — apenas muda o caminho de execução. Uma única tabela
de risco vira a fonte de verdade; todas as regras de escrita a referenciam (sem texto duplicado =
sem contradição).

| Tier | Operação | Salvaguarda | Caminho |
|------|----------|-------------|---------|
| **Leitura** | consulta | nenhuma | `mcp__sql` / skill |
| **T1** — escrita reversível e **pontual** (<50 reg.; não-fiscal; não-append-only; não-auditoria) | corrigir 1 campo, atualizar 1 frete CarVia | **preview (dry-run / antes-e-depois) + UMA confirmação** | skill se cobre; senão `mcp__sql` / script |
| **T2** — escrita em **massa** (≥50) ou sobre **histórico/auditoria** (`operador_id`, `criado_por`, datas/status de evento) | backfill, correção em lote | amostra (COUNT + 3-5 linhas) + **uma** confirmação **citando a quantidade** | skill se cobre; senão `mcp__sql` / script |
| **T3** — **irreversível/fiscal/destrutivo** (NF-e SEFAZ posted = R11; DELETE em massa; TRUNCATE; `UPDATE`/`DELETE` em tabela append-only) | alterar SO faturado; `assai_moto_evento` | confirmação **tipada por risco** (R11) **ou** operação de domínio obrigatória | skill/subagente de domínio; **SQL de escrita proibido** em append-only |

**Regra de ouro:** skill que **cobre** a operação é preferida. Skill **ausente OU read-only/
incompleta NÃO bloqueia** — execute pelo caminho disponível com a salvaguarda do tier. O "NUNCA SQL
cru" fica restrito ao que realmente exige (T3/append-only).

## Mudanças regra-a-regra

Todas no `system_prompt.md`. Versão → **4.5.0**.

### R12 — vira a tabela de risco (absorve R12.1 + R12.2)
Substituir a prosa atual de R12.1 (UPDATE/DELETE em massa) + R12.2 (preferir skill / "NUNCA SQL
cru") pela **tabela de tiers** acima + a regra de ouro. Mantém as proteções reais (massa → amostra
+ confirmação por quantidade; append-only → SQL de escrita proibido) mas **sem o "NUNCA" genérico**
que capturava T1.

### R9 — estende o alcance e aponta para R12
- **Antes:** "Skill/átomo INEXISTENTE não é motivo para RECUSAR… execute pelo caminho disponível
  (script/Bash), mantendo as salvaguardas (R3 confirmação + dry-run)."
- **Depois:** "Skill **inexistente OU que não cobre a operação (read-only / sem o modo necessário)**
  não é motivo para recusar: registre a lacuna (`register_improvement`) e **execute pelo caminho
  disponível com a salvaguarda do tier (R12)**. Registrar é fazer — nunca em vez de fazer."

### R5 — desambigua o canal (banco vs Bash)
- **Antes (bullet):** "Bash NÃO substitui MCP — NUNCA improvise SQL via `Bash python -c` contra o
  banco; use mcp__sql." (lido como "escrita ad-hoc proibida").
- **Depois:** "Para tocar o banco local use `mcp__sql` (não `Bash python -c`) — vale **leitura E
  escrita**; o evaluator do `consultando-sql` valida o DML. Script Python (Bash) é para lógica
  multi-passo / Odoo (XML-RPC) / chamar services, não para falar com o banco local direto."

Reconcilia com R9: o caminho de escrita no banco local é `mcp__sql` (tem evaluator); script é para
o que `mcp__sql` não faz. Some o "script/Bash" genérico de R9 que brigava com R5.

### Intocados (continuam fortes)
R11 + R11.1 + R11.2 (SEFAZ/NF-e posted — confirmação tipada item-a-item), R3 (separação — 1
confirmação), R3.1 (qtd_saldo=0 — confirmação tipada A/B/C), `<cannot_do>` ("modificar banco sem
confirmação"), L1 da hierarquia constitucional ("confirmar antes de operação irreversível"). Nada
de afrouxar destrutivo/fiscal/irreversível — eles **são** o T3.

## Dependências fora do prompt

A calibração é comportamental (prompt), mas duas camadas de runtime podem barrar T1
independentemente do prompt. **Verificar na implementação que nenhuma recusa escrita pontual
reversível:**

1. **Gate runtime `destructive_action_warning`** (`app/agente/config/permissions.py`, refactor
   2026-06-04 T2.1). Hoje bloqueia universalmente `action_update_taxes` (R11.1, T3, flag
   `USE_ODOO_TAX_GATE`) e **apenas avisa** em UPDATE/DELETE em massa (R12.1, decisão Rafael). Confirmar
   que não bloqueia UPDATE pontual reversível (T1).
2. **Evaluator do `consultando-sql`** (canal `mcp__sql`). Já houve bug onde bloqueava UPDATE após
   aprovar INSERT na mesma sessão (IMP-2026-05-13-004/007, corrigido). Confirmar que DML pontual com
   confirmação passa — senão o prompt manda "execute via mcp__sql" e o evaluator recusa (evasão por
   outra causa).

## Governança (PAD-CTX)

- R12.1+R12.2 (~22 linhas de prosa) colapsam na tabela (~12 linhas) + R9 encolhe → **delta esperado
  neutro ou negativo**. Rodar `python scripts/audits/prompt_size_audit.py --check-delta`. Baseline
  atual: `system_prompt.md` 770 linhas / 48.374 bytes / 13.821 tok. Se não crescer, segue limpo; se
  crescer, `--update-baseline && --update-claude-md` consciente no mesmo commit.
- **Sincronizar docs que citam R11/R12:** `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md:350`
  ("R11/R12 confirmação tipada em escrita Odoo/banco" → "tipada só em T3; T1/T2 = 1 confirmação").
  Conferir `app/agente/CLAUDE.md` (seção governança do prompt) e `REGRAS_OUTPUT.md`.
- Atualizar o bloco auto-medido do `app/agente/CLAUDE.md` via `--update-claude-md` se o tamanho mudar.
- Registrar no review trimestral (jul/2026) que R5/R9/R12 foram reconciliados em v4.5.0.

## Critérios de sucesso

1. **Caso-prova CarVia (IMP-24-002):** com o prompt calibrado, diante de "atualize o valor_cotado do
   frete X", o agente roda preview (dry-run) → pede 1 "ok" → executa via o script de escrita / `mcp__sql`
   → registra a lacuna. NÃO recusa.
2. **Sem regressão do "inconsequente":** UPDATE em massa (≥50) ainda exige amostra + confirmação por
   quantidade; operação SEFAZ/append-only ainda exige T3. Validar 1-2 casos representativos.
3. **Sem ambiguidade:** nenhuma regra do prompt pode ser lida como "skill read-only ⇒ proibido agir".
   Grep por "NUNCA" nas regras de escrita: cada ocorrência aponta para T3/append-only, não para T1.

## Fora de escopo (YAGNI)

- Não criar skills novas para os casos de escrita (o objetivo é justamente **não** precisar).
- Não mexer no gate runtime além de **verificar** que não barra T1 (se barrar, vira follow-up próprio).
- Não alterar R11 (SEFAZ) nem R3 (separação) — já são 1 confirmação ou T3 legítimo.
- Não tocar a camada de diretivas dinâmicas (operational_directives) — a correção é estrutural na fonte.
