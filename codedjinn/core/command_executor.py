import subprocess
import shlex
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
    
    def __init__(self, shell: str = "bash"):
        """
        Initialize the command executor.
        
        Args:
            shell: The shell to use for command execution
        """
        self.shell = shell
    
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
            print_text("⚠️  WARNING: This command may be potentially dangerous!", "red")
        
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
    
    def _is_dangerous_command(self, command: str) -> bool:
        """
        Check if a command is potentially dangerous.
        
        Args:
            command: The command to check
            
        Returns:
            True if the command is potentially dangerous
        """
        command_lower = command.lower().strip()
        
        for dangerous_cmd in self.DANGEROUS_COMMANDS:
            if command_lower.startswith(dangerous_cmd.lower()) or f" {dangerous_cmd.lower()}" in command_lower:
                return True
        
        # Check for other dangerous patterns
        dangerous_patterns = [
            '>', '>>', '|', '&&', '||', ';', '$(', '`',
            'curl', 'wget', 'python -c', 'eval', 'exec'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return True
                
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
            # Execute command with output directly to user's terminal
            # This allows real-time output and proper terminal interaction
            result = subprocess.run(
                command,
                shell=True,
                timeout=30  # 30 second timeout
            )
            
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