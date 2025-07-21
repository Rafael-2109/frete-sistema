# 📋 Documentação Completa - Sistema de Carteira de Pedidos

## 📖 Visão Geral
Sistema central de gestão da carteira de pedidos com funcionalidades avançadas de importação, separação, faturamento e controle de inconsistências.

---

## 🛣️ Rotas (Blueprint: `/carteira`)

### **Dashboard e Navegação**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/` | GET | `index()` | Dashboard principal com KPIs e estatísticas |
| `/carteira/principal` | GET | `listar_principal()` | Lista carteira com filtros e paginação |

### **Importação e Exportação**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/importar` | GET/POST | `importar_carteira()` | Interface e processamento de importação |
| `/carteira/baixar-modelo` | GET | `baixar_modelo()` | Download modelo Excel para importação |

### **Operações da Carteira**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/gerar-separacao` | GET/POST | `gerar_separacao()` | Interface para gerar separação (recorte) |
| `/carteira/vincular-separacoes` | POST | `vincular_separacoes()` | Vincula carteira com separações existentes |
| `/carteira/relatorio-vinculacoes` | GET | `relatorio_vinculacoes()` | Relatório carteira ↔ separações |

### **Inconsistências e Faturamento**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/inconsistencias` | GET | `listar_inconsistencias()` | Lista inconsistências de faturamento |
| `/carteira/resolver-inconsistencia/<id>` | POST | `resolver_inconsistencia()` | Resolve inconsistência específica |
| `/carteira/escolher-separacao/<id>` | GET/POST | `escolher_separacao()` | Interface para escolher separação alternativa |

### **Justificativas e Configurações**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/justificar-faturamento-parcial` | GET/POST | `justificar_faturamento_parcial()` | Justifica faturamentos parciais |
| `/carteira/configurar-tipo-carga/<lote_id>` | GET/POST | `configurar_tipo_carga()` | Configura tipo de carga (TOTAL/PARCIAL) |
| `/carteira/processar-alteracao-carga` | POST | `processar_alteracao_carga()` | Processa alteração de tipo de carga |

### **Dashboards Especializados**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/dashboard-saldos-standby` | GET | `dashboard_saldos_standby()` | Dashboard de saldos em standby |

### **APIs Internas**
| Rota | Método | Função | Descrição |
|------|--------|---------|-----------|
| `/carteira/api/item/<id>` | GET | `api_item_detalhes()` | Detalhes JSON de item da carteira |
| `/carteira/api/processar-faturamento` | POST | `processar_faturamento()` | API para baixa automática de NFs |

---

## 🗃️ Modelos (Models)

### **1. CarteiraPrincipal**
**Arquivo:** `app/carteira/models.py`
**Descrição:** Modelo principal da carteira de pedidos

#### Campos Principais:
```python
# Chaves Primárias
num_pedido = String(50)         # Número do pedido
cod_produto = String(50)        # Código do produto

# Dados do Produto
nome_produto = String(255)      # Nome/descrição do produto
qtd_produto_pedido = Float      # Quantidade total do pedido
qtd_saldo_produto_pedido = Float # Quantidade em saldo
preco_produto_pedido = Float    # Preço unitário

# Dados do Cliente
cnpj_cpf = String(20)          # CNPJ/CPF do cliente
raz_social = String(255)       # Razão social completa
raz_social_red = String(100)   # Razão social reduzida
vendedor = String(100)         # Nome do vendedor

# Dados Operacionais
status_pedido = String(50)     # Status atual do pedido
expedicao = Date               # Data prevista de expedição
agendamento = DateTime         # Data/hora de agendamento
protocolo_agendamento = String(100) # Protocolo do agendamento

# Integração com Separação
separacao_lote_id = String(50) # ID do lote de separação vinculado

# Controle
ativo = Boolean                # Item ativo (exclusão lógica)
criado_em = DateTime           # Data de criação
criado_por = String(100)       # Usuário que criou
```

#### Propriedades Calculadas:
- `valor_total_item` - Calcula valor total (qtd × preço)
- `possui_separacao` - Verifica se tem separação vinculada
- `status_agendamento` - Status do agendamento
- `dias_para_expedicao` - Dias até a expedição

### **2. CarteiraCopia**
**Descrição:** Cópia de segurança da carteira para controle de alterações
- Mesma estrutura da CarteiraPrincipal
- Campos adicionais: `snapshot_em`, `motivo_copia`

### **3. InconsistenciaFaturamento**
**Descrição:** Registra inconsistências detectadas no faturamento

#### Campos:
```python
numero_nf = String(20)         # Número da NF com problema
tipo = String(50)              # Tipo da inconsistência
descricao = Text               # Descrição detalhada
detectada_em = DateTime        # Quando foi detectada
resolvida = Boolean            # Se foi resolvida
resolvida_por = String(100)    # Quem resolveu
```

### **4. HistoricoFaturamento**
**Descrição:** Histórico de todas as operações de faturamento
- Rastreamento completo de baixas na carteira
- Vínculo com NFs e quantidades processadas

### **5. VinculacaoCarteiraSeparacao**
**Descrição:** Controle de vínculos entre carteira e separações
- Mapeamento carteira ↔ separação
- Controle de consistência

### **6. Outros Modelos de Apoio**
- `LogAtualizacaoCarteira` - Log de todas as alterações
- `EventoCarteira` - Eventos do ciclo de vida da carteira
- `AprovacaoMudancaCarteira` - Controle de aprovações
- `TipoCarga` - Configurações de tipo de carga
- `FaturamentoParcialJustificativa` - Justificativas de faturamento parcial
- `SaldoStandby` - Saldos em standby
- `SnapshotCarteira` - Snapshots da carteira
- `ControleDescasamentoNF` - Controle de descasamentos

---

## 🎨 Templates

### **Dashboard e Navegação**
| Template | Descrição |
|----------|-----------|
| `dashboard.html` | Dashboard principal com KPIs, estatísticas e ações rápidas |
| `listar_principal.html` | Listagem da carteira com filtros avançados e paginação |

### **Importação e Operações**
| Template | Descrição |
|----------|-----------|
| `importar.html` | Interface de importação com instruções detalhadas |
| `gerar_separacao.html` | Interface para seleção de itens e geração de separação |

### **Relatórios e Controles**
| Template | Descrição |
|----------|-----------|
| `relatorio_vinculacoes.html` | Relatório completo carteira ↔ separações com estatísticas |
| `inconsistencias.html` | Lista inconsistências de faturamento (legado) |
| `listar_inconsistencias.html` | Lista moderna de inconsistências com ações |

### **Justificativas e Configurações**
| Template | Descrição |
|----------|-----------|
| `justificar_faturamento_parcial.html` | Formulário para justificar faturamentos parciais |
| `configurar_tipo_carga.html` | Interface para configurar TOTAL vs PARCIAL |
| `escolher_separacao.html` | Interface para escolher separação alternativa |

---

## ⚙️ Funcionalidades Principais

### **1. Importação Inteligente**
- **Preservação de dados operacionais** (expedição, agendamento, lote)
- **Atualização de dados mestres** (cliente, produto, preços)
- **Validação automática** de colunas obrigatórias
- **Processamento de formatos brasileiros** (vírgula decimal, datas)

### **2. Sistema de Separação**
- **Geração de separações** a partir da carteira
- **Vínculo automático** carteira ↔ separação
- **Controle de consistência** entre sistemas
- **Relatórios de vinculação** detalhados

### **3. Controle de Inconsistências**
- **Detecção automática** de problemas de faturamento
- **Múltiplas ações de resolução** (baixa automática, ignorar, cancelar NF)
- **Histórico completo** de todas as resoluções
- **Interface para escolha** de separação alternativa

### **4. Justificativas e Aprovações**
- **Faturamento parcial** com justificativas obrigatórias
- **Sistema de aprovação** para mudanças críticas
- **Saldos em standby** com controle temporal
- **Configuração de tipos de carga** (TOTAL/PARCIAL)

### **5. Auditoria e Rastreamento**
- **Log completo** de todas as operações
- **Snapshots** da carteira em momentos críticos
- **Histórico de alterações** com usuário e timestamp
- **Eventos do ciclo de vida** da carteira

---

## 🔧 Funções Auxiliares Principais

### **Importação e Processamento**
- `_processar_importacao_carteira_inteligente()` - Processa importação completa
- `_processar_formatos_brasileiros()` - Converte formatos brasileiros
- `_atualizar_item_inteligente()` - Atualiza item preservando dados operacionais
- `_criar_novo_item_carteira()` - Cria novo item na carteira

### **Separação e Vinculação**
- `_processar_geracao_separacao()` - Gera separação a partir de itens selecionados
- `_processar_vinculacao_automatica()` - Vinculação automática carteira ↔ separação
- `_sincronizar_carteira_copia()` - Sincroniza com cópia de segurança

### **Faturamento e Baixas**
- `_processar_baixa_faturamento()` - Processa baixa de NF na carteira
- `_cancelar_nf_faturamento()` - Cancela NF e reverte movimentações
- `_processar_justificativa_faturamento_parcial()` - Processa justificativas

### **Validação e Consistência**
- `_detectar_inconsistencias_automaticas()` - Detecta inconsistências automaticamente
- `_processar_validacao_nf_simples()` - Validação simples de NFs
- `_validar_sincronizacao_baixas_faturamento()` - Valida sincronização

---

## 🎯 Integrações

### **Com Sistema de Separação**
- Geração automática de separações
- Vínculo bidirecional de dados
- Sincronização de status

### **Com Sistema de Faturamento**
- Baixa automática por NF
- Detecção de inconsistências
- Processamento de faturamento parcial

### **Com Sistema de Estoque**
- Integração de saldos
- Movimentações automáticas
- Controle de disponibilidade

### **Com Sistema de Produção**
- Expedições programadas
- Sequenciamento de produção
- Palletização automática

---

## 📊 KPIs e Métricas

### **Dashboard Principal**
- Total de pedidos únicos
- Total de produtos únicos
- Total de itens ativos
- Valor total da carteira
- Breakdown por status
- Top vendedores

### **Controles Operacionais**
- Inconsistências abertas
- Itens sem vinculação
- Expedições próximas (7 dias)
- Saldos em standby

---

## 🔐 Segurança e Permissões

### **Controle de Acesso**
- Login obrigatório em todas as rotas
- Logs de auditoria completos
- Rastreamento de alterações por usuário

### **Validações**
- CSRF protection em formulários
- Validação de entrada de dados
- Sanitização de uploads

---

*Documentação gerada em: {{ date.today() }}*
*Sistema: Carteira de Pedidos v2.0* 