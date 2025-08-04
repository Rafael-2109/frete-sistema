# Fluxo de Sincronização Segura - Frontend Tracking

## 📍 Localização do Botão

**Arquivo:** `/app/templates/odoo/sync_integrada/dashboard.html`
**Linha:** 113-117
**ID do Botão:** `btn-sync-seguro`

```html
<button type="submit" class="btn btn-success btn-lg" id="btn-sync-seguro">
    <i class="fas fa-shield-alt"></i>
    <strong>SINCRONIZAR TUDO (SEGURO)</strong>
    <small class="d-block mt-1">🔄 Faturamento → Carteira</small>
</button>
```

## 🔄 Fluxo Completo do Frontend ao Backend

### 1. **Clique no Botão**
- ID: `btn-sync-seguro`
- Classe: `btn btn-success btn-lg`
- Tipo: Submit button dentro de um formulário

### 2. **Validação JavaScript**
- **Função:** `confirmarSincronizacaoSegura()` (linha 202-222)
- **Evento:** `onsubmit` do formulário (linha 100)
- **Ação:** Mostra confirmação com detalhes da operação
- **Retorno:** `true` permite submit, `false` cancela

### 3. **Formulário HTML**
- **Action:** `{{ url_for('sync_integrada.executar_sincronizacao_segura') }}`
- **Method:** POST
- **Parâmetros:**
  - `usar_filtro_carteira`: checkbox (checked por padrão)

### 4. **Feedback Visual**
- **Durante execução:** (linhas 225-254)
  - Botão muda para spinner + "SINCRONIZANDO..."
  - Classe muda para `btn-warning`
  - Botão fica desabilitado
  - Timeout de segurança: 60 segundos

### 5. **Rota Backend**
- **Arquivo:** `/app/odoo/routes/sincronizacao_integrada.py`
- **Função:** `executar_sincronizacao_segura()` (linha 51)
- **Blueprint:** `sync_integrada_bp`
- **URL:** `/sync_integrada/executar`
- **Decoradores:** `@login_required`

### 6. **Serviço de Sincronização**
- **Import:** `from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService`
- **Método chamado:** `sync_service.executar_sincronizacao_completa_segura(usar_filtro_carteira=usar_filtro_carteira)`

## 📊 Event Listeners JavaScript

### 1. **Confirmação antes do Submit**
```javascript
function confirmarSincronizacaoSegura() {
    // Mostra mensagem detalhada
    // Retorna confirm() do usuário
}
```

### 2. **Listener do DOMContentLoaded**
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Configura listener de submit no formulário
    // Altera visual do botão durante sincronização
    // Implementa timeout de segurança
});
```

### 3. **Submit do Formulário**
```javascript
form.addEventListener('submit', function(e) {
    // Altera texto e aparência do botão
    // Desabilita o botão
    // Configura timeout de 60 segundos
});
```

## 🔐 Características de Segurança

1. **Sequência Fixa:** Faturamento → Carteira (automática)
2. **Confirmação Obrigatória:** Modal JavaScript antes de executar
3. **Feedback Visual:** Botão muda durante processamento
4. **Timeout de Segurança:** 60 segundos para evitar travamento
5. **Login Obrigatório:** Decorador `@login_required`

## 📝 Parâmetros da Requisição

- **usar_filtro_carteira:** 
  - Tipo: checkbox
  - Default: checked (true)
  - Descrição: "Sincronizar apenas pedidos não entregues"

## 🎯 Próximos Passos (para outros agentes)

1. **Backend Tracker:** Analisar `SincronizacaoIntegradaService.executar_sincronizacao_completa_segura()`
2. **API Tracker:** Rastrear chamadas para o Odoo
3. **Database Tracker:** Verificar tabelas afetadas pela sincronização