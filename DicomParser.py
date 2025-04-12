import struct
import os

class DICOMParser:
    def __init__(self, directory_path):
        self.directory_path = directory_path
        self.file = None
        self.endian = "<"  # Domyślnie Little Endian ('<'), Big Endian ('>') jeśli wykryjemy
        self.explicit_vr = True  # Domyślnie zakładamy explicit VR
        self.image_rows = None
        self.image_columns = None
        self.pixel_spacing = None
        self.volume_data = []

    def open_file(self, file_path):
        """Otwiera plik DICOM i sprawdza nagłówek."""
        self.file = open(file_path, 'rb')
        self.file.seek(128)  # Pomijamy preambułę
        prefix = self.file.read(4).decode()
        if prefix != 'DICM':
            raise ValueError("Nieprawidłowy plik DICOM")

        # Sprawdzenie transfer syntax UID (0002,0010)
        self.detect_endian_and_vr()

    def close(self):
        """Zamyka plik DICOM."""
        if self.file:
            self.file.close()
            self.file = None

    def detect_endian_and_vr(self):
        """Wykrywa endian i typ VR na podstawie Transfer Syntax UID."""
        self.file.seek(132)  # Przejdź do miejsca, gdzie zaczyna się właściwy plik DICOM
        while True:
            tag = self.read_tag()
            if not tag:
                break
            group, element, vr, value = tag

            if (group, element) == (0x0002, 0x0010):  # Transfer Syntax UID
                syntax = value.decode().strip()
                print(f"Transfer Syntax UID: {syntax}")

                if syntax == "1.2.840.10008.1.2":  # Implicit VR Little Endian
                    self.explicit_vr = False
                    self.endian = "<"
                elif syntax == "1.2.840.10008.1.2.1":  # Explicit VR Little Endian
                    self.explicit_vr = True
                    self.endian = "<"
                elif syntax == "1.2.840.10008.1.2.2":  # Explicit VR Big Endian
                    self.explicit_vr = True
                    self.endian = ">"
                elif syntax in ["1.2.840.10008.1.2.4.70", "1.2.840.10008.1.2.4.50"]:  # JPEG Lossless, Nonhierarchical, First-Order Prediction and JPEG Baseline (Process 1)
                    print(f"Ignorowanie kodowania: {syntax}")
                    # Ignorujemy kodowanie, ponieważ nie wpływa ono na endian lub typ VR
                else:
                    print(f"Nieznane kodowanie: {syntax}")

                break  # Nie musimy przeszukiwać dalej

    def read_tag(self):
        try:
            data = self.file.read(4)
            if len(data) < 4:
                return None  # Koniec pliku

            group, element = struct.unpack(self.endian + 'HH', data)

            if self.explicit_vr:
                vr_raw = self.file.read(2)
                if len(vr_raw) < 2:
                    return None  # Koniec pliku

                # Sprawdzenie czy VR zawiera tylko litery ASCII
                if vr_raw.isalpha():
                    vr = vr_raw.decode()
                    if vr in ['OB', 'OW', 'OF', 'SQ', 'UT', 'UN']:
                        self.file.read(2)  # Pomiń dwa bajty
                        length = struct.unpack(self.endian + 'I', self.file.read(4))[0]
                    else:
                        length = struct.unpack(self.endian + 'H', self.file.read(2))[0]
                else:
                    # Niepoprawne VR → może to być implicit VR
                    vr = "??"
                    self.file.seek(-2, 1)  # Cofamy wskaźnik pliku
                    length = struct.unpack(self.endian + 'I', self.file.read(4))[0]
            else:
                vr = "??"
                length = struct.unpack(self.endian + 'I', self.file.read(4))[0]

            # Jeśli długość danych jest za duża, przerywamy (by nie próbować czytać błędnych danych)
            if length > 10**7:  # Ograniczenie do 10MB na tag
                print(f"⚠️ Podejrzana długość wartości tagu ({group:04X},{element:04X}): {length}")
                return None

            value = self.file.read(length)

            # Diagnostyka
            print(f"Odczytano tag: ({group:04X},{element:04X}) VR: {vr} Length: {length}")

            return group, element, vr, value
        except struct.error:
            return None

    def extract_image_info(self, file_path):
        """Wydobywa informacje o obrazie, takie jak rozmiar i proporcje piksela z pojedynczego pliku DICOM."""
        self.open_file(file_path)
        while True:
            tag = self.read_tag()
            if not tag:
                break
            group, element, vr, value = tag

            if (group, element) == (0x0028, 0x0010):  # Rows
                self.image_rows = struct.unpack(self.endian + 'H', value)[0]
            elif (group, element) == (0x0028, 0x0011):  # Columns
                self.image_columns = struct.unpack(self.endian + 'H', value)[0]
            elif (group, element) == (0x0028, 0x0030):  # Pixel Spacing
                self.pixel_spacing = [float(x) for x in value.decode().split('\\')]

        self.close()

    def parse(self, file_path):
        """Parsuje pojedynczy plik DICOM."""
        self.open_file(file_path)
        while True:
            tag = self.read_tag()
            if not tag:
                break  # Koniec pliku
            group, element, vr, value = tag
            self.print_tag_value(group, element, vr, value)
        self.close()

    def print_tag_value(self, group, element, vr, value):
        """Wyświetla wartość tagu w czytelnej formie."""
        # Pomija tag z danymi wartości piksela (7FE0,0010)
        if (group, element) == (0x7FE0, 0x0010):
            return

        tag = f"({group:04X},{element:04X})"
        if vr in ['CS', 'SH', 'LO', 'ST', 'LT', 'UT', 'PN', 'AE', 'AS', 'DA', 'DS', 'DT', 'IS', 'TM', 'UI']:
            value = value.decode().strip()
        elif vr == 'US':
            value = struct.unpack(self.endian + 'H', value)[0]
        elif vr == 'UL':
            value = struct.unpack(self.endian + 'I', value)[0]
        else:
            value = value.hex()

        print(f"Tag: {tag} - {vr}: '{value}'")

    def read_volume(self):
        """Czyta wszystkie pliki DICOM w katalogu i przetwarza dane wolumenu."""
        for root, _, files in os.walk(self.directory_path):
            for file in sorted(files):
                if file.lower().endswith('.dcm'):
                    file_path = os.path.join(root, file)
                    self.extract_image_info(file_path)
                    pixel_data = self.read_pixel_data(file_path)
                    if pixel_data:
                        self.volume_data.append(pixel_data)
        
        print(f"Odczytano {len(self.volume_data)} plików DICOM z katalogu {self.directory_path}")

    def read_pixel_data(self, file_path):
        """Czyta dane wartości piksela z pliku DICOM."""
        pixel_data = None
        self.open_file(file_path)
        while True:
            tag = self.read_tag()
            if not tag:
                break
            group, element, vr, value = tag

            if (group, element) == (0x7FE0, 0x0010):  # Pixel Data
                bits_allocated = 16  # Załóżmy 16 bitów na piksel
                num_pixels = self.image_rows * self.image_columns
                if bits_allocated == 16:
                    pixel_data = struct.unpack(self.endian + 'H' * num_pixels, value)
                break
        
        self.close()
        return pixel_data

if __name__ == "__main__":
    volume_path = r"C:\Users\mm-20\Desktop\Wybrane Zastosowania Informatyki - projekt\Dane\stopy-anonymized\stopy-anonymized\A20250305103850\P00001\S0001"
    
    parser = DICOMParser(volume_path)
    parser.read_volume()
    print(f"Volume Data: {len(parser.volume_data)} slices read")