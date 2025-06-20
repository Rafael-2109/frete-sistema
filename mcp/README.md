# Model Context Protocol (MCP) - Sistema de Fretes

Este diretório contém a implementação do **Model Context Protocol** para o Sistema de Fretes, permitindo integração direta com modelos de IA (Claude) para consultar e analisar dados do sistema.

## 🚀 O que é o MCP?

O Model Context Protocol é um protocolo desenvolvido pela Anthropic que permite que aplicações se conectem com modelos de IA de forma mais integrada, fornecendo contexto específico do sistema e ferramentas especializadas.

## 📦 Instalação

### 1. Instalar Dependências

```bash
# No diretório raiz do projeto
pip install -r requirements.txt
```

As seguintes dependências MCP serão instaladas:
- `mcp==1.1.1` - Biblioteca principal do MCP
- `pydantic==2.10.3` - Validação de dados
- `anyio==4.7.0` - Programação assíncrona

### 2. Verificar Instalação

```bash
cd mcp
python start_mcp.py
```

## 🛠️ Configuração

### Para Claude Desktop

1. **Localize o arquivo de configuração:**
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Adicione a configuração do servidor:**

```json
{
  "mcpServers": {
    "frete-sistema": {
      "command": "python",
      "args": ["mcp/mcp_server.py"],
      "cwd": "C:\\Users\\rafael.nascimento\\Desktop\\Sistema Online\\frete_sistema",
      "env": {
        "FLASK_ENV": "development"
      }
    }
  }
}
```

3. **Reinicie o Claude Desktop**

## 🔧 Ferramentas Disponíveis

### `consultar_embarques`
Consulta embarques do sistema com filtros opcionais.

**Parâmetros:**
- `status` (string): ativo, cancelado
- `data_inicio` (string): Data início (YYYY-MM-DD)
- `data_fim` (string): Data fim (YYYY-MM-DD)
- `transportadora` (string): Nome da transportadora
- `limite` (integer): Número máximo de resultados (padrão: 10)

**Exemplo:**
```json
{
  "name": "consultar_embarques",
  "arguments": {
    "status": "ativo",
    "limite": 5
  }
}
```

### `consultar_fretes`
Consulta fretes do sistema.

**Parâmetros:**
- `embarque_id` (integer): ID específico do embarque
- `transportadora` (string): Nome da transportadora
- `status_aprovacao` (string): pendente, aprovado, rejeitado
- `tem_cte` (boolean): true/false se possui CTe
- `limite` (integer): Número máximo de resultados

### `consultar_monitoramento`
Consulta entregas em monitoramento.

**Parâmetros:**
- `nf_numero` (string): Número da nota fiscal
- `status` (string): Status da entrega
- `pendencia_financeira` (boolean): Se tem pendência financeira
- `limite` (integer): Número máximo de resultados

### `consultar_transportadoras`
Lista transportadoras cadastradas.

**Parâmetros:**
- `ativa` (boolean): Se a transportadora está ativa
- `freteiro` (boolean): Se é freteiro
- `nome` (string): Filtro por nome

### `consultar_pedidos`
Consulta pedidos do sistema.

**Parâmetros:**
- `numero_pedido` (string): Número do pedido
- `status` (string): Status do pedido
- `cliente` (string): Nome do cliente
- `limite` (integer): Número máximo de resultados

### `estatisticas_sistema`
Retorna estatísticas gerais do sistema.

**Parâmetros:**
- `periodo_dias` (integer): Período em dias (padrão: 30)

### `consultar_portaria`
Consulta registros da portaria.

**Parâmetros:**
- `status` (string): Status na portaria
- `placa` (string): Placa do veículo
- `data_inicio` (string): Data início
- `limite` (integer): Número máximo de resultados

## 📚 Recursos Disponíveis

### `frete://config/database`
Informações sobre a configuração do banco de dados.

### `frete://schemas/embarques`
Estrutura das tabelas de embarques.

### `frete://schemas/fretes`
Estrutura das tabelas de fretes.

### `frete://help/api`
Documentação das funcionalidades disponíveis.

## 🧪 Exemplos de Uso

### Consultas Básicas

**Embarques ativos:**
```
"Quais embarques estão ativos hoje?"
```

**Estatísticas recentes:**
```
"Mostre as estatísticas dos últimos 7 dias"
```

**Fretes pendentes:**
```
"Há fretes pendentes de aprovação?"
```

### Consultas Avançadas

**Embarques por transportadora:**
```
"Mostre os embarques da transportadora XYZ dos últimos 30 dias"
```

**Monitoramento por NF:**
```
"Qual o status da NF 123456?"
```

**Análise de portaria:**
```
"Quantos veículos estão na portaria agora?"
```

## 🔍 Troubleshooting

### Erro: "Dependência faltando"
```bash
pip install -r requirements.txt
```

### Erro: "Sistema Flask não carregado"
Verifique se:
1. O arquivo `.env` está configurado corretamente
2. O banco de dados está acessível
3. Não há erros de encoding (UTF-8)

### Erro: "MCP Server não conecta"
1. Verifique se o caminho no `claude_desktop_config.json` está correto
2. Reinicie o Claude Desktop
3. Verifique se não há erro de permissões

### Problema com UTF-8
Se houver erro de encoding no `.env`:
```bash
# Recrie o arquivo .env com encoding UTF-8
notepad .env  # Windows
nano .env     # Linux/Mac
```

## 🔐 Segurança

- O servidor MCP está configurado apenas para **leitura** (read-only)
- Não permite modificações nos dados do sistema
- Rate limiting configurado (100 requests/minuto)
- Máximo 10 requests simultâneos

## 📈 Performance

- Queries otimizadas com LIMIT padrão de 10 resultados
- Cache automático de conexões de banco
- Processamento assíncrono para melhor responsividade

## 🔄 Atualizações

Para atualizar o servidor MCP:

1. **Pare o servidor atual** (Ctrl+C)
2. **Atualize o código** conforme necessário
3. **Reinicie o servidor:**
   ```bash
   python start_mcp.py
   ```
4. **Reinicie o Claude Desktop** se necessário

## 📞 Suporte

Para problemas ou dúvidas:

1. Verifique os logs do servidor MCP
2. Teste as ferramentas individualmente
3. Consulte a documentação do MCP: https://modelcontextprotocol.io/
4. Verifique a configuração do Claude Desktop

## 🎯 Casos de Uso

### Para Gestores
- "Quantos embarques saíram esta semana?"
- "Qual o percentual de fretes aprovados?"
- "Há entregas em atraso?"

### Para Operação
- "Quais veículos estão aguardando na portaria?"
- "Mostre os embarques sem CTe"
- "Listar pedidos prontos para embarque"

### Para Financeiro
- "Quais fretes estão pendentes de pagamento?"
- "Mostre as pendências financeiras em aberto"
- "Relatório de faturamento do mês"

---

**Desenvolvido para integração com Claude via Model Context Protocol**  
*Sistema de Fretes - Versão MCP 1.0.0* 