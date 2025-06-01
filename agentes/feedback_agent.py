import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
# Isso assume que 'agentes' é uma pasta dentro do diretório raiz do projeto
# e 'api_rest' também está no diretório raiz.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Importar funções do db.py que usa sqlite3 diretamente
from api_rest.db import (
    get_user_by_id,
    get_answers_for_mock_exam_db,
    get_question_by_id_db, # Usaremos a versão _db que retorna dict
    create_feedback_db,
    get_mock_exam_by_id_db # Adicionado para obter detalhes do simulado, se necessário
)

class FeedbackAgent:
    def __init__(self):
        """
        Construtor do Agente de Feedback.
        Não requer mais uma sessão de banco de dados.
        """
        pass

    def generate_feedback_for_mock_exam(self, user_id: int, mock_exam_id: int):
        """
        Gera feedback para um simulado concluído pelo usuário.

        Args:
            user_id: ID do usuário.
            mock_exam_id: ID do simulado.

        Returns:
            Um dicionário contendo o ID do feedback e seu conteúdo,
            ou None em caso de falha.
        """
        user = get_user_by_id(user_id) # Retorna dict ou None
        if not user:
            print(f"Usuário com ID {user_id} não encontrado.")
            return None

        mock_exam = get_mock_exam_by_id_db(mock_exam_id) # Retorna dict ou None
        if not mock_exam:
            print(f"Simulado com ID {mock_exam_id} não encontrado.")
            return None
        
        # Verifica se o simulado pertence ao usuário (opcional, mas bom para consistência)
        if mock_exam.get('user_id') != user_id:
            print(f"Alerta: O simulado {mock_exam_id} não pertence ao usuário {user_id}.")
            # Decide se quer prosseguir ou retornar um erro/None

        answers = get_answers_for_mock_exam_db(user_id, mock_exam_id) # Retorna lista de dicts
        if not answers:
            print(f"Nenhuma resposta encontrada para o usuário {user_id} no simulado {mock_exam_id}.")
            # Pode ser que o usuário não respondeu nada, ainda assim pode-se gerar um feedback.
            # Se for obrigatório ter respostas, retorne None aqui.
            # Por ora, vamos permitir gerar feedback mesmo sem respostas (score será 0).
            # return None 

        total_questions = len(answers)
        correct_answers_count = sum(1 for ans_dict in answers if ans_dict.get('is_correct'))
        
        score_percentage = 0.0
        if total_questions > 0:
            score_percentage = (correct_answers_count / total_questions) * 100

        feedback_parts = []
        feedback_parts.append(f"Desempenho no Simulado ID {mock_exam_id}:")
        if total_questions > 0:
            feedback_parts.append(f"Você acertou {correct_answers_count} de {total_questions} questões ({score_percentage:.2f}%).")
        else:
            feedback_parts.append("Você não respondeu a nenhuma questão neste simulado.")

        if score_percentage < 50:
            feedback_parts.append("Seu desempenho está abaixo do esperado. Continue estudando e refaça os exercícios.")
        elif score_percentage < 75:
            feedback_parts.append("Bom desempenho! Continue praticando para melhorar ainda mais.")
        else:
            feedback_parts.append("Excelente desempenho! Você está no caminho certo.")

        # Identificar áreas/conteúdos com mais erros
        errors_by_area = {}
        errors_by_conteudo = {}
        incorrectly_answered_question_ids = []

        for ans_dict in answers:
            if not ans_dict.get('is_correct'):
                question_id = ans_dict.get('question_id')
                question_dict = get_question_by_id_db(question_id) # Retorna dict
                if question_dict:
                    incorrectly_answered_question_ids.append(question_dict['id'])
                    area = question_dict.get('area_conhecimento')
                    conteudo = question_dict.get('conteudo')
                    
                    if area:
                        errors_by_area[area] = errors_by_area.get(area, 0) + 1
                    if conteudo:
                        errors_by_conteudo[conteudo] = errors_by_conteudo.get(conteudo, 0) + 1
        
        if errors_by_area:
            feedback_parts.append("\nÁreas com maior número de erros:")
            for area, count in sorted(errors_by_area.items(), key=lambda item: item[1], reverse=True):
                feedback_parts.append(f"- {area}: {count} erro(s)")
        
        if errors_by_conteudo:
            feedback_parts.append("\nConteúdos com maior número de erros:")
            for cont, count in sorted(errors_by_conteudo.items(), key=lambda item: item[1], reverse=True):
                feedback_parts.append(f"- {cont}: {count} erro(s)")
        
        if incorrectly_answered_question_ids:
            feedback_parts.append("\nSugestão: Revise as questões que você errou. Considere criar flashcards para elas.")
            # feedback_parts.append(f"IDs das questões erradas: {incorrectly_answered_question_ids}")


        full_feedback_content = "\n".join(feedback_parts)
        
        # Salvar o feedback no banco de dados
        # create_feedback_db retorna o ID do feedback criado
        new_feedback_id = create_feedback_db(user_id, full_feedback_content, mock_exam_id)
        
        if new_feedback_id:
            print(f"Feedback ID {new_feedback_id} gerado e salvo para o usuário {user_id}, simulado {mock_exam_id}.")
            return {
                "feedback_id": new_feedback_id,
                "user_id": user_id,
                "mock_exam_id": mock_exam_id,
                "content": full_feedback_content
            }
        else:
            print(f"Falha ao salvar o feedback para o usuário {user_id}, simulado {mock_exam_id}.")
            return None

# Exemplo de uso (seria chamado pela API ou outro módulo):
if __name__ == '__main__':
    # Este bloco só será executado se o script for chamado diretamente.
    # Requer que o banco de dados exista e tenha dados de teste.
    from api_rest.db import (
        init_db,
        add_user as add_user_db,
        add_question_db as add_question_db_sqlite,
        create_mock_exam_db as create_mock_exam_db_sqlite,
        add_answer_db as add_answer_db_sqlite
    )
    from werkzeug.security import generate_password_hash # Para o usuário de teste

    # init_db() # Comente após a primeira execução ou se já tiver dados

    # Adicionar usuário de teste
    test_user = get_user_by_id(1)
    if not test_user:
        print("Adicionando usuário de teste (ID 1) para FeedbackAgent...")
        add_user_db("feedback_tester", "feedback@example.com", generate_password_hash("feedbackpass"))
        test_user = get_user_by_id(1)

    if test_user:
        print(f"Usando usuário de teste para FeedbackAgent: {test_user.get('username')}")

        # Adicionar questões de teste
        q1_id, q2_id, q3_id = None, None, None
        if not get_question_by_id_db(1): # Checa se a questão 1 existe
            print("Adicionando questões de teste para FeedbackAgent...")
            q1_id = add_question_db_sqlite("Enunciado Q1 (Feed)", {"A":"1","B":"2"}, "A", "FeedArea1", "FeedCont1")
            q2_id = add_question_db_sqlite("Enunciado Q2 (Feed)", {"A":"x","B":"y"}, "B", "FeedArea1", "FeedCont2")
            q3_id = add_question_db_sqlite("Enunciado Q3 (Feed)", {"A":"z","B":"w"}, "A", "FeedArea2", "FeedCont3")
        else: # Se já existem, pega os IDs (simplificado, assumindo que são 1, 2, 3)
            q1_id, q2_id, q3_id = 1, 2, 3
            if not get_question_by_id_db(q3_id): q3_id = None # Garante que não use ID inválido

        question_ids_for_exam = [q_id for q_id in [q1_id, q2_id, q3_id] if q_id is not None]

        if not question_ids_for_exam:
            print("Nenhuma questão de teste disponível. Saindo do teste do FeedbackAgent.")
        else:
            # Criar um simulado de teste
            mock_exam_test_id = get_mock_exam_by_id_db(1) # Tenta pegar um simulado existente
            if mock_exam_test_id:
                mock_exam_test_id = mock_exam_test_id['id']
            else:
                print("Criando simulado de teste para FeedbackAgent...")
                mock_exam_test_id = create_mock_exam_db_sqlite(test_user['id'], question_ids_for_exam)

            if mock_exam_test_id:
                print(f"Usando simulado de teste ID: {mock_exam_test_id}")
                # Adicionar respostas de teste (simulando que o usuário fez o simulado)
                # Limpa respostas antigas para este simulado (se houver) para não duplicar no cálculo
                # (Em um sistema real, isso seria mais complexo)
                
                # Resposta 1 (correta)
                if q1_id: add_answer_db_sqlite(test_user['id'], q1_id, "A", True, mock_exam_test_id)
                # Resposta 2 (incorreta)
                if q2_id: add_answer_db_sqlite(test_user['id'], q2_id, "A", False, mock_exam_test_id)
                # Resposta 3 (correta)
                if q3_id: add_answer_db_sqlite(test_user['id'], q3_id, "A", True, mock_exam_test_id)

                feedback_agent = FeedbackAgent()
                print(f"\nGerando feedback para usuário ID {test_user['id']} e simulado ID {mock_exam_test_id}...")
                feedback_result = feedback_agent.generate_feedback_for_mock_exam(
                    user_id=test_user['id'],
                    mock_exam_id=mock_exam_test_id
                )

                if feedback_result:
                    print("\n--- Feedback Gerado ---")
                    print(f"ID do Feedback: {feedback_result['feedback_id']}")
                    print(feedback_result['content'])
                    print("-----------------------")
                else:
                    print("Falha ao gerar feedback.")
            else:
                print("Falha ao criar ou obter simulado de teste para o FeedbackAgent.")
    else:
        print("Usuário de teste não encontrado. Execute o db.py ou adicione um usuário manualmente para testar o FeedbackAgent.")

