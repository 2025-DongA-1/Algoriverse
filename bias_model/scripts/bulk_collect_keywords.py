import sys
import os
from dotenv import load_dotenv

# 1. 현재 파일의 위치를 기준으로 'bias_model' 폴더(루트) 찾기
# (scripts 폴더 -> 한 칸 위 bias_model 폴더)
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(current_dir)

# 2. 시스템 경로 추가 (analysis_service import용)
sys.path.append(BASE_DIR)

# 3. ★ 핵심: .env 파일 경로를 직접 만들어서 로딩하기
env_path = os.path.join(BASE_DIR, '.env')

# .env 파일 로딩 시도
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ .env 파일 발견 및 로드: {env_path}")
else:
    print(f"❌ .env 파일을 찾을 수 없습니다! 경로: {env_path}")

# ========================================================
# 4. 모듈 Import & 설정
# ========================================================
from analysis_service import BiasAnalyzer
import pandas as pd
import requests
import re
import pymysql
import time
from tqdm import tqdm

# 5. API 키 확인 (디버깅용 - 실행 시 ID가 보여야 성공!)
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

print(f"🔎 [디버그] 로드된 Client ID: {NAVER_CLIENT_ID}") 

if not NAVER_CLIENT_ID:
    print("🚨 [비상] 키가 로드되지 않았습니다. .env 위치를 확인하거나 키를 직접 입력하세요.")
    # (급하면 여기에 직접 키를 적으세요)
    # NAVER_CLIENT_ID = "네이버_아이디_직접입력"
    # NAVER_CLIENT_SECRET = "네이버_비번_직접입력"

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
# 포트는 int 변환 시 에러 날 수 있으니 안전하게 처리
try:
    DB_PORT = int(os.getenv("DB_PORT"))
except:
    DB_PORT = 3306 # 기본값

# ========================================================
# 5. 키워드 파일(CSV) 경로 설정
# ========================================================
# bias_model/data/bias_data_final.csv
KEYWORDS_FILE = os.path.join(BASE_DIR, 'data', 'bias_data_final.csv')

# 파일 진짜 있나 확인 (디버깅용)
if not os.path.exists(KEYWORDS_FILE):
    print(f"❌ 오류: 설정 파일을 찾을 수 없습니다!")
    print(f"👉 경로 확인: {KEYWORDS_FILE}")
    
    
# ★ 한 키워드당 가져올 기사 수 (최대 1000)
# 100으로 설정하면 -> 115개 키워드 * 100 = 11,500개 (약 20분 소요)
# 500으로 설정하면 -> 115개 키워드 * 500 = 57,500개 (약 1시간+ 소요, 6개월치 충분)
MAX_NEWS_PER_KEYWORD = 500 

def get_naver_news_past(keyword, total_count):
    news_list = []
    # 100개씩 끊어서 과거 페이지로 넘어감 (Pagination)
    for start_index in range(1, total_count, 100):
        if start_index > 1000: break # 네이버 API 최대 한계

        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        params = {
            "query": keyword,
            "display": 100,
            "start": start_index, 
            "sort": "sim"  # 'sim'(정확도순)을 쓰면 과거의 중요한 기사도 잘 나옵니다.
                           # 'date'(날짜순)을 쓰면 무조건 최신부터 가져옵니다.
        }
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                if not items: break
                news_list.extend(items)
            else:
                print(f"API Error: {resp.status_code}")
                break
        except Exception as e:
            print(f"Request Error: {e}")
            break
        
        time.sleep(0.3) # API 보호용 딜레이
        
    return news_list[:total_count]

def save_bulk_to_db(data_list):
    if not data_list: return
    conn = None
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')
        cur = conn.cursor()
        
        # main.py 기준 테이블 컬럼에 맞춤
        sql = "INSERT INTO news (category, title, link, description) VALUES (%s, %s, %s, %s)"
        
        success = 0
        # executemany를 쓰면 더 빠르지만, 오류 확인을 위해 반복문 사용
        for item in data_list:
            try:
                cur.execute(sql, (item['category'], item['title'], item['link'], item['description']))
                success += 1
            except:
                pass # 중복 기사 등은 무시
        
        conn.commit()
        # 중간 점검 출력
        if success > 0:
            print(f"   └─ {success}건 저장 완료")
        
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn: conn.close()

def main():
    # 1. 키워드 파일 로드
    try:
        df = pd.read_csv(KEYWORDS_FILE)
    except:
        df = pd.read_csv(KEYWORDS_FILE, encoding='cp949')

    print(f"🚀 총 {len(df)}개의 키워드로 대량 수집을 시작합니다. (목표: 키워드당 {MAX_NEWS_PER_KEYWORD}개)")
    
    # 2. 키워드별 수집 반복
    for i, row in tqdm(df.iterrows(), total=len(df), desc="전체 진행률"):
        keyword = row['keyword']
        category = row['category']
        
        # 기사 수집
        items = get_naver_news_past(keyword, MAX_NEWS_PER_KEYWORD)
        
        # DB 저장용 데이터 가공
        db_data = []
        for item in items:
            title = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['title'])
            desc = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['description'])
            
            db_data.append({
                'category': category,
                'title': title,
                'link': item['originallink'] or item['link'],
                'description': desc
            })
        
        # 바로바로 저장 (메모리 절약)
        save_bulk_to_db(db_data)
        time.sleep(0.5)

    print("\n🎉 6개월치(추정) 데이터 수집 완료! export_csv.py를 실행하세요.")

if __name__ == "__main__":
    main()