from flask import Flask, render_template, request, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

@app.route('/')
def startpage():

    return render_template('startpage.html')

@app.route('/signup',methods=['GET','POST'])
def signup():

    run_record_result = None
    userid = None
    password = None
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']

        db = sqlite3.connect('marathon.db')
        cursor = db.cursor()

        sql_query_sign ='''
        insert into login
        values (?,?)
        '''

        cursor.execute(sql_query_sign, (userid, password,))
        db.commit() # 커밋을 통해 insert 실행
        db.close()

    return render_template('signup.html', userid = userid)

@app.route('/login')
def login():

    return render_template('login.html')

@app.route('/home', methods=['GET','POST'])
def home():
    run_record_result = None
    if request.method == 'POST':
        if 'distance' in request.form:
            distance = request.form['distance']
            print(distance)

            db = sqlite3.connect('marathon.db')
            cursor = db.cursor()

            sql_query_records = '''
            SELECT *
            FROM run_records
            WHERE distance = ?
            ORDER BY pace ASC, time ASC;
            '''

            cursor.execute(sql_query_records, (distance,))
            run_record_result = cursor.fetchall() 
            db.close()

    return render_template('home.html', run_record_result=run_record_result)

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
            db.close()

            # 평균 시간 저장
            avg_time=result[0]
            session['avg_time'] = avg_time
            print(result[0])
        
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

    return render_template('my_recommand_run.html', age=age, sex=sex, avg_time=avg_time, height=height, run_cadence_result=run_cadence_result)

@app.route('/run_record')
def run_record():
    return render_template('run_record.html')

@app.route('/run_record_search')
def run_record_search():
    return render_template('run_record_search.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='127.0.0.1', port=5000)