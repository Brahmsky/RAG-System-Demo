# RAG_demo - 双引擎智能问答系统

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![RAG](https://img.shields.io/badge/RAG-Retrieval%20Augmented%20Generation-orange.svg)](https://arxiv.org/abs/2005.11401)
[![Knowledge Graph](https://img.shields.io/badge/Knowledge%20Graph-Neo4j-green.svg)](https://neo4j.com/)

一个基于检索增强生成（RAG）技术的双引擎智能问答系统，融合**文本检索**和**知识图谱**，支持多种文档格式、多种检索策略和多语言处理。

## 🌟 主要特性

### 🔍 双引擎检索架构
- **文本检索引擎**: 向量检索 (HNSW)、关键词检索 (BM25)、混合检索 (RRF)、多查询融合
- **知识图谱引擎**: 基于Neo4j的实体关系图谱，支持复杂语义推理
- **智能融合**: 自动选择最优检索策略，提供更精准的答案

### 📚 格式与语言支持
- **文档格式**: Markdown (.md)、Word文档 (.docx)、纯文本 (.txt)
- **多语言支持**: 中文 (jieba分词)、英文智能分词和检索优化
- **自动构图**: 从文档自动抽取实体关系，构建知识图谱

### 🚀 高级功能
- **🎯 智能重排序**: 基于 Cross-Encoder 的多语言结果重排序
- **💡 上下文压缩**: 抽取式压缩，减少 token 消耗，提升生成质量
- **🧠 实体消歧**: LLM驱动的实体识别与合并，保证图谱质量
- **⚡ 持久化存储**: ChromaDB + Neo4j + 增量更新，避免重复处理
- **🏗️ 模块化架构**: 遵循SOLID原则，依赖注入设计，易于扩展和测试

## 🏗️ 系统架构

```mermaid
graph TB
    A[用户查询] --> B[RAGSystem]
    B --> C[文本检索路径]
    B --> D[图谱检索路径]
    
    C --> E[Retriever]
    E --> F[向量检索 Embedder]
    E --> G[关键词检索 BM25]
    E --> H[多查询扩展 MultiqueryGenerator]
    
    F --> I[Reranker重排序]
    G --> I
    H --> I
    I --> J[Compressor压缩]
    
    D --> K[Neo4j图谱]
    K --> L[Cypher查询生成]
    
    J --> M[Generator生成器]
    L --> M
    M --> N[最终答案]
    
    O[知识库文档] --> P[TextProcessor]
    P --> Q[ChromaDB存储]
    P --> R[Data2Neo4j图谱构建]
    R --> K

### 设计模式亮点

#### 依赖注入模式
**问题**: 在重构过程中遇到的依赖纠缠问题
- Retriever 类需要使用 MultiqueryGenerator，但后者需要 LLM 参数
- 如果让 Retriever 直接依赖 LLM，会导致模块职责膨胀

**解决方案**: 依赖倒置 + 抽象接口
```python
# 1. 定义抽象接口
class QueryExpander:
    def expand(self, query: str, num_queries: int) -> List[str]:
        raise NotImplementedError

# 2. 具体实现
class MultiqueryGenerator(QueryExpander):
    def expand(self, query, num_queries=3):
        # LLM 生成多查询逻辑
        return queries

# 3. 依赖注入
self.retriever = Retriever(db, embedder, query_expander=query_expander)
```

#### 策略模式
- **QueryExpander** 作为策略接口
- **MultiqueryGenerator** 作为具体策略实现
- 可轻易添加其他查询扩展策略（如基于规则的扩展、词汇扩展等）

## 🚀 完整部署指南

> ⚠️ **重要提示**: 本系统依赖Neo4j数据库存储知识图谱，必须先安装和配置Neo4j

### 步骤1: 系统要求检查

- **Python 3.9+** (检查: `python --version`)
- **内存**: 至少4GB RAM (推荐8GB+)
- **硬盘空间**: 至尚2GB 可用空间
- **网络**: 稳定的互联网连接 (调用 Gemini API)

### 步骤2: Neo4j数据库安装 🔧

#### 选项A: Neo4j Desktop (🔥 推荐新手)

1. **下载安装**
   ```bash
   # 访问官网下载并安装
   https://neo4j.com/download/
   ```

2. **创建数据库**
   - 打开 Neo4j Desktop
   - 点击 "**New**" -> "**Create Database**"
   - 设置数据库名称: `rag-knowledge-graph`
   - **设置密码**: `password123` (请记住这个密码！)
   - 点击 "**Create**"

3. **启动服务**
   - 选中刚创建的数据库
   - 点击 "**Start**" 按钮
   - 等待状态变为 "**Running**" (通常陠30-60秒)

4. **验证安装**
   ```bash
   # 访问 Web 界面
   http://localhost:7474
   
   # 登录信息
   URI: bolt://localhost:7687
   Username: neo4j
   Password: password123
   ```

#### 选项B: Docker部署 (🚀 推荐开发者)

```bash
# 1. 下载并运行Neo4j容器
docker run \
    --name rag-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -v rag_neo4j_data:/data \
    -v rag_neo4j_logs:/logs \
    --env NEO4J_AUTH=neo4j/password123 \
    --env NEO4J_PLUGINS='["apoc"]' \
    neo4j:5.15

# 2. 检查容器状态
docker ps | grep rag-neo4j

# 3. 查看日志 (确保正常启动)
docker logs rag-neo4j | tail -20

# 4. 验证访问
echo "访问 http://localhost:7474 进行验证"
```

#### 选项C: Neo4j Aura Cloud (☁️ 推荐生产环境)

1. **注册账户**
   ```bash
   # 访问官网注册免费账户
   https://neo4j.com/cloud/aura/
   ```

2. **创建实例**
   - 点击 "**Create Instance**"
   - 选择 "**AuraDB Free**" (免费套餐)
   - 选择区域: 亚太地区 (优化延迟)
   - 记住生成的密码！

3. **获取连接信息**
   ```
   URI: neo4j+s://xxxxxxxx.databases.neo4j.io
   Username: neo4j  
   Password: 系统生成的密码
   ```

### 步骤3: 项目环境配置

```bash
# 1. 克隆项目
git clone https://github.com/Brahmsky/RAG-System-Demo.git
cd RAG-System-Demo

# 2. 创建虚拟环境 (强烈推荐)
python -m venv rag_env

# Windows 激活
rag_env\Scripts\activate

# Linux/Mac 激活
source rag_env/bin/activate

# 3. 升级pip并安装依赖
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. 下载语言模型
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

### 步骤4: 配置环境变量

#### 必需: Google API Key

**Windows (PowerShell):**
```powershell
# 设置环境变量
$env:GOOGLE_API_KEY="your_google_api_key_here"

# 验证设置
echo $env:GOOGLE_API_KEY
```

**Linux/Mac:**
```bash
# 设置环境变量
export GOOGLE_API_KEY="your_google_api_key_here"

# 验证设置
echo $GOOGLE_API_KEY

# 永久保存 (可选)
echo 'export GOOGLE_API_KEY="your_google_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

#### 可选: Neo4j 连接信息

> 如果使用默认设置 (localhost:7687, neo4j/password123)，可跳过此步骤

**Windows (PowerShell):**
```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="password123"
```

**Linux/Mac:**
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password123"
```

### 步骤5: 运行系统

```bash
# 基础测试
python main.py

# 如果成功，您将看到类似输出:
# [Neo4jDatabase] Driver initialized.
# [Data2Neo4j] Compatibility adapter initialized.
# 开始处理知识库文件...
```

### 步骤6: 验证功能

```python
# 打开Python命令行测试
python

# 在Python交互式环境中运行:
from rag_system.config import RAGConfig
from rag_system.rag_system import RAGSystem

config = RAGConfig(embedding_model_name="gemini-embedding-001", verbose=True)
rag = RAGSystem(config)

# 测试文本检索
result = rag.query("什么是人工智能？", mode="vector")
print(result)

# 测试知识图谱 (需要先添加数据)
rag.add_corpus("test_build_graph.md")
result = rag.query("图灵都研究啥的？", mode="graph")
print(result)
```

### 3. 配置环境变量

**设置 Google API Key:**

Windows (PowerShell):
```powershell
$env:GOOGLE_API_KEY="your_google_api_key_here"
```

Linux/Mac:
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

### 步骤7: 常见问题排查 🔧

如果遇到问题，请按照以下步骤排查：

#### Neo4j 连接问题
```bash
# 1. 检查Neo4j服务状态
# Neo4j Desktop: 确保显示"Running"
# Docker: docker ps | grep neo4j

# 2. 检查端口
netstat -an | findstr 7687  # Windows
netstat -an | grep 7687     # Linux/Mac

# 3. 测试连接
# 访问 http://localhost:7474 并登录
```

#### APOC插件问题
```bash
# 如果看到"apoc.refactor.mergeNodes not found"
# 不用担心，系统会自动跳过实体合并功能
# 如需安装: Neo4j Desktop -> Plugins -> APOC -> Install
```

#### API Key问题
```bash
# 检查设置
echo $GOOGLE_API_KEY        # Linux/Mac
echo $env:GOOGLE_API_KEY    # Windows

# 如果显示空白，请重新设置并重启终端
```

## 📖 使用指南

### 基本用法

```python
from rag_system.config import RAGConfig
from rag_system.rag_system import RAGSystem

# 1. 创建配置
config = RAGConfig(
    embedding_model_name="gemini-embedding-001",
    llm_model_name="gemini-2.0-flash",
    verbose=True
)

# 2. 初始化 RAG 系统
rag = RAGSystem(config)

# 3. 添加知识库文档
rag.add_corpus("biology_knowledge.md", language="English")
rag.add_corpus("中文文档.docx", language="Chinese")

# 4. 执行查询
answer = rag.query(
    query="图灵被定成什么罪了？",
    mode="graph",       # 检索模式: text/graph/fusion
    compress=True       # 是否启用上下文压缩
)
print(answer)
```

### 知识库管理

#### 添加文档
```python
# 添加 Markdown 文件 (英文)
rag.add_corpus("advanced_retrieval.md", language="English")

# 添加 Word 文档 (中文)
rag.add_corpus("技术规范.docx", language="Chinese")

# 系统会自动检查重复，只添加新的文档块
```

#### 更新文档
```python
# 更新已存在的文档 (先删除再添加)
rag.update_corpus("biology_knowledge.md", language="English")
```

#### 删除文档
```python
# 从知识库中删除指定文档
rag.remove_corpus("obsolete_document.md")
```

### 检索模式

| 模式 | 描述 | 技术原理 | 适用场景 |
|------|------|----------|----------|
| `vector` | 纯向量检索 | HNSW 算法，语义相似度 | 概念性问题，语义相似性搜索 |
| `keyword` | 纯关键词检索 | BM25 算法，精确匹配 | 专业术语、罕见关键词查找 |
| `hybrid` | 混合检索 | RRF 融合向量+关键词 | 平衡语义和关键词，日常使用 |
| `fusion` | 多查询融合 | LLM 查询扩展 + 多轮检索 | 最佳召回率和准确性 |

#### 检索模式细节
**关键词检索优势**:
- 对于包含 **精确、罕见术语** 的查询，能快速精确定位
- 示例: 查询 "Okapi formula" 时，BM25 直接命中相关文档

**向量检索优势**:
- 理解语义关联，适合概念性和抽象问题
- 能够找到语义相似但关键词不同的文档

**Fusion 模式原理**:
1. LLM 生成多个语义相关查询
2. 对每个查询执行混合检索
3. 使用 RRF 算法融合所有结果

#### 检索模式示例
```python
# 向量检索 - 语义搜索
answer = rag.query("什么是人工智能？", mode="vector")

# 关键词检索 - 精确匹配
answer = rag.query("BM25 algorithm", mode="keyword")

# 混合检索 - 综合考虑
answer = rag.query("深度学习的应用", mode="hybrid")

# 多查询融合 - 最佳效果
answer = rag.query("机器学习算法比较", mode="fusion")

# 知识图谱检索 - 精确关系推理
answer = rag.query("图灵都研究啥的？", mode="graph")

# 双引擎融合 - 最全面覆盖
answer = rag.query("人工智能的发展历史和未来趋势", mode="hybrid_graph")
```

### 高级功能

#### 上下文压缩
```python
# 启用压缩，减少 token 消耗
answer = rag.query(
    query="详细介绍深度学习",
    mode="fusion",
    compress=True,  # 启用压缩
    k=20,          # 检索更多文档
    top_n=5        # 重排序后保留 5 个最相关的
)
```

#### 自定义配置
```python
config = RAGConfig(
    embedding_model_name="gemini-embedding-001",
    reranker_model_name="BAAI/bge-reranker-base",
    llm_model_name="gemini-2.0-flash",
    db_path="./custom_db",
    knowledgebase_path="./documents",
    verbose=False
)
```

## 📁 项目结构

```
RAG_demo/
├── Knowledgebase/              # 知识库文档目录
│   ├── biology_knowledge.md   # 生物学知识
│   ├── tech_news.md           # 技术新闻
│   └── ...
├── rag_system/                 # 核心系统模块
│   ├── config.py              # 配置管理
│   ├── rag_system.py          # 主系统类
│   ├── retriever.py           # 检索器
│   ├── reranker.py            # 重排序器
│   ├── compressor.py          # 压缩器
│   ├── generator.py           # 生成器
│   ├── database.py            # 数据库管理
│   ├── text_utils.py          # 文本处理工具
│   ├── smart_tokenize.py      # 智能分词
│   ├── neo/                   # 知识图谱模块
│   │   ├── Data2Neo4j.py        # 向后兼容适配器
│   │   ├── knowledge_graph_builder.py  # 主协调器
│   │   ├── graph_database.py    # Neo4j数据库操作
│   │   ├── entity_extractor.py  # 实体抽取器
│   │   ├── graph_processor.py   # 图谱处理器
│   │   ├── query_engine.py      # 图谱查询引擎
│   │   ├── entity_merger.py     # 实体合并器
│   │   └── data_structure.py    # 数据结构定义
│   └── ...
├── main.py                     # 主程序入口
├── requirements.txt            # 依赖列表
└── README.md                   # 项目文档
```

## 🔧 配置说明

### RAGConfig 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `embedding_model_name` | str | "gemini-embedding-001" | 嵌入模型名称 |
| `reranker_model_name` | str | "BAAI/bge-reranker-base" | 重排序模型名称 |
| `llm_model_name` | str | "gemini-2.5-flash" | 生成模型名称 |
| `db_path` | str | "./chroma_db" | 向量数据库路径 |
| `knowledgebase_path` | str | "./Knowledgebase" | 知识库文档路径 |
| `verbose` | bool | True | 是否显示详细日志 |

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | str | - | 用户查询问题 |
| `k` | int | 10 | 检索文档数量 |
| `top_n` | int | 3 | 重排序后保留数量 |
| `mode` | str | "hybrid" | 检索模式 |
| `compress` | bool | False | 是否启用压缩 |

## 🔍 支持的文件格式

- **Markdown** (`.md`) - 技术文档、知识库
- **Word文档** (`.docx`) - 正式文档、报告
- **纯文本** (`.txt`) - 简单文本文件

## 🌐 语言支持

### 中文处理
- 使用 `jieba` 分词库进行中文分词
- 支持 `zh_core_web_sm` spaCy 模型
- 优化的中文 BM25 检索

### 英文处理
- 使用 `en_core_web_sm` spaCy 模型
- 标准英文分词和处理

### 语言设置
```python
# 添加中文文档
rag.add_corpus("中文技术文档.md", language="Chinese")

# 添加英文文档
rag.add_corpus("english_document.md", language="English")
```

## ⚡ 性能优化

### 1. 增量更新
系统自动检测已存在的文档块，避免重复处理：
```python
# 只会添加新增的文档块
rag.add_corpus("updated_document.md")
```

### 2. 上下文压缩
减少 token 消耗，提升响应速度：
```python
answer = rag.query("问题", compress=True)
```

### 4. 检索策略性能对比
根据实际测试，不同检索策略的表现：

**测试查询**: "What is the Okapi formula?"

| 检索模式 | 精确性 | 召回率 | 适用场景 |
|------------|----------|----------|------------|
| **keyword** | 高 | 中等 | 精确术语匹配 |
| **vector** | 高 | 高 | 语义理解 |
| **hybrid** | 极高 | 最高 | 综合性能 |
| **fusion** | ⚡最高 | 最高 | 复杂查询 |

**关键发现**:

- **BM25** 对 "Okapi" 这种罕见术语能直接命中最相关文档
- **向量检索** 在语义理解上表现更佳，能找到更多相关内容
- **混合模式** 结合两者优势，效果最均衡

## 🔬 技术栈

- **深度学习框架**: PyTorch 2.8.0+cu126
- **向量数据库**: ChromaDB 1.0.20
- **搜索引擎**: BM25Okapi (rank-bm25)
- **文本处理**: LangChain, spaCy
- **嵌入模型**: Sentence Transformers
- **生成模型**: Google Gemini API
- **重排序**: Cross-Encoder 模型

## 🐛 常见问题

### Q1: 报错 "请先设置 GOOGLE_API_KEY 环境变量"
**解决方案**: 设置环境变量
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

### Q2: spaCy 模型下载失败
**解决方案**: 手动下载语言模型
```bash
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

### Q3: 依赖包安装问题
**问题描述**: torch 安装失败
**解决方案**: 

- 对于 CPU 环境：`pip install torch --index-url https://download.pytorch.org/whl/cpu`
- 对于 GPU 环境：`pip install torch --index-url https://download.pytorch.org/whl/cu121`
- 注意：项目主要使用 API 服务，不依赖 GPU 加速

### Q4: 中文检索效果不佳
**问题描述**: BM25 在处理中文时无法正确分词
**解决方案**: 
- 确保文档语言设置为 "Chinese"
- 检查 jieba 分词库是否正确安装
- 使用 `fusion` 模式获得更好效果
- 遇到单字符干扰时，系统会自动过滤

### Q5: Gemini API 批量处理限制
**问题描述**: 大文档分块超过 100 个时报错
**解决方案**: 系统已自动处理，每批 100 个文档块

### Q6: 内存不足
**解决方案**:
- 减少 `k` 参数值 (检索文档数量)
- 启用 `compress=True`
- 考虑分批处理大文档

### Q7: ChromaDB collection 命名问题
**问题描述**: 模型名包含斜杠时报错
**解决方案**: 系统自动将 "/" 替换为 "_"
**规范**: ChromaDB 仅允许小写字母、数字、点、破折号和下划线

### Q8: Fusion 模式 LLM 输出格式不稳定
**问题描述**: LLM 生成的查询格式不符合预期
**解决方案**: 
- 系统已优化提示词，增加了格式约束
- 使用 `split('\n\n')` 解析空行分隔的查询
- 对于不符合格式的输出，系统会降级为混合检索
