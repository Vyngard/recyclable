from django.contrib import admin
from .models import Container, Image

admin.site.register(Container)


class ImageAdmin(admin.ModelAdmin):
    exclude = ['image_sequence_number']
    model = Image
    readonly_fields = ('image', )


admin.site.register(Image, ImageAdmin)
