# POP-E04 — Emitir Cobranca Bancaria (Boleto)

**Categoria**: E — Financeiro: Recebiveis
**Prioridade**: P2 (Media)
**Status**: A IMPLANTAR
**Executor Atual**: Ninguem
**Executor Futuro**: Jaqueline
**Data Criacao**: 2026-02-16
**Autor**: Claude (Agente Logistico)

---

## Objetivo

Profissionalizar a cobranca de faturas de clientes atraves da emissao de boletos bancarios, substituindo o modelo atual de deposito direto/transferencia manual. O processo envolve a geracao de arquivos de remessa CNAB para o banco, envio ao banco, e importacao dos retornos bancarios para confirmacao de entrada, liquidacao e outras ocorrencias.

---

## Trigger

- **Fatura emitida** (opcoes [436](../financeiro/436-faturamento-geral.md)/[437](../financeiro/437-faturamento-manual.md)) para cliente configurado com cobranca bancaria ([384](../financeiro/384-cadastro-clientes.md))
- **Vencimento proximo** (ex: D-2 antes do vencimento original)
- **Alteracao de vencimento** solicitada pelo cliente
- **Cancelamento de fatura** (gerar remessa tipo Baixa)
- **Protesto** de cliente inadimplente (conforme parametros [384](../financeiro/384-cadastro-clientes.md)/[904](../cadastros/904-bancos-contas-bancarias.md))

---

## Frequencia

- **Diaria**: Geracao de remessa as 17:00h para envio ao banco no mesmo dia
- **Diaria**: Importacao de retorno ANTES DAS 09:30H (sistema envia avisos de atraso nesse horario)
- **Eventual**: Alteracoes de vencimento/baixas conforme necessidade
- **Mensal**: Conferencia de liquidacoes via relatorio 460

---

## Pre-requisitos

### Sistema
1. **Conta bancaria cadastrada** ([opcao 904](../cadastros/904-bancos-contas-bancarias.md)) com carteira de cobranca configurada
2. **Cliente configurado para cobranca bancaria** ([opcao 384](../financeiro/384-cadastro-clientes.md)):
   - Campo "Cobranca" = B (Bancaria)
   - Parametros de protesto definidos (dias para protesto, valor minimo)
   - Flag de tarifas repassaveis (se aplicavel)
3. **Faturas emitidas** (opcoes [436](../financeiro/436-faturamento-geral.md)/[437](../financeiro/437-faturamento-manual.md)) e pendentes de cobranca
4. **Ocorrencias bancarias configuradas** (opcao 912) para contabilizacao automatica
5. **Clientes especiais cadastrados** ([opcao 483](../cadastros/483-cadastro-clientes.md)) se houver excecoes de protesto

### Operacional
- Acesso ao internet banking para envio manual de remessa (se nao houver API automatizada)
- Download de retorno bancario disponivel (arquivo CNAB)
- Conhecimento de codigos de ocorrencia bancaria (002, 003, 006, etc.)

### Pessoas
- Jaqueline treinada em operacao [443](../financeiro/443-gera-arquivo-cobranca.md)/[444](../financeiro/444-cobranca-bancaria.md)
- Rafael como backup
- Contato com gerente do banco para troubleshooting

---

## Passo-a-Passo

### ETAPA 1: Gerar Arquivo de Remessa (Opcao 443)
1. Acessar menu: **Financeiro > Contas a Receber > Gera Arquivo Cobranca — Remessa ([443](../financeiro/443-gera-arquivo-cobranca.md))**
2. Informar:
   - **Banco/Carteira**: selecionar cadastro [904](../cadastros/904-bancos-contas-bancarias.md)
   - **Tipo de remessa**: Inclusao (novas faturas) | Alteracao (vencimentos) | Baixa (cancelamentos) | Protesto
   - **Periodo**: data inicial e final das faturas
   - **Clientes**: filtrar se necessario (ou deixar em branco para todos)
3. Sistema gera arquivo `.REM` na pasta configurada
4. **CHECKPOINT**: Anotar quantidade de titulos incluidos no arquivo

### ETAPA 2: Enviar Remessa ao Banco
**Se API automatizada (Itau/Sicred/Bradesco):**
- Sistema envia automaticamente as 23:00h — PULAR para ETAPA 3

**Se envio manual:**
1. Acessar internet banking
2. Navegar para area de cobranca/remessa
3. Fazer upload do arquivo `.REM`
4. Confirmar envio
5. Aguardar confirmacao do banco (email ou notificacao)

### ETAPA 3: Baixar Arquivo de Retorno
**Se API automatizada:**
- Sistema baixa automaticamente as 23:00h — PULAR para ETAPA 4

**Se download manual:**
1. Acessar internet banking (dia seguinte ou D+2)
2. Baixar arquivo `.RET` da area de cobranca
3. Salvar na pasta configurada do SSW

### ETAPA 4: Importar Retorno (Opcao 444)
**TIMING CRITICO: IMPORTAR ANTES DAS 09:30H**

1. Acessar menu: **Financeiro > Contas a Receber > Cobranca Bancaria — Retorno ([444](../financeiro/444-cobranca-bancaria.md))**
2. Informar:
   - **Banco/Carteira**: mesmo da remessa
   - **Arquivo**: selecionar `.RET` baixado
3. Clicar **Importar**
4. Sistema processa e exibe log de ocorrencias:
   - **002**: Entrada confirmada (boleto registrado no banco)
   - **003**: Entrada rejeitada (verificar motivo)
   - **006**: Liquidacao normal (cliente pagou)
   - **005**: Liquidacao sem registro (pagamento direto)
   - **010**: Sustacao de protesto/baixa
   - **028**: Tarifa bancaria cobrada

### ETAPA 5: Validar Contabilizacao Automatica
1. Para cada liquidacao (ocorrencia 006):
   - Sistema gera **credito** seq 13/14 (Contas a Receber)
   - Sistema gera **debito** seq 63/11 (Banco Conta Movimento)
2. Para tarifas bancarias (ocorrencia 028):
   - Verificar se cliente tera tarifa repassada ([384](../financeiro/384-cadastro-clientes.md))
   - Contabilizacao seq configurada em 912

### ETAPA 6: Tratar Rejeicoes (Ocorrencia 003)
1. Acessar opcao **457** (Controle de Faturas)
2. Filtrar por fatura rejeitada
3. Verificar motivo da rejeicao (campo "Ocorrencia Bancaria")
4. Corrigir dados (ex: CEP invalido, sacado incorreto)
5. Gerar nova remessa ([443](../financeiro/443-gera-arquivo-cobranca.md)) apenas para essa fatura

### ETAPA 7: Monitorar Trocas de Arquivos (Opcao 446)
1. Acessar menu: **Financeiro > Contas a Receber > Monitora Trocas Arquivos (446)**
2. Verificar historico de remessas/retornos
3. Conferir status: Enviado | Processado | Erro
4. Investigar erros (ex: arquivo corrompido, formato invalido)

### ETAPA 8: Conferir Valores de Retornos (Opcao 460)
**Frequencia: Semanal ou mensal**

1. Acessar menu: **Financeiro > Contas a Receber > Valores de Retornos por Ocorrencia (460)**
2. Informar periodo
3. Analisar:
   - Total liquidado (ocorrencia 006)
   - Total de tarifas (ocorrencia 028)
   - Protestos efetivados
4. Cruzar com extrato bancario

### ETAPA 9: Configurar Protesto (Eventual)
**Apenas se cliente inadimplente atingir criterios:**

1. Verificar parametros cliente ([384](../financeiro/384-cadastro-clientes.md)):
   - Dias para protesto (ex: 10 dias apos vencimento)
   - Valor minimo para protesto (ex: R$ 500,00)
2. Verificar se cliente NAO esta em lista de excecoes ([483](../cadastros/483-cadastro-clientes.md))
3. Gerar remessa tipo **Protesto** ([443](../financeiro/443-gera-arquivo-cobranca.md))
4. Banco efetiva protesto automaticamente

### ETAPA 10: Cancelar Boleto (Se Necessario)
**Cenarios: fatura cancelada, pagamento fora do boleto**

1. Acessar opcao **437** (Faturas Emitidas)
2. Selecionar fatura
3. Gerar arquivo de remessa tipo **Baixa** (botao especifico)
4. Enviar ao banco (manual ou automatico)

---

## Contexto CarVia

| Aspecto | Hoje (2026-02-16) | Futuro (Com Cobranca Bancaria) |
|---------|-------------------|--------------------------------|
| **Modelo de cobranca** | Deposito direto/transferencia manual | Boleto bancario via SSW |
| **Controle de pagamentos** | Rafael confere extrato manualmente ([opcao 048](../operacional/048-liquidacao-vista.md)) | Sistema importa retorno automatico ([444](../financeiro/444-cobranca-bancaria.md)) |
| **Aviso de atraso** | Email/WhatsApp manual de Rafael | Sistema envia automatico as 09:30h |
| **Protesto** | NAO acontece | Automatico conforme parametros cliente ([384](../financeiro/384-cadastro-clientes.md)) |
| **Tarifas bancarias** | NAO controladas | Contabilizadas automaticamente (seq 912) |
| **Pre-requisito critico** | — | Cadastrar conta bancaria ([904](../cadastros/904-bancos-contas-bancarias.md)) — ver PEND-11 |
| **Pre-requisito critico** | — | Configurar parametros de cobranca por cliente ([384](../financeiro/384-cadastro-clientes.md)) — ver PEND-08 |
| **Executor** | Rafael (fora do SSW) | Jaqueline (dentro do SSW) |
| **Profissionalizacao** | Baixa (depende de goodwill do cliente) | Alta (cobranca formal com instrumento juridico) |

**Justificativa da implantacao**: Com crescimento da carteira de clientes, cobranca bancaria se torna necessaria para profissionalizar processo, automatizar avisos, e ter instrumento de protesto contra inadimplentes. Hoje CarVia depende de deposito direto, sem controle formal.

---

## Erros Comuns e Solucoes

| Erro | Sintoma | Causa Provavel | Solucao |
|------|---------|----------------|---------|
| **Remessa nao gera titulos** | Arquivo `.REM` vazio ou com 0 registros | Cliente nao configurado com Cobranca=B ([384](../financeiro/384-cadastro-clientes.md)) | Acessar 384, alterar campo "Cobranca" para B, salvar |
| **Ocorrencia 003 (Rejeicao)** | Boleto nao registrado no banco | CEP invalido, sacado sem CPF/CNPJ, vencimento retroativo | Acessar 457, verificar motivo, corrigir cadastro cliente ([384](../financeiro/384-cadastro-clientes.md)) ou fatura (437), gerar nova remessa |
| **Retorno nao importa** | Erro ao processar arquivo `.RET` | Formato CNAB incompativel, banco/carteira nao cadastrado | Verificar versao CNAB do banco (240 ou 400), conferir cadastro [904](../cadastros/904-bancos-contas-bancarias.md), contatar suporte SSW |
| **Tarifa bancaria nao contabilizada** | Ocorrencia 028 sem lancamento contabil | Ocorrencia 028 nao configurada em 912 | Acessar 912, cadastrar ocorrencia 028, associar sequencia contabil |
| **Protesto nao efetivado** | Cliente inadimplente nao protestado | Cliente em lista de excecoes ([483](../cadastros/483-cadastro-clientes.md)) ou dias/valor minimo nao atingido | Verificar 483, remover se necessario; verificar parametros protesto em [384](../financeiro/384-cadastro-clientes.md) |
| **Aviso de atraso enviado antes de importar retorno** | Sistema envia aviso as 09:30h mas retorno importado as 10:00h | Retorno nao importado a tempo | SEMPRE importar retorno ANTES DAS 09:30H |
| **Liquidacao duplicada** | Ocorrencia 006 + baixa manual ([048](../operacional/048-liquidacao-vista.md)) | Rafael deu baixa manual sem esperar retorno | NUNCA dar baixa manual (048) se fatura tem cobranca bancaria — esperar retorno automatico |
| **API automatizada nao funciona** | Remessa nao enviada as 23:00h | Credenciais API expiradas, banco nao suportado | Verificar cadastro [904](../cadastros/904-bancos-contas-bancarias.md) (credenciais API), contatar suporte SSW, usar envio manual temporariamente |

---

## Verificacao Playwright

| Passo | Acao | Elemento Alvo | Validacao |
|-------|------|---------------|-----------|
| **1. Acessar opcao [443](../financeiro/443-gera-arquivo-cobranca.md)** | `page.goto("/opcao/443")` | Menu "Gera Arquivo Cobranca" | `expect(page.locator("h1")).to_contain_text("Remessa")` |
| **2. Selecionar banco** | `page.select_option("#banco", "001")` | Dropdown banco/carteira | `expect(page.locator("#banco")).to_have_value("001")` |
| **3. Selecionar tipo Inclusao** | `page.check("#tipo_inclusao")` | Radio button "Inclusao" | `expect(page.locator("#tipo_inclusao")).to_be_checked()` |
| **4. Gerar remessa** | `page.click("button[type=submit]")` | Botao "Gerar Remessa" | `expect(page.locator(".alert-success")).to_contain_text("Arquivo gerado")` |
| **5. Verificar quantidade titulos** | `page.locator(".qtd-titulos").inner_text()` | Label quantidade | `assert int(qtd) > 0` |
| **6. Acessar opcao [444](../financeiro/444-cobranca-bancaria.md)** | `page.goto("/opcao/444")` | Menu "Cobranca Bancaria — Retorno" | `expect(page.locator("h1")).to_contain_text("Retorno")` |
| **7. Upload arquivo .RET** | `page.set_input_files("#arquivo", "retorno.ret")` | Input file | `expect(page.locator("#arquivo")).to_have_value("retorno.ret")` |
| **8. Importar retorno** | `page.click("button[type=submit]")` | Botao "Importar Retorno" | `expect(page.locator(".alert-success")).to_be_visible()` |
| **9. Verificar ocorrencias** | `page.locator("table.ocorrencias tbody tr")` | Tabela de ocorrencias | `expect(rows.count()).to_be_greater_than(0)` |
| **10. Conferir opcao 460** | `page.goto("/opcao/460")` | Relatorio valores retornos | `expect(page.locator(".total-liquidado")).to_be_visible()` |

---

## POPs Relacionados

| POP | Titulo | Relacao |
|-----|--------|---------|
| **POP-E01** | Emitir Fatura (CTRB/OS) | **PRE-REQUISITO** — fatura deve existir antes de gerar remessa |
| **POP-E02** | Baixar Titulo a Receber | **ALTERNATIVA** — baixa manual ([048](../operacional/048-liquidacao-vista.md)) so para clientes SEM cobranca bancaria |
| **POP-F04** | Conciliar Banco | **DEPENDENTE** — liquidacoes bancarias (ocorrencia 006) devem ser conciliadas via 569 |
| **PEND-08** | Cadastrar Parametros de Cobranca ([384](../financeiro/384-cadastro-clientes.md)) | **PRE-REQUISITO CRITICO** — cliente deve ter Cobranca=B e parametros de protesto |
| **PEND-11** | Cadastrar Conta Bancaria ([904](../cadastros/904-bancos-contas-bancarias.md)) | **PRE-REQUISITO CRITICO** — banco/carteira devem estar configurados com credenciais API (se aplicavel) |
| **POP-G02** | Consultar Inadimplencia | **COMPLEMENTAR** — protesto automatico depende de parametros [384](../financeiro/384-cadastro-clientes.md)/[483](../cadastros/483-cadastro-clientes.md) |

---

## Historico de Revisoes

| Versao | Data | Autor | Alteracoes |
|--------|------|-------|------------|
| **1.0** | 2026-02-16 | Claude (Agente Logistico) | Criacao inicial baseada em docs SSW opcoes [443](../financeiro/443-gera-arquivo-cobranca.md)/[444](../financeiro/444-cobranca-bancaria.md)/446/457/460/480/[904](../cadastros/904-bancos-contas-bancarias.md)/912. Contexto CarVia: implantacao futura (P2), pre-requisitos PEND-08 e PEND-11, executor Jaqueline. Inclui fluxo completo remessa/retorno, contabilizacao automatica, protesto, API automatizada (Itau/Sicred/Bradesco), timing critico importacao retorno antes 09:30h. |
