# Output Patterns

Use these patterns when skills need to produce consistent, high-quality output.

## Template Pattern

Provide templates for output format. Match the level of strictness to your needs.

**For strict requirements (like API responses or data formats):**

```markdown
## Report structure

ALWAYS use this exact template structure:

# [Analysis Title]

## Executive summary
[One-paragraph overview of key findings]

## Key findings
- Finding 1 with supporting data
- Finding 2 with supporting data
- Finding 3 with supporting data

## Recommendations
1. Specific actionable recommendation
2. Specific actionable recommendation
```

**For flexible guidance (when adaptation is useful):**

```markdown
## Report structure

Here is a sensible default format, but use your best judgment:

# [Analysis Title]

## Executive summary
[Overview]

## Key findings
[Adapt sections based on what you discover]

## Recommendations
[Tailor to the specific context]

Adjust sections as needed for the specific analysis type.
```

## Examples Pattern

For skills where output quality depends on seeing examples, provide input/output pairs:

```markdown
## Commit message format

Generate commit messages following these examples:

**Example 1:**
Input: Added user authentication with JWT tokens
Output:
```
feat(auth): implement JWT-based authentication

Add login endpoint and token validation middleware
```

**Example 2:**
Input: Fixed bug where dates displayed incorrectly in reports
Output:
```
fix(reports): correct date formatting in timezone conversion

Use UTC timestamps consistently across report generation
```

Follow this style: type(scope): brief description, then detailed explanation.
```

Examples help Claude understand the desired style and level of detail more clearly than descriptions alone.

## Decision Tree Pattern

For skills with multiple scripts serving different use cases, include a decision tree that maps user triggers to the correct script:

```markdown
## Mapeamento Rapido

| Se a pergunta menciona... | Use este script | Com estes parametros |
|---------------------------|-----------------|----------------------|
| **Resumo completo** ("tudo sobre X") | `script_completo.py` | `--item X` |
| **Comparativo** ("programado vs real") | `script_comparativo.py` | `--item X --de Y --ate Z` |

## Regras de Decisao

1. **VISAO COMPLETA**: "resumo", "tudo sobre", "dados do item"
   -> `script_completo.py --item X`

2. **COMPARATIVO**: "programado", "realizado", "cumpriu"
   -> `script_comparativo.py --item X --de Y --ate Z`

3. SE o usuario menciona APENAS um aspecto parcial:
   -> Redirecionar para skill especializada
```

This pattern ensures the agent selects the correct script and parameters from user intent. Include numbered rules after the table for ambiguous scenarios where multiple scripts could apply.