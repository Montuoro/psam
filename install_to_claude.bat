@echo off
REM Script to install MCP server configuration to Claude Desktop

SET CLAUDE_CONFIG_DIR=C:\Users\PMontuoro\AppData\Roaming\Claude
SET CLAUDE_CONFIG_FILE=%CLAUDE_CONFIG_DIR%\claude_desktop_config.json
SET MCP_CONFIG=C:\data projects\mcp\claude_desktop_config.json

echo ========================================
echo School Data MCP Server Installer
echo ========================================
echo.

REM Check if Claude config directory exists
if not exist "%CLAUDE_CONFIG_DIR%" (
    echo Creating Claude Desktop config directory...
    mkdir "%CLAUDE_CONFIG_DIR%"
)

REM Check if config file already exists
if exist "%CLAUDE_CONFIG_FILE%" (
    echo WARNING: Claude Desktop config file already exists!
    echo Location: %CLAUDE_CONFIG_FILE%
    echo.
    echo You need to manually merge the configuration from:
    echo %MCP_CONFIG%
    echo.
    echo Opening both files in notepad...
    start notepad "%CLAUDE_CONFIG_FILE%"
    timeout /t 2 /nobreak >nul
    start notepad "%MCP_CONFIG%"
    echo.
    echo Please add the "school-data" entry from the second file to the first file's "mcpServers" section.
) else (
    echo No existing config found. Creating new config file...
    copy "%MCP_CONFIG%" "%CLAUDE_CONFIG_FILE%"
    echo Config file created successfully!
    echo Location: %CLAUDE_CONFIG_FILE%
)

echo.
echo ========================================
echo IMPORTANT: Restart Claude Desktop
echo ========================================
echo.
echo After configuring, you MUST restart Claude Desktop completely for changes to take effect.
echo.
pause
