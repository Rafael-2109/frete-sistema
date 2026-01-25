# Framework de Perguntas

## Por Tipo de Tarefa

### Feature Nova

| Fase | Pergunta | Objetivo |
|------|----------|----------|
| 1 | O que voce quer construir? | Visao geral |
| 2 | Qual problema isso resolve? | Justificativa |
| 3 | Quem vai usar? | Usuarios |
| 4 | Quais funcionalidades principais? | Escopo |
| 5 | Precisa de nova tela? | Interface |
| 6 | Quais dados exibir/coletar? | Campos |
| 7 | Como saber se funcionou? | Criterios |

### Bug Fix

| Fase | Pergunta | Objetivo |
|------|----------|----------|
| 1 | Qual o problema? | Sintoma |
| 2 | Qual comportamento esperado? | Correcao |
| 3 | Como reproduzir? | Steps |
| 4 | Quando comecou? | Timeline |
| 5 | Afeta outros lugares? | Impacto |

### Integracao

| Fase | Pergunta | Objetivo |
|------|----------|----------|
| 1 | Qual sistema integrar? | Destino |
| 2 | Quais dados sincronizar? | Payload |
| 3 | Qual direcao? (enviar/receber/ambos) | Fluxo |
| 4 | Frequencia? (real-time/batch) | Timing |
| 5 | Como tratar erros? | Fallback |

### Refatoracao

| Fase | Pergunta | Objetivo |
|------|----------|----------|
| 1 | O que esta ruim hoje? | Problema |
| 2 | Como deveria ficar? | Solucao |
| 3 | Quais arquivos afetados? | Escopo |
| 4 | Pode quebrar algo? | Riscos |
| 5 | Como testar? | Validacao |

---

## Perguntas de Contexto (Pesquisa Automatica)

Antes de perguntar detalhes tecnicos, pesquisar:

```python
# Termos a buscar no codebase
termos = extrair_palavras_chave(resposta_usuario)

# Onde buscar
Grep(pattern=termo, path="app/")
Glob(pattern=f"**/*{termo}*")

# O que mostrar
"Encontrei X arquivos relacionados:
- [arquivo1] - [o que faz]
- [arquivo2] - [o que faz]

Isso esta relacionado?"
```

---

## Perguntas de Criterios (Sempre Fazer)

1. **"Como saber se funcionou?"**
2. **"Quais validacoes?"**
3. **"E se der erro?"**

Transformar respostas em checkboxes verificaveis.

---

## Anti-Patterns (Evitar)

| Errado | Certo |
|--------|-------|
| Fazer 5 perguntas de uma vez | Uma pergunta por mensagem |
| Perguntar sem contexto | Pesquisar e mostrar antes |
| Assumir tecnologia | Perguntar preferencia |
| Pular criterios de aceite | Sempre perguntar validacao |
