# BACKUP DAS ROTAS REMOVIDAS - 22/07/2025
# Estas rotas foram removidas por não serem utilizadas no template

# ROTA 1 - REMOVIDA linha 347-378
@carteira_bp.route('/item/<int:item_id>/endereco')
@login_required
def buscar_endereco_item(item_id: int) -> Union[Response, Tuple[Response, int]]:
    """API para buscar dados de endereço de um item da carteira"""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('carteira_principal'):
            return jsonify({'error': 'Sistema não inicializado'}), 400
            
        item = CarteiraPrincipal.query.get_or_404(item_id)
        
        # Retornar dados do endereço em formato JSON
        dados_endereco = {
            'id': item.id,
            'estado': item.estado,
            'municipio': item.municipio,
            'cnpj_endereco_ent': item.cnpj_endereco_ent,
            'empresa_endereco_ent': item.empresa_endereco_ent,
            'cod_uf': item.cod_uf,
            'nome_cidade': item.nome_cidade,
            'bairro_endereco_ent': item.bairro_endereco_ent,
            'cep_endereco_ent': item.cep_endereco_ent,
            'rua_endereco_ent': item.rua_endereco_ent,
            'endereco_ent': item.endereco_ent,
            'telefone_endereco_ent': item.telefone_endereco_ent
        }
        
        return jsonify(dados_endereco)
        
    except Exception as e:
        logger.error(f"Erro ao buscar endereço do item {item_id}: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ROTA 2 - GET removido, mantido apenas POST (linha 380-417)
# Removido o GET de agendamento_item pois só POST é usado