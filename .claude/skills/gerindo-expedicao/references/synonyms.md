# Sinonimos de Entrada

Mapeamento de termos que o usuario pode usar para a mesma coisa.

> **Quando usar:** Consulte este arquivo quando precisar normalizar a entrada do usuario para termos padrao do sistema.

---

O usuario pode usar diversos termos para a mesma coisa. Normalize antes de processar:

| Termo Usuario | Termo Padrao | Significado |
|---------------|--------------|-------------|
| ketchup, catchup, ketichap | ketchup | Produto ketchup |
| c car, int, com caroço | inteiro/a | Produtos inteiros, que não foram fatiados / processados |
| caixa, cx, unidade, un | unidade | Quantidade de produto |
| loja, filial, unidade (cliente) | loja | Filial do cliente |
| embarque, despacho, saida | expedicao | Data de envio |
| chegada, recebimento, entrega | agendamento | Data de entrega no cliente |
| pedido, PV, OV, venda | pedido | Ordem de venda |
| cliente, comprador, destinatario | cliente | Quem compra |
| transportadora, frete, carrier | transportadora | Empresa de transporte |
| estoque, saldo, disponivel | estoque | Quantidade em armazem |
| falta, ruptura, stockout | ruptura | Estoque insuficiente |
| separacao, picking, sep | separacao | Preparacao de pedido |
| programacao, OP, ordem producao | producao | Ordem de producao |

---

**Importante**: Quando o termo for ambiguo no contexto, PERGUNTE. Ex: "unidade" pode ser quantidade ou filial.
