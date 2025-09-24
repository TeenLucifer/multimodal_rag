import os
from pathlib import Path
#from utils.parse_pdf import parse_doc
from typing import Dict, Any
import chromadb

from llama_index.core import VectorStoreIndex

from utils.embedding import load_corpus
from utils.retrieval import retrieve, synthesis_response

# pdf解析 - 使用绝对路径
__dir__ = os.path.dirname(os.path.abspath(__file__))
persist_dir = Path(__dir__) / "chroma_storage"

# 加载语料库
index = load_corpus(
    corpus_name="deepseek-r1",
    persist_dir=persist_dir
)
# 索引
retriever = index.as_retriever(
    similarity_top_k=5,
    vector_store_query_mode="default",
)

query = "how does deepseek-r1-zero perform on AIME during training"
nodes = retrieve(query=query, retriever=retriever)
response = synthesis_response(query=query, nodes=nodes)
print(response)