from langchain_ollama import ChatOllama

# llm = ChatOllama(
#     model="deepseek-r1:14b",
#     base_url="http://localhost:11434",
#     timeout=300,
#     stream=False
# )

llm = ChatOllama(
    model="qwen2.5:14b",
    base_url="http://localhost:11434",
    timeout=300,
    stream=False
)