from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
import os
from dotenv import load_dotenv

# .env 파일에 있는 내용을 불러옵니다
load_dotenv()

app = Flask(__name__)

# [중요] 프론트엔드에서 API를 호출할 수 있도록 허용 (CORS 설정)
CORS(app)

# 1. MySQL 데이터베이스 연결 설정
# 본인의 MySQL 설정에 맞게 수정해주세요!
db_config = {
    'host': os.getenv("DB_HOST"),      
    'user': os.getenv("DB_USER"),      
    'port' : int(os.getenv("DB_PORT")),            
    'password': os.getenv("DB_NAME"),               
    'db': os.getenv("DB_NAME"),                
    'charset': 'utf8mb4',                # 한글 깨짐 방지
    'cursorclass': pymysql.cursors.DictCursor # 데이터를 딕셔너리 형태(Key:Value)로 가져옴
}

# 2. API 엔드포인트: 전체 뉴스 데이터 조회, 카테고리 선택기능 추가
# 카테고리 : 사용자가 환경을 누르면 환경뉴스만, 노동을 누르면 노동 뉴스만 나오게 하는 기능
@app.route('/api/news', methods=['GET'])
def get_news():
    conn = None
    try:
        
        # DB 연결
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. 프론트엔드에서 보낸 'category' 파라미터 받기
        # 예: http://localhost:5000/api/news?category=환경
        # 주소창에서 category : 정치 같은 값 받아오기
        category_filter = request.args.get('category')

        # 2. SQL 쿼리 동적 작성
        if category_filter:
            # 카테고리가 있으면 해당 카테고리만 최신순 조회
            # %s는 보안을 위해 사용하는 안전한 방식입니다.
            sql = "SELECT * FROM NEWS_ARTICLES WHERE category = %s ORDER BY created_at DESC LIMIT 30"
            cursor.execute(sql, (category_filter,))
        else:
            # 없으면 전체 조회 (기존 방식)
            sql = "SELECT * FROM NEWS_ARTICLES ORDER BY created_at DESC LIMIT 30"
            cursor.execute(sql)
        
        result = cursor.fetchall()
        
        return jsonify({
            'status': 'success', 
            'count': len(result),
            'data': result
        })

    except Exception as e:
        print("에러 발생:", e) # 터미널에서도 에러를 볼 수 있게 출력
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    finally:
        if conn:
            conn.close()

@app.route('/api/news/<int:news_id>', methods=['GET'])
def get_news_detail(news_id):
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        # 1. URL에 적힌 숫자(news_id)에 해당하는 기사 1개만 찾기
        sql = "SELECT * FROM NEWS_ARTICLES WHERE id = %s"
        cursor.execute(sql, (news_id,))
        
        result = cursor.fetchone() # 하나만 가져오므로 fetchall() 대신 fetchone() 사용

        if result:
            return jsonify({'status': 'success', 'data': result})
        else:
            # DB에 해당 ID가 없는 경우 (404 에러 반환)
            return jsonify({'status': 'error', 'message': '기사를 찾을 수 없습니다.'}), 404

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    finally:
        if conn:
            conn.close()

# 서버 실행
if __name__ == '__main__':
    app.run(debug=True, port=5000)