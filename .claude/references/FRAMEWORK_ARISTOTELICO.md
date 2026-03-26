# Framework Aristotelico — Quick Reference

Referencia rapida para uso em analise, planejamento e situacoes novas.

> **Quando usar:** Analise arquitetural, investigacao de bugs complexos, planejamento, situacoes sem regra codificada.
> **Quando NAO usar:** Execucao operacional repetitiva — regras domain-specific (R2/R3/I4) sao superiores.
> **Referencia academica:** `.claude/teoria_aristotelica_x_ia.md` e `.claude/aplicacao_aristotelica.md`

---

## Quatro Causas (checklist pre-acao)

| Causa | Pergunta-chave | No sistema |
|-------|---------------|------------|
| **Material** | Quais dados/recursos/tabelas estao envolvidos? | Substrato da operacao |
| **Formal** | Qual padrao/estrutura se aplica? (protocolo, armadilha, heuristica) | Tipo do problema |
| **Eficiente** | Que mecanismo CAUSA este resultado? (cadeia causal) | Por que acontece |
| **Final** | Qual o PROPOSITO? O que muda se der certo/errado? | Telos da acao |

**Regra de ouro:** Se a causa final estiver vazia (nenhum comportamento mudaria), a acao provavelmente nao vale a pena.

---

## Essencia vs Acidente (triagem de consequencias)

| Tipo | Definicao | Exemplo |
|------|-----------|---------|
| **Essencial** | Se perdido/errado, muda o resultado fundamental | Decisao tomada pelo usuario, regra de negocio, correcao |
| **Acidental** | Se perdido/errado, nenhuma consequencia pratica | Formatacao, timestamp de consulta, dado re-consultavel |

**Uso:** Priorizacao em consolidacao de memorias, compactacao de contexto, e triagem de riscos.

---

## Dynamis/Energeia (avaliacao de risco)

| Conceito | Definicao | Aplicacao |
|----------|-----------|-----------|
| **Dynamis** (potencia) | O que PODE acontecer — modos de falha potenciais | Pre-mortem: "imagine que ja falhou" |
| **Energeia** (ato) | O que ESTA acontecendo — estado atual observado | Testes, monitoramento, feedback |

**Pre-mortem seletivo:** Aplicar apenas para acoes `irreversible` (SQL DELETE, criar separacao). Perguntar: "Liste 2 consequencias negativas e como reverter."

---

## Mapeamento para `resolvendo-problemas`

| Fase | Conceito | Pergunta |
|------|----------|----------|
| 0 Escopo | Causa Final | Qual o TELOS? (estado desejado se resolvido) |
| 1 Pesquisa | Causa Material | Qual o SUBSTRATO? (dados, tabelas, APIs) |
| 2 Analise | Formal + Eficiente | Qual PADRAO? + Qual MECANISMO? |
| 3 Plano | Quatro Causas | Material + formal + eficiente + final por tarefa |
| 4 Validacao | Dynamis/Energeia | Pre-mortem: quais falhas nao foram mapeadas? |
| 5 Implementacao | Praxis | Execucao (sem mudanca) |
| 6 Validacao Final | Ethismos | O que foi aprendido? Qual armadilha/heuristica emergiu? |

---

## Phronesis vs Techne (quando usar cada)

| Contexto | Abordagem | Exemplo |
|----------|-----------|---------|
| **Operacional repetitivo** | Phronesis (regras especificas) | R2: "verifique data_entrega <= D+2" |
| **Situacao nova** | Techne (framework geral) | Fallback deliberativo: 4 perguntas |
| **Analise/planejamento** | Ambos | Framework para estruturar, regras para validar |

> **A armadilha da phronesis:** Vocabulario filosofico faz o sistema SENTIR-SE mais sofisticado sem COMPORTAR-SE melhor. O valor esta na estrutura de raciocinio, nao no rotulo.
