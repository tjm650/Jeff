.PHONY: frontend

ngrok:
	ngrok http 8000



frontend:
	cd frontend && npm run dev


runserver:
	cd backend && python start_with_ngrok.py your_ngrok_auth_token_here

createsuperuser:
	python manage.py createsuperuser
	python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'password123')"


GAK:
	python manage.py create_api_key --name "Frontend API Key" 