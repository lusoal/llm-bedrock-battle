import random
import boto3
import json
import time
from colorama import Fore, Style, init

init(autoreset=True)

def draw_attribute_bar(value, max_value, bar_length=20):
    """Creates a colored bar based on the attribute value relative to max value."""
    filled_length = int(round(bar_length * value / float(max_value)))
    bar = Fore.GREEN + '█' * filled_length + Fore.RED + '█' * (bar_length - filled_length)
    return bar

def display_character_stats(characters):
    """Displays both characters' stats side by side."""
    stats_format = "{0: <15} {1: >20}"
    print(Fore.CYAN + stats_format.format("Attribute", "Value") + Style.RESET_ALL)
    for attr in ["Health", "Intelligence", "Defense"]:
        left_value = getattr(characters[0], attr.lower())
        right_value = getattr(characters[1], attr.lower())
        left_bar = draw_attribute_bar(left_value, 100)
        right_bar = draw_attribute_bar(right_value, 100)
        print(Fore.YELLOW + f"{characters[0].name}: " + left_bar + " " +
              Fore.YELLOW + f"{characters[1].name}: " + right_bar)
        print(stats_format.format(f"{attr}: {left_value}", f"{attr}: {right_value}"))
    print("\n")


def introduction():
    print(Fore.CYAN + "Welcome to the Battle Game!\n" + Style.RESET_ALL)
    print("Get ready to watch a showdown between two characters controlled by AI:")
    print("1. AmazonTitan")
    print("2. Jurassic\n")
    print("Each character has these important qualities:")
    print("- Health: How much damage they can take before losing.")
    print("- Intelligence: How effective their attacks are.")
    print("- Defense: How well they can defend against attacks.\n")
    print("Here are the moves they can make:")
    print("- " + Fore.GREEN + "Attack:" + Style.RESET_ALL + " Try to hurt the other character.")
    print("- " + Fore.YELLOW + "Defense:" + Style.RESET_ALL + " Protect themselves from damage.")
    print("- " + Fore.RED + "Super Attack:" + Style.RESET_ALL + " A powerful move that hurts the opponent a lot.\n")
    print("The game goes on in rounds. Each round, the characters pick their moves.")
    print("After each round, you'll see what happened and what choices were made.\n")
    input(Fore.RED + "Press Enter to start the game..." + Style.RESET_ALL)



def trigger_jurassic(prompt):
    brt = boto3.client(service_name='bedrock-runtime')
    body = json.dumps({
        "prompt": prompt,
        "maxTokens": 50,
        "temperature": 0,
        "topP": 0.9,
        "stopSequences": [],
        "countPenalty": {"scale": 0},
        "presencePenalty": {"scale": 0},
        "frequencyPenalty": {"scale": 0}
    })
    modelId = 'ai21.j2-ultra-v1'  # Model ID for Jurassic
    accept = 'application/json'
    contentType = 'application/json'

    try:
        response = brt.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
        response_body = json.loads(response.get('body').read())
        completion = response_body["completions"][0]["data"]["text"]
        return completion
    except Exception as e:
        raise("An error occurred:", e)

def trigger_titan(prompt):
    brt = boto3.client(service_name='bedrock-runtime')
    body = json.dumps({
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 10,  # Allows for a large response
            "stopSequences": [],  # No specific stop sequences
            "temperature": 0,  # Deterministic output
            "topP": 1  # Considering the full probability distribution
        }
    })
    modelId = 'amazon.titan-text-express-v1'  # Model ID for Amazon Titan Text
    accept = 'application/json'
    contentType = 'application/json'

    try:
        response = brt.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
        response_body = json.loads(response.get('body').read())
        # Assume 'text' is the key where the generated text is stored (adjust based on actual API response)
        completion = response_body.get('results')[0].get("outputText")
        return completion
    except Exception as e:
        raise("An error occurred:", e)

class Character:
    def __init__(self, health, intelligence, defense, name):
        self.health = int(health)
        self.intelligence = int(intelligence)
        self.defense = int(defense)
        self.name = name

    def is_alive(self):
        return self.health > 0

    def attack(self, other):
        # Calculate the base damage inflicted by the attack
        base_damage = 5  # Adjust this value as needed
        
        # Calculate the damage considering attacker's intelligence and defender's defense
        damage = max(abs(self.intelligence - other.defense), 0) + base_damage
        # Reduce the opponent's health by the calculated damage
        other.health = max(other.health - damage, 0)

    def increase_defense(self):  # Renamed method from 'defense' to 'increase_defense'
        self.defense += 10

    def super_attack(self, other):
        # Ensure that the super attack removes at least 10 health points
        damage = 10  # Set damage to 10 or remaining health, whichever is smaller
        other.health = max(other.health - damage, 0)

class Game:
    def __init__(self, characters, models):
        self.characters = characters
        self.models = models
        self.history = []

    def play_round(self):
        for i, model in enumerate(self.models):
            print(Fore.RED + f"\n{self.characters[i].name}'s turn to play:" + Style.RESET_ALL)
            display_character_stats(self.characters)  
            prompt = self.create_prompt(self.characters[i], self.characters[1-i], i)
            strategy = model.decide_action(prompt, self.characters[i].name)  
            self.execute_strategy(strategy, i)
            self.history.append((self.characters[i].name, strategy))
            print(Fore.YELLOW + f"{self.characters[i].name} chooses to {Fore.LIGHTBLUE_EX}{strategy}" + Style.RESET_ALL)
            
            if not self.characters[1-i].is_alive():
                print(Fore.GREEN + f"\n{self.characters[i].name} wins the game!" + Style.RESET_ALL)
                return True
        return False

    def simulate_game(self):
        round_count = 1
        while all(char.is_alive() for char in self.characters):
            print(f"\nStarting Round {round_count}...")
            if self.play_round():
                break
            round_count += 1
            display_character_stats(self.characters)  

    def create_prompt(self, character, opponent, turn):
        history_str = ""
        for index, (name, strategy) in enumerate(self.history):
            if name == character.name:
                result = "increased" if strategy == "attack" else "held steady"
                history_str += f"Round {index+1}: {name} chose to {strategy}, which {result} their advantage.\n"
            else:
                result = "decreased" if strategy == "attack" else "held steady"
                history_str += f"Round {index+1}: {name} chose to {strategy}, which {result} their disadvantage.\n"
        
        prompt = (
            f"Round {len(self.history)+1}, Turn {turn+1}, {character.name}'s turn.\n"
            f"This is a strategic decision-making simulation. {character.name} (You) vs {opponent.name} (Opponent).\n"
            f"Current stats:\n"
            f"  - {character.name}: Intelligence {character.intelligence}, Defense {character.defense}\n"
            f"  - {opponent.name}: Intelligence {opponent.intelligence}, Defense {opponent.defense}\n"
            f"Game History:\n{history_str}"
            "Please select your strategy. Answer should be one of these options and NOTHING ELSE [attack, defense, super_attack]:"
        )
        return prompt


    def execute_strategy(self, strategy, char_index):
        character = self.characters[char_index]
        opponent = self.characters[1 - char_index]

        if strategy.lower() == 'attack':
            character.attack(opponent)
        elif strategy.lower() == 'defense':
            character.increase_defense()  
        elif strategy.lower() == 'super_attack':
            character.super_attack(opponent)

class RandomModel:
    def __init__(self):
        self.last_actions = {"AmazonTitan": "attack", "Jurassic": "attack"}  

    def decide_action(self, prompt, model_name):
        response_model = ""
        if model_name == "AmazonTitan":
            response_model = trigger_titan(prompt)
        elif model_name == "Jurassic":
            response_model = trigger_jurassic(prompt)
        else:
            raise ValueError("Unknown model name")
        
        response_model = response_model.lower()
        
        possible_strategies = ['attack', 'defense', 'super_attack']
        
        direct_health_strategies = ['attack', 'super_attack']
        for strategy in direct_health_strategies:
            if strategy in response_model:
                chosen_action = strategy
                break
        else:
            # If the model's response doesn't contain direct health strategies,
            # choose a random strategy from the available ones
            possible_strategies.remove(self.last_actions.get(model_name, ''))
            chosen_action = random.choice(possible_strategies)
        
        # Update the last chosen action for the model
        self.last_actions[model_name] = chosen_action
        
        return chosen_action

if __name__ == "__main__":
    introduction()  
    character1 = Character(100, 100, 50, "AmazonTitan")
    character2 = Character(100, 100, 50, "Jurassic")

    game = Game([character1, character2], [RandomModel(), RandomModel()])
    game.simulate_game()
