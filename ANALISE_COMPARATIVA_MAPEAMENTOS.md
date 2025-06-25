# 🚨 ANÁLISE COMPARATIVA: PROBLEMAS CRÍTICOS NOS MAPEAMENTOS SEMÂNTICOS

## 📊 **SITUAÇÃO ATUAL ENCONTRADA:**

### **1. Múltiplos Mapeamentos Conflitantes:**
- `mapeamento_semantico.py` (672 linhas) 
- `mapeamento_semantico_limpo.py` (293 linhas)
- Nenhum usa adequadamente o `README_MAPEAMENTO_SEMANTICO_COMPLETO.md`

### **2. ERRO CRÍTICO - Campo "origem":**

#### ❌ **INTERPRETAÇÃO INCORRETA (nos arquivos atuais):**
```python
'origem': {
    'modelo': 'RelatorioFaturamentoImportado',
    'termos_naturais': [
        'origem', 'procedência', 'de onde veio', 'origem da carga',
        'local de origem', 'cidade origem'  # ❌ COMPLETAMENTE ERRADO!
    ]
}
```

#### ✅ **DEFINIÇÃO CORRETA (do README do usuário):**
```
**origem** (VARCHAR(50)) - Nulo: ✅
msm campo do Pedido "num_pedido"
```

### **3. IMPACTO DO ERRO:**
- **Campo de relacionamento ESSENCIAL** interpretado como localização
- **Quebra consultas** tipo "qual NF do pedido X"
- **Relacionamento crítico perdido:** `RelatorioFaturamentoImportado.origem = Pedido.num_pedido`

## 🔍 **ANÁLISE DETALHADA DOS MAPEAMENTOS ESPECIFICADOS:**

### **Campos com Linguagem Natural Detalhada (do README):**

#### **PEDIDOS:**
- `num_pedido`: ["pedido", "pdd", "numero do pedido"]
- `raz_social_red`: ["cliente", "razão social do cliente", "nome do cliente"]
- `cnpj_cpf`: ["cnpj do pedido", "cnpj do cliente"]
- `valor_saldo_total`: ["valor do pedido", "total do pedido", "valor do pdd", "total do pdd"]
- `peso_total`: ["peso do pedido", "peso do pdd", "quilos", "kg", "peso bruto", "peso liquido", "quantos quilos"]
- `agendamento`: ["data de agendamento", "agenda", "data da agenda", "agendamento", "data agendada"]
- `protocolo`: ["protocolo", "protocolo do agendamento"]
- `status`: ["aberto", "cotado", "faturado", "status do pedido", "situação do pedido", "posição do pedido", "embarcado"]

#### **ENTREGAS MONITORADAS:**
- `data_entrega_prevista`: ["previsao de entrega", "data prevista de entrega", "data que vai ser entregue", "quando entrega"]
- `data_hora_entrega_realizada`: ["dia que entregou", "data que foi entregue", "data da entrega", "entregou no dia"]
- `entregue`: ["foi entregue"]
- `status_finalizacao`: ["finalização da entrega", "como finalizou", "entregue", "trocou a nf", "foi devolvida", "nf foi cancelada"]
- `pendencia_financeira`: ["pendencia financeira", "financeiro cobrando", "posição pro financeiro"]
- `nf_cd`: ["NF está no CD", "nota voltou pro cd", "nf no cd"]

#### **CAMPOS TÉCNICOS IMPORTANTES:**
- `pallets`: ["qtd de pallets do pedido", "pallets do pedido", "palets do pedido", "palets do pdd", "total de pallets do pedido", "pallet do pedido", "pallet pdd", "qtd de palets", "qtd de pallets", "qtd de pallet"]
- `modalidade`: ["modalidade", "tipo de veiculo"]
- `tabela_valor_kg`: ["frete peso", "frete kg", "valor por kg", "valor do kg", "frete excedente", "kg excedente"]
- `tabela_percentual_gris`: ["gris", "gerenciamento de risco"]
- `tabela_pedagio_por_100kg`: ["pedagio", "valor do pedagio", "pedagio por 100 kg"]

## ⚠️ **OUTROS PROBLEMAS POTENCIAIS IDENTIFICADOS:**

### **1. Contextos Específicos Não Considerados:**
- **Exemplo:** Campo `origem` em faturamento vs origem geográfica
- **Solução:** Usar contexto específico do modelo

### **2. Relacionamentos Críticos Perdidos:**
- `RelatorioFaturamentoImportado.origem = Pedido.num_pedido`
- `Pedido.nf = EntregaMonitorada.numero_nf`
- `EmbarqueItem.separacao_lote_id` vincula múltiplos modelos

### **3. Status e Regras de Negócio:**
- Status pedido: "aberto", "cotado", "embarcado", "faturado"
- Status entrega: "Entregue", "Cancelada", "Devolvida", "Troca de NF"
- Tipo carga: "FOB", "DIRETA", "FRACIONADA"

## 🔧 **PLANO DE CORREÇÃO:**

### **Etapa 1: Mapeamento Unificado Correto**
- Criar `mapeamento_semantico_correto.py`
- Baseado 100% no `README_MAPEAMENTO_SEMANTICO_COMPLETO.md`
- Integrar com `grupo_empresarial.py` existente

### **Etapa 2: Correções Específicas**
- ✅ Corrigir campo "origem" = número do pedido
- ✅ Mapear todos os campos com linguagem natural especificada
- ✅ Incluir contextos específicos de cada modelo
- ✅ Implementar relacionamentos corretos

### **Etapa 3: Integração**
- Atualizar `claude_real_integration.py` para usar mapeamento correto
- Deprecar mapeamentos antigos
- Testar consultas críticas

## 📋 **CAMPOS CRÍTICOS PARA CORREÇÃO IMEDIATA:**

1. **`origem`** - Campo de relacionamento, não localização
2. **`num_pedido`** - Chave para rastreamento pedido→faturamento
3. **`status`** - Valores específicos por modelo
4. **`agendamento`** - Data crítica para entregas
5. **`pendencia_financeira`** - Flag específico do financeiro
6. **`nf_cd`** - Gatilho para reprocessamento

## 🎯 **RESULTADO ESPERADO:**

Após correção:
- ✅ Campo "origem" corretamente interpretado como número do pedido
- ✅ Consultas tipo "qual pedido da NF X" funcionando
- ✅ Relacionamentos entre modelos funcionais
- ✅ Linguagem natural precisa baseada no uso real
- ✅ Integração com grupos empresariais
- ✅ Sistema de sugestões contextuais correto

---
**Conclusão:** O trabalho detalhado do usuário no README foi fundamental para identificar erros críticos que comprometeriam todo o sistema de IA. A correção é urgente e necessária. 