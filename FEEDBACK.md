- critic should recognize whether the retrieved data are insufficient to explain the query.
- human intents are too narrow.
- search planner is hard-coded. (Determine path direction based on entity type and intent type)
- 'INTENT_CLASSIFICATION_PROMPT', '_extract_entities' doesn't have info over graphdb's entities. Cannot exactly extract entities.
- i want embedding models to be abstract.
```python
from abc import ABC, abstractmethod

# 1. 인터페이스 정의
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass

# 2. OpenAI 구현체
class OpenAIProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str):
        # OpenAI 클라이언트 초기화
        ...
    def embed(self, texts: list[str]) -> list[list[float]]:
        # OpenAI API 호출 로직
        ...

# 3. 로컬 HuggingFace 구현체 (예시)
class LocalProvider(EmbeddingProvider):
    def __init__(self, model_name: str):
        # SentenceTransformers 등을 이용한 로컬 로드
        ...
    def embed(self, texts: list[str]) -> list[list[float]]:
        # 로컬 CPU/GPU 연산
        ...
```
- ABSOLUTELY NONSENSE. MUST CHANGE THING. 
    - `Base confidence on graph result count`: _calculate_confidence at src/agents/nodes/synthesizer.py