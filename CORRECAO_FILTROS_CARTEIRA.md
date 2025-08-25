# Correção dos Filtros de Agendamento e Rotas/Incoterms na Carteira

## 🐛 Problema Identificado
Os botões/badges de filtros "Agendamento" e "Rotas/Incoterms" não estavam funcionando na página `/carteira/workspace`.

## 🔍 Causa Raiz
O JavaScript estava procurando por elementos com a classe `.badge-filtro`, mas no HTML os badges tinham a classe `.bg-filtro`.

## ✅ Correções Aplicadas

### 1. **Arquivo: `/app/templates/carteira/js/carteira-agrupada.js`**

#### Correção do seletor CSS (linha 68)
```javascript
// ANTES (incorreto):
document.querySelectorAll('.badge-filtro').forEach(badge => {

// DEPOIS (correto):
document.querySelectorAll('.bg-filtro').forEach(badge => {
```

#### Adição de cursor pointer para indicar clicabilidade (linha 70)
```javascript
badge.style.cursor = 'pointer';
```

#### Inclusão do campo agendamento nos filtros ativos (linha 13)
```javascript
this.filtrosAtivos = {
    rotas: new Set(),
    incoterms: new Set(),
    subrotas: new Set(),
    agendamento: null  // null, 'com' ou 'sem'
};
```

#### Adição de debug para verificação (linhas 20-33)
```javascript
console.log('🚀 Inicializando CarteiraAgrupada...');
// ... código ...
const totalBadges = document.querySelectorAll('.bg-filtro').length;
if (totalBadges === 0) {
    console.error('❌ ERRO: Nenhum badge .bg-filtro encontrado no DOM!');
} else {
    console.log(`✅ ${totalBadges} badges de filtro encontrados e configurados`);
}
```

### 2. **Arquivo: `/app/templates/carteira/agrupados_balanceado.html`**

#### Adição de estilos CSS para melhor UX (linhas 743-760)
```css
/* Estilos para badges de filtros clicáveis */
.bg-filtro {
    cursor: pointer !important;
    transition: all 0.2s ease;
    user-select: none;
}

.bg-filtro:hover {
    transform: scale(1.05);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.bg-filtro:active {
    transform: scale(0.98);
}

.bg-filtro.ativo {
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
```

## 🎯 Funcionalidade Corrigida

### Agora os filtros funcionam assim:

1. **Badges de Agendamento** (mutuamente exclusivos):
   - "Sem Agendamento" - filtra pedidos sem agendamento
   - "Com Agendamento" - filtra pedidos com agendamento
   - Apenas um pode estar ativo por vez

2. **Badges de Rotas/Incoterms** (múltipla seleção, até 3):
   - Rotas: SP, RJ, MG, ES, SUL, MS-MT, DF-GO-TO, BA, NE, NE2, NO, MARIT.
   - Incoterms: FOB, RED
   - Máximo de 3 filtros ativos simultaneamente

3. **Subrotas SP** (aparecem quando SP é selecionado):
   - Litoral A, B, C
   - A, ABC, B, C, D, E, SP

4. **Comportamento Visual**:
   - Badge inativo: borda colorida com fundo transparente
   - Badge ativo: fundo colorido preenchido
   - Hover: aumenta tamanho e adiciona sombra
   - Click: feedback visual de pressão

## 🧪 Como Testar

1. **Teste Manual na Aplicação**:
   - Acesse `/carteira/workspace` ou `/carteira/agrupados`
   - Clique nos badges de filtros
   - Verifique se mudam de cor (outline → preenchido)
   - Verifique se a tabela é filtrada corretamente
   - Teste o botão "Limpar" quando filtros estão ativos

2. **Teste com Arquivo HTML**:
   - Abra `/test_filtros_carteira.html` no navegador
   - Clique em "Executar Teste"
   - Clique nos badges individualmente
   - Verifique o console do navegador (F12)

3. **Verificação no Console**:
   ```javascript
   // No console do navegador na página da carteira:
   document.querySelectorAll('.bg-filtro').length
   // Deve retornar o número de badges (aproximadamente 19-20)
   
   // Verificar se CarteiraAgrupada foi inicializada:
   window.carteiraAgrupada
   // Deve retornar o objeto CarteiraAgrupada
   
   // Ver filtros ativos:
   window.carteiraAgrupada.filtrosAtivos
   ```

## 📊 Impacto

- **Usuários afetados**: Todos que usam a carteira agrupada
- **Funcionalidades restauradas**:
  - Filtro por status de agendamento
  - Filtro por rotas e incoterms
  - Filtro por subrotas (quando SP selecionado)
  - Limitação de 3 filtros simultâneos
  - Botões de limpar filtros

## 🚀 Deploy

```bash
# Commit das correções
git add app/templates/carteira/js/carteira-agrupada.js
git add app/templates/carteira/agrupados_balanceado.html
git add CORRECAO_FILTROS_CARTEIRA.md
git add test_filtros_carteira.html

git commit -m "fix: correção dos filtros de Agendamento e Rotas/Incoterms na carteira

- Corrigido seletor CSS de .badge-filtro para .bg-filtro
- Adicionado campo agendamento aos filtros ativos
- Melhorado feedback visual com cursor pointer e efeitos hover
- Adicionado debug para facilitar troubleshooting
- Criado arquivo de teste para validação"

git push origin main
```

## ⚠️ Observações

1. Os filtros são aplicados em conjunto (AND):
   - Se selecionar "Com Agendamento" + "SP", mostra apenas pedidos COM agendamento E da rota SP

2. Limite de 3 filtros de rotas/incoterms:
   - Evita complexidade excessiva
   - Mensagem de alerta aparece ao tentar selecionar o 4º filtro

3. Filtros de agendamento são exclusivos:
   - Não pode ter "Com" e "Sem" ao mesmo tempo
   - Clicar no mesmo desativa o filtro

## 📝 Notas de Desenvolvimento

- O código usa classes ES6 para melhor organização
- Event listeners são adicionados uma única vez na inicialização
- Filtros usam `Set()` para evitar duplicatas
- Debug via console para facilitar troubleshooting