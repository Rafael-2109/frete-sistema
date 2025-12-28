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

    @bp.route('/composicao') #type: ignore
    @login_required
    def tela_composicao():
        """Tela de Composicao de Custo via BOM"""
        return render_template('custeio/composicao.html')

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
            from app.custeio.models import CustoMensal

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
                registro = CustoFrete.query.get(id_registro)
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

            registro = CustoFrete.query.get(id_registro)
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
                registro = ParametroCusteio.query.get(id_registro)
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

            parametro = ParametroCusteio.query.get(id_param)
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
            from app import db

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
    # API - COMPOSICAO DE CUSTO (BOM)
    # ================================================

    @bp.route('/api/composicao/listar') #type: ignore
    @login_required
    def listar_composicao():
        """Lista produtos com composicao de custo via BOM"""
        try:
            from app.producao.models import CadastroPalletizacao
            from app.manufatura.models import ListaMateriais
            from app.custeio.models import CustoConsiderado

            filtro_tipo = request.args.get('tipo')  # 'produzido' ou 'comprado'
            termo = request.args.get('termo', '')

            # Buscar produtos - priorizar produzidos (que têm BOM)
            query = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True
            )

            if filtro_tipo == 'produzido':
                query = query.filter(CadastroPalletizacao.produto_produzido == True)
            elif filtro_tipo == 'comprado':
                query = query.filter(CadastroPalletizacao.produto_comprado == True)
            else:
                # Sem filtro: priorizar produtos produzidos (que têm BOM)
                query = query.filter(CadastroPalletizacao.produto_produzido == True)

            if termo:
                query = query.filter(
                    (CadastroPalletizacao.cod_produto.ilike(f'%{termo}%')) |
                    (CadastroPalletizacao.nome_produto.ilike(f'%{termo}%'))
                )

            produtos = query.order_by(CadastroPalletizacao.cod_produto).all()

            # Buscar custos
            custos = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos[c.cod_produto] = float(c.custo_considerado) if c.custo_considerado else None

            # Buscar BOM
            bom_dict = {}
            for bom in ListaMateriais.query.filter_by(status='ativo').all():
                if bom.cod_produto_produzido not in bom_dict:
                    bom_dict[bom.cod_produto_produzido] = []
                bom_dict[bom.cod_produto_produzido].append({
                    'cod_componente': bom.cod_produto_componente,
                    'nome_componente': bom.nome_produto_componente,
                    'qtd_utilizada': float(bom.qtd_utilizada) if bom.qtd_utilizada else 0,
                    'custo_componente': custos.get(bom.cod_produto_componente)
                })

            dados = []
            for p in produtos:
                tipo = 'COMPRADO' if p.produto_comprado else ('INTERMEDIARIO' if p.produto_produzido and not p.produto_vendido else 'ACABADO')
                componentes = bom_dict.get(p.cod_produto, [])

                # Calcular custo BOM
                custo_bom = 0
                for comp in componentes:
                    if comp['custo_componente']:
                        custo_bom += comp['qtd_utilizada'] * comp['custo_componente']

                dados.append({
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto,
                    'tipo': tipo,
                    'custo_considerado': custos.get(p.cod_produto),
                    'custo_bom': custo_bom if componentes else None,
                    'componentes': componentes,
                    'tem_bom': len(componentes) > 0
                })

            return jsonify({
                'sucesso': True,
                'dados': dados,
                'total': len(dados)
            })

        except Exception as e:
            logger.error(f"Erro ao listar composicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/composicao/detalhe/<cod_produto>') #type: ignore
    @login_required
    def detalhe_composicao(cod_produto):
        """Retorna composicao detalhada de um produto (BOM expandida)"""
        try:
            from app.manufatura.models import ListaMateriais
            from app.custeio.models import CustoConsiderado

            # Buscar custos
            custos = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos[c.cod_produto] = float(c.custo_considerado) if c.custo_considerado else None

            # Buscar produtos que tem BOM (intermediarios)
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo').with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            def expandir_bom(cod, nivel=0, visitados=None):
                if visitados is None:
                    visitados = set()

                if cod in visitados or nivel > 5:  # Evitar recursao infinita
                    return []

                visitados.add(cod)

                componentes = ListaMateriais.query.filter_by(
                    cod_produto_produzido=cod,
                    status='ativo'
                ).all()

                resultado = []
                for comp in componentes:
                    custo_unit = custos.get(comp.cod_produto_componente)
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    custo_total = (custo_unit * qtd) if custo_unit else None

                    # Determinar tipo: INTERMEDIARIO se tem BOM, senao COMPRADO
                    tipo_comp = 'INTERMEDIARIO' if comp.cod_produto_componente in produtos_com_bom else 'COMPRADO'

                    item = {
                        'nivel': nivel,
                        'cod_produto': comp.cod_produto_componente,
                        'nome_produto': comp.nome_produto_componente,
                        'qtd_utilizada': qtd,
                        'custo_unitario': custo_unit,
                        'custo_total': custo_total,
                        'tipo': tipo_comp
                    }
                    resultado.append(item)

                    # Expandir sub-componentes
                    sub = expandir_bom(comp.cod_produto_componente, nivel + 1, visitados.copy())
                    resultado.extend(sub)

                return resultado

            composicao = expandir_bom(cod_produto)

            # Calcular custo total
            custo_total = sum(c['custo_total'] or 0 for c in composicao if c['nivel'] == 0)

            return jsonify({
                'sucesso': True,
                'cod_produto': cod_produto,
                'composicao': composicao,
                'custo_total_bom': custo_total
            })

        except Exception as e:
            logger.error(f"Erro ao buscar composicao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/composicao/exportar') #type: ignore
    @login_required
    def exportar_composicao():
        """Exporta composicao de custo para Excel"""
        try:
            import pandas as pd
            from app.producao.models import CadastroPalletizacao
            from app.manufatura.models import ListaMateriais
            from app.custeio.models import CustoConsiderado

            produtos = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.ativo == True
            ).order_by(CadastroPalletizacao.cod_produto).all()

            custos = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos[c.cod_produto] = float(c.custo_considerado) if c.custo_considerado else 0

            bom_dict = {}
            for bom in ListaMateriais.query.filter_by(status='ativo').all():
                if bom.cod_produto_produzido not in bom_dict:
                    bom_dict[bom.cod_produto_produzido] = []
                bom_dict[bom.cod_produto_produzido].append(bom)

            dados_excel = []
            for p in produtos:
                tipo = 'COMPRADO' if p.produto_comprado else ('INTERMEDIARIO' if p.produto_produzido and not p.produto_vendido else 'ACABADO')
                componentes = bom_dict.get(p.cod_produto, [])

                custo_bom = 0
                for comp in componentes:
                    custo_comp = custos.get(comp.cod_produto_componente, 0)
                    qtd = float(comp.qtd_utilizada) if comp.qtd_utilizada else 0
                    custo_bom += custo_comp * qtd

                dados_excel.append({
                    'Codigo': p.cod_produto,
                    'Nome': p.nome_produto,
                    'Tipo': tipo,
                    'Custo Considerado': custos.get(p.cod_produto, 0),
                    'Custo BOM': custo_bom if componentes else '',
                    'Qtd Componentes': len(componentes)
                })

            df = pd.DataFrame(dados_excel)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Composicao Custo')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='composicao_custo.xlsx'
            )

        except Exception as e:
            logger.error(f"Erro ao exportar composicao: {e}")
            return jsonify({'erro': str(e)}), 500

    # ================================================
    # API - DEFINICAO DE CUSTO CONSIDERADO
    # ================================================

    @bp.route('/api/definicao/listar') #type: ignore
    @login_required
    def listar_definicao():
        """Lista produtos com custos para definicao (calcula BOM para produzidos)"""
        try:
            from app.producao.models import CadastroPalletizacao
            from app.custeio.models import CustoConsiderado
            from app.manufatura.models import ListaMateriais

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

            # Buscar custos diretos
            custos_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_dict[c.cod_produto] = {
                    'custo_considerado': float(c.custo_considerado) if c.custo_considerado else None,
                    'custo_medio_mes': float(c.custo_medio_mes) if c.custo_medio_mes else None,
                    'ultimo_custo': float(c.ultimo_custo) if c.ultimo_custo else None,
                    'custo_medio_estoque': float(c.custo_medio_estoque) if c.custo_medio_estoque else None,
                    'tipo_custo': c.tipo_custo_selecionado
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
                """Calcula custo de um produto via BOM recursivamente"""
                if visitados is None:
                    visitados = set()

                if cod in visitados:
                    return None  # Evitar loop infinito

                # Se não tem BOM, usar custo direto
                if cod not in produtos_com_bom:
                    custo_info = custos_dict.get(cod, {})
                    return custo_info.get(campo_custo)

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
                custo = custos_dict.get(p.cod_produto, {})

                # Para produtos produzidos, calcular custos via BOM
                if tipo in ('INTERMEDIARIO', 'ACABADO'):
                    custo_medio_mes = calcular_custo_bom(p.cod_produto, 'custo_medio_mes')
                    ultimo_custo = calcular_custo_bom(p.cod_produto, 'ultimo_custo')
                    custo_medio_estoque = calcular_custo_bom(p.cod_produto, 'custo_medio_estoque')
                else:
                    custo_medio_mes = custo.get('custo_medio_mes')
                    ultimo_custo = custo.get('ultimo_custo')
                    custo_medio_estoque = custo.get('custo_medio_estoque')

                dados.append({
                    'cod_produto': p.cod_produto,
                    'nome_produto': p.nome_produto,
                    'tipo': tipo,
                    'custo_considerado': custo.get('custo_considerado'),
                    'custo_medio_mes': custo_medio_mes,
                    'ultimo_custo': ultimo_custo,
                    'custo_medio_estoque': custo_medio_estoque,
                    'tipo_custo': custo.get('tipo_custo')
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
        """Retorna composição BOM com custos calculados recursivamente por critério"""
        try:
            from app.manufatura.models import ListaMateriais
            from app.custeio.models import CustoConsiderado
            from app.producao.models import CadastroPalletizacao

            criterio = request.args.get('criterio', 'medio_mes')

            # Mapear critério para campo
            campo_custo = {
                'medio_mes': 'custo_medio_mes',
                'ultimo_custo': 'ultimo_custo',
                'medio_estoque': 'custo_medio_estoque'
            }.get(criterio, 'custo_medio_mes')

            # Buscar todos os custos
            custos_dict = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                custos_dict[c.cod_produto] = {
                    'custo_medio_mes': float(c.custo_medio_mes) if c.custo_medio_mes else None,
                    'ultimo_custo': float(c.ultimo_custo) if c.ultimo_custo else None,
                    'custo_medio_estoque': float(c.custo_medio_estoque) if c.custo_medio_estoque else None
                }

            # Buscar produtos com BOM (são intermediários)
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo').with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            def calcular_custo_recursivo(cod, criterio_campo, visitados=None):
                """Calcula custo de um produto recursivamente via BOM"""
                if visitados is None:
                    visitados = set()

                if cod in visitados:
                    return None  # Evitar loop infinito

                # Se é produto comprado ou não tem BOM, usar custo direto
                if cod not in produtos_com_bom:
                    custo_info = custos_dict.get(cod, {})
                    return custo_info.get(criterio_campo)

                # É intermediário - calcular via BOM
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

            def expandir_bom(cod, criterio_campo, nivel=0, visitados=None):
                """Expande BOM e retorna componentes com custos calculados"""
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

                    # Determinar tipo e calcular custo
                    e_intermediario = cod_comp in produtos_com_bom

                    if e_intermediario:
                        # Calcular custo recursivamente
                        custo_unit = calcular_custo_recursivo(cod_comp, criterio_campo, set())
                    else:
                        # Usar custo direto
                        custo_info = custos_dict.get(cod_comp, {})
                        custo_unit = custo_info.get(criterio_campo)

                    custo_total = (custo_unit * qtd) if custo_unit else None

                    item = {
                        'nivel': nivel,
                        'cod_produto': cod_comp,
                        'nome_produto': comp.nome_produto_componente,
                        'qtd_utilizada': qtd,
                        'custo_unitario': custo_unit,
                        'custo_total': custo_total,
                        'tipo': 'INTERMEDIARIO' if e_intermediario else 'COMPRADO'
                    }
                    resultado.append(item)

                    # Expandir sub-componentes se for intermediário
                    if e_intermediario:
                        sub = expandir_bom(cod_comp, criterio_campo, nivel + 1, visitados.copy())
                        resultado.extend(sub)

                return resultado

            composicao = expandir_bom(cod_produto, campo_custo)

            # Calcular custo total (apenas nível 0)
            custo_total = sum(c['custo_total'] or 0 for c in composicao if c['nivel'] == 0)

            return jsonify({
                'sucesso': True,
                'cod_produto': cod_produto,
                'criterio': criterio,
                'componentes': composicao,
                'custo_total': custo_total
            })

        except Exception as e:
            logger.error(f"Erro ao buscar BOM por criterio: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/definicao/salvar', methods=['POST']) #type: ignore
    @login_required
    def salvar_definicao():
        """Salva custo considerado para um produto"""
        try:
            dados = request.json or {}
            cod_produto = dados.get('cod_produto')
            custo_considerado = dados.get('custo_considerado')

            if not cod_produto or custo_considerado is None:
                return jsonify({'erro': 'cod_produto e custo_considerado sao obrigatorios'}), 400

            resultado = ServicoCusteio.cadastrar_custo_manual(
                cod_produto=cod_produto,
                custo_considerado=float(custo_considerado),
                custo_producao=None,
                tipo_custo='MANUAL',
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema',
                motivo='Definicao manual de custo'
            )

            if resultado.get('erro'):
                return jsonify({'sucesso': False, 'erro': resultado['erro']}), 400

            return jsonify({'sucesso': True, 'mensagem': f'Custo definido para {cod_produto}'})

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

    @bp.route('/api/definicao/importar', methods=['POST']) #type: ignore
    @login_required
    def importar_definicao():
        """Importa definicoes de custo de arquivo Excel"""
        try:
            import pandas as pd

            if 'arquivo' not in request.files:
                return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

            arquivo = request.files['arquivo']
            df = pd.read_excel(arquivo)

            if 'Codigo' not in df.columns or 'Custo Considerado' not in df.columns:
                return jsonify({'erro': 'Colunas Codigo e Custo Considerado sao obrigatorias'}), 400

            atualizados = 0
            erros = []

            for idx, row in df.iterrows():
                try:
                    cod_produto = str(row['Codigo']).strip()
                    custo = row['Custo Considerado']

                    if pd.isna(custo) or custo == '':
                        continue

                    resultado = ServicoCusteio.cadastrar_custo_manual(
                        cod_produto=cod_produto,
                        custo_considerado=float(custo),
                        custo_producao=None,
                        tipo_custo='MANUAL',
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
