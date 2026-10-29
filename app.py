import os, io, secrets, html
import requests, qrcode
from flask import Flask, request, jsonify, send_file, render_template_string

app = Flask(__name__)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
PUBLIC_URL = os.environ.get('PUBLIC_URL', '')

PAGE = '''<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QR Screen Lab</title><style>
*{box-sizing:border-box}body{font:16px system-ui,sans-serif;background:#091626;color:#edf7ff;margin:0;padding:22px}main{max-width:520px;margin:30px auto}.card{background:#172b43;border:1px solid #314761;border-radius:18px;padding:23px;margin:15px 0}h1{color:#67e0c6;margin-top:0}p{line-height:1.55;color:#d0dfed}input[type=text],input[type=file]{width:100%;padding:13px;border-radius:10px;border:1px solid #60758d;background:#f6fbff;color:#13283a}button{border:0;background:#35d6ae;color:#092a22;padding:14px 18px;border-radius:10px;font-weight:700;width:100%;margin-top:12px;font-size:16px}button:disabled{opacity:.4}label{display:block;margin:14px 0}small{color:#a9bfce}img#preview{max-width:100%;border-radius:10px;display:none;margin-top:12px}#status{margin-top:12px}a{color:#80f4d6}.hidden{display:none}
</style></head><body><main><div class="card"><h1>🛡️ QR Screen Lab</h1><p>Telefon ekranidagi shaxsiy ma’lumotlar haqida amaliy xavfsizlik tajribasi.</p><label>Ism-familiyangiz<input type="text" id="name" maxlength="70" placeholder="Masalan: Ali Valiyev" autocomplete="name"></label><p><b>Rozilik:</b> Testga kirish uchun rozili bering.</p><label><input type="checkbox" id="agree"> Testga kirishga roziman.</label><button id="start" onclick="begin()">Tajribani boshlash</button><small>Tanlab yuboring</small></div>
<div class="card hidden" id="capture"><h2>1. Ekran suratini tayyorlang</h2><p>Avval bosh ekranda shaxsiy ma’lumotlar ko‘rinmasligiga ishonch hosil qiling.</p><button onclick="captureScreen()">Ekranni ulashish orqali surat olish</button><p><small>Bu imkoniyat ko‘plab telefon brauzerlarida ishlamasligi mumkin.</small></p><label>Yoki telefoningizda skrinshot olib, shu yerdan tanlang:<input type="file" id="file" accept="image/png,image/jpeg,image/webp" onchange="pickFile()"></label><img id="preview" alt="Yuborishdan oldingi skrinshot"><p id="status" role="status"></p><button id="send" disabled onclick="sendPhoto()">Ko‘rdim, tasdiqlayman va yuboraman</button><button onclick="resetPhoto()" style="background:#415a73;color:white">Suratni bekor qilish</button></div>
</main><script>
let photoBlob=null;
function status(s){document.getElementById('status').textContent=s}
function begin(){if(!document.getElementById('name').value.trim())return alert('Ism-familiyangizni kiriting');if(!document.getElementById('agree').checked)return alert('Testga kirish uchun rozilik belgisini qo'ying');document.getElementById('capture').classList.remove('hidden');document.getElementById('capture').scrollIntoView({behavior:'smooth'})}
function resetPhoto(){photoBlob=null;document.getElementById('file').value='';document.getElementById('preview').style.display='none';document.getElementById('preview').removeAttribute('src');document.getElementById('send').disabled=true;status('Surat bekor qilindi.')}
function setPhoto(blob){if(!blob||!['image/jpeg','image/png','image/webp'].includes(blob.type)||blob.size>5*1024*1024){status('JPEG, PNG yoki WebP rasm tanlang (5 MB gacha).');return}photoBlob=blob;const reader=new FileReader();reader.onload=()=>{const p=document.getElementById('preview');p.src=reader.result;p.style.display='block'};reader.readAsDataURL(blob);document.getElementById('send').disabled=false;status('Suratni ko‘rib chiqing. Faqat tasdiqlasangiz yuboriladi.')}
function pickFile(){const f=document.getElementById('file').files[0];if(f)setPhoto(f)}
async function captureScreen(){if(!navigator.mediaDevices||!navigator.mediaDevices.getDisplayMedia){status('Bu brauzer ekran ulashishni qo‘llamaydi. Telefoningizda skrinshot oling va pastdan tanlang.');return}let stream;try{stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});const video=document.createElement('video');video.srcObject=stream;video.muted=true;video.playsInline=true;await video.play();await new Promise(resolve=>{if(video.videoWidth)return resolve();video.onloadedmetadata=resolve});const c=document.createElement('canvas');c.width=Math.min(video.videoWidth,1280);c.height=Math.round(video.videoHeight*c.width/video.videoWidth);c.getContext('2d').drawImage(video,0,0,c.width,c.height);const b=await new Promise(resolve=>c.toBlob(resolve,'image/jpeg',0.8));setPhoto(b)}catch(e){status('Ekran ulashish amalga oshmadi. Skrinshotni o‘zingiz olib yuklashingiz mumkin.')}finally{if(stream)stream.getTracks().forEach(t=>t.stop())}}
async function sendPhoto(){if(!photoBlob||!document.getElementById('agree').checked)return;const b=document.getElementById('send');b.disabled=true;status('Yuborilmoqda...');const f=new FormData();f.append('name',document.getElementById('name').value.trim());f.append('consent','yes');f.append('photo',photoBlob,'screenshot.'+(photoBlob.type==='image/png'?'png':photoBlob.type==='image/webp'?'webp':'jpg'));try{const r=await fetch('/submit',{method:'POST',body:f});const x=await r.json();if(!r.ok)throw new Error(x.error||'Xatolik');status('Skrinshot o‘qituvchiga yuborildi. Rahmat!');photoBlob=null;document.getElementById('preview').style.display='none'}catch(e){status('Yuborilmadi: '+e.message);b.disabled=false}}
</script></body></html>'''

@app.get('/')
def index():
    return render_template_string(PAGE)

@app.get('/qr')
def qr():
    url = (PUBLIC_URL or request.url_root).rstrip('/') + '/'
    b = io.BytesIO()
    qrcode.make(url).save(b, format='PNG')
    b.seek(0)
    return send_file(b, mimetype='image/png')

@app.post('/submit')
def submit():
    if request.form.get('consent') != 'yes':
        return jsonify(error='Testga o'tish talab qilinadi'), 403
    name = request.form.get('name','').strip()
    if not name or len(name)>70:
        return jsonify(error='Ism-familiya noto‘g‘ri'), 400
    f = request.files.get('photo')
    if not f or f.mimetype not in ('image/jpeg','image/png','image/webp'):
        return jsonify(error='Faqat rasm yuborish mumkin'), 400
    data = f.read(5*1024*1024+1)
    if not data or len(data)>5*1024*1024:
        return jsonify(error='Rasm hajmi 5 MB dan oshmasin'), 400
    if not BOT_TOKEN or not CHAT_ID:
        return jsonify(error='Telegram hali sozlanmagan'), 503
    try:
        r=requests.post('https://api.telegram.org/bot'+BOT_TOKEN+'/sendPhoto',
            data={'chat_id':CHAT_ID,'caption':'QR Screen Lab\nTalaba: '+name+'\nRozilik bilan yuborilgan ekran surati'},
            files={'photo':('screenshot.jpg',data,f.mimetype)},timeout=20)
        r.raise_for_status()
        if not r.json().get('ok'):
            return jsonify(error='Telegram qabul qilmadi'), 502
    except (requests.RequestException,ValueError):
        return jsonify(error='Telegramga yuborishda xatolik'), 502
    return jsonify(ok=True)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','5000')))
