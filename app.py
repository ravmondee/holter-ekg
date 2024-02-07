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

# defincja zmiennych globalnych
przesuniecie = 0
fs = 360
nazwa_pliku = '100'
record_all, fields = wfdb.rdsamp(nazwa_pliku, sampfrom=0)
qrs_inds_all = wfdb.processing.xqrs_detect(sig=record_all[:, 0], fs=fields['fs'])
rr_all = wfdb.processing.ann2rr(nazwa_pliku, 'atr', as_array=True)
mean_hr_all = wfdb.processing.calc_mean_hr(rr_all, fs, rr_units='samples')
heart_rate_all = wfdb.processing.compute_hr(len(record_all), qrs_inds_all, fs)
annotacje_all = wfdb.rdann(nazwa_pliku, 'atr', sampfrom=0, sampto=len(record_all))



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
    session.pop("user", None)
    return render_template('blad_logowania.html')


@app.route('/logout', methods=["POST"])
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
    if "user" in session:
        user = session["user"]

        global record_all, qrs_inds_all, rr_all, mean_hr_all, heart_rate_all, annotacje_all, przesuniecie
        
        # Reakcja na przyciski przesuniecia
        if 'przesuniecie' in request.args:
            przesuniecie += int(request.args['przesuniecie'])
        # ustalenie granic wykresu po kliknieciu
        sampfrom = przesuniecie
        sampto = przesuniecie + 3000

        # pobranie rekordów z pliku
        record, fields = wfdb.rdsamp(nazwa_pliku, sampfrom=sampfrom, sampto=sampto)
        
        # zamiana sampli na czas
        # jeszcze nie używamy czasu na razie pracujemy na samplach
        czas_start = sampfrom / fs
        czas_stop = sampto / fs
        # zdefiniowanie osi x dla wykresu
        os_x = range(sampfrom, sampto)

        # obliczenia qrs, rr, heart rate oraz pobranie annotacji
        qrs_inds = wfdb.processing.xqrs_detect(sig=record[:, 0], fs=fields['fs'])
        rr = wfdb.processing.ann2rr(nazwa_pliku, 'atr', as_array=True)
        mean_hr = wfdb.processing.calc_mean_hr(rr, fs, rr_units='samples')
        heart_rate = wfdb.processing.compute_hr(len(record), qrs_inds, fs)
        annotacje = wfdb.rdann(nazwa_pliku, 'atr', sampfrom=sampfrom, sampto=sampto)
        
        # wykres z zaznaczonymi qrs
        # fig=wfdb.plot_items(signal=record, ann_samp=[qrs_inds],return_fig=True)
        # fig=wfdb.plot_wfdb(record=record, annotation=annotacje,plot_sym=True,title='MIT-BIH Record 100',figsize=(20,6),return_fig=True)
        # fig.savefig("ann.png")

        # przekształcenia
        float_mean_hr = float(mean_hr)
        count_N = 0
        count_A = 0

        float_mean_hr_all = float(mean_hr_all)
        count_N_all = 0
        count_A_all = 0

        float_hr = []

        float_hr_all = []

        for i in heart_rate:
            if numpy.isnan(i):
                float_hr.append(float_mean_hr)
            else:
                float_hr.append(float(i))
        
        for i in heart_rate_all:
            if numpy.isnan(i):
                float_hr_all.append(float_mean_hr_all)
            else:
                float_hr_all.append(float(i))

        char_symbol = []

        for i in annotacje.symbol:
            char_symbol.append(str(i))
        
        char_symbol_all = []

        for i in annotacje_all.symbol:
            char_symbol_all.append(str(i))

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

        total_ann_all = len(annotacje_all.symbol)

        count_N_all = char_symbol_all.count('N')
        count_A_all = char_symbol_all.count('A')

        # Średni HR, Max HR, Min HR
        avg_hr = f"{mean_hr:.2f}"

        avg_hr_all = f"{mean_hr:.2f}"

        max_hr = f"{max(float_hr):.2f}"
        min_hr = f"{min(float_hr):.2f}"

        max_hr_all = f"{max(float_hr_all):.2f}"
        min_hr_all = f"{min(float_hr_all):.2f}"

        # Plot signal
        # plt.figure(figsize=(20, 6))
        # plt.style.use('ggplot')
        # plt.plot(record[:, 1], label='Channel 1')
        # plt.title('MIT-BIH Record 100')
        # plt.xlabel('Time (samples)')
        # plt.ylabel('ECG Signal')

        # Save plot to BytesIO buffer
        buf = BytesIO()
        plt.figure(figsize=(12, 6))
        plt.plot(os_x, record)
        plt.title('ECG Signal')
        plt.xlabel('Sample')
        plt.ylabel('Amplitude')

        # Dodaj zaznaczenia annotacji
        for sample, symbol in zip(annotacje.sample, annotacje.symbol):
            if sampfrom <= sample < sampto and sample < len(record_all):
                plt.text(sample, record_all[sample, 0], symbol, fontsize=10, color='red')

        plt.grid(True)
        plt.tight_layout()
        # plt.show()
        # buf1 = BytesIO()
        plt.savefig(buf, format='png')
        # fig.savefig(buf1, format='png')
        buf.seek(0)
        plt.close()

        # Convert image to base64
        chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        # chart_data1 = base64.b64encode(buf1.read()).decode('utf-8')
        # zwrócenie wszystkich danych do html
        return render_template('analiza.html', chart_data=chart_data, avg_hr=avg_hr, max_hr=max_hr, min_hr=min_hr,
                               total_ann=total_ann, count_N=count_N, count_A=count_A, avg_hr_all=avg_hr_all, max_hr_all=max_hr_all, min_hr_all=min_hr_all,
                               total_ann_all=total_ann_all, count_N_all=count_N_all, count_A_all=count_A_all, content=user)
    else:
        return redirect(url_for('login'))


@app.route('/download_pdf')
def download_pdf():
    pass


if __name__ == '__main__':
    app.run(port=5555,threaded=False)
