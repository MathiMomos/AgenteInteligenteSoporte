import src.util.util_subida as upload
upload.sincronizarBaseDeConocimiento(
    carpeta = "/home/daminin/Documents/Repositorios/AgenteInteligenteSoporte/src/archivos", # Cambiar la ruta en el archivo .env para que apunte a la carpeta correcta
    nombreDeBaseDeConocimiento = "utp", #
    tiempoDeEspera = 5
)