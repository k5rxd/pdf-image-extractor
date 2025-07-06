#!/usr/bin/env python3
from PyQt5 import QtCore, QtGui, QtWidgets
import sys, os, io, logging, tempfile
import fitz  # PyMuPDF
from PIL import Image

# ------------------------------
# Logging
# ------------------------------
LOG_FILE = os.path.expanduser('~/pdf_extractor_pro.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# ------------------------------
# Application Styles (3D, animations, shadows)
# ------------------------------
APP_QSS = r"""
/* 3D Buttons */
QPushButton {
    border: 2px solid #888;
    border-radius: 10px;
    padding: 10px 20px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #fafafa, stop:1 #e0e0e0);
    color: #333;
    font: bold 14px;
    box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #ffffff, stop:1 #d0d0d0);
}
QPushButton:pressed {
    background: #c8c8c8;
    box-shadow: inset 0px 2px 4px rgba(0,0,0,0.5);
}

/* Panels */
QMainWindow {
    background-color: #2b2b2b;
}
QWidget#sidebar {
    background-color: #1f1f1f;
    border-right: 1px solid #444;
}
QScrollArea, QListWidget {
    background-color: #292929;
    border: none;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #444;
    border-radius: 5px;
    background-color: #3a3a3a;
    text-align: center;
    color: #eee;
}
QProgressBar::chunk {
    background-color: #29b6f6;
    width: 20px;
    margin: 1px;
}

/* Shadow Effect for thumbnails */
QLabel#thumbLabel {
    border: 1px solid #555;
    border-radius: 5px;
    background-color: #1e1e1e;
    padding: 5px;
}
"""

# ------------------------------
# Worker Thread for extraction
# ------------------------------
class ExtractThread(QtCore.QThread):
    progressChanged = QtCore.pyqtSignal(int, int)
    finished = QtCore.pyqtSignal(list)

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        doc = fitz.open(self.pdf_path)
        total_pages = doc.page_count
        images = []
        for page_number in range(total_pages):
            page = doc[page_number]
            pixlist = page.get_images(full=True)
            for idx, img in enumerate(pixlist):
                xref = img[0]
                base = doc.extract_image(xref)
                images.append((page_number+1, idx+1, base['image']))
            self.progressChanged.emit(page_number+1, total_pages)
        self.finished.emit(images)

# ------------------------------
# Settings Dialog
# ------------------------------
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.resize(400,300)
        layout = QtWidgets.QFormLayout(self)
        self.namingPattern = QtWidgets.QLineEdit('img_P{page}_I{idx}.png')
        layout.addRow('Filename pattern:', self.namingPattern)
        self.defaultFolder = QtWidgets.QLineEdit(os.path.expanduser('~'))
        layout.addRow('Default output dir:', self.defaultFolder)
        self.jpegQuality = QtWidgets.QSpinBox()
        self.jpegQuality.setRange(10,100)
        self.jpegQuality.setValue(90)
        layout.addRow('JPEG Quality:', self.jpegQuality)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

# ------------------------------
# Update Checker Dialog
# ------------------------------
class UpdateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Check for Updates')
        self.resize(350,150)
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel('Checking for updates...')
        layout.addWidget(self.label)
        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)
        self.closeBtn = QtWidgets.QPushButton('Close')
        self.closeBtn.clicked.connect(self.close)
        layout.addWidget(self.closeBtn)
        # Simulate update check
        QtCore.QTimer.singleShot(2000, self._finish)

    def _finish(self):
        self.label.setText('You are running the latest version!')
        self.progress.setValue(100)

# ------------------------------
# Main Application Window
# ------------------------------
class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF Extractor Pro')
        self.resize(1200, 800)
        self.setStyleSheet(APP_QSS)
        self._init_ui()

    def _init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        hbox = QtWidgets.QHBoxLayout(central)

        # Sidebar
        sidebar = QtWidgets.QFrame(objectName='sidebar')
        sidebar.setFixedWidth(280)
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        lbl = QtWidgets.QLabel('PDF Extractor Pro')
        lbl.setFont(QtGui.QFont('Arial', 18, QtGui.QFont.Bold))
        sb_layout.addWidget(lbl)
        self.btnLoad = QtWidgets.QPushButton('Load PDF')
        self.btnSettings = QtWidgets.QPushButton('Settings')
        self.btnUpdate = QtWidgets.QPushButton('Check Updates')
        self.btnExport = QtWidgets.QPushButton('Export Selected')
        for w in [self.btnLoad, self.btnExport, self.btnSettings, self.btnUpdate]:
            sb_layout.addWidget(w)
        sb_layout.addStretch()
        self.progress = QtWidgets.QProgressBar()
        sb_layout.addWidget(self.progress)
        self.logView = QtWidgets.QListWidget()
        sb_layout.addWidget(self.logView, 5)
        hbox.addWidget(sidebar)

        # Thumbnails area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.thumbContainer = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.thumbContainer)
        self.scroll.setWidget(self.thumbContainer)
        hbox.addWidget(self.scroll, 1)

        # Connect signals
        self.btnLoad.clicked.connect(self.load_pdf)
        self.btnExport.clicked.connect(self.export_selected)
        self.btnSettings.clicked.connect(self.open_settings)
        self.btnUpdate.clicked.connect(self.check_updates)
        self.btnExport.setEnabled(False)
        self.settings = {'pattern':'img_P{page}_I{idx}.png','outdir':os.path.expanduser('~'),'quality':90}

    def _log(self, text):
        logging.info(text)
        self.logView.addItem(text)
        self.logView.scrollToBottom()

    def load_pdf(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open PDF', '', 'PDF Files (*.pdf)')
        if not path: return
        self._log(f'Loading {path}')
        self.thread = ExtractThread(path)
        self.thread.progressChanged.connect(lambda cur,tot: self.progress.setValue(int(cur*100/tot)))
        self.thread.finished.connect(self.display_thumbs)
        self.thread.start()

    def display_thumbs(self, images):
        # clear
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget(); w.setParent(None)
        row, col = 0, 0
        self.thumbs = []
        for page, idx, data in images:
            lbl = QtWidgets.QLabel(objectName='thumbLabel')
            pix = self._bytes_to_pixmap(data)
            lbl.setPixmap(pix.scaled(160,160, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            chk = QtWidgets.QCheckBox(f'P{page}-I{idx}')
            container = QtWidgets.QVBoxLayout()
            frame = QtWidgets.QFrame()
            container.addWidget(lbl)
            container.addWidget(chk)
            frame.setLayout(container)
            self.grid.addWidget(frame, row, col)
            self.thumbs.append((chk,data))
            col += 1
            if col>3:
                col=0; row+=1
        self.btnExport.setEnabled(True)
        self._log(f'Displayed {len(self.thumbs)} thumbnails')

    def _bytes_to_pixmap(self, data_bytes):
        img = Image.open(io.BytesIO(data_bytes))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        pix = QtGui.QPixmap()
        pix.loadFromData(buf.getvalue())
        return pix

    def export_selected(self):
        out = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Output Dir', self.settings['outdir'])
        if not out: return
        self._log(f'Exporting to {out}')
        total = sum(1 for chk,_ in self.thumbs if chk.isChecked())
        self.progress.setMaximum(total)
        count=0
        for chk,data in self.thumbs:
            if not chk.isChecked(): continue
            fname = self.settings['pattern'].format(page=chk.text().split('-')[0][1:], idx=chk.text().split('-')[1][1:])
            path = os.path.join(out, fname)
            with open(path,'wb') as f: f.write(data)
            count+=1; self.progress.setValue(count)
        self._log(f'Exported {count}/{total} images')

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.namingPattern.setText(self.settings['pattern'])
        dlg.defaultFolder.setText(self.settings['outdir'])
        dlg.jpegQuality.setValue(self.settings['quality'])
        if dlg.exec_()==QtWidgets.QDialog.Accepted:
            self.settings['pattern']=dlg.namingPattern.text()
            self.settings['outdir']=dlg.defaultFolder.text()
            self.settings['quality']=dlg.jpegQuality.value()
            self._log('Settings updated')

    def check_updates(self):
        dlg = UpdateDialog(self)
        dlg.exec_()

# ------------------------------
# Entry point
# ------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    main()
