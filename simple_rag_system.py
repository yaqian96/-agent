import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TextChunk:
    content: str
    source: str


def _split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if not text:
        return []
    separators = ['\n\n', '\n', '。', '！', '？', '；', '，', ' ']
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            split_at = -1
            for sep in separators:
                pos = text.rfind(sep, start, end)
                if pos > start:
                    split_at = max(split_at, pos + len(sep))
            if split_at > start:
                end = split_at
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


class SimpleRAGSystem:
    def __init__(self, knowledge_base_path: str = 'knowledge_base'):
        self.knowledge_base_path = knowledge_base_path
        self.documents: List[TextChunk] = []
        self._load_knowledge_base()

    def _load_documents(self) -> List[TextChunk]:
        documents: List[TextChunk] = []
        if not os.path.isdir(self.knowledge_base_path):
            print(f'知识库目录不存在: {self.knowledge_base_path}')
            return documents

        for filename in sorted(os.listdir(self.knowledge_base_path)):
            if not filename.endswith('.md'):
                continue
            filepath = os.path.join(self.knowledge_base_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                for chunk in _split_text(content):
                    documents.append(TextChunk(content=chunk, source=filename))
                print(f'加载文档: {filename}')
            except OSError as e:
                print(f'加载文档 {filename} 失败: {e}')

        return documents

    def _load_knowledge_base(self):
        try:
            documents = self._load_documents()
            if not documents:
                print('没有加载到任何文档')
                return
            self.documents = documents
            print(f'知识库加载成功，共 {len(documents)} 个文本块')
        except Exception as e:
            print(f'知识库加载失败: {e}')
            raise

    def _calculate_similarity(self, query: str, text: str) -> float:
        query_lower = query.lower()
        text_lower = text.lower()
        score = 0.0
        keywords = [
            '高温', '天气', '穿', '衣服', '旅游', '景点', '美食',
            '健康', '防晒', '保暖', '雨', '雪', '风', '穿搭', '出行',
        ]
        for keyword in keywords:
            if keyword in query_lower and keyword in text_lower:
                score += 2.0
        for word in query_lower.split():
            if word and word in text_lower:
                score += 1.0
        return score

    def retrieve(self, query: str, weather_context: str = '', k: int = 3) -> List[Dict[str, Any]]:
        if not self.documents:
            return []
        try:
            enhanced_query = f'{query} {weather_context}'
            scored_docs = [
                (doc, self._calculate_similarity(enhanced_query, doc.content))
                for doc in self.documents
            ]
            scored_docs.sort(key=lambda item: item[1], reverse=True)
            results = []
            for doc, score in scored_docs[:k]:
                if score > 0:
                    results.append({
                        'content': doc.content,
                        'source': doc.source,
                        'score': score,
                    })
            return results
        except Exception as e:
            print(f'检索失败: {e}')
            return []

    def retrieve_with_scores(self, query: str, weather_context: str = '', k: int = 3) -> List[Dict[str, Any]]:
        return self.retrieve(query, weather_context=weather_context, k=k)

    def format_retrieved_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        if not retrieved_docs:
            return '未找到相关知识'
        parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            parts.append(
                f"【知识{i}】来源: {doc.get('source', 'unknown')}\n{doc.get('content', '')}"
            )
        return '\n\n'.join(parts)


_rag_system: SimpleRAGSystem | None = None


def get_rag_system(knowledge_base_path: str = 'knowledge_base') -> SimpleRAGSystem:
    global _rag_system
    if _rag_system is None:
        _rag_system = SimpleRAGSystem(knowledge_base_path)
    return _rag_system
