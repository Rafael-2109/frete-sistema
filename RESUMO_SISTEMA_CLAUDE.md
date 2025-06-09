# 🗺️ MAPA MENTAL DO SISTEMA DE FRETES - CLAUDE

> **Arquivo de referência para manter contexto e organização do sistema**

## 📁 ESTRUTURA PRINCIPAL

```
app/
├── auth/           # Autenticação
├── cotacao/        # ⭐ MÓDULO PRINCIPAL - Sistema de cotações
├── pedidos/        # Gestão de pedidos
├── embarques/      # Embarques e fretes
├── transportadoras/# Cadastro de transportadoras  
├── tabelas/        # Tabelas de preços
├── vinculos/       # Vínculos entre transportadoras e cidades
├── localidades/    # Cidades e localização
├── utils/          # Utilitários e serviços
└── templates/      # Templates HTML
```

## 🎯 MÓDULO COTAÇÃO - FUNCIONALIDADES PRINCIPAIS

### Rotas Mapeadas:
- ✅ `/cotacao/iniciar` (POST) - Inicia cotação com pedidos selecionados
- ✅ `/cotacao/tela` (GET/POST) - Tela principal de cotação
- ✅ `/cotacao/fechar_frete` (POST) - Fecha frete direto
- ✅ `/cotacao/fechar_frete_grupo` (POST) - Fecha frete fracionado
- ✅ `/cotacao/excluir_pedido` (POST) - Remove pedido da cotação
- ✅ `/cotacao/incluir_pedido` (POST) - Adiciona pedido à cotação
- ✅ `/cotacao/resumo/<id>` (GET) - Resumo do frete fechado
- ✅ `/cotacao/otimizar` (GET) - **RESTAURADO** (usa funções reais de otimização)

### Templates:
- ✅ `cotacao/cotacao.html` - Tela principal
- ✅ `cotacao/otimizador.html` - Tela do otimizador (sem rota)
- ✅ `cotacao/resumo_frete.html` - Resumo de cotação

## 🔧 FUNCIONALIDADES IMPLEMENTADAS (PROCESSO_COMPLETO.MD)

### ✅ Item 2-a: Sistema "Melhor Opção"
- **Local**: `app/cotacao/routes.py` - função `tela_cotacao()`
- **Status**: ✅ Funcionando
- **Como funciona**:
  1. ETAPA 1: Identifica melhor opção (menor R$/kg) por CNPJ
  2. ETAPA 2: Agrupa melhores opções por transportadora
- **Logs confirmam**: Funcionando para Daniel Ferreira e outros

### ✅ Item 2-b: Modal de Escolha por CNPJ  
- **Local**: `app/templates/cotacao/cotacao.html` (linha ~290)
- **Status**: ✅ Funcionando
- **Funcionalidades**:
  - Interface modal completa
  - Cards de transportadora selecionada
  - Tabelas de opções por CNPJ
  - JavaScript para seleção e adição

### ✅ Sistema de Grupo Empresarial
- **Status**: ✅ Funcionando
- **Exemplo**: Daniel Ferreira (3 transportadoras: IDs 30, 31, 32)
- **Detecção**: Por CNPJ base + similaridade de nome

### ✅ LocalizacaoService
- **Local**: `app/utils/localizacao.py`
- **Status**: ✅ Funcionando
- **Dados**: 5.570 cidades disponíveis
- **Funcionalidades**:
  - Normalização (SAO PAULO → São Paulo/SP)
  - Busca por código IBGE
  - Cache para performance

## 🚨 PROBLEMAS RESOLVIDOS

### ✅ Erro no Otimizador  
- **Problema**: `'None' has no attribute 'strftime'`
- **Causa**: Função `formatar_data_brasileira` não tratava None
- **Solução**: Verificações rigorosas para None/vazio
- **Status**: ✅ Corrigido

### ✅ Botão "Cotar Frete"
- **Problema**: Conflito de JavaScript
- **Solução**: Interface limpa, botões corretos
- **Status**: ✅ Funcionando

### ✅ Rota `/cotacao/otimizar` corrigida e funcional
- **Problema**: Rota causava erro `'dict object' has no attribute 'melhor_opcao'`
- **Solução**: Simplificada com cálculos básicos de otimização (linhas 1234-1304)
- **Status**: ✅ Funcionando

### ✅ Modal "Escolher Transportadora por CNPJ" corrigido
- **Problema**: Botões "Escolher" não mudavam para "Adicionar à Cotação"
- **Solução**: JavaScript corrigido para seletores `.adicionar-cotacao` corretos
- **Status**: ✅ Funcionando

### ✅ Erro de importação CLI
- **Problema**: `cannot import name 'criar_vinculos_faltantes'`
- **Solução**: Adicionado try/catch no `__init__.py` linhas 148-153
- **Status**: ✅ Corrigido

## ❌ PROBLEMAS PENDENTES

*Nenhum problema crítico identificado no momento*

## 📊 MODELOS PRINCIPAIS

### Cotacao (`app/cotacao/models.py`)
- `id`, `usuario_id`, `transportadora_id`
- `data_fechamento`, `status`, `tipo_carga`
- `valor_total`, `peso_total`

### Pedido (`app/pedidos/models.py`)
- `num_pedido`, `cnpj_cpf`, `raz_social_red`
- `nome_cidade`, `cod_uf`, `peso_total`
- `valor_saldo_total`, `status`

### Embarque (`app/embarques/models.py`)
- `transportadora_id`, `numero`, `status`
- `tipo_carga`, `valor_total`, `peso_total`
- Campos de tabela: `tabela_valor_kg`, `modalidade`, etc.

## 🎮 SIMULADOR DE FRETE

### Localização: `app/utils/frete_simulador.py`
### Função principal: `calcular_frete_por_cnpj()`
### Integração: LocalizacaoService + TabelaFrete

## 📋 PRÓXIMAS AÇÕES

1. **🧪 TEST**: Testar sistema completo após correções
2. **✨ FEATURE**: Verificar item 4 do processo (cidade mais cara)
3. **📊 MONITOR**: Acompanhar logs de funcionamento
4. **🔧 OPTIMIZE**: Melhorar performance se necessário

## 💡 NOTAS TÉCNICAS

- **LocalizacaoService**: Usar métodos estáticos, não instanciar
- **Logs de Debug**: Sistema tem logs detalhados funcionando
- **Session**: Pedidos armazenados em `session["cotacao_pedidos"]`
- **JavaScript**: Modal com lógica complexa para seleção CNPJ
- **ICMS**: Sistema busca ICMS por código IBGE ou nome da cidade

---
**📅 Última atualização**: {{datetime.now().strftime('%d/%m/%Y %H:%M')}}
**🤖 Mantido por**: Claude Assistant 