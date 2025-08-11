from setuptools import setup, find_packages
from pathlib import Path

# Read README with proper encoding handling
readme_path = Path(__file__).parent / "README.md"
try:
    long_description = readme_path.read_text(encoding="utf-8")
except FileNotFoundError:
    long_description = (
        "High-performance CLI assistant for generating shell commands using LLM models"
    )

setup(
    name="code_djinn",
    version="0.2.3",
    description="High-performance CLI assistant for generating shell commands using LLM models",
    author="phisanti",
    author_email="tisalon@outlook.com",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "langchain-community>=0.3.20",
        "langchain-mistralai>=0.2.9",
        "langchain-google-genai>=2.1.1",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "code-djinn=codedjinn.main:code_djinn",
        ],
    },
    python_requires=">=3.10",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
