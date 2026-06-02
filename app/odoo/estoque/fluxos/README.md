# fluxos/ — árvore de FLUXOS (camada L3, progressive disclosure)

**Constituição:** [`../CLAUDE.md`](../CLAUDE.md) §5.
**Consumidor:** subagente `gestor-estoque-odoo` (carrega a FOLHA sob demanda; o prompt dele só tem a árvore de decisão).

> **Princípio (`fluxos>>skills`):** poucos átomos (skills) ⟷ muitos fluxos. Adicionar um caso de negócio = adicionar/editar uma folha aqui, **NÃO** criar skill nova. Folha = composição de átomos existentes + args. Se um caso "não cabe" nos args de um átomo, primeiro avaliar arg faltante (estender átomo retrocompatível) antes de criar átomo.

---

## Convenção

- **Numeração hierárquica:** `1 / 1.1 / 1.1.1 / 1.1.1.1`.
- **Nós internos** = condições de roteamento (perguntas objetivas). **NÃO citam skills** — vivem na árvore de decisão do prompt do subagente.
- **Folhas** = 1 arquivo `fluxos/<id>-<slug>.md` por fluxo concreto, com o bloco padrão abaixo. Carregadas sob demanda.

### Formato da FOLHA (`<id>-<slug>.md`)
```
# Fluxo <id> — <nome>
Quando: <condição da árvore que leva aqui>
Premissas (pesquisar+validar ANTES de qualquer write):
  - <produtos/cods, lote|FIFO, qtds, CFOP(D014), saldo disponível, ...>
Sequência (átomos componíveis; output de um alimenta input do próximo):
  1) <skill-átomo> <args>            → output: {...}
  2) <skill-átomo> <args (usa output do passo 1)>
Gotchas do fluxo: <refs G###>
Exemplo:
  python <script da skill> <args> --dry-run     # revisar plano
  python <script da skill> <args> --confirmar    # após OK do usuário
```

---

## Árvore de decisão (galhos — espelha o prompt do subagente)

> Status: ⬜ folha a escrever · ✅ folha pronta. Skills referenciadas nascem pelo [`../ROADMAP_SKILLS.md`](../ROADMAP_SKILLS.md).

```
1  NF inter-company (emissão/SEFAZ entre filiais)
   1.1  só faturamento (saída)
        1.1.1 saída pura até SEFAZ-OK (Skill 8 ATÔMICA L2 — 5 átomos) → ✅ v27+ S5 ([folha](1.1.1-faturamento-saida-pura.md))
        1.1.2 LF→FB ⬜ (variante p/ direção específica — pode ser substituída por 1.1.1 + constants)
        1.1.3 FB→CD ⬜ (idem)
   1.2  só entrada/escrituração
        1.2.1 caminho A — DFe via SEFAZ → escriturando-odoo ✅ v19+ ([folha](1.2.1-escriturar-dfe-industrializacao.md))
        1.2.2 caminho B — DFe via upload XML SAÍDA → escriturando-odoo ✅ v19+ ([folha](1.2.2-criar-dfe-manual-transferencia.md))
        1.2.3 COMPRAS (DFe fornecedor) → DELEGA gestor-recebimento
   1.3  transferência completa (saída+entrada) = compõe 1.1.1 + 1.2.x → ✅ v27+ S5 ([folha](1.3-transferencia-completa.md)) — caminho com-ciclo (AjusteEstoqueInventario existente)
        1.3.1 remessa AVULSA de insumo (sem ciclo de inventário) → ✅ C4 ([folha](1.3.1-remessa-avulsa-insumo.md)) — origina átomos diretamente (Skill 5 picking → Skill 8 SEFAZ → Skill 7 entrada); AjusteEstoqueInventario OPCIONAL (C1)
2  Estoque (sem NF)
   2.1 ajuste de saldo (1 quant pontual; N→1 quants via planilha) → ajustando-quant-odoo ✅ ([folha](2.1-ajuste-saldo-por-planilha.md))
   2.2 realocar saldo (lote→lote mesma loc / loc→loc mesmo lote / MIGRAÇÃO↔Indisponível) → transferindo-interno-odoo 🟡 ([folha](2.2-realocar-saldo.md))
   2.3 transferir saldo entre CÓDIGOS (par UnificacaoCodigos, mesmo lote) → (skill da feature transferencia-saldo-codigo) ⬜
   2.4 cancelar reserva / MLs órfãs / picking → operando-reservas-odoo 🟡 ([folha](2.4-cancelar-reserva-orfa.md))
   2.5 cancelar/validar/devolver picking → operando-picking-odoo 🟡 ([folha](2.5-cancelar-validar-devolver-picking.md))
   2.6 TRATAR reserva ATIVA pré-transferência (caminho A/B/C/D/E) → composição Skills 9+2.4+5+2 🟡 ([folha](2.6-tratar-reserva-bloqueia-transferencia.md))  (NOVO v7 — pré-cond inviolável de Skill 2)
   2.9 CONSULTA ao vivo (saldo restante, quants, MLs, pickings reservando) → consultando-quant-odoo 🟡 ([folha](2.9-consulta-quant-ao-vivo.md))  (+ NOVO v7: --modo move-lines/pickings cross-ref reverso)
3  Produção / PCP
   3.1 cancelar MO (single ou batch — guard G-MO-01 furo contábil) → operando-mo-odoo 🟡 ([folha](3.1-cancelar-mo.md))
       (3.1.c MO COM consumo > 0 → DELEGADO para `mrp.unbuild` cross-skill — sem skill ainda)
4  Planejamento de ajustes (READ Odoo + WRITE banco local — proposta de mudanças futuras)
   4.1 PRE-ETAPA inventario CD/FB D007 (planejar/propor/listar/aprovar com hash sha256 anti-replay) → planejando-pre-etapa-odoo 🟡 ([folha](4.1-pre-etapa-cd-d007.md))
       (substitui NFs inter-filial R$ 32,9 mi + INDISPONIBILIZAR R$ 60,5 mi por transferências internas; gera plano JSON+Excel; NÃO executa — quem executa: `09b_executar_pre_etapa.py` compõe Skills 1+2 ainda como C3 macro, não capinada)
```

> O nó **2.3** já tem spec+plano prontos (`docs/superpowers/{specs,plans}/2026-05-22-transferencia-saldo-codigos-odoo*`) — convergente: `TransferenciaSaldoCodigoService` (= `ajustar_quant`×2 + `criar_se_nao_existe` + espelho local).

---

## Como adicionar um fluxo
1. Identificar o nó na árvore (criar o galho se novo).
2. Escrever `fluxos/<id>-<slug>.md` no formato padrão, compondo átomos EXISTENTES.
3. Refletir o galho na árvore de decisão do prompt de `.claude/agents/gestor-estoque-odoo.md`.
4. Se faltar um átomo, capinar a skill antes (ver `ROADMAP_SKILLS.md`).
