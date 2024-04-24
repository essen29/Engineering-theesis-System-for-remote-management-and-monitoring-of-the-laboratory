from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for, g, flash, Response
from flask_wtf import FlaskForm
from flask_socketio import SocketIO
from datetime import datetime, timedelta
import sqlite3, cv2, csv, io


app = Flask(__name__)

camera = cv2.VideoCapture(0)

app.config['SECRET_KEY'] = "secretkey"

database = 'database.db'

godziny = ["6:00", "7:00", "8:00", "9:00", "10:00", "11:00","12:00", "13:00", "14:00", "15:00", "16:00", "17:00","18:00", "19:00", "20:00"]

@app.route('/')
def home():
    if not g.user_id:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Konto WHERE id = ?', (g.user_id,))
    user = cursor.fetchone()

    return render_template('home.html', imie = user[3], nazwisko=user[4])

@app.before_request
def before_request():
    g.user_id = None
    if 'user_id' in session:
        g.user_id = session['user_id']

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.pop('user_id', None)

        login = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM Konto WHERE login = ? AND haslo = ?', (login, password))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            return redirect(url_for('login'))
        else:
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/<string:budynek>/<int:pietro>', methods=['GET', 'POST'])
def floor(budynek, pietro):
    if not g.user_id:
        flash(f'Nie jesteś zalogowany!', 'danger')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()


    if request.method == 'POST':
        date_value = request.form['datepicker']
        time_value = request.form['timepicker']
        datetime_value = datetime.strptime(date_value + ' ' + time_value, '%Y-%m-%d %H:%M')
    else:
        date_value = datetime.now().date()
        current_time = datetime.now().hour - 6 #6 ponieważ odejmujemy 6 godzin ponieważ godzina 6:00 jest na pozycji 0

        if current_time >= 0 or current_time < 15:
            current_time = current_time
        else:
            current_time = 0
        try:
            time_value = godziny[current_time]
        except:
            date_value = date_value + timedelta(days=1)
            time_value = godziny[0]

        datetime_value = datetime.now()
        datetime_value = datetime_value.replace(microsecond=0)


    #Sprawdzenie które sale z danego piętra są aktualnie zajęte
    zajete_sale = []

    cursor.execute('SELECT * FROM Sale AS S JOIN Budynki AS B ON S.id_budynek = B.id WHERE B.nazwa = ? AND pietro = ?', (budynek, pietro))
    sale_z_pietra = cursor.fetchall()

    for sala in sale_z_pietra:
        cursor.execute('SELECT * FROM Rezerwacje WHERE od <= ? AND do > ? AND id_sala = ?', (datetime_value,datetime_value,sala[0]))
        result = cursor.fetchone()
        if result is not None:
            zajete_sale.append(sala[0])

    conn.close()
    return render_template('floor.html', date_value=date_value, time_value=time_value, zajete_sale=zajete_sale, godziny=godziny, budynek=budynek, pietro=pietro)

@app.route('/<int:id>/<string:data>/<string:czas>', methods=['GET', 'POST'])
def sala(id,data,czas):
    if not g.user_id:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('SELECT typ FROM Sale WHERE id = ?', (id,))
    typ_sali = cursor.fetchone()
    

    #sprawienie ze jezeli aktualnia godzina jest poza 6-20 to automatycznie w formularzu jest 6:00 nastepnego dnia
    if request.method == 'GET':
        data = datetime.strptime(data, '%Y-%m-%d')
        czas = datetime.strptime(czas, '%H:%M')

        if czas.hour < 6 or czas.hour > 19:
            czas = datetime.strptime('06:00', '%H:%M')
            data = data + timedelta(days=1)
        else:
            czas = czas + timedelta(hours=1)
        
        czas = czas.strftime('%H:%M')
        data = data.strftime('%Y-%m-%d')

    cursor.execute('''SELECT R.od, R.do, K.imie, K.nazwisko, K.id, R.id, R.typ FROM Rezerwacje AS R 
                   JOIN Konto AS K ON R.id_konto = K.id 
                   WHERE R.id_sala = ? AND R.do > ?''', 
                   (id, datetime.now()))
    results = cursor.fetchall()

    cursor.execute('SELECT numer_sali FROM Sale WHERE id = ?', (id,))
    numer_sali = cursor.fetchone()

    cursor.execute('SELECT R.id_konto, R.id_stanowiska, R.od, R.do, K.imie, K.nazwisko FROM RezerwacjeStanowiska AS R JOIN Konto AS K ON R.id_konto = K.id WHERE do > ?', (datetime.now(),))
    results65 = cursor.fetchall()
    print(results65)


    results = sorted(results, key=lambda x: x[0])
    results65 = sorted(results65, key=lambda x: x[0])
    #print(results)

    for rekord1 in results:
        for rekord2 in results:
            if rekord1[1] == rekord2[0] and rekord1 != rekord2 and rekord1[4] == rekord2[4] and rekord1[6] == rekord2[6]:
                print("Połączono rezerwacje")
                cursor.execute('DELETE FROM Rezerwacje WHERE id = ?', (rekord2[5],))
                cursor.execute('UPDATE Rezerwacje SET do = ? WHERE id = ?', (rekord2[1], rekord1[5]))
                conn.commit()
                cursor.execute('''SELECT R.od, R.do, K.imie, K.nazwisko, K.id, R.id, R.typ 
                               FROM Rezerwacje AS R 
                               JOIN Konto AS K ON R.id_konto = K.id 
                               WHERE R.id_sala = ? AND R.do > ?''', 
                               (id, datetime.now()))
                results = cursor.fetchall()


    results = sorted(results, key=lambda x: x[0])


    if request.method == 'POST':
        data_od = request.form['data_od']
        data_do = request.form['data_do']
        czas_od = request.form['czas_od']
        czas_do = request.form['czas_do']


        typ = request.form['powod']
        datetime_od = datetime.strptime(data_od + ' ' + czas_od, '%Y-%m-%d %H:%M')
        datetime_do = datetime.strptime(data_do + ' ' + czas_do, '%Y-%m-%d %H:%M')
        
        if datetime_od < datetime.now():
            flash(f'Rezerwacja nie może być w przeszłości!', 'danger')
            conn.close()
            return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
        
        if(datetime_od == datetime_do):
            flash(f'Rezerwacja musi trwać przynajmniej 1 godzinę!', 'danger')
            conn.close()
            return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))

        if datetime_od > datetime_do:
            print("aktywowano")
            flash(f'Data "od" nie może być późniejsza niż data "do"!', 'danger')
            conn.close()
            return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
        
        
        if id == 65:
            stan_1 = request.form.get('option1')
            stan_2 = request.form.get('option2')

            if stan_1 and stan_2:
                flash(f'Zarezerwowano oba stanowiska!', 'success')
                cursor.execute('INSERT INTO RezerwacjeStanowiska (id_konto, id_stanowiska, od, do) VALUES (?, ?, ?, ?)', (g.user_id, 1, datetime_od, datetime_do))
                cursor.execute('INSERT INTO RezerwacjeStanowiska (id_konto, id_stanowiska, od, do) VALUES (?, ?, ?, ?)', (g.user_id, 2, datetime_od, datetime_do))
                conn.commit()
                conn.close()
                return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
            elif stan_1 and stan_2 is None:
                flash(f'Zarezerwowano stanowisko 1!', 'success')
                cursor.execute('INSERT INTO RezerwacjeStanowiska (id_konto, id_stanowiska, od, do) VALUES (?, ?, ?, ?)', (g.user_id, 1, datetime_od, datetime_do))
                conn.commit()
                conn.close()
                return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
            elif stan_1 is None and stan_2:
                flash(f'Zarezerwowano stanowisko 2!', 'success')
                cursor.execute('INSERT INTO RezerwacjeStanowiska (id_konto, id_stanowiska, od, do) VALUES (?, ?, ?, ?)', (g.user_id, 2, datetime_od, datetime_do))
                conn.commit()
                conn.close()
                return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
            else:
                flash(f'Nie zaznaczono żadnego stanowiska!', 'danger')
                conn.close()
                return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))

        if results is not None:
            for result in results:
                od = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                do = datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S')
                if (datetime_od >= od and datetime_od < do) or (datetime_do > od and datetime_do <= do) or (datetime_od <= od and datetime_do >= do):
                    cursor.execute('SELECT * FROM Rezerwacje WHERE id_sala = ? AND (do > ? OR od < ?)', (id, datetime_do, datetime_do))
                    wyniki = cursor.fetchall()

                    wyniki = sorted(wyniki, key=lambda x: x[3])
                    #print(wyniki)

                    tmp_od = datetime.now()
                    tmp_od = tmp_od.replace(minute=0, second=0, microsecond=0)
                    tmp_od = tmp_od + timedelta(hours=1)
                    tmp_od = tmp_od.strftime("%Y-%m-%d %H:%M:%S")

                    wolne_godziny = []

                    #wynik[3] = od wynik[4] = do
                    for wynik in wyniki:
                        if tmp_od >= wynik[3] and tmp_od < wynik[4]:
                            tmp_od = wynik[4]
                        
                        if tmp_od < wynik[3]:
                            wolne_godziny.append([tmp_od, wynik[3]])
                            tmp_od = wynik[4]

                    #dodanie ostatniego przedziału czasowego
                    wolne_godziny.append([results[-1][1], "∞"])

                    wolne_godziny.sort(key=lambda date: abs(datetime.strptime(date[0], '%Y-%m-%d %H:%M:%S') - datetime_od))    
                    print("\n")
                    
                    flash(f'Sala jest już zajęta w tym terminie przez <strong>{result[2]} {result[3]}</strong>!', 'danger')

                    wolne_godziny = wolne_godziny[:3]

                    napis = "Najbliższe wolne godziny dla tej sali:<br>"
                    for i in wolne_godziny:
                        napis = napis + f'{i[0]} - {i[1]}<br>'
                    
                    flash(napis, 'info')

                    conn.close()
                    return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))


        cursor.execute('INSERT INTO Rezerwacje (id_sala, id_konto, od, do, typ) VALUES (?, ?, ?, ?, ?)', 
                       (id, g.user_id, datetime_od, datetime_do, typ))
        conn.commit()
        conn.close()
        flash(f'Rezerwacja została dodana!', 'success')
        return redirect(url_for('sala', id=id, numer_sali = numer_sali[0], data=data, czas=czas))
    
    return render_template('sale.html', id=id, numer_sali = numer_sali[0], data=data, czas=czas, results=results, id_user=g.user_id, godziny=godziny, aktualna_data=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), typ_sali=typ_sali[0],results65=results65)

@app.route('/rezerwacje', methods=['GET', 'POST'])
def rezerwacje():
    if not g.user_id:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('''SELECT R.id, R.id_sala, R.od, R.do, B.nazwa, S.pietro, S.numer_sali, R.typ 
                   FROM Rezerwacje AS R 
                   JOIN Sale AS S ON R.id_sala = S.id 
                   JOIN Budynki AS B ON S.id_budynek = B.id
                   WHERE (R.id_konto = ? AND R.do > ?)''', (g.user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    results = cursor.fetchall()
    conn.close()
    results = sorted(results, key=lambda x: x[2])

    return render_template('rezerwacje.html', results=results)

@app.route('/usun_rekord/<int:id>', methods=['GET', 'POST'])
def usun_rekord(id):
    if not g.user_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Rezerwacje WHERE id = ? AND id_konto = ?', (id, g.user_id))
        result = cursor.fetchone()
        if result is None:
            conn.close()
            flash(f'Nie udało się usunąć rezerwacji!', 'danger')
            return redirect(url_for('rezerwacje'))
        else:
            cursor.execute('DELETE FROM Rezerwacje WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            flash(f'Rezerwacja została usunięta!', 'success')
            return redirect(url_for('rezerwacje'))

    flash(f'Nie udało się usunąć rezerwacji!', 'danger')
    return redirect(url_for('rezerwacje'))

@app.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    if not g.user_id:
        return redirect(url_for('login'))
    
    return render_template('import_csv.html')

@app.route('/upload', methods=['POST'])
def upload():
    if not g.user_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['csv_file']

        if file.filename[-4:] != '.csv':
            flash(f'Plik nie jest w formacie .csv!', 'danger')
            return redirect(url_for('import_csv'))
        
        csv_rezerwacje = []

        with io.TextIOWrapper(file, encoding="utf-8") as text_file:
            reader = csv.reader(text_file, delimiter=';')                
            for row in reader:
                csv_rezerwacje.append(row)

        csv_rezerwacje = csv_rezerwacje[1:]

        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        for rezerwacja in csv_rezerwacje:
            cursor.execute('SELECT id FROM Sale WHERE numer_sali = ?', (rezerwacja[11],))
            id_sala = cursor.fetchone()
            
            if id_sala is None:
                continue
            
            od = datetime.strptime(rezerwacja[7] + " " + rezerwacja[8] + ":00", "%Y-%m-%d %H:%M:%S")
            do = datetime.strptime(rezerwacja[7] + " " + rezerwacja[9] + ":00", "%Y-%m-%d %H:%M:%S")

            if od >= datetime.now():
                cursor.execute('INSERT INTO Rezerwacje (id_sala, id_konto, od, do, typ) VALUES (?, ?, ?, ?, ?)',
                                (id_sala[0], g.user_id, od, do, "Dydaktyczny"))
        
        conn.commit()
        conn.close()
        flash(f'Pomyślnie dodano rezerwacje!', 'success')
        print("sukces")

    return redirect(url_for('import_csv'))
    
    

#kamerki
@app.route('/podglad/<int:id>', methods=['GET', 'POST'])
def podglad(id):
    if not g.user_id:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('SELECT numer_sali FROM Sale WHERE id = ?', (id,))
    numer_sali = cursor.fetchone()
    conn.close()

    return render_template('podglad.html', id=id, numer_sali=numer_sali[0])

@app.route('/B5_1')
def get_B5_1pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/1.png', mimetype='image/jpg')

@app.route('/B5_2')
def get_B5_2pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/2.png', mimetype='image/jpg')

@app.route('/B5_3')
def get_B5_3pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/3.png', mimetype='image/jpg')

@app.route('/B5_4')
def get_B5_4pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/4.png', mimetype='image/jpg')

@app.route('/B5_5')
def get_B5_5pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/5.png', mimetype='image/jpg')

@app.route('/B5_6')
def get_B5_6pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/6.png', mimetype='image/jpg')

@app.route('/B5_7')
def get_B5_7pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/7.png', mimetype='image/jpg')

@app.route('/B5_8')
def get_B5_8pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/8.png', mimetype='image/jpg')

@app.route('/B5_9')
def get_B5_9pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B5/9.png', mimetype='image/jpg')

@app.route('/B4_0')
def get_B4_0pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B4/0.png', mimetype='image/jpg')

@app.route('/B4_1')
def get_B4_1pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B4/1.png', mimetype='image/jpg')

@app.route('/B4_2')
def get_B4_2pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B4/2.png', mimetype='image/jpg')

@app.route('/B4_3')
def get_B4_3pietro():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B4/3.png', mimetype='image/jpg')

@app.route('/B4_4')
def get_B4_parter():
    if not g.user_id:
        return redirect(url_for('login'))

    return send_file('Nieponumerowane sale/B4/-1.png', mimetype='image/jpg')



def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
