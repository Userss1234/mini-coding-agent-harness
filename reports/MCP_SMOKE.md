# MCP Smoke Report

- Trace: `trace.jsonl`
- Capabilities: prompts, resources, tools
- Tool count: 24
- Resource count: 10
- Resource template count: 1
- Prompt count: 3
- Permission policy call isError: `False`

## Tools

- `cache_stats`
- `compact_context`
- `context_pack`
- `delete_file`
- `edit_file`
- `git_diff`
- `grep`
- `index_workspace`
- `list_memories`
- `list_python_files`
- `permission_policy`
- `rag_explain`
- `rag_search`
- `read_file`
- `read_memory`
- `recover_errors`
- `retrieve_then_read`
- `retry_plan`
- `run_py_compile`
- `run_tests`
- `save_memory`
- `shell`
- `todo_write`
- `write_file`

## Resources

- `harness://docs/mcp`
- `harness://docs/readme`
- `harness://docs/readme-zh`
- `harness://rag/index-summary`
- `harness://reports/agent-compare`
- `harness://reports/agent-eval`
- `harness://reports/demo-python-bugfix`
- `harness://reports/eval`
- `harness://reports/eval-history`
- `harness://reports/failure-modes`

## Resource Templates

- `workspace-file`

## Prompts

- `code-maintenance-task`
- `eval-analysis`
- `repo-rag-maintenance`

## Transcript

```json
[
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "initialize",
      "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {
          "name": "mcp-smoke",
          "version": "0.1.0"
        }
      }
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "protocolVersion": "2025-11-25",
        "capabilities": {
          "tools": {
            "listChanged": false
          },
          "resources": {
            "subscribe": false,
            "listChanged": false
          },
          "prompts": {
            "listChanged": false
          }
        },
        "serverInfo": {
          "name": "mini-coding-agent-harness",
          "title": "Mini Coding Agent Harness",
          "version": "0.1.0"
        },
        "instructions": "Use tools to inspect and maintain a local repository. Writes are governed by the harness permission policy."
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "method": "notifications/initialized"
    },
    "response": null
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/list"
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "tools": [
          {
            "name": "cache_stats",
            "description": "Report read_file cache hits, misses, hit rate, and invalidations.",
            "inputSchema": {
              "type": "object",
              "properties": {}
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "compact_context",
            "description": "Summarize trace.jsonl into current goal, files read, files changed, failures, and next step.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "max_items": {
                  "type": "integer"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "context_pack",
            "description": "Retrieve the most relevant workspace file snippets for a task query using local chunked lexical retrieval.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "query": {
                  "type": "string"
                },
                "glob": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                },
                "max_chars_per_file": {
                  "type": "integer"
                },
                "window": {
                  "type": "integer"
                }
              },
              "required": [
                "query"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "delete_file",
            "description": "Delete one workspace file only when confirm is true. Directories are refused.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "confirm": {
                  "type": "boolean"
                }
              },
              "required": [
                "path",
                "confirm"
              ]
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": true,
              "idempotentHint": false,
              "openWorldHint": false
            }
          },
          {
            "name": "edit_file",
            "description": "Replace one exact text block inside a UTF-8 file. old_text must appear exactly once.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "old_text": {
                  "type": "string"
                },
                "new_text": {
                  "type": "string"
                }
              },
              "required": [
                "path",
                "old_text",
                "new_text"
              ]
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": true,
              "idempotentHint": false,
              "openWorldHint": false
            }
          },
          {
            "name": "git_diff",
            "description": "Show repository changes with git diff -- . when the workspace is a Git worktree.",
            "inputSchema": {
              "type": "object",
              "properties": {}
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "grep",
            "description": "Search files by substring.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "pattern": {
                  "type": "string"
                },
                "glob": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                }
              },
              "required": [
                "pattern"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "index_workspace",
            "description": "Build a safe local retrieval index summary for workspace text chunks.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "glob": {
                  "type": "string"
                },
                "chunk_lines": {
                  "type": "integer"
                },
                "overlap": {
                  "type": "integer"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "list_memories",
            "description": "List reusable workflow memories saved under skills/*.md, optionally ranked by a query.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "query": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "list_python_files",
            "description": "List Python files under the workspace, excluding virtualenv/cache directories by default.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "include_venv": {
                  "type": "boolean"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "permission_policy",
            "description": "Explain the current workspace, write, shell, and Git permission boundaries.",
            "inputSchema": {
              "type": "object",
              "properties": {}
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "rag_explain",
            "description": "Turn local RAG matches into a concrete read_file plan with path and line-range arguments.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "query": {
                  "type": "string"
                },
                "glob": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                },
                "chunk_lines": {
                  "type": "integer"
                },
                "overlap": {
                  "type": "integer"
                },
                "read_window": {
                  "type": "integer"
                },
                "max_chars_per_chunk": {
                  "type": "integer"
                }
              },
              "required": [
                "query"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "rag_search",
            "description": "Search workspace code and docs using local chunked lexical retrieval with path and line metadata.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "query": {
                  "type": "string"
                },
                "glob": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                },
                "chunk_lines": {
                  "type": "integer"
                },
                "overlap": {
                  "type": "integer"
                },
                "max_chars_per_chunk": {
                  "type": "integer"
                }
              },
              "required": [
                "query"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the workspace. Supports optional start_line/end_line, line limit, and max_chars.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                },
                "max_chars": {
                  "type": "integer"
                },
                "start_line": {
                  "type": "integer"
                },
                "end_line": {
                  "type": "integer"
                }
              },
              "required": [
                "path"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "read_memory",
            "description": "Read a reusable workflow memory from skills/<slug>.md.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "memory_name": {
                  "type": "string"
                },
                "max_chars": {
                  "type": "integer"
                }
              },
              "required": [
                "memory_name"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "recover_errors",
            "description": "Analyze failed tool calls in trace.jsonl and suggest concrete recovery steps.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "max_items": {
                  "type": "integer"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "retrieve_then_read",
            "description": "Run local RAG, build a read_file plan, and return the retrieved line-range evidence pack.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "query": {
                  "type": "string"
                },
                "glob": {
                  "type": "string"
                },
                "limit": {
                  "type": "integer"
                },
                "chunk_lines": {
                  "type": "integer"
                },
                "overlap": {
                  "type": "integer"
                },
                "read_window": {
                  "type": "integer"
                },
                "max_chars_per_read": {
                  "type": "integer"
                },
                "max_chars_per_chunk": {
                  "type": "integer"
                }
              },
              "required": [
                "query"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "retry_plan",
            "description": "Turn failed trace events into an ordered next-step retry plan with suggested tools.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "max_items": {
                  "type": "integer"
                }
              }
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "run_py_compile",
            "description": "Compile all Python files to check syntax.",
            "inputSchema": {
              "type": "object",
              "properties": {}
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "run_tests",
            "description": "Run the pytest test suite with python -m pytest. By default, use tests/ when it contains pytest files, otherwise run pytest from the workspace root.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "timeout": {
                  "type": "integer"
                },
                "target": {
                  "type": "string"
                }
              }
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": false,
              "idempotentHint": false,
              "openWorldHint": true
            }
          },
          {
            "name": "save_memory",
            "description": "Save a reusable successful workflow into skills/<slug>.md.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string"
                },
                "memory_name": {
                  "type": "string"
                },
                "summary": {
                  "type": "string"
                },
                "trigger": {
                  "type": "string"
                },
                "steps": {
                  "oneOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    }
                  ]
                }
              },
              "required": [
                "memory_name",
                "summary"
              ]
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": true,
              "idempotentHint": false,
              "openWorldHint": false
            }
          },
          {
            "name": "shell",
            "description": "Run a simple allowlisted shell command in the workspace. Shell operators, force flags, and mutating Git commands are blocked.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "command": {
                  "type": "string"
                },
                "timeout": {
                  "type": "integer"
                }
              },
              "required": [
                "command"
              ]
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": false,
              "idempotentHint": false,
              "openWorldHint": true
            }
          },
          {
            "name": "todo_write",
            "description": "Create or replace the current task todo list. Use this before multi-step repository work.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "todos": {
                  "oneOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "task": {
                            "type": "string"
                          },
                          "status": {
                            "type": "string",
                            "enum": [
                              "pending",
                              "in_progress",
                              "completed"
                            ]
                          }
                        },
                        "required": [
                          "task"
                        ]
                      }
                    }
                  ]
                }
              },
              "required": [
                "todos"
              ]
            },
            "annotations": {
              "readOnlyHint": true,
              "destructiveHint": false,
              "idempotentHint": true,
              "openWorldHint": false
            }
          },
          {
            "name": "write_file",
            "description": "Write a UTF-8 text file inside the workspace.",
            "inputSchema": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "content": {
                  "type": "string"
                }
              },
              "required": [
                "path",
                "content"
              ]
            },
            "annotations": {
              "readOnlyHint": false,
              "destructiveHint": true,
              "idempotentHint": false,
              "openWorldHint": false
            }
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "resources/list"
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 3,
      "result": {
        "resources": [
          {
            "uri": "harness://docs/readme",
            "name": "README",
            "description": "Project overview and usage guide.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://docs/readme-zh",
            "name": "README.zh-CN",
            "description": "Chinese project overview and usage guide.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://docs/mcp",
            "name": "MCP",
            "description": "MCP server usage and protocol boundary notes.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/eval",
            "name": "EVAL",
            "description": "Latest scripted benchmark snapshot.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/agent-eval",
            "name": "AGENT_EVAL",
            "description": "Latest committed real-agent evaluation report.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/eval-history",
            "name": "EVAL_HISTORY",
            "description": "Committed eval trend report across agent runs.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/failure-modes",
            "name": "FAILURE_MODES",
            "description": "Committed failure-mode dashboard for agent eval runs.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/agent-compare",
            "name": "AGENT_COMPARE_2_TASKS",
            "description": "Committed memory/context ablation report.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://reports/demo-python-bugfix",
            "name": "DEMO_python_bugfix",
            "description": "Committed deterministic local demo report.",
            "mimeType": "text/markdown"
          },
          {
            "uri": "harness://rag/index-summary",
            "name": "RAG_INDEX_SUMMARY",
            "description": "Dynamic summary of the safe local workspace retrieval index.",
            "mimeType": "text/markdown"
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "resources/templates/list"
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 4,
      "result": {
        "resourceTemplates": [
          {
            "uriTemplate": "harness://workspace/{path}",
            "name": "workspace-file",
            "title": "Workspace File",
            "description": "Read a non-sensitive text file inside the configured workspace.",
            "mimeType": "text/plain",
            "annotations": {
              "audience": [
                "assistant"
              ],
              "priority": 0.7
            }
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 5,
      "method": "prompts/list"
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 5,
      "result": {
        "prompts": [
          {
            "name": "code-maintenance-task",
            "title": "Code Maintenance Task",
            "description": "Plan and execute a repository maintenance task with tool evidence.",
            "arguments": [
              {
                "name": "task",
                "description": "The maintenance task to perform.",
                "required": true
              }
            ]
          },
          {
            "name": "eval-analysis",
            "title": "Evaluation Analysis",
            "description": "Analyze benchmark, trend, and failure-mode reports and summarize risks.",
            "arguments": [
              {
                "name": "report_uri",
                "description": "Optional MCP resource URI to analyze instead of the default eval report set.",
                "required": false
              }
            ]
          },
          {
            "name": "repo-rag-maintenance",
            "title": "Repo RAG Maintenance",
            "description": "Use local retrieval loading first, then inspect exact files and perform a repository maintenance task.",
            "arguments": [
              {
                "name": "task",
                "description": "The repository maintenance task to perform.",
                "required": true
              },
              {
                "name": "query",
                "description": "Optional retrieval query; defaults to the task text.",
                "required": false
              }
            ]
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 6,
      "method": "resources/read",
      "params": {
        "uri": "harness://docs/mcp"
      }
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 6,
      "result": {
        "contents": [
          {
            "uri": "harness://docs/mcp",
            "mimeType": "text/markdown",
            "text": "# MCP Server\n\nThe project exposes its existing `ToolRegistry`, selected project reports, and task prompt templates through a minimal MCP stdio server.\n\n## Run\n\n```powershell\npython main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server\n```\n\nEnable write-capable tools only when you want the MCP client to edit files:\n\n```powershell\npython main.py --workspace . --trace artifacts/mcp_trace.jsonl --allow-write mcp-server\n```\n\n`stdout` is reserved for JSON-RPC MCP messages. Operational trace data is written to the trace file.\n\n## Client Config\n\n`examples/mcp_config.example.json` contains a copyable stdio MCP client configuration:\n\n```json\n{\n  \"mcpServers\": {\n    \"mini-coding-agent-harness\": {\n      \"command\": \"python\",\n      \"args\": [\n        \"/absolute/path/to/mini-coding-agent-harness/main.py\",\n        \"--workspace\",\n        \"/absolute/path/to/mini-coding-agent-harness\",\n        \"--trace\",\n        \"/absolute/path/to/mini-coding-agent-harness/artifacts/mcp_client_trace.jsonl\",\n        \"mcp-server\"\n      ]\n    }\n  }\n}\n```\n\nReplace `/absolute/path/to/mini-coding-agent-harness` with your local checkout path. Use the write-enabled entry in the example file only when the client should be allowed to edit existing files.\n\n## Supported Methods\n\n- `initialize`\n- `notifications/initialized`\n- `ping`\n- `tools/list`\n- `tools/call`\n- `resources/list`\n- `resources/read`\n- `resources/templates/list`\n- `prompts/list`\n- `prompts/get`\n\n`tools/list` maps registered harness tools to MCP tools. The schema comes from each local tool's `input_schema`. Retrieval tools such as `index_workspace`, `rag_search`, `rag_explain`, `retrieve_then_read`, and `context_pack` are exposed through the same permission-checked path.\n\n`tools/call` calls the same permission-checked `ToolRegistry.call(...)` path used by the CLI and agent loop. Tool failures are returned as MCP tool results with `isError: true`, while protocol errors use JSON-RPC error responses.\n\n`resources/list` exposes a small whitelist of project documents and committed reports, including `README.md`, `MCP.md`, `EVAL.md`, `reports/AGENT_EVAL.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, and the demo report. It also exposes `harness://rag/index-summary`, a dynamic summary of the safe local retrieval index. Arbitrary file reads should use the permission-checked `read_file` tool instead.\n\n`resources/templates/list` exposes `harness://workspace/{path}` for safe workspace text resources. Sensitive paths such as `.env`, `.git`, `artifacts`, and `eval_runs` are blocked.\n\n`prompts/list` exposes reusable prompts for repository maintenance, RAG-first maintenance, and evaluation analysis. `prompts/get` fills those prompt templates with caller-provided arguments. The `repo-rag-maintenance` prompt requires a `retrieve_then_read` call before follow-up exact file reads. The `eval-analysis` prompt defaults to `harness://reports/agent-eval`, `harness://reports/eval-history`, and `harness://reports/failure-modes`; pass `report_uri` to analyze one specific report instead.\n\n## Example Messages\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"clientInfo\":{\"name\":\"demo\",\"version\":\"0.1.0\"},\"capabilities\":{}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"read_file\",\"arguments\":{\"path\":\"README.md\",\"limit\":20}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"context_pack\",\"arguments\":{\"query\":\"pytest failing import fix\",\"glob\":\"*.py\",\"limit\":3}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"rag_search\",\"arguments\":{\"query\":\"pytest failing import fix\",\"glob\":\"*.py,*.md\",\"limit\":3}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"rag_explain\",\"arguments\":{\"query\":\"pytest failing import fix\",\"glob\":\"*.py,*.md\",\"limit\":3}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"retrieve_then_read\",\"arguments\":{\"query\":\"pytest failing import fix\",\"glob\":\"*.py,*.md\",\"limit\":3}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"resources/read\",\"params\":{\"uri\":\"harness://rag/index-summary\"}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"resources/read\",\"params\":{\"uri\":\"harness://reports/agent-eval\"}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":10,\"method\":\"resources/read\",\"params\":{\"uri\":\"harness://reports/eval-history\"}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":11,\"method\":\"resources/read\",\"params\":{\"uri\":\"harness://reports/failure-modes\"}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":12,\"method\":\"prompts/get\",\"params\":{\"name\":\"code-maintenance-task\",\"arguments\":{\"task\":\"Fix the failing calculator test and show evidence.\"}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":13,\"method\":\"prompts/get\",\"params\":{\"name\":\"repo-rag-maintenance\",\"arguments\":{\"task\":\"Fix the failing calculator test and show evidence.\",\"query\":\"calculator failing pytest assertion\"}}}\n```\n\n```json\n{\"jsonrpc\":\"2.0\",\"id\":14,\"method\":\"prompts/get\",\"params\":{\"name\":\"eval-analysis\",\"arguments\":{}}}\n```\n\n## Boundaries\n\n- This is a stdio MCP server, not an HTTP/SSE server.\n- It exposes local harness tools, selected read-only resources, and prompt templates.\n- Tool calls keep the harness permission policy.\n- RAG is local chunked lexical retrieval with path and line metadata; it is not embedding-based and does not use a vector database.\n- Write tools still require `--allow-write` for existing files.\n- Shell and Git commands still use the existing allowlist and `shell=False`.\n- It is not an OS-level sandbox.\n- It does not implement OAuth or resource subscriptions.\n"
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 7,
      "method": "prompts/get",
      "params": {
        "name": "code-maintenance-task",
        "arguments": {
          "task": "Fix a failing test and show evidence."
        }
      }
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 7,
      "result": {
        "description": "Repository maintenance prompt with planning and verification requirements.",
        "messages": [
          {
            "role": "user",
            "content": {
              "type": "text",
              "text": "Use the available MCP tools to complete this repository maintenance task.\nStart with todo_write, use context_pack when the relevant files are not obvious, inspect relevant files, make the smallest safe change, run run_tests or run_py_compile, inspect git_diff, and finish with files changed and evidence.\n\nTask: Fix a failing test and show evidence."
            }
          }
        ]
      }
    }
  },
  {
    "request": {
      "jsonrpc": "2.0",
      "id": 8,
      "method": "tools/call",
      "params": {
        "name": "permission_policy",
        "arguments": {}
      }
    },
    "response": {
      "jsonrpc": "2.0",
      "id": 8,
      "result": {
        "content": [
          {
            "type": "text",
            "text": "# Permission Policy\n\n- Workspace root: D:\\-\\hello-agent\\mini-coding-agent-harness\n- Write access: existing files require allow_write\n- File paths are resolved inside the workspace; path escape attempts are blocked.\n- `delete_file` requires `confirm=true` and refuses directories.\n- Shell commands are tokenized with `shlex`, executed with `shell=False`, and shell operators are blocked.\n- Allowed shell executables: cat, dir, echo, findstr, get-childitem, ls, pwd, py, py.exe, pytest, pytest.exe, python, python.exe, type\n- Read-only Git subcommands: branch, diff, log, ls-files, rev-parse, show, status\n- Force flags and mutating Git subcommands are blocked.\n- This is a harness permission policy, not an OS-level sandbox."
          }
        ],
        "structuredContent": {
          "ok": true,
          "metadata": {
            "workspace": "D:\\-\\hello-agent\\mini-coding-agent-harness",
            "allow_write": false,
            "write_tools": [
              "write_file",
              "edit_file",
              "delete_file",
              "save_memory"
            ],
            "delete_requires_confirmation": true,
            "path_scope": "workspace_only",
            "shell_false": true,
            "shell_operator_markers": [
              "&&",
              "||",
              ";",
              "|",
              ">",
              "<",
              "\n",
              "\r"
            ],
            "allowed_shell_commands": [
              "cat",
              "dir",
              "echo",
              "findstr",
              "get-childitem",
              "ls",
              "pwd",
              "py",
              "py.exe",
              "pytest",
              "pytest.exe",
              "python",
              "python.exe",
              "type"
            ],
            "read_only_git_subcommands": [
              "branch",
              "diff",
              "log",
              "ls-files",
              "rev-parse",
              "show",
              "status"
            ],
            "os_sandbox": false
          }
        },
        "isError": false
      }
    }
  }
]
```
