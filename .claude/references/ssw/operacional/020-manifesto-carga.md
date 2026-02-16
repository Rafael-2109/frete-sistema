# Opção 020 — Manifesto de Carga

> **Módulo**: Operacional
> **Páginas de ajuda**: 11 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Emissão de Manifestos Operacionais para transferência de carga entre unidades. O Manifesto Operacional relaciona CTRCs que serão carregados em um veículo, servindo como base para:
- Geração do MDF-e (Manifesto Eletrônico de Documentos Fiscais) no SEFAZ
- Controle de carga/descarga via SSWBar
- Rastreamento de transferências
- Vinculação com CTRB/OS para avaliação de rentabilidade

## Quando Usar

- **Transferência entre unidades**: Agrupar CTRCs que serão transportados juntos
- **Antes da contratação do veículo**: Manifesto pode ser emitido antes do CTRB/OS (opção 072)
- **Operação com sorter**: Geração automática via opção 220
- **Operação fluvial**: Transferências por balsa (emitida por unidade PORTUÁRIA)
- **Operação aérea**: Transferência por companhia aérea (vincula AWB via opção 069)

## Pré-requisitos

### Dados Cadastrais
- **Veículos**: Cavalo e carreta cadastrados (opção 026)
- **Motoristas**: Motorista e ajudante cadastrados (opção 028)
- **Unidades**: Origem e destino cadastradas (opção 401)
- **Rotas**: Previsão de chegada e UFs de percurso cadastradas (opção 403)

### Liberações de Risco (opção 390)
- Veículo com liberação vigente da gerenciadora de risco
- Motorista e ajudante com liberações vigentes
- Requisitos de gerenciamento (rastreador, isca, escolta) conforme valor de mercadoria

### Parametrização MDF-e
- Inscrição Estadual configurada pela Equipe SSW
- Certificado digital válido
- RNTRC do proprietário do veículo atualizado (opção 027)

## Campos / Interface

### Tela Inicial — Criação da Placa Provisória

**CARRETA PROVISÓRIA**: Nome fictício para identificar o agrupamento de CTRCs. Pode ser qualquer nome descritivo (ex: "SP001", "GAIOLA-10"). No momento do carregamento pode não ter definição da carreta definitiva.

**CARRETAS EM CARREGAMENTO**: Lista de placas provisórias em processo de carregamento. Clique para continuar o carregamento de uma placa já iniciada.

### Tela de Carregamento — Apontamento de CTRCs

**CARREGAR CTRC**: Informe série, número e dígito verificador sem separador. Zeros à esquerda são desnecessários. Use tecla '+' para manter a série e posicionar cursor no próximo número.

**CARREGAR TODOS OS CTRCS DA SÉRIE**: Informando apenas a série, todos os CTRCs disponíveis no armazém são apontados de uma vez.

**VER APONTADOS**: Mostra todos os CTRCs disponíveis para carregamento, permitindo seleção com mouse.

**FILTRO**: Permite filtrar CTRCs por:
- Série
- Cidade destino
- Unidade destino
- Cliente remetente
- Cliente destinatário
- Data de emissão

**TOTAIS DESTE CARREGAMENTO**: Quantidade, peso, m³, valor de mercadoria e frete dos CTRCs apontados na placa provisória.

**DISPONÍVEL NO ARMAZÉM**: Totais dos CTRCs filtrados disponíveis. CTRCs com código de ocorrência não aparecem como disponíveis.

**TOTAIS JÁ CARREGADOS**: CTRCs já apontados no veículo, incluindo carga remanescente (não descarregada no manifesto anterior via opção 030).

### Tela de Emissão — Dados do Manifesto

**PLACA DA CARRETA**: Placa definitiva que transportará a mercadoria (deve estar cadastrada na opção 026).

**BALSA** (operação fluvial): Cadastrada na opção 026.

**EMPURRADOR** (operação fluvial): Cadastrado na opção 026.

**CPF DO PILOTO** (operação fluvial): Cadastrado na opção 028.

**PORTO DESTINO** (operação fluvial): Unidade tipo PORTUÁRIA cadastrada na opção 401.

**CONFERENTE**: Se controle de conferentes ativado (opção 903), informar número do conferente que efetuou o carregamento (opção 111).

**UNIDADE DESTINO**: Unidade destino do manifesto.

**PREVISÃO DE CHEGADA**: Data/hora sugerida conforme rota (opção 403), pode ser alterada.

**UFs DO PERCURSO**: UFs sugeridas da rota (opção 403), podem ser alteradas. Se não cadastradas ou CTRC FEC, sistema sugere percurso com menor quantidade de UFs. UFs origem e destino são informadas mas não impressas no MDF-e nem gravadas no XML.

## Fluxo de Uso

### 1. Montagem da Placa Provisória

```
Opção 020 → Informar CARRETA PROVISÓRIA (nome fictício)
→ CARREGAR CTRC (série + número + DV)
→ Repetir para todos os CTRCs
→ Verificar TOTAIS DESTE CARREGAMENTO
→ EMITIR O MANIFESTO
```

### 2. Confirmação de Dados do Veículo

```
Informar PLACA DA CARRETA (definitiva)
→ CONFERENTE (se ativado controle)
→ Confirmar dados
→ Sistema emite Manifesto Operacional
```

### 3. Contratação do Veículo (opção 072)

Emitir CTRB/OS para o veículo que transportará os Manifestos Operacionais. O CTRB pode ser emitido antes ou depois do manifesto.

### 4. Saída do Veículo (opção 025)

```
Opção 025 → Escolher CAVALO ou MANIFESTO (código de barras)
→ Desmarcar manifestos que NÃO receberão saída
→ Confirmar dados: Proprietário, TAC, CTRB/OS, Previsão de chegada, UFs percurso
→ Sistema emite MDF-e no SEFAZ
→ Imprimir DAMDFE (Sintético, sem valor de frete, ou com valor de frete)
```

### 5. Chegada no Destino (opção 030)

Unidade destino registra chegada do manifesto, encerrando automaticamente o MDF-e no SEFAZ.

## Integração com Outras Opções

### Antes da Emissão do Manifesto

| Opção | Função |
|-------|--------|
| 026 | Cadastro de veículos (cavalo, carreta, balsa, empurrador) |
| 027 | Cadastro de proprietários (RNTRC obrigatório para MDF-e) |
| 028 | Cadastro de motoristas e ajudantes |
| 390 | Regras de gerenciamento de risco por valor de mercadoria |
| 401 | Cadastro de unidades origem/destino |
| 403 | Cadastro de rotas (previsão de chegada, UFs de percurso) |
| 903 | Configuração de gerenciadoras de risco |

### Durante o Carregamento

| Opção | Função |
|-------|--------|
| SSWBar | Carga/descarga de veículos referenciando Manifesto Operacional |
| 021 | Cadastro de gaiolas (para unitização) |
| 220 | Emissão automática de Manifestos via sorter |

### Após a Emissão do Manifesto

| Opção | Função |
|-------|--------|
| 023 | Consulta e reimpressão de Manifestos Operacionais |
| 024 | Cancelamento de Manifesto Operacional e MDF-e |
| 034 | Conferência de Manifestos vs documentos do cliente (DACTEs/DANFEs) |
| 072 | Contratação do veículo (CTRB/OS) |
| 025 | Saída do veículo e geração do MDF-e |
| 030 | Chegada do veículo e encerramento do MDF-e |
| 056 | Gestão de rentabilidade (relatório 020: resultado de viagens concluídas) |

### Operações Especiais

| Opção | Função |
|-------|--------|
| 069 | Vincular AWB (CT-e aéreo) ao Manifesto Operacional |
| 179 | Arquivo Fronteira Rápida RN (simplificação de postos fiscais) |
| 201 | Retransmissão, impressão e reimpressão de MDF-es |
| 210 | Divulgação e reserva de Placa Provisória para compartilhamento com outras transportadoras |
| 725 | Romaneio de carregamento (itens do estoque) |

### Rastreamento e Averbação

| Opção | Função |
|-------|--------|
| 383 | Configuração de e-mails de rastreamento |
| Site | Rastreamento on-line disponibilizado para clientes |
| 670 | Geração automática de subcontratos no parceiro |

## Observações e Gotchas

### MDF-e (Manifesto Eletrônico de Documentos Fiscais)

**Agrupamento por UF destino**: Manifestos Operacionais são agrupados para resultar em **um único MDF-e por CNPJ emissor e UF destino**. Encerramentos e inclusões são feitos automaticamente pelo SSW.

**Limite de CT-es**: SEFAZ aceita máximo de 2.048 Kb no XML, cerca de **10.000 CT-es por MDF-e**. Para grandes quantidades, imprima DAMDFE Sintético (relaciona apenas os Manifestos sem listar CT-es).

**3 tipos de DAMDFE**:
- **DAMDFE Sintético**: Não relaciona CTRCs, apenas totais
- **DAMDFE sem valor de frete**: Lista todos os CTRCs sem fretes
- **DAMDFE com valor de frete**: Lista todos os CTRCs com fretes

**DAMDFEs devem substituir anteriores**: DAMDFEs emitidos na saída (opção 025) devem ser entregues ao motorista, substituindo as anteriores.

**Evitar duplicidade de CT-e**: CT-e não é incluído em MDF-e se já foi manifestado em Manifestos anteriores com mesma unidade de emissão ou destino, e se já está na unidade destino. Evita multas. Estes CT-es aparecem no Manifesto Operacional para conferência de descarga (sobras). Pode ser desativado em opção 903/Operação/Evitar duplicidade de CT-e em MDF-e.

**Encerramento automático do MDF-e**: MDF-es sem chegada aos 29 dias de emissão recebem encerramento automático pelo SSW para evitar rejeições no SEFAZ. Verifica todos os CNPJs da opção 401 com mesma raiz dos certificados digitais.

**RPSs e CTRC não fiscal**: Compõem o Manifesto Operacional mas não são submetidos ao SEFAZ.

**Manifestos aéreos**: Usar veículo tipo AVIÃO (opção 026) para não gerar MDF-e.

**Manifestos por ônibus**: Podem ser configurados para não serem enviados ao SEFAZ se veículo for tipo ONIBUS (opção 026). Útil quando usa horário da linha como placa.

**Operação Multimodal**: Manifestos de CT-es Multimodais não são submetidos ao SEFAZ. Operação dos modais ocorre através dos CT-es Vinculados ao Multimodal.

### Cancelamento de Manifesto

**Opção 024**: Cancela Manifesto Operacional e MDF-e.

**Manifesto Operacional cancelado**: Mantém CTRCs apontados na opção 020 para ajustes e posterior emissão de novo Manifesto.

**MDF-e cancelado**: Cancelado no SEFAZ se não decorreram 24h da emissão e não passou por posto fiscal/radar. Se cancelamento não for possível, é apenas **encerrado**. MDF-e encerrado não pode ser apresentado no Posto Fiscal (risco de multa).

**Cancelamento impedido**: Não permitido se veículo já recebeu saída (opção 025).

### Saída de Veículos

**Chegada automática**: Com a saída do veículo (opção 025), todos os MDF-es com destino a esta unidade recebem chegada automaticamente com encerramento no SEFAZ.

**Saída agendada**: Manifesto pode ter saída agendada. Procedimentos burocráticos (emissão MDF-e, SMP) são resolvidos no ato, restando apenas a saída do veículo no futuro.

**Saída automatizada**: Transportadoras com SSWMobile ou dados de satélite podem automatizar saída. Necessário ajustar coordenadas geográficas e raio da unidade (link **Apontar** na opção 401) e ativar função em opção 903/Operação. Identificação de 3 pontos de localização fora do raio na última 1 hora executa saída automaticamente.

**Manifestos sem saída**: Na opção 025, todos os Manifestos do veículo são mostrados. Marcar os que **não receberão saída** para evitar inclusão indevida no MDF-e. MDF-e associado ao manifesto marcado é encerrado automaticamente.

**Manifestos FEC**: Relacionados apenas os que possuem previsão de chegada nas últimas 24h.

### Gerenciamento de Risco

**SMP (Solicitação de Monitoração Preventiva)**: Protocolo ou retorno da gerenciadora integrada on-line (opção 903/Gerenciamento de Risco). Instruções em vermelho retornadas pela gerenciadora devem ser obedecidas. **Veículo não pode sair sem que instrução esteja atendida**. SMP não autorizado pode impedir impressão da DAMDFE (configurável em opção 903).

**Sucessos e insucessos**: Registrados na opção 117 (verificar diariamente).

**Vale Pedágio**: Informação inserida no XML do MDF-e. Obtido do CTRB/OS (opção 072). Falta pode gerar multa inclusive por radares da ANTT.

**Averbação**: Arquivo de CT-es do MDF-e podem ser reenviados conforme exigências da seguradora. Todos os CT-es são averbados obrigatoriamente na autorização pelo SEFAZ (opção 007).

### Vínculo com CTRB/OS

**Opção 072**: Manifestos são vinculados ao CTRB/OS vigente, permitindo obter avaliação de rentabilidade da viagem (opção 056, relatório 020). Emissão CTRB pode ser obrigatória (opção 903/Operação).

**Encerramento do CTRB**: CTRB com destino a esta unidade que está dando saída recebe encerramento automático. Não ocorre quando origem e destino do CTRB são iguais (coleta em andamento).

### Posto Fiscal

**Cuidado com MDF-es encerrados**: Motorista não deve apresentar MDF-es encerrados para fiscalização. MDF-es vigentes são os apresentados nos links da opção 025. Cada UF destino de CNPJ emissor deve ter seu MDF-e vigente.

### Rejeições do SEFAZ

**MDF-e duplicado**: Geração rejeitada se houver MDF-e emitido em data anterior com mesma origem, destino e placa, sem que chegada no destino tenha sido informada (opção 030).

**RNTRC inválido**: RNTRC do proprietário do veículo é verificado pelo SEFAZ. Deve estar correto na opção 027.

### Operação Sem Papel

**Processo completo**: Veja AQUI (link no SSW original) o processo completo para não usar papel na operação.

**Conferência de documentos (opção 034)**: Captura DACTEs/DANFEs anexados ao Manifesto na saída ou chegada. Informação dos capturados é gravada no formato 888/999 (888 capturados, 999 total).

### Rastreamento

**Informação no site**: Saída disponibilizada para site de rastreamento. E-mails disparados conforme opção 383/rastreamento.

**Atualização de previsões**: Todas as saídas dadas em unidades intermediárias atualizam as previsões de todos os Manifestos carregados no veículo.

**Localização on-line**: Via SSWmobile ou satélite da gerenciadora de risco (link **Mapa** na opção 025).

### Geração Automática de Subcontratos

Com a saída pode-se gerar automaticamente todos os subcontratos no SSW da subcontratada, permitindo planejamento antecipado. Configuração pela opção 670.

### Divulgação de Placa Provisória (opção 210)

**Compartilhar transferência**: Reduzir custos e cumprir prazos compartilhando transferência com outras transportadoras. Carga anunciada no SSW, BR116.net e SSWMobile.

**Fluxo**:
1. Montagem da Placa Provisória (opção 020)
2. Divulgação e Reserva (opção 210)
3. Emissão do Manifesto (opção 020) — Placa mostra situação "Divulgado" e "Reservado"
4. Contratação do veículo (opção 072) ou CT-e Redespacho Intermediário (opção 006)

### Operação com Sorter (opção 220)

**SORTER gera Placas Provisórias**: Volumes identificados com etiqueta de código de barras são colocados na esteira. Sorter informa via WebAPI qual rampa (unidade/setor) o volume foi derrubado, juntamente com pesagem e cubagem. SSW inclui volume em Placa Provisória aberta.

**Conclusão da Placa**: Comandada manualmente (opção 220) ou botão com WebAPI. Placas concluídas ficam disponíveis na opção 020 para serem manifestadas e opcionalmente transformadas em gaiola/palete.

**Formato da Placa**: XXX9999, onde XXX é sigla da unidade destino final ou setor de entrega (rampa do sorter). Com conclusão, nova é iniciada avançando numeração 9999.

**Gaiolas e Paletes**: Placa Provisória pode ser transformada com emissão de etiqueta (opção 220). Unitiza CTRCs, reconhecido como um volume em unidades de transbordo. Gaiolas devem ser cadastradas previamente (opção 021).

**Pré-CTRCs**: Saída de veículo pode ser permitida com pré-CTRCs ainda sem autorização no SEFAZ. Configuração em opção 903/Autorização e operação com Pré-CTRC.

### Operação Fluvial

**Unidade PORTUÁRIA**: Manifesto Fluvial só pode ser emitido por unidade tipo PORTUÁRIA (opção 401).

**2 tipos de Manifestos**:
- **Para CTRCs de carretas/manifestos de terceiros**: Carregados em carreta fictícia CARTERC (cadastrada na opção 026)
- **Para CTRCs de clientes próprios**: Pelo menos um manifesto para cada carreta própria

**Dados obrigatórios**: BALSA, EMPURRADOR (opção 026), CPF DO PILOTO (opção 028), PORTO DESTINO (opção 401).

### Impressões Disponíveis (opção 025)

**Manifesto Operacional**: Link imprime o Manifesto.

**MDF-e**: Link imprime o MDF-e.

**DAMDFE Sintético**: Relaciona Manifestos sem listar CT-es.

**DAMDFE**: Relaciona todos os Manifestos com respectivos CT-es sem e com valor de frete.

**DACTEs do Manifesto**: Imprime todos os DACTEs do Manifesto.

**DANFEs do Manifesto**: Imprime todas as DANFEs do Manifesto.

**DACTEs Origem do Manifesto**: DACTEs origem do Manifesto.

**Manifesto CB CT-e**: Manifesto relacionando chaves em código de barras dos CT-es. Útil para parceiros sem SSW e geração de AWB pela cia aérea.

**Manifesto CB NF-e**: Manifesto relacionando chaves em código de barras das NF-es.

### Reimpressão e Retransmissão (opção 201)

**Filas de MDF-e**:
- **DIGITADOS**: Gerados mas não enviados à Receita. Usar link **Enviar à receita**.
- **ENVIADOS À RECEITA**: Enviados mas não autorizados.
- **AUTORIZADOS (SEM IMPRESSÃO)**: Receberam protocolo da Receita, devem ser impressos.
- **DENEGADOS**: Irregularidade fiscal. Recebem protocolo, não podem ser reenviados. Após resolver irregularidades, cancelar Manifesto e MDF-e e gerar outro.
- **REJEITADOS**: Erro, rejeitados pela Receita. Após correção, retransmitir.
- **EM ALTERAÇÃO**: Informativo. Após conclusão passam para DIGITADOS.

**Impressão**: Informar período de emissão (opcional), escolher "digitados por mim" ou "por todos".

**Reimpressão**: Informar primeira e última faixa de MDF-e (sem séries), escolher "M-meus" ou "T-todos".

### Operação Aérea (opção 069)

**Vincular AWB**: Associa CT-e aéreo (AWB) ao Manifesto Operacional.

**Fluxo**:
1. Opção 020: Emitir Manifesto Operacional (carga entre aeroportos)
2. Opção 025: Sem dar saída, imprimir **Manifesto CB CT-e** para check-in da carga pela cia aérea
3. Opção 069: Associar AWB ao Manifesto Operacional
4. Opção 030: Unidade destinatária identifica AWB nas transferências chegando e retira carga no aeroporto

**Dados**: Código de barras do Manifesto, Cia aérea, AWB, Número Operacional, Frete AWB, E-mail unid destino (opcional).

**Relatório Analítico**: Relaciona Manifestos do período mostrando fretes dos CTRCs e AWBs.

### Arquivo Fronteira Rápida RN (opção 179)

Gera arquivo para simplificação de passagem nos postos fiscais do Rio Grande do Norte.

**Fluxo**:
1. Emitir MDF-e com CT-es/NF-es destinados ao RN (opção 020 e 025)
2. Gerar Arquivo Fronteira Rápida RN do MDF-e (opção 179)
3. Transmitir à UVT (Unidade Virtual de Tributação) do SEFAZ-RN

**Dados**: Série e número do MDF-e (não do Manifesto Operacional) ou código de barras do MDF-e (44 dígitos).

### Romaneio de Carregamento (opção 725)

Relação de mercadorias do estoque a serem carregadas.

**Dados**: Placa Provisória em carregamento (opção 020), seus CTRCs apontados e respectivas NFs definem itens a serem mostrados. Somente itens cadastrados na opção 741.

**Classificação**: Código de mercadoria, Descrição da mercadoria ou Embalagem.

**Alternativas**: Informar 12 Manifestos ou 12 Romaneios de Entrega.

### Conferência de Manifestos (opção 034)

Confere se todos os documentos do cliente foram anexados ao Manifesto: boletos de cobrança, manuais, etc. Documentos associados à chave da DANFE.

**Saída**: Confere CTRCs digitando sigla+número+DV ou capturando código de barras dos DACTEs/DANFEs. Manifesto deve estar emitido (opção 020) sem saída.

**Chegada**: Idem, mas Manifesto deve ter recebido chegada (opção 030).

**Conclusão**: Concluir conferência informando situação. Informação dos capturados é gravada nos CTRCs e no Manifesto (opção 023) no formato 888/999 (888 capturados, 999 total). Gera planilha com relação de CTRCs/NFs do Manifesto indicando captura ou não.

**Conferência iniciada mas não concluída**: Fica disponível para ser continuada posteriormente.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
