# Opcao 167 — Conferencia do SSWCOL

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua conferencia dos volumes capturados pelo SSWCOL (coletor de dados em notebook sem conexao com internet) comparando com CTRCs emitidos no SSW. Sistema identifica faltas e grava ocorrencias automaticamente. Permite operacao de coleta offline com transferencia posterior via pendrive.

## Quando Usar
- Conferir volumes coletados em campo (sem internet) contra CTRCs emitidos
- Identificar automaticamente faltas de volumes na coleta
- Gravar ocorrencias de divergencias entre volumes capturados e CTRCs
- Operacoes de coleta com grande volume usando etiquetas do proprio cliente
- Locais sem acesso a internet para coleta em tempo real

## Pre-requisitos
- SSWCOL instalado no notebook de coleta (via opcao 167)
- CTRCs gerados via EDI com respectivos codigos de barras dos volumes
- Ocorrencia de falta cadastrada na opcao 903/Operacao
- Mascara de codigo de barras configurada (opcao 388/Outros, se necessario usar apenas parte do codigo)
- Pendrive para transferencia dos dados do SSWCOL para o SSW

## Campos / Interface

### Tela de Conferencia (SSW - Opcao 167)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Periodo de emissao | Sim | Periodo de emissao dos CTRCs a serem conferidos |
| Remetente | Nao | Filtro de remetente dos CTRCs |
| Placa de coleta | Nao | Filtro de placa do veiculo de coleta |
| Arquivo do pendrive | Sim | Selecionar arquivo de volumes capturados pelo SSWCOL |

### SSWCOL (Notebook de Coleta)

#### Configuracoes
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| PLACA DA CARRETA | Sim | Veiculo de coleta |
| CONFERENTE | Sim | Nome do conferente |
| TAMANHO COD BARRAS | Sim | Quantidade de digitos do codigo de barras da etiqueta do cliente |
| DRIVE | Sim | Drive onde o pendrive esta conectado |
| CLIENTE | Nao | Nome do cliente a ser impresso no relatorio (nao e validado) |
| TRANSPORTADORA | Nao | Nome da transportadora a ser impresso no relatorio (nao e validado) |

#### Interface de Captura
| Elemento | Descricao |
|----------|-----------|
| (1) Codigo de barras | Codigo de barras dos volumes sendo coletados (campo de entrada) |
| (3) Codigo anterior | Codigo do volume anterior lido (confirmacao visual) |
| (4) Quantidade | Quantidade de volumes ja capturados |
| (5) Concluir | Conclui e grava o arquivo no pendrive |

## Fluxo de Uso

### Instalacao e Configuracao
1. Acessar opcao 167 no SSW
2. Baixar e instalar SSWCOL no notebook de coleta
3. Configurar SSWCOL: placa, conferente, tamanho codigo barras, drive do pendrive
4. Configurar mascara de codigo de barras (opcao 388/Outros, se necessario)
5. Cadastrar ocorrencia de falta (opcao 903/Operacao)

### Coleta em Campo (Offline)
1. Abrir SSWCOL no notebook
2. Conectar pendrive no drive configurado
3. Informar cliente e transportadora (opcional, para relatorio)
4. Capturar codigos de barras das etiquetas dos volumes coletados
5. Verificar visualmente codigo anterior lido e quantidade total
6. Ao finalizar coleta, clicar em "Concluir" (grava arquivo no pendrive)
7. Desconectar pendrive

### Conferencia no SSW (Online)
1. Conectar pendrive com arquivo do SSWCOL no computador com SSW
2. Acessar opcao 167
3. Selecionar CTRCs por periodo de emissao, remetente e placa de coleta
4. Importar arquivo de volumes do pendrive
5. Sistema compara volumes capturados com CTRCs emitidos
6. Sistema grava automaticamente ocorrencias de faltas identificadas
7. Visualizar resultado da conferencia (volumes OK, faltas)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 388 | Configuracao de mascara de codigo de barras (Outros) |
| 903 | Cadastro de ocorrencia de falta (Operacao) |
| EDI | Geracao de CTRCs via EDI com codigos de barras dos volumes |

## Observacoes e Gotchas
- **SSWCOL e offline**: Notebook de coleta NAO precisa de conexao com internet — captura e feita localmente
- **Transferencia via pendrive**: Unica forma de transferir dados do SSWCOL para o SSW — pendrive deve estar configurado no SSWCOL
- **CTRCs via EDI obrigatorios**: CTRCs precisam ser gerados via EDI com respectivos codigos de barras dos volumes para conferencia funcionar
- **Mascara de codigo de barras**: Se etiqueta do cliente tiver codigo muito longo, mascara (opcao 388) permite usar apenas parte relevante
- **Ocorrencia de falta automatica**: Sistema grava automaticamente ocorrencia de falta quando volume nao e encontrado — ocorrencia deve estar previamente cadastrada (opcao 903)
- **Cliente e transportadora no SSWCOL**: Campos sao apenas para impressao no relatorio, nenhuma validacao e realizada
- **Codigo anterior visivel**: SSWCOL mostra codigo anterior lido para conferencia visual imediata pelo operador
- **Quantidade em tempo real**: SSWCOL mostra quantidade de volumes ja capturados, permitindo conferencia rapida
- **Tamanho do codigo de barras**: Deve ser configurado corretamente no SSWCOL para leitura adequada das etiquetas
- **Selecao de CTRCs**: Na opcao 167, CTRCs sao selecionados por periodo de emissao, remetente e placa de coleta para otimizar comparacao
- **Conferencia comparativa**: Sistema compara volumes capturados no SSWCOL com CTRCs emitidos no SSW, identificando divergencias
- **Grava no pendrive**: Ao concluir captura no SSWCOL, arquivo e gravado no pendrive — nao esquecer de desconectar corretamente
