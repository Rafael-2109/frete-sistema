# Opção 006 — Emissão de CT-e/CT-e OS em Lote

> **Módulo**: Operacional
> **Páginas de ajuda**: 25 páginas consolidadas (múltiplos padrões EDI e integrações)
> **Atualizado em**: 2026-02-15

## Função

Emissão de CT-es (Conhecimento de Transporte Eletrônico) e CT-e OS (Outros Serviços) em lote, com base em dados recebidos de arquivos EDI, XML de NF-es/CT-es ou romaneios de clientes. A opção 006 é o **ponto central de emissão automática de CTRCs** no SSW, processando documentos importados pela opção 071.

## Quando Usar

- **Emissão em lote de CT-es**: Gerar múltiplos CT-es automaticamente a partir de NF-es/CT-es importadas
- **Clientes com EDI**: Processar arquivos NOTFIS recebidos de embarcadores (PROCEDA, XML, GKO, etc.)
- **CT-e Redespacho Intermediário**: Apontar Manifesto SSW ao receber CT-e de subcontratante
- **CT-e Subcontrato/Redespacho**: Emitir CT-e referenciando CT-e anterior do subcontratante
- **CT-e Reversa**: Após importação de NF-e, emitir CT-e Reversa para coleta
- **CT-e Devolução**: Emitir automaticamente CT-e de devolução invertendo remetente/destinatário
- **Cliente pagador**: Gerar CT-es com base em romaneio do cliente (Mercado Envios)
- **Agrupamento de NF-es**: Consolidar múltiplas NF-es em um único CT-e

## Pré-requisitos

### Importação de Documentos (Opção 071)

Documentos devem estar importados na opção 071, que é o **repositório de NF-es/CT-es** para geração de CTRCs em lote. Formas de importação:

**1. Portal NF-e/CT-e**: SSW busca continuamente nos horários definidos (opção 903/Emissão de CTRCs)

**2. E-mail**:
- XML: Via `xml@ssw.inf.br`
- NOTFIS: Via `notfis.XXX@ssw.inf.br` (XXX = domínio da transportadora)
- Cliente remetente identificado no NOTFIS ou cadastrado como EDI (opção 603)
- Tamanho máximo: 30MB

**3. Arquivo local**: Opção 608 — busca XML direto de pasta no micro

**4. EDI manual**: Opção 600 — importação manual de arquivos NOTFIS

**5. EDI automático**: Opção 603 — configuração de FTP/SFTP, e-mail ou Amazon S3 (A3)

**6. API SSW**: Via token gerado pelo ssw2173 (ex: Click Rodo, CEA Modas)

**7. WebService específico**: Integrações customizadas (ex: AVON, Natura, Loreal)

### Padrões EDI Suportados

| Padrão | Programa | Observação |
|--------|----------|------------|
| PROCEDA 3.0 A | ssw1276 | Arquivo NOTFIS (recebe), CONEMB/OCOREN/DOCCOB (envia) |
| PROCEDA 3.2A SSW RT | ssw3457 | Adequado à Reforma Tributária |
| PROCEDA 4.1 SSW RT | ssw3448 | Adequado à Reforma Tributária, CONEMB/OCOREN |
| PROCEDA 5.0 | ssw2516 | Arquivo NOTFIS |
| PROCEDA 5.1 SSW RT | ssw3458 | Adequado à Reforma Tributária |
| GKO FRETE RT | ssw3464 | Adequado à Reforma Tributária, CONEMB/OCOREN/DOCCOB |
| XML NF-e/CT-e | ssw0866 | Recebe XML de NF-es |
| BRSUPPLY | ssw2074 | Clientes Itaú e Bradesco, agrupamento por E-EDI |

### Configurações Necessárias

- **Tabela de ocorrências** (opção 908): Códigos conforme padrão do embarcador
- **Tabela de volumes** (opção 494): Para clientes que exigem (ex: Natura)
- **Tipo de frete** (opção 485): CIF/FOB, categorias, configurações por cliente
- **Placa de coleta** (opção 026): Para CTRCs gerados com romaneio
- **Conferente** (opção 111): Se controle de conferentes ativado (opção 903)

## Campos / Interface

### Tela da Opção 006 — Emissão em Lote

A interface da opção 006 varia conforme o contexto de uso. As principais variações:

#### 006 - Geração de CTRC com Romaneio

**CNPJ do Pagador**: Cliente **pagador do frete** (subcontratante/redespachador).

**Romaneio**: Número do Romaneio identificando mercadorias entregues pelo cliente.

**Veículo de coleta**: Placa de coleta atribuída aos CT-es sendo gerados.

**Conferente**: Atribuído aos CT-es sendo gerados.

**Rodapé**:
- **Gerar pré-CTRCs**: Gera os pré-CTRCs correspondentes ao Romaneio
- **Gerar pré-CTRCs e pré-Manifesto**: Gera os pré-CTRCs e deixa apontados na placa provisória (coleta) via opção 020

#### 006 - Emissão de CT-es em Lote (EDI)

Tela varia conforme padrão EDI e cliente. Geralmente apresenta:

**Filtros de seleção**:
- Remetente
- Destinatário
- Período de emissão da NF-e
- Código agrupador (para clientes que usam)
- Tipo de documento (NF-e, CT-e anterior)

**Opções de emissão**:
- Emissão simples (1 CTRC por NF-e)
- Agrupamento por critério comercial (pedido, destinatário, recebedor, EDI)
- Agrupamento por critério fiscal (Redespacho Intermediário, Subcontrato, limite 5.000 documentos)
- Rateio de frete entre documentos

**Ações disponíveis**:
- Visualizar documentos a serem processados
- Ajustar dados antes da emissão (opção 071)
- Gerar CT-es em lote
- Visualizar erros de emissão

## Fluxo de Uso

### 1. Fluxo Geral (EDI/XML)

```
Opção 600 → Importar NOTFIS (manual) ou Opção 603 (automático)
↓
Opção 071 → Consultar/ajustar NF-es importadas
↓
Opção 006 → Emitir CT-es em lote
↓
Opção 007 → CT-es autorizados pelo SEFAZ
↓
Opção 600 → Gerar CONEMB/OCOREN/DOCCOB (envio ao cliente)
```

### 2. Fluxo com Romaneio (Cliente Pagador)

```
Cliente → Envia romaneio via WebService
↓
SSW → Gera volumes disponíveis no arquivo
↓
Opção 006 → Buscar romaneio por CNPJ do Pagador + Número
↓
Informar Veículo de coleta + Conferente
↓
Gerar pré-CTRCs ou Gerar pré-CTRCs e pré-Manifesto
↓
Opção 020 → Manifestos ficam disponíveis (se gerou pré-Manifesto)
```

### 3. Fluxo de CT-e Reversa

```
Opção 006 ou 004 → Emitir CT-e Reversa
↓
Opção 215 → Agendar coleta reversa (gera ocorrência SSW 79)
↓
Opção 215 → Comandar veículo para coleta
↓
Opção 215 → Informar coleta realizada (gera ocorrência SSW 78)
```

### 4. Fluxo de CT-e Devolução (Natura)

```
Cliente → Envia NF-e série 003 ou 009 via SFTP
↓
ssw1260 → Reconhece série de devolução
↓
Opção 006 → Emite automaticamente CT-e Devolução invertendo remetente/destinatário
↓
DT (Documento de Transporte) inserido automaticamente
```

### 5. Fluxo de Redespacho Intermediário (Apontar Manifesto SSW)

```
Subcontratante → Envia CT-e via EDI/XML
↓
Opção 071 → CT-e importado como "CT-e anterior"
↓
Opção 006 → Emitir CT-e Redespacho Intermediário
↓
CT-e gerado aponta Manifesto SSW na opção 020
```

## Integração com Outras Opções

### Antes da Emissão

| Opção | Função |
|-------|--------|
| 600 | Importação manual de EDI (NOTFIS, CONEMB, OCOREN, DOCCOB) |
| 603 | Configuração de recebimento automático (FTP/SFTP, e-mail, A3) e envio retroativo (até 30 dias) |
| 608 | Busca de arquivo XML em pasta local |
| 071 | Consulta e ajuste de NF-es/CT-es importadas |
| 908 | Tabela de ocorrências conforme padrão do embarcador |
| 494 | Tabela de volumes (ex: Natura) |
| 485 | Configuração de tipo de frete |
| 903 | Parametrizações gerais (horários de busca Portal NF-e/CT-e, controle de conferentes) |

### Após a Emissão

| Opção | Função |
|-------|--------|
| 007 | Autorização de CT-es no SEFAZ |
| 020 | Manifestos Operacionais (para pré-CTRCs manifestados) |
| 215 | Operacionalização de CT-e Reversa (agendar, comandar, confirmar coleta) |
| 222 | Emissão de CTRC Complementar (Natura: DT manual via e-mail) |
| 379 | Geração automática de CTRCs (alternativa à opção 006) |
| 600 | Geração manual de arquivos de saída (CONEMB, OCOREN, DOCCOB) |
| 101 | Status dos envios de arquivos EDI (link "Arquivos EDI") |
| 602 | Diretório de arquivos EDIs processados (período até 120 dias) |
| 457 | Faturas geradas automaticamente (ex: pré-faturas Natura) |

### Integrações Específicas por Cliente

| Cliente | CNPJ Raiz | Programas | Observação |
|---------|-----------|-----------|------------|
| AVON | 56991441 | ssw1805 (API), ssw2501/ssw2531 (ocorrências) | Emissão via opção 006 |
| AVON 2 / Natura | 7167399 | ssw1260 (NOTFIS SFTP), ssw1905 (CT-e/Faturas WS), ssw1911 (pré-fatura WS), ssw2056 (ocorrências WS) | Emissão EXCLUSIVA via opção 006 para DT. CTRC Complementar (opção 222) requer DT manual. Devolução automática (séries 003/009). |
| Click Rodo (Americanas) | 15121491 | ssw0866 (XML provisório), ssw1864 (NOTFIS API), ssw1690 (ocorrências WS) | Necessário Número do Pedido nos CT-es |
| BRSUPPLY (Itaú/Bradesco) | 03746938, 09216620 | ssw2074 (NOTFIS padrão BRSUPPLY) | Agrupar por E-EDI (consolidador) via opção 006 |
| RTE Rodonaves | 44914992 | ssw2173 API (recebe CT-es), ssw2076 (envia ocorrências), ssw2498/ssw1566 (subcontratada) | Local de início de prestação definido por CNPJ do expedidor |
| CEA Modas | 45242914 | ssw2237 (XML/pré-fatura), ssw1864 (NOTFIS API), ssw2313 (arquivo cobrança) | Após pré-fatura, gerar arquivo de cobrança (ssw2313) |
| Via Varejo / Casas Bahia | 33041260 | ssw3022 (recebe NF-es), ssw3093/ssw2515 (ocorrências/comprovantes), ssw2515 (coleta/laudos) | Laudos de coleta via opção 137. Registrar dados recebedor (nome, documento, parentesco) na entrega |
| Servimed | — | ssw2659 (importa XMLs 00:01h-05:59h), ssw2362 (Comprovei) | Agrupamento automático por código consolidador |
| Loreal | 30278428 | ssw2685 API Neogrid (recebe NF-es, envia CONEMB 3.1, OCORREN 3.1, DOCCOB) | Neogrid: URL, usuário e senha |

## Observações e Gotchas

### Geração Automática de CTRCs

**Objetivo**: Cada documento gravado na opção 071 deve possuir dados suficientes para que a opção 006 (ou opção 379) gere o CTRC **automaticamente**. Normalmente providenciados por programas EDI.

**Premissa**: REGISTRO É AUTOSUFICIENTE — Todos os dados necessários para geração devem estar presentes no REGISTRO.

**Processamento**:

1. **Geração Simples**: 1 CTRC por DOCUMENTO, sem agrupamento nem rateio

2. **Agrupamento de Documentos**:
   - **Comercial**: Por PEDIDO, DESTINATÁRIO, RECEBEDOR, EDI (recebido do cliente)
   - **Fiscal**:
     - Redespacho Intermediário: Gera 1 REGISTRO
     - Subcontrato/Redespacho: Gera 1 REGISTRO para cada DOCUMENTO
     - Limite 5.000 DOCUMENTOs: Gera 1 REGISTRO para cada lote de 5.000 DOCUMENTOS

3. **Rateio de Fretes**:
   - **Cliente**: Critério de rateio por REGISTRO recebido via EDI
   - **Agrupamento**: Rateio entre REGISTROS resultantes do agrupamento (peso, valor, distância, etc.)
   - **Fiscal**: Obedecer limite de 5.000 DOCUMENTOS por REGISTRO. Rateio linear.

### Repositório de Documentos (Opção 071)

**Opção 071 é o repositório**: NF-es/CT-es recebidos por diversos meios são gravados na opção 071 e utilizados para geração de CTRCs em lotes (opção 006 e opção 379).

**Mercado Livre é exceção**: Não tem NF-es/CT-es gravados na opção 071, pois utiliza servidor diferenciado no SSW.

**Tela Inicial da Opção 071**:
- **Uma Nota Fiscal**: Selecionar NF-e ou CT-e por atributo
- **Diversas Notas Fiscais**: Filtrar por remetente, destinatário, período, etc.
  - **Buscar NFs**: Seleciona com filtros
  - **Relatório TXT**: Disponibiliza relatório (informar remetente ou pagador)
  - **Relatório EXCEL**: Idem, em Excel
- **Informar Origem da Prestação**: Para CT-e ainda não autorizado (opção 007), alterar cidade/UF origem. Pode alterar frete e tributação.
- **Selecionar registros para exclusão**: Marcar NF-es/CT-es do período para excluir

**Tela Principal da Opção 071**:
- **Documento origem**: NF (dados da NF-e) ou CT-e anterior (Subcontrato/Redespacho)
- **Remetente**: Cliente vendedor da mercadoria
- **Destinatário**: Cliente comprador da mercadoria
- **Recebedor/Local de Entrega/Redespacho**: Pode ser diferente do destinatário
- **Dados para geração**: Necessários para geração automática via opção 379 (sem opção 006)
- **Demais dados**: Demais campos da NF-e/CT-e

### Arquivos EDI — Envio e Recebimento

**Recebimento automático (Opção 603)**:
- Canais: FTP/SFTP, e-mail, Amazon S3 (A3)
- **Retroativo**: Processar arquivos com até **30 dias** de antecedência (campo "último processamento")

**NOTFIS por e-mail**:
- Cliente envia para `notfis.XXX@ssw.inf.br` (XXX = domínio da transportadora)
- Cliente remetente identificado no NOTFIS (ssw0865)
- Tamanho máximo: 30MB

**Status dos envios (Opção 101)**:
- Link "Arquivos EDI": Acompanhar status dos envios realizados

**Diretório de arquivos processados (Opção 602)**:
- Relaciona EDIs processados no período (até 120 dias)
- Facilita controle e auditoria

**Arquivos de saída gerados (Opção 600)**:
- CONEMB (Conhecimento Embarcados)
- OCOREN (Ocorrências)
- DOCCOB (Documento de Cobrança)

### CT-e Reversa (Opção 215)

**Emissão**: Via opção 006 ou opção 004

**Agendar Coleta**: Opção 215 — grava ocorrência SSW código 79 (opção 405)

**Comandar Coleta para veículo**: Opção 215

**Coleta realizada**: Opção 215 — grava ocorrência SSW código 78 (opção 405). Informar:
- Chave DACTE
- Lacre (se utilizado no kit de coleta reversa)
- Entregue por (nome da pessoa)
- Data/hora

**Alternativa — Módulo Coleta**: Iniciar pela opção 001 e depois emitir CT-e Reversa. Vantagem: CT-e só emitido se coleta tiver sucesso.

### CT-e Redespacho Intermediário — Apontar Manifesto SSW

**Processo**:
1. Transportadora parceira emite CT-e e envia arquivo
2. Subcontratada (usuária do SSW) recebe CT-e via EDI/XML
3. CT-e importado na opção 071 como "CT-e anterior"
4. Opção 006 emite CT-e Redespacho Intermediário
5. CT-e gerado aponta Manifesto SSW gerado pela opção 020

**Uso**: Permite subcontratada manifestar carga recebida de parceiro.

### Clientes com Requisitos Especiais

**Natura**:
- TMATRIZ e TFILIAL (Documento de Transporte) necessários para ajustes no ssw1260
- Tabela de Volumes (opção 494) deve ser configurada
- Tabela de ocorrências configurada pela Equipe SSW
- **Emissão EXCLUSIVA via opção 006** para inserir DT automaticamente
- CTRC Complementar (opção 222): DT manual, obtido da Natura por e-mail
- CTRC Devolução: ssw1260 reconhece séries NF-e 003 e 009, inverte remetente/destinatário automaticamente
- Pré-faturas importadas geram faturas automaticamente (opção 457). Erros na opção 602.

**BRSUPPLY (Itaú/Bradesco)**:
- CT-es devem ser gerados pela opção 006 agrupados por E-EDI (consolidador)
- Gera um único CT-e agrupando NF Venda e NF Remessa
- Código agrupador enviado no NOTFIS

**Via Varejo / Casas Bahia**:
- Laudos de coleta devem ser anexados nas ordens de coleta reversa (opção 137)
- Na entrega, registrar dados do recebedor (nome, documento e parentesco)

**Servimed**:
- Importa XMLs das DANFEs no período de 00:01h a 05:59h
- CNPJ raiz 61.230.314: Peso real = tag `<pesoL>` / 1000. NFs com código consolidador agrupados automaticamente.
- CNPJ raiz 44.463.156: Para alguns CNPJs destinatários, agrupamento nunca ocorre.

**Rodonaves**:
- Local de início de prestação definido pelo CNPJ do expedidor
- Subcontratada: Envia dados do manifesto (ssw2498), dados dos volumes (ssw2076) e ocorrências (ssw1566)

### Padrões EDI e Reforma Tributária

**Padrões atualizados para RT**:
- PROCEDA 3.2A SSW RT (ssw3457)
- PROCEDA 4.1 SSW RT (ssw3448)
- PROCEDA 5.1 SSW RT (ssw3458)
- GKO FRETE RT (ssw3464)

**Conformidade**: Garantem conformidade com exigências fiscais vigentes da Reforma Tributária, mantendo integridade dos processos de integração eletrônica.

**Download de layouts**: Links disponíveis nas ajudas específicas de cada padrão.

### Limitações e Configurações

**Tamanho de arquivo**: E-mail com XML/NOTFIS não deve ultrapassar 30MB.

**Limite de documentos**: 5.000 documentos por REGISTRO em agrupamento fiscal. Acima disso, rateio linear entre lotes.

**Portal NF-e/CT-e**: SSW busca continuamente nos horários definidos (opção 903/Emissão de CTRCs).

**Mercado Livre**: Usa servidor diferenciado, não grava na opção 071.

**Origem da Prestação (Opção 071)**: Para CT-e ainda não autorizado (opção 007), pode alterar cidade/UF origem. Alteração pode impactar frete e tributação.

**Exclusão de registros (Opção 071)**: Selecionar registros emitidos no período para marcar os que devem ser excluídos.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
