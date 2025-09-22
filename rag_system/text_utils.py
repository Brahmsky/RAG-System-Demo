import docx
from pathlib import Path
from langchain.text_splitter import SpacyTextSplitter

class TextProcessor:
    @staticmethod
    def read_file(path: Path) -> str:
        """
        根据文件类型读取并返回全部文本内容。支持.txt,.md,.docx
        """
        if not path.exists():
            raise FileNotFoundError(f"文件 {path} 不存在")
        ext = path.suffix.lower()
        if ext in [".txt", ".md"]:
            return path.read_text(encoding="utf-8")
        elif ext == ".docx":
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        else:
            raise ValueError(f"不支持的文件类型: {ext}(文件: {path})")

    @staticmethod
    def split_text(corpus: str, language="English", chunk_size=512, overlap=50):
        if language == "English":
            pipeline = "en_core_web_sm"
        elif language == "Chinese":
            pipeline = "zh_core_web_sm"
        else:
            raise ValueError("未知语言")
        splitter = SpacyTextSplitter(pipeline=pipeline, chunk_size=chunk_size, chunk_overlap=overlap)
        return splitter.split_text(corpus) # 这里去掉打印日志的逻辑了