# ==========================================
# Algoriverse 관점 분석 서비스 (Backend Module)
# ==========================================
import pandas as pd
import numpy as np
from numpy.linalg import norm
from ckonlpy.tag import Twitter
from gensim.models import Word2Vec
import os

# ==========================================
# [수정] 파일 경로 동적 설정 (폴더 구조 변경 반영)
# ==========================================
# 현재 이 파일(analysis_service.py)이 있는 위치를 기준점으로 잡습니다.
# 이렇게 하면 어디서 실행하든 경로 에러가 절대 안 납니다!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# models 폴더 안의 모델 파일 경로
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'algoriverse.model')

# data 폴더 안의 CSV 파일 경로
CONF_PATH = os.path.join(BASE_DIR, 'data', 'bias_data_final.csv')

class BiasAnalyzer:
    def __init__(self):
        print("🤖 AI 모델 로딩 중... (잠시만 기다려주세요)")
        
        # 1. 모델 파일 존재 확인
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"❌ 모델 파일을 찾을 수 없습니다.\n예상 경로: {MODEL_PATH}")
            
        # 2. Word2Vec 모델 로드
        self.model = Word2Vec.load(MODEL_PATH)
        
        # 3. 설정 파일(CSV) 로드
        if not os.path.exists(CONF_PATH):
             raise FileNotFoundError(f"❌ 설정 파일(CSV)을 찾을 수 없습니다.\n예상 경로: {CONF_PATH}")

        try:
            self.df_conf = pd.read_csv(CONF_PATH)
        except:
            self.df_conf = pd.read_csv(CONF_PATH, encoding='cp949')
            
        # 4. 형태소 분석기(Twitter) & 사용자 사전 구축
        self.twitter = Twitter()
        self.antonym_vec_map = {}
        
        self._initialize_dictionary()
        print("✅ AI 분석 준비 완료!")

    def _initialize_dictionary(self):
        """키워드 사전을 등록하고 반대어 벡터를 미리 계산하는 내부 함수"""
        
        # (1) 키워드와 반대어를 사전에 강제 등록 (쪼개짐 방지)
        new_words = self.df_conf['keyword'].tolist()
        for _, row in self.df_conf.iterrows():
            if pd.notna(row['antonym']):
                ants = str(row['antonym']).split(',')
                new_words.extend([a.strip() for a in ants])
        
        # 중복 제거 후 등록
        for word in set(new_words):
            self.twitter.add_dictionary(word, 'Noun')

        # (2) 반대어 벡터(기준점) 미리 계산
        for _, row in self.df_conf.iterrows():
            target = row['keyword']
            if pd.notna(row['antonym']):
                raw_ants = [a.strip() for a in str(row['antonym']).split(',')]
                valid_vecs = []
                
                for ant in raw_ants:
                    # 모델에 통째로 있으면 사용
                    if ant in self.model.wv:
                        valid_vecs.append(self.model.wv[ant])
                    else:
                        # 없으면 형태소 분석 후 평균값 사용
                        tokens = self.twitter.nouns(ant)
                        sub_vecs = [self.model.wv[t] for t in tokens if t in self.model.wv]
                        if sub_vecs:
                            valid_vecs.append(np.mean(sub_vecs, axis=0))
                
                # 유효한 반대어 벡터들의 평균을 저장
                if valid_vecs:
                    self.antonym_vec_map[target] = np.mean(valid_vecs, axis=0)

    def analyze_article(self, title, description, target_keyword):
        """
        기사 제목과 요약을 받아 편향도 점수를 반환하는 함수
        Return: 양수(+)면 해당 키워드 성향, 음수(-)면 반대 성향
        """
        # 1. 분석 가능한 키워드인지 체크
        if target_keyword not in self.model.wv or target_keyword not in self.antonym_vec_map:
            return None # 분석 불가 (데이터 부족)

        # 2. 기사 텍스트 전처리
        full_text = f"{title} {description}"
        tokens = self.twitter.nouns(full_text)
        
        # 의미 있는 단어만 필터링
        valid_tokens = [t for t in tokens if t in self.model.wv and len(t) > 1]
        
        if not valid_tokens: return 0.0

        # 3. 벡터 계산 (Core Logic)
        my_vec = self.model.wv[target_keyword]          # 기준점 (예: 건국절)
        oppo_vec = self.antonym_vec_map[target_keyword] # 반대점 (예: 광복절, 독립운동)
        article_vec = np.mean([self.model.wv[t] for t in valid_tokens], axis=0) # 기사 위치
        
        # 4. 코사인 유사도 비교
        # (나랑 얼마나 가까운가) - (반대랑 얼마나 가까운가)
        sim_my = np.dot(article_vec, my_vec) / (norm(article_vec)*norm(my_vec))
        sim_oppo = np.dot(article_vec, oppo_vec) / (norm(article_vec)*norm(oppo_vec))
        
        # 점수 리턴
        return sim_my - sim_oppo

# ==========================================
# [실행 테스트] 터미널에서 python analysis_service.py 실행 시 작동
# ==========================================
if __name__ == "__main__":
    # 1. 서비스 초기화
    analyzer = BiasAnalyzer()
    
    # 2. 가상의 테스트 데이터
    test_keyword = "건국절"
    test_title = "광복회, '건국절 제정은 매국 행위' 강력 규탄"
    test_desc = "뉴라이트 역사관에 기반한 건국절 추진을 즉각 중단하라."
    
    print(f"\n🔎 검색 키워드: {test_keyword}")
    print(f"📄 기사 제목: {test_title}")
    
    # 3. 분석 수행
    score = analyzer.analyze_article(test_title, test_desc, test_keyword)
    
    if score is None:
        print("❌ 분석 불가 (키워드 데이터 부족)")
    else:
        print(f"📊 분석 점수: {score:.4f}")
        if score > 0:
            print("👉 결과: [보수/건국절 옹호] 성향")
        else:
            print("👉 결과: [진보/건국절 반대] 성향")