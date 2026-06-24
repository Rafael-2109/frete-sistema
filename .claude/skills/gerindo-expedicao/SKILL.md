---
name: gerindo-expedicao
description: >-
  Carteira, estoque e separacao PRE-faturamento. Gatilhos: "tem pedido do
  Atacadao?", "pedido VCD123 esta em separacao?", "quanto tem de palmito?",
  "quando VCD123 fica disponivel?", "crie separacao do VCD123 pra amanha". Anti:
  ja faturado -> monitorando-entregas; NF no Odoo -> rastreando-odoo; analise
  P1-P7 completa -> analista-carteira.
allowed-tools: Read, Bash, Glob, Grep
---

# Gerindo Expedicao

Skill para consultas e operacoes logisticas da Nacom Goya.

---

## Quando Usar Esta Skill

USE para:
- Consultas de pedidos: "tem pedido do Atacadao?", "pedido VCD123 esta em separacao?"
- Consultas de estoque: "quanto tem de palmito?", "chegou cogumelo?"
- Analise de disponibilidade: "quando VCD123 fica disponivel?", "o que vai dar falta?"
- Calculo de prazo: "se embarcar amanha, quando chega?"
- Criacao de separacao: "crie separacao do VCD123 pra amanha"

NAO USE para:
- Analise COMPLETA da carteira com decisoes (use o Agent `analista-carteira`)
- Comunicacao com PCP ou Comercial (use o Agent)
- Decisoes de priorizacao P1-P7 (use o Agent)

---

## REGRAS CRITICAS (NUNCA VIOLAR)

### 1. GUARDRAIL ANTI-ALUCINACAO
**PROIBIDO** criar, calcular ou inferir dados que NAO foram retornados pelo script.
Se precisar de dado que nao veio no script: EXECUTE o script com flag adequado ou PERGUNTE ao usuario.

### 2. FIDELIDADE AO OUTPUT DO SCRIPT
**TODA informacao na resposta DEVE ter origem no JSON retornado pelo script.**
- Quantidades, valores, datas, nomes: copiar EXATAMENTE do JSON
- NAO arredondar, estimar ou interpolar valores
- Se o script retornou resultado vazio (0 itens), informar claramente: "Nao ha dados cadastrados para [periodo/filtro]"
- NAO inventar dados para preencher resultados vazios
- Sugerir alternativas: "Posso verificar com horizonte maior" ou "Quer que consulte por outro filtro?"

### 3. FILTRAGEM DE FALSE POSITIVES
Scripts com busca semantica podem retornar produtos irrelevantes (ex: "maionese" ao buscar "ketchup").
- **Verificar** se cada item retornado corresponde ao que o usuario pediu
- **Descartar** itens que nao sao do produto solicitado
- **Informar** ao usuario quando houver descarte: "O script tambem retornou [X] por semelhanca, mas nao e [produto pedido]"

### 4. REGRA DE FALLBACK (NUNCA TRAVAR)
Se um script falhar: SEMPRE responda ao usuario com erro e alternativa.
**NUNCA:** Ficar em silencio, travar, ou tentar criar scripts customizados.

### 5. SIMULAR ANTES DE EXECUTAR (ACOES)
Para QUALQUER acao que modifica dados (criar separacao):
1. Executar SEM --executar (simular)
2. Mostrar resultado ao usuario
3. AGUARDAR confirmacao explicita
4. So entao executar COM --executar

### 6. ITEM LIMITANTE — CONFIRMACAO DUPLA OBRIGATORIA
Se a simulacao de `criando_separacao_pedidos.py` retornar `alertas_estoque` NAO-VAZIO:
- **PROIBIDO** executar `--executar` direto, mesmo com confirmacao previa generica do usuario
  (ex: "criar separacao na data Y" NAO autoriza executar com item em falta).
- **OBRIGATORIO** apresentar ao usuario **as opcoes** explicitamente:
  - **A)** Separacao COMPLETA com item em falta (usuario aceita risco de inconsistencia
    operacional na expedicao — separacao tera item incompleto vs estoque)
  - **B)** Separacao PARCIAL `--apenas-estoque` ou excluindo o item limitante
    (`--excluir-produtos '["COD"]'`), expedindo apenas o disponivel
  - **C)** Aguardar disponibilidade (sem criar separacao agora) — sugerir nova data baseada
    em `consultando_programacao_producao.py --produto <produto_em_falta>`
- AGUARDAR escolha explicita (A, B ou C) ANTES de executar `--executar`.
- Motivo: criar separacao completa com item em falta gera inconsistencia na expedicao
  (item nao saira no embarque mas estara reservado, gerando ajuste manual posterior).

---

## DECISION TREE - Qual Script Usar?

### Mapeamento Rapido

| Se a pergunta menciona... | Use este script | Com estes parametros |
|---------------------------|-----------------|----------------------|
| **PRODUTO + CLIENTE/GRUPO** ("quanto de X pro Y?") | `consultando_situacao_pedidos.py` | `--grupo Y --produto X` |
| **Pedidos de um grupo** ("tem pedido do atacadao?") | `consultando_situacao_pedidos.py` | `--grupo atacadao` |
| **Pedidos de um cliente** ("tem pedido do Carrefour?") | `consultando_situacao_pedidos.py` | `--cliente Carrefour` |
| **Pedidos atrasados** | `consultando_situacao_pedidos.py` | `--atrasados` |
| **Estoque de produto** ("quanto tem de X?") | `consultando_produtos_estoque.py` | `--produto X --completo` |
| **Entradas recentes** ("chegou X?") | `consultando_produtos_estoque.py` | `--produto X --entradas` |
| **Ruptura/falta** ("vai faltar X?") | `consultando_produtos_estoque.py` | `--ruptura --dias 7` |
| **Scan ruptura proativo** ("o que vai faltar?") | `consultando_produtos_estoque.py` | `--scan-ruptura-global --dias 7` |
| **Co-passageiros embarque** | `consultando_situacao_pedidos.py` | `--co-passageiros-embarque 1234` |
| **Quando pedido fica disponivel** | `analisando_disponibilidade_estoque.py` | `--pedido VCD123` |
| **Disponibilidade de grupo** | `analisando_disponibilidade_estoque.py` | `--grupo atacadao --completude` |
| **Prazo de entrega** ("quando chega?") | `calculando_leadtime_entrega.py` | `--pedido X --data-embarque Y` |
| **Criar separacao** | `criando_separacao_pedidos.py` | `--pedido X --expedicao Y` (SEM --executar!) |
| **Gerar embarque** (de separacoes ja escolhidas) | `gerar_embarque.py` | `--user-id N --lotes '[...]' --transportadora-id T --tabela "..."` OU `--user-id N --embarque-origem ID` (SEM --confirmar!) |
| **Adicionar lote a embarque EXISTENTE** | `adicionando_item_embarque.py` | `--embarque-id N --lote LOTE_... --user-id N` (SEM --confirmar!) |
| **Programacao de producao** | `consultando_programacao_producao.py` | `--listar --dias 7` |
| **Analise completa da carteira** | `analisando_carteira_completa.py` | `--resumo` ou sem parametros |
| **Priorizar por P1-P7** | `analisando_carteira_completa.py` | `--prioridade N` |

### Regras de Decisao (em ordem de prioridade)

1. **PRODUTO + CLIENTE/GRUPO juntos:** → `consultando_situacao_pedidos.py --grupo X --produto Y`
2. **PEDIDOS de cliente/grupo (sem produto):** → `consultando_situacao_pedidos.py --grupo X`
3. **ESTOQUE de produto (sem cliente):** → `consultando_produtos_estoque.py --produto X --completo`
4. **DISPONIBILIDADE de pedido:** → `analisando_disponibilidade_estoque.py --pedido X`
5. **PRAZO de entrega:** → `calculando_leadtime_entrega.py`
6. **ACAO de criar separacao:** → `criando_separacao_pedidos.py` (SEMPRE simular antes!)
7. **ACAO de gerar embarque** (separacoes JA escolhidas → Cotacao+Embarque): → `gerar_embarque.py` (SEMPRE dry-run antes! `--confirmar` efetiva). NAO lanca frete — o frete nasce depois na portaria/faturamento. v1 SO Nacom (recusa CARVIA-/ASSAI-).
8. **ACAO de adicionar 1 lote a embarque JA EXISTENTE**: → `adicionando_item_embarque.py` (SEMPRE dry-run antes! `--confirmar` efetiva). Recalcula os totais por SOMA dos itens ativos (`sincronizar_totais_embarque`) — NUNCA incremente o total na mao (infla). SO Nacom (LOTE_*); itens CARVIA-* tem fluxo proprio (`reconciliar_embarque_carvia`).

### --cliente vs --grupo (IMPORTANTE)
- **Loja especifica mencionada** (ex: "Atacadao 183", "Assai SP"): usar `--cliente "ATACADAO 183"`
- **Grupo inteiro** (ex: "Atacadao", "Assai"): usar `--grupo atacadao`
- Se resultado de `--grupo` veio muito amplo e usuario quer loja especifica: refinar com `--cliente`

### Como Decidir (Raciocinio Obrigatorio)

**PASSO 1**: O que o usuario quer? (PEDIDOS / ESTOQUE / DISPONIBILIDADE / PRAZO / ACAO)
**PASSO 2**: Tem cliente/grupo? (SIM + produto → situacao_pedidos | SIM sem produto → situacao_pedidos | NAO → produtos_estoque)
**PASSO 3**: A escolha faz sentido? (ESTOQUE mas "pro atacadao" → ERRADO, use PEDIDOS)
**PASSO 4**: Em duvida → pergunte ao usuario!

---

## Termos Ambiguos - PERGUNTE antes de agir!

#### "programacao de entrega" (CRITICO - 4 interpretacoes)
A) Data que cliente solicitou (`data_entrega_pedido`) | B) Data de expedicao (`expedicao`) | C) Data de chegada (`agendamento`) | D) Protocolo de agendamento (`protocolo`)

#### "quantidade pendente"
Acao padrao: Mostrar AMBOS: "Na carteira: X un | Em separacao: Y un | Total: Z un"

#### Multiplas lojas do mesmo grupo
Se resultado tiver mais de 1 loja: PERGUNTAR qual loja.

---

## Scripts — Referencia Detalhada

**Para parametros completos, retornos e modos de operacao**: LER `SCRIPTS.md`

Resumo dos 10 scripts:

| # | Script | Proposito |
|---|--------|-----------|
| 1 | `analisando_disponibilidade_estoque.py` | Disponibilidade para pedidos/grupos |
| 2 | `consultando_situacao_pedidos.py` | Pedidos por filtros diversos |
| 3 | `consultando_produtos_estoque.py` | Estoque, movimentacoes, projecoes |
| 4 | `calculando_leadtime_entrega.py` | Data entrega ou data embarque reversa |
| 5 | `criando_separacao_pedidos.py` | Criar separacoes (simular antes!) |
| 6 | `consultando_programacao_producao.py` | Programacao de producao |
| 7 | `resolver_entidades.py` | Utilitario interno de resolucao |
| 8 | `analisando_carteira_completa.py` | Analise P1-P7 completa com decisoes |
| 9 | `gerar_embarque.py` | Gerar embarque (Cotacao+Embarque) de separacoes ja escolhidas — dry-run antes! NAO lanca frete |
| 10 | `adicionando_item_embarque.py` | Anexar 1 lote Nacom a embarque EXISTENTE — dry-run antes! Recalcula totais por SOMA (anti-inflacao) |

---

## Fluxo de Criacao de Separacao

| Campo | Obrigatorio | Como Obter |
|-------|-------------|------------|
| Pedido | SIM | Usuario informa |
| Data expedicao | SIM | Usuario informa |
| Tipo (completa/parcial) | SIM | Perguntar se nao especificado |
| Agendamento | CONDICIONAL | Verificar ContatoAgendamento pelo CNPJ |
| Protocolo | CONDICIONAL | Se exige agendamento |

Sequencia: SIMULAR → Verificar alertas → Mostrar → Confirmar → EXECUTAR

---

## Resumo Padrao de Pedido (CONSULTAS)

Quando responder consulta de UM pedido especifico (ex: "pedido VCD123 esta completo?"),
INCLUIR PROATIVAMENTE no resumo inicial — sem o usuario pedir:

| Metrica | Origem (script `consultando_situacao_pedidos.py --status`) |
|---------|-----------------------------------------------------------|
| Cliente, cidade/UF, CEP | `pedido.cliente`, `pedido.cidade`, `pedido.uf`, `pedido.cep` |
| Data entrega solicitada | `pedido.data_entrega_pedido` |
| Status atual | `detalhes.status_descricao` (ex: "100% em separacao") |
| Valor total | `detalhes.valor_total_pedido` |
| Itens (count) | derivado do detalhe do retorno |
| **Peso total (kg)** | `pedido.peso_total_kg` |
| **Volume total (m3)** | `pedido.volume_total_m3` |
| **Pallets** | `pedido.pallets_total` |
| Incoterm / FOB | `pedido.incoterm`, `pedido.eh_fob` |
| Bonificacao? | `pedido.eh_bonificacao` |

Motivo: peso/volume/pallets sao informacoes operacionais basicas frequentemente solicitadas
para planejar embarque, frete e logistica. Omiti-las gera turnos desnecessarios.
Se o script nao retornar volume_total_m3 (cadastro sem dimensoes — altura/largura/comprimento
zerados em CadastroPalletizacao), o valor sera 0; informar "volume nao cadastrado para
[N produtos]" em vez de simular.

---

## Organizacao de Resultados na Resposta

### Muitos itens (>10): Priorizar e agrupar
- **Ordenar** por relevancia: valor em risco, urgencia (ruptura antes de deficit), quantidade
- **Mostrar top 5-10** na resposta principal com tabela
- **Agrupar** por categoria quando aplicavel (familia de produto, loja, urgencia)
- **Resumir totais**: "39 produtos criticos, Top 10 por valor em risco:"
- **Oferecer detalhamento**: "Quer ver a lista completa?" ou "Posso detalhar por [criterio]?"

### Poucos itens (<10): Mostrar todos
- Listar individualmente com dados completos

### Resultado vazio (0 itens):
- Informar claramente: "Nao ha [X] para [filtro/periodo]"
- Sugerir motivos possiveis (dados nao cadastrados, periodo diferente)
- Oferecer alternativas (horizonte maior, filtro diferente)

---

## Leitura de References (Sob Demanda)

| Gatilho na Pergunta | Reference a Ler |
|---------------------|-----------------|
| Produto mencionado | `references/products.md` |
| Cliente/Grupo | `references/business.md` |
| Termo desconhecido | `references/glossary.md` |
| Variacao de escrita | `references/synonyms.md` |
| Comunicar PCP/Comercial | `references/communication.md` |
| Duvida de script | `references/examples.md` |
| Priorizacao, clientes top, SLAs | `references/context.md` |

**Grupos Empresariais:** `--grupo atacadao`, `--grupo assai`, `--grupo tenda`
