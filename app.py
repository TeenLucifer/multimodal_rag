import os
from pathlib import Path
from utils.parse_pdf import parse_doc

__dir__ = os.path.dirname(os.path.abspath(__file__))

# pdf解析
output_dir = Path("./pdf_docs/parse_results")
doc_path_list = [Path("./pdf_docs/deepseek-r1.pdf")]
parse_doc(
    path_list=doc_path_list,
    output_dir=output_dir,
    backend="pipeline"
)
output_path_list = [] # 解析结果输出目录
for doc_path in doc_path_list:
    output_path = Path(output_dir / doc_path.stem / "auto")
    output_path_list.append(output_path)

# 文档切分
# 读取"filename_content_list.json"

# 嵌入