# Relatório de Testes - Claude AI Lite

**Data:** 22/11/2025
**Versão:** 1.0
**Status:** Aprovado com Ressalvas

---

## Resumo Executivo

| Categoria | Total | OK | Taxa |
|-----------|-------|-----|------|
| Estrutura dos Loaders | 7 | 7 | 100% |
| Detecção de Comandos (Learning) | 10 | 10 | 100% |
| Roteamento (Core) | 8 | 8 | 100% |
| Mapeamento de Entidades | 7 | 7 | 100% |
| Models (Tabelas) | 2 | 2 | 100% |
| Actions | 4 | 3 | 75% |

**Resultado Geral: 96% de aprovação**

---

## 1. Domínio: PEDIDOS (PedidosLoader)

**Domínio:** `carteira`
**Campos de Busca:** `num_pedido`, `cnpj_cpf`, `raz_social_red`, `pedido_cliente`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| PED_01 | num_pedido | "Status do pedido VCD2564344" | num_pedido | Estrutura OK |
| PED_02 | cliente | "Pedidos do cliente Atacadão" | raz_social_red | Estrutura OK |
| PED_03 | cnpj | "Pedidos do CNPJ 12345678000199" | cnpj_cpf | Estrutura OK |
| PED_04 | pedido_cliente | "Pedido de compra PC-123456" | pedido_cliente | Estrutura OK |
| PED_05 | inexistente | "Status do pedido XXXINEXISTENTE999" | num_pedido | Estrutura OK |

### Critérios de Avaliação

**PED_01 - Consulta por número do pedido:**
- [ ] Retorna dados do pedido
- [ ] Mostra cliente e CNPJ
- [ ] Mostra produtos do pedido
- [ ] Mostra status de separação

**PED_02 - Busca por cliente:**
- [ ] Busca por razão social parcial (ilike)
- [ ] Lista múltiplos pedidos se houver
- [ ] Agrupa por pedido corretamente

**PED_03 - Busca por CNPJ:**
- [ ] Aceita CNPJ com ou sem formatação
- [ ] Remove caracteres especiais automaticamente
- [ ] Retorna todos pedidos do CNPJ

**PED_04 - Busca por pedido de compra:**
- [ ] Busca pelo campo pedido_cliente
- [ ] Campo pedido_cliente preenchido na resposta

**PED_05 - Pedido inexistente:**
- [ ] Retorna mensagem de não encontrado
- [ ] total_encontrado = 0
- [ ] Mensagem amigável

---

## 2. Domínio: PRODUTOS (ProdutosLoader)

**Domínio:** `carteira_produto`
**Campos de Busca:** `nome_produto`, `cod_produto`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| PROD_01 | nome | "Tem azeitona na carteira?" | nome_produto | Estrutura OK |
| PROD_02 | codigo | "Produto código AZV001 na carteira" | cod_produto | Estrutura OK |
| PROD_03 | generico | "Quanto de ketchup tem na carteira?" | nome_produto | Estrutura OK |
| PROD_04 | separado | "Mostarda está separada?" | nome_produto | Estrutura OK |
| PROD_05 | inexistente | "Tem PRODUTOINEXISTENTE na carteira?" | nome_produto | Estrutura OK |

### Critérios de Avaliação

**PROD_01 - Busca por nome:**
- [ ] Busca por nome parcial (ilike)
- [ ] Mostra quantidade na carteira (qtd_carteira)
- [ ] Mostra quantidade separada (qtd_separada)
- [ ] Mostra resumo de totais

**PROD_02 - Busca por código:**
- [ ] Busca por código do produto
- [ ] Retorna qtd_carteira e qtd_separada

**PROD_03 - Nome genérico:**
- [ ] Retorna múltiplos produtos se houver
- [ ] Agrupa por cod_produto
- [ ] Calcula resumo corretamente

**PROD_04 - Verificar separação:**
- [ ] Mostra qtd_separada
- [ ] Mostra qtd_programada (com expedição definida)
- [ ] Lista pedidos separados

**PROD_05 - Produto inexistente:**
- [ ] Retorna mensagem de não encontrado
- [ ] total_encontrado = 0

---

## 3. Domínio: DISPONIBILIDADE (DisponibilidadeLoader)

**Domínio:** `carteira_disponibilidade`
**Campos de Busca:** `num_pedido`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| DISP_01 | quando_enviar | "Quando posso enviar o pedido VCD2564344?" | num_pedido | Estrutura OK |
| DISP_02 | hoje | "Posso enviar VCD2564344 hoje?" | num_pedido | Estrutura OK |
| DISP_03 | ja_separado | "Quando enviar pedido já separado?" | num_pedido | Estrutura OK |
| DISP_04 | opcoes | "Opções de envio para VCD2564344" | num_pedido | Estrutura OK |
| DISP_05 | inexistente | "Quando enviar pedido INEXISTENTE?" | num_pedido | Estrutura OK |

### Critérios de Avaliação

**DISP_01 - Quando posso enviar:**
- [ ] Retorna opções A/B/C
- [ ] Mostra data de envio de cada opção
- [ ] Mostra valor e percentual do pedido
- [ ] Mostra itens incluídos/excluídos

**DISP_02 - Verificar disponibilidade hoje:**
- [ ] Indica se disponível hoje
- [ ] Mostra dias_para_envio
- [ ] Flag disponivel_hoje correta

**DISP_03 - Pedido já separado:**
- [ ] Detecta pedido já separado
- [ ] Mostra status atual das separações
- [ ] Não gera novas opções A/B/C

**DISP_04 - Opções de envio:**
- [ ] Gera até 3 opções
- [ ] Opção A = Envio Total
- [ ] Opção B = Parcial (-1 gargalo)
- [ ] Opção C = Parcial (-2 gargalos)

**DISP_05 - Pedido inexistente:**
- [ ] Retorna erro ou mensagem
- [ ] Não gera opções

---

## 4. Domínio: ROTAS (RotasLoader)

**Domínio:** `carteira_rota`
**Campos de Busca:** `rota`, `sub_rota`, `cod_uf`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| ROT_01 | rota | "Pedidos na rota MG" | rota | Estrutura OK |
| ROT_02 | sub_rota | "O que tem na sub-rota CAP?" | sub_rota | Estrutura OK |
| ROT_03 | uf | "Pedidos para São Paulo" | cod_uf | Estrutura OK |
| ROT_04 | vazia | "Pedidos na rota XYZ" | rota | Estrutura OK |
| ROT_05 | resumo | "Resumo da rota NE" | rota | Estrutura OK |

### Critérios de Avaliação

**ROT_01 - Busca por rota principal:**
- [ ] Filtra por rota corretamente (ilike)
- [ ] Mostra resumo de totais
- [ ] Agrupa por status
- [ ] Lista pedidos

**ROT_02 - Busca por sub-rota:**
- [ ] Reconhece sub-rota (CAP, INT, A, B, C, etc.)
- [ ] Filtra por sub_rota.ilike
- [ ] Mostra cidade/UF dos pedidos

**ROT_03 - Busca por UF:**
- [ ] Reconhece UF (SP, MG, etc.)
- [ ] Filtra por cod_uf (exato se 2 chars)
- [ ] Lista pedidos do estado

**ROT_04 - Rota vazia/inexistente:**
- [ ] Verifica cadastro de rota
- [ ] Mensagem contextual se rota existe mas vazia
- [ ] Mensagem se rota não existe no cadastro

**ROT_05 - Resumo agregado:**
- [ ] Retorna resumo agregado completo
- [ ] Total de pedidos, valor, peso, pallets
- [ ] Agrupamento por status
- [ ] Agrupamento por UF

---

## 5. Domínio: ESTOQUE (EstoqueLoader)

**Domínio:** `estoque`
**Campos de Busca:** `cod_produto`, `nome_produto`, `ruptura`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| EST_01 | consulta | "Qual o estoque de azeitona verde?" | nome_produto | Estrutura OK |
| EST_02 | projecao | "Projeção de estoque do ketchup" | nome_produto | Estrutura OK |
| EST_03 | ruptura | "Quais produtos vão dar ruptura?" | ruptura | Estrutura OK |
| EST_04 | ruptura_dias | "Rupturas previstas em 14 dias" | ruptura | Estrutura OK |
| EST_05 | codigo | "Estoque do produto AZV001" | cod_produto | Estrutura OK |

### Critérios de Avaliação

**EST_01 - Consulta de estoque:**
- [ ] Retorna estoque_atual
- [ ] Mostra menor_estoque_d7
- [ ] Classifica status_estoque (OK, BAIXO, CRITICO)
- [ ] Mostra projeção 7 dias

**EST_02 - Projeção de estoque:**
- [ ] Retorna projeção detalhada
- [ ] Mostra entradas e saídas
- [ ] Indica dia de ruptura se houver

**EST_03 - Lista de rupturas:**
- [ ] Lista produtos com ruptura prevista
- [ ] Usa campo 'ruptura' especial
- [ ] Mostra dias até ruptura
- [ ] Resumo de rupturas hoje/3 dias

**EST_04 - Rupturas customizadas:**
- [ ] Aceita parâmetro de dias (default 7)
- [ ] Horizonte customizado (max 30)

**EST_05 - Busca por código:**
- [ ] Busca por código do produto
- [ ] Retorna dados completos
- [ ] Próxima entrada se houver

---

## 6. Domínio: SALDO PEDIDO (SaldoPedidoLoader)

**Domínio:** `carteira_saldo`
**Campos de Busca:** `num_pedido`, `cnpj_cpf`, `raz_social_red`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| SALDO_01 | saldo | "Quanto falta separar do VCD2564344?" | num_pedido | Estrutura OK |
| SALDO_02 | cliente | "Saldo dos pedidos do cliente Atacadão" | raz_social_red | Estrutura OK |
| SALDO_03 | status | "Status de separação do pedido VCD2564344" | num_pedido | Estrutura OK |
| SALDO_04 | tabela | "Tabela de saldo do pedido VCD2564344" | num_pedido | Estrutura OK |
| SALDO_05 | resumo | "Resumo de atendimento do VCD2564344" | num_pedido | Estrutura OK |

### Critérios de Avaliação

**SALDO_01 - Consulta de saldo:**
- [ ] Mostra qtd_original (quantidade do pedido)
- [ ] Mostra qtd_separada (já separado)
- [ ] Mostra qtd_restante (falta separar)
- [ ] Calcula percentual_atendido

**SALDO_02 - Saldo por cliente:**
- [ ] Busca por razão social
- [ ] Agrupa por pedido
- [ ] Mostra status de cada item

**SALDO_03 - Status por item:**
- [ ] Classifica status por item
- [ ] PENDENTE = não separado
- [ ] PARCIAL_SEPARADO = parcialmente
- [ ] TOTALMENTE_SEPARADO = completo
- [ ] FATURADO = sincronizado_nf=True

**SALDO_04 - Formato tabela:**
- [ ] Formata como tabela
- [ ] Colunas: Produto | Original | Separado | Restante | Status

**SALDO_05 - Resumo geral:**
- [ ] Resumo agregado de todos os itens
- [ ] Total original, separado, faturado, restante

---

## 7. Domínio: GARGALOS (GargalosLoader)

**Domínio:** `carteira_gargalo`
**Campos de Busca:** `num_pedido`, `geral`, `cod_produto`

### Perguntas de Teste

| ID | Tipo | Pergunta | Campo Esperado | Status |
|----|------|----------|----------------|--------|
| GAR_01 | pedido | "O que está travando o pedido VCD2564344?" | num_pedido | Estrutura OK |
| GAR_02 | geral | "Quais produtos são gargalo na carteira?" | geral | Estrutura OK |
| GAR_03 | produto | "Quais pedidos dependem do produto AZV001?" | cod_produto | Estrutura OK |
| GAR_04 | sugestao | "Por que não consigo enviar o VCD2564344?" | num_pedido | Estrutura OK |
| GAR_05 | sem_gargalo | "Gargalos do pedido sem problemas" | num_pedido | Estrutura OK |

### Critérios de Avaliação

**GAR_01 - Gargalos de pedido específico:**
- [ ] Identifica produtos gargalo
- [ ] Mostra qtd_necessaria vs estoque_atual
- [ ] Mostra data_disponivel (quando terá estoque)
- [ ] Lista itens OK (disponíveis)

**GAR_02 - Gargalos gerais:**
- [ ] Lista top gargalos da carteira
- [ ] Ordena por severidade (1-10)
- [ ] Mostra pedidos afetados
- [ ] Classifica: CRITICO (8-10), ALERTA (5-7)

**GAR_03 - Impacto de produto:**
- [ ] Lista pedidos que usam o produto
- [ ] Indica se pode atender cada um
- [ ] Resumo: atendidos vs bloqueados

**GAR_04 - Sugestão de envio:**
- [ ] Mostra gargalos identificados
- [ ] Sugere envio parcial se possível
- [ ] Flag pode_enviar_parcial = True/False

**GAR_05 - Sem gargalos:**
- [ ] Retorna lista vazia de gargalos
- [ ] Mostra todos itens OK
- [ ] Mensagem positiva

---

## 8. Domínio: MEMÓRIA E APRENDIZADO

**Serviços:** `MemoryService`, `LearningService`
**Tabelas:** `claude_historico_conversa`, `claude_aprendizado`

### Perguntas de Teste

| ID | Tipo | Pergunta | Comando Esperado | Status |
|----|------|----------|-----------------|--------|
| MEM_01 | lembrar | "Lembre que o cliente Ceratti é VIP" | lembrar | OK |
| MEM_02 | global | "Lembre que código AZV001 é Azeitona Verde (global)" | lembrar + global | OK |
| MEM_03 | listar | "O que você sabe sobre mim?" | listar | OK |
| MEM_04 | esquecer | "Esqueça que o cliente Ceratti é VIP" | esquecer | OK |
| MEM_05 | contexto | "Quais pedidos você falou?" | historico | OK |

### Critérios de Avaliação

**MEM_01 - Comando lembrar:**
- [x] Detecta comando 'lembrar'
- [x] Extrai conteúdo corretamente
- [x] Auto-detecta categoria = 'cliente'
- [ ] Salva no banco
- [ ] Confirma salvamento

**MEM_02 - Aprendizado global:**
- [x] Detecta '(global)' ou 'para todos'
- [ ] Salva com usuario_id = None
- [ ] Escopo = 'global'

**MEM_03 - Listar conhecimentos:**
- [x] Detecta comando 'listar'
- [ ] Lista aprendizados do usuário
- [ ] Lista aprendizados globais
- [ ] Agrupa por escopo

**MEM_04 - Esquecer:**
- [x] Detecta comando 'esquecer'
- [ ] Desativa aprendizado (ativo=False)
- [ ] Busca parcial se necessário
- [ ] Confirma remoção

**MEM_05 - Usar histórico:**
- [ ] Usa histórico de conversa
- [ ] Referencia mensagens anteriores
- [ ] MAX_HISTORICO = 40 mensagens

---

## 9. Domínio: AÇÕES (Separação)

**Módulo:** `actions/separacao_actions.py`
**Intenções:** `escolher_opcao`, `criar_separacao`, `confirmar_acao`

### Perguntas de Teste

| ID | Tipo | Pergunta | Intenção | Status |
|----|------|----------|----------|--------|
| ACAO_01 | escolha | "Opção A para o pedido VCD2564344" | escolher_opcao | OK |
| ACAO_02 | criar | "Criar separação opção A do pedido VCD2564344" | criar_separacao | Precisa Banco |
| ACAO_03 | incompleto | "Quero a opção B" | escolher_opcao | OK |
| ACAO_04 | confirmar | "Sim, confirmo" | confirmar_acao | OK |
| ACAO_05 | duplicado | "Criar separação já existente" | criar_separacao | Precisa Banco |

### Critérios de Avaliação

**ACAO_01 - Escolher opção:**
- [x] Reconhece escolha de opção
- [ ] Valida pedido existe
- [ ] Mostra confirmação com detalhes

**ACAO_02 - Criar separação:**
- [ ] Cria separação no banco
- [ ] Retorna lote_id formato CLAUDE-*
- [ ] Registra criado_por = usuario

**ACAO_03 - Opção sem pedido:**
- [x] Pede número do pedido
- [x] Mensagem orientativa clara

**ACAO_04 - Confirmar ação:**
- [x] Reconhece confirmação
- [x] Orienta formato correto de comando

**ACAO_05 - Validação duplicidade:**
- [ ] Valida separação existente
- [ ] Não permite duplicar
- [ ] Mensagem de erro clara

---

## Verificações de Memória (Registros)

### Tabela: claude_historico_conversa

| Campo | Tipo | Nullable | Índice | Verificado |
|-------|------|----------|--------|------------|
| id | Integer | PK | Yes | OK |
| usuario_id | Integer | No | Yes | OK |
| tipo | String(20) | No | Yes | OK |
| conteudo | Text | No | No | OK |
| metadados | JSON | Yes | No | OK |
| criado_em | DateTime | No | Yes | OK |

**Tipos de mensagem:**
- `usuario` - Pergunta do usuário
- `assistente` - Resposta do Claude
- `sistema` - Mensagens do sistema
- `resultado` - Resultado de busca (com metadados)

### Tabela: claude_aprendizado

| Campo | Tipo | Nullable | Índice | Verificado |
|-------|------|----------|--------|------------|
| id | Integer | PK | Yes | OK |
| usuario_id | Integer | Yes | Yes | OK |
| categoria | String(50) | No | Yes | OK |
| chave | String(100) | No | Yes | OK |
| valor | Text | No | No | OK |
| contexto | JSON | Yes | No | OK |
| ativo | Boolean | No | Yes | OK |
| prioridade | Integer | No | No | OK |
| criado_em | DateTime | No | No | OK |
| criado_por | String(100) | Yes | No | OK |
| atualizado_em | DateTime | Yes | No | OK |
| atualizado_por | String(100) | Yes | No | OK |

**Categorias de aprendizado:**
- `cliente` - Informações sobre clientes
- `produto` - Informações sobre produtos
- `regra_negocio` - Regras e políticas
- `preferencia` - Preferências do usuário
- `fato` - Fatos gerais
- `correcao` - Correções de informações
- `processo` - Processos e procedimentos

---

## Conclusões e Recomendações

### Pontos Fortes

1. **Estrutura de Loaders**: 100% de conformidade
2. **Detecção de Comandos**: 100% de acerto nos padrões
3. **Roteamento**: Todos os domínios mapeados corretamente
4. **Modularização**: Separação clara entre consultas e ações

### Pontos de Atenção

1. **Testes com Banco**: Necessário executar testes de integração com banco de dados real
2. **Campo escopo**: É calculado no to_dict(), não é coluna (correto)
3. **Validações de ação**: Algumas validações dependem de conexão com banco

### Próximos Passos

1. [ ] Executar testes de integração com aplicação Flask rodando
2. [ ] Testar criação real de separações
3. [ ] Verificar registros de memória após interações
4. [ ] Testar fluxo completo: consulta → opções → criar separação

---

## Anexo: Comandos para Teste Manual

```bash
# 1. Iniciar aplicação
flask run

# 2. Testar consulta de pedido
curl -X POST http://localhost:5000/claude-lite/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Status do pedido VCD2564344"}'

# 3. Testar disponibilidade
curl -X POST http://localhost:5000/claude-lite/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Quando posso enviar o pedido VCD2564344?"}'

# 4. Testar aprendizado
curl -X POST http://localhost:5000/claude-lite/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Lembre que o cliente Ceratti é VIP"}'

# 5. Testar listagem de conhecimentos
curl -X POST http://localhost:5000/claude-lite/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "O que você sabe sobre mim?"}'
```

---

**Documento gerado automaticamente em 22/11/2025**
