import csv
import logging
import base64
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from io import BytesIO

import boto3 as boto3
from cv2 import Mat
from PIL import Image


def convert_spaces_to_pluses(s: str) -> str:
    return s.replace(' ', '+')


def crop_image(frame: Mat) -> Mat:
    height, width = frame.shape[0:2]
    start_row = int(height * 0)
    start_col = int(width * .33)
    end_row = int(height * 1.0)
    end_col = int(width * .66)
    return frame[start_row:end_row, start_col:end_col]

def write_string_to_file(fp: str, string: str):
    try:
        with open(fp, 'w') as file:
            file.write(string)
        logging.debug(f'write_string_to_file() - successfully wrote the string to {fp}')
    except Exception as e:
        logging.error(f'write_string_to_file() - error writing to {fp}: {e}')



def save_image_file(fp: str, image_base64: str) -> None:
    data = image_base64.split(',')[1]
    image_data = base64.b64decode(data)
    image_buffer = BytesIO(image_data)
    img = Image.open(image_buffer)
    img.save(fp, 'PNG')


def s3_data_from_object_url(url: str) -> Tuple[str, str, str]:
    # The URL has the form:
    # https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_object_key}
    # This function returns the bucket_name, region_name and s3_object_key

    url_minus_protocol = url.split('//')[1]
    bucket_name = url_minus_protocol.split('.')[0]
    region_name = url_minus_protocol.split('.')[2]
    s3_object_key = url_minus_protocol.split('amazonaws.com/')[1]
    return bucket_name, region_name, s3_object_key


def url_from_s3_data(bucket_name: str, region_name: str, s3_object_key: str) -> str:
    return f'https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_object_key}'


def read_csv_with_headers(file_path: str) -> List[Dict[str, str]]:
    data = []
    with open(file_path, mode='r', newline='', encoding='utf-8', errors='ignore') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(row)
    return data

BUCKET_NAME: str = 'olyns-recyclable'


def upload_jpeg_base64_to_s3(s3_object_key: str, image_base64: str):
    data = image_base64.split(',')[1]
    image_data = base64.b64decode(data)
    image_buffer = BytesIO(image_data)
    ctype = 'image/png'
    logging.debug(f'upload_jpeg_base64_to_s3() - ctype: {ctype}')
    s3_client = boto3.client('s3')  # get client higher and pass down?
    response = s3_client.put_object(Bucket=BUCKET_NAME, Body=image_buffer, Key=s3_object_key,
                         ACL='private', ContentType=ctype)
    etag = response['ETag'].strip('"')  # ETag is enclosed in double quotes
    return etag




"""
NOT TESTED
def download_image_from_s3_and_save(s3_object_key: str):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_object_key)
        image_data = response['Body'].read()
        extension = s3_object_key.split('.')[-1]
        with open(filename, 'wb') as f:
            filename = '/tmp/container_image' + extension
            f.write(image_data)
        print(f"Image downloaded and saved as {filename}")
    except Exception as e:
        print(f"Error: {e}")

def get_s3_object_etag(s3: BaseClient, s3_object_key: str) -> str:
    try:
        response = s3.head_object(Bucket=BUCKET_NAME, Key=s3_object_key)
        etag = response['ETag'].strip('"')  # ETag is enclosed in double quotes
        return etag
    except Exception as e:
        logging.error(f'get_object_etag() - Error: {e}')
        return ''
"""
