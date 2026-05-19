#!/usr/bin/env node

/**
 * NLSQL MCP Server - Node.js wrapper.
 *
 * Spawns the Python MCP server from a dedicated, package-local virtualenv
 * (built by scripts/install-deps.js with a CrewAI-compatible interpreter).
 * On `start`, if the venv is missing/incomplete, it self-heals before
 * launching (hybrid setup mode).
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');
const { ensureSetup, isVenvReady, venvPython } = require('./scripts/install-deps.js');

class NLSQLMCPServer {
    constructor(options = {}) {
        this.options = {
            // If a caller forces an executable we honor it; otherwise we use
            // the package venv (resolved lazily at start time).
            pythonExecutable: options.pythonExecutable || null,
            serverPath: options.serverPath || this.getDefaultServerPath(),
            cwd: options.cwd || this.getPackageRoot(),
            env: { ...process.env, ...options.env },
            debug: options.debug || false,
        };
        this.process = null;
    }

    getPackageRoot() {
        return path.join(__dirname, 'python-src');
    }

    getDefaultServerPath() {
        return path.join(this.getPackageRoot(), 'nlsql_mcp_server', 'server.py');
    }

    resolvePython() {
        return this.options.pythonExecutable || venvPython();
    }

    async checkPythonDependencies() {
        const py = this.resolvePython();
        return new Promise((resolve, reject) => {
            const checkScript =
                'import mcp, crewai, openai, sqlalchemy; print("DEPENDENCIES_OK")';
            const proc = spawn(py, ['-c', checkScript], {
                stdio: ['pipe', 'pipe', 'pipe'],
                env: this.options.env,
            });
            let out = '';
            let err = '';
            proc.stdout.on('data', (d) => (out += d.toString()));
            proc.stderr.on('data', (d) => (err += d.toString()));
            proc.on('close', (code) => {
                if (code === 0 && out.includes('DEPENDENCIES_OK')) resolve(true);
                else reject(new Error(`Python dependency check failed: ${err || out}`));
            });
            proc.on('error', (e) => reject(new Error(`Failed to run Python: ${e.message}`)));
        });
    }

    async start() {
        // MCP mode = stdio transport (no TTY); keep stdout clean for JSON-RPC.
        const mcpMode = !process.stdin.isTTY;

        if (!isVenvReady()) {
            if (mcpMode) {
                // The venv build is a multi-minute pip install; it cannot
                // complete inside an MCP client's handshake window. Attempting
                // the self-heal here just produces a mysterious timeout. Fail
                // fast with a diagnosable message on stderr (MCP clients
                // surface stderr in their logs) and let the user warm the
                // environment once in a terminal.
                console.error(
                    'NLSQL MCP server cannot start: Python environment is not built yet.\n' +
                    'Run this once in a terminal, then restart your MCP client:\n' +
                    '  npx nlsql-mcp-server install-deps\n'
                );
                process.exit(1);
            }
            // Terminal mode: a human is watching and can wait for the one-time
            // build, so self-heal here.
            console.log(chalk.blue('🔧 Python environment not ready — setting up now...'));
            const ok = await ensureSetup();
            if (!ok) {
                console.error(
                    chalk.red('\n❌ Cannot start: Python environment is not set up.')
                );
                console.error(
                    chalk.gray('   See the instructions above, then re-run.')
                );
                process.exit(1);
            }
        }

        const py = this.resolvePython();

        if (!fs.existsSync(this.options.serverPath)) {
            if (!mcpMode) {
                console.error(
                    chalk.red(`❌ Python server file not found: ${this.options.serverPath}`)
                );
            }
            process.exit(1);
        }

        if (!mcpMode && this.options.debug) {
            console.log(chalk.green(`✅ Using interpreter: ${py}`));
            console.log(chalk.blue('🚀 Starting NLSQL MCP Server...'));
        }

        this.process = spawn(py, ['-m', 'nlsql_mcp_server.server'], {
            cwd: this.options.cwd,
            stdio: 'inherit',
            env: { ...this.options.env, MCP_MODE: mcpMode ? '1' : '0' },
        });

        this.process.on('error', (err) => {
            if (!mcpMode) {
                console.error(chalk.red('❌ Failed to start Python server:'), err.message);
            }
            process.exit(1);
        });

        this.process.on('close', (code) => {
            if (code !== 0 && !mcpMode) {
                console.error(chalk.red(`❌ Python server exited with code ${code}`));
            }
            if (code !== 0) process.exit(code);
        });

        process.on('SIGINT', () => this.stop());
        process.on('SIGTERM', () => this.stop());
    }

    stop() {
        if (this.process) {
            this.process.kill('SIGTERM');
            this.process = null;
        }
        process.exit(0);
    }

    getStatus() {
        return {
            running: this.process !== null && !this.process.killed,
            pid: this.process ? this.process.pid : null,
            venvReady: isVenvReady(),
            options: this.options,
        };
    }
}

if (require.main === module) {
    const server = new NLSQLMCPServer({
        debug: process.argv.includes('--debug') || process.argv.includes('-d'),
    });
    server.start().catch((error) => {
        console.error(chalk.red('Failed to start server:'), error.message);
        process.exit(1);
    });
}

module.exports = NLSQLMCPServer;
