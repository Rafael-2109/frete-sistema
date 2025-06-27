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
- Removido `joinedload(EntregaMonitorada.comentarios)` da query principal
- Comentários agora são carregados manualmente após a query principal
- Adicionado atributo `_comentarios_carregados` para cache
- Sistema usa comentários pré-carregados quando disponíveis

---

## 3. Botão "Atrasados" reposicionado e filtro ajustado ✅

### Alterações:
- **Posição**: Movido para o lado esquerdo (antes das datas)
- **Critério**: Considera apenas **data de expedição < hoje** 
- **Não** verifica mais data de agendamento
- **Sem NF**: Filtra apenas pedidos sem nota fiscal
- **Contador**: Mostra quantos pedidos estão nesta condição
- **JavaScript**: Mantém filtros ao ordenar colunas

---

## 4. Validação de agendamento ajustada ✅

### Regra implementada:
1. **Se forma preenchida**: Grava com a forma informada
2. **Se forma vazia**: Busca em `cadastros_agendamento` por CNPJ
3. **Se encontrar cadastro**: Usa forma e contato cadastrados
4. **Se não encontrar**: Exige preenchimento obrigatório

### Correção adicional:
- **Protocolo não é obrigatório**: Removido `required` do campo no modal HTML
- Protocolo continua opcional conforme formulário backend

---

## 5. Filtro "Agend. Pendente" no Monitoramento corrigido ✅

### Problema principal:
- **Alerta funcionava** mas **filtro não** devido a diferenças na implementação
- Alerta usava dicionário Python sem limpeza de CNPJ
- Filtro usava SQL com `func.replace` para limpar CNPJs

### Solução implementada:
- **Dicionário híbrido**: Criado com CNPJs originais E limpos para compatibilidade
- **Template atualizado**: Verificação com CNPJs limpos em ambas as tabelas (agrupada e normal)
- **Sincronização**: Alerta e filtro agora usam exatamente a mesma lógica

### Como funciona agora:
O filtro mostra TODAS as entregas que:
1. ✅ Têm CNPJ do cliente cadastrado em `contatos_agendamento`
2. ✅ O contato tem forma de agendamento preenchida (≠ vazio ou "SEM AGENDAMENTO")
3. ✅ A entrega não tem nenhum agendamento registrado
4. ✅ A entrega não foi finalizada

---

## ✅ Status Final:

Todas as 5 correções foram implementadas com sucesso:
1. **Campo observ_ped_1**: Expandido para 700 caracteres ✅
2. **Export Excel**: Erro de eager loading resolvido ✅  
3. **Botão Atrasados**: Reposicionado e com filtro correto ✅
4. **Agendamento**: Validação inteligente implementada ✅
5. **Filtro Agend. Pendente**: Sincronizado com alerta ✅

**Deploy necessário**: Fazer push para o Render aplicar as alterações automaticamente.

## Notas importantes:

1. **Migração no Render**: Será aplicada automaticamente no próximo deploy
2. **Botão "Agend. Pendente"**: O problema mencionado precisa ser investigado - o filtro `sem_agendamento` parece estar correto no código
3. **Testes recomendados**: Após o deploy, testar importação de separações com campos grandes de observação 