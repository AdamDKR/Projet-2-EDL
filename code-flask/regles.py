import re
from datetime import date, datetime, timedelta
from typing import Any, Optional


def valider_format_heure(h: str) -> bool:
    """Vérifie que la chaîne correspond strictement au format HH:MM valide (00:00 à 23:59)."""
    if not isinstance(h, str) or not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", h):
        return False
    try:
        datetime.strptime(h, "%H:%M")
        return True
    except ValueError:
        return False


def valider_format_date(d: str) -> bool:
    """Vérifie que la chaîne correspond strictement au format YYYY-MM-DD valide."""
    if not isinstance(d, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _heure_en_minutes(h: str) -> int:
    """Convertit une heure HH:MM en nombre de minutes depuis minuit."""
    parties = h.split(":")
    return int(parties[0]) * 60 + int(parties[1])


def valider_horaires_salle(ouverture: str, fermeture: str) -> tuple[bool, Optional[str]]:
    """Valide les horaires d'ouverture d'une salle (ouverture < fermeture)."""
    if not valider_format_heure(ouverture) or not valider_format_heure(fermeture):
        return False, "Format d'heure d'ouverture ou de fermeture invalide (attendu HH:MM)"
    if _heure_en_minutes(ouverture) >= _heure_en_minutes(fermeture):
        return False, "L'heure d'ouverture doit être strictement antérieure à l'heure de fermeture"
    return True, None


def valider_creneau(
    debut: str,
    fin: str,
    ouverture: str = "08:00",
    fermeture: str = "20:00",
) -> tuple[bool, Optional[str]]:
    """
    Valide les règles temporelles d'un créneau :
    - Format HH:MM pour début et fin
    - Format HH:MM pour ouverture et fermeture
    - Heure de début < heure de fin
    - Respect des horaires d'ouverture et de fermeture
    - Durée entre 30 minutes et 4 heures (240 minutes)
    """
    if not valider_format_heure(debut) or not valider_format_heure(fin):
        return False, "Format d'heure invalide (attendu HH:MM)"

    if not valider_format_heure(ouverture) or not valider_format_heure(fermeture):
        return False, "Format d'heure d'ouverture ou de fermeture invalide (attendu HH:MM)"

    m_deb = _heure_en_minutes(debut)
    m_fin = _heure_en_minutes(fin)
    m_ouv = _heure_en_minutes(ouverture)
    m_fer = _heure_en_minutes(fermeture)

    if m_deb >= m_fin:
        return False, "L'heure de début doit être antérieure à l'heure de fin"

    if m_deb < m_ouv:
        return False, f"Refusée : avant l'ouverture ({ouverture})"

    if m_fin > m_fer:
        return False, f"Refusée : après la fermeture ({fermeture})"

    duree_minutes = m_fin - m_deb
    if duree_minutes < 30:
        return False, "Refusée : durée inférieure à 30 minutes"
    if duree_minutes > 240:
        return False, "Refusée : durée supérieure à 4 heures"

    return True, None


def valider_capacite(participants: Any, capacite_salle: int) -> tuple[bool, Optional[str]]:
    """
    Valide le nombre de participants :
    - Doit être un entier > 0
    - Ne doit pas dépasser la capacité de la salle
    """
    try:
        nb = int(participants)
    except (ValueError, TypeError):
        return False, "Le nombre de participants doit être un entier valide"

    if nb <= 0:
        return False, "Le nombre de participants doit être supérieur à 0"

    if nb > capacite_salle:
        return False, f"Refusée : capacité dépassée (maximum {capacite_salle} participants)"

    return True, None


def verifier_chevauchement(
    debut: str,
    fin: str,
    reservations_existantes: list[dict],
    exclude_id: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """
    Vérifie qu'aucun créneau ne se chevauche avec les réservations existantes.
    Règle : Deux créneaux [d1, f1] et [d2, f2] se chevauchent si d1 < f2 et f1 > d2.
    Deux créneaux contigus (ex: 10h-12h et 12h-13h) sont expressément autorisés.
    """
    try:
        m_deb = _heure_en_minutes(debut)
        m_fin = _heure_en_minutes(fin)
    except Exception:
        return False, "Format d'heure de réservation invalide"

    for r in reservations_existantes:
        if exclude_id is not None and r.get("id") == exclude_id:
            continue
        try:
            r_deb = _heure_en_minutes(r["debut"])
            r_fin = _heure_en_minutes(r["fin"])
        except Exception:
            continue
        # Chevauchement strict
        if m_deb < r_fin and m_fin > r_deb:
            personne = r.get("personne", "une autre réservation")
            return False, f"Refusée : chevauchement avec {personne} ({r['debut']} - {r['fin']})"

    return True, None


def calculer_semaine(date_ref: str | date) -> tuple[date, date]:
    """
    Calcule le lundi et le dimanche de la semaine englobant la date de référence.
    """
    if isinstance(date_ref, str):
        if not valider_format_date(date_ref):
            raise ValueError("date_ref doit être une chaîne au format YYYY-MM-DD")
        d = datetime.strptime(date_ref, "%Y-%m-%d").date()
    elif isinstance(date_ref, date):
        d = date_ref
    else:
        raise TypeError("date_ref doit être une chaîne (YYYY-MM-DD) ou un objet date")

    lundi = d - timedelta(days=d.weekday())
    dimanche = lundi + timedelta(days=6)
    return lundi, dimanche
