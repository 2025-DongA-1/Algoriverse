import time
import schedule
import pymysql
import requests
import re
import pandas as pd
import numpy as np
from numpy.linalg import norm
from analysis_service import BiasAnalyzer # ★ AI 두뇌 탑재
from datetime import datetime
import os
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()

# ==========================================
# [설정] DB 및 API 정보
# ==========================================
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")     
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

CONF_FILE = 'data/bias_data_final.csv'

# ==========================================
# [준비] AI 분석기 미리 로딩 (봇 켜질 때 1번만)
# ==========================================
print("🤖 봇 가동 시작! AI 모델을 로딩합니다...")
analyzer = BiasAnalyzer()

def get_db_connection():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')

# ==========================================
# [수정] 스마트 점수 계산 함수
# ==========================================
def calculate_scores_smart(title, description, search_keyword):
    """
    [최종 개선] 검색어 기반 강제 분석 (유효율 대폭 상승)
    """
    # 1. 기사 벡터 계산 (이건 기본)
    full_text = f"{title} {description}"
    tokens = analyzer.twitter.nouns(full_text)
    valid_tokens = [t for t in tokens if t in analyzer.model.wv and len(t) > 1]
    
    # 기사에 쓸만한 명사가 하나도 없으면 0점 (이건 어쩔 수 없음)
    if not valid_tokens: 
        return 0.0, 0.0, None

    article_vec = np.mean([analyzer.model.wv[t] for t in valid_tokens], axis=0)

    # -----------------------------------------------------------
    # 2. 기준점(키워드) 벡터 만들기 - 여기가 핵심! ⚡
    # -----------------------------------------------------------
    # 검색어(search_keyword)가 모델에 딱 있으면 베스트
    if search_keyword in analyzer.model.wv:
        my_vec = analyzer.model.wv[search_keyword]
        
    else:
        # 없으면? 검색어를 쪼개서 벡터를 만듦 (예: "4대강 보 해체" -> "4대강"+"보"+"해체" 평균)
        # 1) 검색어 자체를 형태소 분석
        kw_tokens = analyzer.twitter.nouns(search_keyword)
        kw_valid = [t for t in kw_tokens if t in analyzer.model.wv]
        
        if kw_valid:
            # 쪼갠 단어들의 평균 벡터 사용
            my_vec = np.mean([analyzer.model.wv[t] for t in kw_valid], axis=0)
        else:
            # 쪼개도 아는 단어가 없으면... 분석 불가 (어쩔 수 없음)
            return 0.0, 0.0, None

    # 3. 반대어(Antonym) 벡터 가져오기
    # (이미 analysis_service에서 계산해둠)
    if search_keyword in analyzer.antonym_vec_map:
        oppo_vec = analyzer.antonym_vec_map[search_keyword]
    else:
        # 반대어 설정이 안 된 키워드라면 분석 불가
        return 0.0, 0.0, None

    # 4. 최종 점수 계산 (코사인 유사도)
    try:
        sim_cons = np.dot(article_vec, my_vec) / (norm(article_vec)*norm(my_vec))
        sim_prog = np.dot(article_vec, oppo_vec) / (norm(article_vec)*norm(oppo_vec))
        
        # 키워드를 찾았으니 검색어를 결과로 리턴
        return float(sim_cons), float(sim_prog), search_keyword
        
    except:
        return 0.0, 0.0, None

# ==========================================
# [수정] Job 함수 (실행 로직)
# ==========================================
def job():
    print(f"\n⏰ [스케줄 실행] 뉴스 수집 및 분석 시작 ({datetime.now()})")
    
    try:
        # DB 연결 확인
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 키워드 파일 로드
        df_conf = pd.read_csv(CONF_FILE) if 'bias_data_final.csv' in CONF_FILE else pd.read_csv(CONF_FILE, encoding='cp949')
        
        total_collected = 0
        analyzed_count = 0
        
        for i, row in df_conf.iterrows():
            keyword = row['keyword']
            category = row['category']
            
            # API 호출 (20개)
            url = "https://openapi.naver.com/v1/search/news.json"
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            params = {"query": keyword, "display": 20, "sort": "date"}
            
            try:
                resp = requests.get(url, headers=headers, params=params)
                if resp.status_code != 200: continue
                items = resp.json().get('items', [])
            except:
                continue
            
            for item in items:
                title = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['title'])
                desc = re.sub(r'<.*?>|&quot;|&gt;|&lt;', '', item['description'])
                link = item['originallink'] or item['link']
                
                # ★ 스마트 분석 실행
                sim_cons, sim_prog, detected_kw = calculate_scores_smart(title, desc, keyword)
                
                # 1. 차이(편향 레벨) 계산
                bias_level = sim_cons - sim_prog  # 이게 바로 우리가 원하는 그 점수!
                
                # 점수가 0이면 중립, 아니면 판정
                judgement = 'NEUTRAL'
                if sim_cons != 0 or sim_prog != 0:
                    analyzed_count += 1 # 분석 성공 카운트
                    diff = sim_cons - sim_prog
                    if diff > 0.02: judgement = 'CONS'
                    elif diff < -0.02: judgement = 'PROG'
                
                # DB 저장 (detected_keywords 컬럼에 실제로 분석한 단어를 넣음)
                # 주의: detected_kw가 None이면 원래 keyword를 넣음
                final_kw = detected_kw if detected_kw else keyword
                
                sql = """
                    INSERT INTO NEWS_ARTICLES 
                    (category, title, link, description, bias_score_cons, bias_score_prog, bias_level, final_judgement, detected_keywords, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                
                try:
                    cur.execute(sql, (category, title, link, desc, sim_cons, sim_prog, bias_level, judgement, final_kw))
                    total_collected += 1
                except Exception as e:
                    pass # 중복은 패스
            
            if total_collected % 100 == 0:
                conn.commit()
            
            time.sleep(0.05) 
            
        conn.commit()
        conn.close()
        print(f"🎉 수집 완료! (총 {total_collected}개 수집 / 그 중 {analyzed_count}개 유효 분석)")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

# ==========================================
# [스케줄링] 주기 설정
# ==========================================
# 테스트를 위해 10초 뒤에 한 번 실행하고, 그 뒤엔 매일 3번 실행
print("⏳ 스케줄러 대기 중... (Ctrl+C로 종료)")

# (1) 즉시 실행 확인용
job()

# (2) 정해진 시간마다 실행 (예: 6시간마다)
schedule.every(6).hours.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)