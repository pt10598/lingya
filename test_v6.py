import os,unittest
os.environ['DATABASE_URL']='sqlite://'
from app import app,db
from khcc import parse_detail,identity,links
from urllib.parse import parse_qs,urlsplit
SRC={'id':'kaohsiung-culture','scope':'city'}
BASE='https://khcc.kcg.gov.tw/rwd_home03.aspx?ID=%24M102&EXEC=D&DATA=4318'
def page(place='至真堂一館',start='115/10/16',end='115/10/27',body='展覽介紹'):
 return f'<span style="font-size:160%">會員聯展</span><div class="row"><div>展覽地點：{place}</div><div>開始日期：{start}</div><div>截止日期：{end}</div></div><div><div id="mydesc">{body}</div></div><footer>高雄市苓雅區五福一路67號</footer>'
class CultureTests(unittest.TestCase):
 def test_exhibition_fields(self):
  r=parse_detail(SRC,BASE,page());self.assertEqual((r['starts'],r['ends']),('2026-10-16','2026-10-27'));self.assertIn('苓雅區',r['location']);self.assertEqual(r['category'],'活動課程')
 def test_footer_does_not_make_other_venue_local(self):self.assertIsNone(parse_detail(SRC,BASE,page(place='大東展覽館')))
 def test_unknown_date_is_not_invented(self):
  r=parse_detail(SRC,BASE,page(start='待定',end='待定'));self.assertEqual((r['starts'],r['ends']),('',''))
 def test_missing_body_is_failure(self):
  with self.assertRaises(RuntimeError):parse_detail(SRC,BASE,'<footer>苓雅區</footer>')
 def test_positive_id_navigation_is_deduplicated(self):self.assertEqual(identity(BASE+'&AP=one'),identity(BASE+'&AP=two'))
 def test_performance_dates_not_merged(self):self.assertNotEqual(identity(BASE.replace('4318','-43')+'&AP=date1'),identity(BASE.replace('4318','-43')+'&AP=date2'))
 def test_reject_external_or_list_links(self):
  self.assertEqual(identity(BASE.replace('khcc.kcg.gov.tw','other.example')),'');self.assertEqual(identity(BASE.replace('EXEC=D','EXEC=L')),'')
 def test_disabled_source_is_not_reported_as_failure(self):
  with app.app_context():
   db.create_all();c=app.test_client();d=c.get('/api/sources').json
   s=next(x for x in d if x['id']=='culture-events');self.assertEqual(s['status'],'暫停收錄');db.session.remove();db.drop_all()
if __name__=='__main__':unittest.main()
