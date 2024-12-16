from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta'  # Cambia esto por una clave secreta segura

# Configuración de la conexión a la base de datos
db_config = {
    'host': '192.168.3.67',
    'user': 'pako',  # Usa el usuario que creaste
    'password': '1020',  # Usa la contraseña segura
    'database': 'Departamentos'
}

# Función para obtener una conexión a la base de datos
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        flash(f"Error al conectar a la base de datos: {err}", 'error')  # Muestra un mensaje de error al usuario
        return None

# Función para convertir números a letras
def num_a_letras(num):
    """Convierte un número a su representación en letras (solo para la parte entera)."""
    unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def _convertir_parte(n):
        if n == 0:
            return ""
        elif n <= 9:
            return unidades[n]
        elif n <= 99:
            decena = n // 10
            unidad = n % 10
            if n < 20:
                return ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"][unidad]
            else:
                return decenas[decena] + (" Y " if unidad > 0 else "") + unidades[unidad]
        else:
            centena = n // 100
            resto = n % 100
            return centenas[centena] + (" " if resto > 0 else "") + _convertir_parte(resto)

    if num == 0:
        return "CERO"

    resultado = ""
    if num >= 1000:
        miles = num // 1000
        resto = num % 1000
        resultado = _convertir_parte(miles) + " MIL" + (" " if resto > 0 else "")
        num = resto

    if num > 0:
        resultado += _convertir_parte(num)

    return resultado

# Ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')  # Ahora renderizamos una plantilla HTML

# Ruta para mostrar el formulario de agregar departamento
@app.route('/agregar_departamento', methods=['GET'])
def mostrar_formulario_agregar_departamento():
    return render_template('agregar_departamento.html')

# Ruta para procesar el formulario de agregar departamento
@app.route('/agregar_departamento', methods=['POST'])
def agregar_departamento():
    numero = request.form['numero']
    renta = request.form['renta']
    dia_pago = request.form['dia_pago']
    observaciones = request.form['observaciones']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO departamentos (numero, renta, dia_pago, observaciones) VALUES (%s, %s, %s, %s)",
                   (numero, renta, dia_pago, observaciones))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('lista_departamentos'))  # Redirige a la lista de departamentos

# Ruta para mostrar el formulario de agregar inquilino
@app.route('/agregar_inquilino', methods=['GET'])
def mostrar_formulario_agregar_inquilino():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, numero FROM departamentos")
    departamentos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('agregar_inquilino.html', departamentos=departamentos)

# Ruta para procesar el formulario de agregar inquilino
@app.route('/agregar_inquilino', methods=['POST'])
def agregar_inquilino():
    departamento_id = request.form['departamento_id']
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    fecha_inicio = request.form['fecha_inicio']
    fecha_fin = request.form['fecha_fin']
    telefono = request.form['telefono']
    fiador_nombre = request.form['fiador_nombre']
    fiador_apellidos = request.form['fiador_apellidos']
    fiador_telefono = request.form['fiador_telefono']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inquilinos (departamento_id, nombre, apellidos, fecha_inicio, fecha_fin, telefono, fiador_nombre, fiador_apellidos, fiador_telefono) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (departamento_id, nombre, apellidos, fecha_inicio, fecha_fin, telefono, fiador_nombre, fiador_apellidos, fiador_telefono))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('lista_inquilinos'))  # Redirige a la lista de inquilinos

# Ruta para listar los departamentos
@app.route('/departamentos')
def lista_departamentos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departamentos")
    departamentos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('lista_departamentos.html', departamentos=departamentos)

# Ruta para listar los inquilinos
@app.route('/inquilinos')
def lista_inquilinos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT i.*, d.numero AS numero_departamento FROM inquilinos i LEFT JOIN departamentos d ON i.departamento_id = d.id")
    inquilinos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('lista_inquilinos.html', inquilinos=inquilinos)

# Ruta para mostrar la página de departamentos y contratos
@app.route('/departamentos_contratos')
def departamentos_contratos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departamentos")
    departamentos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('lista_departamentos_contratos.html', departamentos=departamentos)

# Ruta para mostrar el contrato completo en una página separada
@app.route('/contrato_completo/<int:departamento_id>')
def mostrar_contrato_completo(departamento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener el inquilino actual del departamento
    cursor.execute("SELECT id FROM inquilinos WHERE departamento_id = %s ORDER BY fecha_inicio DESC LIMIT 1", (departamento_id,))
    inquilino = cursor.fetchone()

    if inquilino:
        # Obtener datos del inquilino y departamento
        inquilino = obtener_inquilino_por_id(inquilino['id'])
        departamento = obtener_departamento_por_id(departamento_id)

        if not inquilino or not departamento:
            cursor.close()
            conn.close()
            return "<p>Error: No se encontró el inquilino o el departamento.</p>"

        # Convertir la renta a un entero antes de pasarla a num_a_letras
        renta_en_letras = num_a_letras(int(departamento['renta']))

        # Renderizar la plantilla del contrato completo
        return render_template('contrato_completo.html', inquilino=inquilino, departamento=departamento, renta_en_letras=renta_en_letras, fecha_actual=datetime.date.today().strftime('%d/%m/%Y'), fecha_inicio=inquilino['fecha_inicio'].strftime('%d/%m/%Y'), fecha_fin=inquilino['fecha_fin'].strftime('%d/%m/%Y'))
    else:
        cursor.close()
        conn.close()
        return "<p>No hay inquilino actual para este departamento.</p>"

# Función para obtener datos del inquilino por ID
def obtener_inquilino_por_id(inquilino_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inquilinos WHERE id = %s", (inquilino_id,))
    inquilino = cursor.fetchone()
    cursor.close()
    conn.close()
    return inquilino

# Función para obtener datos del departamento por ID
def obtener_departamento_por_id(departamento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departamentos WHERE id = %s", (departamento_id,))
    departamento = cursor.fetchone()
    cursor.close()
    conn.close()
    return departamento

# Ruta para editar un departamento
@app.route('/editar_departamento/<int:departamento_id>', methods=['GET', 'POST'])
def editar_departamento(departamento_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        # Obtener los datos del departamento a editar
        cursor.execute("SELECT * FROM departamentos WHERE id = %s", (departamento_id,))
        departamento = cursor.fetchone()
        cursor.close()
        conn.close()

        if departamento:
            return render_template('editar_departamento.html', departamento=departamento)
        else:
            flash('Departamento no encontrado', 'error')
            return redirect(url_for('lista_departamentos'))

    elif request.method == 'POST':
        # Actualizar los datos del departamento
        numero = request.form['numero']
        renta = request.form['renta']
        dia_pago = request.form['dia_pago']
        observaciones = request.form['observaciones']

        cursor.execute("UPDATE departamentos SET numero = %s, renta = %s, dia_pago = %s, observaciones = %s WHERE id = %s",
                       (numero, renta, dia_pago, observaciones, departamento_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Departamento actualizado correctamente', 'success')
        return redirect(url_for('lista_departamentos'))

# Ruta para borrar un departamento
@app.route('/borrar_departamento/<int:departamento_id>')
def borrar_departamento(departamento_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM departamentos WHERE id = %s", (departamento_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Departamento borrado correctamente', 'success')
    return redirect(url_for('lista_departamentos'))

# Ruta para editar un inquilino
@app.route('/editar_inquilino/<int:inquilino_id>', methods=['GET', 'POST'])
def editar_inquilino(inquilino_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        # Obtener los datos del inquilino a editar
        cursor.execute("SELECT * FROM inquilinos WHERE id = %s", (inquilino_id,))
        inquilino = cursor.fetchone()

        # Obtener la lista de departamentos para el select
        cursor.execute("SELECT id, numero FROM departamentos")
        departamentos = cursor.fetchall()

        cursor.close()
        conn.close()

        if inquilino:
            return render_template('editar_inquilino.html', inquilino=inquilino, departamentos=departamentos)
        else:
            flash('Inquilino no encontrado', 'error')
            return redirect(url_for('lista_inquilinos'))

    elif request.method == 'POST':
        # Actualizar los datos del inquilino
        departamento_id = request.form['departamento_id']
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']
        telefono = request.form['telefono']
        fiador_nombre = request.form['fiador_nombre']
        fiador_apellidos = request.form['fiador_apellidos']
        fiador_telefono = request.form['fiador_telefono']

        cursor.execute("UPDATE inquilinos SET departamento_id = %s, nombre = %s, apellidos = %s, fecha_inicio = %s, fecha_fin = %s, telefono = %s, fiador_nombre = %s, fiador_apellidos = %s, fiador_telefono = %s WHERE id = %s",
                       (departamento_id, nombre, apellidos, fecha_inicio, fecha_fin, telefono, fiador_nombre, fiador_apellidos, fiador_telefono, inquilino_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Inquilino actualizado correctamente', 'success')
        return redirect(url_for('lista_inquilinos'))

# Ruta para borrar un inquilino
@app.route('/borrar_inquilino/<int:inquilino_id>')
def borrar_inquilino(inquilino_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inquilinos WHERE id = %s", (inquilino_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Inquilino borrado correctamente', 'success')
    return redirect(url_for('lista_inquilinos'))

if __name__ == '__main__':
    app.run(host='192.168.3.100', port=5000)
