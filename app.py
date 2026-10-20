import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, jsonify, render_template, request, abort, Response, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, select, inspect, text
from settings import site_settings

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
    raw=json.loads((BASE / os.getenv('SOURCES_FILE','sources.json')).read_text(encoding='utf-8'))
    district=site_settings()['district']
    return [x for x in raw if not x.get('districts') or district in x['districts']]

def status_key(source_id):
    return source_id if site_settings()['district']=='苓雅區' else site_settings()['district']+':'+source_id

@app.context_processor
def site_context():
    return {'site':site_settings()}


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

def ensure_database():
    db.create_all()

@app.cli.command('init-db')
def init_db():
    ensure_database()
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
        s=stats.get(status_key(src['id']))
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
    if request.args.get('when'):
        today=site_settings()['today']
        period=request.args['when']
        start=today
        if period=='weekend':
            d=datetime.fromisoformat(today).date();start=(d+timedelta(days=(5-d.weekday())%7 if d.weekday()<5 else 0)).isoformat()
            end=(datetime.fromisoformat(start).date()+timedelta(days=1 if d.weekday()!=6 else 0)).isoformat()
        else:end=(datetime.fromisoformat(today).date()+timedelta(days=6)).isoformat()
        if period in ('week','weekend'):
            query=query.where(Item.starts!='',Item.starts<=end,or_(Item.ends>=start,db.and_(Item.ends=='',Item.starts>=start)))
        elif period=='upcoming':query=query.where(Item.starts!='',or_(Item.ends>=today,db.and_(Item.ends=='',Item.starts>=today)))
        elif period=='undated':query=query.where(Item.category=='活動課程',Item.starts=='')
        elif period=='past':query=query.where(Item.ends!='',Item.ends<today)
        else:return jsonify(error='未知日期篩選'),400
    q=request.args.get('q','').strip()[:120]
    if q:
        safe=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        query=query.where(or_(*(c.ilike(f'%{safe}%',escape='\\') for c in (Item.title,Item.summary,Item.location))))
    try: page=max(1,min(int(request.args.get('page',1)),10000))
    except ValueError: return jsonify(error='page 必須是整數'),400
    total=db.session.scalar(select(db.func.count()).select_from(query.subquery()))
    rows=db.session.execute(query.order_by(Item.published.desc(),Item.synced.desc(),Item.id).offset((page-1)*24).limit(24)).scalars()
    return jsonify(items=[r.data() for r in rows], total=total,page=page,pages=(total+23)//24)

@app.get('/api/overview')
def overview():
    district=site_settings()['district'];today=site_settings()['today']
    def count(*conditions):return db.session.scalar(select(db.func.count()).select_from(Item).where(*conditions))
    end=(datetime.fromisoformat(today).date()+timedelta(days=6)).isoformat()
    return jsonify(total=count(),local=count(Item.scope=='local'),
        week=count(Item.starts!='',Item.starts<=end,or_(Item.ends>=today,db.and_(Item.ends=='',Item.starts>=today))),
        dated=count(Item.starts!=''),undated=count(Item.category=='活動課程',Item.starts==''))

@app.get('/about')
@app.get('/contact')
@app.get('/privacy')
@app.get('/sources')
def information():
    return render_template('information.html',kind=request.path.strip('/'),source_list=sources())

@app.get('/guides')
def guides():
    from guides import GUIDES
    return render_template('guides.html',guides=GUIDES)

@app.get('/guides/<slug>')
def guide(slug):
    from guides import GUIDES
    g=next((g for g in GUIDES if g['slug']==slug),None)
    if not g:abort(404)
    return render_template('guide.html',guide=g)

@app.get('/events/<item_id>')
def event(item_id):
    row=db.session.get(Item,item_id)
    if not row:abort(404)
    source=next((s for s in sources() if s['id']==row.source),{'name':row.source})
    return render_template('event.html',item=row,source=source)

@app.get('/ads.txt')
def ads_txt():
    s=site_settings()
    if not s['ads_client']:abort(404)
    return Response('google.com, '+s['ads_client'].removeprefix('ca-')+', DIRECT, f08c47fec0942fa0\n',mimetype='text/plain')

@app.get('/robots.txt')
def robots():
    return Response('User-agent: *\nAllow: /\nDisallow: /api/\n',mimetype='text/plain')

@app.get('/sitemap.xml')
def sitemap():
    from guides import GUIDES
    from xml.sax.saxutils import escape
    base=site_settings()['base_url'] or request.url_root.rstrip('/')
    paths=['/','/guides','/about','/contact','/privacy','/sources']+['/guides/'+g['slug'] for g in GUIDES]
    rows=db.session.execute(select(Item.id).limit(1000)).scalars()
    paths+=['/events/'+i for i in rows]
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(base+p)+'</loc></url>' for p in paths)+'</urlset>',mimetype='application/xml')

if __name__=='__main__':
    with app.app_context(): ensure_database()
    app.run(port=int(os.getenv('PORT','5000')))
