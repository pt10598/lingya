"""Conservative extraction from explicit fields; unknown dates/places remain unknown."""
import re
from datetime import date

DATE=r'(?:民國\s*)?(\d{3,4})\s*(?:年|[-/.])\s*(\d{1,2})\s*(?:月|[-/.])\s*(\d{1,2})\s*日?'

def iso(groups):
    y,m,d=map(int,groups);y=y+1911 if y<1911 else y
    try:return date(y,m,d).isoformat()
    except ValueError:return ''

def category(title):
    rules=[('補助福利',r'補助|津貼|福利|補貼|扶助|救助|減免|年金'),('交通生活',r'交通|施工|停水|停電|道路|垃圾|暫停服務|休館|停止受理'),('活動課程',r'活動|課程|講座|展覽|演出|報名|比賽|大賽|音樂|工作坊|嘉年華|巡迴展'),('健康衛生',r'健康|衛生|疫苗|篩檢|登革熱'),('徵才招考',r'徵才|招考|徵人|職缺')]
    return next((c for c,p in rules if re.search(p,title)),'公告消息')

def tidy_location(value):
    s=re.sub(r'to see the official site|see (?:the )?official (?:site|website)','',str(value or ''),flags=re.I)
    return re.sub(r'\s+',' ',s).strip(' ,，;；')

def labeled(body,labels,limit=110):
    p='(?:'+'|'.join(labels)+r')\s*[：:]\s*([^\n]{1,'+str(limit)+'})'
    m=re.search(p,body)
    if not m:return ''
    return re.split(r'(?:活動時間|活動日期|活動地點|報名方式|報名日期|報名期間|報名截止|申請期限|費用|承辦單位|主辦單位|聯絡方式|相關連結)\s*[：:]',m.group(1))[0].strip(' 。；;')

def enrich(title,body,starts='',ends='',location='',existing_category='公告消息',district='苓雅區'):
    body=str(body or '')
    result={'category':category(title),'starts':starts or '','ends':ends or '','location':tidy_location(location)}
    # Preserve explicit activity category from structured feeds.
    if existing_category=='活動課程' and starts:result['category']='活動課程'
    origin='來源活動欄位' if starts else ''
    if not starts and result['category'] in ('活動課程','健康衛生'):
        value=labeled(body,['活動日期','舉辦日期','演出日期','上課日期','活動時間'],150)
        matches=list(re.finditer(DATE,value))
        dates=[iso(m.groups()) for m in matches]
        valid=bool(dates) and all(dates)
        tail=value[matches[0].end():] if len(matches)==1 else ''
        ambiguous=bool(re.search(r'(?:至|到|～|~|[-—–、])\s*(?:\d{1,2}(?:月|/)\d{1,2}日?|\d{1,2}日)',tail))
        if valid and len(dates)==1 and not ambiguous:
            result['starts']=result['ends']=dates[0];origin='正文明確活動日期'
        elif valid and len(dates)==2 and dates[1]>=dates[0] and re.search(r'至|到|～|~|—|–',value):
            result['starts'],result['ends']=dates;origin='正文明確活動日期區間'
    if result['starts'] and result['category']=='健康衛生':result['category']='活動課程'
    if not result['location']:
        result['location']=tidy_location(labeled(body,['活動地點','上課地點','演出地點','集合地點','辦理地點'],100))
    if re.search('線上|網路直播|視訊',result['location']):place='線上活動'
    elif district in result['location']:place=district+'地點'
    elif result['location']:place='其他／待核對地點'
    else:place='地點待確認'
    deadline_text=labeled(body,['報名截止','報名期限','申請截止','申請期限','受理截止'],120)
    found=[iso(m.groups()) for m in re.finditer(DATE,deadline_text)];found=[d for d in found if d]
    deadline=found[-1] if found else ''
    fee=labeled(body,['活動費用','報名費用','參加費用'],70)
    topics=[]
    for name,p in [('健康','健康|篩檢|疫苗'),('親子兒少','親子|兒少|兒童|幼兒|子女'),('長者','長者|銀髮|老人|敬老'),('身障','身心障礙|身障'),('藝文','展覽|藝文|音樂|演出|文化'),('運動','運動|健身|瑜珈'),('住宅','住宅|租金|租屋'),('就業','就業|職訓|求職')]:
        if re.search(p,title):topics.append(name)
    result['extra']={'date_origin':origin,'place_label':place,'deadline':deadline,'fee':fee,'topics':topics,'version':3}
    return result
