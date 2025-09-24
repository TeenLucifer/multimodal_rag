import base64
from typing import List
from llama_index.core.schema import BaseNode
from llama_index.core.retrievers import BaseRetriever

from .request_models import request_vlm

SYSTEM_PROMPT = """You are a multimodal reasoning assistant.
You are given the following inputs:

1. User query: {query}
2. Text context: {text_context}

Your task is to:
- Always start by understanding the user query.
- If images are uploaded, analyze both the text and image contexts together.
- If images are not uploaded or is empty, analyze only the text context.
- Integrate evidence from the available contexts when forming your answer.
- If information is missing, uncertain, or contradictory, explicitly state it.
- Provide a clear, well-structured response that directly addresses the query.
- Use reasoning that is faithful to the provided contexts; do not hallucinate unsupported details.
"""

def retrieve(query: str, retriever: BaseRetriever) -> List[BaseNode]:
    # TODO(wangjintao): 可以实现多路召回, HyDE等思路
    nodes = retriever.retrieve(query)
    return nodes

def synthesis_response(query: str, nodes: List[BaseNode]) -> str:
    if len(nodes) < 1:
        return "未找到相关答案"

    text_context = ""
    user_content = {
        "role": "user",
        "content": [
            {"type": "text", "text": query}
        ]
    }
    for node in nodes:
        if node.metadata["content_type"] in ("text", "equation", "table"):
            text_context = text_context + node.text + "\n" # 构建文本上下文
        elif node.metadata["content_type"] == ("image"):
            image_path = node.metadata["image_path"] # 构建图片上下文
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                user_content["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

    system_content = {
        "role": "system",
        "content": [{"type": "text","text": SYSTEM_PROMPT.format(query=query, text_context=text_context)}]
    }

    response = request_vlm(system_content=system_content, user_content=user_content)
    return response