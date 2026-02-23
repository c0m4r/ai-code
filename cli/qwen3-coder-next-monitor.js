#!/usr/bin/env node

const readline = require('readline');
const fs = require('fs');
const path = require('path');
const os = require('os');

// --- Constants & Config ---
const UPDATE_INTERVAL_MS = 1000;
const HISTORY_LENGTH = 40;

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
};

const ASCII_LOGO = `
   ______ _           _   _           _ _ 
  |  ____| |         | | (_)         | | |
  | |__  | | ___  ___| |_ _ _ __ ___ | | |
  |  __| | |/ _ \\/ __| __| | '_ \` _ \\| | |
  | |____| |  __/\\__ \\ |_| | | | | | |_|_|
  |______|_|\\___||___/\\__|_|_| |_| |_|_(_)
`;

// --- Helper Functions ---

function color(str, colorCode) {
  return `${colorCode}${str}${COLORS.reset}`;
}

function bright(str) {
  return color(str, COLORS.bright);
}

function getHostname() {
  try {
    return fs.readFileSync('/etc/hostname', 'utf8').trim();
  } catch (e) {
    return 'unknown';
  }
}

function getUptime() {
  const uptimeSeconds = os.uptime();
  const days = Math.floor(uptimeSeconds / 86400);
  const hours = Math.floor((uptimeSeconds % 86400) / 3600);
  const minutes = Math.floor((uptimeSeconds % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
}

function getDateTime() {
  const now = new Date();
  return now.toLocaleString();
}

// --- CPU Monitoring ---
function readCpuStats() {
  const contents = fs.readFileSync('/proc/stat', 'utf8');
  const lines = contents.split('\n');
  const cpuLine = lines.find(line => line.startsWith('cpu '));
  if (!cpuLine) return null;

  const [, user, nice, system, idle, iowait, irq, softirq, steal] = cpuLine.split(/\s+/);
  const idleTime = Number(idle) + Number(iowait);
  const totalTime = Number(user) + Number(nice) + Number(system) + Number(idle) + Number(iowait) + Number(irq) + Number(softirq) + Number(steal);

  return { idleTime, totalTime };
}

let prevCpuStats = readCpuStats();
function getCpuUsage() {
  const current = readCpuStats();
  if (!prevCpuStats || !current) return 0;

  const idleDiff = current.idleTime - prevCpuStats.idleTime;
  const totalDiff = current.totalTime - prevCpuStats.totalTime;
  const usage = totalDiff === 0 ? 0 : (1 - (idleDiff / totalDiff)) * 100;

  prevCpuStats = current;
  return Math.min(Math.round(usage), 100); // clamp to 100
}

// --- Memory & Swap Monitoring ---
function getMemoryInfo() {
  const meminfo = {};
  const contents = fs.readFileSync('/proc/meminfo', 'utf8');
  const lines = contents.split('\n');
  
  for (const line of lines) {
    const [key, value, unit] = line.split(/\s+/);
    if (key && value) {
      meminfo[key.replace(':', '')] = Number(value) * 1024; // Convert from kB to B
    }
  }

  const totalMem = meminfo.MemTotal || 0;
  const freeMem = meminfo.MemFree || 0;
  const availableMem = meminfo.MemAvailable || freeMem;
  const usedMem = totalMem - availableMem;
  const memPercent = totalMem === 0 ? 0 : (usedMem / totalMem) * 100;

  const totalSwap = meminfo.SwapTotal || 0;
  const freeSwap = meminfo.SwapFree || 0;
  const usedSwap = totalSwap - freeSwap;
  const swapPercent = totalSwap === 0 ? 0 : (usedSwap / totalSwap) * 100;

  return {
    mem: { total: totalMem, used: usedMem, percent: memPercent },
    swap: { total: totalSwap, used: usedSwap, percent: swapPercent },
  };
}

// --- Load Average ---
function getLoadAverage() {
  const lavg = os.loadavg();
  return lavg.map(x => Math.round(x * 100) / 100);
}

// --- Network Monitoring (Real-time Mbps) ---
let prevNetStats = {};
function getNetworkUsage() {
  const lines = fs.readFileSync('/proc/net/dev', 'utf8').split('\n').slice(2); // skip header lines
  let totalDownload = 0;
  let totalUpload = 0;

  for (const line of lines) {
    const parts = line.trim().split(/[:\s]+/);
    if (parts.length < 11) continue;

    const interfaceName = parts[0];
    if (interfaceName === 'lo') continue; // skip loopback

    const rxBytes = Number(parts[1]);
    const txBytes = Number(parts[9]);

    totalDownload += rxBytes;
    totalUpload += txBytes;
  }

  const now = Date.now();
  let dlMbps = 0, ulMbps = 0;

  if (prevNetStats.totalDownload !== undefined && prevNetStats.totalUpload !== undefined) {
    const timeDiffSeconds = (now - prevNetStats.time) / 1000;
    if (timeDiffSeconds > 0) {
      const dlDiff = totalDownload - prevNetStats.totalDownload;
      const ulDiff = totalUpload - prevNetStats.totalUpload;
      dlMbps = (dlDiff * 8) / (1024 * 1024) / timeDiffSeconds;
      ulMbps = (ulDiff * 8) / (1024 * 1024) / timeDiffSeconds;
    }
  }

  prevNetStats = { totalDownload, totalUpload, time: now };
  return { dl: dlMbps, ul: ulMbps };
}

// --- CLI UI Rendering ---
function render() {
  // Clear screen and move cursor to top-left
  process.stdout.write('\x1Bc'); // reset terminal
  process.stdout.write('\x1b[2J');
  process.stdout.write('\x1b[3J');
  process.stdout.write('\x1b[H');

  // Print Header
  console.log(bright(ASCII_LOGO));
  console.log(`  ${color('Hostname:', COLORS.cyan)} ${bright(getHostname())}            ${color('Kernel:', COLORS.cyan)} ${os.release()}`);
  console.log(`  ${color('Time:', COLORS.cyan)} ${bright(getDateTime())}        ${color('Uptime:', COLORS.cyan)} ${bright(getUptime())}`);
  console.log('');

  // CPU Section
  const cpu = getCpuUsage();
  const cpuBar = generateBar(cpu, 100, COLORS.green, COLORS.red);
  console.log(`  ${color('[CPU]', COLORS.bright)} ${cpuBar} ${cpu}%`);

  // Memory Section
  const { mem, swap } = getMemoryInfo();
  const memBar = generateBar(mem.percent, 100, COLORS.green, COLORS.red);
  console.log(`  ${color('[RAM]', COLORS.bright)} ${memBar} ${Math.round(mem.percent)}% ${color(formatBytes(mem.used), COLORS.cyan)} / ${color(formatBytes(mem.total), COLORS.cyan)}`);

  // Swap Section
  const swapBar = swap.total > 0 ? generateBar(swap.percent, 100, COLORS.green, COLORS.yellow) : generateBar(0, 100, COLORS.green, COLORS.green);
  console.log(`  ${color('[SWAP]', COLORS.bright)} ${swapBar} ${Math.round(swap.percent)}% ${color(formatBytes(swap.used), COLORS.cyan)} / ${color(formatBytes(swap.total), COLORS.cyan)}`);

  // Load Average Section
  const [l1, l5, l15] = getLoadAverage();
  console.log(`  ${color('[LOAD]', COLORS.bright)} 1m: ${bright(l1)}  |  5m: ${bright(l5)}  |  15m: ${bright(l15)}`);

  // Network Section
  const net = getNetworkUsage();
  console.log(`  ${color('[NET]', COLORS.bright)} DL: ${bright(net.dl.toFixed(2))} Mbps | UP: ${bright(net.ul.toFixed(2))} Mbps`);
  console.log('');
  console.log(color('  Press Ctrl+C to exit.', COLORS.dim));
}

function generateBar(percent, max, colorGood, colorBad) {
  const totalBars = 20;
  const filled = Math.round((percent / max) * totalBars);
  const empty = totalBars - filled;
  let bar = '';
  
  // Threshold logic
  if (percent < 50) bar += color('█'.repeat(filled), colorGood);
  else if (percent < 80) bar += color('█'.repeat(filled), COLORS.yellow);
  else bar += color('█'.repeat(filled), colorBad);

  bar += color('░'.repeat(empty), COLORS.dim);
  return bar;
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// --- Main Loop ---
function init() {
  // Initial CPU stats calculation (seed)
  readCpuStats();
  
  setInterval(render, UPDATE_INTERVAL_MS);
  
  // Ensure first render happens immediately
  render();
  
  // Handle Ctrl+C properly
  process.on('SIGINT', () => {
    console.log('\nExiting monitoring tool...');
    process.exit(0);
  });
}

init();