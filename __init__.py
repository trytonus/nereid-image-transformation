from trytond.pool import Pool
from static_file import NereidStaticFile


def register():
    Pool.register(
        NereidStaticFile,
        module='nereid_image_transformation', type_='model')
