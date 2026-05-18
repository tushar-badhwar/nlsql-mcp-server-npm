#!/usr/bin/env node

/**
 * Python environment setup for the NLSQL MCP Server.
 *
 * CrewAI requires Python >=3.10,<3.14. The user's default `python3` is often
 * incompatible (Homebrew now defaults to 3.14), so we probe for a compatible
 * interpreter and build a dedicated virtualenv inside the package. This also
 * sidesteps PEP 668 ("externally-managed-environment"), which blocks system
 * pip installs on modern macOS/Debian.
 *
 * Hybrid mode: this script never hard-fails `npm install`. If setup can't
 * complete (no compatible Python, no network), the package still installs and
 * `nlsql-mcp-server start` self-heals on first run.
 */

const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');

const PKG_ROOT = path.join(__dirname, '..');
const VENV_DIR = path.join(PKG_ROOT, '.venv');
const REQ_FILE = path.join(PKG_ROOT, 'python-src', 'requirements-runtime.txt');
const READY_MARKER = path.join(VENV_DIR, '.nlsql-ready');

// CrewAI: Requires-Python >=3.10,<3.14
const MIN_MINOR = 10;
const MAX_MINOR = 13;

function venvPython() {
    return process.platform === 'win32'
        ? path.join(VENV_DIR, 'Scripts', 'python.exe')
        : path.join(VENV_DIR, 'bin', 'python');
}

function pyMinor(cmd, args = []) {
    const probe = spawnSync(
        cmd,
        [...args, '-c', 'import sys;print("%d.%d"%sys.version_info[:2])'],
        { encoding: 'utf8' }
    );
    if (probe.status !== 0 || !probe.stdout) return null;
    const m = probe.stdout.trim().match(/^3\.(\d+)$/);
    return m ? parseInt(m[1], 10) : null;
}

function findCompatiblePython() {
    const candidates = [
        ['python3.13'], ['python3.12'], ['python3.11'], ['python3.10'],
    ];
    if (process.platform === 'win32') {
        candidates.push(['py', '-3.13'], ['py', '-3.12'], ['py', '-3.11'], ['py', '-3.10']);
    }
    for (const [cmd, ...args] of candidates) {
        const minor = pyMinor(cmd, args);
        if (minor !== null && minor >= MIN_MINOR && minor <= MAX_MINOR) {
            return { cmd, args };
        }
    }
    // Generic fallbacks, only if they happen to be in range
    for (const cmd of ['python3', 'python']) {
        const minor = pyMinor(cmd);
        if (minor !== null && minor >= MIN_MINOR && minor <= MAX_MINOR) {
            return { cmd, args: [] };
        }
    }
    return null;
}

function isVenvReady() {
    return fs.existsSync(venvPython()) && fs.existsSync(READY_MARKER);
}

function run(cmd, args, opts = {}) {
    return new Promise((resolve, reject) => {
        const p = spawn(cmd, args, { stdio: 'inherit', ...opts });
        p.on('close', (code) =>
            code === 0 ? resolve() : reject(new Error(`${path.basename(cmd)} exited with code ${code}`))
        );
        p.on('error', reject);
    });
}

async function buildVenv(py) {
    const display = [py.cmd, ...py.args].join(' ');
    console.error(chalk.green(`✅ Using ${display} (CrewAI-compatible: 3.${MIN_MINOR}–3.${MAX_MINOR})`));

    // Recreate cleanly so a half-built venv from a prior failed run can't poison this one.
    if (fs.existsSync(VENV_DIR)) {
        fs.rmSync(VENV_DIR, { recursive: true, force: true });
    }

    console.error(chalk.blue(`🐍 Creating virtualenv → ${VENV_DIR}`));
    await run(py.cmd, [...py.args, '-m', 'venv', VENV_DIR]);

    const vpy = venvPython();
    console.error(chalk.blue('📦 Upgrading pip'));
    await run(vpy, ['-m', 'pip', 'install', '--quiet', '--upgrade', 'pip']);

    console.error(chalk.blue('📦 Installing Python dependencies (slim runtime set; a few minutes)'));
    await run(vpy, ['-m', 'pip', 'install', '-r', REQ_FILE]);

    fs.writeFileSync(
        READY_MARKER,
        JSON.stringify({ builtAt: new Date().toISOString(), python: display }) + '\n'
    );
    console.error(chalk.green.bold('✅ Python environment ready'));
}

function printNoPythonHelp() {
    console.error(chalk.yellow.bold('\n⚠️  No CrewAI-compatible Python found (need 3.10–3.13).'));
    console.error(chalk.gray('   CrewAI does not support Python 3.14+ yet.'));
    console.error(chalk.gray('   Install a compatible interpreter, then re-run setup:\n'));
    console.error(chalk.cyan('     macOS:   brew install python@3.13'));
    console.error(chalk.cyan('     Ubuntu:  sudo apt install python3.13 python3.13-venv'));
    console.error(chalk.cyan('     Windows: winget install Python.Python.3.13\n'));
    console.error(chalk.gray('   Then:    npx nlsql-mcp-server install-deps\n'));
}

async function ensureSetup() {
    if (isVenvReady()) return true;

    const py = findCompatiblePython();
    if (!py) {
        printNoPythonHelp();
        return false;
    }
    try {
        await buildVenv(py);
        return true;
    } catch (e) {
        console.error(chalk.yellow(`\n⚠️  Setup did not complete: ${e.message}`));
        console.error(chalk.gray('   Retry anytime with: npx nlsql-mcp-server install-deps\n'));
        return false;
    }
}

async function main() {
    console.error(chalk.blue.bold('🚀 NLSQL MCP Server — Python setup\n'));

    if (!fs.existsSync(REQ_FILE)) {
        console.error(chalk.red(`❌ Requirements file missing: ${REQ_FILE}`));
        process.exit(0); // hybrid: do not fail npm install
    }

    const ok = await ensureSetup();
    if (ok) {
        console.error(chalk.green.bold('\n🎉 Setup complete.'));
        console.error(chalk.gray('   Run: npx nlsql-mcp-server start'));
    } else {
        console.error(chalk.yellow.bold('\n⚠️  Setup incomplete — package installed, Python deps NOT ready.'));
        console.error(chalk.gray('   It will retry on first `start`, or run: npx nlsql-mcp-server install-deps'));
    }
    // Hybrid: npm install always succeeds; runtime self-heals.
    process.exit(0);
}

if (require.main === module) {
    main();
}

module.exports = {
    ensureSetup,
    isVenvReady,
    venvPython,
    findCompatiblePython,
    buildVenv,
    VENV_DIR,
};
