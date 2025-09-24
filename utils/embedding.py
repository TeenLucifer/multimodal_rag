import os
import json
import base64
import chromadb
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import BaseNode, TextNode

from .request_models import request_vlm


load_dotenv()
dashscope_api_key               = os.getenv("DASHSCOPE_API_KEY")
dashscope_base_url              = os.getenv("DASHSCOPE_BASE_URL")
dashscope_llm_model_name        = os.getenv("DASHSCOPE_LLM_MODEL_NAME")
dashscope_vlm_model_name        = os.getenv("DASHSCOPE_VLM_MODEL_NAME")
dashscope_text_embed_model_name = os.getenv("DASHSCOPE_TEXT_EMBED_MODEL_NAME")

embed_model = DashScopeEmbedding(
    model_name=dashscope_text_embed_model_name,
    api_key=dashscope_api_key,
    base_url=dashscope_base_url,
    embed_batch_size=10
)

def _html_table_to_markdown_rapid(html_table):
    '''
    html格式的表格表格解析为markdown
    '''
    try:
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_table.strip(), 'html.parser')
        table = soup.find('table')
        if not table:
            raise ValueError("No <table> found in the HTML.")

        # 初始化存储表格内容的矩阵
        rows = []
        max_cols = 0

        # 解析所有行
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all(['td', 'th']):
                rowspan = int(cell.get('rowspan', 1))  # 获取 rowspan
                colspan = int(cell.get('colspan', 1))  # 获取 colspan
                text = cell.get_text(strip=True)  # 获取单元格内容

                # 填充矩阵，支持跨行或跨列的单元格
                for _ in range(colspan):
                    cells.append({'text': text, 'rowspan': rowspan})
            rows.append(cells)
            max_cols = max(max_cols, len(cells))  # 更新列数

        # 扩展矩阵，处理 rowspan 占用的单元格
        expanded_rows = []
        rowspan_tracker = [0] * max_cols  # 追踪每列的 rowspan
        for row in rows:
            expanded_row = []
            col_idx = 0
            for cell in row:
                # 跳过因 rowspan 导致的占位列
                while col_idx < max_cols and rowspan_tracker[col_idx] > 0:
                    expanded_row.append(None)
                    rowspan_tracker[col_idx] -= 1
                    col_idx += 1

                # 添加当前单元格
                expanded_row.append(cell['text'])
                # 更新 rowspan 追踪器
                if cell['rowspan'] > 1:
                    rowspan_tracker[col_idx] = cell['rowspan'] - 1
                col_idx += 1

            # 补全因 rowspan 导致的剩余占位符
            while col_idx < max_cols:
                if rowspan_tracker[col_idx] > 0:
                    expanded_row.append(None)
                    rowspan_tracker[col_idx] -= 1
                else:
                    expanded_row.append("")
                col_idx += 1

            expanded_rows.append(expanded_row)

        # 将第一行视为表头
        headers = expanded_rows[0]
        body_rows = expanded_rows[1:]

        # 生成 Markdown 表格
        markdown = ''
        if headers:
            markdown += '| ' + ' | '.join(h if h else '' for h in headers) + ' |\n'
            markdown += '| ' + ' | '.join(['-' * (len(h) if h else 3) for h in headers]) + ' |\n'
        for row in body_rows:
            markdown += '| ' + ' | '.join(cell if cell else '' for cell in row) + ' |\n'

        return markdown

    except Exception as e:
        print(f"Error parsing table: {e}")
        return ''

def create_nodes(parsed_result_path_list: List[Path]) -> List[List[BaseNode]]:
    nodes_list = []
    for parsed_result_path in parsed_result_path_list:
        source_file = parsed_result_path.parent.name
        content_file = parsed_result_path / (source_file + "_content_list.json")
        try:
            with open(content_file, 'r', encoding="utf-8") as f:
                content_list = json.load(f)
                nodes = []
                for content in content_list:
                    # 文本直接储存为文本节点
                    if content.get("type") == "text":
                        text_content = content.get("text")

                        meta_info = {
                            "content_type": "text",
                            "page_idx": content.get("page_idx"),
                            "source_file": str(source_file) + ".pdf",
                            "image_path": ""
                        }
                        text_node = TextNode(
                            text=text_content,
                            metadata=meta_info
                        )
                        nodes.append(text_node)
                    # 公式储存为文本节点, 并在meta信息中储存图片链接
                    # TODO(wangjintao): 把公式前后的段落组合到一起, 认为是一个完整的分段
                    elif content.get("type") == "equation":
                        text_content = content.get("text")
                        image_path = content.get("img_path")
                        full_image_path = (parsed_result_path / image_path).as_posix()

                        meta_info = {
                            "content_type": "equation",
                            "page_idx": content.get("page_idx"),
                            "source_file": str(source_file) + ".pdf",
                            "image_path": full_image_path
                        }
                        text_node = TextNode(
                            text=text_content,
                            metadata=meta_info
                        )
                        nodes.append(text_node)
                    # 表格储存为文本节点, 并在meta信息中储存图片链接
                    # TODO(wangjintao): 把表格前后的段落组合到一起, 认为是一个完整的分段
                    elif content.get("type") == "table":
                        table_body = content.get("table_body")
                        table_caption = ""
                        for caption in content.get("table_caption"):
                            table_caption = table_caption + caption + "\n"
                        image_path = content.get("img_path")
                        full_image_path = (parsed_result_path / image_path).as_posix()

                        # 把table_body从html格式转为markdown格式
                        table_body_markdown = _html_table_to_markdown_rapid(table_body)
                        table_content = table_body_markdown + "\n" + table_caption

                        meta_info = {
                            "content_type": "table",
                            "page_idx": content.get("page_idx"),
                            "source_file": str(source_file) + ".pdf",
                            "image_path": full_image_path
                        }
                        text_node = TextNode(
                            text=table_content,
                            metadata=meta_info
                        )
                        nodes.append(text_node)
                    # 图片储存为图片节点
                    elif content.get("type") == "image":
                        image_caption = ""
                        for caption in content.get("image_caption"):
                            image_caption = image_caption + caption + "\n"
                        image_path = content.get("img_path")
                        full_image_path = (parsed_result_path / image_path).as_posix()
                        # 用VLM把图片描述为文本, 通过文本进行嵌入
                        with open(full_image_path, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode("utf-8")
                        system_content = {
                            "role": "system",
                            "content": [{"type": "text", "text": "You are a helpful assistant."}]
                        }
                        user_content = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url":{"url": f"data:image/jpeg;base64,{img_b64}"},
                                },
                                {
                                    "type": "text",
                                    "text": f"The caption of the image is:{image_caption}, please describe the uploaded image in detail."
                                },
                            ],
                        }
                        image_content = request_vlm(system_content=system_content, user_content=user_content)
                        image_content = image_caption + "\n" + image_content

                        meta_info = {
                            "content_type": "image",
                            "page_idx": content.get("page_idx"),
                            "source_file": str(source_file) + ".pdf",
                            "image_path": full_image_path
                        }
                        text_node = TextNode(
                            text=image_content,
                            metadata=meta_info
                        )
                        nodes.append(text_node)
                nodes_list.append(nodes)

        except Exception as e:
            print(f"处理文件 {content_file} 时发生错误: {str(e)}")
            continue

    return nodes_list

def build_corpus(nodes_list: List[List[BaseNode]], persist_dir: Path):
    '''
    创建语料库并嵌入
    '''
    chroma_dir = persist_dir
    chroma_dir.mkdir(exist_ok=True) # 创建持久化目录
    db = chromadb.PersistentClient(path=str(chroma_dir)) # 创建ChromaDB客户端

    filename_list = []

    for nodes in nodes_list:
        filename_list.append(nodes[0].metadata["source_file"])
    for filename, nodes in zip(filename_list, nodes_list):
        collection_name = filename.split(".")[0]

        # 获取或创建集合
        collection = db.get_or_create_collection(collection_name)

        # 创建向量存储
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 创建索引
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=embed_model
        )
        print(f"构建语料库{collection_name}成功")

def load_corpus(corpus_name: str, persist_dir: Path) -> VectorStoreIndex:
    '''
    加载语料库
    '''
    db = chromadb.PersistentClient(path=str(persist_dir))

    try:
        # 获取集合
        collection = db.get_collection(corpus_name)

        # 创建向量存储
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 加载索引
        index = VectorStoreIndex(
            nodes=[],  # 从存储中加载，不需要传入nodes
            storage_context=storage_context,
            embed_model=embed_model
        )
        return index

    except Exception as e:
        print(f"加载语料库{corpus_name}失败: {e}")

def list_collections(persist_dir: Path) -> List[str]:
    db = chromadb.PersistentClient(path=str(persist_dir))
    collections = db.list_collections()
    collections_names = [collection.name for collection in collections]
    return collections_names