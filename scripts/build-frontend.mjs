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
await copyFile(path.join(root, 'src', 'fonts.css'), path.join(web, 'assets', 'fonts.css'));
await copyFile(path.join(root, 'src', 'brand.css'), path.join(web, 'assets', 'brand.css'));
await copyFile(path.join(root, 'src', 'detail.css'), path.join(web, 'assets', 'detail.css'));
await copyFile(path.join(root, 'src', 'refinements.css'), path.join(web, 'assets', 'refinements.css'));
await copyFile(path.join(root, 'src', 'scale100.css'), path.join(web, 'assets', 'scale100.css'));
await copyFile(reactUmd, path.join(web, 'assets', 'vendor', 'react.production.min.js'));
await copyFile(reactDomUmd, path.join(web, 'assets', 'vendor', 'react-dom.production.min.js'));

const sidebarLogo = path.join(root, 'assets', 'logo-transparent.png');
const loginMark = path.join(root, 'assets', 'login-mark-generated.png');
if (!existsSync(sidebarLogo) || !existsSync(loginMark)) {
  console.error('Prepared SERVIX locked logo assets are missing. Run the brand preparation step first.');
  process.exit(1);
}
await copyFile(sidebarLogo, path.join(web, 'assets', 'servix-sidebar-logo.png'));
await copyFile(loginMark, path.join(web, 'assets', 'servix-login-mark.png'));

const manropeSource = path.join(root, 'assets', 'Manrope-wght.ttf');
if (!existsSync(manropeSource)) {
  console.error('Bundled Manrope font is missing. Run the brand preparation step first.');
  process.exit(1);
}
await copyFile(manropeSource, path.join(web, 'assets', 'manrope.ttf'));

console.log('SERVIX frontend built at web/.');
