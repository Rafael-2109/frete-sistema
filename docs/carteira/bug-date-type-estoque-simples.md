<!-- doc:meta
tipo: explanation
camada: L3
sot_de: bug de tipo de data (date vs str) que pode zerar entradas de producao na projecao de estoque_simples
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Bug de tipo de data (date vs str) na projecao de estoque_simples

> **Papel:** Documenta o bug de incompatibilidade de tipo de chave de data (date vs str) que pode zerar as entradas de producao na projecao de estoque, com a correcao recomendada.

## Contexto

`ServicoEstoqueSimples` projeta o estoque combinando saidas (carteira) com entradas de producao programada. As entradas sao indexadas por data num dicionario; se a chave gravada (em `calcular_entradas_previstas`) tem tipo diferente da chave buscada (em `calcular_projecao`), o lookup falha em silencio e a producao some da projecao. Fonte: `app/estoque/services/estoque_simples.py`.

## Indice

- [O Problema](#-o-problema)
- [Confirmacao do bug](#-confirmacao-do-bug)
- [Solucao](#-solucao)
- [Status](#status-verificado-2026-06-15)

## ❌ O PROBLEMA

### Em `calcular_entradas_previstas` (linha 144):
```python
entradas[resultado.data] = float(resultado.quantidade)
# resultado.data é um objeto date (retornado pelo PostgreSQL)
```

### Em `calcular_projecao` (linha 195):
```python
entrada_dia = entradas.get(data, 0)
# data é um objeto date (criado com hoje + timedelta(days=dia))
```

**DEVERIA FUNCIONAR**, pois ambos são objetos `date`.

## 🔍 MAS HÁ UM PROBLEMA SUTIL

### A query usa `func.date()`:
```python
func.date(ProgramacaoProducao.data_programacao).label('data')
```

Dependendo do driver do PostgreSQL e SQLAlchemy, `func.date()` pode retornar:
- Um objeto `datetime.date` 
- Um objeto `datetime.datetime` com hora 00:00:00
- Uma string no formato 'YYYY-MM-DD'

## 🐛 CONFIRMAÇÃO DO BUG

Se `resultado.data` retorna uma **string** (ex: '2025-09-03') e `data` em calcular_projecao é um **objeto date**, então:

```python
entradas['2025-09-03'] = 100  # Chave é STRING
entrada_dia = entradas.get(date(2025, 9, 3), 0)  # Busca por OBJETO DATE
# Resultado: 0 (não encontra!)
```

## ✅ SOLUÇÃO

### Garantir que as chaves sejam sempre do mesmo tipo:

```python
# Em calcular_entradas_previstas (linha 142-144):
for resultado in resultados:
    if resultado.data and resultado.quantidade:
        # Garantir que a chave seja um objeto date
        if isinstance(resultado.data, str):
            data_key = date.fromisoformat(resultado.data)
        elif isinstance(resultado.data, datetime):
            data_key = resultado.data.date()
        else:
            data_key = resultado.data
        entradas[data_key] = float(resultado.quantidade)
```

### OU normalizar ambos para string:

```python
# Em calcular_entradas_previstas:
entradas[str(resultado.data)] = float(resultado.quantidade)

# Em calcular_projecao:
entrada_dia = entradas.get(str(data), 0)
```

## 📊 TESTE PARA CONFIRMAR

```python
# Adicionar log em calcular_entradas_previstas:
logger.debug(f"Tipo de resultado.data: {type(resultado.data)}, valor: {resultado.data}")
logger.debug(f"Chaves no dicionário entradas: {list(entradas.keys())}")

# Adicionar log em calcular_projecao:
logger.debug(f"Buscando data: {data} (tipo: {type(data)})")
logger.debug(f"Encontrou entrada: {entrada_dia}")
```

## 🎯 CONCLUSÃO

O problema é a **incompatibilidade de tipos** entre as chaves do dicionário (possivelmente strings) e as chaves buscadas (objetos date). Isso faz com que `entradas.get(data, 0)` sempre retorne 0, mesmo quando há produção programada.

## Status (verificado 2026-06-15)

- `calcular_entradas_previstas` (`app/estoque/services/estoque_simples.py:144`) ainda **NAO** aplica o guard de tipo — bug em aberto; aplicar a correcao acima.
- A variante batch que JA tem o guard `isinstance` e `calcular_projecao_batch_sem_cnpjs` (`app/estoque/services/estoque_simples.py:702`), nao `calcular_multiplos_produtos` (`:306`, sem guard).
