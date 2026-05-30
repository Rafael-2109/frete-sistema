# DIRETRIZ — Industrialização FB↔LF

> **Documento de DECISÃO** (sessão 2026-05-29). Substitui o paradigma anterior ("Opção 2 / inter-company", agora em `HISTORICO/`).
> - **Alvo do desenho** → `00_FLUXO_ATUAL_VS_IDEAL.md` (seção 3)
> - **Mecanismo técnico** → `ACHADOS_TECNICOS.md`
> - **Plano de execução** → `PLANO_EXECUCAO.md`

---

## 1. O que foi ABANDONADO (e por quê)

A **"Opção 2 / inter-company automático"** (rule_type=`sale_purchase` em FB+LF → PO dispara SO automática; subcontratação; DFe→PO) foi **abandonada**. Motivos verificados ao vivo:

1. **`rule_type='sale_purchase'` é company-wide.** Disparou SO espelho em **TODA** PO inter-company — inclusive **transferências CD↔FB** sem relação com industrialização. Efeito colateral grave. **Revertido para `not_synchronize`** em FB(1) e LF(5).
2. **Odoo bloqueia `stock.rule` cross-company** (`_check_company` → "Empresas incompatíveis"). A automação de procurement entre empresas não é viável por configuração.
3. **MTO/procurement não dispara em LF** (rota MTO global só tem rules em FB). MOs em LF são historicamente manuais.

→ O piloto executado por essa via foi **revertido** (ver §5). Toda doc que descrevia esse fluxo está em `HISTORICO/`.

---

## 2. O que foi ADOTADO (a diretriz)

O **fluxo correto é o do relatório** (`00_FLUXO_ATUAL_VS_IDEAL.md` §3): **baseado em picking físico + material em terceiros**, NÃO em PO/SO.

### Achado-chave que torna a solução CONFIGURÁVEL (sem desenvolvimento)

> **A LF não tem estoque próprio** — só industrializa para a FB. Logo **todo o estoque da LF é material de terceiros (da FB)**.
> As contas de valoração de estoque vêm da **categoria do produto**, e essas contas são **POR EMPRESA** (`ir.property` — provado: a mesma categoria tem contas diferentes em FB/SC/CD/LF).
> **Portanto:** basta apontar, **no contexto da LF**, as contas de estoque das categorias para o **par de terceiros** → toda movimentação na LF lança **net-zero em terceiros**, sem inflar ativo próprio, **por configuração**.

**Configuração-alvo das contas de categoria, no contexto da LF** (a validar com Contador):

| Conta da categoria (contexto LF) | Hoje (errado) | Apontar para |
|---|---|---|
| Valoração de Estoque | 1150100001/07 (MP/PA — ativo próprio) | **1150200001 MATERIAL EM TERCEIROS** |
| Entrada de Estoque | 3201000002 VARIAÇÕES POSITIVAS (um *ganho*!) | **1150200002 ( − ) MATERIAL DE TERCEIROS** |
| Saída de Estoque | 3201000003 VARIAÇÕES NEGATIVAS | **1150200002 ( − ) MATERIAL DE TERCEIROS** |

Efeito: entrada `D 1150200001 / C 1150200002`; consumo na MO + produção do PA (transita por Produção e zera); saída `C 1150200001 / D 1150200002`. **Tudo net-zero em terceiros.** A LF nunca infla ativo próprio — porque não tem.

---

## 3. As duas camadas contábeis (cada movimento gera DUAS)

| Camada | O que é | Onde se configura |
|---|---|---|
| **(1) Fatura / NF** | `account.move` fiscal | operação fiscal → **posição fiscal** (remapeia contas) + **journal** (`default_account_id` / `account_no_payment_id`) → **CONFIGURÁVEL** |
| **(2) Valoração de estoque (SVL)** | `account.move` do diário ESTOQUE, gerado por cada `stock.move` (AVCO real_time) | **contas da categoria do produto, POR EMPRESA** (§2) → **CONFIGURÁVEL** |

Detalhe e provas em `ACHADOS_TECNICOS.md`.

---

## 4. ⚠️ Lado FB é DIFERENTE

A **FB tem estoque próprio** → "tudo = terceiros" **NÃO se aplica** lá. O passivo do relatório (**R$ 785.569,62** só do MOLHO SHOYU PET) está na **Etapa 5 (recebimento do retorno na FB)**, onde hoje os componentes **re-inflam** o estoque da FB. Isso exige tratamento próprio (a NF de retorno deve **baixar** `1150200001` / componentes simbólicos, não somar ao Ativo Estoque). Ver `PLANO_EXECUCAO.md` (Etapa 5) + perguntas ao Contador.

---

## 5. Estado atual

- **Cleanup CONCLUÍDO** (2026-05-29): `rule_type` FB+LF → `not_synchronize`; SOs espúrios 73429/73430 cancelados; PO 42659 cancelada; **NF 725676 cancelada (SEFAZ)** + **picking 322049 revertido** → os **16 insumos do piloto estão de volta em FB/Estoque**. ✅ "De volta ao início."
- **Gatilho de execução ATINGIDO** (material de volta na FB). Falta apenas o "go" do Rafael para iniciar o `PLANO_EXECUCAO.md` (a partir do Passo 0).
- **Fora do escopo deste fluxo** (tratados em **outra operação**, NÃO mexer aqui): limpeza dos artefatos remanescentes do piloto — SO 73424, MO 20154/20155, POs 42666/42686.

> ⚠️ **Bloqueadores antes de executar em volume** (ver `PLANO_EXECUCAO.md`): (1) o approach de configuração das contas de categoria na LF está **raciocinado, não testado** — validar empiricamente num caso controlado antes de PROD; (2) o **lado FB (Etapa 5)** — a baixa dos componentes sem inflar o estoque da FB (passivo de R$ 785k) — **não tem mecanismo definido**; depende do Contador.

---

## Histórico de versões

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-05-29 | Diretriz inicial: abandona Opção 2; adota config de contas de categoria por-empresa na LF |
