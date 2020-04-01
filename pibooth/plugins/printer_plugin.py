# -*- coding: utf-8 -*-

import pibooth
from pibooth.utils import LOGGER, timeit


class PrinterPlugin(object):

    """Plugin to manage the printer.
    """

    @pibooth.hookimpl
    def pibooth_startup(self, app):
        app.printer.nbr_printed = 0

    @pibooth.hookimpl
    def pibooth_cleanup(self, app):
        app.printer.quit()

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        """Reset variables set in this plugin.
        """
        app.nbr_duplicates = 0

    @pibooth.hookimpl
    def state_wait_do(self, cfg, app, events):
        if app.find_print_event(events) and app.previous_picture_file and app.printer.is_installed():

            if app.nbr_duplicates >= cfg.getint('PRINTER', 'max_duplicates'):
                LOGGER.warning("Too many duplicates sent to the printer (%s max)",
                               cfg.getint('PRINTER', 'max_duplicates'))
                return

            elif app.printer_unavailable:
                LOGGER.warning("Maximum number of printed pages reached (%s/%s max)", app.printer.nbr_printed,
                               cfg.getint('PRINTER', 'max_pages'))
                return

            with timeit("Send final picture to printer"):
                app.printer.print_file(app.previous_picture_file,
                                       cfg.getint('PRINTER', 'pictures_per_page'))

            app.nbr_duplicates += 1

    @pibooth.hookimpl
    def state_processing_exit(self, app):
        app.nbr_duplicates = 0

    @pibooth.hookimpl
    def state_print_do(self, cfg, app, events):
        if app.find_print_event(events) and app.previous_picture_file:

            with timeit("Send final picture to printer"):
                app.printer.print_file(app.previous_picture_file,
                                       cfg.getint('PRINTER', 'pictures_per_page'))

            app.nbr_duplicates += 1
