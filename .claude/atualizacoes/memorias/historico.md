# Historico de Atualizacoes — Memorias

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-06-01-1](atualizacao-2026-06-01-1.md) — Decima auditoria. Sistema estruturalmente saudavel (113 topic files, frontmatter 113/113 OK com `type` flat OU sob `metadata:`, 0 links quebrados, 0 orfaos). MEMORY.md estourava o limite (156 linhas / 31.6KB) por entradas de 300-589 chars violando "max 2 linhas". Acao: indice reescrito condensando cada entrada a 1 linha, **preservando os 113 ponteiros** (ZERO remocoes). 1 link quebrado corrigido (gotchas_industrializacao_fb_lf_v24_cirurgia — prefixo `memory/` + movido de Historico p/ Modulos&Skills). Resultado: MEMORY.md **148 linhas / 19.7KB**, folga restaurada. Nenhuma memoria removida (inventario/skills Odoo ainda ativos). Candidata futura: picking_317346_pendente (nao verificavel sem Odoo live).

- [2026-05-25-1](atualizacao-2026-05-25-1.md) — Nona auditoria. Bug estrutural NOVO: 6 arquivos criados em `memory/memory/` (subdir aninhado, possivel bug do skill `remember`) movidos para top-level e subdir removido. 3 correcoes factuais (drift recorrente): skills 40->47 (+6 orquestrador Odoo + 1 HORA); SDK 0.2.82->0.2.87. 86 memorias (cresceu +37 em 7 dias — sessoes intensas SPED ECD V31-V36 + Skills 2/4/5/6/10 + caso real 71 cods). MEMORY.md 128 linhas (85% do budget — alerta). Frontmatter OK em 86/86.

- [2026-05-18-1](atualizacao-2026-05-18-1.md) — Oitava auditoria. Sistema saudavel estruturalmente. 3 correcoes factuais (drift): skills 35->40 invocaveis (+5 SPED ECD + baseline conciliacao); SDK 0.1.80->0.2.82 (migracao minor); 1 orfao detectado e registrado (`feedback_rastrear_acesso_ui_completo.md` existia desde 2026-05-12). 49 memorias (cresceu +17), MEMORY.md 90 linhas. Frontmatter OK em 49/49.

- [2026-05-11-1](atualizacao-2026-05-11-1.md) — Setima auditoria. Sistema saudavel. 3 correcoes factuais: skills 29->35 invocaveis em MEMORY.md + `skills_inventario.md` (6 novas skills motos_assai); SDK 0.1.66->0.1.80 em MEMORY.md + `sdk_0160_subagent_bugs.md` (alinhamento com `requirements.txt`). 32 memorias, MEMORY.md 73 linhas. Frontmatter OK em 32/32.

- [2026-05-05-1](atualizacao-2026-05-05-1.md) — Sexta auditoria. Sistema saudavel em steady-state. 1 correcao factual: `skills_inventario.md` linha `operando-ssw` 18->22 scripts (alinhamento com `ssw_operacoes.md` e MEMORY.md ja em 22). 29 memorias, MEMORY.md 70 linhas. Frontmatter OK em 29/29. 0 memorias `type:project`.

- [2026-04-27-1](atualizacao-2026-04-27-1.md) — Quinta auditoria. 29 memorias auditadas (sistema saudavel), 5 atualizadas (skills_inventario 24->29, ssw_operacoes 18->22, 3 reclassificacoes type:project->feedback/reference). MEMORY.md 70 linhas. Frontmatter OK em 29/29.

- [2026-04-20-1](atualizacao-2026-04-20-1.md) — Quarta auditoria. 1 memoria removida (carvia_auditoria_pendencias — W9 + FC_VIRTUAL->MANUAL concluidos e validados no codigo). MEMORY.md atualizado (skills 23->24, remocao secao "Trabalho em andamento"). 25 memorias, MEMORY.md 67 linhas.

- [2026-04-13-1](atualizacao-2026-04-13-1.md) — Terceira auditoria. 2 memorias atualizadas (skills_inventario 5->23 skills, ssw_operacoes 11->18 scripts). 20 memorias, MEMORY.md 65 linhas.

- [2026-04-06-1](atualizacao-2026-04-06-1.md) — Segunda auditoria. 5 projetos obsoletos removidos, 2 MCP files consolidados em 1, 1 frontmatter corrigido (23->18 arquivos, MEMORY.md 58 linhas).
- [2026-03-28-1](atualizacao-2026-03-28-1.md) — Primeira auditoria. 7 memorias removidas (obsoletas/cobertas por CLAUDE.md), 12 frontmatter adicionados, MEMORY.md reorganizado (30->23 arquivos).

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
