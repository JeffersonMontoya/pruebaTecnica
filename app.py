from flask import Flask, render_template, request, redirect, url_for, send_file, session
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Configuración para subir archivos
UPLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
archivo_guardado = None  # Variable global para la ruta del último archivo procesado

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    global archivo_guardado
    if request.method == 'POST':
        file = request.files['file']
        if file:
            # Guardar archivo subido en la carpeta de Descargas
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            archivo_guardado = filepath

            df = pd.read_excel(filepath)
            if len(df) > 4:
                df_cleaned = df.iloc[4:].reset_index(drop=True)
            else:
                return render_template('index.html', error="Archivo insuficiente.")

            # Limitar a 13 columnas
            expected_columns = 13
            if df_cleaned.shape[1] > expected_columns:
                df_cleaned = df_cleaned.iloc[:, :expected_columns]

            # Renombrar columnas
            df_cleaned.columns = [
                'Correo Electronico', 'N° Orden de trabajo', 'REQ', 'Estado', 'Fecha de creación',
                'Fecha Programada Inicio', 'Fecha Ult Modificación', 'Fecha de Cierre',
                'Categorización N1', 'Categorización N2', 'Categorización N3', 'Detalle descripción', 'Resolución'
            ]

            df_cleaned = df_cleaned.drop(['Fecha Programada Inicio', 'Fecha de Cierre'], axis=1)
            df_cleaned.rename(columns={'Resolución': 'Observación'}, inplace=True)

            # Agregar nuevas columnas
            df_cleaned['Entrega Plan de Trabajo'] = ''
            df_cleaned['Pruebas con SIMM'] = ''
            df_cleaned['Posible Salida a Producción'] = ''
            df_cleaned['Firma SIMM'] = ''

            solicitantes = [" ", "SIMM", "ESI", "SMM"]
            df_cleaned['Solicitante'] = solicitantes[0]
            cols = ['Solicitante'] + [col for col in df_cleaned.columns if col != 'Solicitante']
            df_cleaned = df_cleaned[cols]

            # Lógica de colores de semáforo
            def semaforo_colores(fecha):
                hoy = datetime.now()
                if pd.isnull(fecha):
                    return "sin fecha"
                diferencia = (hoy - fecha).days
                if diferencia <= 30:
                    return "verde"
                elif 30 < diferencia <= 60:
                    return "naranja"
                else:
                    return "rojo"

            df_cleaned['Fecha Ult Modificación'] = pd.to_datetime(df_cleaned['Fecha Ult Modificación'], errors='coerce')
            df_cleaned['Semaforo'] = df_cleaned['Fecha Ult Modificación'].apply(semaforo_colores)

            # Guardar datos en sesión
            data = df_cleaned.to_dict(orient='records')
            session['datos'] = data

            # Guardar archivo limpio
            archivo_guardado = os.path.join(app.config['UPLOAD_FOLDER'], 'resultado_procesado.xlsx')
            df_cleaned.to_excel(archivo_guardado, index=False)

            return render_template('resultado.html', datos=data, solicitantes=solicitantes)

    return render_template('index.html')

@app.route('/descargar', methods=['GET'])
def descargar():
    global archivo_guardado
    if archivo_guardado and os.path.exists(archivo_guardado):
        return send_file(archivo_guardado, as_attachment=True, download_name='resultado_procesado.xlsx')
    else:
        return "No hay archivo disponible para descargar."

@app.route('/regresar', methods=['GET'])
def regresar():
    return redirect(url_for('upload_file'))

if __name__ == '__main__':
    app.run(debug=True)
