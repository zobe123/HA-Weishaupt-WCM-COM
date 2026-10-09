"""Base entity for Weishaupt WCM-COM integration."""

class WeishauptBaseEntity:
    """Basisklasse für Weishaupt-Entitäten."""

    def __init__(self, api):
        """Initialisierung der Basisklasse."""
        self._api = api

    @property
    def api(self):
        """Gibt die API-Instanz zurück."""
        return self._api
