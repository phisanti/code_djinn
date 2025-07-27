from setuptools import setup, find_packages

setup(
    name="codedjinn",
    version="0.2.0",
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
            "code_djinn=codedjinn.main:code_djinn",
        ],
    },
    python_requires=">=3.10",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
