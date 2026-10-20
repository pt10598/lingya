import os,unittest
os.environ['DATABASE_URL']='sqlite://'
from app import app,db
from bs4 import BeautifulSoup

class SeniorTests(unittest.TestCase):
 def setUp(self):self.ctx=app.app_context();self.ctx.push();db.create_all();self.c=app.test_client()
 def tearDown(self):db.session.remove();db.drop_all();self.ctx.pop()
 def test_four_primary_actions_and_collapsed_advanced(self):
  s=BeautifulSoup(self.c.get('/').data,'html.parser')
  actions=s.select('#view-tabs button, #view-tabs > a')
  self.assertEqual(len(actions),4)
  self.assertEqual([x.strong.get_text() for x in actions],['有什麼活動','補助福利','生活通知','找公家機關'])
  self.assertFalse(s.select_one('#advanced-filters').has_attr('open'))
  self.assertFalse(s.select_one('#latest-panel').has_attr('open'))
 def test_font_control_and_script_on_all_pages(self):
  for p in ['/','/services','/privacy','/guides/plan-a-weekend']:
   s=BeautifulSoup(self.c.get(p).data,'html.parser')
   self.assertEqual(s.select_one('#font-large').get_text(),'大字')
   self.assertIsNotNone(s.select_one('script[src="/static/reading.js?v=4.0"]'))
   self.assertIsNotNone(s.select_one('a[href="#main-content"]'))
 def test_privacy_discloses_local_font_preference(self):
  self.assertIn('本機儲存',self.c.get('/privacy').get_data(as_text=True))

if __name__=='__main__':unittest.main()
