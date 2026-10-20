import os,json,unittest
os.environ['DATABASE_URL']='sqlite://'
from datetime import date,timedelta
from unittest.mock import patch
from app import app,db,Item,ItemExtra,ArticleCache,enrich_record,rebuild_existing
from content import enrich,category,tidy_location

class V3Tests(unittest.TestCase):
 def setUp(self):self.ctx=app.app_context();self.ctx.push();db.create_all();self.c=app.test_client()
 def tearDown(self):db.session.remove();db.drop_all();self.ctx.pop()
 def row(self,id,**kw):
  data=dict(id=id,source='lingya-office',title='測試活動',summary='',url='https://example.org/'+id,published='2026-10-20',starts='',ends='',location='',category='活動課程',scope='local',synced='2026-10-20T00:00:00+00:00');data.update(kw);r=Item(**data);db.session.add(r);db.session.flush();return r
 def test_welfare_and_competition_classification(self):
  self.assertEqual(category('116年弱勢兒少生活扶助審核標準'),'補助福利')
  self.assertEqual(category('衛星數位應用創新大賽'),'活動課程')
  self.assertEqual(category('11月戶政事務所暫停服務日期'),'交通生活')
 def test_labeled_dates_not_registration_date(self):
  v=enrich('親子活動','報名截止：115年10月22日 活動日期：115年10月24日 活動地點：高雄市苓雅區某場館')
  self.assertEqual(v['starts'],'2026-10-24');self.assertEqual(v['extra']['deadline'],'2026-10-22')
  self.assertEqual(v['extra']['place_label'],'苓雅區地點')
  self.assertEqual(enrich('親子活動','報名截止：115年10月22日')['starts'],'')
 def test_explicit_range_and_unknown_date(self):
  self.assertEqual(enrich('音樂活動','活動日期：115年10月24日至115年10月25日')['ends'],'2026-10-25')
  self.assertEqual(enrich('活動','今天開跑，報名到月底')['starts'],'')
  self.assertEqual(enrich('活動','活動日期：115年2月31日')['starts'],'')
  self.assertEqual(enrich('活動','活動日期：115年10月24日至10月25日')['starts'],'')
  self.assertEqual(category('健康講座活動'),'活動課程')
 def test_location_cleanup_and_no_office_location_inference(self):
  self.assertEqual(tidy_location('高雄市苓雅區某場館 to see the official site'),'高雄市苓雅區某場館')
  self.assertEqual(enrich('活動','本區公所發布')['extra']['place_label'],'地點待確認')
  self.assertEqual(enrich('活動','活動地點：線上視訊')['extra']['place_label'],'線上活動')
 def test_full_text_search_and_return_details(self):
  r=self.row('body');enrich_record(r,'前文'+('測試'*250)+'搜尋後段關鍵詞');db.session.commit()
  self.assertEqual(self.c.get('/api/news?q=後段關鍵詞').json['total'],1)
  page=self.c.get('/events/body?back=/?view=events%26q=親子').get_data(as_text=True)
  self.assertIn('回到原篩選結果',page)
  page=self.c.get('/events/body?back=https://evil.example/').get_data(as_text=True)
  self.assertNotIn('href="https://evil.example/',page)
 def test_event_default_hides_past_preserves_unknown_and_sorts_date(self):
  today=date.today();future=(today+timedelta(days=5)).isoformat();past=(today-timedelta(days=1)).isoformat()
  self.row('past',starts=past,ends=past);self.row('future',starts=future,ends=future);self.row('unknown');db.session.commit()
  rows=self.c.get('/api/news?view=events').json['items']
  self.assertEqual([r['id'] for r in rows],['future','unknown'])
  self.assertEqual(self.c.get('/api/news?view=events&when=past').json['total'],1)
 def test_revision_ignores_sync_time_but_detects_content_change(self):
  r=self.row('version');db.session.commit();first=self.c.get('/api/revision').json
  r.synced='2026-10-21T00:00:00+00:00';db.session.commit();self.assertEqual(self.c.get('/api/revision').json,first)
  r.title='更新後的活動';db.session.commit();self.assertNotEqual(self.c.get('/api/revision').json,first)
 def test_backfill_updates_existing_without_deleting(self):
  self.row('kept',title='生活扶助申請標準',category='公告消息');db.session.commit()
  self.assertEqual(rebuild_existing(),1);self.assertEqual(db.session.get(Item,'kept').category,'補助福利')
  self.assertIsNotNone(db.session.get(ItemExtra,'kept'))
 def test_page_clamp_and_secondary_pages(self):
  self.row('one');db.session.commit()
  self.assertEqual(self.c.get('/api/news?page=999').json['page'],1)
  self.assertEqual(self.c.get('/services').status_code,200)
  self.assertEqual(self.c.get('/api/news?view=invalid').status_code,400)
 def test_collector_saves_full_body_without_public_body_field(self):
  from collector import sync_one
  src={'id':'unit-test','name':'測試來源','scope':'local','kind':'html','url':'https://example.org/','selectors':[]}
  homepage='<a href="News_Content.aspx?s=1">健康親子講座活動</a>'
  detail='<div class="data_midlle"><div class="data_midlle_news_box01">健康親子講座活動</div><p>活動日期：115年10月24日 活動地點：高雄市苓雅區某場館</p></div>'
  with patch('collector.fetch',return_value=(homepage,{})),patch('collector.detail',return_value=detail):
   result=sync_one(src)
  self.assertEqual(result[1],'成功')
  row=db.session.query(Item).filter_by(source='unit-test').one()
  self.assertEqual(row.starts,'2026-10-24');self.assertIsNotNone(db.session.get(ItemExtra,row.id))
  self.assertNotIn('_body',row.data())
 def test_original_page_has_mobile_filter_and_clear(self):
  page=self.c.get('/').get_data(as_text=True)
  for x in ['更多選擇','清除選擇，回到首頁','最近活動','重要生活通知','有新消息，按這裡更新','state.js?v=5.0']:self.assertIn(x,page)

if __name__=='__main__':unittest.main()
