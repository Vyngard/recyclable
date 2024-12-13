import os
from typing import Tuple, Any
from unittest import skip

import boto3
from django.conf import settings
from django.test import TestCase

from .models import Container, ContainerSize, load_models_from_csv, mk_container
from .utils import s3_data_from_object_url
from .views_helpers import create_size_classifier_json, create_deposit_classifier_json


class ContainerModelTests(TestCase):

    def test_mk_container_good(self) -> None:
        # Create a Container instance with all required fields
        c = mk_container(
            barcode='123',
            brand='coca-cola',
            product_name='coke',
            material_type=Container.MaterialType.PLASTIC,
            plastic_code=Container.PlasticCode.PET,
            liquid_volume=12.0,
            liquid_volume_unit=Container.LiquidVolumeUnit.OZ,
            mass_gram=11.0,
            rigidity=Container.Rigidity.RIGID,
            shape=Container.Shape.UNKNOWN,
            content_type=Container.Contents.UNKNOWN,
            hazardous=Container.Hazardous.NO,
            beverage_type=Container.BeverageType.SOFT_DRINK,
            made_in='UNK',  # New required field
            # Include any other required fields or defaults
        )

        # Assert that the container is valid
        is_valid, reason = c.is_valid()
        self.assertTrue(is_valid, f"Container should be valid, but got: {reason}")

    def test_mk_container_na(self) -> None:
        c = mk_container(
            barcode='123',
            brand='pepsi',
            product_name='pepsi',
            material_type=Container.MaterialType.PLASTIC,
            plastic_code=Container.PlasticCode.NA,
            liquid_volume=12.0,
            liquid_volume_unit=Container.LiquidVolumeUnit.OZ,
            mass_gram=13.0,
            rigidity=Container.Rigidity.RIGID,
            shape=Container.Shape.UNKNOWN,
            content_type=Container.Contents.UNKNOWN,
            hazardous=Container.Hazardous.NO,
            beverage_type=Container.BeverageType.UNKNOWN,
            made_in='UNK',
            # add any other required fields or defaults
        )

        is_valid, reason = c.is_valid()
        self.assertFalse(is_valid)
        self.assertEqual(reason, 'Material type is plastic but the plastic code is NA.')

    def test_material_type(self) -> None:
        self.assertEqual(Container.MaterialType.GLASS, 'glass')

class CsvTests(TestCase):

    def test_read_csv(self) -> None:
        dir_name = os.path.join(settings.BASE_DIR, 'test_data')
        load_models_from_csv(dir_name)
        c1 = Container.objects.get(barcode='00345323')
        print(f'c1: {c1}')

        mtl = c1.material_type
        print(f'mtl: {mtl}')

        self.assertEqual(mtl, Container.MaterialType.PLASTIC)
        self.assertEqual(c1.brand, 'TRADERJOES')
        self.assertEqual(c1.product_name, 'LEMON MINERAL WATER')
        self.assertEqual(c1.plastic_code, Container.PlasticCode.PET)
        self.assertEqual(c1.liquid_volume, 1.25)
        self.assertEqual(c1.made_in, 'UNK')
        # add any other assertions for the container fields

class S3Tests(TestCase):
    @skip("Skipping S3 tests")
    def test_print_buckets(self):
        s3 = boto3.resource('s3')
        for b in s3.buckets.all():
            print(b.name)

class UtilsTests(TestCase):

    def test_data_from_url(self) -> None:
        url = 'https://olyns-recyclable.s3.us-west-2.amazonaws.com/containerimages/995/UNKNOWN-MARS_WRIGLELY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
        bucket_name, region_name, s3_object_key = s3_data_from_object_url(url)
        self.assertEqual(bucket_name, 'olyns-recyclable')
        self.assertEqual(region_name, 'us-west-2')
        self.assertEqual(s3_object_key, 'containerimages/995/UNKNOWN-MARS_WRIGLELY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg')

    def test_url_from_data(self) -> None:
        bucket_name = 'olyns-recyclable'
        region_name = 'us-west-2'
        s3_object_key = 'containerimages/995/UNKNOWN-MARS_WRIGLEY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
        url = f'https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_object_key}'
        expected_url = 'https://olyns-recyclable.s3.us-west-2.amazonaws.com/containerimages/995/UNKNOWN-MARS_WRIGLEY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
        self.assertEqual(url, expected_url)

        bn1, rn1, s3ok1 = s3_data_from_object_url(url)
        self.assertEqual(bn1, bucket_name)
        self.assertEqual(rn1, region_name)
        self.assertEqual(s3ok1, s3_object_key)

class ViewsHelpersTests(TestCase):

    def test_create_count_classifier_json(self) -> None:
        load_models_from_csv(os.path.join(settings.BASE_DIR, 'test_data'))
        size_json = create_size_classifier_json()
        print(f'size_json: {size_json}')
        deposit_json = create_deposit_classifier_json()
        print(f'deposit_json: {deposit_json}')
        # add assertions for the size and deposit JSONs


# class ContainerModelTests(TestCase):
#
#     def test_mk_container_good(self) -> None:
#
#         mtype: Tuple[str, Any] = Container.MaterialType.UNKNOWN
#         print(f'mtype: {mtype}')
#
#         c: Container = mk_container('123',
#                                     'coca-cola',
#                                     'coke',
#                                     Container.MaterialType.PLASTIC,
#                                     Container.PlasticCode.PET,
#                                     12,
#                                     Container.LiquidVolumeUnit.OZ,
#                                     11)
#
#         self.assertIs(c.is_valid()[0], True)
#
#
#     def test_mk_container_na(self) -> None:
#         c: Container = mk_container('123',
#                                     'pepsi',
#                                     'pepsi',
#                                     Container.MaterialType.PLASTIC,
#                                     Container.PlasticCode.NA,
#                                     12,
#                                     Container.LiquidVolumeUnit.OZ,
#                                     13)
#
#         print(f'c: {c}')
#         print(f'c.is_valid(): {c.is_valid()}')
#         is_valid, reason = c.is_valid()
#         self.assertIs(is_valid, False)
#         self.assertEqual(reason, 'Material type is plastic but the plastic code is NA.')
#
#
#     def test_material_type(self) -> None:
#         print('test_material_type()')
#         assert Container.MaterialType.GLASS == 'glass'
#
#
# class CsvTests(TestCase):
#
#     def test_read_csv(self) -> None:
#         dir_name = os.path.join(settings.BASE_DIR, 'test_data')
#         load_models_from_csv(dir_name)
#         c1: Container = Container.objects.get(barcode='00606004')
#         print(f'c1: {c1}')
#
#         mtl: Container.MaterialType = c1.material_type
#         print(f'mtl: {mtl}')
#
#         assert mtl == Container.MaterialType.ALUMINUM
#         assert c1.brand == 'TRADERJOES'
#         assert c1.product_name == 'RHUBARB AND STRAWBERRY SODA'
#         assert c1.plastic_code == Container.PlasticCode.NA
#         assert c1.liquid_volume == 8.45
#         assert c1.size == ContainerSize.LT_24_OZ
#
#
# class S3Tests(TestCase):
#     @skip("")
#     def test_print_buckets(self):
#         s3 = boto3.resources('s3')
#         for b in s3.buckets.all():
#             print(b.name)
#
#
# class UtilsTests(TestCase):
#     def test_data_from_url(self) -> None:
#         url = 'https://olyns-recyclable.s3.us-west-2.amazonaws.com/containerimages/995/UNKNOWN-MARS_WRIGLELY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
#         bucket_name, region_name, s3_object_key = s3_data_from_object_url(url)
#         assert bucket_name == 'olyns-recyclable'
#         assert region_name == 'us-west-2'
#         assert s3_object_key == 'containerimages/995/UNKNOWN-MARS_WRIGLELY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
#
#     def test_url_from_data(self) -> None:
#         bucket_name = 'olyns-recyclable'
#         region_name = 'us-west-2'
#         s3_object_key = 'containerimages/995/UNKNOWN-MARS_WRIGLEY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
#         url = f'https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_object_key}'
#         assert url == 'https://olyns-recyclable.s3.us-west-2.amazonaws.com/containerimages/995/UNKNOWN-MARS_WRIGLEY_MINI_SNICKERS_BAR-MARS_WRIGLEY_MINI_SNICKERS_BAR-200ML-0G-/VALID/995_2023-05-12-15-13-04.jpg'
#
#         bn1, rn1, s3ok1 = s3_data_from_object_url(url)
#         assert bn1 == bucket_name
#         assert rn1 == region_name
#         assert s3ok1 == s3_object_key
#
#
# class ViewsHelpersTests(TestCase):
#
#     def test_create_count_classifier_json(self) -> None:
#         load_models_from_csv(os.path.join(settings.BASE_DIR, 'test_data'))
#         size_json = create_size_classifier_json()
#         print(f'size_json: {size_json}')
#         deposit_json = create_deposit_classifier_json()
#         print(f'deposit_json: {deposit_json}')
