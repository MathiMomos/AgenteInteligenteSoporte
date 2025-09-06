def obtener_prompt(request_data):
    prompt = request_data.get("prompt")
    if not prompt:
        raise ValueError("No se proporcionó un prompt")
    return prompt