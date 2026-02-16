# Opcao 164 — Relacao de Ajudantes

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (referencia na opcao 163)
> **Atualizado em**: 2026-02-14

## Funcao
Gera relacao/relatorio de ajudantes cadastrados pela opcao 163, permitindo filtros por tipo de vinculo (funcionario/terceirizado), status (ativo/bloqueado), unidade, periodo de movimentacao, periodo de cadastramento e validade de gerenciamento de risco. Saida pode ser em formato texto ou planilha Excel.

## Quando Usar
- Listar ajudantes funcionarios ou terceirizados
- Identificar ajudantes bloqueados ou ativos
- Verificar ajudantes com autorizacao de gerenciamento de risco vencida ou proxima do vencimento
- Gerar relacao de ajudantes de uma unidade especifica
- Consultar ajudantes por periodo de cadastramento ou ultimo movimento
- Exportar dados de ajudantes para analise externa (Excel)

## Pre-requisitos
- Ajudantes previamente cadastrados na opcao 163

## Campos / Interface

### Filtros do Relatorio
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Relacao com a transportadora | Sim | C=funcionarios, T=terceirizados, A=todos |
| Bloqueado | Sim | S=bloqueados, N=ativos, T=todos |
| Ultimo movimento - unidade | Nao | Filtrar por unidade de ultimo movimento |
| Ultimo movimento - periodo | Nao | Filtrar por periodo de ultimo movimento |
| Periodo de cadastramento | Nao | Filtrar por periodo de cadastro no sistema |
| Validade de gerenciamento de risco | Nao | Filtrar por periodo de validade de certificacao/autorizacao |
| Arquivo em Excel | Sim | N=texto, S=planilha Excel |

### Dados Cadastrados (Opcao 163)
| Categoria | Campos |
|-----------|--------|
| Dados Pessoais | Nome, endereco, telefone celular (obrigatorio), telefones comercial/pessoal (opcional) |
| Dados de Identificacao | RG numero, orgao expedidor, cidade/UF de expedicao, data de expedicao, data de nascimento, cidade/UF de nascimento, imagem digitalizada do RG |
| Outros Dados | Bloqueado (S/N), Relacao com transportadora (C=CLT, T=terceirizado), Data admissao, Gerenciadora de risco, Autorizacao numero, Valido ate, Observacao |

## Fluxo de Uso

### Gerar Relacao Basica de Ajudantes
1. Acessar opcao 164
2. Selecionar tipo de vinculo (C=funcionarios, T=terceirizados, A=todos)
3. Selecionar status (S=bloqueados, N=ativos, T=todos)
4. Escolher formato (N=texto, S=Excel)
5. Gerar relatorio

### Identificar Ajudantes com Autorizacao Vencida
1. Acessar opcao 164
2. Selecionar tipo de vinculo desejado
3. Selecionar status N=ativos
4. Informar periodo de validade de gerenciamento de risco (data atual ou anterior)
5. Gerar relatorio em Excel para analise
6. Contatar gerenciadora de risco para renovacao

### Consultar Ajudantes de uma Unidade
1. Acessar opcao 164
2. Informar unidade desejada em "Ultimo movimento - unidade"
3. Opcionalmente, informar periodo de ultimo movimento
4. Gerar relatorio

### Listar Novos Cadastros
1. Acessar opcao 164
2. Informar periodo de cadastramento desejado
3. Gerar relatorio com novos ajudantes

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 163 | Cadastro de Ajudantes (fonte dos dados do relatorio) |
| Manifestos | Ajudantes cadastrados podem ser vinculados a Manifestos |
| Romaneios | Ajudantes cadastrados podem ser vinculados a Romaneios |
| Entregas | Ajudantes participam de operacoes de entrega (ultimo movimento rastreado) |
| Coletas | Ajudantes participam de operacoes de coleta |

## Observacoes e Gotchas
- **Cadastro completo obrigatorio**: Dados pessoais (exceto telefones comercial/pessoal) e dados de identificacao (RG completo) sao obrigatorios na opcao 163
- **Cidade/UF de expedicao e nascimento**: Devem ser selecionadas digitando nome da cidade e apertando ENTER (nao e texto livre)
- **Imagem do RG**: Pode ser anexada ao cadastro (util para envio a gerenciadora de risco ou apresentacao em portarias)
- **Validade de autorizacao**: Emissao de Manifesto/Romaneio alerta se autorizacao de gerenciamento de risco do ajudante estiver vencida
- **Exclusao condicional**: Ajudante so pode ser excluido se nao tiver nenhuma operacao vinculada (opcao 163)
- **Ficha cadastral**: Opcao 163 permite impressao de ficha cadastral completa (util para gerenciadora de risco, portarias de clientes, etc.)
- **CLT vs Terceirizado**: Classificacao impacta gestao de pessoal e custos (C=funcionario CLT, T=terceirizado)
- **Bloqueio preserva historico**: Ajudante bloqueado permanece no sistema e no historico de operacoes, mas nao pode ser usado em novas operacoes
- **Excel facilita analise**: Formato Excel permite ordenacao, filtragem e identificacao rapida de ajudantes com autorizacao proxima ao vencimento
- **Ultimo movimento automatico**: Sistema registra automaticamente unidade e data do ultimo movimento do ajudante em operacoes
- **Gerenciadora de risco**: Campo permite registrar qual gerenciadora autorizou o ajudante (importante para auditoria e compliance)
