import re
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='jieba') # 2025.10.7

import jieba  # 之后再导入 jieba

def smart_tokenize(text, lang="auto"):
    has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', text))
    if lang == "zh" or (lang == "auto" and has_chinese):
        tokens = list(jieba.cut(text.lower()))
        tokens = [token.strip() for token in tokens
                  if len(token.strip()) >= 1 and re.match(r'[\u4e00-\u9fa5a-zA-Z0-9]+', token)] # 这里>=1，暂且全部添加
    else:
        tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return tokens