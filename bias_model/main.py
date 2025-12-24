import pandas as pd
import requests
import re
import pymysql
import time
from tqdm import tqdm
import os
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()

# =============================================================================
# [설정] 사용자 정보 입력
# =============================================================================
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")     
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ★ 중요: 포트 번호 수정!
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

DATA_FILE = 'bias_data_final.csv'
TARGET_CATEGORIES = ['외교', '안보', '사법', '노동', '환경']
NEWS_COUNT = 100 

# =============================================================================
# [기능 1] 편향 사전 로드
# =============================================================================
def load_bias_dictionary(filepath):
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"❌ 오류: '{filepath}' 파일을 찾을 수 없습니다.")
        return {}
    word_dict = {}
    for _, row in df.iterrows():
        info = {'tendency': row['tendency'], 'weight': row['weight']}
        word_dict[str(row['keyword']).strip()] = info
        if pd.notna(row['synonyms']):
            for syn in str(row['synonyms']).split(','):
                if syn.strip(): word_dict[syn.strip()] = info
    return word_dict

# =============================================================================
# [기능 2] 편향도 계산기
# =============================================================================
def calculate_bias(text, bias_dict):
    if not bias_dict: return 0, 0, "Error", ""
    score_board = {'진보': 0, '보수': 0}
    detected_words = []
    
    for word, info in bias_dict.items():
        if word in text:
            score_board[info['tendency']] += info['weight']
            detected_words.append(word)
            
    prog, cons = score_board['진보'], score_board['보수']
    if prog > cons: result = "진보 우세"
    elif cons > prog: result = "보수 우세"
    elif prog == 0 and cons == 0: result = "판단 불가"
    else: result = "중립"
    
    return prog, cons, result, ", ".join(detected_words)

# =============================================================================
# [기능 3] 네이버 뉴스 수집
# =============================================================================
def get_naver_news(query, display=10):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    try:
        res = requests.get(url, headers=headers, params={"query": query, "display": display, "sort": "sim"})
        return res.json().get('items', []) if res.status_code == 200 else []
    except: return []

# =============================================================================
# [기능 4] DB 저장 (포트 번호 추가됨!)
# =============================================================================
def save_to_db(data_list):
    if not data_list: return
    
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_HOST, 
            user=DB_USER, 
            password=DB_PASS, 
            db=DB_NAME, 
            charset='utf8mb4',
            port=DB_PORT
        )
        cur = conn.cursor()

        # =========================================================
        # [추가됨] 테이블이 없으면 자동으로 만드는 SQL 실행
        # =========================================================
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS NEWS_ARTICLES (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category VARCHAR(50),
            title VARCHAR(500),
            link VARCHAR(500),
            description TEXT,
            bias_score_prog INT DEFAULT 0,
            bias_score_cons INT DEFAULT 0,
            final_judgment VARCHAR(50),
            detected_keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) DEFAULT CHARSET=utf8mb4;
        """
        cur.execute(create_table_sql)
        # =========================================================
        
        sql = """
            INSERT INTO NEWS_ARTICLES 
            (category, title, link, description, bias_score_prog, bias_score_cons, final_judgment, detected_keywords)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        print("\n💾 데이터베이스에 저장 중...")
        success_cnt = 0
        error_shown = False 
        
        for item in tqdm(data_list, desc="DB Insert"):
            try:
                cur.execute(sql, (
                    item['category'], 
                    item['title'], 
                    item['link'][:999],        
                    item['description'][:2000], 
                    item['prog_score'], 
                    item['cons_score'], 
                    item['judgment'], 
                    item['keywords']
                ))
                success_cnt += 1
            except Exception as e:
                if not error_shown:
                    print(f"\n[❌ 저장 실패 원인]: {e}")
                    print(f"[문제가 된 데이터]: {item['title']}")
                    error_shown = True
        
        conn.commit()
        print(f"🎉 총 {success_cnt}건 저장 완료!")
        
    except Exception as e:
        print(f"❌ DB 접속/생성 오류: {e}")
    finally:
        if conn: conn.close()
# =============================================================================
# [메인] 실행
# =============================================================================
def main():
    bias_dict = load_bias_dictionary(DATA_FILE)
    if not bias_dict: return
    all_results = []
    print(f"\n🚀 뉴스 수집 및 분석 시작...")

    for category in tqdm(TARGET_CATEGORIES, desc="카테고리별 진행"):
        news_items = get_naver_news(f"정치 {category}", display=NEWS_COUNT)
        for item in news_items:
            title = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['title'])
            desc = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['description'])
            full_text = title + " " + desc
            p, c, res, keys = calculate_bias(full_text, bias_dict)
            all_results.append({
                'category': category, 'title': title, 'link': item['originallink'] or item['link'],
                'description': desc, 'prog_score': p, 'cons_score': c, 'judgment': res, 'keywords': keys
            })
        time.sleep(0.5)

    save_to_db(all_results)

if __name__ == "__main__":
    main()