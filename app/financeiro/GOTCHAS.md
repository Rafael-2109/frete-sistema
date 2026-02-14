# Financeiro — Gotchas Detalhados

> Compilado em 14/02/2026 por auditoria completa dos 64 arquivos do modulo.
> O `CLAUDE.md` contem os top gotchas. Este arquivo e a referencia completa.

---

## Models (models.py, 2662 LOC)

### titulo_id: mesmo nome, semanticas opostas
`ExtratoItem.titulo_id` (linha 1355) e DEPRECADO — campo legado sem FK.
`BaixaPagamentoItem.titulo_id` (linha 1980) e ATIVO — armazena account.move.line ID do Odoo.
Ao ver `titulo_id` no codigo, verificar QUAL model antes de usar.

### calcular_valor_titulo vs to_dict: filtros divergentes
`calcular_valor_titulo()` (linha 469) soma APENAS abatimentos `previsto=False` (realizados).
`to_dict()` (linha 553) soma TODOS os abatimentos sem filtro.
`valor_titulo` e `total_abatimentos` na UI divergem quando existem previstos.

### nf_cancelada e property com query N+1
`ContasAReceber.nf_cancelada` (linha 447) faz query a FaturamentoProduto a cada acesso.
Usado em `to_dict()` — iterar N registros gera N queries extras.
NAO e campo SQL. `filter(nf_cancelada == False)` em query NAO funciona.
Routes usam subquery `exists()` em FaturamentoProduto para filtrar em SQL (contas_receber.py:99).

### Float vs Numeric misturados
~25 campos monetarios usam Float (imprecisao). ~11 usam Numeric(15,2) (exato).
Pior: `ExtratoItem.titulo_saldo_antes` e Float (1414), `ExtratoItemTitulo.titulo_saldo_antes` e Numeric (1690).
Comparar `Float == Numeric` pode falhar. Ao criar novo campo monetario, usar Numeric(15,2).

### cnpj_pagador no CNAB e da EMPRESA
`CnabRetornoItem.cnpj_pagador` (linha 2458) contem CNPJ da propria empresa (bug CNAB BMP 274).
Para CNPJ real do cliente: usar property `cnpj_cliente` (busca em ContasAReceber/Faturamento).

### matches_candidatos: tambem em BaixaPagamentoItem
Alem de ExtratoItem (1368), BaixaPagamentoItem (2000) tambem usa TEXT com JSON.
Mesmo pattern: `set_matches_candidatos()` / `get_matches_candidatos()`.
`snapshot_antes`/`snapshot_depois` em 3 models tambem sao TEXT com helpers.

### fonte_conciliacao derivada de regex
`ExtratoItem.fonte_conciliacao` (linha 1551) e property que faz pattern matching em `self.mensagem`.
NAO e campo SQL. Alterar texto da mensagem muda a classificacao da fonte.

---

## Services (26 arquivos)

### Bug 2000-01-01: titulos fantasma do Odoo
`DATA_VENCIMENTO_IGNORAR = date(2000, 1, 1)` (extrato_matching_service.py:49).
Odoo cria linhas duplicadas de desconto com vencimento 01/01/2000.
No matching: AGREGAR com titulos reais da mesma NF. Na baixa: corrigir antes.

### SCORE_MINIMO_AUTO difere: recebimentos=95, pagamentos=90
extrato_matching_service.py:46 vs pagamento_matching_service.py:69.
Atraso > 10 dias garante revisao manual (penalidade -11, score max 89 < 90).

### TRANSITORIA (22199) -> PENDENTES (26868) antes de reconciliar
Extrato Odoo usa conta TRANSITORIA. Trocar para PENDENTES via `_safe_write_statement_line()` ANTES de reconciliar. Sem troca: reconciliacao silenciosamente errada.

### Write-off wizard ja posta E reconcilia
Wizard `account.payment.register` com juros: cria + posta + reconcilia automaticamente.
NAO chamar `action_post()` nem `reconcile()` depois — causa double-posting.

### Parcela 1 no Odoo pode ser 0 ou False
`l10n_br_cobranca_parcela` armazena integer 0 como `False` no Odoo.
Buscar parcela 1: se nao encontrar, fallback para `[0, False]`.

### 5 tipos de baixa — ORDEM OBRIGATORIA
Principal -> Desconto -> Acordo -> Devolucao -> Juros.
Cada etapa revalida saldo em tempo real rebuscando do Odoo.
Juros + principal usa wizard write-off; juros avulso cria lancamento separado.

### desconto_ja_embutido — bug 2000 define comportamento
Se NF NAO passou pela correcao 2000 com modificacao, desconto ja esta no saldo Odoo.
Criar lancamento de desconto separado = desconto DUPLO.

### amount_residual NEGATIVO para contas a pagar
Odoo retorna negativo. Armazenamos `abs()`. Comparar sempre com abs().

### payment_type inversao: outbound=pagar, inbound=receber
`payment_type='outbound' + partner_type='supplier'` (pagar).
`payment_type='inbound' + partner_type='customer'` (receber).

### Bug desconto duplo Odoo: usar saldo_total, NAO balance
Odoo aplica desconto 2x em `balance`. Campo `saldo_total` tem valor correto (1x).
Formula: `valor_titulo = saldo_total`, `valor_original = saldo_total / (1 - desc_pct)`.

### Multi-company: titulo empresa X, extrato empresa Y
Pagamento DEVE ser criado na empresa do TITULO, nao do extrato.
Conta PENDENTES funciona como ponte inter-company.

### CNPJ formatado no Odoo
`l10n_br_cnpj` armazena "XX.XXX.XXX/XXXX-XX". Busca com digitos limpos nao funciona.
Para raiz: formatar como "33.652.456" (8 digitos com pontos).

### Tolerancia de matching: R$ 0.02 absoluto (nao percentual)
`TOLERANCIA_VALOR = 0.02` (extrato_matching_service.py:43).

### ConciliacaoSyncService usa flush(), NAO commit()
O CALLER controla o commit. Adicionar commit() dentro quebra atomicidade.

### Constantes duplicadas entre services
`CONTA_TRANSITORIA` e `CONTA_PAGAMENTOS_PENDENTES` definidas em baixa_pagamentos_service E extrato_conciliacao_service. Manter sincronizadas.

---

## Routes (18 arquivos)

### CNAB400 usa blueprint SEPARADO
`cnab400_bp` com prefix `/cnab400/` (raiz). TODOS demais usam `financeiro_bp` com `/financeiro/`.

### pagamentos_baixas.py SEM @login_required
TODAS as rotas de baixa de pagamentos sao publicas. Design intencional?
pendencias.py:68 tambem sem @login_required mas usa current_user.nome.

### Rota JSON publica para Power Query
`exportar_contas_receber_json()` (contas_receber.py:431) e publica com CORS.
NAO adicionar @login_required — quebra integracao Power Query.
Cuidado ao adicionar campos sensiveis ao service.

### Dois sistemas de baixa completamente distintos
`baixas.py` = contas a RECEBER (Excel, `BaixaTituloLote/Item`)
`pagamentos_baixas.py` = contas a PAGAR (extrato, `BaixaPagamentoLote/Item`)
Rotas: `/contas-receber/baixas/` vs `/contas-pagar/baixas/`

### Dois services de matching (entrada vs saida)
`lote.tipo_transacao == 'saida'` -> PagamentoMatchingService
Qualquer outro -> ExtratoMatchingService
Mesma assinatura, logica diferente.

### valor_titulo e CALCULADO
Apos criar/editar/excluir abatimento, DEVE chamar `conta.atualizar_valor_titulo()`.
Setar valor_titulo diretamente = valor incorreto.

### Comprovantes usam 'sucesso' (pt), demais usam 'success' (en)
comprovantes.py e comprovante_match.py retornam `{'sucesso': True/False}`.
TODOS os outros routes retornam `{'success': True/False}`.

### Desconciliar item: so SEM payment_id
Se `payment_id` existe, pagamento foi criado no Odoo — requer intervencao manual primeiro.

### Stats de extrato EXCLUEM conciliados
Todas queries de stats aplicam `status != 'CONCILIADO'` aos contadores.
Sem filtro: itens conciliados contados 2x. `match_unico` = MATCH_ENCONTRADO + MULTIPLOS_VINCULADOS.

### Journals DESCONTO(886), ACORDO(885), DEVOLUCAO(879) — limitados ao saldo
JUROS (1066) pode ultrapassar o saldo. Ordem: Principal -> Desconto -> Acordo -> Devolucao -> Juros.

### Empresa hardcoded como int
`{1: 'FB', 2: 'SC', 3: 'CD'}`. Sem enum, sem tabela. Model tem `@property empresa_nome`.

---

## Workers (7 arquivos)

### Lock Redis fail-open (design deliberado)
Se Redis indisponivel, lock retorna True (prosseguir sem lock).
NAO "corrigir" para retornar False — travaria sistema se Redis cair.

### lote.status CONCLUIDO mesmo com erros parciais
`lote.status = 'CONCLUIDO'` independente de erros. Verificar `linhas_erro`, nao o status.

### success=True inconsistente entre workers
- baixa_titulos: `success = itens_erro == 0` (correto)
- extrato_conciliacao: `success = True` sempre (confuso)
- comprovante_batch: `success = True` sempre (confuso)

### Timezone mismatch: agora_utc_naive vs RQ
`agora_utc_naive()` retorna Brasil. `job.started_at` e UTC do Redis.
Calculo de duracao pode ter 3h de diferenca.

### _app_context_safe() duplicado em 6 workers
Copy-paste identico. Alterar em 1 NAO altera nos demais.

### PDF desconhecido processado como boleto
Dispatcher retorna `('desconhecido', None)` -> cai no else -> OCR de boleto.
Qualquer PDF nao reconhecido gasta CPU e pode criar registros incorretos.

---

## Parsers

### Boleto hardcoded como 'sicoob'
`detectar_tipo_e_banco` retorna `('boleto', 'sicoob')` para QUALQUER boleto.

### PIX: desambiguacao depende de secoes do PDF
Regex `_RE_NOME` e identico para pagador/destinatario. Secao do PDF desambigua.
Se marcadores de secao ausentes, dados vao para secao errada.
