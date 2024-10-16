import os
from enum import Enum, auto
from typing import Tuple, Any, Optional
import logging

from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from recyclable.utils import read_csv_with_headers, s3_data_from_object_url, url_from_s3_data, \
    convert_spaces_to_pluses


class ContainerSize(Enum):
    LT_24_OZ = 'LT_24_OZ'
    GTE_24_OZ = 'GTE_24_OZ'
    UNKNOWN =  'UNKNOWN'
    #NA = 'NA'




class Container(models.Model):

    class MaterialType(models.TextChoices):
        ALUMINUM = 'alu', _('Aluminum')
        BIMETAL = 'bimetal', _('Bimetal')
        CARDBOARD = 'cardboard', _('Cardboard')
        FOIL_LAMINATE = 'FOIL_LAMINATE', _('Foil Laminate')
        GLASS = 'glass', _('Glass')
        PAPER = 'paper', _('Paper')
        ORGANIC = 'organic', _('Organic')
        PLASTIC = 'plastic', _('Plastic')


        OTHER = 'other', _('Other')
        UNKNOWN = 'unknown', _('Unknown')



    class PlasticCode(models.TextChoices):
        PET = '1_pet', _('1-PET')
        HDPE = '2_hdpe', _('2-HDPE')
        PVC = '3_pvc', _('3-PVC')
        LDPE = '4_ldpe', _('4-LDPE')
        PP = '5_pp', _('5-PP')
        PS = '6_ps', _('6-PS')
        OTHER ='7_o', _('7-OTHER')
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')

    class LiquidVolumeUnit(models.TextChoices):
        OZ = 'OZ', _('fl oz')
        ML = 'ML', _('mL')
        LITER = 'LITER', _('L')
        NA = 'NA', _('NA')

    class RigidityType(models.TextChoices):
        RIGID = 'rigid', _('Rigid')
        FLEXIBLE = 'flexible', _('Flexible')
        UNKNOWN = 'unknown', _('Unknown')

    class ShapeType(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        BOTTLE = 'bottle', _('Bottle')
        CAN_BEVERAGE = 'can_beverage', _('Can Beverage')
        CAN_FOOD = 'can_food', _('Can Food')
        CUP = 'cup', _('Cup')
        JAR = 'jar', _('Jar')
        CUBIC = 'cubic', _('Cubic')
        EGG_SHAPED = 'egg_shaped', _('Egg Shaped')
        BAG_WRAPPER = 'bag_wrapper', _('Bag Wrapper')
        POUCH = 'pouch', _('Pouch')
        REST = 'rest', _('Rest')

    class ContentType(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        BEVERAGE = 'beverage', _('Beverage')
        CANDY = 'candy', _('Candy')
        OIL = 'oil', _('Oil')
        COSMETICS = 'cosmetics', _('Cosmetics')
        PHARMACEUTICAL = 'pharmaceutical', _('Pharmaceutical')
        FOOD = 'food', _('Food')
        CONDIMENTS = 'condiments', _('Condiments')
        FLAMMABLE = 'flammable', _('Flammable')
        REST = 'rest', _('Rest')

    class Hazardous(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        YES = 'yes', _('Yes')
        NO = 'no', _('No')

    class BeverageType(models.TextChoices):
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')
        WATER = 'water', _('Water')
        FLAVORED_WATER = 'flavored_water', _('Flavored Water')
        COCONUT_WATER = 'coconut_water', _('Coconut Water')
        SOFT_DRINK = 'soft_drink', _('Soft Drink')
        SOFT_DRINK_ALTERNATIVE = 'soft_drink_alternative', _('Soft Drink Alternative')
        SPORTS_DRINK = 'sports_drink', _('Sports Drink')
        ENERGY_DRINK = 'energy_drink', _('Energy Drink')
        ALCOHOLIC_BEVERAGE = 'alcoholic_beverage', _('Alcoholic Beverage')
        DAIRY = 'dairy', _('Dairy')
        SUBSTITUTE_MILK = 'substitute_milk', _('Substitute Milk')
        PROTEIN_SHAKE = 'protein_shake', _('Protein Shake')
        FRUIT_JUICE = 'fruit_juice', _('Fruit Juice')
        VEGETABLE_JUICE = 'vegetable_juice', _('Vegetable Juice')
        COFFEE = 'coffee', _('Coffee')
        TEA = 'tea', _('Tea')
        PROBIOTICS = 'probiotics', _('Probiotics')
        REST = 'rest', _('Rest')

    class Alcoholic(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        YES = 'yes', _('Yes')
        NO = 'no', _('No')

    class AlcoholicDrinksType(models.TextChoices):
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')
        ABSINTHE = 'absinthe', _('Absinthe')
        BAIJIU = 'baijiu', _('Baijiu')
        BEER = 'beer', _('Beer')
        BOURBON = 'bourbon', _('Bourbon')
        BRANDY = 'brandy', _('Brandy')
        COCKTAIL_MIX = 'cocktail_mix', _('Cocktail Mix')
        COGNAC = 'cognac', _('Cognac')
        GIN = 'gin', _('Gin')
        HARD_SELTZER = 'hard_seltzer', _('Hard Seltzer')
        MAKGEOLLI = 'makgeolli', _('Makgeolli')
        MALT = 'malt', _('Malt')
        RUM = 'rum', _('Rum')
        SAKE = 'sake', _('Sake')
        SCOTCH = 'scotch', _('Scotch')
        SOJU = 'soju', _('Soju')
        TEQUILA = 'tequila', _('Tequila')
        VERMOUTH = 'vermouth', _('Vermouth')
        VODKA = 'vodka', _('Vodka')
        WHISKY = 'whisky', _('Whisky')
        WINE = 'wine', _('Wine')
        OTHER = 'other', _('Other')

    class WineBottleShape(models.TextChoices):
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')
        ALSACE = 'alsace', _('Alsace')
        BORDEAUX = 'bordeaux', _('Bordeaux')
        BURGUNDY = 'burgundy', _('Burgundy')
        CHAMPAGNE = 'champagne', _('Champagne')
        CHIANTI = 'chianti', _('Chianti')
        PORT = 'port', _('Port')
        PROVENCE = 'provence', _('Provence')
        OTHER = 'other', _('Other')

    class WineType(models.TextChoices):
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')
        ALBARIÑO = 'albariño', _('Albariño')
        CABERNET_FRANC = 'cabernet_franc', _('Cabernet Franc')
        CABERNET_SAUVIGNON = 'cabernet_sauvignon', _('Cabernet Sauvignon')
        CAVA = 'cava', _('Cava')
        CHAMPAGNE = 'champagne', _('Champagne')
        CHARDONNAY = 'chardonnay', _('Chardonnay')
        CHENIN_BLANC = 'chenin_blanc', _('Chenin Blanc')
        GEWÜRZTRAMINER = 'gewürztraminer', _('Gewürztraminer')
        GRÜNER_VELTLINER = 'grüner_veltliner', _('Grüner Veltliner')
        MADEIRA = 'madeira', _('Madeira')
        MALBEC = 'malbec', _('Malbec')
        MERLOT = 'merlot', _('Merlot')
        MUSCAT = 'muscat', _('Muscat')
        PINOT_BLANC = 'pinot_blanc', _('Pinot Blanc')
        PINOT_GRIS = 'pinot_gris', _('Pinot Gris')
        PINOT_NOIR = 'pinot_noir', _('Pinot Noir')
        PORT = 'port', _('Port')
        PROSECCO = 'prosecco', _('Prosecco')
        RED_BLEND = 'red_blend', _('Red Blend')
        RIESLING = 'riesling', _('Riesling')
        ROSÉ = 'rosé', _('Rosé')
        SANCERRE = 'sancerre', _('Sancerre')
        SANGIOVESE = 'sangiovese', _('Sangiovese')
        SAUVIGNON_BLANC = 'sauvignon_blanc', _('Sauvignon Blanc')
        SHERRY = 'sherry', _('Sherry')
        SHIRAZ = 'shiraz', _('Shiraz')
        SPARKLING_WINE = 'sparkling_wine', _('Sparkling Wine')
        SYLVANER = 'sylvaner', _('Sylvaner')
        WHITE_BLEND = 'white_blend', _('White Blend')
        ZINFANDEL = 'zinfandel', _('Zinfandel')

    class MadeIn(models.TextChoices):
        UNK = 'UNK', _('Unknown')
        USA = 'USA', _('USA')
        CAN = 'CAN', _('Canada')
        GBR = 'GBR', _('United Kingdom')

    class RibbedType(models.TextChoices):
        RIBBED_BODY = 'ribbed_body', _('Ribbed Body')
        RIBBED_NECK = 'ribbed_neck', _('Ribbed Neck')
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')

    class RingedType(models.TextChoices):
        SINGLE_RING = 'single_ring', _('Single Ring')
        DOUBLE_RING = 'double_ring', _('Double Ring')
        NA = 'NA', _('NA')
        UNKNOWN = 'unknown', _('Unknown')

    class VisualVolume(models.TextChoices):
        NA = 'NA', _('NA')
        SMALL = 'small', _('Small')
        LT_24OZ = 'LT_24_OZ', _('Less than 24 oz')
        GT_24OZ = 'GT_24_OZ', _('Greater than 24 oz')

    class MaterialColor(models.TextChoices):
            AMBER = 'amber', _('Amber')
            BEIGE = 'beige', _('Beige')
            BLACK = 'black', _('Black')
            BLUE = 'blue', _('Blue')
            BROWN = 'brown', _('Brown')
            COBALT_BLUE = 'cobalt_blue', _('Cobalt Blue')
            EMERALD_GREEN = 'emerald_green', _('Emerald Green')
            FLUORESCENT_GREEN = 'fluorescent_green', _('Fluorescent Green')
            FROSTED = 'frosted', _('Frosted')
            GOLD = 'gold', _('Gold')
            GREEN = 'green', _('Green')
            GREY = 'grey', _('Grey')
            HOLOGRAPHIC = 'holographic', _('Holographic')
            KHAKI = 'khaki', _('Khaki')
            MULTI_COLOR = 'multi_color', _('Multi Color')
            NAVY_BLUE = 'navy_blue', _('Navy Blue')
            OLIVE_GREEN = 'olive_green', _('Olive Green')
            ORANGE = 'orange', _('Orange')
            PINK = 'pink', _('Pink')
            PURPLE = 'purple', _('Purple')
            RED = 'red', _('Red')
            SILVER = 'silver', _('Silver')
            TRANSLUCENT = 'translucent', _('Translucent')
            TRANSPARENT = 'transparent', _('Transparent')
            UNKNOWN = 'unknown', _('Unknown')
            WHITE = 'white', _('White')
            YELLOW = 'yellow', _('Yellow')


    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    barcode = models.CharField(max_length=255, unique=True)
    brand = models.CharField(max_length=255, default='')
    product_name = models.CharField(max_length=255, default='')
    material_type = models.CharField(max_length=31, choices=MaterialType.choices)
    plastic_code = models.CharField(max_length=31, choices=PlasticCode.choices)
    rigidity = models.CharField(max_length=31, choices=RigidityType.choices, default=RigidityType.UNKNOWN)
    shape = models.CharField(max_length=31, choices=ShapeType.choices, default=ShapeType.UNKNOWN)
    content_type = models.CharField(max_length=31, choices=ContentType.choices, default=ContentType.UNKNOWN)
    hazardous = models.CharField(max_length=31, choices=Hazardous.choices, default=Hazardous.UNKNOWN)
    beverage_type = models.CharField(max_length=31, choices=BeverageType.choices, default=BeverageType.UNKNOWN)
    alcohol_percentage = models.FloatField(default=-1.0)
    alcoholic = models.CharField(max_length=31, choices=Alcoholic.choices, default=Alcoholic.NO)
    alcoholic_drinks_type = models.CharField(max_length=31, choices=AlcoholicDrinksType.choices, default=AlcoholicDrinksType.NA)
    wine_bottle_shape = models.CharField(max_length=31, choices=WineBottleShape.choices, default=WineBottleShape.NA)
    wine_type = models.CharField(max_length=31, choices=WineType.choices, default=WineType.NA)
    liquid_volume = models.FloatField()
    liquid_volume_unit = models.CharField(max_length=31, choices=LiquidVolumeUnit.choices)
    mass_gram = models.FloatField(default=0.0)
    ca = models.BooleanField(default=False)
    ct = models.BooleanField(default=False)
    gu = models.BooleanField(default=False)
    hi = models.BooleanField(default=False)
    ia = models.BooleanField(default=False)
    me = models.BooleanField(default=False)
    ma = models.BooleanField(default=False)
    mi = models.BooleanField(default=False)
    ny = models.BooleanField(default=False)
    Or = models.BooleanField(default=False)
    vt = models.BooleanField(default=False)
    made_in = models.CharField(max_length=31, choices=MadeIn.choices, default=MadeIn.UNK)
    juice_percentage = models.FloatField(default=-1.0)
    material_color = models.CharField(max_length=31, choices=MaterialColor.choices, default=MaterialColor.UNKNOWN)
    ribbed = models.CharField(max_length=31, choices=RibbedType.choices, default=RibbedType.NA)
    ringed = models.CharField(max_length=31, choices=RingedType.choices, default=RingedType.NA)
    visual_volume = models.CharField(max_length=31, choices=VisualVolume.choices, default=VisualVolume.NA)


    def __str__(self) -> str:
        return f'Container - id: {self.id}, created_at: {self.created_at},' \
               f'updated_at: {self.updated_at}, ' \
               f'barcode: {self.barcode}, ' \
               f'brand: {self.brand}, ' \
               f'product_name: {self.product_name}, ' \
               f'material_type: {self.material_type}, ' \
               f'plastic_code: {self.plastic_code}, '\
               f'liquid_volume: {self.liquid_volume}, '\
               f'liquid_volume_unit: {self.liquid_volume_unit}, '\
               f'mass_gram: {self.mass_gram}'


    def is_valid(self) -> Tuple[bool, str]:
        if self.material_type == Container.MaterialType.PLASTIC \
                and self.plastic_code == Container.PlasticCode.NA:
            return (False, 'Material type is plastic but the plastic code is NA.')

        return (True, '')


    @property
    def size(self) -> ContainerSize:
        return convert_to_size(self.liquid_volume, self.liquid_volume_unit)


def mk_container(barcode: str,
                 brand: str,
                 product_name: str,
                 material_type: Tuple[str, Any],
                 plastic_code: Tuple[str, Any],
                 liquid_volume: float,
                 liquid_volume_unit: Tuple[str, Any],
                 mass_gram: float,
                 ) -> Container:
    c = Container(barcode=barcode, brand=brand, product_name=product_name, material_type=material_type,
                  plastic_code=plastic_code, liquid_volume=liquid_volume,
                  liquid_volume_unit=liquid_volume_unit, mass_gram=mass_gram)
    print(f'mk_container() - c: {c}')
    return c


def mk_null_container() -> Container:
    return Container(material_type=Container.MaterialType.UNKNOWN,
                     plastic_code=Container.PlasticCode.UNKNOWN,
                     liquid_volume_unit=Container.LiquidVolumeUnit.NA)


class Image(models.Model):

    class LidCapType(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        TRUE = 'true', _('True')
        FALSE = 'false', _('False')

    class LablType(models.TextChoices):
        NECK_ONLY = 'neck_only', _('Neck Only')
        BODY_ONLY = 'body_only', _('Body Only')
        NEITHER = 'neither', _('Neither')
        NECK_AND_BODY = 'neck_and_body', _('Neck and Body')

    class OrientationType(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        STANDING_UP = 'standing_up', _('Standing Up')
        LEANING = 'leaning', _('Leaning')
        ORTHOGONAL = 'orthogonal', _('Orthogonal')
        PARALLEL = 'parallel', _('Parallel')

    class ImageQualityType(models.TextChoices):
        VALID_IMAGE = 'valid_image', _('Valid Image')
        INVALID_IMAGE = 'invalid_image', _('Invalid Image')
        UNKNOWN_IMAGE = 'unknown_image', _('Unknown Image')
        PARTIALLY_SHOWN = 'partially_shown', _('Partially Shown')
        BLURRY_MOVING_BELT = 'blurry_moving_belt', _('Blurry Moving Belt')
        OUT_OF_FOCUS = 'out_of_focus', _('Out of Focus')
        BAD_LIGHTING = 'bad_lighting', _('Bad Lighting')
        BLURRY_MOVING_CONTAINER = 'blurry_moving_container', _('Blurry Moving Container')

    class HandsType(models.TextChoices):
        NO_HANDS = 'no_hands', _('No Hands')
        HANDS = 'hands', _('Hands')
        BLURRY_HANDS_IN = 'blurry_hands_in', _('Blurry Hands In')
        BLURRY_HANDS_OUT = 'blurry_hands_out', _('Blurry Hands Out')

    class CountType(models.TextChoices):
        EMPTY = 'empty', _('Empty')
        SOLO = 'solo', _('Solo')
        MULTIPLE = 'multiple', _('Multiple')



    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    container = models.ForeignKey(Container, null=True, on_delete=models.CASCADE)
    deposit_id = models.CharField(max_length=255, default='')
    image_id = models.CharField(max_length=255, default='')
    aws_entity_tag = models.CharField(max_length=511, unique=True)
    s3_bucket_name = models.CharField(max_length=63)
    aws_region_name = models.CharField(max_length=63)
    s3_object_key = models.CharField(max_length=511, unique=True)
    lid_cap = models.CharField(max_length=31, choices=LidCapType.choices, default=LidCapType.UNKNOWN)
    crush_degree = models.IntegerField()
    label = models.CharField(max_length=31, choices=LablType.choices, default=LablType.BODY_ONLY)
    orientation_style = models.CharField(max_length=31, choices=OrientationType.choices, default=OrientationType.UNKNOWN)
    valid_orientation = models.BooleanField()
    image_quality = models.CharField(max_length=31, choices=ImageQualityType.choices, default=ImageQualityType.UNKNOWN_IMAGE)
    container_in_frame = models.FloatField(default=-1.0)
    image_height = models.FloatField(default=-1.0)
    image_width = models.FloatField(default=-1.0)
    hands_in_image = models.CharField(max_length=31, choices=HandsType.choices, default=HandsType.NO_HANDS)
    count = models.CharField(max_length=31, choices=CountType.choices, default=CountType.SOLO)
    imager_version = models.CharField(max_length=255, default='unknown')
    timestamp = models.DateTimeField(null=True, blank=True, default=None)
    company_name = models.CharField(max_length=255, default='unknown')
    store_name = models.CharField(max_length=255, default='unknown')
    cube_sn = models.CharField(max_length=255, default='unknown')
    database_version = models.IntegerField(default=1)



    def url(self):
        return url_from_s3_data(self.s3_bucket_name, self.aws_region_name, convert_spaces_to_pluses(self.s3_object_key))

    def image(self):
        img_src = self.url()
        return format_html('<img src="{}" style="width: 100%; max-width: 500px" />', img_src)

def load_models_from_csv(dir_name: str) -> None:
    logging.info('reading and saving containers')
    fp = os.path.join(dir_name, 'container.csv')

    containers_all = read_csv_with_headers(fp)

    num_containers = len(containers_all)
    logging.info(f'load_models_from_csv() - num_containers: {num_containers}')

    for row in containers_all:
        barcode = row['barcode']
        logging.info(f'barcode: {barcode}')

        c = Container(barcode=barcode,
                      brand=row['brand'],
                      product_name=row['product_name'],
                      material_type=row['material_type'],
                      plastic_code=row['plastic_code'],
                      liquid_volume=row['liquid_volume'],
                      liquid_volume_unit=row['liquid_volume_unit'],
                      mass_gram=row['mass_grams'],
                      ca=row['CA'],
                      ct=row['CT'],
                      )
        c.save()

    logging.info('reading and saving images')
    fp = os.path.join(dir_name, 'image.csv')
    images_all = read_csv_with_headers(fp)

    num_images = len(images_all)
    logging.info(f'load_models_from_csv() - num_images: {num_images}')

    for row in images_all:
        barcode = row['barcode']
        aws_entity_tag = row['aws_entity_tag']
        s3_bucket_name, aws_region_name, s3_object_key = s3_data_from_object_url(row['aws_object_url'])
        logging.info(f'barcode: {barcode}, aws_entity_tag: {aws_entity_tag}, s3_object_key: {s3_object_key}')

        query_set = Container.objects.filter(barcode=barcode)
        num_containers = len(query_set)

        if num_containers > 1:
            logging.error(f'Found {num_containers} containers with barcode {barcode}, '
                          'but there should have been 1 or none. Skipping this image.')
            break

        c: Optional[Container] = query_set[0] if num_containers == 1 else None

        Image.objects.create(container=c,
                             aws_entity_tag=aws_entity_tag,
                             s3_bucket_name=s3_bucket_name,
                             aws_region_name=aws_region_name,
                             s3_object_key=s3_object_key,
                             crush_degree=row['crush_degree'],
                             valid_orientation=row['valid_orientation']
                             )



OUNCES_PER_LITER = 33.814
MILLIS = 1000
OUNCES_PER_MILLILITER = OUNCES_PER_LITER / MILLIS


def convert_to_liquid_ounces(liquid_volume: float, liquid_volume_unit: Container.LiquidVolumeUnit) -> float:
    if liquid_volume_unit == Container.LiquidVolumeUnit.OZ:
        return liquid_volume
    elif liquid_volume_unit == Container.LiquidVolumeUnit.ML:
        return liquid_volume * OUNCES_PER_MILLILITER
    elif liquid_volume_unit == Container.LiquidVolumeUnit.LITER:
        return liquid_volume * OUNCES_PER_LITER
    elif liquid_volume_unit == Container.LiquidVolumeUnit.NA:
        return -1.0
    elif liquid_volume_unit == Container.LiquidVolumeUnit.UNKNOWN:
        return -1.0
    else:
        raise ValueError(f'Unknown liquid_volume_unit: {liquid_volume_unit}')



def convert_to_size(liquid_volume: float, liquid_volume_unit: Container.LiquidVolumeUnit) -> ContainerSize:
    liquid_ounces = convert_to_liquid_ounces(liquid_volume, liquid_volume_unit)
    if liquid_ounces < 0:
        return ContainerSize.UNKNOWN
    if liquid_ounces < 24:
        return ContainerSize.LT_24_OZ

    return ContainerSize.GTE_24_OZ