# Indice — Modulo Comercial SSW

> **Diretorio**: `.claude/references/ssw/comercial/`
> **Atualizado em**: 2026-02-14

Este indice consolida toda a documentacao do modulo Comercial do SSW Sistemas, organizada por area tematica.

---

## Documentacao Disponivel

### Tabelas de Frete (CORE)
| Arquivo | Opcoes | Descricao |
|---------|--------|-----------|
| `417-418-420-tabelas-frete.md` | 417, 418, 420, 427, 923 | **DOCUMENTO PRINCIPAL** - Todos tipos tabelas frete (Combinada, Percentual, Faixa Peso, Rota, NTC). Adicionais (GRIS, TDE, TRT, etc). Prioridades e integracao. |

### Comissionamento e Vendas
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `408-comissao-unidades.md` | 408 | Comissionamento unidades (filiais, terceiros, embarcadores). Expedicao, recepcao, transbordo. Parcerias SSW. Formas credito CCF (Mapa/Fatura/Capa). |
| `415-gerenciamento-vendedores.md` | 415 | Gerenciamento vendedores. Vinculos cliente-vendedor. Comissoes (conquista/manutencao). Relatorios. Equipes. |
| `397-metas-clientes-alvo.md` | 397 | Metas vendedores e clientes alvo. Acompanhamento performance (relatorios 125/126). |

### Parametros Comerciais
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `423-parametros-comerciais-cliente.md` | 423 | Parametros por cliente: reentrega, devolucao, recoleta, armazenagem, servicos complementares (paletizacao, agendamento, separacao, capatazia). Cubagem. |
| `422-local-entrega-subcontratados.md` | 422 | Endereco especifico entrega para subcontratados (diferente unidade distribuicao). |

### Operacoes e Processos
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `398-escanear-comprovantes-entregas.md` | 398 | Escaneamento comprovantes entrega. SSWScan. Anexacao manual. |
| `OPCOES-COMPLEMENTARES.md` | 428, 431 | Recepcao Capa Remessa (428). Unidades mesmo armazem (431). Fluxos comissionamento. |

---

## Mapa de Navegacao por Necessidade

### "Preciso configurar fretes para clientes"
→ **START**: `417-418-420-tabelas-frete.md`
- Entenda tipos tabelas (Combinada, Percentual, Faixa Peso, Rota)
- Aprenda adicionais (GRIS, TDE, TRT, TAR, pedagio)
- Veja prioridades e integracao

### "Preciso configurar parcerias/subcontratacao"
→ **START**: `408-comissao-unidades.md`
- Cadastro tabelas comissao
- Expedicao/Recepcao/Transbordo
- Formas credito CCF (Mapa/Fatura/Capa)
- Parcerias SSW vs nao-SSW

### "Preciso configurar vendedores"
→ **START**: `415-gerenciamento-vendedores.md`
- Cadastro vendedores e vinculos
- Comissoes (conquista/manutencao/% DESC NTC)
- Metas: `397-metas-clientes-alvo.md`

### "Preciso configurar servicos adicionais"
→ **START**: `423-parametros-comerciais-cliente.md`
- Reentrega/Devolucao/Recoleta
- Armazenagem
- Servicos complementares
- Tabelas CTRC Complementar

### "Preciso entender comprovantes e arquivamento"
→ **START**: `398-escanear-comprovantes-entregas.md`
→ NEXT: `OPCOES-COMPLEMENTARES.md` (opcao 428)

---

## Opcoes por Categoria

### Precificacao
- **417**: Tabela Combinada (peso + valor)
- **418**: Tabela Percentual (desconto/acrescimo NTC)
- **420**: Tabela Faixa Peso
- **427**: Tabela Rota especifica
- **923**: Tabela NTC (referencia)
- **423**: Parametros cliente (servicos)

### Comissionamento
- **408**: Comissao unidades (parcerias)
- **415**: Vendedores
- **397**: Metas e alvos
- **067**: Supervisao/Suporte (referenciado em 415)

### Operacoes Parceria
- **428**: Recepcao Capa Remessa
- **607**: Conferencia fatura subcontratado (ref em 408)
- **486**: Conta Corrente Fornecedor (ref em 408/428)

### Parametros e Configuracoes
- **422**: Local entrega subcontratados
- **423**: Parametros comerciais cliente
- **431**: Unidades mesmo armazem
- **401**: Cadastro unidades (ref geral)
- **483**: Cadastro clientes (ref geral)

### Comprovantes
- **398**: Escanear comprovantes
- **428**: Recepcao capa remessa
- **040**: Arquivamento fisico (ref em 398)

---

## Integracao com Outros Modulos

### Financeiro
- **CCF** (opcao 486): credito comissoes parcerias/agregados
- **Contas Pagar** (opcao 475): acerto saldos CCF
- **Faturamento** (opcao 436): cobranca cliente

### Operacional
- **Emissao CTRC** (004/005/006): aplica tabelas frete
- **Cotacao** (002): usa tabelas para simular
- **Romaneio** (035): considera unidades mesmo armazem
- **Manifestos** (020/025): comissao transbordo

### Cadastros
- **Unidades** (401): origem/destino, parcerias
- **Clientes** (483): tabelas, parametros, TDE/TDC
- **Cidades** (402): TDA, pedagio, prazos
- **Rotas** (403): distancias, pedagios

### Relatorios
- **056**: Relatorios gerenciais (vendedores, comissoes, resultados)
- **300**: Relatorios pessoais vendedor
- **101**: Resultado CTRC (tabela usada, comissoes)
- **392**: Composicao frete (detalhamento)

---

## Opcoes Nao Documentadas (Arquivos Nao Disponiveis)

- **390**: Referenciada como PGR (Plano Gerenciamento Risco) em 407
- **409**: Remuneracao veiculos (referencias indiretas em 075/076)
- **433**: [Consulta/Relatorio]
- **435**: [Consulta/Relatorio]
- **469**: [Impressao/Relatorio - possivelmente relacionado a 468]
- **518**: [Especifico]

**Nota**: Para estas opcoes, consultar ajuda nativa do SSW ou solicitar documentacao adicional.

---

## Glossario Rapido

- **CTRC**: Conhecimento Transporte Rodoviario Carga
- **DACTE**: Documento Auxiliar CT-e
- **CCF**: Conta Corrente Fornecedor
- **NTC**: Tabela generica referencia (923)
- **TDE**: Taxa Dificil Entrega
- **TDC**: Taxa Dificil Coleta
- **TRT**: Taxa Restricao Transito
- **TAR**: Taxa Area Risco
- **TDA**: Taxa Dificil Acesso
- **GRIS**: Gerenciamento Risco
- **FOB Dirigido**: Remetente escolhe transportadora
- **Subcontrato**: Documento fiscal parceria
- **Redespacho**: Transferencia outra transportadora
- **OS**: Ordem Servico (remuneracao agregado)
- **CTRB**: Contrato Transporte Rodoviario Bens
- **RPA**: Recibo Pagamento Autonomo

---

## Proximos Passos

### Para desenvolvedores integrando com SSW:
1. Ler `417-418-420-tabelas-frete.md` para entender precificacao
2. Ler `408-comissao-unidades.md` para entender parcerias
3. Consultar INDEX.md principal (`.claude/references/ssw/INDEX.md`) para visao geral sistema

### Para analistas de negocio:
1. Ler `415-gerenciamento-vendedores.md` para gestao comercial
2. Ler `397-metas-clientes-alvo.md` para acompanhamento performance
3. Ler `423-parametros-comerciais-cliente.md` para servicos adicionais

### Para administradores sistema:
1. Ler `408-comissao-unidades.md` para configurar parcerias
2. Ler `OPCOES-COMPLEMENTARES.md` para fluxos operacionais
3. Ler documentacao infraestrutura (INDEX.md principal)
- [Opcao 062 — Parametros de Frete](062-parametros-frete.md)
- [Opção 100 — Geração de E-mails para Clientes](100-geracao-emails-clientes.md)
- [Opção 101 — Resultado/Consulta CTRC](101-resultado-ctrc.md)
- [Opção 102 — Consulta CTRC Simplificada](102-consulta-ctrc.md)
- [Opção 104 — Faturas Repassadas para Agências](104-faturas-repassadas-agencias.md)
- [Opção 105 — Agendar Processamento Mapa do Embarcador](105-agendar-mapa-embarcador.md)
- [Opção 107 — Gerar Arquivo de Cidades Atendidas](107-gerar-arquivo-cidades-atendidas.md)
- [Opção 110 — Cotação de Fretes pelo Cliente](110-cotacao-fretes-cliente.md)
- [Opção 117 — Monitoração dos Embarcadores](117-monitoracao-embarcadores.md)
- [Opção 119 — Cadastro de Clientes - Ocorrências](119-cadastro-clientes-ocorrencias.md)
- [Opção 124 — Entrada no Almoxarifado](124-entrada-almoxarifado.md)
- [Opção 125 — Rastreamento de Produtos](125-rastreamento-produtos.md)
- [Opção 135 — Carregar GPS](135-carregar-gps.md)
- [Opção 138 — Estorno de Baixa/Entrega e Resgate de CTRC](138-estorno-baixa-entrega.md)
- [Opção 144 — Big Brother SSW - Monitoração das Ações](144-big-brother-monitoracao.md)
- [Opção 146 — Domínios a Serem Buscados](146-dominios-buscados.md)
- [Opcao 147 — Conferencia de Documentos](147-conferencia-documentos.md)
- [Opcao 154 — Localizacao de Fornecedores](154-localizacao-fornecedores.md)
- [Opcao 156 — Fila de Processamento de Relatorios](156-fila-processamento-relatorios.md)
- [Opcao 160 — GNRE DIFAL](160-gnre-difal.md)
- [Opcao 163 — Cadastro de Ajudantes](163-cadastro-ajudantes.md)
- [Opcao 164 — Relacao de Ajudantes](164-relacao-ajudantes.md)
- [Opcao 166 — Capturar Volumes que Gerarao CTRCs](166-capturar-volumes-ctrc.md)
- [Opcao 167 — Conferencia do SSWCOL](167-conferencia-sswcol.md)
- [Opcao 177 — App Android (SSW Mobile)](177-app-android.md)
- [Opcao 178 — Geracao de Arquivo EDI Fiscal MT](178-edi-fiscal-mt.md)
- [Opcao 180 — Observacoes das Tabelas de Fretes](180-observacoes-tabelas-frete.md)
- [Opcao 183 — Tabela de Produtos Controlados](183-tabela-produtos-controlados.md)
- [Opcao 191 — Instrucoes de Clientes (Embarcador)](191-instrucoes-clientes.md)
- [Opção 206 — Chaves DANFEs Capturadas pelo SSWMobile 5 - Coleta](206-chaves-danfes-capturadas-coleta.md)
- [Opção 208 — SSWMobile 4 (versão desktop)](208-sswmobile4-desktop.md)
- [Opção 209 — Troca Veículos e/ou Motoristas de MDF-e](209-troca-veiculos-motoristas-mdfe.md)
- [Opção 211 — Unitização de Volumes do CTRC](211-unitizacao-volumes-ctrc.md)
- [Opção 220 — Emissão de Manifestos e Romaneios com Sorter](220-emissao-manifestos-romaneios-sorter.md)
- [Opcao 221 — Geracao em Lote de CTRCs Complementares](221-geracao-lote-ctrcs-complementares.md)
- [Opcao 222 — Emissao de CTRC para Cobrar Servico Complementar](222-emissao-ctrc-servico-complementar.md)
- [Opcao 228 — Motorista e Quarentena](228-motorista-quarentena.md)
- [Opcao 236 — Consulta e Reimpressao de Romaneios de Entrega](236-consulta-reimpressao-romaneios-entrega.md)
- [Opcao 250 — Controle de Acareacao - Matriz](250-controle-acareacao-matriz.md)
- [Opcao 290 — Tabela de Requisitos PGR](290-tabela-requisitos-pgr.md)
- [Opcao 304 — Areas de Risco](304-areas-risco.md)
- [Opcao 305 — Cadastro de Ocorrencias do SSWMobile 4](305-cadastro-ocorrencias-sswmobile4.md)
- [Opcao 307 — Altera Base de Calculo de ICMS](307-altera-base-calculo-icms.md)
- [Opcao 308 — CTRCs com Fale Conosco Preenchido](308-ctrcs-fale-conosco-preenchido.md)
- [Opcao 335 — Acoes de Vendas](335-acoes-vendas.md)
- [Opcao 343 — Gera Arquivo de Cobranca CNAB](343-gera-arquivo-cobranca-cnab.md)
- [Opcao 379 — Geracao Automatica de Pre-CTRCs](379-geracao-automatica-pre-ctrcs.md)
- [Opcao 380 — Definicao do Orcamento](380-definicao-orcamento.md)
- [Opcao 381 — Cadastro de Clientes - Operacao](381-cadastro-clientes-operacao.md)
- [Opcao 383 — Configuracao de Rastreamento de Clientes](383-configuracao-rastreamento-clientes.md)
- [Opcao 385 — Geracao de Carta de Anuencia](385-geracao-carta-anuencia.md)
- [Opcao 388 — Cadastro de Clientes - Complemento](388-cadastro-clientes-complemento.md)
- [Opcao 389 — Cadastro de Clientes - Credito](389-cadastro-clientes-credito.md)
- [Opção 390 — Cadastro de Espécies de Mercadorias](390-cadastro-especies-mercadorias.md)
- [Opção 409 — Remuneração de Veículos](409-remuneracao-veiculos.md)
- [Opção 427 — Resultado por Cliente](427-resultado-por-cliente.md)
- [Opção 491 — E-mails e Telefones da Unidade](491-emails-telefones-unidade.md)
- [Opção 492 — Cancelamento do Desconto de Duplicatas](492-cancelamento-desconto-duplicatas.md)
- [Opção 494 — Reajuste de Tabelas por Volumes](494-reajuste-tabelas-volume.md)
- [Opção 495 — Reajuste de Tabelas por m³](495-reajuste-tabelas-m3.md)
- [Opção 497 — Metas para Vendedores](497-metas-vendedores.md)
- [Opção 499 — Replicar Configurações do CTRB de Transferência por Veículo](499-replicar-config-ctrb-transferencia-veiculo.md)
- [Opção 500 — Liquidação Parcial de Fatura via Arquivo](500-liquidacao-parcial-fatura-arquivo.md)
- [Opção 923 — Cadastro das Tabelas NTC e Genérica](923-cadastro-tabelas-ntc-generica.md)
