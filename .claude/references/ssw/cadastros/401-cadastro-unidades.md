# Opcao 401 — Cadastro de Unidades

> **Modulo**: Cadastros
> **Paginas de ajuda**: 21 paginas consolidadas (referencias cruzadas)
> **Atualizado em**: 2026-02-14

## Funcao

Cadastra e configura as unidades operacionais e comerciais da transportadora, incluindo filiais, matriz, unidades centralizadoras e agencias. Define parametros fiscais, operacionais, bancarios e de multi-empresa.

## Quando Usar

- Criar nova filial ou unidade operacional
- Configurar parametros fiscais (Inscricao Estadual, CNPJ, regime tributario)
- Definir contas bancarias da unidade
- Configurar emissao de documentos fiscais (CT-e, NF-e, MDF-e)
- Ativar/desativar funcionalidades especificas por unidade
- Configurar multi-empresa (empresas distintas no mesmo dominio)
- Definir unidade como Simples Nacional
- Cadastrar Inscricoes Estaduais Auxiliares para DIFAL
- Configurar certificado digital para emissao de documentos eletronicos

## Pre-requisitos

- Para emissao de CT-e/NF-e/MDF-e: certificado digital tipo A1 (arquivo PFX + senha) cadastrado na opcao 903
- Para SEFAZ Pernambuco: solicitar credenciamento em ambiente de Homologacao antes de producao
- Para SEFAZ Parana: solicitar autorizacao de uso do sistema SSW via site da SEFAZ
- Cidades atendidas devem ser vinculadas pela opcao 402
- Rotas entre unidades configuradas pela opcao 403

## Campos / Interface

### Dados Basicos

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Sigla da unidade | Sim | Identificador unico de 3 letras (ex: SAO, ARA, MTZ) |
| Tipo de unidade | Sim | Filial, Matriz (MTZ), Embarcador, Agencia Correios, FEC (fechada/completa) |
| CNPJ | Sim | CNPJ da unidade (raiz pode ser compartilhada entre unidades) |
| Inscricao Estadual | Condicional | Obrigatorio para emissao de CT-e (numeracao e por IE) |
| Inscricao Municipal | Nao | Para emissao de RPS/NFS-e |
| Razao Social | Sim | Nome juridico da unidade |
| Nome Fantasia | Nao | Nome comercial (usado em etiquetas SIGEP Correios) |

### Dados Fiscais

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| UF | Sim | UF da Inscricao Estadual |
| Simples Nacional | Sim | Indica se a unidade e optante pelo SN |
| Regime PIS/COFINS | Sim | Cumulativo ou Nao Cumulativo (parametrizado pela Equipe SSW) |
| AIDF | Nao | Autorizacao de Impressao de Documentos Fiscais (formularios) |
| IE Auxiliares DIFAL | Nao | Inscricoes Estaduais de outras UFs para recolhimento de DIFAL |
| Credito Presumido ICMS | Nao | Reducao de 20% no GNRE (CONFAZ Convenio ICMS 106/96) |

### Dados Bancarios

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Banco/Agencia/Conta | Sim | Conta principal da unidade (sugerida em diversas opcoes) |
| DV (opcional) | Nao | Digito verificador da conta |

### Multi-Empresa

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Numero da Empresa | Condicional | Identificador numerico quando multi-empresa ativada |

### Parametrizacao Fiscal (CT-e/NF-e/MDF-e)

Configurada pela opcao 920 apos cadastro da unidade:

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Serie Fiscal | Sim | Serie a ser utilizada nos documentos eletronicos |
| Ultimo Numero | Sim | Ultima numeracao utilizada (deixar vazio se serie nova) |
| CNPJ Certificado Digital | Sim | Raiz deve ser a mesma da unidade |
| Data Inicio Emissao | Sim | Data a partir da qual documentos podem ser emitidos |
| Sigla da unidade (opcional) | Nao | Para numeracao exclusiva por unidade (nao apenas por IE) |

## Fluxo de Uso

### Criacao de Nova Unidade

1. Acessar opcao 401
2. Incluir nova unidade informando sigla, CNPJ, IE, tipo
3. Preencher dados fiscais e bancarios
4. Confirmar cadastro
5. Vincular cidades atendidas pela opcao 402
6. Configurar rotas pela opcao 403
7. (Opcional) Parametrizar emissao de documentos fiscais pela opcao 920

### Configuracao para CT-e/NF-e/MDF-e

1. Adquirir certificado digital tipo A1 para o CNPJ
2. Cadastrar certificado na opcao 903
3. Credenciar CNPJ no SEFAZ da UF (verificar em portal SEFAZ)
4. Cadastrar unidade na opcao 401 com IE
5. Parametrizar emissao pela opcao 920

### Multi-Empresa

1. Ativar multi-empresa no dominio (contatar Equipe SSW)
2. Cadastrar unidades informando numero da empresa
3. Usuarios (opcao 925) podem ser vinculados a empresas especificas ou ter acesso a todas

### Tabela CNPJ x Dominio

1. Inclusao/atualizacao de CNPJ em unidade tipo Filial ou Embarcador atualiza automaticamente a tabela CNPJ x Dominio (opcao 934)
2. Exclusao de CNPJ nao desativa automaticamente — fazer manualmente na opcao 934

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 402 | Cidades atendidas pela unidade |
| 403 | Rotas entre unidades |
| 408 | Comissionamento de unidades (ex: Agencias Correios) |
| 456 | Conta corrente — sugestao de banco/ag/ccor da unidade |
| 475 | Contas a Pagar — unidade de pagamento |
| 477 | Consulta Despesas — filtro por empresa (multi-empresa) |
| 478 | Fornecedores — eventos com contas contabeis |
| 503 | Eventos — classificacao tributaria |
| 514 | Aliquotas SN — destaque de impostos por IE |
| 515 | SPED Contribuicoes — CNPJ e regime PIS/COFINS |
| 541 | Plano de contas contabeis |
| 569 | Conciliacao bancaria |
| 690 | Unidades centralizadoras |
| 903 | Certificado digital |
| 920 | Parametrizacao fiscal CT-e/NF-e/MDF-e |
| 925 | Usuarios — vinculo a empresa/unidade |
| 934 | Tabela CNPJ x Dominio |

## Observacoes e Gotchas

### Numeracao de Documentos Fiscais

- **CT-e**: numeracao por Inscricao Estadual (nao por unidade)
- **MDF-e**: numeracao por CNPJ
- Opcao 920 permite numeracao exclusiva por unidade (informar sigla)

### SEFAZ Especiais

- **Pernambuco**: requer testes em Homologacao (10 autorizacoes + 1 cancelamento + 1 anulacao) antes de liberar Producao (automatico em 24h)
- **Parana**: transportadora solicita autorizacao via site SEFAZ identificando SSW como fornecedor, Equipe SSW aprova
- **Ceara**: nao recolhe ICMS via GNRE se valor < R$ 1,00
- **Parana e Bahia**: tomador contribuinte desconta ICMS do frete (nao ha GNRE)

### Simples Nacional

- Unidades SN sao configuradas por IE na opcao 401
- Aliquotas de destaque (ICMS, PIS, COFINS, ISS) configuradas na opcao 514
- Destaque nao gera credito ao cliente
- Sem destaque, imprime mensagem: "Empresa optante pelo Simples Nacional nao gera credito de ICMS"
- SN nao recolhe DIFAL

### Regime PIS/COFINS

- **Nao Cumulativo**: PIS 1,65%, COFINS 7,6% (permite creditos)
- **Cumulativo**: PIS 0,65%, COFINS 3,00% (sem creditos)
- Parametrizacao exclusiva da Equipe SSW (opcao 401)
- Base de calculo: a partir de 01/05/2023 exclui ICMS (MP 1.159/23), a partir de 01/06/2024 exclui IPI (IN 2152/2023)
- Transportadoras com Nao Cumulativo que nao usam Contabilidade SSW devem informar contas contabeis na opcao 515

### Multi-Empresa

- Ativa empresas juridicamente distintas no mesmo dominio SSW
- Campo "Empresa" aparece em diversas opcoes (477, 456, 475, 151, 675)
- Usuario pode ser restrito a uma empresa ou ter acesso a todas (opcao 925)
- Tabela generica (CNPJ da MTZ) aplica-se a todas as empresas

### Tipos de Unidade

- **MTZ (Matriz)**: unidade principal, CNPJ MTZ usado para tabelas genericas
- **Filial**: unidade operacional padrao
- **Embarcador**: unidade do embarcador (cliente que usa SSW para gestao)
- **Agencia Correios**: unidade para integracao com Correios (opcao 165, 176)
- **FEC (Fechada/Completa)**: cidades nao precisam ser configuradas na opcao 402, mas podem ser (para definir praca comercial)

### Unidades Centralizadoras

- Unidades podem indicar outras que centralizam suas operacoes (opcao 690)
- Usado em carregamentos de transferencias (opcao 020)
- Usuario de MTZ ou matriz contabil acessa despesas/dados de todas as unidades

### Banco/Conta

- Sugerido em conta corrente (opcao 456)
- Fatura com cobranca em carteira sem conta definida busca ordem: cliente/Faturamento (384) → unidade de cobranca (384 + 401) → transportadora (903/Cobranca)
- Contas a Pagar (475): campo "Banco" refere-se ao cadastrado na unidade (opcao 401)

### Correios

- Unidade Correios criada como tipo Agencia
- Cidades vinculadas pela opcao 402
- Nome Fantasia da unidade impresso em etiquetas SIGEP como Remetente
- Prazo e-commerce usa campo especifico (opcao 402)

### Formularios CTRC (pre-eletronico)

- Numero do CTRC: sigla (3 letras) + numero (6 digitos) + DV (uso interno, unico, nao se repete)
- Numero do Formulario: autorizado pelo fisco, impresso pela grafica, incorporado no momento da impressao
- Controle de uso pela opcao 537
- AIDF cadastrada na opcao 401 (resumo de formularios liberados/utilizados)

### Termo de Abertura/Encerramento de Livros

- Opcao 634: usa Razao Social da unidade informada (opcao 401)
- Imprime 2 paginas para capear livros contabeis

### GNRE

- IE Auxiliares para DIFAL cadastradas na opcao 401
- Emissao pela opcao 160 (DIFAL destino, FECP, CFOP 5932/6932, DIFAL mercadorias)
- Credito presumido ICMS (opcao 401) reduz valor da GNRE em 20%

### Integracao REINF

- Eventos (opcao 503) definem Natureza do Rendimento e Classificacao Serv. Prest. para REINF
- Fornecedor (opcao 478) define eventos com contas contabeis
- Desoneracao da Folha (CPRB) via Lei 14.973/2024 considerada no REINF (opcao 587)

### EDI Embarcados (Padrão GUANAPACK)

- Razao Social da unidade emissora do CT-e extraida dos dados fiscais (opcao 401)
- Usado no campo D do arquivo CSV CONEMB

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A02](../pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira |
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G04](../pops/POP-G04-relatorios-contabilidade.md) | Relatorios contabilidade |
