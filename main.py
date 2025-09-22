from rag_system.config import RAGConfig
from rag_system.rag_system import RAGSystem

if __name__ == "__main__":
    config = RAGConfig(
        embedding_model_name="gemini-embedding-001",
        llm_model_name="gemini-2.0-flash",
        verbose=True,
    )

    rag = RAGSystem(config)

    rag.add_corpus(filename="fictional_knowledge.md", language="English")
    rag.add_corpus(filename="内蒙古电力公司变电检修管理规定（试行） 第1分册 油浸式变压器（电抗器）检修细则-1.docx", language="Chinese")

    q = "What is the primary function of the Spice Melange?"
    print(rag.query(q, mode="fusion", compress=True))

    rag.remove_corpus("fictional_knowledge.md")

    q = "储油柜及油保护装置检修方案是什么"
    print(rag.query(q, mode='fusion', compress=True))

    q = "What is the primary function of the Spice Melange?"
    print(rag.query(q, mode="fusion", compress=True))