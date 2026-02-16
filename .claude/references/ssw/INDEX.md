# SSW Sistemas — Indice de Documentacao

> **Fonte**: Paginas de ajuda do SSW (`sistema.ssw.inf.br/ajuda/`)
> **Coletado em**: 2026-02-14 | **Atualizado**: 2026-02-16
> **Dominio Nacom**: CV1 (CARVIA LOGISTICA E TRANSPORTE LTDA)
> **Cobertura**: 220 opcoes documentadas, 228 arquivos .md, 20 fluxos end-to-end

## Visao Geral do SSW

O SSW e um sistema integrado para transportadoras que cobre: operacional, comercial, financeiro, fiscal, contabil, frota, logistica e embarcador. Opera de forma 100% online, onde todos os processos sao atualizados em tempo real.

### Principio Fundamental

> "Tudo tem que dar LUCRO" — aplicado em todas as dimensoes: CTRC, cliente, caminhao, unidade e transportadora.

---

## Documentos Transversais

| Documento | Descricao |
|-----------|-----------|
| [CARVIA_OPERACAO.md](CARVIA_OPERACAO.md) | Operacao CarVia: perfil, equipe, clientes, fluxo operacional, gaps, mapa processo→SSW |
| [CARVIA_STATUS.md](CARVIA_STATUS.md) | Status de adocao de cada POP pela CarVia (ATIVO/PARCIAL/NAO IMPLANTADO) |
| [CATALOGO_POPS.md](CATALOGO_POPS.md) | 45 POPs definidos em 7 categorias, priorizados em 5 ondas de escrita |
| [FLUXOS_PROCESSO.md](FLUXOS_PROCESSO.md) | 20 fluxos end-to-end (F01-F20): Coleta → Entrega → Faturamento → Fiscal → Contabil + Frota + Logistica + Embarcador |
| [MAPA_MENU.md](MAPA_MENU.md) | Mapeamento completo dos 26 modulos do menu SSW |
| [ROUTING_SSW.md](ROUTING_SSW.md) | Decision tree: intencao do usuario → documento correto (POPs, opcoes, fluxos) |
| [VERIFICACOES_PENDENTES.md](VERIFICACOES_PENDENTES.md) | Checklist de 42 marcadores [CONFIRMAR] para verificacao via Playwright no SSW |
| [url-map.json](url-map.json) | Mapeamento opcao → URL de ajuda (220 opcoes, 1044 paginas) |

---

## Mapa de Documentacao

### Visao Geral (12 secoes)

| # | Secao | Arquivo | Opcoes Chave | Links |
|---|-------|---------|--------------|-------|
| 01 | Implantacao | [visao-geral/01-implantacao.md](visao-geral/01-implantacao.md) | 925, 918, 401, 402, 403, 904, 903, 483, 417, 418, 420 | 106 |
| 02 | Operacional | [visao-geral/02-operacional.md](visao-geral/02-operacional.md) | 001, 003, 004, 006, 007, 020, 025, 030, 035, 038 | 107 |
| 03 | Comercial | [visao-geral/03-comercial.md](visao-geral/03-comercial.md) | 483, 417, 418, 420, 923, 427, 415, 056 | 44 |
| 04 | Financeiro | [visao-geral/04-financeiro.md](visao-geral/04-financeiro.md) | 436, 048, 444, 475, 486, 458, 569 | 15 |
| 05 | Resultado | [visao-geral/05-resultado.md](visao-geral/05-resultado.md) | 101, 102, 449, 056, 072, 408, 469, 463, 464 | 30 |
| 06 | Info Gerenciais (056) | [visao-geral/06-info-gerenciais.md](visao-geral/06-info-gerenciais.md) | 056 (40+ relatorios) | 98 |
| 07 | Frota | [visao-geral/07-frota.md](visao-geral/07-frota.md) | 026, 131, 313, 314, 315, 316, 317, 475, 320 | 50 |
| 08 | Logistica | [visao-geral/08-logistica.md](visao-geral/08-logistica.md) | 701, 702, 703, 707, 724, 721, 722, 741 | 24 |
| 09 | Contabilidade | [visao-geral/09-contabilidade.md](visao-geral/09-contabilidade.md) | 540, 541, 526, 558, 559, 534, 570 | 40 |
| 10 | Fiscal | [visao-geral/10-fiscal.md](visao-geral/10-fiscal.md) | 007, 009, 014, 512, 515, 567, 903/Certificado | 55 |
| 11 | Multiempresa | [visao-geral/11-multiempresa.md](visao-geral/11-multiempresa.md) | 401, 436, 475, 476, 559, 567 | 60 |
| 12 | Embarcador | [visao-geral/12-embarcador.md](visao-geral/12-embarcador.md) | 401, 402, 403, 417, 418, 056 | 36 |

### Opcoes Documentadas (220 opcoes em 11 diretorios)

| Diretorio | Docs | Exemplos |
|-----------|------|----------|
| `operacional/` | 46 | 001-cadastro-coletas, 004-emissao-ctrcs, 035-romaneio-entregas |
| `comercial/` | 71 | 102-consulta-ctrc, 417-418-420-tabelas-frete, 923-tabelas-ntc |
| `financeiro/` | 24 | 436-faturamento-geral, 475-contas-a-pagar, 486-conta-corrente-fornecedor |
| `fiscal/` | 21 | 512-sped-fiscal, 534-ecd, 560-aprovacao-despesas |
| `cadastros/` | 13 | 401-cadastro-unidades, 483-cadastro-clientes, 903-parametros-gerais |
| `logistica/` | 14 | 701-entrada-estoque, 702-saida-estoque, 741-cadastro-mercadorias |
| `contabilidade/` | 6 | 540-plano-contas, 558-lancamentos-manuais, 569-conciliacao-bancaria |
| `edi/` | 4 | 600-edi-integracao, 614-cadastro-planos-manutencao |
| `embarcador/` | 4 | 804-ctrcs-aquaviario, 835-ajustar-previsao-entrega |
| `relatorios/` | 12 | 056-informacoes-gerenciais, 131-ordens-servico, 314-check-list |

### Proximos Passos

| Fase | Status |
|------|--------|
| Fase 5A — Conhecimento CarVia | Completo — CARVIA_OPERACAO.md |
| Fase 5B — Catalogo de POPs | Completo — CATALOGO_POPS.md (45 POPs, 5 ondas) |
| Fase 5C — Escrita dos POPs | **COMPLETA** — 45/45 POPs escritos (Ondas 1-5) |

### POPs Escritos (Onda 1 — Urgente/Risco Legal)

| POP | Arquivo | Descricao |
|-----|---------|-----------|
| G01 | [pops/POP-G01-sequencia-legal-obrigatoria.md](pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia inviolavel para carga direta (7 etapas) |
| D03 | [pops/POP-D03-manifesto-mdfe.md](pops/POP-D03-manifesto-mdfe.md) | Criar manifesto e emitir MDF-e (obrigatorio interestadual) |
| G02 | [pops/POP-G02-checklist-gerenciadora-risco.md](pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist de aprovacao na gerenciadora de risco |
| C01 | [pops/POP-C01-emitir-cte-fracionado.md](pops/POP-C01-emitir-cte-fracionado.md) | Emitir CT-e para frete fracionado (placa ARMAZEM) |
| C02 | [pops/POP-C02-emitir-cte-carga-direta.md](pops/POP-C02-emitir-cte-carga-direta.md) | Emitir CT-e para carga direta (placa real) |
| D02 | [pops/POP-D02-romaneio-entregas.md](pops/POP-D02-romaneio-entregas.md) | Criar romaneio de entregas (pre-requisito do MDF-e) |

### POPs Escritos (Onda 2 — Operacao Financeira)

| POP | Arquivo | Descricao |
|-----|---------|-----------|
| E02 | [pops/POP-E02-faturar-manualmente.md](pops/POP-E02-faturar-manualmente.md) | Faturar manualmente (opcao 437, processo atual) |
| E01 | [pops/POP-E01-pre-faturamento.md](pops/POP-E01-pre-faturamento.md) | Verificar CTRCs disponiveis antes de faturar (opcao 435) |
| E05 | [pops/POP-E05-liquidar-fatura.md](pops/POP-E05-liquidar-fatura.md) | Liquidar/baixar fatura recebida (opcoes 048, 457, 458) |
| F01 | [pops/POP-F01-contas-a-pagar.md](pops/POP-F01-contas-a-pagar.md) | Lancar contas a pagar — despesas e transportadoras (opcao 475) |
| F02 | [pops/POP-F02-ccf-conta-corrente-fornecedor.md](pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Gerenciar CCF — saldo com fornecedores (opcao 486) |
| F03 | [pops/POP-F03-liquidar-despesa.md](pops/POP-F03-liquidar-despesa.md) | Liquidar/pagar despesa programada (opcao 476) |
| D01 | [pops/POP-D01-contratar-veiculo.md](pops/POP-D01-contratar-veiculo.md) | Contratar veiculo para carga direta — CTRB, CIOT, Vale Pedagio (opcao 072) |

### POPs Escritos (Onda 3 — Cadastros e Comercial)

| POP | Arquivo | Descricao |
|-----|---------|-----------|
| A10 | [pops/POP-A10-implantar-nova-rota.md](pops/POP-A10-implantar-nova-rota.md) | Implantar rota completa — processo composto 8 etapas (401→402→403→478→408→420→002) |
| A01 | [pops/POP-A01-cadastrar-cliente.md](pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente novo (opcao 483 + 384 faturamento) |
| A02 | [pops/POP-A02-cadastrar-unidade-parceira.md](pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira tipo T (opcao 401, CNPJ/conta da CarVia) |
| A05 | [pops/POP-A05-cadastrar-fornecedor.md](pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor/transportadora (opcao 478, CCF obrigatoria) |
| A06 | [pops/POP-A06-cadastrar-custos-comissoes.md](pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos subcontratacao (opcao 408, espelho Sistema Fretes) |
| B01 | [pops/POP-B01-cotar-frete.md](pops/POP-B01-cotar-frete.md) | Cotar frete para cliente (opcao 002, transicao Rafael→Jessica) |
| B02 | [pops/POP-B02-formacao-preco.md](pops/POP-B02-formacao-preco.md) | Entender formacao de preco — 22 parcelas, formula e diagnostico |
| B03 | [pops/POP-B03-parametros-frete.md](pops/POP-B03-parametros-frete.md) | Configurar parametros de frete (903, 469, 423, 062 [CONFIRMAR]) |

### POPs Escritos (Onda 4 — Controle e Gestao)

| POP | Arquivo | Descricao |
|-----|---------|-----------|
| D04 | [pops/POP-D04-chegada-veiculo.md](pops/POP-D04-chegada-veiculo.md) | Registrar chegada de veiculo (opcao 030, A IMPLANTAR — transferencias) |
| D05 | [pops/POP-D05-baixa-entrega.md](pops/POP-D05-baixa-entrega.md) | Registrar baixa de entrega (opcao 038, fecha ciclo operacional) |
| D06 | [pops/POP-D06-registrar-ocorrencias.md](pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias (opcoes 033/038/108, rastreabilidade) |
| D07 | [pops/POP-D07-comprovantes-entrega.md](pops/POP-D07-comprovantes-entrega.md) | Controlar comprovantes de entrega (opcoes 040/049/428, prova juridica) |
| A08 | [pops/POP-A08-cadastrar-veiculo.md](pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo (opcao 026, quando houver frota propria/agregados) |
| A09 | [pops/POP-A09-cadastrar-motorista.md](pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista (opcao 028, cargas diretas com terceiros) |
| B04 | [pops/POP-B04-resultado-ctrc.md](pops/POP-B04-resultado-ctrc.md) | Analisar resultado por CTRC (opcao 101, "CTRC tem que dar LUCRO") |
| B05 | [pops/POP-B05-relatorios-gerenciais.md](pops/POP-B05-relatorios-gerenciais.md) | Gerar relatorios gerenciais (opcao 056, 6 objetivos, 40+ relatorios) |
| E04 | [pops/POP-E04-cobranca-bancaria.md](pops/POP-E04-cobranca-bancaria.md) | Emitir cobranca bancaria — remessa CNAB (443) e retorno (444) |
| F04 | [pops/POP-F04-conciliacao-bancaria.md](pops/POP-F04-conciliacao-bancaria.md) | Conciliar banco (opcao 569, obrigatorio para contabilidade SSW) |

### POPs Escritos (Onda 5 — Complementares)

| POP | Arquivo | Descricao |
|-----|---------|-----------|
| C03 | [pops/POP-C03-emitir-cte-complementar.md](pops/POP-C03-emitir-cte-complementar.md) | Emitir CT-e complementar (opcao 007, diferenca de frete/ICMS/peso) |
| C04 | [pops/POP-C04-custos-extras.md](pops/POP-C04-custos-extras.md) | Registrar custos extras — TDE, diaria, pernoite (opcao 459) |
| C05 | [pops/POP-C05-imprimir-cte.md](pops/POP-C05-imprimir-cte.md) | Imprimir/reimprimir DACTe (opcao 007) |
| C06 | [pops/POP-C06-cancelar-cte.md](pops/POP-C06-cancelar-cte.md) | Cancelar CT-e (opcao 007, prazo SEFAZ 7 dias) |
| C07 | [pops/POP-C07-carta-correcao-cte.md](pops/POP-C07-carta-correcao-cte.md) | Carta de correcao CT-e (opcao 007, nao altera valores/CNPJ) |
| A03 | [pops/POP-A03-cadastrar-cidades.md](pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades atendidas (opcao 402, polos P/R/I) |
| A04 | [pops/POP-A04-cadastrar-rotas.md](pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas (opcao 403, distancia e UFs percurso) |
| A07 | [pops/POP-A07-cadastrar-tabelas-preco.md](pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas de preco por rota (opcao 420, CARP-[SIGLA][POLO]) |
| E03 | [pops/POP-E03-faturamento-automatico.md](pops/POP-E03-faturamento-automatico.md) | Faturar automaticamente (opcao 436, agrupa por regras 384) |
| E06 | [pops/POP-E06-manutencao-faturas.md](pops/POP-E06-manutencao-faturas.md) | Manter faturas — prorrogar, protestar, baixar (opcao 457) |
| F05 | [pops/POP-F05-bloqueio-financeiro-ctrc.md](pops/POP-F05-bloqueio-financeiro-ctrc.md) | Registrar bloqueio financeiro de CTRC (opcao 462) |
| F06 | [pops/POP-F06-aprovar-despesas.md](pops/POP-F06-aprovar-despesas.md) | Aprovar despesas pendentes (opcao 560) |
| G03 | [pops/POP-G03-custos-frota.md](pops/POP-G03-custos-frota.md) | Controlar custos de frota — abastecimento, manutencao, OS (026/320/131/475) |
| G04 | [pops/POP-G04-relatorios-contabilidade.md](pops/POP-G04-relatorios-contabilidade.md) | Extrair relatorios para contabilidade — SPED Fiscal/Contribuicoes (512/515/567) |

---

## Glossario SSW

| Termo | Significado |
|-------|-------------|
| **CTRC** | Conhecimento de Transporte Rodoviario de Cargas (= CT-e apos autorizacao SEFAZ) |
| **CT-e** | Conhecimento de Transporte Eletronico (documento fiscal autorizado) |
| **MDF-e** | Manifesto Eletronico de Documentos Fiscais |
| **CEE** | Controle de Expedicao do Embarcador |
| **RPS** | Recibo Provisorio de Servico (municipal) |
| **NFS-e** | Nota Fiscal de Servico Eletronica |
| **CTRB** | Conhecimento de Transporte (para terceiros/carreteiros) |
| **CCF** | Conta Corrente do Fornecedor (opção 486) |
| **PEF** | Pagamento Eletronico de Fretes |
| **CIOT** | Codigo Identificador da Operacao de Transporte |
| **TAC** | Transportador Autonomo de Cargas |
| **Manifesto Operacional** | Documento interno de transferencia entre unidades |
| **Romaneio** | Documento de carregamento para entrega ao destinatario |
| **Unidade MTZ** | Unidade Matriz (ve dados consolidados de todas unidades) |
| **SSWBar** | Modulo de codigo de barras para identificacao/carregamento de volumes |
| **SSWMobile** | App para celular do motorista (rastreamento, coletas, entregas) |
| **SSWScan** | Modulo de escaneamento de comprovantes de entrega |
| **Opcao NNN** | Tela/funcionalidade do SSW identificada por numero (ex: opção 401 = Cadastro de Unidades) |

---

## Fluxo Operacional Principal

```
COLETA (001/003) → EXPEDIÇÃO (004/006/007) → TRANSFERÊNCIA (020/025)
                                                      ↓
ENTREGA (035/038) ← CHEGADA (030/033) ← ← ← ← ← ← ←
     ↓
FATURAMENTO (436) → COBRANÇA (444) → LIQUIDAÇÃO (048/458)
     ↓
CONTAS A PAGAR (475) → CCF (486) → CONCILIAÇÃO (569)
     ↓
FISCAL (007/512/515) → CONTABILIDADE (540/558/559) → ECD/ECF (534/570)
```

---

## Mapa de Opcoes Referenciadas

> Opcoes frequentes organizadas por modulo. Numero = tela no SSW.

### Cadastros
- **401** — Cadastro de Unidades (matriz, filiais, parceiros)
- **402** — Cidades Atendidas (vinculo cidade ↔ unidade)
- **403** — Rotas (distancias, prazos entre unidades)
- **404** — Setores de Coleta/Entrega (faixas de CEP)
- **405** — Tabela de Ocorrencias
- **406** — Tipos de Mercadorias
- **407** — Especies de Mercadorias
- **483** — Cadastro de Clientes
- **903** — Parametros Gerais
- **904** — Bancos / Contas Bancarias
- **918** — Grupos de Usuarios (cargo/funcao)
- **925** — Cadastro de Usuarios

### Operacional
- **001** — Cadastro de Coletas
- **003** — Ordem de Coleta / Gerenciamento
- **004** — Emissao de Pre-CTRC individual
- **006** — Emissao de Pre-CTRC em lote
- **007** — Envio CT-e ao SEFAZ
- **009** — Impressao de RPS
- **014** — Envio RPS a Prefeitura
- **019** — Planejamento de Carregamento
- **020** — Manifesto Operacional (transferencia)
- **022** — Acompanhamento descarga online
- **025** — Saida de Veiculo
- **026** — Cadastro de Veiculos
- **028** — Cadastro de Motoristas
- **030** — Chegada de Veiculo
- **033** — Ocorrencias de Transferencia
- **035** — Romaneio de Entregas
- **038** — Baixa de Entregas / Ocorrencias
- **040** — Capear Comprovantes de Entrega
- **072** — Contratacao de Veiculo de Transferencia
- **108** — Resolver Ocorrencias/Pendencias

### Comercial
- **102** — Consulta/Situacao do Cliente
- **106** — Performance de Entregas por Cliente
- **119** — Relatorios de Visitas
- **397** — Metas de Vendas
- **415** — Comissionamento de Vendedor
- **417** — Tabela Combinada (peso + valor)
- **418** — Tabela Percentual (valor)
- **420** — Tabela por Rota
- **427** — Tabela Generica NTC
- **469** — Resultados Minimos
- **518** — Aprovacao de Tabelas
- **923** — Tabela Generica

### Financeiro
- **048** — Liquidacao a Vista
- **436** — Faturamento Geral
- **444** — Cobranca Bancaria
- **458** — Financeiro/Caixa
- **475** — Contas a Pagar (despesas)
- **486** — Conta Corrente do Fornecedor (CCF)
- **569** — Conciliacao Bancaria

### Fiscal
- **410** — Tributacao ICMS
- **512** — SPED Fiscal (ICMS/IPI)
- **515** — SPED Contribuicoes (PIS/COFINS)
- **520** — Anulacao/Complemento de Frete
- **567** — Fechamento Fiscal
- **903/Certificado** — Certificado Digital A1

### Contabilidade
- **540** — Plano de Contas
- **541** — Lancamentos Automaticos
- **558** — Lancamentos Manuais
- **559** — Saldo das Contas / Fechamento Contabil
- **534** — ECD (Escrituracao Contabil Digital)
- **570** — ECF (Escrituracao Contabil-Fiscal)

### Informacoes Gerenciais
- **056** — Relatorios Diarios (6 objetivos, 40+ relatorios)
- **300** — Liberacao de Relatorios

### Frota
- **131** — Ordens de Servico (agenda da equipe)
- **313** — Cadastro de Pneus
- **314** — Check-list de Manutencao
- **315** — Vinculacao Check-list ↔ Veiculo
- **316** — Movimentacao de Pneus
- **317** — Vida do Pneu
- **320** — Abastecimento Interno

### Logistica
- **701** — Entrada no Estoque
- **702** — Saida do Estoque
- **703** — NF de Transferencia (armazem geral)
- **724** — Volumes Disponiveis no Estoque
- **741** — Cadastro de Mercadorias
