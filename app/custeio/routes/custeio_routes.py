"""
Rotas do modulo de Custeio
"""
from flask import render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime
from io import BytesIO
import logging

from app.custeio.services.custeio_service import ServicoCusteio

logger = logging.getLogger(__name__)


def register_custeio_routes(bp):
    """Registra rotas do modulo de custeio"""

    # ================================================
    # PAGINAS - DASHBOARD E TELAS CRUD
    # ================================================

    @bp.route('/') #type: ignore
    @login_required
    def index():
        """Dashboard principal de custeio"""
        return render_template('custeio/dashboard.html')

    @bp.route('/frete') #type: ignore
    @login_required
    def tela_frete():
        """Tela CRUD de Custo de Frete"""
        return render_template('custeio/frete.html')

    @bp.route('/producao') #type: ignore
    @login_required
    def tela_producao():
        """Tela de Custo de Producao"""
        return render_template('custeio/producao.html')

    @bp.route('/definicao') #type: ignore
    @login_required
    def tela_definicao():
        """Tela de Definicao de Custo Considerado"""
        return render_template('custeio/definicao.html')

    @bp.route('/mensal') #type: ignore
    @login_required
    def tela_mensal():
        """Tela de Fechamento Mensal de Custos"""
        return render_template('custeio/mensal.html')

    @bp.route('/parametros') #type: ignore
    @login_required
    def tela_parametros():
        """Tela de Parametros de Custeio"""
        return render_template('custeio/parametros.html')

    # ================================================
    # API - DASHBOARD ESTATISTICAS
    # ================================================

    @bp.route('/api/dashboard/estatisticas') #type: ignore
    @login_required
    def dashboard_estatisticas():
        """Retorna estatisticas para o dashboard"""
        try:
            from app.custeio.models import CustoConsiderado, CustoFrete
            from app.producao.models import CadastroPalletizacao

            # Produtos com custo definido
            produtos_custeados = CustoConsiderado.query.filter(
                CustoConsiderado.custo_atual == True,
                CustoConsiderado.custo_considerado.isnot(None)
            ).count()

            # Produtos por tipo
            comprados = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_comprado == True
            ).count()

            produzidos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True
            ).count()

            # Tabelas de frete
            fretes = CustoFrete.query.count()

            return jsonify({
                'sucesso': True,
                'produtos_custeados': produtos_custeados,
                'comprados': comprados,
                'produzidos': produzidos,
                'fretes': fretes
            })

        except Exception as e:
            logger.error(f"Erro ao buscar estatisticas dashboard: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - CUSTO MENSAL
    # ================================================

    @bp.route('/api/mensal/listar') #type: ignore
    @login_required
    def listar_custos_mensais():
        """Lista custos mensais com filtros e estatísticas"""
        try:

            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)
            tipo_produto = request.args.get('tipo', '')  # Corrigido: 'tipo' não 'tipo_produto'
            cod_produto = request.args.get('cod_produto')

            custos = ServicoCusteio.listar_custos_mensais(
                mes=mes,
                ano=ano,
                tipo_produto=tipo_produto if tipo_produto else None,
                cod_produto=cod_produto
            )

            # Calcular estatísticas
            comprados = sum(1 for c in custos if c.get('tipo_produto') == 'COMPRADO')
            intermediarios = sum(1 for c in custos if c.get('tipo_produto') == 'INTERMEDIARIO')
            acabados = sum(1 for c in custos if c.get('tipo_produto') == 'ACABADO')

            # Verificar status do período
            status_periodo = 'ABERTO'
            if custos:
                fechados = sum(1 for c in custos if c.get('status') == 'FECHADO')
                if fechados == len(custos):
                    status_periodo = 'FECHADO'
                elif fechados > 0:
                    status_periodo = 'PARCIAL'

            return jsonify({
                'sucesso': True,
                'dados': custos,
                'total': len(custos),
                'comprados': comprados,
                'intermediarios': intermediarios,
                'acabados': acabados,
                'status_periodo': status_periodo
            })

        except Exception as e:
            logger.error(f"Erro ao listar custos mensais: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/mensal/fechar', methods=['POST']) #type: ignore
    @login_required
    def fechar_mes():
        """Executa fechamento mensal de custos"""
        try:
            dados = request.json or {}
            mes = dados.get('mes')
            ano = dados.get('ano')

            if not mes or not ano:
                return jsonify({'erro': 'Mes e ano sao obrigatorios'}), 400

            resultado = ServicoCusteio.fechar_mes(
                mes=int(mes),
                ano=int(ano),
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            if resultado.get('erro'):
                return jsonify({
                    'sucesso': False,
                    'erro': resultado['erro']
                }), 500

            return jsonify({
                'sucesso': True,
                'resultado': resultado,
                'mensagem': f"Fechamento concluido: {resultado['total']} produtos processados"
            })

        except Exception as e:
            logger.error(f"Erro no fechamento: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/mensal/simular') #type: ignore
    @login_required
    def simular_fechamento():
        """Simula fechamento sem persistir (preview)"""
        try:
            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)

            if not mes or not ano:
                return jsonify({'erro': 'Mes e ano sao obrigatorios'}), 400

            preview = ServicoCusteio.simular_fechamento(mes, ano)

            if preview.get('erro'):
                return jsonify({
                    'sucesso': False,
                    'erro': preview['erro']
                }), 500

            return jsonify({
                'sucesso': True,
                'preview': preview
            })

        except Exception as e:
            logger.error(f"Erro na simulacao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/mensal/exportar') #type: ignore
    @login_required
    def exportar_mensal():
        """Exporta custos mensais para Excel"""
        try:
            import pandas as pd
            from app.custeio.models import CustoMensal

            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)

            if not mes or not ano:
                return jsonify({'erro': 'Mes e ano sao obrigatorios'}), 400

            custos = CustoMensal.query.filter_by(mes=mes, ano=ano).order_by(CustoMensal.cod_produto).all()

            dados_excel = []
            for c in custos:
                dados_excel.append({
                    'Codigo': c.cod_produto,
                    'Nome': c.nome_produto,
                    'Tipo': c.tipo_produto,
                    'Custo Liquido Medio': float(c.custo_liquido_medio) if c.custo_liquido_medio else '',
                    'Ultimo Custo': float(c.ultimo_custo) if c.ultimo_custo else '',
                    'Custo Medio Estoque': float(c.custo_medio_estoque) if c.custo_medio_estoque else '',
                    'Custo BOM': float(c.custo_bom) if c.custo_bom else '',
                    'Qtd Comprada': float(c.qtd_comprada) if c.qtd_comprada else 0,
                    'Valor Compras Liquido': float(c.valor_compras_liquido) if c.valor_compras_liquido else 0,
                    'Status': c.status
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=f'Custo {mes:02d}/{ano}')

            output.seek(0)

            meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            nome_arquivo = f'custo_mensal_{meses[mes]}_{ano}.xlsx'

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao exportar mensal: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/mensal/detalhe-bom/<cod_produto>') #type: ignore
    @login_required
    def detalhe_bom_mensal(cod_produto):
        """
        Retorna detalhes da composição BOM de um produto com custos do período.
        Usado para expansão inline na tela de fechamento mensal.
        """
        try:
            from app.manufatura.services.bom_service import ServicoBOM
            from app.custeio.models import CustoMensal

            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)

            if not mes or not ano:
                return jsonify({'erro': 'Mes e ano são obrigatórios'}), 400

            # Buscar custo mensal do produto pai
            custo_pai = CustoMensal.query.filter_by(
                cod_produto=cod_produto,
                mes=mes,
                ano=ano
            ).first()

            if not custo_pai:
                return jsonify({'erro': f'Produto {cod_produto} não encontrado no período'}), 404

            # Explodir BOM para pegar componentes
            bom = ServicoBOM.explodir_bom(cod_produto, 1.0)

            if not bom.get('componentes'):
                return jsonify({
                    'sucesso': True,
                    'cod_produto': cod_produto,
                    'componentes': [],
                    'mensagem': 'Produto não possui BOM ou é comprado'
                })

            # Buscar custos mensais dos componentes
            componentes_com_custo = []

            for comp in bom.get('componentes', []):
                cod_comp = comp.get('cod_produto')

                # Buscar custo mensal do componente
                custo_comp = CustoMensal.query.filter_by(
                    cod_produto=cod_comp,
                    mes=mes,
                    ano=ano
                ).first()

                qtd_utilizada = comp.get('qtd_necessaria', 0)

                # Determinar custo unitário e total
                custo_unitario = None
                if custo_comp:
                    # Prioridade: BOM > Custo Médio Estoque > Último Custo > Custo Líquido Médio
                    if custo_comp.custo_bom:
                        custo_unitario = float(custo_comp.custo_bom)
                    elif custo_comp.custo_medio_estoque:
                        custo_unitario = float(custo_comp.custo_medio_estoque)
                    elif custo_comp.ultimo_custo:
                        custo_unitario = float(custo_comp.ultimo_custo)
                    elif custo_comp.custo_liquido_medio:
                        custo_unitario = float(custo_comp.custo_liquido_medio)

                custo_total = custo_unitario * qtd_utilizada if custo_unitario else None

                componentes_com_custo.append({
                    'cod_produto': cod_comp,
                    'nome_produto': comp.get('nome_produto', ''),
                    'tipo': comp.get('tipo', 'COMPONENTE'),
                    'nivel': comp.get('nivel', 1),
                    'qtd_utilizada': round(qtd_utilizada, 4),
                    'custo_unitario': round(custo_unitario, 4) if custo_unitario else None,
                    'custo_total': round(custo_total, 4) if custo_total else None,
                    'tem_bom': len(comp.get('componentes', [])) > 0
                })

            # Calcular custo BOM total
            custo_bom_total = sum(c['custo_total'] or 0 for c in componentes_com_custo)

            return jsonify({
                'sucesso': True,
                'cod_produto': cod_produto,
                'nome_produto': custo_pai.nome_produto,
                'tipo': custo_pai.tipo_produto,
                'custo_bom_calculado': round(custo_bom_total, 4),
                'custo_bom_registrado': float(custo_pai.custo_bom) if custo_pai.custo_bom else None,
                'componentes': componentes_com_custo
            })

        except Exception as e:
            logger.error(f"Erro ao buscar detalhe BOM: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - CUSTO CONSIDERADO
    # ================================================

    @bp.route('/api/considerado/listar') #type: ignore
    @login_required
    def listar_custos_considerados():
        """Lista custos vigentes"""
        try:
            tipo_produto = request.args.get('tipo_produto')
            cod_produto = request.args.get('cod_produto')

            custos = ServicoCusteio.listar_custos_considerados(
                tipo_produto=tipo_produto,
                cod_produto=cod_produto
            )

            return jsonify({
                'sucesso': True,
                'dados': custos,
                'total': len(custos)
            })

        except Exception as e:
            logger.error(f"Erro ao listar custos considerados: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/considerado/alterar-tipo', methods=['POST']) #type: ignore
    @login_required
    def alterar_tipo_custo():
        """Altera o tipo de custo considerado para um produto"""
        try:
            dados = request.json or {}
            cod_produto = dados.get('cod_produto')
            tipo_custo = dados.get('tipo_custo')

            if not cod_produto or not tipo_custo:
                return jsonify({'erro': 'cod_produto e tipo_custo sao obrigatorios'}), 400

            resultado = ServicoCusteio.alterar_tipo_custo(
                cod_produto=cod_produto,
                tipo_custo=tipo_custo,
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            if resultado.get('erro'):
                return jsonify({
                    'sucesso': False,
                    'erro': resultado['erro']
                }), 400

            return jsonify({
                'sucesso': True,
                **resultado
            })

        except Exception as e:
            logger.error(f"Erro ao alterar tipo de custo: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/considerado/cadastrar', methods=['POST']) #type: ignore
    @login_required
    def cadastrar_custo_considerado():
        """Cadastra ou atualiza custo considerado manualmente"""
        try:
            dados = request.json or {}
            cod_produto = dados.get('cod_produto')
            custo_considerado = dados.get('custo_considerado')
            custo_producao = dados.get('custo_producao')
            tipo_custo = dados.get('tipo_custo', 'MEDIO_MES')
            motivo = dados.get('motivo')

            if not cod_produto or custo_considerado is None:
                return jsonify({'erro': 'cod_produto e custo_considerado sao obrigatorios'}), 400

            resultado = ServicoCusteio.cadastrar_custo_manual(
                cod_produto=cod_produto,
                custo_considerado=float(custo_considerado),
                custo_producao=float(custo_producao) if custo_producao else None,
                tipo_custo=tipo_custo,
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema',
                motivo=motivo
            )

            if resultado.get('erro'):
                return jsonify({
                    'sucesso': False,
                    'erro': resultado['erro']
                }), 400

            return jsonify({
                'sucesso': True,
                **resultado,
                'mensagem': f"Custo cadastrado para {cod_produto}"
            })

        except Exception as e:
            logger.error(f"Erro ao cadastrar custo: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/considerado/historico/<cod_produto>') #type: ignore
    @login_required
    def historico_custo(cod_produto):
        """Lista historico de versoes de custo de um produto"""
        try:
            historico = ServicoCusteio.listar_historico_custo(cod_produto)
            return jsonify({
                'sucesso': True,
                'dados': historico,
                'total': len(historico)
            })
        except Exception as e:
            logger.error(f"Erro ao buscar historico: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/produtos/buscar') #type: ignore
    @login_required
    def buscar_produtos_custeio():
        """Busca produtos para cadastro de custo"""
        try:
            from app.producao.models import CadastroPalletizacao

            termo = request.args.get('termo', '')
            if len(termo) < 2:
                return jsonify({'dados': []})

            produtos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                (CadastroPalletizacao.cod_produto.ilike(f'%{termo}%')) |
                (CadastroPalletizacao.nome_produto.ilike(f'%{termo}%'))
            ).limit(20).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto,
                    'tipo': 'COMPRADO' if p.produto_comprado else ('INTERMEDIARIO' if p.produto_produzido and not p.produto_vendido else 'ACABADO')
                } for p in produtos]
            })

        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - EXPORTACAO
    # ================================================

    @bp.route('/api/exportar-excel') #type: ignore
    @login_required
    def exportar_excel():
        """Exporta custos para Excel"""
        try:
            import pandas as pd

            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)
            tipo = request.args.get('tipo', 'mensal')  # mensal ou considerado

            if tipo == 'mensal':
                if not mes or not ano:
                    return jsonify({'erro': 'Mes e ano sao obrigatorios para exportacao mensal'}), 400

                custos = ServicoCusteio.listar_custos_mensais(mes=mes, ano=ano)
                nome_arquivo = f'custos_mensais_{mes:02d}_{ano}.xlsx'

                # Preparar dados para Excel
                dados_excel = []
                for c in custos:
                    dados_excel.append({
                        'Codigo': c['cod_produto'],
                        'Nome': c['nome_produto'],
                        'Tipo': c['tipo_produto'],
                        'Custo Liquido Medio': c['custo_liquido_medio'],
                        'Ultimo Custo': c['ultimo_custo'],
                        'Custo Medio Estoque': c['custo_medio_estoque'],
                        'Custo BOM': c['custo_bom'],
                        'Qtd Estoque Inicial': c['qtd_estoque_inicial'],
                        'Custo Estoque Inicial': c['custo_estoque_inicial'],
                        'Qtd Comprada': c['qtd_comprada'],
                        'Valor Compras Bruto': c['valor_compras_bruto'],
                        'ICMS': c['valor_icms'],
                        'PIS': c['valor_pis'],
                        'COFINS': c['valor_cofins'],
                        'Valor Compras Liquido': c['valor_compras_liquido'],
                        'Qtd Estoque Final': c['qtd_estoque_final'],
                        'Custo Estoque Final': c['custo_estoque_final'],
                        'Status': c['status']
                    })

            else:  # considerado
                custos = ServicoCusteio.listar_custos_considerados()
                nome_arquivo = 'custos_considerados.xlsx'

                dados_excel = []
                for c in custos:
                    dados_excel.append({
                        'Codigo': c['cod_produto'],
                        'Nome': c['nome_produto'],
                        'Tipo': c['tipo_produto'],
                        'Custo Medio Mes': c['custo_medio_mes'],
                        'Ultimo Custo': c['ultimo_custo'],
                        'Custo Medio Estoque': c['custo_medio_estoque'],
                        'Custo BOM': c['custo_bom'],
                        'Tipo Selecionado': c['tipo_custo_selecionado'],
                        'Custo Considerado': c['custo_considerado'],
                        'Qtd Estoque Inicial': c['qtd_estoque_inicial'],
                        'Custo Estoque Inicial': c['custo_estoque_inicial'],
                        'Qtd Comprada': c['qtd_comprada_periodo'],
                        'Custo Compras': c['custo_compras_periodo'],
                        'Qtd Estoque Final': c['qtd_estoque_final'],
                        'Custo Estoque Final': c['custo_estoque_final'],
                        'Ultimo Fechamento': f"{c['ultimo_mes_fechado']}/{c['ultimo_ano_fechado']}" if c['ultimo_mes_fechado'] else ''
                    })

            # Criar Excel
            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Custos')

                # Ajustar largura das colunas
                worksheet = writer.sheets['Custos']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas nao instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao exportar Excel: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - ESTATISTICAS
    # ================================================

    @bp.route('/api/estatisticas') #type: ignore
    @login_required
    def estatisticas():
        """Retorna estatisticas gerais de custeio"""
        try:
            from app.custeio.models import CustoMensal, CustoConsiderado
            from sqlalchemy import func

            # Total de produtos com custo
            total_considerados = CustoConsiderado.query.count()

            # Por tipo
            por_tipo = {}
            tipos = CustoConsiderado.query.with_entities(
                CustoConsiderado.tipo_produto,
                func.count(CustoConsiderado.id)
            ).group_by(CustoConsiderado.tipo_produto).all()

            for tipo, qtd in tipos:
                por_tipo[tipo] = qtd

            # Ultimo fechamento
            ultimo = CustoMensal.query.filter_by(
                status='FECHADO'
            ).order_by(
                CustoMensal.ano.desc(),
                CustoMensal.mes.desc()
            ).first()

            ultimo_fechamento = None
            if ultimo:
                ultimo_fechamento = {
                    'mes': ultimo.mes,
                    'ano': ultimo.ano,
                    'data': ultimo.fechado_em.strftime('%d/%m/%Y %H:%M') if ultimo.fechado_em else None
                }

            return jsonify({
                'sucesso': True,
                'total_produtos': total_considerados,
                'por_tipo': por_tipo,
                'ultimo_fechamento': ultimo_fechamento
            })

        except Exception as e:
            logger.error(f"Erro ao buscar estatisticas: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - CUSTO FRETE
    # ================================================

    @bp.route('/api/frete/listar') #type: ignore
    @login_required
    def listar_custos_frete():
        """Lista tabela de custo de frete por incoterm/UF"""
        try:
            from app.custeio.models import CustoFrete
            from datetime import date

            incoterm = request.args.get('incoterm')
            cod_uf = request.args.get('cod_uf')
            apenas_vigentes = request.args.get('apenas_vigentes', 'true').lower() == 'true'

            query = CustoFrete.query

            if incoterm:
                query = query.filter(CustoFrete.incoterm == incoterm)
            if cod_uf:
                query = query.filter(CustoFrete.cod_uf == cod_uf)
            if apenas_vigentes:
                hoje = date.today()
                query = query.filter(
                    CustoFrete.vigencia_inicio <= hoje,
                    (CustoFrete.vigencia_fim.is_(None)) | (CustoFrete.vigencia_fim > hoje)
                )

            custos = query.order_by(CustoFrete.incoterm, CustoFrete.cod_uf).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'id': c.id,
                    'incoterm': c.incoterm,
                    'cod_uf': c.cod_uf,
                    'percentual_frete': float(c.percentual_frete),
                    'vigencia_inicio': c.vigencia_inicio.strftime('%Y-%m-%d') if c.vigencia_inicio else None,
                    'vigencia_fim': c.vigencia_fim.strftime('%Y-%m-%d') if c.vigencia_fim else None,
                    'criado_em': c.criado_em.strftime('%d/%m/%Y %H:%M') if c.criado_em else None,
                    'criado_por': c.criado_por
                } for c in custos],
                'total': len(custos)
            })

        except Exception as e:
            logger.error(f"Erro ao listar custos de frete: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/frete/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_custo_frete():
        """Cria ou atualiza registro de custo de frete"""
        try:
            from app.custeio.models import CustoFrete
            from app import db
            from datetime import datetime

            dados = request.json or {}
            id_registro = dados.get('id')
            incoterm = dados.get('incoterm')
            cod_uf = dados.get('cod_uf')
            percentual = dados.get('percentual_frete')
            vigencia_inicio = dados.get('vigencia_inicio')
            vigencia_fim = dados.get('vigencia_fim')

            if not incoterm or not cod_uf or percentual is None:
                return jsonify({'erro': 'incoterm, cod_uf e percentual_frete são obrigatórios'}), 400

            if id_registro:
                # Atualizar existente
                registro = db.session.get(CustoFrete, id_registro)
                if not registro:
                    return jsonify({'erro': 'Registro não encontrado'}), 404

                registro.incoterm = incoterm
                registro.cod_uf = cod_uf
                registro.percentual_frete = percentual
                registro.vigencia_inicio = datetime.strptime(vigencia_inicio, '%Y-%m-%d').date() if vigencia_inicio else None
                registro.vigencia_fim = datetime.strptime(vigencia_fim, '%Y-%m-%d').date() if vigencia_fim else None
            else:
                # Criar novo
                registro = CustoFrete(
                    incoterm=incoterm,
                    cod_uf=cod_uf,
                    percentual_frete=percentual,
                    vigencia_inicio=datetime.strptime(vigencia_inicio, '%Y-%m-%d').date() if vigencia_inicio else datetime.now().date(),
                    vigencia_fim=datetime.strptime(vigencia_fim, '%Y-%m-%d').date() if vigencia_fim else None,
                    criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                )
                db.session.add(registro)

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': registro.id,
                'mensagem': 'Custo de frete salvo com sucesso'
            })

        except Exception as e:
            logger.error(f"Erro ao salvar custo de frete: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/frete/excluir/<int:id_registro>', methods=['DELETE']) #type: ignore
    @login_required
    def excluir_custo_frete(id_registro):
        """Remove registro de custo de frete"""
        try:
            from app.custeio.models import CustoFrete
            from app import db

            registro = db.session.get(CustoFrete, id_registro)
            if not registro:
                return jsonify({'erro': 'Registro não encontrado'}), 404

            db.session.delete(registro)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Registro excluído com sucesso'
            })

        except Exception as e:
            logger.error(f"Erro ao excluir custo de frete: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - PARAMETROS DE CUSTEIO
    # ================================================

    @bp.route('/api/parametros/listar') #type: ignore
    @login_required
    def listar_parametros():
        """Lista todos os parâmetros de custeio"""
        try:
            from app.custeio.models import ParametroCusteio

            parametros = ParametroCusteio.query.order_by(ParametroCusteio.chave).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'id': p.id,
                    'chave': p.chave,
                    'valor': float(p.valor),
                    'descricao': p.descricao,
                    'atualizado_em': p.atualizado_em.strftime('%d/%m/%Y %H:%M') if p.atualizado_em else None,
                    'atualizado_por': p.atualizado_por
                } for p in parametros],
                'total': len(parametros)
            })

        except Exception as e:
            logger.error(f"Erro ao listar parâmetros: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/parametros/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_parametro():
        """Cria ou atualiza parâmetro de custeio"""
        try:
            from app.custeio.models import ParametroCusteio
            from app import db
            from datetime import datetime

            dados = request.json or {}
            id_registro = dados.get('id')
            chave = dados.get('chave')
            valor = dados.get('valor')
            descricao = dados.get('descricao')

            if not chave or valor is None:
                return jsonify({'erro': 'chave e valor são obrigatórios'}), 400

            if id_registro:
                # Atualizar existente
                registro = db.session.get(ParametroCusteio, id_registro)
                if not registro:
                    return jsonify({'erro': 'Parâmetro não encontrado'}), 404

                registro.valor = valor
                registro.descricao = descricao
                registro.atualizado_em = datetime.utcnow()
                registro.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            else:
                # Verificar se chave já existe - atualizar se existir
                existente = ParametroCusteio.query.filter_by(chave=chave).first()
                if existente:
                    # Atualizar registro existente
                    existente.valor = valor
                    existente.descricao = descricao
                    existente.atualizado_em = datetime.utcnow()
                    existente.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                    registro = existente
                else:
                    # Criar novo registro
                    registro = ParametroCusteio(
                        chave=chave,
                        valor=valor,
                        descricao=descricao,
                        atualizado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                    )
                    db.session.add(registro)

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': registro.id,
                'mensagem': 'Parâmetro salvo com sucesso'
            })

        except Exception as e:
            logger.error(f"Erro ao salvar parâmetro: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/parametros/obter/<chave>') #type: ignore
    @login_required
    def obter_parametro(chave):
        """Obtém valor de um parâmetro específico"""
        try:
            from app.custeio.models import ParametroCusteio

            parametro = ParametroCusteio.query.filter_by(chave=chave).first()

            if not parametro:
                return jsonify({'erro': f'Parâmetro {chave} não encontrado'}), 404

            return jsonify({
                'sucesso': True,
                'chave': parametro.chave,
                'valor': float(parametro.valor),
                'descricao': parametro.descricao
            })

        except Exception as e:
            logger.error(f"Erro ao obter parâmetro: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/parametros/excluir/<int:id_param>', methods=['DELETE']) #type: ignore
    @login_required
    def excluir_parametro(id_param):
        """Exclui um parâmetro de custeio"""
        try:
            from app.custeio.models import ParametroCusteio
            from app import db

            parametro = db.session.get(ParametroCusteio, id_param)
            if not parametro:
                return jsonify({'erro': 'Parâmetro não encontrado'}), 404

            db.session.delete(parametro)
            db.session.commit()

            return jsonify({'sucesso': True, 'mensagem': 'Parâmetro excluído'})

        except Exception as e:
            logger.error(f"Erro ao excluir parâmetro: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/parametros/modelo') #type: ignore
    @login_required
    def modelo_parametros():
        """Gera modelo Excel para importação de parâmetros"""
        try:
            import pandas as pd

            dados = [
                {'Chave': 'CUSTO_OPERACAO_PERCENTUAL', 'Valor': 5.0, 'Descricao': 'Custo operacional sobre preco'},
                {'Chave': 'MARGEM_MINIMA_PERCENTUAL', 'Valor': 10.0, 'Descricao': 'Alerta de margem baixa'},
            ]

            df = pd.DataFrame(dados)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Modelo')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='modelo_parametros.xlsx'
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao gerar modelo: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # EXPORTAÇÃO E IMPORTAÇÃO - CUSTO FRETE
    # ================================================

    @bp.route('/api/frete/exportar') #type: ignore
    @login_required
    def exportar_custos_frete():
        """Exporta tabela de custo de frete para Excel"""
        try:
            import pandas as pd
            from app.custeio.models import CustoFrete

            custos = CustoFrete.query.order_by(CustoFrete.incoterm, CustoFrete.cod_uf).all()

            dados_excel = []
            for c in custos:
                dados_excel.append({
                    'Incoterm': c.incoterm,
                    'UF': c.cod_uf,
                    'Percentual Frete (%)': float(c.percentual_frete) if c.percentual_frete else 0,
                    'Vigência Início': c.vigencia_inicio.strftime('%Y-%m-%d') if c.vigencia_inicio else '',
                    'Vigência Fim': c.vigencia_fim.strftime('%Y-%m-%d') if c.vigencia_fim else '',
                    'Criado Por': c.criado_por or ''
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Custo Frete')

                worksheet = writer.sheets['Custo Frete']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 30)

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='custo_frete.xlsx'
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao exportar custos de frete: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/frete/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_custos_frete():
        """Importa custos de frete de arquivo Excel"""
        try:
            import pandas as pd
            from app.custeio.models import CustoFrete
            from app import db

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            if arquivo.filename == '':
                return jsonify({'erro': 'Nome do arquivo vazio'}), 400

            if not arquivo.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'erro': 'Formato inválido. Use .xlsx ou .xls'}), 400

            # Ler Excel
            df = pd.read_excel(arquivo)

            # Validar colunas obrigatórias
            colunas_obrigatorias = ['Incoterm', 'UF', 'Percentual Frete (%)']
            colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
            if colunas_faltando:
                return jsonify({'erro': f'Colunas obrigatórias faltando: {colunas_faltando}'}), 400

            inseridos = 0
            atualizados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    incoterm = str(row['Incoterm']).strip().upper()
                    cod_uf = str(row['UF']).strip().upper()
                    percentual = float(row['Percentual Frete (%)'])

                    # Vigência início
                    vigencia_inicio = row.get('Vigência Início')
                    if pd.isna(vigencia_inicio) or vigencia_inicio == '':
                        vigencia_inicio = datetime.now().date()
                    elif isinstance(vigencia_inicio, str):
                        vigencia_inicio = datetime.strptime(vigencia_inicio, '%Y-%m-%d').date()
                    else:
                        vigencia_inicio = pd.to_datetime(vigencia_inicio).date()

                    # Vigência fim
                    vigencia_fim = row.get('Vigência Fim')
                    if pd.isna(vigencia_fim) or vigencia_fim == '':
                        vigencia_fim = None
                    elif isinstance(vigencia_fim, str):
                        vigencia_fim = datetime.strptime(vigencia_fim, '%Y-%m-%d').date()
                    else:
                        vigencia_fim = pd.to_datetime(vigencia_fim).date()

                    # Verificar se já existe
                    existente = CustoFrete.query.filter_by(
                        incoterm=incoterm,
                        cod_uf=cod_uf,
                        vigencia_inicio=vigencia_inicio
                    ).first()

                    if existente:
                        existente.percentual_frete = percentual
                        existente.vigencia_fim = vigencia_fim
                        atualizados += 1
                    else:
                        novo = CustoFrete(
                            incoterm=incoterm,
                            cod_uf=cod_uf,
                            percentual_frete=percentual,
                            vigencia_inicio=vigencia_inicio,
                            vigencia_fim=vigencia_fim,
                            criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        )
                        db.session.add(novo)
                        inseridos += 1

                except Exception as e:
                    erros.append(f"Linha {idx + 2}: {str(e)}") # type: ignore

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'inseridos': inseridos,
                'atualizados': atualizados,
                'erros': erros[:10] if erros else [],
                'mensagem': f'{inseridos} inseridos, {atualizados} atualizados' + (f', {len(erros)} erros' if erros else '')
            })

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao importar custos de frete: {e}")
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/frete/modelo') #type: ignore
    @login_required
    def modelo_frete():
        """Gera modelo Excel para importação de custo de frete"""
        try:
            import pandas as pd

            dados = [
                {'Incoterm': 'CIF', 'UF': 'SP', 'Percentual Frete (%)': 5.00, 'Vigência Início': '2025-01-01', 'Vigência Fim': ''},
                {'Incoterm': 'CIF', 'UF': 'RJ', 'Percentual Frete (%)': 6.50, 'Vigência Início': '2025-01-01', 'Vigência Fim': ''},
                {'Incoterm': 'FOB', 'UF': 'SP', 'Percentual Frete (%)': 0.00, 'Vigência Início': '2025-01-01', 'Vigência Fim': ''},
            ]

            df = pd.DataFrame(dados)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Modelo')

                worksheet = writer.sheets['Modelo']
                for idx, col in enumerate(df.columns):
                    worksheet.column_dimensions[chr(65 + idx)].width = 20

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='modelo_custo_frete.xlsx'
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao gerar modelo: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # EXPORTAÇÃO E IMPORTAÇÃO - PARAMETROS
    # ================================================

    @bp.route('/api/parametros/exportar') #type: ignore
    @login_required
    def exportar_parametros():
        """Exporta parâmetros de custeio para Excel"""
        try:
            import pandas as pd
            from app.custeio.models import ParametroCusteio

            parametros = ParametroCusteio.query.order_by(ParametroCusteio.chave).all()

            dados_excel = []
            for p in parametros:
                dados_excel.append({
                    'Chave': p.chave,
                    'Valor': float(p.valor) if p.valor else 0,
                    'Descrição': p.descricao or ''
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Parâmetros')

                worksheet = writer.sheets['Parâmetros']
                worksheet.column_dimensions['A'].width = 35
                worksheet.column_dimensions['B'].width = 15
                worksheet.column_dimensions['C'].width = 50

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='parametros_custeio.xlsx'
            )

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao exportar parâmetros: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/parametros/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_parametros():
        """Importa parâmetros de custeio de arquivo Excel"""
        try:
            import pandas as pd
            from app.custeio.models import ParametroCusteio
            from app import db
            from datetime import datetime

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            if arquivo.filename == '':
                return jsonify({'erro': 'Nome do arquivo vazio'}), 400

            if not arquivo.filename.endswith(('.xlsx', '.xls')):
                return jsonify({'erro': 'Formato inválido. Use .xlsx ou .xls'}), 400

            df = pd.read_excel(arquivo)

            colunas_obrigatorias = ['Chave', 'Valor']
            colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
            if colunas_faltando:
                return jsonify({'erro': f'Colunas obrigatórias faltando: {colunas_faltando}'}), 400

            inseridos = 0
            atualizados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    chave = str(row['Chave']).strip().upper()
                    valor = float(row['Valor'])
                    descricao = str(row.get('Descrição', '')) if not pd.isna(row.get('Descrição')) else ''

                    existente = ParametroCusteio.query.filter_by(chave=chave).first()

                    if existente:
                        existente.valor = valor
                        existente.descricao = descricao
                        existente.atualizado_em = datetime.utcnow()
                        existente.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        atualizados += 1
                    else:
                        novo = ParametroCusteio(
                            chave=chave,
                            valor=valor,
                            descricao=descricao,
                            atualizado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        )
                        db.session.add(novo)
                        inseridos += 1

                except Exception as e:
                    erros.append(f"Linha {idx + 2}: {str(e)}") # type: ignore

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'inseridos': inseridos,
                'atualizados': atualizados,
                'erros': erros[:10] if erros else [],
                'mensagem': f'{inseridos} inseridos, {atualizados} atualizados' + (f', {len(erros)} erros' if erros else '')
            })

        except ImportError:
            return jsonify({'erro': 'Biblioteca pandas não instalada'}), 500
        except Exception as e:
            logger.error(f"Erro ao importar parâmetros: {e}")
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - CUSTO PRODUCAO
    # ================================================

    @bp.route('/api/producao/listar') #type: ignore 
    @login_required
    def listar_producao():
        """Lista produtos produzidos com capacidade e linha de producao"""
        try:
            from app.producao.models import CadastroPalletizacao
            from app.manufatura.models import RecursosProducao
            from app.custeio.models import CustoConsiderado

            filtro_tipo = request.args.get('tipo')  # 'intermediario' ou 'acabado'

            # Buscar produtos produzidos
            query = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True
            )

            if filtro_tipo == 'intermediario':
                query = query.filter(
                    CadastroPalletizacao.produto_vendido == False
                )
            elif filtro_tipo == 'acabado':
                query = query.filter(
                    CadastroPalletizacao.produto_vendido == True
                )

            produtos = query.order_by(CadastroPalletizacao.cod_produto).all()

            # Buscar recursos de producao
            recursos = {}
            for r in RecursosProducao.query.all():
                if r.cod_produto not in recursos:
                    recursos[r.cod_produto] = []
                recursos[r.cod_produto].append({
                    'linha': r.linha_producao,
                    'capacidade': float(r.capacidade_unidade_minuto) if r.capacidade_unidade_minuto else None,
                    'lote_ideal': float(r.qtd_lote_ideal) if r.qtd_lote_ideal else None,
                    'eficiencia': float(r.eficiencia_media) if r.eficiencia_media else None
                })

            # Buscar custos com versão e datas
            custos = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else None,
                    'custo_producao': float(c.custo_producao) if c.custo_producao else None,
                    'versao': c.versao,
                    'vigencia_inicio': c.vigencia_inicio.strftime('%d/%m/%Y %H:%M') if c.vigencia_inicio else None,
                    'atualizado_em': c.atualizado_em.strftime('%d/%m/%Y %H:%M') if c.atualizado_em else None,
                    'atualizado_por': c.atualizado_por
                }

            dados = []
            for p in produtos:
                tipo = 'ACABADO' if p.produto_vendido else 'INTERMEDIARIO'
                rec = recursos.get(p.cod_produto, [])
                custo = custos.get(p.cod_produto, {})

                dados.append({
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto,
                    'tipo': tipo,
                    'linhas_producao': rec,
                    'custo_considerado': custo.get('custo_considerado'),
                    'custo_producao': custo.get('custo_producao'),
                    'versao': custo.get('versao'),
                    'vigencia_inicio': custo.get('vigencia_inicio'),
                    'atualizado_em': custo.get('atualizado_em'),
                    'atualizado_por': custo.get('atualizado_por')
                })

            return jsonify({
                'sucesso': True,
                'dados': dados,
                'total': len(dados)
            })

        except Exception as e:
            logger.error(f"Erro ao listar producao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/producao/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_custo_producao():
        """Salva custo de producao para um produto"""
        try:
            dados = request.json or {}
            cod_produto = dados.get('cod_produto')
            custo_producao = dados.get('custo_producao')

            if not cod_produto:
                return jsonify({'erro': 'cod_produto e obrigatorio'}), 400

            resultado = ServicoCusteio.cadastrar_custo_manual(
                cod_produto=cod_produto,
                custo_considerado=None,  # Nao alterar custo considerado
                custo_producao=float(custo_producao) if custo_producao else None,
                tipo_custo='PRODUCAO',
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema',
                motivo='Custo de producao cadastrado'
            )

            if resultado.get('erro'):
                return jsonify({'sucesso': False, 'erro': resultado['erro']}), 400

            return jsonify({'sucesso': True, 'mensagem': f'Custo de producao salvo para {cod_produto}'})

        except Exception as e:
            logger.error(f"Erro ao salvar custo producao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/producao/exportar') #type: ignore
    @login_required
    def exportar_producao():
        """Exporta custos de producao para Excel"""
        try:
            import pandas as pd
            from app.producao.models import CadastroPalletizacao
            from app.manufatura.models import RecursosProducao
            from app.custeio.models import CustoConsiderado

            produtos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True
            ).order_by(CadastroPalletizacao.cod_produto).all()

            recursos = {}
            for r in RecursosProducao.query.all():
                if r.cod_produto not in recursos:
                    recursos[r.cod_produto] = r.linha_producao

            custos = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else 0,
                    'custo_producao': float(c.custo_producao) if c.custo_producao else 0
                }

            dados_excel = []
            for p in produtos:
                tipo = 'ACABADO' if p.produto_vendido else 'INTERMEDIARIO'
                custo = custos.get(p.cod_produto, {})
                dados_excel.append({
                    'Codigo': p.cod_produto,
                    'Nome': p.nome_produto,
                    'Tipo': tipo,
                    'Linha Producao': recursos.get(p.cod_produto, ''),
                    'Custo Considerado': custo.get('custo_considerado', 0),
                    'Custo Producao': custo.get('custo_producao', 0)
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Custo Producao')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='custo_producao.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao exportar producao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/producao/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_producao(): 
        """Importa custos de producao de arquivo Excel"""
        try:
            import pandas as pd

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            df = pd.read_excel(arquivo)

            colunas_obrigatorias = ['Codigo', 'Custo Producao']
            colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
            if colunas_faltando:
                return jsonify({'erro': f'Colunas faltando: {colunas_faltando}'}), 400

            atualizados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    cod_produto = str(row['Codigo']).strip()
                    custo_producao = float(row['Custo Producao']) if not pd.isna(row['Custo Producao']) else None

                    if custo_producao is not None:
                        resultado = ServicoCusteio.cadastrar_custo_manual(
                            cod_produto=cod_produto,
                            custo_considerado=None,
                            custo_producao=custo_producao,
                            tipo_custo='PRODUCAO',
                            usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema',
                            motivo='Importacao via Excel'
                        )
                        if not resultado.get('erro'):
                            atualizados += 1

                except Exception as e:
                    erros.append(f"Linha {idx + 2}: {str(e)}") # type: ignore

            return jsonify({
                'sucesso': True,
                'atualizados': atualizados,
                'erros': erros[:10],
                'mensagem': f'{atualizados} atualizados' + (f', {len(erros)} erros' if erros else '')
            })

        except Exception as e:
            logger.error(f"Erro ao importar producao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/producao/modelo') #type: ignore
    @login_required
    def modelo_producao():
        """Gera modelo Excel para importacao de custo de producao"""
        try:
            import pandas as pd

            dados = [
                {'Codigo': '101000001', 'Nome': 'Produto Exemplo', 'Custo Producao': 10.50},
            ]

            df = pd.DataFrame(dados)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Modelo')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='modelo_custo_producao.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao gerar modelo producao: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - DEFINICAO DE CUSTO CONSIDERADO
    # ================================================

    @bp.route('/api/definicao/listar') #type: ignore
    @login_required
    def listar_definicao():
        """Lista produtos com custos para definicao (calcula dinamicamente para comprados, BOM para produzidos)"""
        try:
            from app.producao.models import CadastroPalletizacao
            from app.custeio.models import CustoConsiderado
            from app.manufatura.models import ListaMateriais
            from app.custeio.services.custeio_service import ServicoCusteio
            from datetime import date

            filtro_tipo = request.args.get('tipo')
            termo = request.args.get('termo', '')

            query = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True
            )

            if filtro_tipo == 'comprado':
                query = query.filter(CadastroPalletizacao.produto_comprado == True)
            elif filtro_tipo == 'produzido':
                query = query.filter(CadastroPalletizacao.produto_produzido == True)

            if termo:
                query = query.filter(
                    (CadastroPalletizacao.cod_produto.ilike(f'%{termo}%')) |
                    (CadastroPalletizacao.nome_produto.ilike(f'%{termo}%'))
                )

            produtos = query.order_by(CadastroPalletizacao.cod_produto).all()

            # Determinar periodo de referencia (mes atual)
            hoje = date.today()
            mes_ref = hoje.month
            ano_ref = hoje.year

            # Buscar custo_considerado (definido manualmente) e tipo_custo do banco
            custos_considerados_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_considerados_dict[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else None,
                    'tipo_custo': c.tipo_custo_selecionado,
                    'ultimo_mes_fechado': c.ultimo_mes_fechado,
                    'ultimo_ano_fechado': c.ultimo_ano_fechado
                }

            # Identificar produtos comprados para calculo dinamico
            produtos_comprados = set(
                p.cod_produto for p in produtos if p.produto_comprado
            )

            # Cache de custos calculados dinamicamente para COMPRADOS
            custos_dinamicos_dict = {}
            for cod_produto in produtos_comprados:
                # Determinar periodo baseado no ultimo fechamento ou mes atual
                custo_info = custos_considerados_dict.get(cod_produto, {})
                mes_calc = custo_info.get('ultimo_mes_fechado') or mes_ref
                ano_calc = custo_info.get('ultimo_ano_fechado') or ano_ref

                # Calcular dinamicamente usando o servico (mesma logica do modal)
                custos_calc = ServicoCusteio.calcular_custo_comprados(cod_produto, mes_calc, ano_calc)
                custos_dinamicos_dict[cod_produto] = {
                    'custo_medio_mes': custos_calc.get('custo_liquido_medio'),
                    'ultimo_custo': custos_calc.get('ultimo_custo'),
                    'custo_medio_estoque': custos_calc.get('custo_medio_estoque')
                }

            # Identificar produtos com BOM (são produzidos)
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo').with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            # Cache de BOMs para evitar queries repetidas
            bom_cache = {}
            for bom in ListaMateriais.query.filter_by(status='ativo').all():
                if bom.cod_produto_produzido not in bom_cache:
                    bom_cache[bom.cod_produto_produzido] = []
                bom_cache[bom.cod_produto_produzido].append({
                    'cod_componente': bom.cod_produto_componente,
                    'qtd': float(bom.qtd_utilizada) if bom.qtd_utilizada else 0
                })

            def calcular_custo_bom(cod, campo_custo, visitados=None):
                """Calcula custo de um produto via BOM recursivamente usando custos dinamicos"""
                if visitados is None:
                    visitados = set()

                if cod in visitados:
                    return None  # Evitar loop infinito

                # Se nao tem BOM (folha = COMPRADO), usar custo dinamico ou considerado
                if cod not in produtos_com_bom:
                    if campo_custo == 'custo_considerado':
                        return custos_considerados_dict.get(cod, {}).get('custo_considerado')
                    else:
                        return custos_dinamicos_dict.get(cod, {}).get(campo_custo)

                # Tem BOM - calcular recursivamente
                visitados.add(cod)
                componentes = bom_cache.get(cod, [])

                custo_total = 0
                for comp in componentes:
                    custo_comp = calcular_custo_bom(comp['cod_componente'], campo_custo, visitados.copy())
                    if custo_comp is not None:
                        custo_total += custo_comp * comp['qtd']

                return custo_total if custo_total > 0 else None

            dados = []
            for p in produtos:
                tipo = 'COMPRADO' if p.produto_comprado else ('INTERMEDIARIO' if p.produto_produzido and not p.produto_vendido else 'ACABADO')
                custo_considerado_info = custos_considerados_dict.get(p.cod_produto, {})
                custo_dinamico_info = custos_dinamicos_dict.get(p.cod_produto, {})

                # Para produtos produzidos, calcular TODOS os custos via BOM (incluindo custo_considerado)
                if tipo in ('INTERMEDIARIO', 'ACABADO'):
                    custo_medio_mes = calcular_custo_bom(p.cod_produto, 'custo_medio_mes')
                    ultimo_custo = calcular_custo_bom(p.cod_produto, 'ultimo_custo')
                    custo_medio_estoque = calcular_custo_bom(p.cod_produto, 'custo_medio_estoque')
                    custo_considerado = calcular_custo_bom(p.cod_produto, 'custo_considerado')
                else:
                    # COMPRADO: usar custos calculados dinamicamente + custo_considerado do banco
                    custo_medio_mes = custo_dinamico_info.get('custo_medio_mes')
                    ultimo_custo = custo_dinamico_info.get('ultimo_custo')
                    custo_medio_estoque = custo_dinamico_info.get('custo_medio_estoque')
                    custo_considerado = custo_considerado_info.get('custo_considerado')

                dados.append({
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto,
                    'tipo': tipo,
                    'custo_considerado': custo_considerado,
                    'custo_medio_mes': custo_medio_mes,
                    'ultimo_custo': ultimo_custo,
                    'custo_medio_estoque': custo_medio_estoque,
                    'tipo_custo': custo_considerado_info.get('tipo_custo')
                })

            return jsonify({
                'sucesso': True,
                'dados': dados,
                'total': len(dados)
            })

        except Exception as e:
            logger.error(f"Erro ao listar definicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/bom/<cod_produto>') #type: ignore
    @login_required
    def detalhe_bom_por_criterio(cod_produto):
        """
        Retorna composição BOM com TODOS os 4 tipos de custo para cada componente.
        O parâmetro 'criterio' indica qual custo deve ser destacado visualmente.
        Custos sao calculados dinamicamente para garantir consistencia com o modal.
        """
        try:
            from app.manufatura.models import ListaMateriais
            from app.custeio.models import CustoConsiderado
            from app.custeio.services.custeio_service import ServicoCusteio
            from app.producao.models import CadastroPalletizacao
            from datetime import date

            criterio_selecionado = request.args.get('criterio', 'custo_considerado')

            # Lista de todos os tipos de custo
            TIPOS_CUSTO = ['custo_medio_mes', 'ultimo_custo', 'custo_medio_estoque', 'custo_considerado']

            # Determinar periodo de referencia
            hoje = date.today()
            mes_ref = hoje.month
            ano_ref = hoje.year

            # Buscar custo_considerado do banco (e definido manualmente)
            custos_considerados_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_considerados_dict[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else None,
                    'ultimo_mes_fechado': c.ultimo_mes_fechado,
                    'ultimo_ano_fechado': c.ultimo_ano_fechado
                }

            # Identificar produtos comprados
            produtos_comprados = set(
                p.cod_produto for p in
                CadastroPalletizacao.query.filter_by(ativo=True, produto_comprado=True).all()
            )

            # Cache de custos dinamicos para COMPRADOS
            custos_dinamicos_dict = {}

            def obter_custo_dinamico(cod):
                """Obtem custos calculados dinamicamente para um COMPRADO"""
                if cod not in custos_dinamicos_dict and cod in produtos_comprados:
                    custo_info = custos_considerados_dict.get(cod, {})
                    mes_calc = custo_info.get('ultimo_mes_fechado') or mes_ref
                    ano_calc = custo_info.get('ultimo_ano_fechado') or ano_ref
                    custos_calc = ServicoCusteio.calcular_custo_comprados(cod, mes_calc, ano_calc)
                    custos_dinamicos_dict[cod] = {
                        'custo_medio_mes': custos_calc.get('custo_liquido_medio'),
                        'ultimo_custo': custos_calc.get('ultimo_custo'),
                        'custo_medio_estoque': custos_calc.get('custo_medio_estoque'),
                        'custo_considerado': custos_considerados_dict.get(cod, {}).get('custo_considerado')
                    }
                return custos_dinamicos_dict.get(cod, {})

            # Buscar produtos com BOM (são intermediários)
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo').with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            def calcular_custo_recursivo(cod, criterio_campo, visitados=None):
                """Calcula custo de um produto recursivamente via BOM usando custos dinamicos"""
                if visitados is None:
                    visitados = set()

                if cod in visitados:
                    return None

                # Se nao tem BOM (folha = COMPRADO), usar custo dinamico
                if cod not in produtos_com_bom:
                    custo_info = obter_custo_dinamico(cod)
                    return custo_info.get(criterio_campo)

                visitados.add(cod)
                componentes = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod,
                    status='ativo'
                ).all()

                custo_total = 0
                for comp in componentes:
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    custo_comp = calcular_custo_recursivo(comp.cod_produto_componente, criterio_campo, visitados.copy())
                    if custo_comp is not None:
                        custo_total += custo_comp * qtd

                return custo_total if custo_total > 0 else None

            def calcular_todos_custos(cod_comp, qtd, e_intermediario):
                """Calcula todos os 4 tipos de custo para um componente usando custos dinamicos"""
                custos = {}
                for tipo in TIPOS_CUSTO:
                    if e_intermediario:
                        custo_unit = calcular_custo_recursivo(cod_comp, tipo, set())
                    else:
                        # COMPRADO: usar custo dinamico calculado
                        custo_info = obter_custo_dinamico(cod_comp)
                        custo_unit = custo_info.get(tipo)

                    custo_total = (custo_unit * qtd) if custo_unit else None

                    # Mapear nome interno para nome da API
                    nome_api = {
                        'custo_medio_mes': 'medio_mes',
                        'ultimo_custo': 'ultimo_custo',
                        'custo_medio_estoque': 'medio_estoque',
                        'custo_considerado': 'custo_considerado'
                    }.get(tipo, tipo)

                    custos[nome_api] = {
                        'unitario': round(custo_unit, 4) if custo_unit else None,
                        'total': round(custo_total, 4) if custo_total else None
                    }
                return custos

            def expandir_bom_completo(cod, nivel=0, visitados=None):
                """Expande BOM e retorna componentes com TODOS os custos calculados"""
                if visitados is None:
                    visitados = set()

                if cod in visitados or nivel > 5:
                    return []

                visitados.add(cod)

                componentes = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod,
                    status='ativo'
                ).all()

                resultado = []
                for comp in componentes:
                    cod_comp = comp.cod_produto_componente
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    e_intermediario = cod_comp in produtos_com_bom

                    # Calcular TODOS os 4 custos
                    custos = calcular_todos_custos(cod_comp, qtd, e_intermediario)

                    item = {
                        'nivel': nivel,
                        'cod_produto': cod_comp,
                        'nome_produto': comp.nome_produto_componente,
                        'qtd_utilizada': qtd,
                        'tipo': 'INTERMEDIARIO' if e_intermediario else 'COMPRADO',
                        'custos': custos
                    }
                    resultado.append(item)

                    if e_intermediario:
                        sub = expandir_bom_completo(cod_comp, nivel + 1, visitados.copy())
                        resultado.extend(sub)

                return resultado

            composicao = expandir_bom_completo(cod_produto)

            # Calcular totais para cada tipo de custo (apenas nível 0)
            totais = {}
            for tipo_api in ['medio_mes', 'ultimo_custo', 'medio_estoque', 'custo_considerado']:
                total = sum(
                    (c['custos'].get(tipo_api, {}).get('total') or 0)
                    for c in composicao if c['nivel'] == 0
                )
                totais[tipo_api] = round(total, 4) if total > 0 else None

            return jsonify({
                'sucesso': True,
                'cod_produto': cod_produto,
                'criterio_selecionado': criterio_selecionado,
                'componentes': composicao,
                'totais': totais
            })

        except Exception as e:
            logger.error(f"Erro ao buscar BOM por criterio: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/custo-detalhes/<cod_produto>') #type: ignore
    @login_required
    def detalhe_custo_produto(cod_produto):
        """
        Retorna detalhes da fonte de um custo para drill-down no modal.

        Parâmetros:
            tipo: medio_mes | ultimo_custo | medio_estoque | custo_considerado
            historico: true para buscar últimos 90 dias (opcional)

        Retorna dados específicos conforme o tipo:
        - medio_mes/ultimo_custo: Lista de pedidos de compra
        - medio_estoque: Estoque inicial + compras + fórmula
        - custo_considerado: Valor atual + histórico de versões
        """
        try:
            from app import db
            from app.manufatura.models import PedidoCompras
            from app.custeio.models import CustoConsiderado, CustoMensal
            from app.producao.models import CadastroPalletizacao
            from datetime import date, timedelta

            tipo = request.args.get('tipo', 'medio_mes')
            mostrar_historico = request.args.get('historico', 'false').lower() == 'true'

            # Buscar produto
            produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
            nome_produto = produto.nome_produto if produto else cod_produto

            # Buscar custo atual para determinar período de referência
            custo_atual = CustoConsiderado.query.filter_by(
                cod_produto=cod_produto,
                custo_atual=True
            ).first()

            # Determinar período
            hoje = date.today()
            if custo_atual and custo_atual.ultimo_mes_fechado and custo_atual.ultimo_ano_fechado:
                mes_ref = custo_atual.ultimo_mes_fechado
                ano_ref = custo_atual.ultimo_ano_fechado
            else:
                mes_ref = hoje.month
                ano_ref = hoje.year

            # Calcular datas do período
            data_inicio_periodo = date(ano_ref, mes_ref, 1)
            if mes_ref == 12:
                data_fim_periodo = date(ano_ref + 1, 1, 1)
            else:
                data_fim_periodo = date(ano_ref, mes_ref + 1, 1)

            # Se histórico, buscar últimos 90 dias
            if mostrar_historico:
                data_inicio_periodo = hoje - timedelta(days=90)
                data_fim_periodo = hoje + timedelta(days=1)

            # ============================================
            # TIPO: medio_mes ou ultimo_custo
            # ============================================
            if tipo in ['medio_mes', 'ultimo_custo']:
                # Buscar pedidos de compra
                pedidos = PedidoCompras.query.filter(
                    PedidoCompras.cod_produto == cod_produto,
                    PedidoCompras.data_pedido_criacao >= data_inicio_periodo,
                    PedidoCompras.data_pedido_criacao < data_fim_periodo,
                    PedidoCompras.status_odoo.in_(['done', 'purchase']),
                    db.or_(
                        PedidoCompras.tipo_pedido.in_(['compra', 'importacao']),
                        PedidoCompras.tipo_pedido.is_(None)
                    )
                ).order_by(PedidoCompras.data_pedido_criacao.desc()).all()

                # Calcular resumo
                qtd_total = 0
                valor_bruto_total = 0
                icms_total = 0
                pis_total = 0
                cofins_total = 0

                lista_pedidos = []
                for p in pedidos:
                    qtd = float(p.qtd_recebida or p.qtd_produto_pedido or 0)
                    preco = float(p.preco_produto_pedido or 0)
                    valor_bruto = preco * qtd
                    icms = float(p.icms_produto_pedido or 0)
                    pis = float(p.pis_produto_pedido or 0)
                    cofins = float(p.cofins_produto_pedido or 0)
                    valor_liquido = valor_bruto - icms - pis - cofins

                    qtd_total += qtd
                    valor_bruto_total += valor_bruto
                    icms_total += icms
                    pis_total += pis
                    cofins_total += cofins

                    lista_pedidos.append({
                        'num_pedido': p.num_pedido,
                        'fornecedor': p.raz_social or 'N/I',
                        'cnpj': p.cnpj_fornecedor,
                        'data': p.data_pedido_criacao.strftime('%d/%m/%Y') if p.data_pedido_criacao else None,
                        'numero_nf': p.numero_nf or p.nf_numero,
                        'qtd_recebida': qtd,
                        'preco_unitario': preco,
                        'valor_bruto': round(valor_bruto, 2),
                        'icms': round(icms, 2),
                        'pis': round(pis, 2),
                        'cofins': round(cofins, 2),
                        'valor_liquido': round(valor_liquido, 2)
                    })

                valor_liquido_total = valor_bruto_total - icms_total - pis_total - cofins_total
                custo_medio = valor_liquido_total / qtd_total if qtd_total > 0 else 0

                return jsonify({
                    'sucesso': True,
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'tipo': tipo,
                    'periodo': {
                        'mes': mes_ref,
                        'ano': ano_ref,
                        'historico': mostrar_historico,
                        'data_inicio': data_inicio_periodo.strftime('%d/%m/%Y'),
                        'data_fim': (data_fim_periodo - timedelta(days=1)).strftime('%d/%m/%Y')
                    },
                    'resumo': {
                        'qtd_pedidos': len(pedidos),
                        'qtd_comprada': round(qtd_total, 3),
                        'valor_bruto': round(valor_bruto_total, 2),
                        'icms': round(icms_total, 2),
                        'pis': round(pis_total, 2),
                        'cofins': round(cofins_total, 2),
                        'valor_liquido': round(valor_liquido_total, 2),
                        'custo_medio': round(custo_medio, 4)
                    },
                    'pedidos': lista_pedidos
                })

            # ============================================
            # TIPO: medio_estoque
            # ============================================
            elif tipo == 'medio_estoque':
                # Buscar estoque inicial (do mês anterior)
                mes_anterior = mes_ref - 1 if mes_ref > 1 else 12
                ano_anterior = ano_ref if mes_ref > 1 else ano_ref - 1

                custo_anterior = CustoMensal.query.filter_by(
                    cod_produto=cod_produto,
                    mes=mes_anterior,
                    ano=ano_anterior,
                    status='FECHADO'
                ).first()

                qtd_inicial = float(custo_anterior.qtd_estoque_final or 0) if custo_anterior else 0
                custo_inicial = float(custo_anterior.custo_estoque_final or 0) if custo_anterior else 0
                custo_unit_inicial = custo_inicial / qtd_inicial if qtd_inicial > 0 else 0

                # Buscar compras do período (mesmo código acima)
                pedidos = PedidoCompras.query.filter(
                    PedidoCompras.cod_produto == cod_produto,
                    PedidoCompras.data_pedido_criacao >= data_inicio_periodo,
                    PedidoCompras.data_pedido_criacao < data_fim_periodo,
                    PedidoCompras.status_odoo.in_(['done', 'purchase']),
                    db.or_(
                        PedidoCompras.tipo_pedido.in_(['compra', 'importacao']),
                        PedidoCompras.tipo_pedido.is_(None)
                    )
                ).order_by(PedidoCompras.data_pedido_criacao.desc()).all()

                qtd_compras = 0
                valor_liquido_compras = 0
                lista_pedidos = []

                for p in pedidos:
                    qtd = float(p.qtd_recebida or p.qtd_produto_pedido or 0)
                    preco = float(p.preco_produto_pedido or 0)
                    valor_bruto = preco * qtd
                    icms = float(p.icms_produto_pedido or 0)
                    pis = float(p.pis_produto_pedido or 0)
                    cofins = float(p.cofins_produto_pedido or 0)
                    valor_liquido = valor_bruto - icms - pis - cofins

                    qtd_compras += qtd
                    valor_liquido_compras += valor_liquido

                    lista_pedidos.append({
                        'num_pedido': p.num_pedido,
                        'fornecedor': p.raz_social or 'N/I',
                        'data': p.data_pedido_criacao.strftime('%d/%m/%Y') if p.data_pedido_criacao else None,
                        'qtd_recebida': qtd,
                        'valor_liquido': round(valor_liquido, 2)
                    })

                # Calcular estoque final
                qtd_final = qtd_inicial + qtd_compras
                custo_total_final = custo_inicial + valor_liquido_compras
                custo_medio_final = custo_total_final / qtd_final if qtd_final > 0 else 0

                # Montar fórmula
                formula = f"({round(custo_inicial, 2)} + {round(valor_liquido_compras, 2)}) / ({round(qtd_inicial, 3)} + {round(qtd_compras, 3)}) = {round(custo_medio_final, 4)}"

                return jsonify({
                    'sucesso': True,
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'tipo': tipo,
                    'periodo': {
                        'mes': mes_ref,
                        'ano': ano_ref,
                        'historico': mostrar_historico
                    },
                    'estoque_inicial': {
                        'qtd': round(qtd_inicial, 3),
                        'valor': round(custo_inicial, 2),
                        'custo_unitario': round(custo_unit_inicial, 4)
                    },
                    'compras': {
                        'qtd': round(qtd_compras, 3),
                        'valor_liquido': round(valor_liquido_compras, 2),
                        'qtd_pedidos': len(pedidos)
                    },
                    'estoque_final': {
                        'qtd': round(qtd_final, 3),
                        'valor': round(custo_total_final, 2),
                        'custo_medio': round(custo_medio_final, 4)
                    },
                    'formula': formula,
                    'pedidos': lista_pedidos
                })

            # ============================================
            # TIPO: custo_considerado
            # ============================================
            elif tipo == 'custo_considerado':
                # Buscar histórico de versões
                versoes = CustoConsiderado.query.filter_by(
                    cod_produto=cod_produto
                ).order_by(CustoConsiderado.versao.desc()).limit(10).all()

                historico = []
                for v in versoes:
                    historico.append({
                        'versao': v.versao,
                        'custo_considerado': float(v.custo_considerado) if v.custo_considerado else None,
                        'tipo_selecionado': v.tipo_custo_selecionado,
                        'vigencia_inicio': v.vigencia_inicio.strftime('%d/%m/%Y %H:%M') if v.vigencia_inicio else None,
                        'vigencia_fim': v.vigencia_fim.strftime('%d/%m/%Y %H:%M') if v.vigencia_fim else None,
                        'motivo': v.motivo_alteracao,
                        'atualizado_por': v.atualizado_por,
                        'atual': v.custo_atual
                    })

                atual = None
                if custo_atual:
                    atual = {
                        'valor': float(custo_atual.custo_considerado) if custo_atual.custo_considerado else None,
                        'tipo_base': custo_atual.tipo_custo_selecionado,
                        'atualizado_em': custo_atual.vigencia_inicio.strftime('%d/%m/%Y %H:%M') if custo_atual.vigencia_inicio else None,
                        'atualizado_por': custo_atual.atualizado_por
                    }

                return jsonify({
                    'sucesso': True,
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'tipo': tipo,
                    'atual': atual,
                    'historico': historico
                })

            else:
                return jsonify({'erro': f'Tipo de custo invalido: {tipo}'}), 400

        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do custo: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_definicao():
        """
        Salva custo considerado para um produto COMPRADO.

        IMPORTANTE: Produtos INTERMEDIARIOS e ACABADOS nao podem ter
        custo editado diretamente - sao calculados via BOM.
        """
        try:
            from app.producao.models import CadastroPalletizacao

            dados = request.json or {}
            cod_produto = dados.get('cod_produto')
            custo_considerado = dados.get('custo_considerado')

            if not cod_produto or custo_considerado is None:
                return jsonify({'erro': 'cod_produto e custo_considerado sao obrigatorios'}), 400

            # Verificar tipo do produto
            produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
            if not produto:
                return jsonify({'erro': 'Produto nao encontrado'}), 404

            # Bloquear edicao de produtos produzidos (exceto se tambem for comprado)
            if produto.produto_produzido and not produto.produto_comprado:
                tipo = 'INTERMEDIARIO' if not produto.produto_vendido else 'ACABADO'
                return jsonify({
                    'sucesso': False,
                    'erro': f'Produto {tipo} nao pode ter custo editado diretamente. '
                            f'O custo e calculado automaticamente via BOM.'
                }), 400

            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

            resultado = ServicoCusteio.cadastrar_custo_manual(
                cod_produto=cod_produto,
                custo_considerado=float(custo_considerado),
                custo_producao=None,
                tipo_custo='MANUAL',
                usuario=usuario,
                motivo='Definicao manual de custo'
            )

            if resultado.get('erro'):
                return jsonify({'sucesso': False, 'erro': resultado['erro']}), 400

            # ============================================
            # PROPAGAR CUSTOS PARA PRODUTOS QUE USAM ESTE COMPONENTE
            # ============================================
            propagacao = ServicoCusteio.propagar_custos_bom(usuario=usuario)

            mensagem = f'Custo definido para {cod_produto}'
            if propagacao.get('total_atualizados', 0) > 0:
                mensagem += f' e {propagacao["total_atualizados"]} produtos recalculados via BOM'

            return jsonify({
                'sucesso': True,
                'mensagem': mensagem,
                'propagacao': propagacao
            })

        except Exception as e:
            logger.error(f"Erro ao salvar definicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/exportar') #type: ignore
    @login_required
    def exportar_definicao():
        """Exporta definicoes de custo para Excel"""
        try:
            import pandas as pd
            from app.producao.models import CadastroPalletizacao
            from app.custeio.models import CustoConsiderado

            produtos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True
            ).order_by(CadastroPalletizacao.cod_produto).all()

            custos_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_dict[c.cod_produto] = c

            dados_excel = []
            for p in produtos:
                tipo = 'COMPRADO' if p.produto_comprado else ('INTERMEDIARIO' if p.produto_produzido and not p.produto_vendido else 'ACABADO')
                c = custos_dict.get(p.cod_produto)

                dados_excel.append({
                    'Codigo': p.cod_produto,
                    'Nome': p.nome_produto,
                    'Tipo': tipo,
                    'Custo Medio Mes': float(c.custo_medio_mes) if c and c.custo_medio_mes else '',
                    'Ultimo Custo': float(c.ultimo_custo) if c and c.ultimo_custo else '',
                    'Custo Medio Estoque': float(c.custo_medio_estoque) if c and c.custo_medio_estoque else '',
                    'Custo BOM': float(c.custo_bom) if c and c.custo_bom else '',
                    'Custo Considerado': float(c.custo_considerado) if c and c.custo_considerado else ''
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Definicao Custo')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='definicao_custo.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao exportar definicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/exportar-detalhado') #type: ignore
    @login_required
    def exportar_custos_detalhados():
        """
        Exporta custos detalhados com BOM recursivo para ACABADOS/INTERMEDIARIOS.

        Parâmetros:
            cod_produto: Código do produto específico (opcional)
                        Se não informado, exporta todos ACABADOS/INTERMEDIARIOS
        """
        try:
            import pandas as pd
            from app.producao.models import CadastroPalletizacao
            from app.custeio.models import CustoConsiderado
            from app.manufatura.models import ListaMateriais
            from app.custeio.services.custeio_service import ServicoCusteio
            from datetime import date

            cod_produto_filtro = request.args.get('cod_produto')

            # Determinar período de referência
            hoje = date.today()
            mes_ref = hoje.month
            ano_ref = hoje.year

            # Buscar custo_considerado do banco
            custos_considerados_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_considerados_dict[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else None,
                    'ultimo_mes_fechado': c.ultimo_mes_fechado,
                    'ultimo_ano_fechado': c.ultimo_ano_fechado
                }

            # Identificar produtos comprados
            produtos_comprados = set(
                p.cod_produto for p in
                CadastroPalletizacao.query.filter_by(ativo=True, produto_comprado=True).all()
            )

            # Cache de custos dinâmicos para COMPRADOS
            custos_dinamicos_dict = {}
            
            def obter_custo_dinamico(cod):
                if cod not in custos_dinamicos_dict and cod in produtos_comprados:
                    custo_info = custos_considerados_dict.get(cod, {})
                    mes_calc = custo_info.get('ultimo_mes_fechado') or mes_ref
                    ano_calc = custo_info.get('ultimo_ano_fechado') or ano_ref
                    custos_calc = ServicoCusteio.calcular_custo_comprados(cod, mes_calc, ano_calc)
                    custos_dinamicos_dict[cod] = {
                        'custo_medio_mes': custos_calc.get('custo_liquido_medio'),
                        'ultimo_custo': custos_calc.get('ultimo_custo'),
                        'custo_medio_estoque': custos_calc.get('custo_medio_estoque'),
                        'custo_considerado': custos_considerados_dict.get(cod, {}).get('custo_considerado')
                    }
                return custos_dinamicos_dict.get(cod, {})

            # Buscar produtos com BOM
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo').with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            # Nomes dos produtos
            nomes_produtos = {
                p.cod_produto: p.nome_produto for p in CadastroPalletizacao.query.all()
            }

            def calcular_custo_recursivo(cod, campo_custo, visitados=None):
                """Calcula custo recursivamente via BOM"""
                if visitados is None:
                    visitados = set()
                if cod in visitados:
                    return None

                if cod not in produtos_com_bom:
                    custo_info = obter_custo_dinamico(cod)
                    return custo_info.get(campo_custo)

                visitados.add(cod)
                componentes = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod, status='ativo'
                ).all()

                custo_total = 0
                for comp in componentes:
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    custo_comp = calcular_custo_recursivo(comp.cod_produto_componente, campo_custo, visitados.copy())
                    if custo_comp is not None:
                        custo_total += custo_comp * qtd

                return custo_total if custo_total > 0 else None

            def expandir_bom_para_export(cod_produto, cod_pai_raiz, nivel=0, visitados=None):
                """Expande BOM recursivamente para exportação com cod_pai separado"""
                if visitados is None:
                    visitados = set()
                if cod_produto in visitados or nivel > 10:
                    return []

                visitados.add(cod_produto)
                componentes = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod_produto, status='ativo'
                ).all()

                resultado = []
                for comp in componentes:
                    cod_comp = comp.cod_produto_componente
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    e_intermediario = cod_comp in produtos_com_bom

                    # Calcular custos
                    if e_intermediario:
                        custos = {
                            'custo_medio_mes': calcular_custo_recursivo(cod_comp, 'custo_medio_mes'),
                            'ultimo_custo': calcular_custo_recursivo(cod_comp, 'ultimo_custo'),
                            'custo_medio_estoque': calcular_custo_recursivo(cod_comp, 'custo_medio_estoque'),
                            'custo_considerado': calcular_custo_recursivo(cod_comp, 'custo_considerado')
                        }
                    else:
                        custo_info = obter_custo_dinamico(cod_comp)
                        custos = {
                            'custo_medio_mes': custo_info.get('custo_medio_mes'),
                            'ultimo_custo': custo_info.get('ultimo_custo'),
                            'custo_medio_estoque': custo_info.get('custo_medio_estoque'),
                            'custo_considerado': custo_info.get('custo_considerado')
                        }

                    resultado.append({
                        'nivel': nivel,
                        'cod_pai': cod_pai_raiz,
                        'cod_pai_direto': cod_produto,
                        'cod_componente': cod_comp,
                        'nome_produto': comp.nome_produto_componente or nomes_produtos.get(cod_comp, ''),
                        'qtd': qtd,
                        'tipo': 'INTERMEDIARIO' if e_intermediario else 'COMPRADO',
                        **custos
                    })

                    # Recursão para intermediários
                    if e_intermediario:
                        sub = expandir_bom_para_export(cod_comp, cod_pai_raiz, nivel + 1, visitados.copy())
                        resultado.extend(sub)

                return resultado

            # Determinar quais produtos exportar
            if cod_produto_filtro:
                # Produto específico
                produtos_exportar = [cod_produto_filtro]
            else:
                # Todos ACABADOS e INTERMEDIARIOS
                produtos_exportar = [
                    p.cod_produto for p in CadastroPalletizacao.query.filter(
                        CadastroPalletizacao.ativo == True,
                        CadastroPalletizacao.produto_produzido == True
                    ).order_by(CadastroPalletizacao.cod_produto).all()
                ]

            # Gerar dados para Excel com colunas separadas para filtros
            dados_excel = []
            for cod_prod in produtos_exportar:
                nome_prod = nomes_produtos.get(cod_prod, '')
                tipo_prod = 'ACABADO' if CadastroPalletizacao.query.filter_by(
                    cod_produto=cod_prod, produto_vendido=True
                ).first() else 'INTERMEDIARIO'

                # Calcular custos do produto principal
                custo_medio_mes = calcular_custo_recursivo(cod_prod, 'custo_medio_mes')
                ultimo_custo = calcular_custo_recursivo(cod_prod, 'ultimo_custo')
                custo_medio_estoque = calcular_custo_recursivo(cod_prod, 'custo_medio_estoque')
                custo_considerado = calcular_custo_recursivo(cod_prod, 'custo_considerado')

                # Linha do produto principal (cod_pai = ele mesmo, cod_componente vazio)
                dados_excel.append({
                    'Cod Pai': cod_prod,
                    'Cod Pai Direto': '',
                    'Cod Componente': '',
                    'Nivel': 0,
                    'Nome Produto': nome_prod,
                    'Tipo': tipo_prod,
                    'Qtd': '',
                    'Custo Medio Mes': round(custo_medio_mes, 4) if custo_medio_mes else '',
                    'Ultimo Custo': round(ultimo_custo, 4) if ultimo_custo else '',
                    'Custo Medio Estoque': round(custo_medio_estoque, 4) if custo_medio_estoque else '',
                    'Custo Considerado': round(custo_considerado, 4) if custo_considerado else ''
                })

                # Expandir BOM
                componentes = expandir_bom_para_export(cod_prod, cod_prod)
                for comp in componentes:
                    dados_excel.append({
                        'Cod Pai': comp['cod_pai'],
                        'Cod Pai Direto': comp['cod_pai_direto'],
                        'Cod Componente': comp['cod_componente'],
                        'Nivel': comp['nivel'] + 1,
                        'Nome Produto': comp['nome_produto'],
                        'Tipo': comp['tipo'],
                        'Qtd': round(comp['qtd'], 4),
                        'Custo Medio Mes': round(comp['custo_medio_mes'], 4) if comp['custo_medio_mes'] else '',
                        'Ultimo Custo': round(comp['ultimo_custo'], 4) if comp['ultimo_custo'] else '',
                        'Custo Medio Estoque': round(comp['custo_medio_estoque'], 4) if comp['custo_medio_estoque'] else '',
                        'Custo Considerado': round(comp['custo_considerado'], 4) if comp['custo_considerado'] else ''
                    })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Custos Detalhados')

                # Ajustar largura das colunas
                worksheet = writer.sheets['Custos Detalhados']
                worksheet.column_dimensions['A'].width = 15  # Cod Pai
                worksheet.column_dimensions['B'].width = 15  # Cod Pai Direto
                worksheet.column_dimensions['C'].width = 15  # Cod Componente
                worksheet.column_dimensions['D'].width = 8   # Nivel
                worksheet.column_dimensions['E'].width = 40  # Nome
                worksheet.column_dimensions['F'].width = 15  # Tipo
                worksheet.column_dimensions['G'].width = 10  # Qtd
                worksheet.column_dimensions['H'].width = 15  # Medio Mes
                worksheet.column_dimensions['I'].width = 15  # Ultimo
                worksheet.column_dimensions['J'].width = 15  # Medio Estoque
                worksheet.column_dimensions['K'].width = 15  # Considerado

            output.seek(0)

            nome_arquivo = f'custos_detalhados_{cod_produto_filtro}.xlsx' if cod_produto_filtro else 'custos_detalhados_todos.xlsx'
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nome_arquivo
            )

        except Exception as e:
            logger.error(f"Erro ao exportar custos detalhados: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_definicao():
        """
        Importa definicoes de custo de arquivo Excel.

        IMPORTANTE: Apenas produtos COMPRADOS sao importados diretamente.
        Produtos INTERMEDIARIOS e ACABADOS tem seus custos calculados
        automaticamente via BOM apos a importacao.
        """
        try:
            import pandas as pd
            from app.producao.models import CadastroPalletizacao

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            df = pd.read_excel(arquivo)

            if 'Codigo' not in df.columns or 'Custo Considerado' not in df.columns:
                return jsonify({'erro': 'Colunas Codigo e Custo Considerado sao obrigatorias'}), 400

            atualizados = 0
            ignorados_produzidos = 0
            erros = []
            usuario = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'

            for idx, row in df.iterrows():
                try:
                    cod_produto = str(row['Codigo']).strip()
                    custo = row['Custo Considerado']

                    if pd.isna(custo) or custo == '':
                        continue

                    # Verificar se e produto COMPRADO
                    produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                    if not produto:
                        erros.append(f"Linha {idx + 2}: Produto {cod_produto} nao encontrado") # type: ignore
                        continue

                    # Ignorar produtos produzidos (serao calculados via BOM)
                    if produto.produto_produzido and not produto.produto_comprado:
                        ignorados_produzidos += 1
                        continue

                    resultado = ServicoCusteio.cadastrar_custo_manual(
                        cod_produto=cod_produto,
                        custo_considerado=float(custo),
                        custo_producao=None,
                        tipo_custo='MANUAL',
                        usuario=usuario,
                        motivo='Importacao via Excel'
                    )

                    if not resultado.get('erro'):
                        atualizados += 1

                except Exception as e:
                    erros.append(f"Linha {idx + 2}: {str(e)}") # type: ignore

            # ============================================
            # PROPAGAR CUSTOS PARA INTERMEDIARIOS E ACABADOS
            # ============================================
            propagacao = {'total_atualizados': 0}
            if atualizados > 0:
                propagacao = ServicoCusteio.propagar_custos_bom(usuario=usuario)

            mensagem = f'{atualizados} comprados importados'
            if propagacao.get('total_atualizados', 0) > 0:
                mensagem += f', {propagacao["total_atualizados"]} produzidos recalculados via BOM'
            if ignorados_produzidos > 0:
                mensagem += f' ({ignorados_produzidos} produzidos ignorados na importacao)'
            if erros:
                mensagem += f', {len(erros)} erros'

            return jsonify({
                'sucesso': True,
                'atualizados': atualizados,
                'propagacao': propagacao,
                'ignorados_produzidos': ignorados_produzidos,
                'erros': erros[:10],
                'mensagem': mensagem
            })

        except Exception as e:
            logger.error(f"Erro ao importar definicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/modelo') #type: ignore
    @login_required
    def modelo_definicao():
        """Gera modelo Excel para importacao de definicao de custo"""
        try:
            import pandas as pd

            dados = [
                {'Codigo': '101000001', 'Nome': 'Produto Exemplo', 'Custo Considerado': 25.50},
            ]

            df = pd.DataFrame(dados)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Modelo')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='modelo_definicao_custo.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao gerar modelo definicao: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # PAGINA - COMISSAO
    # ================================================

    @bp.route('/comissao') #type: ignore
    @login_required
    def tela_comissao():
        """Tela CRUD de Regras de Comissao"""
        return render_template('custeio/comissao.html')

    # ================================================
    # API - COMISSAO
    # ================================================

    @bp.route('/api/comissao/listar') #type: ignore
    @login_required
    def listar_comissoes():
        """Lista regras de comissao com filtros"""
        try:
            from app.custeio.models import RegraComissao

            tipo_regra = request.args.get('tipo_regra')
            grupo_empresarial = request.args.get('grupo_empresarial')
            raz_social_red = request.args.get('raz_social_red')
            cod_produto = request.args.get('cod_produto')
            apenas_ativos = request.args.get('apenas_ativos', 'true').lower() == 'true'

            query = RegraComissao.query

            if tipo_regra:
                query = query.filter(RegraComissao.tipo_regra == tipo_regra)
            if grupo_empresarial:
                query = query.filter(RegraComissao.grupo_empresarial.ilike(f'%{grupo_empresarial}%'))
            if raz_social_red:
                query = query.filter(RegraComissao.raz_social_red.ilike(f'%{raz_social_red}%'))
            if cod_produto:
                query = query.filter(RegraComissao.cod_produto.ilike(f'%{cod_produto}%'))
            if apenas_ativos:
                query = query.filter(RegraComissao.ativo == True)

            regras = query.order_by(RegraComissao.tipo_regra, RegraComissao.prioridade.desc()).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'id': r.id,
                    'tipo_regra': r.tipo_regra,
                    'grupo_empresarial': r.grupo_empresarial,
                    'raz_social_red': r.raz_social_red,
                    'vendedor': r.vendedor,
                    'cod_produto': r.cod_produto,
                    'cliente_cod_uf': r.cliente_cod_uf,
                    'cliente_vendedor': r.cliente_vendedor,
                    'cliente_equipe': r.cliente_equipe,
                    'produto_grupo': r.produto_grupo,
                    'produto_cliente': r.produto_cliente,
                    'comissao_percentual': float(r.comissao_percentual) if r.comissao_percentual else 0,
                    'vigencia_inicio': r.vigencia_inicio.strftime('%Y-%m-%d') if r.vigencia_inicio else None,
                    'vigencia_fim': r.vigencia_fim.strftime('%Y-%m-%d') if r.vigencia_fim else None,
                    'prioridade': r.prioridade,
                    'descricao': r.descricao,
                    'ativo': r.ativo,
                    'criado_em': r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else None,
                    'criado_por': r.criado_por
                } for r in regras],
                'total': len(regras)
            })

        except Exception as e:
            logger.error(f"Erro ao listar regras de comissao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_comissao():
        """Cria ou atualiza regra de comissao"""
        try:
            from app.custeio.models import RegraComissao
            from app import db
            from datetime import datetime

            dados = request.json or {}
            id_registro = dados.get('id')
            tipo_regra = dados.get('tipo_regra')
            comissao_percentual = dados.get('comissao_percentual')

            if not tipo_regra or comissao_percentual is None:
                return jsonify({'erro': 'tipo_regra e comissao_percentual sao obrigatorios'}), 400

            tipos_validos = ('CLIENTE_PRODUTO', 'GRUPO_PRODUTO', 'VENDEDOR_PRODUTO',
                           'CLIENTE', 'GRUPO', 'VENDEDOR', 'PRODUTO')
            if tipo_regra not in tipos_validos:
                return jsonify({'erro': f'tipo_regra deve ser um de: {", ".join(tipos_validos)}'}), 400

            # Validar criterios conforme tipo
            if tipo_regra == 'CLIENTE_PRODUTO':
                if not dados.get('raz_social_red') or not dados.get('cod_produto'):
                    return jsonify({'erro': 'raz_social_red e cod_produto sao obrigatorios para CLIENTE_PRODUTO'}), 400
            elif tipo_regra == 'GRUPO_PRODUTO':
                if not dados.get('grupo_empresarial') or not dados.get('cod_produto'):
                    return jsonify({'erro': 'grupo_empresarial e cod_produto sao obrigatorios para GRUPO_PRODUTO'}), 400
            elif tipo_regra == 'VENDEDOR_PRODUTO':
                if not dados.get('vendedor') or not dados.get('cod_produto'):
                    return jsonify({'erro': 'vendedor e cod_produto sao obrigatorios para VENDEDOR_PRODUTO'}), 400
            elif tipo_regra == 'CLIENTE' and not dados.get('raz_social_red'):
                return jsonify({'erro': 'raz_social_red e obrigatorio para tipo CLIENTE'}), 400
            elif tipo_regra == 'GRUPO' and not dados.get('grupo_empresarial'):
                return jsonify({'erro': 'grupo_empresarial e obrigatorio para tipo GRUPO'}), 400
            elif tipo_regra == 'VENDEDOR' and not dados.get('vendedor'):
                return jsonify({'erro': 'vendedor e obrigatorio para tipo VENDEDOR'}), 400
            elif tipo_regra == 'PRODUTO' and not dados.get('cod_produto'):
                return jsonify({'erro': 'cod_produto e obrigatorio para tipo PRODUTO'}), 400

            vigencia_inicio = dados.get('vigencia_inicio')
            vigencia_fim = dados.get('vigencia_fim')

            if id_registro:
                # Atualizar existente
                registro = db.session.get(RegraComissao, id_registro)
                if not registro:
                    return jsonify({'erro': 'Regra nao encontrada'}), 404

                registro.tipo_regra = tipo_regra
                registro.grupo_empresarial = dados.get('grupo_empresarial')
                registro.raz_social_red = dados.get('raz_social_red')
                registro.vendedor = dados.get('vendedor')
                registro.cod_produto = dados.get('cod_produto')
                registro.cliente_cod_uf = dados.get('cliente_cod_uf')
                registro.cliente_vendedor = dados.get('cliente_vendedor')
                registro.cliente_equipe = dados.get('cliente_equipe')
                registro.produto_grupo = dados.get('produto_grupo')
                registro.produto_cliente = dados.get('produto_cliente')
                registro.comissao_percentual = comissao_percentual
                registro.vigencia_inicio = datetime.strptime(vigencia_inicio, '%Y-%m-%d').date() if vigencia_inicio else registro.vigencia_inicio
                registro.vigencia_fim = datetime.strptime(vigencia_fim, '%Y-%m-%d').date() if vigencia_fim else None
                registro.prioridade = dados.get('prioridade', 0)
                registro.descricao = dados.get('descricao')
                registro.ativo = dados.get('ativo', True)
                registro.atualizado_em = datetime.utcnow()
                registro.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            else:
                # Criar novo
                registro = RegraComissao(
                    tipo_regra=tipo_regra,
                    grupo_empresarial=dados.get('grupo_empresarial'),
                    raz_social_red=dados.get('raz_social_red'),
                    vendedor=dados.get('vendedor'),
                    cod_produto=dados.get('cod_produto'),
                    cliente_cod_uf=dados.get('cliente_cod_uf'),
                    cliente_vendedor=dados.get('cliente_vendedor'),
                    cliente_equipe=dados.get('cliente_equipe'),
                    produto_grupo=dados.get('produto_grupo'),
                    produto_cliente=dados.get('produto_cliente'),
                    comissao_percentual=comissao_percentual,
                    vigencia_inicio=datetime.strptime(vigencia_inicio, '%Y-%m-%d').date() if vigencia_inicio else datetime.now().date(),
                    vigencia_fim=datetime.strptime(vigencia_fim, '%Y-%m-%d').date() if vigencia_fim else None,
                    prioridade=dados.get('prioridade', 0),
                    descricao=dados.get('descricao'),
                    ativo=dados.get('ativo', True),
                    criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                )
                db.session.add(registro)

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'id': registro.id,
                'mensagem': 'Regra de comissao salva com sucesso'
            })

        except Exception as e:
            logger.error(f"Erro ao salvar regra de comissao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/excluir/<int:id_registro>', methods=['DELETE']) #type: ignore
    @login_required
    def excluir_comissao(id_registro):
        """Soft delete de regra de comissao"""
        try:
            from app.custeio.models import RegraComissao
            from app import db

            registro = db.session.get(RegraComissao, id_registro)
            if not registro:
                return jsonify({'erro': 'Regra nao encontrada'}), 404

            registro.ativo = False
            registro.atualizado_em = datetime.utcnow()
            registro.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Regra desativada com sucesso'
            })

        except Exception as e:
            logger.error(f"Erro ao excluir regra de comissao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/grupos') #type: ignore
    @login_required
    def listar_grupos_comissao():
        """Lista grupos empresariais disponiveis para comissao"""
        try:
            from app.portal.utils.grupo_empresarial import GrupoEmpresarial

            # Obter lista de grupos do mapeamento
            grupos = list(GrupoEmpresarial.GRUPOS.keys())
            grupos.sort()

            return jsonify({
                'sucesso': True,
                'dados': grupos
            })

        except Exception as e:
            logger.error(f"Erro ao listar grupos: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/clientes') #type: ignore
    @login_required
    def listar_clientes_comissao():
        """Lista clientes disponiveis para regra de comissao"""
        try:
            from app.carteira.models import CarteiraPrincipal

            termo = request.args.get('termo', '')
            uf = request.args.get('uf')
            vendedor = request.args.get('vendedor')
            equipe = request.args.get('equipe')

            query = CarteiraPrincipal.query.with_entities(
                CarteiraPrincipal.raz_social_red,
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.vendedor,
                CarteiraPrincipal.equipe_vendas
            ).distinct()

            if termo:
                query = query.filter(CarteiraPrincipal.raz_social_red.ilike(f'%{termo}%'))
            if uf:
                query = query.filter(CarteiraPrincipal.cod_uf == uf)
            if vendedor:
                query = query.filter(CarteiraPrincipal.vendedor.ilike(f'%{vendedor}%'))
            if equipe:
                query = query.filter(CarteiraPrincipal.equipe_vendas.ilike(f'%{equipe}%'))

            clientes = query.limit(50).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'raz_social_red': c.raz_social_red,
                    'cnpj_cpf': c.cnpj_cpf,
                    'cod_uf': c.cod_uf,
                    'vendedor': c.vendedor,
                    'equipe_vendas': c.equipe_vendas
                } for c in clientes if c.raz_social_red]
            })

        except Exception as e:
            logger.error(f"Erro ao listar clientes: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/produtos') #type: ignore
    @login_required
    def listar_produtos_comissao():
        """Lista produtos disponiveis para regra de comissao"""
        try:
            from app.producao.models import CadastroPalletizacao

            termo = request.args.get('termo', '')

            query = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True
            )

            if termo:
                query = query.filter(
                    (CadastroPalletizacao.cod_produto.ilike(f'%{termo}%')) |
                    (CadastroPalletizacao.nome_produto.ilike(f'%{termo}%'))
                )

            produtos = query.order_by(CadastroPalletizacao.cod_produto).limit(50).all()

            return jsonify({
                'sucesso': True,
                'dados': [{
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto
                } for p in produtos]
            })

        except Exception as e:
            logger.error(f"Erro ao listar produtos: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/ufs') #type: ignore
    @login_required
    def listar_ufs_comissao():
        """Lista UFs disponiveis"""
        try:
            from app.carteira.models import CarteiraPrincipal

            ufs = CarteiraPrincipal.query.with_entities(
                CarteiraPrincipal.cod_uf
            ).distinct().filter(
                CarteiraPrincipal.cod_uf.isnot(None)
            ).all()

            return jsonify({
                'sucesso': True,
                'dados': sorted([u.cod_uf for u in ufs if u.cod_uf])
            })

        except Exception as e:
            logger.error(f"Erro ao listar UFs: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/vendedores') #type: ignore
    @login_required
    def listar_vendedores_comissao():
        """Lista vendedores disponiveis"""
        try:
            from app.carteira.models import CarteiraPrincipal

            vendedores = CarteiraPrincipal.query.with_entities(
                CarteiraPrincipal.vendedor
            ).distinct().filter(
                CarteiraPrincipal.vendedor.isnot(None)
            ).all()

            return jsonify({
                'sucesso': True,
                'dados': sorted([v.vendedor for v in vendedores if v.vendedor])
            })

        except Exception as e:
            logger.error(f"Erro ao listar vendedores: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/equipes') #type: ignore
    @login_required
    def listar_equipes_comissao():
        """Lista equipes de vendas disponiveis"""
        try:
            from app.carteira.models import CarteiraPrincipal

            equipes = CarteiraPrincipal.query.with_entities(
                CarteiraPrincipal.equipe_vendas
            ).distinct().filter(
                CarteiraPrincipal.equipe_vendas.isnot(None)
            ).all()

            return jsonify({
                'sucesso': True,
                'dados': sorted([e.equipe_vendas for e in equipes if e.equipe_vendas])
            })

        except Exception as e:
            logger.error(f"Erro ao listar equipes: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_comissao():
        """Importa regras de comissao via Excel"""
        try:
            import pandas as pd
            from app.custeio.models import RegraComissao
            from app import db
            from datetime import datetime

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            df = pd.read_excel(arquivo)

            colunas_obrigatorias = ['Tipo Regra', 'Comissao %']
            for col in colunas_obrigatorias:
                if col not in df.columns:
                    return jsonify({'erro': f'Coluna {col} e obrigatoria'}), 400

            importados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    tipo_regra = str(row['Tipo Regra']).strip().upper()
                    comissao = row['Comissao %']

                    if tipo_regra not in ('GRUPO', 'CLIENTE', 'PRODUTO'):
                        erros.append(f"Linha {idx + 2}: Tipo Regra invalido '{tipo_regra}'") # type: ignore
                        continue

                    if pd.isna(comissao):
                        erros.append(f"Linha {idx + 2}: Comissao % vazia") # type: ignore
                        continue

                    registro = RegraComissao(
                        tipo_regra=tipo_regra,
                        grupo_empresarial=str(row.get('Grupo Empresarial', '')).strip() if pd.notna(row.get('Grupo Empresarial')) else None,
                        raz_social_red=str(row.get('Cliente', '')).strip() if pd.notna(row.get('Cliente')) else None,
                        cliente_cod_uf=str(row.get('UF', '')).strip() if pd.notna(row.get('UF')) else None,
                        cliente_vendedor=str(row.get('Vendedor', '')).strip() if pd.notna(row.get('Vendedor')) else None,
                        cliente_equipe=str(row.get('Equipe', '')).strip() if pd.notna(row.get('Equipe')) else None,
                        cod_produto=str(row.get('Cod Produto', '')).strip() if pd.notna(row.get('Cod Produto')) else None,
                        produto_grupo=str(row.get('Produto Grupo', '')).strip() if pd.notna(row.get('Produto Grupo')) else None,
                        produto_cliente=str(row.get('Produto Cliente', '')).strip() if pd.notna(row.get('Produto Cliente')) else None,
                        comissao_percentual=float(comissao),
                        vigencia_inicio=datetime.now().date(),
                        descricao=str(row.get('Descricao', '')).strip() if pd.notna(row.get('Descricao')) else 'Importado via Excel',
                        ativo=True,
                        criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                    )
                    db.session.add(registro)
                    importados += 1

                except Exception as e:
                    erros.append(f"Linha {idx + 2}: {str(e)}") # type: ignore

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'importados': importados,
                'erros': erros[:10],
                'mensagem': f'{importados} regras importadas' + (f', {len(erros)} erros' if erros else '')
            })

        except Exception as e:
            logger.error(f"Erro ao importar comissoes: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/exportar') #type: ignore
    @login_required
    def exportar_comissao():
        """Exporta regras de comissao para Excel"""
        try:
            import pandas as pd
            from app.custeio.models import RegraComissao

            regras = RegraComissao.query.filter_by(ativo=True).order_by(
                RegraComissao.tipo_regra, RegraComissao.prioridade.desc()
            ).all()

            dados_excel = []
            for r in regras:
                dados_excel.append({
                    'Tipo Regra': r.tipo_regra,
                    'Grupo Empresarial': r.grupo_empresarial or '',
                    'Cliente': r.raz_social_red or '',
                    'UF': r.cliente_cod_uf or '',
                    'Vendedor': r.cliente_vendedor or '',
                    'Equipe': r.cliente_equipe or '',
                    'Cod Produto': r.cod_produto or '',
                    'Produto Grupo': r.produto_grupo or '',
                    'Produto Cliente': r.produto_cliente or '',
                    'Comissao %': float(r.comissao_percentual) if r.comissao_percentual else 0,
                    'Vigencia Inicio': r.vigencia_inicio.strftime('%d/%m/%Y') if r.vigencia_inicio else '',
                    'Vigencia Fim': r.vigencia_fim.strftime('%d/%m/%Y') if r.vigencia_fim else '',
                    'Prioridade': r.prioridade,
                    'Descricao': r.descricao or ''
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Regras Comissao')

                worksheet = writer.sheets['Regras Comissao']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 40)

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='regras_comissao.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao exportar comissoes: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/comissao/modelo') #type: ignore
    @login_required
    def modelo_comissao():
        """Gera modelo Excel para importacao de regras de comissao"""
        try:
            import pandas as pd

            dados = [
                {
                    'Tipo Regra': 'GRUPO',
                    'Grupo Empresarial': 'ATACADAO',
                    'Cliente': '',
                    'UF': '',
                    'Vendedor': '',
                    'Equipe': '',
                    'Cod Produto': '',
                    'Produto Grupo': '',
                    'Produto Cliente': '',
                    'Comissao %': 2.5,
                    'Descricao': 'Comissao padrao Atacadao'
                },
                {
                    'Tipo Regra': 'CLIENTE',
                    'Grupo Empresarial': '',
                    'Cliente': 'SUPERMERCADO XYZ',
                    'UF': 'SP',
                    'Vendedor': '',
                    'Equipe': '',
                    'Cod Produto': '',
                    'Produto Grupo': '',
                    'Produto Cliente': '',
                    'Comissao %': 3.0,
                    'Descricao': 'Comissao cliente especifico'
                },
                {
                    'Tipo Regra': 'PRODUTO',
                    'Grupo Empresarial': '',
                    'Cliente': '',
                    'UF': '',
                    'Vendedor': '',
                    'Equipe': '',
                    'Cod Produto': '101000001',
                    'Produto Grupo': '',
                    'Produto Cliente': '',
                    'Comissao %': 1.5,
                    'Descricao': 'Comissao produto especifico'
                }
            ]

            df = pd.DataFrame(dados)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Modelo')

                worksheet = writer.sheets['Modelo']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 40)

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='modelo_regras_comissao.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao gerar modelo comissao: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - RECALCULO DE MARGEM
    # ================================================

    @bp.route('/api/margem/recalcular', methods=['POST']) #type: ignore
    @login_required
    def recalcular_margem():
        """Recalcula margem para pedidos especificos ou todos"""
        try:
            from app.carteira.models import CarteiraPrincipal
            from app.odoo.services.carteira_service import CarteiraService
            from app import db

            dados = request.json or {}
            num_pedido = dados.get('num_pedido')
            cod_produto = dados.get('cod_produto')
            recalcular_todos = dados.get('todos', False)

            query = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            )

            if num_pedido:
                query = query.filter(CarteiraPrincipal.num_pedido == num_pedido)
            if cod_produto:
                query = query.filter(CarteiraPrincipal.cod_produto == cod_produto)
            if not recalcular_todos and not num_pedido and not cod_produto:
                return jsonify({'erro': 'Informe num_pedido, cod_produto ou todos=true'}), 400

            items = query.all()
            total = len(items)
            atualizados = 0
            erros = []

            service = CarteiraService()

            for item in items:
                try:
                    # Montar dict com dados do item para recalculo
                    item_dict = {
                        'num_pedido': item.num_pedido,
                        'cod_produto': item.cod_produto,
                        'preco_produto_pedido': float(item.preco_produto_pedido) if item.preco_produto_pedido else 0,
                        'qtd_produto_pedido': float(item.qtd_produto_pedido) if item.qtd_produto_pedido else 0,
                        'icms_st_item_pedido': float(item.icms_st_item_pedido) if item.icms_st_item_pedido else 0,
                        'pis_item_pedido': float(item.pis_item_pedido) if item.pis_item_pedido else 0,
                        'cofins_item_pedido': float(item.cofins_item_pedido) if item.cofins_item_pedido else 0,
                        'desconto_item_pedido': float(item.desconto_item_pedido) if item.desconto_item_pedido else 0,
                        'cod_uf': item.cod_uf,
                        'incoterm': item.incoterm,
                        'custo_considerado_snapshot': float(item.custo_considerado_snapshot) if item.custo_considerado_snapshot else 0,
                        'custo_producao_snapshot': float(item.custo_producao_snapshot) if item.custo_producao_snapshot else 0,
                        'desconto_contratual_snapshot': float(item.desconto_contratual_snapshot) if item.desconto_contratual_snapshot else 0,
                        'cnpj_cpf': item.cnpj_cpf,
                        'raz_social_red': item.raz_social_red,
                        'vendedor': item.vendedor,
                        'equipe_vendas': item.equipe_vendas,
                        'forma_pgto_pedido': item.forma_pgto_pedido
                    }

                    resultado = service._calcular_margem_bruta(item_dict)

                    item.margem_bruta = resultado.get('margem_bruta')
                    item.margem_bruta_percentual = resultado.get('margem_bruta_percentual')
                    item.margem_liquida = resultado.get('margem_liquida')
                    item.margem_liquida_percentual = resultado.get('margem_liquida_percentual')
                    item.comissao_percentual = resultado.get('comissao_percentual', 0)

                    atualizados += 1

                except Exception as e:
                    erros.append(f"{item.num_pedido}/{item.cod_produto}: {str(e)}")

            db.session.commit()

            return jsonify({
                'sucesso': True,
                'total': total,
                'atualizados': atualizados,
                'erros': erros[:10],
                'mensagem': f'{atualizados} de {total} registros atualizados'
            })

        except Exception as e:
            logger.error(f"Erro ao recalcular margem: {e}")
            return jsonify({'erro': str(e)}), 500
