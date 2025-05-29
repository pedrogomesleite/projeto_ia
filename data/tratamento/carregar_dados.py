import json
import os

def carregar_json(caminho_relativo):
    caminho_absoluto = os.path.join(os.path.dirname(__file__), caminho_relativo)

    try:
        with open(caminho_absoluto, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
            return dados

    except FileNotFoundError:
        print(f"Arquivo não encontrado: {caminho_relativo}")
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
    
    return []

if __name__ == "__main__":
    caminho = '../tratado/enem_questoes_c_op.json' 
    dados_tratados = carregar_json(caminho)

    for i, item in enumerate(dados_tratados):
        print(item)
