"""Static API reference inventory; never treats a code mention as executed evidence."""
import argparse,html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def audit():
    folder=ROOT/'work/api-2026'
    if not folder.is_dir():raise ValueError('Extracted local 2026 API help is required')
    documented={}
    for path in sorted(folder.glob('c_*.html')):
        match=re.search(r'<title>(.*?)</title>',path.read_text(encoding='utf8',errors='replace'),re.I|re.S)
        if match:
            name=html.unescape(match.group(1)).strip()
            if name.startswith('c:'):documented[name.casefold()]={'name':name,'help_file':path.relative_to(ROOT).as_posix(),'mentions':[]}
    for base in ['src','scripts']:
        for path in sorted((ROOT/base).rglob('*.py')):
            if path.name==Path(__file__).name:continue
            for lineno,line in enumerate(path.read_text(encoding='utf8').splitlines(),1):
                for name in set(re.findall(r'c:[A-Za-z][A-Za-z0-9_]*',line)):
                    if name.casefold() in documented:
                        documented[name.casefold()]['mentions'].append({'file':path.relative_to(ROOT).as_posix(),'line':lineno})
    tools=json.loads((ROOT/'profiles/tool-capabilities.json').read_text(encoding='utf8'))['tools']
    return {'scope':'Extracted c: AutoLISP help entries only; excludes general AutoCAD ActiveX/.NET/ObjectARX and other Lisp entrypoints',
            'interpretation':'Static text mentions include comments and scripts, not call logs or acceptance; absence does not prove never called',
            'documented_entries':len(documented),'entries_mentioned_in_code':sum(bool(v['mentions']) for v in documented.values()),
            'tool_definitions':len(tools),'default_tools':sum(v['default_enabled'] for v in tools.values()),
            'apis':list(documented.values())}

def tool_inventory():
    tools=json.loads((ROOT/'profiles/tool-capabilities.json').read_text(encoding='utf8'))['tools']
    count=sum(v['default_enabled'] for v in tools.values())
    lines=['# 全工具验收清单','',f'{len(tools)}个工具定义：{count}个默认提供，{len(tools)-count}个默认隐藏。默认开放不等于全参数范围验收。','',
           '由 profiles/tool-capabilities.json 生成；更新命令：python -m scripts.audit_api_coverage --write。API与技能对应关系见 [覆盖审计](api-skill-coverage.md)。','',
           '| 工具 | 默认提供 | 状态/范围 | 缺口/替代 | 证据 |','| --- | --- | --- | --- | --- |']
    def cell(value):return str(value or '').replace('|',r'\|').replace('\n',' ')
    for name,item in tools.items():
        lines.append('| '+' | '.join(map(cell,[name,'是' if item['default_enabled'] else '否',item['status']+' / '+item.get('scope',''),item.get('issue') or item.get('replacement'),item.get('evidence')]))+' |')
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    result=audit()
    if args.write:
        out=ROOT/'work/acceptance/api-coverage';out.mkdir(parents=True,exist_ok=True)
        (out/'static-api-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        (ROOT/'docs/tool-inventory.md').write_text(tool_inventory(),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='apis'},ensure_ascii=True,indent=2))
