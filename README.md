# Sistema de Gestao de Fretes — NACOM GOYA

Plataforma enterprise para gestao logistica completa: carteira de pedidos, separacao, embarques, faturamento, frete, financeiro, integracoes ERP e automacao de portais. Operando em producao desde 2025 com 145+ tabelas, 30+ modulos e 147 arquivos de rotas.

## Stack Tecnologica

| Camada | Tecnologia |
|--------|------------|
| Framework | Flask 3.1, SQLAlchemy 2.0, PostgreSQL |
| Frontend | Jinja2, Bootstrap 5, design tokens (light/dark mode) |
| AI | Claude Agent SDK, Anthropic API 0.84, Voyage AI (embeddings semanticos) |
| Automacao | Playwright 1.58 (SSW, Atacadao Portal, NF-e Odoo) |
| Background | Redis 7.2 + RQ 2.6, APScheduler |
| Monitoramento | Sentry SDK 2.54 (APM + AI Monitoring) |
| Deploy | Render.com, Gunicorn 25.1 |
| Busca Semantica | pgvector (produto, entidades financeiras, sessoes agente) |

## Modulos

| Modulo | Descricao |
|--------|-----------|
| **Carteira** | Gestao de pedidos com priorizacao P1-P7, saldos e agendamento |
| **Separacao** | Controle de separacao de produtos, expedicao e protocolos |
| **Embarques** | Gestao de embarques, documentacao e controle de carga |
| **Faturamento** | Notas fiscais, faturamento por produto e acompanhamento |
| **Fretes** | Calculo de frete real vs teorico, tabelas de preco e margem |
| **Financeiro** | Contas a pagar/receber, reconciliacao, comprovantes, extratos |
| **CarVia** | Frete subcontratado: operacoes, cotacao, faturas cliente/transportadora |
| **Recebimento** | Validacao NF x PO, consolidacao, recebimento fisico (4 fases) |
| **Devolucao** | Controle de devolucoes e reversa logistica |
| **Pallet** | Cadastro de palletizacao, EAN e controle de pallets |
| **Estoque** | Consulta e gestao de estoque por produto |
| **Producao** | Programacao e acompanhamento de producao (manufatura) |
| **Cotacao** | Cotacao automatizada de frete por rota e transportadora |
| **Portaria** | Controle de entrada/saida de veiculos |
| **Monitoramento** | Acompanhamento em tempo real de operacoes |
| **Rastreamento** | Tracking de entregas e canhotos |
| **BI** | Dashboards e indicadores operacionais |
| **Seguranca** | Varredura de vulnerabilidades (email breaches, senhas, DNS) |
| **Agente Web** | Agente conversacional AI para usuarios finais (Claude Agent SDK) |
| **Embeddings** | Busca semantica para produtos, entidades financeiras e sessoes |
| **Teams** | Bot assincrono MS Teams via Azure Function bridge |
| **Portal** | Portal do cliente com acesso restrito |
| **Custeio** | Calculo de margem e custeio de frete |
| **Odoo** | Integracao completa ERP: fiscal, financeiro, NF-e, reconciliacao |

## Integracoes Externas

| Sistema | Funcao | Protocolo |
|---------|--------|-----------|
| **Odoo** | ERP — fiscal, financeiro, NF-e, pagamentos | XML-RPC |
| **SSW Sistemas** | TMS — faturamento, CT-e, romaneio, comissoes | Playwright + scraping |
| **Atacadao Portal** | Booking — agendamento, saldo, impressao pedidos | Playwright (Hodie Booking) |
| **MS Teams** | Notificacoes e bot conversacional | Azure Bot Framework |
| **Sentry** | Monitoramento de erros e performance (APM) | SDK + MCP Server |
| **Voyage AI** | Embeddings semanticos (produto, entidades, sessoes) | REST API |
| **Google Maps** | Geocodificacao e distancias | REST API |
| **HIBP** | Verificacao de breaches de email (k-anonymity) | REST API |
| **Linx Microvix** | Integracao com sistema Linx (WS) | SOAP/REST |

## Banco de Dados

- **145+ tabelas** PostgreSQL com schemas auto-documentados
- **pgvector** para busca semantica (3 dominos: produto, financeiro, agente)
- Schemas de referencia em `.claude/skills/consultando-sql/schemas/tables/`

## Instalacao Local

```bash
# Clonar repositorio
git clone <URL_DO_REPOSITORIO>
cd frete_sistema

# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais (ver secao abaixo)

# Executar
python run.py
```

## Variaveis de Ambiente

Configurar no arquivo `.env` (nunca comitar):

| Categoria | Variaveis |
|-----------|-----------|
| **Banco** | `DATABASE_URL`, `SQLALCHEMY_DATABASE_URI` |
| **Redis** | `REDIS_URL` |
| **Autenticacao** | `SECRET_KEY`, `SESSION_SECRET` |
| **Odoo** | `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`, `ODOO_API_KEY` |
| **SSW** | `SSW_URL`, `SSW_DOMINIO`, `SSW_CPF`, `SSW_LOGIN`, `SSW_SENHA` |
| **Atacadao** | `ATACADAO_URL`, `ATACADAO_USER`, `ATACADAO_PASSWORD` |
| **AI** | `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` |
| **Sentry** | `SENTRY_DSN`, `SENTRY_AI_MONITORING` |
| **Teams** | `TEAMS_APP_ID`, `TEAMS_APP_PASSWORD` |
| **Seguranca** | `SEGURANCA_SCAN_ENABLED`, `SEGURANCA_SCAN_HOUR` |
| **Feature Flags** | `PRODUCT_SEMANTIC_SEARCH`, `FINANCIAL_SEMANTIC_SEARCH` |

## Niveis de Acesso

| Nivel | Descricao | Acesso |
|-------|-----------|--------|
| **Portaria** | Acesso apenas aos embarques | Limitado |
| **Vendedor** | Monitoramento proprio + comentarios | Restrito |
| **Gerente Comercial** | Aprovar vendedores + acesso geral | Amplo |
| **Financeiro/Logistica** | Acesso e edicao geral | Completo |
| **Administrador** | Acesso irrestrito + seguranca | Total |

## Estrutura do Projeto

```
frete_sistema/
├── app/                        # Aplicacao principal
│   ├── agente/                 # Agente AI conversacional (Claude Agent SDK)
│   ├── auth/                   # Autenticacao e sessoes
│   ├── carteira/               # Carteira de pedidos (routes/, services/, utils/)
│   ├── carvia/                 # Frete subcontratado
│   ├── embarques/              # Gestao de embarques
│   ├── embeddings/             # Busca semantica (Voyage AI + pgvector)
│   ├── faturamento/            # Notas fiscais e faturamento
│   ├── financeiro/             # Modulo financeiro (routes/, services/, workers/)
│   ├── fretes/                 # Calculo e controle de frete
│   ├── odoo/                   # Integracao ERP (services/, utils/, jobs/)
│   ├── recebimento/            # Recebimento fisico (routes/, services/, workers/)
│   ├── seguranca/              # Varredura de vulnerabilidades
│   ├── teams/                  # Bot MS Teams
│   ├── templates/              # Templates Jinja2
│   ├── static/                 # CSS (design tokens), JS, uploads
│   └── ...                     # +15 modulos adicionais
├── scripts/
│   ├── migrations/             # DDL (Python + SQL) e data fixes
│   └── ...                     # Scripts operacionais
├── .claude/                    # Configuracao Claude Code (skills, references, schemas)
├── config.py                   # Configuracoes Flask
├── requirements.txt            # 171 dependencias
├── Procfile                    # Deploy Render (Gunicorn)
└── render.yaml                 # Configuracao Render
```

## Licenca

Sistema proprietario desenvolvido exclusivamente para NACOM GOYA.
Todos os direitos reservados.
