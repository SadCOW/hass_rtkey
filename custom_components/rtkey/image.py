import logging
from datetime import datetime
import json
import re
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from . import RTKeyCamerasApi, DOMAIN, _LOGGER, CONF_NAME, CONF_CAMERA_IMAGE_REFRESH_INTERVAL

async def async_setup_entry(hass, config_entry, async_add_entities):
    cameras_api = RTKeyCamerasApi(hass, config_entry)

    cameras_info = await cameras_api.get_cameras_info()

    entities = []
    for camera_info in cameras_info["data"]["items"]:
        entities.append(RTKeyCameraImageEntity(hass, config_entry, cameras_api, camera_info))
    async_add_entities(entities)

class RTKeyCameraImageEntity(ImageEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        cameras_api: RTKeyCamerasApi,
        camera_info: dict
    ) -> None:

        super().__init__(hass)

        self.hass = hass
        self.config_entry_id = config_entry.entry_id
        self.config_entry_name = config_entry.data[CONF_NAME]
        self.cameras_api = cameras_api
        self.camera_id = camera_info["id"]
        self.camera_name = self.cameras_api.get_camera_name(camera_info)
        self.entity_name = self.camera_name
        self.entity_id = DOMAIN + "." + re.sub("[^a-zA-z0-9]+", "_", self.entity_name).rstrip("_").lower()
        self.camera_image_refresh_interval = config_entry.options[CONF_CAMERA_IMAGE_REFRESH_INTERVAL]

        self._attr_unique_id = f"camera-image-{self.entity_id}"
        self._attr_name = self.entity_name

    async def async_image(self) -> bytes | None:
        res = await self.cameras_api.get_camera_image(self.camera_id)
        self.camera_image_task = asyncio.create_task(self.set_image_last_updated(self.camera_image_refresh_interval))
        return res

    async def set_image_last_updated(self, ttl: int) -> None:
        await asyncio.sleep(ttl)
        self._attr_image_last_updated = datetime.now()
        await self.hass.services.async_call("homeassistant", "update_entity", {"entity_id": self.entity_id}, blocking=False)

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, f"{self.config_entry_id}_{self.camera_id}")},
            "name": self.camera_name,
        }
