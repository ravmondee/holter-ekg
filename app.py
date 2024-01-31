from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from io import BytesIO
import wfdb
from wfdb import processing
# import aspose.pdf as ap
import matplotlib.pyplot as plt
import base64
import numpy

app = Flask(__name__, static_url_path='/static', static_folder='static')

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
        f.write(f"Liczba annotacji N: {char_symbol.count('N')}\n")
        f.write(f"Liczba annotacji A: {char_symbol.count('A')}\n")
        f.write(f"Maksymalny heart rate: {max(float_hr):.2f}\n")
        f.write(f"Minimalny heart rate: {min(float_hr):.2f}\n")
        for i, (symbol, sample, hr) in enumerate(zip(annotacje.symbol, annotacje.sample, float_hr), start=1):
            czas = sample / annotacje.fs
            f.write(
                f"sample nr: {sample}. Kod annotacji: {symbol}, Czas annotacji: {czas:.2f} sekundy, Heart rate: {hr:.2f}\n")

    f.close()

    # Plot signal
    plt.figure(figsize=(10, 4))
    plt.plot(record[:, 1], label='Channel 1')
    # plt.plot(ann_samp=[qrs_inds], label='Channel 1')
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


# @app.route('/download_pdf')
# def download_pdf():
#     options = ap.HtmlLoadOptions()
#     document = ap.Document("analiza.html", options)
#     document.save("test.pdf")

if __name__ == '__main__':
    app.run()
