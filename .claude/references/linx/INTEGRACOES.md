# Linx — Guia de Integracoes e Manuais Tecnicos

**Ultima Atualizacao**: 23/02/2026

---

## 1. Mapa de APIs e WebServices

O Linx possui **5 interfaces de integracao** distintas:

| Interface | Protocolo | Direcao | URL Base |
|-----------|-----------|---------|----------|
| **WS Saida Padrao** | XML/SOAP | Linx -> Terceiro (leitura) | `https://webapi.microvix.com.br/1.0/api/integracao` |
| **WS B2C** | XML/SOAP | Bidirecional (e-commerce) | `https://webapi.microvix.com.br/1.0/api/integracao` |
| **WS Entrada** | XML/SOAP | Terceiro -> Linx (escrita) | `https://webapi.microvix.com.br/1.0/importador.svc` |
| **Linx ERP REST** | REST/JSON | Bidirecional | Instalacao local (`Setup_LinxErpApi.msi`) |
| **API Faturas a Pagar** | REST/JSON | Terceiro -> Linx (escrita) | `https://eswebapi-integracao.microvix.com.br` |

**Ambiente de homologacao**: `http://aceitacao.microvix.com.br:8728/1.0/api/integracao`

### Resumo de Direcoes (Extracao vs Inclusao)

| Direcao | Interface | O que faz |
|---------|-----------|-----------|
| **Extracao** (Linx -> Nos) | WS Saida Padrao | Le produtos, vendas, clientes, estoque, financeiro |
| **Extracao** (Linx -> Nos) | B2C (metodos `Consulta`) | Le catalogo, pedidos, NF-e (com XML), rastreio |
| **Inclusao** (Nos -> Linx) | WS Entrada | Cadastra produtos, grades, NCM, clientes/fornecedores |
| **Inclusao** (Nos -> Linx) | B2C (metodos `Cadastra`) | Cria clientes, pedidos, itens, planos, rastreio |
| **Inclusao** (Nos -> Linx) | API Faturas a Pagar | Cria faturas a pagar (REST/JSON) |
| **Bidirecional** | Linx ERP REST | Consulta + criacao + atualizacao (instalacao local) |

---

## 2. Autenticacao

### Microvix (WS Saida + B2C)
```
Credenciais: user=linx_b2c / password=linx_b2c
Chave de acesso: UNIQUEIDENTIFIER (fornecida na ativacao)
Parametro obrigatorio: cnpjEmp (VARCHAR 14)
```

### API Faturas a Pagar (REST)
```
Header: IntegrationAutentication = <token JWT>
Token fornecido apos contratacao
```

### Linx ERP REST
```
Instalacao: Setup_LinxErpApi.msi
Path: C:\Program Files (x86)\Linx Sistemas\Linx ERP API
Metodos HTTP: GET (consulta), POST (criacao), PUT (atualizacao)
```

---

## 3. Mecanismo de Timestamp (CRITICO)

O Microvix usa **timestamps incrementais SQL Server** (NAO Unix timestamp):
- Sao contadores por metodo, unicos no banco
- Cada operacao adiciona 1 unidade

**Workflow obrigatorio para sincronizacao**:
```
1. Primeira consulta -> timestamp = 0 -> retorna TODOS os registros
2. Armazenar o MAIOR timestamp retornado
3. Proximas consultas -> usar ultimo timestamp -> retorna apenas novos/modificados
```

---

## 4. WS Saida Padrao — Metodos de Consulta

**Spec oficial**: v209 (16/02/2026) — cada metodo = 1 tabela do banco

### Movimento (Vendas)
| Metodo | Descricao |
|--------|-----------|
| `LinxMovimento` | Dados da venda (com params de tributacao) |
| `LinxMovimentoPrincipal` | Movimento principal |
| `LinxMovimentoPlanos` | Planos/metodos de pagamento |
| `LinxMovimentoDevolucoesItens` | Itens devolvidos |
| `LinxMovimentoIndicacoes` | Cliente que indicou a venda |
| `LinxMovimentoGiftCard` | Gift cards |
| `LinxMovimentoReshop` | Transacoes campanha Reshop |

### Produtos
| Metodo | Descricao |
|--------|-----------|
| `LinxProdutos` | Cadastro de produtos |
| `LinxProdutosDetalhes` | Saldo geral (soma depositos disponiveis p/ venda) |
| `LinxProdutosDetalhesDepositos` | Saldo por deposito especifico |
| `LinxProdutosLotes` | Saldo de lotes |
| `LinxProdutosImagensURL` | URLs de imagens |
| `LinxProdutosCodebar` | Codigos de barras |

### Clientes/Fornecedores
| Metodo | Parametros | Descricao |
|--------|------------|-----------|
| `LinxClientesFornec` | chave, cnpjEmp, data_inicial, data_fim, dt_update_* | Cadastro clientes/fornecedores |
| `LinxClientesEnderecosEntrega` | — | Enderecos de entrega |

### Pedidos e Vendedores
| Metodo | Descricao |
|--------|-----------|
| `LinxPedidosVenda` | Pedidos (join: empresa + clientes_fornecedores + orcamento) |
| `LinxVendedores` | Vendedores (params: chave, cnpjEmp, cod_vendedor, data_upd_inicial) |

### Financeiro
| Metodo | Descricao |
|--------|-----------|
| `LinxSangriaSuprimentos` | Sangrias e suprimentos de caixa |
| `LinxTrocaUnificadaResumoBaixa` | Resumo de baixa de trocas |

---

## 5. WS B2C — Metodos E-commerce

### Formato de requisicao XML
```xml
<LinxMicrovix>
  <Authentication user="linx_b2c" password="linx_b2c" />
  <Command>
    <Name>B2CConsultaProdutos</Name>
    <Parameters>
      <Parameter id="chave">bda920cc-XXXX-XXXX</Parameter>
      <Parameter id="cnpjEmp">00000000000000</Parameter>
      <Parameter id="timestamp">0</Parameter>
    </Parameters>
  </Command>
</LinxMicrovix>
```

### Metodos de LEITURA (GET)

| Area | Metodo | Descricao |
|------|--------|-----------|
| **Empresa** | `B2CConsultaEmpresas` | Dados da empresa |
| | `B2CConsultaFormasPagamento` | Formas de pagamento |
| | `B2CConsultaPlanos` | Planos de pagamento |
| **Classificacao** | `B2CConsultaSetores` | Setores |
| | `B2CConsultaLinhas` | Linhas |
| | `B2CConsultaMarcas` | Marcas |
| | `B2CConsultaColecoes` | Colecoes |
| **Produtos** | `B2CConsultaProdutos` | Catalogo de produtos |
| | `B2CConsultaProdutosDetalhes` | Estoque por empresa |
| | `B2CConsultaProdutosCustos` | Precos e custos |
| | `B2CConsultaProdutosCampanhas` | Campanhas promocionais |
| | `B2CConsultaProdutosPromocao` | Precos promocionais |
| | `B2CConsultaProdutosCodebar` | Codigos de barras |
| | `B2CConsultaProdutosImagens` | Imagens |
| | `B2CConsultaImagensHD` | Imagens HD |
| | `B2CConsultaProdutosAssociados` | Kits/combos |
| | `B2CConsultaProdutosStatus` | Disponibilidade |
| **Pedidos** | `B2CConsultaPedidos` | Pedidos de venda |
| | `B2CConsultaPedidosItens` | Itens do pedido |
| | `B2CConsultaPedidosStatus` | Historico de status |
| **NF-e** | `B2CConsultaNFe` | Notas fiscais — retorna XML completo + chave 44 digitos (ver secao 5.1) |
| **Clientes** | `B2CConsultaClientes` | Cadastro de clientes |
| | `B2CConsultaClientesEnderecosEntrega` | Enderecos de entrega |
| | `B2CConsultaClientesSaldo` | Saldo de credito |
| **Logistica** | `B2CConsultaTransportadores` | Transportadoras |
| | `B2CConsultaCodigoRastreio` | Codigos de rastreio |
| **Outros** | `B2CConsultaFornecedores` | Fornecedores |
| | `B2CConsultaVendedores` | Vendedores |

### Metodos de ESCRITA (POST)

| Metodo | Descricao |
|--------|-----------|
| `B2CCadastraClientes` | Cria cliente |
| `B2CCadastraClientesContatos` | Cria contatos |
| `B2CCadastraClientesEnderecosEntrega` | Cadastra endereco |
| `B2CCadastraPedido` | Cria pedido |
| `B2CCadastraPedidoPlanos` | Define planos do pedido |
| `B2CCadastraPedidoItens` | Adiciona itens ao pedido |
| `B2CCancelaPedido` | Cancela pedido |
| `B2CAtualizaCodigoRastreio` | Atualiza rastreio |

### 5.1. B2CConsultaNFe — Detalhamento (NF-e)

**Fonte verificada**: Spec B2C via DocPlayer (campos confirmados)

#### Campos retornados

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id_nfe` | INT | Codigo interno da NF-e no Microvix |
| `id_pedido` | INT | Codigo do pedido B2C |
| `documento` | INT | Numero da nota fiscal |
| `data_emissao` | SMALLDATETIME | Data de emissao |
| `chave_nfe` | CHAR(44) | Chave de acesso da NF-e (44 digitos SEFAZ) |
| `situacao` | TINYINT | Situacao da NF-e |
| `xml` | VARCHAR(MAX) | **XML COMPLETO da NF-e** (autorizado pela SEFAZ) |
| `excluido` | BIT | Se a NF-e foi excluida |
| `identificador_microvix` | UNIQUEIDENTIFIER | Identificador unico Microvix |
| `dt_insert` | SMALLDATETIME | Data de insercao do registro |
| `valor_nota` | MONEY | Valor total da nota |
| `serie` | VARCHAR(10) | Serie da nota fiscal |
| `frete` | MONEY | Valor do frete na nota |
| `Timestamp` | TIMESTAMP | Timestamp incremental (ver secao 3) |

#### Parametros de consulta

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `chave` | UNIQUEIDENTIFIER | Chave de acesso da API |
| `cnpjEmp` | VARCHAR(14) | CNPJ da empresa |
| `id_nfe` | INT | Filtrar por ID interno |
| `id_pedido` | INT | Filtrar por pedido |
| `documento` | INT | Filtrar por numero da nota |
| `chave_nfe` | CHAR(44) | Filtrar por chave de acesso SEFAZ |
| `data_inicial` | DATE | Filtrar por data de emissao (inicio) |
| `data_fim` | DATE | Filtrar por data de emissao (fim) |
| `timestamp` | TIMESTAMP | Filtrar por timestamp incremental |

#### XML vs DANFE (PDF)

| Artefato | Disponivel via API? | Como obter |
|----------|---------------------|------------|
| **XML da NF-e** | **SIM** — campo `xml` (VARCHAR MAX) | Direto no retorno do `B2CConsultaNFe` |
| **Chave de acesso** | **SIM** — campo `chave_nfe` (44 digitos) | Direto no retorno |
| **DANFE (PDF)** | **NAO** — nao ha campo de PDF na API | Gerar localmente a partir do XML |

**Como gerar DANFE a partir do XML**:
1. Libs Python: `python-danfe`, `brazilfiscal`, `pynfe`
2. A partir da `chave_nfe`: consultar portal SEFAZ (https://www.nfe.fazenda.gov.br)
3. Servidores de rendering: existem servicos que recebem XML e devolvem PDF

**Importante**: O XML retornado e o documento fiscal COMPLETO autorizado pela SEFAZ. Contem todos os dados (emitente, destinatario, itens, impostos, transporte, cobranca). O DANFE e apenas uma representacao grafica simplificada desse XML.

---

## 6. WS Entrada — Envio de Dados para Microvix

**URL**: `https://webapi.microvix.com.br/1.0/importador.svc`

### Metodos de cadastro (diarios, madrugada)
| Metodo | Dados |
|--------|-------|
| `LinxCadastraSetores` | Setores |
| `LinxCadastraLinhas` | Linhas |
| `LinxCadastraMarcas` | Marcas |
| `LinxCadastraColecoes` | Colecoes |
| `LinxCadastraEspessuras` | Espessuras |
| `LinxCadastraClassificacoes` | Classificacoes |
| `LinxCadastraGrade1` | Grade 1 |
| `LinxCadastraGrade2` | Grade 2 |
| `LinxCadastraNcm` | NCM fiscal |
| `LinxCadastraCest` | CEST fiscal |
| `LinxCadastraProdutos` | Produtos completos |
| `LinxCadastraProdutosCodebar` | Codigos de barras |

### Cadastro em tempo real
| Metodo | Dados |
|--------|-------|
| `LinxCadastraClientesFornecedores` | Clientes/Fornecedores + contatos + enderecos |

### Dados aceitos (escopo da API entrada)
- Produtos
- Pedidos de compra
- Orcamentos/pedidos de venda
- Planos de pagamento
- Clientes/Fornecedores

**Contratacao**: Caso Salesforce -> fila "DC Shopping Arquitetura"

---

## 7. API Faturas a Pagar (REST)

**Endpoint**: `POST https://eswebapi-integracao.microvix.com.br/api/Fatura/CadastrarFaturaAPagar`
**Auth**: Header `IntegrationAutentication: <JWT token>`

### Campos do request (JSON)

| Campo | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| `IdUsuario` | Int | Sim | ID usuario Microvix |
| `IdEmpresa` | Int | Sim | ID empresa no portal |
| `IdFornecedor` | Int | Sim | ID fornecedor (CRM) |
| `IdCentroCusto` | Int | Sim | Centro de custo |
| `IdHistoricoContabil` | Int | Sim | Historico contabil |
| `IdContaFluxo` | Int | Sim | Conta contabil |
| `IdCategoriaFinanceira` | Int | Sim | Categoria financeira |
| `IdPortador` | Int | Sim | 1=Carteira, 2=Banco |
| `NumeroDocumento` | Int | Sim | N. do documento |
| `SerieDocumento` | String | Sim | Serie |
| `DataEmissao` | Date | Sim | Emissao |
| `DataVencimento` | Date | Sim | Vencimento |
| `DataLancamento` | Date | Sim | Lancamento |
| `NumeroParcela` | Int | Sim | Parcela atual |
| `TotalParcelas` | Int | Sim | Total parcelas |
| `ValorFatura` | Decimal | Sim | Valor |
| `Observacao` | String | Sim | Observacao |
| `IdFormaPagamento` | Int | Sim | 1=Dinheiro, 2=Cheque vista, 3=Cheque prazo, 4=Crediario, 5=Cartao, 6=Convenio |

---

## 8. Integracao de Estoque — Gotcha Critico

**Divergencia comum**: Saldo no Microvix != saldo no e-commerce.

**Causa**: Configuracao de deposito no modulo Tools:

| Configuracao | Metodo usado | Comportamento |
|--------------|-------------|---------------|
| Deposito configurado em Tools | `B2CConsultaProdutosDetalhesDepositos` | Le saldo APENAS do deposito configurado |
| Sem deposito em Tools | `B2CConsultaProdutosDetalhes` | Soma de TODOS os depositos disponiveis para venda |

**Requisitos**:
- Produto com "Disponivel na loja virtual" = SIM
- Se mudou de NAO->SIM, fazer ajuste de estoque para atualizar timestamp
- Produto precisa de movimentacao de entrada (nota de recebimento) para ter saldo

---

## 9. Status vs Situacao de Pedidos

| Conceito | Tipo | Uso |
|----------|------|-----|
| **Status** (0-11) | Informacional | pendente, faturado, em separacao, cancelado, trocado... |
| **Situacao** (`ativo` + `finalizado`) | Operacional | Determina se aparece na fila de faturamento |

---

## 10. Processo de Contratacao de Integracao

1. Abrir caso no Salesforce -> fila "DC Shopping Arquitetura"
2. Submeter documento de integracao preenchido
3. Pre-analise do arquiteto + criacao de OS
4. Estimativa de horas + proposta comercial
5. Apos aprovacao: startup em 48h
6. Projetos concluem em ~2 semanas (Microvix)
7. Portal modelo e auto-gerado apos regras de integracao estabelecidas
8. Suporte tecnico: fila 47.6 para consulta com arquiteto

**Custos de referencia (B2C)**:
- Ativacao: 30 horas
- Manutencao mensal: R$ 300,00
- Setup: sob consulta

---

## 11. Restricoes e Limitacoes

- **Microvix GO**: Modulo cotacao/pedido de venda indisponivel
- **B2C**: Apenas 1 CNPJ por configuracao de portal
- **Concorrencia**: NAO executar multiplas requisicoes de criacao no mesmo segundo por portal
- **Tabela de preco**: Somente tipo "precos diferentes por produto"
- **Endereco basico**: Obrigatorio para evitar erros de cobranca
- **Acesso direto ao banco**: Microvix NAO compartilha; tudo via API

---

## 12. Exemplo de Codigo (Ruby — gem nao-oficial)

```ruby
require 'linx_microvix'

LinxMicrovix.configure do |config|
  config.user = ENV['LINX_MICROVIX_USER']
  config.pass = ENV['LINX_MICROVIX_PASS']
end

# Consultar clientes/fornecedores
result = LinxMicrovix::Request.new('ClientesFornec', {
  cnpjEmp: '00000000000000',
  data_inicial: '2026-01-01',
  data_fim: '2026-02-23'
}).run
```

**Fonte**: https://github.com/phbruce/linx_microvix (gem Ruby, MIT, minimalista)

---

## 13. Links de Documentacao — Manuais e APIs

### Especificacoes WebService Microvix
| Documento | Link |
|-----------|------|
| WS Saida Padrao v209 (PDF) | https://share.linx.com.br/download/attachments/168641333/Especifica%C3%A7%C3%A3o%20Web%20Service%20de%20Sa%C3%ADda%20Padr%C3%A3o%20-%20v209.pdf |
| WS Saida Padrao (pagina hub) | https://share.linx.com.br/pages/viewpage.action?pageId=168641333 |
| WS B2C (pagina) | https://share.linx.com.br/display/SHOPLINXMICRPUB/WebService+B2C |
| WS B2C v21 (PDF) | https://share.linx.com.br/download/attachments/168641320/Documenta%C3%A7%C3%A3o%20Integra%C3%A7%C3%A3o%20WS%20B2C-V21.pdf |
| WS B2C v36 (PDF) | https://share.linx.com.br/download/attachments/168641320/Documenta%C3%A7%C3%A3o%20Integra%C3%A7%C3%A3o%20WS%20B2C-V36.pdf |
| WS Entrada | https://share.linx.com.br/pages/viewpage.action?pageId=220329671 |
| Spec English v100 (PDF) | https://share.linx.com.br/download/attachments/168641333/Web%20Service%20Specification%20-%20v100%20-%20English%20translation.pdf |
| Integracao hub (tutorial) | https://share.linx.com.br/pages/viewpage.action?pageId=168641350 |
| Saldo de produtos B2C | https://share.linx.com.br/pages/viewpage.action?pageId=218596103 |
| Linx x Microvix (inter-ERP) | https://share.linx.com.br/pages/viewpage.action?pageId=220329717 |

### APIs Especializadas
| Documento | Link |
|-----------|------|
| API Faturas a Pagar | https://share.linx.com.br/pages/viewpage.action?pageId=406984498 |
| API Extrator de Vendas | https://share.linx.com.br/display/SHOPLINXNEW/API+-+Extrator+de+Vendas |
| API Usuarios Linx ERP | https://share.linx.com.br/pages/viewpage.action?pageId=290161836 |
| WebService Linx ERP (intro) | https://share.linx.com.br/display/SHOPLINXNEW/WebService+Linx+ERP |
| API Integracao ERPs (Digital) | https://docs.linxdigital.com.br/docs/api-integracao-com-erps |

### Manuais
| Documento | Link |
|-----------|------|
| Manual WMS | https://share.linx.com.br/download/attachments/182107856/MANUAL%20WMS.pdf |
| Manual Conciliacao v3.7 | https://share.linx.com.br/download/attachments/210563702/Manual%20Webservice%20Concilia%C3%A7%C3%A3o%203.7.pdf |
| Guia Integracao ERP + WMS e-Millennium | https://share.linx.com.br/download/attachments/532483611/Guia%20R%C3%A1pido%20-%20Integra%C3%A7%C3%A3o%20Linx%20ERP%20e%20WMS%20e-Millennium.pdf |
| Linx IO (config) | https://docs.linxdigital.com.br/docs/3-linx-io |
| Config inicial ERP | https://share.linx.com.br/pages/viewpage.action?pageId=174206064 |
| Linx Pay Hub (devs) | https://www.linx.com.br/online-desenvolvedores/ |
| Reforma tributaria | https://share.linx.com.br/x/yNCkIw |
| Release notes 8.1 SP02.25 | https://share.linx.com.br/display/SHOPLINXNEW/Linx+ERP+8.1+Service+Pack+02.25.000 |

### Terceiros
| Recurso | Link |
|---------|------|
| LinkAPI (Microvix) | https://developers.linkapi.solutions/docs/microvix |
| SysMiddle (guia integracao) | https://sysmiddle.com.br/integrar-linxmicrovix-com-erp-padrao/ |
| Gem Ruby (phbruce) | https://github.com/phbruce/linx_microvix |
| DocPlayer (spec B2C) | https://docplayer.com.br/227848410-Especificacao-web-service-b2c-linx-microvix-padrao.html |
