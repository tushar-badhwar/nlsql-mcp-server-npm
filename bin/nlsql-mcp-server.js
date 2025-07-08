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
    .option('--python <executable>', 'Python executable to use', 'python3')
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
                pythonExecutable: options.python
            });

            await server.start();

        } catch (error) {
            console.error(chalk.red('❌ Failed to start server:'), error.message);
            process.exit(1);
        }
    });

program
    .command('install-deps')
    .description('Install Python dependencies')
    .option('--python <executable>', 'Python executable to use', 'python3')
    .action(async (options) => {
        const spinner = ora('Installing Python dependencies...').start();
        
        try {
            const { spawn } = require('child_process');
            const packageRoot = path.join(__dirname, '..', 'python-src');
            const requirementsFile = path.join(packageRoot, 'requirements.txt');

            if (!fs.existsSync(requirementsFile)) {
                throw new Error(`Requirements file not found: ${requirementsFile}`);
            }

            await new Promise((resolve, reject) => {
                const installProcess = spawn(options.python, ['-m', 'pip', 'install', '-r', requirementsFile], {
                    cwd: packageRoot,
                    stdio: 'pipe'
                });

                let output = '';
                let error = '';

                installProcess.stdout.on('data', (data) => {
                    output += data.toString();
                });

                installProcess.stderr.on('data', (data) => {
                    error += data.toString();
                });

                installProcess.on('close', (code) => {
                    if (code === 0) {
                        resolve();
                    } else {
                        reject(new Error(`Installation failed with code ${code}: ${error}`));
                    }
                });

                installProcess.on('error', (err) => {
                    reject(new Error(`Failed to run pip: ${err.message}`));
                });
            });

            spinner.succeed('Python dependencies installed successfully');

        } catch (error) {
            spinner.fail(`Failed to install dependencies: ${error.message}`);
            process.exit(1);
        }
    });

program
    .command('test')
    .description('Test the NLSQL MCP Server installation')
    .option('--python <executable>', 'Python executable to use', 'python3')
    .action(async (options) => {
        console.log(chalk.blue.bold('🧪 Testing NLSQL MCP Server Installation\n'));

        const tests = [
            {
                name: 'Python executable',
                test: async () => {
                    const { spawn } = require('child_process');
                    return new Promise((resolve) => {
                        const pythonProcess = spawn(options.python, ['--version'], { stdio: 'pipe' });
                        pythonProcess.on('close', (code) => resolve(code === 0));
                        pythonProcess.on('error', () => resolve(false));
                    });
                }
            },
            {
                name: 'Python dependencies',
                test: async () => {
                    const server = new NLSQLMCPServer({ pythonExecutable: options.python });
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