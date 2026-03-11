# Metodos de Qualidade — Quick Reference

---

## Quando Usar Qual

| Tipo de Problema | Metodo | Sinal |
|------------------|--------|-------|
| Bug, incidente, falha pontual | **5 Porques** | "Por que X aconteceu?" |
| Performance, processo, fluxo | **CAPDO** | "Como melhorar Y?" |
| Arquitetura, design, multiplas causas | **Ishikawa** | "Quais fatores contribuem?" |
| Desconhecido | Comecar com **5 Porques**, ramificar para Ishikawa se multiplas causas |

---

## 5 Porques (Five Whys)

### Conceito

Cadeia de perguntas "por que?" ate chegar na causa-raiz. Tipicamente 3-7 niveis.

### Formato

```
Sintoma: {o que esta acontecendo}

1. Por que {sintoma}?
   → Porque {causa-1}
   EVIDENCIA: {finding:fato}

2. Por que {causa-1}?
   → Porque {causa-2}
   EVIDENCIA: {finding:fato}

3. Por que {causa-2}?
   → Porque {causa-3}
   EVIDENCIA: {finding:fato}

...

N. CAUSA-RAIZ: {causa-N}
   EVIDENCIA: {finding:fato}
   ACAO CORRETIVA: {o que fazer}
```

### Regras

1. **Cada "por que" DEVE ter evidencia** — sem evidencia, e especulacao
2. **Parar quando a causa esta sob seu controle** — nao descer ate "porque o universo existe"
3. **Se ramificar**: multiplas causas no mesmo nivel → avaliar se e Ishikawa
4. **Validar de tras pra frente**: "Se corrigirmos causa-N, causa-N-1 para? Se para, causa-N-2 para?"

### Armadilhas

- **Parar cedo demais**: "Porque o campo era null" → POR QUE era null?
- **Culpar pessoas**: "Porque o dev errou" → POR QUE o sistema permitiu o erro?
- **Pular niveis**: Cada nivel deve ser verificavel independentemente

### Exemplo (Sistema de Fretes)

```
Sintoma: Embarque criado sem peso_cubado

1. Por que embarque sem peso_cubado?
   → Porque o service nao calcula peso_cubado quando tipo_veiculo e null
   EVIDENCIA: app/fretes/services/embarque_service.py:145

2. Por que tipo_veiculo e null?
   → Porque a rota de criacao nao valida tipo_veiculo como obrigatorio
   EVIDENCIA: app/fretes/routes.py:67

3. Por que a rota nao valida?
   → Porque o form frontend envia campo vazio como null em vez de omitir
   EVIDENCIA: app/templates/fretes/criar_embarque.html:89

CAUSA-RAIZ: Frontend envia null para campos vazios, backend nao valida
ACAO: Adicionar validacao backend (obrigatoria) + frontend (UX)
```

---

## CAPDO (Check-Analyze-Plan-Do)

### Conceito

Ciclo PDCA invertido. Comeca pela medicao (Check), nao pelo plano. Melhor para problemas de processo/performance onde voce precisa medir ANTES de decidir.

### Formato

```
# Check (Medir)
## Metricas Atuais
- {metrica-1}: {valor} — FONTE: {finding}
- {metrica-2}: {valor} — FONTE: {finding}
## Baseline
- {o que e "normal" para comparacao}
## Anomalias
- {desvio do esperado} — FONTE: {finding}

# Analyze (Analisar)
## Causa das Anomalias
- {anomalia-1} causada por {fator} — EVIDENCIA: {finding}
## Correlacoes
- {metrica-A} correlaciona com {metrica-B} porque {razao}
## Restricoes
- {limitacao do sistema que impede melhoria}

# Plan (Planejar)
## Meta
- {metrica-alvo}: de {atual} para {desejado}
## Acoes
1. {acao-1} — impacto esperado: {estimativa}
2. {acao-2} — impacto esperado: {estimativa}
## Criterio de Sucesso
- {como saber se funcionou}

# Do (Executar)
## Implementacao
- {o que foi feito}
## Resultado
- {metrica-1}: {antes} → {depois}
```

### Quando Preferir CAPDO

- Voce tem metricas disponiveis (tempo de resposta, contagem de erros, etc)
- O problema e "esta lento" ou "acontece muito" (nao "esta errado")
- Precisa justificar a mudanca com numeros

---

## Ishikawa (Diagrama de Causa e Efeito)

### Conceito

Categoriza MULTIPLAS causas de um efeito. Util quando 5 Porques ramifica em 3+ causas independentes.

### Categorias Padrao (adaptadas para software)

| Categoria | Exemplos |
|-----------|----------|
| **Codigo** | Bugs, logica incorreta, falta de validacao, race conditions |
| **Dados** | Schema incorreto, dados sujos, falta de constraints, migrations |
| **Infraestrutura** | Timeout, memoria, conexoes, deploy, configuracao |
| **Processo** | Falta de review, documentacao, testes, monitoramento |
| **Dependencias** | Libs desatualizadas, APIs externas, servicos terceiros |
| **Pessoas** | Conhecimento, comunicacao, handoff |

### Formato

```
# Efeito: {problema observado}

## Codigo
- {causa-1} — EVIDENCIA: {finding}
  - {sub-causa} — EVIDENCIA: {finding}
- {causa-2} — EVIDENCIA: {finding}

## Dados
- {causa-3} — EVIDENCIA: {finding}

## Infraestrutura
- {causa-4} — EVIDENCIA: {finding}

## Processo
- {causa-5} — EVIDENCIA: {finding}

## Dependencias
- (nenhuma encontrada)

## Pessoas
- (nao aplicavel — foco em sistema)

## Causas Principais (top 3 por impacto)
1. {causa-X} (categoria: {cat}) — impacto: ALTO
2. {causa-Y} (categoria: {cat}) — impacto: MEDIO
3. {causa-Z} (categoria: {cat}) — impacto: MEDIO
```

### Quando Preferir Ishikawa

- 5 Porques ramificou em 3+ causas independentes
- Problema e sistemico (nao pontual)
- Precisa priorizar entre multiplas causas
- Stakeholders diferentes precisam entender o mapa completo

### Regra de Priorizacao

Depois de mapear, priorizar por:
1. **Frequencia**: Quantas vezes essa causa contribui?
2. **Impacto**: Quanto dano causa quando ocorre?
3. **Controlabilidade**: Podemos agir sobre isso?

Focar nas causas que sao FREQUENTES + ALTO IMPACTO + CONTROLAVEIS.

---

## Combinando Metodos

```
Problema desconhecido
  │
  ├── Comecar com 5 Porques
  │     │
  │     ├── Cadeia linear → continuar 5 Porques ate causa-raiz
  │     │
  │     └── Ramifica em 3+ causas → mudar para Ishikawa
  │           │
  │           └── Para cada causa principal do Ishikawa:
  │                 ├── Se mensuravel → CAPDO para medir e validar
  │                 └── Se nao mensuravel → 5 Porques para aprofundar
  │
  └── Se tem metricas desde o inicio → CAPDO direto
```
