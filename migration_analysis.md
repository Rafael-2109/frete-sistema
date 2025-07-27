# Análise das Migrations - Sistema de Frete

## Status Atual
- **Versão atual no banco**: `permission_system_v1`
- **PreSeparacaoItem**: Campo `separacao_lote_id` existe no modelo ✅

## Diferenças Detectadas

### 1. Novas Tabelas (a serem criadas)
```sql
- permission_cache
- submodule
- user_permission
- permissao_equipe
- permissao_vendedor
- permission_module
- permission_submodule
```

### 2. Tabelas Órfãs (existem no banco mas não nos modelos)
```sql
-- Tabelas de controle antigas
- controle_alteracao_carga
- evento_carteira
- log_atualizacao_carteira
- vinculacao_carteira_separacao
- snapshot_carteira
- tipo_envio
- pre_separacao_itens (duplicada)
- aprovacao_mudanca_carteira
- controle_descasamento_nf
- historico_faturamento
- validacao_nf_simples

-- Tabelas AI antigas
- ai_knowledge_patterns
- ai_advanced_sessions
- ai_learning_patterns
- ai_semantic_mappings
- ai_learning_metrics
- ai_system_config
- ai_business_contexts
- ai_performance_metrics
- ai_semantic_embeddings
- ai_feedback_history
- ai_grupos_empresariais
- ai_response_templates
- ai_learning_history
```

### 3. Mudanças Estruturais Importantes
- Alterações em foreign keys e relacionamentos
- Mudanças em campos de tabelas de permissão
- Novos índices para performance

## Ações Recomendadas

### 1. Backup Imediato
```bash
pg_dump -U frete_user -d frete_sistema > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Revisar Migration Gerada
- O arquivo `/home/rafaelnascimento/projetos/frete_sistema/migrations/versions/935bc4a541de_teste.py` foi gerado
- **NÃO APLICAR** diretamente sem revisão
- Muitas das remoções podem ser tabelas ainda em uso

### 3. Estratégia Sugerida
1. **Manter tabelas órfãs**: Não remover tabelas que podem conter dados importantes
2. **Aplicar apenas adições**: Criar novas tabelas e índices
3. **Postergar remoções**: Analisar cada tabela antes de remover

### 4. Migration Segura
Criar uma migration customizada que:
- Adicione as novas tabelas de permissão
- Adicione novos índices
- NÃO remova tabelas existentes
- Ajuste apenas estruturas críticas

## Próximos Passos
1. Revisar o arquivo de migration gerado
2. Criar migration customizada segura
3. Testar em ambiente de desenvolvimento
4. Aplicar gradualmente em produção