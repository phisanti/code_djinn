"""Ask-mode system prompt builder for analyzing previous output.

Ask mode is a lightweight analysis mode that answers a user question using
the most recent command and its output as context. It does not use tool
calling and does not execute anything.
"""

from codedjinn.context.contextualiser import ContextualiserResult


def build_ask_prompt(ctx: ContextualiserResult) -> str:
    """
    Build system prompt for ask mode.

    This mode does NOT use tool calling - pure text analysis.
    Focus is on answering questions about previous command output.

    Args:
        ctx: ContextualiserResult from contextualiser.contextualise()

    Returns:
        XML-structured system prompt for analysis

    Structure:
        1. <role> - Analysis assistant
        2. <system_context> - OS, shell, cwd
        3. <session_context> - Previous command (critical for ask mode)
        4. <instructions> - How to analyze

    Note: Ask mode typically doesn't need shell history or project context
          (but we could include them if useful in the future)
    """
    sections = []

    # 1. Role description
    sections.append(f"""<role>
You are Code Djinn - a {ctx.system_context.os_name} command-line assistant and code analyst.
Answer questions based on provided context. You do NOT execute commands.
</role>""")

    # 2. Tool capabilities
    sections.append(ctx.capabilities_xml)

    # 3. System context
    sections.append(ctx.system_xml)

    # 4. Session context (critical for ask mode)
    if ctx.session_context:
        sections.append(ctx.session_xml)
    else:
        # Explicit message if no context available
        sections.append("""<session_context>
  <note>No previous command context available.</note>
  <suggestion>Run a command first, then use ask mode to analyze its output.</suggestion>
</session_context>""")

    # 5. Instructions
    sections.append("""<instructions>
- Base your answer on the previous command output in session_context
- If context is insufficient, say so explicitly
- Respond in plain text or markdown (terminal-friendly format)
- Be concise but thorough
- If asked about "the error" or "that file", reference session_context
</instructions>""")

    return "\n\n".join(sections)
