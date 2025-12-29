import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def test_single_article_crawl(keyword):
    print(f"🕵️ 테스트 시작: '{keyword}' 검색 중...")

    # 1. 브라우저 설정 (창 뜨는 거 보고 싶으면 headless 주석 처리)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless")  # 눈으로 확인하려면 주석 처리하세요!

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 2. 네이버 뉴스 검색
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
        driver.get(url)
        time.sleep(2) # 로딩 대기

        # 3. 첫 번째 기사 링크 찾기
        try:
            first_article_btn = driver.find_element(By.CSS_SELECTOR, "a.news_tit")
            link_url = first_article_btn.get_attribute("href")
            print(f"🔗 찾은 링크: {link_url}")
        except:
            print("❌ 기사를 찾을 수 없습니다. 선택자가 바뀌었거나 검색 결과가 없습니다.")
            return

        # 4. 상세 페이지 이동 (Deep Crawling)
        print("🚀 상세 페이지로 이동 중...")
        driver.get(link_url)
        time.sleep(2) # 로딩 대기

        # 5. 제목과 본문 추출 테스트
        print("\n" + "="*40)
        
        # (1) 제목 추출
        try:
            # 메타 태그가 가장 정확함
            title = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']").get_attribute("content")
        except:
            title = driver.title
        
        print(f"✅ [제목]: {title}")

        # (2) 본문 추출 (핵심!)
        # 네이버 뉴스 포맷(news.naver.com)인지, 언론사 자체 사이트인지에 따라 다름
        content = ""
        try:
            # 시도 A: 네이버 뉴스 표준 포맷 (dic_area)
            content_elem = driver.find_element(By.ID, "dic_area")
            content = content_elem.text
            print("✅ [유형]: 네이버 뉴스 포맷 (성공)")
        except:
            try:
                # 시도 B: 스포츠/연예 뉴스 포맷 (articeBody)
                content_elem = driver.find_element(By.ID, "articeBody")
                content = content_elem.text
                print("✅ [유형]: 스포츠/연예 뉴스 포맷 (성공)")
            except:
                # 시도 C: 언론사 자체 홈페이지 (구조가 제각각이라 body 전체를 긁음)
                print("⚠️ [유형]: 언론사 자체 홈페이지 (네이버 포맷 아님)")
                content = driver.find_element(By.TAG_NAME, "body").text
                # body를 긁으면 메뉴 등 잡다한 텍스트가 많으므로, 줄바꿈 기준으로 긴 문단만 필터링하는 게 팁입니다.

        print("-" * 40)
        print(f"📄 [본문 내용 (앞부분 300자만 출력)]:\n")
        print(content[:300] + "..." if len(content) > 300 else content)
        print("=" * 40)

    except Exception as e:
        print(f"🚨 에러 발생: {e}")
    finally:
        print("\n브라우저 종료 중...")
        driver.quit()

# 실행
if __name__ == "__main__":
    # 궁금한 키워드로 테스트 해보세요
    test_single_article_crawl("의대정원")