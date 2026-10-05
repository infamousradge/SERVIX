import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve('web');
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'};
http.createServer((req,res)=>{
  const pathname=(req.url||'/').split('?')[0];
  let file=path.join(root, pathname==='/'?'index.html':pathname);
  if(!file.startsWith(root)){res.writeHead(403); return res.end('Forbidden');}
  if(!fs.existsSync(file)) file=path.join(root,'index.html');
  res.writeHead(200, {'Content-Type':types[path.extname(file)]||'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
}).listen(4173,'127.0.0.1',()=>console.log('SERVIX preview: http://127.0.0.1:4173'));
