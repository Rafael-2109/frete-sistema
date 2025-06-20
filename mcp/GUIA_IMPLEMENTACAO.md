# 🚀 Guia Completo - Implementação MCP Sistema de Fretes

## ✅ Status Atual

- ✅ **Dependências instaladas**: mcp, pydantic, anyio
- ✅ **Estrutura criada**: Servidor MCP, configurações, documentação
- ✅ **Sistema Flask funcionando**: Carregamento dos modelos OK
- ⚠️ **Servidor complexo**: Erro na execução (TaskGroup)

## 🎯 Próximos Passos

### 1. Configuração do Claude Desktop

**Arquivo de configuração:**
```
Windows: C:\Users\rafael.nascimento\AppData\Roaming\Claude\claude_desktop_config.json
```

**Conteúdo a adicionar:**
```json
{
  "mcpServers": {
    "frete-sistema": {
      "command": "python",
      "args": ["mcp/test_mcp_simple.py"],
      "cwd": "C:\\Users\\rafael.nascimento\\Desktop\\Sistema Online\\frete_sistema",
      "env": {
        "FLASK_ENV": "development"
      }
    }
  }
}
```

### 2. Testando a Configuração

1. **Adicione a configuração** no arquivo do Claude Desktop
2. **Reinicie o Claude Desktop** completamente
3. **Teste com:** "Use a ferramenta test_sistema para verificar se está funcionando"

### 3. Resolução dos Problemas

#### Problema Principal: TaskGroup Error

O erro `unhandled errors in a TaskGroup` indica problema com a versão do MCP. 

**Soluções:**

**Opção A - Downgrade MCP:**
```bash
pip uninstall mcp
pip install mcp==1.0.0
```

**Opção B - Atualizar para última versão:**
```bash
pip install --upgrade mcp
```

**Opção C - Usar versão alternativa:**
```bash
pip install mcp-sdk
```

#### Teste Após Correção:
```bash
cd mcp
python test_mcp_simple.py
```

Se não houver erro e ficar aguardando input, significa que está funcionando!

### 4. Evolução do Sistema

#### Fase 1: Servidor Básico (ATUAL)
- ✅ Servidor simples funcional
- 🔄 Teste de conectividade
- 📋 Ferramenta básica de teste

#### Fase 2: Integração com Banco
```python
# Adicionar ao test_mcp_simple.py
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "consultar_embarques_simples":
        # Importar dentro da função
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.embarques.models import Embarque
            embarques = Embarque.query.limit(5).all()
            
            resultado = []
            for e in embarques:
                resultado.append({
                    'id': e.id,
                    'numero': e.numero,
                    'status': e.status
                })
            
            return [TextContent(
                type="text", 
                text=json.dumps(resultado, indent=2)
            )]
```

#### Fase 3: Servidor Completo
- Migrar funcionalidades do `mcp_server.py` uma por vez
- Testar cada ferramenta individualmente
- Adicionar tratamento de erros robusto

### 5. Casos de Uso Planejados

#### Para Gestão:
```
- "Quantos embarques saíram esta semana?"
- "Mostre estatísticas dos últimos 30 dias"
- "Há fretes pendentes de aprovação?"
```

#### Para Operação:
```
- "Quais veículos estão na portaria?"
- "Embarques sem CTe"
- "Status da NF 123456"
```

#### Para Financeiro:
```
- "Fretes pendentes de pagamento"
- "Pendências financeiras em aberto"
- "Relatório de faturamento"
```

### 6. Monitoramento e Debug

#### Logs do Servidor MCP:
```bash
# No diretório mcp
python test_mcp_simple.py > mcp_logs.txt 2>&1
```

#### Debug do Claude Desktop:
1. Abrir DevTools no Claude Desktop (Ctrl+Shift+I)
2. Verificar console para erros de MCP
3. Verificar se o servidor está sendo chamado

#### Teste Manual das Ferramentas:
```bash
# Testar JSON das ferramentas
echo '{"method": "tools/list"}' | python test_mcp_simple.py
```

### 7. Troubleshooting Comum

#### Erro: "Servidor não conecta"
1. Verificar caminho no `claude_desktop_config.json`
2. Verificar se Python está no PATH
3. Reiniciar Claude Desktop

#### Erro: "Dependência não encontrada"
```bash
# Reinstalar dependências
pip uninstall mcp pydantic anyio
pip install mcp==1.0.0 pydantic==2.10.3 anyio==4.7.0
```

#### Erro: "Flask não carrega"
1. Verificar arquivo `.env`
2. Verificar conexão com banco de dados
3. Verificar encoding UTF-8

### 8. Versões Testadas

```
✅ Funcionando:
- Python 3.11
- Flask 3.1.0
- SQLAlchemy 3.1.1

⚠️ Em teste:
- mcp 1.9.4 (versão atual - com erro)
- mcp 1.0.0 (versão recomendada)
```

### 9. Próxima Sessão

**Objetivos:**
1. ✅ Resolver problema TaskGroup
2. ✅ Testar conectividade básica
3. 🔄 Implementar primeira consulta real (embarques)
4. 🔄 Adicionar ferramentas uma por vez
5. 🔄 Testar integração completa

**Preparação:**
- [ ] Backup do servidor atual
- [ ] Teste com versão estável do MCP
- [ ] Configuração no Claude Desktop
- [ ] Primeiros testes de comunicação

---

## 📞 Suporte Rápido

**Erro comum:** `TaskGroup` → `pip install mcp==1.0.0`  
**Não conecta:** Reiniciar Claude Desktop  
**JSON inválido:** Verificar aspas duplas na configuração  
**Path error:** Usar barras duplas no Windows (`\\`)

**Status:** 🟡 **Em desenvolvimento** - Base sólida criada, ajustes finais necessários 