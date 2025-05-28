import pandas as pd
import os

enem2022 = pd.read_json("hf://datasets/maritaca-ai/enem/2022.jsonl", lines=True)
enem2023 = pd.read_json("hf://datasets/maritaca-ai/enem/2023.jsonl", lines=True)
enem2024 = pd.read_json("hf://datasets/maritaca-ai/enem/2024.jsonl", lines=True)

print(enem2022.columns)
questions = enem2022['question']

for quest in questions:
    tags = quest.split(" ")
    print(tags)