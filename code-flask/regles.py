"""Règles métier pour la réservation de salles.
Ce module ne dépend d'aucun framework web (Flask, Streamlit, etc.).
"""

from datetime import date, datetime, timedelta

JOURS_SEMAINE = [
    "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"
]

TYPES_LOCAUX = [
    "Salle de cours",
    "Amphithéâtre",
    "Salle de réunion",
    "Laboratoire",
    "Salle informatique",
]


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


def valider_salle(nom: str, capacite: int, type_local: str = "Salle de cours"):
    """Vérifie la validité des informations d'une salle."""
    if not nom or not nom.strip():
        raise RegleReservationException("Le nom de la salle est obligatoire.")
    if capacite <= 0:
        raise RegleReservationException("La capacité de la salle doit être supérieure à 0.")
    if type_local not in TYPES_LOCAUX:
        raise RegleReservationException(f"Type de local invalide : '{type_local}'.")


def valider_modification_capacite(nouvelle_capacite: int, max_participants_existants: int):
    """Vérifie qu'une réduction de capacité ne rend pas invalides des réservations existantes."""
    if max_participants_existants > 0 and nouvelle_capacite < max_participants_existants:
        raise RegleReservationException(
            f"Impossible de réduire la capacité à {nouvelle_capacite} : "
            f"une réservation compte déjà {max_participants_existants} participants."
        )


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


def _trouver_chevauchement(debut: str, fin: str, reservations: list):
    """Retourne la première réservation qui chevauche [debut, fin[, ou None.
    Finir à 12 h et commencer à 12 h est autorisé.
    """
    min_debut = to_minutes(debut)
    min_fin = to_minutes(fin)

    for r in reservations:
        r_debut = to_minutes(r["debut"])
        r_fin = to_minutes(r["fin"])

        # Deux créneaux [debut, fin[ et [r_debut, r_fin[ se chevauchent si :
        # min_debut < r_fin et min_fin > r_debut
        if min_debut < r_fin and min_fin > r_debut:
            return r
    return None


def valider_non_chevauchement(debut: str, fin: str, reservations_existantes: list):
    """Vérifie que deux réservations d'une même salle ne se chevauchent pas.
    Finir à 12 h et commencer à 12 h est autorisé.
    """
    conflit = _trouver_chevauchement(debut, fin, reservations_existantes)
    if conflit is not None:
        raise RegleReservationException(
            f"Chevauchement détecté : la salle est déjà occupée de {conflit['debut']} à {conflit['fin']}."
        )


def valider_non_chevauchement_personne(
    personne: str, debut: str, fin: str, reservations_personne: list
):
    """Vérifie qu'une personne n'a pas deux réservations qui se chevauchent."""
    conflit = _trouver_chevauchement(debut, fin, reservations_personne)
    if conflit is not None:
        raise RegleReservationException(
            f"Chevauchement détecté : {personne} a déjà une réservation de {conflit['debut']} à {conflit['fin']}."
        )


def valider_reservation(
    personne: str,
    capacite_salle: int,
    debut: str,
    fin: str,
    participants: int,
    reservations_existantes: list,
    reservations_personne: list | None = None,
):
    """Valide l'ensemble des règles pour une réservation."""
    if not personne or not personne.strip():
        raise RegleReservationException("Le nom de la personne est obligatoire.")

    valider_horaires_et_duree(debut, fin)
    valider_capacite(participants, capacite_salle)
    valider_non_chevauchement(debut, fin, reservations_existantes)
    if reservations_personne:
        valider_non_chevauchement_personne(personne, debut, fin, reservations_personne)


def generer_dates_hebdomadaires(date_debut: str, nb_semaines: int) -> list[str]:
    """Génère la liste des dates hebdomadaires à partir de date_debut sur nb_semaines semaines."""
    if nb_semaines < 1 or nb_semaines > 52:
        raise RegleReservationException("Le nombre de semaines doit être compris entre 1 et 52.")
    try:
        d = datetime.strptime(date_debut, "%Y-%m-%d").date()
    except ValueError:
        raise RegleReservationException(f"Format de date invalide : '{date_debut}' (attendu AAAA-MM-JJ).")
    return [(d + timedelta(weeks=i)).isoformat() for i in range(nb_semaines)]


def calculer_semaine(date_ref: str | None = None):
    """Calcule les 7 jours de la semaine (du lundi au dimanche) contenant la date de référence.
    Règle métier : La semaine va du lundi au dimanche.
    """
    if date_ref:
        try:
            d = datetime.strptime(date_ref, "%Y-%m-%d").date()
        except ValueError:
            d = date(2026, 11, 9)
    else:
        d = date(2026, 11, 9)

    # 0 = Lundi, 6 = Dimanche
    lundi = d - timedelta(days=d.weekday())
    dimanche = lundi + timedelta(days=6)

    jours = []
    for i in range(7):
        jour_date = lundi + timedelta(days=i)
        jours.append({
            "date": jour_date.isoformat(),
            "nom_jour": JOURS_SEMAINE[i],
            "label": f"{JOURS_SEMAINE[i]} {jour_date.strftime('%d/%m')}",
        })

    date_prec = (lundi - timedelta(days=7)).isoformat()
    date_suiv = (lundi + timedelta(days=7)).isoformat()

    return {
        "lundi": lundi.isoformat(),
        "dimanche": dimanche.isoformat(),
        "jours": jours,
        "date_prec": date_prec,
        "date_suiv": date_suiv,
    }
