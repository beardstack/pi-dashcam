#!/usr/bin/env python3
"""
"""
from math import log2, fabs
from time import sleep
import pigpio


class Adxl345():
    ADDR_DEV_ID = 0x00
    ADDR_RATE_BW = 0x2C
    ADDR_DATA_FORMAT = 0x31
    ADDR_DATA_X_0 = 0x32 # from here on 6 bytes (2 per coordinate) for X,Y,Z
    ADDR_OFFSET_X = 0x1E
    ADDR_OFFSET_Y = 0x1F
    ADDR_OFFSET_Z = 0x20
    ADDR_POWER_CTL = 0x2D

    def __init__(
            self, sensitivity_range=4, data_rate_level=0):
        # high range values means lower resolution for small movements!
        # low range values means higher resolution for small movements!
        self.set_sensitivity_range(sensitivity_range)
        self.set_data_rate_level(data_rate_level)

    def decode(self, lsb, msb):
        accl = (msb << 8) | lsb
        adjust = 2 * (2**(self.sensitivity_range + 1)) / (2**13) # given g range with 13 bit precision
        correct_accl = (accl - (1 << 16)) * adjust if accl & (1 << 15) else accl * adjust
        return correct_accl

    def set_sensitivity_range(self, sensitivity_range):
        errmsg = f"Sensitivity Range '{sensitivity_range}' needs to integer of 2,4,8,16"
        if not isinstance(sensitivity_range, int):
            raise TypeError(errmsg)
        if sensitivity_range not in (2,4,8,16):
            raise ValueError(errmsg)
        self.sensitivity_range = int(log2(sensitivity_range))-1
        data = self.from_address(Adxl345.ADDR_DATA_FORMAT, 1)[0] & ~0x0F | self.sensitivity_range | 0x08
        self.to_address(Adxl345.ADDR_DATA_FORMAT, data)

    def set_data_rate_level(self, data_rate_level):
        errmsg = f"DataRateLevel '{data_rate_level}' needs to be integer within 0 < DRL <= 16!"
        if not isinstance(data_rate_level, int):
            raise TypeError(errmsg)
        if data_rate_level < 0 or data_rate_level > 16:
            raise ValueError(errmsg)

        self.data_rate_code = 0b1111-(data_rate_level)
        self.data_rate = int(3200/(2**(data_rate_level)))
        self.to_address(Adxl345.ADDR_RATE_BW, self.data_rate_code)

    def set_offset(self, x, y, z):
        offset = {
            Adxl345.ADDR_OFFSET_X: x,
            Adxl345.ADDR_OFFSET_Y: y,
            Adxl345.ADDR_OFFSET_Z: z,
        }
        for addr in offset.keys():
            self.to_address(
                addr,
                int(offset[addr] / Adxl345.FACTOR_HIGH_RES / 4 ) & 0xFF
            )

    def set_on(self):
        self.to_address(Adxl345.ADDR_POWER_CTL, 0x08)

    def set_off(self):
        self.to_address(Adxl345.ADDR_POWER_CTL, 0x00)

    def calibrate(self, margin=0.1):
        self.set_offset(0,0,0)

        accel = self.get_acceleration()
        x,y,z = accel[0], accel[1], accel[2]
        if not all(
            (0-margin < fabs(v) < 0+margin) or (1-margin < fabs(v) < 1+margin)
            for v in (x, y, z)
        ):
            raise ValueError(
                f"WARNING! Please place sensor on appropriate surface; "
                f"values should be around 0 or 1 and not {x,y,z}")
        if not round(x) ^ round(y) ^ round(z):
            raise ValueError(
                "WARNING! Please place sensor on appropriate surface; "
                "values should be around 0 or 1, with only one value 1 "
                f"and not {x,y,z}"
            )
        calibration = [
            round(v) - v
            for v in (x,y,z)
        ]
        self.set_offset(*calibration)

    def get_acceleration(self,axis=0b111):
        byte_ctr = 6 #2 bytes each for x,y,z values
        data = self.from_address(Adxl345.ADDR_DATA_X_0, byte_ctr)
        return [
            self.decode(data[idx], data[idx+1])
            for idx in range(0,byte_ctr, 2)
            if axis & (1 << (idx//2))
        ]



class Adxl345Spi(Adxl345):
    BITMASK_READ = 0x80
    BITMASK_MULTI = 0x40
    ADDR_SELECT_MASK = 0x3f

    def __init__(self, channel=0, mode=0b11, baudrate=2e6):
        self.channel = int(channel)
        self.mode = int(mode)
        self.baudrate = int(baudrate)

        self.pi = pigpio.pi()
        self.spi = self.pi.spi_open(self.channel, self.baudrate, self.mode)

        super().__init__()

    def from_address(self, addr, byte_count):
        bit_msg = [
            addr | Adxl345Spi.BITMASK_READ | (Adxl345Spi.BITMASK_MULTI * (byte_count > 1))
        ]
        # add some random bytes, read bitmask is set -> no writing!
        bit_msg.extend([
            0xFF
            for _ in range(byte_count)
        ])
        count, data = self.pi.spi_xfer(self.spi, bit_msg)
        if count != (byte_count+1) or len(data) != count:
            raise ValueError(
                f"Returned SPI bytes from {addr} seems not to be correct!\n"
                f"Found {[x for x in data]}"
            )
        return data[1:]

    def to_address(self, addr, values):
        data_values = values if isinstance(values, list) else [values]
        bit_msg = [
            addr | (Adxl345Spi.BITMASK_MULTI * (len(data_values) > 1))
        ]
        bit_msg.extend(data_values)
        self.pi.spi_xfer(self.spi, bit_msg)

    def stop(self):
        self.pi.spi_close(self.spi)
        self.pi.stop()

class Adxl345I2C(Adxl345):
    pass


def main():
    test = Adxl345Spi()
    test.set_on()
    for _ in range(10):
        print(", ".join(str(val) for val in test.get_acceleration()))
        sleep(1)
    test.stop()

if __name__ == "__main__":
    # execute only if run as a script
    main()
