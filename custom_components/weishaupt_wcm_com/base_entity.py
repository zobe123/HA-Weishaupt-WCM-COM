from homeassistant.helpers.entity import Entity

class WeishauptBaseEntity(Entity):
    """Base entity for Weishaupt integration."""
    
    def __init__(self, api):
        """Initialize the entity."""
        self._api = api
        self._attr_has_entity_name = True
