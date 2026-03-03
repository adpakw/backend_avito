import pytest
import pytest_asyncio

from app.clients.postgres import get_pg_connection
from app.errors import AdvertisementNotFoundError, SellerNotFoundError
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.sellers import SellerRepository


@pytest_asyncio.fixture
async def seller_repository():
    return SellerRepository()


@pytest_asyncio.fixture
async def advertisement_repository():
    return AdvertisementRepository()


async def setup_database():
    async with get_pg_connection() as conn:
        await conn.execute(
            "DELETE FROM advertisements WHERE id in (1001, 1002, 1003, 1004)"
        )
        await conn.execute("DELETE FROM sellers WHERE id in (101, 102, 103, 104)")

        await conn.execute(
            """
            INSERT INTO sellers (id, is_verified) VALUES 
            (101, true),
            (102, false),
            (103, true),
            (104, true)
        """
        )

        await conn.execute(
            """
            INSERT INTO advertisements (seller_id, id, name, description, category, images_qty, is_closed) VALUES 
            (101, 1001, 'Тестовый товар 1', 'Описание тестового товара 1', 1, 3, false),
            (102, 1002, 'Тестовый товар 2', 'Описание тестового товара 2', 2, 5, false),
            (103, 1003, 'Тестовый товар 3', 'Описание тестового товара 3', 3, 2, false),
            (104, 1004, 'Закрытый товар', 'Описание закрытого товара', 4, 1, true)
        """
        )


async def teardown_database():
    async with get_pg_connection() as conn:
        await conn.execute(
            "DELETE FROM advertisements WHERE id in (1001, 1002, 1003, 1004, 2001)"
        )
        await conn.execute("DELETE FROM sellers WHERE id in (101, 102, 103, 104, 201)")


class TestSellerRepository:
    @pytest.mark.asyncio
    async def test_get_seller(self, seller_repository: SellerRepository):
        await setup_database()
        seller = await seller_repository.get(id=101)

        assert seller.id == 101
        assert seller.is_verified == True
        await teardown_database()

    @pytest.mark.asyncio
    async def test_get_many_sellers(self, seller_repository: SellerRepository):
        await setup_database()
        sellers = await seller_repository.get_many()

        test_sellers = [s for s in sellers if s.id >= 100]

        ids = [seller.id for seller in test_sellers]
        list_is_verified = [seller.is_verified for seller in test_sellers]

        assert ids == [101, 102, 103, 104]
        assert list_is_verified == [True, False, True, True]
        await teardown_database()

    @pytest.mark.asyncio
    async def test_create_seller(self, seller_repository: SellerRepository):
        await setup_database()
        seller = await seller_repository.create(201, True)

        assert seller.id == 201
        assert seller.is_verified == True

        created_seller = await seller_repository.get(id=201)
        assert created_seller.id == 201
        assert created_seller.is_verified == True
        await teardown_database()

    @pytest.mark.asyncio
    async def test_update_seller(self, seller_repository: SellerRepository):
        await setup_database()
        seller = await seller_repository.update(101, is_verified=False)

        assert seller.id == 101
        assert seller.is_verified == False

        updated_seller = await seller_repository.get(id=101)
        assert updated_seller.is_verified == False
        await teardown_database()

    @pytest.mark.asyncio
    async def test_delete_seller(self, seller_repository: SellerRepository):
        await setup_database()
        seller = await seller_repository.delete(103)

        assert seller.id == 103
        assert seller.is_verified == True

        with pytest.raises(SellerNotFoundError):
            await seller_repository.get(id=103)
        await teardown_database()


class TestAdvertisementRepository:
    @pytest.mark.asyncio
    async def test_get_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()
        advertisement = await advertisement_repository.get(item_id=1002)

        assert advertisement.seller_id == 102
        assert advertisement.is_verified_seller == False
        assert advertisement.item_id == 1002
        assert advertisement.name == "Тестовый товар 2"
        assert advertisement.description == "Описание тестового товара 2"
        assert advertisement.category == 2
        assert advertisement.images_qty == 5
        assert advertisement.is_closed == False
        await teardown_database()

    @pytest.mark.asyncio
    async def test_create_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()
        advertisement = await advertisement_repository.create(
            101, 2001, "Новый тестовый товар", "Описание нового товара", 4, 7
        )

        assert advertisement.seller_id == 101
        assert advertisement.id == 2001
        assert advertisement.name == "Новый тестовый товар"
        assert advertisement.description == "Описание нового товара"
        assert advertisement.category == 4
        assert advertisement.images_qty == 7
        assert advertisement.is_closed == False

        created_ad = await advertisement_repository.get(item_id=2001)
        assert created_ad.name == "Новый тестовый товар"
        await teardown_database()

    @pytest.mark.asyncio
    async def test_create_closed_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()
        advertisement = await advertisement_repository.create(
            101, 2001, "Закрытый товар", "Описание", 4, 7, is_closed=True
        )

        assert advertisement.id == 2001
        assert advertisement.is_closed == True
        await teardown_database()

    @pytest.mark.asyncio
    async def test_close_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()

        ad_before = await advertisement_repository.get(item_id=1001)

        closed_ad = await advertisement_repository.close(1001)

        assert closed_ad.id == 1001
        assert closed_ad.is_closed == True

        ad_after = await advertisement_repository.get(item_id=1001)

        assert closed_ad.id == 1001
        assert closed_ad.is_closed == True
        await teardown_database()

    @pytest.mark.asyncio
    async def test_update_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()
        advertisement = await advertisement_repository.update(
            1002,
            description="Новое описание после обновления",
            images_qty=10,
            category=5,
        )

        assert advertisement.seller_id == 102
        assert advertisement.id == 1002
        assert advertisement.name == "Тестовый товар 2"
        assert advertisement.description == "Новое описание после обновления"
        assert advertisement.category == 5
        assert advertisement.images_qty == 10
        assert advertisement.is_closed == False
        await teardown_database()

    @pytest.mark.asyncio
    async def test_delete_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        await setup_database()
        advertisement = await advertisement_repository.delete(1003)

        assert advertisement.seller_id == 103
        assert advertisement.id == 1003
        assert advertisement.name == "Тестовый товар 3"
        assert advertisement.description == "Описание тестового товара 3"
        assert advertisement.category == 3
        assert advertisement.images_qty == 2

        with pytest.raises(AdvertisementNotFoundError):
            await advertisement_repository.get(item_id=1003)
        await teardown_database()
