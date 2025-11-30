1- Quando o pedido VCD123 estará disponivel? - analisando-disponibilidade --pedido ou --grupo
2- O que vai ter de ruptura se eu enviar o pedido VCD123 amanhã? - analisando-disponibilidade --pedido ou --grupo --data
3- Qual pedido eu precisaria alterar a data para enviar o VCD123 amanhã? - analisando-disponibilidade -- pedido ou --grupo --data + buscar pedido que qtd_pedido>qtd_item_falta e qtd_item_falta + qtd_pedido > "VCD123"
4- O que está impactando para enviar os pedidos do Assai de SP completo? - analisando-disponibilidade --pedido ou --grupo e --UF
5- Esses itens que estão dando ruptura no Assai, é por conta de outros pedidos ou falta mesmo? - analisando-disponibilidade --pedido ou --grupo + pegar item_falta pra "pedidos do Assai de SP" analisar se estoque_atual > "pedidos do Assai de sp", se for ">" buscar pedidos que tenham item_falta e trazer pela concentracao "item_falta"/"total_itens"
6- Quais pedidos que não precisam de agendamento é possivel enviar amanhã? - analisando-disponibilidade --pedido ou --grupo --data + contatos_agendamento.forma=='SEM AGENDAMENTO' or CarteiraPrincipal.cnpj_cpf NOT IN contatos_agendamento.cnpj
7- Se embarcar o pedido VCD123 amanhã quando chega no cliente? - --pedido pesquisar nome_cidade(fallback pra municipio se vazio), cod_uf(fallback pra estado se vazio) trazer opções com transportadora + lead time + data(amanhã) + lead_time(dias uteis)
Segue uma função para se definir a data porem já usando a transportadora, a diferença é que trará as transportadoras e o lead time e partirá da data_embarque de embarque, no nosso caso usaremos "D+1":
"
    else:
        # Tenta lead_time
        if embarque.transportadora and embarque.data_embarque:
            cnpj_transp = embarque.transportadora.cnpj
            uf_dest = item_embarque.uf_destino
            cid_dest = item_embarque.cidade_destino

            # ✅ CORREÇÃO: Busca case-insensitive usando UPPER() em ambos os lados
            assoc = (
                CidadeAtendida.query
                .join(Transportadora)
                .join(Cidade, CidadeAtendida.cidade_id == Cidade.id)
                .filter(
                    Transportadora.cnpj == cnpj_transp,
                    CidadeAtendida.uf == uf_dest,
                    func.upper(Cidade.nome) == func.upper(cid_dest)
                )
                .first()
            )
            if assoc and assoc.lead_time and embarque.data_embarque:
                # ✅ CORREÇÃO: Usa dias úteis ao invés de dias corridos
                data_final = adicionar_dias_uteis(embarque.data_embarque, assoc.lead_time)
                "
8- Tem pedido pendente pro Atacadão? consultando_pedidos.py --grupo
9- Falta muito pra matar o pedido do atacadao 183? analisando-disponibilidade --grupo --raz_social_red
10- Tem pedido atrasado pra embarcar? consultando_pedidos.py --expedicao 
11- Os pedidos atrasados são por falta? analisando-disponibilidade --pedido --expedicao
12- Quais pedidos mais estão travando a carteira? analisando-disponibilidade
13- Chegou o palmito? consultando-estoque --produto
14- Tem pedido que ta faltando bonificação? consultando_pedidos.py
15- O que da pra alterar na programação pra matar a ruptura da VF pouch de 150? analisando-programacao
16- Pedido VCD123 ta em separação? consultando_pedidos.py --pedido
17- Falta embarcar muito pessego? consultando_estoque.py --produto
18- Quanto vai sobrar de pessego no estoque? consultando_estoque.py --produto
19- Tem mais pedido pra mandar junto com o Assai lj 123? consultando_pedidos.py --cep --cidade --subrota 
20- O que vai dar falta essa semana? consultando_estoque.py --data



"Quando o pedido VCD123 estará disponível?"
Entidade: Pedido específico (VCD123)
Complexidade: Precisa verificar cada item do pedido vs estoque disponível vs projeção de chegada de estoque
Resposta: Data em que TODOS os itens terão estoque suficiente
"O que vai ter de ruptura se eu enviar o pedido VCD123 amanhã?"
Entidade: Pedido específico
Complexidade: Simular o envio amanhã e ver quais itens ficariam faltando no estoque para outros pedidos/demandas
Resposta: Lista de produtos que entrariam em ruptura
"Qual pedido eu precisaria alterar a data para enviar o VCD123 amanhã?"
Complexidade ALTA: Precisa identificar quais pedidos estão "competindo" pelo mesmo estoque
Raciocínio: Se VCD123 precisa de produto X, e há outros pedidos programados antes usando produto X, qual deles "adiar" liberaria estoque
Resposta: Pedido(s) que se movidos liberam estoque para VCD123
"O que está impactando para enviar os pedidos do Assai de SP completo?"
Entidade: Cliente (Assai) + Filtro (SP) + Condição (completo)
Complexidade: Para cada pedido do Assai de SP, verificar quais itens faltam estoque
Resposta: Gargalos (itens com falta) que impedem envio completo
"Esses itens que estão dando ruptura no Assai, é por conta de outros pedidos ou falta mesmo?"
Complexidade: Distinguir entre falta de estoque absoluta e reservas de outros pedidos
Raciocínio: Analisar se a indisponibilidade é causada por demandas já existentes ou por real escassez de produtos
Resposta: Origem da ruptura - outros pedidos ou falta de estoque
"Quais pedidos que não precisam de agendamento é possível enviar amanhã?"
Filtro: Identificar pedidos sem restrição de agendamento
Critério: Verificar disponibilidade imediata de estoque
Resposta: Relação de pedidos liberados para envio no dia seguinte
"Se embarcar o pedido VCD123 amanhã quando chega no cliente?"
Análise: Calcular tempo de entrega considerando data de expedição
Variáveis: Tempo de trânsito da transportadora e rota específica
Resposta: Previsão da data de recebimento pelo cliente
"Tem pedido pendente pro Atacadão?"
Objetivo: Verificar status de pedidos em aberto para o cliente Atacadão
Ação: Consultar base de dados de pedidos pendentes
Resposta: Confirmação e listagem dos pedidos
"Falta muito pra matar o pedido do Atacadão 183?"
Interpretação: Avaliar completude do pedido
Método: Calcular percentual de itens disponíveis
Resposta: Quantitativo de itens faltantes e representação percentual
"Tem pedido atrasado pra embarcar?"
Critério: Identificar pedidos com data de expedição vencida
Verificação: Comparar data atual com prazo de envio
Resposta: Relação de pedidos em atraso
"Os pedidos atrasados são por falta?"
Investigação: Diagnosticar causa dos atrasos
Foco: Determinar se indisponibilidade de estoque é o principal impedimento
Resposta: Classificação detalhada dos motivos de atraso
"Quais pedidos mais estão travando a carteira?"
Conceito: Identificar pedidos que bloqueiam recursos operacionais
Análise: Avaliar impacto nos estoques e capacidade de atendimento
Complexidade: Mapear pedidos com maior retenção de recursos
"Chegou o palmito?"
Verificação: Entrada recente do produto
Método: Consultar registros de estoque
Resposta: Confirmação e quantitativo
"Tem pedido que tá faltando bonificação?"
Investigação: Identificar pedidos sem condições especiais
Análise: Verificar modelagem do sistema de bonificações
Resposta: Listagem de pedidos sem benefícios associados
"O que dá pra alterar na programação pra matar a ruptura da VF pouch de 150?"
Foco: Produto VF pouch 150
Estratégia: Realocar recursos e ajustar programação
Resposta: Propostas de reorganização de pedidos
"Pedido VCD123 tá em separação?"
Objetivo: Verificar status do pedido
Método: Consulta direta ao sistema
Resposta: Confirmação e detalhamento
"Falta embarcar muito pêssego?"
Verificação: Pendências de embarque do produto
Análise: Avaliar volume de pêssegos não expedidos
Resposta: Quantitativo e situação logística