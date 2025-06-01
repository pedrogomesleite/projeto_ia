import json
import os
import hashlib # Para criar um ID original único se não houver um no JSON
import db # Importa o módulo db.py que acabamos de criar

# Adapte este caminho para o seu arquivo JSON de questões processado
# É CRUCIAL que este JSON contenha o campo "gabarito" para cada questão.
JSON_QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), 'data','tratado', 'enem_questoes_c_op.json')
# Exemplo de como seria um item no JSON com gabarito:
# {
#   "enunciado": "Qual a capital do Brasil?",
#   "area": "geografia",
#   "alternativas": ["A) Rio de Janeiro", "B) São Paulo", "C) Brasília", "D) Salvador", "E) Belo Horizonte"],
#   "gabarito": "C" 
#   "original_id_from_source": "enem2023_q15" (opcional, mas bom ter)
# }


def carregar_json_questoes(caminho_arquivo):
    """Carrega os dados de questões de um arquivo JSON."""
    if not os.path.exists(caminho_arquivo):
        print(f"Arquivo JSON de questões não encontrado em: {caminho_arquivo}")
        return []
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return dados
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        return []
    except Exception as e:
        print(f"Erro ao ler arquivo JSON: {e}")
        return []

def popular_db_com_questoes():
    """Popula o banco de dados com as questões do arquivo JSON."""
    print(f"Carregando questões de: {JSON_QUESTIONS_PATH}")
    questoes_data = carregar_json_questoes(JSON_QUESTIONS_PATH)

    if not questoes_data:
        print("Nenhuma questão carregada do JSON. Verifique o caminho e o conteúdo do arquivo.")
        print("Lembre-se: o JSON precisa ter 'enunciado', 'area', 'alternativas' e 'gabarito'.")
        return

    print(f"Encontradas {len(questoes_data)} questões no JSON.")
    
    added_count = 0
    for i, q_data in enumerate(questoes_data):
        enunciado = q_data.get('enunciado')
        area = q_data.get('area')
        alternativas = q_data.get('alternativas') # Deve ser uma lista
        gabarito = q_data.get('gabarito') # Ex: "A", "B", "C", "D", "E"
        
        # Tenta obter um ID original, se não existir, cria um hash do enunciado
        original_id = q_data.get('original_id_from_source') # Se você tiver um ID único da fonte
        if not original_id:
            # Cria um ID simples baseado no índice ou um hash mais robusto
            # original_id = f"q_{i+1}" 
            original_id = hashlib.md5(enunciado.encode('utf-8')).hexdigest() if enunciado else f"q_fallback_{i}"


        # Validação básica dos dados
        if not all([enunciado, area, alternativas, gabarito]):
            print(f"Questão {i+1} (ID: {original_id}) com dados incompletos. Pulando.")
            print(f"  Enunciado: {'OK' if enunciado else 'FALTA'}")
            print(f"  Área: {'OK' if area else 'FALTA'}")
            print(f"  Alternativas: {'OK' if alternativas and isinstance(alternativas, list) else 'FALTA/INVÁLIDO'}")
            print(f"  Gabarito: {'OK' if gabarito else 'FALTA'}")
            continue
        
        # Verifica se o gabarito é uma string simples (A-E)
        if not isinstance(gabarito, str) or not gabarito.isalpha() or len(gabarito) != 1:
            # Tenta extrair de alternativas como "A) Texto"
            found_gabarito = False
            if isinstance(alternativas, list) and alternativas:
                for alt_idx, alt_text in enumerate(alternativas):
                    if isinstance(alt_text, str) and alt_text.strip().upper().startswith(gabarito.upper()):
                        gabarito_letra = chr(ord('A') + alt_idx)
                        print(f"INFO: Gabarito inferido para questão {original_id} como '{gabarito_letra}' a partir da alternativa que casa com '{gabarito}'.")
                        gabarito = gabarito_letra
                        found_gabarito = True
                        break
            if not found_gabarito:
                print(f"AVISO: Gabarito '{gabarito}' para questão {original_id} não parece ser uma letra de alternativa válida (A-E). Verifique os dados.")
                # Você pode decidir pular esta questão ou tentar um tratamento mais robusto
                # continue 

        db.add_question(original_id, enunciado, area, alternativas, gabarito.upper())
        added_count +=1

    print(f"{added_count} questões foram processadas e tentadas adicionar ao banco de dados.")

if __name__ == '__main__':
    print("Iniciando configuração do banco de dados...")
    # 1. Inicializa as tabelas (cria se não existirem)
    db.init_db()
    
    # 2. Popula com as questões
    # Verifique se o DB já foi populado para não duplicar (a função add_question já tem um try-except para IDs únicos)
    print("\nPopulando o banco de dados com questões...")
    popular_db_com_questoes()
    
    print("\nConfiguração do banco de dados concluída.")
    
    # Exemplo de verificação
    print("\nVerificando algumas questões no banco:")
    all_q = db.get_all_questions()
    if all_q:
        print(f"Total de questões no DB: {len(all_q)}")
        for i in range(min(2, len(all_q))): # Imprime as duas primeiras
            print(f"  ID: {all_q[i]['id']}, Área: {all_q[i]['area']}, Gabarito: {all_q[i]['gabarito']}")
            # print(f"    Enunciado: {all_q[i]['enunciado'][:50]}...")
            # print(f"    Alternativas: {json.loads(all_q[i]['alternativas'])[:1]}")
    else:
        print("Nenhuma questão encontrada no banco de dados após a população.")
