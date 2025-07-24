# 📋 MAPEAMENTO DE ROTAS - CHAMADAS FRONTEND

**Data de Criação**: 24/07/2025  
**Última Atualização**: 24/07/2025

Este documento mapeia TODAS as rotas que são chamadas pelo frontend (JavaScript/AJAX) no sistema.

---

## 🎯 MÓDULO CARTEIRA

### 📊 APIs de Dados e Consultas
- `/carteira/api/item/{itemId}` - GET - Obter dados de item específico
- `/carteira/api/item/{itemId}/recalcular-estoques` - POST - Recalcular estoques do item
- `/carteira/api/item/{itemId}/salvar-alteracao` - POST - Salvar alterações no item
- `/carteira/api/pedido/{numPedido}/itens` - GET - Listar itens do pedido
- `/carteira/api/pedido/{numPedido}/itens-editaveis` - GET - Listar itens editáveis do pedido
- `/carteira/api/pedido/{numPedido}/detalhes` - GET - Detalhes completos do pedido
- `/carteira/api/pedido/{numPedido}/workspace` - GET - Dados do workspace do pedido
- `/carteira/api/pedido/{numPedido}/estoque-d0-d7` - GET - Estoque projetado D0-D7
- `/carteira/api/pedido/{numPedido}/estoque-projetado-28-dias` - GET - Estoque projetado 28 dias
- `/carteira/api/produto/{codProduto}/estoque-d0-d7` - GET - Estoque D0-D7 por produto
- `/carteira/api/produto/{codProduto}/cardex` - GET - Cardex do produto
- `/carteira/api/export-excel/estoque-analise/{numPedido}` - GET - Exportar análise de estoque

### 📅 Agendamento
- `/carteira/item/{itemId}/agendamento` - GET/POST/DELETE - Gerenciar agendamento do item
- `/carteira/api/pedido/{numPedido}/agendamento-existente` - GET - Verificar agendamento existente
- `/carteira/api/pedido/{numPedido}/agendamento-info` - GET - Informações de agendamento
- `/carteira/api/pedido/{numPedido}/salvar-agendamento` - POST - Salvar agendamento do pedido
- `/carteira/api/pedido/{numPedido}/salvar-avaliacoes` - POST - Salvar avaliações do pedido

### 📍 Endereço
- `/carteira/item/{itemId}/endereco` - GET - Obter endereço de entrega
- `/carteira/item/{numPedido}/endereco` - GET - Obter endereço do pedido
- `/carteira/api/pedido/{numPedido}/endereco` - GET - API de endereço do pedido

### 📦 Separações e Lotes
- `/carteira/api/pedido/{numPedido}/separacoes` - GET - Listar separações do pedido
- `/carteira/api/pedido/{numPedido}/criar-separacao` - POST - Criar nova separação
- `/carteira/api/separacao/{loteId}/detalhes` - GET - Detalhes da separação
- `/carteira/api/separacao/{loteId}/editar` - POST - Editar separação
- `/carteira/api/separacao/criar` - POST - Criar separação direta
- `/carteira/api/agrupamentos/enviar-separacao` - POST - Enviar separação de agrupamentos

### 🏗️ Pré-Separações
- `/carteira/api/pedido/{numPedido}/pre-separacoes-agrupadas` - GET - Listar pré-separações agrupadas
- `/carteira/api/pedido/{numPedido}/criar-pre-separacao` - POST - Criar pré-separação
- `/carteira/api/pre-separacao/{preSeparacaoId}` - GET - Obter dados da pré-separação
- `/carteira/api/pre-separacao/{preSeparacaoId}/editar` - POST - Editar pré-separação
- `/carteira/api/pre-separacao/{preSeparacaoId}/cancelar` - POST - Cancelar pré-separação
- `/carteira/api/pre-separacao/{preSeparacaoId}/enviar-separacao` - POST - Enviar para separação
- `/carteira/api/pre-separacao/{preSeparacaoId}/remover` - POST - Remover pré-separação

---

## 🚚 MÓDULO EMBARQUES

- `/embarques/excluir_item/{itemId}` - DELETE - Excluir item do embarque
- `/embarques/registrar_impressao` - POST - Registrar impressão de documentos
- `/fretes/verificar_cte_embarque/{embarqueId}` - GET - Verificar CTe do embarque

---

## 💰 MÓDULO FATURAMENTO

- `/faturamento/api/modal-vinculacao?item={itemId}&tipo={tipo}` - GET - Modal de vinculação
- `/faturamento/api/modal-justificativa?item={itemId}&tipo={tipo}` - GET - Modal de justificativa
- `/faturamento/api/modal-nova-justificativa` - GET - Modal nova justificativa
- `/faturamento/inativar_nfs` - POST - Inativar notas fiscais

---

## 🏙️ MÓDULO LOCALIDADES

- `/localidades/ajax/cidades_por_uf/{uf}` - GET - Cidades por UF
- `/localidades/ajax/microrregioes_por_uf/{uf}` - GET - Microrregiões por UF
- `/localidades/ajax/mesorregioes_por_uf/{uf}` - GET - Mesorregiões por UF

---

## 📦 MÓDULO COTAÇÃO

- `/cotacao/fechar_frete` - POST - Fechar frete individual
- `/cotacao/fechar_frete_grupo` - POST - Fechar frete em grupo

---

## 📊 MÓDULO MONITORAMENTO

- `/monitoramento/{entregaId}/upload_canhoto` - POST - Upload de canhoto
- `/monitoramento/{entregaId}/historico_agendamentos` - GET - Histórico de agendamentos
- `/monitoramento/{entregaId}/adicionar_agendamento` - POST - Adicionar agendamento
- `/monitoramento/confirmar_agendamento/{agendamentoId}` - POST - Confirmar agendamento
- `/monitoramento/{entregaId}/historico_data_prevista` - GET - Histórico de datas previstas
- `/monitoramento/{entregaId}/alterar_data_prevista` - POST - Alterar data prevista

---

## 🚛 MÓDULO TRANSPORTADORAS

- `/transportadoras/dados/{id}` - GET - Dados da transportadora
- `/transportadoras/editar/{id}` - POST - Editar transportadora

---

## 💵 MÓDULO FINANCEIRO

- `/financeiro/pendencias/{nf}/responder` - POST - Responder pendência

---

## 🤖 MÓDULO CLAUDE AI

### Chat e Consultas
- `/claude-ai/api/query` - POST - Consulta ao Claude AI
- `/claude-ai/api/v4/query` - POST - Consulta Claude AI v4
- `/claude-ai/api/health` - GET - Status de saúde do serviço
- `/claude-ai/context-status` - GET - Status do contexto
- `/claude-ai/clear-context` - POST - Limpar contexto
- `/claude-ai/real` - POST - Claude Real query
- `/claude-ai/real/status` - GET - Status Claude Real

### Sugestões e Feedback
- `/claude-ai/api/suggestions` - POST - Obter sugestões
- `/claude-ai/api/suggestions/feedback` - POST - Enviar feedback
- `/claude-ai/api/advanced-feedback` - POST - Feedback avançado

### Dashboard e Métricas
- `/claude-ai/api/dashboard/kpis` - GET - KPIs do dashboard
- `/claude-ai/api/dashboard/graficos` - GET - Gráficos do dashboard
- `/claude-ai/api/dashboard/alertas` - GET - Alertas do dashboard
- `/claude-ai/api/metricas-reais` - GET - Métricas reais
- `/claude-ai/api/system-health-advanced` - GET - Saúde avançada do sistema
- `/claude-ai/api/claude-ai-novo-metrics` - GET - Métricas novo sistema
- `/claude-ai/api/advanced-analytics?days=7` - GET - Analytics avançados

### Autonomia e Sistema
- `/claude-ai/autonomia/descobrir-projeto` - POST - Descobrir projeto
- `/claude-ai/autonomia/inspecionar-banco` - POST - Inspecionar banco
- `/claude-ai/autonomia/ler-arquivo` - POST - Ler arquivo
- `/claude-ai/autonomia/criar-modulo` - POST - Criar módulo
- `/claude-ai/api/forcar-sistema-novo` - POST - Forçar sistema novo
- `/claude-ai/api/diagnostico-rapido` - GET - Diagnóstico rápido

### Admin e Segurança
- `/claude-ai/admin_free_mode_status` - GET - Status free mode
- `/claude-ai/enable_admin_free_mode` - POST - Habilitar free mode
- `/claude-ai/disable_admin_free_mode` - POST - Desabilitar free mode
- `/claude-ai/enable_experimental_feature/{feature}` - POST - Habilitar feature
- `/claude-ai/claude_real_free_mode` - POST - Free mode real
- `/claude-ai/enable_true_autonomy` - POST - Habilitar autonomia
- `/claude-ai/disable_true_autonomy` - POST - Desabilitar autonomia
- `/claude-ai/claude_autonomous_query_route` - POST - Query autônoma
- `/claude-ai/true-free-mode/permission/{requestId}` - POST - Permissão free mode
- `/claude-ai/seguranca/pendentes` - GET - Pendências segurança
- `/claude-ai/seguranca/aprovar/{actionId}` - POST - Aprovar ação
- `/claude-ai/seguranca/emergencia` - POST - Modo emergência

---

## 🔐 MÓDULO PERMISSIONS

- `/permissions/api/usuario/{usuarioId}/permissoes` - GET - Permissões do usuário
- `/permissions/api/permissao` - POST - Criar permissão
- `/permissions/api/modulo/{moduloId}/permissoes` - GET - Permissões do módulo
- `/permissions/api/usuario/{usuarioId}/vendedores` - GET/POST/DELETE - Gerenciar vendedores
- `/permissions/api/usuario/{usuarioId}/equipes` - GET/POST/DELETE - Gerenciar equipes
- `/permissions/api/logs?usuario_id={usuarioId}&limite=20` - GET - Logs de permissões

---

## 🔄 MÓDULO SINCRONIZAÇÃO ODOO

- `/sincronizacao_odoo/api_status_sincronizacao` - GET - Status da sincronização

---

## 📊 APIs GERAIS/INTERNAS

- `/api/estatisticas-internas` - GET - Estatísticas internas
- `/api/embarques-internos?limite=8` - GET - Embarques internos
- `/api/check-permission` - POST - Verificar permissão
- `/auth/regenerate_csrf` - POST - Regenerar token CSRF

---

## 🔗 LINKS DIRETOS (href)

### Carteira
- `/carteira/` - Página principal da carteira
- `/carteira/separacoes` - Listagem de separações
- `/carteira/expedicoes` - Listagem de expedições

### Faturamento
- `/faturamento/` - Dashboard do faturamento
- `/faturamento/editar` - Editar faturamento
- `/faturamento/importar` - Importar dados

### Estoque
- `/estoque/` - Dashboard do estoque
- `/estoque/ajustes` - Ajustes de estoque
- `/estoque/relatorios` - Relatórios de estoque

### Admin
- `/auth/usuarios` - Gerenciar usuários
- `/admin/permissions/` - Gerenciar permissões
- `/admin/sistema` - Configurações do sistema
- `/claude-ai/config` - Configurações Claude AI

### Claude AI
- `/claude-ai/v4/dashboard` - Dashboard v4
- `/claude-ai/chat` - Chat interface
- `/claude-ai/real` - Claude Real interface

### Documentação
- `/MANUAL_ATALHOS_CLAUDE.md` - Manual de atalhos
- `/static/DOCUMENTACAO_MODULO_CARTEIRA.md` - Documentação da carteira
- `/static/reports/*` - Relatórios exportados

---

## 📝 OBSERVAÇÕES IMPORTANTES

1. **Autenticação**: Todas as rotas exigem autenticação, exceto quando especificado
2. **CSRF Token**: Requisições POST devem incluir token CSRF
3. **Cache**: Algumas rotas implementam cache no frontend (5 minutos TTL)
4. **Versionamento**: APIs podem ter versões (ex: /api/v4/)
5. **Rate Limiting**: Algumas rotas podem ter limite de requisições

---

## 🚀 PADRÕES DE NOMENCLATURA

- `/api/*` - APIs REST padrão
- `/ajax/*` - Endpoints AJAX legados
- `/{modulo}/api/*` - APIs específicas do módulo
- `/{modulo}/{id}/{acao}` - Ações sobre recursos

---

**📌 NOTA**: Este documento deve ser atualizado sempre que novas rotas forem adicionadas ou modificadas no frontend.