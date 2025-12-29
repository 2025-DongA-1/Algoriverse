from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 🔥 CORS 필수
import pymysql
import os
from dotenv import load_dotenv

# .env 로딩
load_dotenv()

app = FastAPI()

# 1. CORS 설정 (이게 없으면 프론트에서 에러 납니다!)
origins = [
    "http://localhost:3000", # React/Next.js 로컬 주소
    "*"                      # 개발 중에는 모든 곳 허용
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 설정
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME"),
    'port': int(os.getenv("DB_PORT")),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

@app.get("/")
def read_root():
    return {"message": "Algoriverse API Server is Running!"}

@app.get("/news")
def get_news(keyword: str):
    """
    키워드를 받아서 '가장 보수적인 기사'와 '가장 진보적인 기사' 하나씩 반환
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 1. 데이터 확인
        # (크롤링은 auto_system.py가 하고 있다고 가정하고, 여기선 읽기만 합니다)
        # 만약 데이터가 없으면 빈 값(Null)을 주거나 "수집 중입니다"라고 응답하는 게 빠릅니다.
        
        # [보수 1등] (질문자님 코드 활용)
        sql_conservative = """
            SELECT title, link, content, bias_score 
            FROM NEWS_ARTICLES
            WHERE keyword = %s AND bias = '보수' 
            ORDER BY bias_score DESC LIMIT 1
        """
        cursor.execute(sql_conservative, (keyword,))
        conservative_data = cursor.fetchone()

        # [진보 1등] (질문자님 코드 활용)
        sql_liberal = """
             SELECT title, link, content, bias_score 
             FROM NEWS_ARTICLES 
            WHERE keyword = %s AND bias = '진보' 
            ORDER BY bias_score DESC LIMIT 1
        """
        cursor.execute(sql_liberal, (keyword,))
        liberal_data = cursor.fetchone()
        
        # 데이터가 아예 없는 경우
        if not conservative_data and not liberal_data:
            return {
                "status": "empty", 
                "message": f"'{keyword}'에 대한 분석 데이터가 아직 없습니다. 자동 수집 시스템이 곧 수집할 것입니다."
            }

        # 2. 프론트엔드에게 JSON으로 응답
        return {
            "status": "success",
            "keyword": keyword,
            "data": {
                "conservative": conservative_data, # 데이터 or None
                "liberal": liberal_data           # 데이터 or None
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    finally:
        conn.close()