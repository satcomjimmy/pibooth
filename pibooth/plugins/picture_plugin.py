# -*- coding: utf-8 -*-

import os
import os.path as osp
import itertools
import pibooth
from pibooth.utils import timeit, PoolingTimer
from pibooth.pictures import get_picture_factory


class PicturePlugin(object):

    """Plugin to build the final picture.
    """

    def __init__(self):
        self.picture_destroy_timer = PoolingTimer(0)
        self.second_previous_picture = None

    def _reset_vars(self, app):
        """Destroy final picture (can not be used anymore).
        """
        app.factory_pool.clear()
        app.previous_picture = None
        app.previous_animated = None
        app.previous_picture_file = None

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        """Reset variables set in this plugin.
        """
        self._reset_vars(app)

    @pibooth.hookimpl
    def state_wait_enter(self, cfg, app):
        animated = app.factory_pool.get()
        if animated:
            app.previous_animated = itertools.cycle(animated)

        # Reset timeout in case of settings changed
        self.picture_destroy_timer.timeout = max(0, cfg.getfloat('WINDOW', 'final_image_delay'))
        self.picture_destroy_timer.start()

    @pibooth.hookimpl
    def state_wait_do(self, cfg, app):
        if cfg.getfloat('WINDOW', 'final_image_delay') > 0 and self.picture_destroy_timer.is_timeout():
            self._reset_vars(app)

    @pibooth.hookimpl
    def state_processing_enter(self, app):
        self.second_previous_picture = app.previous_picture
        self._reset_vars(app)

    @pibooth.hookimpl
    def state_processing_do(self, cfg, app):
        with timeit("Creating the final picture"):
            captures = app.camera.get_captures()

            backgrounds = cfg.gettuple('PICTURE', 'backgrounds', ('color', 'path'), 2)
            if app.capture_nbr == app.capture_choices[0]:
                background = backgrounds[0]
            else:
                background = backgrounds[1]

            overlays = cfg.gettuple('PICTURE', 'overlays', 'path', 2)
            if app.capture_nbr == app.capture_choices[0]:
                overlay = overlays[0]
            else:
                overlay = overlays[1]

            texts = [cfg.get('PICTURE', 'footer_text1').strip('"'),
                     cfg.get('PICTURE', 'footer_text2').strip('"')]
            colors = cfg.gettuple('PICTURE', 'text_colors', 'color', len(texts))
            text_fonts = cfg.gettuple('PICTURE', 'text_fonts', str, len(texts))
            alignments = cfg.gettuple('PICTURE', 'text_alignments', str, len(texts))

            def _setup_factory(m):
                m.set_background(background)
                if any(elem != '' for elem in texts):
                    for params in zip(texts, text_fonts, colors, alignments):
                        m.add_text(*params)
                if cfg.getboolean('PICTURE', 'captures_cropping'):
                    m.set_cropping()
                if overlay:
                    m.set_overlay(overlay)
                if cfg.getboolean('GENERAL', 'debug'):
                    m.set_outlines()

            factory = get_picture_factory(captures, cfg.get('PICTURE', 'orientation'))
            _setup_factory(factory)
            app.previous_picture = factory.build()

        savedir = cfg.getpath('GENERAL', 'directory')
        app.previous_picture_file = osp.join(savedir, osp.basename(app.dirname) + "_pibooth.jpg")
        factory.save(app.previous_picture_file)

        if cfg.getboolean('WINDOW', 'animate') and app.capture_nbr > 1:
            with timeit("Asyncronously generate pictures for animation"):
                for capture in captures:
                    factory = get_picture_factory((capture,), cfg.get('PICTURE', 'orientation'), force_pil=True)
                    _setup_factory(factory)
                    app.factorys_pool.add(factory)

    @pibooth.hookimpl
    def state_print_do(self, cfg, app, events):
        if app.find_capture_event(events):
            with timeit("Putting the capture in the forget folder"):
                file_dir, file_name = osp.split(app.previous_picture_file)
                forget_dir = osp.join(file_dir, "forget")
                if not os.path.exists(forget_dir):
                    os.makedirs(forget_dir)
                os.rename(app.previous_picture_file, osp.join(forget_dir, file_name))
                self._reset_vars(app)
                app.previous_picture = self.second_previous_picture
                app.nbr_duplicates = cfg.getint('PRINTER', 'max_duplicates') + 1
