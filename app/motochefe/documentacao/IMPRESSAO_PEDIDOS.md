# 🖨️ Sistema de Impressão de Pedidos - MotoCHEFE

## 📋 Resumo da Implementação

Sistema completo de impressão de pedidos em formato A4 com controle de status de impressão.

---

## 🆕 Campos Adicionados ao Modelo

### PedidoVendaMoto
```python
impresso = db.Column(db.Boolean, default=False, nullable=False, index=True)
impresso_por = db.Column(db.String(100), nullable=True)
impresso_em = db.Column(db.DateTime, nullable=True)
```

**Comportamento:**
- Na primeira impressão: `impresso = True`, registra usuário e data/hora
- Nas próximas impressões: mantém registro original
- Badge "IMPRESSO" aparece na lista e detalhes

---

## 🛣️ Rota Criada

### `/motochefe/pedidos/<id>/imprimir`
- **Método**: GET
- **Permissão**: `@requer_motochefe`
- **Função**: Exibe pedido formatado para impressão A4
- **Comportamento**: Marca como impresso no primeiro acesso

**Arquivo:** `app/motochefe/routes/vendas.py:1176`

---

## 📄 Template de Impressão

### `app/templates/motochefe/vendas/pedidos/imprimir.html`

**Características:**
- ✅ Formato A4 otimizado para impressão
- ✅ Logo da empresa (opcional)
- ✅ Dados completos do cliente (CNPJ, endereço, telefone)
- ✅ Informações das motos (modelo, cor, chassi, pallet, preços)
- ✅ Totais (valor total, quantidade de motos)
- ✅ Condições de pagamento
- ✅ Dados de logística (transportadora, tipo frete)
- ✅ Observações do pedido
- ✅ Dados de faturamento (se faturado)
- ✅ Botão flutuante para impressão
- ✅ CSS otimizado com `@media print`

**Seções:**
1. Cabeçalho com logo e número do pedido
2. Dados do cliente
3. Dados da venda
4. Condições de pagamento
5. Dados de logística
6. Tabela de motos
7. Observações
8. Dados de faturamento (se aplicável)
9. Rodapé com informações de auditoria

---

## 🔘 Botões de Impressão

### 1. Lista de Pedidos
**Localização:** `app/templates/motochefe/vendas/pedidos/listar.html:131`

```html
<a href="{{ url_for('motochefe.imprimir_pedido', id=p.id) }}"
   class="btn btn-secondary btn-sm"
   target="_blank"
   title="Imprimir Pedido">
    <i class="fas fa-print"></i>
    {% if p.impresso %}
    <i class="fas fa-check-circle text-success"></i>
    {% endif %}
</a>
```

**Recursos:**
- Abre em nova aba (`target="_blank"`)
- Badge verde se já foi impresso
- Integrado ao `btn-group` de ações

### 2. Detalhes do Pedido
**Localização:** `app/templates/motochefe/vendas/pedidos/detalhes.html:27`

```html
<a href="{{ url_for('motochefe.imprimir_pedido', id=pedido.id) }}"
   class="btn btn-secondary btn-lg"
   target="_blank">
    <i class="fas fa-print"></i> Imprimir Pedido
    {% if pedido.impresso %}
    <span class="badge bg-success ms-2">
        <i class="fas fa-check"></i> Impresso
    </span>
    {% endif %}
</a>
```

**Recursos:**
- Botão grande no canto superior direito
- Badge "Impresso" se já foi impresso

---

## 🖼️ Logo da Empresa

### Como Adicionar

1. **Crie a pasta** (se não existir):
   ```bash
   mkdir -p app/static/motochefe
   ```

2. **Copie seu logo**:
   ```bash
   cp /caminho/logo.png app/static/motochefe/logo.png
   ```

3. **Especificações recomendadas**:
   - Formato: PNG (transparente) ou JPG
   - Tamanho: 150x80px máximo
   - Resolução: 300 DPI
   - Proporção: Horizontal (landscape)

4. **Se não houver logo**: O espaço fica vazio (sem erro)

**Veja mais em:** `app/motochefe/COMO_ADICIONAR_LOGO.md`

---

## 📦 Arquivos de Migração

### 1. Script Python Local
**Arquivo:** `app/motochefe/scripts/migration_campos_impressao_pedido_local.py`

**Como executar:**
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python3 app/motochefe/scripts/migration_campos_impressao_pedido_local.py
```

**O que faz:**
- Verifica campos existentes
- Remove campos se já existirem (com confirmação)
- Adiciona campos: `impresso`, `impresso_por`, `impresso_em`
- Cria índice `idx_pedido_venda_impresso`
- Exibe verificação completa

### 2. Script SQL Render
**Arquivo:** `app/motochefe/scripts/migration_campos_impressao_pedido_render.sql`

**Como executar:**
1. Acesse o Shell SQL do Render
2. Copie e cole o conteúdo do arquivo
3. Execute

**O que faz:**
- Adiciona campos com `IF NOT EXISTS`
- Cria índice
- Queries de verificação incluídas

---

## 🎨 Personalização do Template

### Cores Principais
```css
/* Vermelho MotoCHEFE */
color: #d32f2f;
background: #d32f2f;

/* Cinza escuro */
color: #333;
background: #333;
```

### Ajustar Tamanho do Logo
Edite `imprimir.html` linha ~47:
```css
.header-logo img {
    max-width: 150px;  /* Ajuste aqui */
    max-height: 80px;  /* Ajuste aqui */
}
```

### Margens de Impressão
Edite `imprimir.html` linha ~20:
```css
@page {
    size: A4;
    margin: 1.5cm;  /* Ajuste aqui */
}
```

---

## 🧪 Como Testar

1. **Rode a migração local:**
   ```bash
   python3 app/motochefe/scripts/migration_campos_impressao_pedido_local.py
   ```

2. **Acesse um pedido:**
   - Lista: `/motochefe/pedidos`
   - Clique no botão 🖨️

3. **Teste a impressão:**
   - Ctrl+P ou botão flutuante
   - Verifique pré-visualização
   - Teste com/sem logo

4. **Verifique status:**
   - Badge "IMPRESSO" deve aparecer
   - Data/hora registrada no banco

---

## 📊 Queries Úteis

### Ver pedidos impressos
```sql
SELECT
    numero_pedido,
    impresso,
    impresso_por,
    impresso_em
FROM pedido_venda_moto
WHERE impresso = TRUE
ORDER BY impresso_em DESC;
```

### Estatísticas de impressão
```sql
SELECT
    impresso,
    COUNT(*) as quantidade
FROM pedido_venda_moto
GROUP BY impresso;
```

### Resetar status de impressão (teste)
```sql
UPDATE pedido_venda_moto
SET impresso = FALSE,
    impresso_por = NULL,
    impresso_em = NULL
WHERE numero_pedido = 'MC 0001';
```

---

## ✅ Checklist de Implementação

- [x] Campos adicionados ao modelo
- [x] Scripts de migração criados (local + Render)
- [x] Rota de impressão criada
- [x] Template A4 completo
- [x] Botão na lista de pedidos
- [x] Botão nos detalhes do pedido
- [x] Suporte para logo
- [x] CSS otimizado para impressão
- [x] Documentação completa

---

## 🐛 Troubleshooting

### Logo não aparece
- Verifique o caminho: `app/static/motochefe/logo.png`
- Teste URL: `http://localhost:5000/static/motochefe/logo.png`
- Limpe cache do navegador

### Campos não existem no banco
- Execute a migração local ou SQL do Render
- Verifique com: `\d pedido_venda_moto` (PostgreSQL)

### Botão não aparece
- Limpe cache do navegador (Ctrl+Shift+R)
- Verifique se os templates foram salvos

---

## 📞 Suporte

Dúvidas? Consulte:
- `COMO_ADICIONAR_LOGO.md` - Instruções do logo
- Código fonte em `routes/vendas.py`
- Template em `templates/motochefe/vendas/pedidos/imprimir.html`

---

**Versão:** 1.0
**Data:** 11/10/2025
**Autor:** Sistema MotoCHEFE
