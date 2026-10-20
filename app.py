import json
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, select

BASE = Path(__file__).parent
app = Flask(__name__)
if os.getenv('DYNO') and not os.getenv('DATABASE_URL'):
    raise RuntimeError('Heroku 必須先加入 Postgres，設定 DATABASE_URL，避免資料隨重啟遺失')
uri = os.getenv('DATABASE_URL', 'sqlite:///lingyatong.db')
if uri.startswith('postgres://'):
    uri = uri.replace('postgres://', 'postgresql+psycopg://', 1)
elif uri.startswith('postgresql://'):
    uri = uri.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config.update(SQLALCHEMY_DATABASE_URI=uri, SQLALCHEMY_TRACK_MODIFICATIONS=False,
                  SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True})
db = SQLAlchemy(app, session_options={'autoflush': False})

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def sources():
    return json.loads((BASE / 'sources.json').read_text(encoding='utf-8'))

class Item(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    source = db.Column(db.String(100), index=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, default='')
    url = db.Column(db.Text, nullable=False)
    published = db.Column(db.String(40), default='', index=True)
    starts = db.Column(db.String(40), default='')
    ends = db.Column(db.String(40), default='')
    location = db.Column(db.Text, default='')
    category = db.Column(db.String(30), index=True)
    scope = db.Column(db.String(30), index=True)
    reason = db.Column(db.String(100))
    synced = db.Column(db.String(40), nullable=False)
    def data(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class ArticleCache(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    text = db.Column(db.Text)
    checked = db.Column(db.Float, default=0)
    etag = db.Column(db.Text)
    modified = db.Column(db.Text)

class SourceStatus(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    checked = db.Column(db.String(40))
    success = db.Column(db.String(40))
    state = db.Column(db.String(30))
    message = db.Column(db.Text)
    count = db.Column(db.Integer, default=0)
    etag = db.Column(db.Text)
    modified = db.Column(db.Text)

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database ready')

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/health')
def health():
    db.session.execute(select(1))
    return jsonify(status='ok')

@app.get('/api/sources')
def api_sources():
    stats = {s.id:s for s in db.session.execute(select(SourceStatus)).scalars()}
    result=[]
    for src in sources():
        s=stats.get(src['id'])
        result.append({**src, 'status':s.state if s else '尚未同步',
                       'checked':s.checked if s else None,'last_success':s.success if s else None,
                       'message':s.message if s else '啟動 worker 後開始同步',
                       'count':s.count if s else 0})
    return jsonify(result)

@app.get('/api/news')
@app.get('/api/agencies/<agency>/news')
def api_news(agency=None):
    query=select(Item)
    if agency:
        if agency not in {s['id'] for s in sources()}: return jsonify(error='未知來源'),404
        query=query.where(Item.source==agency)
    if request.args.get('source'): query=query.where(Item.source==request.args['source'])
    if request.args.get('category'): query=query.where(Item.category==request.args['category'])
    if request.args.get('scope'): query=query.where(Item.scope==request.args['scope'])
    q=request.args.get('q','').strip()[:120]
    if q:
        safe=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        query=query.where(or_(*(c.ilike(f'%{safe}%',escape='\\') for c in (Item.title,Item.summary,Item.location))))
    try: page=max(1,min(int(request.args.get('page',1)),10000))
    except ValueError: return jsonify(error='page 必須是整數'),400
    total=db.session.scalar(select(db.func.count()).select_from(query.subquery()))
    rows=db.session.execute(query.order_by(Item.published.desc(),Item.synced.desc(),Item.id).offset((page-1)*24).limit(24)).scalars()
    return jsonify(items=[r.data() for r in rows], total=total,page=page,pages=(total+23)//24)

if __name__=='__main__':
    with app.app_context(): db.create_all()
    app.run(port=int(os.getenv('PORT','5000')))
