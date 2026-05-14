#!/usr/bin/env node

/**
 * Test suite for NLSQL MCP Server Node.js wrapper
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const chalk = require('chalk');
const NLSQLMCPServer = require('../index.js');

class TestRunner {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }

    addTest(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTests() {
        console.log(chalk.blue.bold('\n=== NLSQL MCP Server Test Suite ===\n'));

        for (const test of this.tests) {
            try {
                console.log(chalk.gray(`▶ Running: ${test.name}`));
                await test.testFn();
                console.log(chalk.green(`  ✅ PASS: ${test.name}`));
                this.passed++;
            } catch (error) {
                console.log(chalk.red(`  ❌ FAIL: ${test.name} - ${error.message}`));
                this.failed++;
            }
        }

        console.log(chalk.gray('\n---'));
        console.log(`Tests completed: ${this.passed} passed, ${this.failed} failed`);

        if (this.failed === 0) {
            console.log(chalk.green('All tests passed! 🎉'));
            return true;
        } else {
            console.log(chalk.red(`${this.failed} test(s) failed`));
            return false;
        }
    }
}

async function main() {
    const runner = new TestRunner();

    // Test 1: Package structure
    runner.addTest('Package structure', async () => {
        const packageJson = require('../package.json');
        assert(packageJson.name === 'nlsql-mcp-server', 'Package name incorrect');
        assert(packageJson.version, 'Version not defined');
        assert(packageJson.bin, 'Binary not defined');

        const requiredFiles = [
            '../index.js',
            '../bin/nlsql-mcp-server.js',
            '../scripts/install-deps.js'
        ];

        for (const file of requiredFiles) {
            const fullPath = path.join(__dirname, file);
            assert(fs.existsSync(fullPath), `Required file missing: ${file}`);
        }
    });

    // Test 2: Python detection
    runner.addTest('Python detection', async () => {
        const pythonExecutables = ['python3', 'python', 'py'];
        let pythonFound = false;

        for (const cmd of pythonExecutables) {
            try {
                await new Promise((resolve, reject) => {
                    const testProcess = spawn(cmd, ['--version'], { stdio: 'pipe' });
                    testProcess.on('close', (code) => {
                        if (code === 0) {
                            pythonFound = true;
                            resolve();
                        } else {
                            reject();
                        }
                    });
                    testProcess.on('error', reject);
                });
                break;
            } catch {
                continue;
            }
        }

        assert(pythonFound, 'Python executable not found');
    });

    // Test 3: Server instantiation
    runner.addTest('Server instantiation', async () => {
        const server = new NLSQLMCPServer({
            debug: true
        });

        assert(server.options, 'Server options not set');
        assert(server.options.debug === true, 'Debug option not set');

        const status = server.getStatus();
        assert(status.running === false, 'Server should not be running initially');
        assert(status.pid === null, 'PID should be null initially');
    });

    // Test 4: Requirements file handling
    runner.addTest('Requirements file handling', async () => {
        const { installPythonDependencies } = require('../scripts/install-deps.js');

        assert(typeof installPythonDependencies === 'function', 'Install function not exported');

        const requirementsPath = path.join(__dirname, '..', 'python-src', 'requirements.txt');
        assert(fs.existsSync(requirementsPath), 'Requirements file should exist');
    });

    // Test 5: CLI script executable
    runner.addTest('CLI script executable', async () => {
        const cliScript = path.join(__dirname, '..', 'bin', 'nlsql-mcp-server.js');

        assert(fs.existsSync(cliScript), 'CLI script not found');

        if (process.platform !== 'win32') {
            const stats = fs.statSync(cliScript);
            const isExecutable = !!(stats.mode & parseInt('111', 8));
            assert(isExecutable, 'CLI script not executable');
        }

        const content = fs.readFileSync(cliScript, 'utf8');
        assert(content.startsWith('#!/usr/bin/env node'), 'CLI script missing proper shebang');
    });

    const success = await runner.runTests();
    process.exit(success ? 0 : 1);
}

if (require.main === module) {
    main().catch((error) => {
        console.error('Test runner failed:', error);
        process.exit(1);
    });
}
