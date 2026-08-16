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
FLAG_MASK_B64="eNrt21tIFFEYAODddXaXNhVdDN1QIS1K7UHLJAgtpNTCsIeiUsuXiBCKiEIzERItb1CWS5BBUXSxHnqQiK5mEFpBEWkRlmmCRJoIXst1pjln3HXdmW3nzM5piv7zNHPOf+ab67m56nSQIGmcOE0S+H+T/+ffOPDBBx/8f8jX/6bMuoa6Hzy4y/uptXAXgij7No497K1sL3+M7lS6fiAfd8UiWRQ/jA7iKDXQ9A2+O9V7ITTfvwnfJ1BO00c3ebhHMvVh/UNJOG2/QrooEh3k7Xy6378vv1inrZ+vsb8DfPDBBx988MEHH3zwwdfY31hm0NJPm+TO67Xz44b4gnrNfFsPnhgfI/CT7pTnrbIGqOKHvRaWBdhc+b7hKq4yMdjrOclnfcz/B0TZrhWLyaXy7z/TTuHPHcUEz3+z6vpU22IC31hXlLMyMsikh/YPfPDBB19DP6o1WVO/jPt5RC/TN91crbrfyRffD5fnBw466uap6y/HHejXTHn3nx9tdq1V1a+eGUHVGGU9/20sx9aa1PPNA84xRKm89+8gv/FqmWr+bgEfL0kPlfn+n+W3xnLV8p9j3pEl//tjHqLteqMq/nrh8o+TfP/Wj2inJUQN/ynmnzFE7U/8KNrriPLfT8f8UDRh+1eAq/XF+uvrhaefQ9z+XsT1vizy0xeuo468/7G8xzU/hfnlB/ajokcBCvq/FAc+gSdGf/xaVNIbpqj/rRQ+nBo/fHwNI4mzGaMEvqlDaDhSFPtm1PE5Nrnl/OAzKuX2/+uEG/BCsV+F8gvdc6b5jBOyxx9NwglkKvQzpl3tnvNrRIFVsv1IYfJ/W5m/8Jto3caMAqvlj7/qsT8WoMRnWvnMxrkT8OA5jYFvP2Icn0CsEt/O59k95v8LUOBpgvFnA/bjFPj7pa4UGw0EfgJe+bGQ+1kOjj0kqhWLAs+RjL/RQ7xG/v6ljHDjW8W14lFgI4mPfhWVRuwnfOe6EyVqJaPAyyR+BMu9IW5/Yvq55lCpWqko8Ia0Hy09/2nn8oj9ttF90kaGt+aETytQ2XZRdu4ZPbGfH+Nl1JCDAu+6LZQyDGMyW4KttpikS6gsm+78dyfu0V27haznKmMyXX8PCnzp2t3Q6fF7tAkTXf8ACnzn3iHZsqu7Z/3rOrr+URT42TN3S9cM70ii7FegwFui7KBmwT+po+yf4qeBRYw43/gAHaHJQNu3c4+lZxQRI9xUOQGv0M8u8Ppl2JfodNR99RL44IMPPvjOPfj/w//XhwRJo/QLKNKgkw=="

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
 return {"batch":"B57_changsha_khitan","changsha":{"tag":"CSA","overlord":"CHC","subject_type":"vassal","development":39},"khitan_culture":{"key":"gdd_khitan","group":"altaic","provinces":sorted(TARGETS)},"liao_flag":{"script":"Khitan Large Script","glyph_pua":"U+E23D","interpretation":"possible Liao/Khitan state name or epithet"},"geometry":"unchanged","areas":"unchanged","trade":"unchanged","bitmap_sha256":sha(BITMAP)}

def write_docs(before:str)->None:
 PLAN.mkdir(parents=True,exist_ok=True)
 data=liao_flag_bytes()[18:];im=Image.new("RGB",(128,128));pixels=[]
 for i in range(0,len(data),3):b,g,r=data[i:i+3];pixels.append((r,g,b))
 im.putdata(pixels);im.resize((512,512),Image.Resampling.NEAREST).save(PLAN/"liao_flag_preview.png")
 report=validate()
 (PLAN/"README.md").write_text("# B57 长沙附庸与契丹文化\n\n长沙国（CSA）改为楚国（CHC）的开局附庸。沈阳（726）与辽阳（5204）改为蒙古文化组下的契丹文化，辽国以契丹为主文化。辽旗使用契丹大字实验字库 U+E23D 字形；研究资料将其视为可能表示辽或契丹国家专称的字符。地图、区域、贸易与发展度不变。\n\n字形依据：https://www.babelstone.co.uk/Blog/2012/10/khitan-seals.html （Seal A6 讨论）\n",encoding="utf-8")
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
