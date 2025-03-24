from setuptools import setup, find_packages

setup(
    name="codedjinn",
    version="0.1.0",
    description="A CLI tool to solve simple code questions within the terminal using LLM models",
    author="phisanti",
    author_email="tisalon@outlook.com",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "langchain[llm]>=0.0.325",
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
