# -*- coding: utf-8 -*-
import os
import mimetypes
from io import BytesIO
from datetime import datetime
from urllib2 import unquote

from PIL import Image
import pytz
from nereid.helpers import send_file
from nereid import url_for, route, abort
from jinja2 import Markup
from werkzeug.utils import secure_filename

from trytond.pool import PoolMeta
from trytond.transaction import Transaction

__all__ = ['NereidStaticFile', 'TransformationCommand']
__metaclass__ = PoolMeta

FILTER_MAP = {
    '': Image.NEAREST,
    'n': Image.NEAREST,
    'b': Image.BILINEAR,
    'c': Image.BICUBIC,
    'a': Image.ANTIALIAS,
}


class TransformationCommand(object):
    """
    >>> c = TransformationCommand()
    >>> c.thumbnail(128, 128)
    TransformationCommand(['thumbnail,w_128,h_128,m_n'])
    >>> c.resize(100, 100)
    TransformationCommand(
        ['thumbnail,w_128,h_128,m_n', 'resize,w_100,h_100,m_n']
    )
    >>> c
    TransformationCommand(
        ['thumbnail,w_128,h_128,m_n', 'resize,w_100,h_100,m_n']
    )
    >>> str(c)
    'thumbnail,w_128,h_128,m_n/resize,w_100,h_100,m_n'
    """

    def __init__(self, commands=None):
        if commands is not None:
            self.commands = commands[:]
        else:
            self.commands = []

    def __repr__(self):
        return u'TransformationCommand(%s)' % self.commands

    def __str__(self):
        return '/'.join(self.commands)

    def __unicode__(self):
        return u'/'.join(self.commands)

    def thumbnail(self, width, height, mode='n'):
        """
        Returns a resize command. To understand more about the arguments see
        `pil documentation
        <http://www.pythonware.com/library/pil/handbook/image.htm>`_

        :param width: Width of the image
        :param height: Height og the image
        :param mode: Filter to use
                      * n - NEAREST
                      * l - BILINEAR
                      * c - BICUBIC
                      * a - ANTIALIAS (best quality)
        """
        arguments = ['thumbnail']
        arguments.append('w_%s' % width)
        arguments.append('h_%s' % height)
        if mode:
            arguments.append('m_%s' % mode)

        self.commands.append(','.join(arguments))
        return self

    def resize(self, width, height, mode='n'):
        """
        Returns a resize command. To understand more about the arguments see
        `pil documentation
        <http://www.pythonware.com/library/pil/handbook/image.htm>`_

        :param width: Width of the image
        :param height: Height og the image
        :param mode: Filter to use
                      * n - NEAREST
                      * l - BILINEAR
                      * c - BICUBIC
                      * a - ANTIALIAS (best quality)
        """
        arguments = ['resize']
        arguments.append('w_%s' % width)
        arguments.append('h_%s' % height)
        if mode:
            arguments.append('m_%s' % mode)

        self.commands.append(','.join(arguments))
        return self

    @staticmethod
    def parse_command(command):
        """
        Parse the given commands to a dictionary of command parameters

        :param command: A special command to be parsed
        :return: A tuple of the operation to be done and parameters for it
        """
        command = unquote(unicode(command))

        try:
            operation, params = command.split(',', 1)
        except ValueError:
            abort(404)

        return operation, dict(
            map(lambda arg: arg.split('_'), params.split(','))
        )


class StaticFileTransformationCommand(TransformationCommand):
    """
    A helper class which can be chained to build resizable image
    urls.

    """
    def __init__(self, static_file, extension=None, commands=None):
        """
        :param static_file: ID of static_file or Active Record
        :param extension: File extension to use
        :param commands: A list of commands (optional)
        """
        self.static_file = static_file
        self.extension = extension or \
            os.path.splitext(static_file.name)[1][1:] or 'png'
        super(StaticFileTransformationCommand, self).__init__(commands)

    def __html__(self):
        return Markup(self.url())

    def url(self, **kwargs):
        """
        Constructs a URL based on the static file and the commands

        .. versionchanged::3.2.0.2

            Supports keyword arguments passed to the url builder

        """
        return url_for(
            'nereid.static.file.transform_static_file',
            active_id=int(self.static_file), commands=unicode(self),
            extension=self.extension, **kwargs
        )


class NereidStaticFile:
    __name__ = "nereid.static.file"

    allowed_operations = ['resize', 'thumbnail']

    @staticmethod
    def thumbnail(image, w=128, h=128, m='n'):
        """
        :param image: Image instance
        :param w: width
        :param h: height
        :param m: mode for the resize operation
                      * n - NEAREST
                      * l - BILINEAR
                      * c - BICUBIC
                      * a - ANTIALIAS (best quality)
        """
        image.thumbnail((int(w), int(h)), FILTER_MAP[m])
        return image

    @staticmethod
    def resize(image, w=128, h=128, m='n'):
        """
        :param image: Image instance
        :param w: width
        :param h: height
        :param m: mode for the resize operation
                      * n - NEAREST
                      * l - BILINEAR
                      * c - BICUBIC
                      * a - ANTIALIAS (best quality)
        """
        return image.resize((int(w), int(h)), FILTER_MAP[m])

    def _transform_static_file(self, commands, extension, filename):
        """
        Transform the static file and send the transformed file

        :param commands: A list of commands separated by /
        :param extension: The image format to use
        :param filename: The file to which the transformed image
                         needs to be written
        """
        # Ugly hack '[:]' to fix issue in python 2.7.3
        image_file = Image.open(BytesIO(self.file_binary[:]))

        parse_command = TransformationCommand.parse_command

        for command in commands.split('/'):
            operation, params = parse_command(command)
            if operation not in self.allowed_operations:
                abort(404)
            image_file = getattr(self, operation)(image_file, **params)

        image_file.save(filename)

    @route('/static-file-transform/<int:active_id>/<path:commands>.<extension>')
    def transform_static_file(self, commands, extension):
        """
        Transform the static file and send the transformed file

        :param commands: A list of commands separated by /
        :param extension: The image format to use
        """
        tmp_folder = os.path.join(
            '/tmp/nereid/', Transaction().database.name, str(self.id)
        )

        try:
            os.makedirs(tmp_folder)
        except OSError, err:
            if err.errno == 17:
                # directory exists
                pass
            else:
                raise

        filename = os.path.join(
            tmp_folder, '%s.%s' % (secure_filename(commands), extension)
        )
        file_date = os.path.exists(filename) and datetime.fromtimestamp(
            os.path.getmtime(filename), pytz.timezone('UTC')
        )

        if not file_date or (
            self.write_date and file_date < pytz.UTC.localize(self.write_date)
        ):
            self._transform_static_file(commands, extension, filename)

        rv = send_file(filename)
        rv.headers['Content-Type'] = mimetypes.guess_type(
            'something.%s' % extension
        )[0]
        rv.headers['Cache-Control'] = 'public, max-age=%d' % 86400
        return rv

    def transform_command(self):
        """
        Returns a chainable StaticFileTransformationCommand object for this
        static file
        """
        return StaticFileTransformationCommand(self)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
