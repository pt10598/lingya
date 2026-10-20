import os
os.environ['DATABASE_URL']='sqlite://'
import unittest
from app import app, db, Item
from collector import canonical, date, relevance, parse_html_list, travel, culture

class AppTests(unittest.TestCase):
    def setUp(self):
        self.ctx=app.app_context();self.ctx.push();db.create_all();self.client=app.test_client()
    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()
    def test_relevance_uses_fields_not_city_name(self):
        src={'scope':'city'}
        self.assertEqual(relevance(src,'活動','高雄左營區')[0],None)
        self.assertEqual(relevance(src,'活動','', '高雄苓雅區')[0],'local')
        self.assertEqual(relevance(src,'高雄市民可申請','')[0],'citywide')
    def test_dates_and_canonical(self):
        self.assertEqual(date('115-10-20'),'2026-10-20')
        self.assertEqual(date('2026-02-31'),'')
        self.assertEqual(canonical('javascript:alert(1)'),'')
        self.assertEqual(canonical('https://example.org/n?s=2&utm_source=x#abc'),'https://example.org/n?s=2')
    def test_article_list_and_original_url(self):
        rows=parse_html_list('<tr><td>115-10-20</td><td><a href="News_Content.aspx?s=1">苓雅活動公告</a></td></tr>','https://lingya.kcg.gov.tw/')
        self.assertEqual(rows[0][2],'2026-10-20')
        self.assertIn('s=1',rows[0][1])
    def test_travel_official_detail_url(self):
        rows=travel({'id':'travel','scope':'city'},'<XML_Head><Info Id="C2_397000000A_007904" Name="鹹酥雞嘉年華" Add="高雄市苓雅區" Start="2026/10/24" /></XML_Head>')
        self.assertEqual(rows[0]['url'],'https://khh.travel/zh-tw/event/calendardetail/7904/')
        self.assertEqual(rows[0]['starts'],'2026-10-24')
    def test_api_filter_page_and_empty(self):
        db.session.add(Item(id='1',source='test',title='苓雅活動',summary='親子',url='https://example.org/a',published='2026-10-20',category='活動課程',scope='local',synced='2026-10-20T00:00:00+00:00'))
        db.session.commit()
        self.assertEqual(self.client.get('/api/news?q=親子').json['total'],1)
        self.assertEqual(self.client.get('/api/news?q=%25').json['total'],0)
        self.assertEqual(self.client.get('/api/news?scope=citywide').json['total'],0)
        self.assertEqual(self.client.get('/api/news?page=no').status_code,400)
        self.assertEqual(self.client.get('/api/agencies/invalid/news').status_code,404)
        self.assertEqual(self.client.get('/').status_code,200)

if __name__=='__main__':unittest.main()
