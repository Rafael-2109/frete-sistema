# Opção 110 — Cotação de Fretes pelo Cliente

> **Módulo**: Comercial
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Permite que clientes com acesso ao SSW efetuem simulações de cotações de frete de forma autônoma, sem necessidade de contato com o SAC da transportadora.

## Quando Usar
- Cliente precisa estimar valor de frete antes de fechar negócio com destinatário
- Conferir se tabelas de frete cadastradas estão corretas
- Simular diferentes cenários (peso, valor, quantidade de volumes) para otimizar custo

## Pré-requisitos
- **Opção 483**: Cadastro de cliente com acesso ao sistema SSW
- **Opção 402**: Cadastro de cidades com praças e prazos
- **Tabelas de frete**: Negociadas e cadastradas para o cliente pagador
- **Cadastro de mercadorias**: Códigos de mercadoria disponíveis

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ PAGADOR | Sim | CNPJ do pagador do frete (link para pesquisa por nome disponível) |
| MERCADORIA | Sim | Código da mercadoria (link para lista de seleção disponível) |
| FRETE | Sim | **1** (CIF) ou **2** (FOB) |
| CEP ORIGEM | Sim | CEP de coleta (link para busca por nome da cidade disponível) |
| CEP DESTINO | Sim | CEP de entrega (link para busca por nome da cidade disponível) |
| CNPJ DESTIN | Não | CNPJ do destinatário (preenche automaticamente Contribuinte e Entrega Difícil) |
| CONTRIBUINTE | Sim | **S** (contribuinte do estado) ou **N** (não contribuinte - usa alíquota ICMS interna) |
| ENTREGA DIFÍCIL | Sim | **S** (cobra TDE se previsto na tabela) ou **N** |
| VALOR DA NF | Sim | Valor da mercadoria em Reais |
| QUANTIDADE DE VOLUMES | Sim | Quantidade de volumes da NF |
| QUANTIDADE DE PARES | Não | Necessário apenas se tabela negociada cobrar por par de volumes |
| PESO (Kg) | Sim | Peso da mercadoria em quilos |
| CUBAGEM (m3) | Sim | Volume em metros cúbicos (link para calcular via dimensões disponível) |
| PESO DE CÁLCULO | Automático | Maior entre peso real e peso cubado (calculado pelo sistema) |

## Fluxo de Uso
1. Cliente faz login no SSW com suas credenciais
2. Acessar opção 110
3. Informar CNPJ PAGADOR (ou pesquisar por nome via link)
4. Selecionar MERCADORIA (via código ou link de lista)
5. Definir tipo de FRETE (1-CIF ou 2-FOB)
6. Informar CEP ORIGEM e CEP DESTINO (busca por nome disponível via link)
7. Opcionalmente informar CNPJ DESTIN (auto-preenche Contribuinte e Entrega Difícil)
8. Configurar CONTRIBUINTE (**S** ou **N**)
9. Configurar ENTREGA DIFÍCIL (**S** ou **N**)
10. Preencher dados da carga: VALOR DA NF, QUANTIDADE DE VOLUMES, PESO, CUBAGEM
11. Se tabela cobrar por par, informar QUANTIDADE DE PARES
12. Clicar em **►** no rodapé para simular
13. Sistema exibe **VALOR DO FRETE R$** com detalhamento de todas as parcelas
14. Repetir simulação alterando dados conforme necessário
15. Se decidir contratar, entrar em contato com SAC para formalizar via opção 002

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 002 | Contratação formal da cotação (via SAC da transportadora) |
| 483 | Cadastro de cliente com permissões de acesso ao sistema |
| 402 | Cadastro de cidades (origem/destino) com praças e prazos |
| Tabelas de frete | Tabelas negociadas entre cliente e transportadora (define cálculo) |

## Observações e Gotchas
- **Apenas simulação**: Esta opção **NÃO cadastra** a cotação no sistema. Para contratar, cliente deve contatar SAC da transportadora
- **Múltiplas simulações**: Possível simular várias vezes alterando dados (peso, valor NF, volumes) para comparar cenários
- **Auto-preenchimento**: Informar CNPJ DESTIN preenche automaticamente campos Contribuinte e Entrega Difícil
- **ICMS interna**: Se destinatário for não contribuinte (**N**), sistema usa alíquota ICMS interna do estado de origem
- **TDE (Taxa de Entrega Difícil)**: Só é cobrada se **S** em Entrega Difícil E se prevista na tabela de frete negociada
- **Peso de cálculo**: Sistema calcula automaticamente o maior valor entre peso real e peso cubado
- **Cubagem via dimensões**: Link disponível para calcular m3 a partir das dimensões dos volumes
- **Validação de tabelas**: Ferramenta útil para cliente conferir se tabelas cadastradas estão corretas
- **Quantidade de pares**: Campo opcional, relevante apenas para tabelas específicas que cobram por par de volumes

