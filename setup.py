#!/usr/bin/env python3
"""
q_agent 安装配置
"""

from setuptools import setup, find_packages

setup(
    name="q_agent",
    version="1.0.0",
    description="AI Agent Learning Framework",
    author="QZY",
    packages=find_packages(),
    install_requires=[
        "typing-extensions>=4.0.0",
        "openai>=1.0.0",
        "anthropic>=0.18.0",
        "websockets>=12.0",
        "sqlalchemy>=2.0.0",
        "pymysql>=1.1.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ]
    },
    python_requires=">=3.10",
)