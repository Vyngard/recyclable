import logging
import os
from datetime import datetime
from threading import Thread
from typing import Any
from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from recyclable.models import Container, mk_container, Image, mk_null_container
from recyclable.utils import save_image_file, upload_jpeg_base64_to_s3, BUCKET_NAME
from recyclable.views_helpers import create_size_classifier_json, create_deposit_classifier_json

def index(_) -> HttpResponse:
    return render(_, "recyclable/index.html")


@login_required
def barcode(request) -> HttpResponse:
    return render(request, "recyclable/barcode.html")

@login_required
def container(request) -> HttpResponse:
    barcode = request.POST.get('barcode', '') or request.GET.get('barcode', '')

    if barcode == '':
        return render(request, "recyclable/barcode.html", {'message': 'Barcode must be entered.'})

    try:
        c = Container.objects.get(barcode=barcode)
        message = f'A container with barcode {barcode} already exists.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    except ObjectDoesNotExist:
        c: Container = mk_null_container()
        message = ''
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    except MultipleObjectsReturned:
        return render(request, "recyclable/barcode.html",
                      {'message': "An internal error has occurred. Error Code 123"})

@login_required
def num_images(request) -> HttpResponse:
    barcode = request.POST.get('barcode', '')
    message = ''

    if barcode == '':
        message += 'Barcode must be entered.\n'
        return render(request, "recyclable/barcode.html", {'message': message})
    try:
        c = Container.objects.get(barcode=barcode)
    except ObjectDoesNotExist:
        c = mk_null_container()

    # Update fields from form data
    update_container_from_request(c, request)
    return render(request, "recyclable/num_images.html", get_container_context(c, barcode, message))


@login_required
def image(request) -> HttpResponse:
    if request.method == 'POST':
        # Check if 'frame_data_url' is in POST data to determine if it's an image capture submission
        frame_data_url = request.POST.get('frame_data_url', '')
        if frame_data_url:
            # This is a submission from image.html after capturing an image
            container_id = request.POST.get('container_id')
            barcode = request.POST.get('barcode')
            i_image = request.POST.get('i_image')
            num_images = request.POST.get('num_images')

            # Validate required fields
            if not container_id or not i_image or not num_images:
                logging.error("image() - Missing required data for image saving.")
                return HttpResponse("Error: Missing required data.", status=400)

            # Convert to integers
            try:
                container_id = int(container_id)
                i_image = int(i_image)
                num_images = int(num_images)
            except ValueError:
                logging.error(f"image() - Invalid data format - container_id: {container_id}, i_image: {i_image}, num_images: {num_images}")
                return HttpResponse("Error: Invalid data format.", status=400)

            # Reconstruct counts from POST data
            counts = {}
            counts_list = []
            for key in request.POST:
                if key.startswith('counts['):
                    name = key[7:-1]  # Extract the name
                    count = request.POST.get(key)
                    try:
                        count = int(count)
                        counts[name] = count
                        counts_list.append((name, count))
                    except ValueError:
                        logging.error(f"image() - Invalid count value for {name}: {count}")
                        return HttpResponse("Error: Invalid count value.", status=400)

            # Get container
            try:
                c = Container.objects.get(pk=container_id)
            except Container.DoesNotExist:
                logging.error(f"image() - Container with id {container_id} does not exist.")
                return HttpResponse("Error: Container does not exist.", status=400)

            # Save the image
            if frame_data_url:
                th = Thread(target=save_image, args=(frame_data_url, c), daemon=True)
                th.start()

            # Increment i_image for the next image
            i_image += 1

            # Check if all images have been captured
            if i_image > num_images:
                return render(request, 'recyclable/barcode.html', {'message': 'All images have been captured.'})
            else:
                # Determine category based on the new i_image
                total = 0
                category = 'unknown'
                for name, count in counts_list:
                    total += count
                    if i_image <= total:
                        category = name
                        break

                # Render image.html for the next image
                return render(request, "recyclable/image.html", {
                    'container_id': container_id,
                    'barcode': barcode,
                    'i_image': i_image,
                    'num_images': num_images,
                    'counts': counts,
                    'counts_list': counts_list,
                    'category': category,
                })
        else:
            # This is the initial submission from num_images.html with percentages
            container_id = request.POST.get('container_id')
            barcode = request.POST.get('barcode')
            num_images_str = request.POST.get('num_images', '0')
            message = ''
            error = False

            # Validate container_id and barcode
            if not container_id or not barcode:
                message = 'Container ID or barcode is missing.'
                return render(request, "recyclable/barcode.html", {'message': message})

            # Validate num_images
            try:
                num_images = int(num_images_str)
                if num_images <= 0:
                    message += 'Number of images must be greater than zero.\n'
                    error = True
            except ValueError:
                message += 'Invalid number of images.\n'
                error = True

            if error:
                return render(request, "recyclable/num_images.html", {
                    'container_id': container_id,
                    'barcode': barcode,
                    'message': message,
                    # Include form values to preserve user input
                })

            # Process percentage inputs
            def parse_percentage(value, field_name):
                try:
                    val = float(value)
                    if val < 0 or val > 100:
                        raise ValueError
                    return val
                except ValueError:
                    nonlocal message, error
                    message += f'Invalid percentage for {field_name}. Must be between 0 and 100.\n'
                    error = True
                    return 0.0

            # Retrieve percentages from POST data
            valid_percentage = parse_percentage(request.POST.get('valid_percentage', ''), 'Valid')
            crushed_1_percentage = parse_percentage(request.POST.get('crushed_1_percentage', ''), 'Crushed 1')
            crushed_2_percentage = parse_percentage(request.POST.get('crushed_2_percentage', ''), 'Crushed 2')
            crushed_3_percentage = parse_percentage(request.POST.get('crushed_3_percentage', ''), 'Crushed 3')
            crushed_4_percentage = parse_percentage(request.POST.get('crushed_4_percentage', ''), 'Crushed 4')
            bad_orientation_percentage = parse_percentage(request.POST.get('bad_orientation_percentage', ''), 'Bad Orientation')
            no_label_percentage = parse_percentage(request.POST.get('no_label_percentage', ''), 'No Label')

            # Validate percentages sum to 100%
            total_percentage = (valid_percentage + crushed_1_percentage + crushed_2_percentage +
                                crushed_3_percentage + crushed_4_percentage +
                                bad_orientation_percentage + no_label_percentage)
            if abs(total_percentage - 100) > 0.01:
                message += 'The percentages must add up to 100%.'
                error = True

            if error:
                return render(request, "recyclable/num_images.html", {
                    'container_id': container_id,
                    'barcode': barcode,
                    'message': message,
                    # Include form values to preserve user input
                })

            # Calculate counts based on percentages
            num_images = int(num_images_str)
            categories = [
                ('valid', valid_percentage),
                ('crushed_1', crushed_1_percentage),
                ('crushed_2', crushed_2_percentage),
                ('crushed_3', crushed_3_percentage),
                ('crushed_4', crushed_4_percentage),
                ('bad_orientation', bad_orientation_percentage),
                ('no_label', no_label_percentage),
            ]

            # Calculate exact counts
            exact_counts = [(name, num_images * (perc / 100)) for name, perc in categories]

            # Calculate integer counts and distribute remaining images
            int_counts = []
            fractional_parts = []
            total_int_counts = 0
            for name, exact_count in exact_counts:
                int_count = int(exact_count)
                int_counts.append((name, int_count))
                fractional_parts.append((name, exact_count - int_count))
                total_int_counts += int_count

            remaining_images = num_images - total_int_counts
            fractional_parts.sort(key=lambda x: x[1], reverse=True)
            for i in range(remaining_images):
                name, _ = fractional_parts[i]
                for j in range(len(int_counts)):
                    if int_counts[j][0] == name:
                        int_counts[j] = (name, int_counts[j][1] + 1)
                        break

            counts = dict(int_counts)
            counts_list = int_counts

            # Initialize i_image
            i_image = 1

            # Determine category for the first image
            total = 0
            category = 'unknown'
            for name, count in counts_list:
                total += count
                if i_image <= total:
                    category = name
                    break

            # Get the container
            try:
                c = Container.objects.get(pk=container_id)
            except Container.DoesNotExist:
                logging.error(f"image() - Container with id {container_id} does not exist.")
                return HttpResponse("Error: Container does not exist.", status=400)

            return render(request, "recyclable/image.html", {
                'container_id': container_id,
                'barcode': barcode,
                'i_image': i_image,
                'num_images': num_images,
                'counts': counts,
                'counts_list': counts_list,
                'category': category,
            })
    else:
        # Handle GET request if necessary
        return HttpResponse("Error: GET method not supported.", status=405)

# @login_required
# def image(request) -> HttpResponse:
#     if request.method == 'POST':
#         # Check if 'frame_data_url' is in POST data to determine if it's an image capture submission
#         frame_data_url = request.POST.get('frame_data_url', '')
#         if frame_data_url:
#             # This is a submission from image.html after capturing an image
#             container_id = request.POST.get('container_id')
#             barcode = request.POST.get('barcode')
#             i_image = request.POST.get('i_image')
#             num_images = request.POST.get('num_images')
#
#             # Validate required fields
#             if not container_id or not i_image or not num_images:
#                 logging.error("image() - Missing required data for image saving.")
#                 return HttpResponse("Error: Missing required data.", status=400)
#
#             # Convert to integers
#             try:
#                 container_id = int(container_id)
#                 i_image = int(i_image)
#                 num_images = int(num_images)
#             except ValueError:
#                 logging.error(f"image() - Invalid data format - container_id: {container_id}, i_image: {i_image}, num_images: {num_images}")
#                 return HttpResponse("Error: Invalid data format.", status=400)
#
#             # Reconstruct counts from POST data
#             counts = {}
#             counts_list = []
#             for key in request.POST:
#                 if key.startswith('counts['):
#                     name = key[7:-1]  # Extract the name
#                     count = request.POST.get(key)
#                     try:
#                         count = int(count)
#                         counts[name] = count
#                         counts_list.append((name, count))
#                     except ValueError:
#                         logging.error(f"image() - Invalid count value for {name}: {count}")
#                         return HttpResponse("Error: Invalid count value.", status=400)
#
#             # Get container
#             try:
#                 c = Container.objects.get(pk=container_id)
#             except Container.DoesNotExist:
#                 logging.error(f"image() - Container with id {container_id} does not exist.")
#                 return HttpResponse("Error: Container does not exist.", status=400)
#
#             # Save the image
#             if frame_data_url:
#                 th = Thread(target=save_image, args=(frame_data_url, c), daemon=True)
#                 th.start()
#
#             # Determine category based on current i_image and counts_list
#             total = 0
#             category = 'unknown'
#             for name, count in counts_list:
#                 total += count
#                 if i_image <= total:
#                     category = name
#                     break
#
#             # Increment i_image for the next image
#             i_image += 1
#
#             # Check if all images have been captured
#             if i_image > num_images:
#                 return render(request, 'recyclable/barcode.html', {'message': 'All images have been captured.'})
#             else:
#                 # Render image.html for the next image
#                 return render(request, "recyclable/image.html", {
#                     'container_id': container_id,
#                     'barcode': barcode,
#                     'i_image': i_image,
#                     'num_images': num_images,
#                     'counts': counts,
#                     'counts_list': counts_list,
#                     'category': category,
#                 })
#         else:
#             # This is the initial submission from num_images.html with percentages
#             container_id = request.POST.get('container_id')
#             barcode = request.POST.get('barcode')
#             num_images_str = request.POST.get('num_images', '0')
#             message = ''
#             error = False
#
#             # Validate container_id and barcode
#             if not container_id or not barcode:
#                 message = 'Container ID or barcode is missing.'
#                 return render(request, "recyclable/barcode.html", {'message': message})
#
#             # Validate num_images
#             try:
#                 num_images = int(num_images_str)
#                 if num_images <= 0:
#                     message += 'Number of images must be greater than zero.\n'
#                     error = True
#             except ValueError:
#                 message += 'Invalid number of images.\n'
#                 error = True
#
#             if error:
#                 return render(request, "recyclable/num_images.html", {
#                     'container_id': container_id,
#                     'barcode': barcode,
#                     'message': message,
#                     # Include form values to preserve user input
#                 })
#
#             # Process percentage inputs
#             def parse_percentage(value, field_name):
#                 try:
#                     val = float(value)
#                     if val < 0 or val > 100:
#                         raise ValueError
#                     return val
#                 except ValueError:
#                     nonlocal message, error
#                     message += f'Invalid percentage for {field_name}. Must be between 0 and 100.\n'
#                     error = True
#                     return 0.0
#
#             # Retrieve percentages from POST data
#             valid_percentage = parse_percentage(request.POST.get('valid_percentage', ''), 'Valid')
#             crushed_1_percentage = parse_percentage(request.POST.get('crushed_1_percentage', ''), 'Crushed 1')
#             crushed_2_percentage = parse_percentage(request.POST.get('crushed_2_percentage', ''), 'Crushed 2')
#             crushed_3_percentage = parse_percentage(request.POST.get('crushed_3_percentage', ''), 'Crushed 3')
#             crushed_4_percentage = parse_percentage(request.POST.get('crushed_4_percentage', ''), 'Crushed 4')
#             bad_orientation_percentage = parse_percentage(request.POST.get('bad_orientation_percentage', ''), 'Bad Orientation')
#             no_label_percentage = parse_percentage(request.POST.get('no_label_percentage', ''), 'No Label')
#
#             # Validate percentages sum to 100%
#             total_percentage = (valid_percentage + crushed_1_percentage + crushed_2_percentage +
#                                 crushed_3_percentage + crushed_4_percentage +
#                                 bad_orientation_percentage + no_label_percentage)
#             if abs(total_percentage - 100) > 0.01:
#                 message += 'The percentages must add up to 100%.'
#                 error = True
#
#             if error:
#                 return render(request, "recyclable/num_images.html", {
#                     'container_id': container_id,
#                     'barcode': barcode,
#                     'message': message,
#                     # Include form values to preserve user input
#                 })
#
#             # Calculate counts based on percentages
#             num_images = int(num_images_str)
#             categories = [
#                 ('valid', valid_percentage),
#                 ('crushed_1', crushed_1_percentage),
#                 ('crushed_2', crushed_2_percentage),
#                 ('crushed_3', crushed_3_percentage),
#                 ('crushed_4', crushed_4_percentage),
#                 ('bad_orientation', bad_orientation_percentage),
#                 ('no_label', no_label_percentage),
#             ]
#
#             # Calculate exact counts
#             exact_counts = [(name, num_images * (perc / 100)) for name, perc in categories]
#
#             # Calculate integer counts and distribute remaining images
#             int_counts = []
#             fractional_parts = []
#             total_int_counts = 0
#             for name, exact_count in exact_counts:
#                 int_count = int(exact_count)
#                 int_counts.append((name, int_count))
#                 fractional_parts.append((name, exact_count - int_count))
#                 total_int_counts += int_count
#
#             remaining_images = num_images - total_int_counts
#             fractional_parts.sort(key=lambda x: x[1], reverse=True)
#             for i in range(remaining_images):
#                 name, _ = fractional_parts[i]
#                 for j in range(len(int_counts)):
#                     if int_counts[j][0] == name:
#                         int_counts[j] = (name, int_counts[j][1] + 1)
#                         break
#
#             counts = dict(int_counts)
#             counts_list = int_counts
#
#             # Initialize i_image
#             i_image = 1
#
#             # Determine category for the first image
#             total = 0
#             category = 'unknown'
#             for name, count in counts_list:
#                 total += count
#                 if i_image <= total:
#                     category = name
#                     break
#
#             # Get the container
#             try:
#                 c = Container.objects.get(pk=container_id)
#             except Container.DoesNotExist:
#                 logging.error(f"image() - Container with id {container_id} does not exist.")
#                 return HttpResponse("Error: Container does not exist.", status=400)
#
#             return render(request, "recyclable/image.html", {
#                 'container_id': container_id,
#                 'barcode': barcode,
#                 'i_image': i_image,
#                 'num_images': num_images,
#                 'counts': counts,
#                 'counts_list': counts_list,
#                 'category': category,
#             })
#     else:
#         # Handle GET request if necessary
#         return HttpResponse("Error: GET method not supported.", status=405)

@login_required
def classifiers(_) -> HttpResponse:
    return render(_, 'recyclable/classifiers.html')

@login_required
def download_size_classifier(_) -> HttpResponse:
    response = HttpResponse(content_type="text/json")
    response['Content-Disposition'] = 'attachment; filename="size_classifier.json"'
    json = create_size_classifier_json()
    response.write(json)
    return response

@login_required
def download_deposit_classifier(_) -> HttpResponse:
    response = HttpResponse(content_type="text/json")
    response['Content-Disposition'] = 'attachment; filename="deposit_classifier.json"'
    json = create_deposit_classifier_json()
    response.write(json)
    return response

def save_image(frame_data_url: Any, container: Container):
    try:
        image_name = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        file_name = f'{container.barcode}__{image_name}.png'
        s3_object_key = f'images/{container.barcode}/{file_name}'

        SAVE_TO_S3 = True
        if SAVE_TO_S3:
            etag = upload_jpeg_base64_to_s3(s3_object_key, frame_data_url)
        else:
            etag = uuid4()

        SAVE_TO_DISK = True
        if SAVE_TO_DISK:
            fp = os.path.join('/tmp', file_name)
            save_image_file(fp, frame_data_url)

        Image.objects.create(
            container=container,
            aws_entity_tag=etag,
            s3_bucket_name=BUCKET_NAME,
            aws_region_name='us-west-2',
            s3_object_key=s3_object_key,
            crush_degree=-1,
            valid_orientation=True,
        )
    except Exception as e:
        logging.error(f'save_image() - exception saving image for container {container.barcode}: {e}')

def update_container_from_request(c, request):
    c.barcode = request.POST.get('barcode', '')
    c.brand = request.POST.get('brand', '')
    c.product_name = request.POST.get('product_name', '')
    c.material_type = request.POST.get('material_type', '')
    c.plastic_code = request.POST.get('plastic_code', '')
    c.rigidity = request.POST.get('rigidity', '')
    c.shape = request.POST.get('shape', '')
    c.content_type = request.POST.get('content_type', '')
    c.hazardous = request.POST.get('hazardous', '')
    c.beverage_type = request.POST.get('beverage_type', '')
    c.alcohol_percentage = float(request.POST.get('alcohol_percentage', -1.0))
    c.alcoholic = request.POST.get('alcoholic', '')
    c.alcoholic_drinks_type = request.POST.get('alcoholic_drinks_type', '')
    c.wine_bottle_shape = request.POST.get('wine_bottle_shape', '')
    c.wine_type = request.POST.get('wine_type', '')
    c.liquid_volume = float(request.POST.get('liquid_volume', 0))
    c.liquid_volume_unit = request.POST.get('liquid_volume_unit', '')
    c.mass_gram = float(request.POST.get('mass_gram', 0))
    c.made_in = request.POST.get('made_in', '')
    c.juice_percentage = float(request.POST.get('juice_percentage', -1.0))
    c.material_color = request.POST.get('material_color', '')
    c.ribbed = request.POST.get('ribbed', '')
    c.ringed = request.POST.get('ringed', '')
    c.visual_volume = request.POST.get('visual_volume', '')
    c.ca = 'ca' in request.POST
    c.ct = 'ct' in request.POST
    c.gu = 'gu' in request.POST
    c.hi = 'hi' in request.POST
    c.ia = 'ia' in request.POST
    c.me = 'me' in request.POST
    c.ma = 'ma' in request.POST
    c.mi = 'mi' in request.POST
    c.ny = 'ny' in request.POST
    c.Or = 'Or' in request.POST
    c.vt = 'vt' in request.POST
    c.save()

def get_container_context(container, barcode, message=''):
    return {
        'message': message,
        'container': container,
        'container_id': container.id,
        'barcode': barcode,
        'material_types': Container._meta.get_field('material_type').choices,
        'plastic_codes': Container._meta.get_field('plastic_code').choices,
        'rigidity_types': Container._meta.get_field('rigidity').choices,
        'shape_types': Container._meta.get_field('shape').choices,
        'content_types': Container._meta.get_field('content_type').choices,
        'hazardous_choices': Container._meta.get_field('hazardous').choices,
        'beverage_types': Container._meta.get_field('beverage_type').choices,
        'alcoholic_choices': Container._meta.get_field('alcoholic').choices,
        'alcoholic_drinks_types': Container._meta.get_field('alcoholic_drinks_type').choices,
        'wine_bottle_shapes': Container._meta.get_field('wine_bottle_shape').choices,
        'wine_types': Container._meta.get_field('wine_type').choices,
        'liquid_volume_units': Container._meta.get_field('liquid_volume_unit').choices,
        'made_in_choices': Container._meta.get_field('made_in').choices,
        'material_color': Container._meta.get_field('material_color').choices,
        'ribbed_types': Container._meta.get_field('ribbed').choices,
        'ringed_types': Container._meta.get_field('ringed').choices,
        'visual_volumes': Container._meta.get_field('visual_volume').choices,
    }