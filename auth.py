
# LIBRERIA MANEJO DE SERVIDORES FLASK
from flask import redirect, url_for, request, render_template, request, session, jsonify, flash, Blueprint, send_from_directory, current_app, Response, stream_with_context

# FUNCIONES EXTERIORES DE MAIN
from funciones import extraer_texto, analisis, formato_compatible, stream_gemini # simular_gemini_stream

# Flask-WTF
from forms import LoginForm, RegisterForm, ReenviarForm, NuevaContra, Soporte, CerrarSesion

# FLASK-MAIL
from flask_mail import Message, Mail
from email.header import Header

from itsdangerous import SignatureExpired, BadSignature, URLSafeTimedSerializer

from flask_login import login_user, current_user, logout_user, login_required

# MODULOS
from services import nuevo_usuario_db, obtener_correo_por_id, verificar_usuario, usuario_existe, subir_cambio_contra_bd, obtener_objeto_bd, tipo_de_cuenta, subir_analisis, obtener_analisis, usuario_estado, extraer_noticia, actualizar_foto, validador_base_de_datos, guarda_texto_bd, extraer_texto_puente, desacoplador_texto

# TOKEN SERIALIZADOR
from itsdangerous import URLSafeTimedSerializer

# HASH DE CONTRASEÑAS
from werkzeug.security import generate_password_hash, check_password_hash

# LECTURA DE VARIABLES DE ENTORNO
from dotenv import load_dotenv
import os

# LIBRERIA GOOGLE GEMINI
from google import genai

from extensions import limitador, mail, google, login_manager, logfire_flask, logfire

load_dotenv()

serializador = URLSafeTimedSerializer(os.getenv("KEY_SERIALI"))

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise RuntimeError("Sin GEMINI_API_KEY en las variables de entorno")

client = genai.Client(api_key=gemini_api_key)   


MAIL_ENABLED = os.getenv("MAIL_ENABLED", "True") == "True"

# Creamos el objeto Blueprint
auth_bp = Blueprint("auth", __name__)

# ENDPOINT PRINCIPAL REDIRECCIONA AL LOGIN
@auth_bp.route("/")
def home():

    logfire.info("Logfire activado")

    if current_user.is_authenticated:
        return render_template("home.html", usuario_firmado = "usuario_firmado")
    else:
        return render_template("home.html", usuario_no_firmado= "usuario_estatus")
    
# ENDPOINT REGISTRO DE USUARIOS
@auth_bp.route("/registro", methods = ["GET", "POST"])
def registro():


    # revisamos si el usuario esta autenticado, si es true redirije al usuario firmado 
    # a la pagina principal
    if current_user.is_authenticated:
        return redirect(url_for("auth.recibir_archivo"))


    # INVOCAMOS LA CLASE DE LOS FORMULARIOS PARA HACER UNA 
    # INSTANCIA Y USAR SUS ATRIBUTOSs
    form = RegisterForm()

    if form.validate_on_submit():

        correo = form.correo.data
        contraseña = form.password.data

        usuario_db = obtener_objeto_bd(correo)

        if usuario_db:

            flash(f"Esta cuenta ya esta registrada con {usuario_db.auth_provider}. Inicia sesion con {usuario_db.auth_provider}", "danger")
            return redirect(url_for("auth.inicio_sesion"))
        

        #  CREAMOS UN HASH DE CONTRASEÑA
        hash_contraseña = generate_password_hash(contraseña)

        usuario_registrandose = nuevo_usuario_db(correo, hash_contraseña, estado= "no-verificado", auth_provider= "local")

        # AGREGAMOS ENCRIPTADOR - EVITAMOS MOSTRAR EL ID DE LA BD
        token_id= serializador.dumps(usuario_registrandose.id, salt="id")
        
        return redirect(url_for("auth.generador_de_token", usuario_actual = token_id, tipo_de_plantilla = "registro_de_usuarios"))

    return render_template("register.html", form=form)


# ENDPOINT GENERADOR DE TOKENS AL EMAIL
@auth_bp.route("/generador/<usuario_actual>/<tipo_de_plantilla>")
def generador_de_token(usuario_actual, tipo_de_plantilla):
        
    # DESENCRIPTADOR DE TOKEN
    # COLOCAR CAPTURADOR DE ERRORES EN CASO DE QUE SALGA FALLA O QUE EXPIRE
    try:
        usuario_actual_id = serializador.loads(usuario_actual, max_age=300, salt="id")
    except SignatureExpired:
        flash("Token expirado, genera uno nuevo")
        return redirect(url_for("auth.reenviar_token"))
    
    except BadSignature:
        return render_template("manejo_errores.html", error="Token inválido"), 400

    correo = obtener_correo_por_id(usuario_actual_id)

    if correo is None:
        flash("Hubo un problema con la base de datos")
        return redirect(url_for("auth.registro"))

    # CREAMOS EL TOKEN CON EL CORREO DEL USUARIO SOBRE EL SALT ESPECIFICADO
    token = serializador.dumps({"correo": correo}, salt="verificacion_email")

    # CREAMOS EL ENLACE DE CONFIRMACION AL USUARIO
    enlace = url_for("auth.ruta_confirmacion", token = token, _external = True)

    try:
        # implementado logica del envio de correo con Flask-MAIL
        mensaje_verifica = Message("Verificacion de correo en tu cuenta Yorgan", recipients = [correo])
        mensaje_verifica.html = render_template("verificar_correo.html", enlace=enlace)
        mail.send(mensaje_verifica)
        
    except(Exception): 
        flash("Reporte no enviado!", "danger")
        return redirect(url_for("auth.soporte_correo"))

    return render_template("mensaje.html", correo= correo, tipo_de_plantilla= tipo_de_plantilla)

# ENDPOINT PARA EXTRAER CORREO Y REENVIAR TOKEN 
@auth_bp.route("/reenviar", methods = ["GET", "POST"])
def reenviar_token():

    # TOMAMOS EL CUERPO DE LA CLASE FORMULARIO
    form = ReenviarForm()

    if not MAIL_ENABLED:
        flash("Servicio de tokens temporalmente deshabilitado.")
        return redirect(url_for("auth.inicio_sesion"))

    # TENEMOS QUE HACER CLASE ESPECIFICA
    if form.validate_on_submit():
        
        correo = form.correo.data

        # OBTENEMOS OBJETO COMPLETO, HAY QUE REVISAR SI ES NECESARIO O
        # BASTA CON SOLO OBTENER INFORMACION DE VERIFICACION USER
        usuario_reenviar_token = obtener_objeto_bd(correo)

        if usuario_reenviar_token is None:
            flash("Cuenta no registrada para reenviar token")
            return redirect(url_for("auth.reenviar_token"))

        if usuario_reenviar_token.estado == "verificado":
            flash("Esta cuenta ya está verificada, no es necesario reenviar token", "danger")
            return redirect(url_for("auth.reenviar_token"))

        token_id= serializador.dumps(usuario_reenviar_token.id, salt="id")

        # ACA REDIRECCIONAMOS AL USUARIO CON SU ID DEL USER EN BD
        return redirect(url_for("auth.generador_de_token", usuario_actual= token_id, tipo_de_plantilla = "reenvio_token"))
    
    # PROGRAMAR PLANTILLA PARA QUE RECIBA FLASH
    return render_template("forms_unifi.html", form=form, plantilla= "reenviar_token")

# ENDPOINT QUE RECIBE CONFIRMACION DEL TOKEN POR CORREO
@auth_bp.route("/confirmacion/<token>")
def ruta_confirmacion(token):

    try:
        # DESENCRIPTAMOS TOKEN PARA VERIFICARLO
        email = serializador.loads(token, max_age=300, salt="verificacion_email")
    except SignatureExpired:
        # SI EL TOKEN YA EXPIRÓ RENDERIZAMOS PLANTILLA DE ERRORES
        return render_template("manejo_errores.html", error= "SignatureExpired", tipo_error= "reenviar")
    
    except BadSignature:
        return render_template("manejo_errores.html", error="Token inválido"), 400
    # SI EL TOKEN CONTIENE ALGUN OTRO DETALLE
    
    except Exception as error:
        # EL ERROR QUE SALGA EL HTML LO RECIBE Y DEPENDE QUE TIPO SEA MUESTRA UNA PLANTILLA EN ESPECIFICO
        return render_template("manejo_errores.html", error = error)

    # SACAMOS EL EMAIL DEL USUARIO A TRAVES DEL TOKEN, INGRESANDO POR KEY EN EL TOKEN
    email_usuario = email["correo"]

    # VERIFICANDO EL USUARIO
    usuario_ya_verificado= verificar_usuario(email_usuario)

    if usuario_ya_verificado is None:
        flash("Hubo un error, contacta a soporte")
        return redirect(url_for("auth.inicio_sesion"))

    login_user(usuario_ya_verificado)

    flash("Tu cuenta fue verificada exitosamente", "success")
    return redirect(url_for("auth.inicio_sesion"))

# ENDPOINT PARA RECUPERACION DE CONTRASELA (ENPOINT A MEJORAR) - OLVIDE CONTRASEÑA
@auth_bp.route("/recuperacion_contraseña", methods = ["GET", "POST"])
def recovery():

    form = ReenviarForm()

    if not MAIL_ENABLED:
        flash("La recuperación de contraseña está temporalmente deshabilitada.")
        return redirect(url_for("auth.inicio_sesion"))

    if form.validate_on_submit():
        # PEDIR CORREO AL USUARIO
        correo = form.correo.data

        usuario_db= obtener_objeto_bd(correo)

        if not usuario_db:
            flash("Tu cuenta no esta registrada, registrala primero")
            return redirect(url_for("auth.registro"))

        if usuario_db.estado == "no-verificado":
            flash("Tu cuenta no esta verificada, verificala primero")
            return redirect(url_for("auth.reenviar_token"))

        if usuario_db.auth_provider == "google":
            flash("Cuenta registrada con Google. No podemos cambiar la contraseña")
            return redirect(url_for("auth.recovery"))
        
        # CREAMOS EL TOKEN CON EL CORREO DEL USUARIO SOBRE EL SALT ESPECIFICADO
        token = serializador.dumps({"correo": correo}, salt="restablecer_contraseña")

        # CREAMOS EL ENLACE DE CONFIRMACION AL USUARIO
        enlace = url_for("auth.nueva_contra_usuario", token = token, _external = True)
        
        try:
            # Concepto del  correo con Flask-MAIL
            mensaje = Message("Restablece tu contraseña en Yorgan", recipients = [correo])

            mensaje.html = render_template("restablecer_password.html", enlace=enlace)
            mail.send(mensaje)
        
        except(Exception): 
            flash("Reporte no enviado!", "danger")
            return redirect(url_for("auth.soporte_correo"))

        flash("Reporte enviado!", "success")

        return render_template("mensaje.html", correo= correo, tipo_de_plantilla= "olvide_contraseña") 
    
    return render_template("forms_unifi.html", form=form, plantilla= "correo_buscar_usuario")

# OLVIDE CONTRASEÑA
@auth_bp.route("/nueva_contra/<token>", methods = ["GET", "POST"])
def nueva_contra_usuario(token):

    form = NuevaContra()

    try:
        # DESENCRIPTAMOS TOKEN PARA VERIFICARLO
        email = serializador.loads(token, max_age=600, salt="restablecer_contraseña")

    except SignatureExpired:
        # SI EL TOKEN YA EXPIRÓ
        return render_template("manejo_errores.html", error= "SignatureExpired", tipo_error = "nueva_contra")
    # SI EL TOKEN CONTIENE ALGUN OTRO DETALLE 
    # EL ERROR QUE SALGA EL HTML LO RECIBE Y DEPENDE QUE TIPO SEA MUESTRA UNA PLANTILLA EN ESPECIFICO
    except Exception as error:
        return render_template("manejo_errores.html", error = error, token= token)

    if form.validate_on_submit():

        contraseña_nueva = form.confirm_password.data
        hash_contra = generate_password_hash(contraseña_nueva)

        # MEDIANTE EL TOKEN SACAMOS EL CORREO DENTRO 
        email_usuario = email["correo"]    

        # FUNCION QUE SUBE LOS CAMBIOS DE LA CONTRASEÑA
        usuario_cambio_contra = subir_cambio_contra_bd(email_usuario, hash_contra)

        # firmamos al usuario
        login_user(usuario_cambio_contra)

        flash('¡Contraseña restablecida! Iniciaste sesion', 'success')
        # 3. Rediriges al interior de la app (Dashboard)
        return redirect(url_for("auth.recibir_archivo"))

    return render_template("forms_unifi.html", form=form, token= token, plantilla= "nueva_contra")


# ENDPOINT INICIO DE SESION DE USUARIOS
@auth_bp.route("/inicio_sesion", methods = ["GET", "POST"])
def inicio_sesion():

    # revisamos si el usuario esta autenticado, si es true redirije al usuario firmado 
    # a la pagina principal
    if current_user.is_authenticated:
        return redirect(url_for("auth.recibir_archivo"))

    form = LoginForm()
    
    if form.validate_on_submit():

        correo = form.correo.data
        contra = form.password.data

        usuario_db= obtener_objeto_bd(correo)
        
        if not usuario_db:
            flash("Correo o contraseña incorrectos")
            return redirect(url_for("auth.registro"))

        # COMPARAMOS CONTRASEÑAS 
        if contra and check_password_hash(usuario_db.contraseña, contra):

            # Revisamos si en la BD el usuario actual esta verificado
            if usuario_db.estado == "no-verificado":
                flash("Usuario no verificado, verifica tu cuenta")
                return redirect(url_for("auth.reenviar_token"))

            if usuario_db.auth_provider is None:
                flash("Hubo un problema con tu cuenta", "danger")
                return redirect(url_for("auth.inicio_sesion"))

            if usuario_db.auth_provider != "local":
                flash(f"Tu cuenta esta registrada con {usuario_db.auth_provider}, usa el boton 'Continuar con google'", "danger")
                return redirect(url_for("auth.inicio_sesion"))

            
            # Funcion que hace una sesion "recuerdame" que dura 30 dias
            # depende de si el usuario la selecciona
            login_user(usuario_db, remember= form.recuerdame.data)            

            # una vez terminado todo, redirijimos al usuario a otra URL
            return redirect(url_for("auth.recibir_archivo"))

        else:
            flash("Contraseñas no coinciden", "error")
            return redirect(url_for("auth.inicio_sesion"))

    return render_template("inicio_sesion.html", form=form)

@auth_bp.route("/login_google")
def login_google():

    redirect_url = url_for("auth.authorize", _external=True)
    return google.authorize_redirect(redirect_url)


@auth_bp.route("/callback", methods = ["GET", "POST"]) # Ruta que recibe el token de google 
def authorize():
    
    # Enviamos el "code" a un endpoint de google
    try:
        # OBTENEMOS EL TOKEN
        token = google.authorize_access_token()
    except Exception as e:
        flash("Se canceló inicio de sesion con google", "danger")
        return redirect(url_for("auth.inicio_sesion"))

    # SACAMOS INFORMACION DEL USER
    user_info = google.get("userinfo").json()

    # SACAMOS DEL "KEY" " DEL DICCIONARIO "EMAIL"
    correo= user_info["email"]
    imagen_user = user_info["picture"]
    
    if not correo or user_info.get("email_verified") not in (True, "true"):
        flash("No pudimos verificar tu correo de Google", "danger")
        return redirect(url_for("auth.inicio_sesion"))

    existe = usuario_existe(correo)

    # SI EXISTE EN LA BASE DE DATOS
    if existe:

        # LLAMAMOS LA FUNCION QUE NOS DA QUE TIPO DE CUENTA ES UN USUARIO
        # PARA SABER EL PROVEDOR Y MOSTRARSELO AL USUARIO 
        # NECESIATAMOS CONSULTA ESPECIFICA
        tipo_cuenta_user= tipo_de_cuenta(correo)

        # VALIDAMOS SI EL USUARIO ES LOCAL
        if tipo_cuenta_user != "google":
            # SE LE NIEGA EL ACCESO, SE LE PIDE FIRMARSE DE OTRA FORMA
            # LLEGAMOS ACA POR QUE EL USUARIO SE REGISTRO "LOCAL"
            flash("Esta cuenta no esta registrada con Google. Por favor, inicia sesión de otra forma.", "danger")
            return redirect(url_for("auth.inicio_sesion"))

        # LLEGAMOS ACA POR QUE EL USUARIO NO ESTA REGISTRADO EN "LOCAL"
        usuario_registrado= obtener_objeto_bd(correo)

        # SI LA FOTO DE PERFIL DE GOOGLE DEL USUARIO ES DIFERENTE A LA ACTUAL
        if usuario_registrado.imagen_google != imagen_user:
            # LA BD LA CAMBIA
            actualizar_foto(usuario_registrado, imagen_user)
        
        login_user(usuario_registrado)
        
        return redirect(url_for("auth.recibir_archivo"))

    # ELSE
    # USUARIO NO ESTA EN BD
    # CREAMOS NUEVO USUARIO A LA BD CON INFO DE GOOGLE
    nuevo_usuario= nuevo_usuario_db(user_info["email"], "N/A", auth_provider= "google", estado= "verificado", imagen_google= imagen_user)
    
    # LO FIRMAMOS CON login_user
    login_user(nuevo_usuario)

    # return redirect(url_for("auth.recibir_archivo", imagen_user=imagen_user))
    return redirect(url_for("auth.recibir_archivo"))

# ENDPOINT PRINCIPAL (ANALIZADOR DE CV)
@auth_bp.route("/analizador", methods = ["GET", "POST"])
@limitador.limit(limit_value="3 per hour", error_message="Has excedido el limite de 3 analisis", methods =["POST"])
@login_required
def recibir_archivo():

    # manejo de formulario 
    if request.method == "POST":
            # recibir archivo cv
        archivo = request.files["cv_file"]
            # recibir descripcion de vacante
        descrip = request.form["job_descrip"]
        
        if not archivo.filename.lower().endswith(".pdf"):
            return jsonify({"fail": "ERROR", "error_details":"El formato de tu archivo no es aceptable (solo .pdf)"}), 400
        
        # limieza descrip (solo detecta si el formulario esta vacio)
        if not descrip:
            return jsonify({"fail": "ERROR", "error_details": "Coloca la descripcion del puesto"}), 400
        if len(descrip) < 40:
            return jsonify({"fail":"ERROR","error_details":"La descripcion es muy corta (no menos de 40 caracteres)" }), 400

        # METODO QUE MUEVE EL CURSOR, NECESARIO PARA LEER LOS BYTES
        archivo.seek(0, 2)
        # ESTANDO EN LA POSICION CORRECTA LEEMOS EL PESO EN BYTES
        peso_en_byte = archivo.tell()
        # OBTENIDO EL DATO ANTERIOR, COLOCAMOS EL CURSOR AL PRINCIPIO
        archivo.seek(0)
        # CONVERSION DEL PESO A MB
        peso_en_mb = peso_en_byte / (1024 * 1024)

        # SI EL PESO DEL ARCHIVO ES MAYOR A 10, CANCELAMOS OPERACION
        if peso_en_mb > 10:
            return jsonify({
                "fail": "413",
                "error_details": "El archivo enviada es demasiado grande para que el servidor la procese."
            }), 413

        # funcion que extrae el texto de las paginas pdf
        paginas = extraer_texto(archivo)

        # VALIDACION LOGICA DE LOS DATOS DEVUELTOS
        if paginas == "":
            return jsonify({"fail":"ERROR 400", "error_details":"No pudimos extraer la informacion de tu archivo"}),400

        id_user = current_user.id

        id_texto_puente_db = guarda_texto_bd(paginas, descrip, id_user)
        
        print("id saliente de guardar texto: ", id_texto_puente_db)
        print("tiipo de dato",type(id_texto_puente_db))

        url_redireccion = url_for("auth.mostrar", id_analisis= id_texto_puente_db)
        
        return jsonify({
            "Exitoso": True,
            "url": url_redireccion
        }), 200

    return render_template("vista_claude_v4.html")

# ENDPOINT MOSTRADOR DE RESULTADOS DEL ANALISIS DE CV
@auth_bp.route("/mostrar/<id_analisis>", methods=["GET", "POST"])
@login_required
@limitador.limit(
    "3 per hour",
    methods=["POST"],
    key_func=lambda: str(current_user.get_id()),
    error_message="Has excedido el límite de 3 análisis por hora")
def mostrar(id_analisis):

    if request.method == "POST":

        print("tenemos id analisis",id_analisis)
        print(type(id_analisis))
        # ATRAVES DE LA CONSULTA A LA BASE DE DATOS SACAMOS "paginas" Y "descrip"
        paginas, descrip= extraer_texto_puente(id_analisis)
        
        print("estamos en mostrar - tenemos paginas cv: ", paginas)
        print("estamos en mostrar - tenemos descripcion job: ", descrip)

        analisis_gemini, texto_cv, texto_job, client_ia, prompt_ia = analisis(paginas, descrip, client)

        # ejecutamos la funcion stream_gemini y guardamos la respuesta 
        # en generador_activo 
        generador_activo = stream_gemini(analisis_gemini, client_ia, prompt_ia, id_user = current_user.id)
    
        # envolvemos la respuesta del stream en stream_with_context función que 
        # mantiene activo el contexto de la petición (request context) 
        # mientras se envían datos en streaming al cliente 
        generador_protegido = stream_with_context(generador_activo)

        # retornamos la respuesta en stream envuelto en "Response"
        return Response(generador_protegido)

    usuario_actual= current_user.id

    calificacion_buscado_por_id = obtener_analisis(id_analisis, usuario_actual)

    if calificacion_buscado_por_id:

        return render_template("mostrar.html", justificacion_db= calificacion_buscado_por_id ,modo_stream = False, identi_analisis=id_analisis)
        
    # si no tenemos analisis, activamos stream
    # MOSTRAR AL USUARIO QUE "ESE ANALISIS NO PERTENECE A ESTA CUENTA
    # pero vamos a hacer el analisis con sus ultimos datos"
    return render_template("mostrar.html", modo_stream=True, identi_analisis=id_analisis)


@auth_bp.route("/soporte",  methods = ["GET", "POST"])
@login_required
def soporte_correo():

    form = Soporte()
    
    # extraemos informacion del formulario manejo de formulario 
    if form.validate_on_submit():

        nombre = form.nombre.data
        correo = form.correo.data
        mensaje = form.mensaje.data
        tipo_de_reporte = form.opcion.data

        correo_soporte= "soporte.yorgan@gmail.com"

        try:
            enviar_correo = Message(tipo_de_reporte, recipients=[correo_soporte])
            enviar_correo.html = render_template("fallas_sugerencias.html", tipo_de_reporte=tipo_de_reporte, nombre= nombre, correo= correo, texto_reporte= mensaje)
            mail.send(enviar_correo)
        
        except(Exception): 
            flash("Reporte no enviado!", "danger")
            return redirect(url_for("auth.soporte_correo"))

        flash("Reporte enviado!", "success")

        return redirect(url_for("auth.soporte_correo"))

    return render_template("soporte_nuevo.html", form=form)

@auth_bp.route("/cerrar_sesion", methods=["POST"])
@login_required
def cerrar_sesion():

    logout_user()
    session.clear()

    return redirect(url_for("auth.home"))

@auth_bp.route("/favicon.ico")
def favicon():

    return send_from_directory(
            os.path.join(current_app.root_path, 'static'),
            'Logo_no_oficial_yorgan (1).png',
            mimetype='image/png'
        )

@auth_bp.route("/quienes_somos")
def quienes_somos():

    return render_template("nosotros.html")

@auth_bp.route("/informacion_estrategica")
def informacion():

    return render_template("informacion_estrategica.html")

@auth_bp.route("/noticia/<slug>")
def noticia(slug):

    slug_noticia= slug

    contenido= extraer_noticia(slug_noticia)

    return render_template("plantilla_noticias.html", noticia=contenido)

@auth_bp.route("/health")
def health_check():

    estado_respuesta= {
        "respuesta":"Buena",
        "base_de_datos":"Buena",
    }

    if not validador_base_de_datos():

        estado_respuesta["respuesta"]= "Mala"
        estado_respuesta["base_de_datos"]= "Mala"

        return jsonify(estado_respuesta), 503
    
    return jsonify(estado_respuesta), 200


