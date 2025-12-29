import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def test_naver_news_force(keyword):
    print(f"🕵️ [강력 모드] '{keyword}' 검색 중...")

    # 1. 브라우저 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 창 뜨는 거 보려면 주석 유지
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 봇 탐지 회피 옵션 추가
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 2. 검색 페이지 접속
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
        driver.get(url)
        time.sleep(3) # 로딩 시간 넉넉히

        # 3. [핵심 수정] 복잡한 경로 다 무시하고, 화면에 있는 'n.news.naver.com' 링크를 싹 긁어옴
        print("🔎 화면 내 '네이버 뉴스' 링크 스캔 중...")
        
        # CSS 선택자: a 태그 중에 href 속성에 'n.news.naver.com'이 포함된 모든 요소
        naver_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='n.news.naver.com']")
        
        real_link = None
        
        # 찾은 링크들 중에서 'news.naver.com'이 포함된 진짜 뉴스 링크만 필터링
        # (가끔 스포츠/연예 뉴스가 섞일 수 있으나 일단 진행)
        for item in naver_links:
            link = item.get_attribute("href")
            # 이상한 링크 제외하고 진짜 뉴스 링크만 선택
            if "n.news.naver.com/mnews/article" in link:
                real_link = link
                print(f"✅ 유효한 링크 발견: {real_link}")
                break
        
        if not real_link:
            print("❌ '네이버 뉴스' 포맷의 기사를 찾을 수 없습니다. (페이지 소스 확인 필요)")
            # 디버깅용: 현재 페이지의 a 태그 몇 개인지 출력
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"   (참고: 현재 페이지에 링크 총 {len(all_links)}개 있음)")
            return

        # 4. 상세 페이지 이동
        print("🚀 상세 페이지로 이동...")
        driver.get(real_link)
        time.sleep(2)

        print("\n" + "="*40)
        
        # 제목
        try:
            title = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']").get_attribute("content")
        except:
            title = driver.title
        print(f"📌 제목: {title}")

        # 본문 (dic_area)
        try:
            content_elem = driver.find_element(By.ID, "dic_area")
            content = content_elem.text
            print("✅ 본문 추출 성공 (dic_area 찾음)")
        except:
            print("⚠️ 일반 뉴스 포맷 아님 (연예/스포츠일 가능성)")
            try:
                content = driver.find_element(By.ID, "articeBody").text
                print("✅ 본문 추출 성공 (articeBody 찾음)")
            except:
                content = "본문 요소를 찾지 못함"

        print("-" * 40)
        print(f"📄 내용 미리보기:\n{content[:200]}")
        print("=" * 40)

    except Exception as e:
        print(f"🚨 에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_naver_news_force("의대정원")