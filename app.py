import os
from typing import List
from pathlib import Path
from pdf2image import convert_from_path

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from utils.parse_pdf import parse_doc
from utils.retrieval import retrieve, synthesis_response
from utils.embedding import create_nodes, build_corpus, load_corpus, list_collections

__dir__ = os.path.dirname(os.path.abspath(__file__))
pdf_dir = "pdf_docs"
persist_dir = Path(__dir__) / "chroma_storage"
parse_output_dir = Path(__dir__) / pdf_dir / "parse_results"

def build_knowledge_base(uploaded_files: List[UploadedFile]) -> List[Path]:
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
    parse_doc(path_list=doc_path_list, output_dir=parse_output_dir)
    output_path_list = [] # 解析结果输出目录
    for doc_path in doc_path_list:
        output_path = Path(parse_output_dir / doc_path.stem / "auto")
        output_path_list.append(output_path)
    # 文档切分
    nodes_list = create_nodes(parsed_result_path_list=output_path_list)
    # 嵌入
    build_corpus(nodes_list=nodes_list, persist_dir=persist_dir)

    return output_path_list

# 初始化session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'retriever' not in st.session_state:
    st.session_state.retriever = None
if 'output_path_list' not in st.session_state:
    st.session_state.output_path_list = None

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
        st.session_state.history.append({"role": "user", "content": question})
        if st.session_state.retriever is not None:
            nodes = retrieve(query=question, retriever=st.session_state.retriever)
            response = synthesis_response(query=question, nodes=nodes)
            st.session_state.history.append({"role": "assistant", "content": response})
        st.rerun()

    if st.button("清除对话"):
        st.session_state.history = []
        st.rerun()

    # 添加collections下拉栏
    st.markdown("---")
    st.subheader("📚 加载知识库")

    try:
        collections = list_collections(persist_dir=persist_dir)
        selected_collection = st.selectbox(
            "选择知识库",
            options=collections,
            help="选择要使用的知识库"
        )

        if st.button("加载知识库"):
            if selected_collection:
                with st.spinner(f"正在加载 {selected_collection}..."):
                    # 调用load_corpus函数加载选中的collection
                    try:
                        loaded_index = load_corpus(corpus_name=selected_collection, persist_dir=persist_dir)
                        st.session_state.retriever = loaded_index.as_retriever(
                            similarity_top_k=5,
                            vector_store_query_mode="default",
                        )
                        st.success(f"加载知识库: {selected_collection} 成功")
                    except Exception as e:
                        st.error(f"加载知识库失败: {e}")

    except Exception as e:
        st.error(f"获取知识库失败: {e}")
        st.selectbox(
            "选择Collection",
            options=["无可用只四库"],
            disabled=True
        )

# 右侧：PDF上传和解析
with col2:
    st.header("📄 PDF上传与解析")

    uploaded_files = st.file_uploader(
        "选择PDF文件",
        type=['pdf'],
        help="上传PDF文件查看解析结果",
        accept_multiple_files=True
    )

    if uploaded_files:
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button("开始解析", type="primary"):
                with st.spinner("正在解析PDF..."):
                    output_path_list = build_knowledge_base(uploaded_files=uploaded_files)
                    # 解析成功后，保存PDF文件信息用于预览
                    st.session_state.output_path_list = output_path_list
                    st.success("PDF解析完成！")

        with col_btn2:
            if st.button("清除结果"):
                st.session_state.output_path_list = None
                st.rerun()

    # PDF预览区域
    if st.session_state.output_path_list:
        st.markdown("---")
        st.subheader("📖 PDF解析预览")
        for output_path in st.session_state.output_path_list:
            pdf_name = output_path.as_posix().split("/")[-2]
            with st.expander(f"📄 {pdf_name}", expanded=True):
                try:
                    # 转换PDF页面为图片（只转换前几页以提高性能）
                    images = convert_from_path(output_path / (pdf_name + "_layout.pdf"), first_page=1, last_page=5)
                    num_pages = len(images)

                    if num_pages > 0:
                        # 创建页码选择器
                        page_num = st.selectbox(
                            f"选择要预览的页码 ({pdf_name})",
                            range(1, num_pages + 1),
                            key=f"page_select_{pdf_name}"
                        )

                        # 显示选中页面的图片
                        if page_num:
                            st.image(
                                images[page_num - 1], 
                                caption=f"第 {page_num} 页",
                                width="stretch"
                            )
                    else:
                        st.warning("无法将PDF转换为图片")

                except Exception as e:
                    st.error(f"PDF预览失败: {e}")

    else:
        st.info("👆 请上传PDF文件查看解析结果")

# 底部信息
st.markdown("---")
st.caption("🚀 基于Streamlit的RAG对话与PDF解析演示系统")