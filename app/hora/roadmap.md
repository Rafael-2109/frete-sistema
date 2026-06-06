# Vendas

### 1
Separar venda de motos × peças/oficina

- Motos com NF
- Peças/oficina em Recibo Simples (com opção de NF se cliente pedir). 

Renomear estrutura dos pedidos de vendas para pedidos de vendas de motos e adicionar uma tela para listagem e criação de pedidos de vendas de peças.

Regra: Tudo que não é moto -> Peças (Há modelos diferentes)

### 4
Envio de NF para email do cliente através de botão na tela "Enviar NF Email" com email faturamento@motochefesp.com.br + email do cliente no pedido (salvar histórico).
(campo email no pedido + auditoria)

### 6
Adicionar campo Origem para identificar de onde o cliente conheceu a loja: [SELECT] Google, Instagram, Facebook e Outros +[TEXT]


### 32
Pre-fillar a loja vinculada ao usuario quando houver no momento da criação de um pedido de vendas mas deixar o SELECT liberado para substituição.

### 36
Adicionar uma seção de "brindes" abaixo da forma de pagamento e considera-la no custo mas não no valor da venda, seria como um desconto porem não computado no valor da moto e sim no valor da venda (Caso não exista valor total da venda no final do pedido incluir)

# Estoque

### 8
Foto do chassi obrigatória quando chassi não for por leitura do QR Code / Codigo de barras.

# Comissão

### 28
Implementar comissão em valor por tipo de peça (1 comissão = 1 codigo peça)
+ comissão em valor para as motos + nivel de desconto considerando valor de desconto + desconto máximo por moto com aprovação atrelado às permissões + tela de aprovações com log
