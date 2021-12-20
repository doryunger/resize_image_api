from api import celery
from api.app_creation import create_app
from api.utils import init_celery

app = create_app()
init_celery(celery, app)
