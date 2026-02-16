# Opção 942 — Upload de Ajudas de Programas de EDI

> **Módulo**: Sistema (Controle)
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Efetua upload de documentos de Ajuda para programas de EDI, permitindo que transportadoras documentem integrações customizadas com clientes.

## Quando Usar
- Criar ou atualizar ajuda de programa EDI customizado
- Documentar integrações específicas com clientes
- Incluir novos clientes em ajuda existente
- Disponibilizar ajuda em todos os servidores SSW

## Pré-requisitos
- Modelo Word fornecido pelo SSW (disponível AQUI)
- Microsoft Word instalado
- Conhecimento do programa EDI a documentar
- Arquivos gerados: HTML + arquivo anexo

## Processo

```
Baixar modelo Word → Editar ajuda → Salvar HTML (ssw9999.htm) →
Compactar ZIP → Upload opção 942 → Verificar opção 600
```

## Como Confeccionar Documento de Ajuda

### 1. Obter Modelo
- Baixar modelo Word (pasta Downloads)
- Abrir com Microsoft Word

### 2. Nome do Arquivo
- Salvar como **ssw9999.htm** (número do programa)
- Formato: **HTML**
- Cada cliente com variações = incluir na mesma ajuda

### 3. Editar Ajuda

#### Manter Componente
- Não remover componente indicado no modelo

#### Incluir/Excluir Linhas na Tabela
1. Marcar linha completa
2. Usar instrumentos Word: copiar, colar, cortar
3. Colar sobre linha marcada = inclusão

#### Criar Links
1. Marcar palavra
2. Botão direito → Link
3. Digitar comando JavaScript:

**Comandos disponíveis**:
- `javascript:showprg('ssw0021',1)` - Abre opção ssw0021
- `javascript:show('/ajuda/ssw0021.htm')` - Abre ajuda ssw0021
- `javascript:show('/ajuda/nova_busca_ssw.htm')` - Abre doc HTML qualquer
- `javascript:youtube('yHFDa9efCQU')` - Abre vídeo YOUTUBE ou LOOM
- `https://sistema.ssw.inf.br/ajuda/uma_nova_transportadora.pdf` - Abre PDF

### 4. Salvar Documento
- Formato: **HTML**
- Nome: **ssw9999** (número do programa)
- Arquivo anexo gerado automaticamente

### 5. Compactar
- Compactar todas ajudas e arquivos anexos da pasta
- Formato: **ZIP**

### 6. Upload
- Usar opção 942
- Escolher arquivo ZIP
- SSW disponibiliza em todos servidores (sobrepõe ajudas anteriores)

### 7. Verificar
- Abrir opção 600
- Verificar como ficou a ajuda
- Corrigir se necessário

## Campos / Interface

### Tela

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Escolher arquivo** | Sim | Fazer upload do arquivo ZIP gerado. SSW disponibiliza ajudas em todos servidores sobrepondo anteriores |

## Fluxo de Uso

1. Baixar modelo Word fornecido pelo SSW
2. Editar ajuda conforme instruções
3. Salvar como **ssw9999.htm** (formato HTML)
4. Compactar arquivo HTML + anexos em ZIP
5. Acessar opção 942
6. Fazer upload do arquivo ZIP
7. Verificar ajuda na opção 600
8. Corrigir se necessário (repetir processo)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 600 | Verificar como ficou a ajuda após upload |

## Observações e Gotchas

### Usuário Deve Entender
- Ajuda deve ser clara e precisa
- Usuário deve conseguir executar processo sem dúvidas
- Testar instruções antes de publicar

### Nome do Arquivo
- **ssw9999.htm**: 9999 = número do programa
- Formato HTML obrigatório
- Extensão .htm (não .html)

### Arquivo Anexo
- Gerado automaticamente ao salvar HTML
- Não deletar
- Compactar junto com HTML

### Múltiplos Clientes
- Incluir todos clientes com variações na mesma ajuda
- Não criar ajudas separadas por cliente

### Links JavaScript
- Usar comandos exatos fornecidos
- Testar links antes de publicar

### Compactação
- Incluir **todos** arquivos da pasta (HTML + anexos)
- Formato ZIP
- Não usar RAR ou outros formatos

### Sobrescrita
- Upload sobrepõe ajudas anteriores de mesmo nome
- Fazer backup antes de atualizar

### Disponibilização
- SSW disponibiliza em **todos servidores**
- Atualização automática

### Verificação
- Sempre verificar na opção 600 após upload
- Corrigir imediatamente se necessário

### Modelo Obrigatório
- Usar modelo fornecido pelo SSW
- Não criar do zero

### Formato de Tabela
- Manter estrutura do modelo
- Marcar linha completa ao editar
- Usar ferramentas Word (não editar HTML)
