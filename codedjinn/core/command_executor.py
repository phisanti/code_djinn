import subprocess
import shutil
from typing import Optional, Tuple
from ..utils import print_text


class CommandExecutor:
    """
    Handles safe command execution with user confirmation and result capture.
    """
    
    DANGEROUS_COMMANDS = [
        'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs', 'dd',
        'shutdown', 'reboot', 'halt', 'poweroff', 'init',
        'kill', 'killall', 'pkill', 'chmod +x', 'sudo'
    ]
    
    def __init__(self, shell: str = "bash", shell_path: str = ""):
        """
        Initialize the command executor.
        
        Args:
            shell: The shell to use for command execution
            shell_path: The full path to the shell executable
        """
        self.shell = shell
        self.shell_path = shell_path
    
    def execute_with_confirmation(
        self, 
        command: str, 
        description: Optional[str] = None,
        auto_confirm: bool = False,
        verbose: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Execute a command after user confirmation.
        
        Args:
            command: The command to execute
            description: Optional description of what the command does
            auto_confirm: Skip confirmation (for testing)
            verbose: Whether to show success/status messages
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Simple confirmation prompt matching intended UX
        print(f"\nDo you want to run the command: {command}?")
        
        if description:
            print_text(f"Description: {description}", "pink")
        
        # Safety check for dangerous commands
        is_dangerous = self._is_dangerous_command(command)
        if is_dangerous:
            print_text("⚠️  WARNING: This command may be potentially dangerous!\n", "red")
        
        # Get user confirmation
        if not auto_confirm:
            if is_dangerous:
                response = input("Type 'YES' to confirm: ").strip()
                if response != "YES":
                    print_text("Command execution cancelled.", "yellow")
                    return False, "", "Execution cancelled by user"
            else:
                response = input().strip().lower()
                if response not in ['', 'y', 'yes']:
                    print_text("Command execution cancelled.", "yellow")
                    return False, "", "Execution cancelled by user"
        
        # Execute the command
        try:
            return self._execute_command(command, verbose, description is not None)
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            print_text(error_msg, "red")
            return False, "", error_msg
    
    SAFE_COMMANDS = [
        'ls', 'dir', 'pwd', 'cd', 'echo', 'cat', 'less', 'more', 'head', 'tail',
        'grep', 'find', 'locate', 'which', 'whereis', 'whoami', 'id', 'date', 'cal',
        'uptime', 'w', 'who', 'ps', 'top', 'htop', 'df', 'du', 'free', 'uname',
        'history', 'alias', 'type', 'file', 'stat', 'wc', 'sort', 'uniq', 'cut',
        'tr', 'awk', 'sed', 'diff', 'cmp', 'tree', 'exa', 'lsd', 'bat', 'fzf',
        'rg', 'ag', 'fd', 'jq', 'yq', 'git status', 'git log', 'git diff', 'git show',
        'npm list', 'pip list', 'cargo --version', 'python --version', 'node --version',
        'lolcat', 'cowsay', 'figlet', 'neofetch', 'screenfetch', 'fortune'
    ]
    
    def _is_dangerous_command(self, command: str) -> bool:
        """
        Check if a command is potentially dangerous.
        
        Args:
            command: The command to check
            
        Returns:
            True if the command is potentially dangerous
        """
        command_lower = command.lower().strip()
        
        # First check for explicitly dangerous commands
        for dangerous_cmd in self.DANGEROUS_COMMANDS:
            if command_lower.startswith(dangerous_cmd.lower()) or f" {dangerous_cmd.lower()}" in command_lower:
                return True
        
        # Check for other dangerous patterns
        dangerous_patterns = [
            '$(', '`', 'curl', 'wget', 'python -c', 'eval', 'exec'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return True
        
        # Check for file redirection (dangerous)
        if '>' in command_lower or '>>' in command_lower:
            return True
        
        # Check for command chaining (dangerous)
        if '&&' in command_lower or '||' in command_lower or ';' in command_lower:
            return True
        
        # Check for piping to shell interpreters (dangerous)
        pipe_to_shell_patterns = ['| sh', '|sh', '| bash', '|bash', '| zsh', '|zsh', '| fish', '|fish']
        for pattern in pipe_to_shell_patterns:
            if pattern in command_lower:
                return True
        
        # Check for pipe to potentially dangerous commands
        if '|' in command_lower:
            # Allow simple pipes to common safe commands
            safe_pipe_targets = [
                'grep', 'awk', 'sed', 'sort', 'uniq', 'head', 'tail', 'cat', 'less', 'more',
                'lolcat', 'cowsay', 'fzf', 'bat', 'exa', 'lsd', 'tree', 'jq', 'yq',
                'wc', 'tr', 'cut', 'column', 'tee', 'xargs', 'find', 'locate',
                'rg', 'ag', 'fd', 'ripgrep', 'the_silver_searcher'
            ]
            pipe_parts = command_lower.split('|')
            if len(pipe_parts) > 1:
                for part in pipe_parts[1:]:  # Check everything after the first pipe
                    part = part.strip()
                    if not any(part.startswith(safe_cmd) for safe_cmd in safe_pipe_targets):
                        return True
        
        # Finally, check if it's a known safe command (only if no dangerous patterns found)
        for safe_cmd in self.SAFE_COMMANDS:
            if command_lower.startswith(safe_cmd.lower()):
                return False
                
        return False
    
    
    def _execute_command(self, command: str, verbose: bool = False, has_description: bool = False) -> Tuple[bool, str, str]:
        """
        Execute the command and display output directly in user's shell.
        
        Args:
            command: The command to execute
            verbose: Whether to show verbose status messages
            has_description: Whether the command has a description
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        print_text("\nExecuting command...", "yellow")
        print()  # Empty line for better readability
        
        try:
            # Execute command with proper shell support for aliases
            result = self._run_with_shell_support(command)
            
            success = result.returncode == 0
            
            # Add a newline after command output for clean separation
            print()
            
            # Display status only if verbose or has description
            if verbose or has_description:
                if success:
                    print_text("✓ Command executed successfully", "green")
                else:
                    print_text(f"✗ Command failed (exit code: {result.returncode})", "red")
            
            # Return empty strings for stdout/stderr since we're not capturing
            return success, "", ""
            
        except subprocess.TimeoutExpired:
            error_msg = "Command execution timed out (30s limit)"
            print_text(error_msg, "red")
            return False, "", error_msg
        
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            print_text(error_msg, "red")
            return False, "", error_msg

    def _run_with_shell_support(self, command: str) -> subprocess.CompletedProcess:
        """
        Execute command with proper shell support including aliases.
        Uses the pre-configured shell path for optimal performance.
        
        Args:
            command: The command to execute
            
        Returns:
            CompletedProcess result
        """
        # Use stored shell path if available and shell is supported
        if self.shell_path and self.shell in ["fish", "zsh", "bash"]:
            return subprocess.run(
                [self.shell_path, "-i", "-c", command],
                timeout=30
            )
        
        # Fallback to dynamic detection if shell path not stored (backward compatibility)
        elif self.shell == "fish":
            fish_path = shutil.which("fish")
            if fish_path:
                return subprocess.run(
                    [fish_path, "-i", "-c", command],
                    timeout=30
                )
        elif self.shell == "zsh":
            zsh_path = shutil.which("zsh")
            if zsh_path:
                return subprocess.run(
                    [zsh_path, "-i", "-c", command],
                    timeout=30
                )
        elif self.shell == "bash":
            bash_path = shutil.which("bash")
            if bash_path:
                return subprocess.run(
                    [bash_path, "-i", "-c", command],
                    timeout=30
                )
        
        # Ultimate fallback to generic shell execution
        return subprocess.run(
            command,
            shell=True,
            timeout=30
        )