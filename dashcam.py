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


def get_usb_storage_device(desired_device=None):
    with open("/proc/partitions") as file:
        file.readline() #skip heading line
        file.readline() #skip empty line
        device_info = [
            [ item.strip() for item in line.strip().split() ]
            for line in file
        ]
        devices = [
            device[3]
            for device in device_info
            if len(device) >= 3 and device[0] in ("8", "259")
        ]
        primary_devices = [
            device[3]
            for device in device_info
            if len(device) >= 3 and device[0] in ("8", "259") and (int(device[1]) % 16) == 0
        ]

        block_class_path = "/sys/class/block"

        primary_usb_devices = [
            device
            for device in primary_devices
            if (
                os.path.islink(f"{block_class_path}/{device}") and
                os.path.realpath(f"{block_class_path}/{device}").find("/usb") > 0
            )
        ]

        usb_partitions = sorted(
            [
                partition
                for partition in devices
                for usb_device in primary_usb_devices
                if partition.startswith(usb_device) and usb_device != partition
            ],
            reverse=True #assuming the last partition of the last is correct
        )

        if desired_device is not None:
            if desired_device in usb_partitions:
                return desired_device
            return None
        return usb_partitions[0]

def mount_usb_device(device, id):
    mnt_path = f"/mnt/{id}"
    if not os.path.ismount(mnt_path):
        os.system(f"mkdir -p {mnt_path}")
        os.system(f"mount {device} {mnt_path}")
    return mnt_path



class Dashcam():
    def __init__(
            self, sequence_count=10, sequence_length=60, resolution=(1920, 1080),
            video_type="h264", video_name_prefix="video-dashcam", bitrate = 17000000,
            framerate=30, video_file_path="/opt/dashcam", pin_btn_cpy=11, pin_btn_info=33,
            pin_btn_pwr=35, pin_btn_stop=37, pin_led_cpy=12, pin_led_pwr=13,
            pin_led_info=15, led_pwr_dim_perc=5, salt_bytes=4):
        self.pin_btn_cpy = pin_btn_cpy
        self.pin_btn_pwr = pin_btn_pwr
        self.pin_btn_info = pin_btn_info
        self.pin_btn_stop = pin_btn_stop
        self.pin_led_pwr = pin_led_pwr
        self.pin_led_cpy = pin_led_cpy
        self.pin_led_info = pin_led_info
        self.pin_led_pwr_dim_percent = led_pwr_dim_perc
        self.pin_blink_seconds = 2
        self.pin_blink_on_seconds = 0.1

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
        self.LED_info = LED(self.pin_led_info)


        self.BTN_data = Switch(self.pin_btn_cpy)
        self.BTN_power = Switch(self.pin_btn_pwr)
        self.BTN_stop = Switch(self.pin_btn_stop)
        self.BTN_info = Switch(self.pin_btn_info)

        self.file_lock = Lock()
        self.camera_lock = Lock()

        self.camera = picamera.PiCamera(
            resolution=self.video_resolution,
            framerate=self.video_frame_rate
        )
        self.camera_state = 0 #0: off, 1: turndown, 2: on
        self.info_led_state = 0
        self.segment_ctr = 0
        self.video_filename = ""

    def get_video_id(self):
        return self.video_name_salt

    def set_video_path(self, path):
        self.video_file_path = path
        self.video_file_path_legal = f"{self.video_file_path}/legal"

    def __del__(self):
        del self.LED_data, self.LED_power

    def _dashcam_video_thread(self):
        self.video_filename = (
            f"{self.video_name_prefix}_"
            f"{int(time())}-{self.video_name_salt}-"
            f"{self.segment_ctr}.{self.video_type}"
        )
        video_path = f"{self.video_file_path}/{self.video_filename}"
        print(f"Recording to '{video_path}'.")
        self.camera.start_recording(
            video_path, format=self.video_type, bitrate=self.video_bit_rate
        )
        self.camera.wait_recording(self.video_sequence_seconds)

        while self.camera_state > 1:
            self.segment_ctr += 1
            tmp_video_filename = (
                f"{self.video_name_prefix}_"
                f"{int(time())}-{self.video_name_salt}-"
                f"{self.segment_ctr}.{self.video_type}"
            )
            video_path = f"{self.video_file_path}/{tmp_video_filename}"
            print(f"Recording to '{video_path}'.")
            self.camera.split_recording(video_path)
            # as the copy thread callback might be a bit too fast,
            # we manage to set the final new filename AFTER the switch
            # which guarantees, that the file is really finished.
            self.video_filename = tmp_video_filename
            self.camera.wait_recording(self.video_sequence_seconds)
        self.camera.stop_recording()
        self.camera_state = 0


    def _dashcam_file_cleanup_thread(self):
        while True:
            self.file_lock.acquire()

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

            self.file_lock.release()
            sleep(self.video_sequence_seconds)

    def _led_power_heartbeat(self, LED):
        LED.set_duty_cycle(self.pin_led_pwr_dim_percent)
        sleep(0.15)
        LED.set_duty_cycle(0)
        sleep(0.15)
        LED.set_duty_cycle(self.pin_led_pwr_dim_percent)
        sleep(0.2)
        LED.set_duty_cycle(0)

    def _dashcam_powerled_thread(self):
        round_cntr = 0
        round_time = 0.5

        LED_is_on = True

        LED_state_switch = {
            0: self.LED_info,
            2: self.LED_power
        }

        while True:
            if self.camera_state in LED_state_switch:
                LED = LED_state_switch[self.camera_state]
                if (self.info_led_state % 4) == 0 and (round_cntr % 60) == 0:
                    self._led_power_heartbeat(LED)
                elif (self.info_led_state % 4) == 1 and (round_cntr % 1) == 0:
                    self._led_power_heartbeat(LED)
                elif (self.info_led_state % 4) == 2:
                    if not LED_is_on:
                        LED.set_on()
                        LED.set_duty_cycle(self.pin_led_pwr_dim_percent)
                        LED_is_on = True
                else:
                    if LED_is_on:
                        LED.set_off()
                        LED_is_on = False
            elif self.camera_state == 1:
                if not LED_is_on:
                    self.LED_info.set_duty_cycle(self.pin_led_pwr_dim_percent)
                    LED_is_on = True
                else:
                    self.LED_info.set_off()
                    LED_is_on = False
            #sleep to make catch changes in e.g. info led status changes
            sleep(round_time)
            round_cntr += round_time

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
        self.file_lock.acquire()
        LED.set_on()

        video_file_list_legal = self.get_video_file_list_legal(
            self.get_directory_file_list(
                self.video_file_path, self.video_type
            ), reverse=False
        )

        timestamp = int(time())
        legal_path = f"{self.video_file_path_legal}/{timestamp}_utc"
        os.makedirs(legal_path, exist_ok=True)

        current_video = self.video_filename
        is_active_saving = current_video in video_file_list_legal
        if is_active_saving:
            video_file_list_legal.remove(current_video)

        for video_file in video_file_list_legal:
            src = f"{self.video_file_path}/{video_file}"
            dst = f"{legal_path}/INCIDENT_{video_file}"
            print(f"Copy '{src}' to '{dst}'.")
            try:
                shutil.copyfile(src, dst)
            except FileNotFoundError:
                print(f"WARNING! File '{src}' is gone. Ignoreing file. Continue")
        while is_active_saving and self.video_filename == current_video:
            #waiting for current video to finish
            sleep(5)
        if is_active_saving:
            src = f"{self.video_file_path}/{current_video}"
            dst = f"{legal_path}/INCIDENT_{current_video}"
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
        self.file_lock.release()

    def _button_copy_functor(self, input):
        if input == 0:
            self.save_video_file_legal(self.LED_data)

    def _button_start_functor(self, input):
        if input == 0:
            if self.camera_state == 0:
                self.camera_lock.acquire()
                self.camera_state = 2
                self.video_thread = Thread(target=self._dashcam_video_thread)
                self.video_thread.start()
                self.LED_power.set_duty_cycle(self.pin_led_pwr_dim_percent)
                sleep(10) #mainly user notification via LED on
                self.camera_lock.release()

    def _button_stop_functor(self, input):
        if input == 0:
            if self.camera_state == 2:
                self.camera_lock.acquire()
                self.camera_state = 1
                self.LED_power.set_off()
                self.camera_lock.release()

    def _button_info_functor(self, input):
        if input == 0:
            # in order to keep numbers small and as we probably won't
            # have more than 100 blinking states, lets keep it 0 < x < 100 !
            self.info_led_state = (self.info_led_state + 1) % 100

    def do_warning(self):
        # just blink at info LED!
        # can be used when e.g. mountpoint is unavailable!!!
        for _ in range(10):
            self.LED_info.set_on()
            sleep(0.5)
            self.LED_info.set_off()
            sleep(0.5)


    def start(self):
        os.makedirs(self.video_file_path, exist_ok=True)
        os.makedirs(self.video_file_path_legal, exist_ok=True)

        self.power_led_thread = Thread(target=self._dashcam_powerled_thread)
        self.clean_thread = Thread(target=self._dashcam_file_cleanup_thread)

        self.BTN_data.set_functor(self._button_copy_functor)
        self.BTN_power.set_functor(self._button_start_functor)
        self.BTN_stop.set_functor(self._button_stop_functor)
        self.BTN_info.set_functor(self._button_info_functor)

        self.power_led_thread.start()
        self.clean_thread.start()

        self._button_start_functor(0)

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
        default="video-dashcam", help=(
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
        "-lc", "--pin_led_copy", metavar="PLC", type=int, required=False,
        default=15, help="Pin number in GPIO.BOARD layout for a data-copy LED."
    )
    parser.add_argument(
        "-lp", "--pin_led_power", metavar="PLP", type=int, required=False,
        default=12, help="Pin number in GPIO.BOARD layout for a power LED."
    )
    parser.add_argument(
        "-li", "--pin_led_info", metavar="PLP", type=int, required=False,
        default=13, help="Pin number in GPIO.BOARD layout for an info LED."
    )
    parser.add_argument(
        "-bc", "--pin_button_copy", metavar="PBC", type=int, required=False,
        default=11, help="Pin number in GPIO.BOARD layout for a data copy button."
    )
    parser.add_argument(
        "-bp", "--pin_button_power", metavar="PBP", type=int, required=False,
        default=35, help="Pin number in GPIO.BOARD layout for a start button."
    )
    parser.add_argument(
        "-bs", "--pin_button_stop", metavar="PBS", type=int, required=False,
        default=37, help="Pin number in GPIO.BOARD layout for a stop button."
    )
    parser.add_argument(
        "-bi", "--pin_button_info", metavar="PBI", type=int, required=False,
        default=33, help="Pin number in GPIO.BOARD layout for a info-led control button."
    )
    parser.add_argument(
        "-d", "--pin_power_dim_percent", metavar="LPD", type=int, required=False,
        default=5, help="Percent dim for the Power LED; if it might be to bright."
    )
    parser.add_argument(
        "--external_usb_storage_device", metavar="DEVICE", type=str, required=False,
        help=(
            "Dev shortcut, e.g. sda1, for a partition/device you want to use as "
            "video storage. Will be directly written on it."
        )
    )

    args = parser.parse_args()

    video_chunk_duration = args.video_chunk_duration
    video_chunk_count = args.video_chunk_count
    video_file_path = args.video_file_path
    video_file_prefix = args.video_file_prefix
    video_resolution = args.video_resolution
    video_bitrate = args.video_bitrate
    video_format = args.video_format
    pin_button_copy = args.pin_button_copy
    pin_button_power = args.pin_button_power
    pin_button_stop = args.pin_button_stop
    pin_button_info = args.pin_button_info
    pin_led_power = args.pin_led_power
    pin_led_copy = args.pin_led_copy
    pin_led_info = args.pin_led_info
    pin_power_dim_percent = args.pin_power_dim_percent
    usb_storage = args.external_usb_storage_device if hasattr(args,'external_usb_storage_device') else None


    dashcam = Dashcam(
        sequence_count=video_chunk_count, sequence_length=video_chunk_duration,
        resolution=video_resolution, video_type=video_format, bitrate=video_bitrate,
        video_name_prefix=video_file_prefix, video_file_path=video_file_path,
        pin_btn_cpy=pin_button_copy, pin_btn_pwr=pin_button_power,
        pin_btn_info=pin_button_info, pin_btn_stop=pin_button_stop,
        pin_led_cpy=pin_led_copy, pin_led_pwr=pin_led_power, pin_led_info=pin_led_info,
        led_pwr_dim_perc=pin_power_dim_percent
    )


    if usb_storage is not None:
        usb_device = get_usb_storage_device(usb_storage)
        if usb_device is not None:
            mount_path = mount_usb_device(f"/dev/{usb_device}", dashcam.get_video_id())
            dashcam.set_video_path(mount_path)
        else:
            dashcam.do_warning()

    dashcam.start()
    dashcam.join_clean_thread()


if __name__=='__main__':
    main()
