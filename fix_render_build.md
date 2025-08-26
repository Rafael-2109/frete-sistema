# Correção do Build no Render - Python 3.13

## Problema
O build está falhando devido a incompatibilidades com Python 3.13:
- `greenlet`: Erro com `_PyCFrame` (estrutura interna removida no Python 3.13)
- `Levenshtein`: Erro com `_PyLong_AsByteArray` (API mudou no Python 3.13)

## Soluções Possíveis

### Solução 1: Especificar Python 3.12 no Render (RECOMENDADA)

Crie ou edite o arquivo `runtime.txt`:

```
python-3.12.7
```

### Solução 2: Atualizar requirements.txt

Adicione versões específicas que suportam Python 3.13:

```txt
# Em requirements.txt, adicione/atualize:
greenlet>=3.1.0  # Versão 3.1.0+ suporta Python 3.13
python-Levenshtein-wheels>=0.13.2  # Use wheels ao invés de Levenshtein puro
```

### Solução 3: Usar alternativas

Remova `Levenshtein` e use `rapidfuzz` que é mais moderno:

```python
# Ao invés de:
# from Levenshtein import distance

# Use:
from rapidfuzz.distance import Levenshtein
distance = Levenshtein.distance(str1, str2)
```

## Ação Imediata

1. Vamos criar o arquivo runtime.txt para forçar Python 3.12
2. Atualizar requirements.txt com versões compatíveis