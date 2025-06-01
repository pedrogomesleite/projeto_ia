import sqlite3
import json
import os

# Define o caminho para o arquivo do banco de dados dentro de uma pasta 'db'
DB_DIR = os.path.join(os.path.dirname(__file__), 'db')
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

    # Tabela de Questões
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_question_id TEXT UNIQUE, -- Um ID único da questão (ex: hash ou ID do JSON)
        enunciado TEXT NOT NULL,
        area TEXT NOT NULL, -- Matéria (ex: matemática, português)
        alternativas TEXT NOT NULL, -- Armazenado como uma string JSON
        gabarito TEXT NOT NULL, -- Ex: "A", "B", "C", "D", "E"
        total_attempts INTEGER DEFAULT 0,
        correct_attempts INTEGER DEFAULT 0,
        hit_rate REAL DEFAULT 0.0, -- (correct_attempts / total_attempts)
        fuzzy_difficulty_label TEXT, -- Ex: "Fácil", "Médio", "Difícil"
        fuzzy_difficulty_score REAL -- Saída numérica da lógica fuzzy (opcional)
    )
    ''')

    # Tabela de Perfil de Desempenho do Usuário por Matéria
    # Para simplificar, vamos considerar um único usuário (user_id = 1)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_subject_profile (
        user_id INTEGER NOT NULL DEFAULT 1,
        area TEXT NOT NULL, -- Matéria
        total_questions_answered INTEGER DEFAULT 0,
        correct_questions_answered INTEGER DEFAULT 0,
        user_area_hit_rate REAL DEFAULT 0.0, -- (correct_area / total_area)
        perceived_weakness_score REAL DEFAULT 1.0, -- (1.0 - user_area_hit_rate)
        PRIMARY KEY (user_id, area)
    )
    ''')
    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso.")

def add_question(original_id, enunciado, area, alternativas, gabarito):
    """Adiciona uma nova questão ao banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO questions (original_question_id, enunciado, area, alternativas, gabarito)
        VALUES (?, ?, ?, ?, ?)
        ''', (original_id, enunciado, area, json.dumps(alternativas), gabarito))
        conn.commit()
        print(f"Questão {original_id} adicionada.")
    except sqlite3.IntegrityError:
        print(f"Questão {original_id} já existe no banco de dados.")
    except Exception as e:
        print(f"Erro ao adicionar questão {original_id}: {e}")
    finally:
        conn.close()

def get_all_questions():
    """Retorna todas as questões do banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()
    conn.close()
    return questions

def get_question_by_id(question_id):
    """Retorna uma questão específica pelo seu ID no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()
    conn.close()
    return question

def update_question_attempts(question_id, is_correct):
    """Atualiza as tentativas e o índice de acerto de uma questão."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT total_attempts, correct_attempts FROM questions WHERE id = ?", (question_id,))
    row = cursor.fetchone()
    if not row:
        print(f"Questão com ID {question_id} não encontrada.")
        conn.close()
        return

    total_attempts = row['total_attempts'] + 1
    correct_attempts = row['correct_attempts'] + (1 if is_correct else 0)
    hit_rate = correct_attempts / total_attempts if total_attempts > 0 else 0.0

    cursor.execute('''
    UPDATE questions
    SET total_attempts = ?, correct_attempts = ?, hit_rate = ?
    WHERE id = ?
    ''', (total_attempts, correct_attempts, hit_rate, question_id))
    
    conn.commit()
    conn.close()
    # print(f"Tentativas da questão {question_id} atualizadas. Acerto: {is_correct}. Novo hit_rate: {hit_rate:.2f}")

def update_question_fuzzy_difficulty(question_id, label, score=None):
    """Atualiza a dificuldade Fuzzy de uma questão."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE questions
    SET fuzzy_difficulty_label = ?, fuzzy_difficulty_score = ?
    WHERE id = ?
    ''', (label, score, question_id))
    conn.commit()
    conn.close()
    # print(f"Dificuldade Fuzzy da questão {question_id} atualizada para {label}.")

def update_user_subject_profile(user_id, area, is_correct):
    """Atualiza o perfil de desempenho do usuário para uma determinada matéria."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT total_questions_answered, correct_questions_answered 
    FROM user_subject_profile 
    WHERE user_id = ? AND area = ?
    ''', (user_id, area))
    profile = cursor.fetchone()

    if profile:
        total_answered = profile['total_questions_answered'] + 1
        correct_answered = profile['correct_questions_answered'] + (1 if is_correct else 0)
    else:
        total_answered = 1
        correct_answered = (1 if is_correct else 0)

    user_area_hit_rate = correct_answered / total_answered if total_answered > 0 else 0.0
    perceived_weakness_score = 1.0 - user_area_hit_rate

    cursor.execute('''
    INSERT OR REPLACE INTO user_subject_profile 
        (user_id, area, total_questions_answered, correct_questions_answered, user_area_hit_rate, perceived_weakness_score)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, area, total_answered, correct_answered, user_area_hit_rate, perceived_weakness_score))
    
    conn.commit()
    conn.close()
    # print(f"Perfil do usuário {user_id} para a área '{area}' atualizado. Acerto: {is_correct}")

def get_user_subject_profiles(user_id=1):
    """Retorna os perfis de matéria para um usuário."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_subject_profile WHERE user_id = ? ORDER BY perceived_weakness_score DESC", (user_id,))
    profiles = cursor.fetchall()
    conn.close()
    return profiles

def get_questions_for_study(area, difficulty_labels, limit=5):
    """Busca questões para estudo com base na área e rótulos de dificuldade."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cria a parte da query para os rótulos de dificuldade
    # Ex: difficulty_labels = ["Fácil", "Médio"] -> "fuzzy_difficulty_label IN ('Fácil', 'Médio')"
    placeholders = ','.join('?' for _ in difficulty_labels)
    query = f"""
    SELECT * FROM questions 
    WHERE area = ? 
    AND fuzzy_difficulty_label IN ({placeholders})
    ORDER BY RANDOM() -- Para pegar questões aleatórias que se encaixam no critério
    LIMIT ?
    """
    params = [area] + difficulty_labels + [limit]
    
    cursor.execute(query, params)
    questions = cursor.fetchall()
    conn.close()
    return questions

if __name__ == '__main__':
    # Este bloco é executado quando o script é chamado diretamente.
    # Útil para inicializar o DB pela primeira vez.
    print(f"Tentando inicializar o banco de dados em: {DB_PATH}")
    init_db()
    print("\nExemplo de busca de perfis (inicialmente vazio):")
    profiles = get_user_subject_profiles(1)
    if profiles:
        for profile in profiles:
            print(dict(profile))
    else:
        print("Nenhum perfil de usuário encontrado.")

    print("\nExemplo de busca de questões (inicialmente vazio):")
    questions_sample = get_all_questions()
    if questions_sample:
        print(f"Encontradas {len(questions_sample)} questões.")
        # print(dict(questions_sample[0])) # Imprime a primeira questão como exemplo
    else:
        print("Nenhuma questão encontrada.")
