cd %~dp0server
cmd /k "..\..\venv\Scripts\activate && python manage.py runserver 8080"
