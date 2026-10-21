"""Culture Bureau adapter: verified public HTML fields, no footer matching."""
import re
from urllib.parse import urljoin,urlsplit,parse_qsl,urlencode,urlunsplit
from bs4 import BeautifulSoup

VENUES=('至德堂','至善廳','至真堂','至美軒')

def identity(url):
    p=urlsplit(url);q=dict(parse_qsl(p.query))
    if p.hostname!='khcc.kcg.gov.tw' or p.path.lower() not in ('/rwd_home02.aspx','/rwd_home03.aspx'):return ''
    if q.get('EXEC')!='D' or not re.fullmatch(r'-?\d+',q.get('DATA','')):return ''
    # AP is navigation state on positive IDs; negative performance IDs need the date.
    keys=['ID','IDK','EXEC','DATA']+(['AP'] if int(q['DATA'])<0 else [])
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(sorted((k,q[k]) for k in keys if k in q)),''))

def links(text,base):
    soup=BeautifulSoup(text,'html.parser');out={}
    for a in soup.select('a[href]'):
        url=identity(urljoin(base,a['href']))
        if not url:continue
        q=dict(parse_qsl(urlsplit(url).query))
        if q.get('ID') not in ('$M102','$5101','$5400','$5501'):continue
        title=a.get('title') or a.get_text(' ',strip=True)
        if len(title)<4:continue
        out.setdefault(url,title)
    # Interleave venue events and announcements so the request cap covers both.
    from itertools import zip_longest
    events=[x for x in out.items() if dict(parse_qsl(urlsplit(x[0]).query)).get('ID')=='$M102']
    news=[x for x in out.items() if x not in events]
    return [x for pair in zip_longest(events,news) for x in pair if x]

def parse_detail(src,url,text,fallback=''):
    from collector import item,date
    soup=BeautifulSoup(text,'html.parser');desc=soup.select_one('#mydesc')
    if desc is None:raise RuntimeError('文化局正文欄位變更，保留舊資料')
    title_el=soup.select_one('span[style*="160%"],h2.margin-bot-30')
    title=title_el.get_text(' ',strip=True) if title_el else fallback
    row=desc.parent.find_previous_sibling('div')
    fields=row.get_text('\n',strip=True) if row else ''
    body=desc.get_text('\n',strip=True)
    def field(label):
        m=re.search('(?:'+label+r')\s*[：:]\s*([^\n]+)',fields)
        return m.group(1).strip() if m else ''
    q=dict(parse_qsl(urlsplit(url).query));event=q.get('ID')=='$M102'
    location=field('展覽地點|演出地點|活動地點') if event else ''
    # These named halls are at Kaohsiung Cultural Center in Lingya, not all KHCC venues.
    if any(location.startswith(v) for v in VENUES):location='高雄市苓雅區文化中心／'+location
    starts=ends=''
    if event:
        starts=date(field('開始日期'));ends=date(field('截止日期'))
        if not starts:
            value=field('演出時間');dates=re.findall(r'\d{3,4}[/.-]\d{1,2}[/.-]\d{1,2}',value)
            if len(dates)==1:starts=ends=date(dates[0])
        if starts and not ends:ends=starts
        if starts and ends and ends<starts:starts=ends=''
    # City eligibility is based on article text, never the bureau's footer address.
    if re.search(r'本市立案|戶籍設於本市|設籍本市',body):body+='\n適用範圍提示：涉及高雄市民或本市團體資格，請依原文確認。'
    result=item(src,title,url,fields+'\n'+body,'',starts,ends,location)
    if result and event:result['category']='活動課程'
    return result

def collect(src,text):
    from collector import detail
    out=[];candidates=links(text,src['url'])
    if not candidates:raise RuntimeError('文化局清單未解析到消息，可能版型變更')
    import os
    for url,title in candidates[:min(40,int(os.getenv('MAX_ARTICLES_PER_SOURCE','40')))]:
        try:
            row=parse_detail(src,url,detail(url),title)
            if row:out.append(row)
        except Exception as e:src.setdefault('_warnings',[]).append(str(e)[:100])
    if candidates and not out and src.get('_warnings') and len(src['_warnings'])>=len(candidates[:min(40,int(os.getenv('MAX_ARTICLES_PER_SOURCE','40')))]):
        raise RuntimeError('文化局詳細頁全數讀取失敗：'+src['_warnings'][0])
    return out
