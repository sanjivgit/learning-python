from langchain_core.prompts import PromptTemplate

chat_prompt = PromptTemplate(
    template="""
You are a helpful, concise AI assistant.

Conversation so far:
{history}

User:
{input}

Assistant:
""",
    input_variables=["history", "input"],
)
