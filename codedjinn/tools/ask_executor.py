"""Safe file reading tool executor for ask mode."""

import os
from pathlib import Path
from typing import Optional


class AskToolExecutor:
    """Execute tools available in ask mode (read_file only).
    
    Ask mode supports read-only operations for gathering context
    during multi-step reasoning. This class ensures all file reads
    are safe and constrained.
    """
    
    # Maximum file size to read (50KB)
    MAX_FILE_SIZE = 50_000
    
    def __init__(self, cwd: Optional[str] = None):
        """Initialize the executor.
        
        Args:
            cwd: Current working directory. Defaults to os.getcwd()
        """
        self.cwd = cwd or os.getcwd()
    
    def execute_read_file(self, path: str) -> str:
        """Safely read file content.
        
        Args:
            path: Path to file (relative or absolute, supports ~/ for home)
            
        Returns:
            File content as string, or error message if read fails
            
        Examples:
            >>> executor = AskToolExecutor()
            >>> content = executor.execute_read_file('./pyproject.toml')
            >>> len(content) > 0
            True
        """
        # Validate path length (prevent DoS)
        if not path or len(path) > 500:
            return f"Error: Invalid path - path too long or empty"
        
        # Validate path safety first
        if not self.is_path_safe(path):
            return f"Error: Cannot read file - path is outside allowed directories: {path}"
        
        # Resolve the path
        try:
            full_path = self._resolve_path(path)
        except Exception as e:
            return f"Error: Invalid path - {path}: {str(e)}"
        
        # Check if file is readable
        try:
            readable_check = self.is_file_readable(full_path)
            if not readable_check.get('readable', False):
                return f"Error: {readable_check.get('reason', 'Cannot read file')}"
        except Exception as e:
            return f"Error: Cannot access file - {str(e)}"
        
        # Read the file
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            return f"Error: File is not text or has encoding issues - {path}"
        except Exception as e:
            return f"Error: Cannot read file - {str(e)}"
    
    def is_path_safe(self, path: str) -> bool:
        """Prevent path traversal attacks.
        
        Allows:
        - Relative paths within cwd (./file.py, ./src/main.py)
        - Home directory paths (~/.../file.txt)
        
        Denies:
        - Absolute paths outside cwd and home (/, /etc, /var)
        - Traversal attempts (../../etc/passwd)
        - System directories
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is safe to read, False otherwise
            
        Examples:
            >>> executor = AskToolExecutor('/Users/santiago/projects/code_djinn')
            >>> executor.is_path_safe('./codedjinn/main.py')
            True
            >>> executor.is_path_safe('../../etc/passwd')
            False
            >>> executor.is_path_safe('/etc/passwd')
            False
        """
        try:
            full_path = self._resolve_path(path)
        except Exception:
            return False
        
        allowed_roots = [
            Path(self.cwd).resolve(),
            Path.home().resolve(),
        ]
        
        # Check if path is under one of the allowed roots
        for root in allowed_roots:
            try:
                full_path.relative_to(root)
                return True
            except ValueError:
                continue
        
        return False
    
    def is_file_readable(self, path: str) -> dict:
        """Check if file is readable and safe to read.
        
        Args:
            path: Full path to file
            
        Returns:
            Dict with keys:
            - readable: bool - True if file can be read
            - reason: str - Explanation if not readable
            
        Examples:
            >>> executor = AskToolExecutor()
            >>> result = executor.is_file_readable('./pyproject.toml')
            >>> result['readable']
            True
        """
        path_obj = Path(path)
        
        # Check if file exists
        if not path_obj.exists():
            return {
                'readable': False,
                'reason': f"File not found - {path}"
            }
        
        # Check if it's a directory
        if path_obj.is_dir():
            return {
                'readable': False,
                'reason': f"Path is a directory, not a file - {path}"
            }
        
        # Check if file is readable (permissions)
        if not os.access(path, os.R_OK):
            return {
                'readable': False,
                'reason': f"Permission denied - {path}"
            }
        
        # Check file size
        try:
            file_size = path_obj.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return {
                    'readable': False,
                    'reason': f"File too large ({file_size} bytes, max {self.MAX_FILE_SIZE})"
                }
        except Exception as e:
            return {
                'readable': False,
                'reason': f"Cannot access file - {str(e)}"
            }
        
        return {
            'readable': True,
            'reason': None
        }
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path, handling ~/ and relative paths.
        
        Args:
            path: Path to resolve (relative, absolute, or ~/...)
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path cannot be resolved
        """
        # Expand home directory
        expanded = Path(path).expanduser()
        
        # If it's an absolute path, use it directly
        if expanded.is_absolute():
            return expanded.resolve()
        
        # Otherwise, treat as relative to cwd
        full_path = Path(self.cwd) / expanded
        return full_path.resolve()
