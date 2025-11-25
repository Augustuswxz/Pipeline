from langchain.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Return x + y"""
    return a + b