import os
import json
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document


class SimpleRAGSystem:
    def __init__(self, knowledge_base_path: str = "knowledge_base"):
        self.knowledge_base_path = knowledge_base_path
        self.documents = []
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        self._load_knowledge_base()
    
    def _load_documents(self) -> List[Document]:
        documents = []
        if not os.path.exists(self.knowledge_base_path):
            print(f"知识库目录不存在: {self.knowledge_base_path}")
            return documents
        
        for filename in os.listdir(self.knowledge_base_path):
            if filename.endswith('.md'):
                filepath = os.path.join(self.knowledge_base_path, filename)
                try:
                    loader = TextLoader(filepath, encoding='utf-8')
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata['source'] = filename
                    documents.extend(docs)
                    print(f"加载文档: {filename}")
                except Exception as e:
                    print(f"加载文档 {filename} 失败: {e}")
        
        return documents
    
    def _load_knowledge_base(self):
        try:
            documents = self._load_documents()
            if not documents:
                print("没有加载到任何文档")
                return
            
            print(f"总共加载 {len(documents)} 个文档")
            
            splits = self.text_splitter.split_documents(documents)
            print(f"分割成 {len(splits)} 个文本块")
            
            self.documents = splits
            print("知识库加载成功")
            
        except Exception as e:
            print(f"知识库加载失败: {e}")
            raise
    
    def _calculate_similarity(self, query: str, text: str) -> float:
        query_lower = query.lower()
        text_lower = text.lower()
        
        score = 0.0
        
        keywords = ["高温", "天气", "穿", "衣服", "旅游", "景点", "美食", "健康", "防晒", "保暖", "雨", "雪", "风"]
        
        for keyword in keywords:
            if keyword in query_lower and keyword in text_lower:
                score += 2.0
        
        for word in query_lower.split():
            if word in text_lower:
                score += 1.0
        
        return score
    
    def retrieve(self, query: str, weather_context: str = "", k: int = 3) -> List[Dict[str, Any]]:
        if not self.documents:
            return []
        
        try:
            enhanced_query = f"{query} {weather_context}"
            
            scored_docs = []
            for doc in self.documents:
                score = self._calculate_similarity(enhanced_query, doc.page_content)
                scored_docs.append((doc, score))
            
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for doc, score in scored_docs[:k]:
                if score > 0:
                    results.append({
                        'content': doc.page_content,
                        'source': doc.metadata.get('source', 'unknown'),
                        'score': score
                    })
            
            return results
        except Exception as e:
            print(f"检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def format_retrieved_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        if not retrieved_docs:
            return "未找到相关知识"
        
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc.get('source', 'unknown')
            content = doc.get('content', '')
            score = doc.get('score', 0.0)
            
            context_parts.append(f"【知识{i}】来源: {source}\n{content}")
        
        return "\n\n".join(context_parts)


rag_system = None


def get_rag_system(knowledge_base_path: str = "knowledge_base") -> SimpleRAGSystem:
    global rag_system
    if rag_system is None:
        rag_system = SimpleRAGSystem(knowledge_base_path)
    return rag_system


if __name__ == '__main__':
    print("初始化 RAG 系统...")
    rag = get_rag_system()
    
    print("\n测试检索功能...")
    query = "高温天气怎么穿衣服"
    results = rag.retrieve(query, k=3)
    
    print(f"\n查询: {query}")
    print(f"检索到 {len(results)} 条相关知识:\n")
    for i, result in enumerate(results, 1):
        print(f"--- 结果 {i} ---")
        print(f"来源: {result['source']}")
        print(f"相似度: {result['score']:.4f}")
        print(f"内容: {result['content'][:200]}...")
        print()