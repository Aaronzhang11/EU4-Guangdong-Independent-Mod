#!/usr/bin/env python3
"""Apply/check the B56 Hainan Austronesian Li polity transaction."""
from __future__ import annotations
import argparse,csv,hashlib,json,re,struct,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2];MOD=ROOT/"guangdong_independent_practice";HIST=MOD/"history/provinces";PLAN=ROOT/"planning/hainan_austronesian_b56"
SOURCE=MOD/"localisation_source/009_gdd_b56_hainan_austronesian_polity_readable_utf8.txt";TARGET=MOD/"localisation/replace/009_gdd_b56_hainan_austronesian_polity_l_english.yml"
MANIFEST=PLAN/"batch_manifest.json";PREVIEW=PLAN/"formal_review.png";VANILLA=Path.home()/"Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
MARKER="GDD_B56_HAINAN_AUSTRONESIAN_POLITY";ISLAND=(666,5301,5302,2160,5303);LI=(5301,5302,2160);CHAO=(666,5303)
EXPECTED_OWNER={**{p:"HLI" for p in LI},**{p:"CZC" for p in CHAO}};EXPECTED_RELIGION={**{p:"hinduism" for p in LI},**{p:"confucianism" for p in CHAO}}
EXPECTED_CULTURE={**{p:"gdd_qiongli" for p in LI},**{p:"gdd_min" for p in CHAO}}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def initial(text):
 m=re.search(r"(?m)^\d+\.\d+\.\d+\s*=\s*\{",text);return text[:m.start()] if m else text
def value(text,key):
 m=re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#]+)",initial(text));return m.group(1) if m else None
def history(pid):
 paths=sorted(HIST.glob(f"{pid} - *.txt"))
 if len(paths)!=1:raise ValueError(f"province {pid} has {len(paths)} local histories")
 return paths[0]
def write_localisation():
 SOURCE.write_text('''l_english:\n HLI:0 "黎"\n HLI_ADJ:0 "黎"\n''',encoding="utf-8-sig")
 sys.path.insert(0,str(ROOT/"tools"));from encode_eu4_chinese_localisation import encode_file,verify_file;encode_file(SOURCE,TARGET);verify_file(SOURCE,TARGET)
def update_tag():
 p=MOD/"common/country_tags/gdd_country_tags.txt";text=p.read_text(encoding="utf-8-sig");begin="# GDD_B56_HAINAN_AUSTRONESIAN_BEGIN";end="# GDD_B56_HAINAN_AUSTRONESIAN_END"
 text=re.sub(rf"(?ms)^\s*{re.escape(begin)}.*?{re.escape(end)}\s*\n?","",text);text=re.sub(r'(?m)^\s*HLI\s*=\s*"[^"]+"\s*\n?',"",text)
 p.write_text(text.rstrip()+f'\n\n{begin}\nHLI = "countries/B56_Li.txt"\n{end}\n',encoding="utf-8")
def update_culture_csv():
 p=ROOT/"planning/culture_overhaul/approved_province_culture_assignments.csv"
 with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f));fields=list(rows[0])
 names={666:"琼州",5301:"儋州",5302:"昌化",2160:"崖州",5303:"万州"};rows=[r for r in rows if int(r["province_id"]) not in ISLAND]
 for pid in ISLAND:
  qiongli=pid in LI
  rows.append(dict(province_id=str(pid),province_name=names[pid],document_group="马来文化组" if qiongli else "百越文化组",document_culture="琼黎文化" if qiongli else "闽越文化",document_entry="黎国南岛腹地" if qiongli else "潮州海南据点",target_culture=EXPECTED_CULTURE[pid],source_rule="user_override",decision_note="B56用户确认：黎国三省为琼黎文化" if qiongli else "B56后续用户修正：潮州控制的琼州、万州改为闽越文化"))
 rows.sort(key=lambda r:int(r["province_id"]))
 with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def run_generators():
 subprocess.run([sys.executable,str(ROOT/"tools/map_pipeline/apply_b43_chunqiu_polities.py"),"--vanilla-root",str(VANILLA)],cwd=ROOT,check=True)
 subprocess.run([sys.executable,str(ROOT/"tools/map_pipeline/apply_culture_overhaul.py")],cwd=ROOT,check=True)
def set_religions():
 for pid,religion in EXPECTED_RELIGION.items():
  p=history(pid);text=p.read_text(encoding="utf-8-sig");text,n=re.subn(r"(?m)^(\s*religion\s*=\s*)[A-Za-z0-9_]+",rf"\g<1>{religion}",text,count=1)
  if n!=1:raise ValueError(f"province {pid} lacks religion")
  p.write_text(text,encoding="utf-8")
def flag_bytes():
 w=h=128;head=struct.pack("<BBBHHBHHHHBB",0,0,2,0,0,0,0,0,w,h,24,0x20);pixels=bytearray()
 for y in range(h):
  for x in range(w):
   color=(31,43,79);dx=x-64;dy=y-48
   if dx*dx+dy*dy<=27*27:color=(222,176,67)
   if 78<=y<=86 and 31<=x<=97 and abs(x-64)<41-(y-78)*2:color=(35,105,91)
   if 65<=y<=77 and abs(x-64)<=2:color=(35,105,91)
   if 90<=y<=94 and 20<=x<=108 and ((x+y)//8)%2==0:color=(222,176,67)
   pixels.extend((color[2],color[1],color[0]))
 return head+bytes(pixels)
def write_flag():(MOD/"gfx/flags/HLI.tga").write_bytes(flag_bytes())
def definitions():
 out={}
 for line in (MOD/"map/definition.csv").read_text(encoding="cp1252").splitlines()[1:]:
  c=line.split(";")
  if len(c)>3 and c[0].isdigit():out[int(c[0])]=tuple(map(int,c[1:4]))
 return out
def render_preview():
 defs=definitions();src=Image.open(MOD/"map/provinces.bmp").convert("RGB");crop_box=(4492,1065,4548,1115);crop=src.crop(crop_box);px=crop.load();lookup={defs[p]:((44,126,104) if p in LI else (139,113,153)) for p in ISLAND};lookup[defs[5304]]=(82,82,78)
 for y in range(crop.height):
  for x in range(crop.width):
   px[x,y]=lookup.get(px[x,y],(218,211,194))
 shown=crop.resize((896,800),Image.Resampling.NEAREST);canvas=Image.new("RGB",(1280,860),(247,245,239));canvas.paste(shown,(20,50));draw=ImageDraw.Draw(canvas);font="/System/Library/Fonts/STHeiti Medium.ttc"
 draw.text((20,12),"海南琼黎政权 · B56正式实装",font=ImageFont.truetype(font,27),fill=(30,34,36));x=945;y=90
 for color,label in (((44,126,104),"黎：儋州、昌化、崖州"),((139,113,153),"潮州：琼州、万州"),((82,82,78),"五指山：不可通行")):
  draw.rectangle((x,y,x+24,y+24),fill=color);draw.text((x+34,y-2),label,font=ImageFont.truetype(font,16),fill=(38,41,43));y+=58
 draw.text((x,y+12),"黎地：琼黎｜潮州据点：闽越",font=ImageFont.truetype(font,15),fill=(38,41,43));draw.text((x,y+49),"黎国：17发展度｜印度教｜无新增贸易中心",font=ImageFont.truetype(font,15),fill=(38,41,43));PLAN.mkdir(parents=True,exist_ok=True);canvas.save(PREVIEW)
def block(text,key):
 m=re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{",text)
 if not m:raise ValueError(f"missing block {key}")
 i=m.end()-1;d=0
 for j in range(i,len(text)):
  d+=(text[j]=="{")-(text[j]=="}")
  if d==0:return text[m.start():j+1]
 raise ValueError(key)
def validate():
 for pid in ISLAND:
  text=history(pid).read_text(encoding="utf-8-sig");cores=set(re.findall(r"(?m)^\s*add_core\s*=\s*(\S+)",initial(text)))
  assert value(text,"owner")==EXPECTED_OWNER[pid] and value(text,"controller")==EXPECTED_OWNER[pid]
  assert value(text,"culture")==EXPECTED_CULTURE[pid] and value(text,"religion")==EXPECTED_RELIGION[pid] and "HLI" in cores and "MNG" not in cores and "center_of_trade" not in initial(text)
 country=(MOD/"history/countries/HLI - Li.txt").read_text(encoding="utf-8-sig")
 for key,want in (("government","tribal"),("add_government_reform","tribal_kingdom"),("primary_culture","gdd_qiongli"),("religion","hinduism"),("capital","5302")):
  assert value(country,key)==want,(key,value(country,key))
 assert (MOD/"common/countries/B56_Li.txt").exists() and (MOD/"gfx/flags/HLI.tga").stat().st_size==18+128*128*3
 tags=(MOD/"common/country_tags/gdd_country_tags.txt").read_text(encoding="utf-8-sig");assert len(re.findall(r'(?m)^HLI\s*=\s*"countries/B56_Li.txt"$',tags))==1
 cultures=(MOD/"common/cultures/00_cultures.txt").read_text(encoding="latin-1");malay=block(cultures,"malay");assert len(re.findall(r"(?m)^\s*gdd_qiongli\s*=\s*\{",malay))==1 and "primary = HLI" in malay
 loc="\n".join(p.read_text(encoding="utf-8-sig") for p in (MOD/"localisation_source").glob("*.txt"))
 for key in ("HLI","HLI_ADJ","gdd_qiongli"):assert len(re.findall(rf"(?m)^\s*{key}:0\s+",loc))==1,key
 return {"country":"HLI","capital":5302,"owned_provinces":list(LI),"claimed_island":list(ISLAND),"development":{"HLI":17,"CZC_hainan":13,"island_total":30},"cultures":{"HLI":"gdd_qiongli","CZC_hainan":"gdd_min"},"religions":{"HLI":"hinduism","CZC_occupation":"confucianism"},"bitmap_changed_pixels":0,"trade_network_changed":False,"new_trade_centres":0}
def write_docs(before):
 v=validate();PLAN.mkdir(parents=True,exist_ok=True);(PLAN/"README.md").write_text("# B56 海南琼黎政权\n\n黎国（HLI）占儋州、昌化、崖州，首都昌化，三省为马来文化组的琼黎文化并信奉印度教；潮州保有琼州、万州，两省为百越文化组的闽越文化并保留儒教。地图、区域和贸易网络不变。\n",encoding="utf-8")
 MANIFEST.write_text(json.dumps({"batch":"B56_hainan_austronesian_polity","marker":MARKER,"map_bitmap_sha256_before":before,"map_bitmap_sha256_after":sha(MOD/"map/provinces.bmp"),"formal_review":str(PREVIEW),"validation":v},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def apply():
 before=sha(MOD/"map/provinces.bmp");write_localisation();update_tag();update_culture_csv();run_generators();set_religions();write_flag();render_preview();write_docs(before)
 if sha(MOD/"map/provinces.bmp")!=before:raise ValueError("B56 changed provinces.bmp")
 print(f"{MARKER}; PASS; HLI_DEV:17; BITMAP_PIXELS:0")
def check():
 v=validate();subprocess.run([sys.executable,str(ROOT/"tools/encode_eu4_chinese_localisation.py"),"--check"],cwd=ROOT,check=True);print(f"{MARKER}_CHECK; PASS; {v}")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args();check() if a.check else apply()
