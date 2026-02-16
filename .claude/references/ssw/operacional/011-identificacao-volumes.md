# Opcao 011 — Identificacao de Volumes

> **Modulo**: Operacional — Expedicao / Coleta
> **Paginas de ajuda**: 5 paginas consolidadas (113, 115, 118, 168, 185)
> **Atualizado em**: 2026-02-14

## Funcao
Efetua emissao de etiquetas com codigo de barras para identificacao de volumes nao etiquetados na origem, complementa dados de DANFEs, libera placas para conferencia e suporta processos de cubagem.

## Quando Usar
- Imprimir etiquetas para volumes nao identificados na origem
- Complementar dados faltantes de DANFEs antes do envio ao SEFAZ
- Liberar placas de coleta para conferencia com SSWBar
- Gerar etiquetas sequenciais (NR1/NR2) para conferencia
- Carregar pendrive para conferencia off-line (SSWCONF)
- Cubar volumes com Regua SSW

## Pre-requisitos
- CTRCs emitidos com identificacao da placa de coleta (opcao 004 ou 006)
- Manifestos com chegada registrada (opcao 030)
- Impressora termica de codigo de barras configurada
- (Opcional) SSWBar instalado para conferencia eletronica
- (Opcional) Regua SSW para cubagem

## Campos / Interface

### Opcao 113 — Identificacao de Volumes Manifestados

| Campo | Descricao |
|-------|-----------|
| **Origem** | Unidade que emitiu o manifesto |
| **Cavalo** | Placa do cavalo mecanico |
| **Carreta** | Placa da carreta |
| **Manifesto** | Numero do manifesto (link abre para impressao) |
| **Peso** | Peso total da carga |
| **Chegada** | Data e hora da chegada |

#### Tela de Impressao

| Campo | Descricao |
|-------|-----------|
| **Placa** | Placa do cavalo do manifesto |
| **Qtde. de Notas Fiscais** | Qtd de NFs sem etiquetas de identificacao |
| **Deslocamento Horizontal** | Ajuste para direita/esquerda (8 ≈ 1mm) |
| **Deslocamento Vertical** | Ajuste para cima/baixo (8 ≈ 1mm) |
| **Quantidade Maxima** | Qtd maxima de etiquetas por CTRC |
| **Tamanho da Etiqueta** | G = grande (9x4.5cm), P = pequena (7x3.5cm) |
| **Temperatura** | Intensidade de impressao (1-9) |
| **Volume Inicial/Final** | Faixa de volumes para impressao |

### Opcao 115 — Atualiza Dados da DANFE

| Funcao | Descricao |
|--------|-----------|
| **Atualizar NR1 e NR2** | Captura etiquetas sequenciais grudadas na NF-e (para SSWBar 2) |
| **Atualizar data de emissao da NF-e** | Complementa data faltante |
| **Atualizar data/CFOP** | Complementa data e CFOP |
| **Atualizar data/CFOP/IE/NR** | Complementa multiplos campos |
| **Importar dados do Portal NF-e** | Busca data, CFOP e IE Substituto no portal nacional |
| **Atualizar chave NF-e** | Complementa chave de CTRCs gerados via EDI |

### Opcao 118 — Liberacao para Etiquetagem

| Campo | Descricao |
|-------|-----------|
| **Placa de Coleta** | Placa a ser liberada para conferencia/identificacao |

### Opcao 168 — Carregamento do SSWCONF

| Campo | Descricao |
|-------|-----------|
| **Codigo de barras do Manifesto/Romaneio** | Captura para incluir na conferencia |
| **Instalar SSWCONF** | Link para instalar software de conferencia off-line |
| **Concluir** | Gera arquivo para gravar no pendrive |

### Opcao 185 — Cubagem com Regua SSW

| Campo | Descricao |
|-------|-----------|
| **NR** | Codigo de barras da etiqueta do volume |
| **Altura** | Dimensao capturada com leitor + regua (capturar 0100 a cada 100cm) |
| **Largura** | Idem |
| **Comprimento** | Idem (ao capturar, cubagem e calculada automaticamente) |

## Fluxo de Uso

### Processo Simplificado (sem SSWBar)
1. Emitir CTRCs com placa de coleta (opcao 004)
2. Liberar placa para etiquetagem (opcao 118)
3. Gerar etiquetas por veiculo (opcao 011)
4. Descarregar veiculo grudando etiquetas nos volumes
5. Verificar sobras/faltas de etiquetas (sobra = falta de volumes, falta = sobra de volumes)

### Processo Completo com Etiquetas do Cliente
1. Gerar CTRCs via EDI com codigos das etiquetas do cliente
2. Cadastrar mascara de etiqueta cliente (se necessario, opcao 388)
3. Liberar placa para conferencia (opcao 118)
4. Usar SSWBar para capturar etiquetas cliente e gerar etiquetas SSW durante descarga

### Processo Completo com Etiquetas Sequenciais SSW
1. Gerar etiquetas sequenciais (link na opcao 011)
2. Grudar etiquetas na coleta: NR1 na NF-e, NR nos volumes, NR2 na NF-e
3. Emitir CTRCs informando NR1 e NR2 (sistema valida: NR1 + Qtd Volumes + 1 = NR2)
4. Liberar placa para conferencia (opcao 118)
5. Usar SSWBar para capturar NRs e gerar etiquetas SSW durante descarga

### Complementar Dados de DANFEs (opcao 115)
1. Acessar opcao 115
2. Escolher funcao (NR1/NR2, data, CFOP, IE, chave)
3. Capturar dados manualmente ou importar do Portal NF-e
4. Atualizar CTRCs antes do envio ao SEFAZ

### Conferencia Off-line com SSWCONF (opcao 168)
1. Instalar SSWCONF no notebook (link na opcao 168)
2. Capturar codigos de barras dos manifestos/romaneios
3. Clicar em Concluir para gerar arquivo
4. Gravar arquivo no pendrive
5. Conectar pendrive no notebook + sirene USB
6. Abrir SSWCONF, carregar arquivo, iniciar conferencia
7. Capturar volumes com leitor laser (sirene toca se volume nao pertence ao manifesto)
8. Finalizar conferencia quando todos os volumes forem lidos

### Cubagem com Regua SSW (opcao 185)
1. Configurar leitor para formato "Intercalado 2 e 5" com 2 caracteres
2. Capturar NR do volume com leitor
3. Capturar Altura com regua (ler 0100 a cada 100cm se > 100cm)
4. Capturar Largura com regua
5. Capturar Comprimento (cubagem e calculada automaticamente)
6. Repetir para proximos volumes

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **004** | Emissao de CTRCs — identifica placa de coleta e NR1/NR2 |
| **006** | Importacao XML — identifica placa de coleta |
| **030** | Chegada de veiculos — permite etiquetagem ate 3 dias apos chegada |
| **084** | Cubagem por CTRC — tem prioridade menor que opcao 185 |
| **184** | Cubagem manual de volumes — complementa opcao 185 |
| **178** | EDI Fiscal MT — exige data/CFOP/IE de NF-e (opcao 115) |
| **388** | Cadastro de clientes — mascara de etiqueta cliente + uso de cubadora |
| **SSWBar** | Sistema de conferencia eletronica com etiquetas |
| **SSWMobile** | Alternativa para cubagem (versao conferente) |

## Observacoes e Gotchas

### Limites e Validacoes
- **Etiquetagem ate 3 dias** apos chegada do veiculo
- **Manifestos relacionados ate 6 dias** de historico
- **NR1 + Qtd Volumes + 1 = NR2** — formula de validacao de etiquetas sequenciais
- **Sobras/faltas indicam problema** — sobra de etiquetas = falta de volumes, falta de etiquetas = sobra de volumes

### Etiquetas
- **Tamanho grande**: minimo 9x4.5cm
- **Tamanho pequeno**: minimo 7x3.5cm
- **Temperatura**: 1-9 (quanto maior, mais forte a impressao)
- **Sequenciais unicas** — numeracao unica para toda a transportadora (nao sobrepoe)
- **Imprimir por produto** — identifica codigo do produto na etiqueta

### Complemento de Dados (opcao 115)
- **Portal NF-e** — busca automatica de data, CFOP e IE Substituto
- **NR1 e NR2** — necessarios para descarga com SSWBar 2
- **Chave NF-e** — CTRCs via EDI podem vir sem chave (complementar antes do SEFAZ)
- **EDI Fiscal MT** — exige data/CFOP/IE completos (opcao 178)

### SSWCONF (Conferencia Off-line)
- **Sem comunicacao com SSW** — util quando nao ha conexao
- **Notebook + Sirene USB** — recomendado para mobilidade nas docas
- **Rele USB** — necessario para acionar sirene (venda Mercado Livre)
- **Senha supervisor** — para desativar sirene e finalizar conferencia
- **Volumes SSW** — nao reconhece etiquetas de clientes

### Cubagem com Regua SSW
- **Regua de madeira 100cm** — venda Mercado Livre (fabricante SOUZA)
- **Leitor configurado** — formato "Intercalado 2 e 5" + 2 caracteres + formato 128 habilitado
- **Prioridade** — cubagem da opcao 185 tem prioridade sobre opcao 084
- **Volumes iguais** — basta cubar 1 volume (media se mais de 1 for cubado)
- **Alternativa SSWMobile** — versao conferente com coletor/celular + leitor

### Processo Simplificado vs Completo
- **Simplificado** — NAO exige liberacao se emissao e com impressao simultanea de etiqueta (opcao 004)
- **Completo** — exige liberacao (opcao 118) para usar SSWBar
- **Etiquetas cliente** — requer EDI com codigos + mascara cadastrada (opcao 388)
- **Etiquetas sequenciais** — requer etiquetagem na coleta (no cliente) antes da emissao do CTRC
