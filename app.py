from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
from io import BytesIO
import wfdb
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import PickleType
from wfdb import processing
import matplotlib.pyplot as plt
import base64
import numpy
from scipy.signal import savgol_filter
import pyhrv.tools as tools
import pyhrv.time_domain as td
import pyhrv.frequency_domain as fd
import pyhrv.nonlinear as nl
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "klucz"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///measurements.db'
db = SQLAlchemy(app)

przesuniecie = 0
nazwa_pliku = '100'
if_time = True


class Measurement(db.Model):
    file = db.Column(db.String, primary_key=True)


#
# with app.app_context():
#     db.create_all()


def load_measurements(session):
    excluded_numbers = [110, 120]

    for measurement_number in range(100, 125):
        if measurement_number not in excluded_numbers:
            file_list = str(measurement_number)

            new_measurement = Measurement(file=file_list)
            session.add(new_measurement)

    session.commit()


# with app.app_context():
#     load_measurements(db.session)


def get_measurement_file(measurementa):
    measurement_file = Measurement.query.filter_by(file=measurementa).first()
    if measurement_file:
        return measurement_file.file
    else:
        return None


global pdf_mean_hr_all, pdf_max_hr_all, pdf_min_hr_all, pdf_total_ann_all, pdf_count_N_all, pdf_count_A_all, pdf_count_slash_all, pdf_count_V_all, pdf_count_L_all


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


@app.route('/blad_logowania', methods=["GET", "POST"])
def blad_logowania():
    session.pop("user", None)
    if request.method == 'POST':
        return redirect(url_for('login'))
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


@app.route('/konfiguracja', methods=['GET', 'POST'])
def konfiguracja():
    if "user" in session:
        user = session["user"]
        if request.method == 'POST':
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            session["start_date"] = start_date
            session["end_date"] = end_date
            return redirect(url_for('dashboard'))
        return render_template('konfiguracja.html', content=user)
    else:
        return redirect(url_for('login'))


@app.route('/analiza', methods=["GET", "POST"])
def analiza():
    if "user" in session:
        user = session["user"]

        global record_all, qrs_inds_all, rr_all, mean_hr_all, heart_rate_all, annotacje_all, przesuniecie, fs, nazwa_pliku, if_time

        plik = "measurements/100"

        with (app.app_context()):
            if request.method == 'POST':
                nazwa_pliku = request.form.get("nazwa_pliku")
                plik = f"measurements/{get_measurement_file(nazwa_pliku)}"
                przesuniecie = 0

        if 'time' in request.args:
            if_time = True
        if 'sample' in request.args:
            if_time = False

        record_all, fields = wfdb.rdsamp(plik, sampfrom=0)
        fs = fields['fs']
        sample = fields['sig_len']
        time_s = round(sample / fs, 2)
        time_m = round(time_s / 60, 2)
        session["pdf_time"] = time_m
        time_h = round(time_m / 60, 2)
        qrs_inds_all = wfdb.processing.xqrs_detect(sig=record_all[:, 0], fs=fs)
        count_qrs_all = len(qrs_inds_all)
        rr_all = wfdb.processing.ann2rr(plik, 'atr', as_array=True)
        mean_hr_all = wfdb.processing.calc_mean_hr(rr_all, fs, rr_units='samples')
        heart_rate_all = wfdb.processing.compute_hr(len(record_all), qrs_inds_all, fs)
        annotacje_all = wfdb.rdann(plik, 'atr', sampfrom=0, sampto=len(record_all))

        rr_intervals = tools.nn_intervals(annotacje_all.sample)

        s = td.sdnn(rr_intervals)
        r = td.rmssd(rr_intervals)
        p = td.nn50(rr_intervals)
        sdnn_all = round(float(s[0]), 2)
        rmssd_all = round(float(r[0]), 2)
        pnn50_all = round(float(p[0]), 2)

        # Reakcja na przyciski przesuniecia
        if 'przesuniecie' in request.args:
            przesuniecie += int(request.args['przesuniecie'])

        # ustalenie granic wykresu po kliknieciu
        sampfrom = przesuniecie
        sampto = przesuniecie + 3000

        # pobranie rekordów z pliku
        record, fields = wfdb.rdsamp(plik, sampfrom=sampfrom, sampto=sampto)

        # zamiana sampli na czas
        czas_start = round(sampfrom / fs, 2)
        czas_stop = round(sampto / fs, 2)
        czas_s = round(czas_stop - czas_start, 2)  # w sekundach
        czas_m = round(czas_s / 60, 2)  # w minutach
        czas_h = round(czas_m / 60, 2)  # w godzinach

        # zdefiniowanie osi x dla wykresu
        os_x = range(sampfrom, sampto)
        os_x_t = numpy.linspace(czas_start, czas_stop, len(record[:, 0]))

        # obliczenia qrs, rr, heart rate oraz pobranie annotacji

        qrs_inds = wfdb.processing.xqrs_detect(sig=record[:, 0], fs=fs)
        count_qrs = len(qrs_inds)
        rr = wfdb.processing.ann2rr(plik, 'atr', as_array=True)

        mean_hr = wfdb.processing.calc_mean_hr(rr, fs, rr_units='samples')
        heart_rate = wfdb.processing.compute_hr(len(record), qrs_inds, fs)
        annotacje = wfdb.rdann(plik, 'atr', sampfrom=sampfrom, sampto=sampto)

        rr_intervals = tools.nn_intervals(annotacje.sample)

        # obliczenia HRV
        s = td.sdnn(rr_intervals)
        r = td.rmssd(rr_intervals)
        p = td.nn50(rr_intervals)
        sdnn = round(float(s[0]), 2)
        rmssd = round(float(r[0]), 2)
        pnn50 = round(float(p[0]), 2)

        # przekształcenia
        float_mean_hr = float(mean_hr)
        count_N = 0
        count_A = 0
        count_slash = 0
        count_V = 0
        count_L = 0
        count_R = 0
        float_mean_hr_all = float(mean_hr_all)
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
            count_slash = char_symbol.count('/')
            count_V = char_symbol.count('V')
            count_L = char_symbol.count('L')
            count_R = char_symbol.count('R')
            session["count_N"] = count_N
            session["count_A"] = count_A
            session["count_slash"] = count_slash
            session["count_V"] = count_V
            session["count_L"] = count_L
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
        count_slash_all = char_symbol_all.count('/')
        count_V_all = char_symbol_all.count('V')
        count_L_all = char_symbol_all.count('L')
        count_R_all = char_symbol_all.count('R')

        session["pdf_mean_hr_all"] = mean_hr_all
        session["pdf_max_hr_all"] = max(float_hr)
        session["pdf_min_hr_all"] = min(float_hr)
        session["pdf_total_ann_all"] = total_ann_all
        session["pdf_count_N_all"] = count_N_all
        session["pdf_count_A_all"] = count_A_all
        session["pdf_count_slash_all"] = count_slash_all
        session["pdf_count_V_all"] = count_V_all
        session["pdf_count_L_all"] = count_L_all
        session["pdf_sdnn_all"] = sdnn_all
        session["pdf_rmssd_all"] = rmssd_all
        session["pdf_pnn50_all"] = pnn50_all

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
        # plotuje samo EKG
        if if_time:
            # plotuje z osią czasu
            plt.plot(os_x_t, record[:, 0])
        else:
            # plotuje z osią sampli
            plt.plot(os_x, record[:, 0])
        # plotuje EKG oraz to pomarańczowe coś
        # plt.plot(os_x, record) 
        # plotuje zfiltrowane EKG
        # plt.plot(os_x, smoothed_signal, color='blue')
        plt.title(f"ECG {nazwa_pliku}")
        if if_time:
            # xlabel dla czasu
            plt.xlabel('Seconds')
        else:
            # xlabel dla sampli
            plt.xlabel('Sample')
        plt.ylabel('Amplitude')

        # Dodaj zaznaczenia annotacji

        if if_time == False:
            # annotacje dla osi sampli
            for sample, symbol in zip(annotacje.sample, annotacje.symbol):
                if sampfrom <= sample < sampto and sample < len(record_all):
                    # annotacje dla normalnego EKG
                    plt.text(sample, record_all[sample, 0], symbol, fontsize=10, color='red')
                    # annotacje dla zfiltrowanego EKG
                    # plt.text(sample, smoothed_signal[sample - sampfrom], symbol, fontsize=10, color='red')
        else:
            # annotacje dla osi czasu
            for sample, symbol in zip(annotacje.sample, annotacje.symbol):
                if czas_start <= sample / fs < czas_stop and sample < len(record_all):
                    plt.text(sample / fs, record_all[sample, 0], symbol, fontsize=10, color='red')

        plt.grid(True)
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return render_template('analiza.html', chart_data=chart_data, avg_hr=avg_hr, max_hr=max_hr, min_hr=min_hr,
                               total_ann=total_ann, count_N=count_N, count_A=count_A, count_slash=count_slash,
                               count_V=count_V, count_L=count_L, count_R=count_R, avg_hr_all=avg_hr_all,
                               max_hr_all=max_hr_all, min_hr_all=min_hr_all, total_ann_all=total_ann_all,
                               count_N_all=count_N_all, count_A_all=count_A_all, count_slash_all=count_slash_all,
                               count_V_all=count_V_all, count_L_all=count_L_all, count_R_all=count_R_all, czas_s=czas_s,
                               czas_m=czas_m, czas_h=czas_h, time_s=time_s, time_m=time_m, time_h=time_h,
                               count_qrs_all=count_qrs_all, count_qrs=count_qrs, sdnn=sdnn, sdnn_all=sdnn_all,
                               rmssd=rmssd, rmssd_all=rmssd_all, pnn50=pnn50, pnn50_all=pnn50_all, content=user)
    else:
        return redirect(url_for('login'))


@app.route('/download_pdf')
def download_pdf():
    global imie_p, nazwisko_p, data_urodzenia_p, lekarz_in
    imie_p = "Jerzy"
    nazwisko_p = "Żuk"
    lekarz_in = "Henryk Karmin"
    data_urodzenia_p = datetime(2000, 2, 28)

    avg_hr_all = session.get("pdf_mean_hr_all", 0)
    max_hr_all = session.get("pdf_max_hr_all", 0)
    min_hr_all = session.get("pdf_min_hr_all", 0)
    total_ann_all = session.get("pdf_total_ann_all", 0)
    count_N_all = session.get("pdf_count_N_all", 0)
    count_A_all = session.get("pdf_count_A_all", 0)
    count_slash_all = session.get("pdf_count_slash_all", 0)
    count_V_all = session.get("pdf_count_V_all", 0)
    count_L_all = session.get("pdf_count_L_all", 0)
    start_date = session.get("start_date", 0)
    end_date = session.get("end_date", 0)
    pdf_SDNN = session.get("pdf_sdnn_all", 0)
    pdf_RMSDD = session.get("pdf_rmssd_all", 0)
    pdf_PNN = session.get("pdf_pnn50_all", 0)
    pdf_time = session.get("pdf_time", 0)
    plik_pdf = generuj_pdf(start_date, end_date, avg_hr_all, max_hr_all, min_hr_all, total_ann_all, count_N_all,
                           count_A_all, count_slash_all,
                           count_V_all, count_L_all, pdf_SDNN, pdf_RMSDD, pdf_PNN, pdf_time)
    return send_file(plik_pdf, as_attachment=True, download_name='Raport_EKG.pdf')


def generuj_pdf(start_date, end_date, pdf_mean_hr_all, pdf_max_hr_all, pdf_min_hr_all, pdf_total_ann_all,
                pdf_count_N_all,
                pdf_count_A_all, pdf_count_slash_all, pdf_count_V_all, pdf_count_L_all, pdf_SDNN, pdf_RMSDD, pdf_PNN,
                pdf_time):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))

    # Tytul
    dzisiejsza_data = datetime.now().strftime("%Y-%m-%d")
    p.drawString(380, 780, f"Data wystawienia raportu: {dzisiejsza_data}")
    x = 60
    y = 700
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(300, 760, "Raport z badania EKG")
    p.line(10, 750, 585, 750)
    # Dane pacjenta:
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(300, 720, "Dane pacjenta")
    p.setFont("Verdana", 12)
    p.drawString(x, y, f"Imię: {imie_p}")
    y -= 20
    p.drawString(x, y, f"Nazwisko: {nazwisko_p}")
    y -= 20
    wiek_pacjenta = datetime.now().year - data_urodzenia_p.year
    if (datetime.now().month, datetime.now().day) < (data_urodzenia_p.month, data_urodzenia_p.day):
        wiek_pacjenta -= 1
    p.drawString(x, y, f"Wiek pacjenta: {wiek_pacjenta}")
    y -= 20
    p.drawString(x, y, f"Lekarz: {lekarz_in}")
    y -= 20
    p.drawString(x, y, f"Przedzial czasowy wykonywanego badania: {start_date} - {end_date}")
    y -= 30

    # Cechy charakterystyczne badania
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(300, y, "Parametry EKG")
    y -= 20
    p.setFont("Verdana", 12)
    p.drawString(x + 20, y, f"*Sredni HR: {pdf_mean_hr_all:.2f}")
    y -= 20
    p.drawString(x + 20, y, f"*Maksymalny HR: {pdf_max_hr_all:.2f}")
    y -= 20
    p.drawString(x + 20, y, f"*Minimalny HR: {pdf_min_hr_all:.2f}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji: {pdf_total_ann_all}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji N: {pdf_count_N_all}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji A: {pdf_count_A_all}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji /: {pdf_count_slash_all}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji V: {pdf_count_V_all}")
    y -= 20
    p.drawString(x + 20, y, f"*Suma anotacji L: {pdf_count_L_all}")
    y -= 20
    p.drawString(x + 20, y, f"*SDNN: {pdf_SDNN}")
    y -= 20
    p.drawString(x + 20, y, f"*RMSSD: {pdf_RMSDD}")
    y -= 20
    p.drawString(x + 20, y, f"*PNN50: {pdf_PNN}")
    y -= 30

    # Wnioski
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(300, y, "Wnioski")
    y -= 20
    p.setFont("Verdana", 12)
    wnioski_txt = f"Całkowity czas badania wynosi {pdf_time} minut. Przy czym średni HR wynosił {pdf_mean_hr_all:.2f}."
    p.drawString(x - 40, y, wnioski_txt)
    y -= 20
    p.drawString(400, 20, "Podpis:")


    p.showPage()
    # Ewentualne wykresy
    # p.drawImage("test.png", 300, 300, width=200, height=200)
    p.save()

    buffer.seek(0)
    return buffer

if __name__ == '__main__':
    app.run(port=5000,threaded=False)
