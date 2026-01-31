// Migration 001: Add description field to Implementation nodes
// Required for vector search embedding (ChromaDB)
// Run: poetry run python scripts/run_migration.py neo4j/migrations/001_add_impl_descriptions.cypher

MATCH (i:Implementation {id: 'impl:langchain'})
SET i.description = 'LLM 애플리케이션 개발 프레임워크. 체인, 에이전트, RAG 파이프라인을 모듈 방식으로 조합하여 구축할 수 있으며, 다양한 LLM 프로바이더와 도구 통합을 지원한다.';

MATCH (i:Implementation {id: 'impl:langgraph'})
SET i.description = '상태 기반 그래프 워크플로 프레임워크. 에이전트 실행 흐름을 노드와 엣지로 정의하며, 조건 분기·루프·사람 승인 등 복잡한 제어 흐름을 지원한다.';

MATCH (i:Implementation {id: 'impl:llamaindex'})
SET i.description = 'LLM 데이터 프레임워크. 문서 인덱싱, 검색 증강 생성(RAG), 구조화된 데이터 쿼리를 위한 커넥터와 인덱스를 제공하며, 다양한 데이터 소스 통합을 지원한다.';

MATCH (i:Implementation {id: 'impl:autogen'})
SET i.description = '멀티 에이전트 대화 프레임워크. 여러 AI 에이전트가 대화를 통해 협력하여 복잡한 작업을 수행하며, 사람-에이전트 간 상호작용과 코드 실행을 지원한다.';

MATCH (i:Implementation {id: 'impl:crewai'})
SET i.description = '역할 기반 멀티 에이전트 오케스트레이션 프레임워크. 각 에이전트에 역할·목표·배경 스토리를 부여하고, 순차적 또는 계층적 프로세스로 작업을 위임·실행한다.';

MATCH (i:Implementation {id: 'impl:openai-agents-sdk'})
SET i.description = 'OpenAI의 에이전트 SDK. 도구 사용, 에이전트 간 핸드오프, 가드레일을 기본 지원하며, OpenAI 모델과 최적화된 통합을 제공한다.';

MATCH (i:Implementation {id: 'impl:semantic-kernel'})
SET i.description = 'Microsoft의 AI 오케스트레이션 SDK. 플러그인 기반으로 LLM 기능을 기존 애플리케이션에 통합하며, 플래너·메모리·함수 호출 등 엔터프라이즈 수준의 AI 기능을 제공한다.';

MATCH (i:Implementation {id: 'impl:mem0'})
SET i.description = 'AI 에이전트용 장기 메모리 라이브러리. 사용자별 개인화된 기억을 저장·검색·갱신하며, 대화 맥락을 세션 간 유지하는 메모리 레이어를 제공한다.';

MATCH (i:Implementation {id: 'impl:zep'})
SET i.description = 'AI 에이전트용 메모리 서비스. 대화 히스토리, 엔티티 추출, 시간 기반 지식 그래프를 관리하며, 장기 메모리와 사실 검색을 서비스 형태로 제공한다.';

MATCH (i:Implementation {id: 'impl:ms-graphrag'})
SET i.description = 'Microsoft의 그래프 기반 RAG 라이브러리. 텍스트에서 지식 그래프를 자동 구축하고, 커뮤니티 요약과 그래프 탐색을 통해 글로벌 질문에 대한 검색 증강 생성을 수행한다.';

MATCH (i:Implementation {id: 'impl:langsmith'})
SET i.description = 'LLM 애플리케이션 관찰·평가 플랫폼. 에이전트 실행 트레이싱, 프롬프트 성능 평가, 데이터셋 관리를 제공하며, LangChain/LangGraph와 긴밀하게 통합된다.';

MATCH (i:Implementation {id: 'impl:langfuse'})
SET i.description = '오픈소스 LLM 관찰·분석 플랫폼. 트레이스·스팬 기반 실행 추적, 비용·지연 분석, 프롬프트 버전 관리를 제공하며, OpenTelemetry 호환 데이터 수집을 지원한다.';

MATCH (i:Implementation {id: 'impl:nemo-guardrails'})
SET i.description = 'NVIDIA의 대화형 AI 가드레일 라이브러리. Colang 스크립트로 대화 흐름 제어, 입력 검증, 주제 이탈 방지, 사실 확인 등의 안전 정책을 선언적으로 정의한다.';

MATCH (i:Implementation {id: 'impl:guardrails-ai'})
SET i.description = 'LLM 출력 검증·교정 라이브러리. RAIL 스펙으로 구조화된 출력 스키마와 검증 규칙을 정의하고, 실패 시 자동 재시도·교정을 수행하여 안정적인 출력을 보장한다.';

MATCH (i:Implementation {id: 'impl:llm-guard'})
SET i.description = 'LLM 보안 라이브러리. 프롬프트 인젝션 탐지, 개인정보 익명화, 유해 콘텐츠 필터링 등 입력·출력 양방향 보안 스캐너를 제공하여 LLM 상호작용을 보호한다.';

MATCH (i:Implementation {id: 'impl:llamaguard'})
SET i.description = 'Meta의 안전성 분류 모델. LLM 입력·출력을 안전 카테고리에 따라 분류하며, 유해 콘텐츠 탐지를 위한 파인튜닝된 Llama 기반 가드레일 모델이다.';
