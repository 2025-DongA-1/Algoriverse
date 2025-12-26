import sys
import os

# 현재 파일의 위치를 기준으로, 한 단계 위(부모 폴더)를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# (이 아래에 원래 있던 import 코드들이 오면 됩니다)
from analysis_service import BiasAnalyzer

import pymysql
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()

# [설정] DB 접속 정보 (main.py와 똑같이!)
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))


def check_data():
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, 
            db=DB_NAME, charset='utf8mb4', port=DB_PORT
        )
        cur = conn.cursor()
        
        # 1. 개수 확인
        cur.execute("SELECT COUNT(*) FROM NEWS_ARTICLES")
        count = cur.fetchone()[0]
        print(f"\n📊 현재 DB에 저장된 총 데이터 개수: {count}건")
        
        # 2. 샘플 데이터 확인 (최근 3개)
        print("\n[최근 수집된 기사 3개 미리보기]")
        cur.execute("SELECT id, category, title, final_judgment FROM NEWS_ARTICLES ORDER BY id DESC LIMIT 3")
        rows = cur.fetchall()
        
        for row in rows:
            print(f"- ID: {row[0]} | [{row[1]}] {row[2][:20]}... | 판정: {row[3]}")
            
    except Exception as e:
        print(f"확인 중 오류 발생: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_data()