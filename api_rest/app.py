from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash # Para senhas

# Importar funções do db.py que usa sqlite3 diretamente
# O ponto antes de db indica que db.py está no mesmo diretório (api_rest)
from .db import (
    add_user,
    get_user_by_username,
    get_user_by_id, # Adicionado para consistência, se necessário
    get_question_by_id_db,
    get_questions_for_mock_exam_db,
    add_answer_db,
    update_mock_exam_status_db,
    get_feedback_for_user_db,
    create_mock_exam_db, # Adicionado para uso pelo agente
    update_question_stats_db, # Renomeado de update_question_stats_and_difficulty
    update_user_proficiency_db, # Renomeado de update_user_proficiency_after_exam
    create_feedback_db, # Adicionado para uso pelo agente
    add_flashcard_db, # Adicionado para persistir flashcards
    get_flashcards_for_user_db # Adicionado para buscar flashcards
)

# Importe seus agentes
# Se 'agentes' é um diretório no mesmo nível que 'api_rest' (projeto_ia/agentes)
# e você executa o app de dentro de 'api_rest' ou 'api_rest' é um módulo,
# o import pode precisar ser relativo: from ..agentes.fuzzy_agent import FuzzyAgente
# Ou, se 'agentes' estiver dentro de 'api_rest': from .agentes.fuzzy_agent import FuzzyAgente
# Vou manter como você forneceu, assumindo que o Python path está configurado
# ou que 'agentes' é um módulo instalável/acessível.
# Para um projeto estruturado com 'app.py' dentro de 'api_rest', e 'agentes' como irmão de 'api_rest',
# seria mais comum executar o app a partir do diretório raiz do projeto (projeto_ia)
# e os imports dos agentes não precisariam de ajuste se 'projeto_ia' estiver no PYTHONPATH.
# Se 'agentes' está no mesmo nível que 'app.py' (dentro de 'api_rest'), então seria:
# from .agentes.fuzzy_agent import FuzzyAgente (etc.)
# Assumindo que 'agentes' é um pacote no diretório pai de 'api_rest'
import sys
import os
# Adiciona o diretório pai de api_rest ao sys.path para encontrar o pacote 'agentes'
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agentes.fuzzy_agent import FuzzyAgente
from agentes.study_card_agent import StudyCardAgent
from agentes.mock_exam_generator_agent import MockExamGeneratorAgent # Ajuste o construtor deste agente
from agentes.feedback_agent import FeedbackAgent # Ajuste o construtor deste agente


app = Flask(__name__)

# Não há mais middleware de sessão SQLAlchemy

# --- Instâncias dos Agentes ---
# Os agentes agora não receberão mais uma sessão de DB no construtor.
# Eles devem chamar as funções de db.py diretamente, se necessário.
# fuzzy_agent = FuzzyAgente() # Instanciado quando necessário
# study_card_agent = StudyCardAgent() # Instanciado quando necessário

# --- Endpoints da API ---

@app.route('/')
def hello():
    return "Bem-vindo à API do Sistema de Estudos para o ENEM com SQLite!"

@app.route('/register', methods=['POST'])
def register_user_route():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "Dados incompletos (username, email, password são obrigatórios)"}), 400

    if len(password) < 6: # Exemplo de validação de senha
        return jsonify({"error": "Senha deve ter pelo menos 6 caracteres"}), 400

    hashed_password = generate_password_hash(password)
    
    user_id = add_user(username, email, hashed_password)

    if user_id:
        return jsonify({"message": "Usuário registrado com sucesso!", "user_id": user_id}), 201
    else:
        # A função add_user já imprime um erro mais específico no console
        return jsonify({"error": "Erro ao registrar usuário. Verifique se o username ou email já existem."}), 400


@app.route('/login', methods=['POST'])
def login_user_route():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username e password são obrigatórios"}), 400

    user = get_user_by_username(username)

    if user and check_password_hash(user['hashed_password'], password):
        # Em uma aplicação real, você geraria um token JWT aqui
        return jsonify({
            "message": "Login bem-sucedido!",
            "user_id": user['id'],
            "username": user['username']
            # Não retorne a senha hash!
        }), 200
    else:
        return jsonify({"error": "Credenciais inválidas"}), 401


@app.route('/users/<int:user_id>/mock_exams', methods=['POST'])
def generate_mock_exam_route(user_id):
    # Verifica se o usuário existe
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": f"Usuário com ID {user_id} não encontrado."}), 404

    data = request.get_json()
    num_questions = data.get('num_questions', 10)
    areas = data.get('areas_conhecimento') # Lista de strings
    conteudos = data.get('conteudos') # Lista de strings

    # O MockExamGeneratorAgent não recebe mais a sessão db.
    # Ele precisará ser adaptado para chamar as funções de db.py diretamente.
    # Por enquanto, vamos simular a chamada e a lógica que ele faria.
    
    # Lógica que estaria dentro do MockExamGeneratorAgent:
    # 1. Obter questões com base nos critérios
    questions_for_exam = get_questions_by_criteria_db(
        area_conhecimento=areas[0] if areas else None, # Simplificado para a primeira área
        conteudo=conteudos[0] if conteudos else None, # Simplificado para o primeiro conteúdo
        limit=num_questions
    )

    if not questions_for_exam:
        return jsonify({"error": "Nenhuma questão encontrada para os critérios fornecidos."}), 404
    
    question_ids = [q['id'] for q in questions_for_exam]

    # 2. Criar o registro do simulado no banco
    mock_exam_id = create_mock_exam_db(user_id, question_ids)

    if mock_exam_id:
        mock_exam_details = get_mock_exam_by_id_db(mock_exam_id)
        # As questões já foram buscadas e serializadas (alternativas) por get_questions_by_criteria_db
        return jsonify({
            "message": "Simulado gerado com sucesso!",
            "mock_exam_id": mock_exam_id,
            "user_id": user_id,
            "status": mock_exam_details.get('status', 'Pendente') if mock_exam_details else 'Pendente',
            "num_questions_generated": len(questions_for_exam),
            "questions": questions_for_exam # questions_for_exam já é uma lista de dicts com alternativas desserializadas
        }), 201
    else:
        return jsonify({"error": "Falha ao gerar simulado"}), 500


@app.route('/users/<int:user_id>/mock_exams/<int:mock_exam_id>/submit', methods=['POST'])
def submit_mock_exam_answers_route(user_id, mock_exam_id):
    # Verificar se usuário e simulado existem
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": f"Usuário com ID {user_id} não encontrado."}), 404
    
    mock_exam = get_mock_exam_by_id_db(mock_exam_id)
    if not mock_exam:
        return jsonify({"error": f"Simulado com ID {mock_exam_id} não encontrado."}), 404
    if mock_exam['user_id'] != user_id:
        return jsonify({"error": "Este simulado não pertence ao usuário especificado."}), 403
    if mock_exam['status'] == "Concluído":
        return jsonify({"error": "Este simulado já foi concluído."}), 400


    data = request.get_json()
    answers_data = data.get('answers') # Espera uma lista de respostas, ex: [{"question_id": X, "user_answer": "A"}, ...]

    if not answers_data:
        return jsonify({"error": "Nenhuma resposta fornecida"}), 400

    fuzzy_agent_instance = FuzzyAgente() # Instancia para usar nas atualizações

    for ans_data in answers_data:
        question_id = ans_data.get('question_id')
        user_choice = ans_data.get('user_answer')

        if question_id is None or user_choice is None:
            app.logger.warning(f"Resposta inválida ignorada: {ans_data}")
            continue

        question = get_question_by_id_db(question_id) # Retorna dict ou None
        if not question:
            app.logger.warning(f"Questão ID {question_id} não encontrada para a resposta.")
            continue 
        
        is_correct = (user_choice.upper() == question['alternativa_correta'].upper())
        
        add_answer_db(user_id, question_id, user_choice, is_correct, mock_exam_id)
        
        # Atualizar estatísticas da questão (índice de acerto geral e dificuldade)
        # Esta lógica precisa ser chamada após CADA resposta.
        answers_for_this_question = get_answers_for_question_db(question_id)
        total_answers_count = len(answers_for_this_question)
        correct_answers_count = sum(1 for ans in answers_for_this_question if ans['is_correct'])
        
        indice_acerto_geral_calc = 0.0
        if total_answers_count > 0:
            indice_acerto_geral_calc = (correct_answers_count / total_answers_count) * 100
        
        # Classificar dificuldade com FuzzyAgent
        nova_dificuldade_fuzzy_output = fuzzy_agent_instance.classificar_dificuldade_questao(indice_acerto_geral_calc)
        dificuldade_classificada_str = nova_dificuldade_fuzzy_output['classificacao_dificuldade']
        
        update_question_stats_db(question_id, indice_acerto_geral_calc, dificuldade_classificada_str)

    # Atualizar status do simulado para "Concluído"
    update_mock_exam_status_db(mock_exam_id, "Concluído")

    # Atualizar proficiência do usuário
    # Esta lógica é chamada APÓS todas as respostas do simulado serem processadas.
    all_answers_for_exam = get_answers_for_mock_exam_db(user_id, mock_exam_id)
    total_questions_in_exam = len(all_answers_for_exam)
    correct_answers_in_exam = sum(1 for ans in all_answers_for_exam if ans['is_correct'])
    
    percentual_acerto_simulado = 0.0
    if total_questions_in_exam > 0:
        percentual_acerto_simulado = (correct_answers_in_exam / total_questions_in_exam) * 100
    
    nova_proficiencia_fuzzy_output = fuzzy_agent_instance.avaliar_proficiencia_usuario(percentual_acerto_simulado)
    nivel_proficiencia_str = nova_proficiencia_fuzzy_output['proficiencia_usuario']
    update_user_proficiency_db(user_id, nivel_proficiencia_str)


    # Gerar feedback
    # O FeedbackAgent não recebe mais a sessão db.
    # feedback_agent = FeedbackAgent() # Se precisar de estado ou múltiplas chamadas
    # feedback_content = feedback_agent.generate_feedback_for_mock_exam(user_id, mock_exam_id) # Método precisa ser adaptado

    # Lógica simplificada do FeedbackAgent diretamente aqui:
    feedback_parts = []
    feedback_parts.append(f"Desempenho no Simulado ID {mock_exam_id}:")
    feedback_parts.append(f"Você acertou {correct_answers_in_exam} de {total_questions_in_exam} questões ({percentual_acerto_simulado:.2f}%).")
    feedback_parts.append(f"Seu novo nível de proficiência é: {nivel_proficiencia_str}.")
    # Adicionar mais detalhes ao feedback se necessário...
    feedback_content_str = "\n".join(feedback_parts)
    
    feedback_id = create_feedback_db(user_id, feedback_content_str, mock_exam_id)

    return jsonify({
        "message": "Respostas submetidas e processadas com sucesso!",
        "mock_exam_id": mock_exam_id,
        "feedback_generated": feedback_id is not None
    }), 200


@app.route('/users/<int:user_id>/feedback', methods=['GET'])
def get_user_feedback_route(user_id):
    # Verificar se usuário existe
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": f"Usuário com ID {user_id} não encontrado."}), 404

    mock_exam_id_filter = request.args.get('mock_exam_id', type=int) 
    
    feedbacks = get_feedback_for_user_db(user_id, mock_exam_id_filter) # Retorna lista de dicts
    if feedbacks:
        # Os dicts já estão prontos para jsonify, data_geracao é string do DB
        return jsonify(feedbacks), 200
    else:
        return jsonify({"message": "Nenhum feedback encontrado"}), 404


@app.route('/users/<int:user_id>/flashcards', methods=['POST'])
def create_flashcard_route(user_id):
    # Verificar se usuário existe
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": f"Usuário com ID {user_id} não encontrado."}), 404

    data = request.get_json()
    question_id = data.get('question_id')

    if not question_id:
        return jsonify({"error": "question_id é obrigatório"}), 400

    question_dict = get_question_by_id_db(question_id) # Retorna dict ou None
    if not question_dict:
        return jsonify({"error": "Questão não encontrada"}), 404

    study_card_agent = StudyCardAgent() 
    # O método criar_flashcard do agente espera um objeto "Question" com atributos.
    # Precisamos simular esse objeto a partir do dicionário ou adaptar o agente.
    # Para agora, vamos passar o dicionário e assumir que o agente pode lidar com isso
    # ou extrair os campos necessários.
    # Idealmente, o agente seria adaptado para aceitar um dicionário ou os campos individualmente.
    
    # Exemplo de como o agente poderia extrair os dados:
    # frente = question_dict['enunciado']
    # verso = f"Resposta: {question_dict['alternativa_correta']}\nÁrea: {question_dict.get('area_conhecimento', 'N/A')}"
    # flashcard_data_simulated = {"frente": frente, "verso": verso}

    # Se StudyCardAgent.criar_flashcard espera um objeto com atributos:
    class QuestionObject:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    question_obj_for_agent = QuestionObject(**question_dict)
    flashcard_data_from_agent = study_card_agent.criar_flashcard(question_obj_for_agent)
    
    # Salvar flashcard no banco
    flashcard_id = add_flashcard_db(
        user_id, 
        question_id, 
        flashcard_data_from_agent['frente'], 
        flashcard_data_from_agent['verso']
    )

    if flashcard_id:
        return jsonify({
            "message": "Flashcard gerado e salvo com sucesso!", 
            "flashcard_id": flashcard_id,
            "data": flashcard_data_from_agent
        }), 201
    else:
        return jsonify({"error": "Falha ao salvar o flashcard"}), 500

@app.route('/users/<int:user_id>/flashcards', methods=['GET'])
def get_user_flashcards_route(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": f"Usuário com ID {user_id} não encontrado."}), 404

    question_id_filter = request.args.get('question_id', type=int)
    flashcards = get_flashcards_for_user_db(user_id, question_id_filter)

    if flashcards:
        return jsonify(flashcards), 200
    else:
        return jsonify({"message": "Nenhum flashcard encontrado"}), 404


if __name__ == '__main__':
    # Para garantir que o DB seja inicializado se ainda não foi
    from .db import init_db # Importa init_db do mesmo diretório
    init_db() # Chama a função de inicialização do db.py
    
    # O app.py está dentro de api_rest, então o host 0.0.0.0 o torna acessível na rede local
    app.run(host='0.0.0.0', port=5000, debug=True)
