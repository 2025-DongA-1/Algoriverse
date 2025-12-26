import sys
import os
from gensim.models import Word2Vec

# ========================================================
# 1. 경로 설정 (scripts -> bias_model 루트 찾기)
# ========================================================
# 현재 파일(scripts/check_...)의 위치
current_dir = os.path.dirname(os.path.abspath(__file__))
# 부모 폴더(bias_model 루트) 위치
BASE_DIR = os.path.dirname(current_dir)

# ========================================================
# 2. 모델 파일 경로 설정 (동적 경로)
# ========================================================
# bias_model/models/algoriverse.model
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'algoriverse.model')

print(f"📂 모델 경로 확인: {MODEL_PATH}")

# 3. 모델 로드 및 테스트
if not os.path.exists(MODEL_PATH):
    print("❌ 오류: 모델 파일을 찾을 수 없습니다.")
    print(f"👉 찾아본 경로: {MODEL_PATH}")
    sys.exit()

try:
    print("🤖 모델 로딩 중...")
    model = Word2Vec.load(MODEL_PATH)
    print("✅ 모델 로딩 완료!\n")
    
    print("📊 [모델 성능 테스트 1] 핵심 키워드 연관성 확인")
    print("-" * 50)

    # 테스트할 단어 리스트
    keywords = ["보수", "진보", "검찰", "대통령"] # 원하는 단어 추가 가능

    for kw in keywords:
        try:
            print(f"\n🔵 '{kw}'와 유사한 단어 TOP 5:")
            similar_words = model.wv.most_similar(kw, topn=5)
            for word, score in similar_words:
                print(f"   - {word} ({score:.4f})")
        except KeyError:
            print(f"   ⚠️ '{kw}' 단어는 학습 데이터에 없습니다.")

except Exception as e:
    print(f"❌ 실행 중 오류 발생: {e}")