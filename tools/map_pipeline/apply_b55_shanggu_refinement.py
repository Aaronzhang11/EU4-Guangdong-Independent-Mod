#!/usr/bin/env python3
"""Apply/check the user-approved B55 Shanggu 2-to-5 province split."""
from __future__ import annotations
import argparse,csv,hashlib,json,re,shutil,subprocess,sys,zlib
from collections import deque
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]; MOD=ROOT/"guangdong_independent_practice"; MAP=MOD/"map"; HIST=MOD/"history/provinces"
PLAN=ROOT/"planning/shanggu_refinement_b55"; MASKS=PLAN/"reviewed_masks.json.zlib"; BACKUP=PLAN/"pre_b55/map/provinces.bmp"; MANIFEST=PLAN/"batch_manifest.json"
SOURCE=MOD/"localisation_source/008_gdd_b55_shanggu_refinement_readable_utf8.txt"; TARGET=MOD/"localisation/replace/008_gdd_b55_shanggu_refinement_l_english.yml"
MARKER="GDD_B55_SHANGGU_REFINEMENT"; NEW=(5351,5352,5353); ALL=(703,2136,*NEW)
RGB={5351:(62,177,143),5352:(196,101,70),5353:(88,137,207)}
EN={703:"Rehe",2136:"Shanggu",5351:"Weizhou",5352:"Longmen",5353:"Xingzhou"}; ZH={5351:"蔚州",5352:"龙门",5353:"兴州"}
HISTORY_NAME={703:"Chengde",2136:"Xuanhua",5351:"Weizhou",5352:"Longmen",5353:"Xingzhou"}
DEV={703:(2,2,1),2136:(1,1,1),5351:(1,1,1),5352:(1,1,1),5353:(1,1,1)}
POL={703:("YAN","gdd_yan","vajrayana","livestock"),2136:("ZSH","gdd_jin","confucianism","grain"),5351:("ZSH","gdd_jin","confucianism","grain"),5352:("ZSH","gdd_jin","confucianism","livestock"),5353:("YAN","gdd_yan","vajrayana","livestock")}

def bounds(text,key,start=0):
 m=re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{",text[start:])
 if not m: raise ValueError(f"missing block {key}")
 a=start+m.start(); i=start+m.end()-1; depth=0
 for j in range(i,len(text)):
  depth += (text[j]=="{")-(text[j]=="}")
  if depth==0:return a,j+1
 raise ValueError(f"unbalanced block {key}")
def replace(text,key,value):
 a,b=bounds(text,key);return text[:a]+value+text[b:]
def add_ids(text,key,ids):
 a,b=bounds(text,key);block=text[a:b];indent=re.match(r"[ \t]*",block).group(0);block=re.sub(rf"(?m)^\s*.*# {MARKER}\s*$\n?","",block);i=block.rfind("}")
 block=block[:i].rstrip()+f"\n{indent}    {' '.join(map(str,ids))} # {MARKER}\n{indent}"+block[i:];return text[:a]+block+text[b:]
def add_nested(text,outer,inner,ids):
 a,b=bounds(text,outer);return text[:a]+add_ids(text[a:b],inner,ids)+text[b:]
def defs():
 out={}
 for line in (MAP/"definition.csv").read_text(encoding="cp1252").splitlines()[1:]:
  c=line.split(";");
  if len(c)>3 and c[0].isdigit():out[int(c[0])]=tuple(map(int,c[1:4]))
 return out
def cells():
 data=json.loads(zlib.decompress(MASKS.read_bytes()).decode())
 return data,{int(pid):{(x,y) for y,x0,x1 in c["runs"] for x in range(x0,x1+1)} for pid,c in data["cells"].items()}
def connected(points):
 seen={next(iter(points))};q=deque(seen)
 while q:
  x,y=q.popleft()
  for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   if p in points and p not in seen:seen.add(p);q.append(p)
 return len(seen)==len(points)
def deep(points):
 edge={p for p in points if any(q not in points for q in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)))};d={p:0 for p in edge};q=deque(edge)
 while q:
  p=q.popleft()
  for n in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
   if n in points and n not in d:d[n]=d[p]+1;q.append(n)
 return max(points,key=lambda p:d.get(p,0))
def apply_bitmap():
 rows=defs(); colours={703:rows[703],2136:rows[2136],**RGB};_,cs=cells(); path=MAP/"provinces.bmp";BACKUP.parent.mkdir(parents=True,exist_ok=True)
 if not BACKUP.exists():shutil.copy2(path,BACKUP)
 im=Image.open(path).convert("RGB");px=im.load();allowed=set(colours.values());changed=0
 for pid,points in cs.items():
  for x,y in points:
   if px[x,y] not in allowed:raise ValueError(f"mask escapes locked exterior at {(x,y)}")
   if px[x,y]!=colours[pid]:px[x,y]=colours[pid];changed+=1
 im.save(path,format="BMP");return changed
def update_definition():
 p=MAP/"definition.csv";lines=[l for l in p.read_text(encoding="cp1252").splitlines() if not(l.split(";",1)[0].isdigit() and int(l.split(";",1)[0]) in NEW)]
 for pid in NEW:r,g,b=RGB[pid];lines.append(f"{pid};{r};{g};{b};{EN[pid]};x")
 p.write_text("\n".join(lines)+"\n",encoding="cp1252");p=MAP/"default.map";t,n=re.subn(r"(?m)^max_provinces\s*=\s*\d+","max_provinces = 5354",p.read_text(encoding="cp1252"));assert n==1;p.write_text(t,encoding="cp1252")
def suffix(text):
 m=re.search(r"(?m)^\d+\.\d+\.\d+\s*=\s*\{",text);return text[m.start():].rstrip()+"\n" if m else ""
def history(pid,dated=""):
 owner,culture,religion,goods=POL[pid];tax,prod,man=DEV[pid];extra="add_core = JIN\n" if pid==2136 else ""
 text=f'''# {pid} - {EN[pid]} - {MARKER}\n\nowner = {owner}\ncontroller = {owner}\nadd_core = {owner}\n{extra}culture = {culture}\nreligion = {religion}\ncapital = "{EN[pid]}"\ntrade_goods = {goods}\nhre = no\nbase_tax = {tax}\nbase_production = {prod}\nbase_manpower = {man}\nis_city = yes\ndiscovered_by = chinese\ndiscovered_by = nomad_group\n'''
 path=HIST/f"{pid} - {HISTORY_NAME[pid]}.txt"
 for old in HIST.glob(f"{pid} - *.txt"):
  if old!=path:old.unlink()
 path.write_text(text.rstrip()+("\n\n"+dated if dated else "\n"),encoding="utf-8")
def update_histories():
 old={pid:next(HIST.glob(f"{pid} - *.txt")).read_text(encoding="utf-8-sig") for pid in (703,2136)}
 history(703,suffix(old[703]));history(2136,suffix(old[2136]));[history(pid) for pid in NEW]
def pos_block(pid,x,y):
 pts=" ".join(f"{x:.3f} {y:.3f}" for _ in range(7));return f'''#{EN[pid]} - {MARKER}\n{pid}={{\n    position={{\n        {pts}\n    }}\n    rotation={{\n        0.000 0.000 0.000 0.000 0.000 0.000 0.000\n    }}\n    height={{\n        0.000 0.000 1.000 0.000 0.000 0.000 0.000\n    }}\n}}'''
def update_positions():
 _,cs=cells();h=Image.open(MAP/"provinces.bmp").height;p=MAP/"positions.txt";text=p.read_text(encoding="cp1252");text=re.sub(rf"(?m)^#.* - {MARKER}\n","",text)
 for pid in ALL:
  x,y=deep(cs[pid]);block=pos_block(pid,x,h-y)
  try:a,b=bounds(text,str(pid));text=text[:a]+block+text[b:]
  except ValueError:text=text.rstrip()+"\n\n"+block+"\n"
 p.write_text(text,encoding="cp1252")
def update_memberships():
 p=MAP/"area.txt";p.write_text(replace(p.read_text(encoding="cp1252"),"hebei_area",f"hebei_area = {{ # {MARKER}\n    {' '.join(map(str,ALL))}\n}}"),encoding="cp1252")
 for rel,key in (("map/climate.txt","mild_winter"),("map/continent.txt","asia")):
  p=MOD/rel;p.write_text(add_ids(p.read_text(encoding="cp1252"),key,NEW),encoding="cp1252")
 p=MAP/"terrain.txt";t=p.read_text(encoding="cp1252");t=add_nested(t,"mountain","terrain_override",(5351,5352));t=add_nested(t,"grasslands","terrain_override",(5353,));p.write_text(t,encoding="cp1252")
 p=MOD/"common/tradenodes/00_tradenodes.txt";p.write_text(add_nested(p.read_text(encoding="cp1252"),"beijing","members",NEW),encoding="cp1252")
 p=MOD/"common/trade_companies/00_trade_companies.txt";p.write_text(add_nested(p.read_text(encoding="cp1252"),"trade_company_north_china","provinces",NEW),encoding="cp1252")
def update_localisation():
 lines=["l_english:"]
 for pid in NEW:lines += [f' PROV{pid}:0 "{ZH[pid]}"',f' PROV_ADJ{pid}:0 "{ZH[pid]}"']
 SOURCE.write_text("\n".join(lines)+"\n",encoding="utf-8-sig");sys.path.insert(0,str(ROOT/"tools"));from encode_eu4_chinese_localisation import encode_file,verify_file;encode_file(SOURCE,TARGET);verify_file(SOURCE,TARGET)
def update_cultures():
 p=ROOT/"planning/culture_overhaul/approved_province_culture_assignments.csv"
 with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f));fields=list(rows[0])
 rows=[r for r in rows if int(r["province_id"]) not in NEW]
 for pid in NEW:rows.append(dict(province_id=str(pid),province_name=ZH[pid],document_group="燕晋文化组",document_culture="晋文化" if pid!=5353 else "燕文化",document_entry=ZH[pid],target_culture=POL[pid][1],source_rule="B55",decision_note="继承母省并按上谷—热河文化边界分配"))
 rows.sort(key=lambda r:int(r["province_id"]))
 with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 subprocess.run([sys.executable,str(ROOT/"tools/map_pipeline/apply_culture_overhaul.py")],cwd=ROOT,check=True)
def update_registry():
 p=ROOT/"docs/map/china_province_split_registry.csv"
 with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f));fields=list(rows[0])
 rows=[r for r in rows if r["draw_batch"]!="B55"]
 for i,pid in enumerate(NEW,1):
  parent=2136 if pid<5353 else 703;r={k:"" for k in fields};r.update(design_key=f"B55-{i:02d}",game_id=str(pid),rgb_r=str(RGB[pid][0]),rgb_g=str(RGB[pid][1]),rgb_b=str(RGB[pid][2]),macro_region="north_china",draw_batch="B55",new_name_zh=ZH[pid],new_name_en=EN[pid],internal_key_hint=f"gdd_b55_{pid}",parent_id=str(parent),parent_definition_name="Xuanhua" if parent==2136 else "Chengde",parent_history_name="Shanggu" if parent==2136 else "Rehe",parent_area="hebei_area",new_tax=str(DEV[pid][0]),new_production=str(DEV[pid][1]),new_manpower=str(DEV[pid][2]),proposed_owner=POL[pid][0],status="implemented",rationale="GeoJSON引导；锁定原上谷区域外缘，仅重画内部边界。");rows.append(r)
 with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
def validate():
 data,cs=cells();rows=defs();im=Image.open(MAP/"provinces.bmp").convert("RGB");px=im.load()
 assert sum(map(len,cs.values()))==data["scope_pixels"]==2192 and all(connected(p) for p in cs.values())
 for pid in NEW:
  assert [other for other,colour in rows.items() if colour==rows[pid]]==[pid],f"province {pid} RGB is not unique"
 for pid,points in cs.items():assert all(px[x,y]==rows[pid] for x,y in points)
 assert sum(sum(DEV[p]) for p in ALL)==17 and "max_provinces = 5354" in (MAP/"default.map").read_text(encoding="cp1252")
 t=(MAP/"area.txt").read_text(encoding="cp1252");a,b=bounds(t,"hebei_area");assert {int(x) for x in re.findall(r"\b\d+\b",t[a:b])}==set(ALL)
 for rel,key,ids in (("map/climate.txt","mild_winter",NEW),("map/continent.txt","asia",NEW)):
  t=(MOD/rel).read_text(encoding="cp1252");a,b=bounds(t,key);members={int(x) for x in re.findall(r"\b\d+\b",t[a:b])};assert set(ids)<=members
 for rel,outer,inner,ids in (("map/terrain.txt","mountain","terrain_override",(5351,5352)),("map/terrain.txt","grasslands","terrain_override",(5353,)),("common/tradenodes/00_tradenodes.txt","beijing","members",NEW),("common/trade_companies/00_trade_companies.txt","trade_company_north_china","provinces",NEW)):
  t=(MOD/rel).read_text(encoding="cp1252");a,b=bounds(t,outer);c,d=bounds(t[a:b],inner);members={int(x) for x in re.findall(r"\b\d+\b",t[a:b][c:d])};assert set(ids)<=members
 positions=(MAP/"positions.txt").read_text(encoding="cp1252")
 for pid in ALL:
  assert len(re.findall(rf"(?m)^\s*{pid}\s*=\s*\{{",positions))==1
  text=next(HIST.glob(f"{pid} - *.txt")).read_text(encoding="utf-8-sig");owner,culture,religion,goods=POL[pid]
  assert f"owner = {owner}" in text and f"controller = {owner}" in text and f"add_core = {owner}" in text
  assert f"culture = {culture}" in text and f"religion = {religion}" in text and f"trade_goods = {goods}" in text and "center_of_trade" not in text
 return {"scope_pixels":2192,"pixel_counts":{str(k):len(v) for k,v in cs.items()},"development_total":17,"province_count":5}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def apply():
 changed=apply_bitmap();update_definition();update_histories();update_positions();update_memberships();update_localisation();update_cultures();update_registry();v=validate()
 (PLAN/"README.md").write_text("# B55 上谷区域局部细化\n\n锁定原 703+2136 外缘，将上谷区域由2省细化为5省；总发展度15→17，不新增贸易中心，不改变贸易路线。\n",encoding="utf-8")
 MANIFEST.write_text(json.dumps({"batch":"B55_shanggu_refinement","reviewed_masks_sha256":sha(MASKS),"backup_sha256":sha(BACKUP),"canonical_bitmap_sha256":sha(MAP/"provinces.bmp"),"changed_pixels_this_run":changed,"validation":v},ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(f"{MARKER}; PASS; CHANGED_PIXELS:{changed}; DEV:17")
def check():
 v=validate();subprocess.run([sys.executable,str(ROOT/"tools/encode_eu4_chinese_localisation.py"),"--check"],cwd=ROOT,check=True);print(f"{MARKER}_CHECK; PASS; {v}")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args();check() if a.check else apply()
