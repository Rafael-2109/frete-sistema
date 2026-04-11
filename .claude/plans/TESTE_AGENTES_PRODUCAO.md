# Teste de Agentes de Producao — Prompts e Gabarito

**Data da coleta**: 04/04/2026
**Como usar**: Envie cada prompt ao agente web (chat) ou via Claude Code (subagente). Cole a resposta na coluna "Resposta Real". Compare com o gabarito.

**Legenda**:
- **R** = Teste de Routing (agente correto foi acionado?)
- **C** = Teste de Capability (dados corretos retornados?)
- **B** = Teste de Boundary (agente rejeitou e redirecionou?)

---

## 1. AUDITOR-FINANCEIRO (P0)

### R1.1 — Routing: deve acionar auditor-financeiro
**Prompt**: "Quantos itens SEM_MATCH tem no extrato?"
**Agente esperado**: `auditor-financeiro`
**Gabarito**: 2.185 itens com status_match = SEM_MATCH
| Resposta Real | OK? |
|---------------|-----|
| | |

### C1.1 — Capability: Interpretar status de match do extrato
**Prompt**: "Me da um resumo dos status de match dos itens de extrato"
**Gabarito**:
| status_match | Qtd |
|--------------|-----|
| MATCH_ENCONTRADO | 12.933 |
| MULTIPLOS_MATCHES | 7.762 |
| SEM_MATCH | 2.185 |
| PENDENTE | 909 |
| Resposta Real | OK? |
|---------------|-----|
| | |

### C1.2 — Capability: Conhecer contas Odoo criticas
**Prompt**: "Qual a conta TRANSITORIA e qual a PENDENTES no Odoo? Me explique a sequencia de reconciliacao"
**Gabarito**: TRANSITORIA = 22199 (1110100003), PENDENTES = 26868 (1110100004). Sequencia: button_draft → write partner/payment_ref → write name (re-buscar IDs) → write account_id ULTIMO → action_post
| Resposta Real | OK? |
|---------------|-----|
| | |

### B1.1 — Boundary: deve redirecionar para controlador-custo-frete
**Prompt**: "Quanto de frete gastei com o Atacadao?"
**Agente esperado**: `controlador-custo-frete` (NÃO auditor-financeiro)
| Resposta Real | OK? |
|---------------|-----|
| | |

### B1.2 — Boundary: deve redirecionar para analista-carteira
**Prompt**: "O que embarcar primeiro hoje?"
**Agente esperado**: `analista-carteira` (NÃO auditor-financeiro)
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 2. CONTROLADOR-CUSTO-FRETE (P1)

### R2.1 — Routing
**Prompt**: "Divergencias de CTe vs cotacao"
**Agente esperado**: `controlador-custo-frete`
| Resposta Real | OK? |
|---------------|-----|
| | |

### C2.1 — Capability: Dashboard de divergencias
**Prompt**: "Quantos fretes tem divergencia CTe vs cotacao acima de R$5?"
**Gabarito**: 611 fretes divergentes. Divergencia media: R$ 1.025,21. Divergencia maxima: R$ 137.802,75
| Resposta Real | OK? |
|---------------|-----|
| | |

### C2.2 — Capability: Despesas extras pendentes
**Prompt**: "Quais despesas extras estao pendentes de aprovacao?"
**Gabarito** (top 5 por valor):
| Tipo | Qtd | Valor Total |
|------|-----|-------------|
| DIARIA | 300 | R$ 204.409,52 |
| DESCARGA | 1.256 | R$ 173.163,26 |
| DEVOLUCAO | 188 | R$ 72.301,98 |
| REENTREGA | 40 | R$ 44.909,53 |
| TDE | 89 | R$ 23.959,95 |
| Resposta Real | OK? |
|---------------|-----|
| | |

### C2.3 — Capability: Conta corrente transportadoras
**Prompt**: "Qual o saldo da conta corrente das transportadoras?"
**Gabarito** (top 5 por saldo absoluto):
| Transportadora | Credito | Debito | Saldo |
|----------------|---------|--------|-------|
| TRANSPORTADORA CENTRAL | R$ 2.436,02 | R$ 0 | +R$ 2.436,02 |
| TOCANTINS TRANSPORTES | R$ 1.130,73 | R$ 3,00 | +R$ 1.127,73 |
| MONTENEGRO TRANSPORTES | R$ 50,00 | R$ 1.040,13 | -R$ 990,13 |
| FIVELOG TRANSPORTES | R$ 769,09 | R$ 0 | +R$ 769,09 |
| DAGO TRANSPORTE | R$ 364,52 | R$ 0,01 | +R$ 364,51 |
| Resposta Real | OK? |
|---------------|-----|
| | |

### B2.1 — Boundary: cotacao teorica → cotando-frete
**Prompt**: "Qual o preco de frete para Manaus 5000kg?"
**Agente esperado**: skill `cotando-frete` (NÃO controlador-custo-frete)
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 3. GESTOR-RECEBIMENTO (P1)

### R3.1 — Routing
**Prompt**: "DFEs bloqueados no recebimento"
**Agente esperado**: `gestor-recebimento`
| Resposta Real | OK? |
|---------------|-----|
| | |

### C3.1 — Capability: Dashboard pipeline
**Prompt**: "Qual o status do pipeline de recebimento? Quantos DFEs por status?"
**Gabarito**:
| Status | Qtd |
|--------|-----|
| bloqueado | 188 |
| aprovado | 3 |
(Nota: pendente e primeira_compra podem ter 0 no momento da coleta)
| Resposta Real | OK? |
|---------------|-----|
| | |

### C3.2 — Capability: Conhecer tolerancias
**Prompt**: "Quais sao as tolerancias de validacao NF x PO?"
**Gabarito**: Quantidade = 10%, Preco = 0% (exato), Data entrega = -5 a +15 dias
| Resposta Real | OK? |
|---------------|-----|
| | |

### C3.3 — Capability: Explicar primeira_compra
**Prompt**: "O que significa primeira_compra no recebimento e como resolver?"
**Gabarito**: Produto/fornecedor sem historico, sem PerfilFiscalProdutoFornecedor. Resolver: cadastrar perfil fiscal, validar NCM/CFOP/CST, aprovar via tela /recebimento/divergencias-fiscais
| Resposta Real | OK? |
|---------------|-----|
| | |

### B3.1 — Boundary: fluxo financeiro pos-recebimento → auditor-financeiro
**Prompt**: "Reconcilie o pagamento da NF de compra 12345"
**Agente esperado**: `auditor-financeiro` ou `especialista-odoo` (NÃO gestor-recebimento)
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 4. GESTOR-DEVOLUCOES (P2)

### R4.1 — Routing
**Prompt**: "Devolucoes pendentes"
**Agente esperado**: `gestor-devolucoes`
| Resposta Real | OK? |
|---------------|-----|
| | |

### C4.1 — Capability: Status pipeline NFDs
**Prompt**: "Quantas NFDs por status temos hoje?"
**Gabarito**:
| Status | Qtd |
|--------|-----|
| VINCULADA_DFE | 4.908 |
| REGISTRADA | 405 |
| Resposta Real | OK? |
|---------------|-----|
| | |

### C4.2 — Capability: Produtos mais devolvidos
**Prompt**: "Quais os 5 produtos mais devolvidos nos ultimos 90 dias?"
**Gabarito**:
| Produto | Qtd |
|---------|-----|
| PALLET [208000012] | 119 |
| COGUMELO INTEIRO BD 6x1,01 KG - CAMPO BELO | 12 |
| TOMATE SECO - BD 6X1,4 KG - CAMPO BELO | 11 |
| PIMENTA BIQUINHO - BD 6X2 KG - CAMPO BELO | 9 |
| PEPINO BD 6x2 KG - CAMPO BELO | 8 |

**Nota**: O PALLET (119) eh devolucao de vasilhame (CFOPs 1920/2920/5920/6920), nao devolucao de mercadoria. O agente deveria mencionar essa distinção.
| Resposta Real | OK? |
|---------------|-----|
| | |

### C4.3 — Capability: Conhecer fases do pipeline
**Prompt**: "Explique as fases do pipeline de devolucao. Quais estao implementadas?"
**Gabarito**: 6 fases. Fases 1-4.5 implementadas (Registro, Ocorrencia, Frete/Descarte, Vinculacao DFe, AI Resolver). Fases 5 (contagem fisica) e 6 (Odoo fiscal entry 16-step) NAO construidas.
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 5. GESTOR-ESTOQUE-PRODUCAO (P2)

### R5.1 — Routing
**Prompt**: "Quais produtos vao faltar nos proximos 7 dias?"
**Agente esperado**: `gestor-estoque-producao`
| Resposta Real | OK? |
|---------------|-----|
| | |

### C5.1 — Capability: Estoque comprometido
**Prompt**: "Quais produtos tem mais estoque comprometido por separacoes pendentes?"
**Gabarito** (top 5):
| Produto | Comprometido |
|---------|-------------|
| PESSEGOS EM CALDA - LATA 12X485 GR - LA FAMIGLIA | 3.648 |
| AZEITONA VERDE FATIADA - POUCH 24X100 GR - LA FAMIGLIA | 3.024 |
| AZEITONA VERDE INTEIRA - VD 12X500 G - CAMPO BELO | 2.797 |
| AZEITONA VERDE SEM CAROCO - POUCH 24X100 GR - LA FAMIGLIA | 2.128 |
| OL. MIS. AZEITE DE OLIVA - VD 12X500 ML - ST ISABEL | 1.930 |
| Resposta Real | OK? |
|---------------|-----|
| | |

### C5.2 — Capability: Conhecer gotchas de campos
**Prompt**: "Qual campo de saldo usar na separacao e qual na carteira principal?"
**Gabarito**: Separacao = `qtd_saldo`. CarteiraPrincipal = `qtd_saldo_produto_pedido`. NUNCA inverter — causa dados errados.
| Resposta Real | OK? |
|---------------|-----|
| | |

### B5.1 — Boundary: priorizar pedidos → analista-carteira
**Prompt**: "Crie a separacao do VCD12345 para amanha"
**Agente esperado**: `analista-carteira` (NÃO gestor-estoque-producao)
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 6. ANALISTA-PERFORMANCE-LOGISTICA (P3)

### R6.1 — Routing
**Prompt**: "Entregas atrasadas hoje"
**Agente esperado**: `analista-performance-logistica`
| Resposta Real | OK? |
|---------------|-----|
| | |

### C6.1 — Capability: Entregas atrasadas
**Prompt**: "Quantas entregas estao atrasadas?"
**Gabarito**: 61 entregas atrasadas (entregue=False, data_entrega_prevista < hoje, status_finalizacao IS NULL)
| Resposta Real | OK? |
|---------------|-----|
| | |

### C6.2 — Capability: Ranking de transportadoras
**Prompt**: "Ranking das 5 maiores transportadoras por volume nos ultimos 90 dias"
**Gabarito**:
| Transportadora | Total | Entregues | Taxa% | Lead Time |
|----------------|-------|-----------|-------|-----------|
| TOCANTINS TRANSPORTES | 138 | 77 | 55,8% | 4,7 dias |
| UMBERTO FERREIRA DE LIMA | 136 | 135 | 99,3% | 1,0 dia |
| VELOCARGAS TRANSPORTES | 113 | 76 | 67,3% | 9,1 dias |
| ADIELSON ESPEDITO DA SILVA | 102 | 100 | 98,0% | 1,0 dia |
| TRANSCABRAL TRANSPORTES | 101 | 79 | 78,2% | 1,4 dias |

**Observacao esperada**: Agente deveria destacar que UMBERTO e ADIELSON (lead time 1 dia, taxa >98%) sao provavelmente entregas locais/SP. TOCANTINS (55.8%) e VELOCARGAS (67.3%) precisam de atencao.
| Resposta Real | OK? |
|---------------|-----|
| | |

### C6.3 — Capability: Comparacao temporal (faturamento)
**Prompt**: "Compare o faturamento dos ultimos 3 meses"
**Gabarito**:
| Mes | NFs | Total Faturado |
|-----|-----|----------------|
| 2026-01 | 884 | R$ 18.127.021,03 |
| 2026-02 | 656 | R$ 16.399.166,11 |
| 2026-03 | 1.068 | R$ 22.341.088,04 |
| 2026-04 | 77 | R$ 2.124.348,54 (parcial) |

**Observacao esperada**: Marco teve +36% vs Fevereiro. Abril tem dados parciais (4 dias).
| Resposta Real | OK? |
|---------------|-----|
| | |

### C6.4 — Capability: Concentracao de embarques
**Prompt**: "Qual a distribuicao de embarques por dia da semana?"
**Gabarito** (ultimos 90 dias):
| Dia | Qtd |
|-----|-----|
| Segunda | 207 |
| Terca | 233 |
| Quarta | 246 |
| Quinta | 265 |
| Sexta | 176 |
| Sabado | 4 |

**Observacao esperada**: Quinta-feira e o dia mais concentrado (23.4%). Sexta cai 33.6% vs Quinta — possivel gargalo de programacao.
| Resposta Real | OK? |
|---------------|-----|
| | |

### B6.1 — Boundary: custo de frete → controlador-custo-frete
**Prompt**: "Qual a divergencia de CTe da Braspress?"
**Agente esperado**: `controlador-custo-frete` (NÃO analista-performance)
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## 7. EXTENSOES DE AGENTES EXISTENTES

### E7.1 — analista-carteira: awareness de devolucoes
**Prompt**: "Analise a carteira e me diga se tem clientes com devolucoes em aberto que possam afetar embarques"
**Agente esperado**: `analista-carteira` (com dados de devolucoes incluidos)
**Gabarito**: Deve consultar nf_devolucao WHERE status NOT IN ('FINALIZADA', 'CANCELADA') agrupado por CNPJ. Hoje ha 405 NFDs REGISTRADAS.
| Resposta Real | OK? |
|---------------|-----|
| | |

### E7.2 — raio-x-pedido: eixo fiscal Odoo
**Prompt**: "Raio-X completo do pedido VCD mais recente — inclui status fiscal"
**Agente esperado**: `raio-x-pedido` (com Passo 5.5 eixo fiscal via rastreando-odoo)
**Verificar**: Deve incluir secao de titulos/pagamentos do Odoo alem de carteira+NF+entregas+frete
| Resposta Real | OK? |
|---------------|-----|
| | |

### E7.3 — gestor-carvia: faturas vencidas
**Prompt**: "Faturas CarVia vencidas"
**Agente esperado**: `gestor-carvia` (com awareness financeiro)
**Gabarito** (top vencidas):
| Cliente | Fatura | Valor | Vencimento | Dias |
|---------|--------|-------|------------|------|
| PRIME VEICULOS | 34-5 | R$ 1.650 | 11/03 | 24d |
| MASTER MOTORS | 36-1 | R$ 1.440 | 13/03 | 22d |
| Laiouns Importacao | FAT-019 | R$ 1.000 | 19/03 | 16d |
| VOLT VERDE BIKE | 51-5 | R$ 3.000 | 20/03 | 15d |
| Resposta Real | OK? |
|---------------|-----|
| | |

### E7.4 — gestor-carvia: compliance
**Prompt**: "Quais riscos de compliance a CarVia tem?"
**Agente esperado**: `gestor-carvia` (com alertas compliance)
**Gabarito**: Deve mencionar: D03 (MDF-e obrigatorio interestadual — NAO IMPLANTADO), D01 (CIOT — NAO IMPLANTADO, multa ANTT), G01 (sequencia legal CT-e antes embarque — PARCIAL, opera por intuicao). 71% dos 45 POPs nao implantados.
| Resposta Real | OK? |
|---------------|-----|
| | |

---

## RESUMO DE TESTES

| # | Agente | Routing | Capability | Boundary | Total |
|---|--------|---------|------------|----------|-------|
| 1 | auditor-financeiro | 1 | 2 | 2 | **5** |
| 2 | controlador-custo-frete | 1 | 3 | 1 | **5** |
| 3 | gestor-recebimento | 1 | 3 | 1 | **5** |
| 4 | gestor-devolucoes | 1 | 3 | 0 | **4** |
| 5 | gestor-estoque-producao | 1 | 2 | 1 | **4** |
| 6 | analista-performance-logistica | 1 | 4 | 1 | **6** |
| 7 | extensoes (carteira+raio-x+carvia) | 0 | 4 | 0 | **4** |
| | **TOTAL** | **6** | **21** | **6** | **33** |

---

## NOTAS

1. **Dados do gabarito**: Coletados em 04/04/2026 via MCP Render (producao). Valores vao mudar com o tempo — o gabarito serve como referencia de ordem de grandeza, nao valor exato.
2. **Teste de routing**: No chat web, verificar se o agente correto aparece no `task_started` SSE event. No Claude Code, verificar se o subagente correto foi invocado.
3. **Teste de boundary**: O agente DEVE recusar a pergunta e redirecionar. Se responder diretamente, falhou.
4. **Colunas corretas**: Os agentes devem usar os nomes EXATOS de colunas do schema (ex: `transportadora` e nao `transportadora_nome`). Se a query falhar, e bug no agent definition.
5. **Anti-alucinacao**: Se o agente inventar numeros que nao batem com o gabarito sem citar fonte, e falha grave.
