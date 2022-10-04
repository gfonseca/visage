#!/usr/bin/env python3
from concurrent.futures import process
import time
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
import sys
import pygame
import numpy as np
import cv2
from mss import mss
from PIL import Image
import sys
import gi
from threading import Thread
from itertools import cycle


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class ProcessState:
    def __init__(self, monitor_number):
        self.set_monitor(monitor_number)
        self.total_monitors = self.get_monitor_count()
        self.pixel_len = 10

        self.server_socket = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        self.server_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        
        self.client_socket = socket(family=AF_INET, type=SOCK_DGRAM)
        self.client_socket.bind(("0.0.0.0", 4211))
        self.client_socket.settimeout(3)
        self.running = True
        self.ip_label = 'SERVER NOT FOUND'
        
        self.broadcast_address = ("255.255.255.255", 4210)
        self.server_ip = None

        self.transmission_thread = None
        self.start_transmission_thread()
       
    def get_monitor_count(self):
        with mss() as sct:
            return len(sct.monitors) -1 

    def set_monitor(self, monitor_number: int):
        with mss() as sct:
            try:
                n = int(monitor_number)
                self.monitor = sct.monitors[n]
            except:
                fail(f"Invalid Monitor number {monitor_number}")
    
    def start_transmission_thread(self):
        self.transmission_thread = run_transmission_thread(self)
    
    def stop(self):
        self.running = False

def run_transmission_thread(state: ProcessState) -> Thread:
    TRANSMITER_THREAD = Thread(target=run_screen_transmiter, args=(state,))
    TRANSMITER_THREAD.start()
    return TRANSMITER_THREAD

def fail(msg: str):
    print("[ERROR]", msg)
    sys.exit(1)

def show_mini_monitor(img):
    cv2.imshow('test', img)
    if cv2.waitKey(33) & 0xFF in (
        ord('q'), 
        27, 
    ): return

def decode_message(msg: bytearray, state: ProcessState):
    sign = msg[:3].decode("UTF-8")

    if sign != "vsg":
        raise Exception("Invalid server header")

    command = int(msg[3])

    if command == 10:
        state.pixel_len = msg[4] | msg[5] << 8
        print(f"Updated pixel_len to {state.pixel_len}")

def run_screen_transmiter(process_state: ProcessState):
    data = MAGIC.encode('UTF-8')
    pool = cycle(['.'*i for i in range(10)])
    clock = pygame.time.Clock()

    process_state.running = True
    process_state.ip_label = f"Searching for server {next(pool)}"
    process_state.server_ip = None
    
    while not process_state.server_ip and process_state.running:
        process_state.ip_label = f"Searching for server {next(pool)}"
        process_state.server_socket.sendto(data, process_state.broadcast_address)

        try:
            msgFromServer = process_state.client_socket.recvfrom(1024)
        except: 
            continue

        process_state.server_ip = msgFromServer[1]
        process_state.ip_label = process_state.server_ip[0]

        try:
            decode_message(msgFromServer[0], process_state)
        except Exception as e:
            print("Failed to decode server message.", e)

    with mss() as sct:
        while process_state.running:
            screenShot = sct.grab(process_state.monitor)
            img = Image.frombytes(
                'RGB', 
                (screenShot.width, screenShot.height), 
                screenShot.rgb, 
            )
            img_array = np.array(img.resize((process_state.pixel_len, process_state.pixel_len)) )
            # show_mini_monitor(img_array)
            colum = img_array[:, -1][::-1]
            pixels = bytearray(np.matrix.flatten(colum))
            process_state.server_socket.sendto(pixels, process_state.server_ip)
            clock.tick(30)
    
    process_state.ip_label  = "Transmission Stopped."
    process_state.stop()


SERVER_PORT         = 4210
CLIENT_PORT         = 4211
MAGIC               = "fna349fn"
bufferSize          = 1024
MONITOR = int(sys.argv[1])

PROCESS_STATE = ProcessState(sys.argv[1])



class MyWindow(Gtk.Window):
    def __init__(self, process_state: ProcessState):
        super().__init__(title="Visage")

        GLib.timeout_add(200, self.update_labels)

        self.connect("destroy", self.hide_app)

        self.state = process_state

        self.quit_button = Gtk.Button(label="Quit")
        self.quit_button.connect("clicked", self.quit_app)

        self.stop_button = Gtk.Button(label="Stop Transmission")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        
        self.start_button = Gtk.Button(label="Start Transmission")
        self.start_button.connect("clicked", self.on_start_clicked)
        
       
        
        self.ip_label = Gtk.Label(label=self.state.ip_label)

        self.frame = Gtk.Frame(label="server IP")
        self.frame.add(self.ip_label)

        self.status_label = Gtk.Label(label="STOP")

        self.frame_state = Gtk.Frame(label="Transmission Status")
        self.frame_state.add(self.status_label)

        self.grid = Gtk.Grid(
            row_spacing=10,
            column_spacing=10,
            margin_bottom=10,
            margin_start=10,
            margin_end=10,
            margin_top=10
        )

        monitors_options = self.build_monitors_buttons()

        self.grid.attach(self.frame, 0, 0, 3, 2)
        self.grid.attach(self.frame_state, 0, 3, 3, 2)
        self.grid.attach(monitors_options, 0, 6, 3, 2)
        self.grid.attach(self.stop_button, 0, 9, 1, 1 )
        self.grid.attach(self.start_button, 1, 9, 1, 1)
        self.grid.attach(self.quit_button, 2, 9, 1, 1)

        self.add(self.grid)

    def on_stop_clicked(self, widget):
        self.state.stop() 
    
    def on_start_clicked(self, widget):
        self.state.stop()
        time.sleep(6)
        self.state.start_transmission_thread()
    
    def on_monitor_toggled(self, button, name):
        self.state.set_monitor(name)
        
    def build_monitors_buttons(self):
        frame = Gtk.Frame(label="Monitors")        
        hbox = Gtk.Box(spacing=6)
        
        btn1 = Gtk.RadioButton.new_with_label_from_widget(None, f"Monitor 1")
        btn1.connect("toggled", self.on_monitor_toggled, 1)
        
        hbox.pack_start(btn1, False, False, 0)
        
        for i in range(1, self.state.total_monitors):
            btn = Gtk.RadioButton.new_with_label_from_widget(btn1, f"Monitor {i+1}")
            btn.set_label(f"Monitor {i+1}")
            btn.connect("toggled", self.on_monitor_toggled, i+1)
            hbox.pack_start(btn, False, False, 0)
        
        frame.add(hbox)
        return frame

    def get_server_ip(self):
        return self.state.server_ip[0] if self.state.server_ip is not None else "No Ip"

    def quit_app(self, window):
        self.state.stop()
        Gtk.main_quit()

    def hide_app(self, window):
        self.hide()
    
    def update_labels(self):
        self.ip_label.set_label(self.state.ip_label)
        self.status_label.set_label("RUNNING" if self.state.running and self.state.server_ip else "STOPPED")
        self.set_buttons_state()
        return GLib.SOURCE_CONTINUE

    def set_buttons_state(self):
        self.start_button.set_sensitive(bool(not self.state.running))
        self.stop_button.set_sensitive(bool(self.state.running))


win = MyWindow(process_state=PROCESS_STATE)
win.show_all()
Gtk.main()
