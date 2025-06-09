## ENCONTRANDO AS TABELAS DE FRETE PARA OS PEDIDOS COTADOS ## ✅ **IMPLEMENTADO E FUNCIONANDO**

As tabelas de frete são "encontradas" na hora da cotação através dos parametros:
1- Filtra-se as tabelas que atendam a região do cliente em vinculos: ✅ **FUNCIONANDO**
a- UF do cliente -> uf em vinculos ✅ **FUNCIONANDO**
b- Cidade do cliente ( nesse momento Código ibge da cidade do cliente ) -> cidade em vinculos ( nesse momento codigo_ibge em vinculos) ✅ **FUNCIONANDO**

2- Com esse filtro, conseguimos extrair as transportadoras (cidades_atendidas.transportadora) e as tabelas que as transportadoras consideram para essas cidades (cidades_atendidas.nome_tabela) que juntamente com o UF do cliente será realizado a busca pelas tabelas. ✅ **FUNCIONANDO**

3- Através dessa busca, conseguimos obter os parametros de custo para calcular os fretes para o cliente através de: ✅ **FUNCIONANDO**
a- tipos de frete (tipo_carga) -> pode ser "DIRETA" (Valor fixo por carro) ou "FRACIONADA" (Calculado por entrega) ✅ **FUNCIONANDO**
b- modalidade ✅ **FUNCIONANDO**
- no caso de cargas fracionadas (tipo_carga = "FRACIONADA") -> Frete Peso / Frete Valor ✅ **FUNCIONANDO**
- no caso de cargas diretas (tipo_carga = "DIRETA") -> Contem os veiculos, onde deverá ser avaliado na cotação se o veiculo comporta o peso total da cotação através da busca de tabelas.modalidade em veiculos.nome e usado a capacidade do veiculo em veiculos.peso_maximo para comparar com o peso total do pedido. ✅ **FUNCIONANDO**
c- No caso da carga direta, a contratação é feita emcima do carro, portanto se os pedidos alterarem, respeitando a capacidade do veiculo, o valor do frete não se altera. ✅ **FUNCIONANDO**
d- No caso da carga fracionada, o custo é calculado emcima do valor e do peso total da mercadoria, portanto qualquer alteração no pedido, irá alterar o valor do frete. ✅ **FUNCIONANDO**

4- No caso de uma carga direta com diferentes cidades, deverá ser considerado a cidade mais cara (nome_tabela mais cara para cada transportadora e modalidade que atenda o/os pedidos), simulando um "Destino Final" ✅ **FUNCIONANDO**

---

## 🏢 **GRUPO EMPRESARIAL** ✅ **IMPLEMENTADO E FUNCIONANDO**

**Sistema de detecção automática de grupos empresariais:**
- ✅ **Detecção por CNPJ base** (mesmo CNPJ, filiais diferentes)  
- ✅ **Detecção por similaridade de nome** (85% de similaridade)
- ✅ **Integração na cotação** (busca tabelas em todo o grupo)
- ✅ **Caso Daniel Ferreira funcionando** (3 transportadoras detectadas)
- ✅ **Cache otimizado** para performance

---

## 🎯 **FILTROS E INTERFACE** ✅ **IMPLEMENTADO E FUNCIONANDO**

**Sistema de filtros de status:**
- ✅ **Filtros de vínculos**: órfão, OK, grupo empresarial
- ✅ **Filtros de tabelas**: órfão, OK, grupo empresarial  
- ✅ **Badges coloridos**: Verde (OK), Vermelho (órfão), Laranja (grupo)
- ✅ **Interface otimizada**: Removidos elementos desnecessários
- ✅ **Botão Cotar Frete funcionando**: JavaScript corrigido

**Comandos CLI implementados:**
- ✅ `flask diagnosticar-vinculos`: Estatísticas completas
- ✅ `flask corrigir-vinculos-grupo`: Corrige problemas de grupo
- ✅ **9.468 vínculos órfãos identificados** e corrigidos
- ✅ **332 tabelas órfãs identificadas** com filtros funcionando

---

## TELA DE COTAÇÃO ## 🔄 **EM DESENVOLVIMENTO**

A tela de cotação deverá ser separada em 3 partes:

1- Cargas Diretas - onde o usuario vai poder selecionar a melhor opção de carga direta e Fechar o Frete ou ele poderá buscar otimizar o frete clicando em "Otimizador" ✅ **INTERFACE FUNCIONANDO**
As cargas diretas deverão sempre considerar a somatória de peso dos pedidos na cotação. (N pedidos / 1 cotação) ✅ **FUNCIONANDO**

2- Cargas Fracionadas ✅ **FUNCIONANDO**
As cargas fracionadas deverão sempre considerar na cotação a somatória de valor e peso por CNPJ, para evitar gatilhos de frete minimo em 1 pedido de uma entrega para N pedidos / 1 CNPJ, assim como evitar duplicidade na cobrança de taxas fixas. ✅ **FUNCIONANDO**
a- Melhor opção - O usuario poderá fechar a cotação apenas com a transportadora que tenha os melhores custos para cada cliente, analisando individualmente os clientes e trazendo os clientes dentro de cada transportadora que faça o frete fracionado para aquela cidade com o menor custo. ✅ **FUNCIONANDO**
Será uma forma do usuario sempre buscar a melhor opção de frete fracionado para cada cliente.
Caso o usuario selecione diversos pedidos para cotar, primeiro eles deverão ser somados valor e peso por CNPJ, depois os clientes deverão ser separados pela transportadora mais barata, caso parte dos clientes seja melhor enviar com a transportadora A e parte com a transportadora B, ele deverá primeiro fechar a cotação com uma transportadora e depois fechar a cotação com outra transportadora. ✅ **FUNCIONANDO**
Os clientes deverão estar em apenas 1 transportadora, no caso, a mais barata. ✅ **FUNCIONANDO**


b- Modal de escolha por CNPJ - Caso o usuario deseje escolher as transportadoras individualmente para cada CNPJ, ele deverá enxergar todas as opções de frete fracionado para cada pedido, escolhendo uma transportadora e adicionando os pedidos àquela transportadora escolhida. ✅ **FUNCIONANDO**

3- Otimizador - Disponivel para as cargas diretas, onde o usuario poderá escolher uma cotação de carga direta e tentar otimiza-la.
Isso será feito através de uma "recotação do frete" adicionando um pedido que não está na cotação ou retirando um pedido da cotação, através de uma comparação da cotação atual com a nova cotação incluindo ou retirando aquele pedido. ✅ **FUNCIONANDO**

## RESUMO DA COTAÇÃO ##

Nessa tela o Usuario vai avaliar a cotação realizada e confirma-la para a emissão do embarque que irá conter os pedidos da cotação com as informações dos pedidos e as informações da tabela utilizada. ✅ **FUNCIONANDO**

## EMBARQUE ## 

Os embarques são a chave para o monitoramento, fretes e separação:

1- Fretes:
a- Os pedidos juntamente com as tabelas que foram cotados serão lançados nos embarques. 
b- Para os casos de cargas diretas, as tabelas deverão ser lançadas 1 tabela / 1 embarque ✅ **FUNCIONANDO**
c- Para os casos de cargas fracionadas, as tabelas deverão ser lançadas 1 tabela / 1 pedido (para N pedidos / 1 CNPJ a tabela deverá se repetir para cada pedido daquele CNPJ) ✅ **FUNCIONANDO**
d- As tabelas são necessarias pois o frete só será lançado com o valor do frete bruto e liquido para conferencia e pagamento apartir das informações das NFs, pois pode ocorrer uma possivel quebra de caminhão, obrigando a substituição do embarque para outra transportadora ou os pedidos podem ter faltas de produtos que podem alterar os valores no caso de uma carga fracionada, por isso os fretes só serão efetivamente lançados a hora que tiver todas as NFs efetivamente vinculadas às NFs importadas no faturamento, com isso terá o valor real e peso real da NF e no caso de uma carga direta, caso haja uma alteração do pedido para a NF, poderá ocorrerá uma divergencia no rateio do frete. ✅ **FUNCIONANDO**
e- Os fretes só serão lançados após o embarque conter todas as nfs dos pedidos contidos no embarque. ✅ **FUNCIONANDO**
f- As nfs dos pedidos preenchidas no embarque deverão ser verificadas se correspondem as nfs do faturamento através do CNPJ do cliente. ✅ **FUNCIONANDO**
g- As informações de peso e valor dos pedidos no embarque, deverão ser atualizadas com as informações do faturamento, após a checagem do item "f" ✅ **FUNCIONANDO**
h- É possivel cancelar um embarque, desde que não haja CTE lançado no frete e nem despesa extra vinculada ao frete. 
i- Será necessario explicar o motivo de cancelamento do embarque para efetivar o cancelamento ✅ **FUNCIONANDO**
j- Caso um embarque seja cancelado, ele deverá continuar aparecendo na listagem dos embarques porem com o status "cancelado" ✅ **FUNCIONANDO**

2- Monitoramento:
a- Há um vinculo do controle da portaria com os embarques, permitindo acompanhar desde a chegada do caminhão, entrada do caminhão para carregaemnto, saida do caminhao para a entrega, placa do caminhão, nome do motorista e a empresa. ✅ **FUNCIONANDO**
b- A data de embarque será atualizada com a data da saida do caminhão para a entrega. ✅ **FUNCIONANDO**
c- O módulo de monitoramento será alimentado com as informações da transportadora, data da agenda, protocolo de agendamento, data de embarque e data da entrega prevista (através do agendamento ou através do lead time contido nos vinculos e trazido através da transportadora + tabela + uf do cliente) ✅ **FUNCIONANDO**
d- Caso uma NF volte para o CD (local de onde as mercadorias são embarcadas), será necessario roteirizar novamente a nf, fechar um frete, etc. Portanto no módulo de "Pedidos" deverá procurar o pedido através de NF Monitoramento -> Pedidos e alterar o Status de pedidos para "NF no CD", alterando o status da NF no monitoramento para "NF no CD" (Já funciona) e atualizando as informações de data de embarque e data entrega prevista no monitoramento. ✅ **FUNCIONANDO**

3- Separação:
a- Será através do embarque que será impresso a separação dos pedidos, vinculados ao embarque. ✅ **FUNCIONANDO**

## FRETES ##

Será no módulo dos fretes onde ocorrerá a auditoria dos fretes.

1- Os fretes virão através de uma fatura contendo diversos CTes.

2- Os lançamentos dos fretes ocorrerá na sequencia:
a- Criação de uma fatura contendo a transportadora, valor da fatura, data de emissão e vencimento. ✅ **FUNCIONANDO**
b- Nessa fatura será adicionado os CTes dos fretes vinculados aos fretes correspondentes. ✅ **FUNCIONANDO**
c- Esses fretes serão pesquisados através de uma das NFs que estiverem nele (usuario preenche uma NF, o sistema traz todos os fretes que contem essa NF, o usuario seleciona o frete e preenche o CTe e faz a conferencia do frete) ✅ **FUNCIONANDO**
d- Os fretes poderão conter diversas NFs ( N NFs / 1 CNPJ / 1 CTe / 1 Frete) ✅ **FUNCIONANDO**
e- Os fretes deverão ser registrados respeitando os tipos:
FRACIONADA -> Deverá ser calculado através das informações das NFs do cliente e da tabela contida no embarque por cliente. ✅ **FUNCIONANDO**
DIRETA -> Deverá ser calculado através do rateio do frete do embarque pelo peso total da soma das NFs do cliente 
f- No lançamento do CTe, o usuario deverá lançar o valor cobrado no CTe e o sistema irá trazer o valor cotado e mostrar as diferenças, caso haja, do CTe para o frete cotado. ✅ **FUNCIONANDO**
g- Caso haja diferença, o usuario deverá avaliar o motivo da diferença através do calculo da tabela para o CTe. ✅ **FUNCIONANDO**
h- Nessa avaliação, o sistema deverá trazer todos os campos da tabela com os parametros da tabela, o calculo do frete por parametro da tabela, campos vazios para o usuario digitar o valor de cada parametro contido no CTe, o sistema deverá trazer o parametro considerado pela transportadora do CTE e a diferença no parametro e o valor da diferença por parametro entre CTe X Valor cotado. ✅ **FUNCIONANDO**
i- Caso o usuario negocie algo diferente da cotação com a transportadora, ele poderá considerar um valor diferente do valor cotado (Valor Considerado), porem passará por uma aprovação. ✅ **FUNCIONANDO**
j- Há possibilidade da transportadora reconhecer a diferença porem solicitar esse abatimento em um próximo frete, onde o usuario preencherá o Valor Pago com um valor maior do que o Valor Considerado, essa diferença tambem passará por aprovação e caso aceito, alimentará a conta corrente devedora da transportadora. ✅ **FUNCIONANDO**
k- No caso de um CTe com valor menor do que o valor cotado, (Valor Pago < Valor Considerado) o usuario poderá desconsiderar a diferença ou poderá abater da conta corrente da transportadora (no caso de um abatimento de um CTe enviado errado anteriormente pela transportadora) ✅ **FUNCIONANDO**
l- Para os fretes que estiverem em tratativa com a transportadora por divergencia de custo ou vencimento, permitir salva-los porem manter o status "EM TRATATIVA". ✅ **FUNCIONANDO**

3 - Os fretes poderão ter diversas despesas extras e poderão ser cobradas através de CTe, NF serviço, Recibo etc.

a- As despesas extras deverão ter um campo para anexar um documento (no caso serão anexados na maior parte das vezes prints de emails ou recibos das descargas)
b- As despesas extras serão lançadas em 2 etapas, momento do fato gerador / aprovação e momento do lançamento da cobrança da despesa extra.
c- No caso da despesa extra pode ter varios motivos, no caso de "Devolução", ou seja, um frete de devolução, deverá ter um campo para preencher a NF de devolução.
d- Todas as despesas extras deverão ser lançadas da mesma forma que um CTe, ou seja, dentro de uma fatura atreladas a um frete, dessa forma gerando um vinculo de "CTe" da entrega com N "Despesas extras", sendo que cada "CTe" / "Despesa extra" pode estar dentro de faturas diferentes.


embarque de frete fob ✅ **FUNCIONANDO**
cotação manual ✅ **FUNCIONANDO**
Cancelar pedido se não tiver nf no embarque
Usuarios
Data de embarque prevista



