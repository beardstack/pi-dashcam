#!/usr/bin/env python3
import os
import shutil
import argparse
import picamera
from led import LED
from switch import Switch
from time import time, sleep
from threading import Thread, Lock
from random import randbytes

class Dashcam():
    def __init__(
            self, sequence_count=10, sequence_length=60, resolution=(1920, 1080),
            video_type="h264", video_name_prefix="dashcam_vid", bitrate = 17000000,
            framerate=30, video_file_path="/dashcam", pin_btn=11, pin_led_cpy=12,
            pin_led_pwr=13, salt_bytes=4, led_pwr_dim_perc=5, pwr_led="on"):
        self.pin_btn = pin_btn
        self.pin_led_pwr = pin_led_pwr
        self.pin_led_cpy = pin_led_cpy
        self.pin_led_pwr_dim_percent = led_pwr_dim_perc
        self.pin_blink_seconds = 2
        self.pin_blink_on_seconds = 0.1
        self.power_led = pwr_led

        self.video_sequence_seconds = sequence_length
        self.video_sequence_count = sequence_count
        self.video_resolution = resolution
        self.video_name_prefix = video_name_prefix
        self.video_file_path=video_file_path
        self.video_file_path_legal=f"{self.video_file_path}/legal"
        self.video_type = video_type if video_type in ("h264", "mjpeg") else "h264"
        self.video_bit_rate = bitrate
        self.video_frame_rate = framerate

        # using a salt to not eventually overwrite files
        # after an unexpected reboot in car; is like
        # a unique identifier for an ongoing record session
        self.video_name_salt = randbytes(salt_bytes).hex()

        self.LED_data = LED(self.pin_led_cpy)
        self.LED_power = LED(self.pin_led_pwr)
        self.BTN = Switch(self.pin_btn)

        self.lock = Lock()

        self.camera = picamera.PiCamera(
            resolution=self.video_resolution,
            framerate=self.video_frame_rate
        )

    def __del__(self):
        del self.LED_data, self.LED_power

    def _dashcam_video_thread(self):
        ctr = 0

        video_filename = (
            f"{self.video_file_path}/{self.video_name_prefix}_"
            f"{int(time())}-{self.video_name_salt}-"
            f"{ctr}.{self.video_type}"
        )
        print(f"Recording to '{video_filename}'.")
        self.camera.start_recording(
            video_filename, format=self.video_type, bitrate=self.video_bit_rate
        )
        self.camera.wait_recording(self.video_sequence_seconds)

        while True:
            ctr += 1
            video_filename = (
                f"{self.video_file_path}/{self.video_name_prefix}_"
                f"{int(time())}-{self.video_name_salt}-"
                f"{ctr}.{self.video_type}"
            )
            print(f"Recording to '{video_filename}'.")
            self.camera.split_recording(video_filename)
            self.camera.wait_recording(self.video_sequence_seconds)

        self.camera.stop_recording() #this will never be reached ;)
        #add maybe some handler in future when e.g. using a PSU/USV

    def _dashcam_file_cleanup_thread(self):
        while True:
            self.lock.acquire()

            video_file_list = self.get_directory_file_list(
                self.video_file_path, self.video_type
            )
            video_file_list_legal = self.get_video_file_list_legal(
                video_file_list, buffer=1
            )

            delete_video_file_list = [
                video_file
                for video_file in video_file_list
                if video_file not in video_file_list_legal
            ]

            for del_video_file in delete_video_file_list:
                print(f"DELETE file '{del_video_file}'")
                try:
                    os.remove(f"{self.video_file_path}/{del_video_file}")
                except FileNotFoundError:
                    print(
                        f"WARNING! File '{self.video_file_path}/{del_video_file}'"
                        " is gone. Ignoreing file. Continue"
                    )

            self.lock.release()
            sleep(self.video_sequence_seconds)

    def _dashcam_powerled_thread(self):
        self.LED_power.set_on()
        sleep(10)
        if self.power_led == "off":
            while True:
                sleep(1)
                #...plsdontdiethread :D
                #...wecoulddobitcoinmining...
        elif self.power_led in ("heartbeat","slowheartbeat"):
            while True:
                self.LED_power.set_duty_cycle(self.pin_led_pwr_dim_percent)
                sleep(0.1)
                self.LED_power.set_duty_cycle(0)
                sleep(0.1)
                self.LED_power.set_duty_cycle(self.pin_led_pwr_dim_percent)
                sleep(0.2)
                self.LED_power.set_duty_cycle(0)
                sleep(60 if self.power_led == "slowheartbeat" else 1)
        else:
            self.LED_power.set_on()
            self.LED_power.set_duty_cycle(self.pin_led_pwr_dim_percent)
            while True:
                sleep(1)
                #...plsdontdiethread :D
                #...wecoulddobitcoinmining...

    def get_directory_file_list(self, path, filetype):
        return [
            file
            for file in os.listdir(path)
            if (
                os.path.isfile(os.path.join(path,file)) and
                file.endswith(f'.{filetype}')
            )
        ]

    def get_video_file_list_legal(self, video_file_list, reverse=True, buffer=0):
        prefix_match_sorted_reduced_video_fileid_list = sorted(
            [
                file.removeprefix(
                    f"{self.video_name_prefix}_"
                ).removesuffix(
                    f'.{self.video_type}'
                )
                for file in video_file_list
                if file.startswith(f"{self.video_name_prefix}_")
            ], key = (
                lambda x: (
                    f"{int(x.split('-')[1] == self.video_name_salt)}{x}"
                )
            ), reverse=reverse
        )

        return [
                f"{self.video_name_prefix}_{fileid}.{self.video_type}"
                for fileid in prefix_match_sorted_reduced_video_fileid_list
            ][:self.video_sequence_count+buffer]

    def save_video_file_legal(self, LED):
        self.lock.acquire()
        LED.set_on()

        video_file_list_legal = self.get_video_file_list_legal(
            self.get_directory_file_list(
                self.video_file_path, self.video_type
            ), reverse=False
        )

        for video_file in video_file_list_legal:
            src = f"{self.video_file_path}/{video_file}"
            dst = f"{self.video_file_path_legal}/INCIDENT_{video_file}"
            print(f"Copy '{src}' to '{dst}'.")
            try:
                shutil.copyfile(src, dst)
            except FileNotFoundError:
                print(f"WARNING! File '{src}' is gone. Ignoreing file. Continue")
        print("Copy done.")

        for round in range(int(self.pin_blink_seconds / self.pin_blink_on_seconds)):
            if round % 2 == 0:
                LED.set_on()
            else:
                LED.set_off()
            sleep(self.pin_blink_on_seconds)

        LED.set_off()
        self.lock.release()

    def _button_copy_functor(self, input):
        if input == 0:
            self.save_video_file_legal(self.LED_data)

    def start(self):
        self.power_led_thread = Thread(target=self._dashcam_powerled_thread)
        self.video_thread = Thread(target=self._dashcam_video_thread)
        self.clean_thread = Thread(target=self._dashcam_file_cleanup_thread)
        self.BTN.set_functor(self._button_copy_functor)

        self.power_led_thread.start()
        self.video_thread.start()
        self.clean_thread.start()

    def join_clean_thread(self):
        self.clean_thread.join()

def main():
    parser = argparse.ArgumentParser(
        description="""DashCam-app following the German traffic and GDPR (DSGVO)
        laws. Is designed to work on any Raspberry PI that provides PiCamera
        library in Python; this fits basically for any 32-Bit driven RPI.
        Mainly used in combination with a RPI Zero W v1.1, which is totally
        sufficient for this purpose.
        Instead of a single, increasing video file, the input video stream is
        splitted into e.g. 60s video chunks; only the last e.g. 10 chunks are kept.
        This allows to have e.g. the last 10 minutes stored but also regularly cleaned
        in order to stay conform towards GDPR.
        There is a special incident procedure: when an attached button is pressed,
        the last e.g. 10 legal video chunks are separately stored and not cleaned
        to e.g. provide some legal information in any case of accident/emergency.
        In addition, two LEDs can be attached to print Power/Heartbeat information
        and to indicate the current, active data copy in any case of accident (this
        will only happen, when you press the button).
        """
    )

    parser.add_argument(
        "-s", "--video_chunk_duration", metavar="S", type=int, required=False,
        default=60, help="Length of a single stored video chunk."
    )
    parser.add_argument(
        "-c", "--video_chunk_count", metavar="C", type=int, required=False,
        default=10, help=(
            "Max. number of sequential video chunks that are stored in parallel"
            "on the disk; this correlates do GDPR laws."
        )
    )
    parser.add_argument(
        "-p", "--video_file_path", metavar="P", type=str, required=False,
        default="/opt/dashcam", help="Location to store dashcam video chunks"
    )
    parser.add_argument(
        "-f", "--video_file_prefix", metavar="F", type=str, required=False,
        default="dashcam-video", help=(
            "Filename prefix for the locally stored video file chunks"
        )
    )
    parser.add_argument(
        "-r", "--video_resolution", metavar="R", nargs=2, type=int, required=False,
        default=(1920, 1080), help="Length of a single stored video chunk."
    )
    parser.add_argument(
        "-br", "--video_bitrate", metavar="BR", type=int, required=False,
        default=7000000, help="Bitrate used to store videos."
    )
    parser.add_argument(
        "-vf", "--video_format", metavar="VF", type=str, required=False,
        default="h264", choices=("h264","mjpeg"),help="File format used to store videos."
    )
    parser.add_argument(
        "-b", "--pin_button", metavar="B", type=int, required=False,
        default=11, help="Pin number in GPIO.BOARD layout for a button."
    )
    parser.add_argument(
        "-lc", "--pin_led_copy", metavar="PLC", type=int, required=False,
        default=12, help="Pin number in GPIO.BOARD layout for a data-copy LED."
    )
    parser.add_argument(
        "-lp", "--pin_led_power", metavar="PLP", type=int, required=False,
        default=13, help="Pin number in GPIO.BOARD layout for a power LED."
    )
    parser.add_argument(
        "-d", "--pin_power_dim_percent", metavar="LPD", type=int, required=False,
        default=5, help="Percent dim for the Power LED; if it might be to bright."
    )
    parser.add_argument(
        "--power_led", metavar="PL", type=str, required=False,
        default="slowheartbeat", choices=("on", "off", "heartbeat", "slowheartbeat"), help=(
            "This option allows to control the power LED; either on, off or"
            "the heart beat mode, where a heartbeat pulse via PWM is started"
            "for the LED"
        )
    )

    args = parser.parse_args()

    print(str(args))

    video_chunk_duration = args.video_chunk_duration
    video_chunk_count = args.video_chunk_count
    video_file_path = args.video_file_path
    video_file_prefix = args.video_file_prefix
    video_resolution = args.video_resolution
    video_bitrate = args.video_bitrate
    video_format = args.video_format
    pin_button = args.pin_button
    pin_led_power = args.pin_led_power
    pin_led_copy = args.pin_led_copy
    pin_power_dim_percent = args.pin_power_dim_percent
    power_led_type = args.power_led


    dashcam = Dashcam(
        sequence_count=video_chunk_count, sequence_length=video_chunk_duration,
        resolution=video_resolution, video_type=video_format, bitrate=video_bitrate,
        video_name_prefix=video_file_prefix, video_file_path=video_file_path,
        pin_btn=pin_button, pin_led_cpy=pin_led_copy, pin_led_pwr=pin_led_power,
        led_pwr_dim_perc=pin_power_dim_percent, pwr_led=power_led_type
    )


    dashcam.start()
    dashcam.join_clean_thread()


if __name__=='__main__':
    main()
