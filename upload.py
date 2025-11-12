import src.util.util_subida as upload
upload.sincronizarBaseDeConocimiento(
    carpeta = "D:/Repos/CiroChatbot/src/archivos", # Cambiar la ruta en el archivo .env para que apunte a la carpeta correcta
    nombreDeBaseDeConocimiento = "test", #
    tiempoDeEspera = 5
)