# Opcao 035 — Romaneio de Entregas

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 8 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Relaciona CTRCs disponiveis para entrega em um veiculo/motorista, gerando Romaneio de Entregas. Emite documentos necessarios (DACTEs, DANFEs), imprime roteiro, gera GPS para navegador, solicita SMP a gerenciadora e controla CIOT/Vale Pedagio.

## Quando Usar
- Carregar CTRCs em veiculo para entrega
- Organizar sequencia de entregas por setor/rota
- Imprimir documentos fiscais para acompanhar veiculo
- Registrar ocorrencia "Saiu para Entrega" (codigo SSW 85)
- Gerar MDF-e de Romaneio (Opcao 236)

## Pre-requisitos
- CTRCs com destino na unidade, disponiveis para entrega
- Veiculo cadastrado (Opcao 026)
- Motorista cadastrado (Opcao 028)
- Setores definidos (Opcao 404) — opcional para ordenacao
- Ajudantes cadastrados (Opcao 163) se controle ativo (Opcao 903)

## Campos / Interface

### Tela Emissao Romaneio
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Veiculo | Sim | Placa do veiculo |
| Motorista | Sim | CPF do motorista |
| Ajudante | Condicional | Se controle ativo (Opcao 903/Operacao) |
| Data entrega | Sim | Data prevista de entrega |
| Itinerante | Nao | S = Romaneio nao retorna no mesmo dia |
| Sequencia roteiro | Condicional | Habilitada se Opcao 903 = S para ordenar por digitacao |

### Facilidades por Romaneio
| Funcao | Descricao |
|--------|-----------|
| Comprovantes | Romaneio + CTRCs + Comprovantes de Entrega |
| Mapa | Localizacao atual do veiculo (SSWMobile 5 ou satelite) |
| Roteiro | Imprime locais de entrega em mapa com numeracao |
| GPS | Gera arquivo IGO para navegador |
| Imprimir DACTEs/DANFEs | Documentos fiscais para acompanhar veiculo |
| SMP | Protocolo de autorizacao da gerenciadora |
| CIOT | CIOT vigente para TAC |
| Tornar itinerante | Muda tipo para Itinerante |

## Fluxo de Uso

### Emissao Basica
1. Acessar Opcao 035
2. Informar veiculo e motorista
3. Selecionar CTRCs para carregar
4. Definir sequencia de entregas (se configurado)
5. Confirmar emissao
6. Sistema gera Romaneio e atribui ocorrencia "85 - Saiu para Entrega"
7. Opcional: Imprimir DACTEs, roteiro, GPS

### Emissao com Gerenciamento de Risco
1. Seguir passos basicos
2. Sistema solicita SMP automaticamente
3. Se SMP obrigatorio (Opcao 903), aguardar autorizacao (Opcao 235)
4. Imprimir Romaneio apos SMP autorizado

### Baixa de Entregas
- Baixa manual (Opcao 038)
- SSWMobile (tempo real)
- SSWScan (escaneamento comprovante)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 020 | MDF-e de transferencia |
| 025 | Saida de veiculo |
| 026 | Cadastro de veiculos |
| 028 | Cadastro de motoristas |
| 030 | Chegada de veiculo |
| 035 | Esta opcao |
| 036 | Consulta Romaneios cancelados |
| 037 | Cancelamento de Romaneio |
| 038 | Baixa de entregas/ocorrencias |
| 040 | Capa de Comprovantes (Romaneios itinerantes) |
| 055 | Lembretes mostrados na tela |
| 072 | CTRB gerado |
| 078 | Conferencia Romaneio x CTRCs |
| 088 | Situacao de veiculos em tempo real |
| 099 | CTRC Complementar de Estadia |
| 101 | Instrucoes ao CTRC |
| 129 | Relacao CTRCs em Romaneios |
| 163 | Cadastro de ajudantes |
| 218 | Instrucoes para SSWMobile |
| 235 | Impressao somente com SMP |
| 236 | MDF-e de Romaneio de Entregas |
| 390 | Requisitos de valores (GR) |
| 404 | Setores (controle de retorno, itinerante) |
| 405 | Tabela de ocorrencias |
| 428 | Arquivamento de Comprovantes |
| 431 | Relacao CTRCs sem Manifesto (para seguradora) |
| 903 | Configuracoes gerais (GR, ajudantes, ordenacao, papel) |
| 925 | Usuario com permissao para operacao sem GR |
| SSWMobile | Baixa tempo real, localizacao, Estou Chegando |
| SSWScan | Escaneamento comprovante |

## Observacoes e Gotchas

### Ordenacao de CTRCs
**Opcao 903/Operacao** define:
- **N**: CTRCs ordenados por SETOR/CEP
- **S**: CTRCs ordenados conforme digitacao/captura
  - Opcao 035: Campo "SEQUENCIA DO ROTEIRO" habilitado
  - SSWBar: Imprime primeiro os carregados por ultimo

### Romaneio Itinerante
- Nao retorna no mesmo dia a unidade
- Comprovantes incluidos em Capa (Opcao 040) somente apos "Retorno do Veiculo"
- Setor marcado como Itinerante (Opcao 404) sugere Romaneio itinerante

### Controle de Retorno
- Romaneios emitidos para setores sem controle (Opcao 404) dispensam baixa obrigatoria diaria
- Util para entregas em distritos distantes

### Gerenciamento de Risco (GR)
Mesmos requisitos da Opcao 003:
- Liberacao de veiculos/motoristas/ajudantes (Opcao 026, 028, 163)
- Requisitos de valores de mercadoria (Opcao 390)
- SMP obrigatorio (Opcao 903/GR) — impressao via Opcao 235

### MDF-e de Romaneio
- Opcao 236 emite MDF-e vinculado a Romaneio
- Opcao 401 pode configurar emissao automatica
- Encerramento automatico:
  - Novo MDF-e para mesmo veiculo
  - Processo diario (Romaneio ja baixado)

### Saida para Entrega (Codigo SSW 85)
- Ocorrencia registrada automaticamente na emissao
- Parceiros nao-SSW podem usar link http://www.ssw.inf.br/2/lastmile ou Opcao 049
- Importante para embarcadores e-commerce

### Operacao Sem Papel
- Ativar em Opcao 903/Operacao
- DACTEs impressos somente para:
  - Clientes que querem papel (Opcao 381)
  - Motoristas sem SSWMobile (Opcao 028)
- Codigo de barras DACTE impresso no Romaneio substitui documento

### Estou Chegando
- Ativado em Opcao 903/Operacao (requer ordenacao = S)
- Raio do local de entrega: configurado em Opcao 903 (sugerido 100m)
- SSWMobile notifica cliente automaticamente

### Conferencia de Carregamento
- Opcao 078: Conferencia Romaneio x CTRCs
- SSWBar: Captura codigo de barras volumes/etiquetas
- Formas: Digitacao, Codigo CTRC, Codigo DACTE

### Cancelamento
- Opcao 037: Cancela Romaneio
- Romaneios com CTRCs que ja receberam ocorrencia NAO podem ser cancelados
- Cancelamento remove ocorrencia "85 - Saiu para Entrega" (mantem instrucao texto)
- Cancela automaticamente: Manifesto Operacional, MDF-e, CIOT, Vale Pedagio

### Baixa Obrigatoria Dia Anterior
- Todos CTRCs do Romaneio do dia anterior devem receber ocorrencia
- Necessario para emitir novo Romaneio no dia seguinte
- Exceto para setores sem controle (Opcao 404)

### CTRCs Pendentes e Em Romaneios
- Opcao 088: CTRCs pendentes de entrega
- Opcao 129: Relacao CTRCs em Romaneios
- Opcao 081: CTRCs disponiveis para entrega (com lembretes)

### Integracao SSWMobile
- Recebe localizacao atual veiculo
- Permite baixa tempo real
- "Estou Chegando" notifica cliente
- Foto ou assinatura como comprovante (Opcao 903/Operacao)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
