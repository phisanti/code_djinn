"""Ask-mode system prompt builder for analyzing previous output.

Ask mode is a lightweight analysis mode that answers a user question using
the most recent command and its output as context. It can read files for
additional context but does not execute any commands.
"""

from codedjinn.context.contextualiser import ContextualiserResult


def build_ask_prompt(ctx: ContextualiserResult) -> str:
    """
    Build system prompt for ask mode.

    This mode supports file reading (via read_file tool) to gather context,
    but does not execute commands. Focus is on answering questions about
    previous command output and code/files.

    Args:
        ctx: ContextualiserResult from contextualiser.contextualise()

    Returns:
        XML-structured system prompt for analysis

    Structure:
        1. <role> - Analysis assistant
        2. <system_context> - OS, shell, cwd
        3. <session_context> - Previous command (critical for ask mode)
        4. <instructions> - How to analyze

    Tools available:
        - read_file: Read file contents for additional context
        - Do NOT use execute_shell_command (not available in ask mode)

    Note: Ask mode typically doesn't need shell history or project context
          (but we could include them if useful in the future)
    """
    sections = []

    # 1. Role description
    sections.append(f"""<role>
You are Code Djinn - a {ctx.system_context.os_name} command-line assistant and code analyst.
Answer questions by analyzing provided context, reading files, and running safe observation commands.
You can read files using the read_file tool and run safe commands using execute_observe_command:
- File inspection: git, ls, grep, find, cat, head, tail
- Process observation: ps (with flags), top (batch mode)
- System info: df, du, free, vm_stat, uname
- Text processing: sed, awk, cut, sort, uniq
You do NOT execute destructive commands.
</role>""")

    # 2. Tool capabilities
    sections.append(ctx.capabilities_xml)

    # 3. System context
    sections.append(ctx.system_xml)

    # 4. File context (user-added files)
    if ctx.file_context and not ctx.file_context.is_empty():
        sections.append(ctx.file_xml)

    # 5. Session context (critical for ask mode)
    if ctx.session_context:
        sections.append(ctx.session_xml)
    else:
        # Explicit message if no context available
        sections.append("""<session_context>
  <note>No previous command context available.</note>
  <suggestion>Run a command first, then use ask mode to analyze its output.</suggestion>
</session_context>""")

    # 6. Instructions
    sections.append("""<instructions>
- Base your answer on the previous command output in session_context
- Use read_file tool to read relevant files when needed for better context
- Use execute_observe_command for safe inspection commands:
  * File inspection: git log, ls, grep, find, cat, head, tail
  * Process queries: ps aux, ps -m (macOS sort by memory), ps -eo, top -l 1 (macOS), top -b -n 1 (Linux)
  * Memory/system: free (Linux), vm_stat (macOS), df, du
- Each tool call should have clear reasoning in the 'context' parameter for accountability
- For process/memory queries, use OS-appropriate syntax:
  * macOS: 'ps aux -m | head -10' (sort by memory), 'top -l 1 | head -20'
  * Linux: 'ps aux --sort=-%mem | head -10', 'top -b -n 1 | head -20', 'free -h'
- If context is insufficient, say so explicitly
- Respond in plain text or markdown (terminal-friendly format)
- Be concise but thorough
- If asked about "the error" or "that file", reference session_context
- When files are in <file_context>, use them to provide informed analysis
- Do NOT attempt destructive commands - only safe observation and file reading allowed
</instructions>""")

    return "\n\n".join(sections)
