import pytest
from app import app
from base import ouvrir_base
from regles import RegleReservationException, valider_reservation


def test_accueil():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "Réservation de salles" in response.text


# =====================================================================
# Tests unitaires des règles métier (Tableau 6 de l'énoncé)
# Salle S1 de capacité 20, déjà réservée le lundi de 10 h à 12 h.
# =====================================================================

RESERVATIONS_S1 = [
    {"debut": "10:00", "fin": "12:00"}
]


def test_regle_chevauchement_refuse():
    """Lundi, 11 h à 13 h -> Refusée : chevauchement."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="11:00",
            fin="13:00",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "chevauchement" in str(exc.value).lower()


def test_regle_creneau_adjacent_accepte():
    """Lundi, 12 h à 13 h -> Acceptée (finir à 12h et commencer à 12h est autorisé)."""
    valider_reservation(
        personne="Bob",
        capacite_salle=20,
        debut="12:00",
        fin="13:00",
        participants=10,
        reservations_existantes=RESERVATIONS_S1,
    )


def test_regle_creneau_adjacent_avant_accepte():
    """Lundi, 9 h à 10 h -> Acceptée (finir à 10h et commencer à 10h est autorisé)."""
    valider_reservation(
        personne="Bob",
        capacite_salle=20,
        debut="09:00",
        fin="10:00",
        participants=10,
        reservations_existantes=RESERVATIONS_S1,
    )


def test_regle_capacite_depassee_refuse():
    """Lundi, 14 h à 15 h, 25 participants -> Refusée : capacité dépassée."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="14:00",
            fin="15:00",
            participants=25,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "capacité" in str(exc.value).lower()


def test_regle_avant_8h_refuse():
    """Lundi, 7 h 30 à 9 h -> Refusée : avant 8 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="07:30",
            fin="09:00",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "8 h" in str(exc.value)


def test_regle_apres_20h_refuse():
    """Une réservation doit se terminer au plus tard à 20 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="19:00",
            fin="20:30",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "20 h" in str(exc.value)


def test_regle_moins_de_30min_refuse():
    """Mardi, 14 h à 14 h 20 -> Refusée : moins de 30 min."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="14:00",
            fin="14:20",
            participants=10,
            reservations_existantes=[],
        )
    assert "30 minutes" in str(exc.value)


def test_regle_plus_de_4h_refuse():
    """Mardi, 8 h à 13 h -> Refusée : plus de 4 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="08:00",
            fin="13:00",
            participants=10,
            reservations_existantes=[],
        )
    assert "4 heures" in str(exc.value)


# =====================================================================
# Tests d'intégration Flask (routes HTTP)
# =====================================================================

def test_route_reserver_succes_et_nettoyage():
    client = app.test_client()

    # Créneau valide le mardi 2026-11-10 de 14:00 à 15:00
    res = client.post(
        "/reservations",
        data={
            "salle_id": 1,
            "personne": "TestUserIntegration",
            "date": "2026-11-10",
            "debut": "14:00",
            "fin": "15:00",
            "participants": 5,
        },
    )
    assert res.status_code == 302

    # Vérification en base
    with ouvrir_base() as conn:
        ligne = conn.execute(
            "SELECT * FROM reservations WHERE personne = 'TestUserIntegration'"
        ).fetchone()
        assert ligne is not None
        assert ligne["salle_id"] == 1
        assert ligne["date"] == "2026-11-10"

        # Nettoyage pour idempotence
        conn.execute("DELETE FROM reservations WHERE personne = 'TestUserIntegration'")


def test_route_reserver_conflit():
    client = app.test_client()

    # La salle 1 a déjà Alice de 10:00 à 12:00 le 2026-11-09 (données de base.sql)
    res = client.post(
        "/reservations",
        data={
            "salle_id": 1,
            "personne": "ConflitUser",
            "date": "2026-11-09",
            "debut": "11:00",
            "fin": "12:30",
            "participants": 5,
        },
    )
    assert res.status_code == 400
    assert "chevauchement" in res.text.lower()
