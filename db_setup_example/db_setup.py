"""
Agentic AI Knowledge Graph - Database Setup

Neo4j 연결 및 초기화를 위한 유틸리티 모듈.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from neo4j import GraphDatabase, Driver
from loguru import logger
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


@dataclass
class Neo4jConfig:
    """Neo4j 연결 설정"""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")


class Neo4jConnection:
    """Neo4j 데이터베이스 연결 관리자"""
    
    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or Neo4jConfig()
        self._driver: Optional[Driver] = None
    
    def connect(self) -> Driver:
        """데이터베이스에 연결"""
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.config.uri}")
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password)
            )
            # 연결 테스트
            self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        return self._driver
    
    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self.connect()
        return self._driver


def run_cypher_file(connection: Neo4jConnection, filepath: Path) -> None:
    """
    Cypher 파일을 읽어서 실행
    
    Args:
        connection: Neo4j 연결
        filepath: Cypher 파일 경로
    """
    logger.info(f"Running Cypher file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 주석 제거하고 명령어 분리
    statements = []
    current_statement = []
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        # 주석 스킵
        if stripped.startswith('//') or not stripped:
            continue
        
        current_statement.append(line)
        
        # 세미콜론으로 끝나면 명령어 완성
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement.rstrip(';'))
            current_statement = []
    
    # 남은 명령어 처리
    if current_statement:
        statement = '\n'.join(current_statement).strip()
        if statement:
            statements.append(statement.rstrip(';'))
    
    # 명령어 실행
    with connection.driver.session(database=connection.config.database) as session:
        for i, statement in enumerate(statements, 1):
            try:
                session.run(statement)
                logger.debug(f"Executed statement {i}/{len(statements)}")
            except Exception as e:
                logger.warning(f"Statement {i} failed: {e}")
                logger.debug(f"Statement: {statement[:100]}...")
    
    logger.info(f"Completed running {len(statements)} statements from {filepath.name}")


def setup_schema(connection: Neo4jConnection, schema_file: Optional[Path] = None) -> None:
    """
    스키마 제약조건 및 인덱스 설정
    
    Args:
        connection: Neo4j 연결
        schema_file: 스키마 Cypher 파일 경로 (기본값: neo4j/schema.cypher)
    """
    if schema_file is None:
        schema_file = Path(__file__).parent.parent / "neo4j" / "schema.cypher"
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    logger.info("Setting up database schema...")
    run_cypher_file(connection, schema_file)
    logger.info("Schema setup complete")


def load_seed_data(connection: Neo4jConnection, seed_file: Optional[Path] = None) -> None:
    """
    Seed 데이터 로드
    
    Args:
        connection: Neo4j 연결
        seed_file: Seed 데이터 Cypher 파일 경로 (기본값: neo4j/seed_data.cypher)
    """
    if seed_file is None:
        seed_file = Path(__file__).parent.parent / "neo4j" / "seed_data.cypher"
    
    if not seed_file.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_file}")
    
    logger.info("Loading seed data...")
    run_cypher_file(connection, seed_file)
    logger.info("Seed data loaded")


def clear_database(connection: Neo4jConnection) -> None:
    """
    데이터베이스 초기화 (모든 노드/관계 삭제)
    
    ⚠️ 주의: 모든 데이터가 삭제됩니다!
    """
    logger.warning("Clearing all data from database!")
    
    with connection.driver.session(database=connection.config.database) as session:
        # 관계 먼저 삭제
        session.run("MATCH ()-[r]->() DELETE r")
        # 노드 삭제
        session.run("MATCH (n) DELETE n")
    
    logger.info("Database cleared")


def get_stats(connection: Neo4jConnection) -> dict:
    """
    데이터베이스 통계 조회
    
    Returns:
        노드/관계 수 통계
    """
    stats = {}
    
    with connection.driver.session(database=connection.config.database) as session:
        # 노드 수
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count")
        stats['nodes'] = {record['label']: record['count'] for record in result}
        
        # 관계 수
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
        stats['relationships'] = {record['type']: record['count'] for record in result}
        
        # 총계
        stats['total_nodes'] = sum(stats['nodes'].values())
        stats['total_relationships'] = sum(stats['relationships'].values())
    
    return stats


def initialize_database(
    connection: Neo4jConnection,
    clear_first: bool = False,
    schema_file: Optional[Path] = None,
    seed_file: Optional[Path] = None
) -> dict:
    """
    데이터베이스 전체 초기화
    
    Args:
        connection: Neo4j 연결
        clear_first: True면 기존 데이터 삭제 후 초기화
        schema_file: 스키마 파일 경로
        seed_file: Seed 데이터 파일 경로
    
    Returns:
        초기화 후 통계
    """
    logger.info("Starting database initialization...")
    
    if clear_first:
        clear_database(connection)
    
    setup_schema(connection, schema_file)
    load_seed_data(connection, seed_file)
    
    stats = get_stats(connection)
    logger.info(f"Initialization complete. Stats: {stats}")
    
    return stats


# CLI 실행
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic AI KG Database Setup")
    parser.add_argument("--clear", action="store_true", help="Clear database before setup")
    parser.add_argument("--schema-only", action="store_true", help="Only setup schema (no seed data)")
    parser.add_argument("--stats", action="store_true", help="Show database statistics only")
    args = parser.parse_args()
    
    config = Neo4jConfig()
    
    with Neo4jConnection(config) as conn:
        if args.stats:
            stats = get_stats(conn)
            print("\n=== Database Statistics ===")
            print(f"Total Nodes: {stats['total_nodes']}")
            print(f"Total Relationships: {stats['total_relationships']}")
            print("\nNodes by Label:")
            for label, count in sorted(stats['nodes'].items()):
                print(f"  {label}: {count}")
            print("\nRelationships by Type:")
            for rel_type, count in sorted(stats['relationships'].items()):
                print(f"  {rel_type}: {count}")
        elif args.schema_only:
            setup_schema(conn)
        else:
            stats = initialize_database(conn, clear_first=args.clear)
            print(f"\n✅ Database initialized successfully!")
            print(f"   Nodes: {stats['total_nodes']}")
            print(f"   Relationships: {stats['total_relationships']}")
