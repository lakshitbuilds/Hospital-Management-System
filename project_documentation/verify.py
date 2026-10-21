from pathlib import Path
import json
import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent
out=root/'render';out.mkdir(exist_ok=True)
pdf=pdfium.PdfDocument(str(root/'HMS_Project_Documentation.pdf'))
reader=PdfReader(root/'HMS_Project_Documentation.pdf')
texts=[];edges=[]
for i,page in enumerate(pdf):
    text=reader.pages[i].extract_text() or ''
    texts.append({'page':i+1,'words':len(text.split()),'text':text})
    page.render(scale=1.4).to_pil().convert('RGB').save(out/f'page-{i+1:03}.png')
    tp=page.get_textpage();w,h=page.get_size()
    for k in range(tp.count_chars()):
        if not tp.get_text_range(k,1).strip():continue
        l,b,r,t=tp.get_charbox(k)
        if l<14 or r>w-14 or b<12 or t>h-12:edges.append(i+1);break
for start in range(0,len(pdf),12):
    sheet=Image.new('RGB',(1800,1920),'#cccccc');dr=ImageDraw.Draw(sheet)
    for n,i in enumerate(range(start,min(start+12,len(pdf)))):
        im=Image.open(out/f'page-{i+1:03}.png');im.thumbnail((438,600))
        x=n%4*450;y=n//4*640
        sheet.paste(im,(x,y+25));dr.text((x+10,y+5),str(i+1),fill='black')
    sheet.save(out/f'contact-{start//12+1:02}.png')
(out/'page_text.json').write_text(json.dumps(texts,indent=2),encoding='utf8')
result={'pages':len(pdf),'words':sum(p['words'] for p in texts),'edge_issues':edges,'low_text_pages':[p['page'] for p in texts if p['words']<20]}
(out/'validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
