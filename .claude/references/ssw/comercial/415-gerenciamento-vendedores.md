# Opcao 415 — Gerenciamento de Vendedores

> **Modulo**: Comercial
> **Paginas de ajuda**: 5 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Parametriza comissionamento de vendedores, define vinculos entre vendedores e clientes, e configura tabelas de comissao diferenciadas por periodo (conquista, manutencao). Sistema permite comissionamento por percentual fixo ou baseado em desconto NTC.

## Quando Usar
- Cadastrar novo vendedor na transportadora
- Vincular vendedor a clientes
- Definir comissoes por cliente ou tipo de mercadoria
- Configurar comissoes de conquista e manutencao
- Trocar vendedor de clientes
- Alterar tabelas de comissao em lote
- Organizar equipes de vendas

## Pre-requisitos
- Vendedor com login no SSW (opcao 925)
- Unidade de atuacao cadastrada (opcao 401)
- Clientes cadastrados (opcao 483)
- Agendamento de processamento configurado (opcao 903)

## Campos / Interface

### Tela Incluir Novo Vendedor
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo do Vendedor | Sim | Codigo numerico do vendedor |
| Ativo | Sim | S para calcular comissao, N inativo |
| Login | Sim | Login do vendedor no SSW (opcao 925) |
| Nome do vendedor | Sim | Nome definido no Login |
| Sigla da unidade | Sim | Unidade de atuacao (opcao 401) |
| Codigo da equipe | Nao | Identifica equipe de vendas (sem padrao) |
| Paga comissao sobre CTRCs | Sim | Emitidos ou liquidados |

### Tela Comissionamento (por Cliente)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Tipo de mercadoria | Nao | Permite diferenciar comissoes por mercadoria |
| Descontar da base | Nao | TDA, TDE, TRT, PIS/COFINS, ICMS/ISS |
| Comissao de conquista | Condicional | % sobre frete ou % sobre DESC NTC por periodo |
| CTRC normal/FEC/complementar | Condicional | % especifico para cada tipo |
| Comissao de manutencao | Condicional | % apos periodo conquista |
| Comissao de manutencao 2 | Condicional | % apos periodo manutencao |
| Periodo | Condicional | Data inicio/fim de cada fase (fim pode ser indefinido) |

## Fluxo de Uso

### Cadastro Novo Vendedor:
1. Acessar opcao 415
2. "Incluir novo vendedor"
3. Informar codigo numerico
4. Preencher dados do vendedor (login, nome, unidade, equipe)
5. Definir criterio pagamento (emitido/liquidado)
6. Gravar cadastro

### Vincular Cliente:
1. Acessar opcao 415
2. "Associar vendedor ao cliente"
3. Selecionar vendedor (codigo)
4. Informar CNPJ cliente
5. Configurar comissoes (conquista/manutencao)
6. Opcionalmente: definir comissao por tipo mercadoria
7. Gravar vinculo

### Troca em Lote:
1. Para troca massiva de clientes: trocar LOGIN do codigo vendedor (nao precisa trocar cliente por cliente)
2. Usar "Trocar cliente do vendedor para" para clientes especificos

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 056 | Relatorios gerenciais (120-128) |
| 067 | Gerenciamento supervisao/suporte |
| 068 | Cotadores |
| 101 | Resultado CTRC - consulta MAPA pagamento |
| 222 | CTRCs complementares |
| 300 | Relatorios pessoais do vendedor |
| 392 | Composicao frete - consulta comissao |
| 397 | Metas e clientes alvo |
| 401 | Cadastro unidades |
| 402 | Cidades (TDA, TDE, TRT) |
| 483 | Cadastro clientes |
| 536 | Relacao de vendedores |
| 903 | Agendamento processamento batch |
| 923 | Tabela NTC |
| 925 | Usuarios/login |

## Observacoes e Gotchas

### Regras Fundamentais
- **Um vendedor por cliente**: cliente so pode ter um vendedor
- **Calculo automatico**: ocorre diariamente nas primeiras horas do dia seguinte
- **FOB Dirigido**: comissao baseada no cliente REMETENTE (nao pagador)
- **Troca de vendedor eficiente**: trocar LOGIN do codigo (nao refazer vinculos)

### Tipos de Comissao
1. **Comissao de Conquista**: maior % por periodo determinado para premiar conquista
2. **Comissao de Manutencao**: % reduzido apos periodo conquista
3. **Comissao de Manutencao 2**: % ainda menor, periodo indefinido aceito

### Formas de Calculo
- **% sobre frete**: percentual sobre valor do frete (podendo descontar TDA/TDE/TRT/PIS/COFINS/ICMS/ISS)
- **% sobre DESC NTC**: comissao baseada em desconto obtido sobre tabela NTC (opcao 923). Quanto maior desconto, menor comissao. Incentiva fretes com maior resultado.

### Relatorios (opcao 056 ou 300)
- **120**: Comissao vendedor analitico (unidade vendedor)
- **121**: Comissao vendedor Excel (unidade vendedor)
- **123**: Clientes sem movimentacao (unidade vendedor)
- **124**: Comissao vendedor resumo (apenas MTZ)
- **125**: Producao vendedor acumulado mes (unidade vendedor, disponivel 12 meses)
- **126**: Producao vendedor resumo (apenas MTZ, disponivel 12 meses)
- **127**: Comissao vendedor previsao (unidade vendedor, CTRCs nao liquidados)
- **128**: Comissao vendedor previsao sintetico (apenas MTZ)

### Relatorios Pessoais
- Liberar opcao 300 para vendedores (retirar opcao 056)
- Vendedores veem apenas suas proprias comissoes

### CTRCs Complementares
- % pode ser diferenciado para:
  - CTRC normal
  - FEC (carga fechada)
  - Complementar (opcao 222)

### Consulta de Comissao Paga
- Opcao 101/Frete ou opcao 392: informa em qual MAPA foi paga comissao do CTRC

### Opcoes de Gestao
- **Consultar tabelas do cliente**: mostra vendedores de um cliente
- **Consultar tabelas do vendedor**: mostra clientes de um vendedor
- **Relacao de vendedores**: relaciona vendedores, clientes e comissoes (opcao 536)
- **Altera tabela do vendedor**: ajustes em lote para todos clientes do vendedor

### Supervisao e Suporte
- Opcao 067: remunera supervisores e equipe suporte com base em comissoes vendedores (opcao 415) e cotadores (opcao 068)
- Base calculo: pode ser sobre frete (B) ou sobre comissao (C)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A01](../pops/POP-A01-cadastrar-cliente.md) | Cadastrar cliente |
