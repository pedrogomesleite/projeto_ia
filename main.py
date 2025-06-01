import random
from api_rest import db # Importa o módulo db.py
import fuzzy_agent # Importa o módulo fuzzy_agent.py
# Para executar o database_setup.py se necessário:
# import database_setup

# --- Configurações da Simulação ---
TOTAL_SIMULATED_USERS = 1 # Para simplificar, começamos com 1 usuário
SIMULATED_ANSWERS_PER_QUESTION = 15 # Quantas vezes cada questão será "respondida" na simulação
ASSUMED_USER_ID = 1 # ID do usuário para o qual estamos rastreando o desempenho por matéria

def simulate_user_attempts():
    """
    Simula um usuário respondendo a várias questões para gerar dados de hit_rate
    e perfil de usuário.
    """
    print("\n--- Iniciando Simulação de Tentativas de Resposta ---")
    questions = db.get_all_questions()

    if not questions:
        print("Nenhuma questão encontrada no banco de dados para simular tentativas.")
        print("Por favor, execute primeiro o 'database_setup.py' para popular o banco.")
        return

    print(f"Simulando respostas para {len(questions)} questões.")
    
    for q_row in questions:
        question = dict(q_row) # Converte a linha do DB para um dicionário
        question_id = question['id']
        correct_answer = question['gabarito'] # Ex: "A", "B", ...
        area = question['area']
        
        # Simula várias tentativas para esta questão
        for _ in range(SIMULATED_ANSWERS_PER_QUESTION):
            # Simula uma resposta do usuário (aleatoriamente A, B, C, D ou E)
            # Numa aplicação real, esta seria a entrada do usuário.
            possible_choices = ["A", "B", "C", "D", "E"]
            user_choice = random.choice(possible_choices)
            
            is_correct = (user_choice == correct_answer.upper())
            
            # Atualiza as tentativas da questão no DB
            db.update_question_attempts(question_id, is_correct)
            
            # Atualiza o perfil de desempenho do usuário para esta matéria
            db.update_user_subject_profile(ASSUMED_USER_ID, area, is_correct)

    print("--- Simulação de Tentativas Concluída ---")

def display_sample_question_stats():
    """Mostra estatísticas de algumas questões após a simulação."""
    print("\n--- Estatísticas de Amostra de Questões (Pós-Simulação) ---")
    questions = db.get_all_questions()
    if not questions:
        print("Nenhuma questão no banco para mostrar estatísticas.")
        return
        
    sample_size = min(5, len(questions)) # Mostra até 5 questões
    for i in range(sample_size):
        q = dict(questions[i])
        print(f"ID: {q['id']}, Área: {q['area']}")
        print(f"  Tentativas: {q['total_attempts']}, Acertos: {q['correct_attempts']}, Hit Rate: {q['hit_rate']:.2f}")
        print(f"  Dificuldade Fuzzy (antes): Label='{q['fuzzy_difficulty_label']}', Score={q['fuzzy_difficulty_score']}")

def display_user_profile():
    """Mostra o perfil de desempenho do usuário por matéria."""
    print("\n--- Perfil de Desempenho do Usuário (Pós-Simulação) ---")
    profiles = db.get_user_subject_profiles(ASSUMED_USER_ID)
    if not profiles:
        print(f"Nenhum perfil encontrado para o usuário ID {ASSUMED_USER_ID}.")
        return
    
    print(f"Desempenho do Usuário ID {ASSUMED_USER_ID} por Matéria (ordenado por maior dificuldade percebida):")
    for profile_row in profiles:
        profile = dict(profile_row)
        print(f"  Matéria: {profile['area']}")
        print(f"    Questões Respondidas: {profile['total_questions_answered']}")
        print(f"    Acertos: {profile['correct_questions_answered']}")
        print(f"    Taxa de Acerto na Matéria: {profile['user_area_hit_rate']:.2f}")
        print(f"    Score de Fraqueza Percebida: {profile['perceived_weakness_score']:.2f}")


if __name__ == '__main__':
    print("--- Iniciando Sistema de Agentes de Estudo ENEM ---")

    # Passo 0: (Opcional, mas recomendado)
    # Verificar se o DB existe e está populado. Se não, sugerir rodar database_setup.py
    # Para este script, vamos assumir que database_setup.py já foi executado.
    # Se quiser automatizar:
    # if not db.get_all_questions(): # Verifica se há questões
    #     print("Banco de dados parece vazio. Executando database_setup.py...")
    #     database_setup.init_db() # Garante que as tabelas existam
    #     database_setup.popular_db_com_questoes()
    # else:
    #     print("Banco de dados já populado.")

    # Passo 1: Simular tentativas de usuários para gerar dados de hit_rate
    # Numa aplicação real, isso aconteceria organicamente com o uso.
    simulate_user_attempts()
    
    # Mostrar algumas estatísticas após a simulação
    display_sample_question_stats()
    display_user_profile()

    # Passo 2: Executar o Agente Classificador de Dificuldade
    difficulty_agent = fuzzy_agent.DifficultyClassifierAgent()
    difficulty_agent.run_classification()

    # Mostrar estatísticas novamente para ver a dificuldade fuzzy aplicada
    print("\n--- Estatísticas de Amostra de Questões (Pós-Classificação Fuzzy) ---")
    questions_after_fuzzy = db.get_all_questions()
    if questions_after_fuzzy:
        sample_size = min(5, len(questions_after_fuzzy))
        for i in range(sample_size):
            q = dict(questions_after_fuzzy[i])
            print(f"ID: {q['id']}, Área: {q['area']}")
            print(f"  Hit Rate: {q['hit_rate']:.2f}")
            print(f"  Dificuldade Fuzzy (depois): Label='{q['fuzzy_difficulty_label']}', Score={q['fuzzy_difficulty_score']:.2f if q['fuzzy_difficulty_score'] else 'N/A'}")
    
    # Próximos passos (a serem implementados):
    # - Criar e executar o Agente Montador de Cards de Estudo
    # - Interface do usuário (web, console, etc.)

    print("\n--- Sistema de Agentes de Estudo ENEM Concluído (Fase Atual) ---")
