"""
API Routes CarVia — Endpoints AJAX (cotacao, busca, cubagem)
"""

import logging
import re
from flask import jsonify, request, redirect
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_api_routes(bp):

    @bp.route('/api/cadastrar-transportadora', methods=['POST'])
    @login_required
    def api_cadastrar_transportadora():
        """Cadastro rapido de transportadora durante importacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        cnpj = data.get('cnpj', '').strip()
        razao_social = data.get('razao_social', '').strip()
        cidade = data.get('cidade', '').strip()
        uf = data.get('uf', '').strip().upper()

        if not all([cnpj, razao_social, cidade, uf]):
            return jsonify({'erro': 'cnpj, razao_social, cidade e uf sao obrigatorios'}), 400
        if len(uf) != 2:
            return jsonify({'erro': 'UF deve ter 2 caracteres'}), 400

        try:
            from app.transportadoras.models import Transportadora

            # Verificar duplicidade
            cnpj_digits = re.sub(r'\D', '', cnpj)
            existente = Transportadora.query.filter(
                db.func.regexp_replace(Transportadora.cnpj, '[^0-9]', '', 'g')
                == cnpj_digits
            ).first()
            if existente:
                return jsonify({
                    'sucesso': True,
                    'transportadora': {
                        'id': existente.id,
                        'razao_social': existente.razao_social,
                        'cnpj': existente.cnpj,
                    },
                    'mensagem': 'Transportadora ja cadastrada',
                })

            # Formatar CNPJ: XX.XXX.XXX/XXXX-XX
            if len(cnpj_digits) == 14:
                cnpj_fmt = (
                    f'{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}'
                    f'/{cnpj_digits[8:12]}-{cnpj_digits[12:]}'
                )
            else:
                cnpj_fmt = cnpj

            freteiro = data.get('freteiro', False)
            transp = Transportadora(
                cnpj=cnpj_fmt,
                razao_social=razao_social,
                cidade=cidade,
                uf=uf,
                freteiro=bool(freteiro),
                ativo=True,
            )
            db.session.add(transp)
            db.session.commit()

            logger.info(
                f"Transportadora cadastrada via importacao: {razao_social} "
                f"({cnpj_fmt}) por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'transportadora': {
                    'id': transp.id,
                    'razao_social': transp.razao_social,
                    'cnpj': transp.cnpj,
                },
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cadastrar transportadora: {e}")
            return jsonify({'erro': str(e)}), 500

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

    @bp.route('/api/cotar-standalone', methods=['POST'])
    @login_required
    def api_cotar_standalone():
        """Cota todas opcoes de frete standalone (NF ou CTe).

        Aceita parametro opcional 'categorias_moto' para cotacao por
        categoria de moto (preco por unidade). Exemplo:
          {"categorias_moto": [{"categoria_id": 1, "quantidade": 3}]}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        categorias_moto = data.get('categorias_moto')

        try:
            peso = float(data.get('peso', 0))
            valor = float(data.get('valor_mercadoria', 0))
        except (ValueError, TypeError):
            return jsonify({'erro': 'Peso e valor devem ser numericos'}), 400

        uf_destino = (data.get('uf_destino') or '').strip().upper()
        cidade_destino = (data.get('cidade_destino') or '').strip() or None
        uf_origem = (data.get('uf_origem') or '').strip().upper() or None
        cnpj_cliente = (data.get('cnpj_cliente') or '').strip() or None

        # Peso obrigatorio apenas se nao ha categorias_moto
        if not categorias_moto and peso <= 0:
            return jsonify({'erro': 'Peso deve ser maior que zero'}), 400
        if not uf_destino:
            return jsonify({'erro': 'UF destino e obrigatoria'}), 400

        try:
            # Se tem categorias_moto, usar CarviaTabelaService diretamente
            if categorias_moto:
                from app.carvia.services.carvia_tabela_service import CarviaTabelaService
                svc = CarviaTabelaService()
                opcoes = svc.cotar_carvia(
                    peso=peso,
                    valor_mercadoria=valor,
                    uf_origem=uf_origem or 'SP',
                    uf_destino=uf_destino,
                    cidade_destino=cidade_destino,
                    cnpj_cliente=cnpj_cliente,
                    categorias_moto=categorias_moto,
                )
                return jsonify({'sucesso': True, 'opcoes': opcoes})

            from app.carvia.services.cotacao_service import CotacaoService
            service = CotacaoService()
            opcoes = service.cotar_todas_opcoes(
                peso, valor, uf_destino, cidade_destino, uf_origem
            )
            return jsonify({'sucesso': True, 'opcoes': opcoes})
        except Exception as e:
            logger.error(f"Erro na cotacao standalone: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

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

                # Buscar tambem por nome de grupo empresarial
                from app.transportadoras.models import GrupoTransportadora
                grupos_match = db.session.query(GrupoTransportadora.id).filter(
                    GrupoTransportadora.nome.ilike(busca_like),
                    GrupoTransportadora.ativo == True  # noqa: E712
                ).subquery()

                query = query.filter(
                    db.or_(
                        Transportadora.razao_social.ilike(busca_like),
                        Transportadora.cnpj.ilike(busca_like),
                        Transportadora.grupo_transportadora_id.in_(
                            db.session.query(grupos_match.c.id)
                        ),
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

            # Expandir grupos: por grupo_transportadora_id E por prefixo CNPJ (filiais)
            from app.transportadoras.filter_utils import expandir_grupo_autocomplete
            membros_grupo = expandir_grupo_autocomplete(transportadoras)
            if apenas_freteiros:
                membros_grupo = [t for t in membros_grupo if t.freteiro]

            resultado = [{
                'id': t.id,
                'nome': t.razao_social,
                'cnpj': t.cnpj,
                'freteiro': t.freteiro,
                'tem_tabela': t.id in tabelas_info,
                'qtd_tabelas': tabelas_info.get(t.id, 0),
                'grupo': t.grupo.nome if t.grupo_transportadora_id and t.grupo else None,
            } for t in transportadoras]

            # Adicionar membros expandidos (grupo/filiais)
            for t in membros_grupo:
                resultado.append({
                    'id': t.id,
                    'nome': t.razao_social,
                    'cnpj': t.cnpj,
                    'freteiro': t.freteiro,
                    'tem_tabela': t.id in tabelas_info,
                    'qtd_tabelas': tabelas_info.get(t.id, 0),
                    'grupo': t.grupo.nome if t.grupo_transportadora_id and t.grupo else None,
                    'via_grupo': True,
                })

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

    # ------------------------------------------------------------------
    # Wizard "Criar CTe Manual" — APIs de selecao
    # ------------------------------------------------------------------

    @bp.route('/api/clientes-nf')
    @login_required
    def api_clientes_nf():
        """Lista clientes distintos (cnpj_emitente + nome_emitente) com contagem de NFs.

        Emitente = cliente pois em importacao_service cnpj_cliente vem do remetente.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.models import CarviaNf
            from sqlalchemy import func as sqlfunc

            resultados = db.session.query(
                CarviaNf.cnpj_emitente,
                CarviaNf.nome_emitente,
                sqlfunc.count(CarviaNf.id).label('qtd_nfs'),
            ).filter(
                CarviaNf.status != 'CANCELADA',
            ).group_by(
                CarviaNf.cnpj_emitente,
                CarviaNf.nome_emitente,
            ).order_by(
                CarviaNf.nome_emitente,
            ).all()

            clientes = [{
                'cnpj': r.cnpj_emitente,
                'nome': r.nome_emitente or r.cnpj_emitente,
                'qtd_nfs': r.qtd_nfs,
            } for r in resultados]

            return jsonify({'sucesso': True, 'clientes': clientes})

        except Exception as e:
            logger.error(f"Erro ao buscar clientes NF: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/nfs-para-cte')
    @login_required
    def api_nfs_para_cte():
        """Lista NFs de um cliente com flag tem_cte (se aparece em carvia_operacao_nfs).

        Query params:
            cnpj_cliente: CNPJ do emitente (obrigatorio)
            com_cte: '0' = sem CTe (default), '1' = com CTe, '' = todas
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        cnpj_cliente = request.args.get('cnpj_cliente', '').strip()
        if not cnpj_cliente:
            return jsonify({'erro': 'cnpj_cliente obrigatorio'}), 400

        com_cte = request.args.get('com_cte', '0')

        try:
            from app.carvia.models import CarviaNf, CarviaOperacaoNf
            from sqlalchemy import func as sqlfunc

            # Subquery: contagem de CTes por NF
            subq = db.session.query(
                CarviaOperacaoNf.nf_id,
                sqlfunc.count(CarviaOperacaoNf.operacao_id).label('qtd_ctes'),
            ).group_by(CarviaOperacaoNf.nf_id).subquery()

            query = db.session.query(
                CarviaNf, subq.c.qtd_ctes,
            ).outerjoin(
                subq, CarviaNf.id == subq.c.nf_id,
            ).filter(
                CarviaNf.cnpj_emitente == cnpj_cliente,
                CarviaNf.status != 'CANCELADA',
            )

            # Filtro com_cte
            if com_cte == '0':
                query = query.filter(subq.c.qtd_ctes.is_(None))
            elif com_cte == '1':
                query = query.filter(subq.c.qtd_ctes > 0)
            # '' = todas (sem filtro)

            query = query.order_by(
                CarviaNf.data_emissao.desc().nullslast(),
                CarviaNf.numero_nf,
            )

            resultados = query.all()

            nfs = []
            for nf, qtd_ctes in resultados:
                nfs.append({
                    'id': nf.id,
                    'numero_nf': nf.numero_nf,
                    'serie_nf': nf.serie_nf,
                    'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else None,
                    'nome_emitente': nf.nome_emitente,
                    'nome_destinatario': nf.nome_destinatario,
                    'uf_destinatario': nf.uf_destinatario,
                    'cidade_destinatario': nf.cidade_destinatario,
                    'uf_emitente': nf.uf_emitente,
                    'cidade_emitente': nf.cidade_emitente,
                    'valor_total': float(nf.valor_total) if nf.valor_total else 0,
                    'peso_bruto': float(nf.peso_bruto) if nf.peso_bruto else 0,
                    'tem_cte': bool(qtd_ctes and qtd_ctes > 0),
                    'qtd_ctes': qtd_ctes or 0,
                })

            return jsonify({'sucesso': True, 'nfs': nfs})

        except Exception as e:
            logger.error(f"Erro ao buscar NFs para CTe: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/transportadoras-modalidade')
    @login_required
    def api_transportadoras_modalidade():
        """Lista transportadoras ativas com tabelas de frete para o UF, agrupando modalidades.

        Query params:
            uf_destino: UF de destino (obrigatorio)
            busca: texto de busca (opcional)
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        uf_destino = request.args.get('uf_destino', '').strip().upper()
        busca = request.args.get('busca', '').strip()

        if not uf_destino:
            return jsonify({'erro': 'uf_destino obrigatorio'}), 400

        try:
            from app.transportadoras.models import Transportadora
            from app.tabelas.models import TabelaFrete

            # Buscar tabelas ativas para o UF destino
            tabelas_query = db.session.query(TabelaFrete).filter(
                TabelaFrete.uf_destino == uf_destino,
                TabelaFrete.ativo == True,  # noqa: E712
            )

            # Coletar transportadora_ids e modalidades
            tabelas_por_transp = {}
            for t in tabelas_query.all():
                tid = t.transportadora_id
                if tid not in tabelas_por_transp:
                    tabelas_por_transp[tid] = {
                        'modalidades': set(),
                        'qtd_tabelas': 0,
                    }
                tabelas_por_transp[tid]['qtd_tabelas'] += 1
                if t.nome_tabela:
                    tabelas_por_transp[tid]['modalidades'].add(t.nome_tabela)

            if not tabelas_por_transp:
                return jsonify({'sucesso': True, 'transportadoras': []})

            # Buscar transportadoras ativas que tem tabela
            query = db.session.query(Transportadora).filter(
                Transportadora.id.in_(tabelas_por_transp.keys()),
                Transportadora.ativo == True,  # noqa: E712
            )

            if busca:
                busca_like = f'%{busca}%'
                query = query.filter(
                    db.or_(
                        Transportadora.razao_social.ilike(busca_like),
                        Transportadora.cnpj.ilike(busca_like),
                    )
                )

            query = query.order_by(Transportadora.razao_social).limit(50)
            transportadoras = query.all()

            resultado = []
            for t in transportadoras:
                info = tabelas_por_transp.get(t.id, {})
                resultado.append({
                    'id': t.id,
                    'razao_social': t.razao_social,
                    'cnpj': t.cnpj,
                    'freteiro': t.freteiro,
                    'modalidades': sorted(info.get('modalidades', set())),
                    'qtd_tabelas': info.get('qtd_tabelas', 0),
                })

            return jsonify({'sucesso': True, 'transportadoras': resultado})

        except Exception as e:
            logger.error(f"Erro ao buscar transportadoras modalidade: {e}")
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # DACTE PDF — Geracao on-demand
    # ------------------------------------------------------------------

    @bp.route('/api/operacao/<int:operacao_id>/dacte')
    @login_required
    def api_download_operacao_dacte(operacao_id):
        """Gera e retorna DACTE PDF de uma CarviaOperacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from flask import make_response
        from app.carvia.models import CarviaOperacao
        from app import db

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return jsonify({'erro': 'Operacao nao encontrada'}), 404

        try:
            from app.carvia.services.dacte_generator_service import DacteGeneratorService
            service = DacteGeneratorService()
            pdf_bytes = service.gerar_dacte_pdf('operacao', operacao_id)

            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            nome_arquivo = f'DACTE_{operacao.cte_numero or operacao_id}.pdf'
            response.headers['Content-Disposition'] = (
                f'inline; filename={nome_arquivo}'
            )
            return response

        except ValueError as e:
            return jsonify({'erro': str(e)}), 404
        except Exception as e:
            import xml.etree.ElementTree as ET
            if isinstance(e, ET.ParseError) or 'not well-formed' in str(e):
                logger.warning(
                    f"XML invalido para DACTE operacao {operacao_id}: {e}"
                )
                return jsonify({
                    'erro': 'XML do CTe invalido ou corrompido. '
                            'Use o PDF Original.'
                }), 422
            logger.error(f"Erro ao gerar DACTE para operacao {operacao_id}: {e}")
            return jsonify({'erro': f'Erro ao gerar DACTE: {e}'}), 500

    @bp.route('/api/subcontrato/<int:subcontrato_id>/dacte')
    @login_required
    def api_download_subcontrato_dacte(subcontrato_id):
        """Gera e retorna DACTE PDF de um CarviaSubcontrato."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from flask import make_response
        from app.carvia.models import CarviaSubcontrato
        from app import db

        sub = db.session.get(CarviaSubcontrato, subcontrato_id)
        if not sub:
            return jsonify({'erro': 'Subcontrato nao encontrado'}), 404

        try:
            from app.carvia.services.dacte_generator_service import DacteGeneratorService
            service = DacteGeneratorService()
            pdf_bytes = service.gerar_dacte_pdf('subcontrato', subcontrato_id)

            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            nome_arquivo = f'DACTE_{sub.cte_numero or subcontrato_id}.pdf'
            response.headers['Content-Disposition'] = (
                f'inline; filename={nome_arquivo}'
            )
            return response

        except ValueError as e:
            return jsonify({'erro': str(e)}), 404
        except Exception as e:
            import xml.etree.ElementTree as ET
            if isinstance(e, ET.ParseError) or 'not well-formed' in str(e):
                logger.warning(
                    f"XML invalido para DACTE subcontrato {subcontrato_id}: {e}"
                )
                return jsonify({
                    'erro': 'XML do CTe invalido ou corrompido. '
                            'Use o PDF Original.'
                }), 422
            logger.error(f"Erro ao gerar DACTE para subcontrato {subcontrato_id}: {e}")
            return jsonify({'erro': f'Erro ao gerar DACTE: {e}'}), 500

    # ------------------------------------------------------------------
    # Download PDF Original (CTe importado de PDF)
    # ------------------------------------------------------------------

    @bp.route('/api/subcontrato/<int:subcontrato_id>/pdf-original')
    @login_required
    def api_download_subcontrato_pdf_original(subcontrato_id):
        """Retorna o PDF original importado de um CarviaSubcontrato."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        import os
        from flask import send_file as flask_send_file
        from app.carvia.models import CarviaSubcontrato
        from app import db

        sub = db.session.get(CarviaSubcontrato, subcontrato_id)
        if not sub:
            return jsonify({'erro': 'Subcontrato nao encontrado'}), 404

        if not sub.cte_pdf_path:
            return jsonify({'erro': 'PDF original nao disponivel para este subcontrato'}), 404

        path = sub.cte_pdf_path

        # Path S3 (URL)
        if path.startswith('http'):
            return redirect(path)

        # Path local
        if os.path.exists(path):
            nome = f'CTe_Sub_{sub.cte_numero or subcontrato_id}_original.pdf'
            return flask_send_file(path, mimetype='application/pdf',
                                   as_attachment=False, download_name=nome)

        # Fallback: presigned URL via FileStorage
        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_presigned_url(path, expires_in=300)
            if url:
                return redirect(url)
        except Exception as e:
            logger.warning(f"Falha ao obter presigned URL para {path}: {e}")

        return jsonify({'erro': 'Arquivo nao encontrado'}), 404

    @bp.route('/api/operacao/<int:operacao_id>/pdf-original')
    @login_required
    def api_download_operacao_pdf_original(operacao_id):
        """Retorna o PDF original importado de uma CarviaOperacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        import os
        from flask import send_file as flask_send_file
        from app.carvia.models import CarviaOperacao
        from app import db

        op = db.session.get(CarviaOperacao, operacao_id)
        if not op:
            return jsonify({'erro': 'Operacao nao encontrada'}), 404

        if not op.cte_pdf_path:
            return jsonify({'erro': 'PDF original nao disponivel para esta operacao'}), 404

        path = op.cte_pdf_path

        if path.startswith('http'):
            return redirect(path)

        if os.path.exists(path):
            nome = f'CTe_{op.cte_numero or operacao_id}_original.pdf'
            return flask_send_file(path, mimetype='application/pdf',
                                   as_attachment=False, download_name=nome)

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            url = storage.get_presigned_url(path, expires_in=300)
            if url:
                return redirect(url)
        except Exception as e:
            logger.warning(f"Falha ao obter presigned URL para {path}: {e}")

        return jsonify({'erro': 'Arquivo nao encontrado'}), 404

    # ------------------------------------------------------------------
    # Conferencia de CTe Subcontratado
    # ------------------------------------------------------------------

    @bp.route('/api/conferencia-subcontrato/<int:sub_id>/calcular', methods=['POST'])
    @login_required
    def api_calcular_conferencia(sub_id):
        """Calcula todas as opcoes de frete para conferencia de um subcontrato."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.services.conferencia_service import ConferenciaService
            service = ConferenciaService()
            resultado = service.calcular_opcoes_conferencia(sub_id)
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao calcular conferencia sub {sub_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/conferencia-subcontrato/<int:sub_id>/registrar', methods=['POST'])
    @login_required
    def api_registrar_conferencia(sub_id):
        """Registra conferencia de um subcontrato (APROVADO/DIVERGENTE)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        valor_considerado = data.get('valor_considerado')
        status = data.get('status', '').strip().upper()
        observacoes = data.get('observacoes', '').strip() or None

        if valor_considerado is None:
            return jsonify({'erro': 'valor_considerado e obrigatorio'}), 400

        try:
            valor_considerado = float(valor_considerado)
        except (ValueError, TypeError):
            return jsonify({'erro': 'valor_considerado deve ser numerico'}), 400

        if status not in ('APROVADO', 'DIVERGENTE'):
            return jsonify({'erro': 'status deve ser APROVADO ou DIVERGENTE'}), 400

        try:
            from app.carvia.services.conferencia_service import ConferenciaService
            service = ConferenciaService()
            resultado = service.registrar_conferencia(
                subcontrato_id=sub_id,
                valor_considerado=valor_considerado,
                status=status,
                usuario=current_user.email,
                observacoes=observacoes,
            )
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao registrar conferencia sub {sub_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

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

            # GAP-33: Registrar valores anteriores para auditoria
            peso_cubado_anterior = float(operacao.peso_cubado) if operacao.peso_cubado else None
            peso_utilizado_anterior = float(operacao.peso_utilizado) if operacao.peso_utilizado else None

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

            # GAP-33: Log de auditoria com valores anteriores e usuario
            peso_cubado_novo = float(operacao.peso_cubado) if operacao.peso_cubado else None
            peso_utilizado_novo = float(operacao.peso_utilizado) if operacao.peso_utilizado else None
            logger.info(
                f"Cubagem atualizada | operacao_id={operacao.id} | "
                f"usuario={current_user.email} | "
                f"peso_cubado: {peso_cubado_anterior} -> {peso_cubado_novo} | "
                f"peso_utilizado: {peso_utilizado_anterior} -> {peso_utilizado_novo}"
            )

            return jsonify({
                'sucesso': True,
                'peso_cubado': peso_cubado_novo,
                'peso_utilizado': peso_utilizado_novo,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar cubagem: {e}")
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # Registrar cotacao via modal unificado
    # ------------------------------------------------------------------

    @bp.route('/api/subcontrato/<int:sub_id>/registrar-cotacao', methods=['POST'])
    @login_required
    def api_registrar_cotacao(sub_id):
        """Registra valor cotado no subcontrato via modal unificado.

        Aceita:
            valor_cotado: float (obrigatorio)
            tabela_frete_id: int (opcional, se veio de opcao de tabela)
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaSubcontrato

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return jsonify({'erro': 'Subcontrato nao encontrado'}), 404

        if sub.status in ('FATURADO', 'CANCELADO', 'CONFERIDO'):
            return jsonify({
                'erro': f'Subcontrato com status {sub.status} nao pode ser cotado.'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        valor_cotado_raw = data.get('valor_cotado')
        if valor_cotado_raw is None:
            return jsonify({'erro': 'valor_cotado e obrigatorio'}), 400

        try:
            valor_cotado = float(valor_cotado_raw)
        except (ValueError, TypeError):
            return jsonify({'erro': 'valor_cotado deve ser numerico'}), 400

        if valor_cotado <= 0:
            return jsonify({'erro': 'valor_cotado deve ser maior que zero'}), 400

        try:
            valor_anterior = float(sub.valor_cotado) if sub.valor_cotado else None
            sub.valor_cotado = valor_cotado

            tabela_frete_id = data.get('tabela_frete_id')
            if tabela_frete_id:
                sub.tabela_frete_id = int(tabela_frete_id)

            if sub.status == 'PENDENTE':
                sub.status = 'COTADO'

            db.session.commit()

            logger.info(
                f"Cotacao registrada via modal | sub_id={sub.id} | "
                f"usuario={current_user.email} | "
                f"valor: {valor_anterior} -> {valor_cotado}"
            )

            return jsonify({
                'sucesso': True,
                'valor_cotado': valor_cotado,
                'status': sub.status,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar cotacao sub {sub_id}: {e}")
            return jsonify({'erro': str(e)}), 500
