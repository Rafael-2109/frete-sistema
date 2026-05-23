# ARQUITETURA — Orquestrador de Operações Odoo

**Criado:** 2026-05-22 | **Status:** ESSÊNCIA DECIDIDA (com Rafael) — implementação pendente (ver [`ROADMAP_SKILLS.md`](ROADMAP_SKILLS.md)).
**Audiência:** Claude Code (dev) + agente web. Doc **machine-first** — contratos e regras, não narrativa para humano.
**Supera:** a metodologia `gold-script→manual→guia→orquestrador-script` de [`PLANO_MIGRACAO.md`](PLANO_MIGRACAO.md)/[`MAPA_ASSUNTOS.md`](MAPA_ASSUNTOS.md). Aqueles seguem válidos como **mineração** (o "o quê existe"); ESTE define o **"como entregar"**.

---

## 0. Por que isto existe

105 scripts ad-hoc em `scripts/inventario_2026_05/` nasceram de "não procurar → recriar" sob pressão. Objetivo: **nunca mais criar script ad-hoc** para operar o Odoo. Toda operação de escrita passa a ser disparada via **skills-átomos versáteis** compostas em **fluxos**, orquestradas pelo subagente **`gestor-estoque-odoo`**. Executor = **Claude Code E agente web** (o agente web só opera via skills/subagentes — por isso skill, não script-CLI standalone).

---

## 1. PRINCÍPIO FUNDADOR (inviolável)

> Toda operação de escrita no Odoo é um **átomo versátil e auto-seguro**:
> - **versátil** — serve N fluxos variando args; nunca assume um fluxo específico;
> - **auto-seguro** — os gotchas do seu objeto estão codificados DENTRO como invariante (validador/guard/retry), não na memória do agente;
> - **2 modos** — `--dry-run` (default seguro: calcula e mostra o plano, não escreve) → `--confirmar` (executa).
>
> Os **fluxos** que compõem átomos vivem em **referências navegáveis** (árvore de progressive disclosure), não em código nem no prompt.
>
> O subagente **pesquisa premissas → navega a árvore → compõe átomos → confirma**. NUNCA recompõe lógica perigosa do zero, NUNCA inventa SQL/XML-RPC, NUNCA cria script ad-hoc.

---

## 2. AS 5 CAMADAS

```
[L4] gestor-estoque-odoo (subagente WRITE)
        pesquisa premissas · navega árvore de decisão · compõe átomos · mostra plano · confirma
   │
[L3] REFERÊNCIAS de fluxo  (consolidacao/fluxos/, árvore 1/2/3…)
        progressive disclosure; cada FOLHA = premissas + sequência de átomos + args + exemplo + gotchas
   │
[L2] SKILLS = átomos versáteis por objeto  (.claude/skills/<skill>/)
        SKILL.md (contrato + receitas) + scripts/ (--dry-run + --confirmar)
   │
[L1] SERVICES / primitivas  (app/odoo/estoque/)
        C1 atômico · C2 composto · C3 macro — gotchas codificados, testados (pytest)
   │
[L0] CONSTANTS  (app/odoo/constants/)
        locations · operacoes_fiscais · picking_types · ids_diversos
```

Regra de dependência: cada camada só conhece a de baixo. L3 referencia L2 por nome+args; L2 importa L1; L1 usa L0. L4 nunca pula direto para L1 sem passar por L2 (skill).

---

## 3. CONTRATO DE ÁTOMO COMPONÍVEL (o coração)

Para que **muitos fluxos** componham **poucos átomos** (§4), cada skill DECLARA um contrato estilo pipe Unix. Toda `SKILL.md` deve conter este bloco:

```
## Contrato
- objeto:        <model Odoo principal> (ex: stock.quant)
- input:         <args nomeados>  (ex: --product --company --location --lote --delta|--valor-absoluto)
- output:        <dict estruturado p/ encadear>  (ex: {status, quant_id, qty_antes, qty_apos, ...})
- pré-condições: <estado exigido do Odoo>  (ex: produto existe; company resolvida)
- pós-condições: <estado garantido>  (ex: 1 stock.move 'Physical Inventory' criado)
- gotchas-invariante: <lista que o átomo trata sozinho>  (ex: G028 consolidar_move_lines)
- modos:         --dry-run (default) → --confirmar
```

**Composição (pipe):** o `output` de um átomo alimenta o `input` do próximo. Ex. fluxo "transferência inter-company":
```
faturando-odoo  --de LF --tipo perda ... --confirmar
   └─ output: {nfe_key, nfe_number, picking_id, status: SEFAZ_OK}
escriturando-odoo  --para FB --nfe-key <do passo anterior> --cfop-entrada 1903 ... --confirmar
   └─ output: {invoice_id, quant_destino, status: ENTRADA_OK}
```

**Regra de ouro (correção 2026-05-22):** o átomo NUNCA embute outro fluxo. `faturando-odoo` SÓ fatura (saída); `escriturando-odoo` SÓ escritura (entrada). Quem une é o FLUXO (L3), não o átomo.

---

## 4. PILAR: fluxos >> skills

Poucos átomos (~8, estáveis) ⟷ MUITOS fluxos (dezenas, crescem sempre). Esta assimetria é **intencional** e dita duas regras:

1. **Átomo é genérico e estável.** Adicionar um caso de negócio NÃO deve exigir tocar um átomo — deve exigir só uma nova referência de fluxo (L3). Se um caso novo "não cabe" nos args de um átomo, primeiro pergunte se é arg faltante (estender o átomo de forma retrocompatível) antes de criar átomo novo.
2. **A inteligência de negócio vive nos fluxos (L3), não nas skills (L2) nem no prompt (L4).** Skills são mecanismo; fluxos são política.

Consequência de design: 1-skill-por-fluxo (cada folha da árvore virar uma skill) é **proibido** — geraria explosão combinatória e duplicação. Folha da árvore = referência leve, não skill.

---

## 5. ÁRVORE DE FLUXOS vs PROMPT ENXUTO (progressive disclosure)

O prompt do subagente (L4) carrega **apenas a árvore de DECISÃO** (galhos), sem citar skills. Ao descer num ramo, carrega **a referência da folha sob demanda** (L3), que aí sim lista átomos+args+exemplo+gotchas. Objetivo: não inflar o prompt com o que não será usado.

**Convenção:**
- Numeração hierárquica `1 / 1.1 / 1.1.1 / 1.1.1.1`.
- **Nós internos** = condições de roteamento (perguntas objetivas). NÃO citam skills.
- **Folhas** = arquivo em `consolidacao/fluxos/<id>-<slug>.md` com o bloco padrão (§5.1).

Esqueleto da árvore (galhos no prompt; folhas em arquivos):
```
1  NF inter-company (envolve emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)
        1.1.1 LF→CD   1.1.1.1 componentes(tipos 1/2/3)  1.1.1.2 acabado(4)  1.1.1.3 ambos
        1.1.2 LF→FB   …
   1.2  só recebimento/entrada
        1.2.1 inventário (DFe próprio) → escriturando-odoo
        1.2.2 COMPRAS (DFe fornecedor) → DELEGA gestor-recebimento
   1.3  transferência completa (saída + entrada) = faturando-odoo ⨾ escriturando-odoo
2  Estoque (sem NF) → ajustando-quant / transferindo-interno / operando-reservas / operando-picking
3  Produção / PCP → operando-mo
```

### 5.1 Formato da FOLHA (referência de fluxo)
```
# Fluxo <id> — <nome>
Quando: <condição que levou até aqui na árvore>
Premissas (pesquisar+validar ANTES): <produtos, lote|FIFO, qtds, CFOP(D014), saldo, ...>
Sequência:
  1) <skill-átomo> <args>  → output usado no passo N
  2) <skill-átomo> <args (recebe output do passo 1)>
Gotchas do fluxo: <refs G###>
Exemplo:
  python .../<script>.py <args> --dry-run   # revisar plano
  python .../<script>.py <args> --confirmar
```

---

## 6. CATÁLOGO DE ÁTOMOS (skills ~8 — por objeto, versáteis)

| Skill | Objeto Odoo | Service base (L1) | Camada | Granularidade |
|-------|-------------|-------------------|--------|---------------|
| `ajustando-quant-odoo` | stock.quant | `StockQuantAdjustmentService` | C1 | pequena |
| `transferindo-interno-odoo` | transferência interna (lote/local/net-zero/MIGRAÇÃO↔Indisponível/indisponibilizar/Pré-Prod↔Estoque) | `StockInternalTransferService` (+ `transferir_lote.py`) | C2 | média |
| `operando-mo-odoo` | mrp.production (cancelar/criar/alterar) | GAP → criar | C2 | média |
| `operando-reservas-odoo` | stock.move.line (unreserve/reassign/órfã/recompute) | GAP → criar | C1/C2 | pequena |
| `operando-picking-odoo` | stock.picking (criar/cancelar/devolver/alterar-lote/validar) | `StockPickingService` | C2 | média |
| `faturando-odoo` | **SÓ SAÍDA**: NF→robô CIEL IT→SEFAZ | `InventarioPipelineService` (etapas saída) | C3 | macro + etapas B→D |
| `escriturando-odoo` | **SÓ ENTRADA**: DFe/NF→in_invoice→saldo | pipeline (etapa entrada) + `escriturar_dfe_lf` | C3 | macro + etapas E→F |
| `planejando-pre-etapa-odoo` | planner (pesquisa+valida) | `PreEtapaEstoqueService` | C2 | — |

**Não-skills:** `operando-lote` (stock.lot) = **utils** (chamado por ajustando/transferindo, não exposto como skill). Leitura/diff = `consultando-sql` + `scripts/.../monitor/`.

> Cada átomo destila scripts ad-hoc específicos — ver mapeamento em [`MAPA_SCRIPTS.md`](MAPA_SCRIPTS.md) e os checkpoints por skill em [`ROADMAP_SKILLS.md`](ROADMAP_SKILLS.md).

---

## 7. GRANULARIDADE (fluxo perigoso = 2 níveis)

Faturamento/escrituração tocam SEFAZ (irreversível). Cada um é **átomo macro** (default, caminho feliz) **+ átomos de etapa** (recuperação/exceção):
- `faturando-odoo`: macro (renomear→picking→liberar→robô→SEFAZ) + etapas B→D recuperáveis. Espelha `09_bulk` + `fat_lf_resume.sh`.
- `escriturando-odoo`: macro (entrada destino) + etapas E→F recuperáveis. Espelha `fat_lf_resume_entrada.sh`.

O caminho feliz usa 1 átomo; a recuperação parcial usa os átomos de etapa.

---

## 8. DETERMINISMO DOS GOTCHAS (gotcha = invariante codificado, não memória do agente)

| Classe de gotcha | Exemplos | Como vira determinístico | Onde |
|------------------|----------|--------------------------|------|
| estrutural | G004 (picking→robô→SEFAZ, nunca account.move) | é a assinatura do átomo | átomo |
| pré-flight fiscal | G035 barcode-GTIN / G017 NCM / G007 price / G018 weight (→ SEFAZ 225) | validador checa+corrige+bloqueia ANTES de transmitir (`gtin_validator`) | pré-condição |
| reserva | G028 over-reservation, G011 qty_done | guard em `validar()` (G028=`consolidar_move_lines`, já existe) | átomo picking |
| infra | G016 SSL crash em loop | retry + keepalive | conexão |
| ordem/sequência | faturar→entrada; sleep entre pickings; validar→liberar | guard clause: átomo N recusa se estado de N-1 ausente | pré-condição |

**Pré-requisito bloqueante:** **G019/G020 estão ABERTOS** (`validar()` engole erro / marca done falso). Devem ser FECHADOS antes de confiar no determinismo de `faturando-odoo`. Não arquitetar sobre bug aberto.
**Irredutível:** tempo do robô CIEL IT (>2h em pico) é externo — polling+timeout dá *resultado* determinístico (OK/timeout), nunca *tempo*.

---

## 9. SUBAGENTE `gestor-estoque-odoo` (NOVO, WRITE)

- **Papel:** orquestrar operações reais no Odoo **e pesquisar premissas obrigatórias** antes de executar (ex: resolver `default_code`→produto, decidir lote/FIFO, validar CFOP D014, conferir saldo).
- **Loop:** identificar intenção → navegar árvore (L3) → carregar folha sob demanda → pesquisar/validar premissas → compor átomos em `--dry-run` → **mostrar plano** → `--confirmar` após OK do usuário.
- **Tools:** Read, Bash (executa scripts das skills), Glob, Grep, memory. Skills: as ~8 + `consultando-sql`, `resolvendo-entidades`.
- **Diferenciação obrigatória** de `gestor-estoque-producao` (READ-ONLY, projeção/análise): a description deve deixar explícito WRITE vs READ para o roteamento não confundir.

---

## 10. FRONTEIRAS (manter — não absorver outros domínios)

| Assunto | Dono | Regra |
|---------|------|-------|
| Faturamento saída inventário | `gestor-estoque-odoo` / `faturando-odoo` | só saída |
| Entrada/escrituração inventário | `gestor-estoque-odoo` / `escriturando-odoo` | DFe de inventário |
| Recebimento de **COMPRAS** (DFe fornecedor, 4 fases) | `gestor-recebimento` | árvore 1.2.2 DELEGA |
| CTe (frete) | módulo `fretes` (`cte_service`) | árvore referencia, não absorve |
| Pallet | módulo `pallet` | idem |
| Diagnóstico cross-area NF/PO/financeiro | `especialista-odoo` | — |
| Criar/alterar código de integração | `desenvolvedor-integracao-odoo` | — |

---

## 11. ESTRUTURA DE ARQUIVOS

```
app/odoo/
  constants/                     # L0 (existe)
  estoque/                       # L1 — MATERIALIZAR (PLANO_MIGRACAO §1, com shims)
    scripts/  {lot,quant,transfer,picking,mo,reserva,...}.py
    orchestrators/  {inventario_pipeline,...}.py
    _utils.py
  services/<nome>_service.py     # vira SHIM: re-export de estoque/ (preserva 105 scripts + testes)

.claude/skills/<skill>/          # L2
  SKILL.md   (contrato §3 + receitas + gotchas)
  scripts/*.py   (--dry-run + --confirmar; importam app.odoo.estoque)

.claude/agents/gestor-estoque-odoo.md   # L4 (prompt = árvore de decisão §5)

docs/inventario-2026-05/consolidacao/
  ARQUITETURA_ORQUESTRADOR_ODOO.md   # este doc
  ROADMAP_SKILLS.md                  # task-list física (checkpoints)
  fluxos/<id>-<slug>.md              # L3 — folhas da árvore (progressive disclosure)
  MAPA_ASSUNTOS.md / MAPA_SCRIPTS.md / PLANO_MIGRACAO.md   # mineração (válidos)
  manuais/<service>.md               # vira/alimenta as SKILL.md
```

---

## 12. INVARIANTES DE EXECUÇÃO (checklist de toda operação WRITE)

1. `--dry-run` SEMPRE primeiro → mostrar plano calculado.
2. Confirmação explícita do usuário antes de `--confirmar` (operações irreversíveis: SEFAZ).
3. Premissas pesquisadas E validadas deterministicamente antes de compor.
4. Verificar resultado DIRETO no Odoo (não confiar só no output do script — regra DEV OpenClaw/Playwright).
5. Operação VIVA: os 105 scripts ad-hoc permanecem intactos até o átomo correspondente maturar; arquivar SUPERADO só após checklist [`PLANO_MIGRACAO.md §7`](PLANO_MIGRACAO.md).

---

## 13. PONTEIROS

- Memória (essência compacta p/ retomar): `memory/arquitetura_orquestrador_odoo.md`
- Task-list física (capinar): [`ROADMAP_SKILLS.md`](ROADMAP_SKILLS.md)
- Mineração script→átomo: [`MAPA_SCRIPTS.md`](MAPA_SCRIPTS.md)
- Assunto×camada×gotchas: [`MAPA_ASSUNTOS.md`](MAPA_ASSUNTOS.md)
- Estrutura/shims `app/odoo/estoque/`: [`PLANO_MIGRACAO.md`](PLANO_MIGRACAO.md)
- Padrão skill completo (SKILL.md+evals+ROUTING_SKILLS+tool_skill_mapper): `memory/feedback_skill_padrao_completo.md`
