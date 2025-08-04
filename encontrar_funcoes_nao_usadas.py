import ast
import os

def encontrar_funcoes_dentro_de_arquivo(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=caminho_arquivo)

    funcoes_definidas = []
    chamadas_encontradas = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                continue  # ignora funções com decorador
            if node.name.startswith('_'):
                continue  # ignora funções privadas
            funcoes_definidas.append((node.name, node.lineno))

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                chamadas_encontradas.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                chamadas_encontradas.add(node.func.attr)

    return [
        (nome, linha)
        for nome, linha in funcoes_definidas
        if nome not in chamadas_encontradas
    ]


def procurar_em_projeto(diretorio_raiz="app"):
    resultado = {}

    for root, _, files in os.walk(diretorio_raiz):
        for file in files:
            if file.endswith(".py"):
                caminho_completo = os.path.join(root, file)
                funcoes = encontrar_funcoes_dentro_de_arquivo(caminho_completo)
                if funcoes:
                    resultado[caminho_completo] = funcoes

    return resultado


if __name__ == "__main__":
    funcoes_nao_usadas = procurar_em_projeto("app")  # ou "." para raiz

    if not funcoes_nao_usadas:
        print("Nenhuma função não usada foi encontrada.")
    else:
        print("Possíveis funções não utilizadas:")
        for arquivo, funcoes in funcoes_nao_usadas.items():
            print(f"\n📄 {arquivo}:")
            for nome, linha in funcoes:
                print(f"  - {nome} (linha {linha})")
