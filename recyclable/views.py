import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4
import re


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.views.decorators.http import require_http_methods
import json

from recyclable.models import Container, Image, mk_null_container
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

        # If the request method is POST, populate container with user input
        if request.method == 'POST':
            update_container_from_request(c, request)

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

    # Update fields from form data before validation
    update_container_from_request(c, request)

    # Validate the mass_gram field
    try:
        mass_gram = float(request.POST.get('mass_gram', -1))
    except ValueError:
        message = 'Invalid input for Mass (gram). Please enter a number.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    if mass_gram <= 0:
        message = 'Mass (gram) must be a number greater than zero.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))

    # Validate the alcohol_percentage field
    try:
        alcohol_percentage = float(request.POST.get('alcohol_percentage', -1))
    except ValueError:
        message = 'Invalid input for Alcohol Percentage. Please enter a valid number.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    if alcohol_percentage < 0 or alcohol_percentage > 100:
        message = 'Alcohol Percentage must be a number between 0 and 100.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))

    # Validate the liquid_volume field
    try:
        liquid_volume = float(request.POST.get('liquid_volume', -1))
    except ValueError:
        message = 'Invalid input for Liquid Volume. Please enter a valid number.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    if liquid_volume <= 0:
        message = 'Liquid Volume must be a number greater than zero.'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))

    # Validate the made_in field using a regular expression
    made_in = request.POST.get('made_in', '').strip().upper()
    if not re.fullmatch(r'[A-Z]{3}', made_in):
        message = 'Made In must be exactly 3 uppercase English letters (A-Z).'
        return render(request, "recyclable/container.html", get_container_context(c, barcode, message))
    else:
        c.made_in = made_in

    # Save the container
    c.save()

    return render(request, "recyclable/num_images.html", get_container_context(c, barcode, message))


@login_required
def image(request) -> HttpResponse:
    if request.method == 'POST':
        # Check if 'frame_data_url' is in POST data
        frame_data_url = request.POST.get('frame_data_url', '')
        if frame_data_url:
            # Handle image capture
            return handle_image_capture(request)
        else:
            # Handle initial submission with percentages
            return handle_initial_submission(request)
    else:
        # Handle GET request if necessary
        return HttpResponse("Error: GET method not supported.", status=405)

def handle_image_capture(request: HttpRequest) -> HttpResponse:
    # Get data from image.html after capturing an image
    container_id = request.POST.get('container_id')
    barcode = request.POST.get('barcode')
    i_image = request.POST.get('i_image')
    num_images = request.POST.get('num_images')
    image_width = request.POST.get('image_width', '')
    image_height = request.POST.get('image_height', '')

    # Validate image dimensions
    try:
        image_width = float(image_width)
        image_height = float(image_height)
    except ValueError:
        logging.error("Invalid image dimensions received.")
        return HttpResponse("Error: Invalid image dimensions.", status=400)

    # Validate required fields
    if not container_id or not i_image or not num_images:
        logging.error("handle_image_capture() - Missing required data for image saving.")
        return HttpResponse("Error: Missing required data.", status=400)

    # Convert to integers
    try:
        container_id = int(container_id)
        i_image = int(i_image)
        num_images = int(num_images)
    except ValueError:
        logging.error(f"handle_image_capture() - Invalid data format - container_id: {container_id}, i_image: {i_image}, num_images: {num_images}")
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
                logging.error(f"handle_image_capture() - Invalid count value for {name}: {count}")
                return HttpResponse("Error: Invalid count value.", status=400)

    # Get container
    try:
        c = Container.objects.get(pk=container_id)
    except Container.DoesNotExist:
        logging.error(f"handle_image_capture() - Container with id {container_id} does not exist.")
        return HttpResponse("Error: Container does not exist.", status=400)

    # Initialize category mapping
    category_to_crush_degree = {
        "valid": 0,
        "crushed_1": 1,
        "crushed_2": 2,
        "crushed_3": 3,
        "crushed_4": 4,
        "bad_orientation": -1,
        "no_label": -1,
    }

    # Determine category based on the current i_image
    total = 0
    category = 'unknown'
    for name, count in counts_list:
        total += count
        if i_image <= total:
            category = name
            break

    # Assign crush degree based on the category
    crush_degree = category_to_crush_degree.get(category, -1)

    # Save the image
    frame_data_url = request.POST.get('frame_data_url', '')
    if frame_data_url:
        save_image(
            frame_data_url,
            c,
            crush_degree=crush_degree,
            category=category,
            image_width=image_width,
            image_height=image_height,
        )

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

def handle_initial_submission(request: HttpRequest) -> HttpResponse:
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
        })

    # Process percentage inputs
    def parse_percentage(value: str, field_name: str) -> float:
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
    total_percentage = (
        valid_percentage + crushed_1_percentage + crushed_2_percentage +
        crushed_3_percentage + crushed_4_percentage +
        bad_orientation_percentage + no_label_percentage
    )
    if abs(total_percentage - 100) > 0.01:
        message += 'The percentages must add up to 100%.'
        error = True

    if error:
        return render(request, "recyclable/num_images.html", {
            'container_id': container_id,
            'barcode': barcode,
            'message': message,
        })

    # Calculate counts based on percentages
    num_images = int(num_images_str)
    categories = [
        ('valid', valid_percentage),
        ('bad_orientation', bad_orientation_percentage),
        ('crushed_1', crushed_1_percentage),
        ('crushed_2', crushed_2_percentage),
        ('crushed_3', crushed_3_percentage),
        ('no_label', no_label_percentage),
        ('crushed_4', crushed_4_percentage),
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
        logging.error(f"handle_initial_submission() - Container with id {container_id} does not exist.")
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
# @login_required
# def image(request) -> HttpResponse:
#     if request.method == 'POST':
#         # Check if 'frame_data_url' is in POST data to determine if it's an image being captured
#         frame_data_url = request.POST.get('frame_data_url', '')
#         if frame_data_url:
#             # Get data from image.html after capturing an image
#             container_id = request.POST.get('container_id')
#             barcode = request.POST.get('barcode')
#             i_image = request.POST.get('i_image')
#             num_images = request.POST.get('num_images')
#             image_width = request.POST.get('image_width', '')
#             image_height = request.POST.get('image_height', '')
#
#             # Validate image dimensions
#             try:
#                 image_width = float(image_width)
#                 image_height = float(image_height)
#             except ValueError:
#                 logging.error("Invalid image dimensions received.")
#                 return HttpResponse("Error: Invalid image dimensions.", status=400)
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
#             # Initialize category mapping
#             category_to_crush_degree = {
#                 "valid": 0,
#                 "crushed_1": 1,
#                 "crushed_2": 2,
#                 "crushed_3": 3,
#                 "crushed_4": 4,
#                 "bad_orientation": -1,
#                 "no_label": -1,
#             }
#
#             # Determine category based on the current i_image
#             total = 0
#             category = 'unknown'
#             for name, count in counts_list:
#                 total += count
#                 if i_image <= total:
#                     category = name
#                     break
#
#
#             # Assign crush degree based on the category
#             crush_degree = category_to_crush_degree.get(category, -1)
#
#             # Save the image
#             if frame_data_url:
#                 save_image(
#                     frame_data_url,
#                     c,
#                     crush_degree=crush_degree,
#                     category=category,
#                     image_width=image_width,
#                     image_height=image_height,
#                 )
#
#             # Increment i_image for the next image
#             i_image += 1
#
#             # Check if all images have been captured
#             if i_image > num_images:
#                 return render(request, 'recyclable/barcode.html', {'message': 'All images have been captured.'})
#             else:
#                 # Determine category based on the new i_image
#                 total = 0
#                 category = 'unknown'
#                 for name, count in counts_list:
#                     total += count
#                     if i_image <= total:
#                         category = name
#                         break
#
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
#                 })
#
#             # Calculate counts based on percentages
#             num_images = int(num_images_str)
#             categories = [
#                 ('valid', valid_percentage),
#                 ('bad_orientation', bad_orientation_percentage),
#                 ('crushed_1', crushed_1_percentage),
#                 ('crushed_2', crushed_2_percentage),
#                 ('crushed_3', crushed_3_percentage),
#                 ('no_label', no_label_percentage),
#                 ('crushed_4', crushed_4_percentage),
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

def save_image(frame_data_url: Any, container: Container, crush_degree: int, category: str, image_width: float, image_height: float):
    try:
        image_name = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        file_name = f'{container.barcode}_{image_name}.png'
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

        # Set valid_orientation based on category
        valid_orientation = False if category == 'bad_orientation' else True

        # Set orientation_style based on valid_orientation
        if valid_orientation:
            orientation_style = Image.Orientation.PARALLEL
        else:
            orientation_style = Image.Orientation.UNKNOWN

        # Set label based on category
        if category in ['valid', 'crushed_1', 'crushed_2', 'crushed_3']:
            label = Image.LabelType.BODY_ONLY
        elif category in ['bad_orientation', 'no_label', 'crushed_4']:
            label = Image.LabelType.NEITHER
        else:
            label = Image.LabelType.BODY_ONLY

        Image.objects.create(
            container=container,
            aws_entity_tag=etag,
            s3_bucket_name=BUCKET_NAME,
            aws_region_name='us-west-2',
            s3_object_key=s3_object_key,
            crush_degree=crush_degree,
            valid_orientation=valid_orientation,
            orientation_style=orientation_style,
            label=label,
            image_width=image_width,
            image_height=image_height,
        )
    except Exception as e:
        logging.error(f'save_image() - exception saving image for container {container.barcode}: {e}')

def update_container_from_request(c: Container, request: HttpRequest) -> None:
    c.barcode: str = request.POST.get('barcode', '')
    c.brand: str = request.POST.get('brand', '')
    c.product_name: str = request.POST.get('product_name', '')
    c.material_type: str = request.POST.get('material_type', '')
    c.plastic_code: str = request.POST.get('plastic_code', '')
    c.rigidity: str = request.POST.get('rigidity', '')
    c.shape: str = request.POST.get('shape', '')
    c.content_type: str = request.POST.get('content_type', '')
    c.hazardous: str = request.POST.get('hazardous', '')
    c.beverage_type: str = request.POST.get('beverage_type', '')
    c.alcohol_percentage: float = float(request.POST.get('alcohol_percentage', -1.0))
    c.alcoholic: str = request.POST.get('alcoholic', '')
    c.alcoholic_drinks_type: str = request.POST.get('alcoholic_drinks_type', '')
    c.wine_bottle_shape: str = request.POST.get('wine_bottle_shape', '')
    c.wine_type: str = request.POST.get('wine_type', '')
    c.liquid_volume: float = float(request.POST.get('liquid_volume', -1.0))
    c.liquid_volume_unit: str = request.POST.get('liquid_volume_unit', '')
    c.mass_gram: float = float(request.POST.get('mass_gram', -1.0))
    c.juice_percentage: float = float(request.POST.get('juice_percentage', -1.0))
    c.material_color: str = request.POST.get('material_color', '')
    c.ribbed: str = request.POST.get('ribbed', '')
    c.ringed: str = request.POST.get('ringed', '')
    c.visual_volume: str = request.POST.get('visual_volume', '')
    c.ca: bool = 'ca' in request.POST
    c.ct: bool = 'ct' in request.POST
    c.gu: bool = 'gu' in request.POST
    c.hi: bool = 'hi' in request.POST
    c.ia: bool = 'ia' in request.POST
    c.me: bool = 'me' in request.POST
    c.ma: bool = 'ma' in request.POST
    c.mi: bool = 'mi' in request.POST
    c.ny: bool = 'ny' in request.POST
    c.Or: bool = 'Or' in request.POST
    c.vt: bool = 'vt' in request.POST

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
        'material_color': Container._meta.get_field('material_color').choices,
        'ribbed_types': Container._meta.get_field('ribbed').choices,
        'ringed_types': Container._meta.get_field('ringed').choices,
        'visual_volumes': Container._meta.get_field('visual_volume').choices,
    }

def production_images(request):
    return render(request, 'recyclable/production_images.html')

def production_image_grid(request):
    # Get filter parameters from request.GET
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    deposit_types = request.GET.getlist('depositType')
    cubes = request.GET.get('selectCubes', '').split('\n')
    
    context = {
        'initial_filters': {
            'start_date': start_date,
            'end_date': end_date,
            'deposit_types': deposit_types,
            'cubes': cubes,
        }
    }
    return render(request, 'recyclable/production_image_grid.html', context)

@require_http_methods(["POST"])
def api_containers(request):
    """API endpoint for fetching container images based on filters"""
    try:
        filters = json.loads(request.body)
        
        # TODO: Implement AWS query logic
        # example response_data
        response_data = {
            "images": [
                {
                    "id": "1",
                    "url": "https://static-olyns.olyns.com/collector/captures/Safeway1483/attempts/2024.11.10/image1.jpg",
                    "filename": "image1.jpg"
                }
                # more images...
            ]
        }
        
        return JsonResponse(response_data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

