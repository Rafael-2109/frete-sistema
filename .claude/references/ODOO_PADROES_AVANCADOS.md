# Padroes Avancados de Implementacao - Odoo

**Ultima verificacao:** Janeiro/2026

---

## Padrao 1: Auditoria Completa por Etapa

```python
from datetime import datetime
import json

class MeuService:
    def _registrar_auditoria(self, entidade_id, etapa, status, **kwargs):
        """Registra CADA etapa para rastreabilidade total"""
        auditoria = MeuProcessoAuditoria(
            entidade_id=entidade_id,
            etapa=etapa,
            etapa_descricao=kwargs.get('descricao'),
            modelo_odoo=kwargs.get('modelo'),
            metodo_odoo=kwargs.get('metodo'),
            acao=kwargs.get('acao'),  # search_read, write, execute_kw
            status=status,  # SUCESSO, ERRO, AVISO
            mensagem=kwargs.get('mensagem'),
            dados_antes=json.dumps(kwargs.get('antes')) if kwargs.get('antes') else None,
            dados_depois=json.dumps(kwargs.get('depois')) if kwargs.get('depois') else None,
            tempo_execucao_ms=kwargs.get('tempo'),
            usuario_nome=self.usuario_nome,
            usuario_ip=self.usuario_ip,
            created_at=datetime.utcnow()
        )
        db.session.add(auditoria)
        db.session.commit()

    def _executar_com_auditoria(self, funcao, entidade_id, etapa, descricao, modelo, acao):
        """Wrapper que executa funcao e registra resultado"""
        inicio = datetime.utcnow()
        try:
            resultado = funcao()
            tempo = (datetime.utcnow() - inicio).total_seconds() * 1000
            self._registrar_auditoria(
                entidade_id, etapa, 'SUCESSO',
                descricao=descricao, modelo=modelo, acao=acao,
                mensagem='OK', tempo=tempo
            )
            return True, resultado, None
        except Exception as e:
            tempo = (datetime.utcnow() - inicio).total_seconds() * 1000
            self._registrar_auditoria(
                entidade_id, etapa, 'ERRO',
                descricao=descricao, modelo=modelo, acao=acao,
                mensagem=str(e), tempo=tempo
            )
            return False, None, str(e)
```

**Referencia:** `app/fretes/services/lancamento_odoo_service.py:498-672`

---

## Padrao 2: Retomada Automatica de Lancamentos Parciais

```python
def _verificar_lancamento_existente(self, dfe_id, company_id):
    """Determina de qual etapa continuar se lancamento foi interrompido"""
    # Verificar estado atual no Odoo
    dfe = self.odoo.read('l10n_br_ciel_it_account.dfe', [dfe_id],
                         ['purchase_id', 'purchase_fiscal_id'])

    if dfe[0].get('purchase_fiscal_id'):
        # Invoice ja existe - verificar estado
        po_fiscal = dfe[0]['purchase_fiscal_id']
        invoices = self.odoo.search_read('account.move',
            [('purchase_id', '=', po_fiscal[0])],
            ['state'])
        if invoices and invoices[0]['state'] == 'posted':
            return {'continuar_de_etapa': 16, 'motivo': 'Invoice ja confirmada'}
        return {'continuar_de_etapa': 13, 'motivo': 'Invoice existe mas nao confirmada'}

    if dfe[0].get('purchase_id'):
        # PO existe - verificar estado
        po = self.odoo.read('purchase.order', [dfe[0]['purchase_id'][0]], ['state'])
        if po[0]['state'] == 'purchase':
            return {'continuar_de_etapa': 11, 'motivo': 'PO confirmado, criar invoice'}
        return {'continuar_de_etapa': 9, 'motivo': 'PO existe mas nao confirmado'}

    return {'continuar_de_etapa': 0, 'motivo': 'Novo lancamento'}
```

---

## Padrao 3: Rollback Inteligente (So se NAO Completou)

```python
def _rollback_lancamento(self, entidade_id, etapas_concluidas, total_etapas=16):
    """Faz rollback APENAS se nao completou todas etapas"""
    if etapas_concluidas >= total_etapas:
        logger.info(f"Rollback NAO executado - todas {total_etapas} etapas concluidas")
        return False  # Preservar dados se completou

    # Limpar campos Odoo da entidade local
    entidade = db.session.get(MinhaEntidade, entidade_id)
    if entidade:
        entidade.odoo_dfe_id = None
        entidade.odoo_purchase_order_id = None
        entidade.odoo_invoice_id = None
        entidade.lancado_odoo_em = None
        entidade.lancado_odoo_por = None
        entidade.status = 'PENDENTE'  # Voltar ao estado anterior
        db.session.commit()
        logger.warning(f"Rollback executado para entidade {entidade_id} (etapa {etapas_concluidas})")
        return True
    return False
```

---

## Padrao 4: Batch Loading (Evitar N+1)

```python
def _sincronizar_com_batch(self, registros):
    """Reduz queries de N+1 para 3 queries totais"""
    # 1. Coletar TODOS os IDs de relacionamentos
    partner_ids = set()
    product_ids = set()
    for r in registros:
        if r.get('partner_id'):
            partner_ids.add(r['partner_id'][0])
        if r.get('product_id'):
            product_ids.add(r['product_id'][0])

    # 2. Fazer batch read UMA UNICA VEZ
    partners = {}
    if partner_ids:
        partner_data = self.odoo.read('res.partner', list(partner_ids),
                                       ['name', 'l10n_br_cnpj', 'state_id'])
        partners = {p['id']: p for p in partner_data}

    products = {}
    if product_ids:
        product_data = self.odoo.read('product.product', list(product_ids),
                                       ['default_code', 'name', 'uom_id'])
        products = {p['id']: p for p in product_data}

    # 3. Usar cache em memoria para processar
    for r in registros:
        partner_id = r['partner_id'][0] if r.get('partner_id') else None
        product_id = r['product_id'][0] if r.get('product_id') else None
        r['_partner_data'] = partners.get(partner_id, {})
        r['_product_data'] = products.get(product_id, {})

    return registros
```

**Referencia:** `app/odoo/services/pedido_compras_service.py` (99.8% otimizado)

---

## Padrao 5: Lock Anti-Duplicata com Redis

```python
import redis
import os

class MeuService:
    def __init__(self):
        self.redis = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))

    def processar_com_lock(self, item_id):
        """Evita processamento duplicado de mesmo item"""
        lock_key = f'lock:meu_processo:{item_id}'

        # Tentar adquirir lock (TTL 30min para operacoes longas)
        if not self.redis.set(lock_key, 'locked', nx=True, ex=1800):
            raise Exception(f"Item {item_id} ja em processamento por outro worker")

        try:
            resultado = self._processar_item(item_id)
            return resultado
        finally:
            # SEMPRE liberar lock no final
            self.redis.delete(lock_key)
```

---

## Padrao 6: Progresso em Tempo Real via Redis

```python
def _atualizar_progresso(self, job_id, etapa, total_etapas, mensagem):
    """Permite frontend acompanhar progresso do job"""
    self.redis.hset(f'job:{job_id}:progress', mapping={
        'etapa_atual': etapa,
        'total_etapas': total_etapas,
        'percentual': int((etapa / total_etapas) * 100),
        'mensagem': mensagem,
        'timestamp': datetime.utcnow().isoformat()
    })
    self.redis.expire(f'job:{job_id}:progress', 3600)  # TTL 1 hora

# No frontend (polling):
# GET /api/job/{job_id}/progress
# → { etapa_atual: 5, total_etapas: 16, percentual: 31, mensagem: "Configurando PO..." }
```

---

## Padrao 7: Timeout Override para Operacoes Longas

```python
def _gerar_po_com_timeout_estendido(self, dfe_id):
    """action_gerar_po_dfe pode demorar 60-90s"""
    try:
        # Timeout padrao e 90s - estender para 180s
        resultado = self.odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'action_gerar_po_dfe',
            [[dfe_id]],
            {},
            timeout_override=180  # 3 minutos
        )
        return resultado
    except Exception as e:
        if 'timeout' in str(e).lower():
            # PO pode ter sido criado mesmo com timeout
            # Verificar se existe antes de considerar erro
            dfe = self.odoo.read('l10n_br_ciel_it_account.dfe', [dfe_id], ['purchase_id'])
            if dfe[0].get('purchase_id'):
                return dfe[0]['purchase_id']  # Sucesso tardio
        raise
```

**Referencia:** `app/fretes/services/lancamento_odoo_service.py:1088-1141`

---

## Padrao 8: Commit Preventivo antes de Ops Longas

```python
def lancar_documento(self, entidade_id):
    """Sessao PostgreSQL expira em ~30s de inatividade"""

    # ETAPA 1-5: Operacoes rapidas locais
    entidade = db.session.get(MinhaEntidade, entidade_id)
    entidade.status = 'PROCESSANDO'
    db.session.commit()  # COMMIT antes de operacao longa

    # ETAPA 6: Operacao LONGA no Odoo (60-90s)
    po_id = self._gerar_po_com_timeout_estendido(dfe_id)

    # Re-buscar entidade (sessao pode ter expirado)
    entidade = db.session.get(MinhaEntidade, entidade_id)
    entidade.odoo_po_id = po_id
    db.session.commit()

    # ... continuar processamento
```

---

## Arvore de Decisao - Qual Padrao Usar

```
TIPO DE INTEGRACAO
│
├─ SINCRONIZACAO (Odoo → Local)
│  ├─ Dados simples (1 modelo) → Service direto
│  ├─ Dados relacionados (N modelos) → Padrao 4 (Batch Loading)
│  └─ Volume alto (>10K registros) → Paginacao + batch
│
├─ LANCAMENTO (Local → Odoo)
│  ├─ Documento simples → Padrao 1 (Auditoria)
│  ├─ Pode ser interrompido → Padrao 2 (Retomada) + Padrao 3 (Rollback)
│  └─ Operacao longa → Padrao 7 (Timeout) + Padrao 8 (Commit Preventivo)
│
├─ PROCESSAMENTO ASSINCRONO
│  ├─ Pode ter duplicatas → Padrao 5 (Lock Redis)
│  └─ Precisa progresso → Padrao 6 (Redis Pubsub)
│
└─ CRITICO (financeiro)
   └─ Usar TODOS os padroes aplicaveis
```

---

## Services de Referencia

| Service | Linhas | Padroes Usados | Arquivo |
|---------|--------|----------------|---------|
| `lancamento_odoo_service.py` | 1.824 | 1, 2, 3, 7, 8 | `app/fretes/services/` |
| `cte_service.py` | 976 | 4 | `app/odoo/services/` |
| `carteira_service.py` | 2.790 | 4 | `app/odoo/services/` |
| `pedido_compras_service.py` | 925 | 4 | `app/odoo/services/` |
| `recebimento_fisico_odoo_service.py` | 500+ | 5, 6 | `app/recebimento/services/` |
| `baixa_titulos_service.py` | 1.128 | 1 | `app/financeiro/services/` |
