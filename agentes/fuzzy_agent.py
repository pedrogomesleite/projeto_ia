import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from api_rest import db # Importa o módulo db.py

# --- Definição do Sistema de Inferência Fuzzy ---

# 1. Variáveis (Antecedente e Consequente)
# Antecedente (Entrada): hit_rate (Índice de Acerto)
# Universo: 0.0 a 1.0 (0% a 100% de acertos)
hit_rate = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'hit_rate')

# Consequente (Saída): question_difficulty (Dificuldade da Questão)
# Universo: 0 a 100 (escala de dificuldade)
question_difficulty = ctrl.Consequent(np.arange(0, 101, 1), 'question_difficulty')

# 2. Funções de Pertinência (Membership Functions)

# Para hit_rate:
# Usaremos 5 níveis: Muito Baixo, Baixo, Médio, Alto, Muito Alto
hit_rate['muito_baixo'] = fuzz.trapmf(hit_rate.universe, [0, 0, 0.1, 0.25])      # 0-25%
hit_rate['baixo'] = fuzz.trimf(hit_rate.universe, [0.15, 0.325, 0.5])           # ~20-50%
hit_rate['medio'] = fuzz.trimf(hit_rate.universe, [0.4, 0.6, 0.8])              # ~40-80%
hit_rate['alto'] = fuzz.trimf(hit_rate.universe, [0.7, 0.825, 0.95])            # ~70-95%
hit_rate['muito_alto'] = fuzz.trapmf(hit_rate.universe, [0.85, 0.95, 1.0, 1.0]) # 85-100%

# Para question_difficulty:
# Usaremos 5 níveis: Muito Fácil, Fácil, Media, Difícil, Muito Difícil
question_difficulty['muito_facil'] = fuzz.trapmf(question_difficulty.universe, [0, 0, 10, 25])       # 0-25
question_difficulty['facil'] = fuzz.trimf(question_difficulty.universe, [15, 32.5, 50])             # ~20-50
question_difficulty['media'] = fuzz.trimf(question_difficulty.universe, [40, 60, 80])               # ~40-80
question_difficulty['dificil'] = fuzz.trimf(question_difficulty.universe, [70, 82.5, 95])            # ~70-95
question_difficulty['muito_dificil'] = fuzz.trapmf(question_difficulty.universe, [85, 95, 100, 100]) # 85-100

# 3. Regras Fuzzy (IF-THEN)
# Se o índice de acerto é alto, a questão é fácil, e vice-versa.
rule1 = ctrl.Rule(hit_rate['muito_alto'], question_difficulty['muito_facil'])
rule2 = ctrl.Rule(hit_rate['alto'], question_difficulty['facil'])
rule3 = ctrl.Rule(hit_rate['medio'], question_difficulty['media'])
rule4 = ctrl.Rule(hit_rate['baixo'], question_difficulty['dificil'])
rule5 = ctrl.Rule(hit_rate['muito_baixo'], question_difficulty['muito_dificil'])

# Adicionando uma regra para hit_rate zero (se nenhuma tentativa ou todos erraram)
# Consideraremos como muito difícil por padrão, mas pode ser ajustado.
rule6 = ctrl.Rule(hit_rate['muito_baixo'] & (hit_rate <= 0.05), question_difficulty['muito_dificil'])


# 4. Controle do Sistema e Simulação
difficulty_ctrl_system = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6])
# difficulty_simulation = ctrl.ControlSystemSimulation(difficulty_ctrl_system)

def get_fuzzy_difficulty_label(difficulty_score):
    """Converte o score numérico de dificuldade em um rótulo textual."""
    if difficulty_score <= 25:
        return "Muito Fácil"
    elif difficulty_score <= 50:
        return "Fácil"
    elif difficulty_score <= 80: # Ajustado para dar mais espaço para "Média"
        return "Média"
    elif difficulty_score <= 95:
        return "Difícil"
    else:
        return "Muito Difícil"

def classify_question_difficulty(current_hit_rate):
    """
    Calcula a dificuldade de uma questão com base no seu índice de acerto
    usando o sistema de inferência fuzzy.
    Retorna o score numérico de dificuldade e o rótulo textual.
    """
    # É importante criar uma nova simulação para cada cálculo se for usar threads
    # ou em contextos onde o estado da simulação anterior pode interferir.
    # Para uso sequencial simples, reutilizar pode ser ok, mas criar nova é mais seguro.
    difficulty_simulation = ctrl.ControlSystemSimulation(difficulty_ctrl_system)

    # Passa o índice de acerto para o sistema de controle
    difficulty_simulation.input['hit_rate'] = current_hit_rate

    # Computa o resultado
    try:
        difficulty_simulation.compute()
        difficulty_score = difficulty_simulation.output['question_difficulty']
        difficulty_label = get_fuzzy_difficulty_label(difficulty_score)
        return difficulty_score, difficulty_label
    except Exception as e:
        print(f"Erro ao calcular dificuldade fuzzy para hit_rate {current_hit_rate}: {e}")
        # Retorna um padrão em caso de erro (ex: Média)
        # Poderia ser mais sofisticado, como logar o erro e retornar None
        return 50.0, "Média"


class DifficultyClassifierAgent:
    def __init__(self):
        print("Agente Classificador de Dificuldade inicializado.")

    def run_classification(self):
        """
        Busca todas as questões que tiveram tentativas, calcula sua dificuldade fuzzy
        e atualiza o banco de dados.
        """
        print("\n--- Iniciando Classificação de Dificuldade Fuzzy ---")
        questions_to_classify = db.get_all_questions() # Poderia filtrar por total_attempts > 0

        if not questions_to_classify:
            print("Nenhuma questão encontrada no banco de dados para classificar.")
            return

        classified_count = 0
        for q_row in questions_to_classify:
            question = dict(q_row) # Converte a linha do DB para um dicionário
            question_id = question['id']
            current_hit_rate = question['hit_rate']
            
            # Só classifica se houve tentativas, ou define uma dificuldade padrão
            if question['total_attempts'] == 0:
                # Define uma dificuldade padrão para questões sem tentativas, ex: "Média"
                # ou pode optar por não classificar ainda (deixando NULO no DB)
                # db.update_question_fuzzy_difficulty(question_id, "Não Classificada", None)
                # print(f"Questão ID {question_id}: Sem tentativas, não classificada.")
                # Para este exemplo, vamos classificar como "Média" se não houver tentativas
                # e o hit_rate for 0.
                 difficulty_score, difficulty_label = classify_question_difficulty(0.5) # Default to medium if no attempts
                 print(f"Questão ID {question_id}: Sem tentativas, classificada como '{difficulty_label}' (default).")

            else:
                difficulty_score, difficulty_label = classify_question_difficulty(current_hit_rate)
                print(f"Questão ID {question_id}: Hit Rate = {current_hit_rate:.2f} -> Dificuldade Score = {difficulty_score:.2f} ({difficulty_label})")
            
            db.update_question_fuzzy_difficulty(question_id, difficulty_label, difficulty_score)
            classified_count += 1
        
        print(f"--- Classificação Fuzzy concluída. {classified_count} questões processadas. ---")

# Exemplo de uso (para ser chamado de um script principal)
if __name__ == '__main__':
    print("Executando fuzzy_agent.py como script principal (para teste).")
    
    # Teste direto da função de classificação
    test_hit_rates = [0.0, 0.15, 0.3, 0.5, 0.75, 0.9, 1.0]
    print("\nTestando a classificação fuzzy para diferentes hit rates:")
    for hr in test_hit_rates:
        score, label = classify_question_difficulty(hr)
        print(f"Hit Rate: {hr:.2f} -> Score Dificuldade: {score:.2f}, Rótulo: {label}")

    # Para testar o agente completo, precisaríamos de um DB populado e com tentativas.
    # Isso será feito no main.py
    
    # Exemplo de como o agente seria chamado:
    # print("\nSimulando execução do Agente Classificador de Dificuldade:")
    # agent = DifficultyClassifierAgent()
    # agent.run_classification()
    # print("Verifique o banco de dados para os rótulos de dificuldade atualizados.")

    # Visualizar as funções de pertinência (opcional, para depuração)
    # hit_rate.view()
    # question_difficulty.view()
    # input("Pressione Enter para continuar após visualizar os gráficos...")
