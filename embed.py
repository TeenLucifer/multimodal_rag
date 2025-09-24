import os
from pathlib import Path
#from utils.parse_pdf import parse_doc
from utils.embedding import create_nodes, build_corpus
from dotenv import load_dotenv


load_dotenv()
dashscope_api_key               = os.getenv("DASHSCOPE_API_KEY")
dashscope_base_url              = os.getenv("DASHSCOPE_BASE_URL")
dashscope_llm_model_name        = os.getenv("DASHSCOPE_LLM_MODEL_NAME")
dashscope_vlm_model_name        = os.getenv("DASHSCOPE_VLM_MODEL_NAME")
dashscope_text_embed_model_name = os.getenv("DASHSCOPE_TEXT_EMBED_MODEL_NAME")

# pdf解析 - 使用绝对路径
__dir__ = os.path.dirname(os.path.abspath(__file__))
output_dir = Path(__dir__) / "pdf_docs" / "parse_results"
doc_path_list = [Path(__dir__) / "pdf_docs" / "deepseek-r1.pdf"]
persist_dir = Path(__dir__) / "chroma_storage"
#parse_doc(
#    path_list=doc_path_list,
#    output_dir=output_dir,
#    backend="pipeline"
#)
output_path_list = [] # 解析结果输出目录
for doc_path in doc_path_list:
    output_path = Path(output_dir / doc_path.stem / "auto")
    output_path_list.append(output_path)
# 文档切分
nodes_list = create_nodes(parsed_result_path_list=output_path_list)
# 嵌入
build_corpus(nodes_list=nodes_list, persist_dir=persist_dir)