from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
from sqlite3 import IntegrityError

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

@app.route('/')
def startpage():

    return render_template('startpage.html')

@app.route('/signup',methods=['GET','POST'])
def signup():

    userid = None
    password = None
    err_msg = None
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']

        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        sql_query_sign ='''
        insert into login
        values (?,?)
        '''

        try :
            cursor.execute(sql_query_sign, (userid, password,))
            db.commit() # 커밋을 통해 insert 실행
        except IntegrityError:
            err_msg = "이미 사용 중인 아이디입니다. 다른 아이디를 사용해주세요."
        db.close()

    return render_template('signup.html', userid = userid, err_msg=err_msg)

@app.route('/login',methods=['GET','POST'])
def login():

    userid = None
    password = None
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']

        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        sql_query_login = '''
        select passwd
        from login
        where id = ?
        '''
        cursor.execute(sql_query_login, (userid,))
        result = cursor.fetchone()
        passwd = result[0]

        if password == passwd :
            session['userid'] = userid
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/home', methods=['GET','POST'])
def home():
    userid = session.get('userid',None)
    run_record_result = None
    selected_distance = None

    if request.method == 'POST':
        if 'distance' in request.form:
            distance = request.form['distance']
            selected_distance = distance
            print(distance)

            db = sqlite3.connect('marathon.db')
            cursor = db.cursor()

            sql_query_records = '''
            SELECT 
                id,
                runner_id,
                distance,
                pace,
                time,
                CAST(SUBSTR(TRIM(time), 1, 2) AS INTEGER) * 3600 +
                CAST(SUBSTR(TRIM(time), 4, 2) AS INTEGER) * 60 +
                CAST(SUBSTR(TRIM(time), 7, 2) AS INTEGER) 
                AS total_seconds
            FROM run_records
            WHERE distance = ?
            order by total_seconds asc, id asc
            '''

            cursor.execute(sql_query_records, (distance,))
            run_record_result = cursor.fetchall() 
            db.close()

    return render_template('home.html', run_record_result=run_record_result, userid=userid, selected_distance=selected_distance)

# get : 서버에서 데이터를 가져올 때 사용
# post : 클라이언트가 서버로 데이터를 보낼때 사용
@app.route('/my_recommand_run', methods=['GET','POST'])
def my_recommand_run():

    # db에 어느 테이블이 있는지 확인하는 코드
    #cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    #tables = cursor.fetchall()
    #print("Tables in the database:", tables)
    
    # 세션에서 이전 값 가져오기
    age = session.get('age', None)
    sex = session.get('sex', None)
    avg_time = session.get('avg_time', None)
    height = session.get('height', None)
    run_cadence_result = session.get('run_cadence_result', None)


    if request.method == 'POST' :
        # 사용자 입력 가져오기
        if 'age' in request.form and 'sex' in request.form:
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
            "db.close()"

            # 평균 시간 저장
            avg_time=result[0]
            session['avg_time'] = avg_time
            print(result[0])

            # 평균 시간을 초 단위로 변환
            avg_time_parts = list(map(int, avg_time.split(':')))
            avg_time_seconds = avg_time_parts[0] * 3600 + avg_time_parts[1] * 60 + avg_time_parts[2]

            # 풀 코스 평균 페이스 계산
            average_pace_per_km_seconds = avg_time_seconds / 42.195
            pace_minutes = int(average_pace_per_km_seconds // 60)
            pace_seconds = int(average_pace_per_km_seconds % 60)

            # 평균 페이스 출력
            average_pace = f"{pace_minutes}:{pace_seconds:02d}"

            # marathon_pace_chart 테이블에서 가장 가까운 값 찾기
            pace_query = '''
            SELECT *, 
                ABS(
                    CAST(SUBSTR(TRIM("42.195km"), 1, 1) AS INTEGER) * 3600 +
                    CAST(SUBSTR(TRIM("42.195km"), 3, 2) AS INTEGER) * 60 + 
                    CAST(SUBSTR(TRIM("42.195km"), 6, 2) AS INTEGER) - ?
                ) AS time_diff
            FROM marathon_pace_chart
            ORDER BY time_diff ASC
            LIMIT 1;
            '''
            cursor.execute(pace_query, (avg_time_seconds,))
            closest_tuple = cursor.fetchone()
            db.close()
        
        if 'height' in request.form:
            height = float(request.form['height'])

            db = sqlite3.connect('marathon.db')
            cursor = db.cursor()

            sql_stride_query = '''
            WITH calculated_stride AS (
                SELECT ? * 0.5 AS stride_cm
            ),
            closest_stride AS (
                SELECT stride_cm
                FROM run_cadence
                ORDER BY ABS(stride_cm - (SELECT stride_cm FROM calculated_stride)) ASC
                LIMIT 1 
            )
            SELECT *
            FROM run_cadence
            WHERE stride_cm = (SELECT stride_cm FROM closest_stride);
            '''

            cursor.execute(sql_stride_query, (height,))
            run_cadence_result = cursor.fetchall() # 모든 결과 가져오기
            db.close()

            session['height'] = height
            session['run_cadence_result'] = run_cadence_result

        session['age'] = age
        session['sex'] = sex

    return render_template('my_recommand_run.html', age=age, sex=sex, avg_time=avg_time, closest_tuple=closest_tuple, average_pace = average_pace, height=height, run_cadence_result=run_cadence_result)

@app.route('/run_record', methods=['GET', 'POST'])
def run_record():
    userid = session.get('userid', None)  # 로그인한 사용자 ID 가져오기
    if not userid:
        return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 이동

    if request.method == 'POST':
        # 폼 데이터 가져오기
        distance = request.form['distance']
        time = request.form['time']

        # 거리 값을 숫자로 변환 (e.g., "10km" → 10)
        distance_km = float(distance.replace('km', '').replace('half', '21.1').replace('full', '42.2'))

        # 완주 시간을 초 단위로 변환
        hours, minutes, seconds = map(int, time.split(':'))
        total_seconds = hours * 3600 + minutes * 60 + seconds

        # Pace 계산 (분/킬로미터)
        pace_seconds = total_seconds / distance_km
        pace_minutes = int(pace_seconds // 60)
        pace_remaining_seconds = int(pace_seconds % 60)
        pace = f"{pace_minutes:02d}:{pace_remaining_seconds:02d}"
        time_02d = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # SQLite 데이터베이스 연결
        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        # 데이터 저장
        cursor.execute(
            "INSERT INTO run_records (runner_id, distance, pace, time) VALUES (?, ?, ?, ?)",
            (userid, distance, pace, time_02d)
        )
        db.commit()
        db.close()

        # 저장 완료 페이지 렌더링
        message = f"RUN 기록이 성공적으로 저장되었습니다! (Pace: {pace} 분/킬로미터)"
        return render_template('run_record_success.html', userid=userid, message=message)
    return render_template('run_record.html', userid=userid)


@app.route('/run_record_search', methods=['GET'])
def run_record_search():
    userid = session.get('userid', None)  # 로그인한 사용자 ID 가져오기
    if not userid:
        return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 이동

    db = sqlite3.connect('marathon.db')
    cursor = db.cursor()

    runs = []
    query = "SELECT * FROM run_records WHERE runner_id = ?"
    cursor.execute(query, (userid,))
    runs = cursor.fetchall()

    db.close()
    return render_template('run_record_search.html', runs=runs, userid=userid)


@app.route('/update_run_record', methods=['POST'])
def update_run_record():
    record_id = request.form['record_id']
    new_distance = request.form['distance']
    new_pace = request.form['pace']
    new_time = request.form['time']
    runner_id = request.form['runner_id']  # 수정 후 검색 유지

    pace_minutes, pace_remaining_seconds = map(int, new_pace.split(':'))
    new_pace_02d = f"{pace_minutes:02d}:{pace_remaining_seconds:02d}"

    hours, minutes, seconds = map(int, new_time.split(':'))
    new_time_02d = f"{hours:02d}:{minutes:02d}:{seconds:02d}"


    db = sqlite3.connect('marathon.db')
    cursor = db.cursor()

    query = '''
    UPDATE run_records
    SET distance = ?, pace = ?, time = ?
    WHERE id = ?
    '''
    cursor.execute(query, (new_distance, new_pace_02d, new_time_02d, record_id))
    db.commit()
    db.close()

    return redirect(f'/run_record_search?runner_id={runner_id}')


@app.route('/delete_run_records', methods=['POST'])
def delete_run_records():
    # 선택된 record_ids 가져오기
    record_ids = request.form.getlist('record_ids')
    runner_id = request.form['runner_id']  # 삭제 후 검색 유지

    if not record_ids:
        return "<h1>Error: No records selected for deletion</h1>"

    db = sqlite3.connect('marathon.db')
    cursor = db.cursor()

    try:
        # SQL 쿼리로 record_ids 삭제
        query = f"DELETE FROM run_records WHERE id IN ({','.join(['?'] * len(record_ids))})"
        cursor.execute(query, record_ids)
        db.commit()
    except Exception as e:
        db.rollback()
        return f"<h1>Error during deletion: {e}</h1>"
    finally:
        db.close()

    # 삭제 후 동일 Runner ID 검색 페이지로 이동
    return redirect(f'/run_record_search?runner_id={runner_id}')


if __name__ == '__main__':
    app.debug = True
    app.run(host='127.0.0.1', port=5000)