Preciso iniciar um projeto que consiste em:
<processo>
<registro_monitoramento>
1- Sinalização na finalização da entrega no monitoramento se houve devolução (boolean)
2- Registro da NFD que ocorreu no ato da entrega pelo monitoramento com motivo da devolução e data de registro na própria entrega e tambem em uma tabela de NFDevolucao, posteriormente essa NFD será vinculada a uma NFD importada do DFe do Odoo <vinculacao_dfe></vinculacao_dfe>
</registro_monitoramento>

<tela_equipe_ocorrencias>
4- Deverá haver uma tabela e painel de registro com tratativas de devolução <tratativa_comercial></tratativa_comercial> utilizado pelo comercial para tratar as informações relacionadas a devolução efetivamente e pela logistica referente as tratativas de Contratacao do frete retorno / monitoramento da localização da devolução (as vezes a transportadora que faz a tentativa de entrega que gerou a devolução tem que deixar a mercadoria no galpão de outra transportadora para realizar um retrabalho ou para programarmos o retorno) / descarte da devolução.

<tratativa_logistica>
 A equipe logistica realizará a contratação de frete (por enquanto a cotacao será realizada manualmente) e fará o monitoramento da devolução até a chegada na empresa se a destinação for definida "retorno" ou deverá realizar um controle de descarte das devoluções que não valem a pena voltar para a empresa que no caso será definido "descarte".
Permitir anexar N emails referente a contratação / descarte.
</tratativa_logistica>

<tratativa_comercial>
O comercial será que preencherá as seguintes informações:
- Categoria da devolução (Departamento na empresa responsavel pela devolução)
- Subcategoria da devolução (motivo da devolução)[pedido cancelado, itens danificados, vazamento...]
- Descrição (detalhamento da devolução)
- Responsavel do departamento pela resolução. 
- Desfecho da ocorrencia
- Status [RESOLVIDO, PENDENTE]
Autorizado por (em alguns casos precisamos registrar quem autorizou a devolução, mas não são todos os casos.)
- Resolvido por (funcionarios envolvidos na solução)
- Origem da devolução (registrado após solucionar e para KPI) [CLIENTE, LOGISTICA, TRANSPORTADORA, REPRESENTANTE, QUALIDADE...]
</tratativa_comercial>

5- Registro da entrada da devolução com contagem e inspeção.
6- Gravação da devolução no Odoo seguindo processo semelhante ao de lançamento de frete.
</tela_equipe_ocorrencias>

<frete_devolucao>
7- O registro da cotação de devolução será realizado em uma tabela de FreteDevolucao com FK para DespesaExtra de frete no Frete da NF de venda.
Pensei nessa forma pois precisava pensar em um jeito de registrar os fretes de devolução mais antigos, momento que o sistema ainda não estava em operação e consequentemente não havia frete de entrega.
8- Ao vincular fia FK / criar a DespesaExtra, ela deverá herdar as informações do FreteDevolucao.
</frete_devolucao>

<vinculacao_dfe>
9- A vinculação com o DFE ocorrerá através do vinculo entre CNPJ da nf de venda + NFD preenchida pelo monitoramento.
10- 1 NF de venda poderá referenciar N NF de venda.
11- Caso não encontre a NFD no monitoramento para fazer o match, a equipe de ocorrencias poderá verificar a NFD em busca da NF de venda através da relação das NF de venda com o mesmo CNPJ que foram emitida ANTES da NFD.
12- Alem disso, a NFD importada do Odoo, em muitos casos virá com o código do produto do cliente, no caso precisaremos de um "De-Para" contendo código do cliente, nosso_codigo, fator de conversão (alguns clientes devolvem em qtd unitaria, alguns devolvem em caixa) e prefixo do CNPJ.
Alguns clientes utilizam o mesmo código para caixa e para unitario, a diferenciação está na unidade de medida na NF (se não houver um padrão nas NFs ou no XML, acho que o melhor é utilizar o Claude Haiku 4.5 para ver a NF e identificar a unidade de medida).
Caso os produtos não possuam "De-Para" cadastrado, acho que podemos utilizar o Haiku 4.5 para identificar através do script de resolver_entidades ou podemos usar uma outra estratégia que avaliar ser eficaz.
13- Através dos produtos e qtds identificadas, conseguiremos obter o peso das mercadorias da NF e esse peso é o que será usado na cotação de frete e registrado em FreteDevolucao.
</vinculacao_dfe>

<contagem_inspecao>
14- Ao chegar a devolução, a logistica deverá realizar a contagem das quantidades recebidas em colunas [CAIXAS CONFORME, UNIDADES CONFORME, CAIXAS NÃO CONFORME, UNIDADES NÃO CONFORME] e o sistema deverá calcular [CAIXAS FALTANTES, UNIDADES FALTANTES]
15- Tambem deverá permitir registrar comentarios no recebimento da NFD e no recebimento das linhas da NFD.
16- Permita tambem anexar N fotos na contagem e inspecao.
</contagem_inspecao>

<local_armazenamento_anexos>
Utilize o S3 implementado em app/utils/file_storage.py e pode verificar como exemplo a implementação de anexar os emails em app/fretes/email_routes.py
</local_armazenamento_anexos>

Pela complexidade da implementação e pela especificação, preciso que NÃO ASSUMA NADA.
Caso possua duvidas é obrigatório perguntar.
Crie um projeto para implementarmos a solicitação documentando toda especificação que enviei acima.

