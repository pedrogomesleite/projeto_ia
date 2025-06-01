from api_rest import db # Importa o módulo db.py
import json

class StudyCardAgent:
    def __init__(self, user_id=1):
        self.user_id = user_id
        print(f"Agente Montador de Cards de Estudo inicializado para o Usuário ID: {self.user_id}")

    def get_weakest_areas(self, top_n=3):
        """
        Identifica as N áreas onde o usuário tem o maior 'perceived_weakness_score'.
        Retorna uma lista de dicionários de perfil de área.
        """
        user_profiles = db.get_user_subject_profiles(self.user_id)
        # A função get_user_subject_profiles já ordena por perceived_weakness_score DESC
        if not user_profiles:
            print(f"Nenhum perfil de matéria encontrado para o usuário {self.user_id}.")
            return []
        return user_profiles[:top_n]

    def generate_study_cards(self, num_cards_per_area=3, target_difficulties=None):
        """
        Gera cards de estudo para o usuário.
        
        Args:
            num_cards_per_area (int): Número de cards a gerar por área de fraqueza.
            target_difficulties (list, optional): Lista de rótulos de dificuldade fuzzy 
                                                  para focar (ex: ["Fácil", "Média"]). 
                                                  Se None, tenta uma mistura.
        Returns:
            list: Uma lista de dicionários, onde cada dicionário é um card de estudo.
        """
        print(f"\n--- Gerando Cards de Estudo para o Usuário ID: {self.user_id} ---")
        weakest_areas_profiles = self.get_weakest_areas()

        if not weakest_areas_profiles:
            print("Não foi possível identificar áreas de fraqueza para gerar cards.")
            return []

        study_cards = []
        
        for profile_row in weakest_areas_profiles:
            profile = dict(profile_row)
            area_name = profile['area']
            print(f"\nFocando na área: {area_name} (Score de Fraqueza: {profile['perceived_weakness_score']:.2f})")

            # Define as dificuldades alvo para esta área
            if target_difficulties:
                current_target_difficulties = target_difficulties
            else:
                # Lógica padrão para escolher dificuldades se não especificado:
                # Tenta pegar questões fáceis e médias primeiro.
                if profile['perceived_weakness_score'] > 0.6: # Se a fraqueza é alta
                    current_target_difficulties = ["Fácil", "Média"]
                elif profile['perceived_weakness_score'] > 0.3: # Fraqueza moderada
                    current_target_difficulties = ["Média", "Difícil"]
                else: # Usuário está bem na área, talvez queira revisar ou desafios
                    current_target_difficulties = ["Difícil", "Muito Difícil", "Média"] 
            
            print(f"  Procurando questões com dificuldades: {current_target_difficulties}")

            questions_for_area = db.get_questions_for_study(
                area=area_name,
                difficulty_labels=current_target_difficulties,
                limit=num_cards_per_area
            )

            if not questions_for_area:
                print(f"  Nenhuma questão encontrada para '{area_name}' com as dificuldades alvo: {current_target_difficulties}.")
                # Tentar com dificuldades mais amplas como fallback
                fallback_difficulties = ["Fácil", "Média", "Difícil", "Muito Fácil", "Muito Difícil"]
                print(f"  Tentando fallback com dificuldades: {fallback_difficulties}")
                questions_for_area = db.get_questions_for_study(
                    area=area_name,
                    difficulty_labels=fallback_difficulties,
                    limit=num_cards_per_area
                )
                if not questions_for_area:
                    print(f"  Nenhuma questão encontrada para '{area_name}' mesmo com fallback.")
                    continue


            for q_row in questions_for_area:
                question = dict(q_row)
                card = {
                    "id_questao_db": question['id'],
                    "area": question['area'],
                    "enunciado": question['enunciado'],
                    "alternativas": json.loads(question['alternativas']), # Converte string JSON para lista
                    "gabarito": question['gabarito'], # Para conferência do usuário
                    "dificuldade_fuzzy": question['fuzzy_difficulty_label']
                }
                study_cards.append(card)
                print(f"  Card adicionado: ID {question['id']} ({question['fuzzy_difficulty_label']})")
        
        print(f"--- Geração de Cards Concluída. Total de cards: {len(study_cards)} ---")
        return study_cards

    def display_study_cards(self, cards):
        """Mostra os cards de estudo de forma legível."""
        if not cards:
            print("\nNenhum card de estudo para mostrar.")
            return

        print("\n╔═════════════════════════════════════════╗")
        print("║          SEUS CARDS DE ESTUDO           ║")
        print("╚═════════════════════════════════════════╝")
        for i, card in enumerate(cards):
            print(f"\nCARD {i+1}/{len(cards)}")
            print(f"-------------------------------------------")
            print(f"Área: {card['area']}")
            print(f"Dificuldade Estimada: {card['dificuldade_fuzzy']}")
            print(f"ID (DB): {card['id_questao_db']}")
            print(f"\nEnunciado:\n{card['enunciado']}")
            print("\nAlternativas:")
            # As alternativas já devem ser uma lista de strings
            for alt in card['alternativas']:
                print(f"  {alt}")
            # print(f"\n(Gabarito para conferência: {card['gabarito']})") # Mostrar ou não o gabarito aqui é uma escolha de design
            print(f"-------------------------------------------\n")
        
        print("Lembre-se de tentar resolver antes de verificar o gabarito!")
        print("Para ver o gabarito, você pode consultar o card pelo ID no banco de dados ou modificar esta função para mostrá-lo.")


# Exemplo de uso (para ser chamado de um script principal)
if __name__ == '__main__':
    print("Executando study_card_agent.py como script principal (para teste).")
    
    # Para testar, precisamos que o DB esteja populado e que o agente fuzzy já tenha rodado.
    # Vamos simular essa condição chamando as funções necessárias se este script for rodado isoladamente.
    # Idealmente, isso seria feito pelo main.py.

    # 1. Garanta que o DB e as tabelas existam
    db.init_db() 

    # 2. Simular algumas tentativas se o DB estiver "zerado" em termos de hit_rates
    # (Esta é uma simulação simplificada, main.py faz isso de forma mais completa)
    test_questions = db.get_all_questions()
    if test_questions and test_questions[0]['total_attempts'] == 0:
        print("Simulando algumas tentativas para popular hit_rates (teste)...")
        from main import simulate_user_attempts # Importa a função de simulação
        simulate_user_attempts()
    
        # 3. Rodar o agente fuzzy se as questões não estiverem classificadas
        import agentes.fuzzy_agent as fuzzy_agent
        fuzzy_classifier = fuzzy_agent.DifficultyClassifierAgent()
        fuzzy_classifier.run_classification()
        print("Classificação Fuzzy de teste concluída.")


    # Agora, criar e usar o agente de cards
    card_agent = StudyCardAgent(user_id=1) # Usando o ASSUMED_USER_ID do main.py
    
    # Gerar cards com dificuldades específicas
    # study_cards_generated = card_agent.generate_study_cards(
    #     num_cards_per_area=2, 
    #     target_difficulties=["Fácil", "Média"]
    # )
    
    # Gerar cards com lógica de dificuldade padrão do agente
    study_cards_generated = card_agent.generate_study_cards(num_cards_per_area=2)

    card_agent.display_study_cards(study_cards_generated)