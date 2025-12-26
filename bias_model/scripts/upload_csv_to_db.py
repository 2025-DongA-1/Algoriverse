import sys
import os

# ========================================================
# [중요] 1. 부모 폴더 경로를 먼저 추가합니다. (순서 중요! ★)
# ========================================================
current_dir = os.path.dirname(os.path.abspath(__file__)) # scripts 폴더
parent_dir = os.path.dirname(current_dir)                # bias_model (루트) 폴더
sys.path.append(parent_dir)


# ========================================================
# [중요] 2. 그 다음에 import를 해야 에러가 안 납니다.
# ========================================================
# (혹시 이 파일에서 분석기가 필요 없다면 이 줄은 지워도 됩니다)
try:
    from analysis_service import BiasAnalyzer 
except ImportError:
    pass # 업로드만 할 때는 없어도 되므로 에러 무시

# (이 아래에 원래 있던 import 코드들이 오면 됩니다)
from analysis_service import BiasAnalyzer
from dotenv import load_dotenv
import pandas as pd
import pymysql
from tqdm import tqdm

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()


# ==========================================
# [설정] DB 정보
# ==========================================
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

# 2. CSV 파일 경로 수정 (data 폴더 안을 가리키도록 설정)
# 이렇게 하면 어디서 실행하든 무조건 정확한 위치를 찾아냅니다!
CSV_FILE = os.path.join(parent_dir, 'data', 'algoriverse_corpus_final.csv')

def main():
    # 1. CSV 파일 읽기
    print(f"📂 '{CSV_FILE}' 로딩 중...")
    
    # 파일이 진짜 있는지 먼저 확인 (친절한 에러 메시지)
    if not os.path.exists(CSV_FILE):
        print(f"❌ 오류: 파일을 찾을 수 없습니다!")
        print(f"👉 찾아본 경로: {CSV_FILE}")
        return
    
    try:
        df = pd.read_csv(CSV_FILE)
    except:
        df = pd.read_csv(CSV_FILE, encoding='cp949')
        
    print(f"🚀 총 {len(df)}건의 데이터를 DB에 업로드합니다.")

    # 2. DB 연결
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')
    cur = conn.cursor()

    # 3. 데이터 삽입
    # (주의: 테이블 컬럼 순서나 이름이 다르면 에러 날 수 있으니 INSERT 문을 잘 확인하세요)
    # NEWS_ARTICLES 테이블 컬럼: category, title, link, description, content(본문은 없으면 desc로 대체)
    sql_insert = """
        INSERT INTO NEWS_ARTICLES (category, title, link, description, created_at) 
        VALUES (%s, %s, %s, %s, NOW())
    """

    success_count = 0
    
    try:
        for _, row in tqdm(df.iterrows(), total=len(df)):
            # 데이터 정제 (NaN 값을 빈 문자열로)
            title = row['title'] if pd.notna(row['title']) else ""
            link = row['link'] if pd.notna(row['link']) else ""
            desc = row['description'] if pd.notna(row['description']) else ""
            category = row['category'] if pd.notna(row['category']) else "General"
            
            # 중복 방지 (선택 사항: 링크가 이미 있으면 건너뛰기)
            # 속도 때문에 일단은 그냥 넣거나, 필요하면 중복 체크 로직 추가
            # 여기서는 일단 무조건 INSERT 시도 (에러나면 pass)
            try:
                cur.execute(sql_insert, (category, title, link, desc))
                success_count += 1
            except Exception as e:
                # 중복 에러 등은 무시하고 계속 진행
                pass
                
            if success_count % 500 == 0:
                conn.commit()
                
        conn.commit()
        print(f"\n🎉 업로드 완료! 총 {success_count}건이 DB에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ DB 연결/업로드 중 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()