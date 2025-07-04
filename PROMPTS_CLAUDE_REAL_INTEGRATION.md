# 🤖 PROMPTS DO CLAUDE REAL INTEGRATION

## 📋 ÍNDICE
1. [System Prompt Principal](#system-prompt-principal)
2. [Prompt de Fallback Simulado](#prompt-de-fallback-simulado)
3. [Prompts de Resposta - Memória Vitalícia](#prompts-de-resposta---memória-vitalícia)
4. [Prompts de Resposta - Agendamentos](#prompts-de-resposta---agendamentos)
5. [Prompts de Resposta - Consulta NFs Específicas](#prompts-de-resposta---consulta-nfs-específicas)
6. [Configuração da API Claude](#configuração-da-api-claude)

---

## 1. System Prompt Principal

**Localização:** `linha 209-225`
**Variável:** `self.system_prompt`

```python
self.system_prompt = \"\"\"Você é Claude AI integrado ao Sistema de Fretes com ACESSO DIRETO ao banco de dados PostgreSQL, forms, models, routes, templates, etc.

🎯 **IMPORTANTE**: Você TEM ACESSO AUTOMÁTICO aos dados do sistema! Os dados abaixo foram carregados AUTOMATICAMENTE pelo seu sistema interno.

DADOS CARREGADOS AUTOMATICAMENTE DO BANCO:
{dados_contexto_especifico}

🧠 **COMO VOCÊ FUNCIONA**:
• Você ACESSA automaticamente o banco PostgreSQL quando recebe uma consulta
• Os dados acima foram carregados pelo SEU próprio sistema de análise
• Você NÃO precisa que o usuário forneça dados - você já os tem
• Analise os dados carregados e forneça insights precisos baseados nos dados REAIS

⚡ **CAPACIDADES ATIVAS**:
• Acesso direto a 70+ tabelas do PostgreSQL
• Carregamento automático de dados por domínio (entregas, fretes, pedidos, etc.)
• Sistema de cache Redis para performance otimizada
Voce tem acesso a todas as tabelas do banco de dados, e pode consultar qualquer informação que você precisa.

Analise os dados carregados automaticamente e forneça insights úteis baseados nos dados REAIS do sistema.\"\"\"
```

---

## 2. Prompt de Fallback Simulado

**Localização:** `linha 2646-2666`
**Função:** `_fallback_simulado()`

```python
return f\"\"\"🤖 **MODO SIMULADO** (Claude Real não disponível)

Consulta recebida: \"{consulta}\"

⚠️ **Para ativar Claude REAL:**
1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente
2. Obtenha chave em: https://console.anthropic.com/
3. Reinicie o sistema

💡 **Com Claude 4 Sonnet Real você terá:**
- Inteligência industrial de ponta
- Análises contextuais precisas
- Diferenciação rigorosa de clientes (Assai ≠ Atacadão)
- Métricas calculadas automaticamente
- Performance otimizada com cache
- Dados completos com reagendamentos

🔄 **Por enquanto, usando sistema básico...\"\"\"
```

---

## 3. Prompts de Resposta - Memória Vitalícia

**Localização:** `linha 376-435`
**Contexto:** Quando usuário pergunta sobre memória/aprendizado do sistema

```python
resultado_memoria = f\"\"\"🤖 **CLAUDE 4 SONNET REAL**

🧠 **MEMÓRIA VITALÍCIA DO SISTEMA**

Aqui está o que tenho armazenado no meu sistema de aprendizado contínuo:

📊 **ESTATÍSTICAS GERAIS**:
• **Total de Padrões Aprendidos**: {total_padroes}
• **Mapeamentos Cliente-Empresa**: {total_mapeamentos}
• **Grupos Empresariais Conhecidos**: {total_grupos}
• **Última Atualização**: {ultima_atualizacao}

🔍 **EXEMPLOS DE PADRÕES APRENDIDOS** (últimos 5):
[... padrões dinâmicos ...]

🏢 **GRUPOS EMPRESARIAIS CONHECIDOS**:
[... grupos dinâmicos ...]

💡 **COMO FUNCIONA MEU APRENDIZADO**:

1. **Padrões de Consulta**: Aprendo como interpretar diferentes formas de fazer perguntas
2. **Mapeamento de Clientes**: Associo variações de nomes aos clientes corretos
3. **Grupos Empresariais**: Identifico empresas que pertencem ao mesmo grupo
4. **Correções do Usuário**: Quando você me corrige, eu registro e aprendo
5. **Contexto Conversacional**: Mantenho histórico da conversa atual

⚡ **CAPACIDADES ATIVAS**:
• ✅ Aprendizado contínuo com cada interação
• ✅ Detecção automática de grupos empresariais
• ✅ Memória conversacional na sessão atual
• ✅ Cache inteligente para respostas frequentes
• ✅ Correção automática de interpretações

📈 **EVOLUÇÃO**:
O sistema melhora continuamente. Cada consulta, correção e feedback contribui para aumentar minha precisão e velocidade de resposta.

---
🧠 **Powered by:** Claude 4 Sonnet + Sistema de Aprendizado Vitalício
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** Banco de Dados PostgreSQL - Tabelas de Aprendizado\"\"\"
```

---

## 4. Prompts de Resposta - Agendamentos

### 4.1. Quando NÃO há agendamentos pendentes

**Localização:** `linha 518-534`

```python
resultado_agendamentos = f\"\"\"🤖 **CLAUDE 4 SONNET REAL**

✅ **AGENDAMENTOS - SITUAÇÃO EXCELENTE**

Não há entregas pendentes de agendamento no momento!

📊 **STATUS ATUAL**:
• Total de entregas pendentes de agendamento: **0**
• Todas as entregas recentes estão com agendamento confirmado
• Sistema monitorado em tempo real

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) + Sistema de Alertas
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** AlertEngine - Dados em tempo real\"\"\"
```

### 4.2. Quando HÁ agendamentos pendentes

**Localização:** `linha 536-594`

```python
resultado_agendamentos = f\"\"\"🤖 **CLAUDE 4 SONNET REAL**

📅 **ENTREGAS COM AGENDAMENTO PENDENTE**

🚨 **ATENÇÃO**: {quantidade} entrega{'s' if quantidade > 1 else ''} {'precisam' if quantidade > 1 else 'precisa'} de agendamento

📊 **DETALHES DAS ENTREGAS PENDENTES**:
[... lista dinâmica de entregas ...]

🎯 **AÇÃO NECESSÁRIA**:
1. Verificar forma de agendamento de cada cliente
2. Entrar em contato para agendar entregas
3. Registrar protocolos de agendamento no sistema

💡 **CRITÉRIO USADO**:
• Entregas embarcadas há mais de 3 dias
• Sem data de entrega prevista definida
• Status não finalizado

📋 **COMO AGENDAR**:
• Acesse o módulo de Monitoramento
• Localize cada NF listada acima
• Clique em \"Agendar\" para registrar o agendamento
• Informe data, hora e protocolo

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) + AlertEngine
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Fonte:** Sistema de Alertas em Tempo Real
📊 **Critério:** Entregas sem data_entrega_prevista embarcadas há >3 dias\"\"\"
```

---

## 5. Prompts de Resposta - Consulta NFs Específicas

**Localização:** `linha 2667-2910`
**Função:** `consultar_posicao_nfs_especificas()`

### 5.1. Cabeçalho da Resposta

```python
resposta = f\"\"\"🔍 **POSIÇÃO DE ENTREGAS - {len(numeros_nf)} NFs CONSULTADAS**

📊 **RESUMO**: {nfs_encontradas} de {len(numeros_nf)} NFs encontradas ({nfs_encontradas/len(numeros_nf)*100:.1f}%)
\"\"\"
```

### 5.2. Seções por Tipo de NF

```python
# Para Entrega Monitorada
resposta += f\"\"\"**NF {nf}** {status_icon} {pendencia_icon}
• **Cliente**: {detalhes.get('cliente', 'N/A')}
• **Status**: {status}
• **Destino**: {detalhes.get('destino', 'N/A')} - {detalhes.get('uf', 'N/A')}
• **Transportadora**: {detalhes.get('transportadora', 'N/A')}
• **Vendedor**: {detalhes.get('vendedor', 'N/A')}
• **Data Embarque**: {detalhes.get('data_embarque', 'Não embarcado')}
• **Data Prevista**: {detalhes.get('data_prevista', 'Sem agendamento')}
• **Data Realizada**: {detalhes.get('data_realizada', 'Não entregue')}
• **Valor NF**: R$ {detalhes.get('valor_nf', 0):,.2f}\"\"\"

# Para Embarque
resposta += f\"\"\"**NF {nf}** {status_icon}
• **Status**: {status}
• **Embarque**: #{detalhes.get('numero_embarque', 'N/A')}
• **Motorista**: {detalhes.get('motorista', 'N/A')}
• **Placa**: {detalhes.get('placa_veiculo', 'N/A')}
• **Data Embarque**: {detalhes.get('data_embarque', 'Aguardando')}
• **Criado em**: {detalhes.get('data_criacao', 'N/A')}\"\"\"

# Para Pedido
resposta += f\"\"\"**NF {nf}** {status_icon}
• **Status**: {status}
• **Pedido**: {detalhes.get('num_pedido', 'N/A')}
• **Cliente**: {detalhes.get('cliente', 'N/A')}
• **Destino**: {detalhes.get('cidade', 'N/A')} - {detalhes.get('uf', 'N/A')}
• **Valor**: R$ {detalhes.get('valor_total', 0):,.2f}
• **Peso**: {detalhes.get('peso_total', 0):,.1f} kg
• **Expedição**: {detalhes.get('expedicao', 'N/A')}
• **Agendamento**: {detalhes.get('agendamento', 'Sem agendamento')}
• **Transportadora**: {detalhes.get('transportadora', 'Não definida')}\"\"\"
```

### 5.3. Rodapé da Consulta NFs

```python
resposta += f\"\"\"---
🔍 **CONSULTA FINALIZADA**
📊 **Total consultado**: {len(numeros_nf)} NFs
✅ **Encontradas**: {nfs_encontradas} NFs
❌ **Não encontradas**: {len(nfs_nao_encontradas)} NFs
📈 **Taxa de sucesso**: {nfs_encontradas/len(numeros_nf)*100:.1f}%

---
🧠 **Powered by:** Claude 4 Sonnet (Anthropic) - Consulta Específica de NFs
🕒 **Processado:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⚡ **Modo:** Busca Multi-Tabela (Entregas + Embarques + Pedidos)\"\"\"
```

### 5.4. Resposta de Erro para NFs

```python
return f\"\"\"❌ **ERRO AO CONSULTAR POSIÇÃO DAS NFs**

**Erro técnico**: {str(e)}

🔧 **Soluções**:
1. Verificar se os números das NFs estão corretos
2. Tentar consulta com menos NFs por vez
3. Contactar suporte se erro persistir

💡 **Formato correto**: 6 dígitos começando com 1
**Exemplo**: 135497, 134451, 136077\"\"\"
```

---

## 6. Configuração da API Claude

**Localização:** `linha 943-956`
**Função:** `processar_consulta_real()`

```python
response = self.client.messages.create(
    model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
    max_tokens=4000,  # Restaurado para análises completas
    temperature=0.0,  # Máxima precisão - sem criatividade
    timeout=120.0,  # 2 minutos para análises profundas
    system=self.system_prompt.format(
        dados_contexto_especifico=self._descrever_contexto_carregado(contexto_analisado)
    ),
    messages=messages  # type: ignore
)
```

### 6.1. Formatação da Resposta Final

```python
resposta_final = f\"\"\"{resultado}

---
Claude 4 Sonnet | {datetime.now().strftime('%d/%m/%Y %H:%M')}\"\"\"
```

---

## 📝 OBSERVAÇÕES IMPORTANTES

### 🎯 **Características dos Prompts:**

1. **System Prompt Dinâmico**: O prompt principal é formatado com dados reais do banco
2. **Respostas Contextuais**: Cada tipo de consulta tem seu próprio formato de resposta
3. **Branding Consistente**: Todos usam "🤖 **CLAUDE 4 SONNET REAL**"
4. **Timestamps**: Todas as respostas incluem data/hora de processamento
5. **Powered by**: Rodapé com tecnologias utilizadas
6. **Emojis Funcionais**: Cada emoji tem significado específico (🎯, 📊, ✅, ❌, etc.)

### 🔧 **Parâmetros Claude API:**

- **Modelo**: `claude-sonnet-4-20250514` (Claude 4 Sonnet)
- **Temperature**: `0.0` (máxima precisão)
- **Max Tokens**: `4000` (análises completas)
- **Timeout**: `120.0` segundos (2 minutos)

### 🧠 **Integração com Sistemas:**

- **Aprendizado Vitalício**: Prompts usam dados aprendidos
- **Cache Redis**: Respostas são cacheadas
- **Contexto Conversacional**: Mantém histórico da conversa
- **Multi-Agent System**: Fallback para outros sistemas IA
- **Human Learning**: Captura feedback automaticamente

---

**Arquivo gerado em:** `{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}`  
**Fonte:** `app/claude_ai/claude_real_integration.py`  
**Total de Linhas Analisadas:** 3553 linhas 