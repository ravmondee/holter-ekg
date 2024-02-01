from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from io import BytesIO
import wfdb
from wfdb import processing
import matplotlib.pyplot as plt
import base64
import numpy

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "klucz"

@app.route('/', methods=["POST", "GET"])
def login():
    if request.method == 'POST':
        user = request.form["login"]
        session["user"] = user
        if request.form["login"] == 'Lekarz' and request.form["password"] == '1234':
            return redirect(url_for('dashboard'))
        elif request.form["login"] == 'admin' and request.form["password"] == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('blad_logowania'))
    else:
        if "user" in session:
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/blad_logowania')
def blad_logowania():
    return render_template('blad_logowania.html')

@app.route('/logout',  methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if "user" in session:
        user = session["user"]
        return render_template('dashboard.html', content=user)
    else:
        return redirect(url_for('login'))
@app.route('/konfiguracja')
def konfiguracja():
     if "user" in session:
        user = session["user"]
        if request.method == 'get':
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

            return redirect(url_for('dashboard'))
        return render_template('konfiguracja.html', content=user)
     else:
         return redirect(url_for('login'))


@app.route('/analiza')
def analiza():
    global total_ann
    if "user" in session:
        user = session["user"]
        fs = 360
        nazwa_pliku = '100'
        record, fields = wfdb.rdsamp(nazwa_pliku, sampfrom=3000, sampto=6000)
        # Obliczenia
        qrs_inds = wfdb.processing.xqrs_detect(sig=record[:, 0], fs=fields['fs'])
        rr = wfdb.processing.ann2rr(nazwa_pliku, 'atr', as_array=True)
        mean_hr = wfdb.processing.calc_mean_hr(rr, fs, rr_units='samples')
        heart_rate = wfdb.processing.compute_hr(len(record), qrs_inds, fs)
        annotacje = wfdb.rdann(nazwa_pliku, 'atr')
        # wykres z zaznaczonymi qrs
        wfdb.plot_items(signal=record, ann_samp=[qrs_inds])

        # przekształcenia
        float_mean_hr = float(mean_hr)
        count_N = 0
        count_A = 0

        float_hr = []

        for i in heart_rate:
            if numpy.isnan(i):
                float_hr.append(float_mean_hr)
            else:
                float_hr.append(float(i))

        char_symbol = []

        for i in annotacje.symbol:
            char_symbol.append(str(i))

        # generacja pliku
        f = open("annotation_log.txt", "w")

        # Sprawdź, czy istnieją annotacje
        if annotacje.aux_note or annotacje.symbol:
            # Wyświetl informacje o annotacjach
            f.write(f"Average Heart Rate: {mean_hr:.2f}\n")
            f.write(f"Liczba annotacji: {len(annotacje.symbol)}\n")
            total_ann = len(annotacje.symbol)
            session["total_ann"] = total_ann
            f.write(f"Liczba annotacji N: {char_symbol.count('N')}\n")
            f.write(f"Liczba annotacji A: {char_symbol.count('A')}\n")
            count_N = char_symbol.count('N')
            count_A = char_symbol.count('A')
            session["count_N"] = count_N
            session["count_A"] = count_A
            f.write(f"Maksymalny heart rate: {max(float_hr):.2f}\n")
            f.write(f"Minimalny heart rate: {min(float_hr):.2f}\n")
            for i, (symbol, sample, hr) in enumerate(zip(annotacje.symbol, annotacje.sample, float_hr), start=1):
                czas = sample / annotacje.fs
                f.write(
                    f"sample nr: {sample}. Kod annotacji: {symbol}, Czas annotacji: {czas:.2f} sekundy, Heart rate: {hr:.2f}\n")

        f.close()

        # Średni HR, Max HR, Min HR
        avg_hr = f"{mean_hr:.2f}"
        max_hr = f"{max(float_hr):.2f}"
        min_hr = f"{min(float_hr):.2f}"

        # Plot signal
        plt.figure(figsize=(20, 6))
        plt.style.use('ggplot')
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
        return render_template('analiza.html', chart_data=chart_data, avg_hr=avg_hr, max_hr=max_hr, min_hr=min_hr, total_ann=total_ann, count_N=count_N, count_A=count_A, content=user)
    else:
        return redirect(url_for('login'))


@app.route('/download_pdf')
def download_pdf():
    pass

if __name__ == '__main__':
    app.run()
