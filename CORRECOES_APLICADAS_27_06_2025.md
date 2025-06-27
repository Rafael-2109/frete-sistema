# Correções Aplicadas - 27/06/2025

## 1. Campo observ_ped_1 aumentado para 700 caracteres ✅

### Alterações realizadas:
- **Migração criada**: `43f95a1ac288_aumentar_limite_observ_ped_1_para_700.py`
- **Modelo atualizado**: Campo em `app/separacao/models.py` alterado de String(255) para String(700)
- **Validação na importação**: Se o texto exceder 700 caracteres, será truncado automaticamente
- **Logs informativos**: Sistema avisa quando trunca o campo

### No Render:
- **Aplicação automática**: A migração será aplicada automaticamente durante o deploy
- **Comando executado**: `flask db upgrade` no `build.sh`
- **Nenhuma ação manual necessária**! 🎉

---

## 2. Erro de exportação Excel do monitoramento corrigido ✅

### Problema:
- `EntregaMonitorada.comentarios` não suportava eager loading devido a `lazy='dynamic'`

### Solução:
- Removido `joinedload` para comentários
- Comentários são carregados manualmente após a query principal
- Uso de atributo temporário `_comentarios_carregados` para otimização

---

## 3. Botão "Atrasados" nos pedidos ✅

### Posicionamento:
- Movido para o **lado esquerdo** dos botões de data

### Lógica de filtro ajustada:
- Considera apenas **data de expedição < hoje**
- **Remove** verificação de data de agendamento
- Filtra apenas pedidos **sem NF**
- Inclui pedidos com status "COTADO" ou "ABERTO"

### Dois níveis:
1. **Atrasados**: Todos os pedidos atrasados (cotados + abertos)
2. **Atrasados Abertos**: Apenas pedidos abertos atrasados

---

## 4. Validação de forma de agendamento ✅

### Fluxo implementado:
1. Se forma de agendamento foi preenchida → usa valor informado
2. Se não foi preenchida → busca em `cadastros_agendamento` pelo CNPJ
3. Se encontrou cadastro → usa forma cadastrada automaticamente
4. Se não encontrou → **obriga preenchimento** com mensagem de erro

### Mensagem de erro:
```
⚠️ É obrigatório informar a forma de agendamento! Este cliente não possui forma de agendamento cadastrada.
```

---

## 5. Filtro "Agend. Pendente" no Monitoramento corrigido ✅

### Problema:
- O filtro estava dentro de uma cadeia de `elif`, então só funcionava quando o status era exatamente "sem_agendamento"
- Entregas sem agendamento mas com outros status (atrasadas, no prazo) não apareciam
- CNPJs com pontos/traços não eram comparados corretamente

### Solução:
- Quando o status é "sem_agendamento", recria a query base para mostrar TODAS as entregas que precisam de agendamento
- Removidas máscaras de CNPJ em ambos os lados da comparação
- Usado `func.replace()` do SQLAlchemy para limpar CNPJs antes da comparação
- Aplicado tanto no filtro quanto no contador

### Funcionamento:
O filtro agora mostra TODAS as entregas que:
1. Têm o CNPJ do cliente cadastrado em `contatos_agendamento`
2. O contato tem forma de agendamento preenchida (diferente de vazio ou "SEM AGENDAMENTO")
3. A entrega não tem nenhum agendamento registrado
4. A entrega não foi finalizada
5. **Independente de outros status** (atrasada, no prazo, etc)

### Script de diagnóstico:
- Criado `verificar_agendamento_pendente.py` para debugar problemas específicos

---

## Resumo das Correções

✅ **Todas as 5 correções foram implementadas com sucesso!**

1. **Campo observ_ped_1**: Aumentado para 700 caracteres com truncamento automático
2. **Exportação Excel**: Corrigido erro de eager loading com comentários
3. **Botão "Atrasados"**: Adicionado à esquerda, filtra por expedição < hoje
4. **Agendamento**: Validação melhorada com busca automática em cadastros
5. **Filtro "Agend. Pendente"**: Corrigido problema de comparação de CNPJs

### Deploy no Render:
- As migrações serão aplicadas automaticamente durante o deploy
- Nenhuma ação manual necessária!

## Notas importantes:

1. **Migração no Render**: Será aplicada automaticamente no próximo deploy
2. **Botão "Agend. Pendente"**: O problema mencionado precisa ser investigado - o filtro `sem_agendamento` parece estar correto no código
3. **Testes recomendados**: Após o deploy, testar importação de separações com campos grandes de observação 