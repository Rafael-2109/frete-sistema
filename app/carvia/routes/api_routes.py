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
        """Cota frete standalone (NF ou CTe).

        Roteamento:
        - SEM categorias_moto → Cotacao de SUBCONTRATO (TabelaFrete / CotacaoService)
        - COM categorias_moto → Cotacao COMERCIAL (CarviaTabelaFrete / CarviaTabelaService)

        Exemplo categorias_moto:
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
                from app.carvia.services.pricing.carvia_tabela_service import CarviaTabelaService
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

            from app.carvia.services.pricing.cotacao_service import CotacaoService
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
            from app.carvia.services.pricing.cotacao_service import CotacaoService
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
            uf_destino: UF de destino (obrigatorio, exceto se todas=true)
            busca: texto de busca (opcional)
            todas: se 'true', retorna TODAS as transportadoras ativas
                   (sem filtro por UF) para cotacao manual
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        uf_destino = request.args.get('uf_destino', '').strip().upper()
        busca = request.args.get('busca', '').strip()
        todas = request.args.get('todas', '').strip().lower() == 'true'

        if not todas and not uf_destino:
            return jsonify({'erro': 'uf_destino obrigatorio'}), 400

        try:
            from app.transportadoras.models import Transportadora
            from app.tabelas.models import TabelaFrete

            # Buscar tabelas para o UF destino (se informado)
            tabelas_por_transp = {}
            if uf_destino:
                tabelas_query = db.session.query(TabelaFrete).filter(
                    TabelaFrete.uf_destino == uf_destino,
                )

                for t in tabelas_query.all():
                    tid = t.transportadora_id
                    if tid not in tabelas_por_transp:
                        tabelas_por_transp[tid] = {
                            'modalidades': set(),
                            'qtd_tabelas': 0,
                        }
                    tabelas_por_transp[tid]['qtd_tabelas'] += 1
                    if t.modalidade:
                        tabelas_por_transp[tid]['modalidades'].add(t.modalidade)

            if not todas and not tabelas_por_transp:
                return jsonify({'sucesso': True, 'transportadoras': []})

            # Buscar transportadoras ativas
            query = db.session.query(Transportadora).filter(
                Transportadora.ativo == True,  # noqa: E712
            )

            # Se nao pediu todas, filtra apenas as que tem tabela para o UF
            if not todas:
                query = query.filter(
                    Transportadora.id.in_(tabelas_por_transp.keys()),
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
            from app.carvia.services.documentos.dacte_generator_service import DacteGeneratorService
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
            from app.carvia.services.documentos.dacte_generator_service import DacteGeneratorService
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
        """Retorna o PDF original de uma CarviaOperacao.

        Suporta modo JSON (`?check=1`) usado pelo botao PDF SSW:
        - disponivel=True + url = abre no navegador.
        - disponivel=False + rebuscando_ssw=True = arquivo sumiu do
          bucket; cte_pdf_path foi limpado e job SSW re-enfileirado.

        Sem `?check=1`: mantem comportamento legado (redirect/send_file).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        import os
        from flask import send_file as flask_send_file, request
        from app.carvia.models import CarviaOperacao
        from app import db

        want_json = request.args.get('check') == '1'

        op = db.session.get(CarviaOperacao, operacao_id)
        if not op:
            return jsonify({'erro': 'Operacao nao encontrada'}), 404

        def _reenfileirar_job_ssw():
            """Limpa cte_pdf_path, enfileira job e retorna tuple (sucesso, msg, job_id)."""
            if not op.cte_numero:
                return (False, 'Operacao sem cte_numero — nao e possivel buscar no SSW', None)
            try:
                op.cte_pdf_path = None
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(
                    f"Falha ao limpar cte_pdf_path op={operacao_id}: {e}"
                )
                return (False, 'Falha ao limpar path — tente novamente', None)
            try:
                from app.portal.workers import enqueue_job
                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    baixar_pdf_ssw_operacao_job,
                )
                job = enqueue_job(
                    baixar_pdf_ssw_operacao_job, operacao_id,
                    queue_name='default', timeout='10m',
                )
                return (
                    True,
                    'PDF ausente no storage. Nova busca no SSW enfileirada — acompanhe o progresso no canto inferior direito.',
                    job.id,
                )
            except Exception as e:
                logger.error(
                    f"Falha ao enfileirar baixar-pdf-ssw op={operacao_id}: {e}"
                )
                return (False, f'Falha ao enfileirar job SSW: {e}', None)

        if not op.cte_pdf_path:
            if want_json:
                return jsonify({
                    'disponivel': False,
                    'mensagem': 'PDF original nao disponivel para esta operacao'
                }), 404
            return jsonify({'erro': 'PDF original nao disponivel para esta operacao'}), 404

        path = op.cte_pdf_path
        nome = f'CTe_{op.cte_numero or operacao_id}_original.pdf'

        # Path URL absoluta
        if path.startswith('http'):
            if want_json:
                return jsonify({'disponivel': True, 'url': path}), 200
            return redirect(path)

        # Path local
        if os.path.exists(path):
            if want_json:
                from flask import url_for
                return jsonify({
                    'disponivel': True,
                    'url': url_for('carvia.api_download_operacao_pdf_original',
                                   operacao_id=operacao_id),
                }), 200
            return flask_send_file(path, mimetype='application/pdf',
                                   as_attachment=False, download_name=nome)

        # Path S3 — checar existencia ANTES de redirect
        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            if storage.file_exists(path):
                url = storage.get_presigned_url(path, expires_in=300)
                if url:
                    if want_json:
                        return jsonify({'disponivel': True, 'url': url}), 200
                    return redirect(url)
        except Exception as e:
            logger.warning(f"Falha ao verificar/gerar presigned URL para {path}: {e}")

        # Arquivo ausente — limpa path, re-enfileira job SSW
        sucesso, mensagem, job_id_rebusca = _reenfileirar_job_ssw()
        status = 202 if sucesso else 500
        if want_json:
            return jsonify({
                'disponivel': False,
                'rebuscando_ssw': sucesso,
                'mensagem': mensagem,
                'job_id': job_id_rebusca,
            }), status
        return jsonify({
            'erro': 'Arquivo nao encontrado',
            'rebuscando_ssw': sucesso,
            'mensagem': mensagem,
            'job_id': job_id_rebusca,
        }), status

    # ------------------------------------------------------------------
    # SSW — Re-buscar CTRC e re-baixar DACTE para CarviaOperacao
    # ------------------------------------------------------------------

    @bp.route('/api/operacao/<int:operacao_id>/atualizar-ctrc', methods=['POST'])
    @login_required
    def api_atualizar_ctrc_operacao(operacao_id):
        """Enfileira job RQ para re-consultar CTRC via SSW opcao 101.

        Usa o worker `verificar_ctrc_operacao_job` que ja existe — roda
        `consultar_ctrc_101.py --cte {n}` e atualiza `CarviaOperacao.ctrc_numero`
        se divergir. Job assincrono (fila `default`, timeout 10m).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.models import CarviaOperacao

            op = db.session.get(CarviaOperacao, operacao_id)
            if not op:
                return jsonify({'erro': 'Operacao nao encontrada'}), 404
            if op.status == 'CANCELADO':
                return jsonify({'erro': 'Operacao cancelada'}), 422
            if not op.cte_numero:
                return jsonify({
                    'erro': 'Operacao sem cte_numero — nao e possivel buscar no SSW'
                }), 422

            from app.portal.workers import enqueue_job
            from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                verificar_ctrc_operacao_job,
            )
            job = enqueue_job(
                verificar_ctrc_operacao_job, operacao_id,
                queue_name='default', timeout='10m',
            )
            return jsonify({
                'sucesso': True,
                'job_id': job.id,
                'mensagem': (
                    'Atualizacao do CTRC enfileirada. '
                    'Atualize a pagina em alguns segundos.'
                ),
            }), 202
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro ao enfileirar atualizar-ctrc op={operacao_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/operacao/<int:operacao_id>/baixar-pdf-ssw', methods=['POST'])
    @login_required
    def api_baixar_pdf_ssw_operacao(operacao_id):
        """Enfileira job RQ para re-baixar DACTE PDF via SSW opcao 101.

        Usa o worker `baixar_pdf_ssw_operacao_job` — roda
        `consultar_ctrc_101.py --cte {n} --baixar-dacte`, faz upload para S3
        em `carvia/ctes_pdf/` e atualiza `CarviaOperacao.cte_pdf_path`.
        Job assincrono (fila `default`, timeout 10m). NAO mexe em XML.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.models import CarviaOperacao

            op = db.session.get(CarviaOperacao, operacao_id)
            if not op:
                return jsonify({'erro': 'Operacao nao encontrada'}), 404
            if not op.cte_numero:
                return jsonify({
                    'erro': 'Operacao sem cte_numero — nao e possivel buscar no SSW'
                }), 422

            from app.portal.workers import enqueue_job
            from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                baixar_pdf_ssw_operacao_job,
            )
            job = enqueue_job(
                baixar_pdf_ssw_operacao_job, operacao_id,
                queue_name='default', timeout='10m',
            )
            return jsonify({
                'sucesso': True,
                'job_id': job.id,
                'mensagem': (
                    'Download do PDF SSW enfileirado. '
                    'Atualize a pagina em ~30 segundos.'
                ),
            }), 202
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro ao enfileirar baixar-pdf-ssw op={operacao_id}: {e}')
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # SSW — Re-buscar CTRC para CarviaCteComplementar (A3.5)
    # ------------------------------------------------------------------

    @bp.route(
        '/api/cte-complementar/<int:cte_comp_id>/atualizar-ctrc',
        methods=['POST'],
    )
    @login_required
    def api_atualizar_ctrc_cte_complementar(cte_comp_id):
        """Enfileira job RQ para consultar/verificar CTRC do CTe Complementar
        via SSW opcao 101.

        A3.5 (2026-04-17): equivalente a `api_atualizar_ctrc_operacao`.
        2026-04-22: worker agora prioriza busca por --cte (em vez de
        --ctrc) sempre que cte_numero estiver preenchido, e baixa o
        DACTE PDF na mesma chamada quando cte_pdf_path vazio.

        Casos tratados no worker:
          - CTE_DISPONIVEL: cte_numero preenchido -> --cte + PDF (se vazio)
          - SO_CTRC (fallback): so ctrc_numero -> --ctrc (legado)
          - SKIPPED: ambos vazios
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.models import CarviaCteComplementar

            cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
            if not cte_comp:
                return jsonify({'erro': 'CTe Complementar nao encontrado'}), 404
            if cte_comp.status == 'CANCELADO':
                return jsonify({'erro': 'CTe Complementar cancelado'}), 422
            if not cte_comp.cte_numero and not cte_comp.ctrc_numero:
                return jsonify({
                    'erro': (
                        'CTe Complementar sem cte_numero e sem ctrc_numero '
                        '— nao e possivel buscar no SSW'
                    )
                }), 422

            from app.portal.workers import enqueue_job
            from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                verificar_ctrc_cte_comp_job,
            )
            job = enqueue_job(
                verificar_ctrc_cte_comp_job, cte_comp_id,
                queue_name='default', timeout='10m',
            )
            return jsonify({
                'sucesso': True,
                'job_id': job.id,
                'mensagem': (
                    'Atualizacao do CTRC (e PDF, se ausente) do CTe '
                    'Complementar enfileirada via SSW 101 --cte. '
                    'Atualize a pagina em alguns segundos.'
                ),
            }), 202
        except Exception as e:
            db.session.rollback()
            logger.error(
                f'Erro ao enfileirar atualizar-ctrc cte_comp={cte_comp_id}: {e}'
            )
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # Status generico de job RQ — usado pelo SswProgress para jobs
    # sem modelo proprio de tracking (atualizar-ctrc, baixar-pdf-ssw,
    # verificar_ctrc_cte_comp, etc).
    # ------------------------------------------------------------------

    @bp.route('/api/ssw-jobs/<job_id>/status', methods=['GET'])
    @login_required
    def api_ssw_job_status(job_id):
        """Retorna status de um job RQ generico.

        Usado pelo cliente JS SswProgress.start({statusType: 'rq_job'})
        para acompanhar jobs sem modelo proprio — quando o job termina,
        `result` carrega o dict retornado pela funcao (CTRC atualizado,
        path do PDF, etc) e a UI usa isso para gerar mensagem final.

        Returns:
            200 {status, result, erro}
              status: queued | started | finished | failed | deferred |
                      scheduled | not_found
            404 quando job expirou do redis (TTL).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from rq.job import Job
            from app.portal.workers import get_redis_connection

            conn = get_redis_connection()
            try:
                job = Job.fetch(job_id, connection=conn)
            except Exception:
                return jsonify({
                    'status': 'not_found',
                    'erro': 'Job nao encontrado (expirou do cache ou ID invalido)',
                }), 404

            status = job.get_status()
            payload = {'job_id': job_id, 'status': status}

            if status == 'finished':
                try:
                    payload['result'] = job.result
                except Exception as e:
                    payload['erro'] = f'Falha ao ler resultado: {e}'
            elif status == 'failed':
                # RQ 1.x: `job.exc_info` esta deprecated e pode ser None em
                # serializers nao-default. `job.latest_result()` expoe o
                # `exc_string` canonico da ultima execucao.
                exc_str = None
                try:
                    result = job.latest_result()
                    if result is not None:
                        exc_str = getattr(result, 'exc_string', None)
                except Exception:
                    pass
                # Fallback para API legada
                if not exc_str:
                    try:
                        exc_str = job.exc_info
                    except Exception:
                        exc_str = None
                payload['erro'] = (exc_str or 'Falha no job')[-1500:]

            return jsonify(payload)
        except Exception as e:
            logger.error(f'Erro ao consultar status job {job_id}: {e}')
            return jsonify({'erro': str(e)}), 500

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
            from app.carvia.services.documentos.conferencia_service import ConferenciaService
            service = ConferenciaService()
            resultado = service.calcular_opcoes_conferencia(sub_id)
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao calcular conferencia sub {sub_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # Phase C (2026-04-14): endpoints frete-based (paralelo aos sub-based).
    # Nova tela /conferir itera fretes diretamente — estas rotas sao a
    # interface canonica daqui para frente.
    # ------------------------------------------------------------------
    @bp.route('/api/conferencia-frete/<int:frete_id>/calcular', methods=['POST'])
    @login_required
    def api_calcular_conferencia_frete(frete_id):
        """Calcula opcoes de frete para conferencia de um CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.models import CarviaFrete
            from app.carvia.services.documentos.conferencia_service import ConferenciaService

            frete = db.session.get(CarviaFrete, frete_id)
            if not frete:
                return jsonify({'sucesso': False, 'erro': 'Frete nao encontrado'}), 404

            # Reusa o motor de calculo existente (sub-based) usando o primary sub
            primary_sub = frete.subcontratos.first()
            if not primary_sub:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Frete sem subcontrato — nao e possivel calcular opcoes',
                }), 400

            service = ConferenciaService()
            resultado = service.calcular_opcoes_conferencia(primary_sub.id)
            # Enriquecer com valores atuais do frete (fonte canonica pos-Phase C)
            if resultado.get('sucesso'):
                resultado['frete_info'] = {
                    'id': frete.id,
                    'status_conferencia': frete.status_conferencia,
                    'valor_cotado': float(frete.valor_cotado or 0),
                    'valor_cte': float(frete.valor_cte or 0),
                    'valor_considerado': (
                        float(frete.valor_considerado)
                        if frete.valor_considerado is not None else None
                    ),
                    'valor_pago': (
                        float(frete.valor_pago)
                        if frete.valor_pago is not None else None
                    ),
                    'requer_aprovacao': frete.requer_aprovacao,
                }
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao calcular conferencia frete {frete_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/conferencia-frete/<int:frete_id>/registrar', methods=['POST'])
    @login_required
    def api_registrar_conferencia_frete(frete_id):
        """Registra conferencia de um CarviaFrete (APROVADO/DIVERGENTE).

        Opera direto em Frete (paridade Nacom). Se DIVERGENTE acima da
        tolerancia, ConferenciaService abre tratativa via AprovacaoFreteService.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        valor_considerado = data.get('valor_considerado')
        valor_pago = data.get('valor_pago')
        status = (data.get('status') or '').strip().upper()
        observacoes = (data.get('observacoes') or '').strip() or None

        if valor_considerado is None:
            return jsonify({'erro': 'valor_considerado e obrigatorio'}), 400
        try:
            valor_considerado = float(valor_considerado)
        except (ValueError, TypeError):
            return jsonify({'erro': 'valor_considerado deve ser numerico'}), 400

        if valor_pago is not None:
            try:
                valor_pago = float(valor_pago)
            except (ValueError, TypeError):
                return jsonify({'erro': 'valor_pago deve ser numerico'}), 400

        if status not in ('APROVADO', 'DIVERGENTE'):
            return jsonify({'erro': 'status deve ser APROVADO ou DIVERGENTE'}), 400

        try:
            from app.carvia.services.documentos.conferencia_service import ConferenciaService
            service = ConferenciaService()
            resultado = service.registrar_conferencia(
                frete_id=frete_id,
                valor_considerado=valor_considerado,
                status=status,
                usuario=current_user.email,
                observacoes=observacoes,
                valor_pago=valor_pago,
            )
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Erro ao registrar conferencia frete {frete_id}: {e}")
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
            # Phase C (2026-04-14): ConferenciaService.registrar_conferencia
            # agora opera em Frete. Resolvemos frete_id via sub.frete_id.
            from app.carvia.models import CarviaSubcontrato
            sub = db.session.get(CarviaSubcontrato, sub_id)
            if not sub:
                return jsonify({'sucesso': False, 'erro': 'Subcontrato nao encontrado'}), 404
            if not sub.frete_id:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Subcontrato sem frete vinculado — conferencia nao disponivel',
                }), 400

            from app.carvia.services.documentos.conferencia_service import ConferenciaService
            service = ConferenciaService()
            resultado = service.registrar_conferencia(
                frete_id=sub.frete_id,
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

    # ==================================================================
    # Modelos de moto (JSON para selects)
    # ==================================================================

    @bp.route('/api/modelos-moto', methods=['GET'])
    @login_required
    def api_listar_modelos_moto():
        """Lista modelos de moto ativos para selects (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaModeloMoto
        modelos = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
            CarviaModeloMoto.nome.asc()
        ).all()

        return jsonify({
            'modelos': [{
                'id': m.id,
                'nome': m.nome,
                'comprimento': float(m.comprimento),
                'largura': float(m.largura),
                'altura': float(m.altura),
                'peso_medio': float(m.peso_medio) if m.peso_medio else None,
            } for m in modelos]
        })

    # ==================================================================
    # Emissao automatica CTe SSW
    # ==================================================================

    @bp.route('/api/nfs/<int:nf_id>/emitir-cte-ssw', methods=['POST'])
    @login_required
    def api_emitir_cte_ssw(nf_id):
        """Dispara emissao assincrona de CTe no SSW para uma NF.

        Body JSON:
            placa: str (default "ARMAZEM")
            cnpj_tomador: str (14 digitos, para fatura 437)
            frete_valor: float (R$ frete peso)
            data_vencimento: str (YYYY-MM-DD)
            uf_origem: str (UF 2 letras: SP, RJ. Auto-detecta da NF se omitido)
            medidas: list[{modelo_id: int, qtd: int}]

        Returns 202:
            {emissao_id, job_id, status, status_url}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Body JSON obrigatorio'}), 400

        placa = data.get('placa', 'ARMAZEM')
        cnpj_tomador = data.get('cnpj_tomador')
        frete_valor = data.get('frete_valor')
        medidas = data.get('medidas')

        if frete_valor is None:
            return jsonify({'erro': 'frete_valor obrigatorio'}), 400

        # Parsear data_vencimento
        data_vencimento = None
        if data.get('data_vencimento'):
            try:
                from datetime import datetime
                data_vencimento = datetime.strptime(
                    data['data_vencimento'], '%Y-%m-%d'
                ).date()
            except ValueError:
                return jsonify({
                    'erro': 'data_vencimento invalida (formato esperado: YYYY-MM-DD)'
                }), 400

        try:
            from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService
            resultado = SswEmissaoService.preparar_emissao(
                nf_id=nf_id,
                placa=placa,
                cnpj_tomador=cnpj_tomador,
                frete_valor=frete_valor,
                data_vencimento=data_vencimento,
                medidas_motos=medidas,
                usuario=current_user.email,
                uf_origem=data.get('uf_origem'),
            )
            resultado['status_url'] = (
                f'/carvia/api/emissao-cte/{resultado["emissao_id"]}/status'
            )
            return jsonify(resultado), 202

        except ValueError as e:
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao enfileirar emissao CTe NF {nf_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/emissao-cte/<int:emissao_id>/status', methods=['GET'])
    @login_required
    def api_status_emissao_cte(emissao_id):
        """Polling: retorna status da emissao SSW."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaEmissaoCte
        emissao = db.session.get(CarviaEmissaoCte, emissao_id)
        if not emissao:
            return jsonify({'erro': 'Emissao nao encontrada'}), 404

        return jsonify({
            'emissao_id': emissao.id,
            'nf_id': emissao.nf_id,
            'status': emissao.status,
            'etapa': emissao.etapa,
            'ctrc': emissao.ctrc_numero,
            'erro': emissao.erro_ssw,
            'operacao_id': emissao.operacao_id,
            'fatura_numero': emissao.fatura_numero,
            'criado_em': emissao.criado_em.isoformat() if emissao.criado_em else None,
            'atualizado_em': emissao.atualizado_em.isoformat() if emissao.atualizado_em else None,
        })

    @bp.route('/api/nfs/<int:nf_id>/emissao-status', methods=['GET'])
    @login_required
    def api_nf_emissao_status(nf_id):
        """Retorna a emissao mais recente de uma NF (para observabilidade on-load).

        Returns 200:
            {emissao: {id, status, etapa, erro, ctrc, operacao_id, fatura_numero,
                       criado_em, atualizado_em} | null}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaEmissaoCte
        emissao = CarviaEmissaoCte.query.filter_by(nf_id=nf_id).order_by(
            CarviaEmissaoCte.id.desc()
        ).first()

        if not emissao:
            return jsonify({'emissao': None})

        return jsonify({'emissao': {
            'id': emissao.id,
            'status': emissao.status,
            'etapa': emissao.etapa,
            'erro': emissao.erro_ssw,
            'ctrc': emissao.ctrc_numero,
            'operacao_id': emissao.operacao_id,
            'fatura_numero': emissao.fatura_numero,
            'criado_em': emissao.criado_em.isoformat() if emissao.criado_em else None,
            'atualizado_em': emissao.atualizado_em.isoformat() if emissao.atualizado_em else None,
        }})

    @bp.route('/api/emitir-cte-ssw/lote', methods=['POST'])
    @login_required
    def api_emitir_cte_ssw_lote():
        """Dispara emissao de CTe SSW para multiplas NFs.

        Body JSON:
            nf_ids: list[int]
            placa: str (default "ARMAZEM")
            cnpj_tomador: str
            frete_valor: float
            data_vencimento: str (YYYY-MM-DD)
            medidas: list[{modelo_id, qtd}]

        Returns 202:
            {emissoes: [{nf_id, emissao_id, status}]}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data or not data.get('nf_ids'):
            return jsonify({'erro': 'nf_ids obrigatorio'}), 400

        nf_ids = data['nf_ids']
        if not isinstance(nf_ids, list) or len(nf_ids) == 0:
            return jsonify({'erro': 'nf_ids deve ser lista nao-vazia'}), 400
        if len(nf_ids) > 20:
            return jsonify({'erro': 'Maximo 20 NFs por lote'}), 400
        if data.get('frete_valor') is None:
            return jsonify({'erro': 'frete_valor obrigatorio'}), 400

        # Parsear data_vencimento
        data_vencimento = None
        if data.get('data_vencimento'):
            try:
                from datetime import datetime
                data_vencimento = datetime.strptime(
                    data['data_vencimento'], '%Y-%m-%d'
                ).date()
            except ValueError:
                return jsonify({
                    'erro': 'data_vencimento invalida (formato YYYY-MM-DD)'
                }), 400

        try:
            from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService
            resultados = SswEmissaoService.preparar_emissao_lote(
                nf_ids=nf_ids,
                placa=data.get('placa', 'ARMAZEM'),
                cnpj_tomador=data.get('cnpj_tomador'),
                frete_valor=data.get('frete_valor'),
                data_vencimento=data_vencimento,
                medidas_motos=data.get('medidas'),
                usuario=current_user.email,
                uf_origem=data.get('uf_origem'),
            )
            return jsonify({'emissoes': resultados}), 202

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao enfileirar lote CTe: {e}")
            return jsonify({'erro': str(e)}), 500

    # ------------------------------------------------------------------
    # Backfill Frete — Cotacao + Recalculo
    # ------------------------------------------------------------------

    @bp.route('/api/fretes/cotar-backfill', methods=['POST'])
    @login_required
    def api_cotar_backfill():
        """Cotacao para backfill — busca melhor tabela e retorna parametros editaveis.

        NAO usa ICMS da cidade — apenas icms_proprio da tabela (regra CarVia).
        Retorna parametros completos + breakdown para edicao no frontend.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        transportadora_id = data.get('transportadora_id')
        peso = float(data.get('peso', 0) or 0)
        valor_mercadoria = float(data.get('valor_mercadoria', 0) or 0)
        uf_destino = (data.get('uf_destino') or '').strip().upper()
        cidade_destino = (data.get('cidade_destino') or '').strip() or None
        modalidade_filtro = (data.get('modalidade') or '').strip() or None

        if not transportadora_id or peso <= 0 or not uf_destino:
            return jsonify({
                'sucesso': False,
                'erro': 'transportadora_id, peso e uf_destino obrigatorios',
            }), 400

        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            from app.tabelas.models import TabelaFrete
            from app.transportadoras.models import Transportadora
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager

            svc = CotacaoService()
            transportadora = db.session.get(Transportadora, int(transportadora_id))
            if not transportadora:
                return jsonify({'sucesso': False, 'erro': 'Transportadora nao encontrada'}), 400

            # Buscar tabelas via CidadeAtendida → grupo empresarial → TabelaFrete
            grupo_ids = svc._obter_grupo_transportadora(int(transportadora_id))
            tabelas = []

            if cidade_destino:
                cidade_obj = svc._resolver_cidade(cidade_destino, uf_destino)
                if cidade_obj:
                    vinculos = svc._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
                    for vinculo in vinculos:
                        if vinculo.transportadora_id not in grupo_ids:
                            continue
                        query = TabelaFrete.query.filter(
                            TabelaFrete.transportadora_id.in_(grupo_ids),
                            TabelaFrete.uf_destino == uf_destino,
                            TabelaFrete.nome_tabela == vinculo.nome_tabela,
                        )
                        tabelas.extend(query.all())

            # Fallback UF: apenas quando cidade NAO foi informada.
            # Se cidade foi informada mas nao tem vinculos, bloquear
            # (mesma politica de CotacaoService.cotar_todas_opcoes).
            if not tabelas and not cidade_destino:
                tabelas = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_destino == uf_destino,
                ).all()

            if not tabelas:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Sem tabela para {transportadora.razao_social} → {uf_destino}',
                })

            # Filtrar por modalidade real (TabelaFrete.modalidade) se informada
            if modalidade_filtro and tabelas:
                filtradas = [t for t in tabelas if t.modalidade == modalidade_filtro]
                if filtradas:
                    tabelas = filtradas

            # Calcular com cada tabela, pegar a melhor
            tabelas_unicas = {t.id: t for t in tabelas}
            melhor = None
            melhor_tabela_dados = None

            for tabela in tabelas_unicas.values():
                try:
                    tabela_dados = TabelaFreteManager.preparar_dados_tabela(tabela)
                    resultado = CalculadoraFrete.calcular_frete_unificado(
                        peso=peso,
                        valor_mercadoria=valor_mercadoria,
                        tabela_dados=tabela_dados,
                        cidade=None,  # CarVia: apenas icms_proprio
                    )
                    if resultado and 'valor_com_icms' in resultado:
                        valor = float(resultado['valor_com_icms'])
                        if melhor is None or valor < melhor['valor']:
                            melhor = {
                                'valor': valor,
                                'tabela_frete_id': tabela.id,
                                'tabela_nome': tabela.nome_tabela,
                                'tabela_modalidade': tabela.modalidade,
                                'resultado': resultado,
                            }
                            melhor_tabela_dados = tabela_dados
                except Exception as e:
                    logger.warning("Erro ao calcular com tabela %s: %s", tabela.id, e)
                    continue

            if not melhor:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Nenhuma tabela conseguiu calcular o frete',
                })

            # Montar parametros editaveis
            resultado = melhor['resultado']
            detalhes = resultado.get('detalhes', {})
            parametros = {
                'valor_kg': float(melhor_tabela_dados.get('valor_kg', 0) or 0),
                'percentual_valor': float(melhor_tabela_dados.get('percentual_valor', 0) or 0),
                'frete_minimo_valor': float(melhor_tabela_dados.get('frete_minimo_valor', 0) or 0),
                'frete_minimo_peso': float(melhor_tabela_dados.get('frete_minimo_peso', 0) or 0),
                'icms_proprio': float(melhor_tabela_dados.get('icms_proprio', 0) or 0),
                'icms_incluso': bool(melhor_tabela_dados.get('icms_incluso', False)),
                'percentual_gris': float(melhor_tabela_dados.get('percentual_gris', 0) or 0),
                'gris_minimo': float(melhor_tabela_dados.get('gris_minimo', 0) or 0),
                'pedagio_por_100kg': float(melhor_tabela_dados.get('pedagio_por_100kg', 0) or 0),
                'valor_tas': float(melhor_tabela_dados.get('valor_tas', 0) or 0),
                'percentual_adv': float(melhor_tabela_dados.get('percentual_adv', 0) or 0),
                'adv_minimo': float(melhor_tabela_dados.get('adv_minimo', 0) or 0),
                'percentual_rca': float(melhor_tabela_dados.get('percentual_rca', 0) or 0),
                'valor_despacho': float(melhor_tabela_dados.get('valor_despacho', 0) or 0),
                'valor_cte': float(melhor_tabela_dados.get('valor_cte', 0) or 0),
            }

            breakdown = {
                'frete_base': float(detalhes.get('frete_base', 0)),
                'gris': float(detalhes.get('gris', 0)),
                'adv': float(detalhes.get('adv', 0)),
                'rca': float(detalhes.get('rca', 0)),
                'pedagio': float(detalhes.get('pedagio', 0)),
                'valor_tas': float(detalhes.get('valor_tas', 0)),
                'valor_despacho': float(detalhes.get('valor_despacho', 0)),
                'valor_cte': float(detalhes.get('valor_cte', 0)),
                'frete_minimo_aplicado': detalhes.get('frete_minimo_aplicado', False),
                'valor_bruto': float(resultado.get('valor_bruto', 0)),
                'valor_com_icms': float(resultado.get('valor_com_icms', 0)),
                'icms_aplicado': float(resultado.get('icms_aplicado', 0)),
            }

            return jsonify({
                'sucesso': True,
                'valor_cotado': round(melhor['valor'], 2),
                'tabela_frete_id': melhor['tabela_frete_id'],
                'tabela_nome': melhor['tabela_nome'],
                'tabela_modalidade': melhor['tabela_modalidade'],
                'parametros': parametros,
                'breakdown': breakdown,
            })

        except Exception as e:
            logger.error("Erro cotacao backfill: %s", e, exc_info=True)
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/fretes/recalcular', methods=['POST'])
    @login_required
    def api_recalcular_frete():
        """Recalcula frete com parametros customizados (editados pelo usuario).

        Aceita todos os parametros da tabela + peso/valor e retorna
        valor recalculado + breakdown. NAO usa ICMS da cidade.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        peso = float(data.get('peso', 0) or 0)
        valor_mercadoria = float(data.get('valor_mercadoria', 0) or 0)
        parametros = data.get('parametros', {})

        if peso <= 0:
            return jsonify({'sucesso': False, 'erro': 'peso obrigatorio'}), 400

        try:
            from app.utils.calculadora_frete import CalculadoraFrete

            # Montar tabela_dados a partir dos parametros editados
            tabela_dados = {
                'valor_kg': float(parametros.get('valor_kg', 0) or 0),
                'percentual_valor': float(parametros.get('percentual_valor', 0) or 0),
                'frete_minimo_valor': float(parametros.get('frete_minimo_valor', 0) or 0),
                'frete_minimo_peso': float(parametros.get('frete_minimo_peso', 0) or 0),
                'icms_proprio': float(parametros.get('icms_proprio', 0) or 0),
                'icms_incluso': bool(parametros.get('icms_incluso', False)),
                'percentual_gris': float(parametros.get('percentual_gris', 0) or 0),
                'gris_minimo': float(parametros.get('gris_minimo', 0) or 0),
                'pedagio_por_100kg': float(parametros.get('pedagio_por_100kg', 0) or 0),
                'valor_tas': float(parametros.get('valor_tas', 0) or 0),
                'percentual_adv': float(parametros.get('percentual_adv', 0) or 0),
                'adv_minimo': float(parametros.get('adv_minimo', 0) or 0),
                'percentual_rca': float(parametros.get('percentual_rca', 0) or 0),
                'valor_despacho': float(parametros.get('valor_despacho', 0) or 0),
                'valor_cte': float(parametros.get('valor_cte', 0) or 0),
                'nome_tabela': parametros.get('nome_tabela', ''),
                'icms': 0,  # nao usar ICMS generico
                'icms_destino': 0,  # nao usar ICMS destino
            }

            resultado = CalculadoraFrete.calcular_frete_unificado(
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                tabela_dados=tabela_dados,
                cidade=None,  # CarVia: apenas icms_proprio
            )

            if not resultado or 'valor_com_icms' not in resultado:
                return jsonify({'sucesso': False, 'erro': 'Calculo retornou vazio'})

            detalhes = resultado.get('detalhes', {})
            breakdown = {
                'frete_base': float(detalhes.get('frete_base', 0)),
                'gris': float(detalhes.get('gris', 0)),
                'adv': float(detalhes.get('adv', 0)),
                'rca': float(detalhes.get('rca', 0)),
                'pedagio': float(detalhes.get('pedagio', 0)),
                'valor_tas': float(detalhes.get('valor_tas', 0)),
                'valor_despacho': float(detalhes.get('valor_despacho', 0)),
                'valor_cte': float(detalhes.get('valor_cte', 0)),
                'frete_minimo_aplicado': detalhes.get('frete_minimo_aplicado', False),
                'valor_bruto': float(resultado.get('valor_bruto', 0)),
                'valor_com_icms': float(resultado.get('valor_com_icms', 0)),
                'icms_aplicado': float(resultado.get('icms_aplicado', 0)),
            }

            return jsonify({
                'sucesso': True,
                'valor_cotado': round(float(resultado['valor_com_icms']), 2),
                'breakdown': breakdown,
            })

        except Exception as e:
            logger.error("Erro recalcular frete: %s", e, exc_info=True)
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
