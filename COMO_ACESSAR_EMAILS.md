# 📧 Como Acessar os Emails Anexados no Sistema

## ✅ Formas de Acesso Disponíveis

### 1. 📋 **Na Visualização do Frete** (PRINCIPAL)
**URL**: `/fretes/{frete_id}`

Ao visualizar qualquer frete, você verá uma seção **"Emails Anexados"** que mostra:
- Lista de todos os emails anexados às despesas deste frete
- Informações de cada email (arquivo, assunto, remetente, data)
- Botões de ação para cada email:
  - 👁️ **Visualizar**: Ver detalhes completos
  - 📥 **Baixar**: Download do arquivo .msg original
  - 🗑️ **Excluir**: Remover o email

### 2. 📧 **Visualização Individual do Email**
**URL**: `/fretes/emails/{email_id}`

Página dedicada para visualizar um email específico com:
- Todos os metadados extraídos
- Preview do conteúdo (primeiros 500 caracteres)
- Informações da despesa relacionada
- Lista de outros emails da mesma despesa
- Botões para download e exclusão

### 3. 📁 **Lista de Emails por Frete**
**URL**: `/fretes/emails/frete/{frete_id}`

Visualização dedicada de todos os emails de um frete:
- Emails agrupados por despesa
- Visão consolidada de todas as comunicações
- Ideal para ter uma visão geral

### 4. 💰 **Lista de Emails por Despesa**
**URL**: `/fretes/emails/despesa/{despesa_id}`

Ver apenas os emails de uma despesa específica:
- Foco em uma única despesa
- Útil para análise detalhada

## 🎯 Onde Anexar Emails

### Ao Criar Despesa Extra:
**URL**: `/fretes/despesas/criar/{frete_id}`

1. Acesse a criação de despesa extra
2. No formulário, procure o campo **"Anexar Emails (.msg)"**
3. Selecione um ou mais arquivos .msg
4. O sistema mostrará preview dos arquivos selecionados
5. Ao salvar, os emails são processados automaticamente

## 📊 Informações Exibidas

Para cada email anexado, o sistema mostra:
- **Nome do arquivo**: Nome original do .msg
- **Assunto**: Extraído automaticamente do email
- **Remetente**: Email de quem enviou
- **Data de envio**: Quando o email foi enviado originalmente
- **Despesa relacionada**: Tipo e valor da despesa
- **Anexado em**: Quando foi adicionado ao sistema
- **Por**: Usuário que fez o upload

## 🔍 Navegação Rápida

### Do Dashboard de Fretes:
1. Acesse `/fretes/`
2. Clique em "Listar Fretes"
3. Encontre o frete desejado
4. Clique no ID ou botão de visualizar
5. Role até a seção "Emails Anexados"

### Atalho Direto:
Se você souber o ID do frete, acesse diretamente:
- `/fretes/{id}` - Ver frete com emails
- `/fretes/emails/frete/{id}` - Ver só os emails

## 💡 Dicas de Uso

1. **Download em Lote**: Na visualização do frete, você pode baixar vários emails rapidamente clicando nos botões de download

2. **Visualização Rápida**: Use o botão 👁️ para ver rapidamente o conteúdo sem baixar

3. **Organização**: Os emails são automaticamente organizados por despesa e data

4. **Busca**: Use Ctrl+F no navegador para buscar por assunto ou remetente

## 🚨 Observações Importantes

- Apenas arquivos **.msg** (Outlook) são aceitos
- O tamanho máximo depende da configuração do servidor
- Emails excluídos são removidos permanentemente
- Se usar S3, os downloads geram URLs temporárias (1 hora)

## 📝 Exemplo de Fluxo Completo

1. **Criar Despesa com Email**:
   ```
   /fretes/despesas/criar/123
   → Anexar arquivo email.msg
   → Salvar despesa
   ```

2. **Visualizar Emails**:
   ```
   /fretes/123
   → Seção "Emails Anexados"
   → Clicar em "Visualizar"
   ```

3. **Baixar Original**:
   ```
   Clicar no botão verde de download
   → Arquivo .msg baixado
   → Pode abrir no Outlook
   ```

---

**Status**: Sistema 100% funcional e pronto para uso!
**Última atualização**: 19/08/2025