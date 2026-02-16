# Opcao 021 — Cadastro de Gaiolas e Estoque de Pallets e Chapas

> **Modulo**: Operacional — Expedicao
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua cadastro de gaiolas e manutencao de estoques de pallets e chapas para controle de patrimonio e unitizacao de carga.

## Quando Usar
- Cadastrar novas gaiolas para unitizacao
- Atualizar localizacao de gaiolas entre unidades
- Gerenciar estoques de pallets e chapas
- Gerar etiquetas de identificacao para controle de patrimonio
- Baixar/estornar gaiolas indisponiveis

## Pre-requisitos
- Controle de gaiolas/pallets/chapas ativado em opcao 903/Operacao
- Unidades e veiculos cadastrados (opcoes 401 e 026)
- Impressora termica para etiquetas

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Gaiola** | Sim | Numero da gaiola com ate 4 digitos |
| **Descricao** | Sim | Nome/identificacao da gaiola |
| **Localizacao atual** | Sim | Unidade (opcao 401) ou veiculo (opcao 026) onde a gaiola esta |
| **Link da gaiola** | - | Mostra descricao, localizacao e Manifesto Operacional vinculado |

## Fluxo de Uso

### Cadastrar/Atualizar Gaiola
1. Informar numero da gaiola (ate 4 digitos)
2. Preencher descricao e localizacao atual
3. Clicar em **ATUALIZAR** para salvar

### Alterar Estoques
1. Usar link **Alteracao de estoques** para pallets e chapas
2. Gaiolas tem estoque alterado automaticamente pelo reposicionamento (opcao 021)

### Gerar Etiquetas
1. Usar opcao **Etiqueta** para imprimir etiqueta de gaiola ja cadastrada
2. Ou usar **Arquivo cod barras** para gerar CSV com todos os codigos de barras

### Baixar Gaiola
1. Selecionar gaiola
2. Clicar em **BAIXAR** para marcar como indisponivel
3. Usar **ESTORNAR BAIXA** para reativar se necessario

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **020** | Emissao de Manifesto Operacional — gaiolas sao carregadas e vinculadas a manifestos |
| **025** | Saida de veiculos — atualiza estoque de gaiolas |
| **030** | Chegada de veiculos — atualiza estoque de gaiolas |
| **058** | Consulta estoque de gaiolas da unidade |
| **401** | Cadastro de unidades — destino de gaiolas |
| **026** | Cadastro de veiculos — localizacao temporaria de gaiolas |
| **715** | Inclusao de CTRCs em gaiolas |
| **903** | Configuracao — ativa controle de gaiolas/pallets/chapas |

## Observacoes e Gotchas
- **Gaiolas usadas para mercadorias de alto valor** — controle rigoroso de patrimonio
- **Estoque atualizado automaticamente** — saidas (opcao 025) e chegadas (opcao 030) alteram estoque
- **Gaiolas geram Manifestos proprios** — cada gaiola pode ter seu Manifesto Operacional separado dos CTRCs
- **Numero ate 4 digitos** — limitacao do sistema
- **Arquivo CSV** — util para confeccao de etiquetas resistentes em fornecedor externo
- **Impressora termica necessaria** — para impressao de etiquetas in-loco
- Pallets e chapas tem controle de estoque separado (nao tem cadastro como gaiolas)
