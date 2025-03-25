def get_command_prompt_template(os_fullname, shell, explain):
    """
    Generate a prompt template for CLI command generation.

    Args:
        os_fullname: The operating system name
        shell: The shell being used
        explain: Boolean indicating whether to include an explanation

    Returns:
        A string containing the prompt template with {wish} placeholder
    """

    # XML-structured prompt
    template = f"""You are a CLI command expert. Generate a command that accomplishes the user's request.

        <context>
        <operating_system>{os_fullname}</operating_system>
        <shell>{shell}</shell>
        <request>{{wish}}</request>
        <explain>{"yes" if explain else "no"}</explain>
        </context>

        <guidelines>
        - Provide a single, concise command that works on the specified OS and shell
        - Use common utilities and avoid complex scripts when possible
        - Prioritize safety (avoid destructive commands without warnings)
        - Use standard flags and options
        - Do not include explanatory text in the command itself
        </guidelines>

        <examples>
        <example>
            <request>Find all PDF files in the current directory and subdirectories</request>
            <response>
            <command>find . -name "*.pdf"</command>
            <description>Searches for PDF files in the current directory and all subdirectories.</description>
            </response>
        </example>
        <example>
            <request>Show disk usage in human-readable format</request>
            <response>
            <command>df -h</command>
            <description>Displays disk space usage with sizes in human-readable format (KB, MB, GB).</description>
            </response>
        </example>
        </examples>

        Respond with a command that fulfills the user's request. Format your response using XML tags as shown below:

        <response>
        <command>your command here</command>
        {("<description>brief explanation here</description>" if explain else "")}
        </response>
        """
    return template
