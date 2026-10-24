# Per-repo fleet start config for sysinternals-mcp
@{
    Name         = 'sysinternals-mcp'
    BackendPort  = 11074
    FrontendPort = 11251
    HealthPath   = '/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind      = 'module-serve'
        Module    = 'sysinternals_mcp.server'
        ServeArgs = '--mode http'
        Env       = @{ MCP_MODE = 'http'; MCP_PORT = '11074'; WEB_PORT = '11074' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}