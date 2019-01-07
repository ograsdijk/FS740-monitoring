import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import os
import glob
import pyvisa
import sys
import configparser
import time
import numpy as np
import shutil, errno
import visa
import atexit
import threading
import inspect
from contextlib import contextmanager
from influxdb import InfluxDBClient
from collections import OrderedDict

from drivers import FS740

@contextmanager
def get_connection(*args, **kwargs):
    connection = InfluxDBClient(*args, **kwargs)
    try:
        yield connection
    finally:
        connection.close()

class RecorderINFLUXDB(threading.Thread):
    def __init__(self, host, port, database, table, user, password,
                 driver, dt, driver_kwargs):
        # thread control
        threading.Thread.__init__(self)
        self.active = threading.Event()

        # record operating parameters
        self.host = host
        self.port = port
        self.database = database
        self.table = table
        self.user = user
        self.password = password
        self.driver = driver
        self.dt = dt
        if 'resource_manager' in driver_kwargs:
            driver_kwargs['resource_manager'] = visa.ResourceManager()
        self.driver_kwargs = driver_kwargs

        with self.driver(**driver_kwargs) as device:
            self.verify = device.VerifyOperation()

    # main recording loop
    def run(self):
        while self.active.is_set():
            with get_connection(host = self.host, port = int(self.port), username = self.user,
                                password = self.password) as con,\
                self.driver(**self.driver_kwargs) as device:
                con.switch_database(self.database)
                device.WriteValueINFLUXDB(con, self.table)
            time.sleep(self.dt)

class RecorderINFLUXDBGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        ########################################
        # recording control and status
        ########################################

        control_frame = tk.LabelFrame(self.parent)
        control_frame.grid(row=0, padx=10, pady=10, sticky="nsew")
        control_frame.grid_columnconfigure(index=2, weight=1)

        record_button = tk.Button(control_frame,
                text="\u26ab Start recording", command = self.start_recording)\
                .grid(row=0, column=0)
        stop_button = tk.Button(control_frame,
                text="\u2b1b Stop recording", command = self.stop_recording)\
                .grid(row=0, column=1)

        self.status = "stopped"
        self.status_message = tk.StringVar()
        self.status_message.set("Ready to Record")
        self.status_label = tk.Label(control_frame, textvariable=self.status_message,
                font=("Helvetica", 16),anchor='e')\
                .grid(row=0, column=2, sticky='nsew')

        ########################################
        # influxdb
        ########################################

        influxdb_frame = tk.LabelFrame(self.parent, text="INFLUXDB")
        influxdb_frame.grid(row=1, padx=10, pady=10, sticky=tk.W)

        tk.Label(influxdb_frame, text="host")\
                .grid(row=0, column=0, sticky=tk.E)
        influxdb_host = tk.Entry(influxdb_frame, width=25,
                textvariable=self.parent.config["host"])\
                .grid(row=0, column=1, sticky=tk.W)
        tk.Label(influxdb_frame, text="port")\
                .grid(row=0, column=2, sticky=tk.E)
        influxdb_port = tk.Entry(influxdb_frame, width=5,
                textvariable=self.parent.config["port"])\
                .grid(row=0, column=3, sticky=tk.W)
        tk.Label(influxdb_frame, text="user")\
                .grid(row=0, column=4, sticky=tk.E)
        influxdb_user = tk.Entry(influxdb_frame, width=10,
                textvariable=self.parent.config["user"])\
                .grid(row=0, column=5, sticky=tk.W)
        tk.Label(influxdb_frame, text="pass")\
                .grid(row=0, column=6, sticky=tk.E)
        influxdb_pass = tk.Entry(influxdb_frame, width=10,
                textvariable=self.parent.config["password"])\
                .grid(row=0, column=7, sticky=tk.W)

        tk.Label(influxdb_frame, text="db")\
                .grid(row=1, column=0, sticky=tk.E)
        influxdb_database = tk.Entry(influxdb_frame, width=25,
                textvariable=self.parent.config["database"])\
                .grid(row=1, column=1, sticky=tk.W)

        ########################################
        # devices
        ########################################

        devices_frame = tk.LabelFrame(self.parent, text="Devices")
        devices_frame.grid(row=2, padx=10, pady=10, sticky='nsew')

        # make the GUI elements and their variables for the list of devices
        self.device_GUI_list = OrderedDict()
        for d in self.parent.devices:

            self.device_GUI_list[d] = OrderedDict([
                ("enable_b"  , tk.Checkbutton(devices_frame, variable=self.parent.devices[d]["enabled"])),
                ("label"     , tk.Label(devices_frame, text=self.parent.devices[d]["label"])),
                ("dt"        , tk.Entry(devices_frame, textvariable=self.parent.devices[d]["dt"], width=5)),
                ("unit"      , tk.Label(devices_frame, text="s", width = 5))
            ])
            signature = inspect.getargspec(self.parent.devices[d]["driver"].__init__)
            driver_args  = signature.args[1:]
            for arg in driver_args:
                self.device_GUI_list[d][arg] =\
                tk.Entry(devices_frame, textvariable=self.parent.devices[d][arg], width=15)
                self.device_GUI_list[d][arg+'_label'] =\
                tk.Label(devices_frame, text = arg)

        # place the device list GUI elements in a grid
        for i,d in enumerate(self.device_GUI_list):
            for j,key in enumerate(self.device_GUI_list[d]):
                self.device_GUI_list[d][key].grid(row=i,column=j,sticky=tk.W)


    def start_recording(self):
        # check we're not recording already
        if self.status == "recording":
            return

        # check influxdb host
        host = self.parent.config["host"].get()
        port = self.parent.config["port"].get()
        user = self.parent.config["user"].get()
        password = self.parent.config["password"].get()
        database = self.parent.config["database"].get()
        with get_connection(host = host, port = int(port), username = user,
                            password = password) as con:
            try:
                con.ping()
            except:
                messagebox.showerror("Connection Error", "Error: cannot connect to INFLUXDB database")
                self.status_message.set("Error: cannot connect to INFLUXDB database")
                return

        # connect to devices and check they respond correctly
        for key in self.parent.devices:
            signature = inspect.getargspec(self.parent.devices[key]["driver"].__init__)
            driver_args  = signature.args[1:]
            d = self.parent.devices[key]
            kwargs_recorder = OrderedDict({arg: d[arg].get() for arg in driver_args})
            if d["enabled"].get():
                d["recorder"] = RecorderINFLUXDB(host, port, database, d["table"], user,
                                         password,
                                         d["driver"], float(d['dt'].get()),
                                         kwargs_recorder)
                if d["recorder"].verify != d["correct_response"]:
                    messagebox.showerror("Device error",
                            "Error: " + d["label"] + " not responding correctly.")
                    self.status_message.set("Device configuration error")
                    return
                d["recorder"].active.set()

        # start all recorders
        for key in self.parent.devices:
            if self.parent.devices[key]["enabled"].get():
                self.parent.devices[key]["recorder"].start()

        # update status
        self.status = "recording"
        self.status_message.set("Recording")

    def stop_recording(self):
        if self.status == "stopped":
            return
        for key in self.parent.devices:
            recorder = self.parent.devices[key].get("recorder")
            if recorder:
                recorder.active.clear()
        self.status = "stopped"
        self.status_message.set("Recording finished")

class CentrexClockGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.winfo_toplevel().title("CeNTREX Clock DAQ")
        self.parent = parent
        atexit.register(self.save_config)

        # read program settings
        self.config = {}
        settings = configparser.ConfigParser()
        settings.read("config/settings.ini")
        for sect in settings.sections():
            for key in settings[sect]:
                self.config[key] = tk.StringVar()
                self.config[key].set(settings[sect][key])

        # read list of devices
        self.devices = OrderedDict()
        devices = configparser.ConfigParser()
        devices.read("config/devices.ini")
        for d in devices.sections():
            signature = inspect.getargspec(eval(devices[d]["driver"]).__init__)
            driver_args  = signature.args[1:]
            self.devices[d] = OrderedDict([
                        ("label"             , devices[d]["label"]),
                        ("driver"            , eval(devices[d]["driver"])),
                        ("table"             , devices[d]["table"]),
                        ("dt"                , tk.StringVar()),
                        ("enabled"           , tk.IntVar()),
                        ("correct_response"  , devices[d]["correct_response"]),
                    ])
            self.devices[d]["enabled"].set(devices[d].getboolean("enabled"),)
            self.devices[d]["dt"].set(devices[d].getfloat("dt"),)

            for arg in driver_args:
                self.devices[d][arg] = tk.StringVar()
                self.devices[d][arg].set(devices[d][arg])

        # GUI elements
        self.recordergui = RecorderINFLUXDBGUI(self, *args, **kwargs)
        self.recordergui.grid(row=0, column=0)

    def save_config(self):
        # write program settings to disk
        with open("config/settings.ini", 'w') as settings_f:
            settings = configparser.ConfigParser()
            settings['influxdb'] = OrderedDict([
                    ('host'      , self.config['host'].get()),
                    ('port'      , self.config['port'].get()),
                    ('database'  , self.config['database'].get()),
                    ('user'      , self.config['user'].get()),
                    ('password'  , self.config['password'].get()),
                ])
            settings.write(settings_f)

        # write device configuration to disk
        with open("config/devices.ini", 'w') as dev_f:
            dev = configparser.ConfigParser()
            for d in self.devices:
                signature = inspect.getargspec(self.devices[d]["driver"].__init__)
                driver_args  = signature.args[1:]
                dev[d] = OrderedDict([
                        ("label"             , self.devices[d]["label"]),
                        ("driver"            , self.devices[d]["driver"].__name__),
                        ("table"             , self.devices[d]["table"]),
                        ("dt"                , self.devices[d]["dt"].get()),
                        ("enabled"           , self.devices[d]["enabled"].get()),
                        ("correct_response"  , self.devices[d]["correct_response"]),
                ])
                for arg in driver_args:
                    dev[d][arg] = self.devices[d][arg].get()
            dev.write(dev_f)

if __name__ == "__main__":
    root = tk.Tk()
    CentrexClockGUI(root).pack(side="top", fill="both", expand=True)
    root.mainloop()
