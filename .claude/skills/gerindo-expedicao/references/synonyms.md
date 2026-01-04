# Sinonimos de Entrada - CRITICOS

Apenas termos NAO OBVIOS que Claude nao saberia inferir do contexto.

> **Quando usar:** Consulte este arquivo quando precisar normalizar termos especificos do dominio logistico.

---

## Termos Criticos (NAO remover)

| Termo Usuario | Termo Padrao | Por que e critico |
|---------------|--------------|-------------------|
| c car, int, com caroco | inteiro/a | Jargao interno: produtos nao fatiados |
| embarque, despacho, saida | expedicao | Termo tecnico: data que SAI do CD |
| chegada, recebimento | agendamento | DIFERENTE de entrega! E a data que CHEGA no cliente |
| RED, redespacho | redespacho | Operacao via SP |
| OP, ordem producao | producao | Programacao de fabrica |

---

## Termos Ambiguos (SEMPRE perguntar)

| Termo | Pode significar | Acao |
|-------|-----------------|------|
| unidade | Quantidade OU filial do cliente | Perguntar contexto |
| entrega | data_entrega_pedido OU agendamento | Perguntar qual |
| disponivel | Estoque atual OU quando fica disponivel | Perguntar qual |

---

**Nota:** Sinonimos obvios (ketchup→catchup, caixa→cx, cliente→comprador) NAO estao aqui porque Claude ja entende.
