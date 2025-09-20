# 🎯 ETAPA 3 - IMPLEMENTAÇÃO REALIZADA

**Data:** 20/01/2025
**Objetivo:** Enriquecer os pedidos com Separações, Faturamentos e dados de Monitoramento

## ✅ ARQUIVOS CRIADOS/MODIFICADOS

### 1. **DocumentoService.py** (NOVO)
**Caminho:** `app/comercial/services/documento_service.py`

**Funcionalidades implementadas:**
- `obter_documentos_pedido()` - Método principal que retorna todos os documentos de um pedido
- `_cliente_precisa_agendamento()` - Verifica se cliente precisa de agendamento baseado em ContatoAgendamento
- `_obter_notas_fiscais_pedido()` - Busca todas as NFs agrupadas por numero_nf
- `_obter_separacoes_pedido()` - Busca separações não sincronizadas agrupadas por separacao_lote_id
- `_calcular_valor_total_pedido()` - Calcula valor total do pedido (CarteiraPrincipal ou FaturamentoProduto)
- `_calcular_valor_total_faturado()` - Soma valores das NFs
- `_calcular_valor_total_separacoes()` - Soma valores das separações
- `_calcular_saldo()` - Fórmula: (Total Pedido - Faturado) - Separações

### 2. **Rota API** (NOVA)
**Arquivo:** `app/comercial/routes/diretoria.py`
**Endpoint:** `/comercial/api/pedido/<num_pedido>/documentos`

**Parâmetros:**
- `num_pedido` (path) - Número do pedido
- `cnpj` (query) - CNPJ do cliente (obrigatório)

**Resposta JSON:**
```json
{
  "cliente_precisa_agendamento": boolean,
  "documentos": [
    {
      "tipo": "NF|Separação|Saldo",
      "tipo_ordem": 1|2|3,
      "numero_nf": string,
      "data_faturamento": string,
      "data_embarque": string,
      "transportadora": string,
      "data_agendamento": string,
      "protocolo_agendamento": string,
      "status_agendamento": string,
      "data_entrega_prevista": string,
      "data_entrega_realizada": string,
      "valor": float
    }
  ],
  "totais": {
    "valor_total_pedido": float,
    "valor_total_faturado": float,
    "valor_total_separacoes": float,
    "saldo": float
  }
}
```

### 3. **Template HTML** (MODIFICADO)
**Arquivo:** `app/templates/comercial/lista_clientes.html`

**Alterações:**
1. **Estrutura de Accordion** - Cada linha de pedido agora tem:
   - Botão de expandir/colapsar (chevron)
   - Linha oculta para conteúdo dos documentos
   - Integração com Bootstrap Collapse

2. **Nova coluna na tabela** - Adicionada coluna para botão de expandir

3. **Funções JavaScript adicionadas:**
   - `toggleDocumentos()` - Controla expansão/colapso e carrega documentos
   - `carregarDocumentosPedido()` - Faz requisição AJAX para API
   - `renderizarDocumentos()` - Renderiza tabela de documentos com lógica condicional
   - `formatarStatusAgendamento()` - Formata badges de status

## 🔧 LÓGICA IMPLEMENTADA

### 1. **Identificação de Cliente com Agendamento**
- Busca em `ContatoAgendamento` pelo CNPJ
- Se `forma != 'SEM AGENDAMENTO'` → Mostra colunas de agendamento
- Se `forma == 'SEM AGENDAMENTO'` ou não encontrado → Mostra apenas "Entrega Prevista"

### 2. **Agrupamento de Documentos**

#### **Notas Fiscais:**
- Agrupadas por `numero_nf`
- Busca dados em `EntregaMonitorada` e `AgendamentoEntrega`
- Fallback para `EmbarqueItem` → `Embarque` para data de embarque

#### **Separações:**
- Agrupadas por `separacao_lote_id`
- Filtradas por `sincronizado_nf=False`
- Data de expedição mostrada com prefixo "Previsão:"
- Transportadora buscada via `EmbarqueItem` → `Embarque`

#### **Saldo:**
- Calculado como: `(Total Pedido - Faturado) - Separações não sincronizadas`
- Aparece como linha separada se > 0

### 3. **Ordenação dos Documentos**
- Primeiro por tipo: NFs (1), Separações (2), Saldo (3)
- Depois por data (mais antiga primeiro)

### 4. **Interface Adaptativa**
- Header da tabela muda baseado em `cliente_precisa_agendamento`
- Com agendamento: 10 colunas (incluindo subseção Agendamento)
- Sem agendamento: 8 colunas (incluindo Entrega Prevista)

## 📊 COLUNAS DA TABELA DE DOCUMENTOS

### **Cliente COM agendamento:**
1. Tipo (badge)
2. **Faturamento:** NF | Data
3. **Embarque:** Data | Transportadora
4. **Agendamento:** Data | Protocolo | Status
5. Entrega
6. Valor

### **Cliente SEM agendamento:**
1. Tipo (badge)
2. **Faturamento:** NF | Data
3. **Embarque:** Data | Transportadora
4. Entrega Prevista
5. Entrega
6. Valor

## 🎨 VISUAL

### **Badges por Tipo:**
- **NF:** Verde com ícone fa-file-invoice
- **Separação:** Amarelo com ícone fa-box-open
- **Saldo:** Azul com ícone fa-calculator

### **Status de Agendamento:**
- **confirmado:** Verde com check
- **aguardando:** Amarelo com clock

### **Totais:**
- Exibidos em card no rodapé com cores distintas
- Total Pedido | Total Faturado | Total Separações | Saldo

## ⚡ PERFORMANCE

- **Cache de documentos:** Documentos carregados são armazenados em `documentosCarregados[numPedido]`
- **Carregamento sob demanda:** Documentos só são carregados quando pedido é expandido
- **Queries otimizadas:** Uso de `group_by` e agregações no banco

## 🔄 PRÓXIMAS ETAPAS

Esta implementação foi projetada para ser **extensível** para a próxima etapa:

### **Etapa 4 - Enriquecimento com Produtos:**
- Cada documento (NF/Separação) poderá ser expandido para mostrar produtos
- Estrutura de accordion aninhado já preparada
- `separacao_lote_id` já retornado para buscar produtos específicos

## 📝 NOTAS DE IMPLEMENTAÇÃO

1. **Fallbacks implementados:**
   - Data embarque: EntregaMonitorada → Embarque
   - Data agendamento: data_agenda → data_entrega_prevista
   - Transportadora Separação: EmbarqueItem → Embarque → "-"

2. **Campos vazios:**
   - Todos os campos não aplicáveis mostram "-"
   - Valores zero não são exibidos como "-"

3. **Conversões de tipo:**
   - Decimals convertidos para float na API
   - Datas formatadas para DD/MM/AAAA

## ✅ TESTES

### **Arquivo de teste criado:** `test_etapa3_comercial.py`
- Testa todos os métodos do DocumentoService
- Verifica integridade dos dados retornados
- Valida cálculos de valores e saldo

### **Verificações de sintaxe:**
- ✅ DocumentoService.py - OK
- ✅ routes/diretoria.py - OK
- ✅ Template HTML - Estrutura válida

## 🚀 COMO USAR

1. **Acessar módulo comercial:** `/comercial/`
2. **Selecionar equipe e vendedor**
3. **Ver lista de clientes agrupados**
4. **Clicar em "Ver Pedidos" de um cliente**
5. **No modal de pedidos, clicar no ícone ▶ para expandir documentos**
6. **Visualizar NFs, Separações e Saldo do pedido**

---

**Implementação concluída com sucesso!** ✅

A estrutura está preparada para a próxima etapa de enriquecimento com produtos.