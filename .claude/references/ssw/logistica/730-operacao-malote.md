# Opção 730 — Operação com Malote

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Efetua operações com Malote (remetentes e destinatários fixos), permitindo cadastro e geração automática de CTRC.

## Quando Usar
- Para operações de transporte com remetentes e destinatários fixos
- Operações repetitivas entre pontos fixos (ex: transporte de documentos entre filiais)
- Operações via SSWMobile com leitura de código de barras do malote

## Pré-requisitos
- Cadastro prévio dos Malotes pela opção 730
- Localização com coordenadas geográficas dos CNPJs (para operações com SSWMobile)

## Campos / Interface

### Gerar CTRC
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ cliente | Sim | Cliente pagador da operação (previamente cadastrado) |
| Número Malote | Sim | Número do Malote cadastrado nesta opção |
| Veículo de coleta | Sim | Veículo que inicia a operação (coleta) |
| CNPJ coleta | Sim | Um dos dois CNPJs cadastrados no Malote (mais próximo do SSWMobile) |
| Nota Fiscal referência | Automático | Gerado com série MAL e número fictício |

### Cadastrar Malote
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ cliente | Sim | Cliente pagador e contratante da operação |
| Número do Malote | Sim | Número único na transportadora (sugerido em código de barras) |
| CNPJ 1 / CNPJ 2 | Sim | Os 2 CNPJs (remetente e destinatário) da operação |
| Documento | Sim | Tipo de documento |
| Tipo | Sim | Tipo de mercadoria |
| Espécie | Sim | Espécie de mercadoria |
| Valor | Sim | Valor declarado |
| Kg | Sim | Peso em quilogramas |

## Fluxo de Uso

### Cadastro Inicial
1. Acessar link "Cadastrar Malote"
2. Informar CNPJ do cliente pagador
3. Definir número único do Malote
4. Cadastrar os 2 CNPJs envolvidos (com coordenadas geográficas)
5. Definir dados padrão (documento, tipo, espécie, valor, kg)

### Geração de CTRC
1. Acessar link "Gerar CTRC"
2. Informar CNPJ do cliente e número do Malote
3. Informar veículo de coleta e CNPJ de coleta
4. Confirmar geração
5. CTRC fica disponível em "Digitados" (opção 007) para envio ao SEFAZ

### Operação via SSWMobile
1. Capturar Número Malote (código de barras) pelo botão "COLETA NF-e"
2. Sistema utiliza CNPJ mais próximo da localização do motorista
3. CTRC gerado automaticamente com NF-e série MAL e número fictício
4. CTRC fica na fila "Digitados" (opção 007) para envio ao SEFAZ

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 007 | CTRCs gerados ficam disponíveis em "Digitados" para envio ao SEFAZ |
| 011 | Consulta etiquetas identificadoras dos malotes (NR) |
| 101 | CTRC com campo DANFEs/NR/Código do Cliente = Número do Malote |
| SSWMobile | Geração automática de CTRC via captura de código de barras |

## Observações e Gotchas
- **Característica principal**: Malotes têm remetentes e destinatários fixos, permitindo geração automática do CTRC
- **Número do Malote**: Gravado no CTRC (opção 101) no campo "DANFEs/NR/Código do Cliente"
- **NF-e automática**: Utiliza data de hoje no formato DDMMAA
- **Série MAL**: NF-e gerada tem série MAL (malote) e número fictício
- **Triagem**: Separação dos malotes por unidade e setor deve ser realizada com etiquetas identificadoras
- **Etiquetas não impressas**: Podem ser consultadas pela opção 011/NR lendo o número do malote (código do cliente)
- **Importação/Exportação**: Links "Importar arq CSV" e "Baixar" permitem gestão em massa dos malotes
- **SSWMobile**: CNPJ de coleta determinado automaticamente pela localização mais próxima do motorista
- **Interação via Número**: No SSWMobile, interação com CTRC é feita apenas pelo Número do Malote gravado no CTRC
