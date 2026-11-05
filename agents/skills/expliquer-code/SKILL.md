---
name: expliquer-code
description: Lit git diff, résume les modifications en exactement 5 lignes, puis génère un diagramme de séquence et un flowchart Mermaid.
---

1. Exécute `git diff` (ou `git diff HEAD~1` si le dernier commit vient d'être posé) pour observer les changements récents.
2. Rédige un résumé synthétique du travail réalisé en **exactement 5 lignes concises**, mettant en valeur les modifications clés et leur impact.
3. Génère un **diagramme de séquence Mermaid** (`mermaid sequenceDiagram`) illustrant les interactions entre l'utilisateur, l'interface Web (Flask), le moteur de règles métier (`regles.py`) et la base de données SQLite.
4. Génère un **diagramme d'activité / flowchart Mermaid** (`mermaid flowchart TD`) détaillant le flux logique d'exécution, les embranchements conditionnels (succès, rejets métier, gestion d'erreurs) et la persistance des données.
5. Présente le tout dans un format markdown élégant et directement lisible.
