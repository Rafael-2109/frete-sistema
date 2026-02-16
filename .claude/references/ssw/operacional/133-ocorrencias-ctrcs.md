# Opção 133 — Informar Ocorrências em CTRCs

> **Módulo**: Operacional
> **Referência interna**: Opção 033
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Registra ocorrências em CTRCs utilizando diversas formas de localização (código de barras, número do CTRC, manifesto, nota fiscal, etiquetas). Sistema permite anexar imagens, incluir instruções e controlar segregação de cargas.

## Quando Usar

- Registrar eventos no ciclo de vida do CTRC (entregas, tentativas, avarias, devoluções)
- Atribuir ocorrências em massa por manifesto operacional
- Cadastrar/baixar sobras de volumes não identificados
- Incluir comprovantes fotográficos de ocorrências
- Enviar instruções para resolução de problemas operacionais
- Responder solicitações do "Fale Conosco" do site de rastreamento

## Campos / Interface

### Tela Inicial - Localização de CTRCs

**Formas de busca:**
- **DACTE (código de barras)**: Código de barras da DACTE
- **CTRC (com DV)**: Sigla e número do CTRC com dígito verificador
- **Manifesto Operacional**: Ocorrência aplicada a todos CTRCs do manifesto (aceita arquivo CSV com NF na primeira coluna)
- **CNPJ do remetente/Nota Fiscal**
- **NR, NR1 ou NR2**: Número da etiqueta de identificação do volume (NR) ou etiquetas sequenciais da NF (NR1/NR2)

**Links especiais:**
- **Minhas Ocorrências**: Acompanhamento das ocorrências registradas pelo usuário (opção 133)
- **Cadastrar sobras**: Registra volumes não identificados (mais eficiente com SSWBar)
- **Baixar sobras**: Baixa sobra quando CTRC correspondente é identificado (consulta via opção 108)

### Tela Principal - Incluir Ocorrências

**Código**: Código de ocorrência cadastrado pela opção 405

**Data/hora**: Data e hora da ocorrência

**Informações complementares**: Complemento da ocorrência (até 70 caracteres)

**Detalhar**: Texto sem limite de tamanho para complementar a ocorrência

**Segregar CTRC**:
- Com **S**, CTRC fica indisponível para continuidade da operação (opção 020, 035, SSWBar) até ser retirado da segregação pela opção 091

**Imagem da ocorrência**:
- Obtidas pelo SSWMobile ou pelos links:
  - **Fotografar**: Através de câmera do computador
  - **Buscar no meu micro**: Múltiplas imagens podem ser importadas (Ctrl+cursor)

### Incluir Instruções

**Instrução**: Texto livre para resolver a ocorrência. Incluída pela unidade expedidora (emissora do CTRC) ou unidade anterior (emissora do último Manifesto), conforme tabela de ocorrências (opção 405). **Instruções não são enviadas ao cliente.**

**Respostas a um Fale Conosco**: Com **S**, a instrução é disponibilizada no Site de Rastreamento, respondendo mensagem postada pelo cliente em "Fale Conosco"

**Mobile**: Link seleciona apenas ocorrências atribuídas por SSWMobile pelo motorista. Instruções para motoristas podem ser enviadas pela opção 218.

**Localização atual**: Traz localização do veículo fornecida pelo SSWMobile ou satélite da gerenciadora de risco

### Ocorrências/Instruções do CTRC

**Inclusão**: Data/hora de inclusão no horário de Brasília (momento de registro no sistema)

**Inclusão Local**: Data/hora de inclusão no horário local da cidade da unidade (respeita fuso-horário)

## Integração com Outras Opções

- **Opção 405**: Cadastro de códigos de ocorrências
- **Opção 038**: Atribuição de ocorrências de entrega (somente na unidade destino)
- **Opção 016**: Devolução de mercadoria (resgate)
- **Opção 091**: Retirada de CTRCs da segregação
- **Opção 020/035**: Operações bloqueadas para CTRCs segregados
- **Opção 108**: Consulta de sobras
- **Opção 138**: Estorno de ocorrências
- **Opção 233**: Atribuição de ocorrências em lotes (requer liberação opção 918)
- **Opção 218**: Envio de instruções para motoristas
- **Opção 089**: Paletização de CTRCs
- **Opção 007**: Recálculo de frete
- **Opção 084/184/185**: Pesagem e cubagem
- **Opção 398**: SSWScan para comprovantes
- **Opção 030**: Chegada de veículo
- **Opção 004**: Unitização (Marketplace)

## Observações e Gotchas

### Características de Códigos SSW Importantes

**01 - Mercadoria entregue**
- Código universal em todas as transportadoras usuárias do SSW
- Não sofre validação de data/hora (sempre atribuído)
- Última imagem de entrega torna-se o Comprovante de Entrega

**31, 32, 33 - Tentativas de entrega**
- Aceitas somente na sequência: primeira, segunda e terceira

**88 - Resgate de mercadoria**
- CTRC fica impedido de ser carregado em Romaneio de Entregas
- Bloqueado para receber ocorrências de ENTREGA
- Permite apenas devolução (opção 016)
- Pode receber ocorrências SSW 26 (Aguardando autorização) e 27 (Devolução autorizada)

**61 - Mercadoria confiscada**
- Em CTRC Unitizado, desfaz a unitização e libera todos os CTRCs
- Operação passa a ser executada individualmente

**71 - Troca de gelo**
- Exige preenchimento de dados do controle de gelo de vacinas

**70 - Pesagem/Cubagem efetuada**
- Peso (Kg) e/ou volume (m3) foram alterados
- Usados no recálculo do frete (opção 007)
- Pode ser realizada por: SSWBalança, cubadora, opção 084, 184, 185

**89 - Paletização efetuada**
- CTRCs paletizados (opção 089) recebem esta ocorrência
- Útil para processo de identificação de cobrança não realizada (opção 056 - Relatório 130)

**19 - Anexado comprovante complementar**
- Nova imagem para melhorar comprovação da entrega
- Entrega continua sendo atribuída ao código 01
- Exemplos: SSWScan, segunda baixa pelo SSWMobile

**80 - Documento de transporte emitido**
- Não é gravado no CTRC da subcontratante quando atribuída pela subcontratada (ambos usuários SSW)
- Evita confusão para cliente que rastreia mercadoria

**03 - Mercadoria devolvida / 38 - Recusa de recebimento**
- Grava automaticamente evento de insucesso de entrega no SEFAZ (CT-e)
- Conforme Ajuste SINIEF nº 9, de 25/10/2007, inciso XXIII do § 1º da cláusula décima oitava-A

**83 - Chegada em unidade de transbordo**
- Registrada automaticamente na chegada do veículo (opção 030) em unidade diferente da destino do CTRC

**84 - Chegada em unidade de entrega**
- Registrada automaticamente na chegada do veículo (opção 030) na unidade destino do CTRC

**95 - Estou chegando**
- Registrada via SSWMobile informando que CTRC é o próximo a ser entregue
- Sistema calcula horário provável usando Google

### Restrições de Ocorrências

- **Ocorrências de entrega**: Só podem ser atribuídas pela opção 038 da unidade destino
- **CTRCs segregados**: Ficam bloqueados para operações até retirada da segregação (opção 091)

### Imagens de Comprovantes

**Formatos aceitos**: JPEG, WEBP, PNG, TIFF, TIF, JP2, J2K, HEIC, HEIF, HEVC, PDF
- Todos convertidos para JPEG e reduzidos para no máximo 200KB

**Exclusão de imagem**:
- Somente pelo usuário que a inseriu
- Apenas se a ocorrência é a última do CTRC
- Usuário master pode quebrar esta regra

**Imagem complementar**:
- Imagem de entrega em CTRC que já possui ocorrência de entrega é gravada com código 19

### Ocorrências em CTRCs Unitizados

Todos os CTRCs unitizados pelo NR Unitizador recebem a mesma ocorrência atribuída a um dos seus CTRCs. Ver mais na Ajuda da opção 004/Marketplace.

### Ocorrências Gravadas como Instruções

SSWMobile e SSWScan registram ocorrências com datas/horas do local. Estas são gravadas como instruções (sem código) se:
- Datas diferentes da data do servidor SSW, OU
- Datas iguais mas diferença de horários > 2 horas

**Exceção**: Ocorrência de entrega 01 sempre recebe o código (sem validação de data/hora)

Ocorrência atribuída com data/hora anterior à última que informa cliente também é gravada como instrução (sem código).

### Estorno de Ocorrências

Última ocorrência do CTRC do tipo BAIXA/ENTREGA ou de resgate (código SSW 88) pode ser estornada pela opção 138.

### Ocorrências em Lotes

Podem ser atribuídas pela opção 233 (filtros na tela e arquivo). Como a opção é muito crítica, precisa ser liberada pela opção 918 pelo usuário master.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D06](../pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias |
