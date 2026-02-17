"""
Rotas para gerenciamento do De-Para de produtos do Atacadão
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('portal_depara', __name__, url_prefix='/atacadao/depara')

@bp.route('/')
@login_required
def index():
    """Página inicial do De-Para Atacadão"""
    return render_template('portal/atacadao/depara/index.html')

@bp.route('/listar')
@login_required
def listar():
    """Lista todos os mapeamentos De-Para"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = ProdutoDeParaAtacadao.query
    
    if search:
        query = query.filter(
            db.or_(
                ProdutoDeParaAtacadao.codigo_nosso.contains(search),
                ProdutoDeParaAtacadao.descricao_nosso.contains(search),
                ProdutoDeParaAtacadao.codigo_atacadao.contains(search),
                ProdutoDeParaAtacadao.descricao_atacadao.contains(search)
            )
        )
    
    query = query.order_by(ProdutoDeParaAtacadao.codigo_nosso)
    
    mapeamentos = query.paginate(page=page, per_page=50, error_out=False)
    
    return render_template('portal/atacadao/depara/listar.html',
                         mapeamentos=mapeamentos,
                         search=search)

@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo mapeamento De-Para"""
    if request.method == 'POST':
        try:
            # Buscar descrição do nosso produto
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            descricao_nosso = ''
            
            # Buscar em CadastroPalletizacao
            produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
            if produto:
                descricao_nosso = produto.nome_produto
            
            mapeamento = ProdutoDeParaAtacadao(
                codigo_nosso=codigo_nosso,
                descricao_nosso=descricao_nosso or request.form.get('descricao_nosso', ''),
                codigo_atacadao=request.form.get('codigo_atacadao', '').strip(),
                descricao_atacadao=request.form.get('descricao_atacadao', '').strip(),
                cnpj_cliente=request.form.get('cnpj_cliente', '').strip(),
                fator_conversao=float(request.form.get('fator_conversao', 1.0)),
                observacoes=request.form.get('observacoes', ''),
                ativo=request.form.get('ativo') == 'on',
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            
            db.session.add(mapeamento)
            db.session.commit()
            
            flash('Mapeamento criado com sucesso!', 'success')
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar mapeamento: {e}")
            flash(f'Erro ao criar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/atacadao/depara/form.html',
                         mapeamento=None,
                         action='novo')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar mapeamento existente"""
    mapeamento = ProdutoDeParaAtacadao.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Buscar descrição atualizada se mudou código
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            if codigo_nosso != mapeamento.codigo_nosso:
                produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
                if produto:
                    mapeamento.descricao_nosso = produto.nome_produto
            
            mapeamento.codigo_nosso = codigo_nosso
            mapeamento.codigo_atacadao = request.form.get('codigo_atacadao', '').strip()
            mapeamento.descricao_atacadao = request.form.get('descricao_atacadao', '').strip()
            mapeamento.cnpj_cliente = request.form.get('cnpj_cliente', '').strip()
            mapeamento.fator_conversao = float(request.form.get('fator_conversao', 1.0))
            mapeamento.observacoes = request.form.get('observacoes', '')
            mapeamento.ativo = request.form.get('ativo') == 'on'
            mapeamento.atualizado_em = agora_utc_naive()
            
            db.session.commit()
            
            flash('Mapeamento atualizado com sucesso!', 'success')
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar mapeamento: {e}")
            flash(f'Erro ao atualizar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/atacadao/depara/form.html',
                         mapeamento=mapeamento,
                         action='editar')

@bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    """Excluir mapeamento"""
    try:
        mapeamento = ProdutoDeParaAtacadao.query.get_or_404(id)
        db.session.delete(mapeamento)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapeamento excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir mapeamento: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    """Importar mapeamentos via planilha Excel/CSV"""
    if request.method == 'POST':
        try:
            if 'arquivo' not in request.files:
                flash('Nenhum arquivo selecionado', 'warning')
                return redirect(request.url)
            
            arquivo = request.files['arquivo']
            
            if arquivo.filename == '':
                flash('Nenhum arquivo selecionado', 'warning')
                return redirect(request.url)
            
            # Salvar arquivo temporário
            filename = secure_filename(arquivo.filename)
            temp_path = os.path.join('/tmp', filename)
            arquivo.save(temp_path)
            
            # Ler planilha com detecção automática de encoding
            if filename.endswith('.csv'):
                # Tentar diferentes encodings para CSV
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(temp_path, encoding=encoding)
                        logger.info(f"CSV lido com sucesso usando encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f"Erro ao tentar encoding {encoding}: {e}")
                        continue
                
                if df is None:
                    # Se nenhum encoding funcionou, tentar com errors='ignore'
                    try:
                        df = pd.read_csv(temp_path, encoding='latin-1', errors='ignore')
                        logger.warning("CSV lido com encoding latin-1 e errors='ignore'")
                        flash('⚠️ Arquivo com caracteres especiais. Alguns podem ter sido ignorados.', 'warning')
                    except Exception as e:
                        flash(f'Erro ao ler arquivo CSV: {str(e)}', 'danger')
                        os.remove(temp_path)
                        return redirect(request.url)
            else:
                # Ler Excel com tratamento de erros
                try:
                    # Primeiro tentar com engine padrão
                    df = pd.read_excel(temp_path)
                    logger.info("Excel lido com sucesso usando engine padrão")
                except Exception as e:
                    logger.warning(f"Erro ao ler Excel com engine padrão: {e}")
                    try:
                        # Tentar com openpyxl explicitamente
                        df = pd.read_excel(temp_path, engine='openpyxl')
                        logger.info("Excel lido com sucesso usando openpyxl")
                    except Exception as e2:
                        logger.warning(f"Erro ao ler Excel com openpyxl: {e2}")
                        try:
                            # Última tentativa: pode ser um CSV com extensão errada
                            logger.warning("Tentando ler como CSV (pode ser extensão errada)")
                            # Aplicar mesma lógica de encoding do CSV
                            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                            df = None
                            
                            for encoding in encodings:
                                try:
                                    df = pd.read_csv(temp_path, encoding=encoding)
                                    logger.warning(f"Arquivo com extensão Excel mas é CSV! Lido com {encoding}")
                                    flash('⚠️ Arquivo parece ser CSV com extensão Excel. Processado com sucesso.', 'warning')
                                    break
                                except Exception as e:
                                    continue
                            
                            if df is None:
                                df = pd.read_csv(temp_path, encoding='latin-1', errors='ignore')
                                logger.warning("CSV (com extensão Excel) lido com latin-1 + ignore")
                                
                        except Exception as e3:
                            flash(f'Erro ao ler arquivo: {str(e3)}', 'danger')
                            os.remove(temp_path)
                            return redirect(request.url)
            
            # Normalizar nomes das colunas (lowercase)
            df.columns = [col.lower().strip() for col in df.columns]

            # Validar colunas obrigatórias
            colunas_obrigatorias = ['cod atacadao', 'nosso cod']
            colunas_existentes = list(df.columns)

            for col in colunas_obrigatorias:
                if col not in colunas_existentes:
                    flash(f'Coluna obrigatória não encontrada: {col}', 'danger')
                    return redirect(request.url)

            # Processar linhas
            contador_criados = 0
            contador_atualizados = 0
            contador_erro = 0
            erros = []

            for index, row in df.iterrows():
                try:
                    codigo_nosso = str(row['nosso cod']).strip()
                    codigo_atacadao = str(row['cod atacadao']).strip()

                    # Pular linhas vazias
                    if not codigo_nosso or not codigo_atacadao or codigo_nosso == 'nan' or codigo_atacadao == 'nan':
                        continue

                    # Descrição do Atacadão (opcional)
                    descricao_atacadao = ''
                    if 'descricao atacadao' in df.columns:
                        descricao_atacadao = str(row.get('descricao atacadao', '') or '').strip()
                        if descricao_atacadao == 'nan':
                            descricao_atacadao = ''

                    # Fator de conversão (opcional)
                    fator_conversao = 1.0
                    if 'fator conversao' in df.columns:
                        try:
                            fator_val = row.get('fator conversao', 1.0)
                            if pd.notna(fator_val):
                                fator_conversao = float(fator_val)
                        except (ValueError, TypeError):
                            fator_conversao = 1.0

                    # CNPJ cliente (opcional)
                    cnpj_cliente = None
                    if 'cnpj cliente' in df.columns:
                        cnpj_val = str(row.get('cnpj cliente', '') or '').strip()
                        if cnpj_val and cnpj_val != 'nan':
                            cnpj_cliente = cnpj_val

                    # Observações (opcional)
                    observacoes = ''
                    if 'observacoes' in df.columns:
                        obs_val = str(row.get('observacoes', '') or '').strip()
                        if obs_val != 'nan':
                            observacoes = obs_val

                    # Verificar se já existe (considera CNPJ se informado)
                    query = ProdutoDeParaAtacadao.query.filter_by(
                        codigo_nosso=codigo_nosso,
                        codigo_atacadao=codigo_atacadao
                    )
                    if cnpj_cliente:
                        query = query.filter_by(cnpj_cliente=cnpj_cliente)
                    else:
                        query = query.filter(ProdutoDeParaAtacadao.cnpj_cliente.is_(None))

                    existe = query.first()

                    if existe:
                        # Atualizar existente - atualiza descrição e outros campos
                        if descricao_atacadao:
                            existe.descricao_atacadao = descricao_atacadao
                        if fator_conversao != 1.0:
                            existe.fator_conversao = fator_conversao
                        if observacoes:
                            existe.observacoes = observacoes
                        existe.atualizado_em = agora_utc_naive()
                        contador_atualizados += 1
                    else:
                        # Buscar descrição do nosso produto
                        descricao_nosso = ''
                        produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
                        if produto:
                            descricao_nosso = produto.nome_produto

                        # Criar novo
                        mapeamento = ProdutoDeParaAtacadao(
                            codigo_nosso=codigo_nosso,
                            descricao_nosso=descricao_nosso,
                            codigo_atacadao=codigo_atacadao,
                            descricao_atacadao=descricao_atacadao,
                            cnpj_cliente=cnpj_cliente,
                            fator_conversao=fator_conversao,
                            observacoes=observacoes,
                            ativo=True,
                            criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        )
                        db.session.add(mapeamento)
                        contador_criados += 1

                except Exception as e:
                    contador_erro += 1
                    erros.append(f"Linha {index + 2}: {str(e)}")  # type: ignore
                    if contador_erro > 10:  # Limitar erros mostrados
                        break
            
            # Commit se tudo ok
            total_processados = contador_criados + contador_atualizados
            if total_processados > 0:
                db.session.commit()
                msg = f'✅ Importação concluída: {contador_criados} criados, {contador_atualizados} atualizados'
                flash(msg, 'success')

            if contador_erro > 0:
                flash(f'⚠️ {contador_erro} linhas com erro', 'warning')
                for erro in erros[:5]:  # Mostrar até 5 erros
                    flash(erro, 'danger')
            
            # Remover arquivo temporário
            os.remove(temp_path)
            
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar planilha: {e}")
            flash(f'Erro ao importar planilha: {str(e)}', 'danger')
            
            # Remover arquivo temporário se existir
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
    
    return render_template('portal/atacadao/depara/importar.html')

@bp.route('/buscar_produto_nosso/<codigo>')
@login_required
def buscar_produto_nosso(codigo):
    """API para buscar descrição do nosso produto"""
    try:
        produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo).first()
        
        if produto:
            return jsonify({
                'success': True,
                'descricao': produto.nome_produto
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao buscar produto: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/converter_codigo/<codigo_nosso>')
@login_required
def converter_codigo(codigo_nosso):
    """API para converter código nosso para código Atacadão"""
    try:
        mapeamento = ProdutoDeParaAtacadao.query.filter_by(
            codigo_nosso=codigo_nosso,
            ativo=True
        ).first()
        
        if mapeamento:
            return jsonify({
                'success': True,
                'codigo_atacadao': mapeamento.codigo_atacadao,
                'descricao_atacadao': mapeamento.descricao_atacadao,
                'fator_conversao': float(mapeamento.fator_conversao)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Mapeamento não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao converter código: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/criar', methods=['POST'])
@login_required
def api_criar():
    """API para criar mapeamento De-Para via AJAX"""
    try:
        data = request.get_json()

        # Validar dados obrigatórios
        if not data.get('codigo_nosso') or not data.get('codigo_atacadao'):
            return jsonify({
                'success': False,
                'message': 'Códigos são obrigatórios'
            }), 400

        # Verificar se já existe
        existe = ProdutoDeParaAtacadao.query.filter_by(
            codigo_nosso=data['codigo_nosso'],
            codigo_atacadao=data['codigo_atacadao']
        ).first()

        if existe:
            return jsonify({
                'success': False,
                'message': 'Mapeamento já existe'
            }), 400

        # Buscar descrição do nosso produto
        descricao_nosso = ''
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=data['codigo_nosso']
        ).first()
        if produto:
            descricao_nosso = produto.nome_produto

        # Criar novo mapeamento
        mapeamento = ProdutoDeParaAtacadao(
            codigo_nosso=data['codigo_nosso'],
            descricao_nosso=descricao_nosso,
            codigo_atacadao=data['codigo_atacadao'],
            descricao_atacadao=data.get('descricao_atacadao', ''),
            fator_conversao=float(data.get('fator_conversao', 1.0)),
            ativo=True,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        )

        db.session.add(mapeamento)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Mapeamento criado com sucesso',
            'id': mapeamento.id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar mapeamento via API: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/exportar')
@login_required
def exportar():
    """Exportar todos os mapeamentos De-Para em xlsx"""
    from io import BytesIO
    from flask import send_file

    try:
        # Buscar todos os mapeamentos ativos
        mapeamentos = ProdutoDeParaAtacadao.query.filter_by(ativo=True).order_by(
            ProdutoDeParaAtacadao.codigo_nosso
        ).all()

        # Criar DataFrame
        dados = []
        for m in mapeamentos:
            dados.append({
                'cod atacadao': m.codigo_atacadao,
                'descricao atacadao': m.descricao_atacadao or '',
                'nosso cod': m.codigo_nosso,
                'descricao nosso': m.descricao_nosso or '',
                'fator conversao': float(m.fator_conversao) if m.fator_conversao else 1.0,
                'cnpj cliente': m.cnpj_cliente or '',
                'observacoes': m.observacoes or ''
            })

        df = pd.DataFrame(dados)

        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='De-Para Atacadao', index=False)

            # Ajustar largura das colunas
            worksheet = writer.sheets['De-Para Atacadao']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].fillna('').astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

        output.seek(0)

        # Nome do arquivo com data
        from datetime import datetime
        filename = f"depara_atacadao_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Erro ao exportar De-Para: {e}")
        flash(f'Erro ao exportar: {str(e)}', 'danger')
        return redirect(url_for('portal.portal_depara.index'))


@bp.route('/modelo')
@login_required
def baixar_modelo():
    """Baixar modelo de planilha xlsx para importação"""
    from io import BytesIO
    from flask import send_file

    try:
        # Criar DataFrame com colunas do modelo
        dados_exemplo = [
            {
                'cod atacadao': '82545',
                'descricao atacadao': 'AZEITONA VERDE CAMPO BELO FAT.POUCH 30x80G',
                'nosso cod': '4310146',
                'descricao nosso': '',  # Será preenchido automaticamente se existir no cadastro
                'fator conversao': 1.0,
                'cnpj cliente': '',  # Opcional - para mapeamento específico por cliente
                'observacoes': ''
            },
            {
                'cod atacadao': '46624',
                'descricao atacadao': 'AZEITONA VERDE CAMPO BELO POUCH 18x180G',
                'nosso cod': '4310152',
                'descricao nosso': '',
                'fator conversao': 1.0,
                'cnpj cliente': '',
                'observacoes': ''
            }
        ]

        df = pd.DataFrame(dados_exemplo)

        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='De-Para Atacadao', index=False)

            # Ajustar largura das colunas
            worksheet = writer.sheets['De-Para Atacadao']
            larguras = {
                'A': 15,  # cod atacadao
                'B': 50,  # descricao atacadao
                'C': 15,  # nosso cod
                'D': 50,  # descricao nosso
                'E': 15,  # fator conversao
                'F': 20,  # cnpj cliente
                'G': 30   # observacoes
            }
            for col, width in larguras.items():
                worksheet.column_dimensions[col].width = width

            # Adicionar comentários/instruções
            from openpyxl.comments import Comment
            worksheet['A1'].comment = Comment(
                'Código do produto no Atacadão (sem zeros à esquerda)',
                'Sistema'
            )
            worksheet['B1'].comment = Comment(
                'Descrição do produto no Atacadão (até 255 caracteres)',
                'Sistema'
            )
            worksheet['C1'].comment = Comment(
                'Nosso código interno do produto',
                'Sistema'
            )
            worksheet['D1'].comment = Comment(
                'Deixe em branco - será preenchido automaticamente',
                'Sistema'
            )
            worksheet['E1'].comment = Comment(
                'Fator de conversão (padrão 1.0)',
                'Sistema'
            )
            worksheet['F1'].comment = Comment(
                'CNPJ do cliente (opcional, para mapeamento específico)',
                'Sistema'
            )

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_depara_atacadao.xlsx'
        )

    except Exception as e:
        logger.error(f"Erro ao gerar modelo: {e}")
        flash(f'Erro ao gerar modelo: {str(e)}', 'danger')
        return redirect(url_for('portal.portal_depara.index'))