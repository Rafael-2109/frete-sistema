# Opcao 388 — Cadastro de Clientes - Complemento

> **Modulo**: Comercial
> **Paginas de ajuda**: 3 paginas consolidadas (184, 172, 243)
> **Atualizado em**: 2026-02-14

## Funcao
Configuracoes complementares de clientes, incluindo uso de mascara de codigo de cliente, geracao de RPS provisorio para unificacao, e Substituicao Tributaria de ISS. Usada como referencia em diversas opcoes do sistema para buscar volumes e configurar comportamentos especificos.

## Quando Usar
- Configurar mascara de codigo de cliente para identificacao de volumes sem etiqueta SSW
- Habilitar geracao de RPS Provisorio para clientes que exigem unificacao de documentos fiscais municipais
- Configurar Substituicao Tributaria (cliente retém ISS para recolhimento)
- Parametrizar uso de cubadora/balanca para geracao de CTRCs Complementares

## Pre-requisitos
- Cliente cadastrado no sistema
- Para Substituicao Tributaria: verificar leis municipais e aceitacao do cliente
- Para RPS Provisorio: cliente deve exigir unificacao de documentos fiscais

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Usa mascara de codigo cliente | Nao | Define se codigo do cliente usa mascara especifica (ex: formato SSCC sem mascara) |
| Gera RPS provisorio | Nao | S=operacoes municipais usam RPS Provisorio (serie 999) para posterior unificacao via opcao 172 |
| Substituicao Tributaria | Nao | S=cliente retém ISS para recolhimento (reduz valor do frete). Considerar leis municipais e aceitacao do cliente |
| Usa da cubadora/balanca | Nao | Diferente de N=habilita geracao de CTRCs Complementares (opcao 221) quando peso de calculo aumenta |

## Fluxo de Uso

### Configuracao de Codigo de Cliente (Mascara)
1. Cadastrar ou editar cliente na opcao 388
2. Configurar campo "Usa mascara de codigo cliente"
3. Codigo do cliente passa a ser aceito sem mascara em opcoes:
   - 184 (cubagem/pesagem manual de volumes)
   - 243 (ocorrencias por volumes)
4. Sistema busca volume usando criterios: unidade do usuario, nao autorizado, nao entregue

### Configuracao de RPS Provisorio (Unificacao)
1. Configurar cliente com "Gera RPS provisorio = S"
2. Operacoes municipais passam a emitir RPS Provisorio (serie 999)
3. RPS Provisorios sao emitidos durante periodo (sem finalidade fiscal/financeira/contabil, apenas operacional)
4. Ao final do periodo, usar opcao 172 para unificar RPSs Provisorios em RPS definitivo
5. RPS unificado e enviado a prefeitura para conversao em NFS-e (opcao 009 ou 014)
6. RPS unificado e o unico documento fiscal do periodo (apuracao de ISS)

### Configuracao de Substituicao Tributaria
1. Verificar leis municipais e aceitacao do cliente
2. Configurar cliente com "Substituicao Tributaria = S"
3. Cliente retém ISS para recolhimento (valor do frete e reduzido)
4. Substituicao e aplicada em operacoes municipais e servicos complementares

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 184 | Cubagem/pesagem manual — aceita codigo de cliente sem mascara (conforme opcao 388) |
| 243 | Ocorrencias por volumes — aceita SSCC sem mascara (conforme opcao 388) |
| 172 | Unificacao de RPSs — unifica RPSs Provisorios gerados conforme configuracao da opcao 388 |
| 009 | Envio de RPS a prefeitura — envia RPS unificado para conversao em NFS-e |
| 014 | Envio de RPS a prefeitura — envia RPS unificado para conversao em NFS-e |
| 004 | Emissao de CTRC — transporte municipal gera RPS Provisorio se configurado |
| 005 | Emissao de CTRC — transporte municipal gera RPS Provisorio se configurado |
| 006 | Emissao de CTRC em lote — transporte municipal gera RPS Provisorio se configurado |
| 015 | Servico complementar Agendamento — gera RPS Provisorio se configurado |
| 016 | Servico complementar Reentrega/Devolucao/Recoleta — gera RPS Provisorio se configurado |
| 089 | Servico complementar Paletizacao — gera RPS Provisorio se configurado |
| 099 | Servico complementar Estadia — gera RPS Provisorio se configurado |
| 199 | Servico complementar Armazenagem — gera RPS Provisorio se configurado |
| 222 | Servico complementar Geral — gera RPS Provisorio se configurado |
| 221 | Geracao de CTRCs Complementares — habilitada pelo campo "Usa da cubadora/balanca" |
| 084 | Cubagem/pesagem por CTRC — prioridade menor que opcao 184 |

## Observacoes e Gotchas
- **Codigo de cliente sem mascara**: ao usar codigo do cliente (ex: SSCC) em vez de codigo de barras SSW, sistema busca volume usando criterios: estar na unidade do usuario, nao autorizado, nao entregue. Se encontrar mais de 1 volume, dimensoes NAO serao gravadas
- **CTRCs unitizados**: ao usar opcao 184 com codigo de cliente, dimensoes sao gravadas APENAS no volume capturado, nao afetando demais volumes de CTRCs unitizados
- **Prioridade de pesagem**: pesos/volumes capturados na opcao 184 (por volume) tem prioridade sobre opcao 084 (por CTRC)
- **Volumes faltantes**: se faltar captura de alguns volumes, sistema calcula media dos ja capturados para calculo do frete
- **RPS Provisorio (serie 999)**: NAO possui finalidade financeira, fiscal ou contabil, apenas operacional. Documento fiscal real e o RPS unificado
- **Unificacao por municipio**: opcao 172 unifica RPSs Provisorios por municipio E codigo de prestacao de servico (viabiliza apuracao de ISS)
- **Substituicao Tributaria**: reduz valor do frete pois cliente retém ISS. Necessario verificar leis municipais e aceitacao do cliente
- **Operacoes municipais**: origem e destino no mesmo municipio (transporte municipal + servicos complementares)
- **Ocorrencias por volume (243)**: ocorrencias SSW validas: 53 (avaria mercadoria), 54 (avaria embalagem), 20 (falta mercadoria), 23 (mercadoria avariada), 38 (recusa recebedor), 49 (falta volume), 51 (sobra volume), 50 (extravio)
- **Complemento de ocorrencia**: texto informado pelo usuario e complementado automaticamente pelo SSW com SSCC do volume
