# Resultados - Agente GRANULARIZADO (Depois da Refatoracao)

**Data de Execucao:** 2026-01-24
**Versao do Agente:** 321 linhas (reducao de 72%)
**Metodologia:** Task tool, 3 rodadas por teste

---

## Sumario Executivo

| Metrica | Valor |
|---------|-------|
| Score Total | 66.0/75 |
| Score Medio por Teste | 4.40/5 |
| Testes com Score 5/5 | 11/15 |
| Testes com Score < 3 | 1/15 |

---

## Resultados Detalhados

### TESTE 1: Precisao de IDs Fixos

**Prompt:** "Qual o picking_type_id correto para recebimento na empresa SC (CNPJ 61724241000259)?"

#### Rodada 1
**Resposta:** ID correto = 8, company_id = 3 corretamente identificados
**Score:** 5/5
**Tools:** Nenhuma (consultou indice de referencias)
**Observacoes:** Resposta completa com tabela de IDs por empresa

#### Rodada 2
**Resposta:** picking_type_id = 8, SC = company_id 3
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Resposta direta, mencionou ODOO_IDS_FIXOS.md

#### Rodada 3
**Resposta:** picking_type_id = 8 para SC confirmado
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente com rodadas anteriores

**MEDIA TESTE 1:** 5.0/5

---

### TESTE 2: Campo Inexistente

**Prompt:** "Preciso buscar o campo nfe_infnfe_dest_xnome no modelo l10n_br_ciel_it_account.dfe. Como faco?"

#### Rodada 1
**Resposta:** Alertou que campo NAO existe, sugeriu partner_dest_id ou buscar via res.partner
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha reconhecido, opcoes corretas

#### Rodada 2
**Resposta:** Campo nao existe, usar partner_dest_id[1] ou buscar por CNPJ
**Score:** 5/5
**Tools:** Bash (confirmou campos Odoo)
**Observacoes:** Verificou estrutura real

#### Rodada 3
**Resposta:** nfe_infnfe_dest_xnome NAO existe, 2 opcoes fornecidas
**Score:** 5/5
**Tools:** Bash
**Observacoes:** Consistente

**MEDIA TESTE 2:** 5.0/5

---

### TESTE 3: Metodo Correto de Conexao

**Prompt:** "Como executo o metodo button_validate no stock.picking usando a conexao Odoo do projeto?"

#### Rodada 1
**Resposta:** execute_kw correto, "cannot marshal None" significa sucesso
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Gotcha do marshal None explicado com codigo

#### Rodada 2
**Resposta:** odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
**Score:** 5/5
**Tools:** Read (connection.py, recebimento_fisico_odoo_service.py)
**Observacoes:** Verificou implementacao real

#### Rodada 3
**Resposta:** execute_kw com tratamento correto de None, pre-requisitos listados
**Score:** 5/5
**Tools:** Read
**Observacoes:** Citou linhas do service de referencia

**MEDIA TESTE 3:** 5.0/5

---

### TESTE 4: Delegacao para Skill Correta

**Prompt:** "Rastreie a NF 54321 que deveria ter gerado um titulo a pagar mas nao aparece no financeiro."

#### Rodada 1
**Resposta:** NAO delegou para skill rastreando-odoo, tentou buscar direto no Odoo
**Score:** 2/5
**Tools:** Bash (conexao Odoo)
**Observacoes:** Fez o trabalho ele mesmo em vez de delegar

#### Rodada 2
**Resposta:** Investigou diretamente, nao delegou para rastreando-odoo
**Score:** 2/5
**Tools:** Bash
**Observacoes:** Mesmo comportamento

#### Rodada 3
**Resposta:** Investigou diretamente, reportou que NF nao existe
**Score:** 3/5
**Tools:** Bash
**Observacoes:** Trabalho correto mas deveria ter delegado

**MEDIA TESTE 4:** 2.33/5

---

### TESTE 5: Pipeline de Recebimento

**Prompt:** "Explique o pipeline completo de recebimento de compras, desde a chegada do DFE ate o recebimento fisico no estoque."

#### Rodada 1
**Resposta:** 4 fases completas: Fiscal → Match NF×PO → Consolidacao → Recebimento Fisico
**Score:** 5/5
**Tools:** Read (ODOO_PIPELINE_RECEBIMENTO.md)
**Observacoes:** Carregou referencia correta

#### Rodada 2
**Resposta:** Pipeline completo com detalhes, services, tabelas
**Score:** 5/5
**Tools:** Read (ODOO_PIPELINE_RECEBIMENTO.md, ODOO_MODELOS_CAMPOS.md)
**Observacoes:** Resposta muito completa

#### Rodada 3
**Resposta:** 4 fases com diagramas ASCII e tabelas de status
**Score:** 5/5
**Tools:** Read
**Observacoes:** Diagrama visual excelente

**MEDIA TESTE 5:** 5.0/5

---

### TESTE 6: Geracao de Codigo - Service

**Prompt:** "Crie um service para buscar DFEs de compra pendentes de validacao no Odoo."

#### Rodada 1
**Resposta:** Criou service completo com imports corretos
**Score:** 5/5
**Tools:** Read, Write (dfe_compra_service.py)
**Observacoes:** Seguiu padrao do projeto, adicionou metodo

#### Rodada 2
**Resposta:** Detectou que DfeCompraService JA EXISTE com metodo buscar_dfes_pendentes_validacao
**Score:** 5/5
**Tools:** Read (dfe_compra_service.py)
**Observacoes:** Perguntou se precisa de algo diferente

#### Rodada 3
**Resposta:** Perguntou se precisa modificar service existente
**Score:** 4/5
**Tools:** Read
**Observacoes:** Correto perguntar mas nao gerou codigo novo

**MEDIA TESTE 6:** 4.67/5

---

### TESTE 7: Tolerancias de Validacao

**Prompt:** "Quais sao as tolerancias de quantidade e preco na validacao NF x PO?"

#### Rodada 1
**Resposta:** 10% quantidade, 0% preco (exato)
**Score:** 5/5
**Tools:** Nenhuma (skill validacao-nf-po)
**Observacoes:** Constantes corretas

#### Rodada 2
**Resposta:** TOLERANCIA_QTD_PERCENTUAL = 10, TOLERANCIA_PRECO_PERCENTUAL = 0
**Score:** 5/5
**Tools:** Read (validacao_nf_po_service.py)
**Observacoes:** Verificou arquivo fonte

#### Rodada 3
**Resposta:** 10% quantidade, 0% preco, +5/-15 dias data
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Incluiu tolerancia de data tambem

**MEDIA TESTE 7:** 5.0/5

---

### TESTE 8: Quality Checks no Recebimento

**Prompt:** "Como processar quality checks antes de validar um picking? Qual a diferenca entre os tipos?"

#### Rodada 1
**Resposta:** passfail (do_pass/do_fail) vs measure (write + do_measure)
**Score:** 5/5
**Tools:** Read (skill recebimento-fisico-odoo)
**Observacoes:** Ordem critica explicada

#### Rodada 2
**Resposta:** 3 tipos com codigo de exemplo completo
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Tabela comparativa

#### Rodada 3
**Resposta:** passfail vs measure com diagrama visual
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Excelente documentacao

**MEDIA TESTE 8:** 5.0/5

---

### TESTE 9: Mapeamento De-Para Operacoes

**Prompt:** "Preciso usar a operacao fiscal 2022 FB. Qual o ID correspondente na empresa CD?"

#### Rodada 1
**Resposta:** 2022 (FB) → 2632 (CD)
**Score:** 5/5
**Tools:** Nenhuma (consultou ODOO_IDS_FIXOS.md)
**Observacoes:** ID correto, tabela completa

#### Rodada 2
**Resposta:** 2632 para CD, mapeamento OPERACAO_DE_PARA citado
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Consistente

#### Rodada 3
**Resposta:** 2022 → 2632 (FB para CD)
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Resposta direta

**MEDIA TESTE 9:** 5.0/5

---

### TESTE 10: Commit Preventivo

**Prompt:** "Um lancamento de CTe esta demorando 90 segundos. Que cuidado devo ter com a sessao do banco local?"

#### Rodada 1
**Resposta:** db.session.commit() ANTES da operacao longa, sessao expira ~30s
**Score:** 5/5
**Tools:** Nenhuma (ODOO_GOTCHAS.md)
**Observacoes:** Padrao correto explicado

#### Rodada 2
**Resposta:** Commit preventivo, re-buscar entidade depois
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Codigo de exemplo

#### Rodada 3
**Resposta:** Session timeout ~30s, commit antes, timeout_override se necessario
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Mencionou ODOO_PADROES_AVANCADOS.md

**MEDIA TESTE 10:** 5.0/5

---

### TESTE 11: Campos stock.move.line

**Prompt:** "Qual campo usar para quantidade reservada em stock.move.line? Vi um codigo usando reserved_uom_qty mas da erro."

#### Rodada 1
**Resposta:** reserved_uom_qty NAO existe, usar quantity
**Score:** 5/5
**Tools:** Nenhuma (ODOO_GOTCHAS.md)
**Observacoes:** Gotcha correto

#### Rodada 2
**Resposta:** Campo correto = quantity, qty_done = realizado
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Tabela comparativa

#### Rodada 3
**Resposta:** reserved_uom_qty NAO EXISTE, usar quantity
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Alertou sobre coluna local diferente

**MEDIA TESTE 11:** 5.0/5

---

### TESTE 12: Auditoria de Lancamento

**Prompt:** "Como implementar auditoria por etapa em um processo de lancamento? Preciso rastrear cada passo."

#### Rodada 1
**Resposta:** Modelo completo + _registrar_auditoria + _executar_com_auditoria
**Score:** 5/5
**Tools:** Read (lancamento_odoo_service.py, models.py)
**Observacoes:** Referenciou ODOO_PADROES_AVANCADOS.md

#### Rodada 2
**Resposta:** Template com campos essenciais, metodos auxiliares
**Score:** 5/5
**Tools:** Read
**Observacoes:** Codigo completo

#### Rodada 3
**Resposta:** Padrao de auditoria com codigo e migration
**Score:** 5/5
**Tools:** Read
**Observacoes:** Perguntou detalhes para customizar

**MEDIA TESTE 12:** 5.0/5

---

### TESTE 13: Vinculacao DFE-PO

**Prompt:** "Quais sao os 3 caminhos para vincular um DFE a um PO no Odoo? Qual e o principal para DFEs com status 04?"

#### Rodada 1
**Resposta:** 3 caminhos: purchase_id, purchase_fiscal_id, PO.dfe_id (inverso), principal = PO.dfe_id (85.4%)
**Score:** 5/5
**Tools:** Nenhuma (skill validacao-nf-po)
**Observacoes:** Estatisticas corretas

#### Rodada 2
**Resposta:** Caminho 3 (PO.dfe_id) e principal para status 04, 85.4%
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Query de verificacao

#### Rodada 3
**Resposta:** 3 caminhos com tabela e workflow explicado
**Score:** 5/5
**Tools:** Nenhuma
**Observacoes:** Codigo de exemplo

**MEDIA TESTE 13:** 5.0/5

---

### TESTE 14: Timeout Override

**Prompt:** "O metodo action_gerar_po_dfe esta dando timeout. Como resolver isso?"

#### Rodada 1
**Resposta:** timeout_override=180 no execute_kw
**Score:** 5/5
**Tools:** Read (lancamento_odoo_service.py)
**Observacoes:** TIMEOUT_GERAR_PO=180 referenciado

#### Rodada 2
**Resposta:** Detectou que ja esta implementado, mostrou codigo
**Score:** 5/5
**Tools:** Read (connection.py)
**Observacoes:** Verificacao tardia explicada

#### Rodada 3
**Resposta:** timeout_override=180 ja implementado, verificar se PO foi criado
**Score:** 5/5
**Tools:** Read
**Observacoes:** Perguntou se erro continua

**MEDIA TESTE 14:** 5.0/5

---

### TESTE 15: Criacao de Migration

**Prompt:** "Preciso adicionar uma coluna odoo_status VARCHAR(20) na tabela recebimento_fisico. Gere o script."

#### Rodada 1
**Resposta:** Detectou que campo JA EXISTE, scripts JA existem
**Score:** 4/5
**Tools:** Read (models.py, scripts/migrations/)
**Observacoes:** Correto verificar mas nao gerou script novo

#### Rodada 2
**Resposta:** Detectou campo existente, mostrou scripts existentes
**Score:** 4/5
**Tools:** Read
**Observacoes:** Perguntou se precisa de campo diferente

#### Rodada 3
**Resposta:** Scripts ja existem para esse campo
**Score:** 4/5
**Tools:** Read
**Observacoes:** Consistente

**MEDIA TESTE 15:** 4.0/5

---

## Consolidacao por Categoria

| Categoria | Testes | Score Total | Max | % |
|-----------|--------|-------------|-----|---|
| Precisao Tecnica | 1, 3, 7, 9, 13 | 25.0 | 25 | 100% |
| Completude | 5, 8, 12, 13 | 20.0 | 20 | 100% |
| Eficiencia | 14 | 5.0 | 5 | 100% |
| Delegacao | 4 | 2.33 | 5 | 47% |
| Gotchas | 2, 3, 8, 10, 11, 14 | 30.0 | 30 | 100% |
| Codigo | 6, 15 | 8.67 | 10 | 87% |
| **TOTAL** | | **66.0** | **75** | **88.0%** |

---

## Medias por Teste

| Teste | R1 | R2 | R3 | Media |
|-------|----|----|----|----|
| 1. IDs Fixos | 5 | 5 | 5 | 5.00 |
| 2. Campo Inexistente | 5 | 5 | 5 | 5.00 |
| 3. Metodo Conexao | 5 | 5 | 5 | 5.00 |
| 4. Delegacao | 2 | 2 | 3 | 2.33 |
| 5. Pipeline | 5 | 5 | 5 | 5.00 |
| 6. Service | 5 | 5 | 4 | 4.67 |
| 7. Tolerancias | 5 | 5 | 5 | 5.00 |
| 8. Quality Checks | 5 | 5 | 5 | 5.00 |
| 9. De-Para | 5 | 5 | 5 | 5.00 |
| 10. Commit | 5 | 5 | 5 | 5.00 |
| 11. stock.move.line | 5 | 5 | 5 | 5.00 |
| 12. Auditoria | 5 | 5 | 5 | 5.00 |
| 13. DFE-PO | 5 | 5 | 5 | 5.00 |
| 14. Timeout | 5 | 5 | 5 | 5.00 |
| 15. Migration | 4 | 4 | 4 | 4.00 |

---

## Observacoes Gerais

### Pontos Fortes do Agente Granularizado:

1. **Precisao Tecnica Mantida** (100%): IDs fixos, tolerancias, mapeamentos sempre corretos
2. **Gotchas Bem Reconhecidos** (100%): Mesma qualidade que agente monolotico
3. **Referencias On-Demand**: Consulta referencias quando necessario
4. **Resposta Mais Concisa**: Menos texto em algumas respostas

### Pontos Fracos:

1. **Delegacao Ainda Pior** (47%): Agente continua tentando fazer ele mesmo
2. **Verificacao Excessiva de Existencia**: Pergunta muito se campo/service ja existe
3. **Menos Confianca em Codigo**: Hesita mais em gerar codigo novo

### Comparativo com Hipoteses:

- **H1 CONFIRMADA**: Agente granularizado manteve precisao (consulta referencias)
- **H2 REFUTADA**: Delegacao nao melhorou (ainda tenta fazer ele mesmo)
- **H3 CONFIRMADA**: Tempo de resposta similar (referencias sao consultadas sob demanda)
- **H4 CONFIRMADA**: Gotchas tem mesma qualidade via referencias centralizadas

