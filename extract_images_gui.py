#!/usr/bin/env python3
"""
Enterprise-Grade PDF Image Extractor GUI
- Robust error handling & logging
- Theme management with fallback support
- Configurable via CLI args
- Packaged-ready for PyInstaller
"""
import sys
import os
import io
import logging
import argparse
from datetime import datetime

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import PySimpleGUI as sg
except ImportError as e:
    print(f"Missing dependency: {e.name}. Please install requirements via: \n"
          "pip3 install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI Pillow PyMuPDF")
    sys.exit(1)

# Setup logging
LOG_FILE = os.path.join(os.path.expanduser('~'), 'pdf_image_extractor.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

APP_THEME = 'LightGrey1'
# Fallback for old versions
try:
    sg.theme(APP_THEME)
except AttributeError:
    sg.ChangeLookAndFeel(APP_THEME)


def extract_images_from_pdf(pdf_path):
    logging.info(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    images = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_img = doc.extract_image(xref)
            images.append((page_idx+1, img_idx+1, base_img['image']))
    logging.info(f"Found {len(images)} images in PDF")
    return images


def create_thumbnail(image_bytes, max_size=(150,150)):
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.thumbnail(max_size)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        return bio.getvalue()


def build_main_window():
    layout = [
        [sg.Text('PDF Image Extractor', font=('Any', 16), pad=(0,10))],
        [sg.Text('Select PDF:'), sg.Input(key='-PDF-'), sg.FileBrowse(file_types=(('PDF','*.pdf'),))],
        [sg.Text('Output Folder:'), sg.Input(key='-OUT-'), sg.FolderBrowse()],
        [sg.Button('Load'), sg.Button('Exit')]
    ]
    return sg.Window('PDF Image Extractor', layout, finalize=True)


def build_selection_window(images):
    checkbox_keys = []
    img_rows = []
    for idx, (pnum, inum, img_bytes) in enumerate(images):
        key = f'-CHK{idx}-'
        checkbox_keys.append((key, idx))
        thumb = create_thumbnail(img_bytes)
        img_rows.append([sg.Checkbox(f'Page {pnum}, Image {inum}', key=key), sg.Image(data=thumb)])
    layout = [ [sg.Column(img_rows, scrollable=True, size=(700,450))], [sg.Button('Download'), sg.Button('Cancel')] ]
    return checkbox_keys, sg.Window('Select Images', layout, finalize=True)


def main(args):
    try:
        window = build_main_window()
        while True:
            evt, vals = window.read()
            if evt in (sg.WINDOW_CLOSED, 'Exit'): break
            if evt == 'Load':
                pdf, out = vals['-PDF-'], vals['-OUT-']
                if not pdf or not out:
                    sg.popup_error('Both PDF and output folder are required!')
                    continue
                if not os.path.isfile(pdf):
                    sg.popup_error('PDF not found!')
                    continue
                os.makedirs(out, exist_ok=True)
                images = extract_images_from_pdf(pdf)
                if not images:
                    sg.popup('No images found.')
                    continue
                window.close()
                checkbox_keys, sel_win = build_selection_window(images)
                while True:
                    e2, v2 = sel_win.read()
                    if e2 in (sg.WINDOW_CLOSED, 'Cancel'):
                        sel_win.close(); return
                    if e2 == 'Download':
                        count = 0
                        for key, idx in checkbox_keys:
                            if v2.get(key):
                                p, i, data = images[idx]
                                fname = f"img_p{p}_i{i}.png"
                                fpath = os.path.join(out, fname)
                                with open(fpath, 'wb') as f: f.write(data)
                                logging.info(f"Saved: {fpath}")
                                count += 1
                        sg.popup('Done', f'{count} images saved to {out}')
                        sel_win.close(); return
        window.close()
    except Exception as e:
        logging.exception('Application error')
        sg.popup_error(f'Unexpected error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enterprise PDF Image Extractor GUI')
    parser.add_argument('--pdf', help='Path to PDF file')
    parser.add_argument('--out', help='Output directory')
    args = parser.parse_args()
    main(args)

# To build executable:
# pyinstaller --onefile --windowed extract_images_gui.py
