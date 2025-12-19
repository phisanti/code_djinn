"""Local project context detection with caching.

Detects project-specific context from the filesystem:
- Project type (python, node, rust, etc.)
- Virtual environment status
- Git repository information
- Key configuration files
- Makefile commands
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
import os
import subprocess
import time


@dataclass
class LocalProjectContext:
    """Detected project context from local filesystem."""
    project_type: Optional[str] = None       # "python", "node", "rust", etc.
    virtual_env: Optional[str] = None        # "active: codedjinn_dev" or "inactive: venv"
    git_branch: Optional[str] = None         # "master", "feature/auth", etc.
    git_status: Optional[str] = None         # "modified: 3 files, untracked: 1 file"
    key_files: List[str] = field(default_factory=list)  # ["Makefile", "docker-compose.yml", ...]
    makefile_commands: List[Dict[str, str]] = field(default_factory=list)  # [{"cmd": "install", "desc": "..."}]


class ProjectDetector:
    """Detects project context with 30-second cache TTL."""

    # Key files to detect (from requirements)
    KEY_FILES = [
        'DESCRIPTION',           # R package
        'Makefile',
        'makefile',
        'docker-compose.yml',
        'docker-compose.yaml',
        'Dockerfile',
        '.dockerignore',
        'requirements.txt',
        'pyproject.toml',
        'setup.py',
        'package.json',
        'Cargo.toml',
        'go.mod',
        'Gemfile',
        'pom.xml',
        'build.gradle',
        'environment.yml',
        'environment.yaml',
        'CMakeLists.txt',
        '.gitlab-ci.yml',
        '.github/workflows',
    ]

    def __init__(self, cache_ttl: int = 30):
        """
        Initialize detector.

        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[LocalProjectContext, float]] = {}

    def get_context(self, directory: str = ".") -> LocalProjectContext:
        """
        Main entry point: Get context with caching.

        Algorithm:
        1. Generate cache key (directory + git HEAD mtime)
        2. Check cache, return if valid (< cache_ttl seconds old)
        3. Otherwise, detect context by calling all _detect_* methods
        4. Store in cache with timestamp
        5. Return LocalProjectContext
        """
        cache_key = self._get_cache_key(directory)
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            cached_context, cached_time = self._cache[cache_key]
            if now - cached_time < self.cache_ttl:
                return cached_context

        # Detect all context
        context = LocalProjectContext(
            project_type=self._detect_project_type(directory),
            virtual_env=self._detect_virtual_env(),
            git_branch=self._detect_git_branch(directory),
            git_status=self._detect_git_status(directory),
            key_files=self._find_key_files(directory),
            makefile_commands=self._parse_makefile(directory)
        )

        # Store in cache
        self._cache[cache_key] = (context, now)

        return context

    def _get_cache_key(self, directory: str) -> str:
        """Generate unique cache key."""
        abs_path = os.path.abspath(directory)

        # Try to get git HEAD mtime for cache invalidation
        git_head = os.path.join(abs_path, '.git', 'HEAD')
        try:
            if os.path.exists(git_head):
                mtime = os.stat(git_head).st_mtime
                return f"{abs_path}:{mtime}"
        except (OSError, IOError):
            pass

        return abs_path

    def _detect_project_type(self, directory: str) -> Optional[str]:
        """
        Detect project type from marker files.

        Markers:
        - python: requirements.txt, setup.py, pyproject.toml, environment.yml
        - node: package.json
        - rust: Cargo.toml
        - go: go.mod
        - ruby: Gemfile
        - java: pom.xml, build.gradle
        - r: DESCRIPTION (R package marker)
        """
        markers = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'environment.yml', 'environment.yaml'],
            'node': ['package.json'],
            'rust': ['Cargo.toml'],
            'go': ['go.mod'],
            'ruby': ['Gemfile'],
            'java': ['pom.xml', 'build.gradle'],
            'r': ['DESCRIPTION'],  # R package
        }

        for project_type, files in markers.items():
            for marker_file in files:
                if os.path.exists(os.path.join(directory, marker_file)):
                    return project_type

        return None

    def _detect_virtual_env(self) -> Optional[str]:
        """
        Detect virtual environment.

        Returns formatted string: "active: name" or "inactive: name"

        Check order:
        1. CONDA_DEFAULT_ENV environment variable
        2. VIRTUAL_ENV environment variable
        3. Directory existence: venv/, .venv/, env/
        """
        # Check conda
        conda_env = os.environ.get('CONDA_DEFAULT_ENV')
        if conda_env:
            return f"active: {conda_env}"

        # Check virtualenv
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            venv_name = os.path.basename(venv_path)
            return f"active: {venv_name}"

        # Check for inactive venv directories
        for venv_dir in ['venv', '.venv', 'env']:
            if os.path.isdir(venv_dir):
                return f"inactive: {venv_dir}"

        return None

    def _detect_git_branch(self, directory: str) -> Optional[str]:
        """
        Detect current git branch.

        Command: git branch --show-current
        Timeout: 2 seconds
        """
        git_dir = os.path.join(directory, '.git')
        if not os.path.exists(git_dir):
            return None

        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                return branch if branch else None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass

        return None

    def _detect_git_status(self, directory: str) -> Optional[str]:
        """
        Detect git status as human-readable string.

        Command: git status --short
        Parse output to count:
        - Modified files (lines starting with ' M' or 'M ')
        - Untracked files (lines starting with '??')

        Return: "modified: N files, untracked: M files" or "clean"
        """
        git_dir = os.path.join(directory, '.git')
        if not os.path.exists(git_dir):
            return None

        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    return "clean"

                # Count file types
                lines = output.split('\n')
                modified = sum(1 for line in lines if line.startswith((' M', 'M ', 'MM', 'AM', ' T')))
                untracked = sum(1 for line in lines if line.startswith('??'))

                parts = []
                if modified > 0:
                    parts.append(f"modified: {modified} file{'s' if modified != 1 else ''}")
                if untracked > 0:
                    parts.append(f"untracked: {untracked} file{'s' if untracked != 1 else ''}")

                return ", ".join(parts) if parts else "clean"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass

        return None

    def _find_key_files(self, directory: str) -> List[str]:
        """Find key files from self.KEY_FILES list."""
        found = []
        for key_file in self.KEY_FILES:
            file_path = os.path.join(directory, key_file)
            if os.path.exists(file_path):
                found.append(key_file)
        return found

    def _parse_makefile(self, directory: str) -> List[Dict[str, str]]:
        """
        Parse ALL Makefile targets and descriptions.

        Supports:
        - Inline comments: target: deps  # description
        - Above-line comments:
          # description
          target: deps

        Returns: [{"cmd": "install", "desc": "Install dependencies"}, ...]

        Skip special targets: ., $, %
        """
        # Find Makefile (case-insensitive)
        makefile_path = None
        for name in ['Makefile', 'makefile']:
            path = os.path.join(directory, name)
            if os.path.exists(path):
                makefile_path = path
                break

        if not makefile_path:
            return []

        commands = []
        current_comment = None

        try:
            with open(makefile_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_stripped = line.strip()

                    # Track comments above targets
                    if line_stripped.startswith('#'):
                        comment_text = line_stripped[1:].strip()
                        if comment_text:  # Non-empty comment
                            current_comment = comment_text
                        continue

                    # Check if line is a target (contains ':' but not '\t')
                    if ':' in line and not line.startswith('\t') and not line.startswith(' '):
                        # Extract target name (before ':')
                        target_part = line.split(':')[0].strip()

                        # Skip special targets
                        if target_part.startswith(('.', '$', '%')):
                            current_comment = None
                            continue

                        # Check for inline comment
                        inline_comment = None
                        if '#' in line:
                            comment_part = line.split('#', 1)[1].strip()
                            if comment_part:
                                inline_comment = comment_part

                        # Prefer inline comment over above-line comment
                        description = inline_comment or current_comment or ""

                        commands.append({
                            "cmd": target_part,
                            "desc": description
                        })

                        # Reset comment tracker
                        current_comment = None
                    else:
                        # Non-target line, reset comment
                        if not line_stripped.startswith('#'):
                            current_comment = None

        except (OSError, IOError, UnicodeDecodeError):
            # Silent error handling as per spec
            return []

        return commands


# ============================================================================
# Singleton Pattern (Convenience)
# ============================================================================

# Global detector instance
_detector: Optional[ProjectDetector] = None


def get_project_detector(cache_ttl: int = 30) -> ProjectDetector:
    """
    Get or create singleton context detector.

    Pattern: Similar to client_cache.py's get_cached_client()

    Args:
        cache_ttl: Cache time-to-live in seconds (default: 30)

    Returns:
        Singleton ProjectDetector instance
    """
    global _detector
    if _detector is None:
        _detector = ProjectDetector(cache_ttl=cache_ttl)
    return _detector
