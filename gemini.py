from langchain_google_genai import ChatGoogleGenerativeAI


def get_gemini_llm(
    model: str = "gemini-2.5-flash-lite",
    temperature: float = 0.2,
):
    """
    Low temperature is critical for syntactic correctness.
    """
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        max_output_tokens=256,
    )
