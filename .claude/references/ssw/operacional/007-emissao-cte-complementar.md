# Opção 007 — Impressão e Autorização de CT-es

> **Módulo**: Operacional
> **Páginas de ajuda**: 12 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Impressão e autorização de CT-es (Conhecimento de Transporte Eletrônico) e RPS (Recibo Provisório de Serviços) no SEFAZ e prefeituras. A opção 007 **vincula os CT-es digitados (opção 004) a documentos fiscais**, permitindo que a operação perante o fisco seja efetivada e a expedição possa ocorrer.

Também gerencia o envio automático de XML de CT-es autorizados para **averbação** nas seguradoras e o cálculo de **emissão de CO2** por trecho de transporte.

## Quando Usar

- **Impressão de CT-es**: Imprimir CT-es digitados (opção 004) ou gerados em lote (opção 006)
- **Autorização no SEFAZ**: Enviar pré-CT-es para autorização (modo automático ou manual)
- **Reimpressão de CT-es**: Reimprimir CT-es autorizados (por faixa de NFs ou CT-es)
- **Trocar parceiro**: Trocar unidade destino antes da impressão para parceiro alternativo de menor custo
- **Imprimir fatura/boleto**: Opcionalmente imprimir fatura/boleto na expedição (CT-es FOB)
- **Averbação**: Enviar XML de CT-es autorizados para seguradoras (ATM, Porto Seguro, Senig, NDD Averba)
- **Pré-CTmodo): Configurar envio automático de pré-CT-es que atendem requisitos

## Pré-requisitos

### Documentos Digitados (Opção 004 ou 006)

CT-es devem estar digitados pela opção 004 (digitação manual) ou gerados em lote pela opção 006 (EDI/XML).

### Formulários Fiscais (Impressão em Matricial)

**Número Fiscal do Primeiro Formulário**: Número de Controle do primeiro formulário sem uso na impressora matricial. Vincula CT-es digitados ao documento físico autorizado pelo fisco estadual.

**Importante**: Número de Controle impresso deve ser igual ao impresso pela gráfica. Se divergente, reimprimir o CT-e. Número correto é necessário para Livro Fiscal e Arquivo Sintegra.

### Configurações de Averbação (Opção 903)

**Documentos Averbáveis**: Definir quais tipos de documentos (opção 903/Gerenciamento de Risco/Averbação). Documentos não averbáveis são enviados com valor de mercadoria igual a R$ 0,01.

**Clientes com seguro próprio** (opção 483, Seguro RCFDC = S): Não têm mercadorias averbadas pela transportadora.

**RCFDC (DDR)**: Parametrizar clientes com carta DDR (opção 483, campo RCFDC). Envia CNPJ do responsável pelo seguro no XML tag `<ObsCont xCampo="RESPSEG"><xTexto>000000000000000</xTexto>`. Se N-não, envia CNPJ da filial emissora.

### Configurações de Pré-CT-e (Opção 903)

**Autorização e operação de Pré-CT-es**: Ativar controles para envio de pré-CT-es ao SEFAZ (opção 007) e prefeituras (opção 009).

**Modo de envio**:
- **A - Automático**: Pré-CT-es que atenderam requisitos são enviados automaticamente a cada 1 minuto. Após autorização, devem ser impressos. RPSs (opção 009) também impressos automaticamente.
- **S - Automático sem impressão**: Mesma funcionalidade de A, sem necessidade de impressão posterior. Opção 025 e opção 038 podem ser usadas para impressão.
- **M - Manual**: Opção 007, opção 014/DF e opção 009 devem ser executados manualmente.

**Requisitos para envio** (configuráveis com N=exige):
- **Com uso de Tabela Genérica**: N = não envia pré-CT-e com frete calculado pela Tabela Genérica (opção 923)
- **Sem pesagem**: N = ativa necessidade de repesagem dos pré-CT-es
- **Sem cubagem**: N = ativa necessidade de cubagem dos pré-CT-es
- **Sem recubagem**: N = ativa necessidade de segunda cubagem (primeira não confiável)
- **Sem Romaneio/Packing List**: N = exige que Romaneio/Packing seja capturado (opção 006/Romaneio) atestando recebimento
- **Sem captura SSWBAR**: N = ativa necessidade de captura de volumes pelo SSWBar (descarga de coleta ou carregamento de Manifesto)
- **Sem conferência pelo conferente**: N = ativa necessidade de conferência da mercadoria (opção 284)
- **Complementar de Reembolso sem autorização**: N = Complementar de Reembolso (opção 222) não será enviado sem autorização prévia por e-mail ou opção 201

**Permite operação com pré-CT-e** (pelo menos uma deve ser N para impedir entrega com pré-CT-es):
- **Emissão de Manifesto Operacional** (opção 020) e SSWBar: Opção 019 relaciona pré-CT-es disponíveis para transferência
- **Saída de veículos** (opção 025)
- **Emissão de Romaneio de Entregas** (opção 035) e SSWBar: Opção 081 relaciona pré-CT-es disponíveis para entrega

**Nota**: Ativação pode provocar lançamento da ocorrência SSW 80 "DOCUMENTO DE TRANSPORTE EMITIDO" no rastreamento fora da sequência normal.

### Parceiros Alternativos (Opção 408, 401, 402)

Para trocar parceiro antes da impressão:

1. **Cadastrar unidades** (opção 401): Unidades operadas por parceiros alternativos com siglas específicas. Não é necessário vincular cidades (opção 402).
2. **Definir comissão** (opção 408): Comissão de recepção de cada parceiro.
3. **Vincular parceiros alternativos** (opção 408): Vincular alternativos a uma unidade principal. Unidade principal é aquela usada para definir cidades atendidas (opção 402).

### Fatura/Boleto na Expedição

Condições para impressão de fatura/boleto (CT-es FOB) na expedição:

- CT-es devem estar impressos
- Clientes (opção 483): CRÉDITO = BANCO ou CARTEIRA, CONDIÇÃO PARA FATURAMENTO = APÓS IMPRESSÃO, PERIODICIDADE diária
- Contas bancárias (opção 904): IMPRIME BLOQUETO = SIM, USA BLOQUETO PRÉ-IMPRESSO = NÃO
- Unidade (opção 401): GERA FATURA/BLOQUETO = SIM

Se condições não atendidas, faturas/boletos não são impressas (faturadas e impressas pelo Faturamento da Matriz).

### Tipo de Impressora

- **CT-e (Matricial)**: Impressora matricial para formulários fiscais
- **Fatura/Boleto (Jato de tinta ou Laser)**: Qualidade na impressão do código de barras do boleto

### Instalação de Impressora

Executar link "CONFIGURAR SEU MICRO" do Menu Principal. Quando mal funcionamento, clicar "VERIFICAR" para verificar se configuração está atualizada.

## Campos / Interface

### Tela Inicial

**NUMERO FISCAL DO PRIMEIRO FORMULARIO**: Número de Controle do primeiro formulário sem uso na impressora matricial. Tela mostra "ÚLTIMO NÚMERO DE FORMULÁRIO UTILIZADO".

**QUANTIDADE DE CTRCS A SEREM IMPRESSOS**: Quantidade de CT-es a serem impressos na unidade (digitados por todos da unidade ou de outras unidades para CT-es complementares).

**CLASSIFICADOS POR**:
- **N - Nenhum**: Ordem de digitação
- **F - Nota Fiscal**: Ordem da numeração da Nota Fiscal (útil quando NFs estão fisicamente classificadas, comum com clientes EDI)
- **U - Unidade destino**: Classificação por unidade destino

**TIPO DE FRETE**: Selecionar CT-es CIF ou FOB. Permite vias de cobrança de CT-es CIF permanecerem na origem aguardando emissão de faturas (opção 440).

**UFS DE DESTINO**: Selecionar CT-es de até 5 UFs destino.

**UNIDADES DE DESTINO**: Selecionar CT-es de até 5 unidades destino.

**PLACA DO VEICULO DE COLETA**: Selecionar apenas um veículo de coleta (CT-es auxiliam na descarga).

**CNPJ DO REMETENTE**: Útil quando expedição por EDI é muito grande (imprimir CT-es de cliente remetente específico).

### Ações de Impressão

**DIGITADOS POR MIM**: Apenas CT-es digitados por mim, ainda não impressos. Considera critérios da tela.

**DIGITADOS POR TODOS**: Todos os CT-es digitados pela filial, ainda não impressos. Considera critérios da tela.

**OS DIGITADO VIA EDI**: Apenas CT-es gerados a partir de arquivos magnéticos incluídos pela opção 006.

### Ações de Reimpressão

**Informando-se faixas de NOTAS FISCAIS**: Primeira e última NF da faixa (mesma ordem digitada) que não tiveram CT-es impressos. Sistema considera apenas NFs digitadas nas últimas 3 horas (reduzir repetição com outros remetentes). Se repetição, usar faixa de CT-es.

**Informando-se faixas de CTRCs**: Números dos CT-es inicial e final da faixa, sem as séries (sigla). Para descobrir número dos CT-es, usar opção 101 ou opção 063.

**SELECIONAR**: Faixa informada pode selecionar "MEUS" (digitados por mim) ou "TODOS" (digitados por todos da unidade).

**Importante**: Reimpressão pode ser usada para imprimir CT-es específicos mesmo ainda não estando impressos.

### Links Adicionais

**RELACIONAR CTRCS NÃO IMPRESSOS**: CT-es não impressos são relacionados. Clicando no CT-e, sistema traz tela de digitação para alteração.

**TROCAR UNIDADES DESTINO DE CTRCS**: Trocar unidades destino de CT-es não impressos visando troca de parceiro (diferente do definido em opção 408 e opção 402). Vide seção "Trocar Parceiro".

**VERSÃO ANTERIOR**: Quando habilitado, versão anterior de impressão do CT-e está disponível. Usar quando alterações na impressão apresentam erros que não podem ser corrigidos de imediato pela Equipe SSW.

### Impressão da Observação do CT-e

Campo OBSERVACAO do CT-e imprime mensagens na seguinte ordem de prioridade:

**NAS 3 PRIMEIRAS LINHAS**:
1. Notas Fiscais agrupadas
2. Observação digitada pelo usuário (opção 004) + mensagem padrão (opção 059)
3. Cancelamento
4. Cortesia
5. Frete a Vista
6. Devolver canhoto de NF carimbado e assinado
7. Informações sobre composição da parcela OUTROS do frete

**NA LINHA 4**:
- Informação de tributação ICMS

## Fluxo de Uso

### 1. Fluxo Geral — Impressão de CT-es

```
Opção 004 ou 006 → CT-es digitados/gerados
↓
Opção 007 → Informar Número Fiscal do Primeiro Formulário
↓
Selecionar critérios (tipo de frete, UF destino, placa de coleta, etc.)
↓
DIGITADOS POR MIM / DIGITADOS POR TODOS / OS DIGITADO VIA EDI
↓
Sistema imprime CT-es na matricial
↓
(Opcional) Sistema pergunta se deseja imprimir FATURA/BLOQUETO
↓
Grampear CT-e com NF-e e colocar no escaninho da filial destino
```

### 2. Fluxo de Reimpressão

```
Opção 007 → Informar critérios (tipo de frete, UF destino, etc.)
↓
Informar faixa de NOTAS FISCAIS ou faixa de CTRCs
↓
SELECIONAR: MEUS ou TODOS
↓
Sistema imprime CT-es selecionados
```

### 3. Fluxo de Troca de Parceiro

```
Opção 004 ou 006 → CT-es digitados/gerados
↓
Opção 007 → Link TROCAR UNIDADES DESTINO DE CTRCS
↓
Marcar CT-es que terão unidade trocada
↓
Sistema apresenta unidade principal + alternativos com comissões de recepção
↓
Escolher unidade (parceiro) desejada (geralmente menor comissão)
↓
(Opcional) Informar veículo provisório para CT-es aparecerem apontados (opção 020)
↓
Opção 007 → Imprimir CT-es normalmente
```

### 4. Fluxo de Autorização de Pré-CT-es (Modo Automático)

```
Opção 903 → Configurar Modo = A ou S
↓
Opção 004 ou 006 → CT-es digitados/gerados
↓
Requisitos atendidos (pesagem, cubagem, captura SSWBar, etc.)
↓
SSW envia pré-CT-es automaticamente ao SEFAZ a cada 1 minuto
↓
SEFAZ autoriza CT-es
↓
Modo A: Opção 007 → Imprimir CT-es autorizados
Modo S: Opção 025 ou 038 → Imprimir (opcional)
```

### 5. Fluxo de Averbação (Automático)

```
Opção 007 → CT-e autorizado pelo SEFAZ
↓
SSW envia XML para seguradora via WebService (ssw1381, ssw1674, ssw1928, ssw3213)
↓
Opção 101 → Verificar resumo de averbação (protocolo, data/hora, valor enviado, número EDI)
↓
Opção 056 → Relatório 165 (Conferência de Averbação) — diário
↓
Opção 117 → Verificar recusas de averbação (se houver)
```

### 6. Fluxo de Cálculo de CO2 (Automático)

```
Coletas: Opção 007/009/014 → Autorização do CT-e → Cálculo CO2
Transferências: Opção 030 → Chegada do veículo → Cálculo CO2
Entregas: Opção 035 → Emissão Romaneio de Entregas → Cálculo CO2
↓
Opção 330 → Consultar CO2 emitido pelo CT-e por trecho
```

## Integração com Outras Opções

### Antes da Impressão

| Opção | Função |
|-------|--------|
| 004 | Digitação manual de CT-es |
| 006 | Geração de CT-es em lote (EDI/XML) |
| 401 | Cadastro de unidades (parceiros alternativos) |
| 402 | Vinculação de cidades a unidades |
| 408 | Comissões de recepção (parceiros) e vinculação de alternativos a principal |
| 483 | Cadastro de clientes (CRÉDITO, CONDIÇÃO PARA FATURAMENTO, PERIODICIDADE, RCFDC) |
| 904 | Contas bancárias (IMPRIME BLOQUETO, USA BLOQUETO PRÉ-IMPRESSO) |
| 903 | Parametrizações gerais (averbação, pré-CT-es, gerenciamento de risco) |
| 059 | Mensagem padrão para observação do CT-e |

### Durante a Impressão

| Opção | Função |
|-------|--------|
| 101 | Descobrir número dos CT-es correspondentes a NFs |
| 063 | Idem |
| 007 | Trocar unidade destino de CT-es não impressos (link TROCAR UNIDADES DESTINO) |

### Após a Impressão

| Opção | Função |
|-------|--------|
| 024 | Cancelamento de Manifesto (se CT-e já manifestado, necessário cancelar Manifesto antes) |
| 004 | Cancelamento de CT-e (se ainda não manifestado) |
| 017 | Reimpressão de faturas/boletos (em caso de problemas) |
| 020 | Emissão de Manifesto Operacional (CT-es impressos) |
| 440 | Impressão de faturas (após faturamento pela Matriz) |

### Averbação

| Opção | Função |
|-------|--------|
| 903 | Parametrização de averbação (documentos averbáveis, valor máximo de mercadoria) |
| 600 | Programas EDI de averbação (ssw1381 ATM, ssw1674 Porto Seguro, ssw1928 Senig, ssw3213 NDD Averba) |
| 056 | Relatório 165 (Conferência de Averbação) — gerado diariamente |
| 101 | Resumo de averbação (protocolo, data/hora, valor enviado, número EDI) |
| 117 | Transações de WebService Recusadas (recusas de averbação) |
| 056 | Situação Geral - Relatório 01 (percentual de documentos averbados diariamente) |

### Pré-CT-es

| Opção | Função |
|-------|--------|
| 903 | Autorização e operação de Pré-CT-es (requisitos, modo de envio) |
| 006 | Captura de Romaneio/Packing List |
| 284 | Conferência da mercadoria pelo conferente |
| 019 | Relacionar pré-CT-es disponíveis para transferência |
| 025 | Saída de veículos (permite operação com pré-CT-es) |
| 035 | Emissão de Romaneio de Entregas (permite operação com pré-CT-es) |
| 038 | Impressão de CT-es autorizados (modo S) |
| 081 | Relacionar pré-CT-es disponíveis para entrega |
| 201 | Autorizar CTRC Complementar de Reembolso (se sem autorização automática) |
| 222 | Emissão de CTRC Complementar de Reembolso |

### CO2

| Opção | Função |
|-------|--------|
| 097 | Cadastro de Tipo de Veículo (consumo médio Km/l, veículo verde) |
| 330 | CO2 emitido pelo CTRC (detalha por trecho de transporte) |
| 403 | Distância da rota (usada no cálculo de CO2 em transferências) |
| 030 | Chegada de veículos (cálculo de CO2 em transferências) |
| 035 | Emissão de Romaneio de Entregas (cálculo de CO2 em entregas) |

## Observações e Gotchas

### Regras do Processo

**ALTERACAO DE CTRC**: CT-e só pode ser alterado pela opção 004 se ainda não tiver sido impresso pela opção 007.

**CANCELAMENTO DE CTRC**: Se CT-e já impresso, sistema só permite cancelamento (opção 004) se ainda não manifestado. Se já manifestado, necessário cancelar Manifesto antes (opção 024).

**IMPRESSÃO HABILITA MANIFESTAÇÃO**: Somente a partir do CT-e impresso passa a existir a operação perante o fisco, e assim a expedição poderá ocorrer.

**GRAMPEAR COM NF-E**: Depois de impresso, cada CT-e deve ser grampeado com sua respectiva Nota Fiscal e colocado no escaninho da filial destino.

### Troca de Parceiro

**Objetivo**: Trocar parceiro original para alternativos sem alterar frete, prazos, etc. Decisão motivada por menor custo (comissão).

**Quando trocar**: Antes da impressão do CT-e (opção 007 e opção 008, link TROCAR UNIDADE DESTINO).

**Parâmetros são da unidade principal**: Todos os parâmetros (frete, prazo, distância, pólo/região/interior, etc.) das unidades alternativas são os da unidade principal cadastrada (opção 401 e opção 402). Comissões (opção 408) das alternativas usam estes parâmetros para cálculo.

**Uma unidade principal pode ser alternativa**: Unidade principal pode ser cadastrada também como alternativa (opção 408). Ocorre quando parceiro opera unidade principal e também atua como alternativa para outra principal. No entanto, uma unidade só pode ser alternativa de uma única principal.

**Registro da troca**: CT-es/Subcontratos que tiverem unidades destino trocadas terão informação gravada nas ocorrências.

**CTRCs FOB A VISTA**: Na troca, sistema estorna débito na unidade anterior e faz na nova (Conta do Fornecedor, opção 486). Para débito ocorrer, unidade (agência ou parceira) deve estar configurada (opção 401) com SIM em "DEBITA AUTOMATICAMENTE FRETE A VISTA".

**Veículo provisório**: Pode-se informar veículo provisório para CT-es/Subcontratos com unidades trocadas aparecerem apontados na opção 020.

### Troca Excepcional (Opção 094)

**Quando usar**: Excepcionalmente, após impressão do CT-e, troca de unidade destino pode ser feita pela opção 094.

**Condições**:
- CT-es devem estar incluídos no Manifesto com destino para a unidade desejada (Manifesto deve ser o último destes CT-es)
- Manifesto deve estar emitido mas não pode ter recebido saída (opção 025)
- CT-es não podem ter comissão já paga (incluídos em Mapa)
- Nova unidade destino (Alternativa) deve estar previamente cadastrada (opção 408) com comissões. Pode ser também FEC (carga fechada).

**Consequências**:
- Informação da troca gravada nas ocorrências do CT-e
- Comissão de recepção recalculada para nova unidade
- Etiquetas de identificação de volumes mostram unidade de destino e setor originais (pode causar confusão)

**IMPORTANTE**: Tratar como caso **Excepcional**, nunca como procedimento padrão. Troca causa documentos em desacordo com informações vigentes, podendo causar confusão em diversos processos.

**Alternativa**: Troca pode ser feita diretamente na emissão do Manifesto (opção 020).

### Fatura/Boleto na Expedição

**Impressão de fatura/boleto**: Sistema pergunta após impressão de CT-es via opção 007 se deseja imprimir FATURA/BLOQUETO (se unidade configurada com opção 401 GERA FATURA/BLOQUETO = SIM).

**Arquivo de remessa não é necessário**: Arquivo não precisa ser gerado (opção 443) para FATURA/BLOQUETO ser gerado na expedição. Arquivo deve ser gerado apenas uma única vez no dia pela equipe de Faturamento. Faturas/boletos emitidos nas expedições são incluídos automaticamente.

**Cancelamento automático**: Cancelamento do CT-e (opção 004) cancela automaticamente a FATURA/BLOQUETO correspondente.

### Averbação

**Envio automático após autorização**: XML de CT-es autorizados (opção 007) é enviado automaticamente via WebService para seguradora.

**Padrões de integração**:
- **ATM** (ssw1381)
- **Porto Seguro** (ssw1674)
- **Senig Seguros** (ssw1928)
- **NDD Averba** (ssw3213)

**Tag `<vCargaAverb>`**: Se documento averbável (opção 903) marcado com S-sim, envia valor total da NF. Se N-não, envia R$ 0,01.

**Tag `<RESPSEG>`**: Se cliente tem carta DDR (opção 483, RCFDC = S), envia CNPJ do responsável pelo seguro. Se N-não, envia CNPJ da filial emissora.

**Valor máximo averbado**: Pode ser incluído valor máximo em opção 903/Frete/Valor máximo de mercadoria do CTRC. SSW trava emissão em opção 004, opção 005 e opção 006.

**Monitoramento**:
- **Relatório 165** (opção 056): Gerado diariamente, lista todos os documentos autorizados no dia anterior (incluindo cancelados) enviados para Seguradora com protocolos de averbação e/ou motivos de rejeições
- **Link Frete** (opção 101): Mostra resumo (Nº do arquivo de averbação, protocolo/número de averbação, data/hora do envio, valor enviado, número de EDI)
- **Transações de WebService Recusadas** (opção 117): Lista recusas por parte da seguradora
- **Situação Geral - Relatório 01** (opção 056): Apresenta percentual de documentos averbados diariamente
- **Alertas diários no Menu Principal**: Para usuários masters quando mercadorias averbáveis não forem 100% averbadas

**Acompanhamento permanente**: Resultado do processamento deve ser acompanhado permanentemente pela transportadora. Se divergências em relação ao esperado, acionar Equipe SSW imediatamente para ajustes.

### Pré-CT-es

**Conceito**: CT-es que ainda não atendem todos os requisitos para envio ao SEFAZ (pesagem, cubagem, captura SSWBar, conferência, etc.).

**Requisitos configuráveis**: Opção 903/Autorização e operação de Pré-CTRCs. Cada requisito pode ser marcado com N (exige atendimento) ou S (não exige).

**Modo de envio**:
- **A - Automático**: Pré-CT-es enviados automaticamente a cada 1 minuto. Após autorização, devem ser impressos. RPSs impressos automaticamente.
- **S - Automático sem impressão**: Idem A, sem necessidade de impressão posterior. Opção 025 e opção 038 podem ser usadas.
- **M - Manual**: Opção 007, opção 014/DF e opção 009 devem ser executados manualmente.

**Pelo menos uma operação deve ser bloqueada**: Pelo menos uma das opções (Emissão de Manifesto Operacional, Saída de veículos, Emissão de Romaneio de Entregas) deve permanecer marcada com N para impedir entrega com pré-CT-es.

**Complementar de Reembolso**: Se "Complementar de Reembolso sem autorização" marcado com N (opção 903), pré-CTRC Complementar de Reembolso (opção 222) não será enviado ao SEFAZ sem prévia autorização por e-mail automático ou opção 201.

**Ocorrência SSW 80**: Ativação de pré-CT-es pode provocar lançamento da ocorrência SSW 80 "DOCUMENTO DE TRANSPORTE EMITIDO" no rastreamento fora da sequência normal.

### Gerenciamento de Risco (Opção 903)

**Processos vinculados** a carregamentos e saída de veículos:

**1. Averbação**: Envio à seguradora dos XMLs de CT-es autorizados (opção 007) e MDF-es (opção 025).

**2. PGR (Plano de Gerenciamento de Riscos)**: Configuração de limites de valores de mercadorias no carregamento de veículos de coletas/entregas (opção 003 e opção 035) e transferências (opção 020). Configuração pela opção 390.

**3. Liberações**: Autorizações de cavalo, carreta, motorista e ajudante verificadas na emissão do Manifesto (opção 020). Autorizações dadas pela gerenciadora de riscos e cadastradas em: opção 026, opção 028 e opção 163. Algumas gerenciadoras fornecem autorizações on-line.

**4. SMP (Solicitação de Monitoração Preventiva)**: Solicitação eletrônica à gerenciadora de riscos. Configurada pelo SSW (futuramente disponível em opção 903). Por padrão SSW aguarda **10 segundos** a resposta do servidor.

**5. GPS**: Recebimento de dados de localização dos veículos por satélite, fornecida pela gerenciadora de riscos. Configurada pelo SSW (futuramente disponível em opção 903).

**Regras de validação** (opção 903/Liberações):
- **Individual**: Cavalo, carreta, motorista e ajudante validados individualmente
- **Conjunto**: Validados em conjunto
- **Operação**: Operação (opção 003, opção 020 e opção 035) deve ter liberação específica da gerenciadora. Nenhum cadastro é verificado.
- **Nenhuma**: Nenhuma validação efetuada

Se omitida, **individual** será utilizada.

**Em caso de não conformidade**:
- **A - Alerta**: Sistema apenas alerta não atendimento das regras (opção 390)
- **B - Bloqueia**: Bloqueia emissão de Romaneio, Manifesto e coletas

**Considerar subcontratos** (opção 390):
- **F - Fiscal**
- **L - Não fiscal**
- **A - Ambos**
- **N - Não considerar**

**SMP rejeitada**: Define se impede emissão de Romaneio de Coletas (opção 003), MDF-e (opção 025) e Romaneio de Entregas (opção 035).

### CO2 (Opção 330)

**Cálculo por trecho**: CO2 emitido pelos veículos é calculado por trecho de transporte (coleta, transferência, entrega).

**Quando ocorre o cálculo**:
- **Coletas**: Autorização do CT-e (opção 007, opção 009 e opção 014)
- **Transferências**: Chegada dos veículos (opção 030)
- **Entrega**: Emissão do Romaneio de Entregas (opção 035)

**Dados necessários** (opção 097 - Tipo de Veículo):
- **Consumo médio (Km/l)**: Necessário para ativação do cálculo de emissão para todo o domínio
- **Veículo verde**: Indicativo de veículo verde (não emite CO2)

**Fórmula do cálculo**:
1. Litros combustível consumidos = Distância / Consumo
2. CO2 veículo = Litros combustível x Fator (fator de emissão que converte litros em kg de CO2)
3. CO2 CTRC = CO2 veículo x (peso CTRC / Capacidade veículo)

**Combustíveis**: Gasolina, etanol, flex, diesel, GNV, elétrico, híbrido (diesel), GAV (gasolina de aviação), QAV (querosene de aviação).

**Distâncias**:
- **Coleta**: Do endereço cliente remetente até unidade expedidora (usa coordenadas geográficas do cliente remetente)
- **Transferência**: Da rota (opção 403)
- **Entrega**: Da unidade destinatária até local de entrega

**Documentos de referência**: CTRC, Manifesto Operacional, Romaneio de Entregas.

**Total CO2**: Mostrado na opção 330. Se ainda não entregue, indicativo "parcial" é mostrado.

**Domínio**: Transportadora que transportou no trecho (pode ser parceiro, desde que use SSW também).

### Integração com Envia By Bus (Ssw2366)

**Geração automática de CT-es**: API recebe dados da Envia By Bus para gerar CT-e normal ou Redespacho Intermediário (ssw2361).

**Configuração pelo SSW**: CNPJ cliente, usuário API (opção 925), sigla da unidade emissora, placa do veículo, código mercadoria e código de espécie.

**Processo**: Geração de CTRCs é automática, ficando disponíveis para envio ao SEFAZ (opção 007).

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-C03](../pops/POP-C03-emitir-cte-complementar.md) | Emitir cte complementar |
| [POP-C05](../pops/POP-C05-imprimir-cte.md) | Imprimir cte |
| [POP-C06](../pops/POP-C06-cancelar-cte.md) | Cancelar cte |
| [POP-C07](../pops/POP-C07-carta-correcao-cte.md) | Carta correcao cte |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E02](../pops/POP-E02-faturar-manualmente.md) | Faturar manualmente |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-F05](../pops/POP-F05-bloqueio-financeiro-ctrc.md) | Bloqueio financeiro ctrc |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
| [POP-G04](../pops/POP-G04-relatorios-contabilidade.md) | Relatorios contabilidade |
