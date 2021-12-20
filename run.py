from api import app_creation
import api

if __name__ == "__main__":
    app=app_creation.create_app(celery=api.celery)
    # Allowing remote clients
    #app.run(host='192.168.40.132')
    #Local machine only
    app.run('127.0.0.1')