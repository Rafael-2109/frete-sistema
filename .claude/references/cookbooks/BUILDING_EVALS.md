# Guia de Building Evals (Avaliações)

**Fonte:** [claude-cookbooks/misc/building_evals.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb)

## O Que São Evals

Evals são sistemas de avaliação para medir a qualidade das respostas de Claude em tarefas específicas. Permitem:

- Testar prompts antes de produção
- Comparar diferentes abordagens
- Garantir consistência de qualidade
- Identificar casos de falha

## Componentes de uma Eval

| Componente | Descrição |
|------------|-----------|
| **Input Prompt** | O que é enviado para Claude (com variáveis) |
| **Model Output** | Resposta gerada por Claude |
| **Golden Answer** | Resposta de referência (esperada) |
| **Score** | Resultado da avaliação (correto/incorreto, 0-100, etc) |

## Três Métodos de Grading

### 1. Code-based Grading (Melhor para tarefas determinísticas)

Usa string matching, regex, ou validação programática.

```python
def grade_completion(output: str, golden_answer: str) -> bool:
    """Avalia se output corresponde à resposta esperada."""
    return output.strip().lower() == golden_answer.strip().lower()

# Exemplo: Quantas pernas tem um animal?
eval_cases = [
    {"input": "humano", "golden": "2"},
    {"input": "cobra", "golden": "0"},
    {"input": "cachorro", "golden": "4"},
]

for case in eval_cases:
    output = get_claude_response(f"Quantas pernas tem um {case['input']}?")
    score = grade_completion(output, case["golden"])
    print(f"{case['input']}: {'✓' if score else '✗'}")
```

**Vantagens:** Rápido, confiável, barato
**Limitações:** Só funciona para outputs determinísticos

### 2. Model-based Grading (Melhor para tarefas abertas)

Claude avalia suas próprias respostas usando um prompt de avaliação.

```python
GRADER_PROMPT = """
Você é um avaliador de qualidade. Compare a resposta com a rubrica.

<answer>
{answer}
</answer>

<rubric>
{rubric}
</rubric>

Avalie se a resposta atende à rubrica.
Retorne sua avaliação em <correctness>correct</correctness> ou
<correctness>incorrect</correctness>.
"""

def grade_with_model(output: str, rubric: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": GRADER_PROMPT.format(answer=output, rubric=rubric)
        }]
    )

    # Extrair resultado
    import re
    match = re.search(r"<correctness>(.*?)</correctness>", response.content[0].text)
    return match.group(1).strip() if match else "unknown"
```

**Vantagens:** Funciona para qualquer tarefa
**Limitações:** Mais lento, pode ter variabilidade

### 3. Human Grading (Última opção)

Avaliação manual por humanos. Use apenas quando necessário.

```python
# Golden answer formatada como rubrica para humano
golden_answer = """
A resposta deve incluir:
✓ Plano de treino com >50 repetições
✓ Exercícios de pernas especificados
✓ Divisão por dia da semana
✗ NÃO deve incluir exercícios de braço
"""
```

**Vantagens:** Funciona para qualquer coisa
**Desvantagens:** Lento, caro, inconsistente

## Implementação Completa

### Estrutura do Eval

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class EvalCase:
    """Um caso de teste para avaliação."""
    input_vars: dict        # Variáveis para preencher o prompt
    golden_answer: str      # Resposta esperada ou rubrica
    tags: list[str] = None  # Categorias para análise

@dataclass
class EvalResult:
    """Resultado de uma avaliação."""
    case: EvalCase
    output: str
    score: bool | float
    grading_method: str

class PromptEvaluator:
    """Framework de avaliação de prompts."""

    def __init__(self, prompt_template: str, grader: Callable):
        self.prompt_template = prompt_template
        self.grader = grader
        self.results: list[EvalResult] = []

    def run_eval(self, cases: list[EvalCase]) -> dict:
        """Executa avaliação em todos os casos."""
        for case in cases:
            # Preenche template
            prompt = self.prompt_template.format(**case.input_vars)

            # Obtém resposta
            output = self._get_response(prompt)

            # Avalia
            score = self.grader(output, case.golden_answer)

            self.results.append(EvalResult(
                case=case,
                output=output,
                score=score,
                grading_method=self.grader.__name__
            ))

        return self._calculate_metrics()

    def _calculate_metrics(self) -> dict:
        """Calcula métricas agregadas."""
        total = len(self.results)
        correct = sum(1 for r in self.results if r.score)

        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0,
            "failed_cases": [r for r in self.results if not r.score]
        }
```

## Aplicação no Frete Sistema

### Eval para Skill de Priorização

```python
PRIORIZACAO_CASES = [
    EvalCase(
        input_vars={
            "pedido": "VCD123",
            "cliente": "ATACADAO",
            "valor": 150000,
            "data_entrega": "2024-12-15",
            "estoque_disponivel": True
        },
        golden_answer="P4",  # Atacadão = P4
        tags=["atacadao", "com_estoque"]
    ),
    EvalCase(
        input_vars={
            "pedido": "VCD456",
            "tipo": "FOB",
            "estoque_parcial": True
        },
        golden_answer="AGUARDAR_COMPLETO",  # FOB sempre completo
        tags=["fob", "parcial"]
    ),
]

def grade_priorizacao(output: str, golden: str) -> bool:
    """Avalia se a priorização está correta."""
    return golden.lower() in output.lower()

# Executar eval
evaluator = PromptEvaluator(
    prompt_template=PRIORIZACAO_PROMPT,
    grader=grade_priorizacao
)
results = evaluator.run_eval(PRIORIZACAO_CASES)
print(f"Acurácia: {results['accuracy']:.1%}")
```

### Eval para Comunicação com PCP

```python
PCP_RUBRIC = """
A mensagem para PCP deve conter:
1. Saudação inicial
2. Lista de PRODUTOS (não pedidos) com falta
3. Para cada produto:
   - Demanda total
   - Estoque atual
   - Quantidade faltante
   - Pedidos afetados
4. Pergunta sobre previsão de produção
5. Tom profissional
"""

PCP_CASES = [
    EvalCase(
        input_vars={
            "produtos_falta": [
                {"nome": "Palmito", "demanda": 1000, "estoque": 300}
            ],
            "pedidos": ["VCD123", "VCD456"]
        },
        golden_answer=PCP_RUBRIC,
        tags=["pcp", "ruptura"]
    ),
]

# Usar model-based grading para avaliação aberta
results = evaluator.run_eval(PCP_CASES)
```

### Eval para Decisão Parcial/Aguardar

```python
PARCIAL_CASES = [
    # Falta <= 10% + demora > 3 dias = PARCIAL
    EvalCase(
        input_vars={
            "percentual_falta": 8,
            "dias_demora": 5,
            "valor_pedido": 50000
        },
        golden_answer="PARCIAL",
        tags=["parcial_auto"]
    ),
    # Falta > 20% = CONSULTAR
    EvalCase(
        input_vars={
            "percentual_falta": 25,
            "dias_demora": 3,
            "valor_pedido": 80000
        },
        golden_answer="CONSULTAR_COMERCIAL",
        tags=["consultar"]
    ),
    # FOB = SEMPRE COMPLETO
    EvalCase(
        input_vars={
            "tipo": "FOB",
            "percentual_falta": 5
        },
        golden_answer="AGUARDAR_COMPLETO",
        tags=["fob"]
    ),
]
```

## Melhores Práticas

### 1. Evals Específicas
- Crie evals separadas por funcionalidade
- Não misture tipos de tarefa na mesma eval

### 2. Volume > Qualidade Individual
- Mais casos simples > poucos casos elaborados
- Cobertura de edge cases é essencial

### 3. Automação
- Prefira code-based quando possível
- Model-based para tarefas abertas
- Human grading apenas quando necessário

### 4. Análise de Falhas
```python
def analyze_failures(results: dict):
    """Analisa casos de falha por categoria."""
    failures = results["failed_cases"]

    by_tag = {}
    for f in failures:
        for tag in f.case.tags or []:
            by_tag.setdefault(tag, []).append(f)

    print("Falhas por categoria:")
    for tag, cases in by_tag.items():
        print(f"  {tag}: {len(cases)} falhas")
```

### 5. Regression Testing
Execute evals após mudanças no prompt para garantir que não quebrou.

## Estrutura de Arquivos Sugerida

```
.claude/
└── evals/
    ├── priorizacao/
    │   ├── cases.json
    │   ├── grader.py
    │   └── results/
    ├── comunicacao_pcp/
    │   ├── cases.json
    │   └── rubrics.md
    └── run_all_evals.py
```

## Referências

- [Building Evals Notebook](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb)
- [Anthropic Eval Best Practices](https://docs.anthropic.com/claude/docs/evaluating-prompts)
