<!-- doc:meta
tipo: how-to
camada: L3
sot_de: Importacao de dados historicos (Excel) para o banco MotoChefe via telas de Carga Inicial e Importacao Historica (fases 1-6).
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# DOCUMENTACAO: CARGA INICIAL - SISTEMA MOTOCHEFE

> **Papel:** guia how-to para importar dados historicos de planilhas Excel no MotoChefe, cobrindo as fases de configuracao base, cadastros dependentes, produtos/clientes, pedidos e historico financeiro.

**Data:** 14/10/2025
**Versao:** 1.1
**Autor:** Claude AI + Rafael Nascimento

---

## Indice

- [Objetivo](#objetivo)
- [Estrutura de arquivos criados](#estrutura-de-arquivos-criados)
- [Como usar](#como-usar)
- [Estrutura das planilhas](#estrutura-das-planilhas)
- [Regras de validacao](#regras-de-validacao)
- [Funcionalidade UPSERT](#funcionalidade-upsert)
- [Exemplo de uso real](#exemplo-de-uso-real)
- [Scripts de migracao](#scripts-de-migracao)
- [Fases avancadas (4, 5 e 6)](#fases-avancadas-4-5-e-6)
- [Troubleshooting](#troubleshooting)
- [Suporte](#suporte)
- [Historico de versoes](#historico-de-versoes)

---

## OBJETIVO

Sistema de importacao de dados historicos de planilhas Excel para o banco de dados do MotoChefe, com validacao de integridade referencial e regras de negocio.

---

## ESTRUTURA DE ARQUIVOS CRIADOS

```
app/motochefe/
├── services/
│   ├── importacao_carga_inicial.py        # Service das fases 1-3
│   ├── importacao_fase4_pedidos.py        # Service da fase 4 (pedidos/vendas)
│   └── importacao_historico_service.py    # Service das fases 5 e 6 (comissoes/montagens)
└── routes/
    ├── __init__.py                         # Registro da rota (atualizado)
    └── carga_inicial.py                    # Rotas HTTP

app/templates/motochefe/carga_inicial/
├── index.html                              # Interface web (fases 1-4)
└── historico.html                          # Interface web (fases 5-6 historicas)
```

> O template real fica em `app/templates/motochefe/carga_inicial/` (templates centralizados da aplicacao), nao em `app/motochefe/templates/`.

---

## COMO USAR

### 1. ACESSAR A TELA

```
URL: http://localhost:5000/motochefe/carga-inicial
```

Ou pelo menu do sistema MotoChefe (adicionar link no dashboard).

### 2. PROCESSO DE IMPORTACAO

O sistema funciona em **3 fases sequenciais** para os cadastros base:

#### **FASE 1: Configuracoes Base** (sem dependencias)
- Equipes de Vendas
- Transportadoras
- Empresas Vendedoras (contas bancarias)
- CrossDocking (apenas 1 registro)
- Custos Operacionais (apenas 1 registro)

#### **FASE 2: Cadastros Dependentes**
- Vendedores (depende de Equipes)
- Modelos de Motos (catalogo)

#### **FASE 3: Produtos e Clientes**
- Clientes (depende de Vendedores)
- Motos (depende de Modelos)

### 3. PASSO A PASSO

1. **Baixar templates** de cada fase
2. **Preencher planilhas** com seus dados historicos
3. **Importar fase 1** completa
4. **Importar fase 2** (habilitado apos fase 1)
5. **Importar fase 3** (habilitado apos fase 2)
6. **Verificar resultados** em cada etapa

---

## ESTRUTURA DAS PLANILHAS

### FASE 1 - TEMPLATE

#### Aba: 1_Equipes
| Campo | Tipo | Obrigatorio | Exemplo | Descricao |
|-------|------|-------------|---------|-----------|
| `equipe_vendas` | Texto | Sim | "Equipe Sul" | Nome da equipe |
| `responsavel_movimentacao` | Texto | Nao | "NACOM" | Responsavel pela movimentacao |
| `custo_movimentacao` | Decimal | Nao | 500.00 | Custo de movimentacao (R$) |
| `incluir_custo_movimentacao` | Boolean | Nao | SIM/NAO | Adicionar ao preco final? |
| `tipo_precificacao` | Texto | Nao | "TABELA" | TABELA ou CUSTO_MARKUP |
| `markup` | Decimal | Nao | 1000.00 | Markup fixo (R$) |
| `tipo_comissao` | Texto | Nao | "FIXA_EXCEDENTE" | FIXA_EXCEDENTE ou PERCENTUAL |
| `valor_comissao_fixa` | Decimal | Nao | 200.00 | Comissao fixa (R$) |
| `percentual_comissao` | Decimal | Nao | 5.00 | Percentual (%) |
| `comissao_rateada` | Boolean | Nao | SIM | Rateio entre vendedores? |
| `permitir_montagem` | Boolean | Nao | SIM | Permitir montagem? |
| `permitir_prazo` | Boolean | Nao | NAO | Permitir prazo de pagamento? |
| `permitir_parcelamento` | Boolean | Nao | NAO | Permitir parcelamento? |

#### Aba: 2_Transportadoras
| Campo | Tipo | Obrigatorio | Exemplo |
|-------|------|-------------|---------|
| `transportadora` | Texto | Sim | "Transportes ABC" |
| `cnpj` | Texto | Nao | "12.345.678/0001-90" |
| `telefone` | Texto | Nao | "(11) 98765-4321" |
| `chave_pix` | Texto | Nao | "123456789" |
| `banco` | Texto | Nao | "Banco do Brasil" |
| `cod_banco` | Texto | Nao | "001" |
| `agencia` | Texto | Nao | "1234" |
| `conta` | Texto | Nao | "56789-0" |

#### Aba: 3_Empresas
| Campo | Tipo | Obrigatorio | Exemplo | Descricao |
|-------|------|-------------|---------|-----------|
| `empresa` | Texto | Sim | "Sogima Motos" | Nome da empresa |
| `cnpj_empresa` | Texto | Nao | "98.765.432/0001-10" | CNPJ |
| `chave_pix` | Texto | Nao | "987654321" | Chave PIX |
| `banco` | Texto | Nao | "Itau" | Nome do banco |
| `cod_banco` | Texto | Nao | "341" | Codigo do banco |
| `agencia` | Texto | Nao | "5678" | Agencia |
| `conta` | Texto | Nao | "12345-6" | Conta |
| `tipo_conta` | Texto | Nao | "FABRICANTE" | FABRICANTE, OPERACIONAL, MARGEM_SOGIMA |
| `baixa_compra_auto` | Boolean | Nao | SIM | Baixa automatica de compras? |
| `saldo` | Decimal | Nao | 50000.00 | Saldo inicial (R$) |

#### Aba: 4_CrossDocking (APENAS 1 LINHA)
| Campo | Tipo | Exemplo |
|-------|------|---------|
| `nome` | Texto | "CrossDocking Generico" |
| Demais campos iguais a **Equipes** | | |

#### Aba: 5_Custos (APENAS 1 LINHA)
| Campo | Tipo | Exemplo |
|-------|------|---------|
| `custo_montagem` | Decimal | 150.00 |
| `custo_movimentacao_devolucao` | Decimal | 300.00 |
| `data_vigencia_inicio` | Data | 01/01/2025 |

---

### FASE 2 - TEMPLATE

#### Aba: 1_Vendedores
| Campo | Tipo | Obrigatorio | Exemplo |
|-------|------|-------------|---------|
| `vendedor` | Texto | Sim | "Joao Silva" |
| `equipe_vendas` | Texto | Sim | "Equipe Sul" |

#### Aba: 2_Modelos
| Campo | Tipo | Obrigatorio | Exemplo | Descricao |
|-------|------|-------------|---------|-----------|
| `nome_modelo` | Texto | Sim | "Voltz EV1" | Nome do modelo |
| `potencia_motor` | Texto | Sim | "2000W" | Potencia (ex: 1000W, 2000W, 3000W) |
| `autopropelido` | Boolean | Nao | SIM | E autopropelido? |
| `preco_tabela` | Decimal | Sim | 8500.00 | Preco de tabela (R$) |
| `descricao` | Texto | Nao | "Moto eletrica cargo" | Descricao |

---

### FASE 3 - TEMPLATE

#### Aba: 1_Clientes
| Campo | Tipo | Obrigatorio | Exemplo |
|-------|------|-------------|---------|
| `cnpj_cliente` | Texto | Sim | "11.222.333/0001-44" |
| `cliente` | Texto | Sim | "Empresa XYZ Ltda" |
| `vendedor` | Texto | Sim | "Joao Silva" |
| `crossdocking` | Boolean | Nao | NAO |
| `endereco_cliente` | Texto | Nao | "Rua ABC" |
| `numero_cliente` | Texto | Nao | "123" |
| `complemento_cliente` | Texto | Nao | "Sala 45" |
| `bairro_cliente` | Texto | Nao | "Centro" |
| `cidade_cliente` | Texto | Nao | "Sao Paulo" |
| `estado_cliente` | Texto | Nao | "SP" |
| `cep_cliente` | Texto | Nao | "01310-100" |
| `telefone_cliente` | Texto | Nao | "(11) 3456-7890" |
| `email_cliente` | Texto | Nao | "contato@xyz.com.br" |

#### Aba: 2_Motos
| Campo | Tipo | Obrigatorio | Exemplo | Descricao |
|-------|------|-------------|---------|-----------|
| `numero_chassi` | Texto | Sim | "9BWZZZ377VT004251" | Chassi (ate 30 chars) |
| `numero_motor` | Texto | Nao | "MOTOR123456" | Motor (unico se preenchido) |
| `nome_modelo` | Texto | Sim | "Voltz EV1" | Nome do modelo (deve existir) |
| `cor` | Texto | Sim | "Branco" | Cor da moto |
| `ano_fabricacao` | Inteiro | Nao | 2024 | Ano de fabricacao |
| `nf_entrada` | Texto | Sim | "NF-001234" | NF de compra |
| `data_nf_entrada` | Data | Sim | 15/01/2025 | Data da NF |
| `data_entrada` | Data | Sim | 16/01/2025 | Data entrada estoque |
| `fornecedor` | Texto | Sim | "Voltz Motors" | Fornecedor |
| `custo_aquisicao` | Decimal | Sim | 7200.00 | Custo de compra (R$) |
| `status` | Texto | Nao | "DISPONIVEL" | DISPONIVEL, VENDIDA, RESERVADA, AVARIADO, DEVOLVIDO |
| `status_pagamento_custo` | Texto | Nao | "PENDENTE" | PENDENTE, PAGO, PARCIAL |
| `empresa_pagadora` | Texto | Nao | "Sogima Motos" | Nome da empresa que pagou |
| `observacao` | Texto | Nao | "Moto revisada" | Observacoes gerais |
| `pallet` | Texto | Nao | "P-001" | Localizacao fisica |

---

## REGRAS DE VALIDACAO

### Validacoes Automaticas

- **Campos obrigatorios**: Sistema para se faltar campo marcado como obrigatorio
- **CNPJ unico**: Clientes nao podem ter CNPJ duplicado
- **Chassi unico**: Motos nao podem ter chassi duplicado
- **Motor unico**: Se preenchido, numero do motor deve ser unico
- **Foreign Keys**: Valida se entidade referenciada existe
- **Valores positivos**: Precos e custos devem ser > 0
- **Formatos de data**: Aceita dd/mm/yyyy, yyyy-mm-dd, dd-mm-yyyy

### Tratamento de Erros

- **Parada imediata**: Sistema para na **primeira linha com erro critico**
- **Mensagem detalhada**: Informa linha, campo e motivo do erro
- **UPSERT ativo**: Pode re-executar sem duplicar dados

---

## FUNCIONALIDADE UPSERT

O sistema usa **UPSERT** (Update + Insert) para permitir re-execucao:

| Tabela | Chave de Busca | Comportamento |
|--------|----------------|---------------|
| `equipe_vendas_moto` | `equipe_vendas` | Atualiza se nome existir |
| `transportadora_moto` | `transportadora` | Atualiza se nome existir |
| `empresa_venda_moto` | `empresa` | Atualiza se nome existir |
| `cross_docking` | Unico registro | Sempre atualiza o primeiro |
| `vendedor_moto` | `vendedor` | Atualiza se nome existir |
| `modelo_moto` | `nome_modelo` | Atualiza se nome existir |
| `cliente_moto` | `cnpj_cliente` | Atualiza se CNPJ existir |
| `moto` | `numero_chassi` | Atualiza se chassi existir |

**Vantagem:** Permite corrigir dados e re-importar sem duplicar registros.

---

## EXEMPLO DE USO REAL

### Cenario: Importar historico de 100 motos vendidas

**Passo 1:** Preparar dados do sistema antigo (Excel)
**Passo 2:** Baixar templates e preencher:
- Fase 1: 2 equipes, 3 transportadoras, 1 empresa
- Fase 2: 5 vendedores, 3 modelos
- Fase 3: 50 clientes, 100 motos

**Passo 3:** Importar Fase 1 — Equipes, transportadoras e empresas criadas
**Passo 4:** Importar Fase 2 — Vendedores vinculados as equipes, modelos cadastrados
**Passo 5:** Importar Fase 3 — Clientes vinculados aos vendedores, motos cadastradas com modelos

**Tempo estimado:** 15-30 minutos (dependendo da preparacao dos dados)

---

## SCRIPTS DE MIGRACAO

Veja os arquivos:
- [migrations/carga_inicial_motochefe_local.py](migrations/carga_inicial_motochefe_local.py) - Execucao local
- [migrations/carga_inicial_motochefe_render.sql](migrations/carga_inicial_motochefe_render.sql) - Execucao no Render

---

## FASES AVANCADAS (4, 5 E 6)

Diferentemente das versoes iniciais deste documento, as fases avancadas **estao implementadas**:

- **Fase 4 - Pedidos e Vendas**: importa pedidos historicos com chassis ja vinculados, executando todas as funcoes automaticas (atualizar status das motos, gerar titulos a receber, gerar titulos a pagar, calcular vencimentos e comissoes). Service: `app/motochefe/services/importacao_fase4_pedidos.py`. Rotas: `/motochefe/carga-inicial/fase4` e `/motochefe/carga-inicial/fase4/importar`. Template: `fase4.html`.
- **Fase 5 - Comissoes** e **Fase 6 - Montagens / Movimentacoes**: importadas pelo fluxo de Importacao Historica. Service: `app/motochefe/services/importacao_historico_service.py` (`importar_comissoes_historico` e `importar_montagens_historico`). Rotas: `/motochefe/carga-inicial/historico` (UI), `/historico/preview` e `/historico/importar`. Template: `historico.html`.

**Recomendacao operacional:** ao importar pedidos historicos ja concluidos, prefira as fases 4-6 (que reproduzem titulos, comissoes e movimentacoes com regras retroativas). Para a operacao corrente (pedidos novos), use o sistema operacional normalmente — ele gera automaticamente titulos financeiros, comissoes, titulos a pagar e movimentacoes.

---

## TROUBLESHOOTING

### Erro: "Equipe nao encontrada"
**Causa:** Tentou importar vendedor antes de criar equipes
**Solucao:** Importe Fase 1 completa primeiro

### Erro: "CNPJ duplicado"
**Causa:** CNPJ ja existe no banco
**Solucao:** Use UPSERT (sistema atualiza automaticamente) ou remova duplicata

### Erro: "Modelo nao encontrado"
**Causa:** Nome do modelo na planilha nao bate com cadastro
**Solucao:** Verifique se nome esta EXATAMENTE igual (case-sensitive)

### Erro: "Numero de motor duplicado"
**Causa:** Mesmo numero de motor em motos diferentes
**Solucao:** Deixe campo vazio ou corrija numeracao

---

## SUPORTE

Para duvidas ou problemas:
1. Consulte os logs detalhados na tela de importacao
2. Verifique a linha exata do erro informada
3. Revise o campo indicado na mensagem de erro
4. Se necessario, consulte este documento ou o codigo-fonte

---

## HISTORICO DE VERSOES

| Versao | Data | Alteracoes |
|--------|------|------------|
| 1.0 | 14/10/2025 | Versao inicial - Fases 1, 2 e 3 |
| 1.1 | 2026-06-15 | Reconciliado: fases 4, 5 e 6 documentadas como implementadas; corrigido path do template para `app/templates/motochefe/`. |

---

**FIM DA DOCUMENTACAO**
