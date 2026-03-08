 A consulta do saldo vai mto de encontro ao processo de realizar o agendamento em lote,   
pois a planilha exportada com o saldo é a mesma utilizada para preencher a qtd desejada    
para agendar em lote.                                                                      
Saldo:                                                                                     
1- URL = https://atacadao.hodiebooking.com.br/relatorio/planilhaPedidos                    
2- Abrir filtros = body > div.wrapper > div.content-wrapper > div.listagem-vue >           
div.filtros > div > a > div > div:nth-child(1) > h4 > i                                    
ou                                                                                         
body > div.wrapper > div.content-wrapper > div.listagem-vue > div.filtros > div > a > div  
> div.col-xs-3.pull-right.text-right > h4 > i                                              
3- Limpar as datas de angendamento = #filtros-collapse > div.filtros-body > div >          
div.col-md-3.bootstrap-daterangepicker > div > span:nth-child(5) > button                  
4- Aplicar Filtros = #enviarFiltros                                                        
5- Exportar par CSV = #exportarExcel                                                       
6- Colunas do CSV c/ significado:                                                          
A- Nr. da carga = Numero sequencial para N cargas da mesma filial (1 por agendamento       
solicitado, repetir quando N produtos = 1 agenda)                                          
B- CNPJ do fornecedor = Utilizar para filtrar os pedidos a serem agendados, após           
utiliza-la, preencher em todos com "61.724.241/0003-30"                                    
C e D - Manter (Coluna C se refere a filial, Coluna D se refere ao pedido_cliente, util    
para verificar saldo desse pedido no sistema)                                              
E- Inutil, remove-la (Numero do pedido que não utilizamos)                                 
F- Código EAN dos produtos = para conseguir identificar, precisaremos incluir em           
CadastroPalletizacao essa coluna e buscar esses dados no Odoo sempre que criar um produto  
pela importação em excel ou por qualquer outra maneira + sempre que atualizar algum        
produto (Na planilha do Atacadao, o formato vem {="17898075642344"} com o "=" e as ")      
G- Inutil (Qtd total do pedido)                                                            
H- Saldo disponivel para agendamento (Resolve a consulta de saldo com filial + produto)    
I e J - Data solicitada para agendamento                                                   
K- Codigo do veiculo = Aqueles numero até 7 que temos registrado no json do Atacadao e na  
função do portal (7 Carreta, etc)                                                          
                                                                                           
Agendamento em lote:                                                                       
1- Utilizamos o conteudo dessa planilha removendo as colunas E e G                         
2- Preenchemos:                                                                            
Coluna A com numero sequencial por agendamento                                             
Coluna B com CNPJ do CD (61.724.241/0003-30)                                               
Coluna D eu copio e colo valores para remover (=""), veja a melhor estrategia para fazer   
isso                                                                                       
Coluna F preencho com a qtd que vou realizar essa agenda (é possivel splitar 1 linha em N  
agendas, exemplo 1 linha contem 10.000 caixas, eu splito em 10 agendas de 1.000 caixas     
copiando a linha e colando 10 vezes com numero de 1 a 10 na coluna A e 1.000 na coluna F)  
Colunas G e H eu utilizo a data que quero agendar                                          
Coluna I Preencho com o tipo do veiculo                                                    
3- Acesso https://atacadao.hodiebooking.com.br/cargas-planilha                             
4- Baixo a planilha modelo em body > div.wrapper > div.content-wrapper > div.content > div 
 > div.planilha-container > div.instrucoes-header > a.btn.btn-primary.pull-right           
Se preferir pra identificar:                                                               
<a href="https://atacadao.hodiebooking.com.br/cargas-planilha/download_modelo?u=2026030810 
381766" target="_blank" class="btn btn-primary pull-right" style="margin-left:0px;">       
                        <i class="fas fa-download"></i> Baixar modelo da planilha          
           </a>                                                                            
5- Esses dados "curados" ou "trabalhados" eu copio da linha 2 até o final e colo na linha  
2 dessa planilha                                                                           
Com isso temos a planilha que seja feito upload para agendamento em lote.                  
6- Clico aqui para buscar a planilha no meu PC - #uploadForm > div > span >                
button.btn.btn-primary.inputfile-browser                                                   
7- Clico em #enviar                                                                        
8- Com isso o portal vai processar a planilha e trazer em uma tela todos as colunas que    
são exigidss para agendar e na frente um campo select com as colunas da minha planilha     
(usando a planilha modelo esses campos se preenchem automaticamente)(Esse processo demora  
proporcionalmente a qtd de linhas a serem agendadas, portanto pode demorar para aparecer   
essa comparação de colunas)                                                                
9 - Clico em body > div.wrapper > div.content-wrapper > div.content > div >                
div:nth-child(3) > div > button.btn.btn-primary.pull-right                                 
Essa etapa tambem demora proporcionalmente a qtd de agendas a serem realizadas.            
10 - Com isso é exibida uma tela de analise do que foi solicitado para agendar e do que    
está apto para agendar.                                                                    
11- Com isso poderá ser exibida alguma linha com Inconsistencia, impossibilitando de       
prosseguir ou caso nenhuma linha esteja inconsistente é possivel Agendar. (As              
inconsistencias podem ser por diversos motivos)(A linha traz todos os campos da planilha   
que foi uploadada para poder identificar qual linha possui problema)                       
<linha_com_inconsistencia>                                                                 
<tr>                                                                                       
                                <td class="bg-danger">Inconsistente                        
                                                                <br>                       
                                <p class="text-danger"><i>                                 
                                 Quantidade solicitada do item 17908152302327 ,(45) é      
maior do que o saldo (0)<br>                                 </i></p>                      
                                                                </td>                      
                                                                                           
                                <td class="bg-danger">1</td>                               
                                <td class="bg-danger">183</td>                             
                                <td class="bg-danger">23/03/2026</td>                      
                                <td class="bg-danger">23/03/2026</td>                      
                                <td class="bg-danger">61.724.241/0003-30 - NACOM GOYA IND  
E COMERCIO DE ALIM LTDA</td>                                                               
                                <td class="bg-danger">295330 / 457650</td>                 
                                <td class="bg-danger">7706 / 17908152302327</td>           
                                <td class="bg-danger">45</td>                              
                                <td class="bg-danger">7 - Carreta-Baú</td>                 
                                                            </tr>                          
</linha_com_inconsistencia>                                                                
<linha_valida>                                                                             
<tr>                                                                                       
                                <td class="bg-white">Válido                                
                                                                </td>                      
                                                                                           
                                <td class="bg-white">1</td>                                
                                <td class="bg-white">183</td>                              
                                <td class="bg-white">23/03/2026</td>                       
                                <td class="bg-white">23/03/2026</td>                       
                                <td class="bg-white">61.724.241/0003-30 - NACOM GOYA IND E 
 COMERCIO DE ALIM LTDA</td>                                                                
                                <td class="bg-white">294748 / 389186</td>                  
                                <td class="bg-white">87854 / 17908152301405</td>           
                                <td class="bg-white">210</td>                              
                                <td class="bg-white">7 - Carreta-Baú</td>                  
                                                            </tr>                          
</linha_valida>                                                                            
Há exibição dessa linha quando há algum erro (confirmação alternativa)                     
<i>Acerte os itens com crítica e suba novamente a planilha, só serão importadas planilhas  
sem críticas..</i>                                                                         
12- Estando tudo certo, exibirá esse botão: #salvar2                                       
13- Ao salvar exibirá esse "mini modal": <div class="modal-content">                       
      <div class="modal-header">                                                           
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span  
aria-hidden="true">×</span></button>                                                       
        <h4 class="modal-title">Alerta</h4>                                                
      </div>                                                                               
      <div class="modal-body">                                                             
        <div class="row">                                                                  
          <div class="col-md-12 form-group">                                               
            <label style="margin-bottom: 20px" class="control-label msg">Registro criado   
com sucesso<div style="margin-top: 30px;" class="rom"><div class="col-sm-6"><a             
href="/cargas?controle=b086065974ce3f67b8b686aa5f100408" class="btn btn-primary">Listar    
cargas</a></div><div class="col-sm-6"><a href="cargas-planilha" class="btn                 
btn-primary">Nova planilha</a></div></div></label>                                         
          </div>                                                                           
        </div>                                                                             
      </div>                                                                               
      <div class="modal-footer" id="footerModalAlerta" name="footerModalAlerta">           
        <div class="row">                                                                  
          <div class="col-md-12">                                                          
            <button type="button" class="btn btn-primary ok">OK</button>                   
          </div>                                                                           
        </div>                                                                             
      </div>                                                                               
    </div>                                                                                 
14- Clicar em OK - #footerModalAlerta > div > div > button                                 
FIM!                                                                                       
                                                                                           
Gothcas:                                                                                   
1- O Atacadão na maioria das lojas não checa se os produtos agendados são os produtos que  
estaremos entregando, com isso para garantir disponibilidade de entrega, em muitos casos   
eu pego 1 pedido, programo 10 entregas mas realizo 40 agendas para que caso alguma agenda  
seja perdida, eu ainda tenho disponibilidade de entrega-la em outro dia.                   
2- As agendas das filiais 111 e 183 (São 2 CD em SP), que são as lojas que mais compram,   
faço com bastante frquencia esse esquema de multiplicar as agendas principalmente nessas   
filiais mas eu realizo elas com pelo aproximadamente 7 pallets para não chamar a atenção   
mas tambem para não consumir tantos itens e permitir que ainda fique com bastante          
disponibilidade para agendar.                                                              
3- Em São Paulo é a região que mais contem lojas do Atacadão, portanto quando eu realizo   
as agendas, frequentemente eu divido a qtd disponivel por 3 ou por 4 (arredondando para    
cima para não ficar decimal).                                                              
4- Em muitos casos quando eu perco a agenda, eu apenas vejo se se há outro agendamento     
futuro e o utilizo, ou seja, em varios casos eu agendo para ter uma janela de recebimento  
e a vinculo em um pedido, se eu perco eu pego outra janela.    