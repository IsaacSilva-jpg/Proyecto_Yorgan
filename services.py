# Aquí escribes las funciones que interactúan con la base 
# de datos (guardar, actualizar, borrar). Este archivo 
# importa los modelos desde models.py.
from models import Usuario, AnalisisCV, noticia
from sqlalchemy import update, select, text, desc

from extensions import db
from typing import List




def obtener_objeto_bd(correo):

    stmt = select(Usuario).where(Usuario.email == correo)
    usuario_db = db.session.scalar(stmt)

    return usuario_db

def nuevo_usuario_db(correo, contraseña, estado, auth_provider):


    # CREAMOS UN NUEVO USUARIO CON LOS DATOS QUE EL USER INGRESO
    nuevo_usuario = Usuario(email= correo, contraseña= contraseña, auth_provider= auth_provider, estado= estado)
    db.session.add(nuevo_usuario)
    db.session.commit()

    return nuevo_usuario

def obtener_correo_por_id(usuario_actual):

    # NECESITAMOS BUSCAR EL EMAIL DEL USUARIO RECIEN REGISTRADO, MEDIANTE SU ID
    # REGRESA NONE SI EL user NO EXISTE
    correo = db.session.query(Usuario.email).filter_by(id=usuario_actual).scalar()

    if correo is None:
        return None
    
    return correo

def verificar_usuario(email_usuario):

    usuario_no_verificado= obtener_objeto_bd(email_usuario)
    print("TENEMOS OBJETO GRACIAS A LA FUNCION: ", usuario_no_verificado)
    
    # Extraemos al usuario de la BD, filtrando a traves del correo que 
    # esta en el token
    # usuario_no_verificado = db.session.query(Usuario).filter_by(email= email_usuario).first()
    
    # Comprobamos si la variable contiene algo
    if usuario_no_verificado:
        # cambiamos el estado del usuario de "no-verificado" a "verificado"
        # sin esto, el usuario seguiria sin verificarse
        usuario_no_verificado.estado = "verificado"
    else:
        usuario_no_verificado = None

    # Subimos los cambios, sin esto la BD no actualiza la informacion anterior
    db.session.commit()
    # redireccionamos al usuario al endpoint de inicio de sesion

    return usuario_no_verificado

def usuario_estado(correo):

    usuario_estado = db.session.query(Usuario.estado).filter_by(email= correo).scalar()

    return usuario_estado


def usuario_existe(correo):

    # usuario existe?
    stmt = select(Usuario).where(Usuario.email == correo)
    existe = db.session.scalar(select(stmt.exists()))
    
    # DEVOLVEMOS TRUE O FALSE
    return existe

def subir_cambio_contra_bd(email_usuario, hash_contra):

    usuario_cambio_contra = db.session.query(Usuario).filter_by(email= email_usuario).first()
    usuario_cambio_contra.contraseña = hash_contra
    db.session.commit()

    return usuario_cambio_contra


def tipo_de_cuenta(correo):

    tipo_de_cuenta = db.session.query(Usuario.auth_provider).filter(Usuario.email == correo).scalar()
    
    return tipo_de_cuenta

# ************************************

def recibidor_falso(id_user, resultado_final):

    nuevo_analisis_id= subir_analisis(id_user, resultado_final)
    
    return nuevo_analisis_id


# ************************************

def subir_analisis(user_id, analisis_gemini):

    nuevo_analisis = (
        db.session.query(AnalisisCV)
        .filter(AnalisisCV.usuario_id == user_id)
        .order_by(AnalisisCV.fecha_creacion.desc())
        .first()
    )

    if not nuevo_analisis:
        print("este usuario no tiene analisis")

    nuevo_analisis.resultado_ia = analisis_gemini
    
    db.session.add(nuevo_analisis)
    db.session.commit()

    return nuevo_analisis.id



def obtener_analisis(id_analisis, usuario_actual):

    calificacion= db.session.query(AnalisisCV.resultado_ia).filter_by(id=id_analisis, usuario_id=usuario_actual).scalar()
    
    if not calificacion:

        return None

    return calificacion

def extraer_noticia(slug_noticia):

    contenido= db.session.query(noticia).filter_by(slug=slug_noticia).first()
    
    return contenido

def cargar_usuario_login_manager(user_id):

    return db.session.get(Usuario, int(user_id))

def actualizar_foto(usuario_registrado, imagen_user):

    usuario_registrado.imagen_google= imagen_user
    db.session.commit()

def validador_base_de_datos():

    try:
        db.session.execute(text('SELECT 1'))
        return True

    except Exception:
        return False


def guarda_texto_bd(paginas, descripcion, id_user):
    
    texto_puente = AnalisisCV(texto_cv= paginas, texto_vacante= descripcion, usuario_id=id_user)

    db.session.add(texto_puente)
    db.session.commit()

    print("ID INSERTADO:", texto_puente.id)
    print("TEXTO CV INSERTADO:", texto_puente.texto_cv[:100])
    print("DESCRIPCIÓN INSERTADA:", texto_puente.texto_vacante[:100])

    return texto_puente.id

def extraer_texto_puente(id_analisis):

    # Obtiene el objeto completo del modelo
    analisis = AnalisisCV.query.filter_by(id=id_analisis).first()

    print("ID RECIBIDO:", id_analisis)

    # POR QUE RAYOS AQUI ARROJA NONE COMO VACIO
    print("OBJETO ENCONTRADO:", analisis)

    # PERO ESTO SI LO DA????
    print("OBJETO ENCONTRADO:", analisis.id)
    print("OBJETO ENCONTRADO:", analisis.usuario_id)

    if analisis:

        # PERO AQUI SI MUESTRA EL TEXTO COMO SI TUVIERA ALGO DENTRO?
        print("TEXTO CV:", analisis.texto_cv)

        print("DESCRIPCIÓN:", analisis.texto_vacante)
        
        texto_cv_puente = analisis.texto_cv
        texto_descripcion = analisis.texto_vacante

        return texto_cv_puente, texto_descripcion

    return None



def desacoplador_texto(calificacion):

# Separamos el veredicto y la justificación usando texto plano
    veredicto = "NO"
    if "CALIFICACION IA: SI" in calificacion.upper() or "CALIFICACION IA: SÍ" in calificacion.upper():
        veredicto = "SI"
            
    # Extraemos la parte de la justificación
    justificacion = calificacion
    if "Justificación:" in calificacion:
        justificacion = calificacion.split("Justificación:")[1].strip()
    elif "Justificacion:" in calificacion:
        justificacion = calificacion.split("Justificacion:")[1].strip()

    return veredicto, justificacion
