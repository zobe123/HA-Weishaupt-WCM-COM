"""Base entity for Weishaupt WCM-COM integration."""

import logging

_LOGGER = logging.getLogger(__name__)

class WeishauptBaseEntity:
    """Basisklasse für Weishaupt-Entitäten."""

    def __init__(self, api):
        """Initialisierung der Basisklasse."""
        self._api = api

    @property
    def api(self):
        """Gibt die API-Instanz zurück."""
        return self._api

    # Diese Methode sollte entfernt oder als abstrakte Methode deklariert werden,
    # da sie in den abgeleiteten Klassen überschrieben wird
    async def async_update(self):
        """Aktualisiert die Zustandsdaten der Entität."""
        _LOGGER.debug("Updating entity")
        await self.hass.async_add_executor_job(self._api.update)
