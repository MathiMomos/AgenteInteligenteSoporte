## #######################################################################################################
##
## @copyright Big Data Academy [info@bigdataacademy.org]
## @professor Alonso Melgarejo [alonsoraulmgs@gmail.com]
##
## #######################################################################################################

## ################q######################################################################################
## @section Configuración
## #######################################################################################################

# Importamos la configuración
import src.util.util_env as key

## ################q######################################################################################
## @section Librerías
## #######################################################################################################

# Utilitario para recortar el documento
from langchain.text_splitter import CharacterTextSplitter

# Librería para generar identificadores únicos
import uuid

# Utilitario para enviar de manera segura contraseñas
from azure.core.credentials import AzureKeyCredential

# Utilitario para conectarnos al servicio de AI Search
from azure.search.documents import SearchClient

# Utilitario para conectarnos al servicio
from azure.ai.formrecognizer import DocumentAnalysisClient

# Utilitario para crear un documento que pueda ser cortado, con el texto extraído
from langchain.schema import Document

# Librería para controlar la ejecución del código
import time

# Librería para manipular el sistema operativa
import os

# Librería con utilitarios para procesar archivos
import shutil

## #######################################################################################################
## @section Funciones
## #######################################################################################################


# Función para obtener los archivos de una ruta
def obtenerArchivos(ruta=None):
    # Listamos el contenido de la carpeta
    os.listdir(ruta)

    # Acumulamos los archivos encontrados
    listaDeArchivos = []
    for elemento in os.listdir(ruta):
        rutaCompleta = os.path.join(ruta, elemento)  # type: ignore

        # Solo añadimos si es archivo (no directorio)
        if os.path.isfile(rutaCompleta):
            listaDeArchivos.append(rutaCompleta)

    return listaDeArchivos


# Extrae el contenido de un archivo
def leerContenidoDeDocumento(rutaArchivo):

    # Nos conectamos al servicio
    servicio = DocumentAnalysisClient(
        key.require("CONF_AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        AzureKeyCredential(key.require("CONF_AZURE_DOCUMENT_INTELLIGENCE_KEY")),
    )

    # Abrimos el documento que queremos analizar
    with open(rutaArchivo, "rb") as archivo:

        # Damos la instruccion de lectura
        instruccion = servicio.begin_analyze_document("prebuilt-read", archivo)

        # Ejecutamos la instruccion para leer
        resultado = instruccion.result()

    # Acumulador del contenido del archivo
    contenido = ""

    # Iteramos cada página leida
    for pagina in resultado.pages:

        # Iteramos cada linea para cada página
        for linea in pagina.lines:

            # Acumulamos el contenido
            contenido = contenido + linea.content + "\n"

    return contenido


# Obtiene los chunks desde un texto leído
def obtenerChunks(contenido: str = ""):
    # Creamos el documento con el texto que hemos extraido
    documento: list[Document] = [Document(page_content=contenido)]

    # Definimos cómo se crearán los chunks del texto
    cortadorDeTexto = CharacterTextSplitter(
        separator="\n",  # Enter
        chunk_size=1000,  # Tamaño de cada fragmento
        chunk_overlap=100,  # Superposición entre fragmentos
    )

    # Creamos los chunks
    chunks = cortadorDeTexto.split_documents(documento)

    # Información del documento que se almacena
    chunksConIdentificadores = []

    # Iteramos los chunks para darle la estructura
    for chunk in chunks:

        # Definimos la estructura del chunk que insertaremos con su identificador
        estructuraDeChunk = {"id": str(uuid.uuid4()), "content": chunk.page_content}

        # Lo agregamos al array
        chunksConIdentificadores.append(estructuraDeChunk)

    return chunksConIdentificadores


# Carga un archivo en una base de conocimiento
def cargarArchivo(rutaDeArchivo=None, nombreDeBaseDeConocimiento: str = ""):
    # Leemos el contenido del archivo
    contenido = leerContenidoDeDocumento(rutaDeArchivo)

    # Creamos los chunks
    chunks = obtenerChunks(contenido)

    # Nos conectamos a la base de conocimiento
    baseDeConocimiento = SearchClient(
        f"https://{key.require("CONF_AZURE_SEARCH_SERVICE_NAME")}.search.windows.net",
        nombreDeBaseDeConocimiento,
        AzureKeyCredential(key.require("CONF_AZURE_SEARCH_KEY")),
    )

    # Insertamos los chunks en la base de conocimiento
    resultadosDeInserciones = baseDeConocimiento.upload_documents(chunks)

    return resultadosDeInserciones


# Sincroniza los documentos de una ruta a una base de conocimiento
def sincronizarBaseDeConocimiento(
    carpeta=None, nombreDeBaseDeConocimiento:str="", tiempoDeEspera: int = 5
):
    archivos_procesados = set()  # Guardamos nombres de archivos ya procesados

    while True:
        print("Ejecutando sincronización...")

        listaDeArchivos = obtenerArchivos(ruta=carpeta)

        if len(listaDeArchivos) >= 1:
            for archivo in listaDeArchivos:
                nombre_archivo = os.path.basename(archivo)

                # Saltamos si ya fue procesado
                if nombre_archivo in archivos_procesados:
                    continue

                print(f"Cargando archivo: {archivo}")

                try:
                    # Si no es Excel, sigue el flujo normal
                    resultadosDeInserciones = cargarArchivo(
                        rutaDeArchivo=archivo,
                        nombreDeBaseDeConocimiento=nombreDeBaseDeConocimiento,
                    )
                    os.remove(archivo)
                    print("Archivo procesado y eliminado correctamente.")

                except Exception as e:
                    print(f"Ocurrió un error al sincronizar: {e}")
                    if carpeta:
                        carpetaDeErrores: str = os.path.join(
                            carpeta, "errores/", str(uuid.uuid4()) + "/"
                        )
                    print(f"Moviendo archivo a carpeta de errores: {carpetaDeErrores}")
                    os.makedirs(carpetaDeErrores, exist_ok=True)
                    shutil.move(archivo, carpetaDeErrores)

        time.sleep(tiempoDeEspera)
