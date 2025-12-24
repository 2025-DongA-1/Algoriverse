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


# ==========================================
# [설정] 본인의 DB 및 API 정보 (bot.py 참조)
# ==========================================
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")     
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET") 

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

# 같은 폴더에 있어야 함
CSV_FILE = 'bias_data_final.csv'

def save_to_db(data_list):
    if not data_list: return
    conn = None
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')
        cur = conn.cursor()
        sql = "INSERT INTO news (category, title, link, description) VALUES (%s, %s, %s, %s)"
        
        for item in data_list:
            try:
                cur.execute(sql, (item['category'], item['title'], item['link'], item['description']))
            except:
                pass # 중복 기사는 무시
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn: conn.close()

def main():
    # 1. 키워드 파일 읽기
    try:
        df = pd.read_csv(CSV_FILE)
    except:
        df = pd.read_csv(CSV_FILE, encoding='cp949')

    print(f"🚀 '{CSV_FILE}'의 {len(df)}개 키워드로 과거 기사를 정밀 수집합니다.")
    
    # 2. 각 키워드별로 검색
    # ★ display=100: 키워드당 100개씩만 모아도 115개 * 100 = 11,500개 확보 가능!
    for i, row in tqdm(df.iterrows(), total=len(df), desc="수집 진행률"):
        keyword = row['keyword']
        category = row['category']
        
        # ★ 핵심: sort='sim' (정확도순)으로 해야 과거의 핫했던 기사가 나옴
        # (sort='date'로 하면 오늘 날짜 기사만 나와서 의미 없음)
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        params = {"query": keyword, "display": 100, "sort": "sim"}
        
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                db_data = []
                for item in items:
                    title = re.sub(r'<.*?>|&quot;', '', item['title'])
                    desc = re.sub(r'<.*?>|&quot;', '', item['description'])
                    db_data.append({
                        'category': category, 
                        'title': title, 
                        'link': item['originallink'] or item['link'], 
                        'description': desc
                    })
                save_to_db(db_data)
        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(0.1) # 네이버 API 차단 방지

    print("\n🎉 수집 완료! 이제 export_csv.py를 실행해서 파일을 추출하세요.")

if __name__ == "__main__":
    main()