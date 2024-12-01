from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/my_recommand_run')
def my_recommand_run():
    return render_template('my_recommand_run.html')

@app.route('/run_record')
def run_record():
    return render_template('run_record.html')

@app.route('/run_record_search')
def run_record_search():
    return render_template('run_record_search.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='127.0.0.1', port=5000)