#!/usr/bin/env node

/**
 * Post-install script for NLSQL MCP Server
 * 
 * This script runs after npm install to set up Python dependencies
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');

async function installPythonDependencies() {
    console.log(chalk.blue('🐍 Setting up Python dependencies for NLSQL MCP Server...'));

    // Detect Python executable
    const pythonExecutables = ['python3', 'python', 'py'];
    let pythonCmd = null;

    for (const cmd of pythonExecutables) {
        try {
            await new Promise((resolve, reject) => {
                const testProcess = spawn(cmd, ['--version'], { stdio: 'pipe' });
                testProcess.on('close', (code) => {
                    if (code === 0) {
                        pythonCmd = cmd;
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

    if (!pythonCmd) {
        console.warn(chalk.yellow('⚠️  Python not found. Please install Python 3.8+ manually.'));
        console.log(chalk.gray('   You can install Python dependencies later with: npm run install-python-deps'));
        return;
    }

    console.log(chalk.green(`✅ Found Python: ${pythonCmd}`));

    // Check if requirements.txt exists
    const requirementsPath = path.join(__dirname, '..', 'python-src', 'requirements.txt');
    
    if (!fs.existsSync(requirementsPath)) {
        console.log(chalk.yellow('⚠️  Requirements file not found. Creating minimal requirements...'));
        
        // Create basic requirements if not exists
        const basicRequirements = `mcp>=1.0.0
crewai>=0.22.0
sqlalchemy>=2.0.0
pandas>=1.5.0
openai>=1.0.0
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
pymysql>=1.0.0
cryptography>=41.0.0`;

        fs.writeFileSync(requirementsPath, basicRequirements);
        console.log(chalk.green('✅ Created requirements.txt'));
    }

    // Install Python dependencies
    try {
        console.log(chalk.blue('📦 Installing Python packages...'));
        
        // First install nl2sql dependencies if available
        const nl2sqlRequirementsPath = path.join(__dirname, '..', 'nl2sql', 'requirements.txt');
        if (fs.existsSync(nl2sqlRequirementsPath)) {
            console.log(chalk.blue('📦 Installing nl2sql dependencies...'));
            await new Promise((resolve, reject) => {
                const nl2sqlInstallProcess = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', nl2sqlRequirementsPath], {
                    stdio: 'inherit'
                });

                nl2sqlInstallProcess.on('close', (code) => {
                    if (code === 0) {
                        resolve();
                    } else {
                        reject(new Error(`nl2sql pip install failed with code ${code}`));
                    }
                });

                nl2sqlInstallProcess.on('error', (err) => {
                    reject(new Error(`Failed to run pip for nl2sql: ${err.message}`));
                });
            });
            console.log(chalk.green('✅ nl2sql dependencies installed successfully!'));
        }
        
        // Then install MCP server dependencies
        await new Promise((resolve, reject) => {
            const installProcess = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', requirementsPath], {
                stdio: 'inherit'
            });

            installProcess.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`pip install failed with code ${code}`));
                }
            });

            installProcess.on('error', (err) => {
                reject(new Error(`Failed to run pip: ${err.message}`));
            });
        });

        console.log(chalk.green('✅ MCP server dependencies installed successfully!'));

    } catch (error) {
        console.warn(chalk.yellow(`⚠️  Failed to install Python dependencies: ${error.message}`));
        console.log(chalk.gray('   You can install them manually with:'));
        console.log(chalk.gray(`   ${pythonCmd} -m pip install -r ${requirementsPath}`));
    }
}

async function downloadPythonSource() {
    console.log(chalk.blue('📥 Setting up Python source code...'));

    const pythonSrcDir = path.join(__dirname, '..', 'python-src');
    const nl2sqlDir = path.join(__dirname, '..', 'nl2sql');
    
    // Create python-src directory if it doesn't exist
    if (!fs.existsSync(pythonSrcDir)) {
        fs.mkdirSync(pythonSrcDir, { recursive: true });
    }

    // Check if we need to copy/download the Python source
    const serverPath = path.join(pythonSrcDir, 'nlsql_mcp_server', 'server.py');
    
    if (!fs.existsSync(serverPath)) {
        console.log(chalk.yellow('⚠️  Python source not found.'));
        console.log(chalk.gray('   The Python source should be included in the npm package.'));
        console.log(chalk.gray('   If you\'re running from source, copy the src/ directory to python-src/'));
        return false;
    }

    // Check if nl2sql is available
    if (!fs.existsSync(nl2sqlDir)) {
        console.log(chalk.yellow('⚠️  nl2sql application not found.'));
        console.log(chalk.gray('   Downloading nl2sql from GitHub...'));
        
        try {
            const { spawn } = require('child_process');
            await new Promise((resolve, reject) => {
                const gitProcess = spawn('git', ['submodule', 'update', '--init', '--recursive'], {
                    cwd: path.join(__dirname, '..'),
                    stdio: 'inherit'
                });
                
                gitProcess.on('close', (code) => {
                    if (code === 0) resolve();
                    else reject(new Error(`Git submodule update failed with code ${code}`));
                });
                
                gitProcess.on('error', reject);
            });
            
            console.log(chalk.green('✅ nl2sql downloaded successfully'));
        } catch (error) {
            console.warn(chalk.yellow(`⚠️  Failed to download nl2sql: ${error.message}`));
            console.log(chalk.gray('   You may need to install nl2sql manually.'));
        }
    } else {
        console.log(chalk.green('✅ nl2sql application found'));
    }

    console.log(chalk.green('✅ Python source code ready'));
    return true;
}

async function main() {
    try {
        console.log(chalk.blue.bold('🚀 NLSQL MCP Server Post-Install Setup\n'));

        // Setup Python source
        const sourceReady = await downloadPythonSource();
        
        if (sourceReady) {
            // Install Python dependencies
            await installPythonDependencies();
        }

        console.log(chalk.green.bold('\n🎉 Setup complete!'));
        console.log(chalk.gray('   Run: npx nlsql-mcp-server start'));
        console.log(chalk.gray('   Or:  npm start'));

    } catch (error) {
        console.error(chalk.red(`❌ Setup failed: ${error.message}`));
        process.exit(1);
    }
}

// Only run if this script is executed directly
if (require.main === module) {
    main();
}

module.exports = { installPythonDependencies, downloadPythonSource };