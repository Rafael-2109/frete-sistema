<objetivo>
Criar um módulo separado para controle de compras, venda, recebimento e estoque das motos nas lojas.
</objetivo>

<regras>
- Módulo totalmente separado dos dados dos outros módulos (Motochefe-distribuidora, CarVia).
- Motivo: HORA é pessoa jurídica distinta, e há risco operacional de misturar estoque HORA com motos da Motochefe-distribuidora ou motos transportadas pela CarVia.
- Isolamento técnico: schema PostgreSQL separado no mesmo banco do sistema atual.
- Stack: Flask + PostgreSQL (mesmo do frete_sistema).
</regras>

<contexto>
Além de distribuir motos elétricas (módulo Motochefe) e transportar motos elétricas e outros produtos (CarVia), possuímos lojas da marca Motochefe operadas pela HORA.

Preciso criar um fluxo de controle de estoque desde o pedido de compras até a venda ao consumidor final, com rastreabilidade unitária por chassi.

Escopo desta fase: estoque (compra → recebimento → baixa por venda).
Fase futura (considerar no modelo, não implementar agora): controle financeiro (pagamento ao fabricante, recebimento da venda, conciliação).
</contexto>

<fluxo_processo_atual>
1. Os pedidos são enviados por Excel em grupo de WhatsApp contendo:

Cabeçalho:
- CNPJ
- Número do pedido

Corpo (por moto):
- Modelo
- Cor
- Chassi
- Preço de compra

2. No grupo de WhatsApp, a pessoa do faturamento da Motochefe (fabricante — fora do nosso controle) define por qual empresa será faturado e envia 1 ou mais NFs para aquele pedido.

Empresas de faturamento: B2B, Laiouns, Q.P.A.
Todas com parser pronto que já extrai modelo, preço, chassi + regex para padronização dos modelos.

3. A partir do pedido, as NFs deverão ser confrontadas para identificar:
- Motos em pedidos não faturadas
- Motos em NF sem pedido

4. Motos faturadas deverão ser recebidas pelas lojas (atualmente Tatuapé, Bragança, Praia Grande — expansível).

5. A loja faz a conferência das motos pela leitura do QR Code (que contém o chassi) + foto.

6. A conferência tem como objetivo identificar divergência de chassi, modelo, cor, ou moto faltando.

7. Após motos lançadas no estoque de cada loja e divergências identificadas (Pedido vs. NF vs. Recebimento), controlar o estoque de cada loja através de:
- Baixa do estoque por venda
- Lançamento dos pedidos e NFs de venda

Venda ao consumidor final:
- Sempre pessoa física
- Pagamento por PIX, cartão de crédito ou, raramente, dinheiro
- NF emitida pela própria loja HORA
</fluxo_processo_atual>

<fora_de_escopo_desta_analise>
- Visão computacional para identificar modelo e cor pela foto (decisão estratégica separada; começar com QR Code + foto para auditoria humana)
- Implementação do módulo financeiro (Fase 2)
</fora_de_escopo_desta_analise>