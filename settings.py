import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

def site_settings():
    district=os.getenv('DISTRICT_NAME','苓雅區').strip()
    if not district or len(district)>20:raise ValueError('DISTRICT_NAME 長度不正確')
    short=district[:-1] if district.endswith('區') else district
    words=[district]
    words.extend(x.strip() for x in os.getenv('DISTRICT_KEYWORDS','Lingya' if district=='苓雅區' else '').split(',') if x.strip())
    client=os.getenv('ADSENSE_CLIENT','').strip()
    if client and not re.fullmatch(r'ca-pub-\d{16}',client):raise ValueError('ADSENSE_CLIENT 格式應為 ca-pub- 加上16位數字')
    slot=os.getenv('ADSENSE_SLOT','').strip()
    if slot and not re.fullmatch(r'\d{5,20}',slot):raise ValueError('ADSENSE_SLOT 應為數字廣告單元 ID')
    email=os.getenv('CONTACT_EMAIL','irataieddie@gmail.com').strip()
    if email and not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',email):raise ValueError('CONTACT_EMAIL 格式不正確')
    return {'name':os.getenv('SITE_NAME',short+'通'),'district':district,'short':short,'city':'高雄市',
            'keywords':words,'contact':email,'operator':os.getenv('SITE_OPERATOR','Eddie'),
            'base_url':os.getenv('SITE_URL','').rstrip('/'),'ads_client':client,'ads_slot':slot,
            'ads_enabled':bool(client and slot and os.getenv('ADSENSE_ENABLED')=='1'),
            'today':datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()}
