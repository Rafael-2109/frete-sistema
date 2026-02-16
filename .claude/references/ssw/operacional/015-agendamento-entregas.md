# Opção 015 — Agendamento de Entregas

> **Módulo**: Operacional
> **Páginas de ajuda**: 4 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Registra o agendamento de entregas de CTRCs, combinando com o recebedor, e permite a emissão de CTRC complementar para cobrança do serviço de agendamento.

## Quando Usar

- Agendar entrega de um CTRC individual
- Agendar entrega de diversos CTRCs simultaneamente (filtros combinados)
- Emitir CTRC complementar cobrando o serviço de agendamento
- Consultar relatório de CTRCs com situação de agendamento
- Clientes que exigem agendamento obrigatório (marcado na opção 483)
- Agendamento prévio antes da autorização CT-e (clientes como Natura e Apple)

## Pré-requisitos

### Para cobrança do agendamento:
- Taxa de agendamento cadastrada na **opção 423** para o cliente OU na **Tabela genérica**
- Se não houver taxa cadastrada, agendamento é registrado sem cobrança

### Exigências fiscais:
- Unidade de emissão (origem ou destino) deve atender exigências da **opção 401**
- RPS é emitido automaticamente na unidade entregadora
- CT-e é emitido na unidade origem (quando RPS não é possível)

## Campos / Interface

### TELA INICIAL

**Agendar um CTRC** (3 formas de localizar):
- **CTRC (com DV)**: Sigla e número do CTRC com dígito verificador
- **CNPJ remetente + Nota Fiscal**: CNPJ do remetente e número da NF
- **Código de barras (CTRC)**: Chave da DACTE

**Agendar diversos**:
- Link que abre tela para agendamento em lote

**Relatório de agendados**:
- **Período de agendamento**: Período no qual foram feitos os agendamentos
- **Unidade de entrega**: (Opcional) Sigla da unidade responsável pela entrega
- **Situação**: P-pendente (não entregue), E-entregue, A-ambos

### TELA AGENDAR UM CTRC

**Dados do agendamento**:
- **Tipo do documento**: C-CT-e ou R-RPS (desabilitado quando não há taxa cadastrada)
- **Emite CTRC Complementar na unidade**: O-origem ou D-destino
- **Data da entrega agendada**: Data combinada para a entrega (ajusta a Previsão de Entrega do CTRC)
- **Hora**: (Opcional) Hora prevista para entrega agendada
- **Contato**: Nome do contato do agendamento
- **Telefone com DDD**: Telefone de contato do agendamento
- **Observações adicionais**: Observações da **opção 059** + complementos

### TELA AGENDAR DIVERSOS CTRCs

**Filtros de seleção**:
- **Agendados**: Seleciona CTRCs já agendados ou não
- **CNPJ remetente**: Filtra por CNPJ remetente
- **CNPJ destinatário**: Filtra por CNPJ destinatário
- **Autorização CTRC**: Período de autorização SEFAZ
- **Previsão de entrega**: Período de data de previsão de entregas
- **Unidade entregadora**: Filtra pela unidade entregadora
- **Agendamento obrigatório**: Seleciona CTRCs cujos destinatários estejam marcados como "exige agendamento" (opção 483)

**Dados do agendamento em lote**:
- **Tipo do documento**: C-CT-e ou R-RPS
- **Envia e-mail p/ destinat**: Envia e-mail aos destinatários para confirmação
- **Agendar para o dia**: Data combinada
- **Hora**: (Opcional) Hora prevista
- **Contato**: Nome do contato
- **Telefone com DDD**: Telefone de contato

**Links da tela**:
- **Agendar CTRCs abaixo marcados**: Executa agendamento, cobrança e disparo de e-mails para CTRCs selecionados
- **Envia e-mail ao abaixo marcados**: Envia e-mails SEM registro de agendamento (requer e-mail serv comple cadastrado na opção 483)

**Colunas importantes da tabela**:
- **CTRC**: Link para consulta (opção 101)
- **Destinatário**: Link para cadastro do cliente (opção 483)
- **Fone e e-mail**: Do destinatário (e-mail só dispara se cadastrado em "e-mail serv comple")
- **Agendado e hora**: Data/hora de agendamento já cadastrados
- **Mais**: Permite individualizar o agendamento para o CTRC

## Fluxo de Uso

### 1. Agendamento Combinado com o Recebedor

1. Transportadora contata o cliente recebedor
2. Definem em conjunto o agendamento
3. Alimentam a **opção 015** com os dados do agendamento
4. SSW envia e-mail de confirmação automaticamente

### 2. Agendamento por E-mail

1. E-mail de sugestão de agendamento é enviado automaticamente ao recebedor logo após chegada do veículo (**opção 030**) na unidade entregadora
2. E-mail é enviado para todos os clientes recebedores que:
   - Exigem agendamento (marcado na **opção 483**)
   - Possuem e-mail cadastrado (campo "e-mail serv comple" na **opção 483**)
3. DANFEs são anexadas aos e-mails
4. Recebedor confirma o agendamento via link no e-mail

### 3. Cobrança do Serviço

**Parcelas do CTRC** (automático):
- Cobrada já na emissão do CTRC principal
- Quando cliente recebedor está marcado como "agendamento obrigatório" (**opção 483**)

**Avulso com a realização do serviço** (manual):
- Cobrança via emissão de CTRC complementar de Agendamento (**opção 015**)
- Usuário que informa frete (**opção 925**): cobrança opcional
- Não cobra quando agendamento já está sendo cobrado como parcela do CTRC principal

**Regras de cálculo**:
- Cálculo usa tabela cadastrada na **opção 423**
- Base de cálculo SEM a parcela do Imposto Repassado do CTRC
- Imposto Repassado é adicionado ao final, conforme incidência no local de entrega
- Cobrança ocorre **uma única vez por CTRC** (reagendamentos não são cobrados novamente)

## Integração com Outras Opções

### Opções Relacionadas

- **Opção 004**: Emissão de CTRC Simplificado (não pode ter CTRC Complementar gerado)
- **Opção 007**: Autorização CT-e (aguarda agendamento antes de enviar ao SEFAZ para clientes específicos)
- **Opção 030**: Chegada do veículo (dispara e-mail de agendamento automático)
- **Opção 059**: Observações do CTRC (mostradas na tela de agendamento)
- **Opção 081**: Relação de CTRCs disponíveis para entrega (administra agendamentos)
- **Opção 101**: Consulta de CTRC
- **Opção 222**: Emissão de CTRC Complementar
- **Opção 225**: Relatório de acompanhamento de agendamentos de entrega
- **Opção 401**: Exigências fiscais para emissão
- **Opção 423**: Cadastro de taxa de agendamento (cliente ou Tabela Genérica)
- **Opção 483**: Cadastro de cliente destinatário (marca "exige agendamento" e cadastra e-mail)
- **Opção 925**: Informação de frete

### Administração de Agendamentos (Opção 081)

**Relação de CTRCs disponíveis para entrega**:

| Situação | Coluna AGENDAMENTO | Ocorrência SSW | SERVADIC |
|----------|-------------------|----------------|----------|
| Agendamento ainda não realizado | Sem data/hora | 35-Aguardando agendamento do cliente | A |
| Agendamento realizado | Com data/hora | 35-Aguardando agendamento do cliente | A |

**Operação**: Entregas devem ser efetuadas nas datas/horas agendadas (coluna AGENDAMENTO)

### Informações ao Cliente

**Ocorrência SSW 35**:
- Tratada como ocorrência da operação
- Disponibilizada via: rastreamento internet, SMS, e-mail, EDI

**E-mail de agendamento**:
- Enviado na chegada na unidade destino (**opção 030**)
- Para clientes que exigem agendamento (**opção 483**)
- DANFEs anexadas

**Acompanhamento**:
- **Opção 225**: Relatório de CTRCs com situação de agendamento
- **Opção 015**: Relatório de agendados (tela inicial)

## Observações e Gotchas

### Regras de Negócio

1. **Agendamento obrigatório antes da autorização CT-e**:
   - Clientes como Natura e Apple exigem agendamento prévio
   - **Opção 007** só envia CT-e ao SEFAZ após agendamento efetuado por esta opção 015

2. **Subcontratos**:
   - Subcontratos são agendados para entrega SEM cobrança do serviço
   - Para cobrar o serviço, a subcontratante deve emitir antes o seu CTRC Complementar (**opção 222**)

3. **Agendamento não pode ser excluído**:
   - Para permitir entrega imediata, altere a **data da entrega agendada** para hoje

4. **CTRC Simplificado** (**opção 004**):
   - Não pode ter CTRC Complementar gerado

5. **SSWBAR**:
   - Permite carregamento de entrega de CTRCs agendados já no dia anterior a partir das 18:00h

6. **DANFEs**:
   - Todos os e-mails de agendamentos disponibilizam respectivas DANFEs
   - Permite ao recebedor conhecer detalhes da mercadoria sendo recebida

7. **Cliente só recebe por NF**:
   - Configurável no recebedor (**opção 483**)
   - CTRC pode ser emitido para este recebedor apenas CTRCs sem agrupamento de NFs

8. **Entrega da mercadoria**:
   - Deve ser feita com o CTRC original

### Limitações e Restrições

- **Período de relatório**: Previsão de entrega limitada aos últimos 90 dias
- **E-mail**: Só dispara quando cadastrado no campo "e-mail serv comple" da **opção 483**
- **Cobrança única**: Mesmo que haja reagendamento, cobrança ocorre apenas uma vez por CTRC
- **Imposto Repassado**: Agendamento é calculado sobre base sem Imposto Repassado, que é adicionado ao final

### Relacionamento com Tutoriais

Para mais informações, consulte o tutorial:
- [Complementação de frete: Conceitos](javascript:show('/ajuda/ssw0684_conceito.htm'))
