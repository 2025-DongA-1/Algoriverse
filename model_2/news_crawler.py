import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from tqdm import tqdm

# ==============================================================================
# [설정] 집에서 돌릴 때는 넉넉하게 긁어도 됩니다!
KEYWORDS = ["김건희 특검", "채상병 특검", "금투세 폐지", "의대 증원", "탈원전", "이재명 재판", "검수완박"]
PAGES_PER_KEYWORD = 5  # 키워드당 5페이지 (약 50개씩)

# [언론사 매핑]
PRESS_MAP = {
    "조선": 1, "중앙": 1, "동아": 1, "문화": 1, "한국경제": 1, "매일경제": 1, "데일리안": 1,
    "한겨레": 0, "경향": 0, "오마이": 0, "프레시안": 0, "미디어오늘": 0, "노컷": 0
}
# ==============================================================================

headers = {
    # 로봇이 아닌 척 위장하는 주민등록증
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

results = []

print(f"🚀 [로컬 PC 버전] 크롤링을 시작합니다...")

for keyword in KEYWORDS:
    search_query = keyword + " 사설"
    print(f"\n🔍 검색어: {search_query}")
    
    for page in tqdm(range(PAGES_PER_KEYWORD)):
        start = page * 10 + 1
        url = f"https://search.naver.com/search.naver?where=news&query={search_query}&start={start}"
        
        try:
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.select("li.bx") 
            
            if not articles:
                continue

            for article in articles:
                # 1. 언론사 확인
                press_tag = article.select_one("a.info.press")
                if not press_tag: continue
                press_name = press_tag.get_text(strip=True).replace("언론사 선정", "")
                
                matched_label = None
                for key, label in PRESS_MAP.items():
                    if key in press_name:
                        matched_label = label
                        break
                
                if matched_label is None: continue
                
                # 2. 제목 가져오기
                title_tag = article.select_one("a.news_tit")
                if not title_tag: continue
                title = title_tag.get_text(strip=True)
                
                # 3. 본문 시도
                content = ""
                links = article.select("a.info")
                naver_link = None
                for link in links:
                    if "n.news.naver.com" in link.get('href', ''):
                        naver_link = link['href']
                        break
                
                if naver_link:
                    try:
                        sub_res = requests.get(naver_link, headers=headers)
                        sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                        body = sub_soup.select_one("#dic_area") or sub_soup.select_one("#newsct_article")
                        if body:
                            content = body.get_text(strip=True)
                    except:
                        pass
                
                if not content or len(content) < 10:
                    dsc = article.select_one("div.dsc_wrap")
                    if dsc: content = dsc.get_text(strip=True)
                    else: content = title 
                
                results.append({
                    "title": title,
                    "content": content,
                    "labels": matched_label
                })
                
            # [중요] 네이버가 눈치채지 못하게 랜덤하게 쉽니다 (0.5초 ~ 1.5초)
            time.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            print(f"Error: {e}")
            continue

# 저장
if len(results) > 0:
    df = pd.DataFrame(results)
    df = df.drop_duplicates(subset=['title'])
    file_name = "political_auto_data.csv"
    df.to_csv(file_name, index=False, encoding="utf-8-sig")
    print(f"\n🎉 성공! 총 {len(df)}개 저장됨: {file_name}")
    print(df['labels'].value_counts())
else:
    print("\n😭 로컬에서도 안 되면 네이버가 정말 깐깐한 겁니다.")