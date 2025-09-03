# 📋 PLANO DE REFATORAÇÃO - workspace-montagem.js

## 📊 ANÁLISE ATUAL
- **Tamanho**: 2.246 linhas (muito grande!)
- **Classe principal**: WorkspaceMontagem
- **Módulos já existentes que ele usa**:
  - LoteManager
  - ModalCardex
  - PreSeparacaoManager
  - WorkspaceTabela
  - WorkspaceQuantidades

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. **Arquivo Monolítico**
- 2.246 linhas em um único arquivo
- Dificulta manutenção e debugging
- Alto acoplamento de responsabilidades

### 2. **Funções Duplicadas**
- ✅ **JÁ RESOLVIDO**: Funções de formatação delegadas para workspace-quantidades.js
- ✅ **JÁ RESOLVIDO**: calcularStatusDisponibilidade e calcularSaldoDisponivel delegados

### 3. **Múltiplas Responsabilidades**
A classe WorkspaceMontagem está fazendo MUITAS coisas:
- Gerenciamento de UI/DOM
- Chamadas de API
- Renderização de HTML
- Gerenciamento de estado
- Manipulação de modais
- Controle de seleção
- Cálculos diversos

## 🎯 OPORTUNIDADES DE MODULARIZAÇÃO

### 1. **workspace-modal-manager.js** (NOVO)
Extrair toda lógica de modais para um módulo separado:
- `mostrarModalEdicaoDatas()` (linha ~1460)
- `salvarEdicaoDatas()` (linha ~1547)
- Gerenciamento de modais Bootstrap
- Templates HTML de modais

### 2. **workspace-api.js** (NOVO)
Centralizar todas as chamadas de API:
- `fetch('/carteira/api/pedido/${numPedido}/workspace')`
- `fetch('/carteira/api/pedido/${numPedido}/pre-separacoes')`
- `fetch('/carteira/api/pedido/${numPedido}/separacoes')`
- `fetch('/carteira/api/pedido/${numPedido}/workspace-estoque')`
- Gerenciamento de AbortController
- Tratamento de erros de API

### 3. **workspace-renderer.js** (NOVO)
Extrair toda lógica de renderização HTML:
- `renderizarWorkspace()` (linha 222)
- `renderizarTabelaProdutos()` (linha 296) - já delega para workspace-tabela
- `renderizarSeparacoesConfirmadas()` (linha 304)
- `renderizarErroWorkspace()` (linha ~166)
- Templates HTML grandes

### 4. **workspace-selection.js** (NOVO)
Gerenciamento de seleção de produtos:
- `configurarCheckboxes()` (linha 559)
- `toggleProdutoSelecionado()` (linha 590)
- `atualizarSelectAll()` (linha 609)
- `limparSelecao()` (linha 731)
- `produtosSelecionados` Set

### 5. **workspace-data-manager.js** (NOVO)
Gerenciamento de estado e dados:
- `dadosProdutos` Map
- `preSeparacoes` Map
- `separacoesConfirmadas` Array
- `limparDadosAnteriores()` (linha 39)
- `coletarDadosProdutosDaTabela()` (linha 705)

### 6. **workspace-utils.js** (EXPANDIR)
Mover utilitários gerais:
- `formatarData()` (linha 493)
- `calcularDiasAte()` (linha 527)
- `getStatusClass()` (linha 467)
- `mostrarFeedback()`

## 📦 ESTRUTURA PROPOSTA

```
app/templates/carteira/js/
├── workspace/                      # NOVO diretório
│   ├── workspace-core.js          # Classe principal (reduzida)
│   ├── workspace-api.js           # Todas chamadas de API
│   ├── workspace-modal-manager.js # Gerenciamento de modais
│   ├── workspace-renderer.js      # Renderização de HTML
│   ├── workspace-selection.js     # Lógica de seleção
│   └── workspace-data-manager.js  # Gerenciamento de estado
├── workspace-montagem.js          # Arquivo principal (simplificado)
├── workspace-quantidades.js       # ✅ Já existe
├── workspace-tabela.js           # ✅ Já existe
├── lote-manager.js               # ✅ Já existe
└── pre-separacao-manager.js      # ✅ Já existe
```

## 🚀 PLANO DE EXECUÇÃO

### FASE 1: Criar Estrutura Base
1. Criar diretório `workspace/`
2. Criar arquivos base dos novos módulos
3. Configurar exports/imports

### FASE 2: Extrair Módulos (Ordem de Prioridade)
1. **workspace-api.js** - Mais fácil de extrair, menor acoplamento
2. **workspace-modal-manager.js** - Código bem isolado
3. **workspace-selection.js** - Lógica específica e isolada
4. **workspace-renderer.js** - Maior trabalho, muito HTML
5. **workspace-data-manager.js** - Precisa cuidado com estado compartilhado

### FASE 3: Refatorar workspace-montagem.js
1. Remover código movido para módulos
2. Adicionar imports dos novos módulos
3. Delegar responsabilidades
4. Reduzir para ~500 linhas (meta)

### FASE 4: Testes e Validação
1. Testar cada funcionalidade
2. Verificar performance
3. Validar que não quebrou nada

## 📈 BENEFÍCIOS ESPERADOS

1. **Manutenibilidade**: Arquivos menores, mais fáceis de entender
2. **Reusabilidade**: Módulos podem ser usados em outros lugares
3. **Testabilidade**: Módulos isolados são mais fáceis de testar
4. **Performance**: Possibilidade de lazy loading de módulos
5. **Colaboração**: Múltiplos devs podem trabalhar em módulos diferentes

## ⚠️ RISCOS E MITIGAÇÕES

### Risco 1: Quebrar funcionalidades existentes
**Mitigação**: Fazer backup, testar cada mudança incrementalmente

### Risco 2: Problemas com escopo/contexto
**Mitigação**: Usar bind() quando necessário, passar contexto explicitamente

### Risco 3: Dependências circulares
**Mitigação**: Planejar bem a hierarquia de módulos

## 📝 NOTAS IMPORTANTES

- **NÃO FAZER TUDO DE UMA VEZ**: Refatorar incrementalmente
- **MANTER COMPATIBILIDADE**: Garantir que tudo continue funcionando
- **DOCUMENTAR MUDANÇAS**: Adicionar comentários explicando delegações
- **VERSIONAR**: Fazer commits frequentes para poder reverter se necessário

## 🎯 MÉTRICA DE SUCESSO

- [ ] workspace-montagem.js com menos de 500 linhas
- [ ] Todos os módulos com responsabilidade única
- [ ] Zero duplicação de código
- [ ] Todas funcionalidades funcionando
- [ ] Código mais legível e manutenível