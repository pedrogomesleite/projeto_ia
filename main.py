import random
import json
import sys
import os

# Adiciona o diretório raiz ao sys.path para garantir que os módulos sejam encontrados
# Isso é útil se você executar o main.py de outros diretórios ou em alguns setups
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_rest import db # Importa o módulo db.py da pasta api_rest
from agentes.fuzzy_agent import FuzzyAgente
from agentes.mock_exam_generator_agent import MockExamGeneratorAgent
from agentes.feedback_agent import FeedbackAgent
from agentes.study_card_agent import StudyCardAgent
from werkzeug.security import generate_password_hash # Para criar usuário de teste

# --- Configurações ---
ASSUMED_USER_ID = 1 # ID do usuário de teste principal
DEFAULT_MOCK_EXAM_QUESTIONS = 5 # Número de questões para simulados de teste

# --- Funções Auxiliares de Povoamento ---
def initialize_and_populate_db():
    """Inicializa o DB e adiciona dados de teste se necessário."""
    print("--- Inicializando e Verificando Banco de Dados ---")
    db.init_db() # Garante que todas as tabelas existam

    # Adicionar um usuário de teste se não existir
    test_user = db.get_user_by_id(ASSUMED_USER_ID)
    if not test_user:
        print(f"Usuário de teste ID {ASSUMED_USER_ID} não encontrado. Criando...")
        hashed_pass = generate_password_hash("testpass123")
        db.add_user(f"testuser{ASSUMED_USER_ID}", f"test{ASSUMED_USER_ID}@example.com", hashed_pass)
        test_user = db.get_user_by_id(ASSUMED_USER_ID) # Tenta buscar novamente
    
    if test_user:
        print(f"Usuário de teste (ID: {test_user['id']}, Username: {test_user['username']}) pronto.")
    else:
        print(f"Falha ao criar/obter usuário de teste ID {ASSUMED_USER_ID}. Verifique db.py.")
        return False

    # Adicionar algumas questões de teste se o banco estiver vazio
    # (O script carregar_dados.py seria o ideal para um povoamento completo)
    if not db.get_questions_by_criteria_db(limit=1):
        print("Nenhuma questão encontrada. Adicionando algumas questões de exemplo...")
        questions_data = [
            {
                "enunciado": "Qual a capital da França?",
                "alternativas": {"A": "Berlim", "B": "Madri", "C": "Paris", "D": "Lisboa", "E": "Roma"},
                "alternativa_correta": "C", "area_conhecimento": "Conhecimentos Gerais", "conteudo": "Geografia",
            },
            {
                "enunciado": "Quanto é 2 + 2?",
                "alternativas": {"A": "3", "B": "4", "C": "5", "D": "22"},
                "alternativa_correta": "B", "area_conhecimento": "Matemática", "conteudo": "Aritmética",
            },
            {
                "enunciado": "Quem escreveu 'Dom Casmurro'?",
                "alternativas": {"A": "José de Alencar", "B": "Carlos Drummond de Andrade", "C": "Machado de Assis", "D": "Cecília Meireles"},
                "alternativa_correta": "C", "area_conhecimento": "Linguagens, Códigos e suas Tecnologias", "conteudo": "Literatura Brasileira",
            },
            {
                "enunciado": "Qual elemento químico tem o símbolo 'O'?",
                "alternativas": {"A": "Ouro", "B": "Oxigênio", "C": "Osvaldo", "D": "Ozônio"},
                "alternativa_correta": "B", "area_conhecimento": "Ciências da Natureza e suas Tecnologias", "conteudo": "Química",
            },
            {
                "enunciado": "Em que ano o homem pisou na Lua pela primeira vez?",
                "alternativas": {"A": "1965", "B": "1969", "C": "1971", "D": "1973"},
                "alternativa_correta": "B", "area_conhecimento": "Ciências Humanas e suas Tecnologias", "conteudo": "História Geral",
            }
        ]
        for q_data in questions_data:
            db.add_question_db(
                enunciado=q_data["enunciado"],
                alternativas=q_data["alternativas"],
                alternativa_correta=q_data["alternativa_correta"],
                area_conhecimento=q_data["area_conhecimento"],
                conteudo=q_data["conteudo"]
            )
        print(f"{len(questions_data)} questões de exemplo adicionadas.")
    else:
        print("Banco de dados já contém questões.")
    print("--- Inicialização Concluída ---")
    return True

# --- Função Principal de Demonstração do Fluxo ---
def run_system_demonstration(user_id: int):
    print(f"\n--- Iniciando Demonstração para Usuário ID: {user_id} ---")

    # Agentes
    mock_exam_agent = MockExamGeneratorAgent()
    fuzzy_agent = FuzzyAgente()
    feedback_agent = FeedbackAgent()
    study_card_agent = StudyCardAgent()

    # 1. Gerar um Simulado
    print("\n[Passo 1: Gerando Simulado]")
    # Para teste, podemos pegar todas as áreas de conhecimento das questões existentes
    all_questions_sample = db.get_questions_by_criteria_db(limit=10) # Pega algumas para extrair áreas
    areas_disponiveis = list(set(q['area_conhecimento'] for q in all_questions_sample if q.get('area_conhecimento')))
    
    simulado_gerado = mock_exam_agent.generate_mock_exam(
        user_id=user_id,
        num_questions=DEFAULT_MOCK_EXAM_QUESTIONS,
        areas_conhecimento=areas_disponiveis[:1] if areas_disponiveis else None # Pega a primeira área disponível ou nenhuma
    )

    if not simulado_gerado or not simulado_gerado.get("questions"):
        print("Falha ao gerar simulado ou simulado sem questões. Encerrando demonstração para este usuário.")
        return
    
    mock_exam_id = simulado_gerado["mock_exam_id"]
    questions_in_exam = simulado_gerado["questions"] # Lista de dicts de questões
    print(f"Simulado ID {mock_exam_id} gerado com {len(questions_in_exam)} questões.")
    for q_idx, q_exam in enumerate(questions_in_exam):
        print(f"  Questão {q_idx+1} (ID: {q_exam['id']}): {q_exam['enunciado'][:50]}...")

    # 2. Simular Respostas do Usuário
    print("\n[Passo 2: Simulando Respostas do Usuário]")
    user_answers_submitted = []
    possible_choices = ["A", "B", "C", "D", "E"] # Assumindo até 5 alternativas

    for q_exam in questions_in_exam:
        question_id = q_exam['id']
        # Simula uma escolha aleatória (numa app real, viria do usuário)
        # Tenta pegar as chaves das alternativas reais, se não, usa A-E
        actual_alternatives = list(q_exam.get('alternativas', {}).keys())
        if not actual_alternatives: # Fallback se 'alternativas' não for um dict com chaves
            actual_alternatives = possible_choices[:len(q_exam.get('alternativas', []))] # Se for lista de strings
            if not actual_alternatives: actual_alternatives = possible_choices

        user_choice = random.choice(actual_alternatives) if actual_alternatives else random.choice(possible_choices)
        is_correct = (user_choice.upper() == q_exam['alternativa_correta'].upper())
        
        answer_id = db.add_answer_db(user_id, question_id, user_choice, is_correct, mock_exam_id)
        if answer_id:
            print(f"  Usuário respondeu à questão ID {question_id} com '{user_choice}'. Correto: {is_correct}. (Resposta ID: {answer_id})")
            user_answers_submitted.append({"question_id": question_id, "is_correct": is_correct})
        else:
            print(f"  Falha ao registrar resposta para questão ID {question_id}.")

    if not user_answers_submitted:
        print("Nenhuma resposta foi submetida com sucesso. Não é possível continuar o processamento.")
        return

    # 3. Processar Respostas: Atualizar Estatísticas das Questões e Proficiência do Usuário
    print("\n[Passo 3: Processando Respostas e Atualizando Estatísticas]")
    
    # 3a. Atualizar Estatísticas das Questões respondidas no simulado
    for q_exam in questions_in_exam:
        question_id = q_exam['id']
        answers_for_this_q = db.get_answers_for_question_db(question_id)
        total_q_answers = len(answers_for_this_q)
        correct_q_answers = sum(1 for ans in answers_for_this_q if ans['is_correct'])
        
        indice_acerto_q = 0.0
        if total_q_answers > 0:
            indice_acerto_q = (correct_q_answers / total_q_answers) * 100
        
        fuzzy_difficulty_output = fuzzy_agent.classificar_dificuldade_questao(indice_acerto_q)
        nova_dificuldade_str = fuzzy_difficulty_output['classificacao_dificuldade']
        
        if db.update_question_stats_db(question_id, indice_acerto_q, nova_dificuldade_str):
            print(f"  Estatísticas da Questão ID {question_id} atualizadas: IC Geral={indice_acerto_q:.2f}%, Dificuldade='{nova_dificuldade_str}'")
        else:
            print(f"  Falha ao atualizar estatísticas da Questão ID {question_id}")

    # 3b. Atualizar Proficiência do Usuário com base no desempenho no simulado
    total_exam_questions_answered = len(user_answers_submitted) # ou len(questions_in_exam) se todas foram respondidas
    correct_exam_answers = sum(1 for ans in user_answers_submitted if ans['is_correct'])
    
    percentual_acerto_simulado = 0.0
    if total_exam_questions_answered > 0:
        percentual_acerto_simulado = (correct_exam_answers / total_exam_questions_answered) * 100
        
    fuzzy_proficiency_output = fuzzy_agent.avaliar_proficiencia_usuario(percentual_acerto_simulado)
    novo_nivel_proficiencia_str = fuzzy_proficiency_output['proficiencia_usuario']
    
    if db.update_user_proficiency_db(user_id, novo_nivel_proficiencia_str):
        print(f"  Proficiência do Usuário ID {user_id} atualizada para '{novo_nivel_proficiencia_str}' (Acerto no simulado: {percentual_acerto_simulado:.2f}%).")
        # Mostrar o perfil do usuário atualizado
        user_profile = db.get_user_by_id(user_id)
        if user_profile:
            print(f"  Perfil atualizado: Username='{user_profile['username']}', Nível='{user_profile['nivel_proficiencia']}'")
    else:
        print(f"  Falha ao atualizar proficiência do Usuário ID {user_id}.")

    # Marcar simulado como concluído
    db.update_mock_exam_status_db(mock_exam_id, "Concluído")
    print(f"  Simulado ID {mock_exam_id} marcado como 'Concluído'.")

    # 4. Gerar Feedback para o Simulado
    print("\n[Passo 4: Gerando Feedback]")
    feedback_gerado = feedback_agent.generate_feedback_for_mock_exam(user_id, mock_exam_id)
    if feedback_gerado:
        print(f"  Feedback ID {feedback_gerado['feedback_id']} gerado:")
        print("  Conteúdo do Feedback:")
        for line in feedback_gerado['content'].split('\n'):
            print(f"    {line}")
    else:
        print("  Falha ao gerar feedback para o simulado.")

    # 5. Criar Flashcards para algumas questões (ex: as erradas ou uma aleatória)
    print("\n[Passo 5: Gerando Flashcards]")
    questions_to_make_flashcards_for = []
    # Tenta pegar uma questão que o usuário errou no simulado
    for ans_info in user_answers_submitted:
        if not ans_info['is_correct']:
            questions_to_make_flashcards_for.append(ans_info['question_id'])
            break # Pega a primeira errada
    
    # Se não errou nenhuma, ou para garantir, pega uma aleatória do simulado
    if not questions_to_make_flashcards_for and questions_in_exam:
        questions_to_make_flashcards_for.append(random.choice(questions_in_exam)['id'])
    
    if questions_to_make_flashcards_for:
        for q_id_flash in questions_to_make_flashcards_for:
            question_data_for_flashcard = db.get_question_by_id_db(q_id_flash)
            if question_data_for_flashcard:
                # O StudyCardAgent espera um objeto com atributos, vamos simular
                class QuestionObject:
                    def __init__(self, **kwargs):
                        self.__dict__.update(kwargs)
                
                question_obj = QuestionObject(**question_data_for_flashcard)
                flashcard_dict = study_card_agent.criar_flashcard(question_obj)
                
                # Salvar no banco
                flashcard_id_db = db.add_flashcard_db(
                    user_id, 
                    q_id_flash, 
                    flashcard_dict['frente'], 
                    flashcard_dict['verso']
                )
                if flashcard_id_db:
                    print(f"  Flashcard ID {flashcard_id_db} criado e salvo para Questão ID {q_id_flash}:")
                    print(f"    Frente: {flashcard_dict['frente'][:60]}...")
                    print(f"    Verso: {flashcard_dict['verso'][:60]}...")
                else:
                    print(f"  Falha ao salvar flashcard para Questão ID {q_id_flash}")
            else:
                print(f"  Não foi possível encontrar dados da Questão ID {q_id_flash} para criar flashcard.")
    else:
        print("  Nenhuma questão selecionada para criar flashcards.")

    print(f"\n--- Demonstração para Usuário ID: {user_id} Concluída ---")


# --- Bloco Principal de Execução ---
if __name__ == '__main__':
    print("--- Iniciando Sistema de Agentes de Estudo ENEM (main.py) ---")

    if not initialize_and_populate_db():
        print("Encerrando devido a falha na inicialização do banco de dados.")
        sys.exit(1) # Sai do script se não conseguir inicializar o básico

    # Executar a demonstração para o usuário de teste principal
    run_system_demonstration(ASSUMED_USER_ID)
    
    # Você poderia adicionar um menu aqui para interagir com o sistema,
    # ou simular múltiplos usuários/ações.

    print("\n--- Execução de main.py Concluída ---")
