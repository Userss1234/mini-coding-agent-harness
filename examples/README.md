# Examples

This directory contains copyable integration examples for running the harness outside the local CLI.

## MCP Client Config

`mcp_config.example.json` shows a stdio MCP client configuration for the harness.

Replace `/absolute/path/to/mini-coding-agent-harness` with the absolute path to your local checkout before using it in a client.

The default server entry is read-focused. Use the `mini-coding-agent-harness-write` entry only when the client should be allowed to edit existing files through the harness permission system.
