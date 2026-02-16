# Opção 101 — Resultado/Consulta CTRC

> **Módulo**: Comercial
> **Páginas de ajuda**: 22 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Consulta completa de CTRCs com análise de resultado comercial, indicadores de gestão (atrasados, prejuízo, desconto NTC) e integrações EDI/API. Interface principal para análise de desempenho operacional e comercial da transportadora.

## Quando Usar

- **Análise de resultado**: Verificar lucro/prejuízo de CTRCs (opção 101/Resultado)
- **Indicadores de gestão**: Monitorar atrasados de entrega, CTRCs com prejuízo, desconto sobre NTC
- **Conferência de armazém**: Identificar sobras e faltas (opção 149)
- **Reembolsos**: Situação de reembolsos (opção 105)
- **Integrações**: Monitorar envios EDI/API via link "Arquivos EDI"

**Para consulta rápida/simplificada**: Use opção 102 (critérios básicos, interface leve)

## Pré-requisitos

### Configurações Necessárias
- **Resultado comercial**: Custos de transferência (opção 403), comissões (opção 408), seguro/GRIS (opção 903)
- **Tabela Genérica NTC**: Opção 427 (cálculo de desconto sobre NTC)
- **Parâmetros de frete**: Opção 062 (desconto máximo, resultado comercial mínimo)
- **Big Brother**: Opção 145 (mobilização gerencial, opcional)

### Permissões e Restrições
- **MTZ (Matriz)**: Visualiza todas as unidades
- **Unidade**: Visualiza apenas seus CTRCs
- **Agência/Parceiro**: Acesso limitado a CTRCs em que é origem/destino
- **Indicadores no Menu Principal**: Atrasados de entrega, Valor do prejuízo (atualizados de hora em hora)

## Campos / Interface

### Link "Resultado" (Opção 101/Resultado)

Detalhamento do resultado comercial e real do CTRC.

#### Composição de Receita

| Campo | Descrição |
|-------|-----------|
| **FRETE** | Valor total do frete (Base de Cálculo, opção 392) |

#### Composição de Despesa

| Campo | Descrição | Base de Cálculo |
|-------|-----------|-----------------|
| **ICMS** | Valor do ICMS destacado no CTRC | Opção 392/TRIBUTAÇÃO |
| **PIS COFINS** | Valor de PIS/COFINS | Opção 903/OUTROS |
| **SEGURO** | Custo do seguro (% sobre valor mercadoria) | Opção 903/OUTROS. **Não considerado** em Subcontratos (seguro é da subcontratante) |
| **GRIS** | Custo de gerenciamento de risco (% valor mercadoria) | Opção 903/OUTROS |
| **PEDÁGIO** | **Não há parcela separada** (incluído em TRANSFERÊNCIA) | - |
| **EXPED** | Comissão de expedição | Opção 408 |
| **TRANSFER** | Valor proporcional de transferência | Opção 403 (ROTA) ou opção 903 (transportadora) |
| **TRANSBOR** | Comissão de transbordo | Opção 408 ou opção 401 (alternativa) |
| **RECEPÇÃO** | Comissão de recepção | Opção 408 |
| **DESP DIV** | Despesas especiais do CTRC | Opção 475 (Contas a Pagar) |

#### Indicadores de Resultado

| Campo | Fórmula | Observações |
|-------|---------|-------------|
| **RESULTADO** | FRETE - (ICMS + PIS COFINS + SEGURO + GRIS + EXPED + TRANSFER + TRANSBOR + RECEPÇÃO + DESP DIV) | Valor negativo = prejuízo |
| **RC (Resultado Comercial)** | (RESULTADO / FRETE) * 100 | Percentual de lucro sobre receita |

### Relatórios de Indicadores

#### Relatórios 010 e 011 — CTRCs Atrasados de Entrega

**Principal indicador de satisfação do cliente**

| Relatório | Agrupamento | Uso Recomendado |
|-----------|-------------|-----------------|
| **010** | Por unidade origem | Análise de origem |
| **011** | Por unidade destino | **Referência para avaliar atrasos da transportadora** |

**Relatórios complementares (FEC/Devolução/Reversa):**
| Relatório | Descrição |
|-----------|-----------|
| **014** | FEC e Devolução por unidade origem |
| **015** | FEC e Devolução por unidade destino |

**Critérios de seleção:**
- CTRCs emitidos nos últimos **90 dias**
- Sem FEC, Devolução, Reversa (exceto relatórios 014/015)
- Processamento: **hora em hora**
- Previsão de entrega: calculada conforme opção 101 (ver CLAUDE.md ou documentação oficial)

**Colunas do relatório:**

| Coluna | Descrição |
|--------|-----------|
| **CTRC** | Número do CTRC/Subcontrato (caractere indica tipo — opção 004) |
| **PREVETR** | Data de previsão de entrega (opção 101) |
| **ATR** | Dias de atraso em relação a HOJE |
| **LOC ATUAL** | Localização atual (domínio + unidade). MANIFE/ROMANE = em trânsito. SEGREG = segregado (opção 091) |
| **OCORRENCIA** | Última ocorrência (domínio, unidade, data, código, descrição). `*` = **RESPONSABILIDADE DO CLIENTE** |
| **PERM** | Dias de permanência na unidade do relatório (desde autorização CT-e ou chegada veículo). Não medido se CTRC em outra unidade |

**Resumos ao final:**
- **Quantidade de CTRCs por unidade** (MTZ)
- **Quantidade de CTRCs por dias de atraso**
  - **Atrasos >10 dias**: Alta chance de virar conta a pagar (indenização)
- **Quantidade de CTRCs por ocorrência**
- **Quantidade de CTRCs por cliente (>3)**
- **Possíveis clientes cobrando mercadorias não entregues** (MTZ)
  - Despesas pagas (opção 477) cujo fornecedor é cliente com CTRCs atrasados
  - Critérios: CNPJ raiz coincide, últimos 90 dias, não é Debita Veículo, não é modelo 57/99
  - **Alerta**: "Se atrasados não resolvidos, Contas a Pagar aumenta"

**Indicador no Menu Principal:** Quantidade de CTRCs atrasados de entrega (atualizado de hora em hora, por unidade destino)

**Opções complementares:**
- **Opção 108**: Sistematizar resolução de causas
- **Opção 145 (Big Brother)**: Mobilizar equipe gerencial
- **Opção 150**: Versão com filtros personalizados (unidade, tipo, período, Excel)

#### Relatório 031 — CTRCs com Prejuízo

**"CTRC tem que dar LUCRO. Nenhuma transportadora quebrou com armazém vazio, mas cheio de CTRCs com prejuízo."**

**Critérios:**
- CTRCs emitidos **ontem**
- Resultado Comercial **negativo**
- Cada unidade vê o seu, MTZ vê todas

**Colunas:**

| Coluna | Descrição |
|--------|-----------|
| **ROTA** | Unidade origem - praça destino |
| **TABELA** | Tipo de tabela (PERC, COMB, INFO, COTA, etc.) + dia/mês vencimento. **VENCID** se vencida |
| **FRETE-R$ (A)** | Valor do frete do CTRC |
| **DESP-R$ (B)** | Despesas do CTRC (opção 101/Resultado) |
| **RES-% (C=A-B)** | Resultado Comercial (opção 101/Resultado) |
| **RESM-%** | Resultado Comercial Mínimo (opção 062) |
| **DIF-%** | Diferença entre RES e RESM |

**Indicador no Menu Principal:** Valor do prejuízo (somatória coluna C dos CTRCs com RC negativo)

**Opções complementares:**
- **Opção 449**: Resultados por cliente
- **Opção 062**: Parâmetros mínimos (Desconto NTC, RC Mínimo)
- **Opção 145 (Big Brother)**: Mobilização gerencial

#### Relatório 030 — CTRCs com Desconto NTC Excedido

**Critérios:**
- CTRCs emitidos **ontem**
- Desconto sobre NTC > Desconto Máximo (opção 062)

**Colunas:**

| Coluna | Descrição |
|--------|-----------|
| **ROTA** | Unidade origem - praça destino |
| **TABELA** | Tipo + vencimento (VENCID se vencida) |
| **FRETE-R$** | Valor do frete do CTRC |
| **FRTNTC-R$** | Frete calculado pela Tabela Genérica (opção 427) |
| **DESC-%** | Percentual de desconto do FRETE em relação ao FRTNTC |
| **DESM-%** | Percentual máximo de desconto (opção 062) |
| **DIF-%** | DESC - DMAX. **Quanto maior, pior o frete** |

**Relatório lista apenas CTRCs com DESC > DMAX**

#### Relatório 032 — Verificação de Frete Calculado pelo Cliente

**Critérios:**
- CTRCs emitidos **ontem**
- Frete vindo do EDI divergente do calculado pelo SSW

**Colunas:**

| Coluna | Descrição |
|--------|-----------|
| **ROTA** | Unidade origem - praça destino |
| **(A) FRT CALC** | Frete calculado pelas tabelas do cliente (SSW) |
| **(B) FRT EDI** | Frete importado do EDI (usado no CTRC) |
| **B-A** | Diferença entre FRT EDI e FRT CALC |

**Relatório lista apenas CTRCs com diferença (sem diferença = não relacionado)**

#### Relatórios 166 e 167 — Resultado Comercial da Unidade

**Diferença entre opção 166 e opção 168:**
- **Relatório 166** (opção 056): Receita = fretes, Despesa = comissões + custos transferência. **Útil para avaliar resultado de cliente**
- **Relatório 168** (opção 056): Receita = serviços prestados, Despesa = Contas a Pagar. **Útil para avaliar resultado da unidade**

| Relatório | Descrição |
|-----------|-----------|
| **166** | CTRCs por unidade recebedora do frete (CIF na origem, FOB no destino). Receitas = fretes pagos, Despesas = comissões (opção 408) + custos transferência (opção 403) |
| **167** | Resumo do relatório 166 por unidade recebedora |

**Linha TOTAIS DA UNIDADE exibe: Resultado Comercial da Unidade em percentual**

**Modelo de resultado: Conforme SSW (opção 101/Resultado)**

### Opção 105 — Situação dos Reembolsos

**Campos:**

| Campo | Descrição |
|-------|-----------|
| **EMISSÃO DOS CTRCS** | Período de emissão para consulta |
| **SITUAÇÃO** | P = Pendentes, E = Entregues, A = Ambos |
| **CNPJ REMETENTE (OPC)** | Filtro por remetente (opcional) |

**Observações:**
- Situação de reembolso de CTRC específico: opção 101 (link no rodapé)
- Entrega de reembolso ao cliente: opção 054 (confirmação de entrega de Capa de Cheques)
- Tutorial completo: ssw0147.htm (Reembolso da mercadoria ao cliente)

### Opção 149 — Conferência do Armazém

**Processo:**
- Confere volumes físicos do armazém vs relatórios SSW
- **Sobras**: Volumes capturados com localização SSW em outra unidade (instrução gravada em opção 101/Ocorrências, **sem código**)
- **Faltas**: Volumes não localizados fisicamente mas com localização SSW na unidade (instrução gravada, **sem código**)

**Campos:**

| Campo | Descrição |
|-------|-----------|
| **INICIAR CONFERÊNCIA** | Inicia conferência (desabilitado após clicar) |
| **FINALIZAR CONFERÊNCIA** | Encerra conferência (habilitado após iniciar, apenas para usuário iniciador ou master). Grava instruções de faltas/sobras, **não grava ocorrências com código** |
| **CAPTURA CB DO VOLUME** | Código de barras do volume. Se NR do SSW não reconhecido, verifica Código do Cliente (sem máscara — opção 388) |
| **ÚLTIMO CB** | Última etiqueta conferida |
| **TOTAL VOLUMES CAPTURADOS** | Quantidade conferida até o momento |
| **ATUALIZAR** | Atualiza contagem de volumes |

**Relatórios:**

| Campo | Descrição |
|-------|-----------|
| **SITUAÇÃO DOS CTRCS** | F = Falta, S = Sobra, T = Ambos |
| **SETOR(ES)** | Filtro por setor (opção 404) |
| **UNIDADE(S) DE DESTINO** | Filtro por unidade destino |
| **SÓ DESCARREGADOS** | Apenas descarregados (opções 078, 064) |

**Rodapé:**

| Link | Descrição |
|------|-----------|
| **DISPONÍVEIS PARA TRANSFERÊNCIA** | CTRCs disponíveis para transferência (opção 019) + volumes capturados |
| **DISPONÍVEIS PARA ENTREGA** | CTRCs disponíveis para entrega (opção 081) + volumes capturados |
| **SEGREGADOS** | CTRCs segregados (opção 091) + volumes capturados |

**Observações:**
- Sobras/faltas indicam falhas em processos operacionais
- Necessário identificar causas e corrigir

### Opção 115 — Atualizar Dados da DANFE

Complementa dados faltantes de DANFEs antes da geração de CTRCs.

**Funções:**

| Função | Descrição |
|--------|-----------|
| **Atualizar NR1 e NR2** | Etiquetas sequenciais grudadas nos volumes. Permite descarga no SSWBar. Se NR1/NR2 tem 6-8 dígitos (gráfica), gravados como Código do Cliente (opção 101/DANFEs/NR). Captura via SSWMobile 5 |
| **Atualizar Data de Emissão da NF-e** | Complementa data de emissão |
| **Atualizar Data de Emissão NF-e/CFOP** | Complementa data + CFOP |
| **Atualizar Data de Emissão/CFOP/IE Substituto/NR1 e NR2** | Complementa 4 campos |
| **Atualizar chave da NF-e** | Complementa chave de acesso (CTRCs gerados via EDI sem chave). Chave possui CNPJ + NF → associação automática com CTRC |
| **Atualiza nº Pedido** | Importa arquivo CSV (2 colunas: chave DANFE + Pedido) |
| **Atualiza Código do Cliente (arquivo)** | CSV com 1 linha por volume. Coluna A = chave NF-e (mesma para todos volumes), Coluna B = Código do Cliente (do volume). Útil quando código não disponível na emissão |
| **Palete** | NF-es peletizadas recebem mesmo Código do Cliente (= pallet). SSWBar emite todas etiquetas do pallet de uma vez (função 1-Descarga Coleta) |

### Link "Arquivos EDI" (Opção 101/Rodapé)

Mostra arquivos EDIs incluindo o CTRC + status de envios.

**Integrações monitoradas:**
- Opção 117: WS rejeitados (últimos 3 meses)
- Opção 602: CT-es importados + download (até 90 dias)
- Opção 605: Arquivos JSON gerados/transmitidos (retransmissões, conferências)

**Integrações EDI/API documentadas:**

| Integração | Função | Observações |
|------------|--------|-------------|
| **ssw2166 (MULTISOFTWARE)** | Função 1: Importa CT-es, Função 2: Recebe NOTFIS (opção 071), Função 3: Envia ocorrências, Função 4: Envia XML CT-e (base64), Função 5: Recebe pedidos | CNPJs diversos embarcadores. CT-es já autorizados SEFAZ, disponíveis para transferência (opção 019). Emissões via opção 006 exclusivamente. Tabela ocorrências: opção 908 |
| **ssw2475 (VM2)** | Função 1: Envia comprovante entrega (base64), Função 2: Envia ocorrências | Modo automático. Ocorrências mapeadas: SSW 01=Entregue, 80=Material origem, 82=Em trânsito, 83=Chegada filial, 85=Em rota entrega |
| **ssw3061 (GRUPO BOTICÁRIO - MULTISOFTWARE - SAP H4NA)** | Função 1: Importa CT-es, Função 2: Consulta SAP HANA (NP → códigos barras), Função 3: Recebe NP via `<b:ProcImportacao>` (Cálamo/Interbelle Regional), Função 4: Recebe NP via `<b:NumeroPedidoEmbarcador>` (entrega direta CD) | CNPJs: 11137051, 77388007, 06147451, 42772439, 48035029. 3 processos de leitura etiqueta. NP opcional mas requerido para leitura etiquetas |
| **ssw3075 (FROTIX)** | Envia ocorrências (eventos) | Modo automático. Sem tabela padrão (requer DEPARA customizado). Reenvio até 30 dias |
| **ssw3085 (INFORDOCS)** | Envia comprovantes entrega | Modo automático. Individual por chave NF-e (repete imagem se CTRC com NF-es agrupadas). Reenvio até 30 dias |
| **ssw3144 (EASYDOC)** | Envia comprovantes entrega (base64) | Webservice automático. Requer URL/usuário/token |
| **ssw3189 (XML CTE BASE64 PADRAO SSW)** | Envia XML CT-e (base64) via POST | Formato XML ou JSON (escolha do cliente). Reenvio até 30 dias. Manual: webserviceXmlCteBase64.html |
| **ssw3285 (CANHOTO FACIL)** | Envia comprovantes entrega | Modo automático. Reenvio até 30 dias |
| **ssw3348 (ALL POST)** | Envia XML CT-e | Modo automático. Individual, XML, sem compactação. Reenvio até 30 dias |
| **ssw3400 (DHL)** | Envia comprovantes entrega (base64) | CNPJs raiz: 00233065, 02836056. Webservice automático |
| **ssw3415 (UNITRAC)** | Envia romaneio + CTRCs (JSON) | Disparo na ocorrência 85 (SAIDA PARA ENTREGA) |
| **ssw3473 (TIM)** | Envia comprovantes entrega | CNPJ raiz: 02421421. Formatos: image/jpeg, image/png, application/pdf. Webservice automático |

**Todos suportam:**
- Opção 101/Arquivos EDI: Status de envios
- Opção 117: WS rejeitados (3 meses)
- Opção 605: Arquivos JSON (retransmissões/conferências)
- Reenvio: Solicitar via edi@ssw.inf.br

### Opção 903/Outros — Parâmetros Gerais

Parâmetros usados no cálculo de resultado (opção 101/Resultado).

| Parâmetro | Descrição | Uso |
|-----------|-----------|-----|
| **Custo seguro (%)** | Percentual sobre valor mercadoria | Resultado Real/Comercial (opção 101/Resultado) |
| **Custo GRIS (% valor mercadoria)** | Gerenciamento de risco | Resultado Real/Comercial (opção 101/Resultado) |
| **Paga comissão para cotação (opção 068) sobre CTRCs** | E = emitido, L = liquidado | Comissionamento |
| **Retirar ICMS da b cálculo da remun agregados** | S = retira ICMS | Remuneração (opção 409) |
| **Reter Previdência Social dos carreteiros** | S = retém (apenas PJ — opção 027) | CTRBs (opções 072, 075, 118) |
| **Reter SEST/SENAT dos carreteiros** | S = retém (apenas PF — opção 027) | CTRBs (opções 072, 075, 118) |
| **Controle orçamentário** | S = obedece limite (opção 380) | Lançamento despesas (opção 475) |
| **Aprovação centralizada de despesas** | S = requer aprovação (opção 560) para liquidação (opção 476). Valor "a partir de" obrigatório | Contas a Pagar |
| **Aprovação centralizada de pedidos** | S = pedidos (opção 158) requerem aprovação (opção 169) para envio e-mail | Gestão de pedidos |
| **Data de retenção das despesas** | DDMMAA. A partir desta data, retenções geram lançamentos próprios | Despesas (opção 475) |
| **CNPJ tag autXML** | Até 3 CNPJs (só números, separados por `;`) | Tag autXML do CT-e. CNPJs podem baixar XML com certificado próprio. Não podem ser remetente/destinatário/pagador |

## Fluxo de Uso

### 1. Análise de Resultado de CTRC
```
1. Consultar CTRC (opção 101 ou 102)
2. Clicar "Resultado" (rodapé)
3. Verificar composição FRETE - DESPESAS
4. Analisar RC (Resultado Comercial %)
5. Comparar com RC Mínimo (opção 062)
```

### 2. Monitoramento de Atrasados de Entrega
```
1. Acessar relatório 011 (opção 056) — referência para avaliar transportadora
2. Analisar colunas: PREVETR, ATR, LOC ATUAL, OCORRENCIA, PERM
3. Identificar CTRCs com ATR >10 dias (risco de indenização)
4. Verificar resumos: por unidade, dias de atraso, ocorrência, cliente
5. Usar opção 108 para sistematizar resolução
6. Ativar Big Brother (opção 145) se necessário
```

### 3. Análise de CTRCs com Prejuízo
```
1. Acessar relatório 031 (opção 056) — CTRCs de ontem
2. Verificar colunas: ROTA, TABELA, FRETE, DESP, RES, RESM, DIF
3. Identificar CTRCs com RES negativo
4. Verificar se TABELA está VENCID
5. Analisar DIF (quanto abaixo do RC Mínimo)
6. Consultar opção 449 para resultado por cliente
7. Ajustar parâmetros (opção 062) se necessário
```

### 4. Conferência de Armazém (Opção 149)
```
1. Clicar "INICIAR CONFERÊNCIA"
2. Capturar códigos de barras dos volumes (campo "CAPTURA CB DO VOLUME")
3. Monitorar "TOTAL VOLUMES CAPTURADOS"
4. Clicar "ATUALIZAR" periodicamente
5. Gerar relatórios: SITUAÇÃO (F/S/T), filtrar por SETOR/UNIDADE/DESCARREGADOS
6. Verificar links rodapé: DISPONÍVEIS TRANSFERÊNCIA/ENTREGA, SEGREGADOS
7. Clicar "FINALIZAR CONFERÊNCIA" (usuário iniciador ou master)
8. Instruções de sobras/faltas gravadas em opção 101/Ocorrências (sem código)
9. Investigar causas e corrigir processos
```

### 5. Monitoramento de Integrações EDI/API
```
1. Consultar CTRC (opção 101)
2. Clicar "Arquivos EDI" (rodapé)
3. Verificar status de envios (OK/Erro)
4. Se erro: opção 117 (WS rejeitados, últimos 3 meses)
5. Conferência: opção 605 (arquivos JSON gerados/transmitidos)
6. Reenvio: solicitar via edi@ssw.inf.br (até 30 dias)
```

### 6. Atualização de Dados DANFE (Opção 115)
```
1. Acessar opção 115
2. Escolher função: NR1/NR2, Data NF-e, CFOP, chave NF-e, Pedido, Código Cliente
3. Para Código Cliente: preparar CSV (coluna A = chave NF-e, coluna B = Código)
4. Para Pedido: preparar CSV (2 colunas: chave DANFE + Pedido)
5. Importar arquivo
6. Verificar CTRCs atualizados (opção 101/DANFEs/NR)
```

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| **004** | Emissão CTRC (tipo de documento, observação) |
| **006** | Emissão lote (integrações MULTISOFTWARE) |
| **007** | Autorização CT-e |
| **019** | Disponível para transferência (CT-es importados) |
| **023** | Consulta Manifestos (link "CTRCs do Manifesto" usa opção 101) |
| **027** | Cadastro proprietário veículo (PF/PJ, retenção SEST/SENAT/Previdência) |
| **030** | Chegada veículo (inicia contagem PERM) |
| **033** | Ocorrências (histórico completo, instruções) |
| **054** | Entrega reembolso ao cliente (confirmação Capa Cheques) |
| **056** | Relatórios diários (010, 011, 014, 015, 031, 030, 032, 166, 167, 168) |
| **062** | Parâmetros mínimos (Desconto NTC, RC Mínimo) |
| **064** | Descarga (conferência armazém) |
| **068** | Cotação (comissão) |
| **070** | Capa Canhoto NF |
| **071** | DANFEs importadas (MULTISOFTWARE) |
| **072, 075, 118** | CTRBs (retenção SEST/SENAT/Previdência) |
| **078** | Descarga (conferência armazém) |
| **081** | Disponível para entrega (conferência armazém) |
| **082** | Capa Comprovante Externo |
| **084** | Informar peso/cubagem |
| **091** | Segregação (LOC ATUAL, conferência armazém) |
| **100** | E-mail marketing |
| **102** | Consulta CTRC simplificada |
| **104** | Fatura/liquidação |
| **105** | Situação reembolsos |
| **108** | Sistematizar resolução de atrasados |
| **115** | Atualizar dados DANFE |
| **117** | WS rejeitados (3 meses) |
| **145** | Big Brother (mobilização gerencial) |
| **148** | Resultados balança/cubadora |
| **149** | Conferência armazém |
| **150** | CTRCs atrasados (filtros personalizados) |
| **158** | Pedidos (aprovação centralizada) |
| **169** | Aprovação pedidos |
| **380** | Orçamento (controle orçamentário) |
| **388** | Configuração cliente (máscara Código Cliente) |
| **392** | Composição frete (Base Cálculo, TRIBUTAÇÃO) |
| **401** | Cadastro unidade (comissão transbordo alternativa) |
| **403** | Distância unidades (custo transferência ROTA) |
| **404** | Setor entrega (conferência armazém) |
| **408** | Comissões (expedição, transbordo, recepção) |
| **409** | Remuneração agregados |
| **427** | Tabela Genérica NTC (cálculo desconto) |
| **449** | Resultado por cliente |
| **475** | Contas a Pagar (DESP DIV, controle orçamentário, aprovação centralizada, data retenção) |
| **476** | Liquidação despesas (aprovação centralizada) |
| **477** | Despesas pagas (clientes cobrando mercadorias) |
| **483** | Cadastro cliente |
| **560** | Aprovação despesas |
| **600** | Importação CT-e externo (MULTISOFTWARE) |
| **602** | CT-es importados + download (90 dias) |
| **605** | Arquivos JSON (retransmissões/conferências) |
| **903** | Parâmetros gerais (seguro, GRIS, PIS/COFINS, controles, autXML) |
| **908** | Tabela ocorrências (MULTISOFTWARE) |

## Observações e Gotchas

### Resultado Comercial

#### Modelo de Cálculo SSW
- **Receita**: FRETE (Base de Cálculo, opção 392)
- **Despesa**: ICMS + PIS COFINS + SEGURO + GRIS + EXPED + TRANSFER + TRANSBOR + RECEPÇÃO + DESP DIV
- **Resultado**: FRETE - DESPESAS (negativo = prejuízo)
- **RC%**: (Resultado / FRETE) * 100

#### Seguro e GRIS
- **Seguro**: Percentual sobre valor mercadoria (opção 903/Outros)
- **GRIS**: Percentual sobre valor mercadoria (opção 903/Outros)
- **Subcontratos**: Seguro **não considerado** (responsabilidade da subcontratante)

#### Pedágio
- **Não há parcela separada** no Resultado Comercial
- Custo incluído em **TRANSFERÊNCIA** (opção 403)

#### PIS/COFINS
- Calculado com base em opção 903/OUTROS
- Se não importado de documento anterior, usa opção 903

#### Transferência
- **Prioridade**: ROTA (opção 403) > transportadora (opção 903)
- Valor proporcional ao custo médio cadastrado

#### Comissões
- **Expedição**: Opção 408
- **Transbordo**: Opção 408 ou opção 401 (alternativa)
- **Recepção**: Opção 408

#### Despesas Diversas
- Lançadas no Contas a Pagar (opção 475)
- Despesas **específicas do CTRC**
- Repassadas ao CTRC no cálculo de resultado

### Indicadores de Gestão

#### Atrasados de Entrega
- **Principal indicador de satisfação do cliente**
- **Processamento**: Hora em hora
- **CTRCs considerados**: Emitidos nos últimos 90 dias, sem FEC/Devolução/Reversa (exceto relatórios 014/015)
- **Previsão de entrega**: Calculada conforme documentação oficial (ver CLAUDE.md ou opção 101)
- **Atrasos >10 dias**: Alta chance de indenização
- **Responsabilidade cliente**: Identificada com `*` na coluna OCORRENCIA
- **Permanência (PERM)**: Contada desde autorização CT-e (opção 007) ou chegada veículo (opção 030). Não medida se CTRC em outra unidade

#### CTRCs com Prejuízo
- **Processamento**: Diário (CTRCs de ontem)
- **Critério**: Resultado Comercial negativo
- **Indicador no Menu Principal**: Valor do prejuízo (soma dos RC negativos)
- **Alerta**: "CTRC tem que dar LUCRO. Nenhuma transportadora quebrou com armazém vazio, mas cheio de CTRCs com prejuízo."

#### Desconto sobre NTC
- **Processamento**: Diário (CTRCs de ontem)
- **Critério**: DESC% > DESM% (opção 062)
- **Cálculo**: DESC% = (FRETE / FRTNTC) * 100
- **FRTNTC**: Frete calculado pela Tabela Genérica (opção 427)
- **DIF%**: Quanto maior, pior o frete

#### Frete Calculado pelo Cliente
- **Processamento**: Diário (CTRCs de ontem)
- **Critério**: FRT EDI (importado) ≠ FRT CALC (SSW)
- **Relatório**: Lista apenas divergências (sem divergência = não relacionado)

#### Possíveis Clientes Cobrando Mercadorias
- **Apenas MTZ**
- **Fonte**: Despesas pagas (opção 477) cujo fornecedor é cliente com CTRCs atrasados
- **Critérios despesa**:
  - CNPJ raiz coincide com cliente atrasado
  - Últimos 90 dias (processos de indenização demorados)
  - Não é Debita Veículo
  - Não é modelo 57 (CT-e) ou 99 (NFS)
- **Alerta**: "Se atrasados não resolvidos, Contas a Pagar aumenta"

### Conferência de Armazém (Opção 149)

#### Sobras
- Volumes capturados com **localização SSW em outra unidade**
- Instrução gravada em opção 101/Ocorrências (**sem código**)
- **Indicam falhas em processos operacionais**

#### Faltas
- Volumes **não localizados fisicamente** mas com localização SSW na unidade
- Instrução gravada em opção 101/Ocorrências (**sem código**)
- **Indicam falhas em processos operacionais**

#### Etiquetas do Cliente
- Se NR do SSW não reconhecido, verifica Código do Cliente (opção 101/DANFEs/NRs)
- Máscara **não usada** (opção 388)

#### Finalização
- Apenas usuário iniciador ou **master** pode finalizar
- Instruções gravadas, **ocorrências com código NÃO gravadas**

### Integrações EDI/API

#### CT-es Importados (MULTISOFTWARE, Grupo Boticário)
- **Já autorizados SEFAZ** ao importar
- Disponíveis para transferência (opção 019)
- Emissões **exclusivamente** via opção 006
- Link "Ocorrências" identifica: "XML do CT-e importado de sistema externo"

#### Grupo Boticário — 3 Processos de Leitura Etiqueta
1. **SAP HANA**: NP enviado → retorna código de barras
2. **Cálamo/Interbelle Regional**: NP na tag `<b:ProcImportacao>` → código = NP + volume (4 dígitos) + total (4 dígitos)
3. **Entrega direta CD**: NP na tag `<b:NumeroPedidoEmbarcador>` → código = mesma composição

**NP opcional mas requerido para leitura de etiquetas**

#### FROTIX
- Sem tabela padrão de ocorrências (eventos)
- **Requer DEPARA customizado** (transportadora envia para edi@ssw.inf.br)

#### INFORDOCS
- Envio **individual por chave NF-e**
- Se CTRC com NF-es agrupadas: **repete imagem do comprovante** para cada NF-e

#### TIM
- Formatos de comprovante: **image/jpeg, image/png, application/pdf**

#### UNITRAC
- Disparo: Ocorrência **85 - SAIDA PARA ENTREGA**
- Formato: JSON (romaneio + CTRCs)

#### Reenvio de Integrações
- **Prazo**: Até 30 dias
- **Solicitação**: edi@ssw.inf.br

### Opção 115 — Atualizar Dados DANFE

#### NR1/NR2
- Etiquetas sequenciais **grudadas nos volumes**
- Permite descarga no SSWBar
- **Captura via SSWMobile 5**
- Se 6-8 dígitos (gráfica): gravados como **Código do Cliente** (opção 101/DANFEs/NR)

#### Chave NF-e
- Complementa CTRCs gerados via EDI **sem chave**
- Chave possui CNPJ + NF → **associação automática** com CTRC

#### Código do Cliente (Arquivo)
- CSV: 1 linha por volume
- Coluna A = chave NF-e (mesma para todos volumes)
- Coluna B = Código do Cliente (do volume)
- **Útil quando código não disponível na emissão**

#### Palete
- NF-es peletizadas recebem **mesmo Código do Cliente** (= código do pallet)
- SSWBar emite todas etiquetas do pallet de uma vez (função 1-Descarga Coleta)

### Opção 903/Outros

#### Tag autXML
- Até **3 CNPJs** (só números, separados por `;`)
- CNPJs podem baixar XML do CT-e com certificado próprio
- **Não podem ser** remetente/destinatário/pagador
- Exemplo: Escritórios de contabilidade

#### Retenções (SEST/SENAT/Previdência)
- **SEST/SENAT**: Apenas PF (opção 027)
- **Previdência**: Apenas PJ (opção 027)
- CTRBs: Opções 072, 075, 118

#### Aprovação Centralizada de Despesas
- Se ativado: despesas requerem aprovação (opção 560) para liquidação (opção 476)
- **Valor "a partir de"** obrigatório

#### Data de Retenção de Despesas
- Formato: DDMMAA
- A partir desta data: retenções geram **lançamentos próprios** de despesas (opção 475)

### Big Brother (Opção 145)
- Mobiliza equipe gerencial para avaliação/correção de problemas
- **Senha requerida** no primeiro acesso do dia (se ativado)
- Uso recomendado: Atrasados de entrega, CTRCs com prejuízo

### Relatórios Diários (Opção 056)
- **Processamento**: Todos os dias com dados de ontem
- **Visibilidade**: Cada unidade vê o seu, MTZ vê todas
- **Atrasados de entrega**: Atualizados de hora em hora

### Indicadores no Menu Principal
- **Atrasados de entrega**: Quantidade de CTRCs (atualizado de hora em hora, por unidade destino)
- **Valor do prejuízo**: Soma dos RC negativos (CTRCs de ontem)

### Opção 166 vs Opção 168
- **166**: Receita = fretes, Despesa = comissões + custos transferência. **Avaliar resultado de cliente**
- **168**: Receita = serviços prestados, Despesa = Contas a Pagar. **Avaliar resultado da unidade**

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-B05](../pops/POP-B05-relatorios-gerenciais.md) | Relatorios gerenciais |
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-C03](../pops/POP-C03-emitir-cte-complementar.md) | Emitir cte complementar |
| [POP-C05](../pops/POP-C05-imprimir-cte.md) | Imprimir cte |
| [POP-C06](../pops/POP-C06-cancelar-cte.md) | Cancelar cte |
| [POP-C07](../pops/POP-C07-carta-correcao-cte.md) | Carta correcao cte |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D07](../pops/POP-D07-comprovantes-entrega.md) | Comprovantes entrega |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
