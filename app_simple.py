import os
from pathlib import Path
import streamlit as st
import PyPDF2
from typing import Dict, Any
from utils.retrieval import retrieve, synthesis_response
from utils.embedding import create_nodes, build_corpus
from utils.parse_pdf import parse_doc
from typing import List

from llama_index.core.retrievers import BaseRetriever

from streamlit.runtime.uploaded_file_manager import UploadedFile


__dir__ = os.path.dirname(os.path.abspath(__file__))

# 模拟MinerU解析功能
def mock_parse_pdf(pdf_file) -> Dict[str, Any]:
    """模拟PDF解析功能"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        
        # 提取文本内容
        full_text = ""
        for page_num in range(min(num_pages, 2)):  # 提取前2页
            page = pdf_reader.pages[page_num]
            full_text += page.extract_text() + "\n\n"
        
        # 生成markdown格式的解析结果
        markdown_result = "你好"

        
        return {
            "markdown": markdown_result,
            "text": full_text,
            "pages": num_pages
        }
    except Exception as e:
        return {"error": str(e)}

# 模拟RAG系统
class SimpleRAG:
    def __init__(self):
        self.history = []
        self.documents = []

    def add_document(self, text: str, filename: str):
        self.documents.append({"text": text[:500], "filename": filename})

    def chat(self, question: str) -> str:
        self.history.append({"role": "user", "content": question})

        # 简单的回复逻辑
        if "pdf" in question.lower() or "文档" in question.lower():
            if self.documents:
                response = f"基于上传的文档，我可以回答关于PDF内容的问题。当前知识库中有{len(self.documents)}个文档。"
            else:
                response = "请先上传PDF文档，我才能基于文档内容回答。"
        else:
            response = f"我理解了您的问题：'{question}'。这是一个模拟的RAG系统回复。"

        self.history.append({"role": "assistant", "content": response})
        return response

def build_knowledge_base(uploaded_files: List[UploadedFile]):
    pdf_dir = "pdf_docs"
    output_dir = Path(__dir__) / pdf_dir / "parse_results"
    persist_dir = Path(__dir__) / "chroma_storage"

    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    for file in uploaded_files:
        try:
            file_path = os.path.join(pdf_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
        except Exception as e:
            st.error(f"加载文件 {file.name} 失败: {e}")

    doc_path_list = []
    if file.name.endswith(".pdf"):
        doc_path_list.append(Path(__dir__) / pdf_dir / file.name)
    # pdf解析
    parse_doc(path_list=doc_path_list, output_dir=output_dir)
    output_path_list = [] # 解析结果输出目录
    for doc_path in doc_path_list:
        output_path = Path(output_dir / doc_path.stem / "auto")
        output_path_list.append(output_path)
    # 文档切分
    nodes_list = create_nodes(parsed_result_path_list=output_path_list)
    # 嵌入
    build_corpus(nodes_list=nodes_list, persist_dir=persist_dir)

# 初始化session state
if 'history' not in st.session_state:
    st.session_state.history = []

st.set_page_config(
    page_title="RAG对话与PDF解析",
    page_icon="📚",
    layout="wide"
)

st.title("📚 RAG对话与PDF解析系统")
st.markdown("---")

# 创建两列布局
col1, col2 = st.columns([1, 1])

# 左侧：RAG对话
with col1:
    st.header("💬 RAG对话")

    # 显示对话历史
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # 用户输入
    if question := st.chat_input("请输入您的问题..."):
        #nodes = retrieve(query=question, retriever=)
        #response = synthesis_response(query=question, nodes=nodes)
        response = "你好"
        st.rerun()

    if st.button("清除对话"):
        st.session_state.rag.history = []
        st.rerun()

# 右侧：PDF上传和解析
with col2:
    st.header("📄 PDF上传与解析")

    uploaded_files = st.file_uploader(
        "选择PDF文件",
        type=['pdf'],
        help="上传PDF文件查看解析结果"
    )

    if uploaded_files:
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button("开始解析", type="primary"):
                with st.spinner("正在解析PDF..."):
                    build_knowledge_base()

        with col_btn2:
            if st.button("清除结果"):
                st.rerun()

        ## 显示解析结果
        #if st.session_state.parse_result:
        #    result = st.session_state.parse_result

        #    if "error" in result:
        #        st.error(f"解析失败: {result['error']}")
        #    else:
        #        st.subheader("📊 解析结果")
        #        st.markdown(result["markdown"])
    else:
        st.info("👆 请上传PDF文件查看解析结果")

# 底部信息
st.markdown("---")
st.caption("🚀 基于Streamlit的RAG对话与PDF解析演示系统")