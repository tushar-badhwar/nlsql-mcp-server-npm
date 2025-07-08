#!/usr/bin/env node

/**
 * NLSQL MCP Server - Node.js Wrapper
 * 
 * This is the main entry point for the Node.js wrapper around the Python NLSQL MCP server.
 * It handles spawning the Python process and managing communication.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');

class NLSQLMCPServer {
    constructor(options = {}) {
        this.options = {
            pythonExecutable: options.pythonExecutable || 'python3',
            serverPath: options.serverPath || this.getDefaultServerPath(),
            cwd: options.cwd || this.getPackageRoot(),
            env: { ...process.env, ...options.env },
            debug: options.debug || false
        };
        this.process = null;
    }

    getPackageRoot() {
        return path.join(__dirname, 'python-src');
    }

    getDefaultServerPath() {
        return path.join(this.getPackageRoot(), 'nlsql_mcp_server', 'server.py');
    }

    async checkPythonDependencies() {
        return new Promise((resolve, reject) => {
            const checkScript = `
import sys
try:
    import mcp
    import crewai
    import openai
    import sqlalchemy
    print("DEPENDENCIES_OK")
    sys.exit(0)
except ImportError as e:
    print(f"MISSING_DEPENDENCY: {e}")
    sys.exit(1)
            `;

            const pythonProcess = spawn(this.options.pythonExecutable, ['-c', checkScript], {
                stdio: ['pipe', 'pipe', 'pipe'],
                env: this.options.env
            });

            let output = '';
            let error = '';

            pythonProcess.stdout.on('data', (data) => {
                output += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                error += data.toString();
            });

            pythonProcess.on('close', (code) => {
                if (code === 0 && output.includes('DEPENDENCIES_OK')) {
                    resolve(true);
                } else {
                    reject(new Error(`Python dependencies check failed: ${error || output}`));
                }
            });

            pythonProcess.on('error', (err) => {
                reject(new Error(`Failed to run Python: ${err.message}`));
            });
        });
    }

    async start() {
        try {
            if (this.options.debug) {
                console.log(chalk.blue('🔍 Checking Python dependencies...'));
            }

            // Check if Python dependencies are installed
            await this.checkPythonDependencies();

            if (this.options.debug) {
                console.log(chalk.green('✅ Python dependencies OK'));
                console.log(chalk.blue('🚀 Starting NLSQL MCP Server...'));
            }

            // Check if server file exists
            if (!fs.existsSync(this.options.serverPath)) {
                throw new Error(`Python server file not found at: ${this.options.serverPath}`);
            }

            // Spawn the Python MCP server
            this.process = spawn(this.options.pythonExecutable, ['-m', 'nlsql_mcp_server.server'], {
                cwd: this.options.cwd,
                stdio: ['inherit', 'inherit', 'inherit'],
                env: this.options.env
            });

            // Handle process events
            this.process.on('error', (err) => {
                console.error(chalk.red('❌ Failed to start Python server:'), err.message);
                process.exit(1);
            });

            this.process.on('close', (code) => {
                if (code !== 0) {
                    console.error(chalk.red(`❌ Python server exited with code ${code}`));
                    process.exit(code);
                }
            });

            // Handle graceful shutdown
            process.on('SIGINT', () => {
                this.stop();
            });

            process.on('SIGTERM', () => {
                this.stop();
            });

            if (this.options.debug) {
                console.log(chalk.green('✅ NLSQL MCP Server started successfully'));
            }

        } catch (error) {
            console.error(chalk.red('❌ Error starting server:'), error.message);
            
            if (error.message.includes('MISSING_DEPENDENCY')) {
                console.log(chalk.yellow('\n💡 Try running: npm run install-python-deps'));
                console.log(chalk.yellow('Or manually install: pip install -r requirements.txt'));
            }
            
            process.exit(1);
        }
    }

    stop() {
        if (this.process) {
            console.log(chalk.yellow('\n🛑 Stopping NLSQL MCP Server...'));
            this.process.kill('SIGTERM');
            this.process = null;
        }
        process.exit(0);
    }

    getStatus() {
        return {
            running: this.process !== null && !this.process.killed,
            pid: this.process ? this.process.pid : null,
            options: this.options
        };
    }
}

// If this file is run directly (not required as a module)
if (require.main === module) {
    const server = new NLSQLMCPServer({
        debug: process.argv.includes('--debug') || process.argv.includes('-d')
    });
    
    server.start().catch((error) => {
        console.error(chalk.red('Failed to start server:'), error.message);
        process.exit(1);
    });
}

module.exports = NLSQLMCPServer;