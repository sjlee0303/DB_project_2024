from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

# get : 서버에서 데이터를 가져올 때 사용
# post : 클라이언트가 서버로 데이터를 보낼때 사용
@app.route('/my_recommand_run', methods=['GET','POST'])
def my_recommand_run():

    # db에 어느 테이블이 있는지 확인하는 코드
    #cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    #tables = cursor.fetchall()
    #print("Tables in the database:", tables)
    age = None
    sex = None
    avg_time = None
    if request.method == 'POST' :
        # 사용자 입력 가져오기
        age = int(request.form['age'])
        sex = request.form['sex']

        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        squl_query = '''
        WITH combined_times AS (
            SELECT "Official Time" AS time
            FROM marathon_results_2015 
            where "M/F" = ? and age BETWEEN ? and ?
            UNION ALL
            SELECT "Official Time"
            FROM marathon_results_2016
            where "M/F" = ? and age BETWEEN ? and ?
            UNION ALL
            SELECT "Official Time"
            FROM marathon_results_2017 
            where "M/F" = ? and age BETWEEN ? and ?
        ),
        time_in_seconds AS (
            SELECT 
                time,
                CAST(SUBSTR(TRIM(time), 1, 2) AS INTEGER) * 3600 +
                CAST(SUBSTR(TRIM(time), 3, 2) AS INTEGER) * 60 + 
                CAST(SUBSTR(TRIM(time), 6, 2) AS INTEGER) 
                AS total_seconds
            FROM combined_times
        ),
        average_seconds AS (
            SELECT AVG(total_seconds) AS avg_seconds
            FROM time_in_seconds
        )
        SELECT 
            CAST(avg_seconds / 3600 AS INTEGER) || ':' || -- Hours
            PRINTF('%02d', (avg_seconds % 3600) / 60) || ':' || -- Minutes
            PRINTF('%02d', avg_seconds % 60) AS avg_time -- Seconds
        FROM average_seconds;
        '''
    
        cursor.execute(squl_query, (sex, age-5, age+5, sex, age-5, age+5, sex, age-5, age+5))
        result = cursor.fetchone()
        db.close()

        # 평균 시간 저장
        avg_time=result[0]
        print(result[0])

    return render_template('my_recommand_run.html', age=age, sex=sex, avg_time=avg_time)

@app.route('/run_record', methods=['GET', 'POST'])
def run_record():
    if request.method == 'POST':
        # 폼 데이터 가져오기
        runner_id = request.form['runner_id']
        distance = request.form['distance']
        pace = request.form['pace']
        time = request.form['time']

        # SQLite 데이터베이스 연결
        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        # 데이터 저장
        cursor.execute(
            "INSERT INTO run_records (runner_id, distance, pace, time) VALUES (?, ?, ?, ?)",
            (runner_id, distance, pace, time)
        )
        db.commit()
        db.close()

        # 성공 메시지
        return "<h1>RUN 기록이 성공적으로 저장되었습니다!</h1>"
    return render_template('run_record.html')


@app.route('/run_record_search', methods=['GET'])
def run_record_search():
    # SQLite 데이터베이스 연결
    db = sqlite3.connect('marathon.db')
    cursor = db.cursor()

    # 사용자 입력 가져오기
    runner_id = request.args.get('runner_id')
    distance = request.args.get('distance')

    # 기본 쿼리
    query = '''
    SELECT
        id,
        runner_id,
        distance,
        pace,
        time,
        RANK() OVER (PARTITION BY distance ORDER BY 
            CAST(SUBSTR(time, 1, 2) AS INTEGER) * 3600 +
            CAST(SUBSTR(time, 4, 2) AS INTEGER) * 60 +
            CAST(SUBSTR(time, 7, 2) AS INTEGER)
        ) AS rank
    FROM run_records
    WHERE 1=1
    '''

    # 조건 추가
    params = []
    if runner_id:
        query += " AND runner_id = ?"
        params.append(runner_id)
    if distance:
        query += " AND distance = ?"
        params.append(distance)

    # 정렬 추가
    query += " ORDER BY distance, rank"

    # 쿼리 실행
    cursor.execute(query, params)
    runs = cursor.fetchall()
    db.close()

    return render_template('run_record_search.html', runs=runs)




if __name__ == '__main__':
    app.debug = True
    app.run(host='127.0.0.1', port=5000)