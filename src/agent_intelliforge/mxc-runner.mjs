// Official MXC V1 SDK; no audit/process backend or unrestricted fallback.
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { finished } from 'node:stream/promises';

const file = process.argv[2];
let child;
try {
  const profile = JSON.parse(fs.readFileSync(file, 'utf8'));
  fs.unlinkSync(file);
  const sdk = await import(pathToFileURL(profile.sdk).href);
  const containment = { type: process.platform === 'win32' ? 'processcontainer' : process.platform === 'darwin' ? 'seatbelt' : 'bubblewrap' };
  // MXC accepts a command line. Each argument is quoted for its native parser,
  // never interpolated into cmd.exe/PowerShell/a shell program.
  const quote = value => process.platform === 'win32'
    ? '"' + value.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\+)$/g, '$1$1') + '"'
    : "'" + value.replaceAll("'", "'\\''") + "'";
  const request = {
    command: profile.argv.map(quote).join(' '),
    workingDirectory: profile.cwd,
    containment,
    filesystem: { readonlyPaths: profile.readonly, readwritePaths: profile.writable },
    network: { egress: { default: profile.network ? 'allow' : 'deny' } },
    timeoutMs: profile.timeoutMs,
    environment: process.env,
    inheritDefaultEnvironment: true,
  };
  if (process.platform === 'win32') {
    const probe = sdk.probe(request);
    if (probe.error || !probe.tier) throw new Error(probe.error || 'MXC ProcessContainer is unavailable; update Windows 11.');
  }
  child = await sdk.spawn(request);
  const input = child.standardInput;
  if (input) process.stdin.pipe(input);
  child.standardOutput?.pipe(process.stdout);
  child.standardError?.pipe(process.stderr);
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { child.kill(); });
  const result = await child.wait();
  await Promise.all([child.standardOutput, child.standardError].filter(Boolean).map(stream => finished(stream)));
  process.exitCode = result.timedOut ? 124 : result.exitCode;
} catch (error) {
  process.stderr.write('MXC isolation failed: ' + error.message + '\n');
  process.exitCode = 2;
} finally {
  child?.dispose();
  if (file && fs.existsSync(file)) fs.unlinkSync(file);
}
