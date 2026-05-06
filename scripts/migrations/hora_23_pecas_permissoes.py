"""Migration HORA 23: data fix — admins ja recebem perm de pecas_cadastro/pecas_estoque
automaticamente (decorator nao exige entry para admin); este script e apenas
documentacao e ponto de extensao caso queira ativar perm para usuarios nao-admin.

Sem DDL — apenas registra que os modulos novos foram adicionados em MODULOS_HORA.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.hora.models.permissao import MODULOS_HORA


def main():
    app = create_app()
    with app.app_context():
        modulos_alvo = {'pecas_cadastro', 'pecas_estoque'}
        existentes = {m for m, _ in MODULOS_HORA}
        faltando = modulos_alvo - existentes
        if faltando:
            raise SystemExit(f'ERRO: modulos {faltando} ausentes em MODULOS_HORA. '
                             f'Atualize app/hora/models/permissao.py.')
        print(f'OK - {modulos_alvo} presentes em MODULOS_HORA.')
        print('Admins (perfil="administrador") ja tem acesso por default.')
        print('Para conceder a usuarios nao-admin: tela /hora/permissoes')


if __name__ == '__main__':
    main()
