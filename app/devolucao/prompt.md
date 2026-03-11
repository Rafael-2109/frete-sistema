Preciso corrigir alguns pontos na tela de devolucao/ocorrencias:

  <exibicao_raz_social_red>
  1- aumentar o truncamento da razao social e região (exibida abaixo do CNPJ)
  2- Incluir a razao social reduzida acima da razao social e alterar a evidencia
  da razao social para razao social reduzida, faça isso tambem no detalhe de 1
  devolucao (devolucao/ocorrencias/###)
  </exibicao_raz_social_red>

  <aba_descarte>
  1- Exibir o nosso código com descição + manter código do cliente com descrição.
  2- Corrigir conversão da unidade de medida (QTD DESCARTE (UN) está exibindo
  igual QTD DESCARTE (CX)) utilizando JS dinamico, ou seja, altera um atualiza o
  outro.
  3- Botão Importar apenas exibe "Arquivo não importado".
  </aba_descarte>
   
  <anexo>
  1- Permita N importações por vez, replicando a "Descricao".
  2- Na listagem dos anexos, inverta a exibicao do nome do arquivo com a descricao
  (Eviencia na Descricao).
  3- Disponibilize um botão "Baixar Todos" que deverá realizar Download de todos
  os anexos daquela NF.
  4- Tipo do documento deverá ser identificado automaticamente e não mais          
  escolhido por usuario mas deverá manter a gravação de "Tipo". 
  5- Exiba uma tabela enxuta com os titpos de documentos aceitos. 
  </anexo>                                                                      
                                                                                
  <reversao>                                                                    
  1- Na exibição da listagem e no detalhe, exibir a NC ao invés de NF (A nf já é
  referenciada em "Ref: NF ###")
  </reversao>                                                           
                                                                        
  <resolucao>                                                           
  Vejo que as devoluções possuem datas de resolução diferente da data de
  lançamento, preciso que investigue e garanta consistencia.          
  Veja o caso abaixo no Render e no Odoo como a resolução possui datas
  divergentes:               
  <render>                   
  /devolucao/ocorrencias/5004                                                     
  </render>                                                                       
  <odoo>                                                                          
  DFe: https://odoo.nacomgoya.com.br/web#id=38076&model=l10n_br_ciel_it_account.df
  e&view_type=form&cids=4-1-3                                                     
  Picking: https://odoo.nacomgoya.com.br/web#id=304308&cids=4-1-3&action=365&activ
  e_id=36681&model=stock.picking&view_type=form                                   
  Fatura: https://odoo.nacomgoya.com.br/web#id=507870&cids=4-1-3&action=245&active
  _id=36681&model=account.move&view_type=form
  </odoo>     
  </resolucao>                                                                   
                                                                                  
  <exibicao_listagem>                                                             
  1- Na listagem, preciso que seja exibido o vendedor e equipe de vendas.           
  Para extração, pode utilizar a NF de venda referenciada e como fallback o cnpj    
  para buscar em FaturamentoProduto.                                                
  2- Exiba em 1 coluna após CLIENTE esses dados de equipe de vendas e vendedor.     
  3- Dentro do badge de status da NF, quando for "Entrada OK" ou "Reversão", veja   
  se é possivel incluir a data da entrada da NF, fazendo o badge ocupar 2 campos    
  de altura estentendo 1 campo para baixo sem que empurre a linha de baixo mais     
  para baixo (preserve a altura da tabela).                                         
  Ou seja, outros campos podem empurrar a linha pra baixo mas o badge com a data    
  não.                                                                              
  </exibicao_listagem>                                                              
                                                                                    
  <exibicao_detalhe>                                                                
  Inclua Vendedor, equipe de vendas e a data da entrada nos detalhes tambem.        
  </exibicao_detalhe>                                                               
                                                                                    
  <permissao_cadastro>                                                              
  Os cadastros de Responsavel, Origem, Categorias e Subcategorias devem passar por  
  uma validação de permissão.                                                       
  Na aba de comercial, exiba um botão de "Autorização" com a tabela dos usuarios e  
  Filtro dinamico.                                                                  
  Apenas administrador e Gerente Comercial podem visualizar, aprovar ou desaprovar  
  nessa tela.                                                                       
  Só tem permissão para criar, remover ou alterar as Categorias, Subcategorias,     
  Responsavel e Origem que estiver flagado nessa tela.                              
  </permissao_cadastro>  

log de quem anexou
campo para financeiro sinalizar pagamento/baixa.

exportação:
