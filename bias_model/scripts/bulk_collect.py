import sys
import os

# 현재 파일의 위치를 기준으로, 한 단계 위(부모 폴더)를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# (이 아래에 원래 있던 import 코드들이 오면 됩니다)
from analysis_service import BiasAnalyzer
import pandas as pd
import requests
import re
import pymysql
import time
from tqdm import tqdm
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()


# ==========================================
# [설정] 본인의 DB 정보 및 API 키
# ==========================================
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")     
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET") 

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

# ★ 목표: 카테고리별로 1000개씩 -> 총 5000개 수집 도전!
TARGET_CATEGORIES = ['정치 외교', '정치 안보', '정치 사법', '정치 노동', '정치 환경']
MAX_NEWS_PER_CATEGORY = 1000 

def get_naver_news_bulk(keyword, total_count):
    news_list = []
    # 네이버 API는 한 번에 100개까지만 줌 -> 반복 호출 필요
    for start_index in range(1, total_count, 100):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        params = {
            "query": keyword,
            "display": 100, # 최대 100
            "start": start_index, 
            "sort": "sim" # 정확도순 (또는 'date' 최신순)
        }
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                if not items: break # 더 이상 기사가 없으면 중단
                news_list.extend(items)
            else:
                print(f"API Error: {resp.status_code}")
                break
        except Exception as e:
            print(f"Request Error: {e}")
            break
        
        time.sleep(0.5) # API 매너
        
    return news_list[:total_count] # 정확히 목표 개수만큼 자르기

def save_bulk_to_db(data_list):
    if not data_list: return
    conn = None
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')
        cur = conn.cursor()
        
        sql = "INSERT INTO news (category, title, link, description) VALUES (%s, %s, %s, %s)"
        
        success = 0
        for item in tqdm(data_list, desc="DB 저장 중"):
            try:
                cur.execute(sql, (item['category'], item['title'], item['link'], item['description']))
                success += 1
            except:
                pass # 중복 키 에러 등은 무시
        
        conn.commit()
        print(f"✅ 총 {success}건 신규 저장 완료!")
        
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn: conn.close()

def main():
    print("🚀 과거 기사 대량 수집 시작...")
    all_data = []
    
    for category in TARGET_CATEGORIES:
        print(f"\n[{category}] 분야 수집 중...")
        items = get_naver_news_bulk(category, MAX_NEWS_PER_CATEGORY)
        
        for item in items:
            title = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['title'])
            desc = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['description'])
            
            all_data.append({
                'category': category.replace("정치 ", ""), # "정치 외교" -> "외교"
                'title': title,
                'link': item['originallink'] or item['link'],
                'description': desc
            })
            
    save_bulk_to_db(all_data)
    print("\n🎉 대량 수집 끝! 이제 export_csv.py를 실행해서 CSV를 뽑아주세요.")

if __name__ == "__main__":
    main()
