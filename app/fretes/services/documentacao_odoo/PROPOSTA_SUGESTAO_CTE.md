# 💡 PROPOSTA: SUGESTÃO AUTOMÁTICA DE CT-e NO FRETE

**Data:** 15/11/2025
**Objetivo:** Otimizar preenchimento de CT-e usando dados já importados do Odoo, mantendo controle do usuário

---

## 🎯 MOMENTO IDEAL

**Rota:** `/fretes/<int:frete_id>/editar`
**Quando:** Ao abrir formulário de edição E frete NÃO tiver `numero_cte` preenchido

---

## 📋 SOLUÇÃO PROPOSTA: COMBO (HÍBRIDA)

### Backend (routes.py)

```python
@fretes_bp.route('/<int:frete_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_frete(frete_id):
    """Edita dados do CTe e valores do frete"""
    frete = Frete.query.get_or_404(frete_id)

    # ✅ VALIDAÇÃO: Não permitir lançar CTe sem fatura vinculada
    if not frete.fatura_frete_id:
        flash('❌ Este frete não possui fatura vinculada!', 'error')
        return redirect(url_for('fretes.visualizar_frete', frete_id=frete.id))

    form = FreteForm(obj=frete)

    # ✅ NOVO: Buscar CTes relacionados para sugestão
    ctes_sugeridos = []
    if not frete.numero_cte:  # Só sugere se ainda não tiver CTe lançado
        ctes_sugeridos = frete.buscar_ctes_relacionados()

    # ✅ CORREÇÃO: Auto-preencher vencimento da fatura
    if frete.fatura_frete and frete.fatura_frete.vencimento and not frete.vencimento:
        frete.vencimento = frete.fatura_frete.vencimento
        form.vencimento.data = frete.fatura_frete.vencimento

    if form.validate_on_submit():
        # ... código existente ...
        pass

    return render_template('fretes/editar_frete.html',
                         form=form,
                         frete=frete,
                         ctes_sugeridos=ctes_sugeridos)  # ✅ NOVO
```

---

### Frontend (editar_frete.html)

#### 1. Alerta para 1 CTe (no topo do formulário)

```html
{% if ctes_sugeridos and ctes_sugeridos|length == 1 %}
{% set cte = ctes_sugeridos[0] %}
<div class="alert alert-info alert-dismissible fade show" role="alert">
    <h5 class="alert-heading">
        <i class="fas fa-lightbulb"></i> CTe Sugerido Encontrado!
    </h5>
    <p class="mb-2">
        Encontramos 1 CTe do Odoo que corresponde a este frete:
    </p>
    <div class="card border-primary mb-2">
        <div class="card-body py-2">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <strong>CTe {{ cte.numero_cte }}{% if cte.serie_cte %}/{{ cte.serie_cte }}{% endif %}</strong><br>
                    <small class="text-muted">
                        Emitente: {{ cte.nome_emitente }}<br>
                        Emissão: {{ cte.data_emissao.strftime('%d/%m/%Y') if cte.data_emissao else 'N/A' }}<br>
                        Valor Total: {{ (cte.valor_total or 0)|moeda_carteira }}<br>
                        Valor Frete: {{ (cte.valor_frete or 0)|moeda_carteira }}
                    </small>
                </div>
                <div class="col-md-4 text-end">
                    <button type="button"
                            class="btn btn-success btn-sm"
                            onclick="preencherCTe('{{ cte.numero_cte }}', '{{ cte.valor_frete }}', '{{ cte.data_emissao.strftime('%Y-%m-%d') if cte.data_emissao else '' }}')">
                        <i class="fas fa-check"></i> Usar este CTe
                    </button>
                    {% if cte.cte_pdf_path %}
                    <a href="{{ url_for('cte.visualizar_pdf', cte_id=cte.id) }}"
                       class="btn btn-danger btn-sm"
                       target="_blank">
                        <i class="fas fa-file-pdf"></i> Ver PDF
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}
```

#### 2. Seção para Múltiplos CTes (antes do formulário)

```html
{% if ctes_sugeridos and ctes_sugeridos|length > 1 %}
<div class="card mb-4 border-info">
    <div class="card-header bg-info">
        <h5 class="mb-0">
            <i class="fas fa-search"></i> CTes Sugeridos ({{ ctes_sugeridos|length }} encontrados)
        </h5>
    </div>
    <div class="card-body">
        <p class="text-muted small mb-3">
            <i class="fas fa-info-circle"></i>
            Encontramos {{ ctes_sugeridos|length }} CTes do Odoo com NFs em comum e mesmo prefixo de CNPJ.
            Clique em "Usar" para preencher automaticamente.
        </p>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>CTe</th>
                        <th>Emitente</th>
                        <th>Emissão</th>
                        <th>Valor Frete</th>
                        <th>Status Odoo</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for cte in ctes_sugeridos %}
                    <tr>
                        <td>
                            <strong>{{ cte.numero_cte }}{% if cte.serie_cte %}/{{ cte.serie_cte }}{% endif %}</strong>
                        </td>
                        <td>{{ cte.nome_emitente }}</td>
                        <td>{{ cte.data_emissao.strftime('%d/%m/%Y') if cte.data_emissao else 'N/A' }}</td>
                        <td>{{ (cte.valor_frete or 0)|moeda_carteira }}</td>
                        <td>
                            <span class="badge bg-secondary">
                                {{ cte.odoo_status_descricao or 'N/A' }}
                            </span>
                        </td>
                        <td>
                            <button type="button"
                                    class="btn btn-success btn-sm"
                                    onclick="preencherCTe('{{ cte.numero_cte }}', '{{ cte.valor_frete }}', '{{ cte.data_emissao.strftime('%Y-%m-%d') if cte.data_emissao else '' }}')">
                                <i class="fas fa-check"></i> Usar
                            </button>
                            {% if cte.cte_pdf_path %}
                            <a href="{{ url_for('cte.visualizar_pdf', cte_id=cte.id) }}"
                               class="btn btn-danger btn-sm"
                               target="_blank">
                                <i class="fas fa-file-pdf"></i>
                            </a>
                            {% endif %}
                            <a href="{{ url_for('cte.detalhar_cte', cte_id=cte.id) }}"
                               class="btn btn-info btn-sm"
                               target="_blank">
                                <i class="fas fa-info-circle"></i>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endif %}
```

#### 3. JavaScript para Preencher Campos

```html
<script>
function preencherCTe(numero_cte, valor_frete, data_emissao) {
    // Preencher número do CTe
    document.getElementById('numero_cte').value = numero_cte;

    // Preencher valor CTe (converter para formato brasileiro)
    const valorFormatado = parseFloat(valor_frete).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    document.getElementById('valor_cte').value = valorFormatado;

    // Copiar valor para valor_considerado (usuário pode editar depois)
    document.getElementById('valor_considerado').value = valorFormatado;

    // Data de emissão (se tiver campo)
    if (data_emissao && document.getElementById('data_emissao_cte')) {
        document.getElementById('data_emissao_cte').value = data_emissao;
    }

    // Feedback visual
    Swal.fire({
        icon: 'success',
        title: 'CTe Selecionado!',
        text: `Dados do CTe ${numero_cte} foram preenchidos. Revise e clique em Salvar.`,
        timer: 3000,
        showConfirmButton: false
    });

    // Scroll para o formulário
    document.getElementById('form-cte').scrollIntoView({ behavior: 'smooth' });

    // Destacar campos preenchidos
    document.getElementById('numero_cte').classList.add('border-success', 'border-2');
    document.getElementById('valor_cte').classList.add('border-success', 'border-2');

    // Remover destaque após 3 segundos
    setTimeout(() => {
        document.getElementById('numero_cte').classList.remove('border-success', 'border-2');
        document.getElementById('valor_cte').classList.remove('border-success', 'border-2');
    }, 3000);
}
</script>
```

---

## 🎨 COMPORTAMENTOS POR CENÁRIO

| Cenário | Comportamento |
|---------|---------------|
| **0 CTes encontrados** | Formulário normal, sem sugestões |
| **1 CTe encontrado** | Alerta azul no topo com botão "Usar este CTe" |
| **2+ CTes encontrados** | Tabela com todos os CTes, cada um com botão "Usar" |
| **Frete já tem CTe** | Não busca sugestões (não mostra nada) |

---

## ✅ VALIDAÇÃO DO USUÁRIO

**IMPORTANTE:** Usuário SEMPRE tem controle:
1. ✅ Pode **ignorar** a sugestão e preencher manualmente
2. ✅ Pode **editar** valores após clicar em "Usar"
3. ✅ **PRECISA clicar em Salvar** para gravar (nada é automático)
4. ✅ Pode **comparar** CTes antes de escolher (se múltiplos)

---

## 📊 DADOS PREENCHIDOS AUTOMATICAMENTE

Ao clicar em "Usar este CTe":

| Campo Frete | Origem CT-e | Editável? |
|-------------|-------------|-----------|
| `numero_cte` | `numero_cte` | ✅ SIM |
| `valor_cte` | `valor_frete` | ✅ SIM |
| `valor_considerado` | `valor_frete` (cópia inicial) | ✅ SIM |
| `data_emissao_cte` | `data_emissao` | ✅ SIM (se campo existir) |

**NÃO preenche automaticamente:**
- ❌ `valor_pago` → Usuário decide depois
- ❌ `status` → Calculado pelas regras
- ❌ `considerar_diferenca` → Escolha do usuário

---

## 🚀 VANTAGENS DA SOLUÇÃO

1. ✅ **Otimiza 80% dos casos** (CT-e já está no Odoo)
2. ✅ **Não força** nada (usuário mantém controle)
3. ✅ **Reduz erros** de digitação
4. ✅ **Acelera** o processo de lançamento
5. ✅ **Permite comparação** quando há múltiplos CTes
6. ✅ **Não invasivo** (não bloqueia fluxo manual)
7. ✅ **Rastreável** (usuário vê de onde vieram os dados)

---

## ⚠️ ATENÇÕES PARA IMPLEMENTAÇÃO

1. **Sempre mostrar valores em reais (R$)** formatados
2. **Permitir edição** após preencher
3. **Não salvar** sem confirmação do usuário
4. **Destacar campos** preenchidos automaticamente
5. **Dar feedback** visual quando preencher

---

## 🔄 FLUXO COMPLETO

```
Usuario abre /fretes/123/editar
         ↓
Backend busca CTes relacionados
         ↓
    ┌────┴────┐
    │         │
0 CTes    1+ CTes
    │         │
    ↓         ↓
Formulário  Exibe Sugestões
normal      (alerta ou tabela)
    │         │
    └────┬────┘
         ↓
Usuario escolhe:
  - Usar CTe → Preenche campos
  - Ignorar → Preenche manual
         ↓
Usuario REVISA valores
         ↓
Usuario clica SALVAR
         ↓
Validações normais
         ↓
Salva no banco
```

---

**FIM DA PROPOSTA**
