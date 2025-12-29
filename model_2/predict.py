import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_PATH = "./my_bias_model"

print(f"📂 AI 모델 로딩 중... ({MODEL_PATH})")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    model.eval()
    print("✅ AI 로딩 완료!")
except Exception as e:
    print(f"🚨 로딩 실패: {e}")
    exit()

# 🔥 [수정됨] 제목(title)과 본문(content)을 같이 받습니다.
def get_bias(title, content):
    # 1. 모델이 글을 다 못 읽으므로, 중요한 부분만 잘라서 합치기 전략!
    # 제목 + 본문 앞 150자 + 본문 뒤 150자 (보통 주장은 끝에 있음)
    if len(content) > 300:
        processed_content = title + " " + content[:150] + " ... " + content[-150:]
    else:
        processed_content = title + " " + content

    inputs = tokenizer(
        processed_content, 
        return_tensors="pt", 
        truncation=True, 
        padding=True, 
        max_length=512  # 모델이 허용하는 최대 길이
    )
    
    # 3. 예측
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)

    prob_liberal = probs[0][0].item() * 100
    prob_conservative = probs[0][1].item() * 100
    
    if prob_conservative > prob_liberal:
        return "보수", round(prob_conservative, 2)
    else:
        return "진보", round(prob_liberal, 2)

# =========================================================
# 테스트
# =========================================================
if __name__ == "__main__":
    print("\n[ 📢 고성능 정치 성향 분석기 (본문 포함) ]")
    
    # 예시 1: 제목은 애매하지만 본문이 진보인 경우
    t1 = "정부, 새로운 세제 개편안 발표"
    c1 = "이번 개편안은 사실상 부자 감세라는 비판을 피하기 어렵다. 서민들의 혜택은 줄어들고 대기업 혜택만 늘어났다."
    res1, score1 = get_bias(t1, c1)
    print(f"\n기사1: {t1}\n판독: {res1} ({score1}%)")
    
    # 예시 2: 제목은 평범하지만 본문이 보수인 경우
    t2 = "에너지 정책, 다시 원점으로"
    c2 = "지난 정부의 탈원전 정책으로 한전 적자가 심각하다. 원전 생태계를 복원하여 에너지 안보를 지켜야 한다."
    res2, score2 = get_bias(t2, c2)
    print(f"\n기사2: {t2}\n판독: {res2} ({score2}%)")

    # 직접 입력 모드
    while True:
        print("\n" + "-"*30)
        user_title = input("📝 제목 입력 (종료: q): ")
        if user_title.lower() == 'q': break
        user_content = input("📝 본문 입력 (없으면 엔터): ")
        
        result, score = get_bias(user_title, user_content)
        print(f"👉 결과: {result} (확신도: {score}%)")