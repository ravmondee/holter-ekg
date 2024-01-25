from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from io import BytesIO
import wfdb
import mpld3
import aspose.pdf as ap
import matplotlib.pyplot as plt
import base64

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/konfiguracja')
def konfiguracja():
    if request.method == 'get':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

        return redirect(url_for('index'))
    return render_template('konfiguracja.html')

@app.route('/analiza')
def analiza():
    record, fields = wfdb.rdsamp('C:/Users/Wojtek/Desktop/WatowskyMed/100', sampfrom=3000, sampto=6000)

    # Plot signal
    plt.figure(figsize=(10, 4))
    plt.plot(record[:, 1], label='Channel 1')
    plt.title('MIT-BIH Record 100')
    plt.xlabel('Time (samples)')
    plt.ylabel('ECG Signal')

    # Save plot to BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Convert image to base64
    chart_data = base64.b64encode(buf.read()).decode('utf-8')

    return render_template('analiza.html', chart_data=chart_data)


@app.route('/download_pdf')
def download_pdf():
    options = ap.HtmlLoadOptions()
    document = ap.Document("analiza.html", options)
    document.save("test.pdf")

if __name__ == '__main__':
    app.run()
