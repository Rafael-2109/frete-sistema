# Opcao 009 — Impressao de RPS e Geracao de NFS-e

> **Modulo**: Operacional — Fiscal
> **Paginas de ajuda**: 3 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Imprime RPS (Recibo Provisorio de Servicos) e converte em NFS-e para prefeituras com autorizacao sincrona via webservice. Suporta emissao de documentos fiscais municipais (ISS) para operacoes de transporte com origem e destino no mesmo municipio.

## Quando Usar
- Imprimir RPS de operacoes municipais (origem = destino)
- Gerar NFS-e sincronamente (prefeituras com webservice)
- Reimprimir RPS/NFS-e ja autorizados
- Associar PDFs de NFS-e aos RPS
- Buscar e validar RPS sem PDF

## Pre-requisitos
- RPS emitido via opcao 004 (transporte municipal) ou opcao 733 (outros servicos)
- Inscricao Municipal cadastrada (opcao 401)
- Aliquotas de ISS por municipio (opcao 402)
- Certificado digital instalado (opcao 903/Certificados) para prefeituras com webservice
- Credenciais cadastradas (algumas prefeituras)

## Campos / Interface

### Tela Principal

| Campo | Descricao |
|-------|-----------|
| **Prefeitura Municipal** | Municipio sede da unidade (opcao 401) |
| **Site** | Link do site da prefeitura para ISS/NFS-e |
| **Vencim Certif Digital** | Vencimento do certificado digital (opcao 903) |
| **Digitados** | Qtd de RPS aguardando envio (link relaciona os RPS) |
| **RPSs nao enviados** | RPS nao enviados por criterios nao atendidos |
| **Autorizados (sem impressao)** | RPS/NFS-e autorizados pela prefeitura ainda nao impressos |
| **Rejeitados** | RPS rejeitados pela prefeitura (link mostra motivos) |

### Imprimir RPSs

| Campo | Descricao |
|-------|-----------|
| **Placa de coleta (opc)** | Filtro opcional por placa |
| **Classificados por Nota Fiscal** | S = ordena por numero da NF-e vinculada |
| **Digitados por mim** | Imprime apenas meus RPS |
| **Digitados por todos** | Imprime todos os RPS da unidade |
| **Na ordem de captura** | Captura chaves DANFE e imprime na mesma ordem (facilita grampeamento) |

### Reimprimir RPSs

| Campo | Descricao |
|-------|-----------|
| **Faixa de RPS** | Informar com digito verificador |
| **Selecionar** | M = meus RPS, T = todos da unidade |

### Associar NFS-e (pdf)

| Campo | Descricao |
|-------|-----------|
| **RPS (sem DV) (opc)** | RPS para associacao individual manual |
| **Arquivo** | Arquivo PDF (pode conter multiplas NFS-e para associacao automatica) |

### Buscar NFS-e

| Campo | Descricao |
|-------|-----------|
| **Periodo de emissao RPS** | Filtro por periodo |
| **Situacao** | S = sem PDF, T = todos |

## Fluxo de Uso

### Impressao Normal (Prefeituras sem Webservice)
1. Emitir RPS via opcao 004 (transporte municipal) ou opcao 733 (outros servicos)
2. Acessar opcao 009
3. Escolher opcao de impressao (por mim, por todos, ordem de captura)
4. Imprimir RPS em formulario continuo ou PDF
5. Gerar arquivo de lote via opcao 014 para envio a prefeitura
6. Aguardar retorno da prefeitura com NFS-e

### Impressao com Webservice (Prefeituras com Autorizacao Sincrona)
1. Emitir RPS via opcao 004 ou opcao 733
2. Acessar opcao 009
3. Clicar em **Enviar a Prefeitura** (RPSs digitados)
4. Sistema submete ao webservice e recebe NFS-e automaticamente
5. Clicar em **Imprimir todos** (autorizados sem impressao)
6. NFS-e e impresso diretamente

### Associar PDF de NFS-e
1. Buscar NFS-e sem PDF (filtro Situacao = S)
2. Baixar PDFs do site da prefeitura (link Consulta NFS-e disponivel para algumas cidades)
3. Salvar PDFs em pasta local
4. Usar opcao **Associar NFS-e (pdf)** com arquivo multi-PDF (ate 200 NFS-e)
5. Sistema associa automaticamente

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **004** | Emissao de RPS para transporte municipal |
| **733** | Emissao de RPS para outros servicos |
| **014** | Geracao de arquivo RPS para prefeituras sem webservice + recepcao de retorno |
| **007** | Impressao de CTRCs (link no rodape) |
| **008** | Impressao de Subcontratos nao fiscais (link no rodape) |
| **172** | Unificacao de diversos RPS provisorios em um RPS fiscal |
| **388** | Configuracao de clientes com Substituicao Tributaria ou RPS provisorio |
| **401** | Cadastro de unidades — define Inscricao Municipal |
| **402** | Cadastro de aliquotas de ISS por municipio |
| **433** | Livro Fiscal — totais de ISS por municipio |
| **563** | Planilha de tributos — ISS a recolher |
| **903** | Configuracao — certificado digital e modo de envio automatico |
| **920** | Controle de numeracao de series de RPS (prefeituras com webservice) |

## Observacoes e Gotchas

### Regras Fiscais (Lei Complementar 116)
- **Frete municipal (origem = destino)** — SEMPRE tem ISS, independente de filial
- Transportadora e responsavel pelo pagamento do ISS no municipio de prestacao
- Origem do frete = cidade atendida pela transportadora (qualquer unidade) OU cidade da unidade expedidora
- Destino = local de entrega (se existir), NAO necessariamente cidade do destinatario

### Processo de Emissao
- **Impressao define data fiscal** — antes da impressao, e apenas pre-CTRC sem valor operacional
- **RPS so pode ser alterado ANTES da impressao** (opcao 004/rodape)
- **Apos impressao** — so pode ser cancelado (opcao 004/rodape)
- **Um formulario NFPS por unidade** — mesma NFPS para todos os municipios da unidade

### Prefeituras com Webservice (Autorizacao Sincrona)
- **70+ cidades suportadas** (AC, AM, BA, CE, DF, ES, GO, MG, MS, MT, PA, PE, PR, RJ, RO, RS, SC, SP)
- **Conversao automatica RPS → NFS-e** — ocorre na opcao 009 sem uso da opcao 014
- **Numeracao controlada** — opcao 920 com certificado digital
- **Serie obrigatoria** — definida por prefeitura (ex: 001, 003, NF, etc.)
- **Certificado Raiz vs Completo** — maioria aceita certificado com mesma raiz CNPJ; algumas exigem CNPJ completo
- **Credenciais** — algumas prefeituras exigem login/senha alem do certificado (link Credenciais na tela)

### Prefeituras sem Webservice (Modo Assincrono)
- **40+ cidades suportadas** (AP, BA, CE, ES, GO, MA, MG, MS, MT, PA, PB, PI, PR, RJ, RO, RS, SC, SP, TO)
- **Usar opcao 014** — gerar lote, enviar ao portal, receber retorno
- **Impressao suficiente** — RPS impresso ja permite prosseguir operacao
- **Retorno manual** — associar NFS-e via opcao 014 ou opcao 009 (PDF)

### Substituicao Tributaria
- Municipios nao-sede: ISS pago pelo tomador via opcao 402 (todo municipio) ou opcao 388 (por cliente)
- Transportadora descontada do frete ISS pago pelo tomador

### Associacao de PDFs
- **Prefeituras com arquivo multi-PDF** — Manaus/AM e Cariacica/ES (ate 200 NFS-e)
- **Consulta facilitada** — Link direto ao site para baixar PDF (Curitiba, Araucaria, Bento Goncalves, Gravatai, Guaramirim, Paranagua, Rio Do Sul, Sao Bento Do Sul, Timbo)
- **Leitura automatica** — SSW le PDFs e associa ao RPS correspondente

### Modo de Envio
- **Automatico** — configurar em opcao 903/Envio de pre-CTRCs ao SEFAZ
- **Manual** — clicar em Enviar a Prefeitura na opcao 009

### Programas de Integracao
- **SSW**: SSWISSNET, sswNFSeDSF, sswNFSe
- **Terceiros**: IPM Fiscal, ISSNet, Converge.net, Atende.net (conforme prefeitura)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
