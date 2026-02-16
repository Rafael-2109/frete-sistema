# Opcao 379 — Geracao Automatica de Pre-CTRCs

> **Modulo**: Comercial
> **Paginas de ajuda**: 6 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Configura parametros para geracao automatica de pre-CTRCs com emissao de etiquetas de volumes pelo cliente. Disponivel somente para clientes CIF (remetente = pagador do frete). Configuracoes tambem sao usadas como sugestao na geracao manual (opcao 006).

## Quando Usar
- Configurar geracao automatica de pre-CTRCs para clientes CIF
- Permitir que cliente remetente/pagador emita etiquetas SSW antes da coleta
- Padronizar parametros de emissao para clientes especificos (reduzindo erros manuais)
- Integrar recepcao automatica de NF-e/CT-e via XML/EDI

## Pre-requisitos
- Cliente CIF (remetente = pagador)
- Recepcao de XMLs de NF-e/CT-e via:
  - Portal NF-e (busca automatica)
  - Opcao 608 (recepcao manual)
  - EDI (visualizavel via opcao 071)
- Documentos de referencia emitidos no mes corrente ou anterior (verificado na chave de acesso)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ do remetente | Sim | Cliente remetente que tambem e pagador do frete |
| CNPJ do pagador | Condicional | Usado em subcontratacao (cliente logistica/embarcador entrega para a transportadora) |
| Unidade de emissao | Sim | Unidade emissora dos pre-CTRCs |
| Tipo de documento | Sim | Escolher um dos disponiveis na opcao 006 |
| Agrupamento de NFs | Sim | D=destinatario, P=pedido, R=recebedor, E=EDI, N=nao agrupa |
| Placa do veiculo de coleta | Nao | Placa de coleta do CTRC |
| Tipo de mercadoria | Nao | Importante pois pode definir a tabela de frete a utilizar |
| Codigo de especie | Nao | Importante para gerenciamento de risco (opcao 390) |
| Usa Tabela Generica | Sim | S=permite calculo do frete pela Tabela Generica (opcao 923), N=nao permite |
| Gera pre-CTRCs automaticamente | Sim | S=geracao automatica ativa, N=desligada (parametros usados como sugestao na opcao 006) |
| Tipo de importacao | Sim | E=EDI, P=Portal NF-E, A=ambos (define qual tipo dispara a geracao) |

## Fluxo de Uso

### Configuracao Inicial
1. Cadastrar cliente com CNPJ do remetente (e pagador, se subcontratacao)
2. Definir unidade de emissao e tipo de documento
3. Configurar agrupamento de NFs
4. Informar placa de veiculo, tipo de mercadoria, codigo de especie (opcionais)
5. Configurar uso de Tabela Generica (S/N)
6. Ativar geracao automatica (S) ou apenas sugestao para geracao manual (N)
7. Definir tipo de importacao (EDI, Portal, ou ambos)

### Geracao Automatica (Apos Configuracao)
1. Cliente emite NF-e e informa transportadora na DANFE
2. XML e recepcionado (Portal NF-e, opcao 608, ou EDI)
3. Sistema gera pre-CTRC automaticamente a cada 1 minuto (ate 3 tentativas)
4. Pre-CTRC fica disponivel na fila "Digitados" da opcao 007
5. Cliente pode emitir etiquetas SSW via:
   - Site: http://www.ssw.inf.br/2/label (alguns minutos apos emissao NF-e)
   - SSW: opcao 079 (se cliente possui SSW instalado)

### Geracao Manual com Sugestao (Configuracao com "N")
1. Configuracao e cadastrada com "Gera pre-CTRCs automaticamente = N"
2. Ao usar opcao 006 (geracao manual), sistema sugere parametros cadastrados
3. Reduz erros de digitacao e padroniza emissao

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 006 | Geracao manual de pre-CTRCs — usa configuracoes da 379 como sugestao |
| 007 | Fila "Digitados" onde pre-CTRCs gerados ficam disponiveis para envio ao SEFAZ |
| 608 | Recepcao manual de XMLs de NF-e |
| 071 | Visualizacao de NF-es recebidas via EDI |
| 079 | Emissao de etiquetas de volumes pelo cliente (SSW instalado nas dependencias) |
| 011 | Emissao de etiquetas pela transportadora (mercadoria ja nas dependencias) |
| 390 | Gerenciamento de risco (usa codigo de especie) |
| 923 | Tabela Generica (habilitada pelo campo "Usa Tabela Generica") |

## Observacoes e Gotchas
- **SOMENTE clientes CIF**: disponivel apenas quando remetente = pagador do frete
- **Documentos recentes**: apenas NF-e/CT-e emitidos no mes corrente e anterior sao processados (verificado na chave de acesso)
- **Geracao a cada 1 minuto**: processo automatico executa a cada minuto, com ate 3 tentativas
- **Sem agrupamento**: CT-es sao gerados automaticamente SEM agrupamento por esta opcao
- **Etiquetas pelo cliente**: link http://www.ssw.inf.br/2/label permite cliente emitir etiquetas SSW alguns minutos apos emissao da NF-e
- **Etiquetas pela transportadora**: SSWBar e opcao 011 sao usados APOS mercadoria estar nas dependencias da transportadora (nao antes)
- **Configuracao sem geracao**: se "Gera pre-CTRCs automaticamente = N", parametros sao apenas SUGERIDOS na opcao 006 (nao gera automaticamente)
- **Tipo de importacao**: define qual fonte dispara a geracao (EDI, Portal NF-E, ou ambos)
- **Subcontratacao**: usar campo "CNPJ do pagador" quando cliente e logistica/embarcador que entrega para a transportadora

## Integracoes API Especificas (Clientes)

### BRITANIA (CNPJ raiz: 07019308)
- **Sistema recebe**: API ssw3277 — recebe NF-es (token fixo criado pelo SSW, informado ao cliente)
- **Sistema envia**:
  - ssw2837 — ocorrencias via WS (URL, usuario e senha do cliente)
  - ssw3281 (F1) — dados de etiqueta para cliente montar etiqueta unica
  - ssw3281 (F2) — XML CT-e padrao Cliente
- **Processo**: cadastro via opcao 379 → etiqueta, XML CT-e e ocorrencias enviados automaticamente
- **OBS**: apenas envio de ocorrencia via WS ativo (Black Friday 2024 pausou testes, retorno previsto 2025)

### ENJOEI (CNPJ raiz: 16922038)
- **Sistema recebe**: API ssw3181 (F1) — recebe Declaracoes de conteudo (URL, usuario e senha do cliente)
- **Sistema envia**:
  - ssw3181 (F2) — dados de etiqueta para cliente montar etiqueta unica
  - ssw3181 (F3) — ocorrencia padrao cliente (DEXPARA considerar XXX)
- **Processo**: cadastro via opcao 379 → etiqueta e ocorrencias enviados automaticamente
