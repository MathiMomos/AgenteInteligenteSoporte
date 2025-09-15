# src/agente/agente_creacion.py
from __future__ import annotations

import json
from enum import Enum
from typing import List, Optional

from langchain.tools import tool
from sqlalchemy.orm import Session

from src.util import util_schemas as sch, util_formatear_conversacion
from src.util.util_memory import memory
from src.crud import crud_tickets
from src.util import util_base_de_datos as db

# =============== Configuración ===============

class TipoTicket(str, Enum):
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"

CONFIRM_WORDS = {
    "si", "sí", "ok", "okay", "dale", "ya", "listo",
    "de acuerdo", "vale", "sip", "claro", "correcto"
}

_agente_creacion_callable = None  # se inyecta en runtime


# =============== Helpers ===============

def _clean_text(text: str) -> str:
    t = (text or "").strip()
    return " ".join(t.split())

def _is_confirmation(text: str) -> bool:
    t = _clean_text(text).lower()
    return t in CONFIRM_WORDS or len(t) <= 3

def _pick_subject_from_conversation(conv: List[dict]) -> Optional[str]:
    """Último mensaje del usuario que no sea simple confirmación y tenga algo de contexto."""
    for msg in reversed(conv):
        if msg.get("role") == "user":
            content = _clean_text(msg.get("content", ""))
            if not _is_confirmation(content) and len(content) >= 6:
                return content
    return None

def _infer_level_from_text(text: str) -> str:
    """Heurística simple de nivel: bajo / medio / alto."""
    t = (text or "").lower()
    urgent = any(k in t for k in [
        "urgente", "inmediato", "crítico", "critico",
        "caído", "caida", "servicio caido", "api rota",
        "producción", "produccion", "no puedo entrar", "no funciona"
    ])
    high = any(k in t for k in ["error", "falla", "bloqueado", "no carga", "muy lento"])
    low  = any(k in t for k in ["consulta", "pregunta", "duda", "información", "informacion"])
    if urgent: return "alto"
    if high:   return "medio"
    if low:    return "bajo"
    return "medio"

def _build_ticket_detail_card(db_session: Session, ticket: db.Ticket) -> dict:
    """Arma el dict que el front renderiza como tarjeta (con Empresa y Servicio)."""
    # Usuario (colaborador -> external) y cliente
    external = None
    cliente = None
    if ticket.id_colaborador:
        col = db_session.query(db.Colaborador).filter(
            db.Colaborador.id_colaborador == ticket.id_colaborador
        ).first()
        if col:
            external = db_session.query(db.External).filter(
                db.External.id_persona == col.id_persona
            ).first()
            cliente = db_session.query(db.Cliente).filter(
                db.Cliente.id_cliente == col.id_cliente
            ).first()

    # Servicio (cliente_servicio -> servicio)
    servicio = None
    cs = db_session.query(db.ClienteServicio).filter(
        db.ClienteServicio.id_cliente_servicio == ticket.id_cliente_servicio
    ).first()
    if cs:
        servicio = db_session.query(db.Servicio).filter(
            db.Servicio.id_servicio == cs.id_servicio
        ).first()

    # Analista (opcional)
    analista_nombre = "-"
    if getattr(ticket, "id_analista", None):
        analista = db_session.query(db.Analista).filter(
            db.Analista.id_analista == ticket.id_analista
        ).first()
        if analista:
            ext_an = db_session.query(db.External).filter(
                db.External.id_persona == analista.id_persona
            ).first()
            if ext_an:
                analista_nombre = ext_an.nombre

    # Fecha
    fecha = "-"
    if getattr(ticket, "created_at", None):
        try:
            fecha = ticket.created_at.strftime("%d/%m/%Y")
        except Exception:
            pass

    # Mapear estado BD -> etiqueta de UI
    raw = (ticket.estado or "").lower().strip()
    if raw in ("aceptado", "abierto", "en proceso", "en progreso"):
        ui = "Abierto"
    elif raw in ("en atención", "en atencion"):
        ui = "En Atención"
    elif raw in ("cerrado", "finalizado"):
        ui = "Cerrado"
    elif raw in ("rechazado", "cancelado", "anulado"):
        ui = "Rechazado"
    else:
        ui = ticket.estado or "-"

    return {
        "id": f"#{ticket.id_ticket}",
        "subject": ticket.asunto or "-",         # <-- SIEMPRE lo persistido
        "type": ticket.tipo or "-",
        "user": getattr(external, "nombre", "-"),
        "company": getattr(cliente, "nombre", "-"),
        "service": getattr(servicio, "nombre", "-"),
        "analyst": analista_nombre,
        "status": ui,
        "date": fecha,
    }


# =============== Agente de creación ===============

def get_agente_creacion_callable(db_session: Session, user_info: sch.TokenData, thread_id: str):
    """Devuelve un callable para crear tickets con contexto de DB, usuario y conversación."""
    def _crear_ticket(asunto: str, tipo: TipoTicket) -> str:
        try:
            # 1) Recuperar conversación (para asunto inteligente y guardar histórico)
            state = memory.get({"configurable": {"thread_id": thread_id}})
            messages = state["channel_values"]["messages"] if state else []
            conversation: List[dict] = util_formatear_conversacion.format_conversation(messages)

            # 2) Asunto inteligente SOLO si lo que llega es confirmación o muy corto
            provided = _clean_text(asunto or "")
            if _is_confirmation(provided) or len(provided) < 6:
                inferred = _pick_subject_from_conversation(conversation)
                final_subject = inferred or provided or "Ticket de soporte"
            else:
                final_subject = provided

            # 3) Inferir nivel desde el contexto
            sample = final_subject + " || " + " ".join(
                m["content"] for m in conversation[-5:] if m.get("role") == "user"
            )
            nivel = _infer_level_from_text(sample)

            # 4) Crear ticket (con nivel)
            ticket = crud_tickets.create_ticket_db(
                db_session=db_session,
                asunto=final_subject,
                tipo=tipo.value,
                user_info=user_info,
                nivel=nivel,  # <-- añadido
            )

            # 5) Guardar conversación en DB
            crud_tickets.save_conversation_db(
                db_session=db_session,
                ticket_id=ticket.id_ticket,
                conversation=conversation,
            )

            # 6) Armar tarjeta SIEMPRE desde la BD + serializar a JSON estricto
            card_dict = _build_ticket_detail_card(db_session, ticket)
            card_json = json.dumps(card_dict, ensure_ascii=False)

            # 7) Mensaje + tarjeta
            texto = (
                f"He generado el ticket **#{ticket.id_ticket}** con su solicitud. "
                "Nuestro equipo de soporte se pondrá en contacto con usted a través de su correo. "
                "A partir de ahora, la atención continuará por ese medio. Gracias por su paciencia. ✨"
            )
            texto += f"\n\n<card type=\"ticket_detail\">{card_json}</card>"

            return texto

        except Exception as e:
            print(f"[crear_ticket] Error: {e}")
            return "Lo siento, ocurrió un error inesperado al intentar crear su ticket."

    return _crear_ticket


@tool
def crear_ticket(asunto: str, tipo: TipoTicket) -> str:
    """
    Usa esta herramienta para crear un nuevo ticket de soporte.
    Debe inicializarse previamente con `get_agente_creacion_callable`.
    """
    if _agente_creacion_callable is None:
        return "El agente de creación no fue inicializado con contexto."
    return _agente_creacion_callable(asunto, tipo)
