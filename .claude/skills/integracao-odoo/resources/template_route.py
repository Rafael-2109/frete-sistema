"""
TEMPLATE: Routes para Lançamento no Odoo
=========================================

Copie este template e adapte para sua entidade.
Substitua 'xxx' pelo nome da sua entidade (ex: frete, despesa, etc.)

Arquivos de referência:
- app/fretes/routes.py - lancar_despesa_odoo()
"""

from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime


# =================== LANÇAMENTO NO ODOO ===================

@seu_blueprint.route('/xxx/<int:xxx_id>/lancar_odoo', methods=['POST'])
@login_required
def lancar_xxx_odoo(xxx_id):
    """
    Lança registro no Odoo via API.
    Requer CTe vinculado e status permitido.
    """
    from app.xxx.services.lancamento_xxx_odoo_service import LancamentoXxxOdooService
    from app.xxx.models import Xxx

    xxx = db.session.get(Xxx,xxx_id) if xxx_id else None

    # ================================================
    # VALIDAÇÕES
    # ================================================

    # Validar tipo de documento (se aplicável)
    # if xxx.tipo_documento != 'CTe':
    #     return jsonify({
    #         'sucesso': False,
    #         'mensagem': 'Tipo de documento não suportado',
    #         'erro': 'Apenas documentos CTe podem ser lançados no Odoo'
    #     }), 400

    # Validar CTe vinculado
    if not xxx.cte_id:  # Ajustar nome do campo
        return jsonify({
            'sucesso': False,
            'mensagem': 'CTe não vinculado',
            'erro': 'Vincule um CTe antes de lançar no Odoo'
        }), 400

    # Validar se já foi lançado
    if xxx.status == 'LANCADO_ODOO':
        return jsonify({
            'sucesso': False,
            'mensagem': 'Registro já foi lançado no Odoo',
            'erro': f'Invoice ID: {xxx.odoo_invoice_id}'
        }), 400

    # Validar status permitido
    if xxx.status not in ['STATUS_PERMITIDO']:  # Ajustar status válidos
        return jsonify({
            'sucesso': False,
            'mensagem': f'Status "{xxx.status}" não permite lançamento',
            'erro': 'Status não permitido'
        }), 400

    # ================================================
    # OBTER DATA DE VENCIMENTO
    # ================================================
    data = request.get_json() or {}
    data_vencimento_str = data.get('data_vencimento')

    data_vencimento = None
    if data_vencimento_str:
        try:
            data_vencimento = datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Data de vencimento inválida',
                'erro': 'Formato esperado: YYYY-MM-DD'
            }), 400

    # ================================================
    # EXECUTAR LANÇAMENTO
    # ================================================
    try:
        service = LancamentoXxxOdooService(
            usuario_nome=current_user.nome,
            usuario_ip=request.remote_addr
        )

        resultado = service.lancar_xxx_odoo(
            xxx_id=xxx_id,
            data_vencimento=data_vencimento
        )

        return jsonify(resultado)

    except Exception as e:
        current_app.logger.error(f"Erro ao lançar no Odoo: {str(e)}")
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro interno: {str(e)}',
            'erro': str(e)
        }), 500


# =================== AUDITORIA ===================

@seu_blueprint.route('/xxx/<int:xxx_id>/auditoria_odoo')
@login_required
def auditoria_xxx_odoo(xxx_id):
    """Exibe auditoria de lançamento Odoo."""
    from app.fretes.models import LancamentoFreteOdooAuditoria
    from app.xxx.models import Xxx

    xxx = db.session.get(Xxx,xxx_id) if xxx_id else None

    # Ajustar filtro conforme campo na auditoria
    auditorias = LancamentoFreteOdooAuditoria.query.filter_by(
        # xxx_id=xxx_id  # ou outro campo
    ).order_by(
        LancamentoFreteOdooAuditoria.etapa
    ).all()

    return render_template(
        'xxx/auditoria_odoo.html',
        xxx=xxx,
        auditorias=auditorias
    )


# =================== TEMPLATE JAVASCRIPT ===================
"""
Adicione este JavaScript no template HTML:

<script>
function lancarXxxOdoo(xxxId, vencimento) {
    const dataVencimento = document.getElementById('dataVencimentoOdoo').value;
    const btnLancar = document.getElementById('btnLancarOdoo');
    const progressBar = document.querySelector('.progress-bar');

    if (!dataVencimento) {
        alert('Informe a data de vencimento');
        return;
    }

    btnLancar.disabled = true;
    btnLancar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Lançando...';

    fetch(`/xxx/${xxxId}/lancar_odoo`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrf_token]').value
        },
        body: JSON.stringify({ data_vencimento: dataVencimento })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            const etapas = data.etapas_concluidas || 0;
            progressBar.style.width = Math.round((etapas / 16) * 100) + '%';
            progressBar.classList.add('bg-success');
            alert('Lançamento concluído!');
            setTimeout(() => location.reload(), 2000);
        } else {
            progressBar.classList.add('bg-danger');
            alert('Erro: ' + data.mensagem);
            btnLancar.disabled = false;
            btnLancar.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Lançar no Odoo';
        }
    })
    .catch(error => {
        console.error(error);
        alert('Erro na comunicação');
        btnLancar.disabled = false;
    });
}
</script>
"""
