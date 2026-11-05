"""Règles métier pour la réservation de salles.
Ce module ne dépend d'aucun framework web (Flask, Streamlit, etc.).
"""


class RegleReservationException(ValueError):
    """Exception levée lorsqu'une règle métier de réservation est enfreinte."""
    pass


def to_minutes(heure_str: str) -> int:
    """Convertit une heure au format 'HH:MM' en nombre de minutes depuis minuit."""
    try:
        parties = heure_str.split(":")
        if len(parties) != 2:
            raise ValueError
        h, m = int(parties[0]), int(parties[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise RegleReservationException(f"Format d'heure invalide : '{heure_str}' (attendu HH:MM)")


def valider_horaires_et_duree(debut: str, fin: str):
    """Vérifie les horaires et la durée de la réservation :
    - Début avant fin
    - Entre 8 h (480 min) et 20 h (1200 min)
    - Durée entre 30 min et 4 h (240 min)
    """
    min_debut = to_minutes(debut)
    min_fin = to_minutes(fin)

    if min_fin <= min_debut:
        raise RegleReservationException("L'heure de fin doit être postérieure à l'heure de début.")

    # Une réservation a lieu entre 8 h et 20 h
    if min_debut < 8 * 60:
        raise RegleReservationException("Une réservation ne peut pas débuter avant 8 h.")
    if min_fin > 20 * 60:
        raise RegleReservationException("Une réservation doit se terminer au plus tard à 20 h.")

    # Dure de 30 min à 4 h
    duree = min_fin - min_debut
    if duree < 30:
        raise RegleReservationException("Une réservation doit durer au moins 30 minutes.")
    if duree > 240:
        raise RegleReservationException("Une réservation ne peut pas dépasser 4 heures.")


def valider_capacite(participants: int, capacite_salle: int):
    """Vérifie que le nombre de participants ne dépasse pas la capacité de la salle."""
    if participants <= 0:
        raise RegleReservationException("Le nombre de participants doit être supérieur à 0.")
    if participants > capacite_salle:
        raise RegleReservationException(
            f"Le nombre de participants ({participants}) dépasse la capacité de la salle ({capacite_salle})."
        )


def valider_non_chevauchement(debut: str, fin: str, reservations_existantes: list):
    """Vérifie que deux réservations d'une même salle ne se chevauchent pas.
    Finir à 12 h et commencer à 12 h est autorisé.
    """
    min_debut = to_minutes(debut)
    min_fin = to_minutes(fin)

    for r in reservations_existantes:
        r_debut = to_minutes(r["debut"])
        r_fin = to_minutes(r["fin"])

        # Deux créneaux [debut, fin[ et [r_debut, r_fin[ se chevauchent si :
        # min_debut < r_fin et min_fin > r_debut
        if min_debut < r_fin and min_fin > r_debut:
            raise RegleReservationException(
                f"Chevauchement détecté : la salle est déjà occupée de {r['debut']} à {r['fin']}."
            )


def valider_reservation(
    personne: str,
    capacite_salle: int,
    debut: str,
    fin: str,
    participants: int,
    reservations_existantes: list,
):
    """Valide l'ensemble des règles pour une réservation."""
    if not personne or not personne.strip():
        raise RegleReservationException("Le nom de la personne est obligatoire.")

    valider_horaires_et_duree(debut, fin)
    valider_capacite(participants, capacite_salle)
    valider_non_chevauchement(debut, fin, reservations_existantes)

