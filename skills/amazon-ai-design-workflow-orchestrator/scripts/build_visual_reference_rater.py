"""Render stable purpose-specific reference ratings and search-again controls."""
from __future__ import annotations

import argparse
import base64
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_discovery import POOL, PENDING, asset_path, digest, read_json, validate_pool
from design_workflow_state import workflow_version_tuple


def legacy_pool(root: Path, pool_path: Path) -> bool:
    pool = read_json(pool_path)
    active_path = root / "active_run.json"
    active = read_json(active_path) if active_path.exists() else {}
    version = str(active.get("workflow_version", ""))
    parsed_version = workflow_version_tuple(version)
    requires_v2 = parsed_version is not None and parsed_version >= (0, 7, 0)
    return pool.get("version") != 2 and not requires_v2


def render_fragment(root: Path, pool_path: Path, title: str) -> str:
    from PIL import Image, ImageOps
    pool = read_json(pool_path)
    errors = validate_pool(pool, root)
    if errors:
        raise ValueError("; ".join(errors))
    if pool.get("status") != "PENDING_RATING":
        raise ValueError("build a new pending pool before showing its rating page")
    cards = []
    for sample in pool["samples"]:
        card = {k: sample.get(k) for k in ("id", "project", "project_url", "purposes", "visual", "layout")}
        card["images"] = []
        for evidence in sample["evidence"]:
            with Image.open(asset_path(root, evidence["path"])) as original:
                img = ImageOps.exif_transpose(original).convert("RGB")
                img.thumbnail((1000, 900))
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=67, optimize=True)
            card["images"].append({"purpose": evidence["purpose"], "src": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()})
        cards.append(card)
    payload = dict(title=title, round=pool["round"], reference_pool_sha256=digest(pool_path), cards=cards)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    fragment = TEMPLATE.replace("__DATA__", encoded)
    if len(fragment.encode()) >= 999_000:
        raise ValueError("rating page exceeds 1 MB; show fewer candidates/images without making typography unreadable")
    return fragment


TEMPLATE = '''<section id="reference-rater">
<style>
#reference-rater{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#25332f;background:#f6f7f4;padding:24px;box-sizing:border-box;max-width:1280px;margin:auto}
#reference-rater *{box-sizing:border-box}#reference-rater h1{font-size:25px;margin:0 0 6px}#reference-rater p{margin:4px 0 18px;color:#52645c}
#reference-rater .cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}#reference-rater article{padding:16px;background:white;border:1px solid #dbe3dd;border-radius:14px;min-width:0}
#reference-rater h2{font-size:17px;margin:0 0 4px}#reference-rater a{color:#38614d;font-size:13px}
#reference-rater .images{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}#reference-rater .images:has(>button:only-child){grid-template-columns:1fr}
#reference-rater button{font:inherit;cursor:pointer;border:1px solid #c6d3cb;border-radius:8px;padding:7px 12px;color:#25332f;background:white}
#reference-rater .image{padding:0;border:0;overflow:hidden;background:#f1f3ef}#reference-rater img{width:100%;height:200px;object-fit:contain;display:block}
#reference-rater .axis{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:10px}#reference-rater .axis span{min-width:62px;font-weight:600}
#reference-rater button[aria-pressed="true"]{background:#254e3d;color:white;border-color:#254e3d}#reference-rater button:focus-visible{outline:3px solid #dda951;outline-offset:2px}
#reference-rater .actions{position:sticky;bottom:0;margin-top:20px;padding:16px;background:#f6f7f4f5;border-top:1px solid #dbe3dd;display:flex;gap:10px;flex-wrap:wrap}
#reference-rater .primary{background:#254e3d;color:white}#reference-rater button:disabled{opacity:.4;cursor:default}
#reference-rater textarea{width:100%;min-height:190px;font:12px/1.5 monospace}#reference-rater [hidden]{display:none!important}
#reference-rater dialog{border:0;border-radius:12px;max-width:94vw;max-height:94vh;padding:12px}#reference-rater dialog img{width:auto;max-width:88vw;height:auto;max-height:80vh}#reference-rater dialog::backdrop{background:#10291dcc}
#reference-rater .status{font-size:13px;color:#52645c;margin-top:12px}#reference-rater .copy{margin-top:8px}
@media(max-width:680px){#reference-rater{padding:14px}.cards{grid-template-columns:1fr!important}#reference-rater .actions{position:static}#reference-rater img{height:175px}}
</style>
<h1></h1><p>只评价你看到的用途，无需填写理由。点击图片可放大。</p>
<div class="cards"></div><div class="status" role="status" aria-live="polite"></div>
<div class="actions"><button class="primary" data-action="CONTINUE">采用这些偏好，继续</button><button data-action="RESEARCH_REJECTED">保留喜欢的，其余换一批</button><button data-action="RESEARCH_ALL">都不合适，换一批</button></div>
<div class="fallback" hidden><p>自动提交不可用，复制结果发回当前对话即可。</p><textarea readonly aria-label="参考选择结果"></textarea><button class="copy">复制结果</button></div>
<dialog><button class="close">关闭大图</button><img alt="参考大图"></dialog>
<script>
(()=>{const data=__DATA__;const root=document.getElementById('reference-rater');root.querySelector('h1').textContent=data.title;
const labels={visual:'画面',layout:'排版'}, choices=[[1,'喜欢'],[0,'一般'],[-1,'不喜欢']];
const ratings=Object.fromEntries(data.cards.map(c=>[c.id,{visual:c.visual??null,layout:c.layout??null}]));
const key='amazon-reference:'+data.reference_pool_sha256;let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
for(const c of data.cards)for(const a of c.purposes){const v=saved[c.id]?.[a];if([-1,0,1].includes(v))ratings[c.id][a]=v}
const dialog=root.querySelector('dialog');root.querySelector('.close').onclick=()=>dialog.close();
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
for(const card of data.cards){const article=document.createElement('article');article.dataset.id=card.id;const h=document.createElement('h2');h.textContent=card.id+' · '+card.project;article.append(h);
const link=document.createElement('a');link.href=card.project_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='查看原项目';article.append(link);
const gallery=document.createElement('div');gallery.className='images';for(const pic of card.images){const b=document.createElement('button');b.className='image';b.setAttribute('aria-label','放大'+labels[pic.purpose]+'参考');const img=document.createElement('img');img.src=pic.src;img.alt=card.project+' · '+labels[pic.purpose];b.append(img);b.onclick=()=>{dialog.querySelector('img').src=pic.src;dialog.showModal()};gallery.append(b)}article.append(gallery);
for(const axis of card.purposes){const row=document.createElement('div');row.className='axis';const label=document.createElement('span');label.textContent=labels[axis];row.append(label);for(const [value,text]of choices){const b=document.createElement('button');b.dataset.axis=axis;b.dataset.value=value;b.textContent=text;b.setAttribute('aria-pressed',String(ratings[card.id][axis]===value));b.onclick=()=>{ratings[card.id][axis]=value;for(const sibling of row.querySelectorAll('button'))sibling.setAttribute('aria-pressed',String(Number(sibling.dataset.value)===value));update()};row.append(b)}article.append(row)}root.querySelector('.cards').append(article)}
function update(){let completed=0,total=0;for(const c of data.cards)for(const a of c.purposes){total++;if(ratings[c.id][a]!==null)completed++}root.querySelector('[data-action="CONTINUE"]').disabled=completed!==total;root.querySelector('.status').textContent='已完成 '+completed+' / '+total+' 项选择 · 第 '+data.round+' 批';try{localStorage.setItem(key,JSON.stringify(ratings))}catch(e){}}
function payload(action){return{rater_contract_version:2,reference_pool_sha256:data.reference_pool_sha256,round:data.round,action,ratings:data.cards.map(c=>({id:c.id,visual:ratings[c.id].visual,layout:ratings[c.id].layout}))}}
async function submit(action){const result=payload(action);const followup='这是正式版参考选择结果。请用 stable reference_discovery.py submit 处理；换批时先重新搜索，无需我补充理由。\\n'+JSON.stringify(result);try{if(!window.openai?.sendFollowUpMessage)throw Error('unavailable');await window.openai.sendFollowUpMessage({prompt:followup,title:'提交参考选择'});root.querySelector('.status').textContent='已提交到当前对话'}catch(e){root.querySelector('textarea').value=JSON.stringify(result,null,2);root.querySelector('.fallback').hidden=false;root.querySelector('.status').textContent='选择已整理，请复制结果发回当前对话'}}
for(const button of root.querySelectorAll('[data-action]'))button.onclick=()=>submit(button.dataset.action);
root.querySelector('.copy').onclick=async()=>{const t=root.querySelector('textarea');try{await navigator.clipboard.writeText(t.value);root.querySelector('.copy').textContent='已复制'}catch(e){t.focus();t.select();root.querySelector('.status').textContent='结果已选中，请复制'}};update();
})();
</script></section>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="主图 A+ 正式版参考选择")
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    pool_path = args.pool.expanduser().resolve() if args.pool else root / POOL
    try:
        if pool_path != root / POOL:
            raise ValueError("--pool must be the current project's visual_reference_pool.json")
        if legacy_pool(root, pool_path):
            import subprocess
            return subprocess.call([sys.executable, str(Path(__file__).with_name("build_visual_reference_rater_legacy.py")), *sys.argv[1:]])
        fragment = render_fragment(root, pool_path, args.title)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(fragment, encoding="utf-8")
        shutil.copyfile(pool_path, root / PENDING)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps({"output": str(args.output.resolve()), "bytes": len(fragment.encode()), "rater_contract_version": 2}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
