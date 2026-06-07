import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class MemoryRecord:
    embedding: List[float]
    metadata: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def fingerprint(self) -> str:
        payload = json.dumps({"e": self.embedding, "m": self.metadata}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

@dataclass
class Task:
    task_id: str
    prompt: str
    provider: ModelProvider
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    attempts: int = 0

class VectorMemoryStore:
    def __init__(self, dimension: int = 1536, max_capacity: int = 10000):
        self.dimension = dimension
        self.max_capacity = max_capacity
        self.store: Dict[str, MemoryRecord] = {}

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    def upsert(self, record: MemoryRecord) -> str:
        if len(self.store) >= self.max_capacity:
            oldest_key = min(self.store, key=lambda k: self.store[k].timestamp)
            del self.store[oldest_key]
        fp = record.fingerprint()
        self.store[fp] = record
        return fp

    def query(self, query_embedding: List[float], top_k: int = 5, threshold: float = 0.75) -> List[Dict[str, Any]]:
        results = []
        for record in self.store.values():
            score = self._cosine_similarity(query_embedding, record.embedding)
            if score >= threshold:
                results.append({"score": score, "metadata": record.metadata, "record": record})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

class Router:
    def __init__(self, fallback: ModelProvider = ModelProvider.LOCAL):
        self.routes: Dict[str, ModelProvider] = {}
        self.fallback = fallback

    def add_rule(self, keyword: str, provider: ModelProvider):
        self.routes[keyword.lower()] = provider

    def resolve(self, prompt: str) -> ModelProvider:
        prompt_lower = prompt.lower()
        for keyword, provider in self.routes.items():
            if keyword in prompt_lower:
                return provider
        return self.fallback

class AgentOrchestrator:
    def __init__(self, memory_dimension: int = 1536):
        self.memory = VectorMemoryStore(dimension=memory_dimension)
        self.router = Router()
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self.active_tasks: Dict[str, Task] = {}

    def configure_routing(self, keyword: str, provider: ModelProvider):
        self.router.add_rule(keyword, provider)

    def _mock_embedding(self, text: str) -> List[float]:
        hash_val = hashlib.sha256(text.encode()).hexdigest()
        return [float(int(hash_val[i:i+8], 16) % 100) / 100 for i in range(0, self.memory.dimension * 2, 2)][:self.memory.dimension]

    async def _execute_task(self, task: Task) -> Any:
        task.status = TaskStatus.RUNNING
        task.attempts += 1
        await asyncio.sleep(0.1)
        if task.provider == ModelProvider.OPENAI:
            task.result = {"choices": [{"text": f"OpenAI processed: {task.prompt}"}]}
        elif task.provider == ModelProvider.ANTHROPIC:
            task.result = {"completion": f"Anthropic processed: {task.prompt}"}
        else:
            task.result = {"output": f"Local model processed: {task.prompt}"}
        task.status = TaskStatus.COMPLETED
        return task.result

    async def _worker(self, worker_id: int):
        while True:
            task = await self.task_queue.get()
            if task.status == TaskStatus.FAILED and task.attempts >= 3:
                self.task_queue.task_done()
                continue
            try:
                memory_context = self.memory.query(self._mock_embedding(task.prompt))
                context_meta = [m["metadata"] for m in memory_context]
                task.prompt = f"{task.prompt} | Context: {context_meta}" if context_meta else task.prompt
                await self._execute_task(task)
            except Exception:
                task.status = TaskStatus.FAILED
                await self.task_queue.put(task)
            finally:
                self.task_queue.task_done()

    async def dispatch(self, prompt: str, task_id: Optional[str] = None) -> str:
        tid = task_id or hashlib.md5(prompt.encode() + str(time.time()).encode()).hexdigest()
        provider = self.router.resolve(prompt)
        task = Task(task_id=tid, prompt=prompt, provider=provider)
        self.active_tasks[tid] = task
        
        embedding = self._mock_embedding(prompt)
        self.memory.upsert(MemoryRecord(embedding=embedding, metadata={"prompt": prompt, "task_id": tid}))
        
        await self.task_queue.put(task)
        return tid

    async def start(self, concurrency: int = 3):
        workers = [asyncio.create_task(self._worker(i)) for i in range(concurrency)]
        await self.task_queue.join()
        for w in workers:
            w.cancel()

    def get_status(self, task_id: str) -> Dict[str, Any]:
        task = self.active_tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        return {"task_id": task.task_id, "status": task.status.value, "provider": task.provider.value, "attempts": task.attempts}

async def main():
    orchestrator = AgentOrchestrator(memory_dimension=64)
    orchestrator.configure_routing("code", ModelProvider.OPENAI)
    orchestrator.configure_routing("essay", ModelProvider.ANTHROPIC)
    
    dispatch_tasks = [
        asyncio.create_task(orchestrator.dispatch("Write a python script for web scraping")),
        asyncio.create_task(orchestrator.dispatch("Write an essay about quantum physics")),
        asyncio.create_task(orchestrator.dispatch("Tell me a joke"))
    ]
    
    task_ids = await asyncio.gather(*dispatch_tasks)
    
    worker_task = asyncio.create_task(orchestrator.start(concurrency=2))
    await asyncio.sleep(1)
    
    for tid in task_ids:
        status = orchestrator.get_status(tid)
        print(json.dumps(status, indent=2))

    await worker_task

if __name__ == "__main__":
    asyncio.run(main())