#!/usr/bin/env python3
"""Apply/check B57 Changsha vassalage and Khitan Liao culture."""
from __future__ import annotations
import argparse,base64,csv,hashlib,json,re,struct,subprocess,sys,zlib
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/"guangdong_independent_practice"
PLAN=ROOT/"planning/changsha_khitan_b57"
VANILLA=Path.home()/"Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
CSV=ROOT/"planning/culture_overhaul/approved_province_culture_assignments.csv"
HIST=MOD/"history/provinces"
DIPLOMACY=MOD/"history/diplomacy/gdd_b52_chu_vassals.txt"
FLAG=MOD/"gfx/flags/LIO.tga"
BITMAP=MOD/"map/provinces.bmp"
TARGETS={726:"沈阳",5204:"辽阳"}
MARKER="GDD_B57_CHANGSHA_KHITAN"
FLAG_MASK_B64="eNrtm8tvG0Ucx2dn1nbdrBvbvcAN8bjAnwARaVUQKWkoSRwOpCqgqodyaZoImjScAeWcQxGi3HtASAhBES0KCEQfvKVe0laCxk6VegNUQO2d2emMbZom6ez+hu7DEvM9RYl/+ciT/X3n94gRMkJWGuqit99bKpYSVrFk/0tHxStu4qq7fYh0+KU/eQraucav+8xPFu5Tf8ca3+W+/7u7mtTZr7oeZ3wdn68+kNyzVy4t8OYGvltIMuM+38wvWzgp5yHW6c38EkrMkTAyfMM3fMM3fMM3fMM3/O7hx9/zBvBFbRprp2tbgXz500KxGFfLW2jh1HwLZSa+rMbXeNW+md4qICq+hXMfxt14LjgCo+Db6CBvUD9G0Zv8KLJVfIxOMSp6Y5/FI9HjU3ZW9F9352NkXxR9cbx9P685SMnfcoUzxueeGtwdgwafnhVHK0F2EJ/ysbiyv58zCP8lkiUxKEuehfFftnM2QPgOQ4e8PmcPwvjD0GvEun2fwPR4KP+yfMXJmdmZUE2/8tjaL35o39HwiNmZ98OeP/KLRv55Jxx5oVmYzP2tkX+/bVXln/CFD5gnPMKDiPr8XXnyBL0BDpH+cwZhNX8PZx4Fyec+9R6Rz8D2FWmaDBTleXy/2n/F23lTw8so34dsgvq4zux0HuPA+//J+U++gugG9z0+IfnP++KZaXwNCTp1/BkUcP9qpBI6J/5S/Ijkj0rPvpqHVkAh9R8hGFJAWufX85cKkIWGRUhw/QcsI7HV5k9aGduqdPgYXINGUX+3zv+wjBlu8fOR1N89BZC2FQrfSf60Uyo645Jfvc/ZBot1lM+f8N+zy0tVmJoymf6o1mpVt5WLNVjY0vLF3gD/vxr/5uNG4P3DPGAt13bzTlUnBAyjrB7Ev0T1+UyLT68H8PPX4j//m0q+hchAZQSi0ZGRRfHm+Ym9Y5W9c/JWr784PAoKrQxllPevTv5/K/PvkPxqd8t/o+m/gaWkTcgFyZ8iuSwZa/lPr/wmSIF8QB1JWpfIRv93oOF2BP6r4t/b+Yv+68DkxJFgTUweyKj41v6p8PBDOXX/lXcBCbTq3J0vytdfAeGsHOA/i14jpIZseJd6lPwfQ8Ob3kqg/4X6r8cuq/k/hYZTFuR/W5YBB3hNzV8EhP8TcP65j344dyFY57//OK/knwSEf1G4d/+LJ/+6gQ8rIFV84Ag0uP62Uqy/0+4/LNQ//ym4//K1+693gvsvjN7S6j/HJf+JyPpPgoY0+m9Gmw/L/rscWf+tO3843p4/HIto/iAM7Ged+ct7Pe35C377r0jmL5rzp0fvmD+Nvx7J/Cn1+VtXzB/h81erY2rRzl/TnT/D5+8DQw+KGwfdv2cgqvm77v7hNel/L0S1f9DdvzRYy/9HwD17yP5Fd//UbN8/oz6NaP9k4aze/m1K8iuR7d/k/vHwAnj/uOK+KvnPufWI9o/t6sCB7l+LpZyMz5SKUe1fU98/a+7f/2OA+f8Hwzd8wzd8wzd8wzd8w3e3Y4ITko3PbOLXsyhBfbaR73sLpxOUy+kGftKfPlz3+bvrjNJmkqKiZ++/zS830vj85a4OHyG7b0cKSjDhw0TSUBd9APp/rFs/lpEp"

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def initial(text:str)->str:
 m=re.search(r"(?m)^\d+\.\d+\.\d+\s*=\s*\{",text)
 return text[:m.start()] if m else text

def value(text:str,key:str)->str|None:
 m=re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#]+)",initial(text))
 return m.group(1) if m else None

def history(pid:int)->Path:
 paths=sorted(HIST.glob(f"{pid} - *.txt"))
 if len(paths)!=1:raise ValueError(f"{pid}: expected one local history, got {len(paths)}")
 return paths[0]

def block(text:str,key:str)->str:
 m=re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{",text)
 if not m:raise ValueError(f"missing block {key}")
 depth=0
 for i in range(m.end()-1,len(text)):
  depth+=(text[i]=="{")-(text[i]=="}")
  if depth==0:return text[m.start():i+1]
 raise ValueError(f"unclosed block {key}")

def update_culture_csv()->None:
 with CSV.open(encoding="utf-8-sig",newline="") as f:
  rows=list(csv.DictReader(f));fields=list(rows[0])
 by_id={int(row["province_id"]):row for row in rows}
 for pid,name in TARGETS.items():
  by_id[pid]=dict(province_id=str(pid),province_name=name,document_group="蒙古文化组",document_culture="契丹文化",document_entry=name,target_culture="gdd_khitan",source_rule="user_override",decision_note="B57用户确认：辽阳、沈阳为契丹文化，归入蒙古文化组")
 with CSV.open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
  writer.writerows(by_id[pid] for pid in sorted(by_id))

def liao_flag_bytes()->bytes:
 mask=zlib.decompress(base64.b64decode(FLAG_MASK_B64))
 if len(mask)!=128*128:raise ValueError("corrupt Khitan flag mask")
 background=(184,151,72);ink=(39,48,54)
 header=struct.pack("<BBBHHBHHHHBB",0,0,2,0,0,0,0,0,128,128,24,0x20)
 pixels=bytearray()
 for opacity in mask:
  rgb=tuple((background[i]*(255-opacity)+ink[i]*opacity+127)//255 for i in range(3))
  pixels.extend((rgb[2],rgb[1],rgb[0]))
 return header+bytes(pixels)

def write_flag()->None:
 FLAG.write_bytes(liao_flag_bytes())

def run_generators()->None:
 subprocess.run([sys.executable,str(ROOT/"tools/map_pipeline/apply_b52_chu_vassals.py"),"--vanilla-root",str(VANILLA)],cwd=ROOT,check=True)
 subprocess.run([sys.executable,str(ROOT/"tools/map_pipeline/apply_culture_overhaul.py")],cwd=ROOT,check=True)

def validate()->dict[str,object]:
 for pid in TARGETS:
  if value(history(pid).read_text(encoding="utf-8-sig"),"culture")!="gdd_khitan":
   raise ValueError(f"{pid}: culture is not gdd_khitan")
 country=(MOD/"history/countries/LIO - Liao.txt").read_text(encoding="utf-8-sig")
 if value(country,"primary_culture")!="gdd_khitan":raise ValueError("LIO primary culture drifted")
 accepted=set(re.findall(r"(?m)^\s*add_accepted_culture\s*=\s*(\S+)",country))
 if accepted!={"manchu","gdd_qi"}:raise ValueError(f"LIO accepted cultures drifted: {accepted}")
 cultures=(MOD/"common/cultures/00_cultures.txt").read_text(encoding="latin-1")
 altaic=block(cultures,"altaic")
 if len(re.findall(r"(?m)^\s*gdd_khitan\s*=\s*\{",altaic))!=1 or "primary = LIO" not in altaic:
  raise ValueError("Khitan culture is not a unique LIO-primary child of altaic")
 diplomacy=DIPLOMACY.read_text(encoding="utf-8-sig")
 for tag in ("EGU","QVN","ZHU","CSA"):
  if len(re.findall(rf"(?m)^\s*second\s*=\s*{tag}\s*$",diplomacy))!=1:
   raise ValueError(f"{tag}: missing unique CHC vassal relation")
 all_diplomacy="\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD/"history/diplomacy").glob("*.txt"))
 if len(re.findall(r"(?m)^\s*second\s*=\s*CSA\s*$",all_diplomacy))!=1:
  raise ValueError("CSA must have exactly one starting subject relation")
 for tag in ("CDE","JJG","HYA"):
  if re.search(rf"(?m)^\s*second\s*=\s*{tag}\s*$",all_diplomacy):
   raise ValueError(f"{tag}: public city must remain independent")
 if FLAG.read_bytes()!=liao_flag_bytes():raise ValueError("LIO Khitan flag drifted")
 loc="\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD/"localisation_source").glob("*.txt"))
 if len(re.findall(r'(?m)^\s*gdd_khitan:0\s+"契丹"\s*$',loc))!=1:
  raise ValueError("Khitan localisation missing")
 return {"batch":"B57_changsha_khitan","changsha":{"tag":"CSA","overlord":"CHC","subject_type":"vassal","development":39},"khitan_culture":{"key":"gdd_khitan","group":"altaic","provinces":sorted(TARGETS)},"liao_flag":{"script":"Khitan Large Script ninefold seal","source_glyph_pua":"U+E23D","seal_glyph_pua":"U+F012","interpretation":"possible Liao/Khitan state name or epithet"},"geometry":"unchanged","areas":"unchanged","trade":"unchanged","bitmap_sha256":sha(BITMAP)}

def write_docs(before:str)->None:
 PLAN.mkdir(parents=True,exist_ok=True)
 data=liao_flag_bytes()[18:];im=Image.new("RGB",(128,128));pixels=[]
 for i in range(0,len(data),3):b,g,r=data[i:i+3];pixels.append((r,g,b))
 im.putdata(pixels);im.resize((512,512),Image.Resampling.NEAREST).save(PLAN/"liao_flag_preview.png")
 report=validate()
 (PLAN/"README.md").write_text("# B57 长沙附庸与契丹文化\n\n长沙国（CSA）改为楚国（CHC）的开局附庸。沈阳（726）与辽阳（5204）改为蒙古文化组下的契丹文化，辽国以契丹为主文化。辽旗使用契丹大字 U+E23D 对应的九叠篆官印字形 U+F012；研究资料将其视为可能表示辽或契丹国家专称的字符。地图、区域、贸易与发展度不变。\n\n字形依据：https://www.babelstone.co.uk/Blog/2012/10/khitan-seals.html （Seal A6 与字形对应表）\n",encoding="utf-8")
 (PLAN/"batch_manifest.json").write_text(json.dumps({"marker":MARKER,"bitmap_sha256_before":before,"bitmap_sha256_after":sha(BITMAP),"validation":report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def apply()->None:
 before=sha(BITMAP);update_culture_csv();run_generators();write_flag();write_docs(before)
 if sha(BITMAP)!=before:raise ValueError("B57 changed provinces.bmp")
 print(json.dumps(validate(),ensure_ascii=False))

def check()->None:
 report=validate()
 subprocess.run([sys.executable,str(ROOT/"tools/encode_eu4_chinese_localisation.py"),"--check"],cwd=ROOT,check=True)
 print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true");args=parser.parse_args()
 check() if args.check else apply()
