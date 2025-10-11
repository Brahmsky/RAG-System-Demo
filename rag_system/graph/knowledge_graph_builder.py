"""
知识图谱构建器
遵循SOLID原则的主要协调器类，组合其他专门的类来完成图谱构建
采用依赖注入和组合模式
"""
from typing import Dict, List
from .graph_database import Neo4jDatabase
from .entity_extractor import EntityExtractor
from .graph_processor import GraphProcessor
from .query_engine import GraphQueryEngine
from .entity_merger import EntityMerger


class KnowledgeGraphBuilder:
    """知识图谱构建器 - 主要协调器类"""
    
    def __init__(self, llm_client, model_name: str, neo4j_config: dict):
        # 初始化各个专门的组件
        self.graph_db = Neo4jDatabase(neo4j_config['uri'], neo4j_config['auth'])
        self.entity_extractor = EntityExtractor(llm_client, model_name)
        self.graph_processor = GraphProcessor(llm_client, model_name)
        self.query_engine = GraphQueryEngine(llm_client, model_name, self.graph_db)
        self.entity_merger = EntityMerger(llm_client, model_name, self.graph_db)
        
        # 文档级实体映射表：{filename: {entity_name: canonical_id}}
        self.document_entities: Dict[str, Dict[str, str]] = {}
    
    def close(self):
        """关闭数据库连接"""
        self.graph_db.close()
        
    # 移除__del__方法，避免重复关闭
    # 实际的资源管理由Neo4jDatabase负责
    
    def process_single_chunk(self, filename: str, text: str, doc_entities_mapping: Dict[str, str] | None = None):
        """
        处理单个文本块并构建知识图谱的主流程。
        1. 从文本中粗提取三元组（使用文档级实体映射）。
        2. 将三元组结构化并进行实体消歧。
        3. 校验并写入数据库。
        """
        # 第一步：粗提取
        raw_triples_str = self.entity_extractor.extract_raw_triples(
            text, filename, doc_entities_mapping
        )
        if not raw_triples_str or not raw_triples_str.strip():
            print(f"步骤 1: 未能从文本中提取到任何有效的三元组，处理终止。")
            return

        # 第二步：结构化与消歧
        existing_entities = self.graph_db.get_existing_entities()
        # 将文档级实体也加入到现有实体列表中，供消歧阶段使用
        if doc_entities_mapping:
            existing_entities.extend(doc_entities_mapping.values())
            
        function_call = self.graph_processor.structure_and_disambiguate_graph(
            raw_triples_str, existing_entities
        )
        if not function_call:
            print(f"步骤 2: LLM 未能将三元组结构化，处理终止。")
            return

        # 第三步：代码校验与写入
        try:
            graph = self.graph_processor.build_graph(function_call)
            self.graph_db.insert_graph(graph, source_doc_id=filename)
        except Exception as e:
            print(f"!!! 步骤 3: Pydantic 最终校验失败，LLM 输出格式仍有问题: {e}")
            print(f"原始图谱数据: {function_call.arguments}")

    def process_document(self, filename: str, full_text: str, chunks: List[str]):
        """
        文档级处理方法：先进行文档级实体识别，再逐chunk构建图谱。
        这是解决分块粒度与图谱提取粒度不一致问题的核心方法。
        """
        print(f"\n=== 开始处理文档 {filename} ===\n")
        
        # 步骤0：文档级实体识别
        doc_entities_mapping = self.entity_extractor.extract_document_entities(filename, full_text)
        if doc_entities_mapping:
            # 存储到实例变量中，供后续chunk处理使用
            self.document_entities[filename] = doc_entities_mapping
            print(f"    文档级实体映射已建立: {len(doc_entities_mapping)} 个实体")
        else:
            print(f"    警告: 文档级实体识别失败，将采用默认chunk级处理")
            self.document_entities[filename] = {}
        
        # 步骤1-3：逐chunk处理，使用文档级实体映射
        for i, chunk in enumerate(chunks):
            print(f"\n--- 处理第 {i+1}/{len(chunks)} 个chunk ---")
            self.process_single_chunk(filename, chunk, doc_entities_mapping)
        
        print(f"\n=== 文档 {filename} 处理完成 ===\n")
    
    def execute_post_processing(self):
        """执行后处理合并"""
        self.entity_merger.execute_post_processing()
    
    def delete_document(self, filename: str):
        """删除指定文档的图谱数据"""
        self.graph_db.delete_source_documents(filename)
        # 清理文档级实体映射
        if filename in self.document_entities:
            del self.document_entities[filename]
    
    def query_graph(self, question: str):
        """查询图谱"""
        context = self.query_engine.query_graph(question)
        if not context:
            return "抱歉，根据您的问题生成的Cypher查询在知识图谱中没有返回任何结果。请尝试换一种问法。"
        return context
    
    def get_graph_schema(self) -> dict:
        """获取图谱Schema信息"""
        return self.graph_db.get_graph_schema()