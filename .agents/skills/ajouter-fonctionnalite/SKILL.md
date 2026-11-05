---
name: ajouter-fonctionnalite
description: Ajoute une fonctionnalité pas à pas en respectant le TDD, le découplage des règles métier et les tests automatisés avec pytest.
---

1. Comprendre la demande et identifier les données impactées dans le modèle.
2. Isoler les règles de validation métier pures dans `regles.py` (sans dépendance à Flask, Streamlit ou SQLite).
3. Rédiger les tests unitaires correspondants dans `test_regles.py` (cas nominaux, cas aux limites, rejets explicites).
4. Implémenter ou mettre à jour les routes et templates dans `app.py`.
5. Rédiger les tests d'intégration dans `test_app.py` en s'assurant que l'isolation de la base de données est respectée (aucune écriture dans `data.db`).
6. Lancer `pytest` et vérifier que tous les tests passent avec succès.
7. Ne jamais exécuter de git commit ou git push sans l'accord explicite et préalable de l'utilisateur.
