# Opção 908 — Tabela de Ocorrências EDI (Configurações do Sistema)

> **Módulo**: Sistema
> **Páginas de ajuda**: 81 páginas consolidadas (133KB)
> **Atualizado em**: 2026-02-14

## Função
Configura tabela DE-PARA de ocorrências entre códigos SSW e códigos do cliente/parceiro para envio e recepção de arquivos EDI. Permite integração com dezenas de plataformas e clientes via API, SFTP, e-mail ou Amazon S3.

## Quando Usar
- Configurar envio de ocorrências para cliente via EDI
- Configurar recepção de ocorrências de parceiro
- Cadastrar tabela DE-PARA de códigos de ocorrências
- Ativar/desativar envio de ocorrências específicas
- Marcar ocorrências finalizadoras (mercadoria perdida)
- Configurar integrações API com clientes (INTELIPOST, NETSHOES, DAFITI, etc.)

## Pré-requisitos
- Para envio: programa EDI do cliente configurado pela Equipe SSW
- Para recepção: parceiro deve enviar arquivos periodicamente
- Códigos de ocorrências da transportadora cadastrados (opção 405 para CTRC, opção 519 para Coleta)
- Para integrações API: credenciais fornecidas pelo cliente (URL, usuário, token)

## Processo

### Envio de Ocorrências (CTRC)

```
Equipe SSW (XXX) - Cria tabela DE-PARA no XXX vinculada ao CNPJ
         ↓
Equipe SSW (domínio) - Puxa tabela do XXX para o domínio
         ↓
Transportadora - Marca "Envia" e "Finalizadora" na opção 908
         ↓
Sistema - Envia ocorrências automaticamente via EDI
```

### Recepção de Ocorrências (de Parceiros)

```
Parceiro - Envia arquivo de ocorrências
         ↓
Opção 908 - Tabela DE-PARA configurada
         ↓
Sistema - Converte códigos e atualiza CTRCs
```

### Coleta

```
Tabela DE-PARA (opção 908) vinculada ao código da transportadora (opção 405)
         ↓
Sem uso do código SSW (direto)
```

## Campos / Interface

### Tela Inicial

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **CNPJ cliente** | Sim | CNPJ do cliente ou parceiro |
| **Referência código** | Sim | **SSW**: relaciona código cliente com código SSW (tabela do XXX). **Domínio**: relaciona com código do domínio (deve marcar Prioritária na tela seguinte) |
| **CTRC** | Não | Configura tabela para CTRCs |
| **Coleta** | Não | Configura tabela para coletas (não usa tabela SSW, direto da opção 405) |

### Tela Principal

#### Para XXX

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Prioritária** | Não | Tabela do Domínio tem prioridade sobre a do SSW |
| **Limpar campos** | Não | Exclui a tabela |
| **Replicar para outro CNPJ** | Não | Copia tabela para CNPJ indicado |
| **Domínios vinculados** | Não | Mostra domínios com mesma raiz de CNPJ (atualização automática exceto Envia/Finalizadora) |
| **Replicar coluna Normal para Código Parceiro** | Não | Útil quando parceiro não usa SSW mas troca ocorrência com código SSW |

#### Para Todos os Domínios - CTRC

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **ENVIA** | Sim | **S**: ocorrência pode ser enviada ao cliente via EDI |
| **FINALIZADORA** | Não | **S**: mercadoria perdida, pode enviar nova e cobrar anterior da transportadora. Apenas pendências. Envio requer liberação prévia (opção 943) |
| **Demais colunas** | - | Definidas pela Equipe SSW com o programa EDI |

#### Para Todos os Domínios - Coleta

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Código/Descrição** | - | Da ocorrência de coleta |
| **Envia** | Sim | **N**: ocorrência não enviada ao cliente |
| **NORMAL** | Não | Códigos para coleta normal (numérico ou alfa). Observação também pode ser utilizada |
| **REVERSA** | Não | Códigos para operação reversa. Se não existir, usa normal |

## Principais Integrações API Disponíveis

### INTELIPOST (ssw1673)
- **Funções**:
  - (1) Envia ocorrências via API
  - (2) Envia ocorrências com geolocalização
  - (3) Envia ocorrências de coleta
  - (4) Envia ocorrências de coleta com geolocalização
  - (5) Envia ocorrências e imagens independente do código (usar com função 1 ou 2)
- **Processo**: Automático, códigos SSW padrão INTELIPOST (opção 908)
- **Comprovante**: Link para acesso
- **Status**: Opção 101 (Arquivos EDI)
- **Reenvio**: Até 30 dias

### NETSHOES (ssw1807)
- **CNPJ raiz**: 09339936
- **Formato**: API JSON
- **Credenciais**: URL, usuário, token (solicitar à NETSHOES, enviar para edi@ssw.inf.br)
- **Status**: Opção 101 (Arquivos EDI), opção 605 (JSON), opção 117 (recusadas)

### DAFITI (ssw1953)
- **CNPJ raiz**: 11200418
- **Funções**: (1) CT-e, (2) Coleta
- **Tabela Local**: Opção 908 (transportadora vincula códigos do cliente aos internos)
- **Processos**: Recebimento NOTFIS, envio ocorrências, consumo CO2
- **Endpoint rastreamento**: https://ssw.inf.br/app/tracking/dafiti/{remessa}
- **Status**: Opção 101, 605, 117

### BRUDAM (ssw1872)
- **Processo**: API automático
- **Comprovante**: Link do documento
- **Reenvio**: Até 30 dias

### WEB (ssw2081)
- **Processo**: API JSON
- **Credenciais**: URL, usuário, token (enviar para edi@ssw.inf.br)

### RANDON (All TECH/All TRANSPORT) (ssw2175)
- **Funções**: (1) Ocorrências e imagens XML, (2) Geolocalização XML
- **Geolocalização**: Latitude/longitude via SSWMobile
- **Comprovante**: Link

### OCORRÊNCIAS PADRÃO SSW (ssw2181)
- **Funções**: (1) CTRC, (2) Coleta
- **Credenciais**: Cliente envia URL e Token para edi@ssw.inf.br
- **Manual**: https://ssw.inf.br/ajuda/webserviceOcorrencias.html
- **Reenvio**: Até 30 dias

### BCUBE (ssw2241)
- **CNPJ raiz**: 09174577
- **Formato**: API JSON
- **Credenciais**: URL, usuário, token

### COMMED (ssw2245)
- **CNPJ raiz**: 02643718, 05312941, 52202744
- **Formato**: CSV
- **Arquivo**: OCOREN (gerado via opção 600, gravado na opção 602 por 120 dias)
- **Envio**: Automático (opção 603 - FTP/SFTP/e-mail/Amazon S3) ou retroativo (até 30 dias)

### MERIDIONAL (MOVVI) (ssw2257)
- **CNPJ raiz**: 23864838
- **Comprovante**: Criptografado em base64

## Fluxo de Uso

### Configurar Envio de Ocorrências (CTRC)

1. Aguardar Equipe SSW criar tabela no XXX
2. Acesse opção 908
3. Informe CNPJ do cliente
4. Selecione "Referência código" = **SSW**
5. Clique em "CTRC"
6. Marque "ENVIA" = **S** para ocorrências a enviar
7. Marque "FINALIZADORA" = **S** se aplicável (apenas pendências)
8. Verifique demais colunas (definidas pela Equipe SSW)
9. Confirme

### Configurar Envio de Ocorrências (Coleta)

1. Acesse opção 908
2. Informe CNPJ do cliente
3. Clique em "Coleta"
4. Configure campos NORMAL e REVERSA (código numérico ou alfa)
5. Marque "Envia" = **S** ou **N**
6. Confirme

### Configurar Recepção de Ocorrências (de Parceiros)

1. Cadastrar tabela DE-PARA na opção 908 (obrigatório)
2. Parceiro envia arquivo (layout específico)
3. Sistema converte códigos automaticamente
4. Atualiza CTRCs da subcontratante

### Configurar Integração API

1. Obter credenciais do cliente (URL, usuário, token)
2. Enviar para edi@ssw.inf.br
3. Aguardar ativação pela Equipe SSW
4. Configurar tabela DE-PARA na opção 908
5. Marcar "Envia" = **S** para ocorrências
6. Verificar status na opção 101, 605, 117

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 101 | Visualiza status de envios EDI (link Arquivos EDI) |
| 117 | Lista transações WebService recusadas (últimos 3 meses) |
| 405 | Códigos de ocorrências de CTRCs da transportadora |
| 519 | Códigos de ocorrências de coletas da transportadora |
| 600 | Gera arquivos EDI (OCOREN, etc.) |
| 602 | Diretório de arquivos EDIs processados (até 120 dias) |
| 603 | Parametriza envio/recebimento automático (FTP/SFTP/e-mail/S3) e retroativo (até 30 dias) |
| 605 | Disponibiliza arquivos JSON gerados (útil para retransmissões) |
| 927 | Tabela DE-PARA para recepção de ocorrências (complementar) |
| 943 | Libera envio de ocorrências finalizadoras |
| 909 | Tabela DE-PARA com códigos alfanuméricos (complementa opção 908) |

## Observações e Gotchas

### Diferença XXX vs Domínio
- **XXX**: Equipe SSW cria tabela vinculada ao CNPJ e código SSW
- **Domínio**: Puxa tabela do XXX sem alteração (exceto Envia/Finalizadora)
- **Tabela Local (Domínio)**: Pode criar tabela própria marcando "Prioritária"

### Ocorrências Finalizadoras
- Apenas para ocorrências tipo **pendência**
- Envio requer liberação prévia (opção 943)
- Fonte na cor vermelha na tela

### Atualização Automática
- Domínios com mesma raiz de CNPJ são atualizados automaticamente quando XXX é alterado
- Exceção: campos Envia e Finalizadora (não atualizam automaticamente)

### Formato do Código
- **Numérico** ou **Alfanumérico**: conforme padrão do cliente
- **Mesma quantidade e tipo de caracteres**: código deve ter exatamente o padrão do cliente
- Divergência causa erro no sistema do cliente (ex: 1 vs 001)

### Ocorrências Consideradas
- Só enviadas se código do cliente estiver informado na tabela

### Conversão Automática (Parceiros SSW)
- Subcontratante e subcontratada usando SSW
- Ocorrências do SUBCONTRATO atualizam CTRC ORIGEM automaticamente
- Base: tabela da opção 924
- Instruções do CTRC ORIGEM atualizam SUBCONTRATO automaticamente
- Visualização de ocorrências do parceiro: opção 108

### Diferença opção 908 vs 909
- **908**: Tabela DE-PARA padrão (numérico ou alfanumérico)
- **909**: Complementa 908 com códigos alfanuméricos do cliente

### Diferença opção 908 vs 927
- **908**: Envio de ocorrências (SSW → Cliente)
- **927**: Recepção de ocorrências (Cliente → SSW)

### Recepção de Arquivo de Ocorrências
- Layout específico (14 posições CNPJ/CTRC, 8 NF, 6 data, 4 hora, 2 código, 30 descrição, 70 complemento)
- Divergência lidos vs importados: dados são Notas Fiscais, sistema usa Conhecimentos

### Envio Automático vs Manual
- **Automático**: Configurar opção 603 (FTP/SFTP/e-mail/S3)
- **Manual**: Gerar via opção 600
- **Retroativo**: Opção 603, campo "último processamento" (até 30 dias)

### Monitoramento
- **Status**: Opção 101 (link Arquivos EDI)
- **JSON**: Opção 605
- **Recusadas**: Opção 117 (últimos 3 meses)

### Geolocalização
- Latitude/longitude capturadas via SSWMobile
- Disponível em integrações: INTELIPOST, RANDON

### Comprovante de Entrega
- Enviado como **link** (INTELIPOST, BRUDAM, RANDON)
- Enviado **criptografado base64** (MERIDIONAL/MOVVI)
- Enviado **após** lançamento ocorrência 01 (código 19 no padrão cliente)

### Reenvio
- Solicitar ao SSW via edi@ssw.inf.br
- Período: até **30 dias**

### Suporte
- Dúvidas EDI: edi@ssw.inf.br
- Suporte geral: suporte@ssw.inf.br
