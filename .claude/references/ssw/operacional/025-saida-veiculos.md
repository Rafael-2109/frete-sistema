# Opção 025 — Saída de Veículos

> **Módulo**: Operacional
> **Páginas de ajuda**: 8 páginas consolidadas (múltiplas opções relacionadas)
> **Atualizado em**: 2026-02-15

## Função

Registra a saída de veículos da unidade, submetendo os Manifestos Operacionais à autorização do SEFAZ para obtenção do **MDF-e** (Manifesto de Documentos Fiscais Eletrônico) - um por UF destino. A opção unifica diversos Manifestos Operacionais carregados no veículo em única MDF-e por UF destino, encerrando MDF-es anteriores se necessário.

## Quando Usar

- Dar saída ao veículo após carregamento de CTRCs (opção 020)
- Autorizar MDF-e junto ao SEFAZ
- Unificar Manifestos Operacionais em MDF-e por UF destino
- Registrar SMP (Solicitação de Monitoramento Preventivo) automático
- Gerar EDI de averbação para seguradoras
- Informar saída para EDI FISCAL (Mato Grosso)
- Registrar saídas em transferências, entregas (opção 035) e coletas (opção 003)

## Pré-requisitos

### Cadastros e Configurações
- **Opção 020**: Manifesto Operacional emitido (com CTRCs carregados)
- **Opção 072**: Veículo contratado para transferência
- **Opção 026**: Veículo cadastrado (placa do cavalo e carretas)
- **Opção 028**: Motorista cadastrado (CPF, telefones para SMP automático)
- **Opção 401**: Unidade emissora cadastrada
- **Opção 403**: Rotas cadastradas (hora limite de saída, prazo de transferência, distância)

### Gerenciamento de Risco (opção 903)
- **Opção 390**: PGR (Plano de Gerenciamento de Risco) configurado
- Autorizações vigentes para veículos, motoristas e ajudantes

### Seguradoras e EDI
- **Opção 603**: Parametrização de programas EDI
- CNPJ da seguradora configurado para geração de arquivo de averbação

## Campos / Interface

### Processo de Saída

**Dados registrados automaticamente**:
- **Data/hora de saída**: Momento em que a saída foi efetivada pela opção 025
- **Hora limite de saída**: Cadastrada na opção 403 (rota)
- **Atraso**: Horas de atraso da saída em relação ao limite
- **Distância**: Distância a ser percorrida pelo Manifesto
- **Prazo**: Prazo de transferência cadastrado na opção 403
- **Peso KG**: Peso real do Manifesto

**Agendar saída veículo** (opcional):
- Agendamento automático de saída para próximas 24 horas
- Configurado na opção 020 (TELA 03 - Emissão do Manifesto)
- Só deve ser utilizado para operações que não exigem intervenção humana (ex: informar SMP)

### Unificação de Manifestos em MDF-e

**Regra SEFAZ**: Apenas um MDF-e (fiscal) pode ser emitido por UF destino

**Processo de unificação**:
- Para diversos Manifestos Operacionais emitidos e carregados no veículo em unidades anteriores
- Opção 025 unifica numa única MDF-e por UF destino
- Encerra MDF-es anteriores se necessário

**Manifesto Operacional vs MDF-e**:
- **Manifesto Operacional**: Conceito SSW utilizado na operação do transporte
  - Representa de fato o que está carregado num veículo
  - Objetiva carregamento real na origem e descarregamento no destino (geralmente via SSWBar)
- **MDF-e**: Documento fiscal autorizado pelo SEFAZ
  - Pode ter diversos Manifestos Operacionais
  - Um único MDF-e por UF destino

## Fluxo de Uso

### 1. Fluxo Normal de Saída

1. **Opção 019**: Relaciona CTRCs disponíveis na unidade para transferência
2. **Opção 020**: Emissão do Manifesto Operacional (carregamento de CTRCs)
3. **Opção 072**: Contratação do veículo que faz a transferência
4. **Opção 025**: Saída do veículo (esta opção)
   - Submete Manifestos Operacionais ao SEFAZ
   - Obtém MDF-e (fiscal) - um por UF destino
   - Vincula Manifestos ao respectivo CTRB/OS de transferência (opção 072)
   - Dispara SMP (Solicitação de Monitoramento Preventivo) automático
   - Gera EDI de averbação para seguradoras
5. **Opção 030**: Chegada do veículo na unidade destino

### 2. Geração de EDI FISCAL (Mato Grosso)

1. **Opção 025**: Saída do veículo (só Manifestos com saída são considerados)
2. **Opção 018**: Geração do arquivo EDI FISCAL
   - Arquivo gerado e gravado na pasta indicada
   - Deve ser enviado à Receita Estadual solicitante (geralmente via site Internet)

**Regras EDI FISCAL MT**:
- Manifesto deve conter somente CTRCs com destino MT
- Todo conteúdo do Manifesto: CTRCs e Subcontratos (em formulário CTRC) com destino Mato Grosso
- Sistema verifica antes da geração do arquivo
- Registros são Notas Fiscais (não CTRCs)
- Número da Carga: Gerado automaticamente de forma sequencial (deixar em branco para novo arquivo)
- Tanto Notas Fiscais de CTRCs como de Subcontratos são incluídos

### 3. Geração de EDI de Averbação (Seguradoras)

1. **Opção 025**: Saída do veículo (informações só são incluídas no arquivo após saída da unidade origem)
2. **Opção 610**: Geração dos arquivos de averbação
   - Informar CNPJ da seguradora
   - SSW localiza programa de geração específico
   - Gera arquivo que deve ser enviado para seguradora

**Regras de Averbação**:
- CTRCs são gravados no arquivo somente se tiverem recebido SAÍDA pela opção 025
- Período informado geralmente refere-se a EMISSÃO de CTRCs
- Efetuar geração no momento em que todos os veículos já receberam saída
- **Seguro Próprio**: Quando campo SEGURO RCFDC no cadastro do cliente (opção 483) estiver com SIM, averbação não ocorre

### 4. SMP (Solicitação de Monitoramento Preventivo) Automático

**Disparado automaticamente na opção 025** (também nas opções 035 - entrega e 003 - coleta)

**Pré-requisitos**:
- Telefones do motorista cadastrados com maior precisão possível (opção 028)
- Configuração via opção 903/Gerenciamento de Risco

**Monitoramento**:
- Integração WebService com Gerenciadoras de Risco
- Transações recusadas podem ser consultadas na opção 117

## Integração com Outras Opções

### Opções Relacionadas - Fluxo Operacional

- **Opção 003**: Coleta (dispara SMP automático)
- **Opção 018**: Geração do EDI FISCAL - MT (após saída do veículo)
- **Opção 019**: Relaciona CTRCs disponíveis na unidade para transferência
- **Opção 020**: Emissão do Manifesto Operacional (CTRCs carregados)
- **Opção 023**: Consulta de totais já carregados nesta Placa Provisória
- **Opção 024**: Cancelamento do MDF-e (até 24h após emissão, sem passagem por barreira fiscal ou radar ANTT)
- **Opção 025**: Saída do veículo (esta opção)
- **Opção 030**: Chegada do veículo (atualiza estoque de gaiolas/pallets, registra chegada para cálculo de permanência)
- **Opção 035**: Romaneio de Entrega (dispara SMP automático)
- **Opção 058**: Estoque de gaiolas e pallets (atualizado por saídas e chegadas)
- **Opção 072**: Contratação do veículo (CTRB/OS de transferência)
- **Opção 080**: Situação de saídas e chegadas de veículos (Manifestos) nas últimas 24 horas
- **Opção 081**: Relação de CTRCs disponíveis para entrega

### Opções Relacionadas - Cadastros

- **Opção 026**: Cadastro de veículos (placa do cavalo e carretas)
- **Opção 028**: Cadastro de motoristas (CPF, telefones para SMP)
- **Opção 401**: Cadastro de unidades emissoras
- **Opção 403**: Rotas (hora limite de saída, prazo de transferência, distância)
- **Opção 483**: Cadastro de clientes (campo SEGURO RCFDC)

### Opções Relacionadas - Gerenciamento de Risco

- **Opção 390**: PGR (Plano de Gerenciamento de Risco)
- **Opção 903**: Ativação de controles (Gerenciamento de Risco)

### Opções Relacionadas - EDI e Integrações

- **Opção 117**: Transações de WebService Recusadas (SMP, SMS, Atualização Cadastral, EDI de Ocorrências, EDI de Averbação)
- **Opção 600**: Cadastro de EDI
- **Opção 603**: Parametrização de programas EDI (processamento automático)
- **Opção 610**: EDI de Seguradoras (geração de arquivos de averbação)

### Opções Relacionadas - Relatórios

- **Opção 080**: Saídas e Chegadas de Veículos (últimas 24 horas)
  - **SAÍDAS**: Manifesto, Distância, Prazo, Peso KG, Saída, Limite, Atraso, NÃO SAIRAM (CTRCs que permaneciam no armazém)
  - **CHEGADAS**: Manifesto, Distância, Prazo, Peso KG, Chegada, Limite, Atraso
- **Opção 164**: Tempo de permanência por unidade - Diário
  - **NÃO RECEBERAM SAÍDA/ENTREGA**: CTRCs emitidos ou que chegaram há mais de 1 dia e não foram transferidos/entregues
  - **RECEBERAM SAÍDA/ENTREGA**: CTRCs que tiveram saída informada (opção 025) ou foram entregues no dia anterior
  - Colunas: PREVENTR, ATR (atraso), EMISSAO/MANIF CHEG, MANIF SAIDA/ENTREGA, CORTE, PERMANENCI
- **Opção 173**: CTRCs sem ocorrência a mais de 5 dias - Diário
  - Considera como ocorrência: emissão do CTRC, emissão do último Manifesto, emissão do último Romaneio, lançamento de ocorrência
  - Colunas: PREVENTR, ATR (atraso), 5D+SEMOCO (tipo: EMI, MAN, ROM, OCO)

### Opção 412 - Cálculo do Custo de Transferência

**Apropriação do custo**:
1. **Na saída do veículo** (opção 025): Sistema vincula Manifestos ao respectivo CTRB/OS de transferência (opção 072)
2. **Rateio nos Manifestos**: Valor do CTRB é rateado proporcionalmente ao Peso de cálculo total × distância percorrida (opção 403)
3. **Com a chegada do Manifesto** (opção 030): Custo de transferência do Manifesto é rateado proporcionalmente ao peso de cálculo de cada CTRC

**Consulta mostra**:
- Todos CTRBs em que o CTRC participou
- Para cada CTRB: Respectivos Manifestos com valores de transferência rateados (coluna VALTRANSF)
- Valor de transferência do CTRC proporcional à participação do peso calculado no total do Manifesto

## Observações e Gotchas

### Regras Fiscais (MDF-e)

1. **Apenas um MDF-e por UF destino**:
   - Opção 025 unifica diversos Manifestos Operacionais numa única MDF-e por UF destino
   - Encerra MDF-es anteriores se necessário

2. **Prazo de cancelamento do MDF-e**:
   - MDF-e só pode ser cancelado (opção 024) até 24h após emissão
   - Não pode ter passado por barreira fiscal ou radar ANTT

3. **RPS e Subcontratos não fiscal**:
   - Não são submetidos ao SEFAZ para aprovação
   - Manifesto Operacional continua sendo utilizado para transferência da carga

4. **Manifesto Operacional Aéreo**:
   - Emitido com veículo tipo AVIÃO (opção 026)
   - Não é submetido ao SEFAZ (não gera MDF-e)

### EDI de Averbação - IMPORTANTE

1. **Período informado**:
   - Cuidado ao informar período (geralmente refere-se a EMISSÃO de CTRCs)
   - CTRCs são gravados no arquivo somente se tiverem recebido SAÍDA pela opção 025
   - Se na próxima geração o período não selecionar novamente, CTRC NÃO SERÁ AVERBADO
   - Efetuar geração no momento em que todos os veículos já receberam saída

2. **Seguro Próprio**:
   - Quando campo SEGURO RCFDC no cadastro do cliente (opção 483) estiver com SIM
   - Averbação das mercadorias deste cliente remetente não ocorre
   - Qualquer tratamento diferenciado deve ser solicitado à Equipe SSW

### EDI FISCAL Mato Grosso

1. **Manifesto deve conter somente CTRCs com destino MT**:
   - Todo conteúdo do Manifesto: CTRCs e Subcontratos (em formulário CTRC) com destino Mato Grosso
   - Sistema faz verificação antes da geração do arquivo

2. **Saída de veículos**:
   - Só Manifestos que receberam saída (opção 025) são considerados

3. **Registros são Notas Fiscais**:
   - Conteúdo do arquivo é de Notas Fiscais (não CTRCs)
   - Quantidade de registros deve ser confrontada com a de Notas Fiscais

4. **Número da Carga**:
   - Gerado automaticamente de forma sequencial para a transportadora
   - Para gerar novo arquivo deixar campo em branco
   - Só informar caso se queira regerar um arquivo anteriormente gerado

5. **CTRCs e Subcontratos**:
   - Tanto Notas Fiscais de CTRCs como de Subcontratos são incluídos no arquivo

### SMP (Solicitação de Monitoramento Preventivo)

1. **Disparo automático**:
   - Ocorre nas operações de transferência (opção 025), entrega (opção 035) e coleta (opção 003)
   - Integração WebService com Gerenciadoras de Risco

2. **Telefones do motorista**:
   - Devem ser preenchidos com maior precisão possível (opção 028)
   - Utilizados no caso de SMP automático na saída de veículos

3. **Transações recusadas**:
   - Consultadas na opção 117 (Transações de WebService Recusadas)
   - Tipos de operação: SMP, SMS, Atualização Cadastral, EDI de Ocorrências, EDI de Averbação

### Relatórios de Permanência

1. **Opção 164 - Tempo de permanência por unidade**:
   - **NÃO RECEBERAM SAÍDA/ENTREGA**: CTRCs emitidos pela unidade ou que chegaram há mais de 1 dia e ainda não foram transferidos/entregues
   - **RECEBERAM SAÍDA/ENTREGA**: CTRCs que tiveram saída informada (opção 025) ou foram entregues no dia anterior
   - **PREVENTR**: Data de previsão de entrega (prazo prometido ao cliente)
   - **ATR**: Quantidade de dias de atraso (negativos indicam previsão de entrega futura)
   - **EMISSAO/MANIF CHEG**: Data de emissão do CTRC ou número do Manifesto e data/hora da chegada
   - **MANIF SAIDA/ENTREGA**: Data de entrega do CTRC ou número do Manifesto e data/hora da saída
   - **CORTE**: Hora de referência para saída do veículo de transferência (apenas informativo, não interfere na permanência)
   - **PERMANENCI**: Quantidade de dias e horas que o CTRC permanece na unidade
   - Somente CTRCs com tempo de permanência superior a 1 dia são listados analiticamente
   - Totalização de CTRCs com permanência inferior é apresentada acima do subtotal da unidade destino final
   - Relatório considera CTRCs emitidos dos últimos 90 dias

2. **Opção 173 - CTRCs sem ocorrência a mais de 5 dias**:
   - Relaciona CTRCs que se encontram na unidade e há mais de 5 dias não receberam ocorrência
   - Considera como ocorrência: emissão do CTRC, emissão do último Manifesto, emissão do último Romaneio, lançamento de ocorrência
   - **5D+SEMOCO**: Indica há quantos dias o CTRC recebeu a última ocorrência
   - Tipo da última ocorrência: **EMI** (emissão), **MAN** (Manifesto), **ROM** (Romaneio), **OCO** (ocorrência lançada)
   - Disponibilizado somente para unidade MTZ (demais unidades veem estes dados nas últimas páginas do relatório 164)

### Cálculo do Custo de Transferência (Opção 412)

1. **Importância do custo de transferência**:
   - Um dos custos mais importantes no transporte
   - Representa valor significativo
   - Difícil apropriação aos responsáveis

2. **Apropriação do custo**:
   - **Na saída do veículo** (opção 025): Vincula Manifestos ao respectivo CTRB/OS de transferência (opção 072)
   - **Rateio nos Manifestos**: Valor do CTRB é rateado proporcionalmente ao Peso de cálculo total × distância percorrida (opção 403)
   - **Na chegada do Manifesto** (opção 030): Custo de transferência do Manifesto é rateado proporcionalmente ao peso de cálculo de cada CTRC

3. **Consulta mostra**:
   - Todos CTRBs em que o CTRC participou
   - Para cada CTRB: Respectivos Manifestos com valores de transferência rateados (primeira coluna VALTRANSF)
   - Segunda coluna VALTRANSF: Valor de transferência do CTRC proporcional à participação do peso calculado no total do Manifesto

### Integrações WebService (Opção 117)

**Operações possíveis**:
1. **SOLICITAÇÃO DE MONITORAMENTO PREVENTIVO (SMP)**: Transferência (opção 025), entrega (opção 035), coleta (opção 003)
2. **PROCESSAMENTO E ENVIO AUTOMÁTICO DE EDI PARA GERAÇÃO DE SMS**: Conforme opção 603
3. **ATUALIZAÇÃO CADASTRAL**: Integração para atualização de autorização da Gerenciadora de Risco de motoristas e veículos
   - Ocorre simultaneamente: emissão do Manifesto (opção 020), emissão do Romaneio (opção 035), atualização de cadastros de motoristas (opção 028) e veículos (opção 026)
4. **PROCESSAMENTO E ENVIO AUTOMÁTICO DE EDI DE OCORRÊNCIAS**: Conforme parametrização de programa EDI (opção 603)
5. **PROCESSAMENTO E ENVIO AUTOMÁTICO DE EDI DE AVERBAÇÃO**: Conforme parametrização de programa EDI (opção 603)

**Transações recusadas**:
- Listadas nos últimos 3 meses
- Filtros: Período, Situação (P-problemas, R-resolvidas, T-todas), Operação (S-SMP, M-SMS, C-Cadastral, O-Ocorrências, A-Averbação, T-todas)
- Histórico de geração mostra: Local, data, hora, usuário e parâmetros de geração

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-C05](../pops/POP-C05-imprimir-cte.md) | Imprimir cte |
| [POP-C06](../pops/POP-C06-cancelar-cte.md) | Cancelar cte |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
