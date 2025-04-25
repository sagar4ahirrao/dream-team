# pip install fastmcp
from mcp.server.fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    return a * b

@mcp.tool()
def data_provider() -> str:
    """A tool that provides some data."""
    # This is a placeholder for the actual data provider logic
    data = "This is some data."
    # read from a file
    with open("data/pred_maint/sensor.csv", "r") as file:
        data = file.read()
    
    return data

if __name__ == "__main__":
    mcp.run(transport="stdio")