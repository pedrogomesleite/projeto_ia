import random
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
# Isso assume que 'agentes' é uma pasta dentro do diretório raiz do projeto
# e 'api_rest' também está no diretório raiz.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Importar funções do db.py que usa sqlite3 diretamente
# Ajuste o caminho conforme a estrutura do seu projeto.
# Se api_rest.db está em ../api_rest/db.py
from api_rest.db import (
    get_user_by_id,
    get_questions_by_criteria_db,
    create_mock_exam_db,
    get_mock_exam_by_id_db # Adicionado para buscar detalhes após a criação
)

class MockExamGeneratorAgent:
    def __init__(self):
        """
        Construtor do Agente Gerador de Simulados.
        Não requer mais uma sessão de banco de dados, pois as funções de db.py
        gerenciam suas próprias conexões.
        """
        pass

    def generate_mock_exam(self, user_id: int, num_questions: int, areas_conhecimento: list[str] = None, conteudos: list[str] = None):
        """
        Gera um simulado personalizado para o usuário.

        Args:
            user_id: ID do usuário.
            num_questions: Número de questões desejadas no simulado.
            areas_conhecimento: Lista de áreas de conhecimento para filtrar as questões.
            conteudos: Lista de conteúdos específicos para filtrar as questões.

        Returns:
            Um dicionário representando o simulado criado e suas questões,
            ou None em caso de falha.
        """
        user = get_user_by_id(user_id) # Retorna um dict ou None
        if not user:
            print(f"Usuário com ID {user_id} não encontrado.")
            return None

        # A proficiência do usuário pode ser usada para refinar a seleção de dificuldade
        # user_proficiency = user.get('nivel_proficiencia')
        # print(f"Gerando simulado para usuário {user.get('username')} com proficiência {user_proficiency}")

        all_matching_questions = [] # Lista de dicionários de questões

        # Coleta questões baseadas nos critérios
        # Nota: get_questions_by_criteria_db já retorna questões aleatórias se houver muitas.
        
        # Se áreas de conhecimento forem especificadas
        if areas_conhecimento:
            for area in areas_conhecimento:
                questions_in_area = get_questions_by_criteria_db(
                    area_conhecimento=area,
                    # Você pode adicionar lógica para filtrar por dificuldade aqui,
                    # buscando a proficiência do usuário e passando para dificuldade_classificada
                    # dificuldade_classificada="Média" # Exemplo
                    limit=num_questions # Pega um número suficiente por área
                )
                for q_dict in questions_in_area:
                    if q_dict not in all_matching_questions: # Evita duplicatas simples
                        all_matching_questions.append(q_dict)
        
        # Se conteúdos específicos forem especificados
        if conteudos:
            for conteudo_esp in conteudos:
                questions_in_conteudo = get_questions_by_criteria_db(
                    conteudo=conteudo_esp,
                    limit=num_questions # Pega um número suficiente por conteúdo
                )
                for q_dict in questions_in_conteudo:
                    if q_dict not in all_matching_questions:
                         all_matching_questions.append(q_dict)
        
        # Se nenhum critério específico, busca geral (mas ainda pode ser muitas questões)
        # É melhor ter pelo menos uma área ou conteúdo para focar.
        # Se for realmente uma busca geral, ajuste o limit.
        if not areas_conhecimento and not conteudos:
            print("Aviso: Gerando simulado com questões gerais. Pode não ser o ideal para estudo focado.")
            all_matching_questions = get_questions_by_criteria_db(
                limit=num_questions * 2 # Pega um pouco mais para garantir variedade na seleção aleatória
            )

        if not all_matching_questions:
            print("Nenhuma questão encontrada para os critérios fornecidos.")
            return None

        # Selecionar um subconjunto aleatório de questões se tivermos mais do que o necessário
        # Ou se a busca por critério retornou mais que o num_questions total desejado
        if len(all_matching_questions) > num_questions:
            selected_questions_dicts = random.sample(all_matching_questions, num_questions)
        else:
            selected_questions_dicts = all_matching_questions # Já são dicionários
            if len(selected_questions_dicts) < num_questions:
                print(f"Aviso: Foram encontradas apenas {len(selected_questions_dicts)} questões para os critérios, menos que as {num_questions} solicitadas.")

        if not selected_questions_dicts:
            print("Não foi possível selecionar questões para o simulado.")
            return None

        question_ids = [q_dict['id'] for q_dict in selected_questions_dicts]
        
        # Criar o MockExam no banco de dados
        # create_mock_exam_db retorna o ID do simulado criado
        new_mock_exam_id = create_mock_exam_db(user_id, question_ids)

        if new_mock_exam_id:
            print(f"Simulado ID {new_mock_exam_id} gerado com sucesso para o usuário {user_id} com {len(question_ids)} questões.")
            # Buscar os detalhes do simulado criado para retornar informações completas
            mock_exam_details = get_mock_exam_by_id_db(new_mock_exam_id)
            if mock_exam_details:
                return {
                    "mock_exam_id": new_mock_exam_id,
                    "user_id": mock_exam_details.get('user_id'),
                    "data_criacao": mock_exam_details.get('data_criacao'),
                    "status": mock_exam_details.get('status'),
                    "questions": selected_questions_dicts # selected_questions_dicts já contém as questões formatadas
                }
            else:
                print(f"Erro ao buscar detalhes do simulado ID {new_mock_exam_id} recém-criado.")
                return None # Ou apenas o ID se os detalhes não forem cruciais aqui
        else:
            print(f"Falha ao registrar o simulado no banco de dados para o usuário {user_id}.")
            return None

# Exemplo de uso (seria chamado pela API ou outro módulo):
if __name__ == '__main__':
    # Este bloco só será executado se o script for chamado diretamente.
    # É necessário que o db.py tenha sido executado para criar o banco e as tabelas.
    # E que existam usuários e questões no banco.

    # Adicionar alguns dados de teste (se o banco estiver vazio)
    from api_rest.db import init_db, add_user as add_user_db, add_question_db as add_question_db_sqlite
    
    # Inicializa o banco (cria tabelas se não existirem)
    # init_db() # Comente após a primeira execução ou se já tiver dados

    # Adiciona um usuário de teste se não existir
    test_user = get_user_by_id(1)
    if not test_user:
        print("Adicionando usuário de teste (ID 1)...")
        # Você precisaria de uma função para hashear a senha aqui
        from werkzeug.security import generate_password_hash
        add_user_db("agent_tester", "agent@example.com", generate_password_hash("password123"))
        test_user = get_user_by_id(1) # Tenta buscar novamente
    
    if test_user:
        print(f"Usando usuário de teste: {test_user}")
        
        # Adiciona algumas questões de teste se não existirem
        if not get_questions_by_criteria_db(area_conhecimento="Matemática", limit=1):
            print("Adicionando questões de teste de Matemática...")
            add_question_db_sqlite(
                enunciado="Quanto é 2 + 2?",
                alternativas={"A": "3", "B": "4", "C": "5", "D": "6"},
                alternativa_correta="B",
                area_conhecimento="Matemática",
                conteudo="Aritmética"
            )
            add_question_db_sqlite(
                enunciado="Quanto é 3 * 5?",
                alternativas={"A": "12", "B": "15", "C": "18", "D": "20"},
                alternativa_correta="B",
                area_conhecimento="Matemática",
                conteudo="Aritmética"
            )
        if not get_questions_by_criteria_db(area_conhecimento="Português", limit=1):
            print("Adicionando questões de teste de Português...")
            add_question_db_sqlite(
                enunciado="Qual o sinônimo de 'rápido'?",
                alternativas={"A": "Lento", "B": "Veloz", "C": "Grande", "D": "Pequeno"},
                alternativa_correta="B",
                area_conhecimento="Português",
                conteudo="Sinônimos"
            )

        generator_agent = MockExamGeneratorAgent()
        
        print("\nGerando simulado de Matemática...")
        simulado_mat = generator_agent.generate_mock_exam(
            user_id=test_user['id'],
            num_questions=2,
            areas_conhecimento=["Matemática"]
        )
        if simulado_mat:
            print("Detalhes do Simulado de Matemática Gerado:")
            # print(json.dumps(simulado_mat, indent=4, ensure_ascii=False)) # Para ver a estrutura completa
            print(f"  ID do Simulado: {simulado_mat['mock_exam_id']}")
            print(f"  Número de Questões: {len(simulado_mat['questions'])}")
            for q in simulado_mat['questions']:
                print(f"    - Questão ID {q['id']}: {q['enunciado'][:30]}...")
        else:
            print("Falha ao gerar simulado de Matemática.")

        print("\nGerando simulado geral (Português e Matemática)...")
        simulado_geral = generator_agent.generate_mock_exam(
            user_id=test_user['id'],
            num_questions=3 # Pedindo 3, pode retornar menos se não houver suficientes
        )
        if simulado_geral:
            print("Detalhes do Simulado Geral Gerado:")
            print(f"  ID do Simulado: {simulado_geral['mock_exam_id']}")
            print(f"  Número de Questões: {len(simulado_geral['questions'])}")
            for q in simulado_geral['questions']:
                print(f"    - Questão ID {q['id']}: {q['enunciado'][:30]}...")
        else:
            print("Falha ao gerar simulado geral.")
    else:
        print("Usuário de teste não encontrado. Execute o db.py ou adicione um usuário manualmente para testar o agente.")

