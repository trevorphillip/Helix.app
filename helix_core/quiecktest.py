from openai import OpenAI

client = OpenAI(
  api_key="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"
)

response = client.responses.create(
  model="gpt-4o-mini",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text);
