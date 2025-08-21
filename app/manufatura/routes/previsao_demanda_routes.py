"""
Rotas de Previsão de Demanda
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import PrevisaoDemanda, GrupoEmpresarial
from datetime import datetime


def register_previsao_demanda_routes(bp):
    
    @bp.route('/previsao-demanda')
    @login_required
    def previsao_demanda():
        """Tela de gestão de previsão de demanda"""
        return render_template('manufatura/previsao_demanda.html')
    
    @bp.route('/api/previsao-demanda/listar')
    @login_required
    def listar_previsoes():
        """Lista previsões de demanda"""
        try:
            ano = request.args.get('ano', datetime.now().year, type=int)
            mes = request.args.get('mes', type=int)
            
            query = PrevisaoDemanda.query.filter_by(data_ano=ano)
            if mes:
                query = query.filter_by(data_mes=mes)
            
            previsoes = query.order_by(PrevisaoDemanda.data_mes, PrevisaoDemanda.cod_produto).all()
            
            return jsonify([{
                'id': p.id,
                'mes': p.data_mes,
                'ano': p.data_ano,
                'nome_grupo': p.nome_grupo,
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_demanda_prevista': float(p.qtd_demanda_prevista or 0),
                'qtd_demanda_realizada': float(p.qtd_demanda_realizada or 0),
                'disparo_producao': p.disparo_producao
            } for p in previsoes])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/criar', methods=['POST'])
    @login_required
    def criar_previsao():
        """Cria nova previsão de demanda"""
        try:
            dados = request.json
            
            previsao = PrevisaoDemanda(
                data_mes=dados['mes'],
                data_ano=dados['ano'],
                nome_grupo=dados.get('nome_grupo'),
                cod_produto=dados['cod_produto'],
                nome_produto=dados.get('nome_produto'),
                qtd_demanda_prevista=dados['qtd_prevista'],
                disparo_producao=dados.get('disparo_producao', 'MTS'),
                criado_por=current_user.nome if current_user.is_authenticated else 'Sistema'
            )
            
            db.session.add(previsao)
            db.session.commit()
            
            return jsonify({'sucesso': True, 'id': previsao.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/previsao-demanda/gerar-historico', methods=['POST'])
    @login_required
    def gerar_previsao_historico():
        """Gera previsão baseada no histórico"""
        try:
            from app.manufatura.services.demanda_service import DemandaService
            
            dados = request.json if request.is_json else request.form
            mes = int(dados.get('mes'))
            ano = int(dados.get('ano'))
            multiplicador = float(dados.get('multiplicador', 1.0))
            
            service = DemandaService()
            qtd_criada = service.criar_previsao_por_historico(mes, ano, multiplicador)
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'{qtd_criada} previsões criadas baseadas no histórico'
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500