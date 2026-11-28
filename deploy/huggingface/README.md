---
title: Crash-Test
emoji: 💥
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Réviser un théorème en cassant ses hypothèses
---

# Crash-Test

Des QCM de révision où la correction est une simulation : casser une hypothèse d'un théorème, mesurer ce qui cède, appliquer la correction. Projet du hackathon ENSAI.

Ce Space construit une seule image Docker : le moteur (FastAPI, NumPy, SciPy) sert l'interface sur `/` et l'API sur `/api`.
