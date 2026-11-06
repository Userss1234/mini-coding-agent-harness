import anyio
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server


async def list_tools(_ctx, _params):
    return types.ListToolsResult(tools=[
        types.Tool(name="echo", input_schema={"type": "object", "properties": {
            "value": {"type": "string"}, "name": {"type": "string"}}, "required": ["value"]}),
        types.Tool(name="fail", input_schema={"type": "object"}),
        types.Tool(name="slow", input_schema={"type": "object"}),
    ])


async def call_tool(_ctx, params):
    if params.name == "slow":
        await anyio.sleep(15)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=(params.arguments or {}).get("value", "fixture failure"))],
        is_error=params.name == "fail",
    )


async def main():
    server = Server("external-fixture", on_list_tools=list_tools, on_call_tool=call_tool)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
