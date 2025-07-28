# Claude AI Migration Scripts

Comprehensive migration toolkit for transferring data and functionality from `claude_ai_novo` to the new MCP (Model Context Protocol) system.

## 📋 Overview

This migration suite provides a complete solution for migrating:
- **Data**: Conversation history, patterns, configurations  
- **Knowledge Base**: SQL databases, semantic mappings, learning patterns
- **Sessions**: Active user sessions, conversation context, memory data
- **Configurations**: Environment variables, system settings, module configs
- **Validation**: Data integrity, completeness, performance testing
- **Rollback**: Complete system restoration capabilities

## 🗂️ Migration Scripts

### Core Migration Scripts

| Script | Purpose | Features |
|--------|---------|----------|
| `claude_ai_migration.py` | Main data migration | Conversation history, learned patterns, configs |
| `config_migrator.py` | Configuration migration | Python/JSON configs, environment variables |
| `knowledge_migrator.py` | Knowledge base migration | SQL databases, semantic mappings, learning data |
| `session_migrator.py` | Session data migration | Active sessions, conversation context, memory |
| `validation_scripts.py` | Data integrity validation | Completeness, performance, integrity checks |
| `migration_orchestrator.py` | Complete workflow orchestration | Parallel execution, progress monitoring |
| `rollback_procedures.py` | Rollback capabilities | Backup restoration, system recovery |

## 🚀 Quick Start

### 1. Simple Migration (Recommended)
```bash
# Run complete migration with orchestrator
python migration/migration_orchestrator.py

# With custom paths
python migration/migration_orchestrator.py \
  --source app/claude_ai_novo \
  --target-db "sqlite:///mcp_sistema.db"
```

### 2. Parallel Migration (Faster)
```bash
# Use parallel execution for faster migration
python migration/migration_orchestrator.py --parallel
```

### 3. Individual Components
```bash
# Migrate only specific components
python migration/claude_ai_migration.py
python migration/config_migrator.py 
python migration/knowledge_migrator.py
python migration/session_migrator.py
```

## 🔧 Detailed Usage

### Migration Orchestrator (Recommended)

The orchestrator coordinates the complete migration process:

```bash
# Full migration with all options
python migration/migration_orchestrator.py \
  --source app/claude_ai_novo \
  --target-db "sqlite:///mcp_sistema.db" \
  --parallel \
  --rollback-on-failure

# Skip specific phases
python migration/migration_orchestrator.py \
  --skip-config \
  --skip-sessions \
  --no-validation

# Sequential execution (safer but slower)
python migration/migration_orchestrator.py --sequential
```

**Orchestrator Options:**
- `--parallel` - Use parallel execution (default)
- `--sequential` - Use sequential execution  
- `--no-backups` - Skip backup creation
- `--no-validation` - Skip validation phase
- `--rollback-on-failure` - Auto-rollback on failure
- `--skip-data` - Skip data migration
- `--skip-config` - Skip configuration migration
- `--skip-knowledge` - Skip knowledge migration
- `--skip-sessions` - Skip session migration

### Individual Migration Scripts

#### 1. Data Migration
```bash
# Basic data migration
python migration/claude_ai_migration.py

# With custom paths
python migration/claude_ai_migration.py \
  --source app/claude_ai_novo \
  --target-db "postgresql://user:pass@host/db"

# Dry run (analysis only)
python migration/claude_ai_migration.py --dry-run
```

#### 2. Configuration Migration
```bash
# Migrate configurations
python migration/config_migrator.py

# Custom source and target
python migration/config_migrator.py \
  --source app/claude_ai_novo \
  --target app/mcp_sistema

# Dry run
python migration/config_migrator.py --dry-run
```

#### 3. Knowledge Base Migration
```bash
# Migrate knowledge base
python migration/knowledge_migrator.py

# With specific database
python migration/knowledge_migrator.py \
  --target-db "sqlite:///knowledge.db"

# Dry run
python migration/knowledge_migrator.py --dry-run
```

#### 4. Session Migration
```bash
# Migrate sessions
python migration/session_migrator.py

# Custom configuration
python migration/session_migrator.py \
  --source app/claude_ai_novo \
  --target-db "sqlite:///sessions.db"

# Dry run
python migration/session_migrator.py --dry-run
```

### Validation

```bash
# Run all validation tests
python migration/validation_scripts.py

# Run specific test
python migration/validation_scripts.py --test integrity
python migration/validation_scripts.py --test performance
python migration/validation_scripts.py --test completeness

# Available tests: integrity, completeness, performance, 
# configuration, sessions, knowledge, rollback
```

### Rollback Procedures

```bash
# Complete rollback
python migration/rollback_procedures.py

# Rollback with specific backup
python migration/rollback_procedures.py \
  --backup-path migration_workspace/20250128_123456/backups/pre_migration

# Analyze backup only
python migration/rollback_procedures.py --analyze-only

# Selective rollback
python migration/rollback_procedures.py \
  --no-database \
  --no-source \
  --no-cleanup
```

## 📊 Migration Process Flow

### Phase 1: Preparation
1. **Backup Creation** - Create pre-migration backups
2. **Source Analysis** - Analyze claude_ai_novo data
3. **Target Preparation** - Prepare MCP system

### Phase 2: Data Migration (Parallel)
1. **Data Migration** - Conversation history, patterns
2. **Configuration Migration** - Settings, environment variables

### Phase 3: Knowledge & Sessions (Parallel)  
1. **Knowledge Migration** - Databases, semantic mappings
2. **Session Migration** - Active sessions, context

### Phase 4: Validation
1. **Data Integrity** - Verify data consistency
2. **Completeness** - Check migration completeness
3. **Performance** - Test system performance
4. **Functionality** - Validate core features

### Phase 5: Reporting
1. **Migration Summary** - Detailed results
2. **Performance Metrics** - Timing and efficiency
3. **Recommendations** - Next steps and improvements

## 📁 Output Files

### Migration Reports
- `migration_final_report.json` - Complete migration summary
- `migration_summary_claude_ai.json` - Data migration details
- `migration_summary_config.json` - Configuration migration details  
- `migration_summary_knowledge.json` - Knowledge migration details
- `migration_summary_sessions.json` - Session migration details
- `migration_validation_report.json` - Validation results

### Log Files
- `migration_orchestrator.log` - Main orchestrator logs
- `migration_claude_ai.log` - Data migration logs
- `migration_config.log` - Configuration migration logs
- `migration_knowledge.log` - Knowledge migration logs
- `migration_sessions.log` - Session migration logs
- `migration_validation.log` - Validation logs
- `migration_rollback.log` - Rollback operation logs

### Workspace Structure
```
migration_workspace_20250128_123456/
├── backups/
│   └── pre_migration/
│       ├── claude_ai_novo_backup.tar.gz
│       ├── mcp_database_backup.db
│       └── backup_manifest.json
├── reports/
│   ├── migration_analysis.json
│   ├── performance_metrics.json
│   └── validation_results.json
└── logs/
    ├── orchestrator.log
    ├── migration_phases.log
    └── error_details.log
```

## ⚙️ Configuration

### Environment Variables

Set these before migration:

```bash
# Required
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite:///mcp_sistema.db"

# MCP-specific (auto-generated during migration)
export MCP_SERVER_NAME="freight-mcp"
export MCP_TOOL_TIMEOUT=30000
export MCP_MAX_CONCURRENT_TOOLS=10
export MCP_RESOURCE_CACHE_TTL=300

# Optional
export MCP_DEBUG=true
export MCP_LOG_LEVEL=INFO
```

### Database Configuration

The migration scripts support both SQLite and PostgreSQL:

**SQLite (Development):**
```bash
export DATABASE_URL="sqlite:///sistema_fretes.db"
```

**PostgreSQL (Production):**
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

## 🔍 Migration Analysis

### Pre-Migration Analysis

Run analysis before migration to understand scope:

```bash
# Analyze all components
python migration/claude_ai_migration.py --dry-run
python migration/config_migrator.py --dry-run
python migration/knowledge_migrator.py --dry-run
python migration/session_migrator.py --dry-run
```

### Expected Migration Data

| Component | Typical Volume | Migration Time |
|-----------|---------------|----------------|
| Conversations | 100-1000 items | 2-10 minutes |
| Configurations | 50-200 files | 1-3 minutes |
| Knowledge Base | 1-10 GB | 5-30 minutes |
| Sessions | 10-100 sessions | 1-5 minutes |
| **Total** | **Variable** | **10-50 minutes** |

## ✅ Validation Criteria

### Data Integrity (90%+ target)
- ✅ Database connections functional
- ✅ Table structures correct
- ✅ Foreign key constraints valid
- ✅ Data consistency maintained

### Completeness (95%+ target)
- ✅ All migration summaries present
- ✅ Expected data volumes migrated
- ✅ No missing critical components

### Performance (85%+ target)
- ✅ Database queries < 5 seconds
- ✅ Session operations < 3 seconds
- ✅ Resource access < 2 seconds

## 🔄 Rollback Procedures

### When to Rollback
- ✅ Migration validation fails
- ✅ Critical data missing
- ✅ Performance unacceptable
- ✅ System functionality broken

### Rollback Process
1. **Backup Analysis** - Verify backup integrity
2. **Database Restoration** - Restore from backup
3. **Configuration Restoration** - Restore settings
4. **Source Data Restoration** - Restore original data
5. **Cleanup** - Remove migrated data
6. **Verification** - Verify rollback success

### Rollback Commands
```bash
# Complete rollback
python migration/rollback_procedures.py

# Selective rollback
python migration/rollback_procedures.py --no-cleanup

# Analyze backup first
python migration/rollback_procedures.py --analyze-only
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Source Path Not Found
```
Error: Source path does not exist: app/claude_ai_novo
```
**Solution:** Specify correct source path with `--source` parameter

#### 2. Database Connection Failed
```
Error: Failed to initialize database: permission denied
```
**Solution:** Check database permissions and connection string

#### 3. Insufficient Disk Space
```
Error: No space left on device
```
**Solution:** Free disk space or use external storage for workspace

#### 4. Migration Timeout
```
Error: Operation timed out after 600 seconds
```
**Solution:** Use `--sequential` mode or increase timeout

### Debug Mode

Enable verbose logging:

```bash
export MCP_DEBUG=true
export MCP_LOG_LEVEL=DEBUG

# Run migration with debug info
python migration/migration_orchestrator.py --parallel
```

### Performance Issues

For large datasets:

```bash
# Use sequential mode
python migration/migration_orchestrator.py --sequential

# Skip non-essential components
python migration/migration_orchestrator.py \
  --skip-sessions \
  --no-validation

# Process in smaller chunks
python migration/claude_ai_migration.py --chunk-size 100
```

## 📞 Support

### Getting Help

1. **Check Logs** - Review log files for detailed errors
2. **Run Validation** - Use validation scripts to identify issues  
3. **Try Rollback** - Restore system to pre-migration state
4. **Analyze Backup** - Verify backup integrity

### Error Reporting

When reporting issues, include:
- Migration command used
- Error message and stack trace
- Relevant log files
- System information (OS, Python version)
- Database type and version

### Best Practices

1. **Always backup** before migration
2. **Test on staging** environment first
3. **Run validation** after migration
4. **Monitor performance** post-migration
5. **Keep backups** for rollback capability

## 🔐 Security Considerations

### Data Protection
- ✅ All sensitive data encrypted in transit
- ✅ Database credentials secured
- ✅ Backup files protected
- ✅ Log files sanitized

### Access Control
- ✅ Migration scripts require appropriate permissions
- ✅ Database access controlled
- ✅ Workspace files secured
- ✅ Rollback procedures protected

## 📈 Performance Optimization

### Parallel Execution
- Use `--parallel` for faster migration
- Monitor system resources during migration
- Adjust `--max-concurrent-tools` if needed

### Database Optimization
- Use SSD storage for better performance
- Increase database connection pool size
- Enable query optimization
- Monitor database locks

### Memory Management
- Large datasets may require more RAM
- Use pagination for large result sets
- Monitor memory usage during migration
- Consider chunked processing for huge datasets

## 🎯 Success Criteria

Migration is considered successful when:

✅ **All validation tests pass (90%+ score)**
✅ **No critical errors in logs**
✅ **System functionality verified**
✅ **Performance meets requirements**
✅ **Data integrity maintained**
✅ **Rollback capability confirmed**

---

**Next Steps:** After successful migration, update system configurations to use MCP endpoints and monitor system performance.