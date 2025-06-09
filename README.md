# 🚚 Sistema de Gestão de Fretes - NACOM GOYA

Sistema completo para gestão de fretes, pedidos, embarques e monitoramento logístico.

## 🏢 Empresa: NACOM GOYA
**Desenvolvido para:** Gestão completa da operação logística

## ⚡ Funcionalidades Principais

### 🎯 OPERACIONAL
- **Pedidos**: Controle completo de pedidos e status
- **Separação**: Gestão da separação de produtos
- **Embarques**: Controle de embarques e documentação
- **Monitoramento**: Acompanhamento em tempo real

### 💰 FINANCEIRO  
- **Fretes**: Cálculo e gestão de fretes
- **Controle Financeiro**: Acompanhamento de custos e receitas

### 📊 CADASTROS
- **Cadastros Gerais**: Clientes, fornecedores, produtos
- **Tabelas de Frete**: Configuração de preços e rotas

### 🔍 CONSULTAS
- **Relatórios**: Diversos relatórios operacionais
- **Importações**: Importação de dados em lote

### 👥 USUÁRIOS
- **Gestão de Usuários**: 5 níveis de permissão
- **Controle de Acesso**: Permissões granulares por módulo

## 🛡️ Níveis de Usuário

| Nível | Descrição | Acesso |
|-------|-----------|--------|
| **Portaria** | Acesso apenas aos embarques | Limitado |
| **Vendedor** | Monitoramento próprio + comentários | Restrito |
| **Gerente Comercial** | Aprovar vendedores + acesso geral | Amplo |
| **Financeiro/Logística** | Acesso e edição geral | Completo |
| **Administrador** | Acesso irrestrito | Total |

## 🚀 Deploy e Produção

### Status Atual: ✅ PRONTO PARA PRODUÇÃO

- ✅ Sistema completo implementado
- ✅ Controle de usuários funcional
- ✅ Dados de teste removidos
- ✅ Arquivos de produção configurados
- ✅ Guia de deploy criado

### Plataforma: Render.com
- **Frontend**: Flask + Bootstrap
- **Backend**: Python + SQLAlchemy  
- **Banco**: PostgreSQL (produção) / SQLite (desenvolvimento)
- **Deploy**: Automático via Git

## 📋 Pré-requisitos

- Python 3.11+
- PostgreSQL (produção)
- SQLite (desenvolvimento)

## 🔧 Instalação Local

```bash
# Clonar repositório
git clone https://github.com/SEU_USUARIO/sistema-fretes.git
cd sistema-fretes

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar banco
flask db upgrade

# Executar
python run.py
```

## 🌐 Acesso

### Desenvolvimento
- **URL**: http://localhost:5000
- **Usuário**: rafael@nacomgoya.com.br
- **Senha**: Rafa2109

### Produção
- **URL**: [Configurar após deploy]
- **Usuário**: rafael@nacomgoya.com.br
- **Senha**: Rafa2109

## 📁 Estrutura do Projeto

```
sistema-fretes/
├── app/                    # Aplicação principal
│   ├── auth/              # Autenticação e usuários
│   ├── pedidos/           # Módulo de pedidos
│   ├── embarques/         # Módulo de embarques
│   ├── fretes/            # Módulo de fretes
│   ├── monitoramento/     # Monitoramento
│   ├── templates/         # Templates HTML
│   └── static/            # CSS, JS, uploads
├── migrations/            # Migrações do banco
├── config.py             # Configurações
├── run.py                # Ponto de entrada
├── requirements.txt      # Dependências
├── Procfile              # Deploy Render
└── render.yaml           # Configuração Render
```

## 🔍 Módulos Implementados

### ✅ Completos e Funcionais:
- **Autenticação** - Sistema completo de usuários
- **Pedidos** - Controle de pedidos e status
- **Embarques** - Gestão de embarques
- **Fretes** - Cálculo e controle
- **Monitoramento** - Acompanhamento
- **Separação** - Controle de separação
- **Cadastros** - Gestão de cadastros
- **Financeiro** - Controle financeiro
- **Tabelas** - Configurações
- **Portaria** - Controle de portaria

## 📈 Próximos Passos

1. **Deploy no Render** (seguir GUIA_DEPLOY_RENDER.md)
2. **Importação de dados reais**
3. **Treinamento de usuários**
4. **Monitoramento em produção**
5. **Melhorias contínuas**

## 📞 Suporte Técnico

**Desenvolvedor**: Claude Sonnet (Anthropic)  
**Empresa**: NACOM GOYA  
**Contato**: rafael@nacomgoya.com.br

## 📄 Licença

Sistema proprietário desenvolvido exclusivamente para NACOM GOYA.

---

**🎉 Sistema de Fretes - Versão Produção**  
*Desenvolvido com ❤️ para otimizar sua operação logística* 