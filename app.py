from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import datetime
import os
import bcrypt
import shutil
import mammoth
from docx import Document

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Configuración de la conexión a la base de datos
db_config = {
    'host': '192.168.3.67',
    'user': 'pako',
    'password': '1020',
    'database': 'Departamentos'
}

# Directorio para las plantillas de contratos
PLANTILLAS_DIR = os.path.join(app.root_path, 'plantillas_contratos')
# Directorio para las plantillas de usuario
PLANTILLAS_USUARIO_DIR = os.path.join(app.root_path, 'plantillas_usuario')

# Función para obtener una conexión a la base de datos
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        flash(f"Error al conectar a la base de datos: {err}", 'error')
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

# --- FUNCIONES PARA EL MANEJO DE USUARIOS ---

def get_user_by_username(username):
    """Obtiene un usuario por su nombre de usuario."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# --- RUTAS ---

# Ruta para la página principal
@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return render_template('index.html')  # Página principal para usuarios logueados
    else:
        return redirect(url_for('login'))  # Redirigir al login si no ha iniciado sesión

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')

# Ruta para el registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']

        # Verificar si el usuario ya existe
        existing_user = get_user_by_username(username)
        if existing_user:
            flash('El nombre de usuario ya está en uso', 'error')
            return redirect(url_for('register'))

        # Hash de la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insertar el nuevo usuario en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (username, password, nombre, apellidos) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, nombre, apellidos)
            )
            conn.commit()
            flash('¡Usuario registrado exitosamente!', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error al registrar el usuario: {err}", 'error')
            print(f"Error al registrar el usuario: {err}")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# Ruta para el logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))

# Ruta para el perfil del usuario
@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Actualizar los datos del perfil del usuario
        direccion_inmueble = request.form['direccion_inmueble']
        nombre_arrendador = request.form['nombre_arrendador']

        try:
            cursor.execute(
                "UPDATE usuarios SET direccion_inmueble = %s, nombre_arrendador = %s WHERE id = %s",
                (direccion_inmueble, nombre_arrendador, user_id)
            )
            conn.commit()
            flash('Perfil actualizado correctamente', 'success')
        except mysql.connector.Error as err:
            flash(f"Error al actualizar el perfil: {err}", 'error')
            print(f"Error al actualizar el perfil: {err}")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('perfil'))

    else:
        # Obtener los datos actuales del usuario
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return render_template('perfil.html', user=user)
        else:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('index'))

# Ruta para mostrar el formulario de agregar departamento
@app.route('/agregar_departamento', methods=['GET'])
def mostrar_formulario_agregar_departamento():
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
    return render_template('agregar_departamento.html')

# Ruta para procesar el formulario de agregar departamento
@app.route('/agregar_departamento', methods=['POST'])
def agregar_departamento():
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
    numero = request.form['numero']
    renta = request.form['renta']
    dia_pago = request.form['dia_pago']
    observaciones = request.form['observaciones']
    inventario = request.form['inventario']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO departamentos (numero, renta, dia_pago, observaciones, inventario) VALUES (%s, %s, %s, %s, %s)",
                   (numero, renta, dia_pago, observaciones, inventario))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('lista_departamentos'))  # Redirige a la lista de departamentos

# Ruta para mostrar el formulario de agregar inquilino
@app.route('/agregar_inquilino', methods=['GET'])
def mostrar_formulario_agregar_inquilino():
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
        inventario = request.form['inventario']

        cursor.execute("UPDATE departamentos SET numero = %s, renta = %s, dia_pago = %s, observaciones = %s, inventario = %s WHERE id = %s",
                       (numero, renta, dia_pago, observaciones, inventario, departamento_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Departamento actualizado correctamente', 'success')
        return redirect(url_for('lista_departamentos'))

# Ruta para borrar un departamento
@app.route('/borrar_departamento/<int:departamento_id>')
def borrar_departamento(departamento_id):
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inquilinos WHERE id = %s", (inquilino_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Inquilino borrado correctamente', 'success')
    return redirect(url_for('lista_inquilinos'))

# --- RUTAS PARA PLANTILLAS DE CONTRATOS ---

@app.route('/seleccionar_plantilla/<int:departamento_id>')
def seleccionar_plantilla(departamento_id):
    """Muestra las plantillas disponibles para un departamento."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Obtener plantillas generales
    plantillas_generales = [{'nombre': plantilla, 'id': None} for plantilla in os.listdir(PLANTILLAS_DIR)]

    # Obtener plantillas del usuario
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nombre_archivo FROM plantillas_usuario WHERE user_id = %s",
        (user_id,)
    )
    plantillas_usuario = [{'nombre': p['nombre_archivo'], 'id': p['id']} for p in cursor.fetchall()]
    cursor.close()
    conn.close()

    return render_template('seleccionar_plantilla.html', departamento_id=departamento_id, plantillas_generales=plantillas_generales, plantillas_usuario=plantillas_usuario)

@app.route('/generar_contrato/<int:departamento_id>/<plantilla_nombre>')
def generar_contrato(departamento_id, plantilla_nombre):
    """Genera el contrato a partir de la plantilla seleccionada."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener el inquilino actual del departamento
    cursor.execute("SELECT id FROM inquilinos WHERE departamento_id = %s ORDER BY fecha_inicio DESC LIMIT 1", (departamento_id,))
    inquilino = cursor.fetchone()

    if inquilino:
        inquilino_id = inquilino['id']
    else:
        flash('No se encontró un inquilino para este departamento.', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Obtener datos del inquilino y departamento
    inquilino = obtener_inquilino_por_id(inquilino_id)
    departamento = obtener_departamento_por_id(departamento_id)

    # Obtener datos del usuario actual (para nombre del arrendador y dirección del inmueble)
    user_id = session['user_id']
    cursor.execute("SELECT nombre_arrendador, direccion_inmueble FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash('Datos del usuario no encontrados.', 'error')
        return redirect(url_for('perfil'))

    nombre_arrendador = user['nombre_arrendador']
    direccion_inmueble = user['direccion_inmueble']

    if not inquilino or not departamento:
        flash('Error: No se encontró el inquilino o el departamento.', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Construir la ruta completa a la plantilla
    plantilla_path = os.path.join(PLANTILLAS_DIR, plantilla_nombre)

    # Leer la plantilla
    try:
        with open(plantilla_path, 'r') as f:
            plantilla_content = f.read()
    except FileNotFoundError:
        flash(f'Error: No se encontró la plantilla {plantilla_nombre}', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Reemplazar los marcadores de posición con la información del inquilino, departamento y usuario
    contrato_final = plantilla_content.replace("{{propietario_nombre}}", nombre_arrendador if nombre_arrendador else "No especificado")
    contrato_final = contrato_final.replace("{{inquilino.nombre}}", inquilino['nombre'] if inquilino['nombre'] else "")
    contrato_final = contrato_final.replace("{{inquilino.apellidos}}", inquilino['apellidos'] if inquilino['apellidos'] else "")
    contrato_final = contrato_final.replace("{{departamento.numero}}", str(departamento['numero']) if departamento['numero'] else "")
    contrato_final = contrato_final.replace("{{departamento.direccion}}", direccion_inmueble if direccion_inmueble else "No especificado")
    contrato_final = contrato_final.replace("{{departamento.renta}}", str(departamento['renta']) if departamento['renta'] else "")
    contrato_final = contrato_final.replace("{{departamento.dia_pago}}", str(departamento['dia_pago']) if departamento['dia_pago'] else "")
    contrato_final = contrato_final.replace("{{departamento.observaciones}}", departamento['observaciones'] if departamento['observaciones'] else "")
    contrato_final = contrato_final.replace("{{fecha_inicio}}", inquilino['fecha_inicio'].strftime('%d/%m/%Y') if inquilino['fecha_inicio'] else "")
    contrato_final = contrato_final.replace("{{fecha_fin}}", inquilino['fecha_fin'].strftime('%d/%m/%Y') if inquilino['fecha_fin'] else "")
    contrato_final = contrato_final.replace("{{inquilino.fiador_nombre}}", inquilino['fiador_nombre'] if inquilino['fiador_nombre'] else "")
    contrato_final = contrato_final.replace("{{inquilino.fiador_apellidos}}", inquilino['fiador_apellidos'] if inquilino['fiador_apellidos'] else "")
    contrato_final = contrato_final.replace("{{fecha_actual}}", datetime.date.today().strftime('%d/%m/%Y'))
     # Formatear el inventario
    inventario = departamento['inventario']
    if inventario:
        inventario_lineas = inventario.splitlines()
        inventario_formateado = "\n".join([f"    • {linea}" for linea in inventario_lineas])
    else:
        inventario_formateado = "No especificado"

    contrato_final = contrato_final.replace("{{departamento.inventario}}", inventario_formateado)

    # Convertir renta a letras
    renta_en_letras = num_a_letras(int(departamento['renta']))
    contrato_final = contrato_final.replace("{{renta_en_letras}}", renta_en_letras if renta_en_letras else "")

    return render_template('contrato_generado.html', contrato=contrato_final, departamento_id=departamento_id)

@app.route('/generar_contrato_usuario/<int:departamento_id>/<plantilla_id>')
def generar_contrato_usuario(departamento_id, plantilla_id):
    """Genera el contrato a partir de una plantilla del usuario."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar que la plantilla pertenece al usuario
    cursor.execute(
        "SELECT * FROM plantillas_usuario WHERE id = %s AND user_id = %s",
        (plantilla_id, user_id)
    )
    plantilla = cursor.fetchone()

    if not plantilla:
        flash('La plantilla no existe o no tienes permiso para usarla', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Construir la ruta completa a la plantilla
    plantilla_path = os.path.join(PLANTILLAS_USUARIO_DIR, str(user_id), plantilla['nombre_archivo'])

    # Obtener el inquilino actual del departamento
    cursor.execute("SELECT id FROM inquilinos WHERE departamento_id = %s ORDER BY fecha_inicio DESC LIMIT 1", (departamento_id,))
    inquilino = cursor.fetchone()

    if inquilino:
        inquilino_id = inquilino['id']
    else:
        flash('No se encontró un inquilino para este departamento.', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Obtener datos del inquilino y departamento
    inquilino = obtener_inquilino_por_id(inquilino_id)
    departamento = obtener_departamento_por_id(departamento_id)

    # Obtener datos del usuario actual (para nombre del arrendador y dirección del inmueble)
    cursor.execute("SELECT nombre_arrendador, direccion_inmueble FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash('Datos del usuario no encontrados.', 'error')
        return redirect(url_for('perfil'))

    nombre_arrendador = user['nombre_arrendador']
    direccion_inmueble = user['direccion_inmueble']

    if not inquilino or not departamento:
        flash('Error: No se encontró el inquilino o el departamento.', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Leer la plantilla
    try:
        with open(plantilla_path, 'r') as f:
            plantilla_content = f.read()
    except FileNotFoundError:
        flash(f'Error: No se encontró la plantilla', 'error')
        return redirect(url_for('departamentos_contratos'))

    # Reemplazar los marcadores de posición
    contrato_final = plantilla_content.replace("{{propietario_nombre}}", nombre_arrendador if nombre_arrendador else "No especificado")
    contrato_final = contrato_final.replace("{{inquilino.nombre}}", inquilino['nombre'] if inquilino['nombre'] else "")
    contrato_final = contrato_final.replace("{{inquilino.apellidos}}", inquilino['apellidos'] if inquilino['apellidos'] else "")
    contrato_final = contrato_final.replace("{{departamento.numero}}", str(departamento['numero']) if departamento['numero'] else "")
    contrato_final = contrato_final.replace("{{departamento.direccion}}", direccion_inmueble if direccion_inmueble else "No especificado")
    contrato_final = contrato_final.replace("{{departamento.renta}}", str(departamento['renta']) if departamento['renta'] else "")
    contrato_final = contrato_final.replace("{{departamento.dia_pago}}", str(departamento['dia_pago']) if departamento['dia_pago'] else "")
    contrato_final = contrato_final.replace("{{departamento.observaciones}}", departamento['observaciones'] if departamento['observaciones'] else "")
    contrato_final = contrato_final.replace("{{fecha_inicio}}", inquilino['fecha_inicio'].strftime('%d/%m/%Y') if inquilino['fecha_inicio'] else "")
    contrato_final = contrato_final.replace("{{fecha_fin}}", inquilino['fecha_fin'].strftime('%d/%m/%Y') if inquilino['fecha_fin'] else "")
    contrato_final = contrato_final.replace("{{inquilino.fiador_nombre}}", inquilino['fiador_nombre'] if inquilino['fiador_nombre'] else "")
    contrato_final = contrato_final.replace("{{inquilino.fiador_apellidos}}", inquilino['fiador_apellidos'] if inquilino['fiador_apellidos'] else "")
    contrato_final = contrato_final.replace("{{fecha_actual}}", datetime.date.today().strftime('%d/%m/%Y'))
    contrato_final = contrato_final.replace("{{departamento.inventario}}", departamento['inventario'] if departamento['inventario'] else "No especificado")

    # Convertir renta a letras
    renta_en_letras = num_a_letras(int(departamento['renta']))
    contrato_final = contrato_final.replace("{{renta_en_letras}}", renta_en_letras if renta_en_letras else "")

    return render_template('contrato_generado.html', contrato=contrato_final, departamento_id=departamento_id)

# --- RUTAS PARA SUBIR Y GESTIONAR PLANTILLAS DE USUARIO ---

@app.route('/subir_plantilla', methods=['GET', 'POST'])
def subir_plantilla():
    """Permite a los usuarios subir sus propias plantillas."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'plantilla' not in request.files:
            flash('No se ha seleccionado ningún archivo', 'error')
            return redirect(request.url)

        file = request.files['plantilla']

        if file.filename == '':
            flash('No se ha seleccionado ningún archivo', 'error')
            return redirect(request.url)

        # Validar la extensión del archivo
        # Ahora se permite .docx, ademas de .txt y .html:
        if file and file.filename.endswith(('.txt', '.html', '.docx')):
            filename = file.filename
            user_id = session['user_id']

            # Guardar la plantilla en el sistema de archivos
            # Asegurarse de que la carpeta del usuario exista
            user_folder = os.path.join(PLANTILLAS_USUARIO_DIR, str(user_id))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)

            # Si es un archivo .docx, convertirlo a HTML
            if filename.endswith('.docx'):
                try:
                    # Convierte el docx a HTML usando mammoth
                    with open(filepath, "rb") as docx_file:
                        result = mammoth.convert_to_html(docx_file)
                        html = result.value # El HTML convertido

                        # Genera un nuevo nombre de archivo con extensión .html
                        html_filename = filename[:-5] + '.html'
                        html_filepath = os.path.join(user_folder, html_filename)

                        # Guarda el HTML en un nuevo archivo
                        with open(html_filepath, 'w', encoding='utf-8') as html_file:
                            html_file.write(html)

                    # Eliminar el archivo .docx original (opcional)
                    os.remove(filepath)

                    # Actualizar el nombre del archivo para referencia en la base de datos
                    filename = html_filename

                except Exception as e:
                    flash(f'Error al convertir el archivo .docx a .html: {e}', 'error')
                    print(f"Error al convertir el archivo .docx a .html: {e}")
                    # Considera eliminar el archivo .docx si la conversión falla
                    os.remove(filepath)
                    return redirect(url_for('gestionar_plantillas'))

            # Guardar la referencia a la plantilla en la base de datos (usando filename)
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO plantillas_usuario (user_id, nombre_archivo) VALUES (%s, %s)",
                    (user_id, filename)
                )
                conn.commit()
                flash('Plantilla subida correctamente', 'success')
            except mysql.connector.Error as err:
                flash(f"Error al guardar la plantilla en la base de datos: {err}", 'error')
                print(f"Error al guardar la plantilla en la base de datos: {err}")
            finally:
                cursor.close()
                conn.close()

            return redirect(url_for('gestionar_plantillas'))
        else:
            flash('Formato de archivo no permitido. Solo se admiten archivos .txt, .html y .docx', 'error')

    return render_template('subir_plantilla.html')

@app.route('/gestionar_plantillas')
def gestionar_plantillas():
    """Permite a los usuarios ver y eliminar sus plantillas."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM plantillas_usuario WHERE user_id = %s",
        (user_id,)
    )
    plantillas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('gestionar_plantillas.html', plantillas=plantillas)

@app.route('/eliminar_plantilla/<int:plantilla_id>')
def eliminar_plantilla(plantilla_id):
    """Elimina una plantilla del usuario."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar que la plantilla pertenece al usuario actual
    cursor.execute(
        "SELECT * FROM plantillas_usuario WHERE id = %s AND user_id = %s",
        (plantilla_id, user_id)
    )
    plantilla = cursor.fetchone()

    if plantilla:
        # Eliminar el archivo del sistema de archivos
        filepath = os.path.join(PLANTILLAS_USUARIO_DIR, str(user_id), plantilla['nombre_archivo'])
        try:
            os.remove(filepath)

            # Eliminar la referencia de la base de datos
            cursor.execute(
                "DELETE FROM plantillas_usuario WHERE id = %s",
                (plantilla_id,)
            )
            conn.commit()
            flash('Plantilla eliminada correctamente', 'success')
        except Exception as e:
            flash(f"Error al eliminar la plantilla: {e}", 'error')
            print(f"Error al eliminar la plantilla: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        flash('La plantilla no existe o no tienes permiso para eliminarla', 'error')
        cursor.close()
        conn.close()

    return redirect(url_for('gestionar_plantillas'))

@app.route('/previsualizar_plantilla/<int:plantilla_id>')
def previsualizar_plantilla(plantilla_id):
    """Previsualiza una plantilla de usuario específica."""
    if 'logged_in' not in session or not session['logged_in']:
        flash('Inicia sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar que la plantilla pertenece al usuario actual
    cursor.execute(
        "SELECT * FROM plantillas_usuario WHERE id = %s AND user_id = %s",
        (plantilla_id, user_id)
    )
    plantilla = cursor.fetchone()

    if not plantilla:
        cursor.close()
        conn.close()
        flash('La plantilla no existe o no tienes permiso para verla', 'error')
        return redirect(url_for('gestionar_plantillas'))

    # Construir la ruta completa a la plantilla
    plantilla_path = os.path.join(PLANTILLAS_USUARIO_DIR, str(user_id), plantilla['nombre_archivo'])

    # Leer la plantilla
    try:
        with open(plantilla_path, 'r') as f:
            plantilla_content = f.read()
    except FileNotFoundError:
        cursor.close()
        conn.close()
        flash(f'Error: No se encontró la plantilla', 'error')
        return redirect(url_for('gestionar_plantillas'))

    # Obtener datos del usuario actual (para nombre del arrendador y dirección del inmueble)
    cursor.execute("SELECT nombre_arrendador, direccion_inmueble FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    

    if not user:
        cursor.close()
        conn.close()
        flash('Datos del usuario no encontrados.', 'error')
        return redirect(url_for('perfil'))

    nombre_arrendador = user['nombre_arrendador']
    direccion_inmueble = user['direccion_inmueble']

    # Reemplazar los marcadores de posición con la información del usuario, o con valores por defecto si no hay información
    contrato_final = plantilla_content.replace("{{propietario_nombre}}", nombre_arrendador if nombre_arrendador else "No especificado")
    contrato_final = contrato_final.replace("{{inquilino.nombre}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{inquilino.apellidos}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{departamento.numero}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{departamento.direccion}}", direccion_inmueble if direccion_inmueble else "No especificado")
    contrato_final = contrato_final.replace("{{departamento.renta}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{departamento.dia_pago}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{departamento.observaciones}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{fecha_inicio}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{fecha_fin}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{inquilino.fiador_nombre}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{inquilino.fiador_apellidos}}", "")  # Valor por defecto
    contrato_final = contrato_final.replace("{{fecha_actual}}", datetime.date.today().strftime('%d/%m/%Y'))
    contrato_final = contrato_final.replace("{{departamento.inventario}}", "No especificado")  # Valor por defecto
    contrato_final = contrato_final.replace("{{renta_en_letras}}", "")  # Valor por defecto

    cursor.close()
    conn.close()

    # Renderizar la plantilla en una página HTML básica
    return render_template('previsualizar_plantilla.html', plantilla_content=contrato_final)

if __name__ == '__main__':
    app.run(debug=True)