# Opcao 003 — Ordem de Coleta / Gerenciamento

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 8 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Repassa coletas cadastradas aos veiculos (comandar), atualiza situacao das coletas, e imprime Ordem de Coleta e Romaneio de Coletas. Permite gestao completa do ciclo de coletas ate confirmacao final (coletada ou cancelada).

## Quando Usar
- Comandar coletas para veiculos
- Atualizar situacao de coletas (comandada, coletada, cancelada)
- Imprimir Ordem de Coleta para motorista
- Gerar Romaneio de Coletas por veiculo
- Imprimir documentos PDF enviados por clientes (coletas reversas)
- Acompanhar coletas pendentes por setor

## Pre-requisitos
- Coletas cadastradas (Opcao 001) ou programadas (Opcao 042)
- Veiculos cadastrados (Opcao 026)
- Motoristas cadastrados (Opcao 028)
- Setores definidos (Opcao 404) — opcional
- Tabela de ocorrencias de coleta (Opcao 519)

## Campos / Interface

### Tela Inicial
| Campo | Descricao |
|-------|-----------|
| Unidades | Unidades do mesmo armazem operacional (Opcao 431) |
| Comandar coletas por data | Traz coletas de data especifica |
| Por veiculo e data | Relacao de coletas comandadas por veiculo/dia |
| Numero da coleta | Busca coleta pelo numero |
| Por codigo de barras | Busca usando codigo da Ordem de Coleta |

### Tela Setores
| Campo | Descricao |
|-------|-----------|
| Setor | Setor definido em Opcao 404 |
| Nome do setor | Identificacao do setor |
| Valor de mercadoria | Valor total (exceto pre-cadastradas) |
| Qtde PRE | Quantidade de pre-cadastradas |
| Qtd TOT | Quantidade total (incluindo pre-cadastradas) |
| Qtd NCOM | Quantidade nao comandadas |
| M3 | Metragem cubica |
| Kg TOT | Peso total |
| Kg NCOM | Peso nao comandado |

### Tela Comandar
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Veiculo | Sim | Placa do veiculo (sugerido conforme Opcao 013) |
| Motorista | Sim | CPF do motorista |
| Data limite inicial | Auto | Limite prometido no cadastro inicial |
| Inclusao | Auto | Tipo: manual, EDI, parceiro, web, API, agendada |
| Coleta subcontratante | Auto | Dominio e numero da coleta da subcontratante |
| DANFEs | Auto | Relacao de DANFEs/Pedidos via EDI |
| Data/hora limite | Auto | Limite prometido |
| Codigo de ocorrencia | Nao | Codigo para envio via EDI (Opcao 519) |

## Abas / Sub-telas

### Ordem de Coleta
- Gera documento para coleta especifica
- Vias duplicadas ou unicas configuravel (Opcao 903/operacao)

### Romaneio de Coletas
- Gera documento para coletas comandadas a veiculo
- Situacao do momento da geracao
- Retirar coleta = descomandar
- Romaneio nao pode ser cancelado

### Documentos de Coleta
- Imprime PDFs enviados por clientes (Opcao 137)
- Por veiculo (opcional) e data
- Usado em coletas reversas

## Fluxo de Uso

### Comandar Coletas
1. Acessar Opcao 003
2. Escolher setor ou informar data
3. Selecionar coletas a comandar
4. Informar veiculo e motorista
5. Confirmar comando
6. Sistema muda situacao para "Comandada"
7. Opcional: Imprimir Romaneio de Coletas

### Baixar Coleta Realizada
1. Localizar coleta comandada
2. Informar ocorrencia "Coletada"
3. Informar data/hora da coleta
4. Opcional: Capturar DANFEs coletadas
5. Sistema muda situacao para "Coletada"

### Cancelar Coleta
1. Localizar coleta
2. Informar ocorrencia "Cancelada"
3. Informar motivo (codigo de ocorrencia)
4. Sistema muda situacao para "Cancelada"

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 001 | Coletas cadastradas |
| 004 | Pre-CTRC gerado com DANFE capturada (Opcao 206) |
| 006 | Gera pre-CTRC a partir de volumes coletados |
| 013 | Veiculos vinculados ao setor (sugestao automatica) |
| 020 | MDF-es vinculados a Romaneio |
| 026 | Cadastro de veiculos |
| 028 | Cadastro de motoristas |
| 042 | Coletas programadas |
| 050 | Informacoes de coletas |
| 072 | CTRB gerado para veiculo |
| 090 | Usuarios que recebem CORREIO de coleta |
| 137 | Documentos PDF de coleta |
| 143 | Envio de SMS ao motorista |
| 163 | Cadastro de ajudantes |
| 166 | Captura volumes on-line |
| 206 | DANFEs coletadas disponiveis para pre-CTRC |
| 228 | Motoristas em quarentena |
| 235 | SMP para impressao de Romaneio |
| 390 | Requisitos de valores de mercadoria (GR) |
| 402 | Mudanca automatica data coleta para dia de atendimento |
| 404 | Setores de coleta |
| 431 | Armazem operacional (une unidades) |
| 519 | Tabela de ocorrencias de coleta |
| 600 | Coletas via EDI |
| 903 | Configuracoes gerais (GR, mudanca automatica data) |
| 925 | Usuario com permissao para operacao sem liberacao GR |
| SSWMobile | Comandar/informar coletas pelo motorista |
| SSWCol | Gravacao off-line de mercadorias |

## Observacoes e Gotchas

### Situacoes de Coletas
Ao final do dia, coletas devem estar:
- **Coletadas** ou **Canceladas**
- NAO pode restar coleta "Cadastrada" ou "Comandada" pendente

### Mudanca Automatica de Data
Opcao 903/Operacao pode configurar:
- Coletas "Cadastradas" ou "Comandadas" ao final do dia
- Alteradas automaticamente para proximo dia de atendimento (Opcao 402)

### Armazem Operacional
- Diversas unidades fiscais (Opcao 401) podem formar mesmo armazem (Opcao 431)
- Coletas dessas unidades aparecem juntas na Opcao 003

### Veiculos Sugeridos
- Veiculos vinculados ao Setor (Opcao 013)
- Sempre sugeridos para comandar coletas
- Facilita operacao e reduz erros

### Gerenciamento de Risco (GR)
Efetuado em conjunto com entrega do veiculo:

#### Liberacao de Veiculos/Motoristas/Ajudantes
- Veiculos (Opcao 026), motoristas (Opcao 028) e ajudantes (Opcao 163)
- Precisam ter autorizacoes vigentes:
  - Individualmente
  - Por conjunto (veiculo + motorista)
  - Por operacao (Romaneio)
- Especificas por gerenciadora (Opcao 903/GR)
- Autorizacao nao liberada so possivel por usuario com permissao (Opcao 925)

#### Requisitos de Valores de Mercadoria
- Valor comandado + ja carregado (coletas + Romaneio de Entregas)
- Pode exigir requisitos (Opcao 390):
  - Veiculos (especificos por cliente)
  - Iscas
- Especie da coleta informada em Opcao 001

#### SMP (Solicitacao de Monitoramento Preventivo)
- Conforme Opcao 903/GR/SMP
- Opcao 235 necessaria para impressao de Romaneio
- Impressao pode ser impedida se SMP rejeitada

### Site de Rastreamento
- Coletas rastreavveis em www.ssw.inf.br
- Informar numero da coleta

### SMS ao Cliente
- Cliente remetente com celular pode receber SMS
- Informando realizacao da coleta
- Configuracao em Opcao 903/SMS

### Vinculo CTRC e Situacao Coletada
CTRC emitido muda coleta para "Coletada" quando:
- Mesma placa de coleta
- Mesma raiz CNPJ remetente
- Data emissao CTRC = data cadastrar/comandar coleta

### SSWMobile
Motorista pode:
- Receber informacoes de coletas
- Informar ocorrencias
- Capturar chave DANFE (informa site sem alimentar Opcao 003)
- Capturar DANFE + volumes (2 etiquetas NR1/NR2)
- Amarrar volumes a DANFEs

### Relacao de Mercadorias Coletadas
- **On-line**: Opcao 166 ou SSWMobile
- **Off-line**: SSWCol (sem internet)
- Arquivo usado para gerar pre-CTRCs (Opcao 006)

### Coletas em Parceiros SSW
- Coleta gravada automaticamente no parceiro
- Subcontratante cadastra (Opcao 001) e identifica parceiro (Opcao 408)
- Parceiro comanda via Opcao 003
- Ocorrencias gravadas em ambos dominios (Opcao 519)

### Unidades Sem Opcao 003
- Usuarios cadastrados em Opcao 090
- Recebem instrucoes de coleta pelo CORREIO SSW

### Shopee B2C
Operacao especifica com DANFEs relacionadas a coleta (ver documentacao AQUI na ajuda SSW).
