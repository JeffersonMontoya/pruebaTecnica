from flask import Flask, render_template, request, redirect, url_for, send_file, session
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta'


UPLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
archivo_guardado = None  

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    global archivo_guardado
    if request.method == 'POST':
        if 'file' not in request.files and 'file2' not in request.files:
            return render_template('index.html', error="No se han seleccionado archivos.")
        
        file1 = request.files.get('file')
        file2 = request.files.get('file2')
        
   
        if not file1 or not file2:
            return render_template('index.html', error="Se requieren ambos archivos.")
        
       
        filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], file1.filename)
        filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], file2.filename)
        file1.save(filepath1)
        file2.save(filepath2)
        
        
        df_simm = pd.read_excel(filepath1)  
        df_seguimiento = pd.read_excel(filepath2)  
        
      
        if len(df_simm) > 4:
            df_simm_cleaned = df_simm.iloc[4:].reset_index(drop=True)
        else:
            return render_template('index.html', error="Archivo SIMM insuficiente.")
        
        
        column_names_simm = [
            'Correo Electronico', 'N° Orden de trabajo', 'REQ', 'Estado', 'Fecha de creación',
            'Fecha Programada Inicio', 'Fecha Ult Modificación', 'Fecha de Cierre',
            'Categorización N1', 'Categorización N2', 'Categorización N3', 'Detalle descripción', 'Resolución'
        ]
        

        expected_columns = len(column_names_simm)
        actual_columns = df_simm_cleaned.shape[1]
        if actual_columns > expected_columns:
            df_simm_cleaned = df_simm_cleaned.iloc[:, :expected_columns]
        elif actual_columns < expected_columns:
           
            for i in range(actual_columns, expected_columns):
                df_simm_cleaned[f"Column_{i}"] = ""
        
        df_simm_cleaned.columns = column_names_simm
        

        df_simm_cleaned = df_simm_cleaned.drop(['Fecha Programada Inicio', 'Fecha de Cierre'], axis=1)
        df_simm_cleaned.rename(columns={'Resolución': 'Observación'}, inplace=True)
        
  
        df_simm_cleaned['Entrega Plan de Trabajo'] = ''
        df_simm_cleaned['Pruebas con SIMM'] = ''
        df_simm_cleaned['Posible Salida a Producción'] = ''
        df_simm_cleaned['Firma SIMM'] = ''
        
        solicitantes = [" ", "SIMM", "ESI", "SMM"]
        df_simm_cleaned['Solicitante'] = solicitantes[0]
        
     
        df_combined = df_simm_cleaned.copy()
        
      
        required_columns = [
            'Solicitante', 'WO', 'REQ', 'Fecha de creación', 'Fecha Ultima Nota',
            'Descripción', 'Detalle Ultima Nota', 'Aplicación', 'Tipo', 'Observaciones UT'
        ]
        
       
        df_combined.rename(columns={'N° Orden de trabajo': 'WO'}, inplace=True)
        
       
        for col in required_columns:
            if col not in df_combined.columns:
                df_combined[col] = ''
        
        
        if 'WO' in df_seguimiento.columns:
            for index, row in df_combined.iterrows():
                wo = row['WO']
                
                matching_rows = df_seguimiento[df_seguimiento['WO'] == wo]
                if not matching_rows.empty:
                    match = matching_rows.iloc[0]
                    for col in required_columns:
                        if col in match and col in df_combined:
                            df_combined.at[index, col] = match.get(col, '')
        
    
        cols = ['Solicitante'] + [col for col in df_combined.columns if col != 'Solicitante']
        df_combined = df_combined[cols]
        
      
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
        
        df_combined['Fecha Ult Modificación'] = pd.to_datetime(df_combined['Fecha Ult Modificación'], errors='coerce')
        df_combined['Semaforo'] = df_combined['Fecha Ult Modificación'].apply(semaforo_colores)
        
     
        data = df_combined.to_dict(orient='records')
        session['datos'] = data
        
      
        archivo_guardado = os.path.join(app.config['UPLOAD_FOLDER'], 'resultado_procesado.xlsx')
        df_combined.to_excel(archivo_guardado, index=False)
        
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