import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from deep_translator import GoogleTranslator
import concurrent.futures

# [모바일 최적화 1] 사이드바를 처음에 숨겨서 좁은 화면을 넓게 쓰게 함
st.set_page_config(
    page_title="Fashion News", 
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="collapsed" 
)

# --- CSS로 모바일에서 더 앱처럼 보이게 꾸미기 ---
st.markdown("""
    <style>
    /* 폰트 크기 조정 및 여백 최적화 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
    }
    /* 뉴스 카드 디자인 */
    div[data-testid="stContainer"] {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
    }
    /* 모바일에서 링크 버튼 잘 보이게 */
    a {
        text-decoration: none;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 사이트 목록
# -------------------------------------------------------------------
site_list = {
    "Hypebeast KR (하입비스트)": "https://news.google.com/rss/search?q=site:hypebeast.kr/fashion&hl=ko&gl=KR&ceid=KR:ko",
    "Dazed Digital (데이즈드)": "https://news.google.com/rss/search?q=site:dazeddigital.com/fashion&hl=en-US&gl=US&ceid=US:en",
    "Vogue US (보그 미국)": "https://news.google.com/rss/search?q=site:vogue.com/fashion&hl=en-US&gl=US&ceid=US:en",
    "Highsnobiety (하이스노바이어티)": "https://news.google.com/rss/search?q=site:highsnobiety.com&hl=en-US&gl=US&ceid=US:en"
}

# -------------------------------------------------------------------
# 사이드바 (설정)
# -------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정 메뉴")
    selected_site_name = st.radio("채널 선택", list(site_list.keys()))
    st.write("---")
    enable_translation = st.toggle("🇰🇷 자동 번역", value=True)
    st.write("---")
    limit_option = st.slider("기사 개수", 10, 50, 20)
    days_option = st.slider("기간 (일)", 1, 30, 7)
    st.info("👆 메뉴를 닫으면 화면이 넓어집니다.")

# -------------------------------------------------------------------
# 함수
# -------------------------------------------------------------------
def process_single_news(news_item):
    title = news_item['title']
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    
    if enable_translation:
        try:
            # 한글이 포함되지 않은 경우에만 번역
            if not any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7a3' for char in title):
                translator = GoogleTranslator(source='auto', target='ko')
                translated = translator.translate(title)
                if translated:
                    title = translated
        except:
            pass 
    news_item['title'] = title
    return news_item

# -------------------------------------------------------------------
# 메인 화면
# -------------------------------------------------------------------
# [모바일 최적화 2] 제목을 간결하게
st.title(f"📱 {selected_site_name.split('(')[0]}")
st.caption("왼쪽 상단 화살표(>)를 눌러 설정을 변경하세요.")

# [모바일 최적화 3] 엄지손가락으로 누르기 쉬운 큰 버튼
if st.button("뉴스 새로고침 🔄", type="primary"):
    status_area = st.empty()
    status_area.info('뉴스를 불러오는 중...')
    
    try:
        rss_url = site_list[selected_site_name]
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(rss_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('item')
        
        raw_news_list = []
        for item in items:
            title_text = item.find('title').text
            if "Page " in title_text or "Category" in title_text: continue

            date_tag = item.find('pubdate')
            article_date_obj = datetime.now()
            display_date = ""
            is_recent = False
            
            if date_tag:
                try:
                    article_date_obj = parsedate_to_datetime(date_tag.text)
                    now = datetime.now(article_date_obj.tzinfo)
                    if (now - article_date_obj).days <= days_option:
                        is_recent = True
                        # 모바일에서는 날짜를 짧게 표시 (2024-02-14)
                        display_date = article_date_obj.strftime("%Y-%m-%d")
                except:
                    is_recent = True 
            else:
                is_recent = True

            if is_recent:
                if item.find('link').next_sibling:
                    link = item.find('link').next_sibling.strip()
                else:
                    link = item.find('link').text
                if "/page/" in link: continue

                raw_news_list.append({
                    'title': title_text,
                    'link': link,
                    'date_str': display_date,
                    'real_date': article_date_obj 
                })

        raw_news_list.sort(key=lambda x: x['real_date'], reverse=True)
        target_news = raw_news_list[:limit_option]

        if target_news:
            final_news_list = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = executor.map(process_single_news, target_news)
                for result in results:
                    final_news_list.append(result)
            
            status_area.empty() # 로딩 문구 삭제
            
            # [모바일 최적화 4] 모바일은 1열로 보는 게 편하므로 컬럼 제거
            for news in final_news_list:
                with st.container(border=True):
                    st.subheader(news['title'])
                    st.caption(f"📅 {news['date_str']}")
                    st.link_button("기사 읽기 👉", news['link'], use_container_width=True)
        else:
            status_area.warning("새로운 소식이 없습니다.")
            
    except Exception as e:
        st.error(f"에러: {e}")