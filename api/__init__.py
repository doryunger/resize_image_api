from celery import Celery

def make_celery(app_name =__name__):
    return Celery(app_name,broker='amqp://localhost//',backend='amqp')
celery=make_celery()