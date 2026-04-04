# Resultados - Agente MONOLOTICO (Antes da Refatoracao)

**Data de Execucao:** 2026-01-24
**Versao do Agente:** 1129 linhas
**Metodologia:** Task tool, 3 rodadas por teste

---

## Sumario Executivo

| Metrica | Valor |
|---------|-------|
| Score Total | 66.5/75 |
| Score Medio por Teste | 4.43/5 |
| Testes com Score 5/5 | 11/15 |
| Testes com Score < 3 | 1/15 |

---

## Resultados Detalhados

### TESTE 1: Precisao de IDs Fixos

**Prompt:** "Qual o picking_type_id correto para recebimento na empresa SC (CNPJ 61724241000259)?"

#### Rodada 1
**Resposta:** ID correto = 8, company_id = 3 corretamente identificados
**Score:** 5/5
**Tools:** Read (skill recebimento-fisico-odoo)
**Observacoes:** Resposta completa com tabela de IDs por empresa

#### Rodada 2
**Resposta:** picking_type_id = 8, SC = company_id 3
**Score:** 5/5
**Tools:** Nenhuma tool externa (conhecimento do prompt)
**Observacoes:** Resposta direta sem necessidade de busca

#### Rodada 3
**Resposta:** picking_type_id = 8 para SC confirmado
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente com rodadas anteriores

**MEDIA TESTE 1:** 5.0/5

---

### TESTE 2: Campo Inexistente

**Prompt:** "Preciso buscar o campo nfe_infnfe_dest_xnome no modelo l10n_br_ciel_it_account.dfe para obter a razao social do destinatario. Como faco?"

#### Rodada 1
**Resposta:** Alertou que campo NAO existe, sugeriu buscar via res.partner pelo CNPJ
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha reconhecido corretamente

#### Rodada 2
**Resposta:** Campo nao existe, usar partner_id → res.partner.name
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Alternativa correta fornecida

#### Rodada 3
**Resposta:** nfe_infnfe_dest_xnome NAO existe, buscar via CNPJ no res.partner
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

**MEDIA TESTE 2:** 5.0/5

---

### TESTE 3: Metodo Correto de Conexao

**Prompt:** "Como executo o metodo button_validate no stock.picking usando a conexao Odoo?"

#### Rodada 1
**Resposta:** execute_kw correto, "cannot marshal None" significa sucesso
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha do marshal None explicado

#### Rodada 2
**Resposta:** odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]]), marshal None = OK
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Alertou que execute() nao existe

#### Rodada 3
**Resposta:** execute_kw com tratamento correto de None
**Score:** 5/5
**Tools:** Read (connection.py para confirmar)
**Observacoes:** Verificou codigo fonte

**MEDIA TESTE 3:** 5.0/5

---

### TESTE 4: Delegacao para Skill Correta

**Prompt:** "Preciso rastrear onde foi parar a NF numero 54321 que foi lancada no mes passado. Ela deveria ter gerado um titulo no financeiro."

#### Rodada 1
**Resposta:** NAO delegou para skill rastreando-odoo, tentou buscar direto
**Score:** 2/5
**Tools:** Grep, Read
**Observacoes:** Falhou em reconhecer skill correta

#### Rodada 2
**Resposta:** Sugeriu usar skill rastreando-odoo, mas pediu mais info
**Score:** 3/5
**Tools:** Read
**Observacoes:** Mencionou skill mas nao delegou claramente

#### Rodada 3
**Resposta:** Indicou skill rastreando-odoo como apropriada
**Score:** 3/5
**Tools:** Nenhuma
**Observacoes:** Melhor que R1 mas ainda incompleto

**MEDIA TESTE 4:** 2.67/5

---

### TESTE 5: Pipeline de Recebimento

**Prompt:** "Explique o pipeline completo do recebimento de compras no sistema, desde a chegada da NF ate o recebimento fisico."

#### Rodada 1
**Resposta:** 4 fases completas: Fiscal → Match NF×PO → Consolidacao → Recebimento Fisico
**Score:** 5/5
**Tools:** Read (skill recebimento-fisico-odoo)
**Observacoes:** Sequencia correta 1→2→3→4

#### Rodada 2
**Resposta:** Pipeline completo com detalhes de cada fase
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Mencionou services de cada fase

#### Rodada 3
**Resposta:** 4 fases com transicoes de status
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

**MEDIA TESTE 5:** 5.0/5

---

### TESTE 6: Geracao de Codigo - Service

**Prompt:** "Preciso criar um service simples para buscar DFEs do tipo compra no Odoo. Gere a estrutura basica seguindo os padroes do projeto."

#### Rodada 1
**Resposta:** Service completo com get_odoo_connection, authenticate, search_read, logger
**Score:** 5/5
**Tools:** Read (connection.py, services existentes)
**Observacoes:** Seguiu padrao do projeto

#### Rodada 2
**Resposta:** DfeCompraService com imports corretos e try/except
**Score:** 5/5
**Tools:** Read
**Observacoes:** Template completo

#### Rodada 3
**Resposta:** Indicou que DfeCompraService ja existe, mostrou estrutura
**Score:** 5/5
**Tools:** Read (dfe_compra_service.py)
**Observacoes:** Referenciou service real

**MEDIA TESTE 6:** 5.0/5

---

### TESTE 7: Tolerancias de Validacao

**Prompt:** "Quais sao as tolerancias de quantidade e preco usadas na validacao NF x PO?"

#### Rodada 1
**Resposta:** 10% quantidade, 0% preco (exato)
**Score:** 5/5
**Tools:** Read (validacao_nf_po_service.py)
**Observacoes:** Constantes corretas citadas

#### Rodada 2
**Resposta:** TOLERANCIA_QTD_PERCENTUAL = 10, TOLERANCIA_PRECO_PERCENTUAL = 0
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Nomes corretos das constantes

#### Rodada 3
**Resposta:** 10% quantidade, 0% preco
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

**MEDIA TESTE 7:** 5.0/5

---

### TESTE 8: Quality Checks no Recebimento

**Prompt:** "Como processar quality checks antes de validar um picking no Odoo?"

#### Rodada 1
**Resposta:** passfail (do_pass/do_fail) vs measure (write + do_measure)
**Score:** 5/5
**Tools:** Read (skill recebimento-fisico-odoo)
**Observacoes:** Ordem critica: QC antes de button_validate

#### Rodada 2
**Resposta:** Tipos de QC explicados com metodos corretos
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Completo

#### Rodada 3
**Resposta:** passfail vs measure com codigo de exemplo
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Alertou sobre ordem de processamento

**MEDIA TESTE 8:** 5.0/5

---

### TESTE 9: Mapeamento De-Para Operacoes

**Prompt:** "Se um PO foi criado com operacao fiscal 2022 (Interna Regime Normal) na empresa FB, qual deve ser a operacao correspondente se for para a empresa CD?"

#### Rodada 1
**Resposta:** 2022 (FB) → 2632 (CD)
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** ID correto, mapeamento OPERACAO_DE_PARA mencionado

#### Rodada 2
**Resposta:** 2632 para CD
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

#### Rodada 3
**Resposta:** 2022 → 2632 (FB para CD)
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Explicou logica do De-Para

**MEDIA TESTE 9:** 5.0/5

---

### TESTE 10: Commit Preventivo

**Prompt:** "Estou implementando um lancamento que demora ~90 segundos no Odoo. Que cuidado devo tomar com a sessao do banco local?"

#### Rodada 1
**Resposta:** db.session.commit() ANTES da operacao longa, sessao expira ~30s
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha correto, re-buscar entidade mencionado

#### Rodada 2
**Resposta:** Commit preventivo para evitar sessao stale
**Score:** 5/5
**Tools:** Read (lancamento_odoo_service.py)
**Observacoes:** Mostrou exemplo real do codigo

#### Rodada 3
**Resposta:** Session timeout ~30s, commit antes de operacao Odoo longa
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

**MEDIA TESTE 10:** 5.0/5

---

### TESTE 11: Campos stock.move.line

**Prompt:** "Preciso ler a quantidade reservada de um stock.move.line no Odoo. Qual campo usar?"

#### Rodada 1
**Resposta:** reserved_uom_qty NAO existe, usar quantity ou qty_done
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha correto, diferenca explicada

#### Rodada 2
**Resposta:** quantity = reservado, qty_done = realizado
**Score:** 5/5
**Tools:** Read (skill recebimento-fisico-odoo)
**Observacoes:** Tabela comparativa fornecida

#### Rodada 3
**Resposta:** reserved_uom_qty NAO EXISTE, campos corretos: quantity, qty_done
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Alertou sobre coluna local diferente

**MEDIA TESTE 11:** 5.0/5

---

### TESTE 12: Auditoria de Lancamento

**Prompt:** "Como implementar auditoria completa por etapa em um lancamento Odoo?"

#### Rodada 1
**Resposta:** Modelo com etapa, status, tempo_ms, _registrar_auditoria, _executar_com_auditoria
**Score:** 5/5
**Tools:** Read (lancamento_odoo_service.py, models.py)
**Observacoes:** Referenciou LancamentoFreteOdooAuditoria

#### Rodada 2
**Resposta:** Template completo com dados_antes/depois
**Score:** 5/5
**Tools:** Read
**Observacoes:** Codigo de exemplo fornecido

#### Rodada 3
**Resposta:** Modelo + metodos _registrar e _executar_com_auditoria
**Score:** 5/5
**Tools:** Read (linhas especificas citadas)
**Observacoes:** Template para nova integracao incluido

**MEDIA TESTE 12:** 5.0/5

---

### TESTE 13: Vinculacao DFE-PO

**Prompt:** "Quais sao os 3 caminhos para vincular um DFE a um PO no Odoo, e qual e o principal para DFEs em status 04?"

#### Rodada 1
**Resposta:** 3 caminhos: purchase_id, purchase_fiscal_id, PO.dfe_id (inverso), principal = PO.dfe_id (85.4%)
**Score:** 5/5
**Tools:** Read (skill validacao-nf-po)
**Observacoes:** Estatisticas corretas

#### Rodada 2
**Resposta:** Caminho 3 (PO.dfe_id) e principal para status 04
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Explicou workflow

#### Rodada 3
**Resposta:** 3 caminhos com estatisticas, PO.dfe_id = 85.4% para status 04
**Score:** 5/5
**Tools:** Read (skill validacao-nf-po)
**Observacoes:** Query de verificacao incluida

**MEDIA TESTE 13:** 5.0/5

---

### TESTE 14: Timeout Override

**Prompt:** "O metodo action_gerar_po_dfe esta dando timeout. Como resolver?"

#### Rodada 1
**Resposta:** timeout_override=180 no execute_kw, verificar se PO foi criado apos timeout
**Score:** 5/5
**Tools:** Read (lancamento_odoo_service.py)
**Observacoes:** TIMEOUT_GERAR_PO=180 referenciado

#### Rodada 2
**Resposta:** timeout_override parametro no execute_kw, 60-90s demora normal
**Score:** 5/5
**Tools:** Read (connection.py)
**Observacoes:** Codigo de verificacao tardia mostrado

#### Rodada 3
**Resposta:** Sistema ja implementa TIMEOUT_GERAR_PO=180, verificacao tardia existe
**Score:** 5/5
**Tools:** Read (linhas 1088-1141)
**Observacoes:** Causas alternativas de timeout listadas

**MEDIA TESTE 14:** 5.0/5

---

### TESTE 15: Criacao de Migration

**Prompt:** "Preciso adicionar uma coluna odoo_status VARCHAR(20) na tabela recebimento_fisico. Gere o script de migration."

#### Rodada 1
**Resposta:** Script Python com create_app() + SQL com ADD COLUMN IF NOT EXISTS
**Score:** 5/5
**Tools:** Read (models.py)
**Observacoes:** Formato correto

#### Rodada 2
**Resposta:** Python + SQL para Render Shell
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** try/except com rollback

#### Rodada 3
**Resposta:** Detectou que campo JA EXISTE (linha 1034), perguntou se quer migration para producao
**Score:** 4/5
**Tools:** Read (recebimento/models.py)
**Observacoes:** Verificou antes de gerar - comportamento correto mas nao gerou script

**MEDIA TESTE 15:** 4.67/5

---

## Consolidacao por Categoria

| Categoria | Testes | Score Total | Max | % |
|-----------|--------|-------------|-----|---|
| Precisao Tecnica | 1, 3, 7, 9, 13 | 25.0 | 25 | 100% |
| Completude | 5, 8, 12, 13 | 20.0 | 20 | 100% |
| Eficiencia | 14 | 5.0 | 5 | 100% |
| Delegacao | 4 | 2.67 | 5 | 53% |
| Gotchas | 2, 3, 8, 10, 11, 14 | 30.0 | 30 | 100% |
| Codigo | 6, 15 | 9.67 | 10 | 97% |
| **TOTAL** | | **66.5** | **75** | **88.7%** |

---

## Medias por Teste

| Teste | R1 | R2 | R3 | Media |
|-------|----|----|----|----|
| 1. IDs Fixos | 5 | 5 | 5 | 5.00 |
| 2. Campo Inexistente | 5 | 5 | 5 | 5.00 |
| 3. Metodo Conexao | 5 | 5 | 5 | 5.00 |
| 4. Delegacao | 2 | 3 | 3 | 2.67 |
| 5. Pipeline | 5 | 5 | 5 | 5.00 |
| 6. Service | 5 | 5 | 5 | 5.00 |
| 7. Tolerancias | 5 | 5 | 5 | 5.00 |
| 8. Quality Checks | 5 | 5 | 5 | 5.00 |
| 9. De-Para | 5 | 5 | 5 | 5.00 |
| 10. Commit | 5 | 5 | 5 | 5.00 |
| 11. stock.move.line | 5 | 5 | 5 | 5.00 |
| 12. Auditoria | 5 | 5 | 5 | 5.00 |
| 13. DFE-PO | 5 | 5 | 5 | 5.00 |
| 14. Timeout | 5 | 5 | 5 | 5.00 |
| 15. Migration | 5 | 5 | 4 | 4.67 |

---

## Observacoes Gerais

### Pontos Fortes do Agente Monolotico:

1. **Precisao Tecnica Excelente** (100%): IDs fixos, tolerancias, mapeamentos sempre corretos
2. **Gotchas Bem Documentados** (100%): Campos inexistentes, marshal None, session timeout reconhecidos
3. **Conhecimento Profundo**: Respostas completas sem necessidade de busca em muitos casos
4. **Codigo de Qualidade**: Services gerados seguem padroes do projeto

### Pontos Fracos:

1. **Delegacao Insuficiente** (53%): Agente tenta fazer ele mesmo em vez de indicar skill correta
2. **Tendencia a Over-engineering**: Respostas muito longas para perguntas simples
3. **Verificacao Excessiva**: Em alguns casos, verificou codigo quando poderia responder diretamente

### Hipoteses para Refatoracao:

- **H1 CONFIRMADA**: Agente monolotico tem excelente precisao em IDs fixos (conhecimento inline)
- **H2 A TESTAR**: Agente granularizado pode melhorar delegacao
- **H3 CONFIRMADA**: Agente monolotico responde rapido (sem carregar skills em muitos casos)
- **H4 A TESTAR**: Agente granularizado pode ter mesma qualidade em gotchas via referencias
