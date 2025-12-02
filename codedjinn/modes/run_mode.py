"""
Run Mode - Handles one-shot command generation and execution.
This is the core of the new architecture that fixes the over-zealous safety bug.
"""

import subprocess
import os
from typing import Tuple, Optional
from ..core.agent_service import AgentService
from ..core.policy_engine import PolicyEngine, PolicyDecision
from ..ui.output import UIManager
from ..ui.prompts import PromptManager


class RunMode:
    """Handles one-shot command generation and execution."""

    def __init__(
        self,
        agent_service: AgentService,
        policy_engine: PolicyEngine,
        ui: UIManager,
        prompt_manager: PromptManager,
        shell_path: str = "",
    ):
        """
        Initialize with injected dependencies.
        
        Args:
            agent_service: AgentService for command generation
            policy_engine: PolicyEngine for safety evaluation
            ui: UIManager for colored output
            prompt_manager: PromptManager for user interactions
            shell_path: Path to shell executable
        """
        self.agent_service = agent_service
        self.policy_engine = policy_engine
        self.ui = ui
        self.prompt_manager = prompt_manager
        self.shell_path = shell_path

    def execute_request(
        self,
        wish: str,
        explain: bool = False,
        verbose: bool = False,
        no_confirm: bool = False,
    ) -> bool:
        """
        Main entry point for run mode.

        Args:
            wish: User's natural language request
            explain: Include explanation of command
            verbose: Show detailed output
            no_confirm: Skip confirmation for ALLOW-level commands

        Returns:
            True if successful, False otherwise
        """
        try:
            if verbose:
                self.ui.info(f"🔍 Processing request: {wish}")
                self.ui.info(f"📋 Policy: {self.policy_engine.get_current_policy_name()}")

            # Generate command using Agno agent
            command, description = self.generate_command(wish, explain)

            if not command:
                self.ui.error("❌ No command was generated")
                return False

            # Display generated command
            self.ui.info("\n📝 Generated command:")
            self.ui.command(f"  {command}")

            if description and explain:
                self.ui.description(f"\n💡 Description:")
                self.ui.description(f"  {description}")

            # 🎯 THE KEY FIX: Assess safety with new policy system
            policy_decision = self.policy_engine.assess_command(command)

            if verbose:
                self.ui.info(f"\n🛡️  Safety assessment: {policy_decision.value}")

            # Execute with appropriate confirmation
            success = self.execute_with_confirmation(
                command, description, policy_decision, no_confirm
            )

            # Show result if verbose
            if verbose:
                self.display_result(success)

            return success

        except Exception as e:
            self.ui.error(f"❌ Error: {str(e)}")
            if verbose:
                import traceback
                self.ui.dim(traceback.format_exc())
            return False

    def generate_command(self, wish: str, explain: bool) -> Tuple[str, Optional[str]]:
        """
        Generate command using Agno agent.
        
        Args:
            wish: User's natural language request
            explain: Whether to include explanation
            
        Returns:
            Tuple of (command, description)
        """
        agent = self.agent_service.get_agent(mode="run")

        # Build prompt
        prompt = wish
        if explain:
            prompt += "\n\nInclude a brief explanation of what the command does."

        # Get agent response
        response = agent.run(prompt)

        # Parse response (simple parsing for now)
        output = response.content if hasattr(response, 'content') else str(response)

        # Extract command and description
        lines = output.strip().split('\n')
        command = lines[0].strip()
        description = '\n'.join(lines[1:]).strip() if len(lines) > 1 and explain else None

        return command, description

    def execute_with_confirmation(
        self,
        command: str,
        description: Optional[str],
        policy_decision: PolicyDecision,
        no_confirm: bool = False,
    ) -> bool:
        """
        Execute command with appropriate confirmation based on policy.

        This is where the OVER-ZEALOUS SAFETY BUG FIX is implemented!

        Args:
            command: Command to execute
            description: Optional command description
            policy_decision: Policy decision from PolicyEngine
            no_confirm: Skip confirmation for ALLOW-level commands

        Returns:
            True if execution successful, False otherwise
        """

        # DENY: Block execution completely
        if policy_decision == PolicyDecision.DENY:
            self.ui.error("\n⛔ BLOCKED: This command is prohibited by safety policy")
            self.ui.warning("Reason: Matches dangerous command pattern")
            return False

        # CONFIRM: Require explicit user confirmation
        if policy_decision == PolicyDecision.CONFIRM:
            self.ui.warning("\n⚠️  This command requires explicit confirmation")
            if not self.prompt_manager.confirm_execution(command, policy_decision):
                self.ui.warning("Command cancelled by user")
                return False

        # ALLOW: Execute with simple confirmation (unless no_confirm is True)
        # 🎯 THE BIG FIX: Commands like "ls | grep foo" now reach here as ALLOW
        # and get simple confirmation instead of requiring "YES"
        if policy_decision == PolicyDecision.ALLOW and not no_confirm:
            # Simple confirmation for allowed commands
            print(f"\nExecute command? (press Enter to confirm, 'n' to cancel): ", end="")
            try:
                response = input().strip().lower()
                if response in ["n", "no"]:
                    self.ui.warning("Command cancelled by user")
                    return False
            except (KeyboardInterrupt, EOFError):
                self.ui.warning("\nCommand cancelled by user")
                return False

        # Execute the command
        return self._execute_command(command)

    def _execute_command(self, command: str) -> bool:
        """
        Execute the command and display output.

        Args:
            command: Command to execute

        Returns:
            True if execution successful, False otherwise
        """
        self.ui.info("\n⚙️  Executing...\n")

        try:
            # Execute with shell support
            if self.shell_path:
                shell_cmd = [self.shell_path, "-c", command]
                result = subprocess.run(
                    shell_cmd,
                    timeout=30,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    timeout=30,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                )

            success = result.returncode == 0
            print()  # Empty line for spacing

            return success

        except subprocess.TimeoutExpired:
            self.ui.error("⏱️  Command timed out (30s limit)")
            return False
        except Exception as e:
            self.ui.error(f"❌ Execution error: {str(e)}")
            return False

    def display_result(self, success: bool):
        """
        Display execution result.

        Args:
            success: Whether execution was successful
        """
        if success:
            self.ui.success("✅ Command completed successfully")
        else:
            self.ui.error("❌ Command failed")
