#!/usr/bin/env node

/**
 * NLSQL MCP Server CLI
 * 
 * Command-line interface for the NLSQL MCP Server
 */

const { Command } = require('commander');
const chalk = require('chalk');
const ora = require('ora');
const path = require('path');
const fs = require('fs');
const NLSQLMCPServer = require('../index.js');
const { ensureSetup, isVenvReady, venvPython, VENV_DIR } = require('../scripts/install-deps.js');

const program = new Command();

// Package info
const packageJson = require('../package.json');

program
    .name('nlsql-mcp-server')
    .description('Natural Language to SQL MCP Server')
    .version(packageJson.version);

program
    .command('start')
    .description('Start the NLSQL MCP Server')
    .option('-d, --debug', 'Enable debug mode')
    .option('--python <executable>', 'Force a specific Python executable (default: package venv)')
    .option('--env-file <file>', 'Environment file to load')
    .action(async (options) => {
        try {
            // Detect MCP mode (no TTY input - either false or undefined when piped)
            const mcpMode = !process.stdin.isTTY;
            
            if (!mcpMode) {
                console.log(chalk.blue.bold(`🤖 NLSQL MCP Server v${packageJson.version}`));
                console.log(chalk.gray('Convert natural language to SQL using AI\n'));
            }

            // Load environment file if specified
            if (options.envFile) {
                if (fs.existsSync(options.envFile)) {
                    require('dotenv').config({ path: options.envFile });
                    if (!mcpMode) {
                        console.log(chalk.green(`📁 Loaded environment from: ${options.envFile}`));
                    }
                } else {
                    if (!mcpMode) {
                        console.warn(chalk.yellow(`⚠️  Environment file not found: ${options.envFile}`));
                    }
                }
            }

            // Check for OpenAI API key
            if (!process.env.OPENAI_API_KEY && !mcpMode) {
                console.warn(chalk.yellow('⚠️  OpenAI API key not set. Natural language features will not work.'));
                console.log(chalk.gray('   Set OPENAI_API_KEY environment variable or use --env-file\n'));
            }

            const server = new NLSQLMCPServer({
                debug: options.debug,
                pythonExecutable: options.python || null
            });

            await server.start();

        } catch (error) {
            console.error(chalk.red('❌ Failed to start server:'), error.message);
            process.exit(1);
        }
    });

program
    .command('install-deps')
    .description('(Re)build the Python virtualenv and install dependencies')
    .action(async () => {
        // Force a clean rebuild even if a venv already exists.
        if (fs.existsSync(VENV_DIR)) {
            fs.rmSync(VENV_DIR, { recursive: true, force: true });
        }
        const ok = await ensureSetup();
        process.exit(ok ? 0 : 1);
    });

program
    .command('test')
    .description('Test the NLSQL MCP Server installation')
    .action(async () => {
        console.log(chalk.blue.bold('🧪 Testing NLSQL MCP Server Installation\n'));

        const tests = [
            {
                name: 'Python virtualenv built',
                test: async () => isVenvReady()
            },
            {
                name: 'Python dependencies (mcp, crewai, openai, sqlalchemy)',
                test: async () => {
                    if (!isVenvReady()) return false;
                    const server = new NLSQLMCPServer({ pythonExecutable: venvPython() });
                    try {
                        await server.checkPythonDependencies();
                        return true;
                    } catch {
                        return false;
                    }
                }
            },
            {
                name: 'OpenAI API key',
                test: async () => {
                    return !!process.env.OPENAI_API_KEY;
                }
            }
        ];

        for (const test of tests) {
            const spinner = ora(`Testing ${test.name}...`).start();
            const result = await test.test();
            
            if (result) {
                spinner.succeed(`${test.name} ✅`);
            } else {
                spinner.fail(`${test.name} ❌`);
            }
        }

        console.log(chalk.green('\n✅ Testing complete!'));
    });

program
    .command('config')
    .description('Generate Claude Desktop configuration')
    .option('--path <path>', 'Custom path to the server')
    .action((options) => {
        const serverPath = options.path || process.cwd();
        
        const config = {
            "mcpServers": {
                "nlsql": {
                    "command": "npx",
                    "args": ["nlsql-mcp-server", "start"],
                    "cwd": serverPath,
                    "env": {
                        "OPENAI_API_KEY": "your_openai_api_key_here"
                    }
                }
            }
        };

        console.log(chalk.blue.bold('📋 Claude Desktop Configuration\n'));
        console.log('Add this to your Claude Desktop config file:\n');
        console.log(chalk.gray(JSON.stringify(config, null, 2)));
        console.log(chalk.yellow('\n💡 Remember to replace "your_openai_api_key_here" with your actual API key'));
    });

// Handle unknown commands
program.on('command:*', function (operands) {
    console.error(chalk.red(`Unknown command: ${operands[0]}`));
    console.log('See --help for available commands');
    process.exit(1);
});

// Show help if no command provided
if (!process.argv.slice(2).length) {
    program.outputHelp();
}

program.parse();