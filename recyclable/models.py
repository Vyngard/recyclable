import os
import traceback
from datetime import datetime
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

    class Rigidity(models.TextChoices):
        RIGID = 'rigid', _('Rigid')
        FLEXIBLE = 'flexible', _('Flexible')
        UNKNOWN = 'unknown', _('Unknown')

    class Shape(models.TextChoices):
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

    class Contents(models.TextChoices):
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
    rigidity = models.CharField(max_length=31, choices=Rigidity.choices, default=Rigidity.RIGID)
    shape = models.CharField(max_length=31, choices=Shape.choices, default=Shape.UNKNOWN)
    content_type = models.CharField(max_length=31, choices=Contents.choices, default=Contents.UNKNOWN)
    hazardous = models.CharField(max_length=31, choices=Hazardous.choices, default=Hazardous.UNKNOWN)
    beverage_type = models.CharField(max_length=31, choices=BeverageType.choices, default=BeverageType.UNKNOWN)
    alcohol_percentage = models.FloatField(default=-1.0, blank=False)
    alcoholic = models.CharField(max_length=31, choices=Alcoholic.choices, default=Alcoholic.NO)
    alcoholic_drinks_type = models.CharField(max_length=31, choices=AlcoholicDrinksType.choices, default=AlcoholicDrinksType.NA)
    wine_bottle_shape = models.CharField(max_length=31, choices=WineBottleShape.choices, default=WineBottleShape.NA)
    wine_type = models.CharField(max_length=31, choices=WineType.choices, default=WineType.NA)
    liquid_volume = models.FloatField(default=-1.0, blank=False)
    liquid_volume_unit = models.CharField(max_length=31, choices=LiquidVolumeUnit.choices)
    mass_gram = models.FloatField(default=-1.0, blank=False)
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
    juice_percentage = models.FloatField(default=-1.0)
    material_color = models.CharField(max_length=31, choices=MaterialColor.choices, default=MaterialColor.UNKNOWN)
    ribbed = models.CharField(max_length=31, choices=RibbedType.choices, default=RibbedType.NA)
    ringed = models.CharField(max_length=31, choices=RingedType.choices, default=RingedType.NA)
    visual_volume = models.CharField(max_length=31, choices=VisualVolume.choices, default=VisualVolume.NA)
    made_in = models.CharField(max_length=3, blank=False, null=False, help_text='Enter the 3-letter country code.', default='UNK')


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


def mk_container(
    barcode: str,
    brand: str,
    product_name: str,
    material_type: str,
    plastic_code: str,
    liquid_volume: float,
    liquid_volume_unit: str,
    mass_gram: float,
    made_in: str,
    rigidity: str = Container.Rigidity.RIGID,
    shape: str = Container.Shape.UNKNOWN,
    content_type: str = Container.Contents.UNKNOWN,
    hazardous: str = Container.Hazardous.UNKNOWN,
    beverage_type: str = Container.BeverageType.UNKNOWN,
    alcohol_percentage: float = -1.0,
    alcoholic: str = Container.Alcoholic.NO,
    alcoholic_drinks_type: str = Container.AlcoholicDrinksType.NA,
    wine_bottle_shape: str = Container.WineBottleShape.NA,
    wine_type: str = Container.WineType.NA,
    juice_percentage: float = -1.0,
    material_color: str = Container.MaterialColor.UNKNOWN,
    ribbed: str = Container.RibbedType.NA,
    ringed: str = Container.RingedType.NA,
    visual_volume: str = Container.VisualVolume.NA,
    ca: bool = False,
    ct: bool = False,
    gu: bool = False,
    hi: bool = False,
    ia: bool = False,
    me: bool = False,
    ma: bool = False,
    mi: bool = False,
    ny: bool = False,
    Or: bool = False,
    vt: bool = False,
) -> Container:
    c = Container(
        barcode=barcode,
        brand=brand,
        product_name=product_name,
        material_type=material_type,
        plastic_code=plastic_code,
        liquid_volume=liquid_volume,
        liquid_volume_unit=liquid_volume_unit,
        mass_gram=mass_gram,
        made_in=made_in,
        rigidity=rigidity,
        shape=shape,
        content_type=content_type,
        hazardous=hazardous,
        beverage_type=beverage_type,
        alcohol_percentage=alcohol_percentage,
        alcoholic=alcoholic,
        alcoholic_drinks_type=alcoholic_drinks_type,
        wine_bottle_shape=wine_bottle_shape,
        wine_type=wine_type,
        juice_percentage=juice_percentage,
        material_color=material_color,
        ribbed=ribbed,
        ringed=ringed,
        visual_volume=visual_volume,
        ca=ca,
        ct=ct,
        gu=gu,
        hi=hi,
        ia=ia,
        me=me,
        ma=ma,
        mi=mi,
        ny=ny,
        Or=Or,
        vt=vt,
    )
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

    class LabelType(models.TextChoices):
        NECK_ONLY = 'neck_only', _('Neck Only')
        BODY_ONLY = 'body_only', _('Body Only')
        NEITHER = 'neither', _('Neither')
        NECK_AND_BODY = 'neck_and_body', _('Neck and Body')

    class Orientation(models.TextChoices):
        UNKNOWN = 'unknown', _('Unknown')
        STANDING_UP = 'standing_up', _('Standing Up')
        LEANING = 'leaning', _('Leaning')
        ORTHOGONAL = 'orthogonal', _('Orthogonal')
        PARALLEL = 'parallel', _('Parallel')

    class ImageQuality(models.TextChoices):
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
    deposit_id = models.CharField(max_length=255, default='', blank=True)
    image_id = models.CharField(max_length=255, default='', blank=True)
    image_sequence_number = models.IntegerField(default=0)
    aws_entity_tag = models.CharField(max_length=511, unique=True)
    s3_bucket_name = models.CharField(max_length=63)
    aws_region_name = models.CharField(max_length=63)
    s3_object_key = models.CharField(max_length=511, unique=True)
    lid_cap = models.CharField(max_length=31, choices=LidCapType.choices, default=LidCapType.UNKNOWN)
    crush_degree = models.IntegerField(blank=False)
    label = models.CharField(max_length=31, choices=LabelType.choices, default=LabelType.BODY_ONLY)
    orientation_style = models.CharField(max_length=31, choices=Orientation.choices, default=Orientation.UNKNOWN)
    valid_orientation = models.BooleanField()
    image_quality = models.CharField(max_length=31, choices=ImageQuality.choices, default=ImageQuality.VALID_IMAGE)
    container_in_frame = models.FloatField(null=True, blank=False)
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



    def url(self) -> str:
        return url_from_s3_data(self.s3_bucket_name, self.aws_region_name, convert_spaces_to_pluses(self.s3_object_key))

    def image(self) -> str:
        img_src = self.url()
        return format_html('<img src="{}" style="width: 100%; max-width: 500px" />', img_src)

    def __str__(self) -> str:
        barcode = self.container.barcode if self.container else 'Unknown'
        return f"{barcode} (Image {self.image_sequence_number})"

    # Override the save method to handle sequence numbering
    def save(self, *args, **kwargs) -> None:
        if not self.pk:
            last_image = Image.objects.filter(container=self.container).order_by('-image_sequence_number').first()
            if last_image:
                self.image_sequence_number = last_image.image_sequence_number + 1
            else:
                self.image_sequence_number = 1
        super().save(*args, **kwargs)


def load_models_from_csv(dir_name: str) -> None:
    logging.info('reading and saving containers')
    fp = os.path.join(dir_name, 'container.csv')

    containers_all = read_csv_with_headers(fp)

    num_containers = len(containers_all)
    logging.info(f'load_models_from_csv() - num_containers: {num_containers}')

    for row in containers_all:
        barcode = row.get('barcode', '').strip()
        if not barcode:
            logging.warning('Skipping container with missing barcode.')
            continue
        logging.info(f'Processing container with barcode: {barcode}')

        # Prepare a dictionary for container fields
        container_fields = {
            'barcode': barcode,
            'brand': row.get('brand', '').strip(),
            'product_name': row.get('product_name', '').strip(),
            'material_type': row.get('material_type', '').strip(),
            'plastic_code': row.get('plastic_code', '').strip(),
            'rigidity': row.get('rigidity', '').strip(),
            'shape': row.get('shape', '').strip(),
            'content_type': row.get('content_type', '').strip(),
            'hazardous': row.get('hazardous', '').strip(),
            'beverage_type': row.get('beverage_type', '').strip(),
            'alcohol_percentage': float_or_default(row.get('alcohol_percentage', ''), -1.0),
            'alcoholic': row.get('alcoholic', '').strip(),
            'alcoholic_drinks_type': row.get('alcoholic_drinks_type', '').strip(),
            'wine_bottle_shape': row.get('wine_bottle_shape', '').strip(),
            'wine_type': row.get('wine_type', '').strip(),
            'liquid_volume': float_or_default(row.get('liquid_volume', ''), -1.0),
            'liquid_volume_unit': row.get('liquid_volume_unit', '').strip(),
            'mass_gram': float_or_default(row.get('mass_gram', ''), -1.0),
            'ca': str_to_bool(row.get('CA', 'False')),
            'ct': str_to_bool(row.get('CT', 'False')),
            'gu': str_to_bool(row.get('GU', 'False')),
            'hi': str_to_bool(row.get('HI', 'False')),
            'ia': str_to_bool(row.get('IA', 'False')),
            'me': str_to_bool(row.get('ME', 'False')),
            'ma': str_to_bool(row.get('MA', 'False')),
            'mi': str_to_bool(row.get('MI', 'False')),
            'ny': str_to_bool(row.get('NY', 'False')),
            'Or': str_to_bool(row.get('OR', 'False')),
            'vt': str_to_bool(row.get('VT', 'False')),
            'juice_percentage': float_or_default(row.get('juice_percentage', ''), -1.0),
            'material_color': row.get('material_color', '').strip(),
            'ribbed': row.get('ribbed', '').strip(),
            'ringed': row.get('ringed', '').strip(),
            'visual_volume': row.get('visual_volume', '').strip(),
            'made_in': row.get('made_in', '').strip().upper(),
        }

        # Create or update the Container instance
        c, created = Container.objects.update_or_create(
            barcode=barcode,
            defaults=container_fields
        )
        if created:
            logging.info(f'Created new container with barcode: {barcode}')
        else:
            logging.info(f'Updated existing container with barcode: {barcode}')

    logging.info('reading and saving images')
    fp = os.path.join(dir_name, 'image.csv')
    images_all = read_csv_with_headers(fp)

    num_images = len(images_all)
    logging.info(f'load_models_from_csv() - num_images: {num_images}')

    for row in images_all:
        barcode = row.get('barcode', '').strip()
        aws_entity_tag = row.get('aws_entity_tag', '').strip()
        s3_bucket_name = row.get('s3_bucket_name', '').strip()
        aws_region_name = row.get('aws_region_name', '').strip()
        image_name = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        file_name = f'{c.barcode}_{image_name}.png'
        s3_object_key = f'images/{c.barcode}/{file_name}'

        if not barcode:
            logging.warning('Skipping image with missing barcode.')
            continue
        elif not aws_entity_tag:
            logging.warning('Skipping image with missing aws_entity_tag.')
            continue
        elif not s3_object_key:
            logging.warning('Skipping image with missing s3_object_key.')
            continue

        if 'aws_object_url' in row and not s3_bucket_name and not aws_region_name and not s3_object_key:
            s3_bucket_name, aws_region_name, s3_object_key = s3_data_from_object_url(row['aws_object_url'])

        logging.info(f'Processing image for barcode: {barcode}, aws_entity_tag: {aws_entity_tag}')

        try:
            c = Container.objects.get(barcode=barcode)
        except Container.DoesNotExist:
            logging.error(f'No container found with barcode {barcode}. Skipping this image.')
            continue

        # Prepare a dictionary for image fields
        image_fields = {
            'container': c,
            'aws_entity_tag': aws_entity_tag,
            's3_bucket_name': s3_bucket_name,
            'aws_region_name': aws_region_name,
            's3_object_key': s3_object_key,
            'deposit_id': row.get('deposit_id', '').strip(),
            'image_id': row.get('image_id', '').strip(),
            'image_sequence_number': int_or_default(row.get('image_sequence_number', ''), 0),
            'lid_cap': row.get('lid_cap', '').strip(),
            'crush_degree': int_or_default(row.get('crush_degree', ''), 0),
            'label': row.get('label', '').strip(),
            'orientation_style': row.get('orientation_style', '').strip(),
            'valid_orientation': str_to_bool(row.get('valid_orientation', 'False')),
            'image_quality': row.get('image_quality', '').strip(),
            'container_in_frame': float_or_default(row.get('container_in_frame', ''), None),
            'image_height': float_or_default(row.get('image_height', ''), -1.0),
            'image_width': float_or_default(row.get('image_width', ''), -1.0),
            'hands_in_image': row.get('hands_in_image', '').strip(),
            'count': row.get('count', '').strip(),
            'imager_version': row.get('imager_version', '').strip(),
            'timestamp': parse_datetime_or_none(row.get('timestamp', '')),
            'company_name': row.get('company_name', '').strip(),
            'store_name': row.get('store_name', '').strip(),
            'cube_sn': row.get('cube_sn', '').strip(),
            'database_version': int_or_default(row.get('database_version', ''), 1),
        }

        try:
            # Create the Image instance
            Image.objects.create(**image_fields)
            logging.info(f'Created image with aws_entity_tag: {aws_entity_tag}')
        except Exception as e:
            logging.error(f'Error creating image for barcode {barcode}: {e}')
            logging.error(traceback.format_exc())


def str_to_bool(value: str) -> bool:
    return value.strip().lower() in ['true', 't', 'yes', '1']

def int_or_default(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default

def float_or_default(value: str, default: float) -> float:
    try:
        return float(value)
    except ValueError:
        return default

def parse_datetime_or_none(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


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