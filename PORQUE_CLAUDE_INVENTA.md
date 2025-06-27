# 🧠 Por Que Claude Inventa Dados?

## 🔍 Análise Técnica do Comportamento

### 1. **Conflito entre Conhecimento Pré-treinado e Dados Fornecidos**

Claude foi treinado com BILHÕES de exemplos que incluem:
- Informações sobre empresas brasileiras (Makro, Walmart, Extra)
- Padrões de resposta "completos" e "úteis"
- Tendência a fornecer respostas detalhadas

Quando recebe dados parciais, o modelo:
```
Dados fornecidos: 78 clientes em 933 registros
Conhecimento interno: "Sistemas de frete atendem centenas de clientes"
Resultado: Tenta "completar" a resposta com conhecimento geral
```

### 2. **Pressão para Ser Útil (Helpfulness Bias)**

O modelo foi treinado para:
- ✅ Ser útil e informativo
- ✅ Fornecer respostas completas
- ❌ Mas isso conflita com "usar apenas dados fornecidos"

Exemplo:
```
Pergunta: "Quais são os principais clientes?"
Dados: ATACADAO, ASSAI, TOTAL ATACADO
Impulso: "Essa lista parece incompleta, vou adicionar outros varejistas conhecidos"
```

### 3. **Problema de Continuidade de Contexto**

Mesmo após correção, Claude não mantém a restrição:

```python
Turno 1: Inventa dados
Turno 2: "Desculpe, vou usar apenas dados reais"
Turno 3: Inventa dados novamente
```

Por quê? Cada resposta é gerada considerando:
- System prompt (instruções gerais)
- Histórico da conversa
- **MAS** o impulso de ser útil é mais forte que a correção anterior

### 4. **Embeddings e Associações Semânticas**

No espaço de embeddings do modelo:
- "ATACADÃO" está próximo de "MAKRO", "WALMART", "EXTRA"
- São todos "grandes varejistas brasileiros"
- O modelo faz associações automáticas

```
Entrada: "clientes do sistema de frete" + "ATACADÃO"
Ativação: neurônios relacionados a "varejo brasileiro"
Saída: lista expandida com empresas similares
```

### 5. **Temperature e Sampling**

Mesmo com temperature baixa (0.1), o modelo ainda:
- Tem probabilidades não-zero para tokens de empresas conhecidas
- Pode amostrar esses tokens durante a geração

### 6. **Falta de Grounding Explícito**

O modelo não tem um mecanismo de "grounding" que:
- Verifique cada afirmação contra os dados
- Bloqueie tokens não presentes nos dados
- Force aderência estrita aos fatos fornecidos

## 💡 Por Isso as Correções São Necessárias

### Script 1: `corrigir_claude_inventando_dados.py`
- Adiciona regras explícitas no system prompt
- Detecta quando pergunta é sobre totais
- Implementa queries especiais sem filtro

### Script 2: `corrigir_claude_forcando_dados_reais.py`
- System prompt AGRESSIVO
- Lista de empresas BANIDAS hardcoded
- Validador que detecta e avisa sobre invenções
- Inclui lista de clientes reais no prompt

## 🎯 Solução Ideal (Futura)

O ideal seria implementar:

1. **Constrained Generation**: Limitar tokens possíveis baseado nos dados
2. **Fact Checking Layer**: Validar cada afirmação antes de incluir
3. **Retrieval-Augmented Generation**: Buscar apenas nos dados fornecidos
4. **Fine-tuning**: Treinar o modelo especificamente para não inventar

## 📊 Resumo

Claude inventa porque:
- Tem conhecimento interno sobre empresas brasileiras
- Foi treinado para ser útil e completo
- Associações semânticas ativam empresas relacionadas
- Não tem mecanismo de grounding estrito
- Cada resposta é gerada semi-independentemente

As correções propostas forçam o modelo a aderir aos dados através de:
- Instruções explícitas e repetitivas
- Validação pós-geração
- Inclusão dos dados reais no prompt
- Proibições específicas 