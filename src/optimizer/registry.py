"""Prompt Registry for version control of agent prompts."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import get_settings
from src.graph.client import Neo4jClient

from .models import PromptVersion


class PromptRegistry:
    """Manage prompt versions and activation."""

    def __init__(self, prompts_dir: Path = None):
        self.prompts_dir = prompts_dir or Path(__file__).parents[2] / "config" / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def _get_client(self) -> Neo4jClient:
        """Get Neo4j client."""
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()
        return client

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of prompt content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse semver string to tuple."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return (1, 0, 0)

    def _increment_version(self, version: str, bump: str = "patch") -> str:
        """Increment version number."""
        major, minor, patch = self._parse_version(version)
        if bump == "major":
            return f"{major + 1}.0.0"
        elif bump == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"

    def get_current_version(self, agent_name: str) -> Optional[PromptVersion]:
        """Get currently active prompt version for an agent."""
        client = self._get_client()
        try:
            result = client.run_cypher("""
                MATCH (pv:PromptVersion {agent_name: $agent_name, is_active: true})
                RETURN pv
            """, {"agent_name": agent_name})

            if not result:
                return None

            pv = result[0]["pv"]
            return PromptVersion(
                id=pv["id"],
                agent_name=pv["agent_name"],
                version=pv["version"],
                prompt_content=pv.get("prompt_content", ""),
                prompt_hash=pv.get("prompt_hash", ""),
                prompt_path=pv.get("prompt_path", ""),
                is_active=pv.get("is_active", False),
                user_approved=pv.get("user_approved", False),
                parent_version=pv.get("parent_version"),
                failure_pattern_id=pv.get("failure_pattern_id"),
                performance_delta=pv.get("performance_delta", 0.0),
                rationale=pv.get("rationale", ""),
            )
        finally:
            client.close()

    def get_version_history(self, agent_name: str, limit: int = 10) -> list[PromptVersion]:
        """Get version history for an agent."""
        client = self._get_client()
        try:
            result = client.run_cypher("""
                MATCH (pv:PromptVersion {agent_name: $agent_name})
                RETURN pv
                ORDER BY pv.created_at DESC
                LIMIT $limit
            """, {"agent_name": agent_name, "limit": limit})

            versions = []
            for row in result:
                pv = row["pv"]
                versions.append(PromptVersion(
                    id=pv["id"],
                    agent_name=pv["agent_name"],
                    version=pv["version"],
                    prompt_content=pv.get("prompt_content", ""),
                    prompt_hash=pv.get("prompt_hash", ""),
                    prompt_path=pv.get("prompt_path", ""),
                    is_active=pv.get("is_active", False),
                    user_approved=pv.get("user_approved", False),
                    parent_version=pv.get("parent_version"),
                    performance_delta=pv.get("performance_delta", 0.0),
                    rationale=pv.get("rationale", ""),
                ))
            return versions
        finally:
            client.close()

    def create_version(
        self,
        agent_name: str,
        content: str,
        rationale: str,
        failure_pattern_id: str = None,
        test_results: dict = None,
        parent_version: str = None,
        performance_delta: float = 0.0,
    ) -> PromptVersion:
        """Create new prompt version (not yet active).

        Args:
            agent_name: Name of the agent.
            content: Full prompt content.
            rationale: Why this change was made.
            failure_pattern_id: Pattern this addresses.
            test_results: Test run summary.
            parent_version: Parent version ID.
            performance_delta: Improvement from parent.

        Returns:
            Created PromptVersion (not yet active).
        """
        # Get current version to calculate next version number
        current = self.get_current_version(agent_name)
        if current:
            new_version = self._increment_version(current.version)
            if not parent_version:
                parent_version = current.id
        else:
            new_version = "1.0.0"

        # Generate IDs and paths
        version_id = f"pv:{agent_name}@{new_version}"
        prompt_hash = self._hash_content(content)

        # Create directory for agent if needed
        agent_dir = self.prompts_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Save prompt to file
        prompt_path = agent_dir / f"v{new_version}.txt"
        prompt_path.write_text(content, encoding="utf-8")

        # Create PromptVersion object
        pv = PromptVersion(
            id=version_id,
            agent_name=agent_name,
            version=new_version,
            prompt_content=content,
            prompt_hash=prompt_hash,
            prompt_path=str(prompt_path.relative_to(self.prompts_dir.parent)),
            is_active=False,
            user_approved=False,
            parent_version=parent_version,
            failure_pattern_id=failure_pattern_id,
            performance_delta=performance_delta,
            test_results=test_results,
            rationale=rationale,
        )

        # Save to Neo4j
        client = self._get_client()
        try:
            client.run_cypher("""
                MERGE (pv:PromptVersion {id: $id})
                SET pv.agent_name = $agent_name,
                    pv.version = $version,
                    pv.prompt_content = $prompt_content,
                    pv.prompt_hash = $prompt_hash,
                    pv.prompt_path = $prompt_path,
                    pv.is_active = false,
                    pv.user_approved = false,
                    pv.parent_version = $parent_version,
                    pv.failure_pattern_id = $failure_pattern_id,
                    pv.performance_delta = $performance_delta,
                    pv.test_results = $test_results,
                    pv.rationale = $rationale,
                    pv.created_at = datetime()
            """, {
                "id": pv.id,
                "agent_name": pv.agent_name,
                "version": pv.version,
                "prompt_content": pv.prompt_content,
                "prompt_hash": pv.prompt_hash,
                "prompt_path": pv.prompt_path,
                "parent_version": pv.parent_version,
                "failure_pattern_id": pv.failure_pattern_id,
                "performance_delta": pv.performance_delta,
                "test_results": json.dumps(test_results) if test_results else None,
                "rationale": pv.rationale,
            })

            # Link to failure pattern if provided
            if failure_pattern_id:
                client.run_cypher("""
                    MATCH (pv:PromptVersion {id: $pv_id})
                    MATCH (fp:FailurePattern {id: $fp_id})
                    MERGE (pv)-[:ADDRESSES]->(fp)
                """, {"pv_id": pv.id, "fp_id": failure_pattern_id})

        finally:
            client.close()

        return pv

    def activate_version(self, version_id: str, approved_by: str = "system") -> bool:
        """Activate a prompt version (deactivate previous).

        Args:
            version_id: Version to activate.
            approved_by: User identifier.

        Returns:
            True if successful.
        """
        client = self._get_client()
        try:
            # Get the version to activate
            result = client.run_cypher("""
                MATCH (pv:PromptVersion {id: $id})
                RETURN pv.agent_name AS agent_name
            """, {"id": version_id})

            if not result:
                return False

            agent_name = result[0]["agent_name"]

            # Deactivate current active version
            client.run_cypher("""
                MATCH (pv:PromptVersion {agent_name: $agent_name, is_active: true})
                SET pv.is_active = false
            """, {"agent_name": agent_name})

            # Activate new version
            client.run_cypher("""
                MATCH (pv:PromptVersion {id: $id})
                SET pv.is_active = true,
                    pv.user_approved = true,
                    pv.approved_at = datetime(),
                    pv.approved_by = $approved_by
            """, {"id": version_id, "approved_by": approved_by})

            # Update current.txt symlink/file
            self._update_current_prompt(agent_name, version_id)

            return True
        finally:
            client.close()

    def _update_current_prompt(self, agent_name: str, version_id: str):
        """Update the current.txt file to point to active version."""
        client = self._get_client()
        try:
            result = client.run_cypher("""
                MATCH (pv:PromptVersion {id: $id})
                RETURN pv.prompt_content AS content
            """, {"id": version_id})

            if result:
                content = result[0]["content"]
                agent_dir = self.prompts_dir / agent_name
                agent_dir.mkdir(parents=True, exist_ok=True)
                current_path = agent_dir / "current.txt"
                current_path.write_text(content, encoding="utf-8")
        finally:
            client.close()

    def rollback(self, agent_name: str, to_version: str = None) -> bool:
        """Rollback to previous version.

        Args:
            agent_name: Agent to rollback.
            to_version: Specific version ID to rollback to. If None, rollback to parent.

        Returns:
            True if successful.
        """
        if to_version:
            return self.activate_version(to_version, approved_by="rollback")

        # Get current version's parent
        current = self.get_current_version(agent_name)
        if not current or not current.parent_version:
            return False

        return self.activate_version(current.parent_version, approved_by="rollback")

    def load_prompt(self, agent_name: str) -> Optional[str]:
        """Load the current active prompt for an agent.

        Args:
            agent_name: Agent name.

        Returns:
            Prompt content or None if not found.
        """
        # First try to load from current.txt
        current_path = self.prompts_dir / agent_name / "current.txt"
        if current_path.exists():
            return current_path.read_text(encoding="utf-8")

        # Fall back to Neo4j
        current = self.get_current_version(agent_name)
        if current:
            return current.prompt_content

        return None

    def initialize_from_code(self, agent_name: str, prompt_content: str) -> PromptVersion:
        """Initialize first version from hardcoded prompt.

        Use this to bootstrap the registry from existing prompts in code.

        Args:
            agent_name: Agent name.
            prompt_content: Current prompt from code.

        Returns:
            Created v1.0.0 PromptVersion (activated).
        """
        # Check if already initialized
        current = self.get_current_version(agent_name)
        if current:
            return current

        # Create initial version
        pv = self.create_version(
            agent_name=agent_name,
            content=prompt_content,
            rationale="Initial version extracted from code",
        )

        # Activate it
        self.activate_version(pv.id, approved_by="initialization")
        pv.is_active = True
        pv.user_approved = True

        return pv


# Singleton instance
_registry: Optional[PromptRegistry] = None


def get_registry() -> PromptRegistry:
    """Get or create singleton PromptRegistry."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
