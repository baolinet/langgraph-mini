# auth/session.py - 用户会话管理模块
from typing import Optional, Protocol, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json
import hashlib


def create_session_token(user_id: str) -> str:
    """创建新的 session token"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"session_{user_id}_{timestamp}"

# LangChain 消息类型（延迟导入避免循环依赖）
Message = None


def _get_message_classes():
    """延迟导入 LangChain 消息类"""
    global Message
    if Message is None:
        from langchain_core.messages import HumanMessage, AIMessage
        Message = {"human": HumanMessage, "ai": AIMessage}
    return Message


@dataclass
class ConversationMessage:
    """会话消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ConversationMessage":
        return ConversationMessage(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: list[ConversationMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)  # 自定义上下文数据
    metadata: dict = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: dict = None) -> ConversationMessage:
        """添加消息"""
        msg = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg
    
    def get_messages(self, limit: Optional[int] = None) -> list[ConversationMessage]:
        """获取消息列表"""
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_message_count(self) -> int:
        """获取消息数量"""
        return len(self.messages)
    
    def clear(self) -> None:
        """清空会话"""
        self.messages.clear()
        self.updated_at = datetime.now()
    
    def to_langchain_messages(self) -> list:
        """转换为 LangChain 消息格式"""
        msg_classes = _get_message_classes()
        result = []
        for msg in self.messages:
            if msg.role == "user":
                result.append(msg_classes["human"](content=msg.content))
            elif msg.role == "assistant":
                result.append(msg_classes["ai"](content=msg.content))
        return result
    
    @staticmethod
    def from_langchain_messages(messages: list, session_id: str, user_id: str) -> "Session":
        """从 LangChain 消息创建会话"""
        session = Session(session_id=session_id, user_id=user_id)
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            content = msg.content if hasattr(msg, "content") else str(msg)
            session.add_message(role, content)
        return session


class SessionStore(Protocol):
    """会话存储接口"""
    
    def get(self, session_id: str) -> Optional[Session]: ...
    def save(self, session: Session) -> None: ...
    def delete(self, session_id: str) -> bool: ...
    def exists(self, session_id: str) -> bool: ...


class InMemorySessionStore:
    """内存会话存储（测试/演示用）"""
    
    def __init__(self, max_sessions: int = 1000, ttl_hours: int = 24):
        self._sessions: dict[str, Session] = {}
        self._max_sessions = max_sessions
        self._ttl = timedelta(hours=ttl_hours)
    
    def _is_expired(self, session: Session) -> bool:
        return datetime.now() - session.updated_at > self._ttl
    
    def _cleanup_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
        for sid in expired:
            del self._sessions[sid]
    
    def _evict_oldest(self) -> None:
        if len(self._sessions) >= self._max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s.updated_at)
            del self._sessions[oldest.session_id]
    
    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and not self._is_expired(session):
            return session
        return None
    
    def save(self, session: Session) -> None:
        self._evict_oldest()
        self._sessions[session.session_id] = session
    
    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions and not self._is_expired(self._sessions[session_id])


class RedisSessionStore:
    """Redis 会话存储（生产环境使用）"""
    
    def __init__(self, redis_client=None, prefix: str = "session:", ttl_seconds: int = 86400):
        self._redis = redis_client
        self._prefix = prefix
        self._ttl = ttl_seconds
    
    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"
    
    def get(self, session_id: str) -> Optional[Session]:
        if not self._redis:
            raise NotImplementedError("Redis client not configured")
        
        data = self._redis.get(self._key(session_id))
        if not data:
            return None
        
        session_dict = json.loads(data)
        session = Session(
            session_id=session_dict["session_id"],
            user_id=session_dict["user_id"],
            created_at=datetime.fromisoformat(session_dict["created_at"]),
            updated_at=datetime.fromisoformat(session_dict["updated_at"]),
            context=session_dict.get("context", {}),
            metadata=session_dict.get("metadata", {}),
        )
        session.messages = [
            ConversationMessage(**msg) for msg in session_dict.get("messages", [])
        ]
        return session
    
    def save(self, session: Session) -> None:
        if not self._redis:
            raise NotImplementedError("Redis client not configured")
        
        data = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": [m.to_dict() for m in session.messages],
            "context": session.context,
            "metadata": session.metadata,
        }
        self._redis.setex(
            self._key(session.session_id),
            self._ttl,
            json.dumps(data)
        )
    
    def delete(self, session_id: str) -> bool:
        if not self._redis:
            raise NotImplementedError("Redis client not configured")
        return bool(self._redis.delete(self._key(session_id)))
    
    def exists(self, session_id: str) -> bool:
        if not self._redis:
            raise NotImplementedError("Redis client not configured")
        return bool(self._redis.exists(self._key(session_id)))


class SessionManager:
    """会话管理器"""
    
    def __init__(self, store: SessionStore):
        self._store = store
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> Session:
        """创建新会话"""
        if session_id is None:
            session_id = self._generate_session_id(user_id)
        
        session = Session(session_id=session_id, user_id=user_id)
        self._store.save(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._store.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self._store.delete(session_id)
    
    def add_user_message(self, session_id: str, content: str, metadata: dict = None) -> Optional[ConversationMessage]:
        """添加用户消息"""
        session = self._store.get(session_id)
        if not session:
            return None
        msg = session.add_message("user", content, metadata)
        self._store.save(session)
        return msg
    
    def add_assistant_message(self, session_id: str, content: str, metadata: dict = None) -> Optional[ConversationMessage]:
        """添加助手消息"""
        session = self._store.get(session_id)
        if not session:
            return None
        msg = session.add_message("assistant", content, metadata)
        self._store.save(session)
        return msg
    
    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> list[ConversationMessage]:
        """获取会话历史"""
        session = self._store.get(session_id)
        if not session:
            return []
        return session.get_messages(limit)
    
    def clear_session(self, session_id: str) -> bool:
        """清空会话"""
        session = self._store.get(session_id)
        if not session:
            return False
        session.clear()
        self._store.save(session)
        return True
    
    def update_context(self, session_id: str, key: str, value: Any) -> bool:
        """更新会话上下文"""
        session = self._store.get(session_id)
        if not session:
            return False
        session.context[key] = value
        self._store.save(session)
        return True
    
    @staticmethod
    def _generate_session_id(user_id: str) -> str:
        """生成会话 ID"""
        raw = f"{user_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


class RagContextManager:
    """RAG 上下文管理器 - 用于会话历史压缩和向量化检索"""
    
    def __init__(self, session_manager: SessionManager, max_tokens: int = 4000):
        self._session_manager = session_manager
        self._max_tokens = max_tokens
    
    def get_context_for_rag(self, session_id: str) -> list[dict]:
        """
        获取用于 RAG 的上下文
        返回格式化的消息列表，可用于向量检索
        """
        messages = self._session_manager.get_conversation_history(session_id)
        
        context = []
        for msg in messages:
            context.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            })
        return context
    
    def summarize_old_messages(self, session_id: str) -> bool:
        """
        压缩旧消息（简化实现：保留最近 N 条）
        生产环境可接入 LLM 进行摘要
        """
        session = self._session_manager.get_session(session_id)
        if not session:
            return False
        
        # 保留最近 10 条消息
        keep_count = 10
        if session.get_message_count() <= keep_count:
            return True
        
        recent = session.messages[-keep_count:]
        session.messages = recent
        self._session_manager._store.save(session)
        return True
    
    def get_relevant_history(self, session_id: str, query: str, top_k: int = 3) -> list[str]:
        """
        获取相关历史消息（简化实现）
        生产环境可接入向量数据库进行语义检索
        """
        messages = self._session_manager.get_conversation_history(session_id)
        
        # 简化：关键词匹配
        relevant = []
        query_lower = query.lower()
        for msg in messages[-10:]:  # 只检索最近 10 条
            if any(keyword in msg.content.lower() for keyword in query_lower.split()):
                relevant.append(msg.content)
                if len(relevant) >= top_k:
                    break
        
        # 如果没有匹配的，返回最近的消息
        if not relevant:
            relevant = [m.content for m in messages[-top_k:]]
        
        return relevant


# 默认会话管理器实例
default_session_store = InMemorySessionStore()
default_session_manager = SessionManager(default_session_store)
default_rag_manager = RagContextManager(default_session_manager)


class SessionService:
    """会话服务 - 处理 FastAPI 会话相关逻辑"""
    
    def __init__(self, session_manager: SessionManager):
        self._manager = session_manager
    
    def get_or_create_session(self, session_token: Optional[str], user_id: str) -> tuple[str, Session]:
        """获取或创建会话"""
        if session_token:
            session = self._manager.get_session(session_token)
            if session:
                return session_token, session
        
        new_session = self._manager.create_session(user_id)
        return new_session.session_id, new_session
    
    def get_session_messages(self, session_token: str) -> list:
        """获取会话消息（LangChain 格式）"""
        session = self._manager.get_session(session_token)
        if session:
            return session.to_langchain_messages()
        return []
    
    def add_messages(self, session_token: str, user_messages: list, ai_message: str, user_id: str = "anonymous") -> None:
        """保存用户和 AI 消息（自动创建会话）"""
        session = self._manager.get_session(session_token)
        if not session:
            self._manager.create_session(user_id, session_token)
        
        for msg in user_messages:
            if hasattr(msg, "content"):
                self._manager.add_user_message(session_token, msg.content)
        if ai_message:
            self._manager.add_assistant_message(session_token, ai_message)
    
    def get_history_count(self, session_token: str) -> int:
        """获取历史消息数量"""
        history = self._manager.get_conversation_history(session_token)
        return len(history)
    
    def get_session_info(self, session_token: str) -> Optional[dict]:
        """获取会话信息"""
        session = self._manager.get_session(session_token)
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": session.get_message_count(),
        }
    
    def get_session_history_api(self, session_token: str) -> list:
        """获取会话历史（API 格式）"""
        history = self._manager.get_conversation_history(session_token)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in history
        ]


default_session_service = SessionService(default_session_manager)
