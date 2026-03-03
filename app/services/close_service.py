import logging
import sys

from app.errors import AdvertisementNotFoundError
from app.models.advertisement import Advertisement
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.cache import CacheRepository
from app.repositories.moderation import ModerationRepository

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")


class CloseService:
    _instance = None

    def __init__(self):
        self.ad_repo = AdvertisementRepository()
        self.moder_repo = ModerationRepository()
        self.cache_repo = CacheRepository()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def close_advertisement(self, item_id: int) -> Advertisement:
        logger.info(f"Closing advertisement item_id={item_id}")

        try:
            ad_data = await self.ad_repo.get(item_id)
        except AdvertisementNotFoundError:
            logger.error(f"Advertisement {item_id} not found")
            raise

        closed_ad = await self.ad_repo.close(item_id)
        logger.info(f"Marked advertisement {item_id} as closed in PostgreSQL")

        try:
            moderations = await self.moder_repo.get_many()
            for mod in moderations:
                if mod.item_id == item_id:
                    await self.moder_repo.delete(mod.id)
                    logger.info(
                        f"Deleted moderation task {mod.id} for item_id={item_id}"
                    )
        except Exception as e:
            logger.warning(
                f"Error deleting moderation tasks for item_id={item_id}: {str(e)}"
            )

        await self.cache_repo.delete_prediction(item_id)
        logger.info(f"Deleted cache data for item_id={item_id}")

        return closed_ad

    def get_close_service(self):
        return self


close_service_client = CloseService()


def get_close_service():
    return close_service_client.get_close_service()
