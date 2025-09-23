import os
from pathlib import Path
#from utils.parse_pdf import parse_doc
from utils.embedding import create_nodes, build_corpus
from dotenv import load_dotenv
from typing import Dict, Any
import chromadb

from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from utils.embedding import load_corpus

load_dotenv()
dashscope_api_key               = os.getenv("DASHSCOPE_API_KEY")
dashscope_base_url              = os.getenv("DASHSCOPE_BASE_URL")
dashscope_llm_model_name        = os.getenv("DASHSCOPE_LLM_MODEL_NAME")
dashscope_vlm_model_name        = os.getenv("DASHSCOPE_VLM_MODEL_NAME")
dashscope_text_embed_model_name = os.getenv("DASHSCOPE_TEXT_EMBED_MODEL_NAME")

# pdf解析 - 使用绝对路径
__dir__ = os.path.dirname(os.path.abspath(__file__))
persist_dir = Path(__dir__) / "chroma_storage"
# 存储加载的索引
indices: Dict[str, VectorStoreIndex] = {}
query_engines: Dict[str, Any] = {}

#collections = self.db.list_collections()

# 加载语料库
index = load_corpus(
    corpus_name="deepseek-r1",
    embed_base_url=dashscope_base_url,
    embed_api_key=dashscope_api_key,
    embed_model_name=dashscope_text_embed_model_name,
    persist_dir=persist_dir
)
# 索引
retriever = index.as_retriever(
    similarity_top_k=5,
    vector_store_query_mode="default",
)

retrieve_res = retriever.retrieve("how does deepseek-r1 perform in math-500")
print(retrieve_res)