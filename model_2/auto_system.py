import os
import time
import random
import schedule
import pymysql
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from predict import get_bias

load_dotenv()

DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME"),
    'port': int(os.getenv("DB_PORT")),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def job():
    keywords = ["검찰개혁","공수처","노란봉투법","탈원전", "대북정책" ] 
    print(f"\n⏰ [Auto System] 정기 작업 시작: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for keyword in keywords:
        # 키워드당 최대 20개까지 수집하도록 설정
        crawl_and_analyze(keyword, limit=20)
        
    print(f"💤 작업 완료. 다음 스케줄 대기 중... (4시간 뒤 실행)\n")

def crawl_and_analyze(keyword, limit=20):
    print(f"🚀 '{keyword}' 뉴스 수집 시작 (목표: {limit}개)...")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless") # 서버용
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    conn = None

    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1" 
        # &sort=1 추가: '최신순'으로 정렬 (중복 줄이고 새 기사 찾기에 유리함)
        
        driver.get(url)
        time.sleep(2)

        # 🔥 [추가된 기능] 스크롤을 내려서 기사를 더 불러옵니다.
        # 네이버는 스크롤을 내려야 다음 기사들이 로딩됩니다.
        for _ in range(3): # 3번 정도 내리면 30~40개 정도 로딩됨
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        # 링크 수집
        naver_links = []
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='n.news.naver.com']")
        
        for elm in elements:
            link = elm.get_attribute("href")
            if "n.news.naver.com/mnews/article" in link and link not in naver_links:
                naver_links.append(link)
        
        # 설정한 개수(limit)만큼만 자르기
        target_links = naver_links[:limit]
        print(f"🎯 발견된 네이버 뉴스: 총 {len(naver_links)}개 -> 상위 {len(target_links)}개 분석 시도")

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        new_article_count = 0

        for link in target_links:
            try:
                # 중복 체크
                check_sql = "SELECT id FROM NEWS_ARTICLES WHERE link = %s"
                cursor.execute(check_sql, (link,))
                if cursor.fetchone():
                    # 이미 있는 기사는 조용히 넘어감 (로그 너무 많이 찍히는 것 방지)
                    continue

                driver.get(link)
                # 🔥 [수정] 랜덤하게 1.5초 ~ 3.5초 사이 쉬기 (사람처럼 보임)
                time.sleep(random.uniform(1.5, 3.5))

                try:
                    title = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']").get_attribute("content")
                except:
                    title = driver.title

                try:
                    content = driver.find_element(By.ID, "dic_area").text
                except:
                    continue # 본문 없으면 패스
                
                if len(content) < 50: continue

                # AI 분석
                bias_label, bias_score = get_bias(title, content)
                
                print(f"   🆕 [신규] {bias_label}: {title[:10]}...")

                insert_sql = """
                    INSERT INTO NEWS_ARTICLES 
                    (keyword, title, content, link, bias, bias_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (keyword, title, content, link, bias_label, bias_score))
                conn.commit()
                new_article_count += 1

            except Exception as e:
                continue

        print(f"✨ '{keyword}' 처리 완료: 신규 저장 {new_article_count}건")

    except Exception as e:
        print(f"🚨 에러: {e}")
    finally:
        driver.quit()
        if conn: conn.close()

if __name__ == "__main__":
    print("🚀 시스템 가동 (4시간 주기 / 최신순 정렬 / 20개 수집)")
    
    job() # 시작하자마자 1회 실행

    # ⏰ [변경] 4시간마다 실행
    schedule.every(4).hours.do(job)

    # (옵션) 만약 특정 시간에만 하고 싶다면 아래처럼 쓰세요
    # schedule.every().day.at("09:00").do(job)
    # schedule.every().day.at("18:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)