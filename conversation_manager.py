import os
import json
import time
from typing import List, Dict, Any

TOKEN_LIMIT = 100000
MESSAGE_LIMIT = 10


class ConversationManager:
    def __init__(self, history_file: str = "conversation_history.json"):
        self.history_file = history_file
        self.conversations: Dict[str, Dict] = {}
        self._load_history()
    
    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
            except Exception as e:
                print(f"加载对话历史失败: {e}")
                self.conversations = {}
    
    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) * 1.3
    
    def create_conversation(self, city: str = "") -> str:
        conv_id = f"conv_{int(time.time())}"
        self.conversations[conv_id] = {
            "id": conv_id,
            "city": city,
            "created_at": time.time(),
            "last_updated": time.time(),
            "message_count": 0,
            "total_tokens": 0,
            "messages": []
        }
        self._save_history()
        return conv_id
    
    def add_message(self, conv_id: str, role: str, content: str) -> Dict:
        if conv_id not in self.conversations:
            conv_id = self.create_conversation()
        
        message = {
            "id": f"msg_{int(time.time())}",
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "tokens": int(self.estimate_tokens(content))
        }
        
        self.conversations[conv_id]["messages"].append(message)
        self.conversations[conv_id]["message_count"] += 1
        self.conversations[conv_id]["total_tokens"] += message["tokens"]
        self.conversations[conv_id]["last_updated"] = time.time()
        
        self._save_history()
        return message
    
    def get_conversation(self, conv_id: str) -> Dict:
        return self.conversations.get(conv_id, {})
    
    def get_all_conversations(self) -> List[Dict]:
        return sorted(
            self.conversations.values(),
            key=lambda x: x["last_updated"],
            reverse=True
        )
    
    def delete_conversation(self, conv_id: str):
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            self._save_history()
    
    def check_message_limit(self, conv_id: str) -> Dict:
        conv = self.conversations.get(conv_id, {})
        count = conv.get('message_count', 0)
        total_tokens = conv.get('total_tokens', 0)
        limit = MESSAGE_LIMIT

        base = {
            'message_count': count,
            'total_tokens': total_tokens,
            'message_limit': limit,
            'remaining': max(0, limit - count),
        }

        if count >= limit:
            return {
                **base,
                'limit_reached': True,
                'warning': True,
                'message': (
                    f'⚠️ 本对话已达 {limit} 条消息上限，请点击左侧「新对话」继续聊天。'
                ),
            }

        if count + 2 > limit:
            return {
                **base,
                'limit_reached': True,
                'warning': True,
                'message': (
                    f'⚠️ 当前已有 {count}/{limit} 条消息，无法再完成本轮问答，请开启新对话。'
                ),
            }

        hint = ''
        if count >= limit - 2:
            hint = (
                f'💡 提示：每轮对话最多 {limit} 条消息，当前 {count}/{limit}，'
                f'本轮结束后将无法继续发送。'
            )
        elif count >= limit - 4:
            hint = f'💡 提示：每轮对话最多 {limit} 条消息，当前 {count}/{limit}。'

        return {
            **base,
            'limit_reached': False,
            'warning': bool(hint),
            'message': hint,
        }

    def can_add_exchange(self, conv_id: str) -> bool:
        return not self.check_message_limit(conv_id).get('limit_reached', False)

    def check_token_limit(self, conv_id: str) -> Dict:
        conv = self.conversations.get(conv_id, {})
        total_tokens = conv.get("total_tokens", 0)
        message_count = conv.get("message_count", 0)
        
        if total_tokens >= TOKEN_LIMIT:
            return {
                "warning": True,
                "message": f"⚠️ 警告：对话上下文已达 {total_tokens:,} tokens，建议压缩历史记录。",
                "total_tokens": total_tokens,
                "message_count": message_count,
                "limit": TOKEN_LIMIT,
                "ratio": total_tokens / TOKEN_LIMIT
            }
        elif total_tokens >= TOKEN_LIMIT * 0.8:
            return {
                "warning": True,
                "message": f"⚠️ 提示：对话上下文已达 {total_tokens:,} tokens（约80%），即将达到上限。",
                "total_tokens": total_tokens,
                "message_count": message_count,
                "limit": TOKEN_LIMIT,
                "ratio": total_tokens / TOKEN_LIMIT
            }
        
        return {
            "warning": False,
            "message": "正常",
            "total_tokens": total_tokens,
            "message_count": message_count,
            "limit": TOKEN_LIMIT,
            "ratio": total_tokens / TOKEN_LIMIT
        }
    
    def compress_conversation(self, conv_id: str, keep_recent: int = 10) -> Dict:
        conv = self.conversations.get(conv_id, {})
        messages = conv.get("messages", [])
        
        if len(messages) <= keep_recent:
            return {
                "success": False,
                "message": f"消息数量不足，当前只有 {len(messages)} 条消息"
            }
        
        original_count = len(messages)
        original_tokens = conv.get("total_tokens", 0)
        
        compressed_messages = messages[-keep_recent:]
        compressed_tokens = sum(msg["tokens"] for msg in compressed_messages)
        
        self.conversations[conv_id]["messages"] = compressed_messages
        self.conversations[conv_id]["total_tokens"] = compressed_tokens
        self.conversations[conv_id]["message_count"] = len(compressed_messages)
        
        self._save_history()
        
        return {
            "success": True,
            "message": f"已压缩历史记录，保留最近 {keep_recent} 条消息",
            "original_count": original_count,
            "compressed_count": len(compressed_messages),
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saved_tokens": original_tokens - compressed_tokens
        }
    
    def get_stats(self) -> Dict:
        total_conversations = len(self.conversations)
        total_messages = sum(conv["message_count"] for conv in self.conversations.values())
        total_tokens = sum(conv["total_tokens"] for conv in self.conversations.values())
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "token_limit": TOKEN_LIMIT,
            "message_limit": MESSAGE_LIMIT,
        }


conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    return conversation_manager


if __name__ == '__main__':
    manager = get_conversation_manager()
    
    print("=== 测试对话管理功能 ===")
    
    conv_id = manager.create_conversation("北京")
    print(f"创建对话: {conv_id}")
    
    manager.add_message(conv_id, "user", "今天天气怎么样？")
    manager.add_message(conv_id, "bot", "今天北京天气晴朗，温度25°C")
    manager.add_message(conv_id, "user", "适合穿什么衣服？")
    manager.add_message(conv_id, "bot", "建议穿短袖T恤和长裤")
    
    print(f"\n对话统计: {manager.get_conversation(conv_id)}")
    
    print(f"\n所有对话: {manager.get_all_conversations()}")
    
    print(f"\nToken检查: {manager.check_token_limit(conv_id)}")
    
    print(f"\n系统统计: {manager.get_stats()}")
    
    print("\n=== 测试完成 ===")