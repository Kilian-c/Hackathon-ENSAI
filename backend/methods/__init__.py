"""Méthodes enregistrées : importer ce paquet remplit le registre.

Les modules sont découverts automatiquement (`pkgutil`) : ajouter une méthode = ajouter un fichier
`backend/methods/<nom>.py` (ou un sous-paquet) avec `@register_method`, sans toucher à ce fichier.
"""

import importlib
import pkgutil

for _module in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
    importlib.import_module(_module.name)
