#! /usr/bin/env python

import sys
from PyQt5 import QtCore, QtGui, QtWidgets

from card_ui import Ui_MainWindow

from smartcard.scard import *
import smartcard.util

SELECT = [0xFF, 0xA4, 0x00, 0x00, 0x01, 0x06]
READ = [0xFF, 0xB0, 0x00]  # add address and length
WRITE = [0xFF, 0xD0, 0x00]  # add address, length, and bytes
PROTECT = [0xFF, 0xD1, 0x00]  # add address, length, and bytes
UNLOCK_WRITE = [0xFF, 0x20, 0x00, 0x00, 0x03]  # add PIN
CHANGE_PIN = [0xFF, 0xD2, 0x00, 0x01, 0x03]  # write PIN
READ_PROT = [0xFF, 0xB2, 0x00, 0x00, 0x04]

PIN = ''


class MyUi(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.hcard = None
        self.dwActiveProtocol = None
        self.hcontext = None
        self.reader = None
        self.setWindowTitle('SLE4442 Manager')
        self.PIN_PROT = [self.ui.bit_8, self.ui.bit_7, self.ui.bit_6, self.ui.bit_5, self.ui.bit_4, self.ui.bit_3, self.ui.bit_2, self.ui.bit_1,
                         self.ui.bit_16, self.ui.bit_15, self.ui.bit_14, self.ui.bit_13, self.ui.bit_12, self.ui.bit_11, self.ui.bit_10, self.ui.bit_9,
                         self.ui.bit_24, self.ui.bit_23, self.ui.bit_22, self.ui.bit_21, self.ui.bit_20, self.ui.bit_19, self.ui.bit_18, self.ui.bit_17,
                         self.ui.bit_32, self.ui.bit_31, self.ui.bit_30, self.ui.bit_29, self.ui.bit_28, self.ui.bit_27, self.ui.bit_26, self.ui.bit_25]

        # segnali
        self.ui.read.clicked.connect(self.read_all)
        self.ui.write.clicked.connect(self.write_all)
        self.ui.connect.clicked.connect(self.connect)
        self.ui.disconnect.clicked.connect(self.disconnect)
        self.ui.unlock.clicked.connect(self.unlock)
        self.ui.change_pin.clicked.connect(self.change_pin)
        self.ui.protect.clicked.connect(self.protect_byte)

    def connect(self):
        try:
            hresult, self.hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to establish context : ' + SCardGetErrorMessage(hresult))
            print('Context established!')

            try:
                hresult, readers = SCardListReaders(self.hcontext, [])
                if hresult != SCARD_S_SUCCESS:
                    raise Exception('Failed to list readers: ' + SCardGetErrorMessage(hresult))
                print('PCSC Readers:', readers)

                if len(readers) < 1:
                    raise Exception('No smart card readers')

                self.reader = readers[0]
                print("Using reader:", self.reader)

                try:
                    hresult, self.hcard, self.dwActiveProtocol = SCardConnect(self.hcontext, self.reader, SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)
                    if hresult != SCARD_S_SUCCESS:
                        raise Exception('Unable to connect: ' + SCardGetErrorMessage(hresult))
                    print('Connected with active protocol', self.dwActiveProtocol)

                    try:
                        hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, SELECT)
                        if hresult != SCARD_S_SUCCESS:
                            raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
                        self.ui.card_status.setStyleSheet('color: black')
                        self.ui.card_status.setText('Connected to card: Read Only')
                        self.ui.write.setEnabled(False)
                        self.ui.change_pin.setEnabled(False)
                        self.ui.protect.setEnabled(False)
                        self.ui.protect_n.setEnabled(False)
                        print('Card successfully initialized')
                    except Exception as message:
                        print("Exception:", message)

                except Exception as message:
                    print("Exception:", message)

            except Exception as message:
                print("Exception:", message)

        except Exception as message:
            print("Exception:", message)

    def protect_byte(self):
        try:
            byte = self.ui.protect_n.value() - 1
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, READ + [byte, 1])
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
            risultato = response[0]
            try:
                hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, PROTECT + [byte, 1, risultato])
                if hresult != SCARD_S_SUCCESS:
                    raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
                if (response[-2] == 144):
                    self.ui.statusbar.showMessage('protetto byte ' + str(byte + 1), 4000)
            except Exception as message:
                print("Exception:", message)
        except Exception as message:
            print("Exception:", message)

    def read_all(self):
        try:
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, READ + [0, 255])
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
            if (response[-2] == 144):
                risultato = response[0:-2]
                for i in range(255):
                    self.ui.dati.setItem(i / 8, i % 8, QtWidgets.QTableWidgetItem(chr(risultato[i])))
                self.ui.statusbar.showMessage('lettura effettuata', 4000)
        except Exception as message:
            print("Exception:", message)

        try:
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, READ_PROT)
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
            if (response[-2] == 144):
                risultato = bin(response[0])[2:] + bin(response[1])[2:] + bin(response[2])[2:] + bin(response[3])[2:]
                for i in range(32):
                    if risultato[i] == "1":
                        self.PIN_PROT[i].setChecked(False)
                        byte = (i / 8) * 8 + 8 - (i % 8) - 1
                        self.ui.dati.item(byte / 8, byte % 8).setBackground(QtGui.QColor(240, 240, 240))
                    elif risultato[i] == "0":
                        self.PIN_PROT[i].setChecked(True)
                        byte = (i / 8) * 8 + 8 - (i % 8) - 1
                        self.ui.dati.item(byte / 8, byte % 8).setBackground(QtGui.QColor(150, 100, 100))
                    else:
                        raise Exception('Errore nella lettura dello stato di protezione dei byte')

        except Exception as message:
            print("Exception:", message)

    def write_all(self):
        risultato = []
        for i in range(255):
            c = self.ui.dati.item(i / 8, i % 8).text()
            if c == '':
                v = 0x00
            else:
                v = ord(str(c))
            risultato.append(v)
        try:
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, WRITE + [0, 255] + risultato)
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
            if (response[-2] == 144):
                self.ui.statusbar.showMessage('write correct', 4000)
        except Exception as message:
            print("Exception:", message)

    def unlock(self):
        try:
            PIN = str(self.ui.pin.text())
            if len(PIN) != 3:
                self.ui.card_status.setStyleSheet('color: red')
                self.ui.card_status.setText('pin di tre caratteri')
            else:
                hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, UNLOCK_WRITE + smartcard.util.toASCIIBytes(PIN))
                if hresult != SCARD_S_SUCCESS:
                    raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
                if response[-1] == 7:
                    self.ui.card_status.setStyleSheet('color: green')
                    self.ui.card_status.setText('card unlocked')
                    self.ui.write.setEnabled(True)
                    self.ui.change_pin.setEnabled(True)
                    self.ui.protect.setEnabled(True)
                    self.ui.protect_n.setEnabled(True)
                    print("Card unlocked and ready to write")
                elif response[-1] == 0:
                    print("carta bloccata")
                    self.ui.card_status.setStyleSheet('color: red')
                    self.ui.card_status.setText('carta bloccata')
                else:
                    print("pin errato")
                    self.ui.card_status.setStyleSheet('color: red')
                    self.ui.card_status.setText('pin errato')

        except Exception as message:
            print("Exception:", message)

    def change_pin(self):
        try:
            PIN = str(self.ui.pin.text())
            if len(PIN) != 3:
                self.ui.card_status.setText('pin di tre caratteri')
            else:
                hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, CHANGE_PIN + smartcard.util.toASCIIBytes(PIN))
                if hresult != SCARD_S_SUCCESS:
                    raise Exception('Failed to transmit: ' + SCardGetErrorMessage(hresult))
                if (response[-2] == 144):
                    self.ui.statusbar.showMessage('PIN modificato', 4000)

        except Exception as message:
            print("Exception:", message)

    def disconnect(self):
        try:
            hresult = SCardDisconnect(self.hcard, SCARD_UNPOWER_CARD)
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to disconnect: ' + SCardGetErrorMessage(hresult))
            print('Disconnected')
            self.ui.card_status.setStyleSheet('color: black')
            self.ui.card_status.setText('carta disconnessa')
            self.ui.write.setEnabled(False)
            self.ui.change_pin.setEnabled(False)
            self.ui.protect.setEnabled(False)
            self.ui.protect_n.setEnabled(False)
            try:
                hresult = SCardReleaseContext(self.hcontext)
                if hresult != SCARD_S_SUCCESS:
                    raise Exception('Failed to release context: ' + SCardGetErrorMessage(hresult))
                print('Released context.')
            except Exception as message:
                print("Exception:", message)
        except Exception as message:
            print("Exception:", message)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myapp = MyUi()
    myapp.show()
    sys.exit(app.exec_())
