---
name: criar-separacao
description: Cria separacao de pedido com simulacao previa obrigatoria
---

Crie uma separacao para o pedido especificado.

## IMPORTANTE: Sempre simular primeiro!

1. Execute SEM `--executar` para simular
2. Mostre o resultado da simulacao ao usuario
3. Solicite confirmacao explicita
4. Somente entao execute COM `--executar`

## Script

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py $ARGUMENTS
```

## Parametros Comuns

- `--pedido VCD123` - Numero do pedido (OBRIGATORIO)
- `--expedicao amanha` - Data de expedicao (OBRIGATORIO)
- `--tipo completa` ou `--tipo parcial`
- `--pallets 28` - Quantidade de pallets
- `--apenas-estoque` - Apenas o disponivel
- `--executar` - Efetivamente criar (usar apos confirmacao)

## Checklist Pre-Criacao

- [ ] Pedido existe e tem saldo?
- [ ] Estoque disponivel verificado?
- [ ] Cliente exige agendamento? (verificar ContatoAgendamento)
- [ ] Data de expedicao faz sentido com lead time?

## Exemplos

```bash
# Simulacao
--pedido VCD123 --expedicao amanha --tipo completa

# Execucao (apos confirmacao)
--pedido VCD123 --expedicao amanha --tipo completa --executar
```

$ARGUMENTS
