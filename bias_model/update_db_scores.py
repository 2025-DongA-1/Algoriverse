import pymysql
import pandas as pd
import numpy as np
from numpy.linalg import norm
from analysis_service import BiasAnalyzer # 우리가 만든 분석기
from tqdm import tqdm
import os
from dotenv import load_dotenv

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

# ==========================================
# [함수] 상세 점수 계산기 (진보/보수 각각 계산)
# ==========================================
def calculate_dual_scores(analyzer, title, description, target_keyword):
    """
    기사와 키워드 간의 상세 점수(유사도)를 계산하여 반환
    Returns: (target_sim, antonym_sim)
    """
    # 1. 기사 텍스트 벡터화
    full_text = f"{title} {description}"
    tokens = analyzer.twitter.nouns(full_text)
    valid_tokens = [t for t in tokens if t in analyzer.model.wv and len(t) > 1]
    
    if not valid_tokens: 
        return 0.0, 0.0 # 분석 불가

    article_vec = np.mean([analyzer.model.wv[t] for t in valid_tokens], axis=0)
    
    # 2. 기준점 벡터 가져오기
    # (analysis_service의 analyzer 객체 내부 변수에 접근)
    if target_keyword not in analyzer.model.wv or target_keyword not in analyzer.antonym_vec_map:
        return 0.0, 0.0

    my_vec = analyzer.model.wv[target_keyword]          # 키워드 (예: 건국절)
    oppo_vec = analyzer.antonym_vec_map[target_keyword] # 반대어 (예: 독립운동)
    
    # 3. 코사인 유사도 계산
    # 기사가 키워드(보수/정부 측)와 얼마나 가까운가?
    sim_target = np.dot(article_vec, my_vec) / (norm(article_vec)*norm(my_vec))
    
    # 기사가 반대어(진보/반대 측)와 얼마나 가까운가?
    sim_antonym = np.dot(article_vec, oppo_vec) / (norm(article_vec)*norm(oppo_vec))
    
    return float(sim_target), float(sim_antonym)

def main():
    # 1. AI 분석기 로딩
    print("🤖 AI 모델 불러오는 중...")
    analyzer = BiasAnalyzer()
    
    # 2. DB 연결
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, port=DB_PORT, charset='utf8')
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # 3. 아직 판정이 안 된(NULL) 데이터만 가져오기
        print("📥 분석할 뉴스 데이터 가져오는 중...")
        # 테이블명: NEWS_ARTICLES, PK: id
        # 조건 없이 모든 기사 가져오기 (전체 다시 분석)
        sql_select = "SELECT id, title, description FROM NEWS_ARTICLES"
        cur.execute(sql_select)
        rows = cur.fetchall()
        
        print(f"🚀 총 {len(rows)}개 기사의 정밀 분석을 시작합니다.")
        
        # 4. 업데이트 쿼리 준비
        # bias_score_cons: 보수(키워드) 점수
        # bias_score_prog: 진보(반대어) 점수
        # final_judgement: 최종 판정 (CONS / PROG / NEUTRAL)
        # detected_keywords: 발견된 키워드
        sql_update = """
            UPDATE NEWS_ARTICLES 
            SET bias_score_cons = %s, 
                bias_score_prog = %s, 
                final_judgement = %s, 
                detected_keywords = %s 
            WHERE id = %s
        """
        
        success_count = 0
        
        for row in tqdm(rows):
            title = row['title'] or ""
            desc = row['description'] or ""
            
            # (1) 기사 내용에서 키워드 찾기
            detected_kw = None
            for kw in analyzer.df_conf['keyword']:
                if kw in title or kw in desc:
                    detected_kw = kw
                    break # 하나 찾으면 중단 (주요 키워드 우선)
            
            if detected_kw:
                # (2) 상세 점수 계산 (Cons, Prog 각각)
                # 가정: 키워드(건국절) = 보수(Cons), 반대어(독립운동) = 진보(Prog)
                sim_cons, sim_prog = calculate_dual_scores(analyzer, title, desc, detected_kw)
                
                # 점수가 유효한 경우에만 업데이트
                if sim_cons != 0.0 or sim_prog != 0.0:
                    
                    # (3) 최종 판정 로직 (점수 차이 비교)
                    diff = sim_cons - sim_prog
                    
                    judgement = 'NEUTRAL'
                    if diff > 0.03:    # 보수 쪽이 0.03점 더 높으면
                        judgement = 'CONS' # 보수
                    elif diff < -0.03: # 진보 쪽이 0.03점 더 높으면
                        judgement = 'PROG' # 진보
                    
                    # (4) DB 업데이트 실행
                    cur.execute(sql_update, (sim_cons, sim_prog, judgement, detected_kw, row['id']))
                    success_count += 1
            
            # 100건마다 DB에 저장 (안전장치)
            if success_count % 100 == 0:
                conn.commit()
                
        conn.commit()
        print(f"\n🎉 분석 완료! 총 {success_count}개 기사가 업데이트 되었습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()