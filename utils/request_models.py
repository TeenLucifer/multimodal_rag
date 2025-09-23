import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
dashscope_api_key               = os.getenv("DASHSCOPE_API_KEY")
dashscope_base_url              = os.getenv("DASHSCOPE_BASE_URL")
dashscope_llm_model_name        = os.getenv("DASHSCOPE_LLM_MODEL_NAME")
dashscope_vlm_model_name        = os.getenv("DASHSCOPE_VLM_MODEL_NAME")
dashscope_text_embed_model_name = os.getenv("DASHSCOPE_TEXT_EMBED_MODEL_NAME")

client = OpenAI(
    api_key=dashscope_api_key,
    base_url=dashscope_base_url,
)

def request_vlm(user_content: dict) -> str:
    completion = client.chat.completions.create(
        model=dashscope_vlm_model_name,
        messages=[
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}],
            },
            user_content
        ],
    )
    return completion.choices[0].message.content

def request_llm():
    pass