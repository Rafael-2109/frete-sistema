# 📋 SISTEMA CARTEIRA DE PEDIDOS - ESPECIFICAÇÃO COMPLETA PARA VALIDAÇÃO

## 🎯 **VISÃO GERAL DO SISTEMA**

### **OBJETIVO PRINCIPAL:**
Sistema central de gestão da carteira de pedidos com vinculação inteligente às separações existentes, controle de faturamento parcial e validação robusta de NFs.

### **VALIDAÇÃO CORRIGIDA:**
```python
# ✅ VALIDAÇÃO FINAL DEFINIDA:
origem_faturamento == pedido_embarque AND cnpj_faturamento == cnpj_embarque
```

---

## 🗂️ **MODELOS DE DADOS - 9 TABELAS ESPECIALIZADAS**

### **1. 📋 CarteiraPrincipal (119 campos)**

**CHAVES PRIMÁRIAS:**
- `num_pedido` + `cod_produto` (chave única de negócio)

**GRUPOS DE CAMPOS:**
```python
# 🆔 IDENTIFICAÇÃO (5 campos)
num_pedido, cod_produto, pedido_cliente, data_pedido, status_pedido

# 👥 CLIENTE (7 campos) 
cnpj_cpf, raz_social, raz_social_red, municipio, estado, vendedor, equipe_vendas

# 📦 PRODUTO (5 campos)
nome_produto, unid_medida_produto, embalagem_produto, materia_prima_produto, categoria_produto

# 💰 COMERCIAL (8 campos)
qtd_produto_pedido, qtd_saldo_produto_pedido, qtd_cancelada_produto_pedido, preco_produto_pedido,
cond_pgto_pedido, forma_pgto_pedido, incoterm, metodo_entrega_pedido

# 🏠 ENDEREÇO ENTREGA (9 campos)
cnpj_endereco_ent, empresa_endereco_ent, cep_endereco_ent, nome_cidade, cod_uf,
bairro_endereco_ent, rua_endereco_ent, endereco_ent, telefone_endereco_ent

# 📅 OPERACIONAL PRESERVADO (5 campos)
expedicao, data_entrega, agendamento, protocolo, roteirizacao

# 🚛 SEPARAÇÃO/LOTE (5 campos)
lote_separacao_id, qtd_saldo, valor_saldo, pallet, peso

# 📊 TOTALIZADORES CALCULADOS (15 campos)
menor_estoque_produto_d7, saldo_estoque_pedido, valor_saldo_total, pallet_total, etc.

# 📈 PROJEÇÃO ESTOQUE D0-D28 (29 campos)
estoque, estoque_d0, estoque_d1, ... estoque_d28

# 🛡️ AUDITORIA (6 campos)
created_at, updated_at, created_by, updated_by, ativo
```

**COMPORTAMENTO ATUALIZAÇÃO:**
- **SEMPRE ATUALIZA:** Dados mestres (cliente, produto, comercial)
- **PRESERVA:** Dados operacionais (expedição, agendamento, protocolo, roteirização, lote)

### **2. 📄 CarteiraCopia (Controle Faturamento)**

**FUNÇÃO:** Espelho da principal + controle específico de baixas
**CAMPO CHAVE:** `baixa_produto_pedido` (quantidade faturada)
**CÁLCULO:** `qtd_saldo_produto_calculado = qtd_produto_pedido - qtd_cancelada - baixa_produto_pedido`

### **3. 📸 SnapshotCarteira (CORRIGIDO)**

**MOMENTO:** Snapshot criado na **IMPORTAÇÃO da carteira** (não na separação)
```python
# CAMPOS PRESERVADOS:
num_pedido, cod_produto, cnpj_cliente, nome_cliente
qtd_produto_pedido, preco_produto, valor_produto_pedido
data_importacao, versao_carteira
```

### **4. 🎯 ValidacaoNFSimples (CORRIGIDA)**

**VALIDAÇÃO FINAL:**
```python
def validar_nf_simples(self):
    # 1️⃣ BUSCAR ORIGEM NO SNAPSHOT
    snapshot = SnapshotCarteira.query.filter_by(num_pedido=self.origem_faturamento).first()
    
    # 2️⃣ VALIDAÇÕES
    if not snapshot:
        return "❌ ORIGEM não encontrada na carteira"
    
    if self.cnpj_faturamento != snapshot.cnpj_cliente:
        return "❌ CNPJ não confere"
    
    return "✅ EXECUTAR: Gerar frete + monitoramento"
```

**CAMPOS:**
```python
numero_nf, origem_faturamento, cnpj_faturamento
origem_encontrada, cnpj_confere, validacao_aprovada
cnpj_esperado, cnpj_recebido, motivo_bloqueio
frete_gerado, monitoramento_registrado, data_execucao
```

### **5. 🎯 TipoEnvio (PARCIAL/TOTAL)**

**TIPOS:**
- **TOTAL:** Carga pode receber alterações até limite
- **PARCIAL:** Carga fixa - alterações geram nova carga

**CAMPOS:**
```python
separacao_lote_id, tipo_envio, capacidade_peso_kg, capacidade_volume_m3
peso_atual_kg, volume_atual_m3, criado_em, criado_por
```

### **6. 📋 FaturamentoParcialJustificativa**

**FUNÇÃO:** Controle de faturamentos parciais com classificação do saldo

**FLUXO:**
```
Separou 100 → Faturou 60 → Saldo 40
↓
MOTIVO: RUPTURA_ESTOQUE, AVARIA_PRODUTO, ERRO_SEPARACAO, etc.
↓  
CLASSIFICAÇÃO: SALDO, NECESSITA_COMPLEMENTO, RETORNA_CARTEIRA, EXCLUIR_DEFINITIVO
↓
AÇÃO: AGUARDA_DECISAO, RETORNOU_CARTEIRA, NOVA_SEPARACAO, DESCARTADO
```

### **7. ⚖️ ControleAlteracaoCarga**

**FUNÇÃO:** Algoritmo inteligente para alterações na carga

**LÓGICA:**
```python
if tipo_envio == 'TOTAL' and peso_dentro_limite:
    decisao = 'ADICIONAR_CARGA_ATUAL'
elif tipo_envio == 'PARCIAL':
    decisao = 'CRIAR_NOVA_CARGA'
else:
    decisao = 'AGUARDA_APROVACAO'
```

### **8. ⏸️ SaldoStandby**

**FUNÇÃO:** Controle de saldos aguardando decisão comercial

**TIPOS:**
- **AGUARDA_COMPLEMENTO:** Novo pedido mesmo CNPJ
- **AGUARDA_DECISAO:** Decisão comercial
- **AGUARDA_REPOSICAO:** Reposição estoque

### **9. 🚨 ControleDescasamentoNF**

**FUNÇÃO:** Detecta descasamento entre Embarques vs Importação vs Separação

**DETECÇÃO:**
```python
if qtd_embarques != qtd_importacao:
    descasamento_detectado = True
    diferenca_critica = abs(qtd_embarques - qtd_importacao)
```

---

## 🔄 **FLUXOS OPERACIONAIS COMPLETOS**

### **🔄 FLUXO 1: IMPORTAÇÃO CARTEIRA**

```
1️⃣ UPLOAD ARQUIVO
   ↓
2️⃣ CRIAR SNAPSHOT (versao_carteira = "2025-06-30-14h30")
   ↓  
3️⃣ PROCESSAR CADA LINHA:
   - Item existe? → ATUALIZAR (preservar operacional)
   - Item novo? → CRIAR
   ↓
4️⃣ SINCRONIZAR CarteiraCopia
   ↓
5️⃣ DETECTAR ALTERAÇÕES (ControleAlteracaoCarga)
   ↓
6️⃣ GERAR EVENTOS (EventoCarteira)
```

### **🔄 FLUXO 2: VINCULAÇÃO INTELIGENTE**

```
1️⃣ BUSCAR SEPARAÇÕES EXISTENTES
   Critério: protocolo + agendamento + expedição
   ↓
2️⃣ VINCULAÇÃO PARCIAL
   Carteira: 100 unidades + Separação: 60 unidades = Vincula 60
   ↓
3️⃣ CRIAR VinculacaoCarteiraSeparacao
   ↓
4️⃣ DEFINIR TipoEnvio (TOTAL/PARCIAL)
```

### **🔄 FLUXO 3: FATURAMENTO (VALIDAÇÃO CORRIGIDA)**

```
1️⃣ NF IMPORTADA
   ↓
2️⃣ VALIDAÇÃO SIMPLES:
   origem_faturamento == pedido_embarque?
   cnpj_faturamento == cnpj_embarque?
   ↓
3️⃣ APROVADA? 
   ✅ SIM: Gerar frete + monitoramento
   ❌ NÃO: Bloquear com motivo
   ↓
4️⃣ FATURAMENTO PARCIAL?
   → Criar FaturamentoParcialJustificativa
   ↓
5️⃣ ATUALIZAR CarteiraCopia.baixa_produto_pedido
```

### **🔄 FLUXO 4: ALTERAÇÃO PÓS-SEPARAÇÃO**

```
1️⃣ CARTEIRA REIMPORTADA (item alterado)
   ↓
2️⃣ DETECTAR DIFERENÇA (ControleAlteracaoCarga)
   ↓
3️⃣ VERIFICAR TipoEnvio:
   TOTAL → Adicionar à carga (se couber)
   PARCIAL → Criar nova carga
   ↓
4️⃣ EXECUTAR DECISÃO
```

---

## 📊 **CENÁRIOS PRÁTICOS**

### **✅ CENÁRIO 1: FATURAMENTO NORMAL**
```
NF: 123456
Origem: PED001 
CNPJ: 12.345.678/0001-90

SNAPSHOT tem: PED001 com CNPJ 12.345.678/0001-90
RESULTADO: ✅ Gera frete + monitoramento
```

### **❌ CENÁRIO 2: ORIGEM INCORRETA**
```
NF: 123457
Origem: PED999
CNPJ: 12.345.678/0001-90

SNAPSHOT: PED999 não encontrado
RESULTADO: ❌ Bloqueia - "Origem PED999 não encontrada na carteira"
```

### **❌ CENÁRIO 3: CNPJ INCORRETO**
```
NF: 123458
Origem: PED001
CNPJ: 99.999.999/0001-99

SNAPSHOT: PED001 existe mas CNPJ diferente
RESULTADO: ❌ Bloqueia - "CNPJ não confere. Esperado: 12.345.678/0001-90"
```

### **🔄 CENÁRIO 4: FATURAMENTO PARCIAL**
```
Separação: 100 unidades
NF: 60 unidades (validação OK)

RESULTADO: 
✅ Gera frete + monitoramento para 60
🟡 Cria FaturamentoParcialJustificativa para saldo 40
📋 Aguarda motivo: RUPTURA_ESTOQUE? AVARIA_PRODUTO?
```

### **⚙️ CENÁRIO 5: ALTERAÇÃO INTELIGENTE**
```
ANTES: Pedido 100 → Separou 60 (TOTAL, limite 80kg)
DEPOIS: Carteira reimportada 120 unidades (+20)

ALGORITMO:
- Peso +20 unidades = +15kg
- Carga atual: 50kg + 15kg = 65kg < 80kg ✅
DECISÃO: ADICIONAR_CARGA_ATUAL
```

### **🚫 CENÁRIO 6: CARGA PARCIAL**
```
ANTES: Pedido 100 → Separou 60 (PARCIAL)
DEPOIS: Carteira reimportada 120 unidades (+20)

TIPO_ENVIO = PARCIAL (não aceita alteração)
DECISÃO: CRIAR_NOVA_CARGA para +20 unidades
```

---

## 🛡️ **VALIDAÇÕES E REGRAS DE NEGÓCIO**

### **📋 IMPORTAÇÃO CARTEIRA:**
1. Campos obrigatórios: `num_pedido`, `cod_produto`, `nome_produto`, `qtd_produto_pedido`, `cnpj_cpf`
2. Chave única: `num_pedido` + `cod_produto`
3. Preservar dados operacionais existentes
4. Criar snapshot automaticamente

### **🔗 VINCULAÇÃO:**
1. Chave vinculação: `num_pedido` + `cod_produto` + `protocolo` + `agendamento` + `expedição`
2. Vinculação parcial: `min(qtd_carteira, qtd_separacao)`
3. One-way: Carteira → Separação (nunca o contrário)

### **✅ VALIDAÇÃO NF:**
1. **origem** (faturamento) deve existir como **pedido** no snapshot
2. **CNPJ** deve conferir exatamente
3. Ambos OK = Executa / Um falha = Bloqueia
4. Sempre transparente no motivo

### **⚖️ ALTERAÇÃO CARGA:**
1. `TipoEnvio = TOTAL`: Verifica capacidade antes de adicionar
2. `TipoEnvio = PARCIAL`: Sempre cria nova carga
3. Registra todas as decisões para auditoria

---

## 🎯 **INTERFACES NECESSÁRIAS**

### **📊 Dashboard Principal:**
- Cards: Total pedidos, produtos, valor carteira
- Breakdown por status
- Alertas: Inconsistências, aprovações pendentes
- Top vendedores

### **📋 Listagem Carteira:**
- Filtros: Pedido, produto, vendedor, status, cliente
- Modal detalhes com AJAX
- Status visual com badges
- Paginação 50 itens

### **📤 Importação:**
- Validação frontend (formato, tamanho)
- Preview arquivo
- Progress bar processamento
- Log de alterações

### **⚠️ Gestão Inconsistências:**
- Lista problemas detectados
- Resolução manual com motivos
- Histórico resoluções

### **🔧 Aprovações:**
- Mudanças pendentes em pedidos cotados
- Workflow: Visualizar → Aprovar/Rejeitar
- Notificações automáticas

---

## 📱 **APIs E INTEGRAÇÕES**

### **🔄 APIs Internas:**
```python
/carteira/api/item/<id>              # Detalhes item
/carteira/api/processar-faturamento  # Baixa automática NFs
/carteira/api/validar-nf             # Validação simples
/carteira/api/inconsistencias        # Lista problemas
/carteira/api/aprovacoes             # Workflow aprovação
```

### **🔗 Integrações Futuras:**
- **Separação:** Geração "recortes" carteira
- **Embarques:** Sincronização status
- **Faturamento:** Baixa automática
- **Estoque:** Projeção integrada

---

## 🚀 **ROTAS FLASK**

```python
# PRINCIPAIS
/carteira/                           # Dashboard
/carteira/principal                  # Listagem
/carteira/importar                   # Upload

# GESTÃO
/carteira/inconsistencias           # Problemas
/carteira/aprovacoes               # Workflow
/carteira/justificativas           # Faturamento parcial
/carteira/standby                  # Saldos parados

# UTILITÁRIOS
/carteira/baixar-modelo            # Excel modelo
/carteira/gerar-separacao          # Interface recorte
```

---

## ⚡ **PERFORMANCE E ESCALABILIDADE**

### **📊 Índices Críticos:**
```sql
-- Buscas frequentes
idx_carteira_num_pedido_cod_produto (num_pedido, cod_produto)
idx_carteira_vendedor_status (vendedor, status_pedido)
idx_carteira_cnpj_ativo (cnpj_cpf, ativo)

-- Vinculação
idx_vinculacao_protocolo_agenda (protocolo_agendamento, data_agendamento)
idx_vinculacao_separacao (separacao_lote_id)

-- Validação
idx_snapshot_versao_pedido (versao_carteira, num_pedido)
idx_validacao_nf_origem (origem_faturamento)
```

### **🔧 Otimizações:**
- Paginação 50 itens
- Cache Redis para consultas frequentes
- JSON para campos dinâmicos
- Soft delete com flag `ativo`

---

## 🔒 **SEGURANÇA E AUDITORIA**

### **🛡️ Controles:**
- Todas alterações logadas (`LogAtualizacaoCarteira`)
- Histórico faturamento preservado
- Snapshot imutável por versão
- Validação CSRF em forms

### **👥 Permissões:**
- Vendedores: Apenas seus pedidos
- Financeiro: Gestão faturamento/inconsistências
- Admin: Acesso completo + aprovações

---

## 📝 **DOCUMENTAÇÃO IMPLEMENTAÇÃO**

### **🎯 Ordem Sugerida:**
1. **Migração tabelas** (flask db migrate + upgrade)
2. **Testes básicos** (CRUD carteira principal)
3. **Importação inteligente** (preservação dados)
4. **Validação NF** (origem + CNPJ)
5. **Vinculação separações** (multi-dimensional)
6. **Controles avançados** (faturamento parcial, alterações)
7. **Interfaces gestão** (inconsistências, aprovações)

---

## ✅ **VALIDAÇÃO FINAL**

**ESTÁ TUDO ALINHADO COM SUAS EXPECTATIVAS?**

1. **✅ Validação corrigida:** origem (faturamento) = pedido (embarque) + CNPJ
2. **✅ Snapshot no momento certo:** Importação da carteira
3. **✅ Vinculação inteligente:** Multi-dimensional com preservação dados
4. **✅ Faturamento parcial:** Controle completo com justificativas
5. **✅ Alterações inteligentes:** TOTAL vs PARCIAL
6. **✅ Sistema robusto:** Nunca quebra, sempre transparente

**APROVADO PARA IMPLEMENTAÇÃO?** 🚀 