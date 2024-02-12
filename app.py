from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from io import BytesIO
import wfdb
from sqlalchemy import PickleType
from wfdb import processing
import matplotlib.pyplot as plt
import base64
import numpy
from scipy.signal import savgol_filter
<<<<<<< HEAD
import pyhrv.tools as tools
import pyhrv.time_domain as td
import pyhrv.frequency_domain as fd
import pyhrv.nonlinear as nl
=======
from flask_sqlalchemy import SQLAlchemy
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "klucz"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///measurements.db'
db = SQLAlchemy(app)


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


# defincja zmiennych globalnych
<<<<<<< HEAD
przesuniecie = 0
nazwa_pliku = '100'
<<<<<<< HEAD
record_all, fields = wfdb.rdsamp(nazwa_pliku, sampfrom=0)
fs=fields['fs']
sample=fields['sig_len']
time_s=round(sample/fs, 2)
time_m=round(time_s/60, 2)
time_h=round(time_m/60, 2)
qrs_inds_all = wfdb.processing.xqrs_detect(sig=record_all[:, 0], fs=fields['fs'])
count_qrs_all= len(qrs_inds_all)
rr_all = wfdb.processing.ann2rr(nazwa_pliku, 'atr', as_array=True)
# mean hr w samplach
=======

with app.app_context():
    plik = f"measurements/{get_measurement_file(nazwa_pliku)}"

record_all, fields = wfdb.rdsamp(plik, sampfrom=0)
qrs_inds_all = wfdb.processing.xqrs_detect(sig=record_all[:, 0], fs=fields['fs'])
rr_all = wfdb.processing.ann2rr(plik, 'atr', as_array=True)
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
mean_hr_all = wfdb.processing.calc_mean_hr(rr_all, fs, rr_units='samples')
# mean hr w sekundach
mean_hr_all_t = wfdb.processing.calc_mean_hr(rr_all, fs, rr_units='seconds')
heart_rate_all = wfdb.processing.compute_hr(len(record_all), qrs_inds_all, fs)
<<<<<<< HEAD
annotacje_all = wfdb.rdann(nazwa_pliku, 'atr', sampfrom=0, sampto=len(record_all))

rr_intervals = tools.nn_intervals(annotacje_all.sample)

# obliczenia HRV
s = td.sdnn(rr_intervals)
r = td.rmssd(rr_intervals)
p = td.nn50(rr_intervals)
sdnn_all = round(float(s[0]), 2)
rmssd_all = round(float(r[0]), 2)
pnn50_all = round(float(p[0]), 2)



=======
annotacje_all = wfdb.rdann(plik, 'atr', sampfrom=0, sampto=len(record_all))
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
=======

>>>>>>> 957fe701c884baaca452f5a7290973de277a4af6


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


@app.route('/analiza', methods=["GET", "POST"])
def analiza():
    if "user" in session:
        user = session["user"]

<<<<<<< HEAD
<<<<<<< HEAD
        global record_all, qrs_inds_all, rr_all, mean_hr_all, heart_rate_all, annotacje_all, przesuniecie, fs
        
=======
        global record_all, qrs_inds_all, rr_all, mean_hr_all, heart_rate_all, annotacje_all, przesuniecie
=======
        przesuniecie = 0
        fs = 360
        nazwa_pliku = 100
        plik = "measurements/100"

        with app.app_context():
            if request.method == 'POST':
                nazwa_pliku = request.form.get("nazwa_pliku")
                plik = f"measurements/{get_measurement_file(nazwa_pliku)}"



        record_all, fields = wfdb.rdsamp(plik, sampfrom=0)
        qrs_inds_all = wfdb.processing.xqrs_detect(sig=record_all[:, 0], fs=fields['fs'])
        rr_all = wfdb.processing.ann2rr(plik, 'atr', as_array=True)
        mean_hr_all = wfdb.processing.calc_mean_hr(rr_all, fs, rr_units='samples')
        heart_rate_all = wfdb.processing.compute_hr(len(record_all), qrs_inds_all, fs)
        annotacje_all = wfdb.rdann(plik, 'atr', sampfrom=0, sampto=len(record_all))
>>>>>>> 957fe701c884baaca452f5a7290973de277a4af6

>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
        # Reakcja na przyciski przesuniecia
        if 'przesuniecie' in request.args:
            przesuniecie += int(request.args['przesuniecie'])
        # ustalenie granic wykresu po kliknieciu
        sampfrom = przesuniecie
        sampto = przesuniecie + 3000

        # pobranie rekordów z pliku
<<<<<<< HEAD
        record, fields = wfdb.rdsamp(nazwa_pliku, sampfrom=sampfrom, sampto=sampto)
        
        # zamiana sampli na czas
        # jeszcze nie używamy czasu na razie pracujemy na samplach
        czas_start = round(sampfrom / fs, 2)
        czas_stop = round(sampto / fs, 2)
        czas_s = round(czas_stop-czas_start, 2) # w sekundach
        czas_m = round(czas_s/60, 2) # w minutach
        czas_h = round(czas_m/60, 2) # w godzinach
=======
        record, fields = wfdb.rdsamp(plik, sampfrom=sampfrom, sampto=sampto)

>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
        # zdefiniowanie osi x dla wykresu
        os_x = range(sampfrom, sampto)
        os_x_t = numpy.linspace(czas_start, czas_stop, len(record[:,0]))

        # obliczenia qrs, rr, heart rate oraz pobranie annotacji
<<<<<<< HEAD
        qrs_inds = wfdb.processing.xqrs_detect(sig=record[:, 0], fs=fs)
        count_qrs = len(qrs_inds)
        rr = wfdb.processing.ann2rr(nazwa_pliku, 'atr', as_array=True)
        # mean_hr w samplach
=======
        qrs_inds = wfdb.processing.xqrs_detect(sig=record[:, 0], fs=fields['fs'])
        rr = wfdb.processing.ann2rr(plik, 'atr', as_array=True)
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
        mean_hr = wfdb.processing.calc_mean_hr(rr, fs, rr_units='samples')
        heart_rate = wfdb.processing.compute_hr(len(record), qrs_inds, fs)
        annotacje = wfdb.rdann(plik, 'atr', sampfrom=sampfrom, sampto=sampto)

<<<<<<< HEAD
        rr_intervals = tools.nn_intervals(annotacje.sample)

        # filtrowanie EKG
        # smoothed_signal = savgol_filter(record[:, 0], window_length=51, polyorder=3)
        
        # wykres z zaznaczonymi qrs
        # fig=wfdb.plot_items(signal=record, ann_samp=[qrs_inds],return_fig=True)
        # fig=wfdb.plot_wfdb(record=record, annotation=annotacje,plot_sym=True,title='MIT-BIH Record 100',figsize=(20,6),return_fig=True)
        # fig.savefig("ann.png")
=======
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6

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
        float_mean_hr_all = float(mean_hr_all)
        float_hr = []
        float_hr_all = []

        for i in heart_rate:
            if numpy.isnan(i):
                float_hr.append(float_mean_hr)
            else:
                float_hr.append(float(i))
<<<<<<< HEAD
        
        
=======

>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
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

        # Średni HR, Max HR, Min HR
        avg_hr = f"{mean_hr:.2f}"

        avg_hr_all = f"{mean_hr:.2f}"

        max_hr = f"{max(float_hr):.2f}"
        min_hr = f"{min(float_hr):.2f}"

        max_hr_all = f"{max(float_hr_all):.2f}"
        min_hr_all = f"{min(float_hr_all):.2f}"

<<<<<<< HEAD
        # Plot signal
        # plt.figure(figsize=(20, 6))
        # plt.style.use('ggplot')
        # plt.plot(record[:, 1], label='Channel 1')
        # plt.title('MIT-BIH Record 100')
        # plt.xlabel('Time (samples)')
        # plt.ylabel('ECG Signal')
        if_time=True

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
        plt.title('ECG Signal')
        if if_time:
            # xlabel dla czasu
            plt.xlabel('Seconds')
        else:
            # xlabel dla sampli
            plt.xlabel('Sample')
        plt.ylabel('Amplitude')

        # Dodaj zaznaczenia annotacji

        if if_time==False:
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
                if czas_start <= sample/fs < czas_stop and sample < len(record_all):
                    plt.text(sample/fs, record_all[sample, 0], symbol, fontsize=10, color='red')

=======
        buf = BytesIO()
        plt.figure(figsize=(12, 6))
        plt.plot(os_x, record[:, 0])
        plt.title(f"ECG {nazwa_pliku}")
        plt.xlabel('Sample')
        plt.ylabel('Amplitude')

        # Dodaj zaznaczenia annotacji
        for sample, symbol in zip(annotacje.sample, annotacje.symbol):
            if sampfrom <= sample < sampto and sample < len(record_all):
                plt.text(sample, record_all[sample, 0], symbol, fontsize=10, color='red')
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6

        plt.grid(True)
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return render_template('analiza.html', chart_data=chart_data, avg_hr=avg_hr, max_hr=max_hr, min_hr=min_hr,
<<<<<<< HEAD
                               total_ann=total_ann, count_N=count_N, count_A=count_A, avg_hr_all=avg_hr_all, max_hr_all=max_hr_all, min_hr_all=min_hr_all,
                               total_ann_all=total_ann_all, count_N_all=count_N_all, count_A_all=count_A_all, czas_s=czas_s, czas_m=czas_m, czas_h=czas_h, time_s=time_s, time_m=time_m, time_h=time_h, count_qrs_all=count_qrs_all, count_qrs=count_qrs, sdnn=sdnn, sdnn_all=sdnn_all, rmssd=rmssd, rmsdd_all=rmssd_all, pnn50=pnn50, pnn50_all=pnn50_all, content=user)
=======
                               total_ann=total_ann, count_N=count_N, count_A=count_A, count_slash=count_slash, count_V=count_V,
                               count_L=count_L, avg_hr_all=avg_hr_all, max_hr_all=max_hr_all, min_hr_all=min_hr_all,
                               total_ann_all=total_ann_all, count_N_all=count_N_all, count_A_all=count_A_all, count_slash_all=count_slash_all,
                               count_V_all=count_V_all, count_L_all=count_L_all, content=user)
>>>>>>> 3b9185a3c1c1523e7efbb01d9890e59e0cb960e6
    else:
        return redirect(url_for('login'))


@app.route('/download_pdf')
def download_pdf():
    pass


if __name__ == '__main__':
    app.run(port=5000)
