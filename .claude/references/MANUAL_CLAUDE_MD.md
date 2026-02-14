# Manual: Criacao de CLAUDE.md de Modulo

**Versao**: 1.0 | **Data**: 14/02/2026

Manual normativo para criar subdirectory CLAUDE.md em modulos do Sistema de Fretes.
Baseado em docs oficiais Anthropic, pesquisa empirica HumanLayer e padroes do projeto.

---

## S1. Fundamentos Oficiais

### Hierarquia de Memoria (6 niveis, carregamento em cascata)

| Nivel | Local | Escopo | Carregamento |
|-------|-------|--------|-------------|
| 1 | `/etc/claude-code/CLAUDE.md` | Organizacao | Sempre |
| 2 | `./CLAUDE.md` ou `./.claude/CLAUDE.md` | Projeto (VCS) | Sempre |
| 3 | `./.claude/rules/*.md` | Regras path-specific | Por glob match |
| 4 | `~/.claude/CLAUDE.md` | Usuario global | Sempre |
| 5 | `./CLAUDE.local.md` | Pessoal/local (.gitignore) | Sempre |
| 6 | `~/.claude/projects/.../memory/` | Auto-memoria | Primeiras 200 linhas |

### Subdirectory CLAUDE.md — Comportamento

- **Carregamento on-demand**: so carrega quando Claude acessa arquivos NAQUELE diretorio
- **Aditivo**: NAO sobrescreve o root — e ADICIONADO ao contexto junto com o root
- **Sem heranca explicita**: subdirectory simplesmente junta ao contexto do pai
- **Conflitos**: instrucao mais especifica (mais proxima do arquivo) tem precedencia

### @imports

- Sintaxe: `@path/to/file.md` — maximo 5 niveis de profundidade
- Paths relativos ao arquivo que contem o import
- Suporta `@~/...` para home directory
- NAO avaliado dentro de blocos de codigo

### .claude/rules/ (desde v2.0.64)

```yaml
---
paths:
  - "app/financeiro/**/*.py"
---
# Regras especificas carregadas apenas para estes arquivos
```

Alternativa ao subdirectory CLAUDE.md para regras path-specific sem poluir diretorios de codigo.

### Limites Praticos

| Metrica | Valor | Fonte |
|---------|-------|-------|
| Tamanho ideal | < 300 linhas | Consenso comunidade + Anthropic |
| Maximo pratico | ~500 linhas | Alem disso, diminishing returns |
| Instrucoes confiaveis | ~150-200 total | System prompt (~50) + root (~30) + subdir (~70-120) |
| Auto-memoria | 200 linhas max | Hard limit no MEMORY.md |

---

## S2. Arquitetura Atual do Projeto

### Root CLAUDE.md como Router (172 linhas)

```
CLAUDE.md (root)
  ├── Regras universais (5 regras criticas)
  ├── Migrations (padrao par .py/.sql)
  ├── Formatacao numerica (filtros Jinja2)
  ├── Modelos criticos (ponteiros → references/)
  ├── Indice de referencias (tabela 13 entradas)
  ├── Arquitetura CSS (5 regras + tabela)
  ├── Caminhos do sistema
  ├── Agente web (CLAUDE.md vs system_prompt.md)
  ├── Subagentes (4 agents + protocolo confiabilidade)
  └── Subdirectory planejados (este manual)
```

### Ecossistema de Documentacao

```
CLAUDE.md (root, 172 linhas) ─── ROUTER
    │
    ├── .claude/references/ (~3,150 linhas em 15 arquivos)
    │   ├── modelos/   → REGRAS_CARTEIRA_SEPARACAO, REGRAS_MODELOS, CADEIA, QUERIES
    │   ├── negocio/   → REGRAS_NEGOCIO, P1_P7, FRETE_REAL_VS_TEORICO, MARGEM
    │   ├── odoo/      → IDS_FIXOS, GOTCHAS, MODELOS_CAMPOS, PIPELINE
    │   ├── design/    → MAPEAMENTO_CORES
    │   └── INDEX.md   → Indice geral
    │
    ├── .claude/skills/ (22 skills, ~5,500 linhas em SKILL.md)
    │   └── cada skill/ → SKILL.md + SCRIPTS.md + scripts/ + references/
    │
    ├── .claude/hooks/ (8 hooks de validacao)
    │   └── ban_datetime_now, lembrar-migration-par, lembrar-regenerar-schemas, ...
    │
    └── .claude/skills/consultando-sql/schemas/tables/ (JSON auto-gerado)
        └── {tabela}.json → Fonte de verdade para campos
```

### O que JA esta coberto (NUNCA duplicar no subdir)

| Topico | Coberto em |
|--------|-----------|
| Timezone (Brasil naive) | `REGRAS_TIMEZONE.md` + hook `ban_datetime_now.py` |
| Migrations (par .py/.sql) | Root CLAUDE.md + hook `lembrar-migration-par.py` |
| CSS (layers, tokens, badges) | Root CLAUDE.md § ARQUITETURA CSS |
| Campos de tabela | Schemas JSON auto-gerados |
| Formatacao numerica | Root CLAUDE.md § FORMATACAO |
| Infraestrutura Render | `INFRAESTRUTURA.md` |
| Subagentes + confiabilidade | Root CLAUDE.md + `SUBAGENT_RELIABILITY.md` |
| Regras P1-P7 | `REGRAS_P1_P7.md` |
| Ambiente virtual | Root CLAUDE.md regra #1 |

---

## S3. Principios de Design

### P1: Complementar, Nunca Duplicar

O subdir CLAUDE.md contem SOMENTE informacao que o root e references NAO cobrem.
Se a informacao ja existe em outro lugar, use um ponteiro (`ver REGRAS_TIMEZONE.md`).

### P2: Regras > Descricoes

```
# ERRADO — Claude infere lendo o codigo
"Este modulo usa o padrao service layer com routes → services → models"

# CORRETO — Claude NAO infere isso sozinho
"NUNCA chamar Odoo diretamente de routes — usar services/*.py como intermediario"
```

### P3: Gotchas > Arquitetura

Claude le e entende codigo. O que ele NAO infere sao armadilhas nao-obvias:
- Campos com nomes enganosos (`qtd_saldo` vs `qtd_saldo_produto_pedido`)
- Efeitos colaterais (`listener X dispara quando Y muda`)
- Restricoes de negocio nao expressas no codigo
- Ordem de operacoes que importa

### P4: Tabelas > Prosa

```
# ERRADO
"O modelo Embarque tem os campos status_embarque que pode ser 'pendente',
'em_transito', 'entregue' ou 'cancelado', e o campo..."

# CORRETO
| Campo | Valores | Gotcha |
|-------|---------|--------|
| status_embarque | pendente, em_transito, entregue, cancelado | Listener atualiza faturamento |
```

### P5: Maximo 150 Linhas

Token budget e finito. Root (~30 instrucoes) + system prompt (~50) ja consomem ~80.
Sobram ~70-120 instrucoes confiaveis para o subdir. **150 linhas e o teto pratico.**

### P6: Fontes de Verdade Unicas

Cada informacao vive em EXATAMENTE um lugar. Outros arquivos apontam para la.

| Informacao | Fonte Unica | Outros Referenciam |
|-----------|-------------|-------------------|
| Campos de tabela | schemas JSON | REGRAS_*.md, SKILL.md |
| Regras timezone | REGRAS_TIMEZONE.md | Root CLAUDE.md, hooks |
| IDs Render | INFRAESTRUTURA.md | Root CLAUDE.md |
| Prioridades P1-P7 | REGRAS_P1_P7.md | system_prompt.md |

---

## S4. Template Padrao

```markdown
# {Modulo} — Guia de Desenvolvimento

**LOC**: {X}K | **Arquivos**: {N} | **Atualizado**: {data}

---

## Escopo

{1-2 frases descrevendo o que o modulo faz. Nao descrever arquitetura — Claude le o codigo.}

## Estrutura

```
app/{modulo}/
  ├── routes/         # {N} blueprints
  ├── services/       # Logica de negocio
  ├── models/         # {N} models
  ├── utils/          # Helpers (se existir)
  └── workers/        # Jobs async (se existir)
```

## Regras Criticas

### R1: {Nome curto}
{Regra imperativa. Exemplo de violacao e correcao.}

### R2: {Nome curto}
{...}

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| {Model} | `{tabela}` | {armadilha nao-obvia} |

## Padroes do Modulo

### {Padrao 1}
{Descricao CURTA do padrao + exemplo minimo se nao-obvio.}

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/{outro}/` | {funcao/model} | {impacto se mudar} |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/{outro}/` | {funcao/model} | {quem quebra se mudar} |

## Skills Relacionadas

| Skill | Opera neste modulo? | Referencia |
|-------|---------------------|-----------|
| {skill} | {Sim/Parcial} | `.claude/skills/{skill}/SKILL.md` |
```

### Notas sobre cada secao

| Secao | Obrigatoria? | Por que |
|-------|-------------|---------|
| Escopo | Sim | 1-2 frases para contexto rapido |
| Estrutura | Sim | Tree simplificado — Claude precisa saber ONDE olhar |
| Regras Criticas | Sim | Razao de existir do subdir CLAUDE.md |
| Modelos | Sim | Gotchas de naming/comportamento — NUNCA listar campos |
| Padroes | Opcional | So se o modulo tem patterns NAO obvios lendo o codigo |
| Interdependencias | Sim | Evita quebrar outros modulos |
| Skills | Opcional | So se skills operam no modulo |

---

## S5. Checklist Pre-Criacao

Antes de criar CLAUDE.md de um modulo, completar TODOS os itens:

### Pesquisa Obrigatoria

- [ ] Listar TODOS os arquivos Python e contar LOC total
- [ ] Ler os 5 maiores arquivos completamente (routes + services)
- [ ] Identificar TODOS os models e suas FK/relacionamentos
- [ ] Mapear TODOS os blueprints/rotas registrados
- [ ] Identificar padroes recorrentes (error handling, decorators, imports)
- [ ] Catalogar gotchas nao-obvios (bugs corrigidos, edge cases, limitacoes)
- [ ] Verificar dependencias: o que importa de outros modulos
- [ ] Verificar dependencias reversas: quem importa DESTE modulo

### Verificacao Anti-Duplicacao

- [ ] Ler root CLAUDE.md — o que ja esta coberto?
- [ ] Ler `.claude/references/INDEX.md` — algum reference ja cobre?
- [ ] Verificar skills que operam neste modulo (ROUTING_SKILLS.md)
- [ ] Verificar hooks que ja validam regras deste modulo
- [ ] Verificar se existe `README.md` no modulo (ex: `app/devolucao/README.md`)

### Validacao Final

- [ ] Resultado tem < 150 linhas
- [ ] ZERO duplicacao com root ou references
- [ ] Cada regra e IMPERATIVA (faca X / nunca faca Y)
- [ ] Cada gotcha cita contexto (modelo, campo, cenario)
- [ ] Links para schemas JSON em vez de listar campos

---

## S6. Anti-padroes Especificos do Projeto

| Anti-padrao | Por que e ruim | Fazer em vez disso |
|------------|---------------|-------------------|
| Listar campos de tabela | Fica desatualizado; schemas JSON sao auto-gerados | `ver schemas/tables/{tabela}.json` |
| Duplicar regras timezone | Ja em REGRAS_TIMEZONE.md + hook ban_datetime_now | Ponteiro: `ver REGRAS_TIMEZONE.md` |
| Duplicar regras CSS | Ja no root CLAUDE.md § ARQUITETURA CSS | Omitir — root cobre |
| Duplicar regras migrations | Ja no root + hook lembrar-migration-par | Omitir — root cobre |
| Colocar IDs Render/Odoo | Ja em INFRAESTRUTURA.md | Ponteiro: `ver INFRAESTRUTURA.md` |
| Descrever subagentes | Ja no root + SUBAGENT_RELIABILITY.md | Omitir — root cobre |
| Explicar arquitetura generica | Claude infere lendo routes → services → models | Foco em GOTCHAS e REGRAS |
| Incluir exemplos longos de codigo | Consome token budget desnecessariamente | Max 3-5 linhas por exemplo |
| Duplicar info de README.md local | Ja existe no modulo | Ponteiro: `ver app/{mod}/README.md` |

---

## S7. Exemplo Comentado: app/pallet/

Exemplo realista baseado no modulo pallet (13.3K LOC, 27 arquivos).

```markdown
# Pallet — Guia de Desenvolvimento

**LOC**: 13.3K | **Arquivos**: 27 | **Atualizado**: 14/02/2026

---

## Escopo

Gestao de pallets (vasilhames retornaveis): creditos a receber de clientes,
emissao de NF de remessa/devolucao, e integracao com Odoo para baixas.

## Estrutura

```
app/pallet/
  ├── routes/          # 5 blueprints (dashboard, controle, tratativa_nfs, movimentacoes, nf_remessa)
  ├── services/        # 7 services (match, sync_odoo, credito, solucao, nf, emissao_nf, odoo_devolucao)
  ├── models/          # 6 models (2 dominios) + 1 legado
  ├── workers/         # Jobs Odoo (devolucao)
  ├── utils.py         # Helpers compartilhados
  └── routes_legacy.py # LEGADO — migrar para routes/
```

## Regras Criticas

### R1: Dois Dominios Independentes
Dominio A (Creditos): PalletCredito → PalletDocumento → PalletSolucao
Dominio B (NFs): PalletNFRemessa → PalletNFSolucao
NUNCA misturar queries entre dominios sem JOIN explicito via match_service.

### R2: ValePallet e Legado
`models/vale_pallet.py` existe APENAS para compatibilidade.
NUNCA adicionar features no ValePallet — usar PalletCredito.

### R3: match_service.py e o Maior Arquivo (1.6K LOC)
Contem logica de matching credito ↔ NF. Alteracoes aqui
afetam AMBOS os dominios. Testar cenarios de match parcial.

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| PalletCredito | `pallet_creditos` | FK para embarque — pode ser NULL |
| PalletDocumento | `pallet_documentos` | Tipos: canhoto, vale, foto |
| PalletSolucao | `pallet_solucoes` | Status afeta saldo do credito |
| PalletNFRemessa | `pallet_nf_remessas` | Precisa ser criada ANTES de PalletNFSolucao |
| PalletNFSolucao | `pallet_nf_solucoes` | FK obrigatoria para nf_remessa |
| ValePallet | `vale_pallets` | LEGADO — somente leitura |

## Padroes do Modulo

### Sync Odoo Bidirecional
`sync_odoo_service.py` sincroniza devolucoes com Odoo.
Fluxo: PalletSolucao (local) → Odoo stock.picking → confirmacao → update local.
NUNCA chamar Odoo diretamente de routes — sempre via services.

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/models/` | Embarque, FaturamentoProduto | FK de creditos |
| `app/odoo/` | OdooService | Sync bidirecional |
| `app/utils/` | timezone, template_filters | Padrao global |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/templates/pallet/` | Templates Jinja2 | 5 telas + modais |
```

### O que este exemplo demonstra

1. **< 80 linhas** — bem abaixo do teto de 150
2. **Zero duplicacao** com root (sem CSS, timezone, migrations)
3. **Regras imperativas** (R1-R3 com "NUNCA" explicito)
4. **Gotchas reais** (ValePallet legado, ordem de criacao NF, match_service complexo)
5. **Ponteiros** para schemas JSON em vez de listar campos
6. **Interdependencias** com impacto claro

---

## Checklist de Revisao do Manual

Ao usar este manual para criar um CLAUDE.md de modulo, verificar:

- [ ] Segui o checklist pre-criacao (S5) completo
- [ ] Resultado tem < 150 linhas
- [ ] NAO dupliquei nada do root CLAUDE.md
- [ ] NAO listei campos de tabela (usei ponteiro para schemas JSON)
- [ ] Cada regra usa linguagem imperativa
- [ ] Inclui interdependencias com impacto explicito
- [ ] Testei: lendo SÓ o subdir + root, consigo trabalhar no modulo?
