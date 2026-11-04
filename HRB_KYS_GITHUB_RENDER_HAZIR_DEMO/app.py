"""Synthetic-data-only local HRB KYS pilot. Not production hardened."""
import os, sqlite3, secrets, hashlib, hmac, time, json
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE=Path(__file__).parent; DATA=Path(os.environ.get('KYS_DATA_DIR',str(BASE/'data'))); DATA.mkdir(parents=True,exist_ok=True); DB=DATA/'pilot.sqlite3'; STORE=DATA/'pdf'; STORE.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='HRB KYS Synthetic Pilot')

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def password_hash(p,salt=None):
 salt=salt or secrets.token_hex(16)
 return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),250000).hex()
def verify(p,h):
 salt,digest=h.split(':'); return hmac.compare_digest(password_hash(p,salt).split(':')[1],digest)

def setup():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,display_name TEXT,password TEXT,admin INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS permissions(user_id INTEGER,department TEXT,PRIMARY KEY(user_id,department));
  CREATE TABLE IF NOT EXISTS page_permissions(user_id INTEGER,page TEXT,PRIMARY KEY(user_id,page));
  CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER,expires INTEGER);
  CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,title TEXT,department TEXT,current_version INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS versions(document_id INTEGER,version INTEGER,filename TEXT,created_at INTEGER,PRIMARY KEY(document_id,version));
  CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,document_id INTEGER,requester_id INTEGER,old_text TEXT,new_text TEXT,status TEXT DEFAULT 'pending',reason TEXT,created_at INTEGER,decided_by INTEGER);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT,detail TEXT,created_at INTEGER);''')
  if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
   admin_pass=os.environ.get('KYS_ADMIN_PASSWORD')
   if not admin_pass or len(admin_pass)<12: raise RuntimeError('KYS_ADMIN_PASSWORD en az 12 karakter olmalı')
   c.execute('INSERT INTO users(username,display_name,password,admin) VALUES(?,?,?,1)',('demet.admin','Gül Demet Sağlık',password_hash(admin_pass)))
   from reportlab.pdfgen import canvas
   for idx,(dept,title) in enumerate([('İnsan Kaynakları','Ornek IK Proseduru'),('Satın Alma','Ornek Satin Alma Proseduru')],1):
    fn=f'sample_{idx}_v1.pdf'; cv=canvas.Canvas(str(STORE/fn)); cv.setFont('Helvetica',16); cv.drawString(60,760,title);cv.setFont('Helvetica',11);cv.drawString(60,725,'Bu belge tamamen kurgusaldir. Gercek HRB verisi icermez.');cv.drawString(60,690,'Bu prosedur ornek metin icerir.');cv.save()
    c.execute('INSERT INTO documents(id,title,department) VALUES(?,?,?)',(idx,title,dept))
    c.execute('INSERT INTO versions VALUES(?,?,?,?)',(idx,1,fn,int(time.time())))
setup()

def audit(c,user_id,action,detail=''):
 c.execute('INSERT INTO audit(user_id,action,detail,created_at) VALUES(?,?,?,?)',(user_id,action,detail,int(time.time())))

def actor(request:Request):
 token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
 if not token: raise HTTPException(401,'Oturum açılmalı')
 with conn() as c:
  r=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
  if not r: raise HTTPException(401,'Oturum geçersiz veya süresi dolmuş')
  return dict(r)

def permitted(c,u,dept):
 return bool(u['admin'] or c.execute('SELECT 1 FROM permissions WHERE user_id=? AND department=?',(u['id'],dept)).fetchone())
def document(c,u,id):
 d=c.execute('SELECT * FROM documents WHERE id=?',(id,)).fetchone()
 if not d: raise HTTPException(404,'Doküman bulunamadı')
 if not permitted(c,u,d['department']): raise HTTPException(403,'Bu departmana erişim yok')
 return d
class Login(BaseModel): username:str; password:str
@app.post('/api/login')
def login(body:Login):
 with conn() as c:
  u=c.execute('SELECT * FROM users WHERE username=?',(body.username,)).fetchone()
  if not u or not verify(body.password,u['password']): raise HTTPException(401,'Giriş bilgileri hatalı')
  token=secrets.token_urlsafe(32); c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],int(time.time())+8*3600));audit(c,u['id'],'login')
  return {'token':token,'user':{'id':u['id'],'name':u['display_name'],'admin':bool(u['admin'])}}
@app.post('/api/logout')
def logout(request:Request,u=Depends(actor)):
 token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
 with conn() as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),));audit(c,u['id'],'logout')
 return {'ok':True}
@app.get('/api/me')
def me(u=Depends(actor)):
 with conn() as c: deps=[r['department'] for r in c.execute('SELECT department FROM permissions WHERE user_id=?',(u['id'],))]
 pages=[r['page'] for r in c.execute('SELECT page FROM page_permissions WHERE user_id=?',(u['id'],))]
 return {'id':u['id'],'name':u['display_name'],'admin':bool(u['admin']),'departments':deps,'pages':pages}
@app.get('/api/documents')
def documents(u=Depends(actor)):
 with conn() as c:
  rows=c.execute('SELECT * FROM documents ORDER BY department,title').fetchall()
  return [dict(r) for r in rows if permitted(c,u,r['department'])]
@app.get('/api/documents/{id}/versions')
def versions(id:int,u=Depends(actor)):
 with conn() as c: document(c,u,id);return [dict(r) for r in c.execute('SELECT version,created_at FROM versions WHERE document_id=? ORDER BY version DESC',(id,))]
@app.get('/api/documents/{id}/pdf/{version}')
def pdf(id:int,version:int,u=Depends(actor)):
 with conn() as c:
  document(c,u,id)
  r=c.execute('SELECT filename FROM versions WHERE document_id=? AND version=?',(id,version)).fetchone()
  if not r:raise HTTPException(404,'Sürüm bulunamadı')
  audit(c,u['id'],'view_pdf',f'{id}:{version}')
  path=STORE/r['filename']
  if not path.is_file():raise HTTPException(404,'PDF dosyası bulunamadı')
  return FileResponse(path,media_type='application/pdf',headers={'Cache-Control':'no-store'})
class Revise(BaseModel): document_id:int;old_text:str;new_text:str
@app.post('/api/revisions')
def create_revision(b:Revise,u=Depends(actor)):
 if not b.old_text.strip() or not b.new_text.strip():raise HTTPException(400,'Eski ve yeni metin zorunlu')
 with conn() as c:
  document(c,u,b.document_id)
  cur=c.execute('INSERT INTO revisions(document_id,requester_id,old_text,new_text,created_at) VALUES(?,?,?,?,?)',(b.document_id,u['id'],b.old_text,b.new_text,int(time.time())))
  audit(c,u['id'],'request_revision',str(cur.lastrowid));return {'id':cur.lastrowid,'status':'pending'}
@app.get('/api/revisions')
def revisions(u=Depends(actor)):
 with conn() as c:
  rows=c.execute('SELECT r.*,d.title,d.department FROM revisions r JOIN documents d ON d.id=r.document_id ORDER BY r.id DESC').fetchall()
  return [dict(r) for r in rows if u['admin'] or (r['requester_id']==u['id'] and permitted(c,u,r['department']))]
class Reject(BaseModel):reason:str
@app.post('/api/revisions/{id}/reject')
def reject(id:int,b:Reject,u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Admin yetkisi gerekli')
 if not b.reason.strip():raise HTTPException(400,'Ret gerekçesi zorunlu')
 with conn() as c:
  r=c.execute('SELECT status FROM revisions WHERE id=?',(id,)).fetchone()
  if not r or r['status']!='pending':raise HTTPException(409,'Talep beklemede değil')
  c.execute("UPDATE revisions SET status='rejected',reason=?,decided_by=? WHERE id=?",(b.reason,u['id'],id));audit(c,u['id'],'reject_revision',str(id))
 return {'ok':True}
@app.post('/api/revisions/{id}/approve')
async def approve(id:int,file:UploadFile=File(...),u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Admin yetkisi gerekli')
 raw=await file.read(15*1024*1024+1)
 if len(raw)>15*1024*1024 or not raw.startswith(b'%PDF-'):raise HTTPException(400,'15 MB altı geçerli PDF gerekli')
 try:
  from pypdf import PdfReader
  import io
  if len(PdfReader(io.BytesIO(raw)).pages)<1:raise ValueError('empty PDF')
 except Exception:raise HTTPException(400,'PDF okunamıyor')
 with conn() as c:
  r=c.execute('SELECT * FROM revisions WHERE id=?',(id,)).fetchone()
  if not r or r['status']!='pending':raise HTTPException(409,'Talep beklemede değil')
  d=c.execute('SELECT * FROM documents WHERE id=?',(r['document_id'],)).fetchone()
  v=d['current_version']+1;fn=f'doc_{d["id"]}_v{v}_{secrets.token_hex(8)}.pdf';(STORE/fn).write_bytes(raw)
  c.execute('INSERT INTO versions VALUES(?,?,?,?)',(d['id'],v,fn,int(time.time())))
  c.execute('UPDATE documents SET current_version=? WHERE id=?',(v,d['id']))
  c.execute("UPDATE revisions SET status='approved',decided_by=? WHERE id=?",(u['id'],id))
  audit(c,u['id'],'approve_revision',f'{id}:v{v}')
 return {'ok':True,'version':v,'note':'Yeni PDF admin tarafından yüklenmiştir; otomatik metin değişimi yapılmamıştır.'}
class AutoApprove(BaseModel):
    confirm: bool = False

@app.post('/api/revisions/{id}/auto-approve')
def auto_approve(id:int,b:AutoApprove,u=Depends(actor)):
    """Only for searchable PDFs with a short, exact, single-line replacement.
    Fail closed rather than publish a damaged or incomplete revision.
    """
    if not u['admin']: raise HTTPException(403,'Yalnızca admin onaylayabilir')
    if not b.confirm: raise HTTPException(400,'Yayınlama onayı zorunlu')
    import fitz
    with conn() as c:
        r=c.execute('SELECT * FROM revisions WHERE id=?',(id,)).fetchone()
        if not r or r['status']!='pending': raise HTTPException(409,'Bekleyen revizyon bulunamadı')
        d=c.execute('SELECT * FROM documents WHERE id=?',(r['document_id'],)).fetchone()
        source=c.execute('SELECT filename FROM versions WHERE document_id=? AND version=?',(d['id'],d['current_version'])).fetchone()
        if not source: raise HTTPException(404,'Kaynak PDF bulunamadı')
        old=r['old_text'].strip(); new=r['new_text'].strip()
        if not old or not new or '\n' in old or '\n' in new or len(old)>150 or len(new)>150:
            raise HTTPException(422,'Otomatik değişim yalnızca 150 karaktere kadar tek satırlık metinlerde desteklenir. Tam PDF yükleyin.')
        pdf=fitz.open(STORE/source['filename'])
        if pdf.needs_pass or len(pdf)==0: raise HTTPException(422,'PDF şifreli veya boş')
        hits=[]
        for i,page in enumerate(pdf):
            for rect in page.search_for(old): hits.append((i,rect))
        if len(hits)!=1:
            pdf.close(); raise HTTPException(422,f'Eski metin PDF içinde tam olarak bir kez bulunmalı. Bulunan: {len(hits)}. Tam PDF yükleyin.')
        i,rect=hits[0]; page=pdf[i]
        # Reject replacement that cannot fit in the original line's horizontal area.
        font_size=10
        available=page.rect.width-rect.x0-35
        if fitz.get_text_length(new,fontname='helv',fontsize=font_size)>available:
            pdf.close();raise HTTPException(422,'Yeni metin sayfaya sığmıyor; manuel PDF hazırlayıp yükleyin.')
        page.add_redact_annot(rect,fill=(1,1,1));page.apply_redactions()
        page.insert_text((rect.x0,rect.y1-2),new,fontsize=font_size,fontname='helv',color=(0,0,0))
        # Verify the new text is actually extractable from the generated PDF.
        if new not in page.get_text():
            pdf.close();raise HTTPException(422,'Yeni PDF metin doğrulamasından geçmedi; tam PDF yükleyin.')
        v=d['current_version']+1;fn=f'doc_{d["id"]}_v{v}_{secrets.token_hex(8)}.pdf'
        try:
            pdf.save(STORE/fn,garbage=4,deflate=True)
        finally:pdf.close()
        try:
            check=fitz.open(STORE/fn)
            if len(check)<1 or new not in check[i].get_text():raise ValueError('PDF doğrulaması başarısız')
            check.close()
            c.execute('INSERT INTO versions VALUES(?,?,?,?)',(d['id'],v,fn,int(time.time())))
            c.execute('UPDATE documents SET current_version=? WHERE id=?',(v,d['id']))
            c.execute("UPDATE revisions SET status='approved',decided_by=? WHERE id=?",(u['id'],id))
            audit(c,u['id'],'auto_approve_revision',f'{id}:v{v}')
        except Exception:
            (STORE/fn).unlink(missing_ok=True)
            raise HTTPException(422,'Üretilen PDF doğrulanamadı')
    return {'ok':True,'version':v,'note':'Yeni PDF üretildi. Yayın öncesi görsel kontrol önerilir.'}

@app.get('/api/users')
def users(u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Admin yetkisi gerekli')
 with conn() as c:
  return [{'id':r['id'],'name':r['display_name'],'username':r['username'],'admin':bool(r['admin']),'departments':[x['department'] for x in c.execute('SELECT department FROM permissions WHERE user_id=?',(r['id'],))],'pages':[x['page'] for x in c.execute('SELECT page FROM page_permissions WHERE user_id=?',(r['id'],))]} for r in c.execute('SELECT * FROM users')]
class NewUser(BaseModel):
 username:str
 display_name:str
 password:str
 departments:list[str]=[]
@app.post('/api/users',status_code=201)
def create_user(b:NewUser,u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Yalnızca Demet Hanım kullanıcı oluşturabilir')
 username=b.username.strip().lower(); name=b.display_name.strip()
 if len(username)<3 or not username.replace('.','').replace('_','').isalnum() or not name or len(b.password)<12:
  raise HTTPException(400,'Geçerli kullanıcı adı, ad soyad ve en az 12 karakter şifre gerekli')
 with conn() as c:
  valid={r['department'] for r in c.execute('SELECT DISTINCT department FROM documents')}
  if set(b.departments)-valid:raise HTTPException(400,'Geçersiz departman')
  try:
   cur=c.execute('INSERT INTO users(username,display_name,password,admin) VALUES(?,?,?,0)',(username,name,password_hash(b.password)))
  except sqlite3.IntegrityError:raise HTTPException(409,'Kullanıcı adı zaten kayıtlı')
  c.executemany('INSERT INTO permissions(user_id,department) VALUES(?,?)',[(cur.lastrowid,d) for d in set(b.departments)])
  audit(c,u['id'],'create_user',f'{cur.lastrowid}:{username}')
  return {'id':cur.lastrowid,'username':username,'departments':b.departments}
class Permissions(BaseModel):
 departments:list[str]
 pages:list[str]=[]
ALLOWED_PAGES={'dashboard','tracking','requests','calendar','reports'}
@app.put('/api/users/{id}/permissions')
def permissions(id:int,b:Permissions,u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Admin yetkisi gerekli')
 with conn() as c:
  target=c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone()
  if not target:raise HTTPException(404,'Kullanıcı bulunamadı')
  if target['admin']:raise HTTPException(400,'Admin izinleri bu ekrandan değiştirilemez')
  valid={r['department'] for r in c.execute('SELECT DISTINCT department FROM documents')}
  if set(b.departments)-valid:raise HTTPException(400,'Geçersiz departman')
  if set(b.pages)-ALLOWED_PAGES:raise HTTPException(400,'Geçersiz sayfa')
  c.execute('DELETE FROM page_permissions WHERE user_id=?',(id,))
  c.executemany('INSERT INTO page_permissions VALUES(?,?)',[(id,p) for p in set(b.pages)])
  c.execute('DELETE FROM permissions WHERE user_id=?',(id,))
  c.executemany('INSERT INTO permissions VALUES(?,?)',[(id,d) for d in set(b.departments)])
  audit(c,u['id'],'update_permissions',f'{id}:{json.dumps(dict(departments=b.departments,pages=b.pages),ensure_ascii=False)}')
 return {'ok':True}
@app.get('/api/audit')
def auditlog(u=Depends(actor)):
 if not u['admin']:raise HTTPException(403,'Admin yetkisi gerekli')
 with conn() as c:return [dict(r) for r in c.execute('SELECT a.*,u.display_name FROM audit a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 100')]
@app.get('/bridge.js')
def bridge():return FileResponse(BASE/'bridge.js',media_type='application/javascript')
@app.get('/')
def index():return FileResponse(BASE/'static'/'index.html')
