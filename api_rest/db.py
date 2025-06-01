import sqlite3
import json
import os
import datetime # Para timestamps

# Define o caminho para o arquivo do banco de dados dentro de uma pasta 'db'
# Isso assume que 'db.py' está dentro de 'api_rest'
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_files')
DB_PATH = os.path.join(DB_DIR, 'enem_study_db.sqlite')

# Garante que o diretório do banco de dados exista
os.makedirs(DB_DIR, exist_ok=True)

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def init_db():
    """Inicializa o banco de dados criando as tabelas necessárias."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de Usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        nivel_proficiencia TEXT -- Ex: Iniciante, Intermediário, Avançado
    )
    ''')

    # Tabela de Questões
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_question_id TEXT UNIQUE, -- ID da fonte original, se houver
        enunciado TEXT NOT NULL,
        area_conhecimento TEXT, -- Ex: Ciências da Natureza
        conteudo TEXT, -- Ex: Química Orgânica
        alternativas TEXT NOT NULL, -- Armazenado como uma string JSON {"A": "...", "B": "..."}
        alternativa_correta TEXT NOT NULL, -- Ex: "A"
        indice_acerto_geral REAL, -- Percentual de acerto de todos os usuários
        dificuldade_classificada TEXT -- Ex: Fácil, Médio, Difícil (pelo FuzzyAgent)
    )
    ''')

    # Tabela de Respostas dos Usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        mock_exam_id INTEGER, -- Pode ser nulo se a resposta não for de um simulado
        user_answer TEXT NOT NULL, -- Alternativa escolhida pelo usuário
        is_correct BOOLEAN NOT NULL,
        data_resposta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (question_id) REFERENCES questions (id),
        FOREIGN KEY (mock_exam_id) REFERENCES mock_exams (id)
    )
    ''')

    # Tabela de Simulados
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mock_exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL, -- Ex: Pendente, Em Andamento, Concluído
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Tabela Associativa: Questões de um Simulado
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mock_exam_questions (
        mock_exam_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        PRIMARY KEY (mock_exam_id, question_id),
        FOREIGN KEY (mock_exam_id) REFERENCES mock_exams (id),
        FOREIGN KEY (question_id) REFERENCES questions (id)
    )
    ''')

    # Tabela de Feedback
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mock_exam_id INTEGER, -- Feedback pode ser associado a um simulado específico
        content TEXT NOT NULL,
        data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (mock_exam_id) REFERENCES mock_exams (id)
    )
    ''')
    
    # Tabela de Flashcards
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        frente TEXT NOT NULL,
        verso TEXT NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (question_id) REFERENCES questions (id)
    )
    ''')

    conn.commit()
    conn.close()
    print(f"Banco de dados inicializado/verificado em: {DB_PATH}")

# --- Funções para Usuários ---
def add_user(username: str, email: str, hashed_password: str) -> int | None:
    """Adiciona um novo usuário e retorna seu ID, ou None em caso de erro."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        print(f"Usuário {username} adicionado com ID {user_id}.")
        return user_id
    except sqlite3.IntegrityError:
        print(f"Erro: Usuário {username} ou email {email} já existe.")
        return None
    except Exception as e:
        print(f"Erro ao adicionar usuário {username}: {e}")
        return None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> dict | None:
    """Busca um usuário pelo seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_username(username: str) -> dict | None:
    """Busca um usuário pelo seu nome de usuário."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_proficiency_db(user_id: int, nivel_proficiencia: str):
    """Atualiza o nível de proficiência de um usuário."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET nivel_proficiencia = ? WHERE id = ?",
            (nivel_proficiencia, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Usuário com ID {user_id} não encontrado para atualizar proficiência.")
            return False
        print(f"Proficiência do usuário ID {user_id} atualizada para {nivel_proficiencia}.")
        return True
    except Exception as e:
        print(f"Erro ao atualizar proficiência do usuário {user_id}: {e}")
        return False
    finally:
        conn.close()

# --- Funções para Questões ---
def add_question_db(enunciado: str, alternativas: dict, alternativa_correta: str,
                 area_conhecimento: str = None, conteudo: str = None,
                 original_question_id: str = None) -> int | None:
    """Adiciona uma nova questão ao banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO questions (original_question_id, enunciado, area_conhecimento, conteudo, alternativas, alternativa_correta)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (original_question_id, enunciado, area_conhecimento, conteudo, json.dumps(alternativas), alternativa_correta))
        conn.commit()
        question_id = cursor.lastrowid
        print(f"Questão adicionada com ID {question_id}.")
        return question_id
    except sqlite3.IntegrityError:
        print(f"Erro: Questão com original_question_id '{original_question_id}' já existe.")
        return None
    except Exception as e:
        print(f"Erro ao adicionar questão: {e}")
        return None
    finally:
        conn.close()

def get_question_by_id_db(question_id: int) -> dict | None:
    """Busca uma questão pelo seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()
    conn.close()
    if question:
        q_dict = dict(question)
        q_dict['alternativas'] = json.loads(q_dict['alternativas']) # Desserializa JSON
        return q_dict
    return None

def get_questions_by_criteria_db(area_conhecimento: str = None, conteudo: str = None,
                               dificuldade_classificada: str = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """Busca questões com base em critérios."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query_base = "SELECT * FROM questions"
    conditions = []
    params = []

    if area_conhecimento:
        conditions.append("area_conhecimento = ?")
        params.append(area_conhecimento)
    if conteudo:
        conditions.append("conteudo LIKE ?") # Busca parcial
        params.append(f"%{conteudo}%")
    if dificuldade_classificada:
        conditions.append("dificuldade_classificada = ?")
        params.append(dificuldade_classificada)

    if conditions:
        query_base += " WHERE " + " AND ".join(conditions)
    
    query_base += " ORDER BY RANDOM()" # Ordem aleatória para variedade
    query_base += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query_base, tuple(params))
    questions_rows = cursor.fetchall()
    conn.close()
    
    questions_list = []
    for row in questions_rows:
        q_dict = dict(row)
        q_dict['alternativas'] = json.loads(q_dict['alternativas'])
        questions_list.append(q_dict)
    return questions_list

def update_question_stats_db(question_id: int, indice_acerto_geral: float, dificuldade_classificada: str):
    """Atualiza o índice de acerto geral e a dificuldade classificada de uma questão."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE questions 
            SET indice_acerto_geral = ?, dificuldade_classificada = ?
            WHERE id = ?
        ''', (indice_acerto_geral, dificuldade_classificada, question_id))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Questão com ID {question_id} não encontrada para atualizar estatísticas.")
            return False
        return True
    except Exception as e:
        print(f"Erro ao atualizar estatísticas da questão {question_id}: {e}")
        return False
    finally:
        conn.close()

# --- Funções para Simulados (MockExams) ---
def create_mock_exam_db(user_id: int, question_ids: list[int], status: str = "Pendente") -> int | None:
    """Cria um novo simulado e retorna seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO mock_exams (user_id, status) VALUES (?, ?)", (user_id, status))
        mock_exam_id = cursor.lastrowid
        
        # Associa questões ao simulado
        for q_id in question_ids:
            # Verifica se a questão existe
            cursor.execute("SELECT id FROM questions WHERE id = ?", (q_id,))
            if cursor.fetchone() is None:
                raise ValueError(f"Questão com ID {q_id} não encontrada.")
            cursor.execute("INSERT INTO mock_exam_questions (mock_exam_id, question_id) VALUES (?, ?)", (mock_exam_id, q_id))
        
        conn.commit()
        print(f"Simulado ID {mock_exam_id} criado para o usuário {user_id}.")
        return mock_exam_id
    except ValueError as ve: # Captura o erro de questão não encontrada
        conn.rollback()
        print(f"Erro ao criar simulado: {ve}")
        return None
    except Exception as e:
        conn.rollback()
        print(f"Erro ao criar simulado para usuário {user_id}: {e}")
        return None
    finally:
        conn.close()

def get_mock_exam_by_id_db(mock_exam_id: int) -> dict | None:
    """Busca um simulado pelo seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mock_exams WHERE id = ?", (mock_exam_id,))
    mock_exam = cursor.fetchone()
    conn.close()
    return dict(mock_exam) if mock_exam else None

def get_questions_for_mock_exam_db(mock_exam_id: int) -> list[dict]:
    """Busca todas as questões associadas a um simulado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT q.* FROM questions q
        JOIN mock_exam_questions meq ON q.id = meq.question_id
        WHERE meq.mock_exam_id = ?
    ''', (mock_exam_id,))
    questions_rows = cursor.fetchall()
    conn.close()

    questions_list = []
    for row in questions_rows:
        q_dict = dict(row)
        q_dict['alternativas'] = json.loads(q_dict['alternativas'])
        questions_list.append(q_dict)
    return questions_list

def update_mock_exam_status_db(mock_exam_id: int, status: str) -> bool:
    """Atualiza o status de um simulado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE mock_exams SET status = ? WHERE id = ?", (status, mock_exam_id))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Simulado com ID {mock_exam_id} não encontrado para atualizar status.")
            return False
        return True
    except Exception as e:
        print(f"Erro ao atualizar status do simulado {mock_exam_id}: {e}")
        return False
    finally:
        conn.close()

# --- Funções para Respostas (Answers) ---
def add_answer_db(user_id: int, question_id: int, user_answer: str, is_correct: bool, mock_exam_id: int = None) -> int | None:
    """Adiciona uma resposta e retorna seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO answers (user_id, question_id, mock_exam_id, user_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, question_id, mock_exam_id, user_answer, is_correct))
        conn.commit()
        answer_id = cursor.lastrowid
        return answer_id
    except Exception as e:
        print(f"Erro ao adicionar resposta: {e}")
        return None
    finally:
        conn.close()

def get_answers_for_mock_exam_db(user_id: int, mock_exam_id: int) -> list[dict]:
    """Busca todas as respostas de um usuário para um simulado específico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM answers WHERE user_id = ? AND mock_exam_id = ?",
        (user_id, mock_exam_id)
    )
    answers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return answers

def get_answers_for_question_db(question_id: int) -> list[dict]:
    """Busca todas as respostas para uma questão específica (para calcular índice de acerto)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM answers WHERE question_id = ?", (question_id,))
    answers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return answers


# --- Funções para Feedback ---
def create_feedback_db(user_id: int, content: str, mock_exam_id: int = None) -> int | None:
    """Cria e armazena um novo feedback, retorna seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO feedback (user_id, mock_exam_id, content) VALUES (?, ?, ?)",
            (user_id, mock_exam_id, content)
        )
        conn.commit()
        feedback_id = cursor.lastrowid
        return feedback_id
    except Exception as e:
        print(f"Erro ao criar feedback: {e}")
        return None
    finally:
        conn.close()

def get_feedback_for_user_db(user_id: int, mock_exam_id: int = None) -> list[dict]:
    """Busca feedbacks para um usuário, opcionalmente filtrando por simulado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM feedback WHERE user_id = ?"
    params = [user_id]
    
    if mock_exam_id:
        query += " AND mock_exam_id = ?"
        params.append(mock_exam_id)
    
    query += " ORDER BY data_geracao DESC"
    
    cursor.execute(query, tuple(params))
    feedbacks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return feedbacks

# --- Funções para Flashcards ---
def add_flashcard_db(user_id: int, question_id: int, frente: str, verso: str) -> int | None:
    """Adiciona um novo flashcard e retorna seu ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO flashcards (user_id, question_id, frente, verso) VALUES (?, ?, ?, ?)",
            (user_id, question_id, frente, verso)
        )
        conn.commit()
        flashcard_id = cursor.lastrowid
        print(f"Flashcard para questão {question_id} adicionado para usuário {user_id} com ID {flashcard_id}.")
        return flashcard_id
    except Exception as e:
        print(f"Erro ao adicionar flashcard para questão {question_id}: {e}")
        return None
    finally:
        conn.close()

def get_flashcards_for_user_db(user_id: int, question_id: int = None) -> list[dict]:
    """Busca flashcards para um usuário, opcionalmente filtrando por questão."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM flashcards WHERE user_id = ?"
    params = [user_id]
    
    if question_id:
        query += " AND question_id = ?"
        params.append(question_id)
        
    query += " ORDER BY data_criacao DESC"
    
    cursor.execute(query, tuple(params))
    flashcards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return flashcards


# Bloco para inicializar o DB se o script for executado diretamente
if __name__ == '__main__':
    print(f"Verificando e, se necessário, inicializando o banco de dados em: {DB_PATH}")
    init_db()
    print("Processo de inicialização do banco de dados concluído.")

    # Exemplo de uso (descomente para testar após a inicialização)
    # print("\nAdicionando usuário de teste...")
    # test_user_id = add_user("testuser_sqlite", "testsqlite@example.com", "hashed_password_example")
    # if test_user_id:
    #     print(f"Usuário de teste adicionado com ID: {test_user_id}")
    #     user_data = get_user_by_id(test_user_id)
    #     print(f"Dados do usuário buscado: {user_data}")

    #     print("\nAdicionando questão de teste...")
    #     alternativas_ex = {"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D"}
    #     q_id = add_question_db(
    #         enunciado="Qual a capital da França?",
    #         alternativas=alternativas_ex,
    #         alternativa_correta="C", # Supondo que C é Paris
    #         area_conhecimento="Conhecimentos Gerais",
    #         conteudo="Geografia"
    #     )
    #     if q_id:
    #         print(f"Questão de teste adicionada com ID: {q_id}")
    #         q_data = get_question_by_id_db(q_id)
    #         print(f"Dados da questão buscada: {q_data}")

    #         print("\nCriando simulado de teste...")
    #         mock_id = create_mock_exam_db(test_user_id, [q_id])
    #         if mock_id:
    #             print(f"Simulado de teste criado com ID: {mock_id}")
    #             mock_data = get_mock_exam_by_id_db(mock_id)
    #             print(f"Dados do simulado: {mock_data}")
    #             questions_in_mock = get_questions_for_mock_exam_db(mock_id)
    #             print(f"Questões no simulado: {questions_in_mock}")
