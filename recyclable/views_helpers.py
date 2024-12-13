from typing import List
import logging
from dataclasses import dataclass, asdict
import json

from enum import Enum, StrEnum, auto
from typing import Optional

from django.db.models import Q

from recyclable.models import Image, ContainerSize, Container

# type S3ObjectKey = str
# type JSON = str


@dataclass
class SizeClassifier:
    lt24oz: list[str]
    gte24oz: list[str]


class Count(Enum):
    EMPTY = 'empty'
    SOLO = 'solo'
    MULTIPLE = 'multiple'

@dataclass
class CountClassifier:
    empty: list[str]
    solo: list[str]
    multiple: list[str]



class DepositClass(StrEnum):
    ALU = auto()
    GLASS = auto()
    PET = auto()
    INVALID_AEROSOL = auto()
    INVALID_BAD_IMAGE = auto()
    INVALID_BAD_ORIENTATION = auto()
    INVALID_BIMETAL = auto()
    INVALID_CAN = auto()
    INVALID_CANDY = auto()
    INVALID_CRUSHED_ALU = auto()
    INVALID_CRUSHED_PET = auto()
    INVALID_DAIRY_PROTEIN = auto()
    INVALID_JARS = auto()
    INVALID_LIQUOR = auto()
    INVALID_NO_LABEL_REST = auto()
    INVALID_REST = auto()
    INVALID_SMALL_PROBIOTIC_REST = auto()
    LIQUOR_GLASS = auto()
    LIQUOR_PET = auto()
    NO_LABEL_PET = auto()
    NOT_CLASSIFIED = auto()



# IMPORTANT NOTE: For each classifier, an image must not belong to more than one class.

def create_count_classifier_json() -> str:
    return "Not implemented yet"

def create_size_classifier_json() -> str:
    valid_containers = Container.objects.filter(
        Q(ca=True) &
        Q(material_type__in=[
            Container.MaterialType.ALUMINUM,
            Container.MaterialType.GLASS,
            Container.MaterialType.PLASTIC
        ])
    )

    lt24oz_urls: List[str] = []
    gte24oz_urls: List[str] = []

    for c in valid_containers:
        imgs = Image.objects.filter(
            Q(container=c) &
            Q(valid_orientation=True) &
            Q(crush_degree__in=[0, 1])
        )

        if c.visual_volume == Container.VisualVolume.LT_24OZ:
            lt24oz_urls.extend([img.url() for img in imgs])
        elif c.visual_volume == Container.VisualVolume.GT_24OZ:
            gte24oz_urls.extend([img.url() for img in imgs])

    classifier = SizeClassifier(lt24oz_urls, gte24oz_urls)
    return json.dumps(asdict(classifier))

def is_valid_container_image(img: Image) -> bool:
    return (img.valid_orientation and
            (img.crush_degree == 0 or img.crush_degree == 1))


def classify_deposit_image(img: Image) -> DepositClass:

    # TODO: This is just a POC.  The priorities of the different classifications need to be
    #       determined and implemented correctly.

    if img.container is None:
        logging.error(f'classify_deposit_image() - image {img} has no container')
        return DepositClass.NOT_CLASSIFIED

    c: Container = img.container

    if is_valid_container_image(img):

        match c.material_type:
            case Container.MaterialType.ALUMINUM:
                return DepositClass.ALU
            case Container.MaterialType.BIMETAL:
                return DepositClass.INVALID_BIMETAL
            case Container.MaterialType.CARDBOARD:
                return DepositClass.INVALID_REST
            case Container.MaterialType.FOIL_LAMINATE:
                return DepositClass.INVALID_REST
            case Container.MaterialType.GLASS:
                return DepositClass.GLASS
            case Container.MaterialType.PAPER:
                return DepositClass.INVALID_REST
            case Container.MaterialType.PLASTIC:
                return DepositClass.PET
            case Container.MaterialType.OTHER:
                return DepositClass.INVALID_REST
            case Container.MaterialType.UNKNOWN:
                return DepositClass.INVALID_REST
            case _:
                logging.error(f'classify_deposit_image() - unhandled material_type: {c.material_type}')

    if not img.valid_orientation:
        return DepositClass.INVALID_BAD_ORIENTATION

    if img.crush_degree > 1:
        match Container.MaterialType(c.material_type):
            case Container.MaterialType.ALUMINUM:
                return DepositClass.INVALID_CRUSHED_ALU
            case Container.MaterialType.PLASTIC:
                return DepositClass.INVALID_CRUSHED_PET
            case _:
                pass

    # TODO: add the rest of the deposit classes

    logging.error(f'classify_deposit_image() - unhandled image: {img}')
    return DepositClass.NOT_CLASSIFIED



def create_deposit_classifier_json() -> str:

    classification_dict: dict[str, list[str]] = {
        DepositClass.ALU: [],
        DepositClass.GLASS: [],
        DepositClass.PET: [],
        DepositClass.INVALID_AEROSOL: [],
        DepositClass.INVALID_BAD_IMAGE: [],
        DepositClass.INVALID_BAD_ORIENTATION: [],
        DepositClass.INVALID_BIMETAL: [],
        DepositClass.INVALID_CAN: [],
        DepositClass.INVALID_CANDY: [],
        DepositClass.INVALID_CRUSHED_ALU: [],
        DepositClass.INVALID_CRUSHED_PET: [],
        DepositClass.INVALID_DAIRY_PROTEIN: [],
        DepositClass.INVALID_JARS: [],
        DepositClass.INVALID_LIQUOR: [],
        DepositClass.INVALID_NO_LABEL_REST: [],
        DepositClass.INVALID_REST: [],
        DepositClass.INVALID_SMALL_PROBIOTIC_REST: [],
        DepositClass.LIQUOR_GLASS: [],
        DepositClass.LIQUOR_PET: [],
        DepositClass.NO_LABEL_PET: [],
        DepositClass.NOT_CLASSIFIED: [],
    }

    images = Image.objects.all()

    for img in images:
        cls = classify_deposit_image(img)
        classification_dict[cls.__str__()].append(img.url())

    # print(f'create_deposit_classifier_json() - classifier: {classifier}')

    return json.dumps(classification_dict)
