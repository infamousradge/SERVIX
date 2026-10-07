import fs from 'node:fs';import vm from 'node:vm';import ts from 'typescript';import assert from 'node:assert/strict';
const code=fs.readFileSync('src/data-tools.tsx','utf8');const context=vm.createContext({React:{},console});vm.runInContext(ts.transpileModule(code,{compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2019}}).outputText,context);
const parse=s=>JSON.parse(JSON.stringify(vm.runInContext(`parseCsv(${JSON.stringify(s)})`,context)));
assert.deepEqual(parse('\uFEFFcode,name,note\r\nC1,"Smith, Inc","line one\nline two ""quoted"""\r\n'),[['code','name','note'],['C1','Smith, Inc','line one\nline two "quoted"']]);
for(const invalid of ['a,a\n1,2','a,b\n1','a,b\n"unclosed,2','a,b\n"closed"oops,2','a,b\n1,2,3'])assert.throws(()=>parse(invalid));
assert.equal(parse('a,b\n0,\n\n').length,2);assert(code.includes('setReview(null)'));assert(code.includes('review.errors>0'));console.log('CSV parser checks passed: BOM, CRLF, multiline, quotes, duplicate headers and malformed rows.');
