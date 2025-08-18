"""
Rotas do Plano Mestre de Produção
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import PlanoMestreProducao
from app.manufatura.services.plano_mestre_service import PlanoMestreService
from app.manufatura.services.demanda_service import DemandaService
from datetime import datetime


def register_plano_mestre_routes(bp):
    
    @bp.route('/plano-mestre')
    @login_required
    def plano_mestre():
        """Tela de gestão do Plano Mestre de Produção"""
        return render_template('manufatura/plano_mestre.html')
    
    @bp.route('/api/plano-mestre/gerar', methods=['POST'])
    @login_required
    def gerar_plano_mestre():
        """Gera plano mestre baseado na previsão de demanda"""
        try:
            dados = request.json if request.is_json else request.form
            mes = int(dados.get('mes'))
            ano = int(dados.get('ano'))
            
            service = PlanoMestreService()
            resultado = service.gerar_plano_mestre(
                mes, ano,
                usuario=current_user.username if current_user.is_authenticated else 'Sistema'
            )
            
            # Ajuste para novo formato de retorno
            if isinstance(resultado, dict):
                criados = resultado.get('criados', [])
                atualizados = resultado.get('atualizados', [])
                total = len(criados) + len(atualizados)
                mensagem = f'{len(criados)} planos criados, {len(atualizados)} atualizados'
            else:
                # Compatibilidade com versão antiga
                criados = resultado
                total = len(resultado)
                mensagem = f'{total} planos criados'
            
            return jsonify({
                'sucesso': True,
                'mensagem': mensagem,
                'planos_criados': len(criados) if isinstance(resultado, dict) else total,
                'planos_atualizados': len(atualizados) if isinstance(resultado, dict) else 0
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/listar')
    @login_required
    def listar_planos():
        """Lista planos mestre de produção"""
        try:
            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)
            
            query = PlanoMestreProducao.query
            if mes:
                query = query.filter_by(data_mes=mes)
            if ano:
                query = query.filter_by(data_ano=ano)
            
            planos = query.order_by(PlanoMestreProducao.cod_produto).all()
            
            return jsonify([{
                'id': p.id,
                'mes': p.data_mes,
                'ano': p.data_ano,
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_demanda_prevista': float(p.qtd_demanda_prevista or 0),
                'qtd_estoque': float(p.qtd_estoque or 0),
                'qtd_estoque_seguranca': float(p.qtd_estoque_seguranca or 0),
                'qtd_reposicao_sugerida': float(p.qtd_reposicao_sugerida or 0),
                'qtd_producao_programada': float(p.qtd_producao_programada or 0),
                'qtd_producao_realizada': float(p.qtd_producao_realizada or 0),
                'disparo_producao': p.disparo_producao,
                'status_geracao': p.status_geracao
            } for p in planos])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/<int:id>/atualizar', methods=['POST'])
    @login_required
    def atualizar_plano(id):
        """Atualiza plano mestre (estoque segurança, etc)"""
        try:
            plano = PlanoMestreProducao.query.get_or_404(id)
            dados = request.json
            
            if 'qtd_estoque_seguranca' in dados:
                plano.qtd_estoque_seguranca = dados['qtd_estoque_seguranca']
            
            if 'qtd_lote_ideal' in dados:
                plano.qtd_lote_ideal = dados['qtd_lote_ideal']
            
            if 'qtd_lote_minimo' in dados:
                plano.qtd_lote_minimo = dados['qtd_lote_minimo']
            
            # Recalcular reposição sugerida
            service = PlanoMestreService()
            plano.qtd_reposicao_sugerida = service._calcular_reposicao_sugerida(plano)
            
            db.session.commit()
            
            return jsonify({'sucesso': True})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/<int:id>/aprovar', methods=['POST'])
    @login_required
    def aprovar_plano(id):
        """Aprova plano mestre para execução"""
        try:
            service = PlanoMestreService()
            plano = service.aprovar_plano(
                id,
                usuario=current_user.username if current_user.is_authenticated else 'Sistema'
            )
            
            return jsonify({
                'sucesso': True,
                'status': plano.status_geracao
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/resumo')
    @login_required
    def resumo_plano():
        """Obtém resumo do plano mestre"""
        try:
            mes = request.args.get('mes', datetime.now().month, type=int)
            ano = request.args.get('ano', datetime.now().year, type=int)
            
            service = PlanoMestreService()
            resumo = service.obter_resumo_plano(mes, ano)
            
            return jsonify(resumo)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/demanda-ativa')
    @login_required
    def demanda_ativa():
        """Obtém demanda ativa (excluindo faturados)"""
        try:
            mes = request.args.get('mes', type=int)
            ano = request.args.get('ano', type=int)
            cod_produto = request.args.get('cod_produto')
            
            service = DemandaService()
            demanda = service.calcular_demanda_ativa(mes, ano, cod_produto)
            
            return jsonify(demanda)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/pedidos-urgentes')
    @login_required
    def pedidos_urgentes():
        """Lista pedidos urgentes que precisam produção"""
        try:
            dias = request.args.get('dias', 7, type=int)
            
            service = DemandaService()
            pedidos = service.obter_pedidos_urgentes(dias)
            
            return jsonify(pedidos)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/atualizar-lote', methods=['POST'])
    @login_required
    def atualizar_planos_lote():
        """Atualiza múltiplos planos mestre de uma vez"""
        try:
            dados = request.json
            planos_atualizados = 0
            
            for item in dados.get('planos', []):
                plano = PlanoMestreProducao.query.get(item['id'])
                if plano:
                    if 'qtd_estoque_seguranca' in item:
                        plano.qtd_estoque_seguranca = item['qtd_estoque_seguranca']
                    
                    if 'qtd_lote_ideal' in item:
                        plano.qtd_lote_ideal = item['qtd_lote_ideal']
                    
                    if 'qtd_lote_minimo' in item:
                        plano.qtd_lote_minimo = item['qtd_lote_minimo']
                    
                    # Recalcular reposição sugerida
                    service = PlanoMestreService()
                    plano.qtd_reposicao_sugerida = service._calcular_reposicao_sugerida(plano)
                    
                    planos_atualizados += 1
            
            db.session.commit()
            
            return jsonify({
                'sucesso': True,
                'planos_atualizados': planos_atualizados
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/plano-mestre/calcular-producao-programada', methods=['GET'])
    @login_required
    def calcular_producao_programada():
        """Calcula qtd_producao_programada para todos os produtos"""
        try:
            mes = request.args.get('mes', datetime.now().month, type=int)
            ano = request.args.get('ano', datetime.now().year, type=int)
            
            service = PlanoMestreService()
            
            # Buscar todos os planos do período
            planos = PlanoMestreProducao.query.filter_by(
                data_mes=mes,
                data_ano=ano
            ).all()
            
            atualizados = 0
            for plano in planos:
                # Recalcular produção programada
                producao_programada = service._calcular_producao_programada(
                    plano.cod_produto, mes, ano
                )
                
                if plano.qtd_producao_programada != producao_programada:
                    plano.qtd_producao_programada = producao_programada
                    # Recalcular reposição sugerida
                    plano.qtd_reposicao_sugerida = service._calcular_reposicao_sugerida(plano)
                    atualizados += 1
            
            db.session.commit()
            
            return jsonify({
                'sucesso': True,
                'planos_atualizados': atualizados,
                'total_planos': len(planos)
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500