# 🔍 ANÁLISE DETALHADA: BOTÃO "SINCRONIZAR TUDO (SEGURO)"

**Data da Análise:** 12/11/2025
**Rota:** `POST /odoo/sync-integrada/executar`
**Formulário:** Dashboard de Sincronização Integrada

---

## 📋 O QUE ACONTECE QUANDO VOCÊ CLICA NO BOTÃO

### 🎯 Resumo Executivo

Quando você clica em **"SINCRONIZAR TUDO (SEGURO)"**, o sistema executa uma sincronização **COMPLETA** em sequência fixa:

1. **FATURAMENTO** (últimas **43.200 minutos** = **30 dias** = **720 horas**)
2. **VALIDAÇÃO** de integridade
3. **CARTEIRA** (últimas **6.360 minutos** = **4,4 dias** = **106 horas**)

---

## 🔄 FLUXO COMPLETO DE EXECUÇÃO

### 1️⃣ ETAPA: INICIALIZAÇÃO

**Arquivo:** `app/odoo/routes/sincronizacao_integrada.py:154-175`

```python
@sync_integrada_bp.route('/executar', methods=['POST'])
def executar_sincronizacao_segura():
    # Captura parâmetros do formulário
    usar_filtro_carteira = request.form.get('usar_filtro_carteira') == 'on'

    # ✅ Chama service de sincronização integrada
    resultado = sync_service.executar_sincronizacao_completa_segura(
        usar_filtro_carteira=usar_filtro_carteira
    )
```

**Parâmetros:**
- `usar_filtro_carteira`: `True` (checkbox marcado por padrão)
  - Se `True`: Sincroniza apenas pedidos **NÃO entregues** (com saldo > 0)
  - Se `False`: Sincroniza **TODOS** os pedidos

---

### 2️⃣ ETAPA 1: SINCRONIZAÇÃO DE FATURAMENTO

**Arquivo:** `app/odoo/services/sincronizacao_integrada_service.py:178-240`

#### 📊 Método Chamado:
```python
def _sincronizar_faturamento_seguro(self):
    # Executa sincronização FALLBACK com limite de 20.000 linhas
    resultado_fat = self.faturamento_service.sincronizar_faturamento_incremental(
        primeira_execucao=False,
        minutos_status=43200  # ⚠️ 30 DIAS!
    )
```

#### ⏰ PERÍODO DE BUSCA: **30 DIAS (43.200 minutos)**

**Arquivo:** `app/odoo/services/faturamento_service.py:592-617`

```python
def sincronizar_faturamento_incremental(
    self,
    primeira_execucao=False,
    minutos_status=1560  # Padrão seria 26 horas (não usado no botão)
):
    # Chama método de busca otimizada
    resultado = self.obter_faturamento_otimizado(
        usar_filtro_postado=True,
        limite=0,  # Limite interno: 20.000 registros
        modo_incremental=True,  # ✅ Modo incremental ativo
        minutos_status=minutos_status  # ⚠️ 43.200 minutos = 30 dias
    )
```

#### 🔍 Query no Odoo:

**Arquivo:** `app/odoo/services/faturamento_service.py:1246-1326`

```python
def obter_faturamento_otimizado(
    self,
    modo_incremental=True,
    minutos_status=43200  # ⚠️ 30 DIAS
):
    # Calcular data de corte
    data_corte = agora_utc - timedelta(minutes=43200)  # 30 dias atrás

    # Domain no Odoo
    domain = [
        ('move_id.create_date', '>=', data_corte_str),  # ⚠️ NFs CRIADAS nos últimos 30 dias
        '|', '|', '|',
        ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
        ('move_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
        ('move_id.l10n_br_tipo_pedido', '=', 'exportacao')
    ]

    # Busca account.move.line (linhas de NF)
    dados = self.connection.search_read(
        'account.move.line',
        domain,
        campos_basicos,
        limit=20000  # ⚠️ LIMITE MÁXIMO: 20.000 registros
    )
```

#### 📊 O QUE É SINCRONIZADO:

**Modelo:** `FaturamentoProduto` (tabela `faturamento_produtos`)

**Dados buscados:**
- ✅ Notas Fiscais **CRIADAS** nos últimos **30 dias**
- ✅ Tipos: Venda, Bonificação, Industrialização, Exportação
- ✅ Limite: **20.000 linhas** (proteção contra timeout)
- ✅ Status: **Todos** (postadas, canceladas, draft)

**Processamento:**
1. Para cada NF:
   - Se **NÃO existe** no banco → **INSERT** (nova)
   - Se **JÁ existe** no banco → **UPDATE** (apenas status)
2. **Movimentações de Estoque** (automático):
   - Cria registros em `movimentacao_estoque` tipo=`SAIDA`, local=`COMERCIAL`
   - Vincula com `numero_nf`

**Campos sincronizados:**
- `numero_nf`, `data_fatura`, `cnpj_cliente`, `nome_cliente`
- `municipio`, `estado`, `vendedor`, `equipe_vendas`
- `cod_produto`, `nome_produto`, `qtd_produto_faturado`
- `preco_produto_faturado`, `valor_produto_faturado`
- `peso_unitario_produto`, `peso_total`
- `origem` (número do pedido origem)
- `status_nf` (Lançado, Cancelado, Provisório)
- `incoterm`

---

### 3️⃣ ETAPA 2: VALIDAÇÃO DE INTEGRIDADE

**Arquivo:** `app/odoo/services/sincronizacao_integrada_service.py:242-308`

```python
def _validar_integridade_pos_faturamento(self):
    # Verifica se existem registros de faturamento
    total_faturamento = db.session.query(FaturamentoProduto).count()

    if total_faturamento == 0:
        problemas.append({
            'tipo': 'SEM_FATURAMENTO',
            'nivel': 'AVISO',
            'mensagem': 'Nenhum registro de faturamento encontrado'
        })
```

**O que valida:**
- ✅ Se existem registros em `faturamento_produtos`
- ✅ Se houve algum erro de banco
- ⚠️ Não bloqueia execução (apenas alerta)

---

### 4️⃣ ETAPA 2.5: ATUALIZAR STATUS FATURADO

**Arquivo:** `app/odoo/services/sincronizacao_integrada_service.py:95-110`

```python
# Forçar atualização de status FATURADO dos pedidos
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
processador = ProcessadorFaturamento()
pedidos_atualizados = processador._atualizar_status_separacoes_faturadas()

db.session.commit()  # ⚠️ COMMIT CRÍTICO antes da carteira
```

**O que faz:**
- ✅ Atualiza status de `Separacao` para `FATURADO` se tiver NF vinculada
- ✅ Marca `sincronizado_nf=True` nas separações com NF
- ✅ **COMMIT obrigatório** antes de processar carteira

---

### 5️⃣ ETAPA 3: SINCRONIZAÇÃO DE CARTEIRA

**Arquivo:** `app/odoo/services/sincronizacao_integrada_service.py:112-142`

#### 📦 Método Chamado:
```python
resultado_carteira = self.carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
    usar_filtro_pendente=usar_filtro_carteira,  # True (checkbox marcado)
    modo_incremental=True,
    minutos_janela=6360,  # ⚠️ 4,4 DIAS (106 horas)
    primeira_execucao=False
)
```

#### ⏰ PERÍODO DE BUSCA: **4,4 DIAS (6.360 minutos = 106 horas)**

**Arquivo:** `app/odoo/services/carteira_service.py:1517-1547`

```python
def sincronizar_carteira_odoo_com_gestao_quantidades(
    self,
    usar_filtro_pendente=True,  # ✅ Apenas pedidos NÃO entregues
    modo_incremental=True,
    minutos_janela=6360,  # ⚠️ 4,4 DIAS
    primeira_execucao=False
):
    # FLUXO:
    # 1. Carrega estado atual em memória
    # 2. Busca dados novos do Odoo
    # 3. Calcula diferenças (reduções/aumentos/novos/removidos)
    # 4. Aplica mudanças respeitando hierarquia
    # 5. Substitui carteira com dados atualizados
    # 6. Verificação pós-sincronização com alertas
```

#### 🔍 Query no Odoo:

**Domain usado:**
```python
domain = [
    ('write_date', '>=', data_corte),  # ⚠️ Modificados nos últimos 4,4 dias
    ('qty_to_invoice', '>', 0),  # ✅ Apenas itens com saldo > 0 (se usar_filtro_pendente=True)
    ('state', 'in', ['sale', 'done']),  # ✅ Apenas pedidos confirmados
    ('move_ids.state', 'not in', ['cancel']),  # ✅ Sem movimentos cancelados
]
```

**Modelo Odoo:** `sale.order.line` (linhas de pedido de venda)

#### 📊 O QUE É SINCRONIZADO:

**Modelo:** `CarteiraPrincipal` (tabela `carteira_principal`)

**Dados buscados:**
- ✅ Pedidos de venda **MODIFICADOS** nos últimos **4,4 dias**
- ✅ Apenas pedidos com **saldo > 0** (qty_to_invoice > 0)
- ✅ Estados: `sale` (confirmado) e `done` (concluído)
- ✅ **SEM limite** de registros (busca tudo que matchear)

**Processamento:**
1. Carrega carteira atual em memória
2. Busca dados novos do Odoo
3. Calcula diferenças:
   - Itens **NOVOS** → INSERT
   - Itens com **quantidade REDUZIDA** → UPDATE
   - Itens com **quantidade AUMENTADA** → UPDATE
   - Itens **REMOVIDOS** do Odoo → DELETE
4. Substitui carteira (TRUNCATE + INSERT bulk)
5. Recompõe pré-separações se necessário

**Campos sincronizados:**
- `num_pedido`, `pedido_cliente`, `cod_produto`, `nome_produto`
- `qtd_produto_pedido`, `qtd_saldo_produto_pedido`, `preco_produto_pedido`
- `cnpj_cpf`, `raz_social`, `raz_social_red`
- `municipio`, `estado`, `vendedor`, `equipe_vendas`
- `expedicao`, `agendamento`, `protocolo`, `data_entrega`
- `observ_ped_1`, `tags_pedido`
- `cnpj_endereco_ent`, `empresa_endereco_ent`, `cep_endereco_ent`
- `nome_cidade`, `cod_uf`, `bairro_endereco_ent`, `rua_endereco_ent`

---

## 📊 RESUMO DOS PERÍODOS

| Etapa | Modelo Odoo | Período | Filtro | Limite |
|-------|-------------|---------|--------|--------|
| **Faturamento** | `account.move.line` | **30 dias** (43.200 min) | `create_date >=` | **20.000 registros** |
| **Carteira** | `sale.order.line` | **4,4 dias** (6.360 min) | `write_date >=` + `qty_to_invoice > 0` | **SEM limite** |

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

### 1. Por que períodos diferentes?

**Faturamento (30 dias):**
- ✅ NFs são **PERMANENTES** (não mudam após criadas)
- ✅ Busca por `create_date` (data criação)
- ✅ Objetivo: Capturar **todas NFs recentes** (incluindo canceladas)
- ✅ Período maior = maior segurança contra perda de NFs

**Carteira (4,4 dias):**
- ✅ Pedidos são **DINÂMICOS** (quantidades mudam constantemente)
- ✅ Busca por `write_date` (data modificação)
- ✅ Objetivo: Capturar apenas **pedidos alterados recentemente**
- ✅ Período menor = sincronização mais rápida

### 2. Limite de 20.000 registros no Faturamento

**Por que existe:**
- ⚠️ Proteção contra **timeout** do Odoo
- ⚠️ Consultas muito grandes (>20k registros) podem derrubar o servidor
- ⚠️ Limite interno do Odoo XML-RPC

**O que acontece se passar de 20.000:**
- ✅ Odoo retorna apenas os **primeiros 20.000** registros
- ⚠️ NFs mais antigas (dentro dos 30 dias) podem não ser sincronizadas
- ✅ Na próxima sincronização manual ou scheduler (a cada 30 min), pega o que faltou

**Solução para grandes volumes:**
- ✅ Executar sincronização **múltiplas vezes** (cada vez pega 20k)
- ✅ Scheduler automático (a cada 30 min) mantém tudo atualizado
- ✅ Usar sincronização de pedido individual para casos específicos

### 3. Filtro de Carteira (checkbox)

**Marcado (padrão):**
- ✅ Sincroniza apenas pedidos com `qty_to_invoice > 0`
- ✅ **Mais rápido** (menos registros)
- ✅ **Mais eficiente** (foco no que importa)
- ✅ Recomendado para uso normal

**Desmarcado:**
- ⚠️ Sincroniza **TODOS** os pedidos (incluindo totalmente entregues)
- ⚠️ **Mais lento** (muito mais registros)
- ⚠️ Útil apenas para **recuperação completa** ou debug

---

## 🕐 TEMPO DE EXECUÇÃO ESPERADO

### Cenário Normal (Checkbox Marcado)

| Volume | Faturamento | Carteira | Total Estimado |
|--------|-------------|----------|----------------|
| **Pequeno** (<1.000 NFs, <5.000 itens) | 10-20s | 15-30s | **25-50s** |
| **Médio** (1.000-5.000 NFs, 5.000-15.000 itens) | 30-60s | 45-90s | **1,5-2,5 min** |
| **Grande** (5.000-20.000 NFs, >15.000 itens) | 60-120s | 90-180s | **2,5-5 min** |

**Fatores que influenciam:**
- 🌐 Velocidade da conexão com Odoo
- 💾 Performance do banco de dados PostgreSQL
- 🖥️ Carga do servidor Render
- 📊 Complexidade dos dados (tags, múltiplos endereços, etc)

---

## 🔄 DIFERENÇA: BOTÃO vs SCHEDULER AUTOMÁTICO

### Botão "SINCRONIZAR TUDO (SEGURO)"

| Aspecto | Configuração |
|---------|--------------|
| **Faturamento** | 30 dias (43.200 min) |
| **Carteira** | 4,4 dias (6.360 min) |
| **Frequência** | Manual (quando usuário clicar) |
| **Objetivo** | Recuperação completa ou atualização manual |

### Scheduler Automático (a cada 30 minutos)

| Aspecto | Configuração |
|---------|--------------|
| **Faturamento** | 4 dias (5.760 min) |
| **Carteira** | 40 minutos |
| **Frequência** | Automático (a cada 30 minutos) |
| **Objetivo** | Manter sistema sempre atualizado |

**Conclusão:**
- ✅ **Botão** = Sincronização **COMPLETA e ABRANGENTE**
- ✅ **Scheduler** = Sincronização **INCREMENTAL e FREQUENTE**

---

## 📝 CASOS DE USO RECOMENDADOS

### Quando usar o BOTÃO:

1. ✅ **Após deploy** ou atualização do sistema
2. ✅ **Recuperação** de dados após problema
3. ✅ **Validação** manual de consistência
4. ✅ **Primeira sincronização** do dia
5. ✅ **Suspeita** de dados desatualizados

### Quando NÃO usar o botão:

1. ❌ **A cada 5 minutos** (deixe scheduler fazer o trabalho)
2. ❌ **Durante uso normal** (scheduler mantém atualizado)
3. ❌ **Múltiplas vezes seguidas** (esperar pelo menos 1 minuto entre cliques)

---

## 🚨 ALERTAS E MENSAGENS

### Mensagens de Sucesso:

```
✅ SINCRONIZAÇÃO INTEGRADA COMPLETA!
🔄 Sequência segura executada: FATURAMENTO → CARTEIRA
⏱️ Operação concluída em 45.3s

📊 Faturamento: 2.345 registros sincronizados
🏭 Estoque: 1.234 movimentações criadas automaticamente
📋 Processamento: 1.100 diretas, 120 com divergência, 14 canceladas

🔄 Carteira: 8.765 inseridos, 123 removidos
🔄 Pré-separações: 45 recompostas automaticamente

🛡️ Sequência segura executada - risco de perda de NFs ELIMINADO
```

### Mensagens de Aviso:

```
⚠️ SINCRONIZAÇÃO PARCIAL concluída
✅ Faturamento: OK
❌ Carteira: Timeout na consulta Odoo

⚠️ 15 alertas detectados (já protegidos)
```

### Mensagens de Erro:

```
❌ FALHA na sincronização integrada: Conexão com Odoo perdida
⏱️ Processo interrompido após 12.5s
🔍 Falha na etapa: INICIANDO_FATURAMENTO
```

---

## 🎯 CONCLUSÃO

Quando você clica no botão **"SINCRONIZAR TUDO (SEGURO)"**:

1. ✅ **Faturamento** busca NFs dos **últimos 30 dias** (limite 20k registros)
2. ✅ **Carteira** busca pedidos **modificados nos últimos 4,4 dias** (sem limite)
3. ✅ Sequência **SEMPRE correta**: FATURAMENTO → CARTEIRA
4. ✅ **Movimentações de estoque** criadas automaticamente
5. ✅ **Pré-separações** recompostas automaticamente
6. ✅ Tempo esperado: **25s a 5min** (depende do volume)

**É seguro clicar?** ✅ **SIM!** O sistema foi projetado para ser à prova de falhas.

---

**Última atualização:** 12/11/2025
**Responsável:** Documentação Técnica do Sistema de Fretes
