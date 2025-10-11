# 🖼️ Como Adicionar o Logo na Impressão de Pedidos

## 📍 Localização do Arquivo

O logo deve ser colocado em:
```
app/static/motochefe/logo.png
```

## 📐 Especificações Recomendadas

- **Formato**: PNG (com transparência) ou JPG
- **Tamanho máximo**: 150px de largura x 80px de altura
- **Resolução**: 300 DPI para impressão de qualidade
- **Proporção**: Preferencialmente horizontal (landscape)

## 🎨 Dicas de Design

1. **Fundo transparente** (PNG): Fica melhor na impressão
2. **Cores**: Preferencialmente em alta resolução e boa definição
3. **Evite**: Logos muito verticais (podem ficar pequenos demais)

## 📂 Estrutura de Pastas

Se a pasta não existir, crie:

```bash
mkdir -p app/static/motochefe
```

Depois copie seu logo:
```bash
cp /caminho/do/seu/logo.png app/static/motochefe/logo.png
```

## ✅ Como Verificar

1. Acesse a impressão de um pedido
2. O logo deve aparecer no canto superior esquerdo
3. Se o logo não existir, o espaço fica vazio (sem erro)

## 🔧 Customização

Se quiser mudar o tamanho ou posição do logo, edite o arquivo:
```
app/templates/motochefe/vendas/pedidos/imprimir.html
```

Procure pela seção `.header-logo img` no CSS:
```css
.header-logo img {
    max-width: 150px;  /* Ajuste aqui */
    max-height: 80px;  /* Ajuste aqui */
    object-fit: contain;
}
```

## 🖨️ Teste de Impressão

1. Acesse um pedido
2. Clique em "Imprimir"
3. Use Ctrl+P ou clique no botão "🖨️ IMPRIMIR"
4. Verifique se o logo aparece corretamente na pré-visualização

---

**Dúvidas?** Entre em contato com o suporte técnico.
