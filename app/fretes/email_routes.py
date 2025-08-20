"""
Rotas para gerenciamento de emails anexados às despesas
"""
from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.fretes.models import DespesaExtra
from app.fretes.email_models import EmailAnexado
from app.utils.email_handler import EmailHandler

emails_bp = Blueprint('emails', __name__, url_prefix='/fretes/emails')


@emails_bp.route('/<int:email_id>')
@login_required
def visualizar_email(email_id):
    """Visualiza detalhes de um email anexado"""
    email = EmailAnexado.query.get_or_404(email_id)
    despesa = email.despesa_extra
    
    # Busca outros emails da mesma despesa
    outros_emails = EmailAnexado.query.filter(
        EmailAnexado.despesa_extra_id == despesa.id,
        EmailAnexado.id != email_id
    ).all()
    
    return render_template('fretes/visualizar_email.html',
                         email=email,
                         despesa=despesa,
                         outros_emails=outros_emails)


@emails_bp.route('/<int:email_id>/download')
@login_required
def download_email(email_id):
    """Faz download do arquivo .msg original"""
    email = EmailAnexado.query.get_or_404(email_id)
    
    try:
        email_handler = EmailHandler()
        # Obter URL do arquivo
        url = email_handler.get_email_url(email.caminho_s3)
        
        if url:
            # Para S3, redireciona para URL assinada
            # Para local, url_for já retorna o caminho correto
            if url.startswith('http'):
                # URL do S3 - redireciona diretamente
                return redirect(url)
            else:
                # Arquivo local - serve através do Flask
                import os
                file_path = os.path.join(current_app.root_path, 'static', email.caminho_s3)
                if os.path.exists(file_path):
                    return send_file(
                        file_path,
                        as_attachment=True,
                        download_name=email.nome_arquivo,
                        mimetype='application/vnd.ms-outlook'
                    )
                else:
                    flash('Arquivo não encontrado', 'error')
                    return redirect(url_for('emails.visualizar_email', email_id=email_id))
        else:
            flash('Erro ao baixar o arquivo de email', 'error')
            return redirect(url_for('emails.visualizar_email', email_id=email_id))
            
    except Exception as e:
        current_app.logger.error(f"Erro ao baixar email {email_id}: {str(e)}")
        flash('Erro ao processar download do email', 'error')
        return redirect(url_for('emails.visualizar_email', email_id=email_id))


@emails_bp.route('/<int:email_id>/excluir')
@login_required
def excluir_email(email_id):
    """Exclui um email anexado"""
    email = EmailAnexado.query.get_or_404(email_id)
    frete_id = email.despesa_extra.frete_id
    
    try:
        # Remove do S3 ou storage local usando FileStorage centralizado
        email_handler = EmailHandler()
        email_handler.deletar_email(email.caminho_s3)
        
        # Remove do banco
        db.session.delete(email)
        db.session.commit()
        
        flash('Email excluído com sucesso', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Erro ao excluir email {email_id}: {str(e)}")
        flash('Erro ao excluir email', 'error')
        db.session.rollback()
    
    return redirect(url_for('fretes.visualizar_frete', frete_id=frete_id))


@emails_bp.route('/despesa/<int:despesa_id>')
@login_required
def listar_emails_despesa(despesa_id):
    """Lista todos os emails de uma despesa"""
    despesa = DespesaExtra.query.get_or_404(despesa_id)
    emails = EmailAnexado.query.filter_by(despesa_extra_id=despesa_id).all()
    
    return render_template('fretes/listar_emails_despesa.html',
                         despesa=despesa,
                         emails=emails)


@emails_bp.route('/frete/<int:frete_id>')
@login_required
def listar_emails_frete(frete_id):
    """Lista todos os emails de um frete (de todas as despesas)"""
    from app.fretes.models import Frete
    
    frete = Frete.query.get_or_404(frete_id)
    
    # Buscar todos os emails das despesas deste frete
    emails = EmailAnexado.query.join(DespesaExtra).filter(
        DespesaExtra.frete_id == frete_id
    ).order_by(EmailAnexado.criado_em.desc()).all()
    
    # Agrupar emails por despesa para melhor visualização
    emails_por_despesa = {}
    for email in emails:
        despesa_id = email.despesa_extra_id
        if despesa_id not in emails_por_despesa:
            emails_por_despesa[despesa_id] = {
                'despesa': email.despesa_extra,
                'emails': []
            }
        emails_por_despesa[despesa_id]['emails'].append(email)
    
    return render_template('fretes/listar_emails_frete.html',
                         frete=frete,
                         emails=emails,
                         emails_por_despesa=emails_por_despesa)