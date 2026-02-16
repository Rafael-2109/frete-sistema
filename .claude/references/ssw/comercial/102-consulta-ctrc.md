# Opção 102 — Consulta CTRC Simplificada

> **Módulo**: Comercial
> **Páginas de ajuda**: 3 páginas consolidadas (ssw0053.htm, ssw0267.htm, ssw1931.htm)
> **Atualizado em**: 2026-02-15

## Função

Consulta simplificada de CT-es, Subcontratos e NFS-es a partir de diversos critérios (CTRC, NF, CT-e, gaiola, pallet, pedido, código de barras, etc.). Interface principal de acesso rápido à situação de documentos fiscais de transporte.

## Quando Usar

- **Rastreamento básico**: Cliente ou operador precisa verificar situação de um documento específico
- **Consulta multi-critério**: Buscar por NF, código de barras de volume, gaiola, pedido, valor do frete
- **Integração EDI**: Verificar protocolo de webservice ou arquivos EDI enviados
- **Cross-domain**: Buscar CTRCs em outros domínios (requer configuração prévia em opção 146 e 434)

**Para consulta a partir de situação**: Use opção 101 (mais robusta, permite filtros complexos)

## Pré-requisitos

### Configurações Necessárias
- **Busca em outros domínios**: Domínios remotos cadastrados em opção 146 + liberação de acesso em opção 434
- **Período padrão**: 100 dias de emissão (configurável na pesquisa)

### Permissões e Restrições
- **Parceiro (opção 401)**: Só acessa CTRCs em que é unidade origem ou destino
- **Cliente (opção 925)**: Não acessa informações de outros clientes (Manifestos/Romaneios não exibidos)
- **Usuário sem permissão de unidade**: Links DACTE/XML/Comprovante não exibidos
- **Arquivo morto**: CTRCs enviados após 90 dias da liquidação+baixa ou 365 dias da emissão (link "Retornar" disponível)

## Campos / Interface

### TELA 01 — Critérios de Busca

Informar **apenas um** dos campos:

| Campo | Formato | Observações |
|-------|---------|-------------|
| **WS-CTRCs não gerados** | Link | Abre opção 117 (transações webservice rejeitadas, últimos 3 meses) |
| **CTRC** | `[sigla] número-sem-DV` | Número interno SSW. Sigla opcional |
| **Nota Fiscal** | `[série/]número` | NF do remetente. Série opcional |
| **NR1, NR2 ou NR** | Código sequencial | Etiquetas de rastreamento de volumes (amarram volumes à DANFE) |
| **Código barras vol cliente/shipment** | Código EDI | Identificação do volume na NF-e (campo do EDI) |
| **CT-e/Num Controle** | Número fiscal | Número impresso no DACTE (acima do código de barras) ou Num. Controle (formulários antigos) |
| **Gaiola** | Código SSWBar | Requer **Período de pesquisa** (data emissão Manifesto ou data autorização CTRC se sem Manifesto). Padrão: 10 dias |
| **Pallet** | Código SSWBar | Idem gaiola |
| **CTRC Origem** | Número CTRC | CTRC emitido pela subcontratante (útil para Subcontratos) |
| **Pedido** | Número/container | Pedido do cliente ou container informado em observação (opção 004) |
| **Valor do frete** | Valor | Busca todos documentos com frete exato |
| **Protocolo webservice** | Número | Protocolo de confirmação EDI/WS do cliente (registro em link "ARQUIVOS" no rodapé) |
| **Período de pesquisa** | Data início/fim | Padrão: 100 dias. Alterável |
| **Código de barras** | 44 dígitos | Código de barras DACTE ou DANFE |

**Buscar em outros domínios**: Checkbox para consulta cross-domain (requer setup prévio)

### TELA 02 — Resultado da Consulta

#### Dados do CTRC

| Campo | Descrição |
|-------|-----------|
| **Resgatar** | Indicativo de ocorrência SSW 88 (resgate solicitado pelo cliente). CTRC deve ser devolvido ao remetente (opção 016) |
| **CTRC** | Número interno SSW |
| **SEFAZ** | Link para eventos oficiais CT-e (autorização, MDF-e, passagem, comprovante entrega). Ctrl+F para buscar |
| **CT-e** | Número fiscal. Link abre detalhes de autorização SEFAZ |
| **Unitizado** | Link mostra CTRCs da unitização (EDI ou opção 609). **Não inclui** unitizações do SSWBar ou opção 011 |
| **AUTORIZADO (SVC)** | CT-e aprovado via SEFAZ Virtual Contingência. **Bloqueia** complemento (opção 222) e Carta Correção (opção 736) |
| **No arq morto → Retornar** | Retorna temporariamente CTRC do arquivo morto (>90 dias liquidação+baixa ou >365 dias emissão) |
| **Entrega agendada** | Data/hora agendada (opção 015) |
| **Previsão de Entrega** | Calculada na emissão e recalculada na autorização SEFAZ (opção 007). Link "Ajustar" = opção 835 |
| **Prazo unid destinatária** | Previsão para unidade (opção 402) contada do 1º dia útil após chegada (opção 030). **Nunca anterior** à previsão do cliente |
| **Estou chegando** | Hora prevista de entrega (SSWMobile, entregas roteirizadas). Desaparece após baixa do Romaneio |
| **Peso real / original** | Peso para cálculo (opção 084 ou SSWBalança). Original mostrado se houve repesagem |
| **Cubagem / original** | M³ total (opção 084 ou cubadora). Link mostra 3 dimensões. Original se houve recubagem |
| **Peso de cálculo** | Maior entre peso real e peso cubado |
| **Valor do frete** | Valor final a receber. **Substituição Tributária**: Base Cálculo - ICMS/ISS |
| **ICMS/ISS** | Valor calculado. **Não exibido** em Substituição Tributária (responsabilidade do pagador/remetente) |
| **IBS/CBS** | Soma IBS+CBS (informativo, não somado ao frete — LC 214/2025) |
| **Frete original** | Guardado quando ocorre reversão (opção 451) |

#### Situação de Liquidação

| Status | Significado |
|--------|-------------|
| **Pendente** | Não faturado nem liquidado |
| **Não liquidado** | Faturado mas não liquidado |
| **Uso operacional** | RPS bloqueado (série 999), será unificado (opção 172) |
| **Bloqueio temporário** | Bloqueado para faturamento (opção 462) |
| **Bloqueio anulação** | Anulado por outro CTRC (opção 520) |
| **Bloqueio substituição** | Substituído por outro CTRC (opção 520) |

#### Clientes

Dados exibidos são do **cadastro atual** (opção 483), não necessariamente do documento. Para dados originais: clicar link DACTE/Subcontrato no topo.

| Campo | Descrição |
|-------|-----------|
| **Remetente, Destinatário, Expedidor, Entrega, Pagador** | Conforme cadastro opção 483 |
| **ED** | Cliente de Entrega Difícil (opção 483) |

#### Operação

| Campo | Descrição |
|-------|-----------|
| **Origem** | Unidade emissora + (P=polo / R=região / I=interior, opção 402). **Cidade origem**: remetente, unidade (placa ARMAZEM) ou expedidor. Define comissionamento (opção 408) |
| **Destino** | Praça da cidade (opção 402). **Cidade destino**: destinatário, recebedor ou transportadora |

#### Outras Informações

| Campo | Descrição |
|-------|-----------|
| **Últ Roman Entregas** | Último Romaneio de Entregas (opção 035). **Itinerante** = tipo Romaneio. **Ver todos** = histórico completo |
| **Capa de Remessa CE** | Gerada pela unidade entregadora (opção 040) para remeter Comprovante de Entrega à Matriz |
| **Pacote de Arquivamento CE** | Capa gerada pela Matriz (opção 428) para arquivar Comprovantes de Entrega |
| **Capa Comprov Ext** | Capa (opção 082) para enviar CE ao subcontratante externo não-SSW |
| **Capa de Canhoto de NF** | Capa (opção 070) para enviar canhotos de NF ao remetente |

#### Situação Atual

- **Última ocorrência** com código SSW (histórico completo em opção 033)
- Ocorrências **INFORMATIVAS** não gravadas como última
- Última ocorrência tipo **ENTREGA ou BAIXA** interrompe gravação de nova ocorrência

### Rodapé — Links Funcionais

| Link | Descrição |
|------|-----------|
| **Ocorrências** | Opção 033: histórico + inclusão de novas ocorrências/instruções |
| **Transferências** | Localização atual + todos Manifestos. Última saída (opção 025) atualiza previsões. `(*)` = possui CTRB/OS associado |
| **Frete** | Opção 392: composição detalhada do frete |
| **Fiscal** | Informações fiscais CTRC/RPS. **Subcontratos**: cidade origem (=CT-e origem) define unidade SEFAZ/UF (opção 402). **Lote contábil**: Diário Auxiliar Saídas (opção 556, Contabilidade SSW) |
| **DANFEs** | Dados das Notas Fiscais + volumes (NR, código barras, endereço armazém, peso, cubagem, dimensões). **NR1/NR2**: limites de NR. **NR**: dados do volume (etiqueta cliente, balança/cubadora — opção 148) |
| | **Peso/cubagem/dimensões**: Capturados na transportadora (opções 084, 184, 185, SSWBalança, cubadoras WS). **Data webservice**: timestamp recepção. **Utilizado para cálculo**: S = usado no frete (se CTRC não autorizado ou cliente usa — opção 388) |
| **Produtos** | Produtos da NF (se XML NF-e disponível). **Código ONU**: identificado automaticamente no XML, exibido em DAMDFE e etiquetas de volumes perigosos |
| **Operação anterior** | Documento fiscal anterior. **CT-e Redespacho Intermediário**: não mostra (muitos docs). Dados: valor frete, ICMS, **PIS/COFINS** (se não importado, usa opção 903/Outros), tipo frete (CIF/FOB), **Cobrar frete** (S = subcontratante cobra via opção 004), **Recebido em** (frete subcontratante recebido — opção 085, descontado da fatura), **Capa Remessa** (opção 082) |
| **Carta de Correção** | Opção 736: corrige dados CT-e não-fiscais |
| **Arquivos EDI** | EDIs incluindo o CTRC. Download até 90 dias (opção 602) |
| **Acareação** | Histórico de acareação de entrega (opções 250, 251) |
| **SSWBAR/sorter** | Conferências de volumes (cargas/descargas) em tempo real. **Sobras/faltas**: identificadas na conclusão (SSWBar, opção 022, opção 264). Conclusão automática se não houver divergências. **Asterisco** em Descarga Coletas/Manifesto = descarga não concluída (some em 30 dias). **Gaiola/pallet**: inclusão registrada em ocorrências. **Desmonte** em transbordo registrado em ocorrências. Dados disponíveis por 6 meses. **Sorter**: usa WebAPI, login da unidade instalada (opção 219) |
| **Comprovante de Entrega** | Imagem: foto SSWMobile ou DACTE assinada (SSWScan). **Fotos de ocorrência ENTREGA**: sobrepõem existentes. **Escaneamento** (opção 398): ocorrência SSW 19, exibida como CE. **Registro SEFAZ**: código hash registrado com protocolo (cartório digital). **Glacier**: após 1 ano, armazenado AWS Glacier (disponibilização até 5h, válida 7 dias). Imagens disponíveis por 5 anos |
| **Liquidação** | Fatura incluindo o CTRC (opção 104) |
| **CO2 emitido** | Opção 330: Kg CO2 por trecho |
| **Resultado** | Opção 393: resultado real/comercial. **Indisponível** para usuário tipo cliente (opção 925) |

## Fluxo de Uso

### 1. Consulta Básica
```
1. Informar critério de busca (ex: NF, CTRC, código barras)
2. Ajustar período se necessário (padrão 100 dias)
3. Visualizar resultado com situação atual
```

### 2. Rastreamento Completo
```
1. Consultar CTRC (opção 102)
2. Clicar "Transferências" → ver Manifestos e localização
3. Clicar "Ocorrências" → histórico detalhado (opção 033)
4. Verificar "Comprovante de Entrega" se baixado
```

### 3. Consulta Cross-Domain
```
1. Marcar "Buscar em outros domínios"
2. Informar critério
3. Sistema busca em domínios configurados (opção 146)
4. Requer liberação prévia em cada domínio (opção 434)
```

### 4. Arquivo Morto
```
1. Consultar CTRC com >90 dias liquidação+baixa ou >365 dias emissão
2. Sistema exibe "No arq morto → Retornar"
3. Clicar link para retorno temporário
4. Realizar consulta necessária
```

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| **101** | Consulta CTRC avançada (filtros complexos, situação) |
| **004** | Emissão CTRC (observação com pedido/container) |
| **007** | Autorização SEFAZ (recalcula previsão) |
| **011** | Unitização (não considerada no link "Unitizado") |
| **015** | Agendamento de entrega |
| **016** | Devolução ao remetente (resgate) |
| **022, 264** | Conclusão sobras/faltas SSWBar |
| **025** | Saída veículo (atualiza previsões Manifesto) |
| **030** | Chegada na unidade |
| **033** | Ocorrências (histórico completo + inclusão) |
| **035** | Romaneio de Entregas |
| **040** | Capa de Remessa CE (unidade → Matriz) |
| **070** | Capa Canhoto NF (Matriz → remetente) |
| **082** | Capa Comprovante Externo (Matriz → subcontratante) |
| **084** | Informar peso/cubagem |
| **085** | Recebimento frete subcontratante |
| **100** | E-mail marketing (bloqueio via opção 814) |
| **104** | Fatura/liquidação |
| **117** | WS rejeitados (não gerou CTRC, 3 meses) |
| **146** | Cadastro domínios para busca cross-domain |
| **148** | Resultados balança/cubadora |
| **172** | Unificação RPS (uso operacional) |
| **184, 185** | Ajuste peso/cubagem |
| **219** | Configuração sorter |
| **222** | Complemento CT-e (bloqueado se SVC) |
| **250, 251** | Acareação de entrega |
| **330** | Emissão CO2 |
| **383** | Rastreamento automático (e-mail, bloqueio opção 814) |
| **384** | Fatura automática (e-mail, bloqueio opção 814) |
| **388** | Configuração cliente (uso peso/cubagem para cálculo) |
| **392** | Composição do frete |
| **393** | Resultado real/comercial |
| **398** | Escaneamento CE (ocorrência SSW 19) |
| **401** | Cadastro unidade (tipo Agência/Parceiro) |
| **402** | Praças/distâncias |
| **403** | Distância entre unidades |
| **404** | Setor de entrega |
| **408** | Comissionamento |
| **428** | Pacote Arquivamento CE (Matriz) |
| **434** | Liberação acesso cross-domain |
| **451** | Reversão de frete |
| **462** | Bloqueio temporário faturamento |
| **483** | Cadastro cliente (envio DACTE/XML/EDI, bloqueio opção 814) |
| **520** | Anulação/substituição CTRC |
| **556** | Diário Auxiliar Saídas (lote contábil) |
| **602** | Download arquivos EDI (90 dias) |
| **609** | Unitização via sistema |
| **736** | Carta de Correção |
| **814** | Desbloqueio e-mail cliente |
| **835** | Ajustar previsão de entrega |
| **903** | PIS/COFINS (usado se não importado de doc anterior) |
| **925** | Permissões de acesso usuário |

### Distância Total do CTRC
Soma de 3 distâncias (opção 402):
1. Cidade origem → unidade origem
2. Unidade origem → unidade destino (opção 403)
3. Unidade destino → cidade destino

**Alternativa**: Distância Google
**Carga Fechada/Completa**: SEMPRE usa distância Google

## Observações e Gotchas

### Prioridade de Dados
1. **Clientes exibidos**: Cadastro atual (opção 483), **não** dados do documento
2. **Dados originais**: Clicar DACTE/Subcontrato no topo da tela

### Peso/Cubagem para Cálculo
- **Não utilizado** se CTRC já autorizado SEFAZ
- **Não utilizado** se cliente não usa (opção 388)
- Campo "Utilizado para cálculo" = S indica uso efetivo

### Arquivo Morto
- **Envio**: 90 dias após liquidação+baixa OU 365 dias após emissão
- **Retorno**: Temporário via link "Retornar"

### Comprovante de Entrega
- **Prioridade**: Fotos ocorrência ENTREGA > escaneamento (SSW 19) > DACTE assinada
- **SEFAZ**: Hash registrado em minutos (cartório digital)
- **Glacier**: Após 1 ano, disponibilização até 5h, válida 7 dias
- **Retenção**: 5 anos

### Restrições de Acesso
- **Parceiro**: Só CTRCs em que é origem/destino
- **Cliente**: Não vê Manifestos, Romaneios, dados de outros clientes
- **Sem permissão de unidade**: DACTE/XML/CE não exibidos
- **Responsável por pagador**: DACTE/XML/CE não exibidos

### Última Ocorrência
- Ocorrências **INFORMATIVAS** não gravam como última
- Ocorrências **ENTREGA ou BAIXA** travam gravação de novas

### Substituição Tributária
- **Valor frete** = Base Cálculo - ICMS/ISS
- **ICMS/ISS** não exibido (responsabilidade pagador/remetente)

### IBS/CBS
- Valor informativo (LC 214/2025)
- **Não somado** ao valor a receber

### Unitização
- Link "Unitizado" mostra apenas EDI ou opção 609
- **Não inclui**: SSWBar (opção 011)

### CT-e SVC (SEFAZ Virtual Contingência)
- **Bloqueia**: Complemento (opção 222) e Carta Correção (opção 736)

### E-mail Automático (LGPD)
- Cliente pode cancelar recebimento (links no cabeçalho/rodapé)
- Controle **por domínio** (todas transportadoras)
- Desbloqueio via opção 814 (todos tipos de e-mail)

### Gaiola/Pallet
- **Período obrigatório**: Data emissão Manifesto (ou autorização se sem Manifesto)
- **Padrão**: 10 dias

### SSWBar/Sorter
- **Dados disponíveis**: 6 meses
- **Asterisco** em Descarga = não concluída (some em 30 dias)
- **Sorter**: Login da unidade instalada

### PIS/COFINS
- Importado de documento anterior
- Se não importado: usa opção 903/Outros

### Prazo Unidade Destinatária
- Contado do 1º dia útil após chegada (opção 030)
- **Nunca anterior** à previsão do cliente

### DACTE — Itens Importantes
1. **(1)**: Sigla unidade destino (opção 401)
2. **(2)**: Setor de entrega (opção 404)
3. **(3)**: Número CTRC (sigla + número + DV) — número interno SSW
4. **(4)**: Chave CT-e/DACTE (44 dígitos)

### Protocolo Webservice
- Registrado em link "ARQUIVOS" no rodapé
- Confirmação EDI/WS do cliente

### Previsão de Entrega
- Calculada na **emissão** (opção 004)
- **Recalculada** na autorização SEFAZ (opção 007)
- Ajuste manual via opção 835

### "Estou Chegando" (SSWMobile)
- Apenas entregas **roteirizadas**
- Desaparece após baixa do Romaneio

### Código ONU
- Identificação automática no XML NF-e (descrição mercadoria)
- Exibido em DAMDFE e etiquetas volumes perigosos

### CT-e Redespacho Intermediário
- Link "Operação anterior" **não mostra** documentos (podem ser muitos)

### WS-CTRCs Não Gerados
- Link abre opção 117
- Transações webservice **rejeitadas** (últimos 3 meses)

### Página de Averbação PAMWEB (ssw0267.htm)
**Incluída no consolidado mas não diretamente relacionada à opção 102**. Referência cruzada:
- Opção 509 (geração arquivo averbação PAMWEB)
- Históricos de remessa gravados no item EDI da opção 102 (campo CNPJ seguradora)

### Desbloqueio E-mail (ssw1931.htm)
**Incluída no consolidado como referência ao processo de bloqueio LGPD**:
- Opção 814: Desbloqueio de e-mails bloqueados por clientes
- Controle por domínio (todas transportadoras)
- Opções que disparam e-mails: 483, 383, 384, 100
- Link de cancelamento em cabeçalho/rodapé de todos e-mails SSW

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-B05](../pops/POP-B05-relatorios-gerenciais.md) | Relatorios gerenciais |
