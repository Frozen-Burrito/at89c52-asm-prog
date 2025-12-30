import serial


class SerialProgrammer:
    RESPONSE_SUCCESS = bytes([0xA5, (~0xA5) & 0xFF])

    def __init__(self, port: str, bitrate: int, address_range: tuple[int, int]) -> None:
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = bitrate
        self.ser.timeout = 1
        
        self.address_range = address_range

    
    def open(self) -> None:
        if self.ser is not None:
            print("DEBUG: open serial port")
            self.ser.open()


    def seek(self, address) -> bool:
        # Serial port must be open.
        if self.ser is None or not self.ser.is_open:
            print("ERROR: serial port is not open, call open() first")
            return False
        
        # Validate address range.
        start, end = self.address_range
        if address < start or address > end:
            print(f"ERROR: seek address out of range {start} - {end}")
            return False
        
        # Write seek command.
        address_low = address & 0xFF
        address_high = (address >> 8) & 0xFF

        payload = [0x10, (~0x10) & 0xFF, address_high, address_low]
        checksum = sum(payload) & 0xFF
        payload.append(checksum)

        num_bytes_written = self.ser.write(bytes(payload))

        # Check if write sent the complete payload.
        if num_bytes_written != len(payload):
            print(f"ERROR: seek tried to write {len(payload)} bytes, but only {num_bytes_written} were written")
            return False
        
        response = self.ser.read(1)
        if response != self.RESPONSE_SUCCESS:
            print(f"ERROR: seek got response {response}")
            return False

        return True

    
    def close(self) -> None:
        if self.ser is not None:
            print("DEBUG: close serial port")
            self.ser.close()
        self.ser = None
