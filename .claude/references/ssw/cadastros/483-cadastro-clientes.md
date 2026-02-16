# Opcao 483 — Cadastro de Clientes

> **Modulo**: Cadastros
> **Paginas de ajuda**: 34 paginas consolidadas (referencias cruzadas)
> **Atualizado em**: 2026-02-14

## Funcao

Gerencia o cadastro completo de clientes da transportadora, incluindo dados basicos, fiscais, operacionais, comerciais, cobranca, rastreamento e servicos adicionais. Serve como base para emissao de CT-e, calculo de frete, faturamento e relacionamento comercial.

## Quando Usar

- Cadastrar novo cliente (remetente, destinatario, pagador, expedidor, recebedor)
- Atualizar dados cadastrais, fiscais ou operacionais
- Configurar parametros de cobranca, faturamento e rastreamento
- Definir servicos adicionais exigidos pelo cliente (TDE, agendamento, paletizacao, etc.)
- Vincular vendedor e unidade responsavel
- Configurar envio de XML/DACTE por e-mail
- Consultar situacao cadastral no SEFAZ
- Importar/exportar cadastros em lote via CSV

## Pre-requisitos

- Cidade do cliente deve estar cadastrada (pode ser criada automaticamente pelo SSW)
- Vendedor deve estar cadastrado (opcao 415) se for vincular
- Unidade responsavel deve existir (opcao 401)
- Para cobranca bancaria: banco cadastrado (opcao 401, 384)

## Campos / Interface

### Dados Basicos

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ/CPF | Sim | 14 digitos (PJ) ou 11 digitos (PF). Produtor rural e estrangeiro tem regras especiais |
| Tipo | Automatico | CNPJ ou CPF (pode ser corrigido clicando no link) |
| IE | Condicional | Inscricao Estadual. Informar ISENTO para isentos. Consultavel no SINTEGRA |
| SitCad | Nao | Situacao cadastral: A-ativo, B-baixado, I-isento, N-inativa, S-suspensa |
| IM | Nao | Inscricao Municipal |
| CFOP | Sim | I-industria, C-comercio, R-produtor rural, T-transportadora, P-governo municipal/estadual, U-governo federal, O-telecomunicacoes, E-energia eletrica, N-nao contribuinte |
| SN | Nao | Optante pelo Simples Nacional (consultavel em portal) |
| Nome | Sim | Razao social (3+ caracteres para busca) |
| Endereco | Sim | Logradouro, numero, complemento, bairro (obrigatorio), CEP |
| Cidade/UF | Sim | Busca por parte do nome via link |
| Latitude/Longitude | Automatico | Incluido automaticamente. Botao Apontar permite definir manualmente |
| Telefone | Nao | Telefone fixo |
| Celular | Nao | Imprescindivel para disparo de SMS |
| 0800 | Nao | Telefone gratuito |
| E-mail | Nao | Multiplos separados por ponto-e-virgula. SSW valida dominio |
| Site | Nao | Site do cliente na internet |
| Codigo OTM | Nao | Codigo ANTT para Operador de Transporte Multimodal |

### Parametros Operacionais

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Transportar | Automatico | Mostra se liberado para transporte (configurado na opcao 389) |
| Vendedor | Nao | Vendedor vinculado (opcao 415) |
| Atendente resp | Nao | Login do usuario responsavel pelo atendimento |
| Classificacao | Sim | E-especial (exige negociacao previa), C-comum (apenas comunicado) |
| Unidade responsavel | Sim | Unidade comercialmente responsavel. M-manual, A-automatica (conforme opcao 402) |
| Praça da tabela | Sim | O-Praca Operacional, C-Praca Comercial (reduz quantidade de tabelas) |
| ICMS/ISS na tabela | Sim | N-adiciona ao frete, S-ja incluso |
| PIS/COFINS na tabela | Sim | N-adiciona ao frete (junto com ICMS/ISS), S-ja incluso |
| Pode agrupar NF | Sim | N-nao permite agrupar NFs no CTRC |
| Devolve canhoto de NF | Nao | S-exige devolucao (impresso no DACTE) |
| Verifica CIF/FOB | Sim | N-nao verifica restricao da cidade (opcao 402) |
| Exige Pedido no CTRC | Nao | S-solicita pedido na digitacao (opcao 004) |

### Cobranca e Faturamento

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cobranca | Sim | A VISTA, CARTEIRA (sem cobranca bancaria), BANCO (com cobranca bancaria) |
| Paga TDA | Sim | N-nao paga TDA da cidade (opcao 402), S-paga se Acesso dificil = S |
| Paga TDE | Sim | N-nao paga TDE do destinatario (opcao 487) |
| Seguro RCFDC | Nao | S-cliente segura a carga (transportadora nao averba) |
| Seguro RCTRC | Nao | Normalmente N (apolice da transportadora) |
| Segmento | Nao | Codigo de atividade definido pela transportadora |
| CNAE 2.0 | Nao | Classificacao IBGE (nivel Grupo - 3 primeiros numeros) |

### Servicos Adicionais (Remetente/Destinatario)

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Coleta dificil | Nao | S-cobra TDC do pagador |
| Acesso dificil | Nao | S-cobra TDA do pagador (remetente ou destinatario) |
| Entrega dificil | Nao | S-cobra TDE (pode marcar raiz CNPJ na opcao 394) |
| Grau de Dificuldade | Nao | 1 a 9 (quando Entrega Dificil = S). TDE conforme grau (opcao 487) |
| Exige agendamento | Nao | S-cobra agendamento (independente de realizar). Etiqueta sai como AGENDADO |
| Exige paletizacao | Nao | S-cobra paletizacao (pode cobrar avulso via opcao 089) |
| Exige separacao | Nao | S-cobra separacao |
| Exige capatazia | Nao | S-cobra capatazia (portos/aeroportos) |
| Exige veiculo dedicado | Nao | S-cobra veiculo dedicado |
| Recebe NFs agrupadas | Nao | S-destinatario/recebedor aceita CTRCs com NFs agrupadas |
| E-mails serv complem | Nao | Contatos para servicos adicionais |
| Fone serv complem | Nao | DDD e numero para servicos adicionais |

### Envio de XML/DACTE

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Frequencia | Nao | L-lote as 06h (ate 10 arquivos compactados), O-online apos autorizacao |
| E-mail com corpo | Sim | S-com texto padrao, N-sem corpo (apenas anexo) |
| Compactado | Sim | S-compacta arquivos em ZIP, N-nao compacta |
| E-mails | Nao | Multiplos separados por ponto-e-virgula. Link Buscar consulta outros dominios |
| CT-e 3.0 | Nao | S-envia versao 3.0 (padrao e 4.0). Para clientes que nao ajustaram sistemas |

### Outros

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Ultima ocorrencia | Automatico | Mostra ultima ocorrencia registrada |
| Cadastro SEFAZ | Consulta | Dados oficiais do SEFAZ em XML (nao disponivel para AL, AM, AP, DF, MA, MT, PA, PI, RJ, RO, RR, SE, TO) |

## Fluxo de Uso

### Cadastro de Novo Cliente

1. Acessar opcao 483
2. Informar CNPJ/CPF ou parte do nome (minimo 3 caracteres)
3. Se nao existir: SSW busca em outros dominios para auxiliar preenchimento
4. Preencher dados basicos: nome, IE, endereco, contato
5. Configurar parametros operacionais: vendedor, unidade responsavel, classificacao
6. Definir cobranca e faturamento (link Faturamento abre opcao 384)
7. Configurar servicos adicionais se aplicavel
8. Salvar (botao Atualizar)

### Importacao em Lote (CSV)

1. Clicar em "Baixar" para obter template CSV
2. Preencher planilha:
   - Clientes novos: campos obrigatorios + demais assumem padroes
   - Clientes existentes: apenas campos informados serao atualizados
   - Separador: ponto-e-virgula (nao usar dentro dos campos)
3. Importar via "Importar arq CSV"

### Consulta no SEFAZ

1. No cadastro do cliente, clicar em "Cadastro SEFAZ"
2. SSW busca dados oficiais em XML (se UF disponivel)
3. Verificar campos importantes:
   - `<cSit>`: 0-nao habilitado, 1-habilitado
   - `<indCredNFe>`: credenciamento NF-e (0-4)
   - `<indCredCTe>`: credenciamento CT-e (0-4)
   - `<xRegApur>`: regime de apuracao (SIMPLES NACIONAL aparece aqui)
4. Dados NAO atualizam automaticamente o cadastro

### Atualizacao Automatica

SSW atualiza cadastro automaticamente em 2 processos:

1. **Portal Nacional de XMLs** (opcao 595):
   - XMLs de NF-e/CT-e atualizam fornecedor (opcao 478) e cliente
   - Atualiza se IE, SN ou CEP do emissor forem diferentes
   - Campos atualizados: endereco, IE, SN

2. **Geracao de CTRCs**:
   - **Opcao 004/005** (com NF-e):
     - Remetente: IE, CEP, SN diferentes atualizam cadastro
     - Destinatario: IE, CEP, SN diferentes atualizam, exceto clientes A e B (ABC). Se CEP diferente, usa local de entrega sem atualizar opcao 388
     - SN atualizado via consulta SEFAZ (tag xRegApur) quando disponivel (ex: MG)
     - CEP invalido: substitui por primeiro CEP valido seguinte (opcao 944) com mesmo codigo IBGE
   - **Opcao 006/379** (sem NF-e):
     - Remetente: IE, CEP, SN diferentes atualizam, exceto clientes A e B
     - Destinatario: IE, CEP+num rua diferentes atualizam, exceto clientes A e B. SN nao e atualizado

### Configuracoes Complementares (Links Rodape)

- **Operacao** (opcao 381): regras de envio pre-CTRC ao SEFAZ
- **Rastreamento** (opcao 383): rastreamento e disparo de e-mails
- **Credito** (opcao 389): bloquear transporte e limites de credito
- **Faturamento** (opcao 384): regras de faturamento e cobranca
- **Ocorrencias** (opcao 385): historico de ocorrencias
- **Mercadorias** (opcao 386): vincular tipos de mercadorias
- **Especies** (opcao 382): vincular especies de mercadorias (gerenciamento de risco - opcao 390)
- **Relacionamento** (opcao 387): cadastrar contatos
- **Outros** (opcao 388): outras configuracoes

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004, 005, 006 | Emissao de CTRC usa dados do cliente |
| 007, 009 | Envio de XML/DACTE por e-mail |
| 100 | Envio de e-mail ao cliente |
| 102 | Situacao do cliente (operacional, financeiro, resultado) |
| 134 | Cliente com restricao de cidade pode receber entregas |
| 146 | Busca clientes em outros dominios |
| 381 | Regras de envio pre-CTRC ao SEFAZ |
| 382 | Especies de mercadorias (gerenciamento de risco) |
| 383 | Rastreamento e disparo de e-mails |
| 384 | Faturamento e cobranca |
| 385 | Ocorrencias do cliente |
| 386 | Tipos de mercadorias vinculados |
| 387 | Relacionamento (contatos) |
| 388 | Outras configuracoes |
| 389 | Credito (bloquear transporte, limites) |
| 390 | Gerenciamento de risco |
| 394 | Raiz CNPJ com entrega dificil |
| 402 | Cidades atendidas (TDA, restricoes CIF/FOB) |
| 404 | Faixa de CEP (TDA prioritario) |
| 405 | Ocorrencias de entrega (reentrega automatica) |
| 406 | Tipos de mercadorias (calculo frete) |
| 415 | Vendedores |
| 417, 418 | Tabelas de fretes |
| 423 | Cubagem e cobrancas complementares |
| 434 | Liberar acesso de outros dominios |
| 461 | Relacionamento por segmento/CNAE |
| 467 | Relacao de clientes Especiais |
| 478 | Fornecedores (atualizacao automatica via XML) |
| 483 | Cadastro de clientes (esta opcao) |
| 487 | TDE destinatario |
| 497 | Analise de perfil e potencial de carga |
| 503 | Eventos (gerenciamento de risco) |
| 513 | Tabela de devolucao/recoleta/reentrega (prioridade sobre 423) |
| 525 | Recadastramento massificado CNAE 2.0 |
| 583 | Grupos de clientes |
| 595 | Portal Nacional de XMLs (atualizacao automatica) |
| 925 | Usuarios (tipo CLIENTE tem acesso restrito) |
| 944 | Correios (validacao CEP) |

## Observacoes e Gotchas

### CNPJ/CPF Especiais

- **Produtor rural**: regras especificas (consultar documentacao SSW)
- **Cliente estrangeiro**: regras especificas (consultar documentacao SSW)
- **Pessoa Fisica**: 11 digitos, validacao automatica de CPF

### CFOP e Tributacao

- **CFOP automatico**: SSW assume I se encontrar palavra "industria" no nome, senao C
- **P e U**: solicita Numero do Empenho na emissao (opcao 004)
- **N (nao contribuinte)**: identifica cliente nao contribuinte mesmo com IE informada
- **Alteracao**: apenas usuario configurado como ALTERA cadastro (opcao 925) pode alterar CFOP (afeta tributacao ICMS)
- **Tabela CFOP**: coluna indTransp = 1 indica codigos usados no transporte

### Situacao Cadastral (SitCad)

- **Atualizacao automatica**: situacoes A e B atualizadas via consulta SEFAZ, exceto UFs: RJ, DF, RO, AM, RR, PA, AP, TO, MA, PI, AL, SE
- **Alerta na emissao**: opcoes 004 e 005 alertam quando destinatario PJ tem situacao B, N ou S (evita apreensao na UF destino)
- **Consulta manual**: SINTEGRA ou link Cadastro SEFAZ

### Simples Nacional (SN)

- **Consulta online**: em MG, SSW verifica SEFAZ a cada emissao de CTRC (opcao 004) e atualiza SN (optante nao tem isencao ICMS)
- **Cadastro SEFAZ**: tag `<xRegApur>` identifica SIMPLES NACIONAL
- **Atualizacao automatica**: via XMLs (opcao 595) e geracao de CTRCs (opcoes 004/005)

### E-mail e Comunicacao

- **Validacao**: SSW verifica validade do e-mail consultando o site associado
- **Multiplos e-mails**: separar com ponto-e-virgula
- **Busca em outros dominios**: link Buscar consulta e-mails atualizados em outras transportadoras
- **Atualizacao cascata**: e-mails informados atualizam e-mail de cobranca (opcao 384) se nao existir nenhum

### ICMS/ISS e PIS/COFINS Repassados

- **ICMS/ISS na tabela = N**: valor adicionado na parcela IMPOSTO REPASSADO
- **PIS/COFINS**: so e repassado junto com ICMS/ISS (ICMS reduz base de calculo PIS/COFINS)
- **Frete informado**: se "Frete Informado e frete final = N" (opcao 903/Frete), ICMS/ISS na tabela do cliente e verificado
- **Tabela Generica**: transportadoras a partir de numero 1032 (ano 2012) nao tem ICMS/ISS repassado (opcao 923)
- **Aliquotas PIS/COFINS**: definidas na opcao 401 (varia por regime cumulativo/nao cumulativo)
- **Base de calculo**: a partir de 03/01/2022, PIS/COFINS e reduzido do ICMS (antes nao era)
- **Algoritmo**: consultar documentacao SSW para calcular base quando repassa ICMS e PIS/COFINS

### Servicos Adicionais

- **Cobranca automatica**: independe de realizar o servico (agendamento, paletizacao, etc.)
- **Cobranca avulsa**: via CTRC Complementar (opcoes 015, 089, 222)
- **Valor por ocorrencia**: cadastrar na opcao 423
- **Etiquetas**: volumes de CTRCs com "Exige agendamento = S" saem identificados como AGENDADO
- **TDE por grau**: opcao 487 permite cobrar TDE conforme grau de dificuldade (1-9)
- **Raiz CNPJ**: opcao 394 permite marcar raiz como entrega dificil (alternativa a marcar CNPJ individualmente)

### Latitude/Longitude

- **Inclusao automatica**: atualizado quando cadastro e atualizado ou operacao com cliente e realizada
- **Manual**: botao Apontar permite definir localizacao manualmente

### Classificacao ABC

- **Mostra no nome**: entre parenteses aparece classificacao ABC (faturamento) e 123 (inadimplencia)
- **Protecao contra atualizacao**: clientes A e B nao tem CEP atualizado automaticamente na geracao de CTRCs (usa local de entrega sem atualizar opcao 388)

### Busca em Outros Dominios

- **CNPJ nao cadastrado**: SSW busca em outros dominios para auxiliar preenchimento (decisao de usar e do usuario)
- **E-mails e celulares**: link Buscar consulta outros dominios, apenas para clientes que tiveram CTRCs emitidos
- **Requisitos**: dominio deve estar cadastrado na opcao 146 e ter liberado acesso na opcao 434

### Unidade Responsavel

- **M-manual**: so alterada manualmente
- **A-automatica**: alterada conforme alteracoes na cidade (opcao 402)
- **Cascata**: unidade cobranca (opcao 384) tambem e atualizada automaticamente caso esteja em branco

### CEP Invalido

- **Substituicao**: cadastro atualizado com primeiro CEP valido seguinte (conforme Correios - opcao 944) com mesmo codigo IBGE
- **Link CEP**: no campo Endereco, link permite informar CEP e obter nome do logradouro

### Devolve Canhoto de NF

- **Impressao**: observacao impressa no DACTE quando remetente for pagador do frete
- **Sugestao**: sugerida no campo Instrucoes entrega (opcoes 004, 005, 006)
- **Visibilidade**: mostrada no Romaneio de Entregas e SSWMobile

### Codigo OTM

- **ANTT**: disponibilizado pela ANTT para PJ realizar Transporte Multimodal de Cargas (origem ate destino, meios proprios ou terceiros)

### Usuarios Restritos

- **Tipo CLIENTE** (opcao 925): nao tem acesso a links de manutencao, ocorrencia, tabelas, analise, etc.
- **Agencia/Parceiro**: se unidade nao e responsavel (opcao 483), nao tem acesso aos links
- **Consulta externa** (opcao 146): nao tem acesso aos links

### CT-e 3.0 vs 4.0

- **Padrao**: versao 4.0
- **CT-e 3.0 = S**: cliente pagador recebe CT-es em versao 3.0 (para sistemas que nao ajustaram para 4.0)

### Importacao CSV

- **Separador**: ponto-e-virgula (nao usar dentro dos campos, usar virgula se necessario)
- **Novos vs Existentes**: novos exigem campos obrigatorios, existentes atualizam apenas campos informados
- **Template**: link Baixar fornece formato correto

### Cadastro SEFAZ (XML)

- **UFs nao disponiveis**: AL, AM, AP, DF, MA, MT, PA, PI, RJ, RO, RR, SE, TO
- **Nao atualiza automaticamente**: dados sao consultivos, usuario decide se atualiza cadastro
- **Campos criticos**: cSit, indCredNFe, indCredCTe, xRegApur

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A01](../pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente |
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
| [POP-C02](../pops/POP-C02-emitir-cte-carga-direta.md) | Emitir cte carga direta |
| [POP-E01](../pops/POP-E01-pre-faturamento.md) | Pre faturamento |
| [POP-E02](../pops/POP-E02-faturar-manualmente.md) | Faturar manualmente |
| [POP-E04](../pops/POP-E04-cobranca-bancaria.md) | Cobranca bancaria |
