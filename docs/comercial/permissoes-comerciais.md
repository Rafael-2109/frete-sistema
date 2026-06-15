<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Sistema de permissoes comerciais (PermissaoComercial/LogPermissaoComercial) — modelo de acesso, regras de negocio e operacao
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🔒 Sistema de Permissões Comerciais

> **Papel:** Explica o modelo de permissões comerciais (Etapa 5) que restringe o acesso de vendedores apenas aos dados de equipes/vendedores que estão autorizados a visualizar.

## Contexto

Implementado em 21/01/2025, o sistema de permissões comerciais limita a visibilidade de cada vendedor no módulo Comercial, garantindo que só vejam dados das equipes e vendedores liberados, enquanto administradores e gerentes comerciais mantêm acesso total. Este documento é fonte-de-verdade do modelo de acesso, das regras de negócio e da operação dessa funcionalidade.

## Indice

- [Funcionalidades Implementadas](#-funcionalidades-implementadas)
- [Arquivos Criados/Modificados](#-arquivos-criadosmodificados)
- [Como Usar](#-como-usar)
- [Regras de Negócio](#-regras-de-negócio)
- [Fluxo de Permissões](#-fluxo-de-permissões)
- [Verificação de Funcionamento](#-verificação-de-funcionamento)
- [Manutenção](#️-manutenção)
- [Importante](#️-importante)
- [SQL Úteis](#-sql-úteis)

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### 1. **Modelos de Dados**
- `PermissaoComercial`: Armazena permissões de equipes e vendedores por usuário
- `LogPermissaoComercial`: Registra histórico completo de alterações

### 2. **Controle de Acesso**
- Vendedores só veem dados de equipes/vendedores permitidos
- Administradores e Gerentes Comerciais veem tudo
- Vendedores sem permissões não veem nenhum dado

### 3. **Interface de Administração**
- Dois painéis separados: Equipes e Vendedores
- Drag-and-drop visual para gerenciar permissões
- Logs detalhados de todas alterações

### 4. **Restrições no Sistema**
- Menus ocultos para vendedores (apenas Comercial visível)
- Redirecionamento automático se tentar acessar outras áreas
- Validação em tempo real das permissões

## 📁 ARQUIVOS CRIADOS/MODIFICADOS

### Novos Arquivos:
- `/app/comercial/models.py` - Modelos de permissão e log
- `/app/comercial/services/permissao_service.py` - Lógica de permissões
- `/app/comercial/decorators.py` - Decorators de acesso
- `/app/templates/comercial/admin/lista_vendedores.html` - Lista de vendedores
- `/app/templates/comercial/admin/editar_permissoes.html` - Interface de edição

### Arquivos Modificados:
- `/app/__init__.py` - Context processor com flags de vendedor
- `/app/templates/base.html` - Menus condicionais baseados em perfil
- `/app/comercial/routes/diretoria.py` - Filtros de permissão aplicados

## 🚀 COMO USAR

### 1. **Tabelas no Banco**
As tabelas `permissao_comercial` e `log_permissao_comercial` já existem no banco (schema confirmado em `.claude/skills/consultando-sql/schemas/tables/permissao_comercial.json`). Foram criadas via migration (Flask-Migrate) e não exigem nenhum script standalone — não há um `criar_tabelas_permissao_comercial.py` no projeto. Para ambientes novos, aplicar as migrations normalmente (`flask db upgrade`).

### 2. **Acessar Interface de Administração**
- Login como Administrador ou Gerente Comercial
- Menu Comercial → Gerenciar Permissões

### 3. **Configurar Permissões**
- Selecione o vendedor
- Use os painéis para adicionar/remover:
  - **Equipes**: Vendedor vê todos os vendedores da equipe
  - **Vendedores específicos**: Vendedor vê apenas estes vendedores
- Alterações são salvas automaticamente

## 🔑 REGRAS DE NEGÓCIO

### Para Vendedores:
1. **Sem permissões** = Não vê nenhum dado
2. **Permissão de equipe** = Vê todos vendedores da equipe
3. **Permissão de vendedor** = Vê apenas aquele vendedor
4. **Múltiplas permissões** = Soma de todos os acessos
5. **Apenas módulo Comercial** = Outros menus ficam ocultos

### Para Outros Perfis:
- **Administrador**: Acesso total sem restrições
- **Gerente Comercial**: Acesso total + pode gerenciar permissões
- **Outros perfis**: Acesso normal ao sistema (sem módulo comercial)

## 📊 FLUXO DE PERMISSÕES

```
Vendedor faz login
    ↓
Sistema verifica perfil = 'vendedor'
    ↓
Oculta menus não-comerciais
    ↓
Vendedor acessa Comercial
    ↓
Sistema busca permissões do vendedor
    ↓
┌─ Tem permissões? ─┐
│                    │
SIM                 NÃO
│                    │
↓                    ↓
Filtra dados        Mostra aviso
permitidos          "Sem permissões"
```

## 🔍 VERIFICAÇÃO DE FUNCIONAMENTO

### Como Administrador:
1. Acesse `/comercial/admin/permissoes`
2. Configure permissões para um vendedor teste
3. Verifique os logs de alteração

### Como Vendedor:
1. Faça login com usuário vendedor
2. Verifique que só vê menu Comercial
3. Acesse dashboard e confirme que só vê equipes/vendedores permitidos
4. Tente acessar outra área (deve redirecionar)

## 🛠️ MANUTENÇÃO

### Adicionar Nova Permissão:
```python
from app.comercial.services.permissao_service import PermissaoService

# Adicionar permissão
PermissaoService.adicionar_permissao(
    usuario_id=1,
    tipo='equipe',  # ou 'vendedor'
    valor='VENDAS_SP',
    admin_email='admin@empresa.com'
)
```

### Consultar Permissões:
```python
# Obter permissões de um usuário
permissoes = PermissaoService.obter_permissoes_usuario(usuario_id=1)
print(f"Equipes: {permissoes['equipes']}")
print(f"Vendedores: {permissoes['vendedores']}")
```

### Verificar Logs:
```python
# Últimas 50 alterações de um usuário
logs = PermissaoService.obter_logs_usuario(usuario_id=1, limite=50)
for log in logs:
    print(f"{log.data_hora}: {log.descricao_acao} por {log.admin.nome}")
```

## ⚠️ IMPORTANTE

1. **Sempre teste** as permissões após configurar
2. **Monitore os logs** para auditoria
3. **Vendedor sem permissões** não consegue ver nada (por design)
4. **Backup regular** das tabelas de permissão é recomendado
5. **Campo vendedor_vinculado** no Usuario pode ser removido futuramente

## 📝 SQL ÚTEIS

### Ver todas permissões:
```sql
SELECT
    u.nome as usuario,
    p.tipo,
    p.valor,
    p.criado_em
FROM permissao_comercial p
JOIN usuarios u ON u.id = p.usuario_id
ORDER BY u.nome, p.tipo, p.valor;
```

### Logs das últimas 24h:
```sql
SELECT
    u1.nome as usuario_alterado,
    u2.nome as admin,
    l.acao,
    l.tipo,
    l.valor,
    l.data_hora
FROM log_permissao_comercial l
JOIN usuarios u1 ON u1.id = l.usuario_id
JOIN usuarios u2 ON u2.id = l.admin_id
WHERE l.data_hora >= NOW() - INTERVAL '24 hours'
ORDER BY l.data_hora DESC;
```

## ✅ Status

O sistema de permissões comerciais está totalmente funcional e em produção.
