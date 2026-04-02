from langchain_core.prompts import ChatPromptTemplate
from gemini import get_gemini_llm
from prompts import SYSTEM_PROMPT, USER_PROMPT


def generate_alpha_expression() -> str:
    llm = get_gemini_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]
    )

    chain = prompt | llm

    response = chain.invoke({})
    expr = response.content.strip()

    return expr
    return "Sub(Add(close, 0.5), 0.5)"
