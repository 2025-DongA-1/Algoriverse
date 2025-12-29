# test_ai.py (VS Code에서 실행)
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

# 폴더 경로 (압축 푼 폴더 이름과 똑같아야 함)
MODEL_PATH = "./my_bias_model" 

print(f"📂 모델 로딩 중... ({MODEL_PATH})")

# 1. 모델 불러오기
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    print("✅ 로딩 완료! AI가 준비되었습니다.")
except Exception as e:
    print(f"🚨 오류 발생: {e}")
    exit()

# 2. 판독 함수
def analyze_bias(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)
        
    prob_liberal = probs[0][0].item() * 100
    prob_conservative = probs[0][1].item() * 100
    
    label = "🔴 보수" if prob_conservative > prob_liberal else "🔵 진보"
    score = max(prob_conservative, prob_liberal)
    
    print(f"\n문장: {text}")
    print(f"판독: {label} ({score:.1f}%)")

# 3. 테스트
analyze_bias("대통령의 결단이 경제를 살렸다.")
analyze_bias("검찰 독재 정권의 폭주를 막아야 한다.")