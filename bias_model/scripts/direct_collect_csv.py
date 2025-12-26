import sys
import os

# ========================================================
# 1. 프로젝트 루트(bias_model 폴더) 위치 찾기
# ========================================================
# scripts 폴더 -> 부모(bias_model) 폴더
BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

# 부모 폴더를 경로에 추가 (analysis_service import용)
sys.path.append(BASE_DIR)

# ========================================================
# 2. Import
# ========================================================
from analysis_service import BiasAnalyzer
import pandas as pd
import requests
import re
import time
from tqdm import tqdm
from dotenv import load_dotenv

# ========================================================
# 3. .env 로딩 (bias_model 폴더 안에서 찾기)
# ========================================================
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ==========================================
# [설정] API 키 가져오기
# ==========================================
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")     
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET") 

# ==========================================
# [수정] ★ CSV 파일 경로를 'data' 폴더로 연결
# ==========================================
# 읽을 파일: data/bias_data_final.csv
INPUT_CSV = os.path.join(BASE_DIR, 'data', 'bias_data_final.csv')

# 저장할 파일: data/algoriverse_corpus_final.csv (여기에 저장해야 깔끔함)
OUTPUT_CSV = os.path.join(BASE_DIR, 'data', 'algoriverse_corpus_final.csv')

# 파일 확인 (디버깅용)
if not os.path.exists(INPUT_CSV):
    print(f"❌ 오류: 입력 파일을 찾을 수 없습니다!")
    print(f"👉 경로 확인: {INPUT_CSV}")
else:
    print(f"📂 입력 파일 확인 완료: {INPUT_CSV}")
    print(f"📂 저장 경로 설정 완료: {OUTPUT_CSV}")

def main():
    # 1. 키워드 파일 읽기
    try:
        df_conf = pd.read_csv(INPUT_CSV)
    except:
        df_conf = pd.read_csv(INPUT_CSV, encoding='cp949')
    
    print(f"🚀 총 {len(df_conf)}개 키워드로 수집을 시작합니다. (DB 없이 바로 저장)")
    print("   (예상 소요 시간: 5~10분)")

    all_news = []

    # 2. 수집 시작
    # 키워드당 100개씩만 확실하게 가져옵니다. (115개 * 100 = 11,500건 목표)
    for i, row in tqdm(df_conf.iterrows(), total=len(df_conf), desc="수집 중"):
        keyword = row['keyword']
        category = row['category']
        
        # 'sim'(관련도순)으로 해야 과거 '검수완박' 같은 기사가 잡힙니다.
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        params = {"query": keyword, "display": 100, "sort": "sim"}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                for item in items:
                    title = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['title'])
                    desc = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['description'])
                    
                    all_news.append({
                        'category': category,
                        'title': title,
                        'link': item['originallink'] or item['link'],
                        'description': desc,
                        'content': title + " " + desc  # 학습용 컬럼 미리 생성
                    })
            else:
                print(f"API Error ({resp.status_code})")
        except Exception as e:
            print(f"Connection Error: {e}")
        
        time.sleep(0.1) # 차단 방지

    # 3. 데이터프레임 변환 및 중복 제거
    if all_news:
        df_result = pd.DataFrame(all_news)
        print(f"\n📥 수집된 원본 데이터: {len(df_result)}건")
        
        # 중복 제거 (링크 기준)
        df_clean = df_result.drop_duplicates(subset=['link'], keep='first')
        print(f"🧹 중복 제거 후 최종 데이터: {len(df_clean)}건")
        
        # 파일 저장
        df_clean.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\n🎉 파일 생성 완료: {OUTPUT_CSV}")
        print("▶ 이 파일을 Colab에 업로드하세요!")
    else:
        print("\n❌ 수집된 데이터가 없습니다. API 키를 확인해주세요.")

if __name__ == "__main__":
    main()