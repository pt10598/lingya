"""Official-source adapters. No browser automation, no access-control bypass."""
import hashlib
import os
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from app import app, db, Item, ArticleCache, SourceStatus, sources, now, status_key, enrich_record

from settings import site_settings
from content import category, enrich

UA='DistrictTong/2.0 (+contact: '+os.getenv('CRAWLER_CONTACT','not-configured')+')'
MAX_BYTES=20*1024*1024
_robots={}
_last={}

def clean(value):
    return BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True)

def canonical(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname: return ''
    params=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(sorted(params)),''))

def fetch(url, conditional=None, redirects=0):
    host=urlsplit(url).netloc
    root=f'{urlsplit(url).scheme}://{host}'
    if root not in _robots:
        rp=RobotFileParser()
        try:
            r=requests.get(root+'/robots.txt',headers={'User-Agent':UA},timeout=(8,20))
            if r.status_code==200: rp.parse(r.text.splitlines())
            elif r.status_code in (404,410): rp.parse([])
            else: raise RuntimeError('robots.txt 無法確認，稍後重試')
        except requests.RequestException as e: raise RuntimeError('robots.txt 連線失敗') from e
        _robots[root]=rp
    rp=_robots[root]
    if not rp.can_fetch(UA,url): raise RuntimeError('robots.txt 不允許此路徑')
    delay=max(1.0,float(rp.crawl_delay(UA) or rp.crawl_delay('*') or 0))
    wait=delay-(time.monotonic()-_last.get(host,0))
    if wait>0:time.sleep(wait)
    headers={'User-Agent':UA,**(conditional or {})}
    _last[host]=time.monotonic()
    # Redirects are followed explicitly so robots is checked on each target.
    with requests.get(url,headers=headers,timeout=(8,25),stream=True,allow_redirects=False) as r:
        if r.is_redirect:
            
            if redirects>=4:raise RuntimeError('來源重新導向次數過多')
            target=urljoin(url,r.headers.get('Location',''))
            if urlsplit(target).hostname != urlsplit(url).hostname:raise RuntimeError('來源跨網域轉址，請人工確認：'+target)
            return fetch(target,conditional,redirects+1)
        if r.status_code==304:return None,r.headers
        r.raise_for_status()
        parts=[];size=0
        for chunk in r.iter_content(65536):
            size+=len(chunk)
            if size>MAX_BYTES:raise RuntimeError('來源資料超過20MB限制')
            parts.append(chunk)
        data=b''.join(parts)
        encoding=r.encoding if r.encoding and r.encoding.lower()!='iso-8859-1' else 'utf-8'
        return data.decode(encoding,errors='replace'),r.headers

def date(value):
    value=str(value or '').strip()
    m=re.search(r'(?<!\d)(\d{3,4})[-/.年](\d{1,2})[-/.月](\d{1,2})',value)
    if m:
        y,mo,d=map(int,m.groups());y=y+1911 if y<1911 else y
        try:return datetime(y,mo,d).date().isoformat()
        except ValueError:return ''
    try:return parsedate_to_datetime(value).date().isoformat()
    except (ValueError,TypeError,OverflowError):return ''

def classify(title):
    return category(title)

# Matching only article/event fields; never the institution's footer address.
def relevance(src,title,body,location=''):
    site=site_settings()
    if src.get('scope')=='local':
        if src.get('districts') and site['district'] not in src['districts']:return None,None
        return 'local',site['district']+'在地機關發布'
    if any(re.search(re.escape(w),title+' '+body+' '+location,re.I) for w in site['keywords']):return 'local','內容或地址提及'+site['district']
    if re.search(r'高雄市民|全市|設籍高雄|本市市民|本市居民',title+' '+body):return 'citywide','全市適用，資格以原文為準'
    return None,None

def item(src,title,url,body='',published='',starts='',ends='',location=''):
    url=canonical(url);title=clean(title)
    if not url or not title:return None
    body=clean(body);scope,reason=relevance(src,title,body,location)
    if not scope:return None
    prefix='' if site_settings()['district']=='苓雅區' else site_settings()['district']+'|'
    return dict(id=hashlib.sha256((prefix+src['id']+'|'+url).encode()).hexdigest(),source=src['id'],title=title,
                summary=body[:400],url=url,published=date(published),starts=date(starts),ends=date(ends),
                location=clean(location),category=classify(title),scope=scope,reason=reason,synced=now(),_body=body)

def parse_html_list(text,base):
    soup=BeautifulSoup(text,'html.parser');found={}
    for a in soup.select('a[href]'):
        href=urljoin(base,a['href'])
        if not re.search(r'(News_Content|NewsContent|News_Detail|NewsDetail|CityNews_Detail)',href,re.I):continue
        if urlsplit(href).hostname!=urlsplit(base).hostname:continue
        title=a.get('title') or a.get_text(' ',strip=True)
        if len(title)<4:continue
        row=a.find_parent('tr') or a.find_parent('li') or a.parent
        found[canonical(href)]=(title,href,date(row.get_text(' ',strip=True)))
    return list(found.values())

def article(text):
    soup=BeautifulSoup(text,'html.parser')
    for x in soup.select('script,style,nav,footer,header'):x.decompose()
    for selector in ('.essay','.article-content','.news-content','.page-content','.data_midlle', 'article'):
        el=soup.select_one(selector)
        if el:return el.get_text(' ',strip=True)
    # Do not fall back to full page: its footer could falsely match Lingya.
    return ''

def detail(url):
    key=hashlib.sha256(canonical(url).encode()).hexdigest()
    c=db.session.get(ArticleCache,key)
    if c and time.time()-c.checked<1800:return c.text
    headers={}
    if c and c.etag:headers['If-None-Match']=c.etag
    if c and c.modified:headers['If-Modified-Since']=c.modified
    body,h=fetch(url,headers)
    if not c:c=ArticleCache(id=key);db.session.add(c)
    if body is not None:
        c.text=body;c.etag=h.get('ETag');c.modified=h.get('Last-Modified')
    c.checked=time.time()
    return c.text or ''

def html_source(src,text):
    soup=BeautifulSoup(text,'html.parser');lists=[(src['url'],text)];seen={src['url']}
    for a in soup.select('a[href]'):
        if a.get_text(' ',strip=True) in src.get('selectors',[]):
            u=canonical(urljoin(src['url'],a['href']))
            if u not in seen and urlsplit(u).hostname==urlsplit(src['url']).hostname:
                seen.add(u)
                if len(lists)>=5:break
                try:
                    body,_=fetch(u);lists.append((u,body))
                except Exception as e:src.setdefault('_warnings',[]).append(str(e)[:100])
    links={}
    for base,body in lists:
        for title,url,pub in parse_html_list(body,base):links[canonical(url)]=(title,url,pub)
    if not links:raise RuntimeError('未解析到公告，可能版型變更；保留舊資料')
    records=[]
    for title,url,pub in list(links.values())[:int(os.getenv('MAX_ARTICLES_PER_SOURCE','40'))]:
        # New articles immediately; existing detail pages revalidated every 30 min.
        try:text=detail(url)
        except Exception as e:
            src.setdefault('_warnings',[]).append(str(e)[:100]);continue
        soup=BeautifulSoup(text,'html.parser')
        heading=soup.select_one('.data_midlle h2, .data_midlle h3, .data_midlle_news_box01')
        if heading and len(heading.get_text(strip=True))>3:title=heading.get_text(' ',strip=True)
        dateline=soup.select_one('.data_midlle .nosnippet')
        pub=pub or (date(dateline.get_text(' ',strip=True)) if dateline else '')
        data=item(src,title,url,article(text),pub)
        if data:records.append(data)
    return records

def travel(src,text):
    soup=BeautifulSoup(text,'xml');rows=soup.find_all(lambda x:x.name and x.name.lower()=='info')
    if not rows:raise RuntimeError('XML活動欄位不符，請確認來源')
    out=[]
    for r in rows:
        d={k.lower():v for k,v in r.attrs.items()}
        for c in r.find_all(recursive=False):d[c.name.lower()]=c.get_text(' ',strip=True)
        # Never substitute feed URL for the original event page.
        url=d.get('website') or d.get('url')
        if not url and re.fullmatch(r'C2_397000000A_\d+',d.get('id','')):
            url='https://khh.travel/zh-tw/event/calendardetail/'+str(int(d['id'].rsplit('_',1)[1]))+'/'
        if not url:continue
        v=item(src,d.get('name'),url,d.get('description',''),d.get('changetime',''),d.get('start',''),d.get('end',''),d.get('add','')+' '+d.get('location',''))
        if v:
            v['category']='活動課程';out.append(v)
    return out

def culture(src,text):
    import json
    data=json.loads(text)
    if not isinstance(data,list):raise RuntimeError('藝文JSON格式不是陣列')
    out=[]
    for d in data:
        shows=d.get('showInfo') or []
        loc=' '.join(str(x.get('location',''))+' '+str(x.get('locationName','')) for x in shows)
        body=d.get('descriptionFilterHtml','')
        if site_settings()['city'] not in loc and not any(w in loc+str(body) for w in site_settings()['keywords']):continue
        url=d.get('sourceWebPromote') or d.get('webSales')
        if not url:continue
        v=item(src,d.get('title'),url,body,d.get('editModifyDate',''),d.get('startDate',''),d.get('endDate',''),loc)
        if v:
            v['category']='活動課程';out.append(v)
    return out

def sync_one(src):
    with app.app_context():
        s=db.session.get(SourceStatus,status_key(src['id'])) or SourceStatus(id=status_key(src['id']))
        s.checked=now();db.session.add(s)
        try:
            conditional={}
            if src['kind']!='html':
                if s.etag:conditional['If-None-Match']=s.etag
                if s.modified:conditional['If-Modified-Since']=s.modified
            text,headers=fetch(src['url'],conditional)
            if text is None:
                s.state='成功';s.success=now();s.message='來源未變更（304）'
            else:
                adapter={'html':html_source,'travel_xml':travel,'culture_json':culture}[src['kind']]
                records=adapter(src,text)
                for data in records:
                    full_body=data.pop('_body','')
                    existing=db.session.get(Item,data['id'])
                    if existing:
                        for k,v in data.items():setattr(existing,k,v)
                    else:
                        existing=Item(**data);db.session.add(existing)
                    db.session.flush()
                    enrich_record(existing,full_body)
                s.state='成功';s.success=now();s.count=len(records)
                s.message=f'本輪同步 {len(records)} 則符合條件資訊'
                if src.get('_warnings'):
                    s.state='部分成功';s.message+='；部分頁面失敗：'+'；'.join(src['_warnings'][:2])
                s.etag=headers.get('ETag');s.modified=headers.get('Last-Modified')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            s=db.session.get(SourceStatus,status_key(src['id'])) or SourceStatus(id=status_key(src['id']))
            s.checked=now();s.state='失敗';s.message=str(e)[:450]
            db.session.add(s);db.session.commit()
        return src['id'],s.state,s.message

def sync_all():
    from concurrent.futures import ThreadPoolExecutor
    enabled=[s for s in sources() if s.get('enabled')]
    # Separate hosts concurrently. Each adapter serializes its own page requests.
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(sync_one,enabled))
