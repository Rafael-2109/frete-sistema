# Briefing Nacom Goya — Contexto para Extracao de Conhecimento

## A. Quem eh a Nacom Goya

Industria de alimentos (conservas, molhos, oleos) com faturamento mensal de ~R$ 16 milhoes e volume de ~1.000.000 kg/mes. Opera com planta fabril propria (fracionamento de conservas importadas em bombonas), galpoes subcontratados (La Famiglia — molhos e oleos) e CD/armazem com capacidade de 4.000 pallets e expedicao maxima de 500 pallets/dia.

Marcas proprias: Campo Belo, La Famiglia, St Isabel, Casablanca, Dom Gameiro.

Clientes concentrados em atacarejo: Atacadao (50% do faturamento, ~R$ 8MM/mes), Assai (13%), Gomes da Costa (4%, industria), Mateus (3%), Dia a Dia (2%), Tenda (2%). Atacadao domina — quando Atacadao atrasa, a empresa sente.

Estrutura comercial: 4 gestores (Junior = key accounts/Atacadao/Assai SP; Miler = Brasil exceto SP; Fernando = industrias; Denise = vendas internas). ~500 pedidos/mes.

## B. Cadeia de Valor

Fluxo completo de um pedido:

Pedido (CarteiraPrincipal) -> Separacao (picking do estoque) -> Embarque (carregamento no caminhao) -> Faturamento (emissao de NF) -> Frete (transporte) -> Entrega (confirmacao no destino) -> Financeiro (cobranca e reconciliacao)

Tabelas-chave: carteira_principal -> separacao -> embarque_itens/embarques -> faturamento_produto -> entregas_monitoradas -> fretes -> contas_a_receber

Campos de ligacao: num_pedido, separacao_lote_id, numero_nf, embarque_id. O campo `sincronizado_nf` (boolean) marca a fronteira pre/pos-faturamento.

## C. Sistemas

| Sistema | Papel | Escopo |
|---------|-------|--------|
| Sistema de Fretes | Sistema interno (este sistema). Gestao de pedidos, separacao, embarque, frete, financeiro, producao | Core |
| Odoo | ERP da Nacom Goya. Contabilidade, fiscal (NF-e), compras (POs), pagamentos, extratos bancarios | ERP principal |
| SSW | ERP da CarVia (transportadora subcontratada). Cadastros, comissoes, CTe, romaneio, faturamento | CarVia |
| Linx/Microvix | Sistema da Motochefe (modulo ainda nao ativado no sistema de fretes) | Futuro |
| CarVia | Modulo de frete subcontratado (inbound). Operacoes, subcontratos, cotacoes, faturas | Logistica inbound |
| Portal Atacadao | Hodie Booking (hodiebooking.com.br). Agendamento de entregas, consulta de saldo, impressao de pedidos | Atacadao |

## D. Dominios

Dominios de conhecimento da organizacao (use texto livre — se a conversa revelar dominio nao listado, use-o):

- **comercial**: Pedidos, clientes, precos, bonificacao, gestores, vendedores
- **logistica**: Embarques, transportadoras, frete, rotas, lead time, CTe, devolucao
- **recebimento**: Compras, NF de entrada, match NF x PO, recebimento fisico, fornecedores
- **financeiro**: Contas a pagar/receber, extratos, reconciliacao, titulos, boletos, Odoo contabil
- **producao**: Programacao, recursos, insumos, materia-prima, capacidade de linhas
- **estoque**: Movimentacao, saldo, projecao, ruptura, disponibilidade
- **expedicao**: Separacao, palletizacao, agendamento, expedicao, status de embarque
- **carvia**: Frete subcontratado, operacoes CarVia, SSW, subcontratos, faturas transportadora
- **fiscal**: NF-e, CFOP, ICMS, IPI, pendencias fiscais, perfil fiscal
- **integracao**: Odoo, SSW, Linx, sincronizacao entre sistemas, jobs automaticos
- **seguranca**: Vulnerabilidades de colaboradores, senhas, DNS, email breaches
- **portal**: Portal Atacadao, agendamento, saldo, pedidos web

## E. Gargalos Recorrentes

1. **Agendas** (gargalo #1): Cliente demora para aprovar agenda de entrega
2. **Materia-prima** (gargalo #2): MP importada com lead time longo e imprevisivel
3. **Producao** (gargalo #3): Capacidade limitada de linhas de producao
4. **Inconsistencia entre sistemas**: Dados divergentes entre Sistema de Fretes, Odoo, SSW
5. **Campos vazios/errados**: Endereco incompleto, CNPJ divergente, dados nao populados
6. **Regras de cliente**: Cada rede tem exigencias (agendamento, pedido completo, horario)

## F. Vocabulario

| Termo | Significado |
|-------|-------------|
| Matar pedido | Completar 100% do pedido (faturar tudo) |
| Ruptura | Falta de estoque para atender demanda |
| Falta absoluta | Estoque < demanda (nem sem concorrencia atende) |
| Falta relativa | Estoque comprometido com outros pedidos |
| RED | Redespacho via Sao Paulo |
| FOB / Coleta | Cliente retira no CD |
| CIF | Nacom entrega no cliente |
| Completude | % do pedido original ja faturado |
| Concentracao | Quanto um item representa do valor total do pedido |
| Bonificacao | Itens sem cobranca (promocao), enviados junto com venda |
| sincronizado_nf | Flag que marca separacao como faturada (True = ja virou NF) |
| Travando a carteira | Pedidos que consomem estoque impedindo outros |
| D-2, D-1, D0 | Dias relativos a data de entrega |
| Parcial | Enviar apenas parte do pedido (nem todos os itens ou quantidades) |
| Lote (separacao_lote_id) | Identificador unico de uma separacao de pedidos |
| PO | Purchase Order (pedido de compra no Odoo) |
| CTe | Conhecimento de Transporte Eletronico |
| De-para | Mapeamento entre codigos/nomes de sistemas diferentes |
