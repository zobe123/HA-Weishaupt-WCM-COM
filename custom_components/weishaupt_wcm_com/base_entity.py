from homeassistant.helpers.update_coordinator import CoordinatorEntity

class WeishauptBaseEntity(CoordinatorEntity):
    """Base entity for Weishaupt integration."""
    
    def __init__(self, api):
        """Initialize the entity."""
        super().__init__(api)
        self._api = api
        self._attr_has_entity_name = True
