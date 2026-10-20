import os
os.environ['DATABASE_URL']='sqlite://'
from unittest.mock import patch
import unittest
from datetime import date,timedelta
from app import app,db,Item,ensure_database
from settings import site_settings

class V2Tests(unittest.TestCase):
    def setUp(self):
        self.ctx=app.app_context();self.ctx.push();ensure_database();self.c=app.test_client()
    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()
    def row(self,i,**data):
        v=dict(id=i,source='lingya-office',title='測試活動',summary='測試資料不會隨部署包提供',url='https://example.org/'+i,published='2026-10-20',category='活動課程',scope='local',synced='2026-10-20T00:00:00+00:00',starts='',ends='');v.update(data);db.session.add(Item(**v))
    def test_page_routes_and_no_ads_by_default(self):
        for p in ['/','/about','/privacy','/contact','/sources','/guides','/guides/plan-a-weekend','/guides/read-a-benefit-notice','/guides/check-official-information','/robots.txt','/sitemap.xml']:
            r=self.c.get(p);self.assertEqual(r.status_code,200,p)
            self.assertNotIn(b'pagead/js/adsbygoogle.js',r.data)
        self.assertEqual(self.c.get('/ads.txt').status_code,404)
        self.assertEqual(self.c.get('/guides/missing').status_code,404)
    def test_date_filter_includes_ongoing_not_past_or_undated(self):
        today=date.fromisoformat(site_settings()['today'])
        self.row('ongoing',starts=(today-timedelta(days=2)).isoformat(),ends=(today+timedelta(days=2)).isoformat())
        self.row('one-day',starts=today.isoformat())
        self.row('past',starts=(today-timedelta(days=5)).isoformat(),ends=(today-timedelta(days=1)).isoformat())
        self.row('unknown');db.session.commit()
        self.assertEqual(self.c.get('/api/news?when=week').json['total'],2)
        self.assertEqual(self.c.get('/api/news?when=undated').json['total'],1)
        self.assertEqual(self.c.get('/api/news?when=past').json['total'],1)
        self.assertEqual(self.c.get('/api/overview').json['week'],2)
        self.assertEqual(self.c.get('/api/news?when=bad').status_code,400)
    def test_detail_and_sitemap(self):
        self.row('one');db.session.commit()
        self.assertEqual(self.c.get('/events/one').status_code,200)
        self.assertIn(b'https://example.org/one',self.c.get('/events/one').data)
        self.assertIn(b'/events/one',self.c.get('/sitemap.xml').data)
        self.assertEqual(self.c.get('/events/missing').status_code,404)
    def test_verification_without_ads_loading(self):
        with patch.dict(os.environ,{'ADSENSE_CLIENT':'ca-pub-1234567890123456','ADSENSE_ENABLED':'0'}):
            page=self.c.get('/').data
            self.assertIn(b'google-adsense-account',page)
            self.assertNotIn(b'pagead/js/adsbygoogle.js',page)
            self.assertIn(b'google.com, pub-1234567890123456, DIRECT',self.c.get('/ads.txt').data)
    def test_manual_ads_only_on_guides(self):
        with patch.dict(os.environ,{'ADSENSE_CLIENT':'ca-pub-1234567890123456','ADSENSE_SLOT':'1234567890','ADSENSE_ENABLED':'1'}):
            self.assertIn(b'pagead/js/adsbygoogle.js',self.c.get('/guides/plan-a-weekend').data)
            self.assertNotIn(b'pagead/js/adsbygoogle.js',self.c.get('/').data)
    def test_reinitialize_keeps_existing_data(self):
        self.row('kept');db.session.commit();ensure_database()
        self.assertIsNotNone(db.session.get(Item,'kept'))

if __name__=='__main__':unittest.main()
