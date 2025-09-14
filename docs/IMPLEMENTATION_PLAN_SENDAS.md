# 🔧 PLANO DE IMPLEMENTAÇÃO - UNIFICAÇÃO AGENDAMENTO SENDAS

**Data:** 2025-01-14
**Prioridade:** ALTA
**Tempo Estimado:** 8 horas

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### ✅ FASE 1: CORREÇÕES CRÍTICAS (2h)

#### 1.1 CORRIGIR ENDPOINT FLUXO 2
```javascript
// app/templates/carteira/js/agendamento/sendas/portal-sendas.js
// LINHA 187

// REMOVER:
const response = await fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async', {

// SUBSTITUIR POR:
const response = await fetch('/portal/sendas/fila/processar', {
```

#### 1.2 CORRIGIR WORKER - PRESERVAR DADOS
```python
# app/portal/workers/sendas_jobs.py
# LINHAS 36-58

# REMOVER TODO O BLOCO:
lista_cnpjs_processada = []
for item in lista_cnpjs_agendamento:
    # ... código que destrói dados
lista_cnpjs_agendamento = lista_cnpjs_processada

# SUBSTITUIR POR:
# Detectar formato e preservar dados completos
if lista_cnpjs_agendamento and isinstance(lista_cnpjs_agendamento[0], dict):
    if 'itens' in lista_cnpjs_agendamento[0]:
        # Dados completos - NÃO MODIFICAR
        logger.info("[Worker] Usando dados completos fornecidos")
    else:
        # Formato simples - converter datas se necessário
        for item in lista_cnpjs_agendamento:
            if isinstance(item.get('data_agendamento'), str):
                item['data_agendamento'] = datetime.strptime(
                    item['data_agendamento'], '%Y-%m-%d'
                ).date()
```

#### 1.3 ADICIONAR FLAG EM PREENCHER_PLANILHA
```python
# app/portal/sendas/preencher_planilha.py
# LINHA 144 - Modificar assinatura

# ATUAL:
def preencher_multiplos_cnpjs(self, arquivo_origem, lista_cnpjs_agendamento,
                              arquivo_destino=None):

# NOVO:
def preencher_multiplos_cnpjs(self, arquivo_origem, lista_cnpjs_agendamento,
                              arquivo_destino=None, usar_dados_fornecidos=False):

# LINHA 190 - Adicionar lógica no início do método:
if usar_dados_fornecidos and lista_cnpjs_agendamento and 'itens' in lista_cnpjs_agendamento[0]:
    logger.info("✅ Usando dados PRÉ-PROCESSADOS da fila")
    todos_dados = self._converter_dados_fornecidos(lista_cnpjs_agendamento)
else:
    logger.info("📋 Buscando dados das 3 fontes")
    # Código atual de busca...
```

#### 1.4 IMPLEMENTAR _converter_dados_fornecidos
```python
# app/portal/sendas/preencher_planilha.py
# ADICIONAR NOVO MÉTODO após linha 890

def _converter_dados_fornecidos(self, dados_fornecidos):
    """Converte dados da fila para formato esperado pelo preenchimento"""
    todos_dados = {}

    for grupo in dados_fornecidos:
        cnpj = grupo['cnpj']
        protocolo = grupo.get('protocolo')

        # Converter itens para formato interno
        dados_convertidos = []
        for item in grupo.get('itens', []):
            dados_convertidos.append({
                'num_pedido': item.get('num_pedido'),
                'pedido_cliente': item.get('pedido_cliente'),
                'cod_produto': item.get('cod_produto'),
                'nome_produto': item.get('nome_produto'),
                'quantidade': item.get('quantidade'),
                'peso': item.get('peso', 0),
                'data_expedicao': item.get('data_expedicao'),
                'data_agendamento': grupo.get('data_agendamento'),
                'protocolo': protocolo,
                'observacoes': f"Protocolo: {protocolo}"
            })

        todos_dados[cnpj] = {
            'cnpj': cnpj,
            'itens': dados_convertidos,
            'peso_total': grupo.get('peso_total', 0),
            'protocolo': protocolo
        }

    return todos_dados
```

---

### ✅ FASE 2: IMPLEMENTAR RETORNO DE PROTOCOLO (2h)

#### 2.1 CRIAR FUNÇÃO UNIVERSAL DE RETORNO
```python
# app/portal/sendas/retorno_agendamento.py
# CRIAR NOVO ARQUIVO

from app import db
from app.separacao.models import Separacao
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def salvar_protocolo_retorno(dados_retorno):
    """
    Salva protocolo no local correto baseado no tipo de origem

    Args:
        dados_retorno: {
            'tipo_origem': 'lote_sp'|'carteira'|'nf',
            'documento_origem': str,
            'protocolo': str,
            'data_agendamento': date,
            'itens': list
        }
    """
    try:
        tipo = dados_retorno.get('tipo_origem')
        documento = dados_retorno.get('documento_origem')
        protocolo = dados_retorno.get('protocolo')
        data_agendamento = dados_retorno.get('data_agendamento')

        if tipo in ['lote_sp', 'carteira']:
            # Atualizar Separacao
            updated = Separacao.query.filter_by(
                separacao_lote_id=documento
            ).update({
                'protocolo': protocolo,
                'agendamento': data_agendamento,
                'agendamento_confirmado': True
            })
            db.session.commit()
            logger.info(f"✅ Protocolo salvo em {updated} registros Separacao")

        elif tipo == 'nf':
            # Buscar EntregaMonitorada
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=documento
            ).first()

            if entrega:
                # Criar AgendamentoEntrega
                agendamento = AgendamentoEntrega(
                    entrega_id=entrega.id,
                    data_agendada=data_agendamento,
                    forma_agendamento='Portal Sendas',
                    protocolo_agendamento=protocolo,
                    status='confirmado',
                    autor='Sistema',
                    criado_em=datetime.utcnow()
                )
                db.session.add(agendamento)

                # Atualizar EntregaMonitorada
                entrega.data_agenda = data_agendamento
                entrega.reagendar = False

                db.session.commit()
                logger.info(f"✅ AgendamentoEntrega criado para NF {documento}")
            else:
                logger.warning(f"EntregaMonitorada não encontrada para NF {documento}")

        return True

    except Exception as e:
        logger.error(f"Erro ao salvar protocolo: {e}")
        db.session.rollback()
        return False
```

#### 2.2 INTEGRAR RETORNO NO WORKER
```python
# app/portal/workers/sendas_jobs.py
# LINHA 125 - Após sucesso do processamento

# ADICIONAR:
from app.portal.sendas.retorno_agendamento import salvar_protocolo_retorno

# LINHA 130-145 - Processar retorno
if resultado and protocolo:
    # Identificar tipo de origem
    tipo_origem = 'lote_sp'  # padrão
    documento_origem = None

    if lista_cnpjs_agendamento and 'itens' in lista_cnpjs_agendamento[0]:
        # Veio da fila - tem tipo_origem nos itens
        primeiro_item = lista_cnpjs_agendamento[0]['itens'][0]
        tipo_origem = primeiro_item.get('tipo_origem', 'lote_sp')
        documento_origem = primeiro_item.get('documento_origem')

    # Salvar protocolo
    dados_retorno = {
        'tipo_origem': tipo_origem,
        'documento_origem': documento_origem,
        'protocolo': protocolo,
        'data_agendamento': lista_cnpjs_agendamento[0].get('data_agendamento'),
        'itens': lista_cnpjs_agendamento[0].get('itens', [])
    }

    salvar_protocolo_retorno(dados_retorno)
```

---

### ✅ FASE 3: ADICIONAR IDENTIFICAÇÃO UNIVERSAL (2h)

#### 3.1 CRIAR ENDPOINT DIRETO POR CNPJ
```python
# app/portal/utils/routes.py
# ADICIONAR NOVO ENDPOINT

@portal_utils_bp.route('/api/identificar-portal-por-cnpj', methods=['POST'])
@login_required
def identificar_portal_por_cnpj():
    """Identifica portal diretamente pelo CNPJ"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj')

        if not cnpj:
            return jsonify({'success': False, 'error': 'CNPJ não fornecido'}), 400

        from app.portal.utils.grupo_empresarial import GrupoEmpresarial

        portal = GrupoEmpresarial.identificar_portal(cnpj)
        grupo = GrupoEmpresarial.identificar_grupo(cnpj)

        return jsonify({
            'success': True,
            'portal': portal,
            'grupo': grupo,
            'tem_portal': portal is not None
        })

    except Exception as e:
        logger.error(f"Erro ao identificar portal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

#### 3.2 ADICIONAR IDENTIFICAÇÃO NO FLUXO 3
```javascript
// app/templates/monitoramento/listar_entregas.html
// LINHA 2650 - Antes de abrir modal

// ADICIONAR:
async function identificarPortalPorCnpj(cnpj) {
    try {
        const response = await fetch('/portal/utils/api/identificar-portal-por-cnpj', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ cnpj: cnpj })
        });

        const result = await response.json();
        return result.portal;
    } catch (error) {
        console.error('Erro ao identificar portal:', error);
        return null;
    }
}

// LINHA 2655 - Ao clicar no botão
const portal = await identificarPortalPorCnpj(data.entrega.cnpj_cliente);
if (portal === 'sendas') {
    // Continuar com fluxo Sendas
} else if (portal === 'atacadao') {
    // Fluxo Atacadão
}
```

---

### ✅ FASE 4: REMOVER CÓDIGO REDUNDANTE (2h)

#### 4.1 REMOVER ARQUIVOS OBSOLETOS
```bash
# Executar comandos para remover arquivos documentados como obsoletos
rm docs/FLUXO_SENDAS_ATUAL_VS_IDEAL.md
rm docs/FLUXO_UNIFICADO_SENDAS.md
rm docs/FLUXOS_AGENDAMENTO_SENDAS.md
# Manter apenas TECHNICAL_SPEC_SENDAS.md e IMPLEMENTATION_PLAN_SENDAS.md
```

#### 4.2 REMOVER CÓDIGO COMENTADO
```python
# app/portal/sendas/preencher_planilha.py
# Remover todos os blocos comentados com # COMPATIBILIDADE
# Remover logs desnecessários de debug
```

---

## 🧪 TESTES DE VALIDAÇÃO

### TESTE 1: Fluxo 2 (Carteira)
1. Acessar carteira agrupada
2. Selecionar lote com CNPJ Sendas (06057223*)
3. Clicar em agendar
4. Verificar se chama `/portal/sendas/fila/processar`
5. Verificar protocolo salvo em Separacao

### TESTE 2: Fluxo 3 (NF)
1. Acessar listar entregas
2. Selecionar NF de cliente Sendas
3. Agendar via modal
4. Verificar AgendamentoEntrega criado com protocolo

### TESTE 3: Worker preservando dados
1. Verificar logs: "Usando dados PRÉ-PROCESSADOS"
2. Confirmar que pedido_cliente não é buscado novamente
3. Verificar tempo de processamento reduzido

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Antes | Depois |
|---------|-------|--------|
| Queries por agendamento | 300+ | <50 |
| Tempo processamento | 45s | <15s |
| Taxa erro pedido_cliente | 15% | <2% |
| Protocolos salvos | 33% | 100% |

---

## 🚀 ORDEM DE EXECUÇÃO

1. **BACKUP** do código atual
2. **FASE 1** - Correções críticas (HOJE)
3. **TESTES** básicos de não-regressão
4. **FASE 2** - Retorno protocolo
5. **FASE 3** - Identificação universal
6. **FASE 4** - Limpeza código
7. **TESTES** completos
8. **DEPLOY** em produção

---

## ⚠️ RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar Fluxo 1 | Baixa | Alto | Testar isoladamente |
| FilaAgendamentoSendas vazia | Média | Médio | Validar antes processar |
| Timeout no worker | Baixa | Baixo | Aumentar timeout para 20m |

---

## 📝 NOTAS FINAIS

- **NÃO adicionar compatibilidade** - Transição direta
- **Todos os fluxos via workers** - Manter assíncrono
- **FilaAgendamentoSendas necessária** - Para acumulação
- **pedido_cliente CRÍTICO** - Sempre com fallback Odoo
- **Protocolo em TODOS os fluxos** - Rastreabilidade completa