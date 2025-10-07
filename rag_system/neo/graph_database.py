"""
Neo4j图数据库操作类
遵循单一职责原则，专门负责数据库连接和基础CRUD操作
"""
from typing import List, Dict
from neo4j import GraphDatabase as Neo4jDriver
from .data_structure import KnowledgeGraph


class Neo4jDatabase:
    """Neo4j图数据库连接和基础操作管理器"""
    
    def __init__(self, uri: str, auth: tuple):
        self.driver = Neo4jDriver.driver(uri, auth=auth)
        print("[Neo4jDatabase] Driver initialized.")
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()
            self.driver = None  # 避免重复关闭
            print("Neo4j Driver closed.")
    
    def __del__(self):
        self.close()
    
    def get_existing_entities(self) -> List[str]:
        """获取数据库中所有现有实体ID"""
        if not self.driver:
            return []
        with self.driver.session() as session:
            entities = session.run("MATCH (n) RETURN n.id AS id, labels(n)[0] AS label")
            ids = [record['id'] for record in entities]
        return ids
    
    def get_graph_schema(self) -> dict:
        """获取图谱Schema信息"""
        with self.driver.session() as session:
            nodes_query = "CALL db.labels() YIELD label RETURN collect(label) AS labels"
            node_labels = session.run(nodes_query).single()['labels']

            edges_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS types"
            edge_labels = session.run(edges_query).single()['types']

        return {
            "node_labels": node_labels,
            "relationship_types": edge_labels
        }
    
    def insert_graph(self, graph: KnowledgeGraph, source_doc_id: str):
        """将知识图谱插入数据库"""
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                # 建点
                for node in graph.nodes:
                    cypher_query = f"""
                    MERGE (n:{node.label} {{id: $id}})
                    SET n += $props
                    SET n.sources = [s IN coalesce(n.sources, []) WHERE s <> $source_doc_id] + [$source_doc_id]
                    """
                    tx.run(cypher_query, id=node.id, props=node.properties, source_doc_id=source_doc_id)
                    print(f"Merged node: {node.label}(id='{node.id}')")
                
                # 建边
                for edge in graph.edges:
                    cypher_query = f"""
                    MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
                    MERGE (a) -[r:{edge.label}]-> (b)
                    SET r += $props
                    SET r.sources = [s IN coalesce(r.sources, []) WHERE s <> $source_doc_id] + [$source_doc_id]
                    """
                    tx.run(cypher_query, source_id=edge.source, target_id=edge.target,
                           props=edge.properties, source_doc_id=source_doc_id)
                    print(f"Merged edge: ({edge.source})-[{edge.label}]->({edge.target})")
        
        print("\nGraph ingestion complete!")
    
    def execute_cypher(self, cypher_query: str) -> List[Dict]:
        """执行Cypher查询并返回结果"""
        with self.driver.session() as session:
            result = session.run(cypher_query)
            return [record.data() for record in result]
    
    def delete_source_documents(self, source_doc_id: str):
        """删除指定来源文档的所有图谱数据"""
        print(f"Deleting source: '{source_doc_id}'...")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                # 移除所有节点的文档来源属性
                node_unlink_query = """
                MATCH (n) WHERE $source_doc_id IN n.sources
                SET n.sources = [s IN n.sources WHERE s <> $source_doc_id]
                RETURN count(n) AS nodes_unlinked
                """
                node_result = tx.run(node_unlink_query, source_doc_id=source_doc_id).single()
                print(f"  - Unlinked source from {node_result['nodes_unlinked']} nodes.")

                # 移除所有边的文档来源属性
                edge_unlink_query = """
                MATCH ()-[r]->() WHERE $source_doc_id IN r.sources
                SET r.sources = [s IN r.sources WHERE s <> $source_doc_id]
                RETURN count(r) AS edges_unlinked
                """
                edge_result = tx.run(edge_unlink_query, source_doc_id=source_doc_id).single()
                print(f"  - Unlinked source from {edge_result['edges_unlinked']} edges.")

                # 删除孤儿关系
                orphan_edge_query = """
                MATCH ()-[r]->() WHERE r.sources IS NULL OR r.sources = []
                DELETE r
                RETURN count(r) AS edges_deleted
                """
                edge_del_result = tx.run(orphan_edge_query).single()
                print(f"  - Deleted {edge_del_result['edges_deleted']} orphan edges.")

                # 删除孤儿节点
                orphan_node_query = """
                MATCH (n) WHERE n.sources IS NULL OR n.sources = []
                DETACH DELETE n
                RETURN count(n) AS nodes_deleted
                """
                node_del_result = tx.run(orphan_node_query).single()
                print(f"  - Deleted {node_del_result['nodes_deleted']} orphan nodes.")

        print(f"\nDeletion process for '{source_doc_id}' complete!")
    
    def merge_entities(self, merge_mapping: dict):
        """根据映射关系合并重复实体"""
        if not merge_mapping:
            print("--> 数据库合并: 没有需要合并的实体。")
            return

        print("--> 数据库合并: 开始执行节点合并操作...")
        with self.driver.session() as session:
            for duplicate_id, primary_id in merge_mapping.items():
                if duplicate_id == primary_id:
                    continue

                print(f"    - 正在合并 '{duplicate_id}' -> '{primary_id}'...")
                query = """
                MATCH (primary {id: $primary_id}), (duplicate {id: $duplicate_id})
                CALL apoc.refactor.mergeNodes([primary, duplicate], {
                    properties: 'combine', 
                    mergeRels: true
                })
                YIELD node
                RETURN count(node) as merged_count
                """
                try:
                    result = session.run(query, primary_id=primary_id, duplicate_id=duplicate_id)
                    summary = result.consume()
                    if summary.counters.nodes_deleted > 0:
                        print(f"      成功合并并删除了节点 '{duplicate_id}'。")
                    else:
                        print(f"      警告: 未找到或未能合并节点 '{duplicate_id}'。")
                except Exception as e:
                    print(f"      错误: 合并 '{duplicate_id}' 时发生错误: {e}")

        print("--> 数据库合并: 节点合并操作完成。")