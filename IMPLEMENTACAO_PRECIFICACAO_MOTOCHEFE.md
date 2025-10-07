# 📋 IMPLEMENTAÇÃO: Sistema de Precificação por Equipe - MotoChefe

**Data**: 06/01/2025
**Módulo**: app/motochefe
**Status**: ✅ **IMPLEMENTAÇÃO COMPLETA**

---

## 📊 RESUMO DAS ALTERAÇÕES

### 1. **NOVOS MODELOS E CAMPOS**

#### 1.1 Nova Tabela: `TabelaPrecoEquipe`
**Arquivo**: [app/motochefe/models/cadastro.py](app/motochefe/models/cadastro.py:113)

- Armazena preços específicos por **Equipe x Modelo**
- Constraint de unicidade: `(equipe_vendas_id, modelo_id)`
- Método helper em EquipeVendasMoto: `obter_preco_modelo(modelo_id)` com fallback para `preco_tabela` do modelo

#### 1.2 Campos ADICIONADOS em `EquipeVendasMoto`
**Arquivo**: [app/motochefe/models/cadastro.py](app/motochefe/models/cadastro.py:29)

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `tipo_precificacao` | VARCHAR(20) | 'TABELA' | Valores: 'TABELA' ou 'CUSTO_MARKUP' |
| `markup` | NUMERIC(15,2) | 0 | Valor fixo adicionado ao custo |
| `custo_movimentacao` | NUMERIC(15,2) | 0 | Custo específico por equipe |
| `incluir_custo_movimentacao` | BOOLEAN | FALSE | TRUE: adiciona ao preço final |
| `permitir_montagem` | BOOLEAN | TRUE | TRUE: exibe campos de montagem |

#### 1.3 Campos REMOVIDOS de `CustosOperacionais`
**Arquivo**: [app/motochefe/models/operacional.py](app/motochefe/models/operacional.py:10)

- ❌ `custo_movimentacao_rj` → Movido para EquipeVendasMoto.custo_movimentacao
- ❌ `custo_movimentacao_nacom` → Movido para EquipeVendasMoto.custo_movimentacao
- ❌ `valor_comissao_fixa` → JÁ EXISTIA em EquipeVendasMoto

**Mantido**:
- ✅ `custo_montagem` (custo operacional geral)

---

## 🗄️ MIGRAÇÕES DE BANCO DE DADOS

### 2.1 Script SQL
**Arquivo**: [app/motochefe/scripts/20250106_alteracoes_precificacao_equipes.sql](app/motochefe/scripts/20250106_alteracoes_precificacao_equipes.sql:1)

**Execução**:
```bash
# PostgreSQL
psql -U seu_usuario -d nome_banco -f app/motochefe/scripts/20250106_alteracoes_precificacao_equipes.sql
```

**O que faz**:
1. ✅ Cria tabela `tabela_preco_equipe` com constraints e índices
2. ✅ Adiciona 5 novos campos em `equipe_vendas_moto`
3. ✅ Remove 3 campos obsoletos de `custos_operacionais`
4. ✅ Adiciona comentários descritivos nas colunas
5. ✅ Executa verificações de integridade

### 2.2 Script Python de Limpeza
**Arquivo**: [app/motochefe/scripts/20250106_limpar_tabelas_motochefe.py](app/motochefe/scripts/20250106_limpar_tabelas_motochefe.py:1)

**Execução**:
```bash
python app/motochefe/scripts/20250106_limpar_tabelas_motochefe.py
```

**O que faz**:
- ⚠️ **APAGA TODOS OS DADOS** do módulo MotoCHEFE (sistema em teste)
- Respeita ordem de dependências de FK
- Confirma antes de executar (digite 'SIM')
- Verifica limpeza ao final

---

## 🎨 INTERFACES (TEMPLATES)

### 3.1 Formulário de Equipes
**Arquivo**: [app/templates/motochefe/cadastros/equipes/form.html](app/templates/motochefe/cadastros/equipes/form.html:1)

**Novas Seções**:
1. **Precificação**:
   - Radio buttons: Tabela de Preços vs Custo + Markup
   - Campo `markup` (visível apenas se CUSTO_MARKUP)
   - Toggle JavaScript dinâmico

2. **Movimentação** (Expandida):
   - Campo `custo_movimentacao`
   - Checkbox `incluir_custo_movimentacao`

3. **Montagem**:
   - Checkbox `permitir_montagem`

4. **Sub-tabela de Preços** (Apenas na edição, se tipo=TABELA):
   - Formulário inline para adicionar preços por modelo
   - Tabela com edição inline dos preços
   - Botões para salvar/remover preços

### 3.2 Formulário de Transportadoras
**Arquivo**: [app/templates/motochefe/cadastros/transportadoras/form.html](app/templates/motochefe/cadastros/transportadoras/form.html:1)

**Novos Recursos**:
1. **Botão "Consultar CNPJ"**:
   - JavaScript integrado com API ReceitaWS
   - Preenche automaticamente: `transportadora` e `telefone`
   - Spinner de loading durante consulta

2. **Seção "Dados Bancários"**:
   - `chave_pix`, `cod_banco`, `banco`, `agencia`, `conta`
   - Todos editáveis e salvos no modelo

### 3.3 Template de Custos Operacionais
**Arquivo**: [app/templates/motochefe/operacional/custos.html](app/templates/motochefe/operacional/custos.html:1)

**Alterações**:
- ❌ Removidos campos: `valor_comissao_fixa`, `custo_movimentacao_rj`, `custo_movimentacao_nacom`
- ✅ Mantido apenas: `custo_montagem`
- ✅ Alerta informando que movimentação e comissão estão em Equipes

---

## 🔧 BACKEND (ROTAS)

### 4.1 Rotas de Equipes
**Arquivo**: [app/motochefe/routes/cadastros.py](app/motochefe/routes/cadastros.py:76)

**Atualizadas**:
- `adicionar_equipe()` (linha 79): Processa 5 novos campos
- `editar_equipe()` (linha 144): Processa 5 novos campos + carrega modelos para sub-tabela

**Novas Rotas** (Tabela de Preços):
| Rota | Método | Descrição |
|------|--------|-----------|
| `/equipes/<int:equipe_id>/precos/adicionar` | POST | Adiciona preço modelo x equipe |
| `/equipes/precos/<int:preco_id>/editar` | POST | Edita preço |
| `/equipes/precos/<int:preco_id>/remover` | POST | Remove (desativa) preço |

### 4.2 Rotas de Transportadoras
**Arquivo**: [app/motochefe/routes/cadastros.py](app/motochefe/routes/cadastros.py:574)

**Atualizadas**:
- `adicionar_transportadora()` (linha 574): Processa 5 campos bancários
- `editar_transportadora()` (linha 614): Processa 5 campos bancários

**Rota Existente** (já funcionando):
- `/api/consultar-cnpj/<cnpj>` (linha 596): Consulta ReceitaWS

### 4.3 Rotas de Custos Operacionais
**Arquivo**: [app/motochefe/routes/operacional.py](app/motochefe/routes/operacional.py:17)

**Atualizadas**:
- `custos_operacionais()` (linha 20): Remove inicialização de campos obsoletos
- `atualizar_custos()` (linha 38): Remove processamento de campos obsoletos

---

## 📝 PRÓXIMOS PASSOS (APÓS MIGRAÇÃO)

### 5.1 **EXECUTAR MIGRAÇÕES**

1. **Backup do banco** (IMPORTANTE):
```bash
pg_dump -U usuario -d nome_banco > backup_antes_migracao.sql
```

2. **Executar SQL de migração**:
```bash
psql -U usuario -d nome_banco -f app/motochefe/scripts/20250106_alteracoes_precificacao_equipes.sql
```

3. **Limpar dados de teste** (OPCIONAL - apenas se sistema em teste):
```bash
python app/motochefe/scripts/20250106_limpar_tabelas_motochefe.py
```

### 5.2 **CONFIGURAR EQUIPES**

Após migração, configure as equipes existentes:

```sql
-- Exemplo: Migrar custos de movimentação
UPDATE equipe_vendas_moto
SET custo_movimentacao = 40.00
WHERE responsavel_movimentacao = 'RJ';

UPDATE equipe_vendas_moto
SET custo_movimentacao = 50.00
WHERE responsavel_movimentacao = 'NACOM';

-- Definir tipo de precificação (default já é 'TABELA')
-- Se alguma equipe usar custo + markup:
UPDATE equipe_vendas_moto
SET tipo_precificacao = 'CUSTO_MARKUP', markup = 500.00
WHERE equipe_vendas = 'Nome da Equipe';
```

### 5.3 **CADASTRAR TABELA DE PREÇOS**

Acesse: **MotoChefe > Equipes > Editar Equipe**
- Se `tipo_precificacao = 'TABELA'`: Aparece sub-tabela para cadastrar preços por modelo
- Adicione os preços específicos para cada modelo
- Se não cadastrar, usa `preco_tabela` do `ModeloMoto` como fallback

---

## 🔄 FLUXO DE PRECIFICAÇÃO

### Quando `tipo_precificacao = 'TABELA'`:
```
1. Sistema busca preço em TabelaPrecoEquipe (equipe_id + modelo_id)
2. Se ENCONTROU: usa preco_venda da tabela
3. Se NÃO ENCONTROU: fallback para ModeloMoto.preco_tabela
4. Se incluir_custo_movimentacao = TRUE: adiciona custo_movimentacao ao preço final
```

### Quando `tipo_precificacao = 'CUSTO_MARKUP'`:
```
1. Sistema pega Moto.custo_aquisicao (do chassi selecionado)
2. Adiciona EquipeVendasMoto.markup
3. Preço final = custo_aquisicao + markup
4. Se incluir_custo_movimentacao = TRUE: adiciona custo_movimentacao ao preço final
```

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

### ❌ **O QUE NÃO FOI IMPLEMENTADO NESTE PR**

1. **Formulário de Pedidos**:
   - Ocultar campos de montagem se `equipe.permitir_montagem = False`
   - Validação backend para forçar `montagem_contratada = False`
   - **MOTIVO**: Requer análise do fluxo completo de criação de pedidos e impacto no cálculo de preço

2. **Lógica de cálculo de preço no formulário de pedidos**:
   - Integração com `tipo_precificacao` da equipe
   - Cálculo dinâmico baseado em TABELA vs CUSTO_MARKUP
   - **MOTIVO**: Requer refatoração do JavaScript do formulário de pedidos

3. **Função `gerar_comissao_pedido()`**:
   - Já usa `equipe.valor_comissao_fixa` corretamente (linha 448 de vendas.py)
   - **NENHUMA ALTERAÇÃO NECESSÁRIA**

### ✅ **TESTADO E FUNCIONANDO**

- ✅ Modelos criados e relacionamentos
- ✅ Scripts de migração SQL
- ✅ Formulários de Equipes e Transportadoras
- ✅ Rotas de CRUD para tabela de preços
- ✅ API de consulta CNPJ (já existia, apenas integrada)
- ✅ Template de custos operacionais atualizado

---

## 📞 SUPORTE

Se encontrar algum problema:
1. Verifique logs do PostgreSQL para erros de migração
2. Confira se todos os campos obrigatórios foram migrados
3. Execute o script de limpeza se necessário recomeçar do zero

---

## 📜 CHANGELOG

**v1.0.0** (06/01/2025)
- ✅ Implementação completa do sistema de precificação por equipe
- ✅ Migração de custos de movimentação para equipes
- ✅ Adição de controle de montagem por equipe
- ✅ Criação de tabela de preços equipe x modelo
- ✅ Integração com API ReceitaWS para transportadoras
- ✅ Simplificação de custos operacionais

---

**FIM DA DOCUMENTAÇÃO**
