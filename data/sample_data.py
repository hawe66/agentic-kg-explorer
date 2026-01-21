"""Sample data for Agentic AI Knowledge Graph.

This module contains curated sample data about Agentic AI research:
- Key papers and articles
- Core concepts
- Relationships between them
"""

from datetime import datetime
from src.graph.schema import (
    Document, Concept, Author, Source, Relationship,
    RelationType, MidCategory, SubCategory, DocumentType
)


# ============================================================================
# Sources
# ============================================================================

SOURCES = [
    Source(id="src-arxiv", name="arXiv", source_type="preprint", url="https://arxiv.org"),
    Source(id="src-openai", name="OpenAI Blog", source_type="blog", url="https://openai.com/blog"),
    Source(id="src-anthropic", name="Anthropic", source_type="blog", url="https://anthropic.com"),
    Source(id="src-google", name="Google AI Blog", source_type="blog", url="https://ai.googleblog.com"),
    Source(id="src-langchain", name="LangChain Blog", source_type="blog", url="https://blog.langchain.dev"),
]


# ============================================================================
# Authors
# ============================================================================

AUTHORS = [
    Author(id="auth-shinn", name="Noah Shinn", affiliation="Princeton"),
    Author(id="auth-yao", name="Shunyu Yao", affiliation="Princeton"),
    Author(id="auth-madaan", name="Aman Madaan", affiliation="CMU"),
    Author(id="auth-khattab", name="Omar Khattab", affiliation="Stanford"),
    Author(id="auth-wei", name="Jason Wei", affiliation="Google"),
    Author(id="auth-wang", name="Xuezhi Wang", affiliation="Google"),
]


# ============================================================================
# Concepts
# ============================================================================

CONCEPTS = [
    # Architecture - Multi-Agent
    Concept(
        id="concept-multi-agent",
        name="Multi-Agent Systems",
        aliases=["MAS", "Multi-Agent Collaboration"],
        definition="Systems where multiple AI agents collaborate to solve complex tasks",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.MULTI_AGENT_SYSTEMS,
    ),
    Concept(
        id="concept-autogen",
        name="AutoGen",
        aliases=["Microsoft AutoGen"],
        definition="Microsoft's framework for building multi-agent conversational systems",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.MULTI_AGENT_SYSTEMS,
    ),
    Concept(
        id="concept-crewai",
        name="CrewAI",
        aliases=[],
        definition="Framework for orchestrating role-playing autonomous AI agents",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.MULTI_AGENT_SYSTEMS,
    ),
    
    # Architecture - Orchestration
    Concept(
        id="concept-langgraph",
        name="LangGraph",
        aliases=[],
        definition="Library for building stateful, multi-actor applications with LLMs as graphs",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.AGENT_ORCHESTRATION,
    ),
    Concept(
        id="concept-dspy",
        name="DSPy",
        aliases=["Declarative Self-improving Python"],
        definition="Framework for programming—not prompting—language models with automatic optimization",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.AGENT_ORCHESTRATION,
    ),
    
    # Architecture - Memory
    Concept(
        id="concept-agent-memory",
        name="Agent Memory",
        aliases=["LLM Memory", "Conversational Memory"],
        definition="Mechanisms for agents to store and retrieve information across interactions",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.MEMORY_AND_STATE,
    ),
    Concept(
        id="concept-episodic-memory",
        name="Episodic Memory",
        aliases=[],
        definition="Memory storing specific experiences and events for later retrieval",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.MEMORY_AND_STATE,
    ),
    
    # Architecture - Tool Use
    Concept(
        id="concept-tool-use",
        name="Tool Use",
        aliases=["Function Calling", "Tool Calling"],
        definition="Capability of LLMs to use external tools and APIs to accomplish tasks",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.TOOL_USE,
    ),
    Concept(
        id="concept-mcp",
        name="Model Context Protocol",
        aliases=["MCP"],
        definition="Anthropic's protocol for standardized tool and context integration with LLMs",
        category_mid=MidCategory.ARCHITECTURE,
        category_sub=SubCategory.TOOL_USE,
    ),
    
    # Reasoning - Planning
    Concept(
        id="concept-react",
        name="ReAct",
        aliases=["Reasoning and Acting"],
        definition="Prompting paradigm that interleaves reasoning traces and task-specific actions",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.PLANNING,
    ),
    Concept(
        id="concept-plan-solve",
        name="Plan-and-Solve",
        aliases=[],
        definition="Prompting strategy that first creates a plan then executes it step by step",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.PLANNING,
    ),
    
    # Reasoning - Self-Reflection
    Concept(
        id="concept-reflexion",
        name="Reflexion",
        aliases=[],
        definition="Framework for verbal reinforcement learning through linguistic self-reflection",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.SELF_REFLECTION,
    ),
    Concept(
        id="concept-self-refine",
        name="Self-Refine",
        aliases=[],
        definition="Iterative refinement approach where LLM provides feedback on its own output",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.SELF_REFLECTION,
    ),
    
    # Reasoning - CoT
    Concept(
        id="concept-cot",
        name="Chain-of-Thought",
        aliases=["CoT", "CoT Prompting"],
        definition="Prompting technique that elicits step-by-step reasoning in LLMs",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.COT_VARIANTS,
    ),
    Concept(
        id="concept-tot",
        name="Tree-of-Thoughts",
        aliases=["ToT"],
        definition="Extension of CoT that explores multiple reasoning paths as a tree",
        category_mid=MidCategory.REASONING,
        category_sub=SubCategory.COT_VARIANTS,
    ),
    
    # Grounding - RAG
    Concept(
        id="concept-rag",
        name="Retrieval-Augmented Generation",
        aliases=["RAG"],
        definition="Technique combining retrieval systems with generative models for grounded responses",
        category_mid=MidCategory.GROUNDING,
        category_sub=SubCategory.RAG,
    ),
    
    # Grounding - Knowledge Graphs
    Concept(
        id="concept-graphrag",
        name="GraphRAG",
        aliases=["Graph-based RAG"],
        definition="RAG approach using knowledge graphs for structured retrieval and reasoning",
        category_mid=MidCategory.GROUNDING,
        category_sub=SubCategory.KNOWLEDGE_GRAPHS,
    ),
    
    # Evaluation - Benchmarks
    Concept(
        id="concept-agentbench",
        name="AgentBench",
        aliases=[],
        definition="Benchmark for evaluating LLMs as agents across diverse environments",
        category_mid=MidCategory.EVALUATION,
        category_sub=SubCategory.BENCHMARKS,
    ),
    
    # Industry - Developer Tools
    Concept(
        id="concept-cursor",
        name="Cursor",
        aliases=[],
        definition="AI-powered code editor with integrated LLM assistance",
        category_mid=MidCategory.INDUSTRY,
        category_sub=SubCategory.DEVELOPER_TOOLS,
    ),
    Concept(
        id="concept-claude-code",
        name="Claude Code",
        aliases=[],
        definition="Anthropic's command-line tool for agentic coding with Claude",
        category_mid=MidCategory.INDUSTRY,
        category_sub=SubCategory.DEVELOPER_TOOLS,
    ),
]


# ============================================================================
# Documents
# ============================================================================

DOCUMENTS = [
    # Papers
    Document(
        id="doc-reflexion",
        title="Reflexion: Language Agents with Verbal Reinforcement Learning",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2303.11366",
        summary="Introduces Reflexion, a framework where agents verbally reflect on task feedback to improve decision-making without weight updates.",
        authors=["Noah Shinn", "Federico Cassano", "Ashwin Gopinath"],
        published_date=datetime(2023, 3, 20),
        tags=["self-reflection", "reinforcement-learning", "agents"],
    ),
    Document(
        id="doc-self-refine",
        title="Self-Refine: Iterative Refinement with Self-Feedback",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2303.17651",
        summary="Proposes Self-Refine where LLMs iteratively improve outputs through self-generated feedback without additional training.",
        authors=["Aman Madaan", "Niket Tandon", "et al."],
        published_date=datetime(2023, 3, 30),
        tags=["self-feedback", "iterative-refinement"],
    ),
    Document(
        id="doc-react",
        title="ReAct: Synergizing Reasoning and Acting in Language Models",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2210.03629",
        summary="Introduces ReAct paradigm that interleaves reasoning traces and actions for improved task performance.",
        authors=["Shunyu Yao", "Jeffrey Zhao", "et al."],
        published_date=datetime(2022, 10, 6),
        tags=["reasoning", "acting", "agents"],
    ),
    Document(
        id="doc-cot",
        title="Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2201.11903",
        summary="Demonstrates that prompting LLMs to generate intermediate reasoning steps improves performance on complex tasks.",
        authors=["Jason Wei", "Xuezhi Wang", "et al."],
        published_date=datetime(2022, 1, 28),
        tags=["prompting", "reasoning", "chain-of-thought"],
    ),
    Document(
        id="doc-dspy",
        title="DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2310.03714",
        summary="Introduces DSPy framework for programming LMs declaratively with automatic prompt optimization.",
        authors=["Omar Khattab", "Arnav Singhvi", "et al."],
        published_date=datetime(2023, 10, 5),
        tags=["prompt-optimization", "framework", "dspy"],
    ),
    Document(
        id="doc-promptwizard",
        title="PromptWizard: Task-Aware Prompt Optimization Framework",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2405.18369",
        summary="Microsoft's framework for feedback-driven prompt optimization with self-evolving mechanisms.",
        authors=["Eshaan Agarwal", "Joykirat Singh", "et al."],
        published_date=datetime(2024, 5, 28),
        tags=["prompt-optimization", "feedback", "microsoft"],
    ),
    Document(
        id="doc-apo",
        title="Automatic Prompt Optimization with Gradient Descent and Beam Search",
        doc_type=DocumentType.PAPER,
        source_url="https://arxiv.org/abs/2305.03495",
        summary="Proposes APO using natural language 'gradients' to iteratively improve prompts.",
        authors=["Reid Pryzant", "Dan Iter", "et al."],
        published_date=datetime(2023, 5, 4),
        tags=["prompt-optimization", "gradient-descent"],
    ),
    
    # Articles/Memos
    Document(
        id="doc-langgraph-intro",
        title="Introduction to LangGraph: Building Stateful AI Agents",
        doc_type=DocumentType.ARTICLE,
        source_url="https://blog.langchain.dev/langgraph",
        summary="Overview of LangGraph's approach to building multi-actor LLM applications with state management.",
        authors=["LangChain Team"],
        published_date=datetime(2024, 1, 15),
        tags=["langgraph", "agents", "tutorial"],
    ),
    Document(
        id="doc-mcp-intro",
        title="Introducing the Model Context Protocol",
        doc_type=DocumentType.ARTICLE,
        source_url="https://anthropic.com/news/model-context-protocol",
        summary="Anthropic's announcement of MCP for standardized tool and context integration.",
        authors=["Anthropic"],
        published_date=datetime(2024, 11, 25),
        tags=["mcp", "tools", "anthropic"],
    ),
]


# ============================================================================
# Relationships
# ============================================================================

RELATIONSHIPS = [
    # Document -> Concept (DISCUSSES)
    Relationship(source_id="doc-reflexion", target_id="concept-reflexion", rel_type=RelationType.INTRODUCES),
    Relationship(source_id="doc-reflexion", target_id="concept-episodic-memory", rel_type=RelationType.DISCUSSES),
    Relationship(source_id="doc-reflexion", target_id="concept-agent-memory", rel_type=RelationType.DISCUSSES),
    
    Relationship(source_id="doc-self-refine", target_id="concept-self-refine", rel_type=RelationType.INTRODUCES),
    
    Relationship(source_id="doc-react", target_id="concept-react", rel_type=RelationType.INTRODUCES),
    Relationship(source_id="doc-react", target_id="concept-tool-use", rel_type=RelationType.DISCUSSES),
    
    Relationship(source_id="doc-cot", target_id="concept-cot", rel_type=RelationType.INTRODUCES),
    
    Relationship(source_id="doc-dspy", target_id="concept-dspy", rel_type=RelationType.INTRODUCES),
    
    Relationship(source_id="doc-langgraph-intro", target_id="concept-langgraph", rel_type=RelationType.DISCUSSES),
    Relationship(source_id="doc-langgraph-intro", target_id="concept-agent-memory", rel_type=RelationType.DISCUSSES),
    
    Relationship(source_id="doc-mcp-intro", target_id="concept-mcp", rel_type=RelationType.INTRODUCES),
    Relationship(source_id="doc-mcp-intro", target_id="concept-tool-use", rel_type=RelationType.DISCUSSES),
    
    # Concept -> Concept relationships
    Relationship(source_id="concept-reflexion", target_id="concept-self-refine", rel_type=RelationType.RELATED_TO, 
                 properties={"relation_type": "similar_approach"}),
    Relationship(source_id="concept-reflexion", target_id="concept-episodic-memory", rel_type=RelationType.IMPLEMENTS),
    
    Relationship(source_id="concept-react", target_id="concept-cot", rel_type=RelationType.EXTENDS),
    Relationship(source_id="concept-react", target_id="concept-tool-use", rel_type=RelationType.IMPLEMENTS),
    
    Relationship(source_id="concept-tot", target_id="concept-cot", rel_type=RelationType.EXTENDS),
    
    Relationship(source_id="concept-langgraph", target_id="concept-agent-memory", rel_type=RelationType.IMPLEMENTS),
    Relationship(source_id="concept-langgraph", target_id="concept-react", rel_type=RelationType.IMPLEMENTS),
    
    Relationship(source_id="concept-dspy", target_id="concept-cot", rel_type=RelationType.IMPLEMENTS),
    
    Relationship(source_id="concept-autogen", target_id="concept-multi-agent", rel_type=RelationType.IMPLEMENTS),
    Relationship(source_id="concept-crewai", target_id="concept-multi-agent", rel_type=RelationType.IMPLEMENTS),
    Relationship(source_id="concept-autogen", target_id="concept-crewai", rel_type=RelationType.COMPETES_WITH),
    
    Relationship(source_id="concept-graphrag", target_id="concept-rag", rel_type=RelationType.EXTENDS),
    
    Relationship(source_id="concept-mcp", target_id="concept-tool-use", rel_type=RelationType.IMPLEMENTS),
    
    Relationship(source_id="concept-cursor", target_id="concept-tool-use", rel_type=RelationType.IMPLEMENTS),
    Relationship(source_id="concept-claude-code", target_id="concept-tool-use", rel_type=RelationType.IMPLEMENTS),
    Relationship(source_id="concept-cursor", target_id="concept-claude-code", rel_type=RelationType.COMPETES_WITH),
    
    # Document -> Source
    Relationship(source_id="doc-reflexion", target_id="src-arxiv", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-self-refine", target_id="src-arxiv", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-react", target_id="src-arxiv", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-cot", target_id="src-arxiv", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-dspy", target_id="src-arxiv", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-langgraph-intro", target_id="src-langchain", rel_type=RelationType.PUBLISHED_IN),
    Relationship(source_id="doc-mcp-intro", target_id="src-anthropic", rel_type=RelationType.PUBLISHED_IN),
    
    # Document -> Author
    Relationship(source_id="doc-reflexion", target_id="auth-shinn", rel_type=RelationType.AUTHORED_BY),
    Relationship(source_id="doc-react", target_id="auth-yao", rel_type=RelationType.AUTHORED_BY),
    Relationship(source_id="doc-self-refine", target_id="auth-madaan", rel_type=RelationType.AUTHORED_BY),
    Relationship(source_id="doc-dspy", target_id="auth-khattab", rel_type=RelationType.AUTHORED_BY),
    Relationship(source_id="doc-cot", target_id="auth-wei", rel_type=RelationType.AUTHORED_BY),
    
    # Document -> Document (citations)
    Relationship(source_id="doc-reflexion", target_id="doc-react", rel_type=RelationType.CITES),
    Relationship(source_id="doc-react", target_id="doc-cot", rel_type=RelationType.CITES),
    Relationship(source_id="doc-self-refine", target_id="doc-cot", rel_type=RelationType.CITES),
    Relationship(source_id="doc-dspy", target_id="doc-cot", rel_type=RelationType.CITES),
]


def get_all_sample_data() -> dict:
    """Get all sample data as a dictionary."""
    return {
        "sources": SOURCES,
        "authors": AUTHORS,
        "concepts": CONCEPTS,
        "documents": DOCUMENTS,
        "relationships": RELATIONSHIPS,
    }
