# Opcao 408 — Comissao de Unidades

> **Modulo**: Comercial
> **Paginas de ajuda**: 10 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra tabelas de calculo de comissionamento para unidades operacionais (filiais, terceiros, embarcadores). Define parametros para remuneracao de servicos de expedicao, recepcao, transferencia e transbordo prestados por unidades da transportadora ou parceiros subcontratados.

## Quando Usar
- Contratar transportadora parceira (subcontratacao)
- Definir comissionamento de filiais para calculo de resultados
- Configurar pagamento de terceiros por expedicao/recepcao
- Estabelecer parametros de parcerias (usando ou nao SSW)
- Alterar tabelas de comissao para clientes, cidades, rotas especificas
- Definir unidades alternativas de entrega

## Pre-requisitos
- Unidade cadastrada (opcao 401) - tipo Filial, Terceiro ou Embarcador
- Subcontratado cadastrado como fornecedor (opcao 478) com Ativo=S e Conta Corrente de Fornecedor=S
- Conta Corrente do Fornecedor criada (opcao 486)
- Subcontratado cadastrado como transportadora (opcao 485) com status ativo
- Para parcerias SSW: aprovacao do subcontratado via opcao 508

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade | Sim | Sigla da unidade (opcao 401) para cadastrar comissao |
| Comissao geral | Nao | Tabela geral da unidade (filial ou terceirizada) |
| Tabelas especificas | Nao | Por Cliente, Cidade, Rota, Tipo Mercadoria, CIF/FOB, Empresa |
| Comissao de transbordo | Nao | Para unidades intermediarias que efetuam transbordo |
| Unidades Alternativas | Nao | Define unidades alternativas para entregas |

### Tela Comissao Geral - Como Expedidora

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Subcontratado | Sim | CNPJ do parceiro subcontratado |
| Aprovado por | Condicional | Usuario aprovador se subcontratada usa SSW (opcao 508) |
| Senha para alteracao | Condicional | Senha fornecida pela subcontratada (opcao 508) para alteracoes |
| Data inicial | Sim | Data inicio do comissionamento |
| Data final | Nao | Pode ser omitida (indeterminada) |
| Tipo Frete | Sim | CIF, FOB ou Ambas |
| 1. Sobre frete | Nao | % para Polo, Regiao, Interior com descontos (Seguro, PIS/COFINS, parcelas) |
| 2. Sobre valor mercadoria | Nao | % sobre valor da mercadoria |
| 3. Sobre peso | Nao | Despacho (R$), Cubagem (Kg/m3), Valor da faixa (R$ ou R$/Kg), Tabela por faixas |
| 4. Comissao minima | Nao | Maior entre R$/ton, R$, %frete |
| 5. Adicionar TDC/TRT/TDA/TAR/Pedagio | Nao | % sobre parcelas + minimos + pedagio por frac 100Kg |
| 6. Sobre CTRCs complementares | Nao | % sobre paletizacao, agendamento, estadia, reentrega, armazenagem |
| 7. Sobre Carga Fechada | Nao | Comissao complementar para destino FEC |
| 8. Sobre frete aereo | Nao | Comissao especifica para CTRC aereo |
| 9. Aplicar sobre CTRCs | Nao | Liquidados (S/N) |
| 10. Conta Corrente Fornecedor | Sim | Mapa, Fatura ou Capa de Remessa |
| 11. Emissao Subcontrato/Redespacho | Condicional | Utiliza comissao (S/N), Paga ICMS aliquota (%) |

### Tela Comissao Geral - Como Receptora

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| 5. Adicionar TDE/TRT/TDA/TAR/Pedagio | Nao | % sobre taxas cobradas no CTRC ou sobre frete |
| 7. Sobre Carga Fechada | Nao | % sobre comissao (nao frete) - apenas ajuda descarga |
| 9. Aplicar sobre CTRCs | Nao | Comprovante Entrega arquivado, Imagem Comprovante |
| 10. Conta Corrente Fornecedor | Sim | M-mapa, F-fatura ou C-capa |
| 11. Emissao Subcontrato/Redespacho | Condicional | Utiliza comissao (S/N), Paga ICMS aliquota (%) |
| Sincronizar ENTREGA DIFICIL | Nao | Sincroniza Entrega Dificil dos clientes entre subcontratada e subcontratante |

## Fluxo de Uso

### Fluxo Basico (Nova Parceria):
1. Cadastrar unidade operacional (opcao 401)
2. Cadastrar subcontratado como fornecedor (opcao 478)
3. Criar Conta Corrente do Fornecedor (opcao 486)
4. Cadastrar como transportadora (opcao 485)
5. Acessar opcao 408
6. Selecionar unidade
7. Criar Comissao Geral:
   - Informar CNPJ subcontratado
   - Definir datas inicial/final
   - Configurar parametros de expedicao (itens 1-11)
   - Configurar parametros de recepcao (itens 1-11)
8. Se subcontratado usa SSW: aguardar aprovacao (opcao 508)
9. Configurar tabelas especificas se necessario (cliente, cidade, rota)

### Fluxo Calculo:
1. Comissao calculada na emissao do CTRC (opcao 004) para expedicao/recepcao
2. Comissao de transbordo calculada na saida do veiculo (opcao 025)
3. Valores creditados na CCF (opcao 486) conforme forma escolhida:
   - **Mapa**: agendamento batch (opcao 903)
   - **Fatura**: conferencia manual (opcao 607)
   - **Capa**: recepcao de remessa (opcao 428)

### Fluxo Encerramento de Parceria:
1. Usar opcao 414 para encerramento
2. NAO encerrar unidade (sigla) - apenas trocar prestador
3. Tabelas de frete dependentes da sigla continuam validas

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 004 | Emissao CTRC - calcula comissao expedicao/recepcao |
| 025 | Saida veiculo - calcula comissao transbordo |
| 026 | Parametrizacao multiempresas |
| 056 | Relatorios de comissao |
| 101 | Resultado comercial do CTRC |
| 388 | Unidades alternativas por cliente remetente/destinatario |
| 393 | Resultados do CTRC |
| 395 | Unidades alternativas por peso/CEP/mercadoria |
| 401 | Cadastro de unidades |
| 402 | Cidades de atendimento, prazos e fretes |
| 403 | Rotas de transferencia |
| 414 | Encerramento de parcerias |
| 417/418 | Tabelas de frete de clientes |
| 428 | Recepcao Capa de Remessa (forma C de credito CCF) |
| 475 | Eventos de despesa |
| 478 | Cadastro fornecedores |
| 483 | Cadastro clientes |
| 485 | Cadastro transportadoras |
| 486 | Conta Corrente do Fornecedor (credito comissao) |
| 508 | Aprovacao tabelas pelo subcontratado (se usa SSW) |
| 607 | Conferencia fatura subcontratado (forma F de credito CCF) |
| 609 | CTRCs unitizados - comissao distribuida linearmente |
| 671 | Alteracao manual comissao de CTRC |
| 903 | Processamento batch Mapa (forma M de credito CCF) |

## Observacoes e Gotchas

### Conceitos Fundamentais
- **Parceria**: Cliente contrata transportadora, parceiro executa operacao parcial/totalmente
- **Um Subcontrato por CTRC**: Quando parceiro usa SSW, apenas 1 Subcontrato por CTRC
- **Comissao de filiais**: Visa calculo de remuneracao (nao financeiro) para resultado do CTRC
- **CTRCs unitizados**: Comissao calculada somando dados de todos CTRCs, distribuida linearmente
- **Multiempresas**: Varias transportadoras associadas prestam servicos com parametrizacao via opcao 408

### Tabelas Especificas (Ordem de Prioridade)
1. Especifica para CLIENTE
2. Especifica para CIDADE
3. Especifica para ROTA (emissao CTRC e Manifesto)
   - Recalculada se raiz CNPJ unidade = raiz CNPJ veiculo
   - Comissao recepcao NAO pode estar em Mapa/Fatura/Capa
4. Especifica por TIPO DE MERCADORIA
5. Especifica para CIF
6. Especifica para FOB
7. Especifica para EMPRESA
8. Comissao Geral (fallback)

### Calculo de Comissao
- **Expedicao**: soma itens 1-3, compara com minimo (4), adiciona item 5
- **Recepcao**: mesma formula (itens 1-5)
- **Cubagem = 0**: usa peso real do CTRC
- **Cubagem = 999,99**: usa peso calculo do CTRC
- **Transbordo**: identificado quando CTRC muda Manifesto em unidade diferente da emissora, com placa diferente

### Formas de Credito CCF
- **Mapa (M)**: processamento batch agendado (opcao 903). Contratada opera unidade no SSW da transportadora
- **Fatura (F)**: conferencia manual (opcao 607). Subcontratada pode ou nao usar SSW
- **Capa (C)**: recepcao de Capa de Remessa (opcao 428). Subcontratada usa seu proprio SSW. TEM PRIORIDADE sobre Mapa/Fatura
- Credito ocorre para qualquer CNPJ com mesma raiz

### Parcelas e Taxas
- **TDC, TRT, TDA, TAR**: so adicionadas se existirem no CTRC subcontratante
- **Pedagio**: sempre adicionado, mesmo sem parcela no CTRC
- **TDA, TAR, TRT**: pagas para unidade origem/destino que realizou servico. Se ambos, cada um fica com metade
- **Sincronizar ENTREGA DIFICIL**: atualiza diariamente cliente Entrega Dificil entre subcontratada e subcontratante (ambas usando SSW)

### SSW Basico para Parceiros
- Versao gratuita para parceiros que emitem Subcontratos/Redespachos exclusivamente para contratantes usuarios SSW
- Permite informar ocorrencias e entregas on-line sem custos

### Unidades Alternativas
- Uma unidade pode ser alternativa de mais de uma principal
- Escolha automatica: por peso/CEP/mercadoria (opcao 395) ou por cliente (opcao 388)
- Troca manual: opcao 020
- Cada alternativa deve ter tabela de comissao (opcao 408), senao usa tabela da subcontratada
- Cidades, prazos e fretes: SEMPRE pela unidade principal (nunca alternativa)
- Nao servem para expedicao - configurar rotas (opcao 403) para unidades origem

### Frete Aereo
- SSW pode usar parametros opcao 408 em vez de item 8 exclusivo (configuracao SSW)

### Multiempresas - Relatorios
- **107**: Comissao agenciamento multiempresa (analitico por empresa)
- **108**: Resumo 107 (somente MTZ)
- **116**: Comissao transferencia (analitico por empresa)
- **117**: Resumo 116 (somente MTZ)
- **168**: Resultado da unidade (receitas opção 408 vs despesas opção 475)
- Juncao 108+117 em Excel: valores totais a pagar/receber entre empresas

### Restricoes e Limites
- Comissao NAO pode ser alterada (opcao 671) se ja estiver em MAPA
- Alteracoes gravadas nas ocorrencias do CTRC (opcao 101)
- Para CTRCs complementares (opcao 222): comissao so paga se Reembolso ao Parceiro = S
- ICMS SP: se origem CTRC = SP e sede unidade expedicao/recepcao Redespacho = SP, nao ha pagamento ICMS mesmo cadastrado

### Aprovacao e Seguranca
- Subcontratado que usa SSW: deve aprovar tabela via opcao 508
- Alteracoes: exigem senha fornecida pela subcontratada (opcao 508)
- Raiz CNPJ: ultima atualizacao CCF atualiza todos CNPJs mesma raiz

### Historico e Relatorios
- Importar/Baixar CSV: permite importacao em lote com relatorio sucesso/insucesso
- Relacao de unidades: gera relatorio com unidades e informacoes cadastrais
- Imprimir relatorio: relaciona unidades e comissoes (relatorio e Excel)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A02](../pops/POP-A02-cadastrar-unidade-parceira.md) | Cadastrar unidade parceira |
| [POP-A04](../pops/POP-A04-cadastrar-rotas.md) | Cadastrar rotas |
| [POP-A05](../pops/POP-A05-cadastrar-fornecedor.md) | Cadastrar fornecedor |
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-B05](../pops/POP-B05-relatorios-gerenciais.md) | Relatorios gerenciais |
| [POP-C01](../pops/POP-C01-emitir-cte-fracionado.md) | Emitir cte fracionado |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
