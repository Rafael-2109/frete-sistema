<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da skill consultando-venda-loja (Onda F / HORA M3 venda READ) — EXECUTADA
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->
# Spec — Skill `consultando-venda-loja` (Onda F / HORA M3 venda READ)

> **Papel:** Spec — Skill `consultando-venda-loja` (Onda F / HORA M3 venda READ).

## Indice

- [1. Contexto e problema](#1-contexto-e-problema)
- [2. Objetivo](#2-objetivo)
  - [Não-objetivos (YAGNI)](#não-objetivos-yagni)
- [3. Escopo — 3 capacidades (modos)](#3-escopo-3-capacidades-modos)
- [4. Arquitetura](#4-arquitetura)
  - [4.1 Contrato CLI](#41-contrato-cli)
  - [4.2 Saída JSON (shapes)](#42-saída-json-shapes)
  - [4.3 Reuso de services (assinaturas verificadas)](#43-reuso-de-services-assinaturas-verificadas)
- [5. Pacote completo (wiring — checklist `feedback_skill_padrao_completo`)](#5-pacote-completo-wiring-checklist-feedback_skill_padrao_completo)
- [6. Testes (determinístico, $0, sem DB/PROD — `feedback_evals_llm_caros_preferir_pytest`)](#6-testes-determinístico-0-sem-dbprod-feedback_evals_llm_caros_preferir_pytest)
- [7. Riscos / decisões](#7-riscos-decisões)
- [8. Critérios de aceite](#8-critérios-de-aceite)
- [Contexto](#contexto)

**Data:** 2026-06-02
**Status:** design aprovado (brainstorming) — aguardando review da spec antes do plano de implementação
**Onda:** F (auditoria de skills) — fechar gap "HORA M3 venda sem skill" (relatório `AUDITORIA_SKILLS_2026-05-29.md` L53, P1 L120)
**Worktree:** `frete_sistema_onda_f`, branch `skills/onda-f-venda-hora` (base main `977216a7e`)

---

## 1. Contexto e problema

O subsistema de **venda** da Lojas HORA já está **LIVE em produção** (`app/hora`): model `HoraVenda`/`HoraVendaItem`, workflow de status `COTACAO→CONFIRMADO→FATURADO→CANCELADO`, services `venda_service`, `venda_preview_service`, `venda_audit`, emissão NFe via TagPlus, tabela de preço (`hora_modelo.preco_a_vista`/`preco_a_prazo` + fallback `hora_tabela_preco`).

Porém **não existe skill** para o **Agente Lojas HORA** (`app/agente_lojas/`) consultar vendas. A skill é referenciada como `registrando-venda` (comentada em `skills_whitelist.py:22` como "M3 (futuro)"; citada em `system_prompt.md:62`, `consultando-estoque-loja` SKILL.md L21/L44, `rastreando-chassi`), mas **nunca foi criada**. O nome `registrando-venda` sugere WRITE, o que está **errado**: o agente Lojas HORA é um *orientador* READ-only e a criação de venda já nasce por outro fluxo (upload de DANFE PDF na web). Decisão (brainstorming 2026-06-02): a skill é **READ**.

## 2. Objetivo

Criar a skill READ **`consultando-venda-loja`** para o Agente Lojas HORA consultar vendas, validar preço/desconto e ver margem — respeitando o escopo de loja via `<loja_context>`, no mesmo padrão das skills-irmãs do cluster HORA (`consultando-estoque-loja`, `acompanhando-pedido`).

### Não-objetivos (YAGNI)
- **Zero WRITE**: não cria, edita, confirma, cancela venda nem emite/cancela NFe.
- Não relaxa a barreira SDK / `disallowed_tools` (é READ — `permissions.py:95` falava em relaxar para um WRITE; **não se aplica**).
- Não reimplementa fórmulas fiscais (preço/desconto/margem) — **reusa os services existentes**.

## 3. Escopo — 3 capacidades (modos)

| Modo | Pergunta do operador | Fonte |
|---|---|---|
| `vendas` (default) | "minhas vendas hoje", "venda #X", "essa moto (chassi) foi vendida?", "vendas pendentes de NFe", "vendas com divergência" | **SQL bruto** sobre `hora_venda` + `hora_venda_item` + `hora_venda_divergencia` + `hora_tagplus_nfe_emissao` |
| `preco` | "preço de tabela do modelo X à vista/à prazo", "desconto de R$Y / Z% no modelo X bate com a tabela?" | **reuso** `venda_service.buscar_preco_para_pedido` + `venda_service._resolver_preco_tabela` |
| `margem` | "qual a margem da venda #X?" (custo, líquido, % margem) | **reuso** `venda_preview_service.montar_preview` |

**Sensibilidade:** o modo `margem` expõe **custo da moto** (`HoraPedidoItem.preco_compra_esperado`) e % de margem. Aprovado pelo dono do dado (brainstorming 2026-06-02). Respeita escopo de loja (operador só vê margem das vendas da sua loja).

## 4. Arquitetura

**1 skill, 1 script** `consultando_venda_loja.py`, padrão do cluster HORA:
- `from app import create_app, db` + `with app.app_context()`.
- `--loja-ids` CSV (None = admin / `pode_ver_todas`).
- Saída `print(json.dumps(..., default=_json_default))` com `escopo_aplicado` + `_debug.query_ms`.
- Helpers `_json_default` (datetime→iso, Decimal→float) e `_parse_loja_ids` (idênticos ao `acompanhando_pedido.py`).

**Híbrido deliberado (decisão de design):**
- `vendas` → SQL bruto (igual `acompanhando-pedido`): self-contained, zero acoplamento, query simples.
- `preco`/`margem` → **reusa services**: as fórmulas de preço/desconto/margem são não-triviais e já existem. Reimplementá-las em SQL recriaria a duplicação que o relatório (item 2.1) classificou como o **pior tipo de drift**.

### 4.1 Contrato CLI

```bash
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo vendas --loja-ids 2 \
    [--venda-id 123] [--chassi ABC123] [--status CONFIRMADO] [--somente-pendentes-nfe]

python .../consultando_venda_loja.py --modo preco \
    --modelo-id 10 --forma-pagamento A_VISTA [--preco-final 12990.00] [--modelo "BOB"]

python .../consultando_venda_loja.py --modo margem --venda-id 123 --loja-ids 2
```

- `--modo` default `vendas`.
- `vendas`: escopo via `hora_venda.loja_id = ANY(:ids)`; venda com `loja_id NULL` (não atribuída) só visível a admin (`pode_ver_todas`). Filtros opcionais: `--venda-id`, `--chassi` (EXISTS em `hora_venda_item`, ILIKE), `--status`, `--somente-pendentes-nfe` (sem NFe aprovada).
- `preco`: `--modelo-id` (primário) OU `--modelo` nome (lookup best-effort em `hora_modelo.nome_modelo` + `hora_modelo_alias`); `--forma-pagamento` (A_VISTA/A_PRAZO); `--preco-final` opcional dispara `venda_service.validar_desconto_tabela` (novo wrapper público → desconto R$/% + flag divergência). **Nível modelo — sem filtro de loja.**
- `margem`: `--venda-id` obrigatório; venda precisa estar no escopo de loja (senão retorna `{erro: fora_de_escopo}`).

### 4.2 Saída JSON (shapes)

- **vendas**: `{escopo_aplicado:{loja_ids,pode_ver_todas}, vendas:[{id,status,status_label,loja_id,loja_apelido,data,valor_total,valor_frete,vendedor,forma_pagamento,nf_saida_numero,nfe_status,divergencias,itens:[{numero_chassi,modelo,cor,preco_final,desconto_aplicado,desconto_percentual}]}], total_vendas}`
- **preco**: `{modelo_id,modelo_nome,forma_pagamento,preco_tabela,preco_a_vista,preco_a_prazo,fonte, validacao_desconto?:{preco_final,desconto_rs,desconto_pct,divergencia}}`
- **margem**: `{venda_id,escopo_ok, preview:{venda_total,frete,custo_moto_total,liquido,margem_bruta,margem_pct,tem_custo_faltante,itens:[{numero_chassi,modelo,cor,preco_venda,custo_moto,sem_custo}]}}`

> Colunas exatas de `hora_venda`/`_item`/`_divergencia`/`hora_tagplus_nfe_emissao` serão confirmadas contra `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` na implementação (regra CLAUDE.md — schemas são a fonte de verdade de campos). **[ASSUNÇÃO-CONFIRMAR na impl]**

### 4.3 Reuso de services (assinaturas verificadas)
- `venda_preview_service.montar_preview(venda: HoraVenda) -> dict` — campos `venda_total/frete/custo_moto_total/liquido/margem_bruta/margem_pct/tem_custo_faltante/itens` (lido em `app/hora/services/venda_preview_service.py:48-108`).
- `venda_service.buscar_preco_para_pedido(modelo_id, forma_pagamento_hora) -> {preco,fonte,tipo_pagamento,preco_a_vista,preco_a_prazo}` (CLAUDE.md §15).
- **NOVO** `venda_service.validar_desconto_tabela(modelo_id, valor_final, forma_pagamento_hora=None, na_data=None) -> dict {preco_referencia, desconto_rs, desconto_pct, tabela_id, divergencia}` — wrapper **público** (decisão do dono 2026-06-02) que delega à privada `_resolver_preco_tabela(modelo_id, na_data, valor_final, forma_pagamento_hora)`. `na_data` default = data Brasil via helper de timezone do projeto (**NUNCA** `date.today()`/`datetime.now()` — hook `ban_datetime_now`). Motivo: evita acoplar a skill a função `_privada` (anti-padrão de fronteira-borrada do relatório item 2.1) e troca a tupla-de-5 por dict.

## 5. Pacote completo (wiring — checklist `feedback_skill_padrao_completo`)
1. `.claude/skills/consultando-venda-loja/SKILL.md` — frontmatter `name`, `description` (USAR QUANDO / NÃO USAR PARA + "Respeita escopo de loja via <loja_context>"), `allowed-tools: Read, Bash, Glob, Grep`. Seções: Quando Usar, REGRAS CRÍTICAS (escopo, status derivado, sensibilidade margem), Invocação, Output JSON.
2. `.claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py`.
3. `app/agente_lojas/config/skills_whitelist.py` — substituir `# 'registrando-venda', # M3 (futuro)` por `'consultando-venda-loja',` no set `SKILLS_DOMINIO_HORA`.
4. `app/agente_lojas/prompts/system_prompt.md:62` — reescrever a linha `registrando-venda: validação de tabela de preço + desconto` → descrição READ da `consultando-venda-loja` (consulta vendas + preço/desconto + margem).
5. Corrigir refs penduradas a `registrando-venda` → `consultando-venda-loja`: `consultando-estoque-loja/SKILL.md:21,44`, `rastreando-chassi` (se houver). Verificar `permissions.py:95` (comentário sobre WRITE — atualizar nota ou deixar, pois não relaxamos disallow).
6. `.claude/references/ROUTING_SKILLS.md` — adicionar no cluster HORA (árvore + contagem/inventário).
7. `app/agente/services/tool_skill_mapper.py` — adicionar `consultando-venda-loja` à categoria HORA (telemetria).
8. **Sem** alteração em `disallowed_tools`/barreira SDK (READ).
9. `app/hora/services/venda_service.py` — adicionar função **pública** `validar_desconto_tabela` (aditiva; delega a `_resolver_preco_tabela`; `na_data` via helper de timezone). **Único toque em runtime `app/hora`** — additivo, zero mudança de comportamento dos callers existentes. Migration não aplicável (sem DDL). Coberto por teste em `tests/hora/`.

## 6. Testes (determinístico, $0, sem DB/PROD — `feedback_evals_llm_caros_preferir_pytest`)
`tests/skills/consultando_venda_loja/test_consultando_venda_loja.py`:
- `preco`/`margem`: carregar o script via `importlib` (padrão `test_cleanup_pos_bulk.py`), **mockar** `buscar_preco_para_pedido`, `validar_desconto_tabela`, `montar_preview` → asserir o shaping do JSON, validação de desconto e flag de divergência. Zero DB.
- **Wrapper novo**: teste unitário de `venda_service.validar_desconto_tabela` em `tests/hora/` (delega corretamente a `_resolver_preco_tabela`; mapeia tupla→dict; flag de divergência) — com `_resolver_preco_tabela`/tabela mockados (sem DB).
- `vendas`: testar roteamento de `--modo`, `_parse_loja_ids` (CSV→list, None=admin), e o shaping/escopo com a **execução SQL injetada/mockada** (`db.session.execute` mockado retornando rows canônicas) → asserir `escopo_aplicado`, filtro de `loja_id NULL` para não-admin, e que venda fora de escopo não aparece.
- Sem evals LLM (vetados por custo).

## 7. Riscos / decisões
- **`_resolver_preco_tabela` é "privada"** — **RESOLVIDO (dono, 2026-06-02):** expor wrapper **público** `venda_service.validar_desconto_tabela` (aditivo, baixo risco) e a skill importa o público; NÃO importar a `_privada` (evita fronteira-borrada do item 2.1). Atenção timezone: `na_data` via helper do projeto.
- **`loja_id` nullable** em `hora_venda` — **CONFIRMADO (dono, 2026-06-02):** operador escopado **NÃO** vê venda com `loja_id NULL`; só admin (`pode_ver_todas`).
- **Margem expõe custo**: aprovado (dono, 2026-06-02); documentar na SKILL.md (REGRAS CRÍTICAS) que o dado é sensível e só sai no escopo da loja.

## 8. Critérios de aceite
- Skill invocável; 3 modos retornam JSON válido; escopo de loja respeitado (operador não vê venda/margem de outra loja).
- `preco`/`margem` reusam services (sem reimplementar fórmula).
- pytest determinístico verde, sem DB/PROD.
- Wiring completo (whitelist + system_prompt + ROUTING + tool_skill_mapper + refs corrigidas); barreira SDK intacta.
- `py_compile` + `--help` OK.

## Contexto

_A completar (PAD-A Onda 4)._
