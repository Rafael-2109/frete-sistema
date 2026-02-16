# Opcao 154 — Localizacao de Fornecedores

> **Modulo**: Comercial
> **Paginas de ajuda**: 4 paginas consolidadas (154, 157, 158, 159)
> **Atualizado em**: 2026-02-14

## Funcao
Localiza fornecedores no Contas a Pagar de todas as transportadoras usuarios do SSW, permitindo buscar por parte do nome do produto. Sistema auxilia no processo de compras mostrando situacao do produto no Almoxarifado e pedidos em andamento, com objetivo de comprar pelo menor preco sem processos administrativos obsoletos.

## Quando Usar
- Buscar fornecedores de um produto especifico usando parte do nome
- Comparar precos praticados por fornecedores em outras transportadoras SSW
- Localizar contatos (telefone, e-mail) de fornecedores potenciais
- Preparar relatorio de fornecedores para posterior contato
- Iniciar processo de compras no sistema integrado SSW

## Pre-requisitos
- Produto cadastrado no Almoxarifado (opcao 123)
- XML de NF-es no Contas a Pagar (opcao 475) da propria transportadora e/ou demais usuarios SSW
- Descricao precisa do produto (marca, modelo, etc.) para busca eficaz

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo produto | Sim | Produto previamente cadastrado no Almoxarifado (opcao 123). Permite busca por partes do nome |

### Tela de Busca
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidades | Nao | Ate 3 unidades para definir as cidades dos fornecedores |
| Compras dos ultimos | Sim | Quantidade de dias a serem pesquisadas nas compras realizadas |
| Parte do nome do produto | Sim | Partes do nome a serem buscadas na descricao do produto nos XML das NF-es. Deve identificar o produto com precisao (marca, modelo, etc.) |
| Pesquisar na minha transportadora | Opcao | Busca apenas na base de dados da propria transportadora |
| Pesquisar em todas as transportadoras SSW | Opcao | Busca na base de dados de todos os usuarios SSW |

### Tela Resultante (Colunas da Tabela)
| Coluna | Descricao |
|--------|-----------|
| Item da Nota Fiscal | Descricao dos produtos conforme DANFE |
| Unidade | Unidade de medida |
| Valor unitario | Preco unitario praticado pelo fornecedor (variavel importante para escolha) |
| Fornecedor | CNPJ do fornecedor |
| Nome | Nome do fornecedor |
| Cidade | Cidade do fornecedor |
| UF | Estado do fornecedor |
| Fone | Telefone do fornecedor |
| e-mail | E-mail do fornecedor |

## Fluxo de Uso

### Localizacao Basica de Fornecedores
1. Acessar opcao 154
2. Escolher codigo do produto no Almoxarifado (opcao 123)
3. Sistema mostra situacao do produto no Almoxarifado e pedidos em andamento
4. Informar ate 3 unidades (cidades) para filtrar
5. Definir periodo de compras a pesquisar (ultimos X dias)
6. Informar parte do nome do produto que identifique com precisao
7. Escolher escopo: minha transportadora OU todas as transportadoras SSW
8. Marcar fornecedores desejados na tabela resultante
9. Gerar relatorio de fornecedores selecionados para contato

### Processo Completo de Compras (Integracao)
1. **Localizacao (opcao 154)**: Buscar fornecedores e gerar relatorio
2. **Solicitacao de Cotacao (opcao 157)**: Enviar e-mail solicitando cotacao a fornecedores especificos
3. **Pedido (opcao 158)**: Selecionar cotacao recebida e enviar pedido
4. **Aprovacao (opcao 169)**: Aprovar pedido para envio de e-mail (se funcao ativada na opcao 903)
5. **Recebimento (opcao 124)**: Registrar entrada no Almoxarifado
6. **Consulta (opcao 159)**: Acompanhar pedido desde solicitacao ate recebimento

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 123 | Cadastro de Produtos no Almoxarifado (pre-requisito) |
| 124 | Entrada no Almoxarifado (recebimento dos produtos) |
| 128 | Consulta situacao dos Pedidos |
| 139 | Cadastro de e-mail do usuario (para receber copia de pedidos) |
| 157 | Solicitacao de Cotacao via e-mail |
| 158 | Realizacao do Pedido |
| 159 | Consulta de Pedido (acompanhamento) |
| 169 | Aprovacao de Pedidos |
| 475 | Contas a Pagar (fonte dos dados de NF-es) |
| 478 | Cadastro de e-mail do fornecedor |
| 903 | Ativacao da funcao de Aprovacao de Pedidos (Outros) |

## Observacoes e Gotchas
- **Parte do nome do produto**: Usar termos que identifiquem com precisao (marca, modelo, etc.) — descricoes genericas retornam muitos resultados irrelevantes
- **Valor unitario e uma variavel**: Preco mostrado e importante mas nao e a unica consideracao — qualidade, prazo e confiabilidade tambem devem ser avaliados
- **Pedidos em andamento**: Sistema mostra pedidos ja realizados, evitando compras duplicadas
- **Pesquisa colaborativa**: Buscar em todas as transportadoras SSW amplia significativamente as opcoes de fornecedores e permite comparacao de precos reais praticados
- **Relatorio para contato**: Marcar fornecedores gera relatorio com todos os dados de contato, facilitando negociacao posterior
- **Aprovacao de Pedidos**: Funcao de aprovacao (opcao 169) e opcional e deve ser ativada pela opcao 903 — quando ativa, pedidos so sao enviados apos aprovacao
- **Pedidos aprovados sao imutaveis**: Apos aprovacao, pedidos nao podem mais ser alterados
- **E-mail obrigatorio**: Fornecedor deve ter e-mail cadastrado (opcao 478) para receber cotacoes e pedidos
- **Unidade de entrega**: Definir corretamente a unidade de entrega no pedido para evitar problemas logisticos
