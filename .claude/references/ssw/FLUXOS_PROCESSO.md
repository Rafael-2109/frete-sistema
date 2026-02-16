# Fluxos de Processo End-to-End — SSW Sistemas

> **Versao**: 1.0
> **Data**: 2026-02-15
> **Fonte**: 227 docs de opcoes + 12 visoes gerais
> **Cobertura**: 20 fluxos, 120+ opcoes referenciadas

---

## Indice

| Dominio | Fluxos | Opcoes-chave |
|---------|--------|--------------|
| **Operacional** | F01-F05 | 001, 003, 004, 006, 007, 020, 025, 030, 035, 038 |
| **Financeiro** | F06-F09 | 436, 444, 458, 475, 476, 486, 569 |
| **Fiscal** | F10 | 512, 515, 567 |
| **Contabil** | F11 | 534, 558, 559, 566, 570 |
| **Comercial** | F12 | 415, 483 |
| **Parcerias** | F13-F14 | 072, 075, 076, 409, 486 |
| **Frota** | F15-F17 | 026, 131, 313, 316, 320, 475 |
| **Municipal** | F18 | 009, 014 |
| **Logistica** | F19 | 701, 702, 707 |
| **Embarcador** | F20 | 105, 020, 025, 963 |

---

## Mapa Geral de Dependencias

```
F01 Coleta → F02 Expedicao → F03 Transferencia → F04 Chegada → F05 Entrega
                                      ↓                              ↓
                                F13 Contratacao                 F14 Remuneracao
                                      ↓                              ↓
                                      └──────── F08 Contas a Pagar ←─┘
                                                      ↓
F05 Entrega → F06 Faturamento → F07 Liquidacao → F09 Conciliacao
                                                      ↓
                                      F10 Fechamento Fiscal → F11 Fechamento Contabil
```

---

# OPERACIONAL (F01-F05)

## F01 — Coleta de Mercadoria

### Trigger
Cliente solicita coleta via telefone, internet (`ssw.inf.br/2/coleta`), API (`sswCotacaoColeta`) ou EDI (opcao 600 + 006).

### Pre-requisitos
- **Opcao 402**: Cidade de coleta cadastrada com dias de atendimento
- **Opcao 388/402**: Unidade de coleta definida (prioridade: 388 > 402 > usuario > 395)
- **Opcao 519**: Tabela de ocorrencias de coleta (parceiros SSW)
- **Opcao 390 + 903/GR**: Se GR ativa, campo "Especie" obrigatorio

### Passos
1. **Opcao 001 — SAC/Cadastro de Coleta**: Dados remetente (CNPJ/CPF), endereco, data/hora limite. Sistema sugere unidade de coleta. Situacao: "Cadastrada"
2. **Opcao 042 — Agendamento Automatico** (opcional): Programa coletas recorrentes
3. **Opcao 003 — Comandar Coletas**: Selecionar setor (404), informar veiculo (sugerido via 013) e motorista. Situacao: "Comandada"
4. **SSWMobile — Coleta no Cliente**: Motorista recebe coletas online, captura chaves DANFE via opcao 206. Situacao: "Coletada"
5. **Opcao 003 — Baixar Coleta**: Informar ocorrencia "Coletada" + data/hora

### Pontos de Decisao
- Se coleta programada (042): Situacao "Pre-cadastrada"
- Se cliente tem EDI: ssw2287 permite inclusao com numero do Pedido
- Se via parceiro SSW (408): Grava coleta no dominio do parceiro, ocorrencias em ambos dominios
- Se apos hora limite (404): Cadastro so para dia seguinte
- Se mesma raiz CNPJ + mesma placa + mesma data: CTRC emitido muda coleta para "Coletada" automaticamente

### Diagrama
```
001 SAC → 042 Agendamento → 003 Comandar → SSWMobile → 206 DANFE
                                  ↓
                            003 Baixar Coletada
```

### Problemas Comuns
- Coleta sem unidade definida → verificar 388 (cliente) ou 402 (cidade)
- GR bloqueia operacao → Especie obrigatoria (390) se GR ativa (903)
- Veiculo sem liberacao GR → veiculos/motoristas/ajudantes precisam autorizacoes vigentes

### Integracao
- **Alimenta**: F02 (Expedicao) — DANFEs capturadas (206) disponiveis para CT-e
- **Depende de**: Cadastros (401, 402, 404, 388, 390, 519)

---

## F02 — Expedicao / Emissao CT-e

### Trigger
Mercadoria coletada/recebida na unidade, pronta para emissao fiscal.

### Pre-requisitos
- XML da NF-e importado (portal, email, opcao 608, EDI)
- **Opcao 483**: Cliente cadastrado
- **Opcao 417/418**: Tabela de frete ou valores manuais
- **Opcao 903/Certificados**: Certificado digital A1 (.PFX + senha)
- **Opcao 401**: Inscricao Municipal (para RPS municipal)

### Passos
1. **Opcao 004 — CT-e Individual**: CNPJ remetente/destinatario, dados NF-e (numero, chave 44 digitos, peso, volumes, valor), placa coleta. Sistema calcula frete automaticamente
   - CT-e: origem ≠ destino (ICMS)
   - RPS: origem = destino (ISS)
2. **Opcao 006 — CT-e em Lote**: Repositorio NF-es (071), agrupamento (por pedido, destinatario, recebedor, EDI). Rateio de frete entre CTRCs
3. **Opcao 007 — Autorizacao SEFAZ**: Manual (903=M) ou automatico (903=A/S, a cada 1 min). Requisitos configuraveis: pesagem (084), cubagem (084/185), SSWBar (264), conferencia (284). Averbacao automatica as seguradoras
4. **Opcao 009 — RPS/NFS-e**: Prefeituras COM webservice (70+): conversao automatica. SEM webservice (40+): imprimir RPS, gerar lote (014), enviar portal
5. **Opcao 007 — Impressao CT-e**: Formulario matricial ou modo S (sem impressao). FOB pode gerar fatura/boleto

### Pontos de Decisao
- Transporte municipal → RPS (009). Intermunicipal/interestadual → CT-e (007)
- Cliente com EDI → opcao 006 em lote
- Clientes especiais (Natura, AVON, Via Varejo) → emissao EXCLUSIVA via 006
- FOB a vista → faturamento pode ser gerado na expedicao (007)
- CT-e Complementar → opcoes 222, 016, 089, 015, 099, 199

### Diagrama
```
206 DANFE → 004/006 Pre-CTRC → 007 SEFAZ → CT-e Autorizado → 007 Impressao
                ↓                    ↓
           071 Repositorio      Averbacao automatica
004 Pre-RPS → 009 Prefeitura → NFS-e
```

### Problemas Comuns
- Certificado digital vencido → bloqueia totalmente emissao fiscal
- Cubagem/pesagem obrigatoria (903) sem executar 084 → impressao bloqueada
- MDF-e duplicado → rejeicao se houver MDF-e anterior sem chegada (030)
- RNTRC invalido → SEFAZ rejeita (027)

### Integracao
- **Alimenta**: F03 (Transferencia), F05 (Entrega)
- **Depende de**: F01 (DANFEs capturadas)

---

## F03 — Transferencia entre Unidades

### Trigger
CT-e emitido para outra unidade (destino ≠ origem).

### Pre-requisitos
- CT-es impressos e disponiveis no armazem
- **Opcao 026/027/028**: Veiculos, proprietarios, motoristas cadastrados
- **Opcao 390**: PGR configurado (gerenciamento de risco)
- **Opcao 403**: Rotas cadastradas (previsao chegada, UFs percurso, distancia)

### Passos
1. **Opcao 019 — Planejamento**: Relaciona CTRCs disponiveis para transferencia
2. **Opcao 020 — Manifesto Operacional**: Informar carreta provisoria, carregar CTRCs (serie+numero+DV), emitir manifesto informando placa definitiva, conferente, unidade destino, previsao chegada
3. **Opcao 072 — Contratacao Veiculo**: Placa, CEP origem, unidade destino. Sistema calcula distancia (403 ou Google). Gera CIOT automaticamente + Vale Pedagio. Credita CCF (486)
   - **Carreteiro**: CTRB + RPA + CIOT por viagem + retencoes INSS/IR
   - **Agregado**: OS + CIOT 30 dias, acerto na CCF
   - **Frota**: CTRB para adiantamentos, sem CIOT
4. **Opcao 025 — Saida Veiculo**: Unifica Manifestos em MDF-e por UF destino, submete SEFAZ. SMP automatico (gerenciadoras de risco). Impressao DAMDFE (sintetico, com/sem frete)

### Pontos de Decisao
- Operacao fluvial (portuaria): BALSA, EMPURRADOR, CPF PILOTO obrigatorios
- Operacao aerea: Manifesto nao gera MDF-e, vincular AWB (069)
- Vale Pedagio nao informado → multa ANTT (Res. 2.885/2008)
- SMP rejeitada → impressao DAMDFE bloqueada (903)
- >10.000 CT-es → usar DAMDFE Sintetico (limite SEFAZ: 2.048 Kb XML)

### Diagrama
```
019 Planejamento → 020 Manifesto → 072 CTRB → 025 Saida → MDF-e SEFAZ
                        ↓              ↓           ↓
                   Carreta Prov    CCF 486    SMP/Pedagio
                                                  ↓
                                            Rastreamento → 030 Chegada (F04)
```

### Problemas Comuns
- RNTRC invalido → SEFAZ rejeita MDF-e
- Liberacao GR expirada → veiculo/motorista/ajudante sem autorizacao
- CIOT nao encerrado >60 dias → bloqueio ANTT
- MDF-e sem chegada aos 29 dias → encerramento automatico SSW

### Integracao
- **Alimenta**: F04 (Chegada), F08 (Contas a Pagar via CCF)
- **Depende de**: F02 (CT-es autorizados)

---

## F04 — Chegada e Descarga

### Trigger
Veiculo chega a unidade destino apos viagem de transferencia.

### Pre-requisitos
- Veiculo com saida registrada (025)
- Manifesto Operacional emitido e nao cancelado

### Passos
1. **Opcao 030 — Chegada**: Captura codigo de barras Manifesto. MDF-e encerrado automaticamente no SEFAZ. CTRB/OS encerrado. CTRCs ficam disponiveis
2. **Opcao 078 — Inicio Descarga** (opcional): SSWBar atualiza chegada automaticamente
3. **Opcao 264 — Descarga SSWBar**: Captura codigo barras volumes. Detecta faltas e sobras automaticamente. Gaiolas/pallets podem ser descarregados sem conferencia (064)
4. **Opcao 033 — Ocorrencias Transferencia**: Registrar avarias, extravios, atrasos. Sistema notifica unidade origem
5. **Opcao 108 — Instrucoes**: Unidade origem fornece instrucoes para resolucao. Unidade atual consulta via opcao 133

### Regra Critica
**Nenhuma ocorrencia deve permanecer pendente sem instrucoes ao final do dia.**

### Diagrama
```
030 Chegada → 078 Inicio → 264 SSWBar → 064 Fim → CTRCs Disponiveis
                              ↓
                    Faltas/Sobras Detectadas
                              ↓
                    033 Ocorrencia → 108 Instrucoes → 133 Minhas Ocorrencias
```

### Integracao
- **Alimenta**: F05 (Entrega) — CTRCs disponiveis
- **Depende de**: F03 (Saida registrada)

---

## F05 — Entrega ao Destinatario

### Trigger
CT-e na unidade de entrega (destino final).

### Pre-requisitos
- CTRCs com chegada registrada (030)
- CTRCs sem ocorrencia tipo PRE-ENTREGA e nao segregados (091)

### Passos
1. **Opcao 081 — Planejamento Entrega**: Filtros por setor (404), subcontratante (485), previsao, ABC (102). Funcoes de roteirizacao (limite 300 pontos/setor)
2. **Opcao 035 — Romaneio de Entregas**: Veiculo, motorista, data entrega. SMP automatico. MDF-e de Romaneio (236). Ocorrencia SSW 85 "Saiu para Entrega"
   - Operacao Sem Papel (903): DACTEs so para clientes que querem papel (381) ou motoristas sem SSWMobile (028)
3. **SSWMobile — Baixa Tempo Real**: Foto ou assinatura como comprovante. "Estou Chegando" notifica cliente automaticamente
4. **Opcao 038 — Baixa Manual**: Por romaneio, codigo de barras, digitacao ou romaneio devolucao. Informar recebedor (nome, documento, parentesco) se exigido
5. **Opcao 048 — Liquidacao FOB**: Liquidar fretes FOB A VISTA recebidos por motorista
6. **SSWScan — Escaneamento Comprovantes**: Codigo de barras DACTE faz baixa automatica + anexa comprovante
7. **Opcao 040 — Capa Comprovantes**: Para romaneios itinerantes, enviar comprovantes a matriz

### Pontos de Decisao
- Roteirizacao: com (081) ou sem (sequencia no carregamento 035/SSWBar)
- FOB A VISTA: informar "Receber frete" (038) → Liquidar (048)
- Controle estadias (903): chegada/saida → CTRC Estadia automatico (099) se alem franquia
- CTRC Reentrega (423 = S + ocorrencia REENTREGA): emitido automaticamente

### Diagrama
```
081 Planejamento → Roteirizacao → 035 Romaneio → SSWMobile Baixa
                                       ↓              ↓
                                  SMP/CIOT      Comprovante
                                       ↓              ↓
                                  038 Baixa → 398 Anexar → 040 Capa
                                       ↓
                                  048 Liquidar FOB
```

### Problemas Comuns
- Romaneio sem baixa dia anterior → bloqueio para novo Romaneio (exceto setores sem controle)
- SMP rejeitada → impressao Romaneio bloqueada
- Localizacao errada no mapa → corrigir antes de anotar volumes
- Estadia nao cobrada → verificar relatorio 056/130

### Integracao
- **Alimenta**: F06 (Faturamento), F14 (Remuneracao agregados)
- **Depende de**: F04 (CTRCs disponiveis)

---

# FINANCEIRO (F06-F09)

## F06 — Faturamento

### Trigger
CTRCs autorizados pelo SEFAZ, entregas realizadas.

### Pre-requisitos
- **Opcao 384**: Regras de faturamento do cliente (tipo A/M, periodicidade, separacao, vencimento, banco/carteira)
- **Opcao 483**: Dados do cliente pagador (vendedor, classificacao, envio fatura)
- **Opcao 903/Faturamento**: Automacao agendada (6:00h faturamento, 23:00h cobranca)
- Mes contabil aberto (559)

### Passos
1. **Opcao 435 — Pre-Faturamento**: Lista CTRCs disponiveis para faturar
2. **Opcao 436 — Faturamento Geral**: Agrupa CTRCs em faturas. Requer usuario MTZ. Parametros: CTRCs autorizados ate, data emissao, valor minimo, periodicidade. Aplica debitos/creditos (459). Gera fatura com numero + DV
3. **Opcao 443 — Arquivo Remessa**: Gera arquivo cobranca bancaria (CNAB 400 ou API) para banco ≠ 999
4. **Opcao 444 — Arquivo Retorno**: Recebe confirmacoes banco. Importar ANTES 09:30h. Ocorrencias: 002 (entrada confirmada), 006 (liquidacao), 010 (sustacao protesto)
5. **Opcao 457 — Manutencao Faturas**: Instrucoes bancarias (Abater, Prorrogar, Protestar, Sustar, Baixar). Serasa/Equifax/SPC. Repasse para agencia (CCF 486)

### Pontos de Decisao
- Cliente Tipo A (automatico) → opcao 436. Tipo M (manual) → opcao 437
- Banco 999 (carteira propria) → sem cobranca bancaria
- Creditos > valor fatura → fatura NAO gerada
- Processamento > 200.000 CTRCs → opcao 156 (assincrono)

### Diagrama
```
CTRCs Autorizados → 435 Lista → 436 Faturamento ← 384 Regras
                                      ↓
                              ┌───────┴───────┐
                          Banco=999      Banco≠999
                          (Carteira)         ↓
                              │          443 Remessa → BANCO → 444 Retorno
                              └───────┬───────┘
                                      ↓
                                 457 Manutencao
```

### Integracao
- **Alimenta**: F07 (Liquidacao)
- **Depende de**: F02 (CT-es autorizados), F05 (entregas realizadas)

---

## F07 — Liquidacao e Cobranca

### Trigger
Fatura emitida, vencimento programado.

### Passos
1. **Opcao 444 — Retorno Bancario**: Liquidacao via banco. Contabilizacao automatica (541). Tarifas repassadas ao cliente (384/912)
2. **Opcao 048 — Liquidacao a Vista**: Fretes FOB recebidos por motorista. Gera relacao (452), confrontar com extrato (456)
3. **Opcao 480 — Promessas Pagamento**: Cliente informa data compromisso. Promessa vencida → aviso atraso
4. **Opcao 457 — Instrucoes**: Protestar (R), Baixar (B), Sustar (S). Marcar Serasa/Equifax/SPC (instrucao 96)
5. **Opcao 458 — Caixa Online**: Registra liquidacoes, movimentacoes dinheiro, conciliacao fisica

### Bloqueios Automaticos (Transportar = N)
- Tabelas apagadas (903/Frete)
- Faturas vencidas alem prazo (903/Prazos)
- Faturas protestadas (457)
- Retorno banco protestado (444)
- Inativo cadastro fiscal (808)
- Pendencias SERASA (389)

### Diagrama
```
Fatura (436) → ┌──────┴──────┐
           Banco=999    Banco≠999 → 443 → BANCO → 444 (006=Liquidado)
               │              │
               └──────┬──────┘
                      ↓
                 458 Caixa ← 048 Liquidacao vista
                      ↓
                 569 Conciliacao
```

### Integracao
- **Alimenta**: F09 (Conciliacao)
- **Depende de**: F06 (Faturas)

---

## F08 — Contas a Pagar

### Trigger
Despesa a lancar (combustivel, manutencao, salarios, agregados, etc.)

### Pre-requisitos
- **Opcao 478**: Fornecedor cadastrado, CCF ativada (S/N)
- **Opcao 503**: Eventos de despesa (processos automaticos, creditos PIS/COFINS, retencoes)
- **Opcao 526**: Conta contabil credito do evento

### Passos
1. **Opcao 475 — Programacao Despesas**: Importacao automatica XMLs SEFAZ (5 anos) ou inclusao manual (CNPJ/CPF ou chave NF-e). Evento (503), dados fiscais, retencoes. Gera numero de lancamento. Confirmacao SEFAZ automatica
   - Lancamentos complementares: debita veiculo (577), informa consumo (576), estoque bomba (575), debita CCF (486), debita CTRC (579)
   - Aprovacao centralizada (903): despesa pendente (560) ate aprovacao
2. **Opcao 486 — CCF**: Debitos automaticos (despesa com "Debita CCF=X"), creditos automaticos (CTRB/OS). Acerto manual ou automatizado (903). Gera CTRB/RPA + despesa com 2 parcelas
3. **Opcao 476 — Liquidacao**: A vista, cheque (ate 10), PEF (CTRBs), arquivo bancario (522). Estorno so por usuario que incluiu ou MTZ
4. **Opcao 522 — Arquivo C Pagar**: Para despesas com codigo de barras boleto ou QR Code PIX

### Pontos de Decisao
- Fornecedor CCF ativa → despesa debita CCF automaticamente
- Evento "Credita PIS/COFINS=S" + unidade nao-cumulativa (401) → gera credito
- CFOP 1406/2406/1551/2551 → cadastra imobilizado automaticamente (704)
- Salarios → opcao 580 (NAO 475). Provisao sem lancamento financeiro → opcao 554

### Diagrama
```
NF-e/CT-e (SEFAZ) → 475 Programacao ← 503 Eventos
                          ↓
                    ┌─────┴─────┐
                CCF Ativa    CCF Inativa
                    ↓            │
                486 CCF          │
                    └─────┬─────┘
                          ↓
                    560 Aprovacao ← 903
                          ↓
                    476 Liquidacao → 458 Caixa → 569 Conciliacao
```

### Integracao
- **Alimenta**: F09 (Conciliacao)
- **Depende de**: F03 (CTRBs via 072), F14 (OS via 075)

---

## F09 — Conciliacao Bancaria

### Trigger
Final do dia/mes, apos lancamentos financeiros.

### Pre-requisitos
- **OBRIGATORIO para contabilidade SSW** — pre-requisito para qualquer funcionalidade contabil

### Passos
1. **Opcao 456 — Extrato Bancario**: Conciliar cheques compensados, transferencias, tarifas
2. **Opcao 571 — Razao Contabil**: Adiantamentos/creditos nao identificados (credito seq. 82)
3. **Opcao 569 — Conciliacao**: Informar banco/agencia/conta, data, saldo do extrato. Sistema valida. Divergencia → retornar 456/571. **Bloqueio retroativo**: periodo conciliado NAO permite alteracoes
4. **Opcao 559 — Fechamento Contabil**: Apos conciliacao, calcular saldos, fechar periodo
5. **Opcao 458 — Caixa**: Conciliacao dinheiro especie via contagem fisica

### Impedimentos por Conciliacao (periodo conciliado)
- Cancelamento CTRB/OS em data conciliada (074)
- Lancamentos manuais contabeis (558)
- Alteracao despesas em data conciliada (475)
- Estorno liquidacao (requer desconciliar antes)

### Diagrama
```
Lancamentos Financeiros → ┌──────┴──────┐
                       Banco           Caixa
                          ↓               ↓
                    456 Extrato    458 Contagem fisica
                          ↓
                    571 Ajustes
                          ↓
                    569 Conciliacao → BLOQUEIO RETROATIVO
                          ↓
                    559 Fechamento Contabil
```

### Integracao
- **Depende de**: F07 (Liquidacoes), F08 (Pagamentos)
- **Alimenta**: F11 (Fechamento Contabil)

---

# FISCAL E CONTABIL (F10-F11)

## F10 — Fechamento Fiscal

### Trigger
Final do mes (obrigacao mensal ICMS/IPI e PIS/COFINS).

### Pre-requisitos
- Lancamentos entrada/saida finalizados
- Validador SPED Fiscal e SPED Contribuicoes instalados
- **Opcao 401**: IE + regime PIS/COFINS. **Opcao 410**: Tributacao ICMS
- **Opcao 903/Certificado**: Certificado digital A1 ativo

### Passos
1. **Opcao 567 — Fechamento Fiscal**: Impede alteracoes retroativas. FECHADO AUTOMATICAMENTE ao gerar SPED Fiscal (512)
2. **Opcao 512 — SPED Fiscal ICMS/IPI**: Gera arquivo por IE. Fecha 567 automaticamente por IE
3. **Opcao 515 — SPED Contribuicoes PIS/COFINS**: Gera arquivo por raiz CNPJ. Requer regime nao-cumulativo (401) e eventos configurados (503)
4. **Conferencia**: Livro ICMS (433), Livro ISS (633), SINTEGRA (496), DIFAL (471)
5. **Transmissao SEFAZ**: Arquivo validado → envio

### Pontos de Decisao
- Simples Nacional → opcao 514 (Aliquotas Simples Nacional)
- UF = Distrito Federal → opcao 777 (Livro Eletronico DF)
- ICMS Monofasico (CST 61) → preencher grupo na 475 para credito

### Diagrama
```
Emissao mensal → 567 Fechamento (bloqueia)
                      ↓
                 512 SPED Fiscal (fecha auto por IE)
                      ↓
                 515 SPED Contribuicoes (fecha auto por raiz CNPJ)
                      ↓
                 433/633/496/471 (conferencia)
                      ↓
                 Transmissao SEFAZ
```

### Integracao
- **Alimenta**: F11 (Fechamento Contabil)
- **Depende de**: F02 (CT-es), F08 (despesas)

---

## F11 — Fechamento Contabil

### Trigger
Final do mes ou exercicio.

### Pre-requisitos
- Conciliacao bancaria em dia (569) — **OBRIGATORIO**
- Plano de Contas (540), lancamentos automaticos (541/526) configurados
- Mes anterior fechado
- Validador ECD/ECF instalados. NIRE da Junta Comercial

### Passos
1. **Opcao 558 — Lancamentos Manuais**: Lote com debitos = creditos. Importacao CSV possivel
2. **Opcao 559 — Saldo + Fechamento**: CALCULAR SALDOS → VER SALDOS → FECHAR/ABRIR. Reabertura remove saldos meses seguintes
3. **Opcao 566 — ARE**: Fim de exercicio. Zera contas resultado (grupo 5), transfere para PL
4. **Opcao 534 — ECD (SPED Contabil)**: Periodo nao-anual: Livro A → HASH Validador → Livro R (enviar). Periodo anual: Livro G direto
5. **Opcao 570 — ECF**: Requer ECD (534) gerado e assinado ANTES. Importar ECD no Validador ECF. Lucro Presumido → ECF Livro Caixa adicional

### Diagrama
```
558 Lanc. manuais → 559 Saldo + Fechamento → 566 ARE (fim exercicio)
                                                   ↓
                    534 ECD (A→HASH→R ou G) → 570 ECF → Transmissao Receita
```

### Problemas Comuns
- Lote incompleto (debitos ≠ creditos) → nao efetiva
- Mes anterior aberto → impossivel calcular saldos
- ECD nao gerado antes ECF → validador falha
- Reabertura sem recalculo → saldos meses seguintes removidos

### Integracao
- **Depende de**: F09 (Conciliacao), F10 (Fechamento Fiscal)
- **Alimenta**: Arquivos SPED → Receita Federal

---

# COMERCIAL E PARCERIAS (F12-F14)

## F12 — Comissionamento de Vendedor

### Trigger
Final do periodo de apuracao (mensal).

### Passos
1. **Opcao 415 — Cadastro Vendedor**: Codigo, ativo, login (925), unidade, equipe. Paga comissao sobre CTRCs emitidos ou liquidados
   - Comissao de conquista: % sobre frete OU % sobre DESC NTC (periodo definido)
   - Comissao de manutencao: % reduzido apos conquista
   - Calculo automatico diario (903)
2. **Opcao 483 — Vincular Vendedor ao Cliente**: CTRCs do cliente geram comissao
3. **Opcao 056 — Relatorios**: 120 (analitico), 121 (Excel), 123 (clientes sem movimentacao), 124 (resumo MTZ para pagamento), 127/128 (previsao)
4. **Opcao 475 — Contas a Pagar**: Lancar comissao apurada
5. **Opcao 397 — Metas**: Meta mensal por vendedor/cliente. Cliente Alvo (S) destacado em relatorios (125/126)

### Pontos de Decisao
- Comissao sobre DESC NTC → incentiva fretes com maior resultado (maior desconto = menor comissao)
- Troca de vendedor → trocar LOGIN do codigo (415) em vez de refazer vinculos
- Supervisores → opcao 067 (base sobre frete=B ou sobre comissao=C)

### Diagrama
```
415 Vendedor → 483 Vincular cliente → Emissao CTRCs → Calculo diario (903)
                                                            ↓
                                                   056 Relatorios (120-128)
                                                            ↓
                                                   475 Contas a Pagar → 476 Liquidacao
```

---

## F13 — Contratacao de Veiculo para Transferencia

### Trigger
Manifesto emitido, veiculo necessario para transferencia.

### Pre-requisitos
- **Opcao 026/027**: Veiculo e proprietario cadastrados
- **Opcao 478**: Fornecedor com CCF ativada
- **Opcao 399/499**: Tabelas de contratacao (rota/veiculo)
- Vale Pedagio obrigatorio para terceiros (ANTT)

### Passos
1. **Opcao 399/499 — Tabelas**: Rota (399) ou veiculo (499, prioridade). Tabela ANTT frete minimo (apenas referencia)
2. **Opcao 072 — Contratacao**: Placa, CEP origem, unidade destino, tipo carga, valor. CIOT + Vale Pedagio automaticos. Credita CCF (486)
3. **Opcao 486 — CCF**: Debitos (combustivel, pedagio), creditos (CTRB/OS). Acerto gera Contas a Pagar
4. **Opcao 475 → 476**: Programacao e liquidacao do pagamento

### Tipos de Contratacao

| Tipo | Documento | CIOT | Retencoes |
|------|-----------|------|-----------|
| Carreteiro (PF) | CTRB por viagem | Por viagem | INSS, IR, SEST/SENAT |
| Agregado | OS na viagem | 30 dias | No acerto CCF |
| Frota | CTRB adiantamentos | Nenhum | Conforme despesa |

### Diagrama
```
399/499 Tabelas → 072 Contratacao → CTRB/OS + CIOT + Vale Pedagio
                                         ↓
                                    486 CCF → Acerto → 475 C. Pagar → 476 Liquidacao
```

---

## F14 — Remuneracao Coleta/Entrega (Agregados)

### Trigger
Entregas realizadas (romaneios baixados com ocorrencias).

### Pre-requisitos
- **Opcao 478**: Fornecedor com CCF ativada
- **Opcao 409**: Tabela remuneracao (% frete, valor/entrega, valor/coleta, valor/KM, diaria, minimo diario)

### Passos
1. **Opcao 409 — Tabela Remuneracao**: Componentes por veiculo. Replicacao via opcao 086
2. **Opcao 076 — Demonstrativo** (previa): Veiculo + periodo. NAO processa pagamentos
3. **Opcao 075 — Processamento**: Calcula remuneracao, emite OS, credita CCF (486)
4. **Opcao 486 → 475 → 476**: Acerto CCF → Contas a Pagar → Liquidacao

### Fluxo Automatizado (opcional)
- Ativar em 903/Agendar + 478 (fornecedor). Executa 076+075 automaticamente. E-mail demonstrativo ao fornecedor. Relatorio 056/276

### Periodos de Calculo
- **Coletas**: Periodo autorizacao CT-e (0:00h-6:00h → dia anterior)
- **Entregas**: Periodo emissao romaneios
- **Valores frete**: Sempre integrais (com ICMS)
- **Reentrega**: Contabilizada mais de uma vez

### Diagrama
```
409 Tabela → 076 Demonstrativo (previa) → 075 Processamento → OS + CCF 486
                                                                      ↓
                                                    486 Acerto → 475 C. Pagar → 476 Liquidacao
```

---

# FROTA (F15-F17)

## F15 — Manutencao Preventiva

### Trigger
Quilometragem atinge limite de check-list (314) ou plano de manutencao (614).

### Pre-requisitos
- **Opcao 097**: Tipo veiculo com "Frota controla"=X, "Possui odometro"=X
- **Opcao 026**: Veiculo com odometro inicial
- **Opcao 314**: Check-list com periodicidade em Km (ex: 30.000)
- **Opcao 614**: Plano manutencao com ate 20 itens (Dias OU Km)
- Vinculacao: 315 (check-list→veiculo), 615 (plano→veiculo)

### Passos
1. Configurar tipo veiculo (097) → cadastrar veiculo (026)
2. Criar check-list (314) ou plano (614) → vincular ao veiculo (315/615)
3. Quilometragem atualizada automaticamente via operacoes 025/030/035 (API Google)
4. Sistema gera OS na opcao 131 quando Km atinge limite
5. Equipe resolve OS na 131: informa odometro, descreve providencias
6. Proximo agendamento criado automaticamente conforme periodicidade

### Diagrama
```
097 Tipo → 026 Veiculo → 314/614 Check-list/Plano → 315/615 Vincula
                ↓                                           ↓
          025/030/035 Operacao                         131 OS gerada
                ↓                                           ↓
          Odometro atualizado                        Equipe resolve
                                                           ↓
                                                    Proximo agendamento
```

---

## F16 — Controle de Pneus

### Trigger
Movimentacao de pneu (troca de posicao, retirada, instalacao).

### Passos
1. Numerar pneus fisicamente (numeradores eletricos)
2. **Opcao 313 — Cadastrar**: Numero, dados, localizacao, Km inicial
3. **Opcao 316 — Movimentar**: Posicoes (1o digito=eixo, 2o=E/D, 3o=I/E, 4o=T tracao, S1/S2=estepes, CONS=conserto, sigla=almoxarifado)
4. Operacao (025/030/035) → pneus nas posicoes recebem Km automaticamente
5. **Opcao 317 — Vida do Pneu**: Historico completo desde aquisicao
6. **Opcao 318 — Estoque**: Pneus em almoxarifados

### Diagrama
```
097 → 026 Veiculo → 313 Cadastro → 316 Movimentacao
              ↓                          ↓
        025/030/035              Historico 317 + Estoque 318
              ↓
        Km atualizado automaticamente
```

---

## F17 — Consumo de Combustivel

### Trigger
Abastecimento registrado (475 ou 320).

### Pre-requisitos
- **Opcao 026**: Medias min/max de consumo configuradas no veiculo
- **Opcao 503**: Evento com "Informa consumo"=X

### Passos
1. **Opcao 475 — Despesa**: Lancamento com evento tipo COMBUSTIVEL → calcula media
   **OU Opcao 320 — Bomba Interna**: Codigo bomba, placa, litros → valor por tipo veiculo (321)
2. Sistema calcula media do abastecimento
3. Se media < minimo OU > maximo → OS automatica na opcao 131
4. Equipe resolve OS (vazamento, problema mecanico, desvio)
5. **Opcao 322 — Relatorio Consumo**: Todos abastecimentos + medias do mes

### Diagrama
```
475 Despesa OU 320 Bomba → Calcula media ← odometro (025/030/035)
                                  ↓
                           Fora limites? → 131 OS automatica → Equipe resolve
```

---

# OUTROS (F18-F20)

## F18 — Emissao de RPS/NFS-e

### Trigger
Servico municipal (frete com origem = destino).

### Pre-requisitos
- **Opcao 401**: Inscricao Municipal
- **Opcao 402**: Aliquota ISS por municipio (Normal ou Substituicao Tributaria)
- **Opcao 903**: Certificado digital (prefeituras com webservice)

### Passos
1. **Opcao 004 — Emissao RPS** (transporte municipal): Origem = Destino → ISS calculado. Status "DIGITADOS"
   **OU Opcao 733 — RPS Outros Servicos** (logistica): CNPJ, descricao, valor
2. **Opcao 009 — Conversao**:
   - **COM webservice (70+ cidades)**: "Enviar a Prefeitura" → NFS-e automatica → "Imprimir todos"
   - **SEM webservice (40+ cidades)**: Imprimir RPS → opcao 014 gerar lote → enviar portal → importar retorno

### Diagrama
```
004 Transp OU 733 Outros → RPS "DIGITADOS"
                                ↓
                  ┌─────────────┴─────────────┐
              COM webservice              SEM webservice
                  ↓                           ↓
           009 Enviar → NFS-e auto      009 Imprimir → 014 Lote → Portal
```

---

## F19 — Gestao de Estoque (Logistica/Armazenagem)

### Trigger
Mercadoria do cliente chega para armazenagem.

### Pre-requisitos
- **Opcao 388**: Cliente como ARMAZEM GERAL ou OPERADOR LOGISTICO
- **Opcao 741**: Produtos cadastrados (ou importacao automatica via XML)

### Modalidades

| Tipo | Fiscal | NFT | NF Saida |
|------|--------|-----|----------|
| Armazem Geral | Sim (SEFAZ) | Obrigatoria (707) | NF venda cliente |
| Operador Logistico | Nao | Nenhuma | Mesma NF entrada |

### Passos
1. **Opcao 701 — Entrada**: Importar NF-e (chave 44 digitos) → cadastra produtos automaticamente (741). Guarda ICMS se "VINCULAR NF DE ENTRADA"=S (388)
2. **Opcao 721 — Saldo**: Entradas, saidas e saldos em tempo real
3. **Opcao 702 — Saida**: Armazem Geral → emite NFT. Operador Logistico → mesma NF entrada
   - Tipos: N (retorno nao simbolico), S (retorno simbolico), E (devolucao), I (industrializacao)
4. **Opcao 707 — Aprovacao NFT** (so Armazem Geral): Enviar ao SEFAZ → DANFE
5. **Opcao 733 — Cobranca**: RPS servico armazenagem → 009/014 para NFS-e

### Diagrama
```
741 Produtos → 701 Entrada (XML NF-e) → 721 Saldo → 702 Saida
                                                        ↓
                                              ┌─────────┴─────────┐
                                         Armazem Geral      Operador
                                              ↓                  ↓
                                         707 NFT (SEFAZ)    Mesma NF
                                              ↓
                                         733 Cobranca → 009/014 NFS-e
```

### Conceito: M2 Empilhado
- Formula: `area_sem_empilhamento / qtd_maxima_empilhavel`
- Exemplo: 1,2 m2 com empilhamento max 50 → 0,024 m2/caixa
- Usado em 741 (cadastro) e 722 (saldos diarios Excel para calculo armazenagem)

---

## F20 — Embarcador: Expedicao

### Trigger
Mercadoria a expedir pelo embarcador.

### Pre-requisitos
- **Opcao 401**: Unidade tipo EMBARCADOR
- **Opcao 402/401**: Cidades atendidas + transportadoras contratadas associadas
- **Opcao 417/418**: Tabelas frete. **Opcao 618**: Aprovacao pelas transportadoras
- **Opcao 403**: Rotas. **Opcao 405**: Ocorrencias. SSWBar configurado

### Tipos de Unidade
| Tipo | Descricao |
|------|-----------|
| Terceira | Transportadora contratada (embarcador sem instalacao fisica) |
| Filial | Transporte operado pelo proprio embarcador |
| Embarcador | Onde expedicao ocorre (emite CEE) |
| Alternativa | Transportadoras diferentes por regiao/mercadoria |

### Passos
1. XML NF-e → CEE criado automaticamente com frete calculado
2. **Opcao 105 — CEE Manual**: Emissao/alteracao (se ainda nao em Manifesto)
3. SSWBar → identificacao volumes (etiqueta EAN com codigo de barras + QR Code)
4. SSWBar → carregamento nos veiculos
5. **Opcao 020 — Manifesto CEEs**: Documento formal de passagem a transportadora
6. **Opcao 025 — Saida**: MDF-e emitido se unidade tem certificado digital
7. Transportadora opera usando frete calculado pelo embarcador no CT-e
8. Rastreamento online (`ssw.inf.br`)
9. **Opcao 963 — Mapa Fretes a Pagar**: Processamento agendado CEEs entregues → Contas a Pagar

### Diagrama
```
XML NF-e → CEE (auto) → SSWBar Etiquetas → SSWBar Carregamento
                                                    ↓
                              105 Manual → 020 Manifesto → 025 Saida → MDF-e
                                                                  ↓
                                                    Transportadora → CT-e (com frete CEE)
                                                                  ↓
                                                    Rastreamento → 963 Mapa → C. Pagar
```

---

# INTEGRACOES TRANSVERSAIS

## Odometro como Eixo Central (F15/F16/F17)

Fluxos de Frota dependem de atualizacao automatica de odometro via operacoes:
- **Opcao 025**: Saida veiculo (API Google)
- **Opcao 030**: Chegada veiculo
- **Opcao 035**: Romaneio entregas

Falha nesta integracao afeta: manutencao preventiva, quilometragem de pneus, calculo de media de combustivel.

## CCF como Integrador Financeiro

**Opcao 486** conecta automaticamente:
- CTRBs de transferencia (072) → credito
- OS de coleta/entrega (075) → credito
- Despesas (475 com "Debita CCF") → debito
- Abastecimento interno (320) → debito veiculos terceiros
- Acerto → Contas a Pagar (475) → Liquidacao (476)

Categorias: Agente/Parceiro, Proprietario, Motorista (define contas contabeis via 541).

## SSWBar como Ferramenta Transversal

- **F01**: Descarga coleta (identificacao volumes, conferencia)
- **F03**: Carregamento Manifesto (captura volumes, sequencia)
- **F04**: Descarga transferencia (264 — faltas/sobras automaticas)
- **F05**: Carregamento entrega (035 — sequencia roteiro)
- **F19**: Carga/descarga mercadorias (armazenagem)
- **F20**: Identificacao volumes + carregamento (embarcador)

## SSWMobile

- **F01**: Recebe coletas online, captura DANFE (206)
- **F03**: Localizacao a cada 5 min, saida automatica (3 pontos fora raio)
- **F05**: Roteiro, baixa tempo real, foto/assinatura, "Estou Chegando"

## Lancamentos Automaticos Contabeis (Opcao 541)

| Evento | Credito | Debito |
|--------|---------|--------|
| Liquidacao fatura (006) | Seq 13/14 (Dupl. Receber) | Seq 63/11 (Banco) |
| Liquidacao c/ juros | Seq 33 | Seq 13/14 |
| Liquidacao c/ desconto | Seq 13/14 | Seq 35 |
| Liquidacao despesa a vista | Seq 63/11 (Banco) | Conta credito evento |
| Liquidacao despesa cheque | Seq 17 (Cheques a Pagar) | Conta credito evento |
| Compensacao cheque | Seq 11 (Banco) | Seq 17 |
| CCF Coleta agregado | Seq 42 | Seq 25 |
| CCF Transferencia agregado | Seq 43 | Seq 25 |
| CCF Agente/Parceiro | Seq 44 | Seq 25 |
| CCF Motorista Frota | Seq 63/11 | Seq 19 |
| Adiantamento nao identificado | Seq 82 | Seq 63/11 |

## Ocorrencias SSW Padronizadas

| Codigo | Descricao | Gerada por |
|--------|-----------|------------|
| SSW 19 | Anexado comprovante complementar | 398 |
| SSW 29 | Chegada local entrega (estadia) | SSWMobile |
| SSW 78 | Coleta realizada (reversa) | SSWMobile |
| SSW 79 | Coleta agendada (reversa) | SSWMobile |
| SSW 80 | Documento transporte emitido | 007 |
| SSW 85 | Saiu para entrega | 035 |
| SSW 88 | Resgate mercadoria | 101 |
| SSW 95 | Estou Chegando (previsao mudou) | SSWMobile |

## Certificado Digital A1

- Tipo: Arquivo PFX + senha. Raiz CNPJ: todos CNPJs compartilham
- Vencimento: Alertas em opcoes 007, 551, 707
- **Bloqueia totalmente**: Emissao CT-e, MDF-e, NFS-e, NFT, SPED, CIOT
- Renovacao: Adquirir novo .PFX, instalar via 903/Certificados

## Opcao 903 — Parametros Centrais

| Area | Parametros-chave |
|------|-----------------|
| Frete | Cubagem padrao, aprovacao tabelas, prazo vencimento |
| Prazos | Dias inadimplencia, prazo Entrega Dificil |
| Credito | Limites ABC (A, B, C) |
| Operacao | Conferentes, cubagem obrigatoria, Estou Chegando, Sem Papel |
| PEF/CIOT | Administradoras, valor CIOT bruto, PEF parcela |
| GR | Gerenciadora padrao, provedor satelite, SMP |
| SMS | Provedor, credenciais |
| Envio SEFAZ | Automatico/Manual, requisitos pre-CT-es |
| Certificados | CNPJ, PFX, senha, RNTRC |
| Faturamento | Horario automatico (6:00h), cobranca API (23:00h) |

---

## Hierarquias de Configuracao

### Faturamento
1. Cliente especifico (384): Tipo, periodicidade, separacao, vencimento, banco
2. Transportadora (903): Automacao agendada

### Limites de Credito
1. Grupo (583) — prevalece se cliente em grupo
2. Transportadora ABC (903) — usado se sem grupo
3. Individual cliente (389) — sempre consultado

### Tabelas de Frete (Prioridade)
1. Frete informado por usuario autorizado (925)
2. Cotacao (002)
3. Tabelas do cliente (417/418)
4. Tabelas por rota (420)
5. Tabela Generica (923)

### Contratacao Transferencia
1. Tabela por veiculo (499) — prioridade
2. Tabela por rota (399) — fallback
