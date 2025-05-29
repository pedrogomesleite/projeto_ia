import re
import pandas as pd
import os

enem2022 = pd.read_json("hf://datasets/maritaca-ai/enem/2022.jsonl", lines=True)
enem2023 = pd.read_json("hf://datasets/maritaca-ai/enem/2023.jsonl", lines=True)
enem2024 = pd.read_json("hf://datasets/maritaca-ai/enem/2024.jsonl", lines=True)

print(enem2022.columns)

print(enem2022['exam'])
questions = enem2022['question']

dicionario = {}

for quest in questions:
    tags = re.sub(r'[,\.?;\\/]', ' ', quest).title().replace('[[placeholder]]', ' ').replace('[[Placeholder]]', ' ').replace("\n", ' ').split(" ")
    for i, tag in enumerate(tags):
        if not tags[i] in dicionario:
            dicionario[tags[i]] = 0
        dicionario[tags[i]] += 1


# categorizar as tags com fuzzy


tagsD = {}
for palavra in re.sub(r'[,\.?;\\/]', ' ', questions[2]).title().replace('[[placeholder]]', ' ').replace('[[Placeholder]]', ' ').replace("\n", ' ').split(" "):
    tagsD.setdefault(palavra, dicionario[palavra]);


print(dict(sorted(tagsD.items())))


# print(dicionario)