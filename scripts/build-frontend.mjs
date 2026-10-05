import { mkdir, rm, copyFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = path.join(root, 'web');
await rm(web, { recursive: true, force: true });
await mkdir(path.join(web, 'assets', 'vendor'), { recursive: true });

const localTscCli = path.join(root, 'node_modules', 'typescript', 'bin', 'tsc');
if (!existsSync(localTscCli)) {
  console.error('TypeScript is not installed. Run npm ci first.');
  process.exit(1);
}
const typecheck = spawnSync(process.execPath, [localTscCli, '-p', 'tsconfig.json'], { cwd: root, stdio: 'inherit' });
if (typecheck.status !== 0) process.exit(typecheck.status ?? 1);

const reactUmd = path.join(root, 'node_modules', 'react', 'umd', 'react.production.min.js');
const reactDomUmd = path.join(root, 'node_modules', 'react-dom', 'umd', 'react-dom.production.min.js');
if (!existsSync(reactUmd) || !existsSync(reactDomUmd)) {
  console.error('React UMD runtime files are missing. Run npm ci with React 18.3.1.');
  process.exit(1);
}

await copyFile(path.join(root, 'index.html'), path.join(web, 'index.html'));
await copyFile(path.join(root, 'src', 'styles.css'), path.join(web, 'assets', 'app.css'));
await copyFile(path.join(root, 'src', 'brand.css'), path.join(web, 'assets', 'brand.css'));
await copyFile(path.join(root, 'src', 'detail.css'), path.join(web, 'assets', 'detail.css'));
await copyFile(reactUmd, path.join(web, 'assets', 'vendor', 'react.production.min.js'));
await copyFile(reactDomUmd, path.join(web, 'assets', 'vendor', 'react-dom.production.min.js'));
const logoSource = path.join(root, 'assets', 'logo.png');
if (existsSync(logoSource)) await copyFile(logoSource, path.join(web, 'assets', 'servix-logo.png'));
console.log('SERVIX frontend built at web/.');
