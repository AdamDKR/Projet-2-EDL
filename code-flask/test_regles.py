from datetime import date
import pytest
from regles import (
    calculer_semaine,
    valider_capacite,
    valider_creneau,
    valider_format_date,
    valider_format_heure,
    verifier_chevauchement,
)

# Réservation existante de référence selon le protocole (Tableau 6) :
# Salle S1 de capacité 20, déjà réservée le lundi de 10:00 à 12:00 par Alice.
RESERVATIONS_S1_LUNDI = [
    {
        "id": 1,
        "salle_id": 1,
        "personne": "Alice",
        "date": "2026-11-09",
        "debut": "10:00",
        "fin": "12:00",
        "participants": 12,
    }
]


def test_tableau_6_chevauchement_interdit():
    """Lundi, 11 h à 13 h -> Refusée : chevauchement"""
    valide, err = verifier_chevauchement("11:00", "13:00", RESERVATIONS_S1_LUNDI)
    assert not valide
    assert err is not None
    assert "chevauchement" in err.lower()


def test_tableau_6_contiguite_exacte_apres_autorisee():
    """Lundi, 12 h à 13 h -> Acceptée (contiguïté à droite)"""
    valide, err = verifier_chevauchement("12:00", "13:00", RESERVATIONS_S1_LUNDI)
    assert valide
    assert err is None


def test_tableau_6_contiguite_exacte_avant_autorisee():
    """Lundi, 09 h à 10 h -> Acceptée (contiguïté à gauche)"""
    valide, err = verifier_chevauchement("09:00", "10:00", RESERVATIONS_S1_LUNDI)
    assert valide
    assert err is None


def test_tableau_6_capacite_depassee():
    """Lundi, 14 h à 15 h, 25 participants pour salle capacité 20 -> Refusée : capacité dépassée"""
    valide, err = valider_capacite(25, capacite_salle=20)
    assert not valide
    assert err is not None
    assert "capacité" in err.lower()


def test_capacite_valide():
    """20 participants pour salle capacité 20 -> Acceptée"""
    valide, err = valider_capacite(20, capacite_salle=20)
    assert valide
    assert err is None

    valide, err = valider_capacite(1, capacite_salle=20)
    assert valide
    assert err is None


def test_capacite_invalide_zero_ou_negative():
    """Participants <= 0 ou non entier -> Refusée"""
    valide, err = valider_capacite(0, capacite_salle=20)
    assert not valide
    assert "supérieur à 0" in err

    valide, err = valider_capacite(-3, capacite_salle=20)
    assert not valide
    assert "supérieur à 0" in err

    valide, err = valider_capacite("abc", capacite_salle=20)
    assert not valide
    assert "entier valide" in err


def test_tableau_6_avant_ouverture():
    """Lundi, 7 h 30 à 9 h -> Refusée : avant 8 h"""
    valide, err = valider_creneau("07:30", "09:00", ouverture="08:00", fermeture="20:00")
    assert not valide
    assert err is not None
    assert "avant" in err.lower()


def test_apres_fermeture():
    """18 h 00 à 20 h 30 -> Refusée : après 20 h"""
    valide, err = valider_creneau("18:00", "20:30", ouverture="08:00", fermeture="20:00")
    assert not valide
    assert err is not None
    assert "après" in err.lower()


def test_tableau_6_duree_moins_de_30_min():
    """Mardi, 14 h à 14 h 20 (20 min) -> Refusée : moins de 30 min"""
    valide, err = valider_creneau("14:00", "14:20")
    assert not valide
    assert err is not None
    assert "inférieure à 30 minutes" in err.lower() or "30" in err


def test_duree_exacte_30_min():
    """14 h à 14 h 30 (30 min) -> Acceptée"""
    valide, err = valider_creneau("14:00", "14:30")
    assert valide
    assert err is None


def test_tableau_6_duree_plus_de_4_h():
    """Mardi, 8 h à 13 h (5 h) -> Refusée : plus de 4 h"""
    valide, err = valider_creneau("08:00", "13:00")
    assert not valide
    assert err is not None
    assert "supérieure à 4 heures" in err.lower() or "4 heures" in err


def test_duree_exacte_4_h():
    """08 h à 12 h (4 h) -> Acceptée"""
    valide, err = valider_creneau("08:00", "12:00")
    assert valide
    assert err is None


def test_heures_inverses_ou_identiques():
    """Début >= fin -> Refusée"""
    valide, err = valider_creneau("15:00", "14:00")
    assert not valide
    assert "antérieure" in err

    valide, err = valider_creneau("10:00", "10:00")
    assert not valide
    assert "antérieure" in err


def test_formats_invalides():
    assert not valider_format_heure("25:00")
    assert not valider_format_heure("10h30")
    assert not valider_format_heure(123)
    assert valider_format_heure("08:00")

    assert not valider_format_date("2026/11/09")
    assert not valider_format_date("09-11-2026")
    assert not valider_format_date(None)
    assert valider_format_date("2026-11-09")


def test_chevauchement_englobant():
    """Une réservation qui englobe entièrement une autre -> Refusée"""
    valide, err = verifier_chevauchement("09:00", "13:00", RESERVATIONS_S1_LUNDI)
    assert not valide

    """Une réservation entièrement contenue à l'intérieur d'une autre -> Refusée"""
    valide, err = verifier_chevauchement("10:30", "11:30", RESERVATIONS_S1_LUNDI)
    assert not valide


def test_chevauchement_exclusion_id():
    """Lors de la modification d'une réservation, elle ne doit pas entrer en conflit avec elle-même"""
    valide, err = verifier_chevauchement(
        "10:00", "12:00", RESERVATIONS_S1_LUNDI, exclude_id=1
    )
    assert valide
    assert err is None


def test_calcul_semaine_lundi_au_dimanche():
    """
    Le 9 novembre 2026 est un lundi.
    La semaine doit aller du lundi 2026-11-09 au dimanche 2026-11-15.
    """
    # Test avec la date du lundi
    lundi, dimanche = calculer_semaine("2026-11-09")
    assert lundi == date(2026, 11, 9)
    assert dimanche == date(2026, 11, 15)

    # Test avec le mercredi au milieu
    lundi, dimanche = calculer_semaine("2026-11-11")
    assert lundi == date(2026, 11, 9)
    assert dimanche == date(2026, 11, 15)

    # Test avec le dimanche de fin de semaine
    lundi, dimanche = calculer_semaine("2026-11-15")
    assert lundi == date(2026, 11, 9)
    assert dimanche == date(2026, 11, 15)

    # Test avec objet date
    lundi, dimanche = calculer_semaine(date(2026, 11, 13))
    assert lundi == date(2026, 11, 9)
    assert dimanche == date(2026, 11, 15)


def test_formats_heure_et_date_strictes():
    """Vérifie que les formats HH:MM et YYYY-MM-DD sont strictement respectés sans ambiguïté."""
    # Heure avec un seul chiffre pour l'heure ou les minutes
    assert not valider_format_heure("9:00")
    assert not valider_format_heure("09:5")
    assert not valider_format_heure("9:5")
    assert not valider_format_heure("24:00")
    assert not valider_format_heure("12:60")
    assert valider_format_heure("09:00")
    assert valider_format_heure("23:59")

    # Date avec un seul chiffre pour le mois ou le jour
    assert not valider_format_date("2026-1-9")
    assert not valider_format_date("2026-01-9")
    assert not valider_format_date("26-11-09")
    assert not valider_format_date("2026-02-30")
    assert valider_format_date("2026-01-09")


def test_chevauchement_numerique_pieges_lexicographiques():
    """
    Vérifie qu'un créneau 08:00-11:00 détecte bien le conflit avec 09:00-10:00,
    ce qui échouait avec une simple comparaison lexicographique de chaînes.
    """
    resas = [{"id": 1, "debut": "08:00", "fin": "11:00", "personne": "Alice"}]
    valide, err = verifier_chevauchement("09:00", "10:00", resas)
    assert not valide
    assert "chevauchement" in err.lower()

    # Début identique
    valide, err = verifier_chevauchement("08:00", "09:00", resas)
    assert not valide

    # Fin identique
    valide, err = verifier_chevauchement("10:00", "11:00", resas)
    assert not valide

    # Contiguïté exacte après
    valide, err = verifier_chevauchement("11:00", "12:00", resas)
    assert valide
    assert err is None

    # Contiguïté exacte avant
    valide, err = verifier_chevauchement("07:00", "08:00", resas)
    assert valide
    assert err is None


def test_valider_horaires_salle_comparaison_numerique():
    """Valide les plages d'ouverture avec comparaison numérique fiable."""
    from regles import valider_horaires_salle

    valide, err = valider_horaires_salle("09:00", "17:00")
    assert valide
    assert err is None

    valide, err = valider_horaires_salle("17:00", "09:00")
    assert not valide
    assert "strictement antérieure" in err

    valide, err = valider_horaires_salle("08:00", "08:00")
    assert not valide

    valide, err = valider_horaires_salle("invalide", "18:00")
    assert not valide


def test_valider_creneau_horaires_salle_invalides():
    """Valide que des horaires d'ouverture ou de fermeture invalides ne provoquent pas de crash."""
    valide, err = valider_creneau("10:00", "11:00", ouverture="invalide", fermeture="20:00")
    assert not valide
    assert "invalide" in err.lower()

