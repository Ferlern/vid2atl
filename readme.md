### Docker

- Установить [Docker](https://www.docker.com/products/docker-desktop/)
- `git clone https://github.com/Ferlern/vid2atl.git & cd vid2atl`
- `docker-compose up -d`

### No Docker

- Установить [Python >3.9](https://www.python.org/downloads/)
- Установить [Poetry](https://www.jetbrains.com/help/pycharm/poetry.html)
- `git clone https://github.com/Ferlern/vid2atl.git & cd vid2atl`
- Установить зависимости `poetry install`
- Активировать виртуальное окружение
- Запустить сервер `uvicorn src.main:app`
