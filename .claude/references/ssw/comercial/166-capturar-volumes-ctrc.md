# Opcao 166 — Capturar Volumes que Gerarao CTRCs

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Captura codigos de barras de volumes entregues pelo embarcador para posterior geracao de CTRCs correspondentes. Volumes identificados com codigo de barras sao recepcionados pela transportadora, gerando um arquivo que sera utilizado pela opcao 006 para emissao dos CTRCs. Dados das Notas Fiscais devem estar previamente recebidos por arquivos EDI.

## Quando Usar
- Recepcionar volumes de embarcador com identificacao por codigo de barras
- Criar arquivo de volumes para posterior emissao de CTRCs
- Gerar comprovante de volumes recebidos do cliente
- Operacoes com grande volume de coleta/recebimento
- Clientes que utilizam EDI para envio de dados de NF-e

## Pre-requisitos
- Dados das Notas Fiscais recebidos via arquivo EDI (opcao 600)
- Codigos de barras dos volumes recebidos juntamente com os dados das NF-es no EDI
- Mascara de codigo de barras configurada (opcao 483/Outros, se necessaria)
- Cliente embarcador cadastrado no sistema
- Leitor de codigo de barras (ou SSWMobile/SSWCar)

## Campos / Interface

### Tela Principal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cliente | Sim | CNPJ do cliente embarcador |
| Iniciar | Acao | Inicia a captura de codigos de barras dos volumes em novo arquivo. Finaliza anormalmente arquivo anterior em andamento (mas deixa disponivel para geracao de CTRCs) |
| Continuar anterior | Acao | Continua captura em arquivo anteriormente finalizado |
| Concluir arquivo | Acao | Conclui arquivo em andamento, deixa disponivel para geracao de CTRCs (opcao 006) e imprime relatorio de comprovante |
| Abandona arquivo | Acao | Abandona arquivo em andamento (cancela captura) |

### SSWCar (Alternativa Offline)
| Funcao | Descricao |
|--------|-----------|
| F4 | Cadastrar transportadora e cliente |
| Captura | Capturar todos os codigos de barras dos volumes recebidos em tela unica |
| F1 | Gerar relatorio PDF dos volumes recepcionados (quantidade total imediata, arquivar para uso posterior) |
| F11 | Limpar volumes capturados anteriormente |

## Fluxo de Uso

### Processo Completo (Web)
1. Receber arquivo EDI com dados de NF-es e codigos de barras dos volumes (opcao 600)
2. Verificar mascara de codigo de barras (opcao 483/Outros)
3. Acessar opcao 166
4. Informar CNPJ do cliente embarcador
5. Clicar em "Iniciar" para criar novo arquivo de captura
6. Capturar codigos de barras dos volumes com leitor
7. Clicar em "Concluir arquivo" quando finalizar
8. Imprimir/salvar relatorio de comprovante dos volumes recebidos
9. Gerar CTRCs correspondentes pela opcao 006

### Processo com SSWMobile
1. Abrir SSWMobile no dispositivo movel
2. Selecionar funcao de captura de volumes (opcao 166)
3. Informar cliente embarcador
4. Capturar codigos de barras com camera do dispositivo
5. Concluir arquivo localmente
6. Transmitir arquivo concluido para o servidor (requer internet apenas neste momento)
7. Gerar CTRCs pela opcao 006

### Processo com SSWCar (Offline)
1. Instalar SSWCar no computador local
2. Cadastrar transportadora e cliente (F4)
3. Capturar todos os codigos de barras em tela unica
4. Gerar relatorio PDF (F1) e arquivar
5. Transmitir arquivo para o servidor
6. Gerar CTRCs pela opcao 006

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 006 | Emissao de CTRCs (gera CTRCs com base nos volumes capturados pela opcao 166) |
| 600 | Recebimento de arquivo EDI (dados de NF-es e codigos de barras dos volumes) |
| 483 | Configuracao de mascara de codigo de barras (Outros) |

## Observacoes e Gotchas
- **NF-es obrigatorias via EDI**: Dados das Notas Fiscais devem estar previamente recebidos por arquivos EDI antes de capturar volumes
- **Codigo de barras no EDI**: Codigos de barras dos volumes devem ser recebidos juntamente com os dados das NF-es no arquivo EDI
- **Mascara de codigo de barras**: Se necessaria, deve ser configurada na opcao 483/Outros para correta leitura dos volumes
- **Finalizar anormalmente**: Clicar em "Iniciar" quando ja existe arquivo em andamento finaliza anormalmente o anterior, mas deixa volumes disponiveis para geracao de CTRCs
- **Comprovante automatico**: Ao concluir arquivo, relatorio dos volumes capturados e impresso automaticamente como comprovante de recebimento
- **Arquivo concluido disponivel**: Apos conclusao, arquivo fica disponivel na opcao 006 para geracao dos CTRCs correspondentes
- **SSWMobile**: Permite captura sem micro, requer internet apenas para transmissao do arquivo concluido (nao durante a captura)
- **SSWCar para offline**: Ideal para instalacoes do cliente sem internet, onde recebimento deve ser rapido e seguro
- **Relatorio PDF do SSWCar**: Relatorio gerado (F1) deve ser arquivado para eventual uso posterior (auditoria, conferencia)
- **Limpar captura anterior (SSWCar)**: F11 limpa volumes capturados anteriormente, permitindo nova captura limpa
- **Continuar anterior**: Permite retomar captura de arquivo ja finalizado (util para adicionar volumes esquecidos)
- **Abandona arquivo**: Cancela captura em andamento sem deixar volumes disponiveis para geracao de CTRCs
