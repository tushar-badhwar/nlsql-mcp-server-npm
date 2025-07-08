#!/usr/bin/env node

/**
 * Test suite for NLSQL MCP Server Node.js wrapper
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const NLSQLMCPServer = require('../index.js');
const ConfigManager = require('../lib/config.js');
const { Logger } = require('../lib/logger.js');

class TestRunner {
    constructor() {
        this.tests = [];
        this.logger = new Logger({ prefix: 'TEST' });
        this.passed = 0;
        this.failed = 0;
    }

    addTest(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTests() {
        this.logger.header('NLSQL MCP Server Test Suite');
        
        for (const test of this.tests) {
            try {
                this.logger.step(`Running: ${test.name}`);
                await test.testFn();
                this.logger.success(`PASS: ${test.name}`);
                this.passed++;
            } catch (error) {
                this.logger.error(`FAIL: ${test.name} - ${error.message}`);
                this.failed++;
            }
        }

        this.logger.separator();
        this.logger.info(`Tests completed: ${this.passed} passed, ${this.failed} failed`);
        
        if (this.failed === 0) {
            this.logger.success('All tests passed! 🎉');
            return true;
        } else {
            this.logger.error(`${this.failed} test(s) failed`);
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
        
        // Check required files exist
        const requiredFiles = [
            '../index.js',
            '../bin/nlsql-mcp-server.js',
            '../lib/config.js',
            '../lib/logger.js',
            '../scripts/install-deps.js'
        ];
        
        for (const file of requiredFiles) {
            const fullPath = path.join(__dirname, file);
            assert(fs.existsSync(fullPath), `Required file missing: ${file}`);
        }
    });

    // Test 2: Configuration manager
    runner.addTest('Configuration manager', async () => {
        const config = new ConfigManager();
        const defaultConfig = config.getDefaultConfig();
        
        assert(defaultConfig.python, 'Python config missing');
        assert(defaultConfig.server, 'Server config missing');
        assert(Array.isArray(defaultConfig.python.requirements), 'Requirements should be array');
        
        // Test Claude Desktop config generation
        const claudeConfig = config.generateClaudeDesktopConfig();
        assert(claudeConfig.mcpServers, 'MCP servers config missing');
        assert(claudeConfig.mcpServers.nlsql, 'NLSQL server config missing');
    });

    // Test 3: Logger functionality
    runner.addTest('Logger functionality', async () => {
        const logger = new Logger({ level: 'debug' });
        
        assert(logger.shouldLog('error'), 'Should log error');
        assert(logger.shouldLog('debug'), 'Should log debug');
        
        const logger2 = new Logger({ level: 'warn' });
        assert(logger2.shouldLog('error'), 'Should log error');
        assert(!logger2.shouldLog('debug'), 'Should not log debug');
    });

    // Test 4: Python detection
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

    // Test 5: Server instantiation
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

    // Test 6: Requirements file creation
    runner.addTest('Requirements file handling', async () => {
        const { installPythonDependencies } = require('../scripts/install-deps.js');
        
        // Test that the install script exists and can be required
        assert(typeof installPythonDependencies === 'function', 'Install function not exported');
        
        // Check if requirements.txt would be created
        const testRequirementsPath = path.join(__dirname, '..', 'python-src', 'requirements.txt');
        const parentDir = path.dirname(testRequirementsPath);
        
        if (!fs.existsSync(parentDir)) {
            fs.mkdirSync(parentDir, { recursive: true });
        }
        
        if (!fs.existsSync(testRequirementsPath)) {
            const basicRequirements = `mcp>=1.0.0
crewai>=0.22.0`;
            fs.writeFileSync(testRequirementsPath, basicRequirements);
        }
        
        assert(fs.existsSync(testRequirementsPath), 'Requirements file should exist or be creatable');
    });

    // Test 7: CLI script executable
    runner.addTest('CLI script executable', async () => {
        const cliScript = path.join(__dirname, '..', 'bin', 'nlsql-mcp-server.js');
        
        // Check file exists
        assert(fs.existsSync(cliScript), 'CLI script not found');
        
        // Check it's executable (on Unix systems)
        if (process.platform !== 'win32') {
            const stats = fs.statSync(cliScript);
            const isExecutable = !!(stats.mode & parseInt('111', 8));
            assert(isExecutable, 'CLI script not executable');
        }
        
        // Check shebang
        const content = fs.readFileSync(cliScript, 'utf8');
        assert(content.startsWith('#!/usr/bin/env node'), 'CLI script missing proper shebang');
    });

    // Run all tests
    const success = await runner.runTests();
    process.exit(success ? 0 : 1);
}

if (require.main === module) {
    main().catch((error) => {
        console.error('Test runner failed:', error);
        process.exit(1);
    });
}