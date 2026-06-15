# 🚀 INSTRUÇÕES DE DEPLOY - Sistema MotoChefe

**Data**: 07/10/2025
**Status**: ✅ **PRONTO PARA DEPLOY**

---

## 📋 RESUMO

Implementação **100% concluída** com:
- ✅ Backend completo (modelos, services, APIs)
- ✅ Frontend completo (form.html refatorado)
- ✅ CRUD CrossDocking (rotas + templates)
- ✅ Menu atualizado
- ✅ Scripts de migração (Python + SQL)

---

## 🚀 OPÇÃO 1: DEPLOY LOCAL/DESENVOLVIMENTO

### 1. Executar Migração Python

```bash
python app/motochefe/scripts/migration_crossdocking_parcelas.py
```

**Saída esperada**:
```
🚀 Iniciando migração: CrossDocking e Parcelamento...
============================================================
📋 Criando tabelas...
✅ Tabelas criadas com sucesso!
...
✅ Migração concluída com sucesso!
```

### 2. Reiniciar Aplicação

```bash
# Se estiver usando gunicorn
pkill gunicorn && gunicorn app:app

# Se estiver usando Flask dev server
flask run
```

### 3. Testar Funcionalidades

1. **Acessar MotoChefe → CrossDocking**
   - URL: `http://localhost:5000/motochefe/crossdocking`

2. **Criar Pedido**
   - Testar cascata: Equipe → Vendedor → Cliente
   - Testar SELECT de cores
   - Testar cálculo com frete

---

## 🌐 OPÇÃO 2: DEPLOY RENDER (PRODUÇÃO)

### 1. Fazer Push para GitHub

```bash
git add .
git commit -m "feat: Implementa CrossDocking, Parcelamento e Refatorações MotoChefe

- Adiciona modelos: ParcelaPedido, ParcelaTitulo, CrossDocking, TabelaPrecoCrossDocking
- Adiciona campos: ClienteMoto (vendedor_id, crossdocking), EquipeVendasMoto (permitir_prazo, permitir_parcelamento), PedidoVendaMoto (prazo_dias, numero_parcelas)
- Cria services: precificacao_service, parcelamento_service
- Refatora frontend: cascata dinâmica, SELECT cores, cálculo frete
- Adiciona CRUD CrossDocking completo
- Corrige importação valores brasileiros e case-insensitive

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

### 2. Executar Migração no Render

**Opção A: Via Script Python (após deploy)**

1. Abra Shell do Render:
   - Dashboard → Seu Web Service → Shell

2. Execute:
   ```bash
   python app/motochefe/scripts/migration_crossdocking_parcelas.py
   ```

**Opção B: Via SQL Direto (PostgreSQL)**

1. Abra PostgreSQL Shell do Render:
   - Dashboard → Seu Database → Connect → Shell (psql)

2. Copie e cole TODO o conteúdo de:
   ```
   MIGRATION_SQL_RENDER.sql
   ```

3. Execute (pressione Enter)

4. Verifique resumo final:
   ```
   Tabelas criadas: 4
   Campos em cliente_moto: 3
   Campos em equipe_vendas_moto: 2
   Campos em pedido_venda_moto: 2
   ```

### 3. Restart Aplicação no Render

- Dashboard → Seu Web Service → Manual Deploy → Deploy latest commit

---

## ⚙️ CONFIGURAÇÃO INICIAL (APÓS MIGRAÇÃO)

### 1. Atualizar Clientes Existentes

Como `vendedor_id` agora é **NOT NULL**, todos os clientes precisam de vendedor:

**Via Interface**:
- Acessar MotoChefe → Clientes
- Editar cada cliente e definir vendedor

**Via SQL** (se preferir atribuir em lote):
```sql
-- Atribuir todos os clientes sem vendedor ao vendedor ID 1
UPDATE cliente_moto
SET vendedor_id = 1
WHERE vendedor_id IS NULL;
```

### 2. Configurar Equipes

Definir permissões de prazo e parcelamento:

**Via Interface**:
- Acessar MotoChefe → Equipes de Vendas
- Editar cada equipe
- Marcar checkboxes conforme necessário:
  - ☐ Permitir Prazo
  - ☐ Permitir Parcelamento

**Via SQL**:
```sql
-- Exemplo: Habilitar prazo e parcelamento para equipe "Vendas RJ"
UPDATE equipe_vendas_moto
SET permitir_prazo = TRUE,
    permitir_parcelamento = TRUE
WHERE equipe_vendas = 'Vendas RJ';
```

### 3. Cadastrar CrossDockings (Opcional)

Se necessário, criar regras de CrossDocking:

- Acessar MotoChefe → CrossDocking → Adicionar
- Preencher configurações
- Gerenciar tabela de preços

---

## ✅ CHECKLIST DE VALIDAÇÃO

Após deploy, testar:

### Backend
- [ ] Migração executada sem erros
- [ ] Tabelas criadas (4 novas)
- [ ] Campos adicionados (7 campos)
- [ ] Clientes com vendedor_id definido

### Frontend
- [ ] Menu mostra "CrossDocking"
- [ ] Tela de pedidos:
  - [ ] Cascata funciona (Equipe → Vendedor → Cliente)
  - [ ] SELECT de cores mostra quantidade
  - [ ] Cálculo inclui frete
  - [ ] Parcelas recalculam corretamente
- [ ] CRUD CrossDocking acessível

### Funcionalidades
- [ ] Importar motos (valores brasileiros)
- [ ] Criar pedido completo
- [ ] Testar parcelamento
- [ ] Validar cálculos

---

## 🐛 TROUBLESHOOTING

### Erro: "vendedor_id cannot be null"

**Causa**: Clientes sem vendedor definido

**Solução**:
```sql
UPDATE cliente_moto SET vendedor_id = 1 WHERE vendedor_id IS NULL;
```

### Erro: "table already exists"

**Causa**: Migração já executada

**Solução**: Normal, pode ignorar. Script tem proteção `IF NOT EXISTS`.

### Menu não mostra CrossDocking

**Causa**: Cache do navegador

**Solução**: Ctrl+Shift+R (hard refresh)

---

## 📁 ARQUIVOS MODIFICADOS

### ✅ Criados (14):
1. `app/motochefe/services/precificacao_service.py`
2. `app/motochefe/services/parcelamento_service.py`
3. `app/motochefe/routes/crossdocking.py`
4. `app/motochefe/scripts/migration_crossdocking_parcelas.py`
5. `app/templates/motochefe/cadastros/crossdocking/listar.html`
6. `app/templates/motochefe/cadastros/crossdocking/form.html`
7. `app/templates/motochefe/cadastros/crossdocking/precos.html`
8. `MIGRATION_SQL_RENDER.sql`
9. `INSTRUCOES_DEPLOY_FINAL.md` (este arquivo)
10-14. Documentação (.md)

### ✅ Modificados (9):
1. `app/motochefe/models/vendas.py`
2. `app/motochefe/models/cadastro.py`
3. `app/motochefe/models/__init__.py`
4. `app/motochefe/routes/produtos.py`
5. `app/motochefe/routes/vendas.py`
6. `app/motochefe/routes/__init__.py`
7. `app/motochefe/services/pedido_service.py`
8. `app/templates/motochefe/vendas/pedidos/form.html`
9. `app/templates/base.html`

---

## 📊 PRÓXIMOS PASSOS (PÓS-DEPLOY)

1. **Treinar usuários** nas novas funcionalidades
2. **Configurar CrossDockings** conforme regras de negócio
3. **Monitorar** primeiros pedidos com parcelamento
4. **Validar** cálculos de frete e comissões

---

## 📞 SUPORTE

**Documentação completa**:
- 📋 [CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md](CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md) - Resumo completo
- 🎉 [PLANO_IMPLEMENTACAO_MOTOCHEFE.md](PLANO_IMPLEMENTACAO_MOTOCHEFE.md) - Plano detalhado
- 🚀 [MIGRATION_SQL_RENDER.sql](MIGRATION_SQL_RENDER.sql) - Script SQL

**Em caso de dúvidas**:
- Consulte os services criados como referência
- Todos os padrões seguem código existente
- Templates baseados em EquipeVendasMoto

---

✅ **Sistema pronto para produção!**

**Desenvolvido com precisão e atenção aos detalhes.** ✨
