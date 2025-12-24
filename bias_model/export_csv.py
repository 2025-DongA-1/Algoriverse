import pandas as pd
import pymysql
import os
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()


# ==========================================
# [설정] 본인의 DB 정보
# ==========================================
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

OUTPUT_FILE = 'algoriverse_corpus_final.csv'

def export_db_to_csv_clean():
    print("🚀 DB 접속 및 데이터 추출 시작...")
    
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS,
            db=DB_NAME, port=DB_PORT, charset='utf8'
        )
        
        # 1. DB에서 모든 데이터 가져오기
        # (혹시 테이블명이 news가 아니면 수정하세요)
        sql = "SELECT * FROM NEWS_ARTICLES" 
        df = pd.read_sql(sql, conn)
        
        print(f"📥 DB 원본 데이터: {len(df)}건 로드됨")
        
        # 2. 중복 제거 (링크 기준)
        # bulk_collect와 keyword_collect를 둘 다 하면 중복이 생길 수밖에 없음
        df_clean = df.drop_duplicates(subset=['link'], keep='first')
        
        print(f"🧹 중복 기사 제거 완료: {len(df) - len(df_clean)}건 삭제됨")
        print(f"✅ 최종 학습 데이터: {len(df_clean)}건")
        
        # 3. 학습용 컬럼 생성 (제목 + 본문 요약 합치기)
        # title과 description 컬럼이 있는지 확인
        if 'title' in df_clean.columns and 'description' in df_clean.columns:
            df_clean['content'] = df_clean['title'] + " " + df_clean['description']
        else:
            print("⚠️ 컬럼 확인 필요: title/description 컬럼이 감지되지 않아 전체를 저장합니다.")
        
        # 4. CSV 저장
        df_clean.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"🎉 파일 생성 완료: '{OUTPUT_FILE}'")
        print("▶ 이 파일을 Colab에 업로드해서 학습을 시작하세요!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    export_db_to_csv_clean()