from django.urls import path

from . import views

app_name = "recyclable"
urlpatterns = [
    path('', views.index, name='index'),
    path('barcode', views.barcode, name='barcode'),
    path('container', views.container, name='container'),
    path('num_images', views.num_images, name='num_images'),
    path('image', views.image, name='image'),
    path('classifiers', views.classifiers, name='classifiers'),
    path('download_size_classifier', views.download_size_classifier, name='download_size_classifier'),
    path('download_deposit_classifier', views.download_deposit_classifier, name='download_deposit_classifier'),
    path('production_images/', views.production_images, name='production_images'),
    path('production_images/grid/', views.production_image_grid, name='production_image_grid'),
    path('api/containers/', views.api_containers, name='api_containers'),
]
