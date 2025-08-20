# 📧 Funcionalidade de Anexar Emails às Despesas de Frete

## 📋 Resumo
Implementação completa para anexar e visualizar emails (.msg) relacionados às despesas de frete, com armazenamento no S3 para garantir persistência entre deploys.

## 🎯 Funcionalidades Implementadas

### 1. **Upload de Múltiplos Emails**
- Campo no formulário de criação de despesas para anexar arquivos .msg
- Suporte para múltiplos arquivos em uma única operação
- Preview dos arquivos selecionados com JavaScript

### 2. **Processamento de Emails .msg**
- Extração automática de metadados:
  - Remetente
  - Destinatários
  - Assunto
  - Data de envio
  - Quantidade de anexos
  - Preview do conteúdo (primeiros 500 caracteres)

### 3. **Armazenamento Seguro**
- Upload para Amazon S3 (quando configurado)
- Fallback para armazenamento local
- Estrutura organizada: `/fretes/despesas/{id}/emails/`

### 4. **Visualização de Emails**
- Interface dedicada para visualizar detalhes do email
- Exibição de metadados extraídos
- Preview do conteúdo do email
- Lista de outros emails da mesma despesa

### 5. **Download e Exclusão**
- Download do arquivo .msg original
- Exclusão com remoção do S3/local
- Confirmação antes de excluir

## 📁 Arquivos Criados/Modificados

### Novos Arquivos:
1. **`app/fretes/email_models.py`**
   - Modelo `EmailAnexado` para armazenar referências dos emails

2. **`app/utils/email_handler.py`**
   - Classe `EmailHandler` para processar .msg e gerenciar S3

3. **`app/fretes/email_routes.py`**
   - Rotas para visualizar, baixar e excluir emails

4. **`app/templates/fretes/visualizar_email.html`**
   - Template para visualização de emails

5. **`create_email_tables.py`**
   - Script para criar a tabela no banco de dados

### Arquivos Modificados:
1. **`app/fretes/forms.py`**
   - Adicionado campo `emails_anexados` no `DespesaExtraForm`

2. **`app/templates/fretes/criar_despesa_extra_frete.html`**
   - Adicionado campo de upload com preview JavaScript

3. **`app/fretes/routes.py`**
   - Atualizada rota `criar_despesa_extra_frete` para processar emails

4. **`app/__init__.py`**
   - Registrado blueprint `emails_bp`

5. **`requirements.txt`**
   - Adicionada dependência `extract-msg==0.45.0`

## 🚀 Como Usar

### 1. Instalar Dependências
```bash
pip install extract-msg==0.45.0
```

### 2. Criar Tabela no Banco
```bash
python create_email_tables.py
```

### 3. Configurar S3 (Opcional)
No arquivo `.env`:
```env
AWS_ACCESS_KEY_ID=sua_chave
AWS_SECRET_ACCESS_KEY=sua_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=seu_bucket
```

### 4. Usar a Funcionalidade
1. Ao criar uma despesa extra em `/fretes/despesas/criar/{id}`
2. Selecione um ou mais arquivos .msg no campo "Anexar Emails"
3. Os emails serão processados e armazenados
4. Visualize os emails anexados na página de detalhes do frete

## 🔧 Configuração do S3

### Permissões Necessárias no Bucket S3:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::seu-bucket/*",
                "arn:aws:s3:::seu-bucket"
            ]
        }
    ]
}
```

## 📊 Estrutura do Banco de Dados

### Tabela: `emails_anexados`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Chave primária |
| despesa_extra_id | Integer | FK para despesas_extras |
| nome_arquivo | String(255) | Nome original do arquivo |
| caminho_s3 | String(500) | Caminho no S3 ou local |
| tamanho_bytes | Integer | Tamanho do arquivo |
| remetente | String(255) | Email do remetente |
| destinatarios | Text | JSON com destinatários |
| assunto | String(500) | Assunto do email |
| data_envio | DateTime | Data/hora de envio |
| tem_anexos | Boolean | Se tem anexos |
| qtd_anexos | Integer | Quantidade de anexos |
| conteudo_preview | Text | Preview do conteúdo |
| criado_em | DateTime | Data de upload |
| criado_por | String(100) | Usuário que fez upload |

## 🎨 Interface do Usuário

### Formulário de Upload:
- Campo de seleção múltipla de arquivos
- Preview em tempo real dos arquivos selecionados
- Validação de tipo de arquivo (.msg apenas)

### Visualização:
- Cabeçalho com metadados do email
- Preview do conteúdo
- Botões para download e exclusão
- Lista de outros emails relacionados

## ⚡ Performance e Otimizações

1. **Processamento Assíncrono**: Os metadados são extraídos durante o upload
2. **Cache de Preview**: Apenas os primeiros 500 caracteres são armazenados
3. **Compressão S3**: Possibilidade de adicionar compressão gzip no futuro

## 🔒 Segurança

1. **Validação de Arquivo**: Apenas .msg são aceitos
2. **Sanitização de Nome**: Usa `secure_filename()` do Werkzeug
3. **Permissões**: Requer login para todas as operações
4. **S3 Privado**: Arquivos não são públicos no S3

## 📝 TODOs Futuros

- [ ] Adicionar busca por conteúdo dos emails
- [ ] Implementar visualização inline de anexos do email
- [ ] Adicionar compressão antes do upload para S3
- [ ] Criar relatório de emails por período
- [ ] Implementar OCR para emails escaneados
- [ ] Adicionar suporte para arquivos .eml além de .msg

## 🐛 Troubleshooting

### Erro: "extract_msg not found"
```bash
pip install extract-msg==0.45.0
```

### Erro: "S3 access denied"
- Verifique as credenciais AWS no .env
- Confirme permissões do bucket

### Emails não aparecem
- Execute `python create_email_tables.py`
- Verifique logs em `app.logger`

## 📚 Documentação das Bibliotecas

- [extract-msg](https://github.com/TeamMsgExtractor/msg-extractor): Extração de dados de arquivos .msg
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html): SDK AWS para Python

---

**Desenvolvido por:** Claude AI Assistant
**Data:** 19/08/2025
**Versão:** 1.0.0