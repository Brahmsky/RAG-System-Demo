import docx
from pathlib import Path
from langchain.text_splitter import SpacyTextSplitter, RecursiveCharacterTextSplitter
from typing import List

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
    def split_text(
        corpus: str,
        language: str = "auto",  # auto / Chinese / English
        chunk_size: int = 512,   # 建议中文用 384~512，英文用 256~384
        chunk_overlap: int = 50
    ) -> List[str]:

        # 自动检测语言（简单版）
        if language == "auto":
            chinese_chars = sum(1 for c in corpus if '\u4e00' <= c <= '\u9fff')
            english_chars = sum(1 for c in corpus if 'a' <= c.lower() <= 'z')
            language = "Chinese" if chinese_chars > english_chars else "English"

        # 根据语言设置分隔符和默认 chunk_size
        if language == "Chinese":
            separators = [
                "\n\n",         # 段落
                "\n",           # 行
                "。|！|？|；",   # 句号类（支持正则）
                "，|、",         # 逗号类
                " ",            # 空格（中英文混合时有用）
                ""              # 字符级兜底
            ]
            if chunk_size == 512:  # 如果没指定，中文默认更大
                chunk_size = 512
        else:  # English
            separators = [
                "\n\n",
                "\n",
                ". |! |? |; ",  # 注意空格，避免切在缩写如 "Dr." 后面
                ", ",
                " ",
                ""
            ]
            if chunk_size == 512:
                chunk_size = 256  # 英文信息密度高，块小点

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,  # 按字符数，简单可靠
            is_separator_regex=True  # 允许使用正则表达式分隔符（中文需要）
        )

        chunks = splitter.split_text(corpus)

        # 可选：过滤掉过短的块（比如只有标点或空格）
        chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 20]

        print(f"[文本切分] 完成：{len(chunks)} 个块 | 语言：{language} | 目标块大小：{chunk_size}")
        return chunks