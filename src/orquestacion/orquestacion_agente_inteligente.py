# orquestacion_agente_inteligente.py
from src.agente import agente_principal

def main():
    print("=== Asistente de Soporte ===")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_input = input("Usuario: ").strip()
        if not user_input:
            continue

        if user_input.lower() in ["salir", "exit", "quit"]:
            print("Saliendo...")
            break

        try:
            respuesta = agente_principal.handle_query(user_input)
            print(f"Asistente: {respuesta}")
        except Exception as e:
            print(f"[Error] {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
