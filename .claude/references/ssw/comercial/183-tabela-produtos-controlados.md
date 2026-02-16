# Opcao 183 — Tabela de Produtos Controlados

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (183, 083)
> **Atualizado em**: 2026-02-14

## Funcao
Define por NCM (Nomenclatura Comum do Mercosul) os produtos controlados, perigosos, Anvisa, pereciveis e vacinas. Manutencao desta opcao e realizada APENAS pela equipe SSW. Informacoes cadastradas sao utilizadas pela opcao 083 para geracao de relatorios aos orgaos controladores (Policia Federal, Exercito, SSP, IBAMA, DNIT) e para controle de gelo de vacinas e pereciveis.

## Quando Usar
- **Equipe SSW APENAS**: Cadastrar ou atualizar NCM de produtos controlados
- **Equipe SSW APENAS**: Definir orgaos controladores por NCM
- **Equipe SSW APENAS**: Configurar prazos de validade de gelo para pereciveis e vacinas
- **Usuarios finais**: Consultar relacao de produtos controlados cadastrados
- **Usuarios finais**: Gerar relatorios para orgaos controladores (opcao 083)

## Pre-requisitos
- Codigo NCM do produto (ate 8 digitos)
- Descricao do produto
- Identificacao dos orgaos controladores (Policia Federal, Exercito, SSP, ANVISA)
- Codigo TPN (para Policia Federal)
- Numero de Ordem (para Exercito)
- Prazos de validade de gelo (para pereciveis e vacinas)

## Campos / Interface

### Tela Principal (Opcao 183)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| NCM | Sim | Nomenclatura Comum do Mercosul de ate 8 digitos |
| Descricao | Sim | Descricao do produto correspondente ao codigo NCM |
| Ativo | Sim | S=produto ativo para uso nos demais processos do SSW, N=inativo |

### Controlado
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Policia Federal | Nao | S=produto controlado pela Policia Federal (Portaria 240/2019) |
| Codigo TPN | Condicional | Obrigatorio se controlado pela Policia Federal (usado no SIPROQUIM) |
| Operacao | Nao | Exportacao marcada indica que produto e controlado apenas em operacoes de exportacao |
| Exercito | Nao | S=produto controlado pelo Exercito |
| Numero de Ordem | Condicional | Codigo de Classificacao do Exercito (obrigatorio se controlado pelo Exercito) |
| SSP | Nao | S=produto controlado pelas Secretarias Estaduais de Seguranca Publica |

### ANVISA
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| ANVISA | Nao | S=produto controlado pela ANVISA (Portaria 344/1998 MS - artigo 67) |
| Etiqueta | Nao | S=palavra ANVISA sera impressa na etiqueta de identificacao dos volumes |

### Perecivel
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Perecivel | Nao | S=NCM de perecivel que necessita controle de reposicao de gelo |
| Etiqueta | Nao | S=palavra PERECIVEL sera impressa na etiqueta de identificacao dos volumes |
| Prazo validade | Condicional | Prazos (em horas) para troca de diversos tipos de gelos: Agua, Seco, Gel, Espuma |

### Vacina
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Vacina | Nao | S=NCM de vacina que necessita controle de reposicao de gelo |
| Etiqueta | Nao | S=palavra VACINA sera impressa na etiqueta de identificacao dos volumes |
| Prazo validade | Condicional | Prazos (em horas) para troca de diversos tipos de gelos: Agua, Seco, Gel, Espuma |

### Relatorio (Link "Relacao de Produtos Controlados")
| Coluna | Descricao |
|--------|-----------|
| NCM | Nomenclatura Comum do Mercosul |
| DESCRICAO | Descricao da mercadoria |
| ATI | X=NCM ativo |
| PFE | X=Policia Federal |
| EXE | X=Exercito |
| SSP | X=Secretaria da Seguranca Publica |
| ANV | X=Anvisa |
| PERECI | Perecivel. Valores nas colunas: ETIQ (etiqueta), AGUA, SECO, GEL, ESPU (horas para proxima troca) |
| VACINA | Vacina. Valores nas colunas: ETIQ (etiqueta), AGUA, SECO, GEL, ESPU (horas para proxima troca) |

## Fluxo de Uso

### Cadastrar Produto Controlado (Equipe SSW)
1. Acessar opcao 183
2. Informar codigo NCM (ate 8 digitos)
3. Informar descricao do produto
4. Marcar "Ativo" como S
5. Definir orgaos controladores (PFE, EXE, SSP, ANVISA)
6. Informar codigos especificos (TPN para PFE, Numero de Ordem para EXE)
7. Se perecivel ou vacina, marcar campo e definir prazos de validade de gelo
8. Configurar impressao em etiqueta (ANVISA, PERECIVEL, VACINA)
9. Salvar cadastro

### Consultar Produtos Controlados (Usuarios Finais)
1. Acessar opcao 183
2. Clicar em link "Relacao de Produtos Controlados"
3. Visualizar relatorio com todos os NCM cadastrados e seus controles

### Gerar Relatorios para Orgaos Controladores (Opcao 083)
1. Acessar opcao 083
2. Selecionar orgao controlador (Policia Federal, Exercito, SSP, IBAMA, DNIT)
3. Informar periodo (mes/ano ou ano de emissao dos CTRCs)
4. Informar dados especificos do orgao (certificados, declarante, etc.)
5. Gerar relatorio (usa dados cadastrados na opcao 183)
6. Enviar relatorio ao orgao controlador

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 083 | Relatorios de Produtos Controlados e Perigosos (usa dados da opcao 183) |
| 004 | Emissao de CTRC (alerta para produtos controlados pela Policia Federal) |
| 005 | Emissao de CTRC (alerta para produtos controlados pela Policia Federal) |
| 006 | Geracao de CTRC (importa NCM do XML da NF-e, identifica produtos controlados) |
| 011 | Etiqueta de identificacao de volumes (imprime ANVISA, PERECIVEL, VACINA, PERIGOSO, CONTROLADO) |
| 019 | CTRCs Disponiveis para Transferencia (permite selecionar CTRCs com produtos perigosos) |
| 081 | CTRCs Disponiveis para Entrega (permite selecionar CTRCs com produtos perigosos) |
| SSWBar | Etiqueta de identificacao de volumes (imprime ANVISA, PERECIVEL, VACINA, PERIGOSO, CONTROLADO) |
| DAMDFE | Observacoes do DAMDFE (relaciona produtos perigosos com codigos ONU) |
| SIPROQUIM | Arquivo gerado pela opcao 083 para importacao no sistema da Policia Federal |
| STRPP | Sistema de Transporte Rodoviario de Produtos Perigosos (DNIT) |

## Observacoes e Gotchas
- **Manutencao EXCLUSIVA da equipe SSW**: Usuarios finais NAO podem cadastrar ou alterar produtos controlados — apenas consultar
- **Produtos Controlados vs Produtos Perigosos**: Controlados sao marcados por NCM (opcao 183). Perigosos sao identificados automaticamente por codigo ONU na descricao (XML da NF-e)
- **Alerta apenas para Policia Federal**: Apenas produtos controlados pela Policia Federal recebem alerta na emissao do CTRC (opcoes 004 e 005). Outros orgaos nao tem bloqueio, apenas relatorios periodicos
- **Codigo ONU identifica perigosos**: Sistema identifica automaticamente produtos perigosos lendo codigo ONU (ou UN) na descricao do XML da NF-e
- **XML da NF-e e fundamental**: Todo o processo depende do XML da NF-e para identificacao do NCM e codigo ONU — sem XML, produto nao e identificado
- **Etiqueta de volume**: Palavras impressas na ordem: VACINA, PERECIVEL, ANVISA, PERIGOSO, CONTROLADO (alem de PRIORITARIO, ESPECIAL, PESSOA FISICA)
- **IBAMA usa multiplas fontes**: IBAMA utiliza marcas de PFE, EXE, SSP E TAMBEM produtos com codigo ONU na descricao
- **Instrucao Normativa nº 9 de 25/03/2020**: Expedidor de produtos perigosos deve cadastrar rotas no STRPP (https://servicos.dnit.gov.br/cargasperigosas/LoginEmpresa)
- **SIPROQUIM**: Arquivo gerado pela opcao 083 para importacao no sistema da Policia Federal — CTRC nao entregue e considerado com data de previsao (retificar manualmente apos entrega)
- **Codigo TPN**: Usado pela Policia Federal (obrigatorio para produtos controlados pela PFE)
- **Numero de Ordem**: Codigo de Classificacao do Exercito (obrigatorio para produtos controlados pelo Exercito)
- **Prazos de validade de gelo**: Definidos em horas para troca de gelo: Agua, Seco, Gel, Espuma (para pereciveis e vacinas)
- **Portaria 240/2019**: Base legal para controle de produtos pela Policia Federal
- **Portaria 344/1998 MS - artigo 67**: Base legal para medicamentos controlados pela ANVISA
- **Tabela NCM atualizada**: SSW ja utiliza Tabela NCM conforme Nota Tecnica 2016.003 v 3.00 (vigencia a partir de 01/04/2022)
- **Produtos perigosos DNIT**: Nenhum alerta ou bloqueio no SSW — carregamento deve ser feito manualmente conforme IN nº 9/2020 (ex: nao carregar juntos alimento e veneno)
- **Destinos especificos PFE**: Para Boliv ia, Colombia e Peru, existem produtos quimicos especificos sob controle da Policia Federal
