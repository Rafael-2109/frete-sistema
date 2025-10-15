# 📦 DOCUMENTAÇÃO: CARGA INICIAL - SISTEMA MOTOCHEFE

**Data:** 14/10/2025
**Versão:** 1.0
**Autor:** Claude AI + Rafael Nascimento

---

## 🎯 OBJETIVO

Sistema de importação de dados históricos de planilhas Excel para o banco de dados do MotoChefe, com validação de integridade referencial e regras de negócio.

---

## 📋 ESTRUTURA DE ARQUIVOS CRIADOS

```
app/motochefe/
├── services/
│   └── importacao_carga_inicial.py    # Service com lógica de importação
├── routes/
│   ├── __init__.py                     # Registro da rota (atualizado)
│   └── carga_inicial.py                # Rotas HTTP
└── templates/motochefe/
    └── carga_inicial/
        └── index.html                  # Interface web
```

---

## 🚀 COMO USAR

### 1️⃣ ACESSAR A TELA

```
URL: http://localhost:5000/motochefe/carga-inicial
```

Ou pelo menu do sistema MotoChefe (adicionar link no dashboard).

### 2️⃣ PROCESSO DE IMPORTAÇÃO

O sistema funciona em **3 fases sequenciais**:

#### **FASE 1: Configurações Base** (sem dependências)
- ✅ Equipes de Vendas
- ✅ Transportadoras
- ✅ Empresas Vendedoras (contas bancárias)
- ✅ CrossDocking (apenas 1 registro)
- ✅ Custos Operacionais (apenas 1 registro)

#### **FASE 2: Cadastros Dependentes**
- ✅ Vendedores (→ depende de Equipes)
- ✅ Modelos de Motos (catálogo)

#### **FASE 3: Produtos e Clientes**
- ✅ Clientes (→ depende de Vendedores)
- ✅ Motos (→ depende de Modelos)

### 3️⃣ PASSO A PASSO

1. **Baixar templates** de cada fase
2. **Preencher planilhas** com seus dados históricos
3. **Importar fase 1** completa
4. **Importar fase 2** (habilitado após fase 1)
5. **Importar fase 3** (habilitado após fase 2)
6. **Verificar resultados** em cada etapa

---

## 📊 ESTRUTURA DAS PLANILHAS

### FASE 1 - TEMPLATE

#### Aba: 1_Equipes
| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `equipe_vendas` | Texto | ✅ | "Equipe Sul" | Nome da equipe |
| `responsavel_movimentacao` | Texto | ❌ | "NACOM" | Responsável pela movimentação |
| `custo_movimentacao` | Decimal | ❌ | 500.00 | Custo de movimentação (R$) |
| `incluir_custo_movimentacao` | Boolean | ❌ | SIM/NAO | Adicionar ao preço final? |
| `tipo_precificacao` | Texto | ❌ | "TABELA" | TABELA ou CUSTO_MARKUP |
| `markup` | Decimal | ❌ | 1000.00 | Markup fixo (R$) |
| `tipo_comissao` | Texto | ❌ | "FIXA_EXCEDENTE" | FIXA_EXCEDENTE ou PERCENTUAL |
| `valor_comissao_fixa` | Decimal | ❌ | 200.00 | Comissão fixa (R$) |
| `percentual_comissao` | Decimal | ❌ | 5.00 | Percentual (%) |
| `comissao_rateada` | Boolean | ❌ | SIM | Rateio entre vendedores? |
| `permitir_montagem` | Boolean | ❌ | SIM | Permitir montagem? |
| `permitir_prazo` | Boolean | ❌ | NAO | Permitir prazo de pagamento? |
| `permitir_parcelamento` | Boolean | ❌ | NAO | Permitir parcelamento? |

#### Aba: 2_Transportadoras
| Campo | Tipo | Obrigatório | Exemplo |
|-------|------|-------------|---------|
| `transportadora` | Texto | ✅ | "Transportes ABC" |
| `cnpj` | Texto | ❌ | "12.345.678/0001-90" |
| `telefone` | Texto | ❌ | "(11) 98765-4321" |
| `chave_pix` | Texto | ❌ | "123456789" |
| `banco` | Texto | ❌ | "Banco do Brasil" |
| `cod_banco` | Texto | ❌ | "001" |
| `agencia` | Texto | ❌ | "1234" |
| `conta` | Texto | ❌ | "56789-0" |

#### Aba: 3_Empresas
| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `empresa` | Texto | ✅ | "Sogima Motos" | Nome da empresa |
| `cnpj_empresa` | Texto | ❌ | "98.765.432/0001-10" | CNPJ |
| `chave_pix` | Texto | ❌ | "987654321" | Chave PIX |
| `banco` | Texto | ❌ | "Itaú" | Nome do banco |
| `cod_banco` | Texto | ❌ | "341" | Código do banco |
| `agencia` | Texto | ❌ | "5678" | Agência |
| `conta` | Texto | ❌ | "12345-6" | Conta |
| `tipo_conta` | Texto | ❌ | "FABRICANTE" | FABRICANTE, OPERACIONAL, MARGEM_SOGIMA |
| `baixa_compra_auto` | Boolean | ❌ | SIM | Baixa automática de compras? |
| `saldo` | Decimal | ❌ | 50000.00 | Saldo inicial (R$) |

#### Aba: 4_CrossDocking (APENAS 1 LINHA)
| Campo | Tipo | Exemplo |
|-------|------|---------|
| `nome` | Texto | "CrossDocking Genérico" |
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
| Campo | Tipo | Obrigatório | Exemplo |
|-------|------|-------------|---------|
| `vendedor` | Texto | ✅ | "João Silva" |
| `equipe_vendas` | Texto | ✅ | "Equipe Sul" |

#### Aba: 2_Modelos
| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `nome_modelo` | Texto | ✅ | "Voltz EV1" | Nome do modelo |
| `potencia_motor` | Texto | ✅ | "2000W" | Potência (ex: 1000W, 2000W, 3000W) |
| `autopropelido` | Boolean | ❌ | SIM | É autopropelido? |
| `preco_tabela` | Decimal | ✅ | 8500.00 | Preço de tabela (R$) |
| `descricao` | Texto | ❌ | "Moto elétrica cargo" | Descrição |

---

### FASE 3 - TEMPLATE

#### Aba: 1_Clientes
| Campo | Tipo | Obrigatório | Exemplo |
|-------|------|-------------|---------|
| `cnpj_cliente` | Texto | ✅ | "11.222.333/0001-44" |
| `cliente` | Texto | ✅ | "Empresa XYZ Ltda" |
| `vendedor` | Texto | ✅ | "João Silva" |
| `crossdocking` | Boolean | ❌ | NAO |
| `endereco_cliente` | Texto | ❌ | "Rua ABC" |
| `numero_cliente` | Texto | ❌ | "123" |
| `complemento_cliente` | Texto | ❌ | "Sala 45" |
| `bairro_cliente` | Texto | ❌ | "Centro" |
| `cidade_cliente` | Texto | ❌ | "São Paulo" |
| `estado_cliente` | Texto | ❌ | "SP" |
| `cep_cliente` | Texto | ❌ | "01310-100" |
| `telefone_cliente` | Texto | ❌ | "(11) 3456-7890" |
| `email_cliente` | Texto | ❌ | "contato@xyz.com.br" |

#### Aba: 2_Motos
| Campo | Tipo | Obrigatório | Exemplo | Descrição |
|-------|------|-------------|---------|-----------|
| `numero_chassi` | Texto | ✅ | "9BWZZZ377VT004251" | Chassi (até 30 chars) |
| `numero_motor` | Texto | ❌ | "MOTOR123456" | Motor (único se preenchido) |
| `nome_modelo` | Texto | ✅ | "Voltz EV1" | Nome do modelo (deve existir) |
| `cor` | Texto | ✅ | "Branco" | Cor da moto |
| `ano_fabricacao` | Inteiro | ❌ | 2024 | Ano de fabricação |
| `nf_entrada` | Texto | ✅ | "NF-001234" | NF de compra |
| `data_nf_entrada` | Data | ✅ | 15/01/2025 | Data da NF |
| `data_entrada` | Data | ✅ | 16/01/2025 | Data entrada estoque |
| `fornecedor` | Texto | ✅ | "Voltz Motors" | Fornecedor |
| `custo_aquisicao` | Decimal | ✅ | 7200.00 | Custo de compra (R$) |
| `status` | Texto | ❌ | "DISPONIVEL" | DISPONIVEL, VENDIDA, RESERVADA, AVARIADO, DEVOLVIDO |
| `status_pagamento_custo` | Texto | ❌ | "PENDENTE" | PENDENTE, PAGO, PARCIAL |
| `empresa_pagadora` | Texto | ❌ | "Sogima Motos" | Nome da empresa que pagou |
| `observacao` | Texto | ❌ | "Moto revisada" | Observações gerais |
| `pallet` | Texto | ❌ | "P-001" | Localização física |

---

## ⚙️ REGRAS DE VALIDAÇÃO

### Validações Automáticas

✅ **Campos obrigatórios**: Sistema para se faltar campo marcado como obrigatório
✅ **CNPJ único**: Clientes não podem ter CNPJ duplicado
✅ **Chassi único**: Motos não podem ter chassi duplicado
✅ **Motor único**: Se preenchido, número do motor deve ser único
✅ **Foreign Keys**: Valida se entidade referenciada existe
✅ **Valores positivos**: Preços e custos devem ser > 0
✅ **Formatos de data**: Aceita dd/mm/yyyy, yyyy-mm-dd, dd-mm-yyyy

### Tratamento de Erros

🔴 **Parada imediata**: Sistema para na **primeira linha com erro crítico**
📊 **Mensagem detalhada**: Informa linha, campo e motivo do erro
🔄 **UPSERT ativo**: Pode re-executar sem duplicar dados

---

## 🔄 FUNCIONALIDADE UPSERT

O sistema usa **UPSERT** (Update + Insert) para permitir re-execução:

| Tabela | Chave de Busca | Comportamento |
|--------|----------------|---------------|
| `equipe_vendas_moto` | `equipe_vendas` | Atualiza se nome existir |
| `transportadora_moto` | `transportadora` | Atualiza se nome existir |
| `empresa_venda_moto` | `empresa` | Atualiza se nome existir |
| `cross_docking` | Único registro | Sempre atualiza o primeiro |
| `vendedor_moto` | `vendedor` | Atualiza se nome existir |
| `modelo_moto` | `nome_modelo` | Atualiza se nome existir |
| `cliente_moto` | `cnpj_cliente` | Atualiza se CNPJ existir |
| `moto` | `numero_chassi` | Atualiza se chassi existir |

**Vantagem:** Permite corrigir dados e re-importar sem duplicar registros.

---

## 📝 EXEMPLO DE USO REAL

### Cenário: Importar histórico de 100 motos vendidas

**Passo 1:** Preparar dados do sistema antigo (Excel)
**Passo 2:** Baixar templates e preencher:
- Fase 1: 2 equipes, 3 transportadoras, 1 empresa
- Fase 2: 5 vendedores, 3 modelos
- Fase 3: 50 clientes, 100 motos

**Passo 3:** Importar Fase 1
✅ Resultado: Equipes, transportadoras e empresas criadas

**Passo 4:** Importar Fase 2
✅ Resultado: Vendedores vinculados às equipes, modelos cadastrados

**Passo 5:** Importar Fase 3
✅ Resultado: Clientes vinculados aos vendedores, motos cadastradas com modelos

**Tempo estimado:** 15-30 minutos (dependendo da preparação dos dados)

---

## 🛠️ SCRIPTS DE MIGRAÇÃO

Veja os arquivos:
- `migrations/carga_inicial_motochefe_local.py` - Execução local
- `migrations/carga_inicial_motochefe_render.sql` - Execução no Render

---

## ⚠️ LIMITAÇÕES ATUAIS

### Fase 4, 5 e 6 NÃO IMPLEMENTADAS

Por decisão de escopo, as fases avançadas **NÃO foram implementadas**:

❌ **Fase 4:** Pedidos e Vendas
❌ **Fase 5:** Títulos Financeiros e Comissões
❌ **Fase 6:** Embarques e Movimentações

**Motivo:** Estes dados são gerados através de **regras de negócio complexas** e **gatilhos automáticos** do sistema. É mais seguro criar os pedidos manualmente pelo sistema operacional do que importar títulos financeiros prontos.

**Recomendação:** Após importar Fase 1-3, use o sistema normalmente para criar pedidos, que gerarão automaticamente:
- Títulos financeiros
- Comissões
- Títulos a pagar
- Movimentações

---

## 🔧 TROUBLESHOOTING

### Erro: "Equipe não encontrada"
**Causa:** Tentou importar vendedor antes de criar equipes
**Solução:** Importe Fase 1 completa primeiro

### Erro: "CNPJ duplicado"
**Causa:** CNPJ já existe no banco
**Solução:** Use UPSERT (sistema atualiza automaticamente) ou remova duplicata

### Erro: "Modelo não encontrado"
**Causa:** Nome do modelo na planilha não bate com cadastro
**Solução:** Verifique se nome está EXATAMENTE igual (case-sensitive)

### Erro: "Número de motor duplicado"
**Causa:** Mesmo número de motor em motos diferentes
**Solução:** Deixe campo vazio ou corrija numeração

---

## 📞 SUPORTE

Para dúvidas ou problemas:
1. Consulte os logs detalhados na tela de importação
2. Verifique a linha exata do erro informada
3. Revise o campo indicado na mensagem de erro
4. Se necessário, consulte este documento ou o código-fonte

---

## 📜 HISTÓRICO DE VERSÕES

| Versão | Data | Alterações |
|--------|------|------------|
| 1.0 | 14/10/2025 | Versão inicial - Fases 1, 2 e 3 |

---

**FIM DA DOCUMENTAÇÃO**
