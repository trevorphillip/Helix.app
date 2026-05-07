import os
from openai import OpenAI

print("Key present:", bool(os.getenv("")))
client = OpenAI(api_key=os.getenv("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"))

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role":"user","content":"Say 'hello from CRISPR app'"}]
)
print(resp.choices[0].message.content)
