# Atualizacao CLAUDE.md — 2026-05-25-1

**Data**: 2026-05-25  **Auditados**: 9/9  **Modificados**: 9

## Resumo

Auditoria dos 9 CLAUDE.md. Mudanca estrutural mais expressiva: **odoo** ganhou o
subpacote `estoque/` (13 arquivos / ~6.7K LOC) com scripts atomicos das skills
WRITE (Skills 1, 2, 2.4, 4, 5, 6, 9) + 2 novos services (`stock_mo_service`,
`transferencia_saldo_codigo_service`) + 2 modulos de constants (`picking_types`,
`ids_diversos`) — total 46 → 63 arquivos e 23K → 28.8K LOC. **CarVia** ganhou
feature de anexos polimorficos (route `anexo_routes` + model `anexos` + service
`documentos/anexo_service`) — 104 → 107 arquivos, 108 → 109 templates, 66.1K →
66.9K LOC. **Carteira** documentou `alert_system.py` no root (existia mas faltava
na arvore). Demais modulos (agente, agente/services, financeiro, seguranca,
teams) sem mudanca estrutural — apenas datas e LOC ajustados.

## Estado Atual (apos auditoria)

| Modulo | Arquivos .py | LOC | Templates |
|--------|--------------|------|-----------|
| agente | 80 | ~41.9K | 5 |
| agente/services | 17 | ~10.5K | — |
| carteira | 50 | ~18.5K | 13 + 22 JS |
| carvia | 107 | ~66.9K | 109 |
| financeiro | 80 | ~46.1K | 29 |
| odoo | 63 (50 root + 13 estoque/) | ~28.8K (22.1K root + 6.7K estoque) | — |
| seguranca | 14 | ~2.0K | 8 |
| teams | 4 | ~2.5K | — |

## Alteracoes por Arquivo

### CLAUDE.md (raiz)
- Data: 18/05/2026 → 25/05/2026
- Todos os caminhos da tabela "CAMINHOS DO SISTEMA" e references verificados —
  todos existem. Nenhuma mudanca de conteudo.

### app/agente/CLAUDE.md
- Header: 41.7K → 41.9K LOC (data 18/05 → 25/05)
- 80 arquivos / 5 templates confirmados. Sem mudanca estrutural.

### app/agente/services/CLAUDE.md
- Header: data 2026-05-18 → 2026-05-25
- 17 arquivos / ~10.5K LOC confirmados. Sem mudanca estrutural.
- LOC ajustado: `tool_skill_mapper.py` 337 → 350 (aplicado pelo linter automatico)

### app/carteira/CLAUDE.md
- Header: 18.4K → 18.5K LOC (data 18/05 → 25/05)
- **Adicionado** `alert_system.py` na arvore Estrutura (`AlertaSistemaCarteira`,
  integrado com `NotificationDispatcher`). Arquivo ja existia mas nao estava
  documentado na arvore.
- 50 .py / 13 HTML / 22 JS confirmados.

### app/carvia/CLAUDE.md
- Header: 104 / 66.1K / 108 templates → 107 / 66.9K / 109 templates
  (data 2026-05-18 → 2026-05-25)
- Estrutura ajustada:
  - **Routes** 29 → 30 sub-rotas: adicionado `anexo` (anexo_routes.py — uploads
    polimorficos para CarviaFrete + CarviaSubcontrato via CarviaAnexoService)
  - **Services documentos** 9 → 10: adicionado `anexo_service`
  - **Models** 13 → 14: adicionado `anexos` (model polimorfico)
  - **Services total** 41 → 42
- Routes/services/models reais confirmados arquivo a arquivo (sem `__init__.py`).

### app/financeiro/CLAUDE.md
- Header: data 18/05 → 25/05/2026 (LOC inalterado em ~46.1K)
- 80 .py confirmados. Sem mudanca estrutural.

### app/odoo/CLAUDE.md
- Header: 46 / 23K → 63 / 28.8K (data 20/05 → 25/05)
- Adicionado ponteiro de header para `app/odoo/estoque/CLAUDE.md` (subpacote
  com 13 arquivos / ~6.7K LOC).
- Estrutura ajustada:
  - **constants/** 2 → 4 modulos: adicionados `picking_types.py` e
    `ids_diversos.py`
  - **services/** 19 → 21: adicionados `stock_mo_service.py` (SHIM Skill 4) e
    `transferencia_saldo_codigo_service.py` (transferencia entre codigos de
    produto)
  - **estoque/** novo subpacote inteiro: 13 arquivos divididos em scripts/
    (7 atomos das Skills 1, 2, 2.4, 4, 5, 6, 9), orchestrators/
    (pre_etapa_executor.py — macro C3) e fluxos/ (folhas Markdown).
- Tabela "Subpacote estoque/" atualizada com versoes vigentes (Skill 2 v10,
  Skill 4 v5, Skill 5 v3, Skill 6 v6, Skill 9 v7+, reservas v7+) e nova entrada
  para `planejando-pre-etapa-odoo` (Skill 6).

### app/seguranca/CLAUDE.md
- Header: data 18/05 → 25/05/2026 (14 / 2K LOC / 8 templates inalterados)

### app/teams/CLAUDE.md
- Header: data 18/05 → 25/05/2026 (4 / 2.5K LOC inalterados)

## Observacoes

- **estoque/ subpacote em rapido crescimento**: passou de 0 → 13 arquivos
  em ~3 sessoes (D-7 a hoje). Cobre 7 skills do orquestrador WRITE Odoo +
  fluxos compostos. CLAUDE.md proprio em `app/odoo/estoque/CLAUDE.md` ja
  existia e foi referenciado na entrada do header do `app/odoo/CLAUDE.md`.
- **Carvia anexos polimorficos**: feature adicionada nas ultimas 2 semanas —
  cobre uploads de comprovantes para CarviaFrete + CarviaSubcontrato (paridade
  Nacom). Migration nao identificada no escopo dessa auditoria (CLAUDE.md
  documenta apenas estrutura).
- **Carteira alert_system.py**: arquivo `app/carteira/alert_system.py` (104
  linhas) define `AlertaSistemaCarteira.verificar_separacoes_cotadas_antes_sincronizacao()`
  — integrado com `NotificationDispatcher`. Existia desde antes mas faltava na
  arvore Estrutura.
- **Nenhum caminho inexistente** detectado nos 9 arquivos. Todas as refs
  internas (`.claude/`, sub-docs CarVia/Odoo, references) verificadas.
- Modulos perifericos sem CLAUDE.md (recebimento, portal, pedidos, pallet,
  producao, motochefe) continuam fora do escopo desta auditoria — planejados
  em `~/.claude/CLAUDE.md`.
