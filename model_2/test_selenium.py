from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def test_selenium_debug(keyword):
    print(f"🕵️‍♂️ [진단] '{keyword}' 검색 시작 (로봇 흔적 지우기 적용)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 🔥 [핵심] "나 로봇 아니야!"라고 속이는 결정적인 옵션
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # 윈도우 크기도 사람처럼 크게 설정
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
        driver.get(url)
        time.sleep(5) # 로딩 넉넉하게 5초 대기
        
        # 1. 현재 어떤 페이지에 있는지 확인
        print(f"👀 현재 페이지 제목: {driver.title}")
        print(f"🔗 현재 URL: {driver.current_url}")
        
        # 2. 기사 제목 태그(a.news_tit) 찾기 시도
        titles = driver.find_elements(By.CSS_SELECTOR, "a.news_tit")
        
        if len(titles) > 0:
            print(f"\n🎉 성공! 기사 {len(titles)}개를 찾았습니다!")
            for t in titles[:3]:
                print(f"- {t.text}")
        else:
            print("\n🚨 여전히 0개입니다. 혹시 클래스명이 다를까요?")
            # 3. 만약 못 찾으면, '뉴스' 비슷한 거라도 긁어보기 (구조 파악용)
            print("👉 화면에 있는 '링크(a)' 태그들을 무작위로 5개 조사합니다:")
            all_links = driver.find_elements(By.TAG_NAME, "a")
            count = 0
            for link in all_links:
                txt = link.text.strip()
                if len(txt) > 10: # 글자가 좀 긴 것만 출력 (뉴스 제목일 확률 높음)
                    print(f"   [후보] {txt} (클래스: {link.get_attribute('class')})")
                    count += 1
                    if count >= 5: break

    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")
        
    finally:
        print("\n(브라우저를 닫습니다...)")
        driver.quit()

if __name__ == "__main__":
    test_selenium_debug("의대정원")