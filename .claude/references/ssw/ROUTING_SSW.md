# SSW — Routing de Documentacao para o Agente

> **Criado em**: 2026-02-16
> **Atualizado em**: 2026-02-16 (B2: decision trees, Top 40 errata, cross-ref)
> **Objetivo**: Permitir ao agente web encontrar rapidamente o documento SSW correto para qualquer pergunta do usuario
> **Cobertura**: 45 POPs, 220 opcoes, 20 fluxos, 12 visoes gerais

---

## Regra Zero: Nacom vs CarVia

> **Nacom Goya** = Industria de alimentos. CONTRATA frete. Usa o **Sistema de Fretes** (app Flask, banco PostgreSQL).
> **CarVia Logistica** = Transportadora. VENDE frete. Usa o **SSW** (sistema externo web).

| Sinal na pergunta | Empresa | Skill correta |
|--------------------|---------|---------------|
| "no SSW", "opcao NNN", "CarVia", "CTRC", "MDF-e", "POP" | CarVia | `acessando-ssw` |
| "cotacao de frete" (sem "SSW") | Nacom | `cotando-frete` |
| "estoque", "separacao", "embarque", "pedido VCD" | Nacom | `gerindo-expedicao` |
| "NF entregue?", "canhoto", "devolucao" | Nacom | `monitorando-entregas` |
| "faturamento" (sem "SSW"/"CarVia") | Nacom | `consultando-sql` ou `monitorando-entregas` |
| Ambiguo ("faturamento", "tabela de frete") | — | Perguntar: "Voce quer no SSW (CarVia) ou no sistema interno (Nacom)?" |

**Quando nao qualificado**: O contexto padrao e **Nacom** (90% dos usuarios sao da operacao Nacom). SSW so e relevante quando explicitamente mencionado ou quando o usuario e identificado como operador CarVia.

---

## Decision Tree Principal

```
PERGUNTA DO USUARIO
    |
    ├── "Como fazer X no SSW?" / "passo a passo"
    |       → POP correspondente (ver Mapa Intencao→POP)
    |
    ├── "O que e opcao NNN?" / "para que serve a NNN?"
    |       → Doc de opcao (ver Mapa Intencao→Opcao)
    |
    ├── "Fluxo completo de X" / "processo end-to-end"
    |       → FLUXOS_PROCESSO.md secao FNN (ver Mapa Intencao→Fluxo)
    |
    ├── "Configurar X" / "parametrizar"
    |       → Doc de opcao de cadastro + POP de implantacao
    |
    ├── "Relatorio de X" / "gerar relatorio"
    |       → ver Arvore 9 "Gerar relatorio" abaixo
    |
    ├── "Consultar dados de X" / "buscar informacao"
    |       → ver Arvore 7 "Consultar dados" abaixo
    |
    ├── "Integrar via EDI" / "enviar/receber arquivo eletronico"
    |       → ver Arvore 8 "Integracoes EDI" abaixo
    |
    ├── "Controlar entregas" / "comprovante" / "canhoto"
    |       → ver Arvore 10 "Controlar entregas" abaixo
    |
    ├── "CarVia faz X?" / "a gente usa opcao NNN?"
    |       → CARVIA_STATUS.md (status de adocao por POP)
    |
    ├── "Visao geral do modulo X"
    |       → visao-geral/NN-modulo.md (ver indice abaixo)
    |
    ├── "Qual a sequencia legal?" / "regras da seguradora"
    |       → POP-G01 (sequencia legal) + POP-G02 (gerenciadora risco)
    |
    └── "Navegar/preencher tela SSW via browser"
            → POP correspondente + browser tool (Playwright)
```

---

## Mapa Intencao → POP (45 POPs)

### A — Implantacao e Cadastros

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| cadastrar cliente novo | A01 | pops/POP-A01-cadastrar-cliente.md |
| cadastrar unidade parceira / transportadora terceiro | A02 | pops/POP-A02-cadastrar-unidade-parceira.md |
| cadastrar cidades atendidas | A03 | pops/POP-A03-cadastrar-cidades.md |
| cadastrar rotas | A04 | pops/POP-A04-cadastrar-rotas.md |
| cadastrar fornecedor / transportadora subcontratada | A05 | pops/POP-A05-cadastrar-fornecedor.md |
| cadastrar custos / comissoes de subcontratacao | A06 | pops/POP-A06-cadastrar-custos-comissoes.md |
| cadastrar tabela de preco por rota | A07 | pops/POP-A07-cadastrar-tabelas-preco.md |
| cadastrar veiculo | A08 | pops/POP-A08-cadastrar-veiculo.md |
| cadastrar motorista | A09 | pops/POP-A09-cadastrar-motorista.md |
| implantar nova rota completa / abrir cidade | A10 | pops/POP-A10-implantar-nova-rota.md |

### B — Comercial e Precificacao

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| cotar frete para cliente / cotacao SSW | B01 | pops/POP-B01-cotar-frete.md |
| entender formacao de preco / simulacao incorreta | B02 | pops/POP-B02-formacao-preco.md |
| configurar parametros de frete (062) | B03 | pops/POP-B03-parametros-frete.md |
| analisar resultado por CTRC / lucratividade | B04 | pops/POP-B04-resultado-ctrc.md |
| gerar relatorios gerenciais (056) | B05 | pops/POP-B05-relatorios-gerenciais.md |

### C — Operacional: Emissao

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| emitir CTe fracionado / placa ARMAZEM | C01 | pops/POP-C01-emitir-cte-fracionado.md |
| emitir CTe carga direta / placa real | C02 | pops/POP-C02-emitir-cte-carga-direta.md |
| emitir CTe complementar / diferenca frete | C03 | pops/POP-C03-emitir-cte-complementar.md |
| registrar custos extras / TDE / diaria / pernoite | C04 | pops/POP-C04-custos-extras.md |
| imprimir CTe / reimprimir DACTe | C05 | pops/POP-C05-imprimir-cte.md |
| cancelar CTe | C06 | pops/POP-C06-cancelar-cte.md |
| carta de correcao CTe | C07 | pops/POP-C07-carta-correcao-cte.md |

### D — Operacional: Transporte e Entrega

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| contratar veiculo / CIOT / vale pedagio | D01 | pops/POP-D01-contratar-veiculo.md |
| criar romaneio de entregas | D02 | pops/POP-D02-romaneio-entregas.md |
| criar manifesto / emitir MDF-e | D03 | pops/POP-D03-manifesto-mdfe.md |
| registrar chegada de veiculo | D04 | pops/POP-D04-chegada-veiculo.md |
| registrar baixa de entrega | D05 | pops/POP-D05-baixa-entrega.md |
| registrar ocorrencias / atraso / avaria | D06 | pops/POP-D06-registrar-ocorrencias.md |
| controlar comprovantes de entrega / canhoto | D07 | pops/POP-D07-comprovantes-entrega.md |

### E — Financeiro: Recebiveis

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| verificar CTRCs disponiveis para faturar / pre-faturamento | E01 | pops/POP-E01-pre-faturamento.md |
| faturar manualmente (437) | E02 | pops/POP-E02-faturar-manualmente.md |
| faturar automaticamente (436) | E03 | pops/POP-E03-faturamento-automatico.md |
| emitir boleto / cobranca bancaria (444) | E04 | pops/POP-E04-cobranca-bancaria.md |
| liquidar fatura / baixar pagamento recebido | E05 | pops/POP-E05-liquidar-fatura.md |
| manter faturas / prorrogar / protestar | E06 | pops/POP-E06-manutencao-faturas.md |

### F — Financeiro: Pagaveis

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| lancar contas a pagar / despesa | F01 | pops/POP-F01-contas-a-pagar.md |
| gerenciar CCF / conta corrente fornecedor | F02 | pops/POP-F02-ccf-conta-corrente-fornecedor.md |
| liquidar despesa / pagar fornecedor | F03 | pops/POP-F03-liquidar-despesa.md |
| conciliar banco | F04 | pops/POP-F04-conciliacao-bancaria.md |
| registrar bloqueio financeiro de CTRC | F05 | pops/POP-F05-bloqueio-financeiro-ctrc.md |
| aprovar despesas pendentes | F06 | pops/POP-F06-aprovar-despesas.md |

### G — Compliance, Frota e Gestao

| Intencao do usuario | POP | Arquivo |
|---------------------|-----|---------|
| sequencia legal obrigatoria / regras carga direta | G01 | pops/POP-G01-sequencia-legal-obrigatoria.md |
| checklist gerenciadora de risco | G02 | pops/POP-G02-checklist-gerenciadora-risco.md |
| controlar custos de frota / combustivel / manutencao | G03 | pops/POP-G03-custos-frota.md |
| extrair relatorios para contabilidade / SPED | G04 | pops/POP-G04-relatorios-contabilidade.md |

---

## Mapa Intencao → Opcao SSW (Top 50)

> **ERRATA B2**: Caminhos de arquivo corrigidos contra `ssw-option-map.txt`. Opcoes com doc inexistente marcadas `[DOC PENDENTE]`.

| Intencao do usuario | Opcao | Doc SSW | Modulo |
|---------------------|-------|---------|--------|
| cadastrar coleta | 001 | operacional/001-cadastro-coletas.md | Operacional |
| consultar coletas | 002 | operacional/002-consulta-coletas.md | Operacional |
| comandar coletas | 003 | operacional/003-ordem-coleta-gerenciamento.md | Operacional |
| emitir pre-CTRC individual | 004 | operacional/004-emissao-ctrcs.md | Operacional |
| emitir pre-CTRC em lote / CTe-OS | 006 | operacional/006-emissao-cte-os.md | Operacional |
| emitir CTe complementar / enviar SEFAZ | 007 | operacional/007-emissao-cte-complementar.md | Operacional |
| manifesto operacional | 019 | operacional/019-manifesto-operacional.md | Operacional |
| manifesto de carga | 020 | operacional/020-manifesto-carga.md | Operacional |
| saida de veiculo / MDF-e | 025 | operacional/025-saida-veiculos.md | Operacional |
| cadastrar veiculo | 026 | relatorios/026-cadastro-veiculos.md | Cadastro |
| cadastrar motorista | 028 | operacional/028-relacao-motoristas.md | Operacional |
| chegada de veiculo | 030 | operacional/030-chegada-de-veiculo.md | Operacional |
| romaneio de entregas | 035 | operacional/035-romaneio-entregas.md | Operacional |
| controle de entregas | 036 | operacional/036-controle-entregas.md | Operacional |
| baixa de entregas / ocorrencias | 038 | operacional/038-baixa-entregas-ocorrencias.md | Operacional |
| controle comprovantes entrega | 049 | operacional/049-controle-comprovantes.md | Operacional |
| relatorios gerenciais | 056 | relatorios/056-informacoes-gerenciais.md | Gerencial |
| parametros de frete | 062 | comercial/062-parametros-frete.md | Comercial |
| contratacao de veiculo (coleta/entrega) | 071 | operacional/071-contratacao-de-veiculos.md | Operacional |
| contratacao de veiculo (transferencia) | 072 | operacional/072-contratacao-de-veiculo-de-transferencia.md | Operacional |
| controle de contratacao | 073 | operacional/073-controle-de-contratacao.md | Operacional |
| resultado por CTRC | 101 | comercial/101-resultado-ctrc.md | Comercial |
| consulta CTRC / cliente | 102 | comercial/102-consulta-ctrc.md | Comercial |
| cotacao de frete (SSW) | 110 | comercial/110-cotacao-fretes-cliente.md | Comercial |
| instrucoes para ocorrencias de entrega | 108 | operacional/108-ocorrencias-entrega.md | Operacional |
| ocorrencias de CTRCs | 133 | operacional/133-ocorrencias-ctrcs.md | Operacional |
| faturamento por regras (cliente) | 384 | financeiro/384-cadastro-clientes.md | Financeiro |
| escanear comprovantes entregas | 398 | comercial/398-escanear-comprovantes-entregas.md | Comercial |
| unidades | 401 | cadastros/401-cadastro-unidades.md | Cadastro |
| cidades atendidas | 402 | cadastros/402-cidades-atendidas.md | Cadastro |
| rotas | 403 | cadastros/403-rotas.md | Cadastro |
| custos/comissoes unidades | 408 | comercial/408-comissao-unidades.md | Comercial |
| tabelas de frete combinada | 417 | comercial/417-418-420-tabelas-frete.md | Comercial |
| tabela percentual | 418 | comercial/417-418-420-tabelas-frete.md | Comercial |
| tabela por rota | 420 | comercial/417-418-420-tabelas-frete.md | Comercial |
| resultado por cliente | 427 | comercial/427-resultado-por-cliente.md | Comercial |
| pre-faturamento | 435 | financeiro/435-pre-faturamento.md | Financeiro |
| faturamento geral / automatico | 436 | financeiro/436-faturamento-geral.md | Financeiro |
| faturamento manual | 437 | financeiro/437-faturamento-manual.md | Financeiro |
| cobranca bancaria | 444 | financeiro/444-cobranca-bancaria.md | Financeiro |
| manutencao faturas | 457 | financeiro/457-manutencao-faturas.md | Financeiro |
| caixa online | 458 | financeiro/458-caixa-online.md | Financeiro |
| custos extras (TDE, diaria) | 459 | financeiro/459-cadastro-tde.md | Financeiro |
| bloqueio financeiro CTRC | 462 | financeiro/462-bloqueio-financeiro-ctrc.md | Financeiro |
| resultado por unidade (sintetico) | 463 | fiscal/463-resultado-por-unidade-sintetico.md | Fiscal |
| contas a pagar | 475 | financeiro/475-contas-a-pagar.md | Financeiro |
| liquidacao despesas | 476 | financeiro/476-liquidacao-despesas.md | Financeiro |
| cadastro fornecedor | 478 | financeiro/478-cadastro-fornecedores.md | Financeiro |
| cadastrar cliente | 483 | cadastros/483-cadastro-clientes.md | Cadastro |
| conta corrente fornecedor | 486 | financeiro/486-conta-corrente-fornecedor.md | Financeiro |
| SPED Contribuicoes (PIS/COFINS) | 515 | fiscal/515-sped-contribuicoes.md | Fiscal |
| aprovacao de despesas | 560 | fiscal/560-aprovacao-despesas.md | Fiscal |
| conciliacao bancaria | 569 | financeiro/569-conciliacao-bancaria.md | Financeiro |
| grupo de clientes / limites credito | 583 | financeiro/583-grupo-clientes.md | Financeiro |
| EDI — integracao eletronica | 600 | edi/600-edi-integracao-eletronica.md | EDI |
| EDI — geracao/envio automatico | 603 | edi/603-geracao-envio-automatico-edis.md | EDI |
| EDI — envio automatico seguradora | 616 | edi/616-envio-automatico-edis-seguradora.md | EDI |
| parametros RCTR-C (seguro) | 630 | logistica/630-parametros-rctr-c.md | Logistica |
| parametros gerais | 903 | cadastros/903-parametros-gerais.md | Cadastro |

---

## Mapa Intencao → Fluxo (20 Fluxos)

| Intencao do usuario | Fluxo | Secao em FLUXOS_PROCESSO.md |
|---------------------|-------|----------------------------|
| coleta de mercadoria | F01 | OPERACIONAL — F01 Coleta |
| emitir CTe / expedicao | F02 | OPERACIONAL — F02 Expedicao |
| transferencia entre unidades | F03 | OPERACIONAL — F03 Transferencia |
| chegada e descarga | F04 | OPERACIONAL — F04 Chegada |
| entrega ao destinatario | F05 | OPERACIONAL — F05 Entrega |
| faturamento (faturas e cobranca) | F06 | FINANCEIRO — F06 Faturamento |
| liquidacao e cobranca | F07 | FINANCEIRO — F07 Liquidacao |
| contas a pagar (despesas) | F08 | FINANCEIRO — F08 Contas a Pagar |
| conciliacao bancaria | F09 | FINANCEIRO — F09 Conciliacao |
| fechamento fiscal (SPED) | F10 | FISCAL — F10 Fechamento Fiscal |
| fechamento contabil (ECD/ECF) | F11 | CONTABIL — F11 Fechamento Contabil |
| comissionamento de vendedor | F12 | COMERCIAL — F12 Comissionamento |
| contratacao de veiculo | F13 | PARCERIAS — F13 Contratacao |
| remuneracao coleta/entrega (agregados) | F14 | PARCERIAS — F14 Remuneracao |
| manutencao preventiva | F15 | FROTA — F15 Manutencao |
| controle de pneus | F16 | FROTA — F16 Pneus |
| consumo de combustivel | F17 | FROTA — F17 Combustivel |
| emissao RPS/NFS-e | F18 | OUTROS — F18 Municipal |
| gestao de estoque (logistica) | F19 | OUTROS — F19 Estoque |
| embarcador: expedicao | F20 | OUTROS — F20 Embarcador |

---

## Mapa Visao Geral

| Modulo | Arquivo | Quando usar |
|--------|---------|-------------|
| Implantacao | visao-geral/01-implantacao.md | Setup inicial, usuarios, parametros, certificados |
| Operacional | visao-geral/02-operacional.md | Coleta, expedicao, transferencia, entrega |
| Comercial | visao-geral/03-comercial.md | Tabelas, vendedores, cotacao, performance |
| Financeiro | visao-geral/04-financeiro.md | Faturamento, cobranca, caixa, contas a pagar |
| Resultado | visao-geral/05-resultado.md | Lucratividade CTRC, cliente, veiculo |
| Info Gerenciais | visao-geral/06-info-gerenciais.md | 40+ relatorios (opcao 056) |
| Frota | visao-geral/07-frota.md | Veiculos, pneus, manutencao, combustivel |
| Logistica | visao-geral/08-logistica.md | Armazenagem, estoque, NFT |
| Contabilidade | visao-geral/09-contabilidade.md | Plano contas, lancamentos, ECD/ECF |
| Fiscal | visao-geral/10-fiscal.md | SPED, CTe, MDF-e, RPS, tributacao |
| Multiempresa | visao-geral/11-multiempresa.md | Consolidacao, unidades, faturamento grupo |
| Embarcador | visao-geral/12-embarcador.md | CEE, SSWBar, mapa fretes |

---

## Arvores de Decisao — Cenarios Ambiguos

### 1. "Emitir documento fiscal"

```
O que deseja emitir?
    |
    ├── CT-e individual → Opcao 004 (POP-C01 fracionado ou POP-C02 carga direta)
    ├── CT-e em lote → Opcao 006
    ├── Enviar ao SEFAZ → Opcao 007
    ├── CT-e complementar → Opcao 007 funcao complementar (POP-C03)
    ├── RPS municipal → Opcao 009 (F18)
    ├── MDF-e → Opcao 020+025 (POP-D03)
    └── NFS-e → Opcao 009 [DOC PENDENTE: 014] (F18)
```

### 2. "Faturar"

```
Tipo de faturamento?
    |
    ├── "ver o que esta disponivel para faturar" → Opcao 435 (POP-E01)
    ├── "faturar manualmente / selecionar CTRCs" → Opcao 437 (POP-E02)
    ├── "faturar automaticamente / em lote" → Opcao 436 (POP-E03)
    └── "manter fatura existente / prorrogar / protestar" → Opcao 457 (POP-E06)
```

### 3. "Registrar algo em estoque"

```
Contexto?
    |
    ├── Descarga operacional (transferencia chegou) → Opcao 030 (F04) [DOC PENDENTE: 264]
    ├── Logistica / armazenagem (mercadoria de cliente) → Opcao 701 entrada (F19)
    └── Saida de mercadoria armazenada → Opcao 702 saida (F19)
```

### 4. "Opcao 020"

```
Qual funcao da opcao 020?
    |
    ├── Criar manifesto operacional (para transferencia entre unidades) → operacional/020-manifesto-carga.md
    └── NOTA: opcao 020 NAO e resultado financeiro. Resultado = opcao 101
```

### 5. "Opcao 056 / Relatorio"

```
Qual relatorio?
    |
    ├── Situacao geral (CTRCs, entregas, coletas) → 056 objetivo 1
    ├── Rastreamento de CTe (por periodo/cliente) → 056 objetivo 2
    ├── Performance de entregas → 056 objetivo 3
    ├── Faturamento / financeiro → 056 objetivo 4
    ├── Resultado / lucratividade → 056 objetivo 5
    ├── Frota / combustivel / manutencao → 056 objetivo 6
    └── Se nao sabe qual: consultar visao-geral/06-info-gerenciais.md
```

### 6. "Cadastrar cliente"

```
O que precisa?
    |
    ├── Dados cadastrais (CNPJ, endereco, contato) → Opcao 483 (POP-A01 parte 1)
    ├── Parametros de faturamento (tipo, prazo, banco) → Opcao 384 (POP-A01 parte 2)
    ├── Parametros comerciais (tabela, vendedor) → Opcao 423
    ├── Consultar dados do cliente → Opcao 102
    └── Limites de credito → Opcao 389 (individual) ou 583 (grupo)
```

### 7. "Consultar dados" (NOVO)

```
Que tipo de dado quer consultar?
    |
    ├── CTRC / conhecimento de transporte
    |       ├── Dados do CTRC (remetente, destinatario, valores) → Opcao 102 (comercial/102-consulta-ctrc.md)
    |       ├── Resultado/lucratividade do CTRC → Opcao 101 (comercial/101-resultado-ctrc.md)
    |       ├── Ocorrencias do CTRC (atraso, avaria, etc.) → Opcao 133 (operacional/133-ocorrencias-ctrcs.md)
    |       └── Rastreamento (onde esta a mercadoria) → Opcao 125 (comercial/125-rastreamento-produtos.md)
    |
    ├── Cliente
    |       ├── Dados cadastrais → Opcao 483 (cadastros/483-cadastro-clientes.md)
    |       ├── Situacao financeira / credito → Opcao 389 (comercial/389-cadastro-clientes-credito.md)
    |       ├── Resultado por cliente → Opcao 427 (comercial/427-resultado-por-cliente.md)
    |       ├── Parametros comerciais → Opcao 423 (comercial/423-parametros-comerciais-cliente.md)
    |       └── Historico de ocorrencias → Opcao 119 (comercial/119-cadastro-clientes-ocorrencias.md)
    |
    ├── Veiculo / motorista
    |       ├── Dados do veiculo → Opcao 026 (relatorios/026-cadastro-veiculos.md)
    |       ├── Relacao de proprietarios → Opcao 027 (operacional/027-relacao-proprietarios-veiculos.md)
    |       ├── Relacao de motoristas → Opcao 028 (operacional/028-relacao-motoristas.md)
    |       └── Contratacoes do veiculo → Opcao 073 (operacional/073-controle-de-contratacao.md)
    |
    ├── Coleta
    |       ├── Consultar coletas existentes → Opcao 002 (operacional/002-consulta-coletas.md)
    |       └── Gerenciar/comandar coletas → Opcao 003 (operacional/003-ordem-coleta-gerenciamento.md)
    |
    ├── Fornecedor / transportadora
    |       ├── Dados cadastrais → Opcao 478 (financeiro/478-cadastro-fornecedores.md)
    |       ├── Conta corrente → Opcao 486 (financeiro/486-conta-corrente-fornecedor.md)
    |       └── Localizacao de fornecedores → Opcao 154 (comercial/154-localizacao-fornecedores.md)
    |
    └── Consulta rapida (busca generica) → Opcao 053 (operacional/053-consulta-rapida.md)
```

### 8. "Integracoes EDI" (NOVO)

```
Qual aspecto de EDI?
    |
    ├── "O que e EDI no SSW?" / visao geral
    |       → Opcao 600 (edi/600-edi-integracao-eletronica.md)
    |       Cobre: NOTFIS, OCOREN, DOCCOB, CONEMB, CTe-XML, etc.
    |
    ├── "Gerar/enviar arquivos EDI automaticamente"
    |       → Opcao 603 (edi/603-geracao-envio-automatico-edis.md)
    |       Geracao em lote + envio programado para clientes
    |
    ├── "Enviar EDI para seguradora / RCTR-C"
    |       → Opcao 616 (edi/616-envio-automatico-edis-seguradora.md)
    |       Averbacao de carga para seguradora
    |
    ├── "Cadastrar planos de manutencao (EDI frota)"
    |       → Opcao 614 (edi/614-cadastro-planos-manutencao.md)
    |
    ├── "EDI fiscal / manifesto eletronico"
    |       → Opcao 178 (comercial/178-edi-fiscal-mt.md)
    |
    ├── "Controle de uploads EDI"
    |       → Opcao 942 (relatorios/942-controle-upload-ajudas-edi.md)
    |
    └── "Parametros de seguro / RCTR-C"
            → Opcao 630 (logistica/630-parametros-rctr-c.md)
            Configuracao base para averbacao via EDI 616
```

### 9. "Gerar relatorio" (NOVO)

```
Qual tipo de relatorio?
    |
    ├── Relatorios gerenciais diarios (056) — PAINEL CENTRAL
    |       |
    |       ├── Objetivo 1: Situacao geral / lucro
    |       |       → Rels 001, 075, 050-061, 069-070, 100, 150-153
    |       |
    |       ├── Objetivo 2: Entregas no prazo
    |       |       → Rels 010-013, 080-088, 164
    |       |
    |       ├── Objetivo 3: CTRC/cliente com lucro
    |       |       → Rels 030-032, 130
    |       |
    |       ├── Objetivo 4: Caminhao com lucro
    |       |       → Rels 020-023
    |       |
    |       ├── Objetivo 5: Unidade com lucro
    |       |       → Rels 166-168
    |       |
    |       ├── Objetivo 6: Inadimplencia
    |       |       → Rels 040-041, 154-157
    |       |
    |       └── Nao sabe qual objetivo → visao-geral/06-info-gerenciais.md
    |               (indice completo com 60+ relatorios)
    |
    ├── Relatorio de resultado / lucratividade
    |       ├── Por CTRC → Opcao 101 (comercial/101-resultado-ctrc.md)
    |       ├── Por cliente → Opcao 427 (comercial/427-resultado-por-cliente.md)
    |       ├── Por unidade (sintetico) → Opcao 463 (fiscal/463-resultado-por-unidade-sintetico.md)
    |       └── Por unidade (analitico) → Opcao 464 (fiscal/464-resultado-por-unidade-analitico.md)
    |
    ├── Relatorio de liquidacao / financeiro
    |       ├── Liquidacao detalhado → Opcao 455 (financeiro/455-relatorio-liquidacao-detalhado.md)
    |       ├── Conta corrente cliente → Opcao 456 (financeiro/456-conta-corrente.md)
    |       └── Planilhas conferencia contabil → Opcao 526 (fiscal/526-planilhas-conferencia-contabil.md)
    |
    ├── Relatorio de frota / manutencao
    |       ├── Check-list manutencao → Opcao 314 (relatorios/314-check-list-manutencao.md)
    |       ├── Movimentacao de pneus → Opcao 316 (relatorios/316-movimentacao-pneus.md)
    |       ├── Abastecimento interno → Opcao 320 (relatorios/320-abastecimento-interno.md)
    |       └── Ordens de servico → Opcao 131 (relatorios/131-ordens-servico.md)
    |
    ├── Relatorio fiscal / contabil
    |       ├── SPED Fiscal ICMS/IPI → Opcao 512 (fiscal/512-sped-fiscal-icms-ipi.md)
    |       ├── SPED EFD-Reinf → Opcao 587 (financeiro/587-gerar-sped-efd-reinf.md)
    |       ├── ECD (escrituracao contabil) → Opcao 534 (fiscal/534-ecd-escrituracao-contabil-digital.md)
    |       ├── ECF (escrituracao fiscal) → Opcao 570 (contabilidade/570-ecf-escrituracao-contabil-fiscal.md)
    |       ├── DIRF → Opcao 590 (financeiro/590-gerar-arquivo-dirf.md)
    |       └── Livros auxiliares → Opcao 556 (fiscal/556-livros-auxiliares.md)
    |
    ├── Fila de processamento de relatorios → Opcao 156 (comercial/156-fila-processamento-relatorios.md)
    |       (consultar status quando relatorio demora)
    |
    └── Configuracoes de relatorios / sistema → Opcao 908 (relatorios/908-configuracoes-sistema.md)
```

### 10. "Controlar entregas" (NOVO)

```
Qual aspecto da entrega?
    |
    ├── ANTES da entrega (planejamento)
    |       ├── Criar romaneio de entregas → Opcao 035 (POP-D02)
    |       ├── Agendamento de entregas → Opcao 015 (operacional/015-agendamento-entregas.md)
    |       ├── Previsao de entrega por cliente → Opcao 696 (logistica/696-previsao-entrega-cliente.md)
    |       └── Previsao de entrega detalhada → Opcao 697 (logistica/697-previsao-entrega-por-cliente.md)
    |
    ├── DURANTE a entrega (acompanhamento)
    |       ├── Controle de entregas em andamento → Opcao 036 (operacional/036-controle-entregas.md)
    |       ├── Acompanhamento geral → Opcao 039 (operacional/039-acompanhamento.md)
    |       └── Rastreamento de produtos → Opcao 125 (comercial/125-rastreamento-produtos.md)
    |
    ├── APOS a entrega (baixa e comprovantes)
    |       ├── Registrar baixa de entrega → Opcao 038 (POP-D05)
    |       ├── Escanear comprovantes (canhoto) → Opcao 398 (comercial/398-escanear-comprovantes-entregas.md)
    |       ├── Controle de comprovantes → Opcao 049 (operacional/049-controle-comprovantes.md) (POP-D07)
    |       └── Estornar baixa de entrega → Opcao 138 (comercial/138-estorno-baixa-entrega.md)
    |
    ├── PROBLEMAS (ocorrencias)
    |       ├── Registrar ocorrencia (atraso, avaria, extravio) → Opcao 133 (POP-D06)
    |       ├── Cobranca de estadia/entrega → Opcao 523 (fiscal/523-cobranca-estadia-entrega.md)
    |       └── Consultar/reimprimir romaneios → Opcao 236 (comercial/236-consulta-reimpressao-romaneios-entrega.md)
    |
    └── RELATORIOS de entrega
            └── Opcao 056, Objetivo 2 — performance entregas (rels 010-013, 080-088)
                Ver visao-geral/06-info-gerenciais.md secao Objetivo 2
```

---

## Glossario de Diretorios

| Diretorio | Conteudo |
|-----------|----------|
| `pops/` | 45 POPs (procedimentos passo-a-passo) |
| `visao-geral/` | 12 documentos de visao geral por modulo |
| `operacional/` | 47 docs de opcoes operacionais |
| `comercial/` | 72 docs de opcoes comerciais |
| `financeiro/` | 27 docs de opcoes financeiras |
| `fiscal/` | 22 docs de opcoes fiscais |
| `cadastros/` | 13 docs de opcoes de cadastro |
| `logistica/` | 14 docs de opcoes de logistica |
| `contabilidade/` | 6 docs de opcoes contabeis |
| `edi/` | 4 docs de integracoes EDI |
| `embarcador/` | 4 docs de embarcador |
| `relatorios/` | 12 docs de relatorios |

---

## Opcoes Conhecidas SEM Documentacao

| Opcao | Nome provavel | Referenciada em | Prioridade |
|-------|--------------|-----------------|------------|
| **014** | Impressao NFS-e (complementar a 009) | Arvore 1 "Emitir documento fiscal" | MEDIA |
| **264** | Descarga operacional | Arvore 3 "Registrar algo em estoque" | MEDIA |
| **428** | Controle Comprovantes Entrega | POP-D07, referenciado em 3 docs | BAIXA |
| **431** | Relacionado a CTRCs | url-map.json (3 paginas) | BAIXA |
| **433** | — | url-map.json (1 pagina) | BAIXA |
| **469** | Resultados Minimos | INDEX.md, POP-B03, 5+ docs | MEDIA |
| **518** | Aprovacao de Tabelas | INDEX.md, 10 paginas ajuda | MEDIA |

> **Nota**: Estas opcoes tem paginas de ajuda no SSW (ver url-map.json) mas ainda nao foram convertidas em docs .md.
>
> **Correcao B2**: Opcao 390 REMOVIDA desta lista — doc existe em `comercial/390-cadastro-especies-mercadorias.md` (e cadastro de especies de mercadorias, NAO PGR). Opcao 503 REMOVIDA — doc existe em `fiscal/503-manutencao-de-eventos.md`. Opcoes 014 e 264 ADICIONADAS (referenciadas em decision trees sem doc).
>
> **Correcao B3**: 6 opcoes REMOVIDAS desta lista — docs criados: 062 (`comercial/062-parametros-frete.md`), 108 (`operacional/108-ocorrencias-entrega.md`), 437 (`financeiro/437-faturamento-manual.md`), 459 (`financeiro/459-cadastro-tde.md`), 462 (`financeiro/462-bloqueio-financeiro-ctrc.md`), 515 (`fiscal/515-sped-contribuicoes.md`).

---

## Errata B2 — Correcoes no Top 50 (ex-Top 40)

Caminhos de arquivo corrigidos em relacao a versao anterior:

| Opcao | Antes (INCORRETO) | Agora (CORRETO) |
|-------|--------------------|-----------------|
| 002 | `comercial/002-cotacao-de-frete.md` | `operacional/002-consulta-coletas.md` (cotacao e opcao 110) |
| 003 | `operacional/003-gerenciamento-coletas.md` | `operacional/003-ordem-coleta-gerenciamento.md` |
| 006 | `operacional/006-emissao-ctrcs-lote.md` | `operacional/006-emissao-cte-os.md` |
| 007 | `operacional/007-emissao-cte.md` | `operacional/007-emissao-cte-complementar.md` |
| 025 | `operacional/025-saida-veiculo.md` | `operacional/025-saida-veiculos.md` |
| 026 | `operacional/026-cadastro-veiculos.md` | `relatorios/026-cadastro-veiculos.md` |
| 028 | `operacional/028-cadastro-motoristas.md` | `operacional/028-relacao-motoristas.md` |
| 030 | `operacional/030-chegada-veiculo.md` | `operacional/030-chegada-de-veiculo.md` |
| 038 | `operacional/038-baixa-entregas.md` | `operacional/038-baixa-entregas-ocorrencias.md` |
| 056 | `visao-geral/06-info-gerenciais.md` | `relatorios/056-informacoes-gerenciais.md` |
| 384 | `comercial/384-faturamento-cliente.md` | `financeiro/384-cadastro-clientes.md` |
| 408 | `comercial/408-custos-resultado-ctrc.md` | `comercial/408-comissao-unidades.md` |
| 458 | `financeiro/458-financeiro-caixa.md` | `financeiro/458-caixa-online.md` |
| 459 | `financeiro/459-relacao-adicionais.md` | `financeiro/459-cadastro-tde.md` (criado B3) |
| 478 | `financeiro/478-dados-fornecedor.md` | `financeiro/478-cadastro-fornecedores.md` |
| 569 | `contabilidade/569-conciliacao-bancaria.md` | `financeiro/569-conciliacao-bancaria.md` |

---

## Referencia Rapida — Documentos Transversais

| Documento | Quando usar |
|-----------|-------------|
| INDEX.md | Ponto de entrada — indice completo de toda documentacao |
| CARVIA_OPERACAO.md | Perfil da empresa, equipe, clientes, gaps, fluxo atual |
| CARVIA_STATUS.md | Status de adocao de cada POP pela CarVia |
| CATALOGO_POPS.md | Definicao dos 45 POPs (categorias, prioridades, ondas) |
| FLUXOS_PROCESSO.md | 20 fluxos end-to-end com diagramas e dependencias |
| MAPA_MENU.md | Mapeamento completo dos 26 modulos do menu SSW |
| url-map.json | Mapeamento programatico opcao→URLs de ajuda |
