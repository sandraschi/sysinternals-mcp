# Sysinternals MCP -- dev recipes
serve port="11074":
    uv run python -m sysinternals_mcp.server --port {{port}}

test:
    uv run pytest tests/ -q --tb=short

lint:
    uv run ruff check src/ tests/

fmt:
    uv run ruff format src/ tests/

check: lint
    uv run ruff check --fix src/ tests/

pack:
    uv run python -m mcpb pack . dist/sysinternals-mcp-v0.1.0.mcpb

validate:
    uv run python -m mcpb validate

clean:
    Remove-Item -Recurse -Force dist/ -ErrorAction SilentlyContinue
