# Opcoes 417, 418, 420 — Tabelas de Frete

> **Modulo**: Comercial
> **Referencias**: Opcoes 417 (Combinada), 418 (Percentual), 420 (Faixa Peso), 427 (Rota), 923 (NTC)
> **Atualizado em**: 2026-02-14

## Funcao
Conjunto de opcoes para cadastro e gestao de tabelas de frete de clientes. Cada opcao representa um modelo diferente de precificacao. Tabelas definem valores de frete cobrados por origem-destino com parametros como peso, valor mercadoria, distancia, e adicionais (GRIS, TDE, TRT, pedagio, etc.).

## Tipos de Tabelas

### Opcao 417 - Tabela Combinada
- **Frete Peso + Frete Valor**: combina R$/ton com % sobre valor mercadoria
- **Despacho**: valor fixo R$ por CTRC
- **Minimo**: valor minimo garantido
- **Uso**: tabela mais completa e flexivel, padrao para maioria dos clientes

### Opcao 418 - Tabela Percentual
- **Percentual sobre NTC**: desconto ou acrescimo sobre tabela NTC (opcao 923)
- **Uso**: clientes com fretes baseados em referencia NTC

### Opcao 420 - Tabela por Faixa de Peso
- **Faixas progressivas**: valores R$ ou R$/Kg por faixas de peso (ate X Kg)
- **Despacho**: valor fixo por CTRC
- **Uso**: fretes com variacao significativa por peso (courier, aereo)

### Opcao 427 - Tabela de Rota
- **Especifica por rota**: origem-destino especificos
- **Prioridade sobre generica**: sobrepoe tabela geral do cliente
- **Uso**: rotas com precificacao diferenciada

### Opcao 923 - Tabela NTC (Referencia)
- **Tabela generica**: valores de referencia por distancia e peso
- **Tarifas**: progressivas conforme Km rodado
- **Base para desconto**: usada em opcao 418 e como referencia geral

## Quando Usar

- Cadastrar novo cliente com tabela de frete
- Ajustar precos para cliente existente
- Criar tabela diferenciada para rota especifica
- Definir FOB Dirigido (remetente escolhe transportadora)
- Configurar simulacao de tabela (teste antes ativar)
- Replicar tabela entre clientes ou unidades
- Importar/exportar tabelas em CSV

## Pre-requisitos

- Cliente cadastrado (opcao 483)
- Unidades origem/destino cadastradas (opcao 401)
- Cidades de atendimento configuradas (opcao 402)
- Para NTC: tarifas cadastradas (opcao 923)

## Campos Comuns (Todas Tabelas)

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CNPJ Cliente | Sim | Cliente pagador (ou remetente se FOB Dirigido) |
| Unidade origem | Sim | Unidade de coleta |
| Unidade/UF destino | Sim | Unidade ou UF de entrega |
| Ativa | Sim | S=ativa, N=simulacao (nao usa em calculo real) |
| FOB Dirigido | Nao | S para frete FOB onde remetente escolhe transportadora |
| Data inicio/fim | Condicional | Periodo validade tabela |
| ICMS/ISS na tabela | Nao | S se frete ja inclui imposto (N=repassa ao cliente) |
| PIS/COFINS na tabela | Nao | S se frete ja inclui (N=repassa ao cliente) |

## Adicionais de Frete (Configurados nas Tabelas)

### Taxas Percentuais
| Taxa | Base Calculo | Descricao |
|------|--------------|-----------|
| GRIS | % valor mercadoria | Gerenciamento Risco |
| Ad Valorem | % valor mercadoria | Seguro carga |
| Pedagio | R$/frac 100Kg ou % frete | Postos pedagio na rota |

### Taxas Fixas/Condicionais
| Taxa | Calculo | Descricao |
|------|---------|-----------|
| TDE | R$/ton, % val merc, % frete + min R$ | Taxa Dificil Entrega (opcao 487, 483) |
| TDC | R$/ton, % val merc, % frete + min R$ | Taxa Dificil Coleta (opcao 483) |
| TRT | R$/ton, % val merc, % frete + min R$ | Taxa Restricao Transito (opcao 530) |
| TDA | R$/ton, % val merc, % frete + min R$ | Taxa Dificil Acesso (opcao 402) |
| TAR | R$/ton, % val merc, % frete + min R$ | Taxa Area Risco (opcao 304) |
| Coleta | R$ fixo | Cobrada se placa informada (exceto ARMAZEM/ARMA999) |
| Entrega | R$ fixo | Nao cobrada se destino = sigla unidade ou BALCAO |

### Servicos Adicionais
| Servico | Calculo | Descricao |
|---------|---------|-----------|
| Agendamento | R$ ou % frete | Servico agendamento entrega (opcao 483, 423) |
| Paletizacao | R$ ou % frete | Paletizacao mercadoria (opcao 483, 423) |
| Separacao | R$ ou % frete | Separacao volumes (opcao 483, 423) |
| Capatazia | R$ ou % frete | Movimentacao carga (opcao 483, 423) |
| Veiculo Dedicado | R$ ou % frete | Veiculo exclusivo (opcao 483, 423) |
| Reembolso | % valor mercadoria + min R$ | Cobranca valor mercadoria (opcao 105) |
| Devolucao Canhoto | R$ fixo | Devolucao comprovante NF (opcao 423) |

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 002 | Cotacao - usa tabelas para calcular frete |
| 004/005/006 | Emissao CTRC - aplica tabela no calculo |
| 101 | Resultado CTRC - mostra tabela utilizada |
| 222 | CTRCs complementares |
| 304 | Taxa Area Risco (TAR) |
| 392 | Composicao frete - link para tabela usada |
| 394 | CNPJ raiz - Entrega Dificil |
| 401 | Cadastro unidades (origem/destino) |
| 402 | Cidades - TDA, pedagio |
| 419 | Desconto sobre NTC |
| 423 | Servicos adicionais |
| 468 | Impressao tabelas |
| 473 | Consulta TDEs cadastrados |
| 483 | Cadastro clientes - TDE, TDC, Entrega Dificil, servicos |
| 487 | Tabela TDE especifica |
| 494 | Tabela por volume |
| 495 | Tabela por metro cubico |
| 501 | Tabelas de tarifas |
| 530 | TRT - areas restricao transito |
| 903 | Parametros gerais |
| 923 | Tabela NTC (referencia) |

## Observacoes e Gotchas

### Prioridades de Tabelas
1. **Tabela de Rota** (opcao 427) - maior prioridade
2. **Tabela especifica UF destino**
3. **Tabela generica cliente**
4. **Tabela NTC** (opcao 923) - menor prioridade (referencia)

### FOB Dirigido
- Tabela DEVE estar cadastrada no **cliente REMETENTE** (nao pagador)
- Remetente escolhe transportadora
- Marcar "FOB Dirigido = S" na tabela

### Simulacao
- Tabela com "Ativa = N" nao e usada em calculos reais
- Permite testar precos antes ativar
- Util para apresentacoes comerciais

### Impostos Repassados
- **ICMS/ISS na tabela = N**: imposto repassado ao cliente (adicionado ao frete calculado)
- **PIS/COFINS na tabela = N**: idem
- **S**: frete informado ja e valor final com impostos
- Configuracao geral: opcao 903/Frete

### TDE (Taxa Dificil Entrega)
- **Prioridade 1**: TDE das tabelas de frete cliente (417, 418, 420)
- **Prioridade 2**: TDE da Rota (427)
- **Prioridade 3**: TDE Generica (923)
- **Prioridade 4**: Tabela TDE especifica (opcao 487)
- Destinatario deve estar marcado "Entrega Dificil" (opcao 483) ou raiz CNPJ (opcao 394)
- TDE = 0 e reconhecido (zera cobranca)

### TRT (Taxa Restricao Transito)
- Municipios restringem trafego caminhoes grandes
- Tabela geral: opcao 530
- Areas restricao: por CEP (geral ou por cliente)
- FOB Dirigido: area deve estar no cliente REMETENTE

### Cubagem
- Cubagem configurada na tabela (Kg/m3)
- Peso cubado = volume (m3) x cubagem
- Frete calculado sobre maior: peso real ou peso cubado
- Cubagem padrao: opcao 423

### Base de Calculo
- Valores com ICMS (integral) quando impostos sao base para calculos secundarios
- "Val frete" NAO considera "Impostos Repassados" (TRT calculado antes, entra na base ICMS)

### Replicacao e Importacao
- **Replicar**: copiar tabela entre clientes/unidades
- **CSV**: baixar, editar, importar (sobrepoe cadastrados)
- Historico de alteracoes: rastreabilidade de mudancas

### Relatorios
- Opcao 468: impressao de tabelas com filtros (tipo, ativo, FOB, unidade, UF, periodo, cliente)
- Filtros: periodo inclusao, alteracao, ultimo movimento

### Consultas
- Opcao 473: consulta TDEs cadastrados
- Opcao 101/392: identifica tabela utilizada no CTRC

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
