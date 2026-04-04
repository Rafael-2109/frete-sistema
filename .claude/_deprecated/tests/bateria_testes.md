# Bateria de Testes - Agente desenvolvedor-integracao-odoo

## Objetivo
Avaliar desempenho do agente em duas arquiteturas:
- **Monolotico**: Prompt com 1129 linhas (atual)
- **Granularizado**: Prompt com ~400 linhas + referencias on-demand

## Metodologia
- Execucao via **Task tool** com subagent_type="desenvolvedor-integracao-odoo"
- **3 rodadas** por teste para consistencia estatistica
- Total: 15 testes x 3 rodadas = **45 execucoes** por arquitetura

---

## Escala de Pontuacao

| Pontos | Significado |
|--------|-------------|
| 5 | Excelente - Resposta perfeita, sem falhas |
| 4 | Bom - Resposta correta com detalhes menores faltando |
| 3 | Adequado - Resposta funcional mas incompleta |
| 2 | Parcial - Resposta com erros ou omissoes significativas |
| 1 | Insuficiente - Resposta incorreta ou muito incompleta |
| 0 | Falha total - Nao conseguiu responder |

---

## TESTE 1: Precisao de IDs Fixos

**Categoria:** Precisao Tecnica
**Prompt:**
```
Qual o picking_type_id correto para recebimento na empresa SC (CNPJ 61724241000259)?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| ID correto | `8` | 3 pts |
| Menciona que SC = company_id 3 | Sim | 1 pt |
| Nao inventa IDs | Nenhum ID fabricado | 1 pt |
| **TOTAL** | | **5 pts** |

**Resposta Ideal:** "O picking_type_id para recebimento na empresa SC (company_id 3) e 8."

---

## TESTE 2: Campo Inexistente

**Categoria:** Gotchas
**Prompt:**
```
Preciso buscar o campo nfe_infnfe_dest_xnome no modelo l10n_br_ciel_it_account.dfe para obter a razao social do destinatario. Como faco?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Avisa que campo NAO existe | Sim, claramente | 2 pts |
| Sugere alternativa | Buscar via res.partner pelo CNPJ | 2 pts |
| Nao gera codigo com campo inexistente | Codigo nao usa nfe_infnfe_dest_xnome | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 3: Metodo Correto de Conexao

**Categoria:** Precisao Tecnica + Gotchas
**Prompt:**
```
Como executo o metodo button_validate no stock.picking usando a conexao Odoo?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Usa execute_kw (NAO execute) | `odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])` | 2 pts |
| Menciona tratamento de "cannot marshal None" | Sim, como sucesso | 2 pts |
| Avisa que execute() NAO existe | Sim | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 4: Delegacao para Skill Correta

**Categoria:** Delegacao
**Prompt:**
```
Preciso rastrear onde foi parar a NF numero 54321 que foi lancada no mes passado. Ela deveria ter gerado um titulo no financeiro.
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Indica skill rastreando-odoo | "Use a skill rastreando-odoo" | 2 pts |
| Nao tenta fazer a consulta ele mesmo | Nao gera codigo de busca complexo | 1 pt |
| Menciona que esta skill e para DESENVOLVIMENTO | Sim | 1 pt |
| Sugere script/metodo especifico | rastrear_nf() ou equivalente | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 5: Pipeline de Recebimento

**Categoria:** Completude
**Prompt:**
```
Explique o pipeline completo do recebimento de compras no sistema, desde a chegada da NF ate o recebimento fisico.
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Menciona Fase 1 (Validacao Fiscal) | Sim, com service | 1 pt |
| Menciona Fase 2 (Match NF x PO) | Sim, com tolerancias | 1 pt |
| Menciona Fase 3 (Consolidacao PO) | Sim, com PO Conciliador | 1 pt |
| Menciona Fase 4 (Recebimento Fisico) | Sim, com passos | 1 pt |
| Sequencia correta | 1→2→3→4 obrigatorio | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 6: Geracao de Codigo - Service

**Categoria:** Codigo
**Prompt:**
```
Preciso criar um service simples para buscar DFEs do tipo compra no Odoo. Gere a estrutura basica seguindo os padroes do projeto.
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Import correto | `from app.odoo.utils.connection import get_odoo_connection` | 1 pt |
| Autenticacao | `odoo.authenticate()` | 1 pt |
| Metodo correto | `search_read` com fields | 1 pt |
| Logger configurado | `logger = logging.getLogger(__name__)` | 1 pt |
| Tratamento de erro | try/except com rollback | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 7: Tolerancias de Validacao

**Categoria:** Precisao Tecnica
**Prompt:**
```
Quais sao as tolerancias de quantidade e preco usadas na validacao NF x PO?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Tolerancia quantidade | 10% | 2 pts |
| Tolerancia preco | 0% (exato) | 2 pts |
| Menciona constantes no service | TOLERANCIA_QTD_PERCENTUAL, TOLERANCIA_PRECO_PERCENTUAL | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 8: Quality Checks no Recebimento

**Categoria:** Completude + Gotchas
**Prompt:**
```
Como processar quality checks antes de validar um picking no Odoo?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Distingue passfail vs measure | Sim, com metodos diferentes | 2 pts |
| Metodo passfail | do_pass / do_fail | 1 pt |
| Metodo measure | write(measure) + do_measure | 1 pt |
| Avisa: PROCESSAR ANTES de button_validate | Sim, ordem critica | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 9: Mapeamento De-Para Operacoes

**Categoria:** Precisao Tecnica
**Prompt:**
```
Se um PO foi criado com operacao fiscal 2022 (Interna Regime Normal) na empresa FB, qual deve ser a operacao correspondente se for para a empresa CD?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| ID correto | 2632 | 3 pts |
| Explica o mapeamento | OPERACAO_DE_PARA | 1 pt |
| Nao inventa IDs | Apenas os documentados | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 10: Commit Preventivo

**Categoria:** Gotchas
**Prompt:**
```
Estou implementando um lancamento que demora ~90 segundos no Odoo. Que cuidado devo tomar com a sessao do banco local?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Avisa sobre sessao PostgreSQL expirando | Sim, ~30s | 2 pts |
| Sugere db.session.commit() ANTES | Sim | 2 pts |
| Menciona re-buscar entidade depois | Sim, sessao pode ter expirado | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 11: Campos stock.move.line

**Categoria:** Gotchas
**Prompt:**
```
Preciso ler a quantidade reservada de um stock.move.line no Odoo. Qual campo usar?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Avisa que reserved_uom_qty NAO existe | Sim | 2 pts |
| Indica campo correto | `quantity` ou `qty_done` | 2 pts |
| Explica diferenca | quantity=reservado, qty_done=realizado | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 12: Auditoria de Lancamento

**Categoria:** Completude
**Prompt:**
```
Como implementar auditoria completa por etapa em um lancamento Odoo?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Modelo de auditoria com campos essenciais | etapa, status, tempo_ms, mensagem | 2 pts |
| Registro de CADA etapa | Sim, sucesso E erro | 1 pt |
| Dados antes/depois | Opcional mas mencionado | 1 pt |
| Referencia ao lancamento_odoo_service | Como exemplo | 1 pt |
| **TOTAL** | | **5 pts** |

---

## TESTE 13: Vinculacao DFE-PO

**Categoria:** Precisao Tecnica + Completude
**Prompt:**
```
Quais sao os 3 caminhos para vincular um DFE a um PO no Odoo, e qual e o principal para DFEs em status 04?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Caminho 1: DFE.purchase_id | Sim | 1 pt |
| Caminho 2: DFE.purchase_fiscal_id | Sim, status 06 | 1 pt |
| Caminho 3: PO.dfe_id (inverso) | Sim | 1 pt |
| Identifica Caminho 3 como PRINCIPAL para status 04 | Sim | 2 pts |
| **TOTAL** | | **5 pts** |

---

## TESTE 14: Timeout Override

**Categoria:** Eficiencia + Gotchas
**Prompt:**
```
O metodo action_gerar_po_dfe esta dando timeout. Como resolver?
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Identifica que demora 60-90s | Sim | 1 pt |
| Sugere timeout_override=180 | Sim, no execute_kw | 2 pts |
| Sugere verificar se PO foi criado apos timeout | Sim, pode ter sucesso tardio | 2 pts |
| **TOTAL** | | **5 pts** |

---

## TESTE 15: Criacao de Migration

**Categoria:** Codigo + Completude
**Prompt:**
```
Preciso adicionar uma coluna odoo_status VARCHAR(20) na tabela recebimento_fisico. Gere o script de migration.
```

**Criterios de Avaliacao:**
| Criterio | Esperado | Peso |
|----------|----------|------|
| Script Python com create_app() | Sim | 1 pt |
| SQL com ADD COLUMN IF NOT EXISTS | Sim | 1 pt |
| Import correto (sys.path) | Sim | 1 pt |
| Versao SQL para Render Shell | Sim | 1 pt |
| try/except com rollback | Sim | 1 pt |
| **TOTAL** | | **5 pts** |

---

## Resumo por Categoria

| Categoria | Testes | Peso Total | Max Pontos |
|-----------|--------|------------|------------|
| Precisao Tecnica | 1, 3, 7, 9, 13 | 25% | 25 pts |
| Completude | 5, 8, 12, 13 | 20% | 20 pts |
| Eficiencia | 14 | 15% | 5 pts |
| Delegacao | 4 | 15% | 5 pts |
| Gotchas | 2, 3, 8, 10, 11, 14 | 15% | 30 pts |
| Codigo | 6, 15 | 10% | 10 pts |

**TOTAL MAXIMO: 75 pontos**

---

## Template de Registro

```markdown
### Teste X - Rodada Y

**Prompt:** [copiado do teste]

**Resposta do Agente:**
[colar resposta]

**Avaliacao:**
| Criterio | Pontos | Observacao |
|----------|--------|------------|
| 1. | /X | |
| 2. | /X | |
| ... | | |
| **TOTAL** | /5 | |

**Tools Usados:** X (Read, Grep, etc)
**Tempo de Resposta:** Xs (estimado)
```
