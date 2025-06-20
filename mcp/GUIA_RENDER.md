# 🌐 **GUIA: INTEGRAÇÃO MCP NO RENDER**

## 📋 **Visão Geral**

Este guia mostra como integrar o Model Context Protocol (MCP) diretamente no Render.com, permitindo que os usuários acessem as funcionalidades do sistema de fretes via:

1. **API REST** (Mais simples)
2. **Servidor MCP Dedicado** (Mais avançado)

---

## 🛠️ **Opção 1: API REST (RECOMENDADA)**

### **Como Funciona**
- Endpoints REST no próprio Flask
- Acesso via HTTP/HTTPS de qualquer lugar
- Compatível com qualquer cliente (Postman, curl, JavaScript, etc.)

### **Endpoints Disponíveis**

```bash
# 🏥 Saúde da API
GET https://frete-sistema.onrender.com/api/v1/health

# 📚 Documentação
GET https://frete-sistema.onrender.com/api/v1/docs

# 🚚 Consultas do sistema
GET /api/v1/embarques?status=ativo&limite=10
GET /api/v1/fretes?status_aprovacao=pendente&limite=10
GET /api/v1/monitoramento?nf_numero=123456
GET /api/v1/cliente/Assai?uf=SP&limite=5
GET /api/v1/estatisticas?periodo_dias=30
GET /api/v1/portaria?status=DENTRO

# 📊 Download Excel
GET /api/v1/cliente/Carrefour/excel?uf=RJ&limite=10
```

### **Exemplos de Uso**

#### **1. Consulta por Cliente (JavaScript)**
```javascript
// Consultar entregas do Assai
fetch('https://frete-sistema.onrender.com/api/v1/cliente/Assai?uf=SP&limite=5')
  .then(response => response.json())
  .then(data => {
    console.log('Resumo:', data.resumo);
    console.log('Pedidos:', data.data);
  });
```

#### **2. Download Excel (Python)**
```python
import requests

# Baixar relatório Excel do Carrefour
response = requests.get(
    'https://frete-sistema.onrender.com/api/v1/cliente/Carrefour/excel',
    params={'uf': 'RJ', 'limite': 10}
)

if response.status_code == 200:
    with open('relatorio_carrefour.xlsx', 'wb') as f:
        f.write(response.content)
    print("📊 Excel baixado com sucesso!")
```

#### **3. Estatísticas do Sistema (curl)**
```bash
# Obter estatísticas dos últimos 30 dias
curl "https://frete-sistema.onrender.com/api/v1/estatisticas?periodo_dias=30" | jq .
```

### **Autenticação**
- Todos os endpoints (exceto `/health` e `/docs`) exigem login no sistema
- Use sessões do Flask ou implemente token JWT se necessário

---

## 🏗️ **Opção 2: Servidor MCP Dedicado**

### **Arquitetura**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude PC     │───▶│  Render MCP     │───▶│  Render Flask   │
│   (Local)       │    │  (Worker)       │    │  (Web Service)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Configuração no Render**

#### **1. Arquivo render_mcp.yaml**
```yaml
services:
  # Serviço Flask existente
  - type: web
    name: frete-sistema
    env: python
    buildCommand: pip install -r requirements.txt && flask db upgrade
    startCommand: python run.py
    
  # Novo serviço MCP
  - type: worker
    name: frete-sistema-mcp
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: cd mcp && python servidor_render.py
    envVars:
      - key: FLASK_URL
        value: https://frete-sistema.onrender.com
      - key: MCP_USER
        value: sistema_mcp
```

#### **2. Configuração do Claude Desktop**
```json
{
  "mcpServers": {
    "frete-sistema-render": {
      "command": "python",
      "args": ["/caminho/para/cliente_mcp_render.py"],
      "env": {
        "MCP_SERVER_URL": "https://frete-sistema-mcp.onrender.com",
        "API_KEY": "sua_chave_api"
      }
    }
  }
}
```

---

## 🚀 **Deploy e Configuração**

### **Passo 1: Atualizar requirements.txt**
```bash
# Adicionar dependências MCP
echo "mcp==1.0.0" >> requirements.txt
echo "requests>=2.31.0" >> requirements.txt
```

### **Passo 2: Commit e Push**
```bash
git add .
git commit -m "🌐 Adicionar integração MCP com Render"
git push origin main
```

### **Passo 3: Configurar no Render**
1. Acesse o dashboard do Render
2. Vá em seu serviço "frete-sistema"
3. Na aba "Environment", adicione:
   - `FLASK_URL=https://frete-sistema.onrender.com`
   - `MCP_USER=sistema_mcp`

### **Passo 4: Testar a API**
```bash
# Testar saúde da API
curl https://frete-sistema.onrender.com/api/v1/health

# Verificar documentação
curl https://frete-sistema.onrender.com/api/v1/docs
```

---

## 🔧 **Configuração para Usuários**

### **Acesso via Navegador**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Sistema de Fretes - API</title>
</head>
<body>
    <h1>Consultas do Sistema</h1>
    
    <button onclick="consultarCliente()">Consultar Assai SP</button>
    <button onclick="baixarExcel()">Baixar Excel Carrefour</button>
    
    <div id="resultado"></div>
    
    <script>
        async function consultarCliente() {
            const response = await fetch('/api/v1/cliente/Assai?uf=SP&limite=5');
            const data = await response.json();
            document.getElementById('resultado').innerHTML = 
                `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        
        async function baixarExcel() {
            const response = await fetch('/api/v1/cliente/Carrefour/excel?uf=RJ');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'relatorio_carrefour.xlsx';
            a.click();
        }
    </script>
</body>
</html>
```

### **Aplicativo Mobile (React Native)**
```javascript
import React, { useState } from 'react';
import { View, Button, Text } from 'react-native';

const FreteAPI = () => {
    const [dados, setDados] = useState(null);
    
    const consultarCliente = async (cliente, uf) => {
        try {
            const response = await fetch(
                `https://frete-sistema.onrender.com/api/v1/cliente/${cliente}?uf=${uf}`
            );
            const data = await response.json();
            setDados(data);
        } catch (error) {
            console.error('Erro:', error);
        }
    };
    
    return (
        <View>
            <Button 
                title="Consultar Assai SP" 
                onPress={() => consultarCliente('Assai', 'SP')} 
            />
            <Text>{JSON.stringify(dados, null, 2)}</Text>
        </View>
    );
};
```

---

## 📊 **Exemplos de Respostas da API**

### **Consulta por Cliente**
```json
{
  "success": true,
  "cliente": "ASSAI",
  "uf": "SP",
  "resumo": {
    "total_pedidos": 3,
    "valor_total": 15420.50,
    "pedidos_faturados": 2,
    "percentual_faturado": 66.7
  },
  "data": [
    {
      "pedido": {
        "numero": "VCD2519284",
        "data": "15/06/2024",
        "cliente": "Assai LJ 264",
        "destino": "São Paulo/SP",
        "valor": 5840.39,
        "status": "Faturado",
        "nf": "133526"
      },
      "faturamento": {
        "data_fatura": "15/06/2024",
        "valor_nf": 5056.00,
        "saldo_carteira": 784.39,
        "status_faturamento": "Parcial"
      },
      "monitoramento": {
        "status_entrega": "Agendado",
        "transportadora": "Braspress",
        "pendencia_financeira": false,
        "data_prevista": "27/06/2024"
      }
    }
  ],
  "usuario": "sistema_api",
  "timestamp": "2024-06-20T10:30:15"
}
```

### **Estatísticas do Sistema**
```json
{
  "success": true,
  "data": {
    "periodo_analisado": "Últimos 30 dias",
    "embarques": {
      "total": 45,
      "ativos": 12,
      "cancelados": 33
    },
    "fretes": {
      "total": 127,
      "pendentes_aprovacao": 8,
      "aprovados": 119,
      "percentual_aprovacao": 93.7
    },
    "entregas": {
      "total_monitoradas": 892,
      "entregues": 734,
      "pendencias_financeiras": 23,
      "percentual_entrega": 82.3
    }
  }
}
```

---

## 🔐 **Segurança e Monitoramento**

### **Headers de Segurança**
```python
# Configuração CORS já implementada
API_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}
```

### **Logs e Auditoria**
```python
# Todos os acessos são logados automaticamente
logger.info(f"🌐 API: {endpoint} | User: {user} | IP: {ip}")
```

### **Rate Limiting (Futuro)**
```python
# Implementar se necessário
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)
```

---

## 💡 **Vantagens da Integração no Render**

### **✅ Benefícios**
- **Disponibilidade 24/7**: Sempre online, sem depender de PCs locais
- **Escalabilidade**: Render gerencia recursos automaticamente
- **Backup automático**: Dados seguros na nuvem
- **API REST universal**: Qualquer linguagem/plataforma pode usar
- **SSL/HTTPS**: Comunicação segura por padrão
- **Logs centralizados**: Monitoramento via dashboard Render

### **📱 Casos de Uso**
- **Aplicativos móveis**: Acesso direto via HTTP
- **Dashboards externos**: Power BI, Tableau, Grafana
- **Integrações**: Zapier, Microsoft Power Automate
- **Chatbots**: WhatsApp Business, Telegram
- **Relatórios automáticos**: Scripts Python agendados

---

## 🆔 **URLs de Produção**

### **API REST**
- **Base URL**: `https://frete-sistema.onrender.com/api/v1`
- **Documentação**: `https://frete-sistema.onrender.com/api/v1/docs`
- **Saúde**: `https://frete-sistema.onrender.com/api/v1/health`

### **Exemplos Diretos**
```bash
# Consultar Assai em SP
https://frete-sistema.onrender.com/api/v1/cliente/Assai?uf=SP&limite=5

# Baixar Excel do Carrefour
https://frete-sistema.onrender.com/api/v1/cliente/Carrefour/excel?uf=RJ

# Estatísticas dos últimos 30 dias
https://frete-sistema.onrender.com/api/v1/estatisticas?periodo_dias=30
```

---

## 🏁 **Conclusão**

A integração no Render oferece a melhor solução para disponibilizar as funcionalidades MCP:

1. **Opção 1 (API REST)**: Mais simples, funciona imediatamente
2. **Opção 2 (MCP Server)**: Mais avançada, para uso especializado

**Recomendação**: Comece com a API REST e evolua para o servidor MCP se necessário.

**Status**: ✅ Pronto para deploy e uso em produção! 