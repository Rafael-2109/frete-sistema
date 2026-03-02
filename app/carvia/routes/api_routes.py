"""
API Routes CarVia — Endpoints AJAX (cotacao, busca, cubagem)
"""

import logging
from flask import jsonify, request
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_api_routes(bp):

    @bp.route('/api/calcular-cubagem', methods=['POST'])
    @login_required
    def api_calcular_cubagem():
        """Calcula peso cubado a partir das dimensoes"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        try:
            comprimento = float(data.get('comprimento', 0))
            largura = float(data.get('largura', 0))
            altura = float(data.get('altura', 0))
            fator = float(data.get('fator', 5000))
            volumes = int(data.get('volumes', 1))

            if fator <= 0:
                return jsonify({'erro': 'Fator divisor deve ser maior que zero'}), 400

            peso_cubado = (comprimento * largura * altura / fator) * volumes

            return jsonify({
                'sucesso': True,
                'peso_cubado': round(peso_cubado, 3),
                'formula': f'({comprimento} x {largura} x {altura} / {fator}) x {volumes}',
            })
        except (ValueError, TypeError) as e:
            return jsonify({'erro': f'Valores invalidos: {e}'}), 400

    @bp.route('/api/calcular-cotacao', methods=['POST'])
    @login_required
    def api_calcular_cotacao():
        """Calcula cotacao de frete para um subcontrato"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        operacao_id = data.get('operacao_id')
        transportadora_id = data.get('transportadora_id')

        if not operacao_id or not transportadora_id:
            return jsonify({'erro': 'operacao_id e transportadora_id sao obrigatorios'}), 400

        try:
            from app.carvia.services.cotacao_service import CotacaoService
            service = CotacaoService()
            resultado = service.cotar_subcontrato(
                operacao_id=int(operacao_id),
                transportadora_id=int(transportadora_id),
            )
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro na cotacao: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/opcoes-transportadora')
    @login_required
    def api_opcoes_transportadora():
        """Lista transportadoras disponiveis para subcontratacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        busca = request.args.get('busca', '')
        uf_destino = request.args.get('uf_destino', '')
        apenas_freteiros = request.args.get('freteiro', '') == '1'

        try:
            from app.transportadoras.models import Transportadora
            query = db.session.query(Transportadora).filter(
                Transportadora.ativo == True  # noqa: E712
            )

            if apenas_freteiros:
                query = query.filter(Transportadora.freteiro == True)  # noqa: E712

            if busca:
                busca_like = f'%{busca}%'
                query = query.filter(
                    db.or_(
                        Transportadora.razao_social.ilike(busca_like),
                        Transportadora.cnpj.ilike(busca_like),
                    )
                )

            # Se informou UF destino, indicar quais tem tabela ativa
            tabelas_info = {}
            if uf_destino:
                from app.tabelas.models import TabelaFrete
                tabelas = db.session.query(
                    TabelaFrete.transportadora_id,
                    db.func.count(TabelaFrete.id).label('qtd_tabelas'),
                ).filter(
                    TabelaFrete.uf_destino == uf_destino,
                    TabelaFrete.ativo == True,  # noqa: E712
                ).group_by(TabelaFrete.transportadora_id).all()

                tabelas_info = {t.transportadora_id: t.qtd_tabelas for t in tabelas}

            query = query.order_by(Transportadora.razao_social).limit(50)
            transportadoras = query.all()

            resultado = [{
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
                'freteiro': t.freteiro,
                'tem_tabela': t.id in tabelas_info,
                'qtd_tabelas': tabelas_info.get(t.id, 0),
            } for t in transportadoras]

            return jsonify({'sucesso': True, 'transportadoras': resultado})

        except Exception as e:
            logger.error(f"Erro ao buscar transportadoras: {e}")
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # Download de arquivos originais (S3 / local)
    # ------------------------------------------------------------------

    @bp.route('/api/nf/<int:nf_id>/arquivo/<tipo>')
    @login_required
    def api_download_nf_arquivo(nf_id, tipo):
        """Gera URL presigned para download do XML ou PDF original de uma NF."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        if tipo not in ('xml', 'pdf'):
            return jsonify({'erro': 'Tipo deve ser "xml" ou "pdf"'}), 400

        from app.carvia.models import CarviaNf
        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada'}), 404

        path = nf.arquivo_xml_path if tipo == 'xml' else nf.arquivo_pdf_path
        if not path:
            return jsonify({
                'sucesso': False,
                'mensagem': f'Arquivo {tipo.upper()} nao disponivel no storage',
            }), 404

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_file_url(path)
            if not url:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Erro ao gerar URL do arquivo',
                }), 500
            return jsonify({
                'sucesso': True,
                'url': url,
                'arquivo': nf.arquivo_nome_original or f'nf_{nf.numero_nf}.{tipo}',
            })
        except Exception as e:
            logger.error(f"Erro ao gerar URL para NF {nf_id} ({tipo}): {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/operacao/<int:operacao_id>/xml')
    @login_required
    def api_download_operacao_xml(operacao_id):
        """Gera URL presigned para download do CTe XML original de uma operacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaOperacao
        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return jsonify({'erro': 'Operacao nao encontrada'}), 404

        if not operacao.cte_xml_path:
            return jsonify({
                'sucesso': False,
                'mensagem': 'CTe XML nao disponivel no storage',
            }), 404

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_file_url(operacao.cte_xml_path)
            if not url:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Erro ao gerar URL do arquivo',
                }), 500
            return jsonify({
                'sucesso': True,
                'url': url,
                'arquivo': operacao.cte_xml_nome_arquivo or f'cte_{operacao.cte_numero}.xml',
            })
        except Exception as e:
            logger.error(f"Erro ao gerar URL para operacao {operacao_id} XML: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fatura-cliente/<int:fatura_id>/pdf')
    @login_required
    def api_download_fatura_cliente_pdf(fatura_id):
        """Gera URL presigned para download do PDF original de uma fatura cliente."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaFaturaCliente
        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'erro': 'Fatura nao encontrada'}), 404

        if not fatura.arquivo_pdf_path:
            return jsonify({
                'sucesso': False,
                'mensagem': 'PDF nao disponivel no storage',
            }), 404

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_file_url(fatura.arquivo_pdf_path)
            if not url:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Erro ao gerar URL do arquivo',
                }), 500
            return jsonify({
                'sucesso': True,
                'url': url,
                'arquivo': fatura.arquivo_nome_original or f'fatura_{fatura.numero_fatura}.pdf',
            })
        except Exception as e:
            logger.error(f"Erro ao gerar URL para fatura cliente {fatura_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fatura-transportadora/<int:fatura_id>/pdf')
    @login_required
    def api_download_fatura_transportadora_pdf(fatura_id):
        """Gera URL presigned para download do PDF original de uma fatura transportadora."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaFaturaTransportadora
        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'erro': 'Fatura nao encontrada'}), 404

        if not fatura.arquivo_pdf_path:
            return jsonify({
                'sucesso': False,
                'mensagem': 'PDF nao disponivel no storage',
            }), 404

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_file_url(fatura.arquivo_pdf_path)
            if not url:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Erro ao gerar URL do arquivo',
                }), 500
            return jsonify({
                'sucesso': True,
                'url': url,
                'arquivo': fatura.arquivo_nome_original or f'fatura_{fatura.numero_fatura}.pdf',
            })
        except Exception as e:
            logger.error(f"Erro ao gerar URL para fatura transportadora {fatura_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/atualizar-cubagem', methods=['POST'])
    @login_required
    def api_atualizar_cubagem():
        """Atualiza cubagem de uma operacao e recalcula peso_utilizado"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        operacao_id = data.get('operacao_id')
        if not operacao_id:
            return jsonify({'erro': 'operacao_id obrigatorio'}), 400

        try:
            from app.carvia.models import CarviaOperacao
            operacao = db.session.get(CarviaOperacao, int(operacao_id))
            if not operacao:
                return jsonify({'erro': 'Operacao nao encontrada'}), 404

            # Peso cubado direto OU por dimensoes
            peso_cubado_direto = data.get('peso_cubado')
            if peso_cubado_direto:
                operacao.peso_cubado = float(peso_cubado_direto)
            else:
                # Calcular por dimensoes
                comp = data.get('cubagem_comprimento')
                larg = data.get('cubagem_largura')
                alt = data.get('cubagem_altura')
                fator = data.get('cubagem_fator', 5000)
                volumes = data.get('cubagem_volumes', 1)

                if comp and larg and alt:
                    operacao.cubagem_comprimento = float(comp)
                    operacao.cubagem_largura = float(larg)
                    operacao.cubagem_altura = float(alt)
                    operacao.cubagem_fator = float(fator)
                    operacao.cubagem_volumes = int(volumes)
                    operacao.calcular_cubagem()

            # Recalcular peso utilizado
            operacao.calcular_peso_utilizado()
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'peso_cubado': float(operacao.peso_cubado) if operacao.peso_cubado else None,
                'peso_utilizado': float(operacao.peso_utilizado) if operacao.peso_utilizado else None,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar cubagem: {e}")
            return jsonify({'erro': str(e)}), 500
