run:
	docker run -it -d --env-file .env --restart=unless-stopped --name buy_bid humantrembles/first_bot_image
stop:
	docker stop buy_bid
attach:
	docker attach buy_bid
dell:
	docker rm buy_bid

# Запускает все сервисы в фоновом режиме
up:
	docker-compose up -d --build

# Останавливает и удаляет контейнеры, сети и тома
down:
	docker-compose down

# Пересобирает образ бота и перезапускает сервисы
restart:
	docker-compose restart bot

# Показывает логи всех сервисов (или конкретного, e.g., make logs s=bot)
logs:
	docker-compose logs -f $(s)

# Показывает статус контейнеров
ps:
	docker-compose ps

# Зайти в командную строку запущенного контейнера (e.g., make shell s=bot)
shell:
	docker-compose exec $(s) /bin/bash

.PHONY: up down restart logs ps shell