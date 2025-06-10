# 🕐 **Guia de Timezone Brasileiro**

Sistema completo de gerenciamento de timezone brasileiro implementado no sistema de fretes.

## 📋 **Problema Resolvido**

- ✅ **Antes**: Sistema usava UTC sem conversão → horários incorretos
- ✅ **Agora**: Conversão automática para timezone brasileiro (America/Sao_Paulo)
- ✅ **Suporte**: Horário de verão automático
- ✅ **Formatos**: Datas e horários no padrão brasileiro

## 🔧 **Filtros Jinja2 Disponíveis**

### **1. `formatar_data_segura`**
```html
{{ pedido.criado_em | formatar_data_segura }}
<!-- Resultado: 10/06/2025 -->

{{ pedido.criado_em | formatar_data_segura('%d/%m/%Y') }}
<!-- Resultado: 10/06/2025 -->
```

### **2. `formatar_data_hora_brasil`**
```html
{{ pedido.criado_em | formatar_data_hora_brasil }}
<!-- Resultado: 10/06/2025 17:30 -->

{{ pedido.criado_em | formatar_data_hora_brasil('%d/%m/%Y às %H:%M:%S') }}
<!-- Resultado: 10/06/2025 às 17:30:45 -->
```

### **3. `formatar_hora_brasil`**
```html
{{ pedido.criado_em | formatar_hora_brasil }}
<!-- Resultado: 17:30 -->

{{ pedido.criado_em | formatar_hora_brasil('%H:%M:%S') }}
<!-- Resultado: 17:30:45 -->
```

### **4. `diferenca_timezone`**
```html
<span>Timezone: {{ diferenca_timezone() }}</span>
<!-- Resultado: UTC-3 ou UTC-2 (depende do horário de verão) -->
```

## 🔧 **Funções Python Disponíveis**

### **No Backend (Python)**
```python
from app.utils.timezone import (
    agora_brasil,
    utc_para_brasil,
    brasil_para_utc,
    formatar_data_hora_brasil,
    agora_utc
)

# Obter datetime atual do Brasil
agora = agora_brasil()

# Converter UTC para Brasil
dt_utc = datetime.utcnow()
dt_brasil = utc_para_brasil(dt_utc)

# Salvar no banco (sempre em UTC)
pedido.criado_em = agora_utc()
```

## 🌐 **Funções Globais em Templates**

### **1. `agora_brasil()`**
```html
<p>Agora: {{ agora_brasil() | formatar_data_hora_brasil }}</p>
```

### **2. `timezone_info()`**
```html
{% set tz = timezone_info() %}
<p>Timezone: {{ tz.nome }}</p>
<p>Sigla: {{ tz.sigla }}</p>
<p>Diferença UTC: {{ tz.diferenca_utc }}</p>
<p>Horário de verão: {{ tz.horario_verao }}</p>
```

## 📄 **Componente Pronto para Uso**

### **Incluir informações de timezone**
```html
{% include '_timezone_info.html' %}
```

Exibe: `🕐 10/06/2025 17:30 BRT`

## 🛠️ **Exemplos Práticos de Uso**

### **1. Listar pedidos com horário brasileiro**
```html
{% for pedido in pedidos %}
<tr>
    <td>{{ pedido.numero }}</td>
    <td>{{ pedido.criado_em | formatar_data_hora_brasil }}</td>
    <td>{{ pedido.criado_em | formatar_data_segura }}</td>
</tr>
{% endfor %}
```

### **2. Exibir logs com timezone**
```html
<div class="log-entry">
    <small class="text-muted">
        {{ log.timestamp | formatar_data_hora_brasil('%d/%m %H:%M') }}
    </small>
    <span>{{ log.message }}</span>
</div>
```

### **3. Formulário com data atual**
```html
<input type="datetime-local" 
       value="{{ agora_brasil().strftime('%Y-%m-%dT%H:%M') }}"
       name="data_agendamento">
```

## ⚙️ **Configuração Técnica**

### **Biblioteca Necessária**
```
pytz==2025.2  # ✅ Já adicionada ao requirements.txt
```

### **Timezone Configurado**
- **Timezone**: `America/Sao_Paulo`
- **Siglas**: `BRT` (horário normal) / `BRST` (horário de verão)
- **Diferença UTC**: `-3h` ou `-2h` (automático)

## 🔄 **Migração de Templates Existentes**

### **Antes**
```html
{{ pedido.criado_em.strftime('%d/%m/%Y') }}  ❌ Timezone errado
```

### **Depois**
```html
{{ pedido.criado_em | formatar_data_segura }}  ✅ Timezone brasileiro
```

## 🎯 **Boas Práticas**

1. **Use sempre os filtros** em templates em vez de `.strftime()`
2. **Salve sempre em UTC** no banco de dados
3. **Converta para brasileiro** apenas na exibição
4. **Use `agora_utc()`** para timestamps de banco
5. **Use `agora_brasil()`** para exibição ao usuário

## 🔍 **Verificação de Funcionamento**

### **1. Teste simples**
```html
<p>UTC: {{ agora_utc() }}</p>
<p>Brasil: {{ agora_brasil() | formatar_data_hora_brasil }}</p>
<p>Diferença: {{ diferenca_timezone() }}</p>
```

### **2. Comparação de horários**
```html
{% set agora_utc = agora_utc() %}
{% set agora_br = agora_brasil() %}
<p>UTC: {{ agora_utc.strftime('%H:%M:%S') }}</p>
<p>Brasil: {{ agora_br.strftime('%H:%M:%S') }}</p>
```

## 🎉 **Resultado Final**

✅ **Todos os horários** agora exibem timezone brasileiro  
✅ **Conversão automática** de UTC para Brasil  
✅ **Horário de verão** tratado automaticamente  
✅ **Formatos consistentes** em todo o sistema  
✅ **Performance otimizada** com filtros cached  

**O sistema agora mostra horários corretos para o Brasil! 🇧🇷** 