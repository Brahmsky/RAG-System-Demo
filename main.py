from rag_system.config import RAGConfig
from rag_system.rag_system import RAGSystem

def pipeline_test(config: RAGConfig):
    rag = RAGSystem(config)

    rag.add_corpus(filename="fictional_knowledge.md", language="English")
    # rag.add_corpus(filename="内蒙古电力公司变电检修管理规定（试行） 第1分册 油浸式变压器（电抗器）检修细则-1.docx", language="Chinese")

    q = "What is the primary function of the Spice Melange?"
    print(rag.query(q, mode="fusion", compress=True, source_filter="fictional_knowledge.md"))

    rag.remove_corpus("fictional_knowledge.md")

    q = "储油柜及油保护装置检修方案是什么"
    print(rag.query(q, mode='fusion', compress=True))

    q = "What is the primary function of the Spice Melange?"
    print(rag.query(q, mode="fusion", compress=True))

if __name__ == "__main__":
    config = RAGConfig(
        embedding_model_name="gemini-embedding-001",
        llm_model_name="deepseek-chat",
        verbose=True,
    )

    rag = RAGSystem(config)

    # rag.remove_corpus('Alan Turing.md')
    # rag.add_corpus('Alan Turing.md')

    # print(rag.query("图灵在性格上有什么特点？") + '\n') # 默认是文本+图谱混合检索，文本检索是BM25+向量检索，无compress
    # print(rag.query("图灵的身体素质如何？") + '\n')
    # print(rag.query("图灵都提出过什么，研究过什么？") + '\n')
    # print(rag.query("图灵都有什么头衔啊，身份啊之类的东西？") + '\n')
    # print(rag.query("图灵在跑步上有很多佚事，说来讲讲") + '\n')

    rag.add_corpus("test_build_graph.md")
    print(rag.query("图灵被定成什么罪了？", mode="graph"))
    print(rag.query("图灵有什么研究领域？", mode="graph"))